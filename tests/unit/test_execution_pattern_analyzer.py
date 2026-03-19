import pytest

from src.application.execution_pattern_analyzer import (
    ExecutionPatternAnalyzer,
    ExecutionPatternAnalysis,
)


def test_analyze_detects_multiple_patterns_and_serializes():
    analyzer = ExecutionPatternAnalyzer()
    events = [
        {
            "order_id": "ord-1",
            "requested_qty": 100,
            "filled_qty": 100,
            "requested_price": 100.0,
            "filled_price": 100.2,
            "latency_ms": 120,
            "side": "BUY",
            "status": "FILLED",
        },
        {
            "order_id": "ord-2",
            "requested_qty": 100,
            "filled_qty": 70,
            "requested_price": 100.0,
            "filled_price": 103.0,
            "latency_ms": 900,
            "side": "BUY",
            "status": "PARTIAL",
            "failure_reason": "timeout",
        },
    ]

    analysis = analyzer.analyze(events)

    assert isinstance(analysis, ExecutionPatternAnalysis)
    assert analysis.summary.event_count == 2
    assert analysis.summary.fill_rate == pytest.approx(0.85)
    assert analysis.summary.avg_slippage_points == pytest.approx(1.6)
    assert analysis.summary.avg_latency_ms == pytest.approx(510.0)
    assert analysis.summary.failure_reasons == {"timeout": 1}
    assert set(analysis.patterns_detected) == {
        "LOW_FILL_RATE",
        "HIGH_SLIPPAGE",
        "HIGH_LATENCY",
        "FAILURE_REASON_CLUSTER",
    }
    assert len(analysis.insights) == 4
    assert analysis.to_dict()["summary"]["event_count"] == 2


def test_analyze_empty_returns_zero_summary():
    analyzer = ExecutionPatternAnalyzer()

    analysis = analyzer.analyze([])

    assert analysis.summary.event_count == 0
    assert analysis.summary.fill_rate == 0.0
    assert analysis.insights == []
    assert analysis.patterns_detected == []


def test_analyze_rejects_invalid_values():
    analyzer = ExecutionPatternAnalyzer()

    with pytest.raises(ValueError):
        analyzer.analyze(
            [
                {
                    "order_id": "bad-1",
                    "requested_qty": 10,
                    "filled_qty": 10,
                    "latency_ms": -5,
                }
            ]
        )

    with pytest.raises(ValueError):
        analyzer.analyze(
            [
                {
                    "order_id": "bad-2",
                    "requested_qty": -10,
                    "filled_qty": 10,
                    "latency_ms": 5,
                }
            ]
        )


def test_analyze_flags_outliers_basic():
    analyzer = ExecutionPatternAnalyzer()
    events = [
        {
            "order_id": "ord-a",
            "requested_qty": 10,
            "filled_qty": 10,
            "requested_price": 100.0,
            "filled_price": 100.1,
            "latency_ms": 10,
            "side": "BUY",
            "status": "FILLED",
        },
        {
            "order_id": "ord-b",
            "requested_qty": 10,
            "filled_qty": 10,
            "requested_price": 100.0,
            "filled_price": 100.2,
            "latency_ms": 11,
            "side": "BUY",
            "status": "FILLED",
        },
        {
            "order_id": "ord-c",
            "requested_qty": 10,
            "filled_qty": 10,
            "requested_price": 100.0,
            "filled_price": 100.0,
            "latency_ms": 12,
            "side": "BUY",
            "status": "FILLED",
        },
        {
            "order_id": "ord-d",
            "requested_qty": 10,
            "filled_qty": 10,
            "requested_price": 100.0,
            "filled_price": 100.0,
            "latency_ms": 2500,
            "side": "BUY",
            "status": "FILLED",
        },
    ]

    analysis = analyzer.analyze(events)

    assert analysis.summary.outlier_count >= 1
    assert analysis.summary.p95_latency_ms > 1000.0
    assert any(insight.pattern == "OUTLIERS_PRESENT" for insight in analysis.insights)
