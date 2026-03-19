"""Universal kill switch.

Modulo para consolidar eventos de risco de multiplas origens e decidir o
estado final do kill-switch de forma deterministica.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from math import isfinite
from collections.abc import Iterable, Mapping
from typing import Any

ALLOWED_SEVERITIES = ("INFO", "WARNING", "CRITICAL")


def _now_utc() -> datetime:
    """Retorna o timestamp atual em UTC."""
    return datetime.utcnow()


def _as_text(value: Any, default: str = "") -> str:
    """Converte um valor para texto de forma segura."""
    if value is None:
        return default
    return str(value)


def _coerce_bool(value: Any) -> bool:
    """Normaliza valores booleanos vindos de dicts ou objetos."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "f", "no", "n", "off", ""}:
            return False
        raise ValueError(f"Valor booleano invalido: {value!r}")
    return bool(value)


def _serialize_value(value: Any) -> Any:
    """Converte valores para uma estrutura JSON serializavel."""
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    if isinstance(value, set):
        return [_serialize_value(item) for item in sorted(value, key=str)]
    return value


def _get_event_value(event: Any, field_name: str, default: Any = None) -> Any:
    """Obtém um campo de um evento, aceitando dict ou objeto."""
    if isinstance(event, Mapping):
        return event.get(field_name, default)
    if hasattr(event, field_name):
        return getattr(event, field_name)
    raise TypeError(
        "Cada evento deve ser um mapping ou objeto com os campos esperados."
    )


def _normalize_event(event: Any) -> dict[str, Any]:
    """Normaliza um evento para um formato interno consistente."""
    source = _as_text(_get_event_value(event, "source", "unknown"), "unknown") or "unknown"
    severity = _as_text(_get_event_value(event, "severity", "INFO"), "INFO").upper()
    if severity not in ALLOWED_SEVERITIES:
        raise ValueError(
            f"severity invalida: {severity!r}. Valores aceitos: {', '.join(ALLOWED_SEVERITIES)}"
        )

    score_raw = _get_event_value(event, "score_impacto", None)
    score_value = None if score_raw is None else float(score_raw)
    if score_value is not None and not isfinite(score_value):
        raise ValueError("score_impacto deve ser um numero finito")

    timestamp_raw = _get_event_value(event, "timestamp", None)
    if isinstance(timestamp_raw, datetime):
        timestamp = timestamp_raw.isoformat(timespec="seconds")
    elif timestamp_raw is None:
        timestamp = _now_utc().isoformat(timespec="seconds")
    else:
        timestamp = _as_text(timestamp_raw)

    return {
        "source": source,
        "severity": severity,
        "score_impacto": score_value,
        "kill_switch_ativo": _coerce_bool(_get_event_value(event, "kill_switch_ativo", False)),
        "category": _as_text(_get_event_value(event, "category", ""), ""),
        "message": _as_text(_get_event_value(event, "message", ""), ""),
        "timestamp": timestamp,
    }


@dataclass
class UniversalKillSwitchResult:
    """Resultado consolidado do kill-switch universal."""

    active: bool
    reason: str
    severity: str
    trigger_count: int
    trigger_sources: list[str] = field(default_factory=list)
    score_impacto_medio: float = 0.0
    actions: list[str] = field(default_factory=list)
    audit: dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=_now_utc)

    def __post_init__(self) -> None:
        """Valida o resultado consolidado."""
        if self.severity not in ALLOWED_SEVERITIES:
            raise ValueError(
                f"severity invalida: {self.severity!r}. Valores aceitos: {', '.join(ALLOWED_SEVERITIES)}"
            )
        if self.trigger_count < 0:
            raise ValueError("trigger_count nao pode ser negativo")
        if not isfinite(float(self.score_impacto_medio)):
            raise ValueError("score_impacto_medio deve ser finito")
        self.trigger_sources = [str(source) for source in self.trigger_sources]
        self.actions = [str(action) for action in self.actions]
        self.reason = str(self.reason)

    def to_dict(self) -> dict[str, Any]:
        """Converte o resultado para um dicionario serializavel."""
        return {
            "active": self.active,
            "reason": self.reason,
            "severity": self.severity,
            "trigger_count": self.trigger_count,
            "trigger_sources": list(self.trigger_sources),
            "score_impacto_medio": self.score_impacto_medio,
            "actions": list(self.actions),
            "audit": _serialize_value(self.audit),
            "generated_at": self.generated_at.isoformat(timespec="seconds"),
        }


