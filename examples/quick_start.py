"""
Quantum Operator - Quick Start Example

This example demonstrates how to use the Quantum Operator
to analyze the market and get trading decisions.
"""

from decimal import Decimal

from config import get_config
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


def example_with_mt5():
    """Example using real MT5 data."""
    print("=== Quantum Operator - Example with MT5 ===\n")

    # Get configuration
    config = get_config()

    # Connect to MT5
    print("Connecting to MT5...")
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("Failed to connect to MT5")
        return

    print("Connected!\n")

    # Get market data
    symbol = Symbol(config.trading_symbol)
    print(f"Fetching data for {symbol}...")

    candles = mt5.get_candles(
        symbol=symbol,
        timeframe=TimeFrame.M15,
        count=100,
    )

    if not candles:
        print("Failed to get candles")
        mt5.disconnect()
        return

    print(f"Got {len(candles)} candles\n")

    # Initialize Quantum Operator
    print("Initializing Quantum Operator...")
    operator = QuantumOperatorEngine()

    # Analyze and decide
    print("Running complete analysis...\n")

    decision = operator.analyze_and_decide(
        symbol=symbol,
        candles=candles,
        # Market data (would be fetched from APIs in production)
        dollar_index=Decimal("104.5"),
        vix=Decimal("16.8"),
        selic=Decimal("10.75"),
        ipca=Decimal("4.5"),
        usd_brl=Decimal("5.85"),
        embi_spread=250,
    )

    # Display decision
    print(decision.executive_summary)
    print()

    print("Multi-dimensional Analysis:")
    print(f"  Macro:        {decision.macro_bias}")
    print(f"  Fundamental:  {decision.fundamental_bias}")
    print(f"  Sentiment:    {decision.sentiment_bias}")
    print(f"  Technical:    {decision.technical_bias}")
    print(f"  Alignment:    {decision.alignment_score:.0%}")
    print()

    print("Supporting Factors:")
    for factor in decision.supporting_factors:
        print(f"  {factor}")
    print()

    if decision.recommended_entry:
        entry = decision.recommended_entry
        print("Recommended Entry:")
        print(f"  Signal:       {entry.signal.value}")
        print(f"  Entry:        R$ {entry.entry_price.value:,.2f}")
        print(f"  Stop Loss:    R$ {entry.stop_loss.value:,.2f}")
        print(f"  Take Profit:  R$ {entry.take_profit.value:,.2f}")
        print(f"  R/R Ratio:    {entry.risk_reward_ratio:.2f}")
        print(f"  Quality:      {entry.setup_quality.value}")
        print(f"  Confidence:   {entry.confidence:.0%}")
        print(f"  Reason:       {entry.reason}")
    else:
        print("No entry point identified - HOLD")

    # Disconnect
    mt5.disconnect()
    print("\nDisconnected from MT5")


if __name__ == "__main__":
    example_with_mt5()
