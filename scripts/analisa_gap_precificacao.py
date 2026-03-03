"""
Análise do GAP não precificado - Impacto na Venda
Verifica se o GAP de abertura afeta a estratégia de venda
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta


def analisar_gap():
    """Analisa o GAP de abertura do dia."""

    if not mt5.initialize():
        print("❌ Erro ao conectar ao MT5\n")
        return

    simbolo = "WINJ26"

    if not mt5.symbol_select(simbolo):
        print(f"❌ Símbolo {simbolo} não encontrado\n")
        return

    print("\n" + "="*80)
    print("📊 ANÁLISE DO GAP - Impacto na Estratégia")
    print("="*80 + "\n")

    # Obter últimos 5 dias de dados
    print("[1/3] Coletando histórico de 5 dias...\n")

    barras = mt5.copy_rates_from_pos(simbolo, mt5.TIMEFRAME_D1, 0, 5)

    if barras is None or len(barras) == 0:
        print("❌ Erro ao obter dados\n")
        mt5.shutdown()
        return

    df = pd.DataFrame(barras)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)

    print("HISTÓRICO DOS ÚLTIMOS 5 DIAS:\n")

    for i in range(len(df)):
        dia = df.index[i]
        linha = df.iloc[i]

        print(f"{i+1}. {dia.strftime('%d/%m/%Y (%A)')}")
        print(f"   Abertura: {linha['open']:,.2f}")
        print(f"   Máxima:   {linha['high']:,.2f}")
        print(f"   Mínima:   {linha['low']:,.2f}")
        print(f"   Fechamento: {linha['close']:,.2f}")

        if i > 0:
            ref_anterior = df.iloc[i-1]['close']
            gap = linha['open'] - ref_anterior
            gap_pct = (gap / ref_anterior) * 100

            if abs(gap) > 0.01:
                tipo_gap = "⬆️  GAP de alta" if gap > 0 else "⬇️  GAP de baixa"
                print(f"   {tipo_gap}: {gap:,.2f} pontos ({gap_pct:+.2f}%)")
            else:
                print(f"   ➡️  Sem GAP significativo")

        print()

    # Análise detalhada do GAP de hoje
    print("="*80)
    print("🎯 ANÁLISE DO GAP DE HOJE (03/03/2026)")
    print("="*80 + "\n")

    dia_atual = df.iloc[-1]
    dia_anterior = df.iloc[-2]

    preco_fechamento_anterior = dia_anterior['close']
    preco_abertura_hoje = dia_atual['open']
    preco_atual = dia_atual['close']

    gap = preco_abertura_hoje - preco_fechamento_anterior
    gap_pct = (gap / preco_fechamento_anterior) * 100

    print(f"Fechamento anterior (02/03): {preco_fechamento_anterior:,.2f}")
    print(f"Abertura hoje (03/03):        {preco_abertura_hoje:,.2f}")
    print(f"Tipo GAP:                     {gap:+,.2f} pontos ({gap_pct:+.2f}%)")
    print()

    if gap > 0:
        print("📈 GAP DE ALTA (mercado abriu mais caro)")
        print()
        print("   Impacto na análise:")
        print(f"   • Novas compras já começam acima do suporte")
        print(f"   • Necessário testar o fechamento anterior para confirmar tendência")
        print(f"   • Nível crítico de stop para compras: {preco_fechamento_anterior:,.2f}")
        print()
    elif gap < 0:
        print("📉 GAP DE BAIXA (mercado abriu mais barato)")
        print()
        print("   Impacto na análise:")
        print(f"   • Vendidos começaram stronger (forte pressão inicial)")
        print(f"   • Nível crítico de suporte: {preco_fechamento_anterior:,.2f}")
        print(f"   • Resistência: {preco_abertura_hoje:,.2f}")
        print()
    else:
        print("➡️  SEM GAP SIGNIFICATIVO")
        print()

    # GAP precificado ou não?
    print()
    print("="*80)
    print("❓ O GAP FOI PRECIFICADO? (Análise Crítica)")
    print("="*80 + "\n")

    movimentacao_intraday = preco_atual - preco_abertura_hoje
    movimentacao_pct = (movimentacao_intraday / preco_abertura_hoje) * 100

    print(f"Abertura (Gap):       {preco_abertura_hoje:,.2f}")
    print(f"Fechamento:           {preco_atual:,.2f}")
    print(f"Movimento intraday:   {movimentacao_intraday:+,.2f} ({movimentacao_pct:+.2f}%)")
    print()

    if gap > 0:  # GAP de alta
        if preco_atual < preco_fechamento_anterior:
            print("🔴 GAP NÃO PRECIFICADO (REJEITADO)")
            print()
            print("   O mercado abriu em gap de alta, MAS")
            print("   Fechou ABAIXO do nível anterior.")
            print()
            print("   Interpretação técnica:")
            print("   • Venda realizada FORTE durante o dia")
            print("   • GAP de alta foi uma armadilha para comprados")
            print("   • Sinais de fraqueza confirmados no fechamento")
            print(f"   • Próximo suporte: {preco_fechamento_anterior:,.2f} (nível anterior)")

            venda_recomendacao = "🟢 VENDA AINDA MAIS RECOMENDADA"
            boost_venda = 10  # +10% de confiança na venda

        else:
            print("🟡 GAP PARCIALMENTE PRECIFICADO")
            print()
            print("   Mercado abriu em gap de alta e mantém ganho.")
            print("   Mas não consegue manter força.")
            print()
            print("   Interpretação técnica:")
            print("   • Comprados tentam segurar ganho do gap")
            print("   • Vendidos conseguem bloquear avanço")
            print("   • Possível consolidação ou retrocesso")

            venda_recomendacao = "🟡 VENDA COM CAUTELA"
            boost_venda = 0  # Sem boost adicional

    else:  # GAP de baixa
        if preco_atual > preco_abertura_hoje:
            print("🟡 GAP PARCIALMENTE RECUPERADO")
            print()
            print("   Mercado abriu em gap de baixa, MAS")
            print("   Conseguiu recuperar durante o dia.")
            print()
            print("   Interpretação técnica:")
            print("   • Vendidos iniciarem forte, MAS")
            print("   • Compradores entraram e reverteram movimento")
            print("   • Possibilidade de bounce real")

            venda_recomendacao = "🟠 VENDA MENOS RECOMENDADA"
            boost_venda = -10  # -10% de confiança

        else:
            print("🔴 GAP TOTALMENTE PRECIFICADO (CONFIRMADO)")
            print()
            print("   Mercado abriu em gap de baixa e mantém pressão.")
            print("   Fechou ainda mais barato.")
            print()
            print("   Interpretação técnica:")
            print("   • Tendência de baixa MUITO FORTE confirmada")
            print("   • Vendedores mantêm controle")
            print("   • Próximas metas de queda estão abertas")

            venda_recomendacao = "🟢 VENDA CONFIRMADA E RECOMENDADA"
            boost_venda = 15  # +15% de confiança

    print()
    print(f"Recomendação: {venda_recomendacao}")
    print(f"Boost de confiança: {boost_venda:+d}pp")

    # Impacto nas probabilidades
    print()
    print("="*80)
    print("📊 IMPACTO NAS PROBABILIDADES DE VENDA")
    print("="*80 + "\n")

    prob_venda_anterior = 0.623  # 62.3% da análise anterior
    prob_venda_com_gap = prob_venda_anterior + (boost_venda / 100)
    prob_venda_com_gap = max(0.20, min(0.90, prob_venda_com_gap))

    print(f"Probabilidade de VENDA (técnica + macro):  {prob_venda_anterior*100:.1f}%")
    print(f"Ajuste GAP:                                {boost_venda:+d}pp")
    print(f"Probabilidade de VENDA (com GAP):          {prob_venda_com_gap*100:.1f}%")
    print()

    print(f"Delta:                                     {(prob_venda_com_gap - prob_venda_anterior)*100:+.1f}pp")

    if prob_venda_com_gap > 0.65:
        print()
        print("✅ VENDA ATIVADA COM ALTA CONFIANÇA (>65%)")
        print(f"   Recomendação: Abrir SHORT com targets agressivos")
    elif prob_venda_com_gap > 0.55:
        print()
        print("🟡 VENDA EM ZONA DE PROBABILIDADE MÉDIA (55-65%)")
        print(f"   Recomendação: Entrada técnica, com stop rigoroso")
    else:
        print()
        print("❌ VENDA NÃO RECOMENDADA (<55%)")

    # Setup de venda revisado
    print()
    print("="*80)
    print("🎯 SETUP DE VENDA COM GAP CONSIDERADO")
    print("="*80 + "\n")

    entrada = preco_atual
    target_agressivo = preco_abertura_hoje - (gap * 2)  # Rejeita gap + recida
    target_conservador = dia_anterior['low']  # Fundo do dia anterior
    stop_loss = preco_abertura_hoje + (abs(gap) * 1.5)  # Acima do gap como confirmação

    risco = entrada - stop_loss
    retorno_agressivo = entrada - target_agressivo
    retorno_conservador = entrada - target_conservador

    rr_agressivo = retorno_agressivo / abs(risco) if risco != 0 else 0
    rr_conservador = retorno_conservador / abs(risco) if risco != 0 else 0

    print(f"Entrada:              {entrada:,.2f}")
    print(f"Stop Loss:            {stop_loss:,.2f} (risco: {risco:,.2f} pontos)")
    print()
    print(f"Target Agressivo:     {target_agressivo:,.2f} (+{retorno_agressivo:,.2f}pts, RR 1:{rr_agressivo:.2f})")
    print(f"Target Conservador:   {target_conservador:,.2f} (+{retorno_conservador:,.2f}pts, RR 1:{rr_conservador:.2f})")
    print()

    print("Decisão:")
    if abs(gap) > 500:  # Gap > 500 pontos é significativo
        print(f"  ⚠️  GAP muito significativo ({abs(gap):,.0f} pontos)")
        print(f"  Este gap PRECISA ser respeitado na estratégia")

    if gap < 0 and preco_atual < dia_anterior['close']:
        print(f"  ✅ GAP de baixa confirmado (não rejeitado)")
        print(f"  Venda é setup de HIGH PROBABILITY")

    mt5.shutdown()


if __name__ == "__main__":
    analisar_gap()
    print("\n" + "="*80)
    print("✅ Análise de GAP concluída")
    print("="*80 + "\n")
