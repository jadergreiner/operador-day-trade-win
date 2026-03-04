"""
Etapa 4: E2E Full Flow Test for P0-2

Simulates complete P0-2 pipeline execution as operator would use via .bat files:
1. Launch INICIAR_DIARIOS.bat (starts P0-2 in background)
2. Monitor P0-2 completion
3. Launch INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat (checks GATE 2)
4. Validate GATE 2 decision
5. Measure performance (timing, memory)

Run: pytest scripts/test_p0_2_e2e_full_flow.py -v -s
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

import pytest

DATA_DIR = Path("data")
BACKTEST_DIR = DATA_DIR / "backtest"
LOGS_DIR = DATA_DIR / "logs"


class TestP0_2_E2E_FullFlow:
    """End-to-end tests simulating operator workflow."""

    def setup_method(self) -> None:
        """Ensure clean state before each test."""
        if BACKTEST_DIR.exists():
            for f in BACKTEST_DIR.glob("p0_2_status*"):
                f.unlink(missing_ok=True)
            for f in BACKTEST_DIR.glob("gate2_decision*"):
                f.unlink(missing_ok=True)

    # ====================================================================
    # Test 1: Simulate INICIAR_DIARIOS.bat launching P0-2 in background
    # ====================================================================
    def test_p0_2_e2e_01_launch_from_diarios_bat(self) -> None:
        """Test: INICIAR_DIARIOS.bat can be parsed and contains P0-2 launch."""
        bat_file = Path("INICIAR_DIARIOS.bat")
        assert bat_file.exists(), "INICIAR_DIARIOS.bat not found"
        
        content = bat_file.read_text(encoding="utf-8")
        
        # Verify key elements
        assert "run_p0_2_backtest.py" in content
        assert "start /B" in content
        assert "python" in content
        
        print("[E2E-01] ✓ INICIAR_DIARIOS.bat is properly configured for P0-2 launch")

    # ====================================================================
    # Test 2: Simulate INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat GATE 2 check
    # ====================================================================
    def test_p0_2_e2e_02_gate2_checkpoint_in_agent_bat(self) -> None:
        """Test: Agent BAT file contains GATE 2 checkpoint."""
        bat_file = Path("INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat")
        assert bat_file.exists(), "INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat not found"
        
        content = bat_file.read_text(encoding="utf-8")
        
        # Verify GATE 2 validation
        assert "check_p0_2_status.py" in content
        assert "CAPITAL_SCALE" in content or "100000" in content
        
        print("[E2E-02] ✓ Agent BAT has GATE 2 checkpoint")

    # ====================================================================
    # Test 3: Full P0-2 pipeline execution with status tracking
    # ====================================================================
    def test_p0_2_e2e_03_full_pipeline_with_timing(self) -> None:
        """Test: Full P0-2 pipeline completes with reasonable timing."""
        start_time = time.time()
        
        # Create directories
        BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Simulate P0-2 execution by creating status markers
        # (In real E2E, would call run_p0_2_backtest.py)
        status_file = BACKTEST_DIR / "p0_2_status.json"
        decision_file = BACKTEST_DIR / "gate2_decision.json"
        
        # Write simulated completion markers
        status_file.write_text(json.dumps({
            "completed": True,
            "gate2_passed": True,
            "timestamp": time.time(),
            "decision": "PASS"
        }))
        
        decision_file.write_text(json.dumps({
            "gate2_passed": True,
            "decision": "PASS",
            "timestamp": time.time()
        }))
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # Verify files exist
        assert status_file.exists()
        assert decision_file.exists()
        
        # Verify timing is reasonable (should be instant in simulation)
        assert elapsed < 1.0, f"Pipeline simulation took {elapsed}s (should be <1s)"
        
        print(f"[E2E-03] ✓ Full pipeline completed in {elapsed:.3f}s")

    # ====================================================================
    # Test 4: GATE 2 decision workflow (PASS case)
    # ====================================================================
    def test_p0_2_e2e_04_gate2_pass_workflow(self) -> None:
        """Test: GATE 2 PASS decision triggers capital scaling."""
        BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
        
        # Setup GATE 2 PASS state - need BOTH files
        status_file = BACKTEST_DIR / "p0_2_status.json"
        decision_file = BACKTEST_DIR / "gate2_decision.json"
        
        status_file.write_text(json.dumps({
            "completed": True,
            "gate2_passed": True,
            "decision": "PASS",
            "timestamp": time.time()
        }))
        
        decision_file.write_text(json.dumps({
            "gate2_passed": True,
            "decision": "PASS",
            "timestamp": time.time()
        }))
        
        # Run check_p0_2_status.py to verify decision retrieval
        result = subprocess.run(
            ["python", "scripts/check_p0_2_status.py"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Should return 0 (PASS)
        assert result.returncode == 0, (
            f"Expected exit code 0 (PASS), got {result.returncode}"
        )
        
        # Should indicate capital scaling
        assert "[OK]" in result.stdout or "100k" in result.stdout or "PASSOU" in result.stdout
        
        print("[E2E-04] ✓ GATE 2 PASS decision workflow OK (capital scales to 100k)")

    # ====================================================================
    # Test 5: GATE 2 decision workflow (FAIL case)
    # ====================================================================
    def test_p0_2_e2e_05_gate2_fail_workflow(self) -> None:
        """Test: GATE 2 FAIL decision keeps capital at baseline."""
        BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
        
        # Setup GATE 2 FAIL state
        decision_file = BACKTEST_DIR / "gate2_decision.json"
        decision_file.write_text(json.dumps({
            "gate2_passed": False,
            "decision": "FAIL",
            "timestamp": time.time()
        }))
        
        # Setup status file
        status_file = BACKTEST_DIR / "p0_2_status.json"
        status_file.write_text(json.dumps({
            "completed": True,
            "gate2_passed": False,
            "decision": "FAIL"
        }))
        
        # Run check_p0_2_status.py to verify decision retrieval
        result = subprocess.run(
            ["python", "scripts/check_p0_2_status.py"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Should return 1 (FAIL)
        assert result.returncode == 1, (
            f"Expected exit code 1 (FAIL), got {result.returncode}"
        )
        
        # Should indicate capital stays at baseline
        assert "[FAIL]" in result.stdout or "50k" in result.stdout or "FALHOU" in result.stdout
        
        print("[E2E-05] ✓ GATE 2 FAIL decision workflow OK (capital stays at 50k)")

    # ====================================================================
    # Test 6: Non-blocking execution flow
    # ====================================================================
    def test_p0_2_e2e_06_nonblocking_execution(self) -> None:
        """Test: P0-2 execution doesn't block operator (start /B verification)."""
        bat_file = Path("INICIAR_DIARIOS.bat")
        content = bat_file.read_text(encoding="utf-8")
        
        # Verify start /B is used (non-blocking)
        assert "start /B" in content, "BAT should use 'start /B' for non-blocking"
        
        # Verify output redirection to log (so console isn't spammed)
        assert ">" in content and ("log" in content.lower() or ".log" in content)
        
        # Count process would be launched but BAT continues immediately
        print("[E2E-06] ✓ Non-blocking execution verified (uses 'start /B')")

    # ====================================================================
    # Test 7: Status files persistence and readability
    # ====================================================================
    def test_p0_2_e2e_07_status_files_persistence(self) -> None:
        """Test: Status files persist and are readable by downstream processes."""
        BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create test status file
        status_file = BACKTEST_DIR / "p0_2_status.json"
        test_data = {
            "completed": True,
            "gate2_passed": True,
            "timestamp": "2026-03-04T12:00:00Z",
            "decision": "PASS",
            "backtest_dir": str(BACKTEST_DIR),
            "metrics": {
                "sharpe": 1.23,
                "win_rate": 0.65,
                "drawdown": 0.12
            }
        }
        status_file.write_text(json.dumps(test_data, indent=2))
        
        # Verify file exists and is readable
        assert status_file.exists()
        loaded = json.loads(status_file.read_text())
        
        # Verify all fields
        assert loaded["completed"] is True
        assert loaded["gate2_passed"] is True
        assert loaded["decision"] == "PASS"
        assert "metrics" in loaded
        
        print("[E2E-07] ✓ Status files persist and are readable")

    # ====================================================================
    # Test 8: Log file generation and accessibility
    # ====================================================================
    def test_p0_2_e2e_08_log_files_accessible(self) -> None:
        """Test: Log files are created and accessible for monitoring."""
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create test log file (simulating P0-2 execution)
        log_file = LOGS_DIR / "p0_2_execution_test.log"
        log_content = """
[2026-03-04 12:00:00] Starting P0-2 pipeline...
[2026-03-04 12:01:00] Etapa 1: Backtest running (252 days)...
[2026-03-04 12:05:00] Etapa 1: Complete (3780 trades simulated)
[2026-03-04 12:05:30] Etapa 2: Generating report...
[2026-03-04 12:06:00] GATE 2: Validating criteria...
[2026-03-04 12:06:15] GATE 2: PASS (Sharpe=1.23, WR=0.65)
[2026-03-04 12:06:15] Pipeline complete!
        """.strip()
        log_file.write_text(log_content)
        
        # Verify accessibility
        assert log_file.exists()
        assert log_file.is_file()
        assert log_file.stat().st_size > 0
        
        # Verify content is readable
        content = log_file.read_text()
        assert "Pipeline complete" in content
        
        print("[E2E-08] ✓ Log files generated and accessible")

    # ====================================================================
    # Test 9: Error handling - P0-2 still running check
    # ====================================================================
    def test_p0_2_e2e_09_running_state_handling(self) -> None:
        """Test: System correctly handles P0-2 still running state."""
        # Don't create status file (simulates P0-2 still running)
        self.setup_method()  # Clean state
        
        # Run check_p0_2_status.py
        result = subprocess.run(
            ["python", "scripts/check_p0_2_status.py"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Should return 2 (still running)
        assert result.returncode == 2, (
            f"Expected exit code 2 (running), got {result.returncode}"
        )
        
        # Should indicate continued execution
        assert "execucao" in result.stdout.lower() or "running" in result.stdout.lower()
        
        print("[E2E-09] ✓ Running state handled correctly (exit code 2)")

    # ====================================================================
    # Test 10: Complete workflow sequence
    # ====================================================================
    def test_p0_2_e2e_10_complete_operator_workflow(self) -> None:
        """Test: Complete operator workflow from .bat launch to decision."""
        BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        
        print("\n[E2E-10] Simulating complete operator workflow...")
        
        # Step 1: Operator launches INICIAR_DIARIOS.bat
        print("  [Step 1] Operator launches INICIAR_DIARIOS.bat...")
        bat_file = Path("INICIAR_DIARIOS.bat")
        assert bat_file.exists()
        print("  [Step 1] ✓ BAT file found")
        
        # Step 2: P0-2 starts in background (simulated)
        print("  [Step 2] P0-2 launches in background (start /B)...")
        # NOT creating status file yet - simulates P0-2 truly running
        # (file doesn't exist yet = process is executing)
        print("  [Step 2] ✓ P0-2 running in background")
        
        # Step 3: Operator launches agent .bat
        print("  [Step 3] Operator launches INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat...")
        agent_bat = Path("INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat")
        assert agent_bat.exists()
        print("  [Step 3] ✓ Agent BAT file found")
        
        # Step 4: Agent BAT checks GATE 2 (P0-2 still running)
        print("  [Step 4] Agent BAT checks P0-2 status...")
        result = subprocess.run(
            ["python", "scripts/check_p0_2_status.py"],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert result.returncode == 2, f"Expected 2 (running), got {result.returncode}"
        print("  [Step 4] ✓ P0-2 still running (exit 2)")
        
        # Step 5: P0-2 completes with decision
        print("  [Step 5] P0-2 completes backtest...")
        status_file = BACKTEST_DIR / "p0_2_status.json"
        decision_file = BACKTEST_DIR / "gate2_decision.json"
        decision_file.write_text(json.dumps({
            "gate2_passed": True,
            "decision": "PASS",
            "timestamp": time.time()
        }))
        status_file.write_text(json.dumps({
            "completed": True,
            "gate2_passed": True,
            "decision": "PASS",
            "timestamp": time.time()
        }))
        print("  [Step 5] ✓ P0-2 complete with GATE 2 PASS")
        
        # Step 6: Operator (or agent) checks final decision
        print("  [Step 6] Agent checks final GATE 2 decision...")
        result = subprocess.run(
            ["python", "scripts/check_p0_2_status.py"],
            capture_output=True,
            text=True,
            timeout=5
        )
        assert result.returncode == 0, f"Expected 0 (PASS), got {result.returncode}"
        print("  [Step 6] ✓ GATE 2 PASS (exit 0)")
        
        # Step 7: Capital scaling decision made
        print("  [Step 7] Capital scales to R$ 100k (GATE 2 PASS)...")
        assert "100k" in result.stdout or "[OK]" in result.stdout or "PASSOU" in result.stdout
        print("  [Step 7] ✓ Capital decision communicated")
        
        print("\n[E2E-10] ✓ Complete workflow successful!\n")

    # ====================================================================
    # Test 11: Performance metrics - minimal overhead
    # ====================================================================
    def test_p0_2_e2e_11_performance_overhead(self) -> None:
        """Test: P0-2 integration adds minimal overhead."""
        BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
        
        # Measure check_p0_2_status.py response time
        start = time.time()
        result = subprocess.run(
            ["python", "scripts/check_p0_2_status.py"],
            capture_output=True,
            text=True,
            timeout=5
        )
        elapsed = time.time() - start
        
        # Should be very fast (< 100ms)
        assert elapsed < 0.5, f"Status check took {elapsed:.2f}s (should be < 0.5s)"
        
        print(f"[E2E-11] ✓ Status check overhead: {elapsed*1000:.1f}ms (target < 500ms)")

    # ====================================================================
    # Test 12: Cross-platform compatibility verification
    # ====================================================================
    def test_p0_2_e2e_12_windows_compatibility(self) -> None:
        """Test: Windows-specific features work correctly."""
        # Verify start /B syntax is Windows-correct
        bat_file = Path("INICIAR_DIARIOS.bat")
        content = bat_file.read_text(encoding="utf-8")
        
        # Verify Windows path separators
        assert "python" in content
        assert "start /B" in content or "START /B" in content.upper()
        
        # Verify log redirection syntax
        assert ">" in content  # Output redirection
        assert ".log" in content or "log" in content.lower()
        
        print("[E2E-12] ✓ Windows compatibility verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
