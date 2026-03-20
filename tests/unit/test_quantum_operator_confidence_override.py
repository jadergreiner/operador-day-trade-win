from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from src.application.services.quantum_operator import QuantumOperatorEngine
from src.domain.value_objects.financial import Symbol


def _fake_candles() -> list[SimpleNamespace]:
    candle = SimpleNamespace(
        high=SimpleNamespace(value=100.0),
        low=SimpleNamespace(value=99.0),
        close=SimpleNamespace(value=99.8),
    )
    return [candle for _ in range(20)]


def _build_engine(confidence_override_path: Path) -> QuantumOperatorEngine:
    engine = QuantumOperatorEngine(confidence_override_path=confidence_override_path)

    engine.macro_service = SimpleNamespace(
        analyze_current_macro_conditions=lambda **kwargs: SimpleNamespace(
            impact_on_brazil="NEUTRAL",
            key_points=[],
        ),
        get_trading_bias_from_macro=lambda: "BEARISH",
    )
    engine.fundamental_service = SimpleNamespace(
        analyze_brazil_fundamentals=lambda **kwargs: SimpleNamespace(
            brazil_risk_rating=SimpleNamespace(value="LOW"),
            capital_flow=SimpleNamespace(value="NEUTRAL"),
            key_factors=[],
        ),
        get_trading_bias_from_fundamentals=lambda: "BEARISH",
    )
    engine.sentiment_service = SimpleNamespace(
        analyze_market_sentiment=lambda **kwargs: SimpleNamespace(
            volatility="LOW",
            market_condition=SimpleNamespace(value="RANGING"),
            key_signals=[],
        ),
        get_trading_bias_from_sentiment=lambda: "BULLISH",
    )
    engine.technical_service = SimpleNamespace(
        analyze_technical=lambda **kwargs: SimpleNamespace(
            best_entry=SimpleNamespace(reason="setup valido", risk_reward_ratio=1.8),
            technical_bias="BULLISH",
            trend_strength=SimpleNamespace(value="WEAK"),
        )
    )

    return engine


def test_quantum_operator_usa_threshold_padrao_sem_override(tmp_path: Path) -> None:
    engine = _build_engine(tmp_path / "missing_override.json")

    decision = engine.analyze_and_decide(
        symbol=Symbol("WIN$N"),
        candles=_fake_candles(),
        dollar_index=Decimal("100"),
        vix=Decimal("20"),
        selic=Decimal("10.5"),
        ipca=Decimal("4.0"),
        usd_brl=Decimal("5.10"),
        embi_spread=250,
    )

    assert decision.action.value == "BUY"
    assert decision.confidence == Decimal("0.77")


def test_quantum_operator_respeita_confidence_diaria(tmp_path: Path) -> None:
    override_path = tmp_path / "confidence_override_today.json"
    override_path.write_text(
        '{"confidence_current": 0.32}',
        encoding="utf-8",
    )
    engine = _build_engine(override_path)

    decision = engine.analyze_and_decide(
        symbol=Symbol("WIN$N"),
        candles=_fake_candles(),
        dollar_index=Decimal("100"),
        vix=Decimal("20"),
        selic=Decimal("10.5"),
        ipca=Decimal("4.0"),
        usd_brl=Decimal("5.10"),
        embi_spread=250,
    )

    assert decision.action.value == "BUY"
    assert decision.confidence == Decimal("0.71")
    assert decision.urgency == "OPPORTUNISTIC"
    assert "DAILY GATE" in decision.executive_summary
    assert "35%" in decision.executive_summary
    assert "32%" in decision.executive_summary


def test_quantum_operator_logs_daily_gate(tmp_path: Path, caplog) -> None:
    override_path = tmp_path / "confidence_override_today.json"
    override_path.write_text('{"confidence_current": 0.32}', encoding="utf-8")
    engine = _build_engine(override_path)

    with caplog.at_level("INFO", logger="src.application.services.quantum_operator"):
        engine.analyze_and_decide(
            symbol=Symbol("WIN$N"),
            candles=_fake_candles(),
            dollar_index=Decimal("100"),
            vix=Decimal("20"),
            selic=Decimal("10.5"),
            ipca=Decimal("4.0"),
            usd_brl=Decimal("5.10"),
            embi_spread=250,
        )

    assert any("daily_gate=0.35" in record.message for record in caplog.records)
    assert any("override=0.32" in record.message for record in caplog.records)
