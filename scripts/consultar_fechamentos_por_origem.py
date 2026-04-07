#!/usr/bin/env python3
"""Consulta rápida dos fechamentos por AGENTE, OPERADOR e MERCADO.

Uso:
    python scripts/consultar_fechamentos_por_origem.py --days 7
    python scripts/consultar_fechamentos_por_origem.py --json
    python scripts/consultar_fechamentos_por_origem.py --sql
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from src.application.dashboard_stats_server import StatsQueryService


SQL_REFERENCIA = """
SELECT COALESCE(encerrado_por, 'SISTEMA') AS origem,
       COALESCE(motivo_encerramento, 'NAO_INFORMADO') AS motivo,
       COUNT(*) AS quantidade,
       ROUND(COALESCE(SUM(pl_final), 0), 2) AS pnl_total
FROM posicoes_encerradas
WHERE datetime(encerrado_em) >= datetime('now', '-7 days')
GROUP BY COALESCE(encerrado_por, 'SISTEMA'),
         COALESCE(motivo_encerramento, 'NAO_INFORMADO')
ORDER BY quantidade DESC, origem ASC, motivo ASC;
""".strip()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lista fechamentos do Micro Tendência por origem operacional.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Janela em dias para a consulta (padrão: 7).",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Caminho opcional do SQLite a consultar.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Exibe a saída em JSON estruturado.",
    )
    parser.add_argument(
        "--sql",
        action="store_true",
        help="Exibe a query SQL de referência e encerra.",
    )
    return parser.parse_args()


def _print_tabela(titulo: str, linhas: list[tuple[str, str, str, str]]) -> None:
    print(f"\n{titulo}")
    print("-" * len(titulo))
    if not linhas:
        print("(sem dados)")
        return

    larguras = [max(len(str(valor)) for valor in coluna) for coluna in zip(*linhas)]
    for linha in linhas:
        print(
            " | ".join(
                str(valor).ljust(larguras[idx]) for idx, valor in enumerate(linha)
            )
        )


def main() -> int:
    args = _parse_args()

    if args.sql:
        print(SQL_REFERENCIA)
        return 0

    servico = StatsQueryService(db_path=args.db_path)
    resumo = servico.obter_resumo_fechamentos_por_origem(dias=args.days)

    if args.json:
        print(json.dumps(resumo, ensure_ascii=False, indent=2))
        return 0

    print("=" * 72)
    print("FECHAMENTOS POR ORIGEM OPERACIONAL")
    print("=" * 72)
    print(f"Banco: {resumo.get('db_path')}")
    print(f"Período: últimos {resumo.get('periodo_dias')} dia(s)")
    print(f"Total de fechamentos: {resumo.get('total_fechamentos', 0)}")

    linhas_origem = [("ORIGEM", "QTD", "%", "PNL TOTAL")]
    for origem, dados in (resumo.get("por_origem") or {}).items():
        linhas_origem.append(
            (
                origem,
                str(dados.get("quantidade", 0)),
                f"{dados.get('percentual', 0.0):.2f}%",
                f"{dados.get('pnl_total', 0.0):+.2f}",
            )
        )
    _print_tabela("Resumo por origem", linhas_origem)

    linhas_motivo = [("MOTIVO", "QTD", "PNL TOTAL", "-")]
    for motivo, dados in (resumo.get("por_motivo") or {}).items():
        linhas_motivo.append(
            (
                motivo,
                str(dados.get("quantidade", 0)),
                f"{dados.get('pnl_total', 0.0):+.2f}",
                "",
            )
        )
    _print_tabela("Resumo por motivo", linhas_motivo)

    recentes = resumo.get("fechamentos_recentes") or []
    linhas_recentes = [("TRADE", "ORIGEM", "MOTIVO", "PNL")]
    for item in recentes:
        linhas_recentes.append(
            (
                str(item.get("trade_id", "")),
                str(item.get("encerrado_por", "")),
                str(item.get("motivo_encerramento", "")),
                f"{float(item.get('pl_final', 0.0)):+.2f}",
            )
        )
    _print_tabela("Fechamentos recentes", linhas_recentes)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
