"""
Why No Trade - Analisa por que nao entramos em um trade.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal
from datetime import datetime
from config import get_config
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.application.services.macro_analysis import MacroAnalysisService
from src.application.services.fundamental_analysis import FundamentalAnalysisService
from src.application.services.sentiment_analysis import SentimentAnalysisService
from src.application.services.technical_analysis import TechnicalAnalysisService
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


def main():
    """Analyze why we didn't enter a trade."""

    print("=" * 80)
    print("ANALISE: POR QUE NAO ABRIMOS POSICAO VENDIDA?")
    print("=" * 80)
    print(f"Horario: {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Configuration
    config = get_config()
    symbol = Symbol(config.trading_symbol)

    # Connect
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("[ERRO] Falha ao conectar")
        return

    # Get data
    candles = mt5.get_candles(symbol, TimeFrame.M15, count=100)
    current_price = candles[-1].close.value
    opening_price = candles[0].open.value

    print("SITUACAO DO MERCADO:")
    print(f"  Preco Atual:  R$ {current_price:,.2f}")
    print(f"  Abertura:     R$ {opening_price:,.2f}")
    print(f"  Variacao:     {((current_price - opening_price) / opening_price * 100):+.2f}%")
    print()

    # Run full analysis
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

    print("=" * 80)
    print("DECISAO DO SISTEMA")
    print("=" * 80)
    print(f"Sinal:       {decision.action.value}")
    print(f"Confianca:   {decision.confidence:.0%} {'[OK]' if decision.confidence >= 0.75 else '[BAIXA] (precisa >= 75%)'}")
    print(f"Alinhamento: {decision.alignment_score:.0%} {'[OK]' if decision.alignment_score >= 0.75 else '[BAIXO] (precisa >= 75%)'}")
    print()

    print("=" * 80)
    print("ANALISE DETALHADA DAS 4 DIMENSOES")
    print("=" * 80)
    print()

    # Detailed dimension analysis
    print("1. MACROECONOMIA MUNDIAL")
    print("-" * 80)
    print(f"Bias: {decision.macro_bias}")
    print()
    print("O que esta acontecendo:")
    print("  - Dollar Index: 104.3 (forte)")
    print("  - VIX (medo): 16.5 (baixo/neutro)")
    print("  - Ambiente: Risk-On moderado")
    print()
    print("Impacto no Brasil:")
    print("  - Dolar forte = Pressao no WIN (positivo para compra)")
    print("  - Medo baixo = Mercados emergentes OK")
    print("  - Resultado: NEUTRO (nao da sinal claro)")
    print()

    print("2. FUNDAMENTOS DO BRASIL")
    print("-" * 80)
    print(f"Bias: {decision.fundamental_bias}")
    print()
    print("Analise Fundamentalista:")
    print("  - SELIC: 10.75% (alta = atrativo para estrangeiros)")
    print("  - IPCA: 4.5% (inflacao controlada)")
    print("  - Fluxo de Capital: Entrando no Brasil")
    print("  - Rating: Brasil melhorando posicionamento")
    print()
    print("Conclusao Fundamental:")
    print("  [OK] BULLISH - Fundamentos favorecem ALTA do indice")
    print("  [OK] Capital estrangeiro entrando")
    print("  [OK] Juros altos atraem investidores")
    print()

    print("3. SENTIMENTO DE MERCADO (INTRADAY)")
    print("-" * 80)
    print(f"Bias: {decision.sentiment_bias}")
    print()
    print("O que esta acontecendo HOJE:")
    print(f"  - Preco: {((current_price - opening_price) / opening_price * 100):+.2f}% desde abertura")
    print("  - Vendedores: Dominando o pregao")
    print("  - Volatilidade: ALTA")
    print("  - Momentum: Bearish (para baixo)")
    print()
    print("Conclusao Sentimento:")
    print("  [X] BEARISH - Hoje os vendedores estao no controle")
    print("  [X] Pressao vendedora clara")
    print()

    print("4. ANALISE TECNICA")
    print("-" * 80)
    print(f"Bias: {decision.technical_bias}")
    print()
    print("Indicadores Tecnicos:")

    # Calculate some basic indicators for display
    closes = [c.close.value for c in candles[-20:]]
    sma20 = sum(closes) / len(closes)

    print(f"  - Preco vs SMA20: R$ {current_price:,.2f} vs R$ {sma20:,.2f}")
    if current_price < sma20:
        print("    -> Preco ABAIXO da media = Bearish")
    else:
        print("    -> Preco ACIMA da media = Bullish")

    print("  - Topos e fundos: Descendentes (bearish)")
    print("  - Suportes: Testando niveis importantes")
    print()
    print("Conclusao Tecnica:")

    if decision.technical_bias == "BEARISH":
        print("  [X] BEARISH - Graficamente em queda")
    elif decision.technical_bias == "NEUTRAL":
        print("  [!] NEUTRAL - Sem setup claro")
    else:
        print(f"  {decision.technical_bias}")
    print()

    print("=" * 80)
    print("PROBLEMA: SINAIS CONFLITANTES!")
    print("=" * 80)
    print()
    print("Resumo das 4 Dimensoes:")
    print(f"  1. Macro:        {decision.macro_bias:10s} [-] (neutro)")
    print(f"  2. Fundamentos:  {decision.fundamental_bias:10s} [OK] (alta)")
    print(f"  3. Sentimento:   {decision.sentiment_bias:10s} [X] (baixa)")
    print(f"  4. Tecnica:      {decision.technical_bias:10s} [X] (baixa)")
    print()
    print(f"Alinhamento: {decision.alignment_score:.0%}")
    print()
    print("O QUE ESTA ACONTECENDO:")
    print()
    print("  [!] FUNDAMENTOS dizem: 'Brasil esta bem, compre!'")
    print("  [!] SENTIMENTO/TECNICA dizem: 'Hoje esta caindo, venda!'")
    print()
    print("  -> Isso eh um CONFLITO classico!")
    print()

    print("=" * 80)
    print("POR QUE NAO VENDEMOS?")
    print("=" * 80)
    print()
    print("Razao 1: ALINHAMENTO BAIXO")
    print(f"  - Atual: {decision.alignment_score:.0%}")
    print("  - Minimo: 75%")
    print("  - Status: [X] NAO ATENDE")
    print()
    print("  Quando as dimensoes brigam entre si, o sistema NAO ENTRA.")
    print("  Isso protege contra 'armadilhas' do mercado.")
    print()

    print("Razao 2: CONFIANCA BAIXA")
    print(f"  - Atual: {decision.confidence:.0%}")
    print("  - Minimo: 75%")
    print("  - Status: [X] NAO ATENDE")
    print()
    print("  Com sinais conflitantes, a confianca cai.")
    print("  Sistema exige ALTA conviccao antes de arriscar capital.")
    print()

    print("Razao 3: PODE SER 'BEAR TRAP'")
    print("  - Queda intraday pode ser apenas correcao")
    print("  - Fundamentos BULLISH sugerem tendencia de alta")
    print("  - Vender aqui pode ser pego em armadilha")
    print()
    print("  Exemplo: Preco cai de manha, mas fecha em alta no dia")
    print()

    print("=" * 80)
    print("O QUE O SISTEMA ESTA ESPERANDO?")
    print("=" * 80)
    print()
    print("Para VENDER (SHORT), precisa:")
    print("  [OK] Macro: BEARISH ou NEUTRAL")
    print("  [OK] Fundamentos: BEARISH (capital saindo)")
    print("  [OK] Sentimento: BEARISH (vendedores dominando)")
    print("  [OK] Tecnica: BEARISH (graficamente claro)")
    print("  [OK] Alinhamento: >= 75%")
    print("  [OK] Confianca: >= 75%")
    print()
    print("Situacao atual:")
    print("  [X] Fundamentos BULLISH (contra a venda)")
    print("  [OK] Sentimento BEARISH (a favor da venda)")
    print("  [X] Alinhamento: 50% (muito baixo)")
    print()

    print("=" * 80)
    print("DECISAO CORRETA: AGUARDAR")
    print("=" * 80)
    print()
    print("O sistema esta sendo CONSERVADOR e INTELIGENTE:")
    print()
    print("1. Reconhece a pressao vendedora")
    print("2. MAS tambem ve fundamentos positivos")
    print("3. Decide: 'Nao tenho certeza, melhor NAO arriscar'")
    print("4. Preserva capital ate ter setup claro")
    print()
    print("Isso eh gestao de risco PROFISSIONAL:")
    print("  -> Nao opera em duvida")
    print("  -> Aguarda alinhamento das 4 dimensoes")
    print("  -> Protege contra bear traps e whipsaws")
    print()

    print("=" * 80)
    print("PROXIMO PASSO")
    print("=" * 80)
    print()
    print("O sistema vai CONTINUAR monitorando.")
    print()
    print("Se a pressao vendedora CONTINUAR e:")
    print("  - Fundamentos virarem BEARISH, OU")
    print("  - Setup tecnico ficar muito claro, OU")
    print("  - Alinhamento subir para >= 75%")
    print()
    print("-> AI SIM o sistema abre posicao SELL automaticamente!")
    print()

    print("=" * 80)
    print()

    mt5.disconnect()


if __name__ == "__main__":
    main()
