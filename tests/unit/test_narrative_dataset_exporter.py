"""Testes unitarios para narrative_dataset_exporter."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from src.application.narrative_dataset_exporter import build_dataset, to_json_payload


def _sample_record(
    trade_id: str = "T-001",
    timestamp: datetime | str = datetime(2026, 3, 18, 10, 30, 0),
    category: str = "trade",
    outcome: str | None = "win",
) -> dict[str, object]:
    return {
        "trade_id": trade_id,
        "timestamp": timestamp,
        "headline": "Narrativa do pregao",
        "narrative": "Evento estruturado de mercado.",
        "category": category,
        "session_id": "S-001",
        "outcome": outcome,
        "tags": ["win", "trend"],
        "context": {"symbol": "WIN", "score": 0.87},
    }


def test_build_dataset_with_empty_list_returns_zero_stats() -> None:
    dataset = build_dataset([])

    assert dataset["total_records"] == 0
    assert dataset["records"] == []
    assert dataset["statistics"]["by_category"] == {}
    assert dataset["statistics"]["by_outcome"] == {}
    assert dataset["statistics"]["unique_trade_ids"] == 0


def test_build_dataset_normalizes_datetime_fields() -> None:
    dataset = build_dataset([_sample_record()])

    record = dataset["records"][0]

    assert record["trade_id"] == "T-001"
    assert record["timestamp"] == "2026-03-18T10:30:00"
    assert record["headline"] == "Narrativa do pregao"
    assert record["tags"] == ["win", "trend"]
    assert record["context"] == {"symbol": "WIN", "score": 0.87}


def test_build_dataset_accepts_iso_timestamp_string() -> None:
    dataset = build_dataset([
        _sample_record(timestamp="2026-03-18T11:15:00", trade_id="T-002")
    ])

    assert dataset["records"][0]["timestamp"] == "2026-03-18T11:15:00"


def test_build_dataset_counts_categories_and_outcomes() -> None:
    dataset = build_dataset(
        [
            _sample_record(trade_id="T-001", category="trade", outcome="win"),
            _sample_record(trade_id="T-002", category="trade", outcome="loss"),
            _sample_record(trade_id="T-003", category="reflection", outcome="win"),
        ]
    )

    assert dataset["statistics"]["by_category"] == {"reflection": 1, "trade": 2}
    assert dataset["statistics"]["by_outcome"] == {"loss": 1, "win": 2}
    assert dataset["statistics"]["unique_trade_ids"] == 3


def test_build_dataset_counts_none_outcome_as_none_bucket() -> None:
    dataset = build_dataset([_sample_record(outcome=None)])

    assert dataset["statistics"]["by_outcome"] == {"none": 1}


def test_build_dataset_rejects_non_list_input() -> None:
    with pytest.raises(TypeError, match="records deve ser uma lista"):
        build_dataset({})  # type: ignore[arg-type]


def test_build_dataset_rejects_missing_required_fields() -> None:
    with pytest.raises(ValueError, match="Campos obrigatorios ausentes"):
        build_dataset([{"trade_id": "T-001"}])


def test_build_dataset_rejects_invalid_timestamp_type() -> None:
    bad_record = _sample_record()
    bad_record["timestamp"] = 123  # type: ignore[assignment]

    with pytest.raises(TypeError, match="timestamp deve ser datetime ou string ISO"):
        build_dataset([bad_record])


def test_build_dataset_rejects_invalid_tags_and_context_types() -> None:
    bad_record = _sample_record()
    bad_record["tags"] = "not-a-list"  # type: ignore[assignment]

    with pytest.raises(TypeError, match="tags deve ser uma lista"):
        build_dataset([bad_record])


def test_to_json_payload_serializes_valid_dataset() -> None:
    dataset = build_dataset([_sample_record()])

    payload = to_json_payload(dataset)
    parsed = json.loads(payload)

    assert parsed["total_records"] == 1
    assert parsed["records"][0]["trade_id"] == "T-001"
    assert parsed["statistics"]["by_category"] == {"trade": 1}


def test_to_json_payload_rejects_invalid_dataset_schema() -> None:
    with pytest.raises(ValueError, match="Dataset invalido"):
        to_json_payload({"records": []})  # type: ignore[arg-type]
