"""Testes unitarios da persistencia do Macro Scenario Guardian."""

from __future__ import annotations

import sys
import types
from datetime import datetime

from src.application.services import macro_scenario_guardian as msg


def _make_alert(severity: str, category: str, message: str) -> msg.MacroAlert:
    """Helper para criar alertas do guardian."""
    return msg.MacroAlert(
        timestamp=datetime.now().isoformat(),
        severity=severity,
        category=category,
        message=message,
        action="MONITOR",
        data={"source": category, "valor_atual": severity},
    )


def test_macro_alert_to_universal_log_event_maps_core_fields():
    """A conversao deve expor os campos canonicos do log universal."""
    alert = _make_alert("WARNING", "TESTE", "Alerta de teste")

    event = msg.macro_alert_to_universal_log_event(alert)

    assert event["timestamp"] == alert.timestamp
    assert event["severity"] == "WARNING"
    assert event["tipo_evento"] == "TESTE"
    assert event["descricao"] == "Alerta de teste"
    assert event["valor_atual"] == "WARNING"
    assert event["score_impacto"] == 65
    assert event["action"] == "MONITOR"


def test_run_guardian_check_persists_info_warning_and_critical(monkeypatch):
    """run_guardian_check deve persistir alertas de varios niveis no log."""
    recorded = []

    def ensure_macro_guardian_log_table(db_path: str):
        recorded.append(("ensure", db_path))

    def append_macro_guardian_events(events, db_path: str):
        recorded.append(("append", db_path, events))

    fake_module = types.ModuleType("src.application.macro_guardian_universal_log")
    fake_module.ensure_macro_guardian_log_table = ensure_macro_guardian_log_table
    fake_module.append_macro_guardian_events = append_macro_guardian_events
    monkeypatch.setitem(sys.modules, "src.application.macro_guardian_universal_log", fake_module)

    info_alert = _make_alert("INFO", "INFO_EVENT", "Info mockada")
    warning_alert = _make_alert("WARNING", "WARNING_EVENT", "Warning mockada")
    critical_alert = _make_alert("CRITICAL", "CRITICAL_EVENT", "Critical mockada")

    monkeypatch.setattr(msg, "check_dollar_aggression", lambda state: [info_alert])
    monkeypatch.setattr(msg, "check_sp500_shock", lambda state, db_path: [warning_alert])
    monkeypatch.setattr(msg, "check_win_reversal", lambda state, db_path: [critical_alert])
    monkeypatch.setattr(msg, "check_scenario_change", lambda state, db_path: [])
    monkeypatch.setattr(msg, "check_divergences", lambda state, db_path: [])
    monkeypatch.setattr(msg, "check_calendar_events", lambda state: [])
    monkeypatch.setattr(msg, "check_fear_greed", lambda state: [])

    state = msg.GuardianState(n_checks=1)

    new_alerts = msg.run_guardian_check(
        state,
        "ignored.sqlite",
        persist_to_universal_log=True,
    )

    assert [a.severity for a in new_alerts] == ["INFO", "WARNING", "CRITICAL"]
    assert recorded[0] == ("ensure", "ignored.sqlite")
    assert recorded[1][0] == "append"
    assert recorded[1][1] == "ignored.sqlite"

    persisted_events = recorded[1][2]
    assert [event["severity"] for event in persisted_events] == ["INFO", "WARNING", "CRITICAL"]
    assert [event["score_impacto"] for event in persisted_events] == [30, 65, 100]
    assert [event["tipo_evento"] for event in persisted_events] == [
        "INFO_EVENT",
        "WARNING_EVENT",
        "CRITICAL_EVENT",
    ]
