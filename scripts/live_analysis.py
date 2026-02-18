"""
Live Market Analysis - Real-time analysis during trading hours.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal
from datetime import datetime
from config import get_config
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


def analyze_live_market():
    """Analyze market with real-time data from MT5."""
    print("=" * 80)
    print("OPERADOR QUANTICO - ANALISE EM TEMPO REAL")
    print("=" * 80)
    print()

    now = datetime.now()
    print(f"Horario: {now.strftime('%H:%M:%S')} (Brasilia)")
    print(f"Status: MERCADO ABERTO")
    print()

    # Get config
    config = get_config()

    # Connect to MT5
    print("Conectando ao MT5...")
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("[ERRO] Falha ao conectar ao MT5")
        return

    print("[OK] Conectado!\n")

    # Get symbol
    symbol = Symbol(config.trading_symbol)
    print(f"Simbolo: {symbol}")
    print()

    # Get current price
    print("Capturando preco atual...")
    tick = mt5.get_current_tick(symbol)
    print(f"  Bid: R$ {tick.bid.value:,.2f}")
    print(f"  Ask: R$ {tick.ask.value:,.2f}")
    print(f"  Last: R$ {tick.last.value:,.2f}")
    print()

    # Get candles for analysis
    print("Capturando dados de mercado...")
    candles_5m = mt5.get_candles(symbol, TimeFrame.M5, count=100)
    candles_15m = mt5.get_candles(symbol, TimeFrame.M15, count=100)

    if not candles_5m or not candles_15m:
        print("[ERRO] Falha ao obter candles")
        mt5.disconnect()
        return

    print(f"  [OK] {len(candles_5m)} candles de 5min")
    print(f"  [OK] {len(candles_15m)} candles de 15min")
    print()

    # Show opening info
    opening_candle = candles_5m[0]
    current_candle = candles_5m[-1]

    print("-" * 80)
    print("RESUMO DO PREGAO (desde abertura)")
    print("-" * 80)
    print(f"  Abertura:       R$ {opening_candle.open.value:,.2f}")
    print(f"  Atual:          R$ {current_candle.close.value:,.2f}")
    print(f"  Maxima do dia:  R$ {max(c.high.value for c in candles_5m):,.2f}")
    print(f"  Minima do dia:  R$ {min(c.low.value for c in candles_5m):,.2f}")

    change = ((current_candle.close.value - opening_candle.open.value) / opening_candle.open.value) * 100
    print(f"  Variacao:       {change:+.2f}%")
    print()

    # Run complete analysis
    print("-" * 80)
    print("EXECUTANDO ANALISE MULTIDIMENSIONAL...")
    print("-" * 80)
    print()

    operator = QuantumOperatorEngine()

    # Simulated macro data (in production would fetch from APIs)
    print("[1/4] Analisando cenario macroeconomico global...")
    print("[2/4] Analisando fundamentos do Brasil...")
    print("[3/4] Analisando sentimento de mercado intraday...")
    print("[4/4] Analisando tecnica e identificando setups...")
    print()

    decision = operator.analyze_and_decide(
        symbol=symbol,
        candles=candles_15m,
        # Current market conditions (examples - would be fetched)
        dollar_index=Decimal("104.3"),
        vix=Decimal("16.5"),
        selic=Decimal("10.75"),
        ipca=Decimal("4.5"),
        usd_brl=Decimal("5.85"),
        embi_spread=250,
    )

    print("=" * 80)
    print("DECISAO DO HEAD FINANCEIRO")
    print("=" * 80)
    print()

    # Display decision
    print(decision.executive_summary)
    print()

    print("-" * 80)
    print("ANALISE MULTIDIMENSIONAL")
    print("-" * 80)
    print(f"  Macro (Global):       {decision.macro_bias}")
    print(f"  Fundamentos (BR):     {decision.fundamental_bias}")
    print(f"  Sentimento (Intraday):{decision.sentiment_bias}")
    print(f"  Tecnica (Entry):      {decision.technical_bias}")
    print()
    print(f"  Alinhamento:          {decision.alignment_score:.0%}")
    print(f"  Nivel de Risco:       {decision.risk_level}")
    print()

    print("-" * 80)
    print("FATORES DE SUPORTE")
    print("-" * 80)
    for factor in decision.supporting_factors:
        # Remove emojis for Windows console
        clean = factor.encode('ascii', 'ignore').decode('ascii').strip()
        print(f"  {clean}")
    print()

    if decision.warning_factors:
        print("-" * 80)
        print("FATORES DE ATENCAO")
        print("-" * 80)
        for warning in decision.warning_factors:
            clean = warning.encode('ascii', 'ignore').decode('ascii').strip()
            print(f"  {clean}")
        print()

    if decision.recommended_entry:
        entry = decision.recommended_entry
        print("-" * 80)
        print("SETUP RECOMENDADO")
        print("-" * 80)
        print(f"  Tipo:         {entry.setup_type}")
        print(f"  Sinal:        {entry.signal.value}")
        print(f"  Qualidade:    {entry.setup_quality.value}")
        print()
        print(f"  Entrada:      R$ {entry.entry_price.value:,.2f}")
        print(f"  Stop Loss:    R$ {entry.stop_loss.value:,.2f}")
        print(f"  Take Profit:  R$ {entry.take_profit.value:,.2f}")
        print()
        print(f"  R/R Ratio:    {entry.risk_reward_ratio:.2f}")
        print(f"  Confianca:    {entry.confidence:.0%}")
        print()
        print(f"  Razao: {entry.reason}")
        print()

        # Calculate position size
        risk_amount = abs(entry.entry_price.value - entry.stop_loss.value)
        print(f"  Risco por contrato: R$ {risk_amount:,.2f}")
        print()
    else:
        print("-" * 80)
        print("RECOMENDACAO")
        print("-" * 80)
        print("  [AGUARDAR] Sem setup claro no momento.")
        print("  Aguarde melhores condicoes de entrada.")
        print()

    # Account info
    print("-" * 80)
    print("CONTA")
    print("-" * 80)
    balance = mt5.get_account_balance()
    equity = mt5.get_account_equity()
    print(f"  Saldo:  R$ {balance:,.2f}")
    print(f"  Equity: R$ {equity:,.2f}")
    print()

    # Disconnect
    mt5.disconnect()

    print("=" * 80)
    print("[OK] ANALISE CONCLUIDA")
    print("=" * 80)
    print()

    return decision


if __name__ == "__main__":
    analyze_live_market()
