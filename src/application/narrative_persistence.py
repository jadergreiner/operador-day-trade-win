"""
Persistencia em memoria de narrativas estruturadas de trading.

Responsabilidades:
- Armazenar narrativas em memoria com serializacao amigavel para JSON.
- Consultar narrativas por trade_id.
- Retornar a narrativa mais recente.
- Expor metricas basicas de uso.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any


@dataclass(frozen=True)
class NarrativeRecord:
    """Registro estruturado de narrativa de trade."""

    trade_id: str
    timestamp: datetime
    headline: str
    narrative: str
    category: str
    session_id: str | None = None
    outcome: str | None = None
    tags: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Converte o registro para uma estrutura serializavel."""
        return {
            "trade_id": self.trade_id,
            "timestamp": self.timestamp.isoformat(),
            "headline": self.headline,
            "narrative": self.narrative,
            "category": self.category,
            "session_id": self.session_id,
            "outcome": self.outcome,
            "tags": list(self.tags),
            "context": dict(self.context),
        }


class NarrativePersistence:
    """
    Persistencia em memoria para narrativas estruturadas.

    A implementacao foi desenhada para ser simples, deterministica e
    diretamente serializavel em JSON, facilitando integracao com outras
    camadas de storytelling.
    """

    def __init__(self) -> None:
        self._records: list[NarrativeRecord] = []
        self._lock = RLock()

    def save_narrative(
        self,
        narrative: NarrativeRecord | dict[str, Any],
    ) -> NarrativeRecord:
        """
        Salva uma narrativa em memoria.

        Aceita tanto o dataclass `NarrativeRecord` quanto um dict com os
        campos obrigatorios:
        - trade_id
        - timestamp
        - headline
        - narrative
        - category
        """
        record = self._normalize_record(narrative)
        with self._lock:
            self._records.append(record)
        return record

    def list_by_trade_id(self, trade_id: str) -> list[dict[str, Any]]:
        """Lista narrativas associadas a um trade_id."""
        with self._lock:
            records = [r for r in self._records if r.trade_id == trade_id]
        return [record.to_dict() for record in records]

    def get_latest_narrative(self) -> dict[str, Any] | None:
        """Retorna a narrativa mais recente ou None quando vazio."""
        with self._lock:
            if not self._records:
                return None
            latest = max(self._records, key=lambda record: record.timestamp)
        return latest.to_dict()

    def get_metrics(self) -> dict[str, Any]:
        """Retorna metricas basicas de armazenamento."""
        with self._lock:
            total_records = len(self._records)
            trade_ids = {record.trade_id for record in self._records}
            categories = sorted({record.category for record in self._records})
            latest = max(self._records, key=lambda record: record.timestamp, default=None)

        return {
            "total_records": total_records,
            "total_trade_ids": len(trade_ids),
            "categories": categories,
            "has_records": total_records > 0,
            "latest_timestamp": (
                latest.timestamp.isoformat() if latest is not None else None
            ),
        }

    def list_all(self) -> list[dict[str, Any]]:
        """Retorna todas as narrativas em formato serializavel."""
        with self._lock:
            records = sorted(self._records, key=lambda record: record.timestamp)
        return [record.to_dict() for record in records]

    def clear(self) -> None:
        """Remove todas as narrativas armazenadas."""
        with self._lock:
            self._records.clear()

    def _normalize_record(
        self,
        narrative: NarrativeRecord | dict[str, Any],
    ) -> NarrativeRecord:
        if isinstance(narrative, NarrativeRecord):
            return narrative

        required_fields = ("trade_id", "timestamp", "headline", "narrative", "category")
        missing = [field_name for field_name in required_fields if field_name not in narrative]
        if missing:
            raise ValueError(
                "Campos obrigatorios ausentes: " + ", ".join(missing)
            )

        timestamp = narrative["timestamp"]
        if not isinstance(timestamp, datetime):
            raise TypeError("timestamp deve ser uma instancia de datetime")

        tags = narrative.get("tags", [])
        context = narrative.get("context", {})

        if not isinstance(tags, list):
            raise TypeError("tags deve ser uma lista")
        if not isinstance(context, dict):
            raise TypeError("context deve ser um dicionario")

        return NarrativeRecord(
            trade_id=str(narrative["trade_id"]),
            timestamp=timestamp,
            headline=str(narrative["headline"]),
            narrative=str(narrative["narrative"]),
            category=str(narrative["category"]),
            session_id=(
                None if narrative.get("session_id") is None else str(narrative["session_id"])
            ),
            outcome=(
                None if narrative.get("outcome") is None else str(narrative["outcome"])
            ),
            tags=[str(tag) for tag in tags],
            context=dict(context),
        )
