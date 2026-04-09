"""Testes do enforcer de isolamento estrito do terminal MT5."""

from __future__ import annotations

import pytest

from src.infrastructure.terminal_isolation_enforcer import (
    TerminalIsolationEnforcer,
    TerminalIsolationViolation,
)


class TestTerminalIsolationEnforcerStrictMode:
    """Valida que o enforcer fixa o uso da Clear sem bloquear outros MT5."""

    def test_validate_before_operation_tolera_outro_terminal_quando_clear_esta_ok(self, monkeypatch: pytest.MonkeyPatch) -> None:
        enforcer = TerminalIsolationEnforcer(
            expected_terminal_path=r"C:\Program Files\Clear Investimentos MT5 Terminal\terminal64.exe",
            enforce_mode="HARD_STOP",
        )

        monkeypatch.setattr(
            "os.path.exists",
            lambda _path: True,
        )
        monkeypatch.setattr(enforcer, "_find_clear_terminal_pids", lambda: [12345])
        monkeypatch.setattr(
            enforcer,
            "_find_dangerous_terminals",
            lambda: "UNEXPECTED_MT5 (PID:999, exe:C:/Program Files/FBS MetaTrader 5/terminal64.exe)",
        )

        assert enforcer.validate_before_operation("launcher_preflight") is True
        status = enforcer.get_isolation_status()
        assert status["clear_terminal_running"] is True
        assert "UNEXPECTED_MT5" in str(status["dangerous_terminals_detected"])
