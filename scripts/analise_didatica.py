"""
Análise Didática do Mercado - Operador Quântico
Por que estamos AGUARDANDO e não OPERANDO
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal
from datetime import datetime
from config import get_config
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.application.services.volume_analysis import VolumeAnalysisService
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


def main():
    """Análise didática completa."""

    print("=" * 80)
    print("ANALISE DIDATICA - POR QUE ESTAMOS AGUARDANDO?")
    print("=" * 80)
    print(f"Horario: {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Conectar
    config = get_config()
    symbol = Symbol(config.trading_symbol)

    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("[ERRO] Falha ao conectar")
        return

    # Obter dados
    print("Conectado! Analisando mercado...")
    print()

    candles = mt5.get_candles(symbol, TimeFrame.M15, count=100)

    if not candles:
        print("[ERRO] Sem dados")
        mt5.disconnect()
        return

    # Calcular métricas básicas
    opening_candle = candles[0]
    current_candle = candles[-1]

    opening_price = opening_candle.open.value
    current_price = current_candle.close.value
    high = max(c.high.value for c in candles)
    low = min(c.low.value for c in candles)

    price_change_pct = ((current_price - opening_price) / opening_price) * 100
    amplitude_pct = ((high - low) / opening_price) * 100

    # Análise de volume
    volume_service = VolumeAnalysisService()
    volume_today, volume_avg_3days, volume_variance_pct = volume_service.calculate_volume_metrics(candles)

    # Decisão do sistema
    operator = QuantumOperatorEngine()
    decision = operator.analyze_and_decide(
        symbol=symbol,
        candles=candles,
        dollar_index=Decimal("104.3"),
        vix=Decimal("16.5"),
        selic=Decimal("10.75"),
        ipca=Decimal("4.5"),
        usd_brl=Decimal("5.85"),
        embi_spread=250,
    )

    # ============================================================================
    # SITUAÇÃO ATUAL DO MERCADO
    # ============================================================================

    print("=" * 80)
    print("SITUACAO ATUAL DO MERCADO")
    print("=" * 80)
    print()

    print(f"Simbolo:     {symbol}")
    print(f"Abertura:    R$ {opening_price:,.2f}")
    print(f"Atual:       R$ {current_price:,.2f}")
    print(f"Maxima:      R$ {high:,.2f}")
    print(f"Minima:      R$ {low:,.2f}")
    print()

    print(f"Variacao:    {price_change_pct:+.2f}%")
    print(f"Amplitude:   {amplitude_pct:.2f}%")

    if volume_variance_pct is not None:
        print(f"Volume:      {volume_variance_pct:+.1f}% vs media 3 dias")
    print()

    # Interpretar movimento
    if price_change_pct < -1.0:
        print("MOVIMENTO: Queda FORTE desde a abertura")
        print("  -> Vendedores dominando o pregao")
        print("  -> Pressao vendedora evidente")
    elif price_change_pct < -0.3:
        print("MOVIMENTO: Queda MODERADA desde a abertura")
        print("  -> Vendedores com ligeira vantagem")
    elif price_change_pct > 1.0:
        print("MOVIMENTO: Alta FORTE desde a abertura")
        print("  -> Compradores dominando o pregao")
    elif price_change_pct > 0.3:
        print("MOVIMENTO: Alta MODERADA desde a abertura")
        print("  -> Compradores com ligeira vantagem")
    else:
        print("MOVIMENTO: Lateral - indecisao")
        print("  -> Equilibrio entre compradores e vendedores")

    print()

    # ============================================================================
    # ANÁLISE DAS 4 DIMENSÕES - O QUE CADA UMA VÊ
    # ============================================================================

    print("=" * 80)
    print("O QUE CADA DIMENSAO ESTA VENDO")
    print("=" * 80)
    print()

    # DIMENSÃO 1: MACRO
    print("1. MACROECONOMIA MUNDIAL")
    print("-" * 80)
    print(f"Status: {decision.macro_bias}")
    print()
    print("O que esta analisando:")
    print("  - Dollar Index (DXY): 104.3 (dolar forte)")
    print("  - VIX (indice do medo): 16.5 (baixo/neutro)")
    print("  - Ambiente global: Risk-On moderado")
    print()

    if decision.macro_bias == "BULLISH":
        print("Interpretacao MACRO:")
        print("  -> Dolar FORTE pressiona ativos emergentes PARA BAIXO")
        print("  -> Mas VIX baixo = mercados calmos, sem panico")
        print("  -> Resultado: Pressao VENDEDORA leve no Brasil")
        print("  TRIGGER: Precisaria VIX > 20 OU DXY > 106 para confirmar bearish forte")
    elif decision.macro_bias == "BEARISH":
        print("Interpretacao MACRO:")
        print("  -> Cenario internacional desfavoravel para emergentes")
        print("  -> Dolar forte + medo alto = fuga de capital")
        print("  -> Resultado: Pressao VENDEDORA forte")
        print("  CONFIRMADO: Ambiente macro favorece VENDA")
    else:
        print("Interpretacao MACRO:")
        print("  -> SEM TENDENCIA CLARA no cenario internacional")
        print("  -> Dolar forte MAS VIX baixo = sinais mistos")
        print("  -> Resultado: NEUTRO - nao ajuda nem atrapalha")
        print("  TRIGGER: Aguardando VIX mudar OU DXY romper niveis chave")

    print()

    # DIMENSÃO 2: FUNDAMENTOS
    print("2. FUNDAMENTOS DO BRASIL")
    print("-" * 80)
    print(f"Status: {decision.fundamental_bias}")
    print()
    print("O que esta analisando:")
    print("  - SELIC: 10.75% (juros altos)")
    print("  - IPCA: 4.5% (inflacao controlada)")
    print("  - EMBI+: 250 pontos (risco-pais baixo)")
    print("  - USD/BRL: R$ 5.85 (cambio estavel)")
    print()

    if decision.fundamental_bias == "BULLISH":
        print("Interpretacao FUNDAMENTAL:")
        print("  -> Juros ALTOS = atrativo para capital estrangeiro")
        print("  -> Inflacao CONTROLADA = economia estavel")
        print("  -> Risco-pais BAIXO = investidores confiam no Brasil")
        print("  -> Resultado: ENTRADA de capital, suporte para ALTA")
        print()
        print("  [!] CONFLITO: Fundamentos POSITIVOS mas preco CAINDO")
        print("      Isso sugere que a queda pode ser TEMPORARIA")
        print()
        print("  TRIGGER para virar BEARISH:")
        print("    - SELIC cair abaixo de 10%")
        print("    - OU EMBI+ subir acima de 300")
        print("    - OU USD/BRL romper R$ 6.00 (fuga de capital)")
    elif decision.fundamental_bias == "BEARISH":
        print("Interpretacao FUNDAMENTAL:")
        print("  -> Fundamentos DETERIORADOS")
        print("  -> Capital SAINDO do Brasil")
        print("  -> Resultado: Pressao natural para BAIXA")
        print("  CONFIRMADO: Fundamentos favorecem VENDA")
    else:
        print("Interpretacao FUNDAMENTAL:")
        print("  -> Fundamentos MISTOS - sem direcao clara")
        print("  -> Resultado: NEUTRO")
        print("  TRIGGER: Aguardando mudanca nos dados fundamentais")

    print()

    # DIMENSÃO 3: SENTIMENTO
    print("3. SENTIMENTO DE MERCADO (INTRADAY)")
    print("-" * 80)
    print(f"Status: {decision.sentiment_bias}")
    print()
    print("O que esta analisando:")
    print(f"  - Preco: {price_change_pct:+.2f}% hoje")
    print(f"  - Volatilidade: {amplitude_pct:.2f}%")
    if volume_variance_pct is not None:
        print(f"  - Volume: {volume_variance_pct:+.1f}% vs media")
    print()

    if decision.sentiment_bias == "BEARISH":
        print("Interpretacao SENTIMENTO:")
        print("  -> VENDEDORES dominando HOJE")
        print("  -> Cada tentativa de alta e punida com vendas")
        print("  -> Momentum descendente claro")

        if volume_variance_pct and volume_variance_pct < Decimal("-20"):
            print()
            print("  [!] ALERTA DE VOLUME:")
            print(f"      Volume {volume_variance_pct:.1f}% ABAIXO da media")
            print("      -> Movimento SEM CONVICCAO")
            print("      -> Pode ser ARMADILHA (bear trap)")
            print("      -> Probabilidade de REVERSAO alta")
            print()
            print("  INTERPRETACAO COMBINADA:")
            print("    Preco caindo MAS volume fraco = DESCONFIAR")
            print("    Movimento pode ser FALSO")
            print()
            print("  TRIGGER para confirmar queda REAL:")
            print("    - Volume subir acima da media")
            print("    - E preco continuar caindo")
            print("    - = Convicçao vendedora VERDADEIRA")
        elif volume_variance_pct and volume_variance_pct > Decimal("20"):
            print()
            print("  [OK] VOLUME CONFIRMANDO:")
            print(f"      Volume {volume_variance_pct:+.1f}% ACIMA da media")
            print("      -> Movimento com CONVICCAO")
            print("      -> Queda eh REAL, nao eh armadilha")
            print("      CONFIRMADO: Sentimento bearish TEM fundamento")
        else:
            print()
            print("  Volume: Normal")
            print("  TRIGGER: Aguardando volume aumentar para confirmar direcao")

    elif decision.sentiment_bias == "BULLISH":
        print("Interpretacao SENTIMENTO:")
        print("  -> COMPRADORES dominando HOJE")
        print("  -> Momentum ascendente")
        print("  CONFIRMADO: Sentimento favorece COMPRA")
    else:
        print("Interpretacao SENTIMENTO:")
        print("  -> LATERAL - sem direcao clara HOJE")
        print("  -> Compradores e vendedores equilibrados")
        print("  TRIGGER: Aguardando rompimento para um lado")

    print()

    # DIMENSÃO 4: TÉCNICA
    print("4. ANALISE TECNICA")
    print("-" * 80)
    print(f"Status: {decision.technical_bias}")
    print()
    print("O que esta analisando:")
    print("  - Medias moveis (SMA 20, 50, 200)")
    print("  - Suportes e resistencias")
    print("  - Padroes graficos")
    print("  - Setup de entrada/saida")
    print()

    # Calcular SMA20 para exemplo
    closes = [c.close.value for c in candles[-20:]]
    sma20 = sum(closes) / len(closes)

    print(f"Preco vs SMA20: R$ {current_price:,.2f} vs R$ {sma20:,.2f}")

    if decision.technical_bias == "BEARISH":
        print()
        print("Interpretacao TECNICA:")
        if current_price < sma20:
            print("  -> Preco ABAIXO da media = tendencia de baixa")
        print("  -> Topos e fundos DESCENDENTES")
        print("  -> Graficamente formando setup de VENDA")
        print()
        print("  [?] MAS PERGUNTA CRITICA:")
        print("      Tem um PONTO DE ENTRADA claro?")
        print("      Tem nivel de STOP LOSS definido?")
        print()
        if decision.recommended_entry is None:
            print("  [X] NAO - Setup tecnico ainda NAO formou")
            print("      -> Estamos em 'meio do nada'")
            print("      -> Sem nivel claro para entrar")
            print()
            print("  TRIGGER para setup formar:")
            print("    - Preco testar uma RESISTENCIA e rejeitar")
            print("    - OU romper um SUPORTE importante")
            print("    - = AI SIM temos ponto de entrada claro")
        else:
            print("  [OK] SIM - Setup tecnico FORMADO")
            print(f"      Entrada sugerida: R$ {decision.recommended_entry:.2f}")
            print("      CONFIRMADO: Setup tecnico existe")

    elif decision.technical_bias == "BULLISH":
        print()
        print("Interpretacao TECNICA:")
        print("  -> Setup tecnico de COMPRA formando")
        print("  CONFIRMADO: Graficamente favorece entrada comprada")
    else:
        print()
        print("Interpretacao TECNICA:")
        print("  -> SEM setup claro no momento")
        print("  -> Aguardando formacao grafica")
        print("  TRIGGER: Formacao de padrao (suporte, resistencia, etc)")

    print()

    # ============================================================================
    # POR QUE NÃO ESTAMOS OPERANDO
    # ============================================================================

    print("=" * 80)
    print("POR QUE NAO ESTAMOS OPERANDO?")
    print("=" * 80)
    print()

    print("DECISAO DO SISTEMA:")
    print(f"  Sinal:       {decision.action.value}")
    print(f"  Confianca:   {decision.confidence:.0%}")
    print(f"  Alinhamento: {decision.alignment_score:.0%}")
    print()

    print("REQUISITOS PARA OPERAR:")
    print(f"  [{'OK' if decision.confidence >= 0.75 else 'X'}] Confianca >= 75%  (atual: {decision.confidence:.0%})")
    print(f"  [{'OK' if decision.alignment_score >= 0.75 else 'X'}] Alinhamento >= 75% (atual: {decision.alignment_score:.0%})")
    print()

    # Análise detalhada do problema
    print("DIAGNOSTICO DO PROBLEMA:")
    print()

    # Contar quantas dimensões estão alinhadas
    dimensions = {
        'Macro': decision.macro_bias,
        'Fundamentos': decision.fundamental_bias,
        'Sentimento': decision.sentiment_bias,
        'Tecnica': decision.technical_bias,
    }

    bearish_count = sum(1 for v in dimensions.values() if v == 'BEARISH')
    bullish_count = sum(1 for v in dimensions.values() if v == 'BULLISH')
    neutral_count = sum(1 for v in dimensions.values() if v == 'NEUTRAL')

    print("Resumo das 4 Dimensoes:")
    for name, bias in dimensions.items():
        symbol_char = "+" if bias == "BULLISH" else "-" if bias == "BEARISH" else "="
        print(f"  {symbol_char} {name:13s}: {bias}")
    print()

    print(f"BEARISH: {bearish_count}/4 dimensoes")
    print(f"BULLISH: {bullish_count}/4 dimensoes")
    print(f"NEUTRAL: {neutral_count}/4 dimensoes")
    print()

    # Identificar o conflito
    if bearish_count >= 3:
        print("[OK] ALINHAMENTO SUFICIENTE para VENDA")
        print("     Mas pode estar faltando outro requisito...")
    elif bullish_count >= 3:
        print("[OK] ALINHAMENTO SUFICIENTE para COMPRA")
        print("     Mas pode estar faltando outro requisito...")
    else:
        print("[X] CONFLITO ENTRE DIMENSOES")
        print()
        print("PROBLEMA IDENTIFICADO:")

        if bullish_count > 0 and bearish_count > 0:
            print(f"  -> {bullish_count} dimensao(es) dizendo COMPRA")
            print(f"  -> {bearish_count} dimensao(es) dizendo VENDA")
            print(f"  -> {neutral_count} dimensao(es) neutra(s)")
            print()
            print("  ISSO EH UM CONFLITO CLASSICO!")
            print()
            print("  Quando as dimensoes BRIGAM entre si:")
            print("    - Sistema NAO tem certeza")
            print("    - Confianca cai automaticamente")
            print("    - Resultado: NAO OPERA")
            print()
            print("  POR QUE isso protege:")
            print("    - Evita entrar em 'armadilhas'")
            print("    - Aguarda situacao CLARA")
            print("    - Preserva capital")

    print()

    # ============================================================================
    # O QUE ESTAMOS ESPERANDO - TRIGGERS
    # ============================================================================

    print("=" * 80)
    print("O QUE ESTAMOS ESPERANDO PARA OPERAR?")
    print("=" * 80)
    print()

    if bearish_count > bullish_count:
        print("CENARIO: Mais dimensoes BEARISH que BULLISH")
        print("DIRECAO PROVAVEL: Venda (Short)")
        print()
        print("TRIGGERS NECESSARIOS para abrir posicao VENDIDA:")
        print()

        # Listar o que falta
        if decision.fundamental_bias == "BULLISH":
            print("  1. [AGUARDANDO] Fundamentos virarem BEARISH")
            print("     Como isso aconteceria:")
            print("       - SELIC cair (menos atrativo)")
            print("       - OU risco-pais subir (EMBI+ > 300)")
            print("       - OU dolar disparar (USD/BRL > R$ 6.00)")
            print()

        if decision.technical_bias != "BEARISH" or decision.recommended_entry is None:
            print("  2. [AGUARDANDO] Setup tecnico CLARO se formar")
            print("     Como isso aconteceria:")
            print("       - Preco testar resistencia e ser rejeitado")
            print("       - OU romper suporte importante")
            print("       - = Ponto de entrada definido com stop loss claro")
            print()

        if volume_variance_pct and volume_variance_pct < Decimal("-20"):
            print("  3. [AGUARDANDO] Volume CONFIRMAR o movimento")
            print("     Como isso aconteceria:")
            print(f"       - Volume atual: {volume_variance_pct:.1f}% abaixo da media")
            print("       - Precisamos volume SUBIR (acima da media)")
            print("       - = Movimento teria CONVICCAO verdadeira")
            print()

        print("  RESUMO: Aguardando que TODAS as pecas se encaixem")
        print("          Quando isso acontecer:")
        print("          -> Alinhamento sobe para >= 75%")
        print("          -> Confianca sobe para >= 75%")
        print("          -> Sistema ENTRA automaticamente")

    elif bullish_count > bearish_count:
        print("CENARIO: Mais dimensoes BULLISH que BEARISH")
        print("DIRECAO PROVAVEL: Compra (Long)")
        print()
        print("TRIGGERS NECESSARIOS para abrir posicao COMPRADA:")
        print("  [Similar ao acima, mas no sentido oposto]")

    else:
        print("CENARIO: Empate ou maioria NEUTRAL")
        print()
        print("O QUE ESTAMOS ESPERANDO:")
        print("  -> Mercado DEFINIR uma direcao clara")
        print("  -> Pode ser rompimento de suporte/resistencia")
        print("  -> Ou mudanca nos fundamentos/macro")
        print()
        print("TRIGGERS:")
        print("  - Preco romper nivel tecnico importante")
        print("  - OU noticia/dado fundamental mudar cenario")
        print("  - OU macro global virar (VIX, DXY)")

    print()
    print("=" * 80)
    print("CONCLUSAO")
    print("=" * 80)
    print()
    print("O sistema esta sendo CONSERVADOR e INTELIGENTE:")
    print()
    print("  1. Reconhece os sinais do mercado")
    print("  2. MAS identifica CONFLITOS entre dimensoes")
    print(f"  3. Confianca baixa ({decision.confidence:.0%}) = 'nao tenho certeza'")
    print("  4. Decisao: AGUARDAR ate ter setup CLARO")
    print()
    print("Isso eh GESTAO DE RISCO PROFISSIONAL:")
    print("  -> Nao opera na duvida")
    print("  -> Preserva capital")
    print("  -> Aguarda alinhamento das 4 dimensoes")
    print("  -> Quando todas alinharem = entrada automatica!")
    print()
    print("=" * 80)

    mt5.disconnect()


if __name__ == "__main__":
    main()
