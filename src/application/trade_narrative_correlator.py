"""
Correlacionador de trades com narrativas de sessao.

Responsabilidades:
- Correlacionar trades com narrativas persistidas.
- Priorizar match por trade_id.
- Usar fallback temporal simples quando trade_id nao estiver disponivel.
- Expor metricas e features serializaveis para outras camadas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable


@dataclass(frozen=True)
class TradeNarrativeCorrelation:
    """Representa a correlacao entre um trade e uma narrativa."""

    trade_id: str | None
    narrative_trade_id: str | None
    trade_timestamp: str | None
    narrative_timestamp: str | None
    match_type: str
    time_delta_minutes: float | None
    narrative_headline: str | None
    narrative_category: str | None
    narrative_text: str | None
    matched: bool

    def to_dict(self) -> dict[str, Any]:
        """Converte a correlacao para estrutura serializavel."""
        return {
            "trade_id": self.trade_id,
            "narrative_trade_id": self.narrative_trade_id,
            "trade_timestamp": self.trade_timestamp,
            "narrative_timestamp": self.narrative_timestamp,
            "match_type": self.match_type,
            "time_delta_minutes": self.time_delta_minutes,
            "narrative_headline": self.narrative_headline,
            "narrative_category": self.narrative_category,
            "narrative_text": self.narrative_text,
            "matched": self.matched,
        }


class TradeNarrativeCorrelator:
    """
    Correlaciona trades com narrativas persistidas.

    O comportamento principal e deterministico:
    - se `trade_id` existir em ambos os lados, prioriza esse match;
    - caso contrario, tenta associar por proximidade temporal;
    - respeita uma janela temporal maxima configuravel.
    """

    def __init__(self, temporal_window_minutes: int = 30) -> None:
        if temporal_window_minutes < 0:
            raise ValueError("temporal_window_minutes nao pode ser negativo")
        self._temporal_window = timedelta(minutes=temporal_window_minutes)

    def correlate(
        self,
        trades: list[dict[str, Any]],
        narratives: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Correlaciona uma lista de trades com narrativas."""
        trade_items = [self._normalize_trade(trade) for trade in trades]
        narrative_items = [self._normalize_narrative(narrative) for narrative in narratives]

        correlations: list[TradeNarrativeCorrelation] = []
        for trade in trade_items:
            correlations.append(self._match_trade(trade, narrative_items))

        correlated_trades = sum(1 for item in correlations if item.matched)
        direct_matches = sum(1 for item in correlations if item.match_type == "trade_id")
        temporal_matches = sum(1 for item in correlations if item.match_type == "temporal")

        return {
            "total_trades": len(trade_items),
            "total_narratives": len(narrative_items),
            "correlated_trades": correlated_trades,
            "unmatched_trades": len(trade_items) - correlated_trades,
            "correlation_rate": (
                correlated_trades / len(trade_items) if trade_items else 0.0
            ),
            "direct_matches": direct_matches,
            "temporal_matches": temporal_matches,
            "correlations": [item.to_dict() for item in correlations],
        }

    def extract_features(self, correlations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extrai features simples e serializaveis a partir das correlacoes."""
        features: list[dict[str, Any]] = []
        for item in correlations:
            trade_text = self._string_value(item.get("narrative_text"))
            headline = self._string_value(item.get("narrative_headline"))
            match_type = self._string_value(item.get("match_type"))
            time_delta = item.get("time_delta_minutes")
            time_delta_value = float(time_delta) if time_delta is not None else None

            features.append(
                {
                    "trade_id": self._string_value(item.get("trade_id")),
                    "matched": bool(item.get("matched", False)),
                    "match_type": match_type,
                    "time_delta_minutes": time_delta_value,
                    "narrative_length": len(trade_text),
                    "headline_length": len(headline),
                    "has_category": item.get("narrative_category") is not None,
                    "narrative_trade_id": self._string_value(item.get("narrative_trade_id")),
                }
            )

        return features

    def _match_trade(
        self,
        trade: dict[str, Any],
        narratives: list[dict[str, Any]],
    ) -> TradeNarrativeCorrelation:
        trade_id = trade["trade_id"]
        trade_timestamp = trade["timestamp"]

        direct_candidates = [
            narrative
            for narrative in narratives
            if trade_id is not None and narrative["trade_id"] == trade_id
        ]
        if direct_candidates:
            narrative = self._choose_best_narrative(trade_timestamp, direct_candidates)
            return self._build_correlation(trade, narrative, "trade_id")

        temporal_candidates = self._find_temporal_candidates(trade_timestamp, narratives)
        if temporal_candidates:
            narrative = temporal_candidates[0]
            return self._build_correlation(trade, narrative, "temporal")

        return TradeNarrativeCorrelation(
            trade_id=trade_id,
            narrative_trade_id=None,
            trade_timestamp=self._format_timestamp(trade_timestamp),
            narrative_timestamp=None,
            match_type="unmatched",
            time_delta_minutes=None,
            narrative_headline=None,
            narrative_category=None,
            narrative_text=None,
            matched=False,
        )

    def _build_correlation(
        self,
        trade: dict[str, Any],
        narrative: dict[str, Any],
        match_type: str,
    ) -> TradeNarrativeCorrelation:
        trade_timestamp = trade["timestamp"]
        narrative_timestamp = narrative["timestamp"]
        time_delta_minutes = None
        if trade_timestamp is not None and narrative_timestamp is not None:
            time_delta_minutes = abs(
                (narrative_timestamp - trade_timestamp).total_seconds() / 60.0
            )

        return TradeNarrativeCorrelation(
            trade_id=trade["trade_id"],
            narrative_trade_id=narrative["trade_id"],
            trade_timestamp=self._format_timestamp(trade_timestamp),
            narrative_timestamp=self._format_timestamp(narrative_timestamp),
            match_type=match_type,
            time_delta_minutes=time_delta_minutes,
            narrative_headline=self._string_value(narrative["headline"]) or None,
            narrative_category=self._string_value(narrative["category"]) or None,
            narrative_text=self._string_value(narrative["narrative"]) or None,
            matched=True,
        )

    def _choose_best_narrative(
        self,
        trade_timestamp: datetime | None,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if trade_timestamp is None:
            return candidates[0]

        return min(
            candidates,
            key=lambda narrative: (
                abs((narrative["timestamp"] - trade_timestamp).total_seconds()),
                narrative["timestamp"],
            ),
        )

    def _find_temporal_candidates(
        self,
        trade_timestamp: datetime | None,
        narratives: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if trade_timestamp is None:
            return []

        candidates = []
        for narrative in narratives:
            delta = abs(narrative["timestamp"] - trade_timestamp)
            if delta <= self._temporal_window:
                candidates.append((delta, narrative))

        candidates.sort(key=lambda item: (item[0], item[1]["timestamp"]))
        return [narrative for _, narrative in candidates]

    def _normalize_trade(self, trade: dict[str, Any]) -> dict[str, Any]:
        return {
            "trade_id": self._optional_string_value(
                self._first_present(trade, "trade_id", "id", "ticket", "order_id")
            ),
            "timestamp": self._parse_timestamp(
                self._first_present(
                    trade,
                    "timestamp",
                    "trade_timestamp",
                    "entry_time",
                    "exit_time",
                    "opened_at",
                    "closed_at",
                )
            ),
        }

    def _normalize_narrative(self, narrative: dict[str, Any]) -> dict[str, Any]:
        return {
            "trade_id": self._optional_string_value(
                self._first_present(narrative, "trade_id", "id", "ticket", "order_id")
            ),
            "timestamp": self._parse_timestamp(
                self._first_present(
                    narrative,
                    "timestamp",
                    "created_at",
                    "published_at",
                    "narrative_timestamp",
                )
            ),
            "headline": self._optional_string_value(
                self._first_present(narrative, "headline", "title", "summary")
            ),
            "category": self._optional_string_value(
                self._first_present(narrative, "category", "type", "kind")
            ),
            "narrative": self._optional_string_value(
                self._first_present(narrative, "narrative", "text", "body", "content")
            ),
        }

    def _first_present(self, data: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]
        return None

    def _parse_timestamp(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        raise TypeError("timestamp deve ser datetime ou string ISO")

    def _format_timestamp(self, value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None

    def _string_value(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    def _optional_string_value(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)
