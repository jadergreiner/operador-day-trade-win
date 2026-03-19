"""Testes unitarios para ROADMAP-DIARIOS-01: logging_recovery_handler."""

from __future__ import annotations

import json

from src.application.logging_recovery_handler import LoggingRecoveryHandler


def test_register_failure_tracks_warning_status() -> None:
    handler = LoggingRecoveryHandler()

    handler.register_failure(
        "journal",
        ValueError("erro de leitura"),
        {"thread": "journal"},
    )

    status = handler.get_component_status("journal")

    assert status["known"] is True
    assert status["failure_count"] == 1
    assert status["recovery_attempt_count"] == 0
    assert status["severity"] == "warning"
    assert status["healthy"] is False
    assert status["latest_context"] == {"thread": "journal"}
    assert status["last_failure"]["error_type"] == "ValueError"


def test_register_failure_accepts_string_error_and_context_copy() -> None:
    handler = LoggingRecoveryHandler()
    context = {"critical": True, "source": "watchdog"}

    handler.register_failure("watchdog", "critical panic", context)
    context["critical"] = False

    status = handler.get_component_status("watchdog")

    assert status["severity"] == "critical"
    assert status["last_failure"]["error_message"] == "critical panic"
    assert status["latest_context"] == {"critical": True, "source": "watchdog"}


def test_register_recovery_attempt_success_marks_component_healthy() -> None:
    handler = LoggingRecoveryHandler()

    handler.register_failure("recovery", RuntimeError("falha inicial"))
    handler.register_recovery_attempt("recovery", "restart_thread", True, "ok")

    status = handler.get_component_status("recovery")

    assert status["healthy"] is True
    assert status["severity"] == "info"
    assert status["successful_recoveries"] == 1
    assert status["failed_recoveries"] == 0
    assert status["last_recovery_attempt"]["action"] == "restart_thread"
    assert status["last_recovery_attempt"]["success"] is True


def test_register_recovery_attempt_failure_keeps_warning_status() -> None:
    handler = LoggingRecoveryHandler()

    handler.register_failure("worker", RuntimeError("falha"))
    handler.register_recovery_attempt("worker", "retry", False, "timeout")

    status = handler.get_component_status("worker")

    assert status["healthy"] is False
    assert status["severity"] == "warning"
    assert status["failed_recoveries"] == 1
    assert status["last_recovery_attempt"]["details"] == "timeout"


def test_third_failure_escalates_to_critical() -> None:
    handler = LoggingRecoveryHandler()

    handler.register_failure("engine", "erro 1")
    handler.register_failure("engine", "erro 2")
    handler.register_failure("engine", "erro 3")

    status = handler.get_component_status("engine")

    assert status["failure_count"] == 3
    assert status["severity"] == "critical"
    assert status["open_issues"] == 3


def test_build_report_aggregates_counts() -> None:
    handler = LoggingRecoveryHandler()

    handler.register_failure("journal", RuntimeError("falha leve"))
    handler.register_recovery_attempt("journal", "restart", True)
    handler.register_failure("watchdog", "fatal loop", {"critical": True})

    report = handler.build_report()

    assert report["component_count"] == 2
    assert report["failure_count"] == 2
    assert report["recovery_attempt_count"] == 1
    assert report["successful_recoveries"] == 1
    assert report["failed_recoveries"] == 0
    assert report["severity_counts"]["info"] == 1
    assert report["severity_counts"]["critical"] == 1
    assert report["severity_counts"]["warning"] == 0


def test_build_report_is_json_serializable() -> None:
    handler = LoggingRecoveryHandler()
    handler.register_failure("component", "erro simples")

    report = handler.build_report()

    encoded = json.dumps(report, ensure_ascii=False)
    assert "\"component_count\": 1" in encoded


def test_to_markdown_contains_summary_and_components() -> None:
    handler = LoggingRecoveryHandler()
    handler.register_failure("journal", "erro simples")
    handler.register_recovery_attempt("journal", "restart", True)
    handler.register_failure("watchdog", "fatal", {"critical": True})

    markdown = handler.to_markdown()

    assert "# Logging Recovery Report" in markdown
    assert "journal" in markdown
    assert "watchdog" in markdown
    assert "| Component | Healthy | Severity |" in markdown


def test_unknown_component_returns_default_status() -> None:
    handler = LoggingRecoveryHandler()

    status = handler.get_component_status("unknown")

    assert status["known"] is False
    assert status["healthy"] is True
    assert status["severity"] == "info"
    assert status["failure_count"] == 0
    assert status["recovery_attempt_count"] == 0
    assert status["last_failure"] is None
    assert status["last_recovery_attempt"] is None


def test_multiple_components_remain_sorted_in_report() -> None:
    handler = LoggingRecoveryHandler()

    handler.register_failure("zeta", "erro")
    handler.register_failure("alpha", "erro")

    report = handler.build_report()
    components = [item["component"] for item in report["components"]]

    assert components == ["alpha", "zeta"]
