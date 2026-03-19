"""
ROADMAP-DIARIOS-01: Monitor de saude dos diarios.

Responsabilidades:
- Receber snapshots de saude do watchdog.
- Classificar severidade operacional por thread e por sistema.
- Gerar saidas padrao para auditoria (dict/JSON e markdown).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Severidade de saude operacional."""

    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ThreadHealthRecord:
    """Registro de saude de uma thread em um instante."""

    name: str
    alive: bool
    restarts: int
    max_restarts: int
    health_status: str
    severity: Severity
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Converte registro para estrutura serializavel."""
        return {
            "name": self.name,
            "alive": self.alive,
            "restarts": self.restarts,
            "max_restarts": self.max_restarts,
            "health_status": self.health_status,
            "severity": self.severity.value,
            "reason": self.reason,
        }


class DiariosHealthMonitor:
    """Agrega saude de threads de diarios e produz relatorio consolidado."""

    def __init__(self) -> None:
        self._last_report: dict[str, Any] | None = None

    def ingest_report(self, watchdog_report: dict[str, Any]) -> None:
        """Armazena ultimo report bruto vindo do watchdog."""
        self._last_report = watchdog_report

    def build_summary(self) -> dict[str, Any]:
        """Gera sumario consolidado com severidade por thread e global."""
        report = self._last_report or {"threads": {}, "recovery_events": 0}
        threads_data = report.get("threads", {})

        records: list[ThreadHealthRecord] = []
        for name, details in threads_data.items():
            records.append(self._classify_thread(name, details))

        overall = self._compute_overall_severity(records)
        counts = {
            Severity.OK.value: sum(1 for r in records if r.severity == Severity.OK),
            Severity.WARNING.value: sum(
                1 for r in records if r.severity == Severity.WARNING
            ),
            Severity.CRITICAL.value: sum(
                1 for r in records if r.severity == Severity.CRITICAL
            ),
        }

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_severity": overall.value,
            "total_threads": len(records),
            "threads_by_severity": counts,
            "recovery_events": int(report.get("recovery_events", 0)),
            "threads": [record.to_dict() for record in records],
        }

    def to_markdown(self) -> str:
        """Renderiza o sumario atual em markdown para auditoria operacional."""
        summary = self.build_summary()
        lines = [
            "# Relatorio de Saude dos Diarios",
            "",
            f"- Timestamp: `{summary['timestamp']}`",
            f"- Severidade geral: `{summary['overall_severity']}`",
            f"- Threads monitoradas: `{summary['total_threads']}`",
            f"- Recovery events: `{summary['recovery_events']}`",
            "",
            "| Thread | Alive | Restarts | Max | Health | Severity | Motivo |",
            "|---|---:|---:|---:|---|---|---|",
        ]

        for thread in summary["threads"]:
            lines.append(
                "| {name} | {alive} | {restarts} | {max_restarts} | {health_status} | "
                "{severity} | {reason} |".format(**thread)
            )

        return "\n".join(lines)

    def _classify_thread(
        self,
        name: str,
        details: dict[str, Any],
    ) -> ThreadHealthRecord:
        alive = bool(details.get("alive", False))
        restarts = int(details.get("restarts", 0))
        max_restarts = int(details.get("max_restarts", 0))
        health_status = str(details.get("health_status", "unknown"))

        severity = Severity.OK
        reason = "operacao normal"

        if not alive and health_status in {"stopped", "critical"}:
            severity = Severity.CRITICAL
            reason = "thread parada ou em estado critico"
        elif restarts > 0 or health_status in {"degraded"}:
            severity = Severity.WARNING
            reason = "thread com reinicio recente"
        elif not alive:
            severity = Severity.WARNING
            reason = "thread nao viva no momento"

        return ThreadHealthRecord(
            name=name,
            alive=alive,
            restarts=restarts,
            max_restarts=max_restarts,
            health_status=health_status,
            severity=severity,
            reason=reason,
        )

    def _compute_overall_severity(self, records: list[ThreadHealthRecord]) -> Severity:
        if any(r.severity == Severity.CRITICAL for r in records):
            return Severity.CRITICAL
        if any(r.severity == Severity.WARNING for r in records):
            return Severity.WARNING
        return Severity.OK
