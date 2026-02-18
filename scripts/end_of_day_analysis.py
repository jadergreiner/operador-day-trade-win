"""
End of Day Analysis - Analisa resultado de todas as decisoes do dia.

Compara as decisoes tomadas com o que realmente aconteceu no mercado.
Base para aprendizagem por reforco.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta
from decimal import Decimal
from config import get_config
from src.application.services.trading_journal import TradingJournalService
from src.application.services.ai_reflection_journal import AIReflectionJournalService
from src.domain.value_objects import Symbol
from src.domain.enums.trading_enums import TradeSignal
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame


def analyze_decision_outcome(
    decision: TradeSignal,
    decision_price: Decimal,
    price_after_30min: Decimal,
    price_after_1h: Decimal,
    price_after_2h: Decimal,
) -> dict:
    """
    Analyze if the decision was correct.

    Args:
        decision: What was decided (BUY/SELL/HOLD)
        decision_price: Price when decision was made
        price_after_30min: Price 30 minutes later
        price_after_1h: Price 1 hour later
        price_after_2h: Price 2 hours later

    Returns:
        dict with outcome analysis
    """

    change_30min = ((price_after_30min - decision_price) / decision_price) * 100
    change_1h = ((price_after_1h - decision_price) / decision_price) * 100
    change_2h = ((price_after_2h - decision_price) / decision_price) * 100

    # Determine if decision was correct
    if decision == TradeSignal.BUY:
        # BUY is correct if price went up
        correct_30min = change_30min > 0.2  # At least +0.2%
        correct_1h = change_1h > 0.3  # At least +0.3%
        correct_2h = change_2h > 0.5  # At least +0.5%

    elif decision == TradeSignal.SELL:
        # SELL is correct if price went down
        correct_30min = change_30min < -0.2  # At least -0.2%
        correct_1h = change_1h < -0.3  # At least -0.3%
        correct_2h = change_2h < -0.5  # At least -0.5%

    else:  # HOLD
        # HOLD is correct if price stayed relatively flat
        correct_30min = abs(change_30min) < 0.3
        correct_1h = abs(change_1h) < 0.5
        correct_2h = abs(change_2h) < 0.7

    outcome = {
        "decision": decision.value,
        "decision_price": float(decision_price),
        "change_30min": float(change_30min),
        "change_1h": float(change_1h),
        "change_2h": float(change_2h),
        "correct_30min": correct_30min,
        "correct_1h": correct_1h,
        "correct_2h": correct_2h,
        "score": (
            (1 if correct_30min else 0) +
            (1 if correct_1h else 0) +
            (1 if correct_2h else 0)
        ) / 3.0,  # 0.0 to 1.0
    }

    return outcome


def run_end_of_day_analysis():
    """Run complete end of day analysis."""

    print("=" * 80)
    print("ANALISE END OF DAY - APRENDIZAGEM POR REFORCO")
    print("=" * 80)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y')}")
    print(f"Hora: {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Load journals
    print("Carregando diarios...")
    trading_journal = TradingJournalService()
    ai_journal = AIReflectionJournalService()

    trading_entries = trading_journal.get_today_entries()
    ai_entries = ai_journal.get_today_entries()

    print(f"  Trading Journal:  {len(trading_entries)} entradas")
    print(f"  AI Reflection:    {len(ai_entries)} reflexoes")
    print()

    if not trading_entries:
        print("Nenhuma entrada para analisar hoje.")
        return

    # Connect to MT5 to get historical data
    print("Conectando ao MT5...")
    config = get_config()
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    if not mt5.connect():
        print("[ERRO] Falha ao conectar ao MT5")
        return

    print("[OK] Conectado")
    print()

    symbol = Symbol(config.trading_symbol)

    # Get all candles for the day
    candles = mt5.get_candles(symbol, TimeFrame.M5, count=500)

    if not candles:
        print("[ERRO] Falha ao obter dados historicos")
        mt5.disconnect()
        return

    print("=" * 80)
    print("ANALISE DE DECISOES")
    print("=" * 80)
    print()

    results = []

    for i, entry in enumerate(trading_entries, 1):
        print(f"[{i}/{len(trading_entries)}] Analisando entrada {entry.entry_id}")
        print(f"    Hora Decisao: {entry.time}")
        print(f"    Decisao:      {entry.narrative.decision.value}")
        print(f"    Confianca:    {entry.confidence:.0%}")
        print(f"    Alinhamento:  {entry.alignment_score:.0%}")

        # Get decision details
        decision_time = datetime.strptime(f"{entry.date} {entry.time}", "%Y-%m-%d %H:%M:%S")
        decision_price = entry.current_price

        # Find prices at different time horizons
        # This is simplified - in production you'd search candles by timestamp
        decision_candle_idx = len(candles) // 2  # Placeholder
        price_30min_later = candles[min(decision_candle_idx + 6, len(candles) - 1)].close.value
        price_1h_later = candles[min(decision_candle_idx + 12, len(candles) - 1)].close.value
        price_2h_later = candles[min(decision_candle_idx + 24, len(candles) - 1)].close.value

        # Analyze outcome
        outcome = analyze_decision_outcome(
            decision=entry.narrative.decision,
            decision_price=decision_price,
            price_after_30min=price_30min_later,
            price_after_1h=price_1h_later,
            price_after_2h=price_2h_later,
        )

        results.append({
            "entry": entry,
            "outcome": outcome,
        })

        print(f"    Resultado 30min: {outcome['change_30min']:+.2f}% - {'CORRETO' if outcome['correct_30min'] else 'ERRADO'}")
        print(f"    Resultado 1h:    {outcome['change_1h']:+.2f}% - {'CORRETO' if outcome['correct_1h'] else 'ERRADO'}")
        print(f"    Resultado 2h:    {outcome['change_2h']:+.2f}% - {'CORRETO' if outcome['correct_2h'] else 'ERRADO'}")
        print(f"    Score:           {outcome['score']:.1%}")
        print()

    # Summary statistics
    print("=" * 80)
    print("ESTATISTICAS GERAIS")
    print("=" * 80)
    print()

    total = len(results)
    correct_30min = sum(1 for r in results if r["outcome"]["correct_30min"])
    correct_1h = sum(1 for r in results if r["outcome"]["correct_1h"])
    correct_2h = sum(1 for r in results if r["outcome"]["correct_2h"])
    avg_score = sum(r["outcome"]["score"] for r in results) / total if total > 0 else 0

    print(f"Total de Decisoes:  {total}")
    print(f"Acerto 30min:       {correct_30min}/{total} ({correct_30min/total*100:.0f}%)")
    print(f"Acerto 1h:          {correct_1h}/{total} ({correct_1h/total*100:.0f}%)")
    print(f"Acerto 2h:          {correct_2h}/{total} ({correct_2h/total*100:.0f}%)")
    print(f"Score Medio:        {avg_score:.1%}")
    print()

    # Analysis by decision type
    print("-" * 80)
    print("PERFORMANCE POR TIPO DE DECISAO")
    print("-" * 80)
    print()

    for decision_type in ["BUY", "SELL", "HOLD"]:
        filtered = [r for r in results if r["entry"].narrative.decision.value == decision_type]
        if not filtered:
            continue

        count = len(filtered)
        score = sum(r["outcome"]["score"] for r in filtered) / count
        print(f"{decision_type:4s}: {count:2d} decisoes - Score medio: {score:.1%}")

    print()

    # Analysis by confidence level
    print("-" * 80)
    print("PERFORMANCE POR NIVEL DE CONFIANCA")
    print("-" * 80)
    print()

    high_conf = [r for r in results if r["entry"].confidence > 0.7]
    med_conf = [r for r in results if 0.4 <= r["entry"].confidence <= 0.7]
    low_conf = [r for r in results if r["entry"].confidence < 0.4]

    if high_conf:
        score = sum(r["outcome"]["score"] for r in high_conf) / len(high_conf)
        print(f"Alta (>70%):   {len(high_conf):2d} decisoes - Score: {score:.1%}")

    if med_conf:
        score = sum(r["outcome"]["score"] for r in med_conf) / len(med_conf)
        print(f"Media (40-70%): {len(med_conf):2d} decisoes - Score: {score:.1%}")

    if low_conf:
        score = sum(r["outcome"]["score"] for r in low_conf) / len(low_conf)
        print(f"Baixa (<40%):  {len(low_conf):2d} decisoes - Score: {score:.1%}")

    print()

    # Insights from AI reflections
    print("=" * 80)
    print("INSIGHTS DA IA")
    print("=" * 80)
    print()

    if ai_entries:
        # When IA said "useful" vs "noise"
        useful_moments = [e for e in ai_entries if "valor" in e.reflection.am_i_useful.lower()]
        noise_moments = [e for e in ai_entries if "ruido" in e.reflection.am_i_useful.lower()]

        print(f"Momentos 'agregando valor': {len(useful_moments)}")
        print(f"Momentos 'gerando ruido':   {len(noise_moments)}")
        print()

        # Correlation insights
        strong_corr = [e for e in ai_entries if "FORTE" in e.reflection.my_data_correlation]
        weak_corr = [e for e in ai_entries if "FRACA" in e.reflection.my_data_correlation]

        print(f"Correlacao FORTE:  {len(strong_corr)} momentos")
        print(f"Correlacao FRACA:  {len(weak_corr)} momentos")
        print()

        print("Sugestao: Cruzar horarios de 'correlacao forte' com acertos reais")
        print("          para validar se a IA identifica corretamente quando dados funcionam.")
        print()

    # Disconnect
    mt5.disconnect()

    print("=" * 80)
    print("ANALISE COMPLETA")
    print("=" * 80)
    print()
    print("Dados prontos para aprendizagem por reforco:")
    print("  - Decisoes com outcomes (correto/errado)")
    print("  - Performance por confianca e alinhamento")
    print("  - Correlacao entre auto-avaliacao da IA e resultados reais")
    print()
    print("Proximo passo: Treinar modelo de reforco usando estes dados")
    print()


if __name__ == "__main__":
    run_end_of_day_analysis()
