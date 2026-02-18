"""
Trading Dashboard - Mostra status do sistema em tempo real.
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


def clear_screen():
    """Clear terminal screen."""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def display_dashboard():
    """Display trading dashboard."""

    config = get_config()
    symbol = Symbol(config.trading_symbol)

    # Connect
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("[ERRO] Nao conectado ao MT5")
        return

    # Get data
    balance = mt5.get_account_balance()
    candles = mt5.get_candles(symbol, TimeFrame.M5, count=100)

    if not candles:
        print("[ERRO] Sem dados")
        mt5.disconnect()
        return

    current_candle = candles[-1]
    opening_candle = candles[0]

    current_price = current_candle.close.value
    opening_price = opening_candle.open.value
    change = ((current_price - opening_price) / opening_price) * 100

    # Analyze
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

    # Display
    clear_screen()

    print("=" * 80)
    print(f"TRADING DASHBOARD - {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 80)
    print()

    print("CONTA:")
    print(f"  Saldo: R$ {balance:,.2f}")
    print()

    print("MERCADO:")
    print(f"  Simbolo:  {symbol}")
    print(f"  Preco:    R$ {current_price:,.2f}")
    print(f"  Variacao: {change:+.2f}% (desde abertura)")
    print()

    print("ANALISE ATUAL:")
    print(f"  Sinal:       {decision.action.value}")
    print(f"  Confianca:   {decision.confidence:.0%}")
    print(f"  Alinhamento: {decision.alignment_score:.0%}")
    print()

    print("CONTEXTO:")
    print(f"  Macro:        {decision.macro_bias}")
    print(f"  Fundamentos:  {decision.fundamental_bias}")
    print(f"  Sentimento:   {decision.sentiment_bias}")
    print(f"  Tecnica:      {decision.technical_bias}")
    print()

    # Entry decision
    would_enter = (
        decision.action.value in ["BUY", "SELL"]
        and decision.confidence >= Decimal("0.75")
        and decision.alignment_score >= Decimal("0.75")
    )

    print("STATUS:")
    if would_enter:
        print(f"  [ENTRADA] Condicoes para {'COMPRA' if decision.action.value == 'BUY' else 'VENDA'}")
        if decision.recommended_entry:
            entry = decision.recommended_entry
            print(f"  Entry:  R$ {entry.entry_price.value:,.2f}")
            print(f"  Stop:   R$ {entry.stop_loss.value:,.2f}")
            print(f"  Target: R$ {entry.take_profit.value:,.2f}")
            print(f"  R/R:    {entry.risk_reward_ratio:.2f}")
    else:
        print(f"  [AGUARDANDO] Setup de qualidade")
        if decision.confidence < Decimal("0.75"):
            print(f"    - Confianca: {decision.confidence:.0%} < 75%")
        if decision.alignment_score < Decimal("0.75"):
            print(f"    - Alinhamento: {decision.alignment_score:.0%} < 75%")

    print()
    print(f"Razao: {decision.primary_reason}")
    print()

    print("=" * 80)
    print("Sistema monitorando automaticamente a cada 30 segundos")
    print("=" * 80)

    mt5.disconnect()


if __name__ == "__main__":
    import time

    try:
        while True:
            display_dashboard()
            time.sleep(30)  # Update every 30 seconds
    except KeyboardInterrupt:
        print("\n\nDashboard interrompido")
