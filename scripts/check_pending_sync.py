#!/usr/bin/env python3
"""
P50-CHECK: Verificação de Operações Pendentes no Startup

Executado no início de cada sessão (via launchers .bat) para detectar e alertar
sobre trades e posições que ficaram pendentes do pregão anterior sem persistência
no SQLite.

Detecta:
  1. posicoes_abertas com data anterior ao dia atual (orphans de sessão anterior)
  2. trades com status='OPEN' criados antes de hoje (não foram fechados no banco)
  3. Divergência entre JSONs de histórico e registros no SQLite

Ação:
  - Modo REPORT (padrão): lista pendências e avisa, sem alterar dados
  - Modo AUTO (--auto): tenta resolver automaticamente via sync_mt5_trades_to_db
  - Sempre retorna exit code 0 (não bloqueia o startup)

Uso:
  python scripts/check_pending_sync.py
  python scripts/check_pending_sync.py --auto
  python scripts/check_pending_sync.py --db data/db/trading_rl_direto.db
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
OUTPUTS_DIR = ROOT_DIR / "outputs"

# Valor do ponto do mini-índice WIN (R$ por ponto por contrato)
VALOR_PONTO_WIN = 0.20


def _log(msg: str, level: str = "INFO") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "[INFO]", "WARN": "[AVISO]", "OK": "[OK]", "FIX": "[CORR]"}.get(level, "[INFO]")
    print(f"  {prefix} {ts} {msg}")


def _resolve_db(args_db: str | None) -> Path:
    """Resolve o banco SQLite a ser verificado."""
    if args_db:
        return Path(args_db).expanduser()

    # Seguir mesma prioridade do db_paths.py
    for env_var in ("DIARIOS_DB_PATH", "RL_DIRETO_DB_PATH", "RL5000_DB_PATH",
                    "MICRO_TENDENCIA_DB_PATH", "TRADING_DB_PATH", "DB_PATH"):
        val = os.getenv(env_var, "").strip()
        if val:
            return Path(val)

    return ROOT_DIR / "data" / "db" / "trading.db"


def _check_posicoes_abertas(cur: sqlite3.Cursor, hoje: str) -> list[dict]:
    """Retorna posições abertas de dias anteriores (orphans)."""
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posicoes_abertas'")
    if not cur.fetchone():
        return []

    cur.execute(
        """
        SELECT posicao_id, trade_id, symbol, direcao, preco_entrada, criado_em
        FROM posicoes_abertas
        WHERE DATE(criado_em) < ?
        ORDER BY criado_em
        """,
        (hoje,),
    )
    rows = cur.fetchall()
    return [
        {"posicao_id": r[0], "trade_id": r[1], "symbol": r[2],
         "direcao": r[3], "preco_entrada": r[4], "criado_em": r[5]}
        for r in rows
    ]


def _check_trades_open_antigos(cur: sqlite3.Cursor, hoje: str) -> list[dict]:
    """Retorna trades com status OPEN criados antes de hoje."""
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
    if not cur.fetchone():
        return []

    cur.execute(
        """
        SELECT trade_id, symbol, side, entry_price, entry_time, status
        FROM trades
        WHERE status = 'OPEN' AND DATE(entry_time) < ?
        ORDER BY entry_time
        """,
        (hoje,),
    )
    rows = cur.fetchall()
    return [
        {"trade_id": r[0], "symbol": r[1], "side": r[2],
         "entry_price": r[3], "entry_time": r[4], "status": r[5]}
        for r in rows
    ]


def _check_json_nao_sincronizados(db_path: Path, hoje: str) -> list[dict]:
    """
    Verifica JSONs de historico_fechamentos do dia anterior que não estão no SQLite.
    Retorna lista de tickets pendentes.
    """
    ontem = (datetime.now().date() - timedelta(days=1)).isoformat()
    hist_files = glob.glob(str(OUTPUTS_DIR / "historico_fechamentos_*.json"))

    pendentes = []
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
    if not cur.fetchone():
        conn.close()
        return []

    for f_path in hist_files:
        try:
            items = json.loads(Path(f_path).read_text(encoding="utf-8"))
            for item in items:
                ticket = item.get("ticket")
                ts_fechamento = item.get("timestamp_fechamento", "")
                if not ticket or not ts_fechamento:
                    continue
                # Só checar fechamentos de ontem
                if not ts_fechamento.startswith(ontem):
                    continue
                # Verificar se está no banco
                cur.execute(
                    "SELECT id FROM trades WHERE trade_id = ? AND status = 'CLOSED'",
                    (str(ticket),),
                )
                if not cur.fetchone():
                    pendentes.append({
                        "ticket": ticket,
                        "motivo": item.get("motivo"),
                        "pnl": item.get("pnl_reais"),
                        "timestamp": ts_fechamento,
                        "arquivo": Path(f_path).name,
                    })
        except Exception:
            pass

    conn.close()
    return pendentes


def _tentar_sync_automatico(db_path: Path) -> bool:
    """Tenta rodar sync_mt5_trades_to_db.py para recuperar trades pendentes."""
    sync_script = SCRIPTS_DIR / "sync_mt5_trades_to_db.py"
    if not sync_script.exists():
        _log("Script sync_mt5_trades_to_db.py não encontrado — sync automático indisponível.", "WARN")
        return False

    _log("Tentando sync automático via sync_mt5_trades_to_db.py (--days-back 2)...", "FIX")
    try:
        result = subprocess.run(
            [sys.executable, str(sync_script), "--db", str(db_path), "--days-back", "2", "--lock-timeout", "10"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            _log(f"Sync concluído: {result.stdout.strip()}", "OK")
            return True
        else:
            _log(f"Sync falhou (code={result.returncode}): {result.stderr.strip()[:200]}", "WARN")
            return False
    except subprocess.TimeoutExpired:
        _log("Sync expirou (>60s) — verifique conexão com MT5.", "WARN")
        return False
    except Exception as e:
        _log(f"Erro ao rodar sync: {e}", "WARN")
        return False


def _espelhar_para_diarios(db_path: Path) -> None:
    """Espelha trades CLOSED de ontem do DB atual para trading_diarios.db."""
    diarios_db = ROOT_DIR / "data" / "db" / "trading_diarios.db"
    if not diarios_db.exists() or db_path == diarios_db:
        return

    ontem = (datetime.now().date() - timedelta(days=1)).isoformat()

    try:
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(diarios_db))
        src_cur = src.cursor()
        dst_cur = dst.cursor()

        # Verificar se trading_diarios.db tem tabela trades
        dst_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
        if not dst_cur.fetchone():
            src.close()
            dst.close()
            return

        src_cur.execute(
            """
            SELECT trade_id, symbol, side, quantity, entry_price, entry_time,
                   exit_price, exit_time, stop_loss, take_profit, status,
                   broker_trade_id, commission, profit_loss, return_percentage,
                   notes, created_at, updated_at, execution_method
            FROM trades
            WHERE DATE(entry_time) = ? AND status = 'CLOSED'
            """,
            (ontem,),
        )
        rows = src_cur.fetchall()
        inserted = 0
        for r in rows:
            dst_cur.execute("SELECT id FROM trades WHERE trade_id = ?", (r[0],))
            if not dst_cur.fetchone():
                dst_cur.execute(
                    """INSERT INTO trades (trade_id, symbol, side, quantity, entry_price, entry_time,
                        exit_price, exit_time, stop_loss, take_profit, status,
                        broker_trade_id, commission, profit_loss, return_percentage,
                        notes, created_at, updated_at, execution_method)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    r,
                )
                inserted += 1
        dst.commit()
        src.close()
        dst.close()

        if inserted > 0:
            _log(f"{inserted} trades de {ontem} espelhados para trading_diarios.db", "FIX")
    except Exception as e:
        _log(f"Erro ao espelhar para trading_diarios.db: {e}", "WARN")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica operações pendentes no startup.")
    parser.add_argument("--db", type=str, default=None, help="Caminho do SQLite a verificar.")
    parser.add_argument("--auto", action="store_true", help="Tenta corrigir automaticamente via sync MT5.")
    parser.add_argument("--quiet", action="store_true", help="Suprimir output se sem pendências.")
    args = parser.parse_args()

    hoje = datetime.now().date().isoformat()
    db_path = _resolve_db(args.db)

    if not db_path.exists():
        if not args.quiet:
            _log(f"Banco não encontrado: {db_path} — nenhuma pendência verificada.", "WARN")
        return 0

    print()
    print("  ┌─────────────────────────────────────────────────────┐")
    print(f"  │  P50-CHECK  Verificação de Pendências de Startup    │")
    print(f"  │  Banco : {db_path.name:<44}│")
    print(f"  │  Data  : {hoje:<44}│")
    print("  └─────────────────────────────────────────────────────┘")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    pendencias = False

    # 1. posicoes_abertas de dias anteriores
    orphans = _check_posicoes_abertas(cur, hoje)
    if orphans:
        pendencias = True
        _log(f"{len(orphans)} posição(ões) ABERTAS do pregão anterior detectada(s):", "WARN")
        for p in orphans:
            data = p['criado_em'][:10] if p['criado_em'] else "?"
            _log(f"   ticket={p['trade_id']} | {p['direcao']} {p['symbol']} @ {p['preco_entrada']} | data={data}", "WARN")
    else:
        if not args.quiet:
            _log("posicoes_abertas: nenhuma pendência do pregão anterior.", "OK")

    # 2. Trades OPEN antigos
    trades_antigos = _check_trades_open_antigos(cur, hoje)
    if trades_antigos:
        pendencias = True
        _log(f"{len(trades_antigos)} trade(s) OPEN de dias anteriores detectado(s):", "WARN")
        for t in trades_antigos:
            data = t['entry_time'][:10] if t['entry_time'] else "?"
            _log(f"   trade_id={t['trade_id']} | {t['side']} {t['symbol']} @ {t['entry_price']} | data={data}", "WARN")
    else:
        if not args.quiet:
            _log("trades OPEN antigos: nenhuma pendência.", "OK")

    conn.close()

    # 3. JSONs de histórico não sincronizados (ontem)
    json_pendentes = _check_json_nao_sincronizados(db_path, hoje)
    if json_pendentes:
        pendencias = True
        _log(f"{len(json_pendentes)} fechamento(s) de ontem no JSON ainda não no SQLite:", "WARN")
        for j in json_pendentes:
            _log(f"   ticket={j['ticket']} | {j['motivo']} | PnL=R${j['pnl']:.2f} | {j['arquivo']}", "WARN")
    else:
        if not args.quiet:
            _log("JSONs de histórico: tudo sincronizado.", "OK")

    # Ação: sync automático se solicitado ou se houver pendências
    if pendencias:
        print()
        if args.auto:
            _log("Modo AUTO ativo — iniciando recuperação...", "FIX")
            synced = _tentar_sync_automatico(db_path)
            if synced:
                _espelhar_para_diarios(db_path)
                _log("Recuperação concluída. Verifique os bancos ao final.", "OK")
            else:
                _log("Sync automático não disponível (MT5 offline?). Pendências persistem.", "WARN")
                _log("Execute manualmente após o pregão:", "WARN")
                _log(f"  python scripts/sync_mt5_trades_to_db.py --db {db_path.name} --days-back 2", "WARN")
        else:
            _log("Execute 'check_pending_sync.py --auto' para tentar recuperação automática.", "WARN")
            _log("Ou aguarde: o P50-SYNC ao final do pregão resolverá as pendências.", "WARN")
    else:
        if not args.quiet:
            _log("Nenhuma pendência detectada. Banco em estado limpo.", "OK")

    print()
    # Sempre retorna 0 — nunca bloqueia o startup
    return 0


if __name__ == "__main__":
    sys.exit(main())
