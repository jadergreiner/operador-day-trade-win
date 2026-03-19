"""
Exportador de dataset de narrativas e correlacoes.

Responsabilidades:
- Normalizar registros de narrativas em uma estrutura JSON-friendly.
- Gerar estatisticas por categoria e por outcome.
- Validar schema basico antes da serializacao.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any


_REQUIRED_FIELDS = ("trade_id", "timestamp", "headline", "narrative", "category")


def build_dataset(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Construi um dataset serializavel a partir de registros de narrativa.

    Args:
        records: Lista de dicionarios com campos de narrativa.

    Returns:
        Estrutura JSON-friendly com registros normalizados e estatisticas.
    """
    if not isinstance(records, list):
        raise TypeError("records deve ser uma lista")

    normalized_records = [_normalize_record(record) for record in records]
    statistics = _build_statistics(normalized_records)

    return {
        "schema_version": "narrative_dataset_v1",
        "generated_at": datetime.now().isoformat(),
        "total_records": len(normalized_records),
        "records": normalized_records,
        "statistics": statistics,
    }


def to_json_payload(dataset: dict[str, Any]) -> str:
    """
    Converte um dataset validado para JSON.

    Args:
        dataset: Estrutura gerada por `build_dataset`.

    Returns:
        String JSON formatada.
    """
    _validate_dataset(dataset)
    return json.dumps(dataset, indent=2, ensure_ascii=False)


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise TypeError("Cada registro deve ser um dicionario")

    missing = [field for field in _REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError("Campos obrigatorios ausentes: " + ", ".join(missing))

    timestamp = record["timestamp"]
    if isinstance(timestamp, datetime):
        timestamp_value = timestamp.isoformat()
    elif isinstance(timestamp, str):
        timestamp_value = _normalize_timestamp_string(timestamp)
    else:
        raise TypeError("timestamp deve ser datetime ou string ISO")

    tags = record.get("tags", [])
    context = record.get("context", {})

    if not isinstance(tags, list):
        raise TypeError("tags deve ser uma lista")
    if not isinstance(context, dict):
        raise TypeError("context deve ser um dicionario")

    return {
        "trade_id": str(record["trade_id"]),
        "timestamp": timestamp_value,
        "headline": str(record["headline"]),
        "narrative": str(record["narrative"]),
        "category": _normalize_label(record["category"], fallback="unknown"),
        "session_id": _optional_string(record.get("session_id")),
        "outcome": _optional_string(record.get("outcome")),
        "tags": [str(tag) for tag in tags],
        "context": dict(context),
    }


def _normalize_timestamp_string(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("timestamp nao pode ser vazio")
    try:
        datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp deve estar em formato ISO valido") from exc
    return normalized


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized if normalized else None


def _normalize_label(value: Any, fallback: str) -> str:
    normalized = str(value).strip()
    return normalized if normalized else fallback


def _build_statistics(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_category: dict[str, int] = {}
    by_outcome: dict[str, int] = {}
    unique_trade_ids = set()

    for record in records:
        category = record["category"]
        outcome = record["outcome"] if record["outcome"] is not None else "none"
        trade_id = record["trade_id"]

        by_category[category] = by_category.get(category, 0) + 1
        by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
        unique_trade_ids.add(trade_id)

    return {
        "by_category": dict(sorted(by_category.items())),
        "by_outcome": dict(sorted(by_outcome.items())),
        "unique_trade_ids": len(unique_trade_ids),
    }


def _validate_dataset(dataset: dict[str, Any]) -> None:
    if not isinstance(dataset, dict):
        raise TypeError("dataset deve ser um dicionario")

    required_fields = ("schema_version", "generated_at", "total_records", "records", "statistics")
    missing = [field for field in required_fields if field not in dataset]
    if missing:
        raise ValueError("Dataset invalido: campos ausentes: " + ", ".join(missing))

    if not isinstance(dataset["records"], list):
        raise TypeError("dataset.records deve ser uma lista")
    if not isinstance(dataset["statistics"], dict):
        raise TypeError("dataset.statistics deve ser um dicionario")
    if not isinstance(dataset["total_records"], int):
        raise TypeError("dataset.total_records deve ser um inteiro")
    if dataset["total_records"] != len(dataset["records"]):
        raise ValueError("dataset.total_records nao confere com a quantidade de registros")
    if not isinstance(dataset["schema_version"], str):
        raise TypeError("dataset.schema_version deve ser uma string")
    if not isinstance(dataset["generated_at"], str):
        raise TypeError("dataset.generated_at deve ser uma string")
