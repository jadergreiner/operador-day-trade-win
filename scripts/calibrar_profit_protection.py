"""
Entrypoint CLI para calibração de perfis do ProfitProtectionEngine.

Carrega trades do SQLite, executa replay com baseline + candidatos,
e grava relatório em outputs/profit_protection/.

Uso:
    python scripts/calibrar_profit_protection.py
    python scripts/calibrar_profit_protection.py --perfis conservador agressivo
    python scripts/calibrar_profit_protection.py --db caminho/custom.db
    python scripts/calibrar_profit_protection.py --dry-run
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Raiz do projeto
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.application.services.profit_protection_calibration_service import (
    calibrar_perfis,
)
from src.infrastructure.config.config_loader import ConfigLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("calibrar_profit_protection")

# ============================================================
# CONSTANTES
# ============================================================

DB_PADRAO = _ROOT / "data" / "db" / "trading.db"
CONFIG_PADRAO = _ROOT / "config" / "profit_protection.yaml"
OUTPUT_DIR = _ROOT / "outputs" / "profit_protection"


# ============================================================
# CARGA DE TRADES DO SQLite
# ============================================================


def _carregar_trades_sqlite(db_path: Path) -> list:
    """Lê trades fechados do banco.

    Retorna lista de dicts compatíveis com `calibrar_perfis`.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Banco não encontrado: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()

        # Verifica se tabela existe
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='trades'"
        )
        if not cursor.fetchone():
            logger.warning("Tabela 'trades' não encontrada; retornando lista vazia.")
            return []

        cursor.execute(
            """
            SELECT
                id as trade_id,
                symbol,
                side as direction,
                entry_price,
                exit_price,
                quantity,
                stop_loss as initial_sl,
                take_profit as initial_tp,
                return_percentage as resultado_pct,
                entry_time
            FROM trades
            WHERE status = 'CLOSED'
              AND return_percentage IS NOT NULL
            ORDER BY entry_time ASC
            """
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    trades = []
    for row in rows:
        entry = float(row["entry_price"] or 0)
        exit_p = float(row["exit_price"] or entry)

        # Simula preços tick-by-tick com 3 pontos: entrada, meio e saída
        medio = (entry + exit_p) / 2
        precos = [entry, medio, exit_p]

        trades.append(
            {
                "trade_id": row["trade_id"],
                "symbol": row["symbol"] or "WIN$N",
                "direction": row["direction"] or "BUY",
                "entry_price": entry,
                "entry_time": row["entry_time"],
                "quantity": float(row["quantity"] or 1),
                "initial_sl": float(row["initial_sl"] or 0),
                "initial_tp": float(row["initial_tp"] or 0),
                "precos": precos,
                "resultado_final_pct": float(row["resultado_pct"] or 0),
            }
        )

    logger.info("Trades carregados do SQLite: %d", len(trades))
    return trades


def _contar_pregoes(trades: list) -> int:
    """Estima número de pregões distintos nas entradas."""
    datas = set()
    for t in trades:
        et = t.get("entry_time")
        if et:
            data_str = str(et)[:10]
            datas.add(data_str)
    return len(datas)


# ============================================================
# ESCRITA DE SAÍDA
# ============================================================


def _gravar_saida(relatorio_dict: dict, relatorio_md: str, data_str: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = OUTPUT_DIR / f"baseline_vs_calibrado_{data_str}.json"
    md_path = OUTPUT_DIR / f"baseline_vs_calibrado_{data_str}.md"

    json_path.write_text(
        json.dumps(relatorio_dict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    md_path.write_text(relatorio_md, encoding="utf-8")

    logger.info("Relatório JSON gravado em: %s", json_path)
    logger.info("Relatório Markdown gravado em: %s", md_path)


# ============================================================
# ENTRYPOINT
# ============================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Calibra perfis do ProfitProtectionEngine comparando baseline "
            "vs candidatos sobre trades históricos."
        )
    )
    parser.add_argument(
        "--db",
        default=str(DB_PADRAO),
        help=f"Caminho do banco SQLite (padrão: {DB_PADRAO})",
    )
    parser.add_argument(
        "--config",
        default=str(CONFIG_PADRAO),
        help=f"Caminho do YAML de config (padrão: {CONFIG_PADRAO})",
    )
    parser.add_argument(
        "--perfis",
        nargs="*",
        default=None,
        help="Perfis candidatos a comparar (ex: conservador agressivo). "
        "Se omitido, compara todos os perfis do YAML.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Executa sem gravar arquivos de saída.",
    )
    args = parser.parse_args()

    # 1. Carregar config
    loader = ConfigLoader.get_instance(yaml_path=Path(args.config))
    cfg = loader._get_config()  # Acesso direto para obter o objeto de config
    logger.info(
        "Config carregado | perfil_ativo=%s | shadow_mode=%s | versao=%s",
        cfg.profile_ativo,
        cfg.shadow_mode,
        cfg.version,
    )

    # 2. Carregar trades
    trades = _carregar_trades_sqlite(Path(args.db))
    n_pregoes = _contar_pregoes(trades)
    logger.info("Pregões estimados: %d", n_pregoes)

    if not trades:
        logger.error("Nenhum trade fechado encontrado. Abortando calibração.")
        sys.exit(2)

    # 3. Calibrar
    relatorio = calibrar_perfis(
        trades_replay=trades,
        cfg=cfg,
        perfis_candidatos=args.perfis,
        n_pregoes=n_pregoes,
    )

    # 4. Exibir resumo
    print("\n" + relatorio.to_markdown())
    print(
        f"\n✔ Evidência suficiente: {'SIM' if relatorio.evidencia_suficiente else 'NÃO'}"
    )
    print(f"✔ Perfil recomendado: {relatorio.perfil_recomendado}")
    print(f"✔ Motivo: {relatorio.motivo_recomendacao}\n")

    # 5. Gravar saída
    if not args.dry_run:
        data_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        _gravar_saida(relatorio.to_dict(), relatorio.to_markdown(), data_str)
    else:
        logger.info("--dry-run ativo: saída não gravada.")


if __name__ == "__main__":
    main()
