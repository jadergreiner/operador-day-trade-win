#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditoria de Episodios Micro Tendencia (CALIBRACAO-MICRO-03).

Relatorio operacional:
  - Quantos episodios acumulados com outcome conhecido
  - Win rate real do Micro Tendencia (nao do backtest)
  - Ultima vez que AC6.8 retreinou o modelo
  - Versao atual do LightGBM em producao

Uso:
    python scripts/auditoria_micro_episodios.py
    python scripts/auditoria_micro_episodios.py --db data/db/trading.db
    python scripts/auditoria_micro_episodios.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def _conectar(db_path: str) -> sqlite3.Connection:
    if not Path(db_path).exists():
        print(f"[ERRO] Banco nao encontrado: {db_path}")
        sys.exit(1)
    return sqlite3.connect(db_path)


def _auditoria_episodios(conn: sqlite3.Connection) -> dict:
    """Consulta tabela micro_episodios."""
    cur = conn.cursor()

    # Total com outcome
    try:
        cur.execute(
            "SELECT COUNT(*) FROM micro_episodios WHERE outcome IS NOT NULL"
        )
        total = int(cur.fetchone()[0])
    except Exception:
        total = 0

    if total == 0:
        return {
            "total_episodios": 0,
            "win_rate_real": None,
            "wins": 0,
            "losses": 0,
            "breakevens": 0,
            "pnl_medio_pts": None,
            "pnl_total_pts": None,
            "primeiro_episodio": None,
            "ultimo_episodio": None,
            "status": "SEM_EPISODIOS",
        }

    # Wins/Losses/Breakevens
    cur.execute(
        """
        SELECT
            SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END),
            SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END),
            SUM(CASE WHEN outcome='BREAKEVEN' THEN 1 ELSE 0 END),
            AVG(resultado_pts),
            SUM(resultado_pts),
            MIN(timestamp_entrada),
            MAX(timestamp_entrada)
        FROM micro_episodios
        WHERE outcome IS NOT NULL
        """
    )
    row = cur.fetchone()
    wins = int(row[0] or 0)
    losses = int(row[1] or 0)
    breakevens = int(row[2] or 0)
    pnl_medio = float(row[3] or 0.0)
    pnl_total = float(row[4] or 0.0)
    primeiro = str(row[5] or "")
    ultimo = str(row[6] or "")

    win_rate = wins / total if total > 0 else 0.0

    return {
        "total_episodios": total,
        "win_rate_real": round(win_rate, 4),
        "wins": wins,
        "losses": losses,
        "breakevens": breakevens,
        "pnl_medio_pts": round(pnl_medio, 2),
        "pnl_total_pts": round(pnl_total, 2),
        "primeiro_episodio": primeiro,
        "ultimo_episodio": ultimo,
        "status": "COM_EPISODIOS",
    }


def _auditoria_diario(conn: sqlite3.Connection) -> dict:
    """Consulta tabela diario_episodios (inclui entradas do Micro Tendencia)."""
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT COUNT(*) FROM diario_episodios WHERE resultado_pts IS NOT NULL"
        )
        total = int(cur.fetchone()[0])
    except Exception:
        return {"total": 0, "status": "TABELA_INEXISTENTE"}

    cur.execute(
        """
        SELECT
            SUM(CASE WHEN foi_acerto=1 THEN 1 ELSE 0 END),
            AVG(resultado_pts),
            MAX(timestamp_saida)
        FROM diario_episodios
        WHERE resultado_pts IS NOT NULL
        """
    )
    row = cur.fetchone()
    return {
        "total": total,
        "wins": int(row[0] or 0),
        "pnl_medio_pts": round(float(row[1] or 0.0), 2),
        "ultimo_registro": str(row[2] or ""),
        "status": "OK",
    }


