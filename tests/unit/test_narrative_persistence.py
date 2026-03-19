"""Testes unitarios para NarrativePersistence."""

from __future__ import annotations

from datetime import datetime

import pytest

from src.application.narrative_persistence import NarrativePersistence, NarrativeRecord


def _sample_record(
    trade_id: str = "T-001",
    timestamp: datetime | None = None,
    category: str = "session",
    headline: str = "Mercado calmo",
    narrative: str = "Narrativa estruturada do pregão.",
) -> NarrativeRecord:
    return NarrativeRecord(
        trade_id=trade_id,
        timestamp=timestamp or datetime(2026, 3, 18, 10, 30, 0),
        headline=headline,
        narrative=narrative,
        category=category,
        session_id="S-001",
        outcome="neutral",
        tags=["calmo", "observacao"],
        context={"symbol": "WIN", "confidence": 0.75},
    )


def test_save_narrative_returns_record_and_serializable_dict() -> None:
    persistence = NarrativePersistence()
    record = persistence.save_narrative(_sample_record())

    payload = record.to_dict()

    assert payload["trade_id"] == "T-001"
    assert payload["timestamp"] == "2026-03-18T10:30:00"
    assert payload["headline"] == "Mercado calmo"
    assert payload["context"]["symbol"] == "WIN"


def test_save_narrative_from_dict_is_accepted() -> None:
    persistence = NarrativePersistence()

    record = persistence.save_narrative(
        {
            "trade_id": "T-002",
            "timestamp": datetime(2026, 3, 18, 11, 0, 0),
            "headline": "Venda com pressao",
            "narrative": "Narrativa de venda com forte fluxo.",
            "category": "trade",
            "tags": ["sell", "fluxo"],
            "context": {"direction": "SELL"},
        }
    )

    assert record.trade_id == "T-002"
    assert record.category == "trade"
    assert record.tags == ["sell", "fluxo"]


def test_list_by_trade_id_filters_records() -> None:
    persistence = NarrativePersistence()
    persistence.save_narrative(_sample_record(trade_id="T-001", category="trade"))
    persistence.save_narrative(_sample_record(trade_id="T-002", category="trade"))
    persistence.save_narrative(_sample_record(trade_id="T-001", category="reflection"))

    records = persistence.list_by_trade_id("T-001")

    assert len(records) == 2
    assert all(record["trade_id"] == "T-001" for record in records)


def test_list_by_trade_id_returns_empty_list_when_missing() -> None:
    persistence = NarrativePersistence()
    persistence.save_narrative(_sample_record(trade_id="T-001"))

    records = persistence.list_by_trade_id("T-999")

    assert records == []


def test_get_latest_narrative_returns_most_recent_record() -> None:
    persistence = NarrativePersistence()
    persistence.save_narrative(
        _sample_record(trade_id="T-001", timestamp=datetime(2026, 3, 18, 9, 0, 0))
    )
    persistence.save_narrative(
        _sample_record(trade_id="T-002", timestamp=datetime(2026, 3, 18, 12, 0, 0))
    )

    latest = persistence.get_latest_narrative()

    assert latest is not None
    assert latest["trade_id"] == "T-002"
    assert latest["timestamp"] == "2026-03-18T12:00:00"


def test_get_latest_narrative_returns_none_when_empty() -> None:
    persistence = NarrativePersistence()

    assert persistence.get_latest_narrative() is None


def test_get_metrics_for_empty_store() -> None:
    persistence = NarrativePersistence()

    metrics = persistence.get_metrics()

    assert metrics["total_records"] == 0
    assert metrics["total_trade_ids"] == 0
    assert metrics["categories"] == []
    assert metrics["has_records"] is False
    assert metrics["latest_timestamp"] is None


def test_get_metrics_reports_basic_counts() -> None:
    persistence = NarrativePersistence()
    persistence.save_narrative(_sample_record(trade_id="T-001", category="trade"))
    persistence.save_narrative(_sample_record(trade_id="T-002", category="reflection"))
    persistence.save_narrative(
        _sample_record(
            trade_id="T-001",
            category="trade",
            timestamp=datetime(2026, 3, 18, 13, 0, 0),
        )
    )

    metrics = persistence.get_metrics()

    assert metrics["total_records"] == 3
    assert metrics["total_trade_ids"] == 2
    assert metrics["categories"] == ["reflection", "trade"]
    assert metrics["has_records"] is True
    assert metrics["latest_timestamp"] == "2026-03-18T13:00:00"


def test_list_all_is_sorted_by_timestamp() -> None:
    persistence = NarrativePersistence()
    persistence.save_narrative(
        _sample_record(trade_id="T-002", timestamp=datetime(2026, 3, 18, 12, 0, 0))
    )
    persistence.save_narrative(
        _sample_record(trade_id="T-001", timestamp=datetime(2026, 3, 18, 9, 0, 0))
    )

    records = persistence.list_all()

    assert [record["trade_id"] for record in records] == ["T-001", "T-002"]


def test_clear_removes_all_records() -> None:
    persistence = NarrativePersistence()
    persistence.save_narrative(_sample_record())

    persistence.clear()

    assert persistence.list_all() == []
    assert persistence.get_metrics()["total_records"] == 0


def test_save_narrative_validates_required_fields() -> None:
    persistence = NarrativePersistence()

    with pytest.raises(ValueError, match="Campos obrigatorios ausentes"):
        persistence.save_narrative({"trade_id": "T-001"})


def test_save_narrative_rejects_invalid_timestamp_type() -> None:
    persistence = NarrativePersistence()

    with pytest.raises(TypeError, match="timestamp deve ser uma instancia"):
        persistence.save_narrative(
            {
                "trade_id": "T-001",
                "timestamp": "2026-03-18T10:30:00",
                "headline": "headline",
                "narrative": "narrative",
                "category": "trade",
            }
        )
