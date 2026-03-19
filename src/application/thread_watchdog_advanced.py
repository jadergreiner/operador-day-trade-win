"""
ROADMAP-DIARIOS-01: Watchdog avancado para threads dos diarios.

Objetivos:
- Monitorar threads criticas em ciclo continuo ou sob demanda.
- Reiniciar automaticamente threads mortas ate limite configurado.
- Registrar eventos de recuperacao para auditoria.
- Expor relatorio de saude consolidado para observabilidade.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import threading
import time
import traceback
from typing import Any, Callable, Optional


logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Status de saude agregado de uma thread monitorada."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    STOPPED = "stopped"


@dataclass(frozen=True)
class ManagedThreadConfig:
    """Configuracao de monitoramento para uma thread."""

    name: str
    target: Callable[[], None]
    max_restarts: int = 3
    restart_backoff_sec: float = 0.0
    daemon: bool = True


@dataclass(frozen=True)
class RecoveryEvent:
    """Evento de tentativa de recuperacao de thread."""

    thread_name: str
    timestamp: datetime
    restart_attempt: int
    success: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """Converte evento para dicionario serializavel."""
        return {
            "thread_name": self.thread_name,
            "timestamp": self.timestamp.isoformat(),
            "restart_attempt": self.restart_attempt,
            "success": self.success,
            "reason": self.reason,
        }


@dataclass
class _ManagedThreadState:
    """Estado interno de uma thread monitorada."""

    config: ManagedThreadConfig
    thread: Optional[threading.Thread] = None
    restart_count: int = 0
    last_heartbeat: Optional[datetime] = None
    last_failure_reason: Optional[str] = None
    alive: bool = False
    stopped: bool = False


class ThreadWatchdogAdvanced:
    """
    Watchdog avancado com reinicio automatico e relatorio de saude.

    Esse modulo prioriza uma API deterministica via `monitor_once()`, para
    que testes e scripts possam validar comportamento sem depender de loops.
    """

    def __init__(self, logger_instance: Optional[logging.Logger] = None) -> None:
        self._logger = logger_instance or logger
        self._states: dict[str, _ManagedThreadState] = {}
        self._events: list[RecoveryEvent] = []
        self._lock = threading.Lock()

    def register_thread(self, config: ManagedThreadConfig) -> None:
        """Registra uma thread para monitoramento."""
        with self._lock:
            self._states[config.name] = _ManagedThreadState(config=config)

    def start_all(self) -> None:
        """Inicia todas as threads registradas que ainda nao foram iniciadas."""
        with self._lock:
            states = list(self._states.values())
        for state in states:
            self._start_thread(state)

    def stop_thread(self, thread_name: str) -> None:
        """Marca uma thread como parada para impedir novos reinicios."""
        with self._lock:
            state = self._states[thread_name]
            state.stopped = True
            state.alive = False

    def monitor_once(self) -> None:
        """Executa uma iteracao de monitoramento e recuperacao."""
        with self._lock:
            states = list(self._states.values())

        for state in states:
            if state.stopped:
                continue

            thread = state.thread
            if thread is not None and thread.is_alive():
                state.alive = True
                continue

            state.alive = False
            reason = state.last_failure_reason or "thread finalizada sem erro"
            if state.restart_count >= state.config.max_restarts:
                self._append_event(state, success=False, reason=reason)
                self._logger.warning(
                    "Thread %s excedeu limite de reinicios (%s).",
                    state.config.name,
                    state.config.max_restarts,
                )
                state.stopped = True
                continue

            if state.config.restart_backoff_sec > 0:
                time.sleep(state.config.restart_backoff_sec)

            state.restart_count += 1
            self._start_thread(state)
            self._append_event(
                state,
                success=True,
                reason=f"reinicio automatico apos: {reason}",
            )

    def update_heartbeat(self, thread_name: str) -> None:
        """Atualiza heartbeat manual da thread para observabilidade."""
        with self._lock:
            self._states[thread_name].last_heartbeat = datetime.now()

    def get_thread_snapshot(self, thread_name: str) -> dict[str, Any]:
        """Retorna snapshot do estado de uma thread."""
        with self._lock:
            state = self._states[thread_name]
            return self._snapshot_for_state(state)

    def get_recovery_events(self) -> list[dict[str, Any]]:
        """Retorna eventos de recuperacao em formato serializavel."""
        with self._lock:
            return [event.to_dict() for event in self._events]

    def generate_health_report(self) -> dict[str, Any]:
        """Gera relatorio consolidado de saude das threads monitoradas."""
        with self._lock:
            snapshots = {
                name: self._snapshot_for_state(state)
                for name, state in self._states.items()
            }

        totals = {
            HealthStatus.HEALTHY.value: 0,
            HealthStatus.DEGRADED.value: 0,
            HealthStatus.CRITICAL.value: 0,
            HealthStatus.STOPPED.value: 0,
        }
        for snapshot in snapshots.values():
            totals[snapshot["health_status"]] += 1

        return {
            "timestamp": datetime.now().isoformat(),
            "total_threads": len(snapshots),
            "threads": snapshots,
            "totals_by_health": totals,
            "recovery_events": len(self.get_recovery_events()),
        }

    def _append_event(
        self,
        state: _ManagedThreadState,
        success: bool,
        reason: str,
    ) -> None:
        with self._lock:
            self._events.append(
                RecoveryEvent(
                    thread_name=state.config.name,
                    timestamp=datetime.now(),
                    restart_attempt=state.restart_count,
                    success=success,
                    reason=reason,
                )
            )

    def _start_thread(self, state: _ManagedThreadState) -> None:
        config = state.config

        def _wrapper() -> None:
            try:
                config.target()
            except Exception as exc:  # pragma: no cover - execucao de thread
                tb = traceback.format_exc()
                failure_reason = f"{type(exc).__name__}: {exc}"
                self._logger.error(
                    "Thread %s falhou. Stack trace: %s",
                    config.name,
                    tb,
                )
                with self._lock:
                    state.last_failure_reason = failure_reason
                    state.alive = False
            finally:
                with self._lock:
                    state.alive = False

        thread = threading.Thread(name=config.name, target=_wrapper, daemon=config.daemon)
        thread.start()

        with self._lock:
            state.thread = thread
            state.alive = True
            if state.last_heartbeat is None:
                state.last_heartbeat = datetime.now()

    def _snapshot_for_state(self, state: _ManagedThreadState) -> dict[str, Any]:
        health_status = HealthStatus.HEALTHY
        if state.stopped:
            health_status = HealthStatus.STOPPED
        elif state.restart_count >= max(1, state.config.max_restarts):
            health_status = HealthStatus.CRITICAL
        elif state.restart_count > 0:
            health_status = HealthStatus.DEGRADED

        return {
            "alive": state.alive,
            "restarts": state.restart_count,
            "max_restarts": state.config.max_restarts,
            "last_failure_reason": state.last_failure_reason,
            "last_heartbeat": (
                state.last_heartbeat.isoformat() if state.last_heartbeat else None
            ),
            "health_status": health_status.value,
        }
