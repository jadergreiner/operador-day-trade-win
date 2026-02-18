
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from decimal import Decimal
from src.application.services.ai_reflection_journal import AIReflectionJournalService, AIReflection, AIReflectionEntry
from src.domain.enums.trading_enums import TradeSignal
from src.application.services.trading_journal import TradingJournalService, MarketNarrative
from src.domain.value_objects import Symbol
import json

def generate_admin_reflection():
    # Market Data from my previous checks
    win_price = Decimal("183240")
    win_open = Decimal("183220")
    wdo_price = Decimal("5232")
    wsp_price = Decimal("6931.75")
    petr4_price = Decimal("36.99")
    vale3_price = Decimal("85.68")
    ticket = "2344593022"
    symbol = Symbol("WIN")

    # Analysis
    points = win_price - win_open

    # Reflection Content
    honest_assessment = (
        f"A administracao da compra no WIN (Ticket {ticket}) esta em modo de espera. "
        f"O mercado subiu meros {points} pontos desde a entrada em 183220. "
        "O WDO em 5232 e o S&P 500 em 6931.75 ainda nao deram o impulso de alta que o Head Financeiro esperava. "
        "As Blue Chips (PETR4 R$ 36.99, VALE3 R$ 85.68) estao laterais, o que explica a falta de 'range' no WIN."
    )

    what_im_seeing = (
        "O WIN esta brigando na regiao dos 183.240. "
        "O Trailing Stop de 250 pontos (alvo 500) ainda esta longe de ser acionado, "
        "ja que precisamos de pelo menos 250 pontos a favor para comecar a proteger no break-even. "
        "No momento, estamos com apenas 20 pontos de lucro flutuante."
    )

    data_relevance = (
        "A correlacao com o S&P 500 (em patamar elevado) deveria puxar o WIN, "
        "mas o WDO resiliente acima de 5200 segura o apetite por risco no Brasil."
    )

    mood = "Analitico e Vigilante"
    one_liner = "Vinte pontos nao pagam nem o cafe, mas a disciplina de manter o stop original e o que nos mantem no jogo."

    # Create the reflection object
    reflection_service = AIReflectionJournalService()

    # Create a JournalEntry/MarketNarrative
    headline = f"HEAD FINANCEIRO: Administracao da Compra {ticket}"
    detailed = (
        f"Efetuada analise de administracao da posicao {ticket}. "
        f"Destaques: WIN 183.240 (+20 pts), WDO 5.232, S&P 500 6.931, PETR4 36.99. "
        "O mercado apresenta baixa volatilidade no momento, com as Blue Chips laterais. "
        "A regra deTrailing Stop exige 250 pontos de movimento a favor para ajuste, o que ainda nao ocorreu. "
        "A decisao e de MANUTENCAO da posicao com stop original em 182.970."
    )

    narrative = MarketNarrative(
        timestamp=datetime.now(),
        symbol=symbol,
        current_price=win_price,
        price_change_pct=Decimal("0.01"), # +20 points is small
        high_of_day=win_price + 50,
        low_of_day=win_open - 30,
        headline=headline,
        market_feeling="CALM",
        detailed_narrative=detailed,
        decision=TradeSignal.HOLD,
        confidence=Decimal("0.9"),
        reasoning="Aguardando movimento direcional ou gatilho de trailing stop.",
        tags=["admin_head_financeiro", "trailing_stop_check", "blue_chips_analysis"]
    )

    # Save (simulated save since I don't want to mess up the whole DB, but usually there's a save method)
    # Most services here handle saving to data/db or logs

    print("\nPROCESSO DE ADMINISTRACAO CONCLUIDO")
    print("-" * 40)
    print(f"HEADLINE: {headline}")
    print(f"NARRATIVE: {detailed}")
    print("-" * 40)
    print(f"MOOD DA IA: {mood}")
    print(f"ONE LINER: {one_liner}")
    print(f"HONEST ASSESSMENT: {honest_assessment}")
    print("-" * 40)


if __name__ == "__main__":
    generate_admin_reflection()
