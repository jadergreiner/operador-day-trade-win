"""Testes unitarios para ROADMAP-DIARIOS-01: thread_watchdog_advanced."""

from __future__ import annotations

import threading
import time

import pytest

from src.application.thread_watchdog_advanced import (
    HealthStatus,
    ManagedThreadConfig,
    ThreadWatchdogAdvanced,
)


def test_register_and_start_threads() -> None:
    run_flag = {"executed": False}

    def target() -> None:
        run_flag["executed"] = True

    watchdog = ThreadWatchdogAdvanced()
    watchdog.register_thread(ManagedThreadConfig(name="journal", target=target))
    watchdog.start_all()
    time.sleep(0.05)

    snapshot = watchdog.get_thread_snapshot("journal")
    assert run_flag["executed"] is True
    assert snapshot["restarts"] == 0


def test_restart_after_failure() -> None:
    counter = {"calls": 0}
    lock = threading.Lock()

    def flaky_target() -> None:
        with lock:
            counter["calls"] += 1
            current = counter["calls"]
        if current == 1:
            raise RuntimeError("falha inicial")
        time.sleep(0.2)

    watchdog = ThreadWatchdogAdvanced()
    watchdog.register_thread(
        ManagedThreadConfig(
            name="reflection",
            target=flaky_target,
            max_restarts=2,
        )
    )

    watchdog.start_all()
    time.sleep(0.05)
    watchdog.monitor_once()
    time.sleep(0.05)

    snapshot = watchdog.get_thread_snapshot("reflection")
    events = watchdog.get_recovery_events()

    assert snapshot["restarts"] >= 1
    assert counter["calls"] >= 2
    assert any(event["success"] for event in events)


def test_stop_after_max_restarts_exceeded() -> None:
    def always_fail() -> None:
        raise ValueError("erro permanente")

    watchdog = ThreadWatchdogAdvanced()
    watchdog.register_thread(
        ManagedThreadConfig(name="rl", target=always_fail, max_restarts=1)
    )

    watchdog.start_all()
    time.sleep(0.05)
    watchdog.monitor_once()
    time.sleep(0.05)
    watchdog.monitor_once()

    snapshot = watchdog.get_thread_snapshot("rl")
    events = watchdog.get_recovery_events()

    assert snapshot["health_status"] == HealthStatus.STOPPED.value
    assert snapshot["restarts"] == 1
    assert any(event["success"] is False for event in events)


def test_update_heartbeat() -> None:
    def target() -> None:
        time.sleep(0.1)

    watchdog = ThreadWatchdogAdvanced()
    watchdog.register_thread(ManagedThreadConfig(name="hb", target=target))
    watchdog.start_all()
    watchdog.update_heartbeat("hb")

    snapshot = watchdog.get_thread_snapshot("hb")
    assert snapshot["last_heartbeat"] is not None


def test_generate_health_report_contains_totals() -> None:
    def ok_target() -> None:
        time.sleep(0.1)

    watchdog = ThreadWatchdogAdvanced()
    watchdog.register_thread(ManagedThreadConfig(name="journal", target=ok_target))
    watchdog.register_thread(ManagedThreadConfig(name="ai", target=ok_target))
    watchdog.start_all()
    time.sleep(0.05)

    report = watchdog.generate_health_report()

    assert report["total_threads"] == 2
    assert "totals_by_health" in report
    assert "healthy" in report["totals_by_health"]
    assert "journal" in report["threads"]
    assert "ai" in report["threads"]


def test_stop_thread_prevents_new_restarts() -> None:
    counter = {"calls": 0}

    def fail_once() -> None:
        counter["calls"] += 1
        raise RuntimeError("erro")

    watchdog = ThreadWatchdogAdvanced()
    watchdog.register_thread(
        ManagedThreadConfig(name="manual_stop", target=fail_once, max_restarts=5)
    )
    watchdog.start_all()
    time.sleep(0.05)
    watchdog.stop_thread("manual_stop")
    watchdog.monitor_once()

    snapshot = watchdog.get_thread_snapshot("manual_stop")
    assert snapshot["health_status"] == HealthStatus.STOPPED.value
    assert snapshot["restarts"] == 0
