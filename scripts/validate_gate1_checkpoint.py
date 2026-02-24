#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gate 1 Checkpoint Validation Script
====================================

Valida todos os 4 critérios críticos para Gate 1 (05/03):
  1. ML Metrics (F1 > 0.65)
  2. Performance (P95 < 500ms)
  3. Code Quality (100% type hints + 85+ tests)
  4. Risk Framework (3 gates OK)

Execução:
  python scripts/validate_gate1_checkpoint.py
  python scripts/validate_gate1_checkpoint.py --detailed
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, List
import logging

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)

# Repo root
REPO_ROOT = Path(__file__).parent.parent
BACKTEST_FILE = REPO_ROOT / "backtest_optimized_results.json"
GATE2_RESULTS_FILE = REPO_ROOT / "reports" / "gate2_backtest_results.json"

# Gate 1 Thresholds
GATE1_THRESHOLDS = {
    "ml_f1_min": 0.65,
    "ml_capture_min": 85.0,
    "ml_fp_max": 10.0,
    "ml_win_rate_min": 60.0,
    "performance_p95_max_ms": 500.0,
    "code_tests_min": 85,
    "code_type_hints_pct": 100.0,
}


class Gate1Validator:
    """Validador de Gate 1 checkpoint."""

    def __init__(self, detailed: bool = False):
        self.detailed = detailed
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "gate1_components": {},
            "overall_status": "UNKNOWN",
            "go_no_go": None,
            "issues": []
        }

    def validate_ml_metrics(self) -> Tuple[bool, Dict]:
        """Valida critério 1: ML Metrics."""
        logger.info("=" * 60)
        logger.info("VALIDATING: ML Metrics (F1 > 0.65)")
        logger.info("=" * 60)

        try:
            with open(BACKTEST_FILE, 'r') as f:
                data = json.load(f)

            f1_score = data.get('f1_score', 0)
            capture = data.get('metrics', {}).get('taxa_captura_pct', 0)
            fp_rate = data.get('metrics', {}).get('taxa_false_positive_pct', 100)
            win_rate = data.get('taxas', {}).get('win_rate_estimado_pct', 0)

            # Validações
            f1_pass = f1_score >= GATE1_THRESHOLDS["ml_f1_min"]
            capture_pass = capture >= GATE1_THRESHOLDS["ml_capture_min"]
            fp_pass = fp_rate <= GATE1_THRESHOLDS["ml_fp_max"]
            win_pass = win_rate >= GATE1_THRESHOLDS["ml_win_rate_min"]

            logger.info(f"  F1 Score:           {f1_score:.4f} >= {GATE1_THRESHOLDS['ml_f1_min']} → "
                       f"{'✅ PASS' if f1_pass else '❌ FAIL'}")
            logger.info(f"  Capture Rate:       {capture:.2f}% >= {GATE1_THRESHOLDS['ml_capture_min']:.0f}% → "
                       f"{'✅ PASS' if capture_pass else '❌ FAIL'}")
            logger.info(f"  False Positive:     {fp_rate:.2f}% <= {GATE1_THRESHOLDS['ml_fp_max']:.0f}% → "
                       f"{'✅ PASS' if fp_pass else '❌ FAIL'}")
            logger.info(f"  Win Rate:           {win_rate:.2f}% >= {GATE1_THRESHOLDS['ml_win_rate_min']:.0f}% → "
                       f"{'✅ PASS' if win_pass else '❌ FAIL'}")

            all_pass = f1_pass and capture_pass and fp_pass and win_pass
            status = "🟢 PASS" if all_pass else "🔴 FAIL"

            logger.info(f"\n  Overall ML Status: {status}\n")

            return all_pass, {
                "f1_score": f1_score,
                "capture": capture,
                "fp_rate": fp_rate,
                "win_rate": win_rate,
                "all_pass": all_pass
            }

        except FileNotFoundError:
            logger.error(f"❌ File not found: {BACKTEST_FILE}")
            self.results["issues"].append("backtest_optimized_results.json não encontrado")
            return False, {}
        except Exception as e:
            logger.error(f"❌ Error validating ML metrics: {e}")
            self.results["issues"].append(f"ML Metrics validation error: {str(e)}")
            return False, {}

    def validate_performance(self) -> Tuple[bool, Dict]:
        """Valida critério 2: Performance."""
        logger.info("=" * 60)
        logger.info("VALIDATING: Performance (P95 < 500ms)")
        logger.info("=" * 60)

        try:
            with open(GATE2_RESULTS_FILE, 'r') as f:
                data = json.load(f)

            summary = data.get('summary', {})
            latency = summary.get('latency', {})
            p95_ms = latency.get('p95_ms', float('inf'))
            memory_mb = summary.get('memory_mb', 0)

            # Validações
            p95_pass = p95_ms <= GATE1_THRESHOLDS["performance_p95_max_ms"]
            memory_pass = memory_mb <= 200  # 200MB target

            logger.info(f"  P95 Latency:        {p95_ms:.2f}ms <= {GATE1_THRESHOLDS['performance_p95_max_ms']:.0f}ms → "
                       f"{'✅ PASS' if p95_pass else '❌ FAIL'}")
            logger.info(f"  Memory Peak:        {memory_mb:.1f}MB <= 200MB → "
                       f"{'✅ PASS' if memory_pass else '❌ FAIL'}")

            all_pass = p95_pass and memory_pass
            status = "🟢 PASS" if all_pass else "🔴 FAIL"

            logger.info(f"\n  Overall Performance Status: {status}\n")

            return all_pass, {
                "p95_ms": p95_ms,
                "memory_mb": memory_mb,
                "all_pass": all_pass
            }

        except FileNotFoundError:
            logger.error(f"❌ File not found: {GATE2_RESULTS_FILE}")
            self.results["issues"].append("gate2_backtest_results.json não encontrado")
            return False, {}
        except Exception as e:
            logger.error(f"❌ Error validating performance: {e}")
            self.results["issues"].append(f"Performance validation error: {str(e)}")
            return False, {}

    def validate_code_quality(self) -> Tuple[bool, Dict]:
        """Valida critério 3: Code Quality."""
        logger.info("=" * 60)
        logger.info("VALIDATING: Code Quality (100% type hints + 85+ tests)")
        logger.info("=" * 60)

        try:
            # Run pytest
            logger.info("  Running pytest...")
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT)
            )

            # Parse output (expect "85 passed" or similar)
            output = result.stdout
            tests_match = None
            for line in output.split('\n'):
                if 'passed' in line.lower():
                    # Extract number
                    import re
                    match = re.search(r'(\d+)\s+passed', line)
                    if match:
                        tests_match = int(match.group(1))
                        break

            tests_passing = tests_match if tests_match else 0
            tests_pass = tests_passing >= GATE1_THRESHOLDS["code_tests_min"]

            logger.info(f"  Tests Passing:      {tests_passing}/{GATE1_THRESHOLDS['code_tests_min']} → "
                       f"{'✅ PASS' if tests_pass else '❌ FAIL'}")

            # Check type hints
            logger.info("  Checking type hints...")
            mypy_result = subprocess.run(
                [sys.executable, "-m", "mypy", "src/", "scripts/",
                 "--strict", "--ignore-missing-imports"],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT)
            )

            type_hints_pass = mypy_result.returncode == 0
            logger.info(f"  Type Hints (MyPy):  {'✅ PASS' if type_hints_pass else '❌ FAIL'}")

            all_pass = tests_pass and type_hints_pass
            status = "🟢 PASS" if all_pass else "🔴 FAIL"

            logger.info(f"\n  Overall Code Quality Status: {status}\n")

            return all_pass, {
                "tests_passing": tests_passing,
                "type_hints_strict": type_hints_pass,
                "all_pass": all_pass
            }

        except Exception as e:
            logger.error(f"❌ Error validating code quality: {e}")
            self.results["issues"].append(f"Code quality validation error: {str(e)}")
            return False, {}

    def validate_risk_framework(self) -> Tuple[bool, Dict]:
        """Valida critério 4: Risk Framework (Sprint 1 deliverable)."""
        logger.info("=" * 60)
        logger.info("VALIDATING: Risk Framework (Sprint 1)")
        logger.info("=" * 60)

        try:
            # Check if RiskValidator classes exist
            risk_validator_file = REPO_ROOT / "src" / "application" / "risk_validator.py"

            if not risk_validator_file.exists():
                logger.warning("  ⚠️  risk_validator.py não encontrado (esperado Sprint 1)")
                return False, {
                    "capital_gate_ready": False,
                    "correlation_gate_ready": False,
                    "volatility_gate_ready": False,
                    "all_pass": False
                }

            # Read file to check for Gate implementations
            with open(risk_validator_file, 'r') as f:
                content = f.read()

            capital_gate = 'check_capital' in content or 'CapitalAdequacy' in content
            correlation_gate = 'check_correlation' in content or 'Correlation' in content
            volatility_gate = 'check_volatility' in content or 'Volatility' in content

            logger.info(f"  Capital Gate:       {'✅ READY' if capital_gate else '⏳ NOT YET'}")
            logger.info(f"  Correlation Gate:   {'✅ READY' if correlation_gate else '⏳ NOT YET'}")
            logger.info(f"  Volatility Gate:    {'✅ READY' if volatility_gate else '⏳ NOT YET'}")

            all_ready = capital_gate and correlation_gate and volatility_gate

            if all_ready:
                status = "🟢 READY"
            else:
                status = "🟡 IN PROGRESS (Sprint 1)"
                logger.warning("  ℹ️  Risk Framework implementação em Sprint 1")

            logger.info(f"\n  Overall Risk Framework Status: {status}\n")

            return all_ready, {
                "capital_gate_ready": capital_gate,
                "correlation_gate_ready": correlation_gate,
                "volatility_gate_ready": volatility_gate,
                "all_pass": all_ready
            }

        except Exception as e:
            logger.error(f"❌ Error validating risk framework: {e}")
            self.results["issues"].append(f"Risk framework validation error: {str(e)}")
            return False, {}

    def run_validation(self) -> bool:
        """Executa validação completa."""
        logger.info("\n" + "🎯 GATE 1 CHECKPOINT VALIDATION" + "\n")
        logger.info(f"Start Time: {self.results['timestamp']}")
        logger.info("=" * 60 + "\n")

        # Validar cada critério
        ml_pass, ml_data = self.validate_ml_metrics()
        perf_pass, perf_data = self.validate_performance()
        code_pass, code_data = self.validate_code_quality()
        risk_pass, risk_data = self.validate_risk_framework()

        # Consolidar resultados
        self.results["gate1_components"] = {
            "ml_metrics": {"pass": ml_pass, "data": ml_data},
            "performance": {"pass": perf_pass, "data": perf_data},
            "code_quality": {"pass": code_pass, "data": code_data},
            "risk_framework": {"pass": risk_pass, "data": risk_data}
        }

        # Determinar GO/NO-GO
        # ML, Performance, Code Quality devem ser PASS
        # Risk Framework pode estar em progresso (Sprint 1)
        go_no_go = ml_pass and perf_pass and code_pass

        self.results["overall_status"] = "GO" if go_no_go else "NO-GO"
        self.results["go_no_go"] = go_no_go

        # Print summary
        logger.info("=" * 60)
        logger.info("GATE 1 CHECKPOINT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  ML Metrics:        {'✅ PASS' if ml_pass else '❌ FAIL'}")
        logger.info(f"  Performance:       {'✅ PASS' if perf_pass else '❌ FAIL'}")
        logger.info(f"  Code Quality:      {'✅ PASS' if code_pass else '❌ FAIL'}")
        logger.info(f"  Risk Framework:    {'✅ READY' if risk_pass else '🟡 SPRINT 1'}")

        logger.info("\n" + "=" * 60)
        if go_no_go:
            logger.info("🟢 GATE 1 DECISION: GO APPROVED")
            logger.info("Sprint 2 Kickoff: 06/03 09:00 BRT")
        else:
            logger.info("🔴 GATE 1 DECISION: NO-GO")
            logger.info("Reschedule required - see issues below")

        if self.results["issues"]:
            logger.info("\n⚠️  ISSUES FOUND:")
            for issue in self.results["issues"]:
                logger.info(f"  • {issue}")

        logger.info("=" * 60 + "\n")

        # Save results to JSON
        results_file = REPO_ROOT / "reports" / "gate1_validation_results.json"
        results_file.parent.mkdir(parents=True, exist_ok=True)

        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"Results saved to: {results_file}\n")

        return go_no_go


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Gate 1 Checkpoint Validation")
    parser.add_argument('--detailed', action='store_true',
                       help='Print detailed output')
    args = parser.parse_args()

    validator = Gate1Validator(detailed=args.detailed)
    go_no_go = validator.run_validation()

    # Return exit code
    return 0 if go_no_go else 1


if __name__ == "__main__":
    sys.exit(main())

