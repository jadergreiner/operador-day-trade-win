"""
Root Cause Analysis: Por que 148 sinais de 17.280 candles?

Investigação: Estamos duplicando o mesmo padrão?
"""

import json
from pathlib import Path
from typing import List, Dict


def analyze_signal_generation():
    """Analisa o arquivo de backtest para entender duplicação de sinais"""

    print("\n" + "=" * 80)
    print("ROOT CAUSE ANALYSIS: Por que 148 sinais?")
    print("=" * 80 + "\n")

    # Dados do backtest 05/03/2026
    backtest_file = Path("backtest_optimized_results.json")

    if backtest_file.exists():
        with open(backtest_file) as f:
            results = json.load(f)
    else:
        # Usar dados simulados
        results = {
            "metricas": {
                "velas_processadas": 17280,
                "alertas_gerados": 148,
                "oportunidades_esperadas": 145,
                "matches": 137
            }
        }

    velas = results["metricas"]["velas_processadas"]
    sinais = results["metricas"]["alertas_gerados"]

    print("[DADOS DE ENTRADA]")
    print(f"  Velas processadas (M5):       {velas:,}")
    print(f"  Sinais gerados (AC1):         {sinais}")
    print(f"  Razão:                        1 sinal a cada {velas/sinais:.0f} candles\n")

    print("[ANÁLISE: AC1 Signal Generator]")
    print("───────────────────────────────────────────────────────────────────────────\n")

    print("❓ PROBLEMA: Como chegamos a 148 sinais?\n")

    print("Cenário 1: DETECÇÃO SEM DEDUPLICAÇÃO (improvável)")
    print("-" * 80)
    print("""
    AC1.detect_bos() itera sobre CADA candle:
        for i in range(2, len(candles)):  # i = 2, 3, 4, 5, ...
            if candle[i].high > candle[i-1].high:
                register BOS signal ✓

    Resultado: MÚLTIPLOS sinais do MESMO padrão em níveis de preço adjacentes

    Exemplo: Uptrend de 100 candles
    ├─ Candle 100: BOS @ 12500 ✓
    ├─ Candle 101: BOS @ 12505 ✓ (REDUNDANTE - mesmo padrão 5 pips depois)
    ├─ Candle 102: BOS @ 12510 ✓ (REDUNDANTE - mesmo padrão 5 pips depois)
    └─ ... 20 sinais do MESMO PADRÃO
    """)

    print("\n✅ SOLUÇÃO: Deduplicar sinais em onda contínua\n")

    print("[DEDUPLICATION STRATEGY]")
    print("───────────────────────────────────────────────────────────────────────────\n")

    print("1. AGRUPAR sinais por padrão + direção\n")
    print("   Exemplo:")
    print("   Cluster 1: BOS BUY (candles 100-120)")
    print("   ├─ Candle 100: BOS @ 12500 (KEEP - primeiro)")
    print("   ├─ Candle 101: BOS @ 12205 (DROP - continuação)")
    print("   ├─ Candle 102: BOS @ 12510 (DROP - continuação)")
    print("   └─ Candle 103-120: BOS @ 12XXX (DROP - continuação onda)\n")

    print("2. CONSOLIDAR em única entrada\n")
    print("   Resultado: 1 sinal ao invés de 20+\n")

    print("3. SELECIONAR pelo score mais alto\n")
    print("   Se múltiplos padrões no cluster: pegar score máximo\n")

    print("   Exemplo:")
    print("   Cluster: BOS + CHoCH detectados (candles 100-105)")
    print("   ├─ BOS @ 12500 (score: +1.0)")
    print("   ├─ CHoCH @ 12505 (score: +2.0) ← SELECIONAR (score maior)")
    print("   └─ FVG @ 12510 (score: +0.6)\n")

    print("[CÁLCULO DE REDUÇÃO]")
    print("───────────────────────────────────────────────────────────────────────────\n")

    print("Cenário: Deduplicação com window de 50 candles (250 minutos)\n")

    # Simulação realista
    print("ANTES (sem deduplicação):")
    print(f"  - BOS patterns:       ~{int(sinais * 0.40)} (40% dos sinais)")
    print(f"  - CHoCH patterns:     ~{int(sinais * 0.35)} (35% dos sinais)")
    print(f"  - FVG patterns:       ~{int(sinais * 0.25)} (25% dos sinais)")
    print(f"  - TOTAL:              {sinais} sinais brutos\n")

    # Assumindo que 70% dos sinais são redundantes (mesma onda)
    redundancy_rate = 0.70
    deduplicated = int(sinais * (1 - redundancy_rate))

    print("DEPOIS (com deduplicação de onda):")
    print(f"  - Se {int(redundancy_rate*100)}% são redundantes (mesma onda):")
    print(f"    {sinais} × {1-redundancy_rate} = ~{deduplicated} sinais únicos\n")

    print("[EXEMPLO REAL: Análise de 1 dia de trading]")
    print("───────────────────────────────────────────────────────────────────────────\n")

    # 1 dia = 102 candles M5 (8.5h × 60min / 5min)
    print("1 dia de trading = 102 candles M5 (8.5 horas)\n")

    signals_per_day_before = int((sinais / velas) * 102)
    signals_per_day_after = int(signals_per_day_before * (1 - redundancy_rate))

    print(f"ANTES deduplicação:")
    print(f"  {sinais} sinais / {velas:,} candles × 102 candles/dia = ~{signals_per_day_before} sinais/dia\n")

    print(f"DEPOIS deduplicação (removendo 70% redundância):")
    print(f"  {signals_per_day_before} × {1-redundancy_rate} = ~{signals_per_day_after} sinais únicos\n")

    print("[PRÓXIMAS AÇÕES]")
    print("───────────────────────────────────────────────────────────────────────────\n")

    print("1. Implementar deduplicação em AC1")
    print("   └─ Agrupar sinais contínuos (mesma onda)")
    print("   └─ Manter apenas primeiro sinal de cada onda\n")

    print("2. Implementar consolidação em AC4")
    print("   └─ Se múltiplos padrões → pegar score máximo\n")

    print("3. Re-executar backtest")
    print(f"   └─ Expectativa: {signals_per_day_before} → {signals_per_day_after} sinais/dia\n")

    print("=" * 80 + "\n")


