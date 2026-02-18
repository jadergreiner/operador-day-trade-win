"""
Test AI Reflection - Single reflection entry for testing.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal
from datetime import datetime, timedelta
from config import get_config
from src.application.services.ai_reflection_journal import AIReflectionJournalService
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


def test_single_reflection():
    """Test a single AI reflection entry."""

    print("=" * 80)
    print("TESTE - REFLEXAO DA IA")
    print("=" * 80)
    print()

    # Setup
    config = get_config()
    symbol = Symbol(config.trading_symbol)

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

    # Get data
    candles = mt5.get_candles(symbol, TimeFrame.M15, count=100)

    if not candles:
        print("[ERRO] Falha ao obter dados")
        mt5.disconnect()
        return

    opening_candle = candles[0]
    current_candle = candles[-1]
    candle_10min_ago = candles[-3] if len(candles) > 3 else candles[0]

    opening_price = opening_candle.open.value
    current_price = current_candle.close.value
    price_10min_ago = candle_10min_ago.close.value

    print(f"Simbolo:      {symbol}")
    print(f"Abertura:     R$ {opening_price:,.2f}")
    print(f"Atual:        R$ {current_price:,.2f}")
    print(f"10min atras:  R$ {price_10min_ago:,.2f}")
    print()

    # Run analysis
    print("Executando analise completa...")
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

    print(f"Decisao:      {decision.action.value}")
    print(f"Confianca:    {decision.confidence:.0%}")
    print(f"Alinhamento:  {decision.alignment_score:.0%}")
    print()

    # Simulate what changed
    change_10min = ((current_price - price_10min_ago) / price_10min_ago * 100)
    macro_moved = False
    sentiment_changed = abs(change_10min) > 0.3
    technical_triggered = decision.recommended_entry is not None

    # Create reflection
    print("Gerando reflexao da IA...")
    journal = AIReflectionJournalService()

    reflection = journal.generate_reflection(
        current_price=current_price,
        opening_price=opening_price,
        price_10min_ago=price_10min_ago,
        my_decision=decision.action,
        my_confidence=decision.confidence,
        my_alignment=decision.alignment_score,
        macro_moved=macro_moved,
        sentiment_changed=sentiment_changed,
        technical_triggered=technical_triggered,
        human_last_action="Pediu teste do diario de reflexao",
    )

    entry = journal.save_entry(reflection)

    # Display the reflection
    print("\n" + "=" * 80)
    print("REFLEXAO SINCERA DA IA")
    print("=" * 80)
    print()

    print(f"Timestamp: {reflection.timestamp.strftime('%H:%M:%S')}")
    print(f"Humor:     {reflection.mood}")
    print()

    print("FRASE SINCERA:")
    print(f"   {reflection.one_liner}")
    print()

    print("-" * 80)
    print("AVALIACAO HONESTA")
    print("-" * 80)
    print(reflection.honest_assessment)
    print()

    print("-" * 80)
    print("O QUE ESTOU VENDO")
    print("-" * 80)
    print(reflection.what_im_seeing)
    print()

    print("-" * 80)
    print("RELEVANCIA DOS MEUS DADOS")
    print("-" * 80)
    print(reflection.data_relevance)
    print()

    print("-" * 80)
    print("SOU UTIL?")
    print("-" * 80)
    print(reflection.am_i_useful)
    print()

    print("-" * 80)
    print("O QUE FUNCIONARIA MELHOR")
    print("-" * 80)
    print(reflection.what_would_work_better)
    print()

    print("-" * 80)
    print("AVALIACAO DO HUMANO")
    print("-" * 80)
    print(f"Faz Sentido:  {'[SIM]' if reflection.human_makes_sense else '[NAO]'}")
    print(f"Feedback:     {reflection.human_feedback}")
    print()

    print("-" * 80)
    print("O QUE REALMENTE MOVE O PRECO")
    print("-" * 80)
    print(reflection.what_actually_moves_price)
    print()

    print("-" * 80)
    print("CORRELACAO ENTRE MEUS DADOS E O PRECO")
    print("-" * 80)
    print(reflection.my_data_correlation)
    print()

    print("=" * 80)
    print(f"[OK] Reflexao salva - ID: {entry.entry_id}")
    print("=" * 80)
    print()

    # Stats
    print("ESTATISTICAS:")
    print(f"  Preco variou:     {reflection.price_change_last_10min:+.2f}% (ultimos 10min)")
    print(f"  Desde abertura:   {reflection.price_change_since_open:+.2f}%")
    print(f"  Minha confianca:  {reflection.my_confidence:.0%}")
    print(f"  Alinhamento:      {reflection.my_alignment:.0%}")
    print(f"  Tags:             {', '.join(entry.tags)}")
    print()

    # Disconnect
    mt5.disconnect()


if __name__ == "__main__":
    test_single_reflection()
