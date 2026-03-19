"""
Canal utilitario para vincular reflexoes a acoes/trades.

Responsabilidades:
- Registrar acoes e reflexoes com validacao basica.
- Deduplicar registros por id para manter idempotencia.
- Vincular reflexoes a acoes por id direto ou proximidade temporal.
- Sumarizar o impacto por tipo de acao.
- Expor serializacao amigavel para dict/JSON.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


def _parse_datetime(value: Any) -> datetime:
    """Converte valor para datetime.

    Aceita datetime puro ou string ISO 8601. Strings terminadas em ``Z``
    sao convertidas para offset UTC compativel com ``fromisoformat``.
    """

    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        return datetime.fromisoformat(normalized)
    raise TypeError("timestamp deve ser datetime ou string ISO")


def _parse_float(value: Any) -> float:
    """Converte valor numerico para float com validacao simples."""

    if isinstance(value, bool) or value is None:
        raise TypeError("impacto deve ser numerico")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError as exc:
            raise TypeError("impacto deve ser numerico") from exc
    raise TypeError("impacto deve ser numerico")


def _optional_string(value: Any) -> str | None:
    """Normaliza valor opcional para string."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(frozen=True)
class ActionRecord:
    """Representa uma acao ou trade observavel pelo canal."""

    action_id: str
    action_type: str
    timestamp: datetime
    impact: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Converte a acao para estrutura serializavel."""

        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "timestamp": self.timestamp.isoformat(),
            "impact": self.impact,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ReflectionRecord:
    """Representa uma reflexao associavel a uma acao."""

    reflection_id: str
    timestamp: datetime
    text: str | None = None
    action_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Converte a reflexao para estrutura serializavel."""

        return {
            "reflection_id": self.reflection_id,
            "timestamp": self.timestamp.isoformat(),
            "text": self.text,
            "action_id": self.action_id,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ReflectionActionLink:
    """Correlacao entre uma reflexao e uma acao/trade."""

    reflection_id: str
    action_id: str
    action_type: str
    reflection_timestamp: str
    action_timestamp: str
    time_delta_minutes: float
    impact: float
    matched_by: str

    def to_dict(self) -> dict[str, Any]:
        """Converte o link para estrutura serializavel."""

        return {
            "reflection_id": self.reflection_id,
            "action_id": self.action_id,
            "action_type": self.action_type,
            "reflection_timestamp": self.reflection_timestamp,
            "action_timestamp": self.action_timestamp,
            "time_delta_minutes": self.time_delta_minutes,
            "impact": self.impact,
            "matched_by": self.matched_by,
        }


@dataclass(frozen=True)
class ActionImpactSummary:
    """Resumo agregado do impacto por tipo de acao."""

    action_type: str
    action_count: int
    linked_reflections: int
    total_impact: float
    average_impact: float
    positive_actions: int
    negative_actions: int
    neutral_actions: int
    link_rate: float

    def to_dict(self) -> dict[str, Any]:
        """Converte o resumo para estrutura serializavel."""

        return {
            "action_type": self.action_type,
            "action_count": self.action_count,
            "linked_reflections": self.linked_reflections,
            "total_impact": self.total_impact,
            "average_impact": self.average_impact,
            "positive_actions": self.positive_actions,
            "negative_actions": self.negative_actions,
            "neutral_actions": self.neutral_actions,
            "link_rate": self.link_rate,
        }


class ReflectionActionChannel:
    """Canal de correlacao entre reflexoes e acoes/trades.

    A classe aceita dicionarios simples, normaliza os dados e mantem
    registros unicos por id. O vinculo entre reflexao e acao segue a
    ordem:

    1. match direto por ``action_id``;
    2. fallback temporal dentro da janela configurada.
    """

    def __init__(self, temporal_window_minutes: int = 30) -> None:
        """Inicializa o canal.

        Args:
            temporal_window_minutes: Janela maxima para match temporal.
        """

        if temporal_window_minutes < 0:
            raise ValueError("temporal_window_minutes nao pode ser negativo")

        self._temporal_window = timedelta(minutes=temporal_window_minutes)
        self._actions: dict[str, ActionRecord] = {}
        self._reflections: dict[str, ReflectionRecord] = {}
        self._links_cache: list[ReflectionActionLink] = []
        self._links_dirty = True

    def add_action(self, action: ActionRecord | dict[str, Any]) -> ActionRecord:
        """Registra uma acao com deduplicacao por id."""

        normalized = self._normalize_action(action)
        existing = self._actions.get(normalized.action_id)
        if existing is not None:
            return existing

        self._actions[normalized.action_id] = normalized
        self._links_dirty = True
        return normalized

    def add_reflection(self, reflection: ReflectionRecord | dict[str, Any]) -> ReflectionRecord:
        """Registra uma reflexao com deduplicacao por id."""

        normalized = self._normalize_reflection(reflection)
        existing = self._reflections.get(normalized.reflection_id)
        if existing is not None:
            return existing

        self._reflections[normalized.reflection_id] = normalized
        self._links_dirty = True
        return normalized

    def link_reflections(self) -> list[ReflectionActionLink]:
        """Vincula reflexoes a acoes usando a regra de prioridade definida."""

        if not self._links_dirty:
            return list(self._links_cache)

        links: list[ReflectionActionLink] = []
        used_actions: set[str] = set()

        ordered_reflections = sorted(
            self._reflections.values(),
            key=lambda item: (item.timestamp, item.reflection_id),
        )
        ordered_actions = sorted(
            self._actions.values(),
            key=lambda item: (item.timestamp, item.action_id),
        )

        for reflection in ordered_reflections:
            matched = self._match_reflection(reflection, ordered_actions, used_actions)
            if matched is not None:
                action, matched_by = matched
                used_actions.add(action.action_id)
                links.append(
                    self._build_link(
                        reflection=reflection,
                        action=action,
                        matched_by=matched_by,
                    )
                )

        self._links_cache = links
        self._links_dirty = False
        return list(links)

    def summarize_impact_by_action_type(
        self,
        window_start: datetime | str | None = None,
        window_end: datetime | str | None = None,
    ) -> dict[str, Any]:
        """Resumo agregado do impacto por tipo de acao.

        Args:
            window_start: Inicio opcional da janela temporal.
            window_end: Fim opcional da janela temporal.
        """

        start_dt = _parse_datetime(window_start) if window_start is not None else None
        end_dt = _parse_datetime(window_end) if window_end is not None else None

        filtered_actions = [
            action
            for action in self._actions.values()
            if self._is_within_window(action.timestamp, start_dt, end_dt)
        ]
        links = [
            link
            for link in self.link_reflections()
            if self._is_within_window(_parse_datetime(link.action_timestamp), start_dt, end_dt)
        ]

        by_type: dict[str, list[ActionRecord]] = {}
        for action in filtered_actions:
            by_type.setdefault(action.action_type, []).append(action)

        linked_by_type: dict[str, int] = {}
        for link in links:
            linked_by_type[link.action_type] = linked_by_type.get(link.action_type, 0) + 1

        summaries = [
            self._build_summary(
                action_type=action_type,
                actions=actions,
                linked_reflections=linked_by_type.get(action_type, 0),
            ).to_dict()
            for action_type, actions in sorted(by_type.items())
        ]

        return {
            "temporal_window_minutes": int(self._temporal_window.total_seconds() // 60),
            "window_start": start_dt.isoformat() if start_dt is not None else None,
            "window_end": end_dt.isoformat() if end_dt is not None else None,
            "total_actions": len(filtered_actions),
            "total_reflections": len(
                [
                    reflection
                    for reflection in self._reflections.values()
                    if self._is_within_window(reflection.timestamp, start_dt, end_dt)
                ]
            ),
            "linked_reflections": len(links),
            "unlinked_reflections": len(
                [
                    reflection
                    for reflection in self._reflections.values()
                    if self._is_within_window(reflection.timestamp, start_dt, end_dt)
                    and reflection.reflection_id not in {link.reflection_id for link in links}
                ]
            ),
            "summaries": summaries,
        }

    def to_dict(
        self,
        *,
        include_links: bool = True,
        include_summary: bool = True,
    ) -> dict[str, Any]:
        """Serializa o estado atual do canal para dict."""

        payload: dict[str, Any] = {
            "temporal_window_minutes": int(self._temporal_window.total_seconds() // 60),
            "actions": [action.to_dict() for action in self._actions.values()],
            "reflections": [reflection.to_dict() for reflection in self._reflections.values()],
        }
        if include_links:
            payload["links"] = [link.to_dict() for link in self.link_reflections()]
        if include_summary:
            payload["impact_summary"] = self.summarize_impact_by_action_type()
        return payload

    def to_json_ready(self) -> dict[str, Any]:
        """Alias explicito para serializacao amigavel a JSON."""

        return self.to_dict()

    def _normalize_action(self, action: ActionRecord | dict[str, Any]) -> ActionRecord:
        """Normaliza entrada de acao."""

        if isinstance(action, ActionRecord):
            return action
        if not isinstance(action, dict):
            raise TypeError("action deve ser dict ou ActionRecord")

        action_id = _optional_string(
            action.get("action_id")
            or action.get("trade_id")
            or action.get("id")
            or action.get("ticket")
            or action.get("order_id")
        )
        action_type = _optional_string(action.get("action_type") or action.get("type"))
        timestamp_value = action.get("timestamp") or action.get("action_timestamp")

        if action_id is None or action_type is None or timestamp_value is None:
            raise ValueError("acao deve conter action_id, action_type e timestamp")

        impact = _parse_float(action.get("impact"))
        metadata = action.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise TypeError("metadata deve ser dict")

        return ActionRecord(
            action_id=action_id,
            action_type=action_type,
            timestamp=_parse_datetime(timestamp_value),
            impact=impact,
            metadata=dict(metadata),
        )

    def _normalize_reflection(
        self,
        reflection: ReflectionRecord | dict[str, Any],
    ) -> ReflectionRecord:
        """Normaliza entrada de reflexao."""

        if isinstance(reflection, ReflectionRecord):
            return reflection
        if not isinstance(reflection, dict):
            raise TypeError("reflection deve ser dict ou ReflectionRecord")

        reflection_id = _optional_string(
            reflection.get("reflection_id") or reflection.get("id")
        )
        timestamp_value = reflection.get("timestamp") or reflection.get("created_at")
        if reflection_id is None or timestamp_value is None:
            raise ValueError("reflexao deve conter reflection_id e timestamp")

        action_id = _optional_string(
            reflection.get("action_id")
            or reflection.get("trade_id")
            or reflection.get("related_action_id")
        )
        metadata = reflection.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise TypeError("metadata deve ser dict")

        text = _optional_string(
            reflection.get("text")
            or reflection.get("narrative")
            or reflection.get("body")
            or reflection.get("content")
        )

        return ReflectionRecord(
            reflection_id=reflection_id,
            timestamp=_parse_datetime(timestamp_value),
            text=text,
            action_id=action_id,
            metadata=dict(metadata),
        )

    def _match_reflection(
        self,
        reflection: ReflectionRecord,
        actions: list[ActionRecord],
        used_actions: set[str],
    ) -> tuple[ActionRecord, str] | None:
        """Encontra a melhor acao para uma reflexao."""

        if reflection.action_id is not None:
            direct = self._actions.get(reflection.action_id)
            if direct is not None:
                return direct, "action_id"

        temporal_candidates = [
            action
            for action in actions
            if action.action_id not in used_actions
            and abs(action.timestamp - reflection.timestamp) <= self._temporal_window
            and (
                reflection.action_id is None
                or action.action_type == self._actions.get(reflection.action_id, action).action_type
            )
        ]
        if not temporal_candidates:
            temporal_candidates = [
                action
                for action in actions
                if action.action_id not in used_actions
                and abs(action.timestamp - reflection.timestamp) <= self._temporal_window
            ]

        if not temporal_candidates:
            return None

        best = min(
            temporal_candidates,
            key=lambda action: (
                abs((action.timestamp - reflection.timestamp).total_seconds()),
                action.timestamp,
                action.action_id,
            ),
        )
        return best, "temporal"

    def _build_link(
        self,
        reflection: ReflectionRecord,
        action: ActionRecord,
        matched_by: str,
    ) -> ReflectionActionLink:
        """Cria um link serializavel entre reflexao e acao."""

        delta_minutes = abs((action.timestamp - reflection.timestamp).total_seconds()) / 60.0
        return ReflectionActionLink(
            reflection_id=reflection.reflection_id,
            action_id=action.action_id,
            action_type=action.action_type,
            reflection_timestamp=reflection.timestamp.isoformat(),
            action_timestamp=action.timestamp.isoformat(),
            time_delta_minutes=round(delta_minutes, 2),
            impact=action.impact,
            matched_by=matched_by,
        )

    def _build_summary(
        self,
        action_type: str,
        actions: list[ActionRecord],
        linked_reflections: int,
    ) -> ActionImpactSummary:
        """Cria resumo agregado para um tipo de acao."""

        total_impact = sum(action.impact for action in actions)
        action_count = len(actions)
        positive_actions = sum(1 for action in actions if action.impact > 0)
        negative_actions = sum(1 for action in actions if action.impact < 0)
        neutral_actions = sum(1 for action in actions if action.impact == 0)
        average_impact = total_impact / action_count if action_count else 0.0
        link_rate = linked_reflections / action_count if action_count else 0.0

        return ActionImpactSummary(
            action_type=action_type,
            action_count=action_count,
            linked_reflections=linked_reflections,
            total_impact=round(total_impact, 4),
            average_impact=round(average_impact, 4),
            positive_actions=positive_actions,
            negative_actions=negative_actions,
            neutral_actions=neutral_actions,
            link_rate=round(link_rate, 4),
        )

    def _is_within_window(
        self,
        timestamp: datetime,
        window_start: datetime | None,
        window_end: datetime | None,
    ) -> bool:
        """Verifica se timestamp esta dentro da janela opcional."""

        if window_start is not None and timestamp < window_start:
            return False
        if window_end is not None and timestamp > window_end:
            return False
        return True
