"""
ROADMAP-DIARIOS-01: Handler de logging e recuperacao.

Responsabilidades:
- Registrar falhas de forma estruturada.
- Acompanhar tentativas de recuperacao por componente.
- Classificar severidade operacional e gerar resumo consolidado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
from typing import Any


class RecoverySeverity(str, Enum):
    """Severidade operacional usada no rastreio de falhas."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class FailureEvent:
    """Evento de falha registrado para um componente."""

    component: str
    timestamp: datetime
    error_type: str
    error_message: str
    context: dict[str, Any]
    severity: RecoverySeverity

    def to_dict(self) -> dict[str, Any]:
        """Converte o evento para uma estrutura serializavel."""
        return {
            "component": self.component,
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.error_type,
            "error_message": self.error_message,
            "context": dict(self.context),
            "severity": self.severity.value,
        }


@dataclass(frozen=True)
class RecoveryAttempt:
    """Tentativa de recuperacao registrada para um componente."""

    component: str
    timestamp: datetime
    action: str
    success: bool
    details: str
    severity: RecoverySeverity

    def to_dict(self) -> dict[str, Any]:
        """Converte a tentativa para uma estrutura serializavel."""
        return {
            "component": self.component,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "success": self.success,
            "details": self.details,
            "severity": self.severity.value,
        }


@dataclass
class _ComponentHistory:
    """Historico interno de falhas e recuperacoes por componente."""

    failures: list[FailureEvent] = field(default_factory=list)
    recovery_attempts: list[RecoveryAttempt] = field(default_factory=list)


