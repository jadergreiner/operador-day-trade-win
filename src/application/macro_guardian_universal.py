"""Canal universal de contexto macro para consumo por agentes operacionais.

Este modulo consolida o historico do ``macro_guardian_log`` em um snapshot
padronizado, integra o ``UniversalKillSwitch`` e expõe features prontas para
consumo por modelos ou camadas de decisao.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from src.application.macro_guardian_universal_log import (
    fetch_latest_guardian_snapshot,
    fetch_recent_macro_guardian_events,
)
from src.application.universal_kill_switch import UniversalKillSwitch

DEFAULT_TABLE_LOOKBACK_MINUTES = 30
DEFAULT_EVENT_LIMIT = 100
DEFAULT_REGIME = "ESTAVEL"

ALLOWED_SEVERITIES = ("INFO", "WARNING", "CRITICAL")


def _now_utc() -> datetime:
    """Retorna o timestamp atual em UTC."""
    return datetime.utcnow()


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Converte um valor para float sem propagar excecoes de parsing."""
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number != number:
        return default
    return number


def _safe_int(value: Any, default: int = 0) -> int:
    """Converte um valor para int de forma tolerante."""
    if value is None:
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_text(value: Any, default: str = "") -> str:
    """Converte um valor para texto garantindo fallback."""
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_bool(value: Any) -> bool:
    """Normaliza um valor para bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "f", "no", "n", "off", ""}:
            return False
    return bool(value)


def _parse_timestamp(value: Any) -> datetime | None:
    """Tenta converter timestamps ISO-8601 em ``datetime``."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = _safe_text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _serialize_value(value: Any) -> Any:
    """Serializa valores complexos para estrutura compatível com JSON."""
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, Mapping):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    if isinstance(value, set):
        return [_serialize_value(item) for item in sorted(value, key=str)]
    return value


def _normalize_severity(value: Any) -> str:
    """Normaliza severidade para os valores canônicos."""
    severity = _safe_text(value, "INFO").upper()
    return severity if severity in ALLOWED_SEVERITIES else "INFO"


def _normalize_kill_switch_score(value: Any) -> float | None:
    """Normaliza score para a escala esperada pelo ``UniversalKillSwitch``.

    O log macro costuma persistir valores em faixa 0-100, enquanto o
    consolidado universal trabalha com scores normalizados em 0-1.
    """
    if value is None:
        return None
    score = _safe_float(value, 0.0)
    if score == 0.0 and value not in {0, 0.0, "0", "0.0"}:
        return None
    if score > 1.0:
        return max(0.0, min(1.0, score / 100.0))
    return max(0.0, min(1.0, score))


