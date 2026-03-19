"""Testes unitarios para TradeNarrativeCorrelator."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from src.application.trade_narrative_correlator import TradeNarrativeCorrelator


def _trade(
    trade_id: str | None,
    timestamp: datetime,
    *,
    side: str = "BUY",
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "trade_id": trade_id,
        "timestamp": timestamp,
        "side": side,
    }
    if extra:
        payload.update(extra)
    return payload


def _narrative(
    trade_id: str | None,
    timestamp: datetime,
    *,
    headline: str = "Mercado calmo",
    category: str = "trade",
    narrative: str = "Narrativa estruturada do pregão.",
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "trade_id": trade_id,
        "timestamp": timestamp,
        "headline": headline,
        "category": category,
        "narrative": narrative,
    }
    if extra:
        payload.update(extra)
    return payload


def test_correlate_matches_by_trade_id() -> None:
    correlator = TradeNarrativeCorrelator()
    trade_ts = datetime(2026, 3, 18, 10, 0, 0)
    narrative_ts = datetime(2026, 3, 18, 10, 5, 0)

    result = correlator.correlate(
        [_trade("T-001", trade_ts)],
        [_narrative("T-001", narrative_ts)],
    )

    assert result["total_trades"] == 1
    assert result["correlated_trades"] == 1
    assert result["direct_matches"] == 1
    assert result["temporal_matches"] == 0
    assert result["correlations"][0]["match_type"] == "trade_id"
    assert result["correlations"][0]["matched"] is True


def test_correlate_prefers_trade_id_over_temporal_distance() -> None:
    correlator = TradeNarrativeCorrelator()

    result = correlator.correlate(
        [_trade("T-001", datetime(2026, 3, 18, 10, 0, 0))],
        [
            _narrative("T-001", datetime(2026, 3, 18, 11, 0, 0), headline="ID"),
            _narrative("T-999", datetime(2026, 3, 18, 10, 1, 0), headline="Temporal"),
        ],
    )

    assert result["correlations"][0]["match_type"] == "trade_id"
    assert result["correlations"][0]["narrative_headline"] == "ID"


def test_correlate_uses_temporal_fallback_without_trade_id() -> None:
    correlator = TradeNarrativeCorrelator(temporal_window_minutes=15)

    result = correlator.correlate(
        [_trade(None, datetime(2026, 3, 18, 10, 0, 0))],
        [_narrative(None, datetime(2026, 3, 18, 10, 8, 0), headline="Fallback")],
    )

    assert result["correlated_trades"] == 1
    assert result["temporal_matches"] == 1
    assert result["correlations"][0]["match_type"] == "temporal"
    assert result["correlations"][0]["narrative_headline"] == "Fallback"


def test_correlate_temporal_fallback_respects_window() -> None:
    correlator = TradeNarrativeCorrelator(temporal_window_minutes=5)

    result = correlator.correlate(
        [_trade(None, datetime(2026, 3, 18, 10, 0, 0))],
        [_narrative(None, datetime(2026, 3, 18, 10, 8, 0), headline="Too far")],
    )

    assert result["correlated_trades"] == 0
    assert result["unmatched_trades"] == 1
    assert result["correlations"][0]["match_type"] == "unmatched"
    assert result["correlations"][0]["matched"] is False


def test_correlate_returns_zero_metrics_for_empty_inputs() -> None:
    correlator = TradeNarrativeCorrelator()

    result = correlator.correlate([], [])

    assert result["total_trades"] == 0
    assert result["total_narratives"] == 0
    assert result["correlated_trades"] == 0
    assert result["correlation_rate"] == 0.0
    assert result["correlations"] == []


def test_correlate_handles_duplicate_trade_ids() -> None:
    correlator = TradeNarrativeCorrelator()

    result = correlator.correlate(
        [
            _trade("T-001", datetime(2026, 3, 18, 10, 0, 0)),
            _trade("T-001", datetime(2026, 3, 18, 10, 2, 0)),
        ],
        [_narrative("T-001", datetime(2026, 3, 18, 10, 1, 0))],
    )

    assert result["total_trades"] == 2
    assert result["correlated_trades"] == 2
    assert all(item["match_type"] == "trade_id" for item in result["correlations"])


def test_correlate_handles_duplicate_narratives_for_same_trade_id() -> None:
    correlator = TradeNarrativeCorrelator()

    result = correlator.correlate(
        [_trade("T-001", datetime(2026, 3, 18, 10, 0, 0))],
        [
            _narrative("T-001", datetime(2026, 3, 18, 10, 5, 0), headline="A"),
            _narrative("T-001", datetime(2026, 3, 18, 10, 1, 0), headline="B"),
        ],
    )

    assert result["correlated_trades"] == 1
    assert result["correlations"][0]["narrative_headline"] == "B"


def test_correlate_accepts_iso_string_timestamps() -> None:
    correlator = TradeNarrativeCorrelator()

    result = correlator.correlate(
        [{"trade_id": "T-001", "timestamp": "2026-03-18T10:00:00"}],
        [
            {
                "trade_id": "T-001",
                "timestamp": "2026-03-18T10:02:00",
                "headline": "ISO",
                "category": "trade",
                "narrative": "texto",
            }
        ],
    )

    assert result["correlations"][0]["trade_timestamp"] == "2026-03-18T10:00:00"
    assert result["correlations"][0]["narrative_timestamp"] == "2026-03-18T10:02:00"


def test_extract_features_builds_serializable_rows() -> None:
    correlator = TradeNarrativeCorrelator()
    result = correlator.correlate(
        [_trade("T-001", datetime(2026, 3, 18, 10, 0, 0))],
        [_narrative("T-001", datetime(2026, 3, 18, 10, 1, 0), headline="Headline")],
    )

    features = correlator.extract_features(result["correlations"])

    assert features[0]["trade_id"] == "T-001"
    assert features[0]["matched"] is True
    assert features[0]["headline_length"] == len("Headline")
    assert features[0]["narrative_length"] == len("Narrativa estruturada do pregão.")


def test_extract_features_handles_unmatched_row() -> None:
    correlator = TradeNarrativeCorrelator()
    features = correlator.extract_features(
        [
            {
                "trade_id": "T-001",
                "matched": False,
                "match_type": "unmatched",
                "time_delta_minutes": None,
                "narrative_headline": None,
                "narrative_category": None,
                "narrative_text": None,
                "narrative_trade_id": None,
            }
        ]
    )

    assert features[0]["matched"] is False
    assert features[0]["narrative_length"] == 0
    assert features[0]["headline_length"] == 0


def test_correlate_result_is_json_serializable() -> None:
    correlator = TradeNarrativeCorrelator()

    result = correlator.correlate(
        [_trade("T-001", datetime(2026, 3, 18, 10, 0, 0))],
        [_narrative("T-001", datetime(2026, 3, 18, 10, 1, 0))],
    )

    encoded = json.dumps(result, ensure_ascii=False)

    assert "\"total_trades\": 1" in encoded
    assert "\"match_type\": \"trade_id\"" in encoded


def test_correlator_rejects_negative_window() -> None:
    with pytest.raises(ValueError, match="nao pode ser negativo"):
        TradeNarrativeCorrelator(temporal_window_minutes=-1)
