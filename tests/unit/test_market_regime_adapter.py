"""Testes unitarios para `src.application.market_regime_adapter`."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from src.application.market_regime_adapter import (
    MarketRegime,
    MarketRegimeAdapter,
    MarketRegimeRecommendation,
)


def test_classifies_trending_up_from_dict_input() -> None:
    adapter = MarketRegimeAdapter()

    recommendation = adapter.recommend(
        {
            "trend_strength": 82.0,
            "directional_bias": 64.0,
            "adx": 34.0,
            "volatility": 24.0,
            "atr_percent": 1.4,
            "range_compression": 18.0,
        }
    )

    assert recommendation.regime == MarketRegime.TRENDING_UP
    assert 0.0 <= recommendation.confidence <= 1.0
    assert recommendation.confidence > 0.5
    assert 0.0 < recommendation.risk_multiplier <= 1.08
    assert recommendation.position_size_multiplier > 1.0
    assert any("tendencia" in reason.lower() for reason in recommendation.reasons)


def test_classifies_trending_down_from_object_input() -> None:
    adapter = MarketRegimeAdapter()
    source = SimpleNamespace(
        trend_strength=-78.0,
        directional_bias=-62.0,
        adx=31.0,
        volatility=20.0,
        atr_percent=1.1,
        range_compression=20.0,
    )

    recommendation = adapter.analyze(source)

    assert recommendation.regime == MarketRegime.TRENDING_DOWN
    assert 0.0 <= recommendation.confidence <= 1.0
    assert recommendation.confidence > 0.5
    assert 0.0 < recommendation.risk_multiplier <= 1.08
    assert recommendation.position_size_multiplier > 1.0
    assert any("baixa" in reason.lower() for reason in recommendation.reasons)


def test_classifies_ranging_when_compression_dominates() -> None:
    adapter = MarketRegimeAdapter()

    recommendation = adapter.recommend(
        {
            "trend_strength": 12.0,
            "directional_bias": 4.0,
            "adx": 15.0,
            "volatility": 18.0,
            "atr_percent": 0.8,
            "range_compression": 84.0,
        }
    )

    assert recommendation.regime == MarketRegime.RANGING
    assert 0.0 <= recommendation.confidence <= 1.0
    assert recommendation.risk_multiplier < 1.0
    assert recommendation.position_size_multiplier < 1.0
    assert any("lateral" in reason.lower() for reason in recommendation.reasons)


def test_classifies_high_volatility_when_volatility_is_dominant() -> None:
    adapter = MarketRegimeAdapter()

    recommendation = adapter.recommend(
        {
            "trend_strength": 18.0,
            "directional_bias": 7.0,
            "adx": 19.0,
            "volatility": 88.0,
            "atr_percent": 5.4,
            "range_compression": 24.0,
        }
    )

    assert recommendation.regime == MarketRegime.HIGH_VOLATILITY
    assert 0.0 <= recommendation.confidence <= 1.0
    assert recommendation.risk_multiplier > 1.0
    assert recommendation.position_size_multiplier > 0.0
    assert recommendation.position_size_multiplier < 1.0
    assert any("volatilidade" in reason.lower() for reason in recommendation.reasons)


def test_empty_input_returns_neutral_fallback() -> None:
    adapter = MarketRegimeAdapter()

    recommendation = adapter.recommend({})

    assert recommendation.regime == MarketRegime.RANGING
    assert recommendation.confidence == pytest.approx(0.15)
    assert recommendation.risk_multiplier == pytest.approx(1.0)
    assert recommendation.position_size_multiplier == pytest.approx(1.0)
    assert recommendation.reasons == [
        "Entrada insuficiente para classificar regime com confianca."
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"trend_strength": float("nan")},
        {"volatility": "abc"},
        {"adx": float("nan")},
    ],
)
def test_invalid_numeric_values_raise_value_error(payload: dict[str, object]) -> None:
    adapter = MarketRegimeAdapter()

    with pytest.raises(ValueError):
        adapter.recommend(payload)


def test_confidence_and_multipliers_are_bounded() -> None:
    adapter = MarketRegimeAdapter()

    recommendation = adapter.recommend(
        {
            "trend_strength": 98.0,
            "directional_bias": 96.0,
            "adx": 48.0,
            "volatility": 12.0,
            "atr_percent": 0.9,
            "range_compression": 8.0,
        }
    )

    assert 0.0 <= recommendation.confidence <= 1.0
    assert recommendation.risk_multiplier > 0.0
    assert recommendation.position_size_multiplier > 0.0
    assert recommendation.risk_multiplier <= 1.85
    assert recommendation.position_size_multiplier <= 1.35


def test_to_dict_is_serializable_and_uses_enum_values() -> None:
    recommendation = MarketRegimeRecommendation(
        regime=MarketRegime.TRENDING_UP,
        confidence=0.8765,
        risk_multiplier=0.9345,
        position_size_multiplier=1.2345,
        reasons=["Teste de serializacao."],
        signals={"recognized_metrics": 6.0, "trend_up_score": 90.0},
    )

    payload = recommendation.to_dict()
    encoded = json.dumps(payload, ensure_ascii=False)

    assert payload["regime"] == MarketRegime.TRENDING_UP.value
    assert payload["confidence"] == 0.8765
    assert payload["signals"]["trend_up_score"] == 90.0
    assert "\"regime\": \"TRENDING_UP\"" in encoded


def test_alias_para_dict_matches_to_dict() -> None:
    recommendation = MarketRegimeRecommendation(
        regime=MarketRegime.RANGING,
        confidence=0.25,
        risk_multiplier=1.0,
        position_size_multiplier=1.0,
        reasons=["Fallback neutro."],
        signals={"recognized_metrics": 0.0},
    )

    assert recommendation.para_dict() == recommendation.to_dict()