@dataclass(slots=True)
class MacroGuardianSnapshot:
    """Snapshot consolidado do estado macro."""

    timestamp: datetime = field(default_factory=_now_utc)
    score_guardian: float = 0.0
    alertas_ativos: int = 0
    regime_macro: str = DEFAULT_REGIME
    kill_switch_ativo: bool = False
    kill_switch_reason: str = ""
    total_eventos: int = 0
    severities: dict[str, int] = field(default_factory=dict)
    eventos_recentes: list[dict[str, Any]] = field(default_factory=list)
    kill_switch_actions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Converte o snapshot para um dicionario serializavel."""
        payload = asdict(self)
        payload["timestamp"] = self.timestamp.isoformat(timespec="seconds")
        return _serialize_value(payload)

    @property
    def recent_events(self) -> list[dict[str, Any]]:
        """Alias para compatibilidade com consumidores legados."""
        return self.eventos_recentes

    def to_feature_dict(self) -> dict[str, Any]:
        """Converte snapshot para o contrato de features usado pelos agentes."""
        return {
            "score_guardian": self.score_guardian,
            "alertas_ativos": self.alertas_ativos,
            "regime_macro": self.regime_macro,
            "kill_switch_ativo": self.kill_switch_ativo,
            "kill_switch_reason": self.kill_switch_reason,
            "total_eventos": self.total_eventos,
            "severity_info": self.severities.get("INFO", 0),
            "severity_warning": self.severities.get("WARNING", 0),
            "severity_critical": self.severities.get("CRITICAL", 0),
            "kill_switch_actions": list(self.kill_switch_actions),
            "timestamp": self.timestamp.isoformat(timespec="seconds"),
        }


class MacroGuardianUniversal:
    """Canal universal para consumo do contexto macro por qualquer agente."""

    def __init__(
        self,
        db_path: str | Path,
        *,
        kill_switch: UniversalKillSwitch | None = None,
        lookback_minutes: int = DEFAULT_TABLE_LOOKBACK_MINUTES,
        event_limit: int = DEFAULT_EVENT_LIMIT,
    ) -> None:
        self.db_path = Path(db_path)
        self.lookback_minutes = max(0, int(lookback_minutes))
        self.event_limit = max(1, int(event_limit))
        self.kill_switch = kill_switch or UniversalKillSwitch()

    def get_recent_events(
        self,
        *,
        limit: int | None = None,
        severities: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Retorna eventos recentes do ``macro_guardian_log``.

        A leitura fica encapsulada para que qualquer agente consuma o mesmo
        contrato de dados sem conhecer detalhes de persistência.
        """
        try:
            return fetch_recent_macro_guardian_events(
                self.db_path,
                limit=limit or self.event_limit,
                severities=severities,
            )
        except Exception:
            return []

    def _build_kill_switch_payload(self, events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        """Monta eventos no formato esperado pelo consolidado universal."""
        payloads: list[dict[str, Any]] = []
        for event in events:
            payloads.append(
                {
                    "source": _safe_text(event.get("source"), "macro_guardian"),
                    "severity": _normalize_severity(event.get("severity")),
                    "score_impacto": _normalize_kill_switch_score(event.get("score_impacto")),
                    "kill_switch_ativo": _safe_bool(event.get("kill_switch_ativo", False)),
                    "category": _safe_text(event.get("tipo_evento") or event.get("category"), ""),
                    "message": _safe_text(event.get("descricao") or event.get("message"), ""),
                    "timestamp": event.get("timestamp"),
                }
            )
        return {"events": payloads}

    def build_snapshot(
        self,
        *,
        lookback_minutes: int | None = None,
        event_limit: int | None = None,
    ) -> MacroGuardianSnapshot:
        """Cria um snapshot consolidado do estado macro."""
        lookback = self.lookback_minutes if lookback_minutes is None else max(0, int(lookback_minutes))
        limit = self.event_limit if event_limit is None else max(1, int(event_limit))

        events = self.get_recent_events(limit=limit)
        if not events:
            try:
                fallback = fetch_latest_guardian_snapshot(self.db_path, lookback_minutes=lookback)
            except Exception:
                fallback = {}
            return MacroGuardianSnapshot(
                score_guardian=_safe_float(fallback.get("score_impacto_medio"), 0.0),
                alertas_ativos=_safe_int(fallback.get("alertas_ativos"), 0),
                regime_macro=_safe_text(fallback.get("regime_macro"), DEFAULT_REGIME),
                kill_switch_ativo=_safe_bool(fallback.get("kill_switch_ativo", False)),
                kill_switch_reason="Sem eventos recentes." if not fallback else _safe_text(
                    fallback.get("kill_switch_reason"), ""
                ),
                total_eventos=_safe_int(fallback.get("total_eventos"), 0),
                metadata={
                    "lookback_minutes": lookback,
                    "event_limit": limit,
                    "source": "fallback_snapshot",
                },
            )

        cutoff = _now_utc() - timedelta(minutes=lookback)
        recentes: list[dict[str, Any]] = []
        for event in events:
            parsed_ts = _parse_timestamp(event.get("timestamp"))
            if parsed_ts is None or parsed_ts >= cutoff:
                recentes.append(event)

        if not recentes:
            recentes = list(events)

        severities = {"INFO": 0, "WARNING": 0, "CRITICAL": 0}
        for event in recentes:
            severities[_normalize_severity(event.get("severity"))] += 1

        alertas_ativos = severities["WARNING"] + severities["CRITICAL"]
        score_values = [
            _safe_float(event.get("score_impacto"), 0.0)
            for event in recentes
            if event.get("score_impacto") is not None
        ]
        score_guardian = sum(score_values) / len(score_values) if score_values else 0.0

        try:
            kill_switch_result = self.kill_switch.evaluate(
                self._build_kill_switch_payload(recentes)["events"]
            )
            kill_switch_ativo = bool(kill_switch_result.active)
            kill_switch_reason = _safe_text(kill_switch_result.reason, "")
            kill_switch_actions = list(kill_switch_result.actions)
        except Exception:
            kill_switch_ativo = any(
                _safe_bool(event.get("kill_switch_ativo", False))
                or _normalize_severity(event.get("severity")) == "CRITICAL"
                for event in recentes
            )
            kill_switch_reason = "Falha ao consolidar kill switch universal."
            kill_switch_actions = ["MONITOR"]

        if kill_switch_ativo and not kill_switch_reason:
            kill_switch_reason = "Kill switch acionado por alerta macro."

        if kill_switch_ativo:
            regime_macro = "CRITICO"
        elif alertas_ativos >= 3 or score_guardian <= -3.0:
            regime_macro = "ALERTA"
        elif alertas_ativos == 0 and score_guardian >= 2.0:
            regime_macro = "FAVORAVEL"
        else:
            regime_macro = DEFAULT_REGIME

        return MacroGuardianSnapshot(
            score_guardian=score_guardian,
            alertas_ativos=alertas_ativos,
            regime_macro=regime_macro,
            kill_switch_ativo=kill_switch_ativo,
            kill_switch_reason=kill_switch_reason,
            total_eventos=len(recentes),
            severities=severities,
            eventos_recentes=[dict(event) for event in recentes],
            kill_switch_actions=kill_switch_actions,
            metadata={
                "lookback_minutes": lookback,
                "event_limit": limit,
                "events_considered": len(recentes),
                "events_total_loaded": len(events),
            },
        )

    def export_features(
        self,
        snapshot: MacroGuardianSnapshot | None = None,
        *,
        lookback_minutes: int | None = None,
        event_limit: int | None = None,
    ) -> dict[str, Any]:
        """Exporta features prontas para uso por agentes/modelos."""
        if snapshot is None:
            snapshot = self.build_snapshot(
                lookback_minutes=lookback_minutes,
                event_limit=event_limit,
            )
        return _serialize_value(snapshot.to_feature_dict())

    def export_snapshot_json(
        self,
        *,
        lookback_minutes: int | None = None,
        event_limit: int | None = None,
    ) -> str:
        """Serializa o snapshot para JSON, util para logs e integrações."""
        snapshot = self.build_snapshot(
            lookback_minutes=lookback_minutes,
            event_limit=event_limit,
        )
        return json.dumps(snapshot.to_dict(), ensure_ascii=False)

    def health_check(self) -> dict[str, Any]:
        """Retorna um status simples de integridade do canal universal."""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            try:
                conn.execute("SELECT 1")
            finally:
                conn.close()
            return {
                "ok": True,
                "db_path": str(self.db_path),
                "table": "macro_guardian_log",
            }
        except Exception as exc:
            return {
                "ok": False,
                "db_path": str(self.db_path),
                "table": "macro_guardian_log",
                "error": _safe_text(exc, "erro desconhecido"),
            }


__all__ = [
    "DEFAULT_EVENT_LIMIT",
    "DEFAULT_REGIME",
    "DEFAULT_TABLE_LOOKBACK_MINUTES",
    "MacroGuardianSnapshot",
    "MacroGuardianUniversal",
]
