#!/usr/bin/env python
"""
Script para análise de bloqueios de execução de trade.

Analisa arquivos CSV/JSON gerados por BlockageLogger e produz:
1. Estatísticas consolidadas
2. Gráficos de distribuição (texto ASCII)
3. Recomendações de ajuste de parâmetros

Uso:
    python scripts/analyze_blockages.py agente_direto_20260316_103045
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from src.application.blockage_logging import BlockageReason


def carregar_bloqueios_json(arquivo: Path) -> Dict:
    """
    Carrega bloqueios de arquivo JSON.

    Args:
        arquivo: Caminho do arquivo JSON

    Returns:
        Dicionário com dados dos bloqueios
    """
    with open(arquivo, "r", encoding="utf-8") as f:
        return json.load(f)


def contar_bloqueios_por_motivo(bloqueios: List[Dict]) -> Dict[str, int]:
    """
    Conta bloqueios por motivo.

    Args:
        bloqueios: Lista de bloqueios

    Returns:
        Dicionário com contagem por motivo
    """
    counts: Dict[str, int] = {}
    for bloqueio in bloqueios:
        motivo = bloqueio["motivo"]
        counts[motivo] = counts.get(motivo, 0) + 1
    return counts


def gerar_grafico_barras(
    dados: Dict[str, int], largura_max: int = 50
) -> str:
    """
    Gera gráfico de barras em ASCII.

    Args:
        dados: Dicionário com {motivo: contagem}
        largura_max: Largura máxima da barra em caracteres

    Returns:
        String com gráfico formatado
    """
    if not dados:
        return "Sem dados para gráfico"

    max_valor = max(dados.values())
    linhas = []

    for motivo, valor in sorted(dados.items(), key=lambda x: x[1],
                                reverse=True):
        percentual = (valor / max_valor) * largura_max
        barra = "█" * int(percentual)
        linhas.append(
            f"{motivo:30} | {barra:<{largura_max}} | {valor}"
        )

    return "\n".join(linhas)


def gerar_recomendacoes(
    bloqueios: List[Dict], stats: Dict[str, int]
) -> List[str]:
    """
    Gera recomendações de ajuste baseadas em padrões.

    Args:
        bloqueios: Lista de bloqueios
        stats: Estatísticas por motivo

    Returns:
        Lista de recomendações em português
    """
    recomendacoes = []
    total = len(bloqueios)

    if total == 0:
        recomendacoes.append(
            "✅ Nenhum bloqueio. Sistema operando normalmente."
        )
        return recomendacoes

    hourly = stats.get("HOURLY_LIMIT_EXCEEDED", 0)
    cooldown = stats.get("COOLDOWN_ACTIVE", 0)
    loss_streak = stats.get("LOSS_STREAK_COOLDOWN", 0)
    outside = stats.get("OUTSIDE_TRADING_HOURS", 0)

    if hourly > total * 0.5:
        recomendacoes.append(
            "⚠️ HOURLY_LIMIT_EXCEEDED é 50% dos bloqueios. "
            "Considere aumentar limite de trades/hora de 3 para 5."
        )

    if cooldown > total * 0.3:
        recomendacoes.append(
            "⚠️ COOLDOWN_ACTIVE é 30% dos bloqueios. "
            "Cooldown de 5 min pode ser reduzido para 3 min."
        )

    if loss_streak > total * 0.2:
        recomendacoes.append(
            "⚠️ LOSS_STREAK_COOLDOWN é 20% dos bloqueios. "
            "2 perdas consecutivas ativam 30 min cooldown - considere 15 min."
        )

    if outside > 0:
        recomendacoes.append(
            f"ℹ️ {outside} bloqueios fora do horário de trading. Normal."
        )

    if total < 5:
        recomendacoes.append(
            "✅ Poucos bloqueios. Parametros estão bem configurados."
        )

    return recomendacoes


def analisar_bloqueios(session_id: str,
                      outputs_dir: Path = Path("outputs")) -> None:
    """
    Analisa bloqueios de uma sessão.

    Args:
        session_id: ID da sessão do agente
        outputs_dir: Diretório onde estão os arquivos
    """
    arquivo_json = outputs_dir / f"agente_bloqueios_{session_id}.json"

    if not arquivo_json.exists():
        print(f"❌ Arquivo não encontrado: {arquivo_json}")
        sys.exit(1)

    dados = carregar_bloqueios_json(arquivo_json)
    bloqueios = dados.get("bloqueios", [])
    stats = contar_bloqueios_por_motivo(bloqueios)

    print("\n" + "=" * 70)
    print(f"ANÁLISE DE BLOQUEIOS - {session_id}")
    print("=" * 70 + "\n")

    # Resumo
    print("📊 RESUMO")
    print("-" * 70)
    print(f"Total de bloqueios: {len(bloqueios)}")
    print(f"Data de criação: {dados.get('timestamp_criacao', 'N/A')}")
    print()

    # Gráfico
    if bloqueios:
        print("📈 DISTRIBUIÇÃO POR MOTIVO")
        print("-" * 70)
        print(gerar_grafico_barras(stats))
        print()

    # Tabela de motivos
    print("📋 CONTAGEM POR MOTIVO")
    print("-" * 70)
    for motivo in BlockageReason:
        valor = motivo.value
        count = stats.get(valor, 0)
        percentual = (count / len(bloqueios) * 100) if bloqueios else 0
        print(f"{valor:30} | {count:4d} ({percentual:5.1f}%)")
    print()

    # Recomendações
    recomendacoes = gerar_recomendacoes(bloqueios, stats)
    print("💡 RECOMENDAÇÕES")
    print("-" * 70)
    for rec in recomendacoes:
        print(rec)
    print()

    print("=" * 70)
    print(f"✅ Análise completa. Dados em {arquivo_json}")
    print("=" * 70 + "\n")


def main() -> None:
    """Função principal do script."""
    if len(sys.argv) < 2:
        print("Uso: python scripts/analyze_blockages.py <session_id>")
        print()
        print("Exemplo:")
        print(
            "  python scripts/analyze_blockages.py agente_direto_20260316"
        )
        sys.exit(1)

    session_id = sys.argv[1]
    analisar_bloqueios(session_id)


if __name__ == "__main__":
    main()
