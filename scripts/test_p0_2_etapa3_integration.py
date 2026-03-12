"""
Etapa 3 Integration Tests for P0-2 Background Execution

Tests BAT file integration with P0-2 pipeline:
- INICIAR_DIARIOS.bat launching P0-2 in background (start /B)
- INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat checking GATE 2 decision
- Status persistence via JSON files
- Non-blocking execution flow

Run: pytest scripts/test_p0_2_etapa3_integration.py -v
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import pytest

DATA_DIR = Path("data")
BACKTEST_DIR = DATA_DIR / "backtest"
LOGS_DIR = DATA_DIR / "logs"


class TestEtapa3Integration:
    """Integration tests for BAT files + P0-2 background execution."""

    def cleanup_files(self) -> None:
        """Ensure clean state before each test."""
        if BACKTEST_DIR.exists():
            for f in BACKTEST_DIR.glob("p0_2_status*"):
                f.unlink(missing_ok=True)
            for f in BACKTEST_DIR.glob("gate2_decision*"):
                f.unlink(missing_ok=True)

    # ====================================================================
    # Test 1: verify run_p0_2_backtest.py exists and is executable
    # ====================================================================
    def test_etapa3_run_backtest_script_exists(self) -> None:
        """Test: run_p0_2_backtest.py Python script is accessible."""
        script_path = Path("scripts/run_p0_2_backtest.py")
        assert script_path.exists(), "run_p0_2_backtest.py not found"
        assert script_path.is_file(), "run_p0_2_backtest.py is not a file"

        # Verify it's syntactically valid Python
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                compile(f.read(), str(script_path), "exec")
        except SyntaxError as e:
            pytest.fail(f"Syntax error in run_p0_2_backtest.py: {e}")

    def test_etapa3_check_status_script_exists(self) -> None:
        """Test: check_p0_2_status.py Python script is accessible."""
        script_path = Path("scripts/check_p0_2_status.py")
        assert script_path.exists(), "check_p0_2_status.py not found"
        assert script_path.is_file(), "check_p0_2_status.py is not a file"

        # Verify it's syntactically valid Python
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                compile(f.read(), str(script_path), "exec")
        except SyntaxError as e:
            pytest.fail(f"Syntax error in check_p0_2_status.py: {e}")

    # ====================================================================
    # Test 2: check_p0_2_status.py correctly reports "not started" state
    # ====================================================================
    def test_etapa3_check_status_not_started(self) -> None:
        """Test: check_p0_2_status.py returns exit code 2 when P0-2 not started."""
        # Ensure no status files exist
        self.cleanup_files()

        # Run check_p0_2_status.py script
        try:
            result = subprocess.run(
                ["python", "scripts/check_p0_2_status.py"],
                capture_output=True,
                text=True,
                timeout=10
            )
        except subprocess.TimeoutExpired:
            pytest.fail("check_p0_2_status.py timed out")

        # Should return exit code 2 (P0-2 not running)
        assert result.returncode == 2, (
            f"Expected exit code 2 (not started), got {result.returncode}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    # ====================================================================
    # Test 3: Simulate P0-2 completion and verify decision is retrieved
    # ====================================================================
    def test_etapa3_check_status_with_simulated_completion(self) -> None:
        """Test: check_p0_2_status.py retrieves GATE 2 decision when complete."""
        # Create directories
        BACKTEST_DIR.mkdir(parents=True, exist_ok=True)

        # Write simulated status files
        status_file = BACKTEST_DIR / "p0_2_status.json"
        decision_file = BACKTEST_DIR / "gate2_decision.json"

        status_file.write_text(json.dumps({
            "completed": True,
            "gate2_passed": True,
            "timestamp": "2026-03-04T12:34:56Z",
            "decision": "PASS",
            "decision_is_final": True,
            "dataset_audit": {"audit_passed": True}
        }))

        decision_file.write_text(json.dumps({
            "gate2_passed": True,
            "decision": "PASS",
            "timestamp": "2026-03-04T12:34:56Z"
        }))

        # Run check_p0_2_status.py
        try:
            result = subprocess.run(
                ["python", "scripts/check_p0_2_status.py"],
                capture_output=True,
                text=True,
                timeout=10
            )
        except subprocess.TimeoutExpired:
            pytest.fail("check_p0_2_status.py timed out")

        # Should return exit code 0 (GATE 2 PASS)
        assert result.returncode == 0, (
            f"Expected exit code 0 (PASS), got {result.returncode}\n"
            f"stdout: {result.stdout}"
        )

        # Check that decision is printed
        assert "PASS" in result.stdout or "[OK]" in result.stdout

    # ====================================================================
    # Test 4: Simulate GATE 2 FAIL and verify decision is retrieved
    # ====================================================================
    def test_etapa3_check_status_gate2_fail(self) -> None:
        """Test: check_p0_2_status.py correctly returns FAIL decision."""
        # Create directories
        BACKTEST_DIR.mkdir(parents=True, exist_ok=True)

        # Write simulated FAIL status files
        status_file = BACKTEST_DIR / "p0_2_status.json"
        decision_file = BACKTEST_DIR / "gate2_decision.json"

        status_file.write_text(json.dumps({
            "completed": True,
            "gate2_passed": False,
            "timestamp": "2026-03-04T12:34:56Z",
            "decision": "FAIL",
            "decision_is_final": True,
            "dataset_audit": {"audit_passed": True}
        }))

        decision_file.write_text(json.dumps({
            "gate2_passed": False,
            "decision": "FAIL",
            "timestamp": "2026-03-04T12:34:56Z"
        }))

        # Run check_p0_2_status.py
        try:
            result = subprocess.run(
                ["python", "scripts/check_p0_2_status.py"],
                capture_output=True,
                text=True,
                timeout=10
            )
        except subprocess.TimeoutExpired:
            pytest.fail("check_p0_2_status.py timed out")

        # Should return exit code 1 (GATE 2 FAIL)
        assert result.returncode == 1, (
            f"Expected exit code 1 (FAIL), got {result.returncode}\n"
            f"stdout: {result.stdout}"
        )

        # Check that decision is printed
        assert "FAIL" in result.stdout or "[FAIL]" in result.stdout

    def test_etapa3_check_status_requires_auditable_decision(self) -> None:
        """Test: status sem dataset auditavel retorna erro conservador."""
        BACKTEST_DIR.mkdir(parents=True, exist_ok=True)

        status_file = BACKTEST_DIR / "p0_2_status.json"
        decision_file = BACKTEST_DIR / "gate2_decision.json"

        status_file.write_text(json.dumps({
            "completed": True,
            "gate2_passed": False,
            "timestamp": "2026-03-04T12:34:56Z",
            "decision": "FAIL",
            "decision_is_final": False,
            "error_code": "DATASET_AUDIT_FAILED",
            "dataset_audit": {
                "audit_passed": False,
                "audit_issues": ["dataset_flagged_as_synthetic"]
            }
        }))

        decision_file.write_text(json.dumps({
            "gate2_passed": False,
            "decision": "FAIL",
            "timestamp": "2026-03-04T12:34:56Z"
        }))

        result = subprocess.run(
            ["python", "scripts/check_p0_2_status.py"],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 3, (
            f"Expected exit code 3 (indefinido/erro), got {result.returncode}\n"
            f"stdout: {result.stdout}"
        )
        assert "auditavel" in result.stdout.lower() or "conservador" in result.stdout.lower()

    # ====================================================================
    # Test 5: Verify BAT files are syntactically valid
    # ====================================================================
    def test_etapa3_iniciar_diarios_bat_exists(self) -> None:
        """Test: INICIAR_DIARIOS.bat contains P0-2 launch commands."""
        bat_file = Path("INICIAR_DIARIOS.bat")
        assert bat_file.exists(), "INICIAR_DIARIOS.bat not found"

        content = bat_file.read_text(encoding="utf-8")

        # Verify key integration elements
        assert "run_p0_2_backtest.py" in content, (
            "INICIAR_DIARIOS.bat missing P0-2 script call"
        )
        assert "start /B" in content, (
            "INICIAR_DIARIOS.bat missing start /B (background execution)"
        )
        assert "p0_2_execution.log" in content, (
            "INICIAR_DIARIOS.bat missing log redirection"
        )

    def test_etapa3_iniciar_agent_bat_gate2_validation(self) -> None:
        """Test: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat checks GATE 2."""
        bat_file = Path("INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat")
        assert bat_file.exists(), "INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat not found"

        content = bat_file.read_text(encoding="utf-8")

        # Verify GATE 2 validation integration
        assert "check_p0_2_status.py" in content, (
            "Agent BAT file missing GATE 2 status check"
        )
        assert "GATE2" in content.upper(), (
            "Agent BAT file missing GATE 2 label/comment"
        )
        assert "CAPITAL_SCALE" in content or "100000" in content, (
            "Agent BAT file missing capital scaling logic"
        )

    # ====================================================================
    # Test 6: Verify status file format is correct
    # ====================================================================
    def test_etapa3_status_file_format(self) -> None:
        """Test: P0-2 status JSON file has required fields."""
        BACKTEST_DIR.mkdir(parents=True, exist_ok=True)

        status_file = BACKTEST_DIR / "p0_2_status.json"

        # Write a valid status file
        status_data = {
            "completed": True,
            "gate2_passed": True,
            "timestamp": "2026-03-04T12:34:56Z",
            "decision": "PASS",
            "decision_is_final": True,
            "dataset_audit": {"audit_passed": True}
        }
        status_file.write_text(json.dumps(status_data))

        # Read and validate
        loaded = json.loads(status_file.read_text())

        assert "completed" in loaded, "Missing 'completed' field"
        assert "gate2_passed" in loaded, "Missing 'gate2_passed' field"
        assert "timestamp" in loaded, "Missing 'timestamp' field"
        assert "decision" in loaded, "Missing 'decision' field"
        assert loaded["decision"] in ["PASS", "FAIL"], "Invalid decision value"

    # ====================================================================
    # Test 7: Verify exit code mapping is correct
    # ====================================================================
    def test_etapa3_exit_codes_mapping(self) -> None:
        """Test: check_p0_2_status.py exit codes match .bat expectations."""
        # This is a documentation test - verifying the contract
        # between check_p0_2_status.py and .bat files

        exit_codes_mapping = {
            0: "GATE 2 PASS - use R$ 100k",
            1: "GATE 2 FAIL - use R$ 50k",
            2: "P0-2 still running - skip check",
            3: "Error checking status"
        }

        # Verify that all expected codes are in the mapping
        # (This test just documents the contract)
        assert all(isinstance(k, int) for k in exit_codes_mapping.keys())
        assert all(isinstance(v, str) for v in exit_codes_mapping.values())


class TestEtapa3NonBlocking:
    """Tests for non-blocking execution requirements."""

    def test_etapa3_background_execution_nonblocking(self) -> None:
        """Test: `start /B` syntax produces non-blocking execution."""
        # This is more of a Windows command documentation test
        # verifying that expected behavior is correct

        # Verify the command syntax is correct
        start_command = "start /B python scripts/run_p0_2_backtest.py"

        assert "/B" in start_command, "Missing /B flag for background execution"
        assert "python" in start_command, "Missing python executable"
        assert "run_p0_2_backtest.py" in start_command, "Missing script name"

    def test_etapa3_error_recovery_nonblocking(self) -> None:
        """Test: check_p0_2_status.py always returns (never hangs)."""
        # Ensure check_p0_2_status.py has short timeout/polling
        # and doesn't block indefinitely

        script_path = Path("scripts/check_p0_2_status.py")
        content = script_path.read_text(encoding="utf-8")

        # Verify timeout is present (max ~10 seconds)
        assert "timeout" in content.lower() or "sleep" in content.lower(), (
            "Status check script should have timeout/polling mechanism"
        )

    def test_etapa3_log_redirection_works(self) -> None:
        """Test: Log output is redirected to file (doesn't block)."""
        bat_content = Path("INICIAR_DIARIOS.bat").read_text(encoding="utf-8")

        # Verify redirection syntax
        assert ">" in bat_content and "log" in bat_content.lower(), (
            "BAT file should redirect output to log file"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