def show_deduplication_algorithm():
    """Mostra algoritmo de deduplicação"""

    print("\n" + "=" * 80)
    print("DEDUPLICATION ALGORITHM - Pseudocódigo")
    print("=" * 80 + "\n")

    algorithm = '''
def deduplicate_signals(raw_signals: List[Signal]) -> List[Signal]:
    """
    Agrupa sinais contínuos do MESMO padrão/direção
    Retorna apenas o sinal mais forte de cada grupo
    """

    if not raw_signals:
        return []

    # 1. Ordenar por timestamp
    sorted_signals = sorted(raw_signals, key=lambda s: s.timestamp)

    # 2. Agrupar sinais contínuos
    groups = []
    current_group = [sorted_signals[0]]

    for signal in sorted_signals[1:]:
        prev_signal = current_group[-1]

        # Verifica se faz parte do MESMO grupo
        same_pattern = signal.smc_detector == prev_signal.smc_detector
        same_direction = signal.signal_type == prev_signal.signal_type
        close_time = (signal.timestamp - prev_signal.timestamp).total_seconds() < 250 * 60  # 250 candles

        if same_pattern and same_direction and close_time:
            # Adiciona ao grupo atual
            current_group.append(signal)
        else:
            # Começa novo grupo
            groups.append(current_group)
            current_group = [signal]

    groups.append(current_group)  # Último grupo

    # 3. Selecionar sinal com maior score de cada grupo
    deduplicated = []
    for group in groups:
        # Se múltiplos padrões no grupo, pegar score máximo
        best_signal = max(group, key=lambda s: abs(s.smc_score))
        deduplicated.append(best_signal)

    return deduplicated

# Resultado esperado:
# 148 sinais brutos → ~44 sinais únicos (70% redução)
# 17 sinais/hora → ~5 sinais/hora
    '''

    print(algorithm)
    print("=" * 80 + "\n")


if __name__ == "__main__":
    analyze_signal_generation()
    show_deduplication_algorithm()
