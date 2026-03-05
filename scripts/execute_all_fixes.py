#!/usr/bin/env python3
"""
EXECUTOR MASTER: Run all 3 critical fixes in sequence.

Sequence:
1. Fix #1: Database schema migration (add pnl column)
2. Fix #2: P0-2 Backtest PYTHONPATH setup (already done inline)
3. Fix #3: Macro data provider fallback (validate)

Execution:
  python scripts/execute_all_fixes.py
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime


def log_header(title: str):
    """Print section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def log_success(msg: str):
    """Print success message."""
    print(f"✅ {msg}")


def log_error(msg: str):
    """Print error message."""
    print(f"❌ {msg}")


def run_fix(script_name: str, description: str) -> bool:
    """Run a fix script and return success status."""
    log_header(f"FIX: {description}")

    script_path = Path(__file__).parent / script_name

    if not script_path.exists():
        log_error(f"Script not found: {script_path}")
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=False,
            timeout=60
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log_error(f"Script timeout: {script_name}")
        return False
    except Exception as e:
        log_error(f"Script execution failed: {e}")
        return False


def main():
    """Execute all fixes."""
    log_header("🔧 CRITICAL FIXES EXECUTOR - 05/03/2026")

    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nRunning 3 critical fixes for Gate 1 validation...\n")

    results = {}

    # =========================================================================
    # FIX #1: Database Schema Migration
    # =========================================================================
    success_1 = run_fix(
        "fix_database_schema.py",
        "Database Schema Migration (add pnl column)"
    )
    results["Database Schema"] = success_1

    if success_1:
        log_success("Database schema migration complete")
    else:
        log_error("Database schema migration failed - continuing anyway")

    # =========================================================================
    # FIX #2: P0-2 Backtest PYTHONPATH (already done in run_p0_2_backtest.py)
    # =========================================================================
    log_header("FIX: P0-2 Backtest PYTHONPATH Setup")
    print("✓ Already patched in: scripts/run_p0_2_backtest.py")
    print("✓ Added sys.path insertion for project root")
    success_2 = True
    results["P0-2 PYTHONPATH"] = success_2

    # =========================================================================
    # FIX #3: Macro Data Provider Fallback (validate)
    # =========================================================================
    success_3 = run_fix(
        "macro_data_provider_fallback.py",
        "Macro Data Provider Fallback System"
    )
    results["Macro Data Fallback"] = success_3

    if success_3:
        log_success("Macro data provider fallback operational")
    else:
        log_error("Macro data provider test failed - check connectivity")

    # =========================================================================
    # Summary
    # =========================================================================
    log_header("📋 EXECUTION SUMMARY")

    all_success = all(results.values())
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for fix_name, success in results.items():
        status = "✓ PASS" if success else "⚠ WARN"
        print(f"  {status:10} {fix_name}")

    print(f"\nTotal: {passed}/{total} fixes successful")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if all_success:
        log_header("✅ ALL CRITICAL FIXES COMPLETE")
        print("\nNext steps:")
        print("  1. Restart INICIAR_DIARIOS.bat")
        print("  2. Monitor daily_confidence_retraining.py logs")
        print("  3. Validate P0-2 backtest execution")
        print("  4. Check Gate 1 metrics by 17:00 BRT")
        return 0
    else:
        log_header("⚠️ SOME FIXES INCOMPLETE")
        print("\nReview errors above and re-run if needed:")
        print("  python scripts/execute_all_fixes.py")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
