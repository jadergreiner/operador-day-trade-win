"""
BLID-029: Script CLI para fechamento diario por agente RL.

Executa o FechamentoDiarioAgenteService para cada agente registrado
em AGENT_MAGIC_NUMBERS (rl_5000 e rl_direto) e gera relatorios Markdown
individuais em outputs/diarios/.

Uso:
    python scripts/fechar_diario_por_agente.py
    python scripts/fechar_diario_por_agente.py --data 2026-04-30
    python scripts/fechar_diario_por_agente.py --data 2026-04-30 --db-path data/db/trading.db

Executor: INICIAR_DIARIOS.bat
ADR: ADR-012 (magic numbers), ADR-001 (SQLite direto)
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

# Garante que o projeto root esta no PYTHONPATH ao executar diretamente
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import AGENT_MAGIC_NUMBERS
from src.application.services.fechamento_diario_agente_service import (
    FechamentoDiarioAgenteService,
)

# ---------------------------------------------------------------------------
# Configuracao de logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("fechar_diario_por_agente")

# ---------------------------------------------------------------------------
# Agentes suportados pelo fechamento diario
# ---------------------------------------------------------------------------

_AGENTES_DIARIO = ("rl_5000", "rl_direto")


def _parse_args() -> argparse.Namespace:
    """Parsear argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description="Gera relatorio de fechamento diario por agente RL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--data",
        default=str(date.today()),
        metavar="YYYY-MM-DD",
        help="Data da sessao a fechar (padrao: hoje)",
    )
    parser.add_argument(
        "--db-path",
        default="data/db/trading.db",
        metavar="PATH",
        help="Caminho para o banco SQLite trading.db (padrao: data/db/trading.db)",
    )
    parser.add_argument(
        "--outputs-dir",
        default="outputs/diarios",
        metavar="DIR",
        help="Diretorio de saida dos relatorios Markdown (padrao: outputs/diarios/)",
    )
    return parser.parse_args()


def main() -> int:
    """Executar fechamento diario para todos os agentes suportados.

    Returns:
        0 em caso de sucesso total
        1 em caso de qualquer erro
    """
    args = _parse_args()

    data = args.data
    db_path = Path(args.db_path)
    outputs_dir = Path(args.outputs_dir)

    logger.info("Iniciando fechamento diario — data=%s db=%s", data, db_path)

    svc = FechamentoDiarioAgenteService()
    erros: list[str] = []

    for agent_name in _AGENTES_DIARIO:
        magic = AGENT_MAGIC_NUMBERS[agent_name]
        logger.info("Processando agente=%s magic=%d", agent_name, magic)

        try:
            relatorio = svc.gerar_relatorio(agent_name, magic, data, db_path)
            md_path = svc.gerar_markdown(relatorio, outputs_dir)

            logger.info(
                "Agente=%s | status=%s | trades=%d | pnl=%.2f | win_rate=%.1f%% | arquivo=%s",
                agent_name,
                relatorio.status,
                relatorio.total_trades,
                relatorio.pnl_total_reais,
                relatorio.win_rate * 100,
                md_path,
            )

        except FileNotFoundError as exc:
            logger.error("Banco nao encontrado para agente=%s: %s", agent_name, exc)
            erros.append(f"{agent_name}: {exc}")

        except ValueError as exc:
            logger.error("Parametro invalido para agente=%s: %s", agent_name, exc)
            erros.append(f"{agent_name}: {exc}")

        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro inesperado para agente=%s: %s", agent_name, exc)
            erros.append(f"{agent_name}: {exc}")

    if erros:
        logger.error("Fechamento diario concluido com %d erro(s):", len(erros))
        for erro in erros:
            logger.error("  - %s", erro)
        return 1

    logger.info("Fechamento diario concluido com sucesso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
