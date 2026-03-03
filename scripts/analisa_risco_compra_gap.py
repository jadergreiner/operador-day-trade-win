"""
Análise de Risco: Força Compradora para Fechar o GAP
Avalia se há risco de reversão (compra forte) para fechar o GAP de -3.650
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime


def analisar_risco_fechamento_gap():
    """Analisa o risco de fechamento do gap por força compradora."""

    if not mt5.initialize():
        print("❌ Erro ao conectar ao MT5\n")
        return

    simbolo = "WINJ26"

    if not mt5.symbol_select(simbolo):
        print(f"❌ Símbolo {simbolo} não encontrado\n")
        return

    print("\n" + "="*80)
    print("⚠️  ANÁLISE DE RISCO: FORÇA COMPRADORA para Fechar o GAP")
    print("="*80 + "\n")

    # Obter dados intradiary (5min) para análise detalhada
    print("[1/4] Coletando candles 5min de hoje...\n")

    barras_5min = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_M5, 0, 288)  # 6 horas de pregão

    if barras_5min is None or len(barras_5min) == 0:
        print("❌ Erro ao obter dados 5min\n")
        mt5.shutdown()
        return

    df_5min = pd.DataFrame(barras_5min)
    df_5min['time'] = pd.to_datetime(df_5min['time'], unit='s')
    df_5min.set_index('time', inplace=True)

    # Dados diários para referência
    barras_d1 = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_D1, 0, 5)
    df_d1 = pd.DataFrame(barras_d1)
    df_d1['time'] = pd.to_datetime(df_d1['time'], unit='s')
    df_d1.set_index('time', inplace=True)

    # Níveis críticos
    fechamento_anterior = df_d1.iloc[-2]['close']  # 192.400
    abertura_hoje = df_d1.iloc[-1]['open']          # 188.750
    gap = abertura_hoje - fechamento_anterior       # -3.650

    print(f"Níveis críticos de hoje:")
    print(f"  Fechamento anterior: {fechamento_anterior:,.2f}")
    print(f"  Abertura de hoje:    {abertura_hoje:,.2f}")
    print(f"  GAP:                 {gap:+,.2f} ({(gap/fechamento_anterior)*100:+.2f}%)\n")

    # Análise intraday
    print("[2/4] Analisando movimento intraday...\n")

    # Preço mínimo e máximo do dia até agora
    preco_minimo_hoje = df_5min['low'].min()
    preco_maximo_hoje = df_5min['high'].max()
    preco_atual = df_5min.iloc[-1]['close']

    print(f"Movimento de hoje:")
    print(f"  Abertura:            {abertura_hoje:,.2f}")
    print(f"  Mínima do dia:       {preco_minimo_hoje:,.2f}")
    print(f"  Máxima do dia:       {preco_maximo_hoje:,.2f}")
    print(f"  Preço atual:         {preco_atual:,.2f}\n")

    # Calcular força do movimento
    distancia_minima = preco_minimo_hoje - abertura_hoje
    distancia_maxima = preco_maximo_hoje - abertura_hoje
    movimento_atual = preco_atual - abertura_hoje

    print(f"Direção do movimento:")
    print(f"  Queda máxima:        {distancia_minima:+,.2f} pontos ({(distancia_minima/abertura_hoje)*100:+.2f}%)")
    print(f"  Alta máxima:         {distancia_maxima:+,.2f} pontos ({(distancia_maxima/abertura_hoje)*100:+.2f}%)")
    print(f"  Movimento atual:     {movimento_atual:+,.2f} pontos ({(movimento_atual/abertura_hoje)*100:+.2f}%)\n")

    # Análise de candles (volume e força)
    print("[3/4] Analisando força compradora vs vendedora...\n")

    # Últimos 20 candles (últimas 1h40min)
    df_recente = df_5min.tail(20)

    # Body real dos candles (close - open)
    df_recente['body'] = df_recente['close'] - df_recente['open']
    df_recente['body_pct'] = (df_recente['body'] / df_recente['open']) * 100

    # Contadores
    candles_alta = len(df_recente[df_recente['body'] > 0])
    candles_baixa = len(df_recente[df_recente['body'] < 0])
    candles_doji = len(df_recente[df_recente['body'].abs() < 50])

    volume_media = df_recente['tick_volume'].mean()
    volume_ultimo = df_recente.iloc[-1]['tick_volume']

    print(f"Últimos 20 candles (1h40min):")
    print(f"  Candles de alta:     {candles_alta}/20 ({candles_alta*5:.0f}%)")
    print(f"  Candles de baixa:    {candles_baixa}/20 ({candles_baixa*5:.0f}%)")
    print(f"  Dojis (indecisão):   {candles_doji}/20")
    print(f"  Volume médio:        {volume_media:,.0f}")
    print(f"  Volume último:       {volume_ultimo:,.0f}\n")

    # Análise de momentum
    print("[4/4] Avaliando cenários e riscos...\n")

    print("="*80)
    print("CENÁRIO 1: FORÇA COMPRADORA PARA FECHAR O GAP")
    print("="*80 + "\n")

    # Cenário de compra
    alvo_fechamento_gap = fechamento_anterior

    if candles_alta > candles_baixa:
        sinais_compra = "🟢"
        frase_compra = "POSSÍVEL - Compradores estão tentando"
        prob_fechamento_gap = 0.60  # 60% chance
    elif candles_alta == candles_baixa:
        sinais_compra = "🟡"
        frase_compra = "EQUILIBRADO - Mercado indeciso"
        prob_fechamento_gap = 0.45
    else:
        sinais_compra = "🔴"
        frase_compra = "IMPROVÁVEL - Vendedores têm controle"
        prob_fechamento_gap = 0.25

    print(f"{sinais_compra} {frase_compra}")
    print(f"\nPontos para COMPRA (fechar gap):")
    print(f"  • Gap de -3.650 é muito grande (provoca compras técnicas)")
    print(f"  • Suporte nos -1.650 já pode atrair compradores")
    print(f"  • Se RSI < 30, possível bounce técnico automático")
    print(f"  • Compradores podem usar: Stop em 189.500 (mínima ontem)")

    print(f"\nAlvo se fechar gap:")
    print(f"  • Target 1: {alvo_fechamento_gap:,.2f} (fechar 100% do gap)")
    print(f"  • Movimento necessário: +{alvo_fechamento_gap - preco_atual:,.2f} pontos")
    print(f"  • Percentual: +{((alvo_fechamento_gap - preco_atual)/preco_atual)*100:.2f}%")

    print(f"\nProbabilidade de sucesso:")
    print(f"  • Fechar gap hoje: {prob_fechamento_gap*100:.0f}%")
    print(f"  • Atingir alvo: {prob_fechamento_gap*100*.8:.0f}% (80% dos que tentam)")

    print()
    print("="*80)
    print("CENÁRIO 2: CONTINUAÇÃO DA QUEDA (validar venda)")
    print("="*80 + "\n")

    # Cenário de venda
    alvo_queda = preco_minimo_hoje - (abs(gap) * 0.5)  # Mais 50% do gap como queda adicional

    if candles_baixa > candles_alta:
        sinais_venda = "🟢"
        frase_venda = "PROVÁVEL - Vendedores mantêm controle"
        prob_queda = 0.75
    elif candles_baixa == candles_alta:
        sinais_venda = "🟡"
        frase_venda = "EQUILIBRADO"
        prob_queda = 0.45
    else:
        sinais_venda = "🔴"
        frase_venda = "IMPROVÁVEL - Falta pressão vendedora"
        prob_queda = 0.30

    print(f"{sinais_venda} {frase_venda}")
    print(f"\nPontos para VENDA (continuar queda):")
    print(f"  • GAP confirmado durante o dia (não rejeitado)")
    print(f"  • Movimento intraday ainda para baixo")
    print(f"  • Volume de vendas mantido")
    print(f"  • Próximas metas: {preco_minimo_hoje:,.2f} (baixa do dia)")

    print(f"\nAlvo se continuar queda:")
    print(f"  • Target 1: {preco_minimo_hoje:,.2f} (mínima do dia)")
    print(f"  • Target 2: {alvo_queda:,.2f} (extensão da queda)")
    print(f"  • Movimento necessário: {preco_minimo_hoje - preco_atual:+,.2f} pontos")

    print(f"\nProbabilidade de sucesso:")
    print(f"  • Atingir mínima: {prob_queda*100:.0f}%")
    print(f"  • Vai mais abaixo: {prob_queda*100*.6:.0f}% (60% dos que continuam)")

    # Análise crítica
    print()
    print("="*80)
    print("⚠️  ANÁLISE CRÍTICA - Qual é o risco REAL?")
    print("="*80 + "\n")

    risco_fechamento = prob_fechamento_gap
    risco_queda = prob_queda

    diferenca = risco_queda - risco_fechamento

    print(f"Probabilidade de VENDA (queda): {risco_queda*100:.0f}%")
    print(f"Probabilidade de COMPRA (gap):  {risco_fechamento*100:.0f}%")
    print(f"Diferença:                      {diferenca*100:+.0f}pp\n")

    if diferenca > 0.20:
        print("✅ VENDA É A OPÇÃO MAIS PROVÁVEL")
        print(f"   Risco de gap fechar: BAIXO ({risco_fechamento*100:.0f}%)")
        print(f"   Recomendação: Manter venda com stop em {alvo_fechamento_gap:,.2f}\n")

        recomendacao_final = "VENDA COM CONFIANÇA"
        ajuste_prob = -5  # -5pp de penalidade por risco potencial

    elif diferenca > 0.05:
        print("🟡 VENDA É FAVORÁVEL MAS COM RISCO")
        print(f"   Risco de gap fechar: MODERADO ({risco_fechamento*100:.0f}%)")
        print(f"   Recomendação: Venda com stop ACIMA do gap\n")

        recomendacao_final = "VENDA COM STOP ACIMA DO GAP"
        ajuste_prob = -10  # -10pp de penalidade

    else:
        print("❌ RISCO EQUILIBRADO - Considerar aguardar")
        print(f"   Risco de gap fechar: ALTO ({risco_fechamento*100:.0f}%)")
        print(f"   Recomendação: Aguardar mais clareza\n")

        recomendacao_final = "AGUARDAR - Risco Alto"
        ajuste_prob = -20  # -20pp de penalidade

    # Recalcular probabilidades
    print()
    print("="*80)
    print("📊 AJUSTE NA PROBABILIDADE DE VENDA")
    print("="*80 + "\n")

    prob_venda_original = 0.773  # 77.3% da análise anterior
    prob_venda_ajustada = prob_venda_original + (ajuste_prob / 100)
    prob_venda_ajustada = max(0.30, min(0.90, prob_venda_ajustada))

    print(f"Prob. de VENDA (com GAP precificado):  {prob_venda_original*100:.1f}%")
    print(f"Ajuste por risco de fechamento gap:   {ajuste_prob:+d}pp")
    print(f"Prob. de VENDA (com risco):           {prob_venda_ajustada*100:.1f}%")
    print()

    print("="*80)
    print("🎯 RECOMENDAÇÃO FINAL EXECUTIVA")
    print("="*80 + "\n")

    print(f"Setup: {recomendacao_final}\n")

    if prob_venda_ajustada > 0.60:
        print(f"✅ VENDA AINDA RECOMENDADA ({prob_venda_ajustada*100:.1f}%)")
        print(f"\n   Como proteger de uma reversão (compra do gap):")
        print(f"   • STOP LOSS: {alvo_fechamento_gap:,.2f} (acima do gap)")
        print(f"   • Este stop confirmaria reversão (não false spike)")
        print(f"   • Risco máximo: {alvo_fechamento_gap - preco_atual:,.2f} pontos")
        print(f"   • Retorno objetivo: {preco_minimo_hoje - preco_atual:+,.2f} pontos")
        print(f"   • Risk/Reward: 1:{(preco_minimo_hoje - preco_atual)/(alvo_fechamento_gap - preco_atual):.2f}")

    else:
        print(f"⚠️  VENDA A CONSIDERAR COM CUIDADO ({prob_venda_ajustada*100:.1f}%)")
        print(f"\n   Alternativas:")
        print(f"   1. Aguardar mais clareza técnica")
        print(f"   2. Se vender: stop MUITO apertado (acima do gap)")
        print(f"   3. Considerar compra se RSI bounçar + volume")

    mt5.shutdown()


if __name__ == "__main__":
    analisar_risco_fechamento_gap()
    print("\n" + "="*80)
    print("✅ Análise de risco concluída")
    print("="*80 + "\n")
