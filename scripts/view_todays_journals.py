"""
View Today's Journals - Visualiza resumo dos diarios de hoje.

Mostra todas as entradas criadas hoje nos dois diarios.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from src.application.services.trading_journal import TradingJournalService
from src.application.services.ai_reflection_journal import AIReflectionJournalService


def display_trading_summary(journal: TradingJournalService):
    """Display trading journal summary."""

    entries = journal.get_today_entries()

    if not entries:
        print("Nenhuma entrada de trading hoje.")
        return

    print("=" * 80)
    print(f"DIARIO DE TRADING - {len(entries)} ENTRADAS HOJE")
    print("=" * 80)
    print()

    # Summary stats
    decisions = {"BUY": 0, "SELL": 0, "HOLD": 0}
    sentiments = {}
    total_confidence = 0

    for entry in entries:
        decisions[entry.narrative.decision.value] = decisions.get(entry.narrative.decision.value, 0) + 1
        sentiment = entry.narrative.market_feeling
        sentiments[sentiment] = sentiments.get(sentiment, 0) + 1
        total_confidence += entry.confidence

    avg_confidence = total_confidence / len(entries) if entries else 0

    print("ESTATISTICAS:")
    print(f"  Total de Entradas:  {len(entries)}")
    print(f"  Confianca Media:    {avg_confidence:.0%}")
    print()
    print("DECISOES:")
    for decision, count in decisions.items():
        pct = (count / len(entries) * 100) if entries else 0
        print(f"  {decision:4s}: {count:2d} ({pct:.0f}%)")
    print()
    print("SENTIMENTOS:")
    for sentiment, count in sorted(sentiments.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(entries) * 100) if entries else 0
        print(f"  {sentiment:10s}: {count:2d} ({pct:.0f}%)")
    print()

    print("-" * 80)
    print("TIMELINE DE ENTRADAS")
    print("-" * 80)
    for entry in entries:
        print(f"[{entry.time}] {entry.narrative.decision.value:4s} {entry.confidence:3.0%} - {entry.narrative.market_feeling:10s}")
        print(f"           {entry.narrative.headline[:65]}")
        print()


def display_ai_reflection_summary(journal: AIReflectionJournalService):
    """Display AI reflection summary."""

    entries = journal.get_today_entries()

    if not entries:
        print("Nenhuma reflexao da IA hoje.")
        return

    print("=" * 80)
    print(f"DIARIO DE REFLEXAO DA IA - {len(entries)} REFLEXOES HOJE")
    print("=" * 80)
    print()

    # Summary stats
    moods = {}
    correlations = {"FORTE": 0, "MODERADA": 0, "FRACA": 0, "INVERSA": 0}
    usefulness_low = 0
    usefulness_medium = 0
    usefulness_high = 0

    for entry in entries:
        mood = entry.reflection.mood
        moods[mood] = moods.get(mood, 0) + 1

        # Parse correlation
        corr = entry.reflection.my_data_correlation.split(" ")[0]
        if corr in correlations:
            correlations[corr] += 1

        # Parse usefulness
        useful = entry.reflection.am_i_useful.lower()
        if "ruido" in useful or "nao" in useful:
            usefulness_low += 1
        elif "valor" in useful or "agregando" in useful:
            usefulness_high += 1
        else:
            usefulness_medium += 1

    print("ESTATISTICAS:")
    print(f"  Total de Reflexoes: {len(entries)}")
    print()
    print("HUMORES DA IA:")
    for mood, count in sorted(moods.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(entries) * 100) if entries else 0
        print(f"  {mood:12s}: {count:2d} ({pct:.0f}%)")
    print()
    print("CORRELACAO DADOS x PRECO:")
    for corr, count in correlations.items():
        if count > 0:
            pct = (count / len(entries) * 100) if entries else 0
            print(f"  {corr:10s}: {count:2d} ({pct:.0f}%)")
    print()
    print("AUTO-AVALIACAO DE UTILIDADE:")
    print(f"  Alta:   {usefulness_high:2d} ({usefulness_high/len(entries)*100:.0f}%) - 'Agregando valor'")
    print(f"  Media:  {usefulness_medium:2d} ({usefulness_medium/len(entries)*100:.0f}%) - 'Zona cinza'")
    print(f"  Baixa:  {usefulness_low:2d} ({usefulness_low/len(entries)*100:.0f}%) - 'Gerando ruido'")
    print()

    print("-" * 80)
    print("FRASES MAIS RECENTES")
    print("-" * 80)
    for entry in entries[-10:]:  # Last 10
        print(f"[{entry.time}] {entry.reflection.mood:12s} - {entry.reflection.one_liner}")
    print()


def main():
    """Main entry point."""

    print()
    print("=" * 80)
    print("RESUMO DOS DIARIOS DE HOJE")
    print("=" * 80)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y')}")
    print(f"Hora: {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Load journals
    trading_journal = TradingJournalService()
    ai_journal = AIReflectionJournalService()

    # Display summaries
    display_trading_summary(trading_journal)
    print()
    display_ai_reflection_summary(ai_journal)

    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