class UniversalKillSwitch:
    """Consolidador universal de gatilhos de risco.

    A classe recebe eventos de diferentes origens e decide se o kill-switch
    deve ser ativado com base nas regras:

    - qualquer evento com ``kill_switch_ativo=True``;
    - qualquer evento com severidade ``CRITICAL``;
    - media de ``score_impacto`` acima do threshold configurado.
    """

    def __init__(self, score_threshold: float = 0.75) -> None:
        """Inicializa o kill-switch universal.

        Args:
            score_threshold: threshold da media de score_impacto para ativacao.
        """
        self.score_threshold = self._validate_threshold(score_threshold)

    @staticmethod
    def _validate_threshold(value: Any) -> float:
        """Valida o threshold configurado no construtor."""
        try:
            threshold = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("score_threshold deve ser numerico") from exc
        if not isfinite(threshold):
            raise ValueError("score_threshold deve ser finito")
        return threshold

    def evaluate(self, events: Iterable[Any]) -> UniversalKillSwitchResult:
        """Avalia uma sequencia de eventos e retorna o estado final."""
        if events is None:
            raise ValueError("events nao pode ser None")
        if isinstance(events, (str, bytes)):
            raise TypeError("events deve ser um iteravel de eventos, nao texto")

        try:
            normalized_events = [_normalize_event(event) for event in events]
        except TypeError:
            raise
        except (ValueError, AttributeError, KeyError, TypeError) as exc:
            raise ValueError(f"evento invalido: {exc}") from exc

        if not normalized_events:
            return UniversalKillSwitchResult(
                active=False,
                reason="Nenhum evento recebido.",
                severity="INFO",
                trigger_count=0,
                trigger_sources=[],
                score_impacto_medio=0.0,
                actions=["MONITOR"],
                audit={
                    "score_threshold": self.score_threshold,
                    "events_total": 0,
                    "events_with_score": 0,
                    "kill_switch_ativo_detectado": False,
                    "critical_detectado": False,
                    "average_threshold_exceeded": False,
                    "normalized_events": [],
                },
            )

        score_values = [
            float(event["score_impacto"])
            for event in normalized_events
            if event["score_impacto"] is not None
        ]
        score_medio = sum(score_values) / len(score_values) if score_values else 0.0

        kill_switch_hits = [
            index for index, event in enumerate(normalized_events) if event["kill_switch_ativo"]
        ]
        critical_hits = [
            index for index, event in enumerate(normalized_events) if event["severity"] == "CRITICAL"
        ]
        average_trigger = bool(score_values) and score_medio > self.score_threshold

        trigger_indexes = set(kill_switch_hits) | set(critical_hits)
        if average_trigger:
            trigger_indexes.update(
                index
                for index, event in enumerate(normalized_events)
                if event["score_impacto"] is not None
            )

        trigger_sources = []
        seen_sources = set()
        for index in sorted(trigger_indexes):
            source = normalized_events[index]["source"]
            if source not in seen_sources:
                seen_sources.add(source)
                trigger_sources.append(source)

        active = bool(kill_switch_hits or critical_hits or average_trigger)
        if critical_hits:
            severity = "CRITICAL"
        elif active:
            severity = "WARNING"
        else:
            severity = "INFO"

        reason_parts: list[str] = []
        if kill_switch_hits:
            reason_parts.append(
                f"{len(kill_switch_hits)} evento(s) com kill_switch_ativo=True"
            )
        if critical_hits:
            reason_parts.append(f"{len(critical_hits)} evento(s) CRITICAL")
        if average_trigger:
            reason_parts.append(
                f"media score_impacto={score_medio:.3f} acima do threshold={self.score_threshold:.3f}"
            )
        if not reason_parts:
            reason_parts.append("Nenhum gatilho de risco relevante encontrado.")

        actions: list[str]
        if active:
            actions = ["PAUSE_NEW_ENTRIES", "NOTIFY_RISK_CHANNEL", "LOG_AUDIT"]
            if average_trigger and not critical_hits:
                actions.append("REDUCE_EXPOSURE")
            if kill_switch_hits:
                actions.append("REVIEW_KILL_SWITCH_SOURCE")
        else:
            actions = ["MONITOR"]

        return UniversalKillSwitchResult(
            active=active,
            reason="; ".join(reason_parts),
            severity=severity,
            trigger_count=len(trigger_indexes),
            trigger_sources=trigger_sources,
            score_impacto_medio=score_medio,
            actions=actions,
            audit={
                "score_threshold": self.score_threshold,
                "events_total": len(normalized_events),
                "events_with_score": len(score_values),
                "kill_switch_ativo_detectado": bool(kill_switch_hits),
                "critical_detectado": bool(critical_hits),
                "average_threshold_exceeded": average_trigger,
                "trigger_indexes": sorted(trigger_indexes),
                "trigger_sources": trigger_sources,
                "score_impacto_medio": score_medio,
                "normalized_events": normalized_events,
            },
        )

    def __call__(self, events: Iterable[Any]) -> UniversalKillSwitchResult:
        """Atalho para avaliar eventos chamando a instancia diretamente."""
        return self.evaluate(events)


__all__ = [
    "ALLOWED_SEVERITIES",
    "UniversalKillSwitch",
    "UniversalKillSwitchResult",
]
