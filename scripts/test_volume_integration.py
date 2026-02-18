"""
Test Volume Integration in Journals - Validates volume analysis is working.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from decimal import Decimal
from datetime import datetime
from config import get_config
from src.application.services.trading_journal import TradingJournalService
from src.application.services.ai_reflection_journal import AIReflectionJournalService
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.application.services.volume_analysis import VolumeAnalysisService
from src.domain.value_objects import Symbol
from src.domain.enums.trading_enums import TradeSignal
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


def test_volume_integration():
    """Test that volume analysis is integrated into journals."""

    print("=" * 80)
    print("TESTE DE INTEGRACAO - VOLUME NOS DIARIOS")
    print("=" * 80)
    print()

    # Connect and get data
    config = get_config()
    symbol = Symbol(config.trading_symbol)

    print("Conectando ao MT5...")
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("[ERRO] Falha ao conectar")
        return False

    print("[OK] Conectado\n")

    # Get candles
    print("Obtendo dados de mercado...")
    candles = mt5.get_candles(symbol, TimeFrame.M15, count=400)  # 4+ days

    if not candles:
        print("[ERRO] Sem dados")
        mt5.disconnect()
        return False

    print(f"[OK] {len(candles)} candles obtidos\n")

    # Calculate volume metrics
    print("-" * 80)
    print("TESTE 1: Volume Analysis Service")
    print("-" * 80)

    volume_service = VolumeAnalysisService()
    volume_today, volume_avg_3days, volume_variance_pct = volume_service.calculate_volume_metrics(candles)

    if volume_variance_pct is not None:
        print(f"[OK] Volume Hoje:      {volume_today:,} contratos")
        print(f"[OK] Media 3 Dias:     {volume_avg_3days:,} contratos")
        print(f"[OK] Variacao:         {volume_variance_pct:+.1f}%")
        print(f"[OK] Interpretacao:    {volume_service.get_volume_interpretation(volume_variance_pct)}")
        print()
        test1_passed = True
    else:
        print("[X] Falha ao calcular volume")
        test1_passed = False

    # Get market data
    opening_candle = candles[0]
    current_candle = candles[-1]
    opening_price = opening_candle.open.value
    current_price = current_candle.close.value
    high = max(c.high.value for c in candles)
    low = min(c.low.value for c in candles)

    # Get decision
    print("-" * 80)
    print("TESTE 2: Trading Journal com Volume")
    print("-" * 80)

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

    decision_data = {
        "action": decision.action,
        "confidence": decision.confidence,
        "primary_reason": decision.primary_reason,
        "macro_bias": decision.macro_bias,
        "fundamental_bias": decision.fundamental_bias,
        "sentiment_bias": decision.sentiment_bias,
        "technical_bias": decision.technical_bias,
        "alignment_score": decision.alignment_score,
        "supporting_factors": decision.supporting_factors,
        "market_regime": decision.market_regime,
    }

    journal = TradingJournalService()

    try:
        narrative = journal.create_narrative(
            symbol=symbol,
            current_price=current_price,
            opening_price=opening_price,
            high=high,
            low=low,
            decision_data=decision_data,
            volume_today=volume_today,
            volume_avg_3days=volume_avg_3days,
            volume_variance_pct=volume_variance_pct,
        )

        print("[OK] Narrativa criada com volume")
        print()
        print("Amostra da narrativa:")
        print(f"  Headline: {narrative.headline}")
        print(f"  Feeling:  {narrative.market_feeling}")
        print()
        print("  Narrative excerpt:")
        excerpt = narrative.detailed_narrative[:200] + "..."
        print(f"  {excerpt}")
        print()

        # Check if volume is mentioned
        if volume_variance_pct and volume_variance_pct < Decimal("-20"):
            if "volume BAIXO" in narrative.detailed_narrative.lower() or "volume baixo" in narrative.detailed_narrative.lower():
                print("[OK] Volume BAIXO mencionado na narrativa")
                test2_passed = True
            else:
                print("[X] Volume nao mencionado (esperado para volume baixo)")
                test2_passed = False
        elif volume_variance_pct and volume_variance_pct > Decimal("20"):
            if "volume ALTO" in narrative.detailed_narrative or "volume alto" in narrative.detailed_narrative.lower():
                print("[OK] Volume ALTO mencionado na narrativa")
                test2_passed = True
            else:
                print("[X] Volume nao mencionado (esperado para volume alto)")
                test2_passed = False
        else:
            print("[OK] Volume normal - mencao opcional na narrativa")
            test2_passed = True

        # Check tags
        print()
        print(f"Tags geradas: {', '.join(narrative.tags)}")

        volume_tags = [t for t in narrative.tags if 'volume' in t or 'conviction' in t or 'divergence' in t or 'trap' in t]
        if volume_tags:
            print(f"[OK] Tags de volume encontradas: {', '.join(volume_tags)}")
        else:
            print("[!] Nenhuma tag de volume (OK se volume normal)")

        print()

    except Exception as e:
        print(f"[X] Erro ao criar narrativa: {e}")
        test2_passed = False

    # Test AI Reflection
    print("-" * 80)
    print("TESTE 3: AI Reflection com Volume")
    print("-" * 80)

    ai_journal = AIReflectionJournalService()

    try:
        reflection = ai_journal.generate_reflection(
            current_price=current_price,
            opening_price=opening_price,
            price_10min_ago=current_price * Decimal("0.998"),  # Simulate 10min ago
            my_decision=decision.action,
            my_confidence=decision.confidence,
            my_alignment=decision.alignment_score,
            macro_moved=False,
            sentiment_changed=True,
            technical_triggered=False,
            human_last_action="Testing volume integration",
            volume_variance_pct=volume_variance_pct,
        )

        print("[OK] Reflexao criada com volume")
        print()
        print("Amostra da reflexao:")
        print(f"  Mood:      {reflection.mood}")
        print(f"  One-liner: {reflection.one_liner}")
        print()
        print("  Data Relevance:")
        relevance_excerpt = reflection.data_relevance[:150] + "..."
        print(f"  {relevance_excerpt}")
        print()

        # Check if volume is mentioned in critical cases
        if volume_variance_pct and abs(volume_variance_pct) > Decimal("20"):
            if "volume" in reflection.data_relevance.lower():
                print("[OK] Volume mencionado na relevancia dos dados")
                test3_passed = True
            else:
                print("[X] Volume nao mencionado (esperado para volume extremo)")
                test3_passed = False
        else:
            print("[OK] Volume normal - mencao opcional na reflexao")
            test3_passed = True

        print()
        print("  What Actually Moves Price:")
        mover_excerpt = reflection.what_actually_moves_price[:150]
        print(f"  {mover_excerpt}")

        if volume_variance_pct and volume_variance_pct < Decimal("-20"):
            if "FALSO" in reflection.what_actually_moves_price or "falso" in reflection.what_actually_moves_price:
                print("[OK] Movimento falso identificado por falta de volume")
            else:
                print("[!] Movimento falso nao identificado (OK se preco estavel)")

        print()

    except Exception as e:
        print(f"[X] Erro ao criar reflexao: {e}")
        test3_passed = False

    # Summary
    print("=" * 80)
    print("RESUMO DOS TESTES")
    print("=" * 80)

    tests = [
        ("Volume Analysis Service", test1_passed),
        ("Trading Journal Integration", test2_passed),
        ("AI Reflection Integration", test3_passed),
    ]

    all_passed = True
    for test_name, passed in tests:
        status = "[OK] PASSOU" if passed else "[X] FALHOU"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print()

    if all_passed:
        print("[OK] TODOS OS TESTES PASSARAM")
        print()
        print("A integracao de volume nos diarios esta funcionando corretamente!")
        print()
        print("Proximos passos:")
        print("  1. python scripts/continuous_journal.py     - Diario a cada 15min com volume")
        print("  2. python scripts/ai_reflection_continuous.py - Reflexao a cada 10min com volume")
        print("  3. python scripts/view_journals.py           - Ver diarios com contexto de volume")
        print()
    else:
        print("[X] ALGUNS TESTES FALHARAM")
        print()
        print("Por favor, revise os erros acima.")
        print()

    mt5.disconnect()

    return all_passed


if __name__ == "__main__":
    success = test_volume_integration()
    sys.exit(0 if success else 1)
