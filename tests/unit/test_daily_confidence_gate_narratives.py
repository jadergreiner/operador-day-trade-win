from __future__ import annotations

from decimal import Decimal

from src.application.services.ai_reflection_journal import AIReflectionJournalService
from src.application.services.trading_journal import TradingJournalService
from src.domain.enums.trading_enums import TradeSignal
from src.domain.value_objects.financial import Symbol


def test_trading_journal_inclui_gate_diario_na_narrativa() -> None:
    journal = TradingJournalService()

    narrative = journal.create_narrative(
        symbol=Symbol("WIN$N"),
        current_price=Decimal("180500"),
        opening_price=Decimal("180000"),
        high=Decimal("181200"),
        low=Decimal("179900"),
        decision_data={
            "action": TradeSignal.HOLD,
            "confidence": Decimal("0.71"),
            "primary_reason": "Setup com alinhamento bom",
            "sentiment_bias": "BULLISH",
        },
        daily_confidence_gate=Decimal("0.35"),
    )

    assert "Gate diario atual: 35%" in narrative.detailed_narrative
    assert "DECISAO: OBSERVAR." in narrative.detailed_narrative


def test_ai_reflection_inclui_gate_diario_na_autoavaliacao(monkeypatch) -> None:
    journal = AIReflectionJournalService()
    monkeypatch.setattr(journal, "_persist_to_disk", lambda reflection: None)
    monkeypatch.setattr("random.choice", lambda seq: seq[0])

    reflection = journal.generate_reflection(
        current_price=Decimal("180500"),
        opening_price=Decimal("180000"),
        price_10min_ago=Decimal("180200"),
        my_decision=TradeSignal.BUY,
        my_confidence=Decimal("0.18"),
        my_alignment=Decimal("0.63"),
        macro_moved=False,
        sentiment_changed=True,
        technical_triggered=True,
        human_last_action="observando",
        daily_confidence_gate=Decimal("0.35"),
    )

    assert reflection.honest_assessment.startswith("Gate diario atual: 35%.")
    assert "sinais firmes" in reflection.honest_assessment
