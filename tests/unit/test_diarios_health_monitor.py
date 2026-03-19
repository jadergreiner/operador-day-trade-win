"""Testes unitarios para `src.application.diarios_health_monitor`."""

from __future__ import annotations

from src.application.diarios_health_monitor import (
    DiariosHealthMonitor,
    Severity,
    ThreadHealthRecord,
)


def test_default_summary_without_ingestion() -> None:
    monitor = DiariosHealthMonitor()

    summary = monitor.build_summary()

    assert summary["overall_severity"] == Severity.OK.value
    assert summary["total_threads"] == 0
    assert summary["recovery_events"] == 0
    assert summary["threads_by_severity"] == {
        Severity.OK.value: 0,
        Severity.WARNING.value: 0,
        Severity.CRITICAL.value: 0,
    }
    assert summary["threads"] == []


def test_ingest_report_and_summary_fields() -> None:
    monitor = DiariosHealthMonitor()
    monitor.ingest_report(
        {
            "threads": {
                "journal": {
                    "alive": True,
                    "restarts": 0,
                    "max_restarts": 3,
                    "health_status": "healthy",
                }
            },
            "recovery_events": 2,
        }
    )

    summary = monitor.build_summary()

    assert summary["total_threads"] == 1
    assert summary["recovery_events"] == 2
    assert summary["threads_by_severity"][Severity.OK.value] == 1
    assert summary["threads"][0]["name"] == "journal"
    assert summary["threads"][0]["alive"] is True
    assert summary["threads"][0]["health_status"] == "healthy"


def test_classify_thread_ok_when_alive_and_clean() -> None:
    monitor = DiariosHealthMonitor()

    record = monitor._classify_thread(
        "journal",
        {
            "alive": True,
            "restarts": 0,
            "max_restarts": 3,
            "health_status": "healthy",
        },
    )

    assert record.severity == Severity.OK
    assert record.reason == "operacao normal"
    assert record.to_dict()["severity"] == Severity.OK.value


def test_classify_thread_warning_for_restart_history() -> None:
    monitor = DiariosHealthMonitor()

    record = monitor._classify_thread(
        "reflection",
        {
            "alive": True,
            "restarts": 1,
            "max_restarts": 3,
            "health_status": "degraded",
        },
    )

    assert record.severity == Severity.WARNING
    assert record.reason == "thread com reinicio recente"


def test_classify_thread_warning_when_not_alive_but_not_critical() -> None:
    monitor = DiariosHealthMonitor()

    record = monitor._classify_thread(
        "ai",
        {
            "alive": False,
            "restarts": 0,
            "max_restarts": 2,
            "health_status": "unknown",
        },
    )

    assert record.severity == Severity.WARNING
    assert record.reason == "thread nao viva no momento"


def test_classify_thread_critical_when_stopped() -> None:
    monitor = DiariosHealthMonitor()

    record = monitor._classify_thread(
        "rl",
        {
            "alive": False,
            "restarts": 4,
            "max_restarts": 4,
            "health_status": "stopped",
        },
    )

    assert record.severity == Severity.CRITICAL
    assert record.reason == "thread parada ou em estado critico"


def test_overall_severity_promotes_to_warning() -> None:
    monitor = DiariosHealthMonitor()
    monitor.ingest_report(
        {
            "threads": {
                "journal": {
                    "alive": True,
                    "restarts": 0,
                    "max_restarts": 3,
                    "health_status": "healthy",
                },
                "reflection": {
                    "alive": True,
                    "restarts": 1,
                    "max_restarts": 3,
                    "health_status": "degraded",
                },
            }
        }
    )

    summary = monitor.build_summary()

    assert summary["overall_severity"] == Severity.WARNING.value
    assert summary["threads_by_severity"][Severity.OK.value] == 1
    assert summary["threads_by_severity"][Severity.WARNING.value] == 1
    assert summary["threads_by_severity"][Severity.CRITICAL.value] == 0


def test_overall_severity_promotes_to_critical() -> None:
    monitor = DiariosHealthMonitor()
    monitor.ingest_report(
        {
            "threads": {
                "journal": {
                    "alive": True,
                    "restarts": 0,
                    "max_restarts": 3,
                    "health_status": "healthy",
                },
                "ai": {
                    "alive": False,
                    "restarts": 3,
                    "max_restarts": 3,
                    "health_status": "critical",
                },
            }
        }
    )

    summary = monitor.build_summary()

    assert summary["overall_severity"] == Severity.CRITICAL.value
    assert summary["threads_by_severity"][Severity.CRITICAL.value] == 1


def test_recovery_events_are_preserved_in_summary() -> None:
    monitor = DiariosHealthMonitor()
    monitor.ingest_report(
        {
            "threads": {
                "journal": {
                    "alive": True,
                    "restarts": 0,
                    "max_restarts": 3,
                    "health_status": "healthy",
                }
            },
            "recovery_events": 5,
        }
    )

    summary = monitor.build_summary()

    assert summary["recovery_events"] == 5


def test_markdown_has_expected_structure_and_content() -> None:
    monitor = DiariosHealthMonitor()
    monitor.ingest_report(
        {
            "threads": {
                "journal": {
                    "alive": True,
                    "restarts": 0,
                    "max_restarts": 3,
                    "health_status": "healthy",
                },
                "reflection": {
                    "alive": True,
                    "restarts": 1,
                    "max_restarts": 3,
                    "health_status": "degraded",
                },
            },
            "recovery_events": 1,
        }
    )

    markdown = monitor.to_markdown()

    assert "# Relatorio de Saude dos Diarios" in markdown
    assert "| Thread | Alive | Restarts | Max | Health | Severity | Motivo |" in markdown
    assert "journal" in markdown
    assert "reflection" in markdown
    assert "warning" in markdown


def test_thread_health_record_to_dict_is_serializable_shape() -> None:
    record = ThreadHealthRecord(
        name="journal",
        alive=True,
        restarts=0,
        max_restarts=3,
        health_status="healthy",
        severity=Severity.OK,
        reason="operacao normal",
    )

    payload = record.to_dict()

    assert payload == {
        "name": "journal",
        "alive": True,
        "restarts": 0,
        "max_restarts": 3,
        "health_status": "healthy",
        "severity": Severity.OK.value,
        "reason": "operacao normal",
    }
