import logging

from src.infrastructure.monitoring.heartbeat_monitor import (
    HeartbeatLoggingHandler,
    HeartbeatMonitor,
)


def test_heartbeat_monitor_warns_only_after_timeout() -> None:
    monitor = HeartbeatMonitor(timeout_seconds=60, last_heartbeat=100.0)

    assert monitor.should_warn(now=159.9) is False
    assert monitor.should_warn(now=160.1) is True


def test_logging_handler_touches_for_runtime_activity() -> None:
    monitor = HeartbeatMonitor(timeout_seconds=60, last_heartbeat=100.0)
    handler = HeartbeatLoggingHandler(monitor)
    record = logging.LogRecord(
        name="scripts.operar_novo_agente_rl_real_antiovertrading",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="[CICLO 13] Iniciando iteração do loop...",
        args=(),
        exc_info=None,
    )

    handler.emit(record)

    assert monitor.last_heartbeat > 100.0


def test_logging_handler_ignores_monitor_messages() -> None:
    monitor = HeartbeatMonitor(timeout_seconds=60, last_heartbeat=100.0)
    handler = HeartbeatLoggingHandler(monitor)
    record = logging.LogRecord(
        name="__main__",
        level=logging.WARNING,
        pathname=__file__,
        lineno=20,
        msg="[MONITOR] Sem heartbeat por 370s - processo pode estar travado!",
        args=(),
        exc_info=None,
    )

    handler.emit(record)

    assert monitor.last_heartbeat == 100.0
