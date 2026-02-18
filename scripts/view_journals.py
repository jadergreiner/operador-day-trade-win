"""
View Journals - Visualiza diarios gerados hoje.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from src.application.services.trading_journal import TradingJournalService
from src.application.services.ai_reflection_journal import AIReflectionJournalService


def display_trading_journal():
    """Display trading journal entries."""

    journal = TradingJournalService()
    entries = journal.get_today_entries()

    print("=" * 80)
    print("DIARIO DE TRADING - STORYTELLING")
    print("=" * 80)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y')}")
    print(f"Total de Entradas: {len(entries)}")
    print()

    if not entries:
        print("Nenhuma entrada registrada hoje.")
        print()
        print("Os diarios sao gerados automaticamente:")
        print("  - Trading Storytelling: A cada 15 minutos")
        print("  - AI Reflection: A cada 10 minutos")
        print()
        print("Para iniciar: python scripts/start_journals_full_display.py")
        print()
        return

    for i, entry in enumerate(entries, 1):
        print("-" * 80)
        print(f"ENTRADA #{i} - {entry.time}")
        print("-" * 80)
        print()
        print(f"MANCHETE:")
        print(f"  {entry.narrative.headline}")
        print()
        print(f"SENTIMENTO: {entry.narrative.market_feeling}")
        print()
        print("NARRATIVA:")
        print(entry.narrative.detailed_narrative)
        print()
        print("CONTEXTO:")
        print(f"  Macro: {entry.macro_bias} | Fundamentos: {entry.fundamental_bias}")
        print(f"  Sentimento: {entry.sentiment_bias} | Tecnica: {entry.technical_bias}")
        print(f"  Alinhamento: {entry.alignment_score:.0%}")
        print()
        print(f"DECISAO: {entry.narrative.decision.value} ({entry.confidence:.0%} confianca)")
        print(f"Razao: {entry.reasoning}")
        print()
        print(f"Tags: {', '.join(entry.tags)}")
        print()


def display_ai_reflection():
    """Display AI reflection entries."""

    journal = AIReflectionJournalService()
    entries = journal.get_today_entries()

    print("=" * 80)
    print("DIARIO DE REFLEXAO DA IA")
    print("=" * 80)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y')}")
    print(f"Total de Reflexoes: {len(entries)}")
    print()

    if not entries:
        print("Nenhuma reflexao registrada hoje.")
        print()
        return

    for i, entry in enumerate(entries, 1):
        ref = entry.reflection

        print("-" * 80)
        print(f"REFLEXAO #{i} - {entry.time}")
        print("-" * 80)
        print()
        print(f"Humor: {ref.mood}")
        print(f"Frase: {ref.one_liner}")
        print()
        print("AVALIACAO HONESTA:")
        print(ref.honest_assessment)
        print()
        print("O QUE ESTOU VENDO:")
        print(ref.what_im_seeing)
        print()
        print("RELEVANCIA DOS DADOS:")
        print(ref.data_relevance)
        print()
        print("SOU UTIL?")
        print(ref.am_i_useful)
        print()
        print("O QUE FUNCIONARIA MELHOR:")
        print(ref.what_would_work_better)
        print()
        print("AVALIACAO DO HUMANO:")
        print(f"  Faz Sentido: {'SIM' if ref.human_makes_sense else 'NAO'}")
        print(f"  Feedback: {ref.human_feedback}")
        print()
        print("O QUE MOVE O PRECO:")
        print(ref.what_actually_moves_price)
        print()
        print("CORRELACAO DOS DADOS:")
        print(ref.my_data_correlation)
        print()


def main():
    """Display all journals."""

    print()
    print("=" * 80)
    print("DIARIOS DO OPERADOR QUANTICO")
    print("=" * 80)
    print()

    # Trading Storytelling Journal
    display_trading_journal()

    print()

    # AI Reflection Journal
    display_ai_reflection()

    print()
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