class LoggingRecoveryHandler:
    """
    Handler para logging estruturado de falhas e recuperacao.

    O estado eh mantido por componente para permitir auditoria, resumo
    consolidado e exportacao em formatos simples.
    """

    def __init__(self) -> None:
        self._components: dict[str, _ComponentHistory] = {}
        self._lock = threading.RLock()

    def register_failure(
        self,
        component: str,
        error: Exception | str,
        context: dict[str, Any] | None = None,
    ) -> FailureEvent:
        """
        Registra uma falha estruturada para um componente.

        Args:
            component: Nome do componente afetado.
            error: Excecao ou mensagem descritiva da falha.
            context: Metadados opcionais da ocorrencia.
        """
        normalized_context = dict(context or {})
        error_type, error_message = self._normalize_error(error)

        with self._lock:
            history = self._components.setdefault(component, _ComponentHistory())
            failure_index = len(history.failures) + 1
            severity = self._classify_failure(
                component=component,
                error_message=error_message,
                context=normalized_context,
                failure_index=failure_index,
            )
            event = FailureEvent(
                component=component,
                timestamp=datetime.now(),
                error_type=error_type,
                error_message=error_message,
                context=normalized_context,
                severity=severity,
            )
            history.failures.append(event)
            return event

    def register_recovery_attempt(
        self,
        component: str,
        action: str,
        success: bool,
        details: str = "",
    ) -> RecoveryAttempt:
        """
        Registra uma tentativa de recuperacao para um componente.

        Args:
            component: Nome do componente afetado.
            action: Nome da acao executada.
            success: True se a recuperacao funcionou.
            details: Informacoes adicionais da tentativa.
        """
        with self._lock:
            history = self._components.setdefault(component, _ComponentHistory())
            severity = (
                RecoverySeverity.INFO
                if success
                else RecoverySeverity.WARNING
            )
            attempt = RecoveryAttempt(
                component=component,
                timestamp=datetime.now(),
                action=action,
                success=success,
                details=details,
                severity=severity,
            )
            history.recovery_attempts.append(attempt)
            return attempt

    def get_component_status(self, component: str) -> dict[str, Any]:
        """
        Retorna o status atual de um componente.

        Para componentes desconhecidos, devolve um status neutro.
        """
        with self._lock:
            history = self._components.get(component)
            if history is None:
                return {
                    "component": component,
                    "known": False,
                    "healthy": True,
                    "severity": RecoverySeverity.INFO.value,
                    "failure_count": 0,
                    "recovery_attempt_count": 0,
                    "successful_recoveries": 0,
                    "failed_recoveries": 0,
                    "last_failure": None,
                    "last_recovery_attempt": None,
                    "latest_context": {},
                    "open_issues": 0,
                }

            last_failure = history.failures[-1] if history.failures else None
            last_recovery = (
                history.recovery_attempts[-1]
                if history.recovery_attempts
                else None
            )
            recovered = self._is_recovered(last_failure, last_recovery)
            severity = self._current_severity(history, recovered)

            successful_recoveries = sum(
                1 for attempt in history.recovery_attempts if attempt.success
            )
            failed_recoveries = len(history.recovery_attempts) - successful_recoveries

            return {
                "component": component,
                "known": True,
                "healthy": recovered,
                "severity": severity.value,
                "failure_count": len(history.failures),
                "recovery_attempt_count": len(history.recovery_attempts),
                "successful_recoveries": successful_recoveries,
                "failed_recoveries": failed_recoveries,
                "last_failure": (
                    last_failure.to_dict() if last_failure is not None else None
                ),
                "last_recovery_attempt": (
                    last_recovery.to_dict() if last_recovery is not None else None
                ),
                "latest_context": (
                    dict(last_failure.context) if last_failure is not None else {}
                ),
                "open_issues": 0 if recovered else len(history.failures),
            }

    def build_report(self) -> dict[str, Any]:
        """
        Gera um resumo consolidado em formato JSON-serializavel.
        """
        with self._lock:
            components = sorted(self._components.keys())
            statuses = [self.get_component_status(name) for name in components]

        severity_counts = {
            RecoverySeverity.INFO.value: sum(
                1 for status in statuses if status["severity"] == RecoverySeverity.INFO.value
            ),
            RecoverySeverity.WARNING.value: sum(
                1
                for status in statuses
                if status["severity"] == RecoverySeverity.WARNING.value
            ),
            RecoverySeverity.CRITICAL.value: sum(
                1
                for status in statuses
                if status["severity"] == RecoverySeverity.CRITICAL.value
            ),
        }

        failure_count = sum(int(status["failure_count"]) for status in statuses)
        recovery_count = sum(
            int(status["recovery_attempt_count"]) for status in statuses
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "component_count": len(statuses),
            "failure_count": failure_count,
            "recovery_attempt_count": recovery_count,
            "successful_recoveries": sum(
                int(status["successful_recoveries"]) for status in statuses
            ),
            "failed_recoveries": sum(
                int(status["failed_recoveries"]) for status in statuses
            ),
            "severity_counts": severity_counts,
            "components": statuses,
        }

    def to_markdown(self) -> str:
        """
        Renderiza o resumo consolidado em Markdown.
        """
        report = self.build_report()
        lines = [
            "# Logging Recovery Report",
            "",
            f"- Timestamp: `{report['timestamp']}`",
            f"- Components: `{report['component_count']}`",
            f"- Failures: `{report['failure_count']}`",
            f"- Recovery attempts: `{report['recovery_attempt_count']}`",
            f"- Successful recoveries: `{report['successful_recoveries']}`",
            f"- Failed recoveries: `{report['failed_recoveries']}`",
            "",
            "| Component | Healthy | Severity | Failures | Recoveries | Open issues |",
            "|---|---|---|---:|---:|---:|",
        ]

        for status in report["components"]:
            lines.append(
                "| {component} | {healthy} | {severity} | {failure_count} | "
                "{recovery_attempt_count} | {open_issues} |".format(**status)
            )

        return "\n".join(lines)

    def _normalize_error(self, error: Exception | str) -> tuple[str, str]:
        if isinstance(error, Exception):
            return type(error).__name__, str(error)
        return "str", error

    def _classify_failure(
        self,
        component: str,
        error_message: str,
        context: dict[str, Any],
        failure_index: int,
    ) -> RecoverySeverity:
        message = error_message.lower()
        flags = {
            str(key).lower(): value for key, value in context.items()
        }

        if (
            bool(flags.get("critical"))
            or bool(flags.get("fatal"))
            or "critical" in message
            or "fatal" in message
            or "panic" in message
        ):
            return RecoverySeverity.CRITICAL

        if failure_index >= 3:
            return RecoverySeverity.CRITICAL

        return RecoverySeverity.WARNING

    def _is_recovered(
        self,
        last_failure: FailureEvent | None,
        last_recovery: RecoveryAttempt | None,
    ) -> bool:
        if last_failure is None:
            return True
        if last_recovery is None:
            return False
        return last_recovery.success and last_recovery.timestamp >= last_failure.timestamp

    def _current_severity(
        self,
        history: _ComponentHistory,
        recovered: bool,
    ) -> RecoverySeverity:
        if not history.failures and not history.recovery_attempts:
            return RecoverySeverity.INFO

        if recovered:
            return RecoverySeverity.INFO

        last_failure = history.failures[-1]
        return last_failure.severity
