import pytest

from src.application.execution_pattern_analyzer import ExecutionPatternAnalyzer
from src.application.order_manager_learner import (
    ExecutionAdjustmentRecommendation,
    OrderManagerLearner,
)


def test_recommend_conservative_when_execution_is_poor():
    analyzer = ExecutionPatternAnalyzer()
    learner = OrderManagerLearner()

    history = [
        {
            "quality_score": 34.0,
            "fill_rate": 0.70,
            "latency_ms": 900.0,
            "slippage_points": 4.0,
            "failure_reason": "timeout",
            "status": "REJECTED",
            "outcome": "LOSS",
        },
        {
            "quality_score": 42.0,
            "fill_rate": 0.80,
            "latency_ms": 650.0,
            "slippage_points": 3.2,
            "failure_reason": "liquidity",
            "status": "PARTIAL",
            "outcome": "LOSS",
        },
    ]
    patterns = analyzer.analyze(
        [
            {
                "order_id": "o1",
                "requested_qty": 10,
                "filled_qty": 6,
                "requested_price": 100.0,
                "filled_price": 104.0,
                "latency_ms": 900.0,
                "side": "BUY",
                "status": "PARTIAL",
                "failure_reason": "timeout",
            },
            {
                "order_id": "o2",
                "requested_qty": 10,
                "filled_qty": 7,
                "requested_price": 100.0,
                "filled_price": 103.5,
                "latency_ms": 650.0,
                "side": "BUY",
                "status": "REJECTED",
                "failure_reason": "liquidity",
            },
        ]
    )

    recommendation = learner.recommend(history, patterns)

    assert isinstance(recommendation, ExecutionAdjustmentRecommendation)
    assert recommendation.mode == "CONSERVATIVE"
    assert recommendation.sl_multiplier > 1.0
    assert recommendation.tp_multiplier < 1.0
    assert recommendation.confidence > 0.0
    assert any("slippage" in reason.lower() for reason in recommendation.reasons)
    assert recommendation.to_dict()["mode"] == "CONSERVATIVE"


def test_recommend_aggressive_when_execution_is_very_good():
    learner = OrderManagerLearner()
    history = [
        {
            "quality_score": 90.0,
            "fill_rate": 1.0,
            "latency_ms": 70.0,
            "slippage_points": 0.3,
            "status": "FILLED",
            "outcome": "WIN",
        },
        {
            "quality_score": 88.0,
            "fill_rate": 0.98,
            "latency_ms": 90.0,
            "slippage_points": 0.2,
            "status": "FILLED",
            "outcome": "WIN",
        },
        {
            "quality_score": 84.0,
            "fill_rate": 0.99,
            "latency_ms": 80.0,
            "slippage_points": 0.1,
            "status": "FILLED",
            "outcome": "BREAKEVEN",
        },
    ]

    recommendation = learner.recommend_adjustments(history)

    assert recommendation.mode == "AGGRESSIVE"
    assert recommendation.sl_multiplier < 1.0
    assert recommendation.tp_multiplier >= 1.0
    assert recommendation.confidence > 0.5
    assert recommendation.signals["avg_quality"] > 80.0


def test_recommend_empty_history_returns_balanced_neutral():
    learner = OrderManagerLearner()

    recommendation = learner.recommend([], None)

    assert recommendation.mode == "BALANCED"
    assert recommendation.confidence == 0.0
    assert recommendation.sl_multiplier == pytest.approx(1.0)
    assert recommendation.tp_multiplier == pytest.approx(1.0)
    assert recommendation.reasons == ["Historico vazio, mantendo configuracao neutra."]


def test_recommend_rejects_invalid_history_values():
    learner = OrderManagerLearner()

    with pytest.raises(ValueError):
        learner.recommend(
            [
                {
                    "quality_score": 10.0,
                    "fill_rate": 0.5,
                    "latency_ms": -1.0,
                    "slippage_points": 2.0,
                }
            ]
        )