def _auditoria_execution_feedback(conn: sqlite3.Connection) -> dict:
    """Consulta tabela execution_feedback."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM execution_feedback")
        total = int(cur.fetchone()[0])
    except Exception:
        return {"total": 0, "status": "TABELA_INEXISTENTE"}

    cur.execute(
        """
        SELECT
            SUM(CASE WHEN outcome_type='WIN' THEN 1 ELSE 0 END),
            SUM(CASE WHEN outcome_type='LOSS' THEN 1 ELSE 0 END),
            MAX(created_at)
        FROM execution_feedback
        """
    )
    row = cur.fetchone()
    return {
        "total": total,
        "wins": int(row[0] or 0),
        "losses": int(row[1] or 0),
        "ultimo_feedback": str(row[2] or ""),
        "status": "OK",
    }


def _auditoria_modelo_lgbm(models_dir: str = "data/models") -> dict:
    """Verifica versao atual do LightGBM em producao."""
    models_path = Path(models_dir)

    # Busca arquivos de modelo LightGBM
    padroes = [
        "lgbm_model*.pkl",
        "lightgbm*.pkl",
        "modelo_lgbm*.pkl",
        "*.lgbm",
    ]
    arquivos: list[tuple[float, Path]] = []
    for padrao in padroes:
        for f in models_path.glob(padrao):
            arquivos.append((f.stat().st_mtime, f))

    if not arquivos:
        return {
            "versao": "NAO_ENCONTRADO",
            "data_treino": None,
            "caminho": None,
            "status": "MODELO_AUSENTE",
        }

    # Modelo mais recente
    arquivos.sort(reverse=True)
    _, modelo_path = arquivos[0]
    mtime = modelo_path.stat().st_mtime
    data_treino = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

    # Versao via baseline_history.json (gerado pelo AC6.9)
    versao = "desconhecida"
    history_path = models_path / "baseline_history.json"
    if history_path.exists():
        try:
            with open(history_path) as f:
                history = json.load(f)
            if history:
                versao = history[-1].get("version_id", "desconhecida")
        except Exception:
            pass

    return {
        "versao": versao,
        "data_treino": data_treino,
        "caminho": str(modelo_path),
        "status": "OK" if "2026-03" in data_treino else "DESATUALIZADO",
    }


def _auditoria_ultimo_retreino(conn: sqlite3.Connection) -> dict:
    """Verifica ultima vez que AC6.8 executou retreinamento."""
    cur = conn.cursor()
    # Tabela rl_training_metrics e gerada pelo AC6.8
    try:
        cur.execute(
            """
            SELECT MAX(created_at), COUNT(*)
            FROM rl_training_metrics
            """
        )
        row = cur.fetchone()
        ultimo = str(row[0] or "")
        total = int(row[1] or 0)
    except Exception:
        return {
            "ultimo_retreino": None,
            "total_retreinos": 0,
            "status": "TABELA_INEXISTENTE",
        }

    return {
        "ultimo_retreino": ultimo,
        "total_retreinos": total,
        "status": "OK" if ultimo else "SEM_RETREINOS",
    }


def _imprimir_relatorio(relatorio: dict) -> None:
    """Imprime relatorio formatado no terminal."""
    ep = relatorio["episodios"]
    diario = relatorio["diario_episodios"]
    feedback = relatorio["execution_feedback"]
    modelo = relatorio["modelo_lgbm"]
    retreino = relatorio["ultimo_retreino"]
    gerado_em = relatorio["gerado_em"]

    print("\n" + "=" * 68)
    print("  AUDITORIA MICRO TENDENCIA — CALIBRACAO-MICRO-03")
    print(f"  Gerado: {gerado_em}")
    print("=" * 68)

    # Episodios
    print("\n  [1] EPISODIOS ACUMULADOS (micro_episodios)")
    if ep["status"] == "SEM_EPISODIOS":
        print("      Nenhum episodio registrado ainda.")
        print("      > Aguardando CALIBRACAO-MICRO-01 liberar os primeiros trades.")
    else:
        wr = ep["win_rate_real"]
        wr_icon = "🟢" if wr >= 0.55 else ("🟡" if wr >= 0.45 else "🔴")
        print(f"      Total: {ep['total_episodios']}")
        print(f"      {wr_icon} Win Rate real: {wr:.1%} (baseline: 55%)")
        print(f"      Wins: {ep['wins']}  Losses: {ep['losses']}  "
              f"Breakevens: {ep['breakevens']}")
        print(f"      PnL medio: {ep['pnl_medio_pts']:+.1f} pts")
        print(f"      PnL total: {ep['pnl_total_pts']:+.1f} pts")
        print(f"      Primeiro: {ep['primeiro_episodio'][:19]}")
        print(f"      Ultimo:   {ep['ultimo_episodio'][:19]}")

    # Diario episodios
    print("\n  [2] DIARIO_EPISODIOS (formato EpisodioOperador)")
    if diario["status"] == "TABELA_INEXISTENTE":
        print("      Tabela nao encontrada.")
    else:
        print(f"      Total: {diario['total']}")
        if diario["total"] > 0:
            print(f"      Wins: {diario['wins']}")
            print(f"      PnL medio: {diario['pnl_medio_pts']:+.1f} pts")
            print(f"      Ultimo: {diario['ultimo_registro'][:19]}")

    # Execution feedback
    print("\n  [3] EXECUTION_FEEDBACK (ciclo AC5.9)")
    if feedback["status"] == "TABELA_INEXISTENTE":
        print("      Tabela nao encontrada.")
    else:
        print(f"      Total: {feedback['total']}")
        if feedback["total"] > 0:
            print(f"      Wins: {feedback['wins']}  Losses: {feedback['losses']}")
            print(f"      Ultimo: {feedback['ultimo_feedback'][:19]}")

    # Ultimo retreino AC6.8
    print("\n  [4] ULTIMO RETREINO AC6.8 (OnlineLearning)")
    if retreino["status"] == "TABELA_INEXISTENTE":
        print("      Tabela rl_training_metrics nao encontrada.")
    elif retreino["status"] == "SEM_RETREINOS":
        print("      Nenhum retreino executado ainda.")
        t = ep.get("total_episodios", 0)
        restam = max(0, 20 - t)
        if restam > 0:
            print(f"      > Faltam {restam} episodio(s) para atingir threshold de 20.")
    else:
        print(f"      Ultimo retreino: {retreino['ultimo_retreino'][:19]}")
        print(f"      Total de retreinos: {retreino['total_retreinos']}")

    # Modelo LightGBM
    print("\n  [5] MODELO LIGHTGBM EM PRODUCAO")
    m_icon = "🟢" if modelo["status"] == "OK" else "🔴"
    print(f"      {m_icon} Versao: {modelo['versao']}")
    if modelo["data_treino"]:
        print(f"      Data de treino: {modelo['data_treino']}")
    if modelo["caminho"]:
        print(f"      Arquivo: {modelo['caminho']}")
    if modelo["status"] == "MODELO_AUSENTE":
        print("      > Modelo nao encontrado em data/models/.")
    elif modelo["status"] == "DESATUALIZADO":
        print("      > Modelo anterior a marco/2026. Retreino necessario.")

    print("\n" + "=" * 68)

    # Conclusao
    total_ep = ep.get("total_episodios", 0)
    print("\n  CONCLUSAO:")
    if total_ep == 0:
        print("  [!] Sem episodios — agente ainda nao operou.")
        print("      Verificar CALIBRACAO-MICRO-01 (threshold de confianca).")
    elif total_ep < 10:
        print(f"  [~] {total_ep}/10 episodios para acionar AC6.7 (DriftDetector).")
    elif total_ep < 20:
        print(f"  [~] {total_ep}/20 episodios para acionar AC6.8 (OnlineLearning).")
    else:
        wr = ep.get("win_rate_real", 0.0) or 0.0
        if wr >= 0.55:
            print(f"  [OK] {total_ep} episodios | WR={wr:.1%} | Pipeline ativo.")
        else:
            print(
                f"  [!] {total_ep} episodios | WR={wr:.1%} abaixo do baseline (55%)."
            )
            print("      Verificar AC6.7 por alertas de drift.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auditoria de episodios do Micro Tendencia (CALIBRACAO-MICRO-03)"
    )
    parser.add_argument(
        "--db",
        default="data/db/trading.db",
        help="Caminho para o banco SQLite (padrao: data/db/trading.db)",
    )
    parser.add_argument(
        "--models-dir",
        default="data/models",
        help="Diretorio dos modelos ML (padrao: data/models)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Saida em formato JSON",
    )
    args = parser.parse_args()

    conn = _conectar(args.db)

    relatorio = {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "db_path": args.db,
        "episodios": _auditoria_episodios(conn),
        "diario_episodios": _auditoria_diario(conn),
        "execution_feedback": _auditoria_execution_feedback(conn),
        "ultimo_retreino": _auditoria_ultimo_retreino(conn),
        "modelo_lgbm": _auditoria_modelo_lgbm(args.models_dir),
    }

    conn.close()

    if args.json:
        print(json.dumps(relatorio, ensure_ascii=False, indent=2))
    else:
        _imprimir_relatorio(relatorio)


if __name__ == "__main__":
    main()
