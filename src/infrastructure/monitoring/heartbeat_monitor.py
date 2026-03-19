"""Utilitarios para monitoramento de heartbeat de processos supervisionados."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field


@dataclass
class HeartbeatMonitor:
    """Mantem timestamp da ultima atividade relevante do processo."""

    timeout_seconds: float
    last_heartbeat: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def touch(self) -> None:
        """Atualiza o heartbeat para o instante atual."""
        with self._lock:
            self.last_heartbeat = time.time()

    def elapsed(self, now: float | None = None) -> float:
        """Retorna segundos desde a ultima atividade observada."""
        current = time.time() if now is None else now
        with self._lock:
            return current - self.last_heartbeat

    def should_warn(self, now: float | None = None) -> bool:
        """Indica se o tempo sem atividade excedeu o timeout."""
        return self.elapsed(now=now) > self.timeout_seconds


class HeartbeatLoggingHandler(logging.Handler):
    """Atualiza heartbeat ao observar logs que indiquem atividade real."""

    def __init__(
        self,
        heartbeat_monitor: HeartbeatMonitor,
        *,
        ignored_markers: tuple[str, ...] = ("[MONITOR]",),
    ) -> None:
        super().__init__(level=logging.NOTSET)
        self.heartbeat_monitor = heartbeat_monitor
        self.ignored_markers = ignored_markers

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
        except Exception:
            message = ""

        if any(marker in message for marker in self.ignored_markers):
            return

        self.heartbeat_monitor.touch()
