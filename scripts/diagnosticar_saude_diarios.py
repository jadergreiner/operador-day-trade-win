"""Script CLI de Diagnostico de Saude Pre-Sessao dos Diarios.

BLID-028 / ROADMAP-DIARIOS-08
Executor: INICIAR_DIARIOS.bat

Executa o diagnostico completo dos bancos de dados do pipeline de Diarios
e imprime o resultado no terminal.

Uso:
    python scripts/diagnosticar_saude_diarios.py [--db-path PATH]

Exemplo:
    python scripts/diagnosticar_saude_diarios.py
    python scripts/diagnosticar_saude_diarios.py --db-path data/db/trading_diarios.db

Codigos de saida:
    0 — OK (sem problemas detectados)
    1 — WARNING (problemas nao criticos)
    2 — CRITICAL (banco ausente ou corrompido)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _obter_db_path_padrao() -> Path:
    """Retorna o caminho padrao do banco de dados dos Diarios (ADR-019)."""
    return Path("data") / "db" / "trading_diarios.db"


def main() -> int:
    """Executa diagnostico de saude e retorna codigo de saida.

    Returns:
        0 se OK, 1 se WARNING, 2 se CRITICAL.
    """
    parser = argparse.ArgumentParser(
        description="Diagnostico de saude pre-sessao dos bancos de Diarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=_obter_db_path_padrao(),
        help="Caminho para o banco SQLite (padrao: data/db/trading_diarios.db)",
    )
    args = parser.parse_args()

    from src.application.services.diarios_health_check_service import (
        DiariosHealthCheckService,
    )

    servico = DiariosHealthCheckService()
    relatorio = servico.gerar_relatorio_diagnostico(args.db_path)
    print(relatorio)

    resultado = servico.executar_diagnostico_completo(args.db_path)
    status = resultado["status_geral"]

    if status == "OK":
        return 0
    elif status == "WARNING":
        return 1
    else:
        return 2


if __name__ == "__main__":
    sys.exit(main())
