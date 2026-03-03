#!/usr/bin/env python
"""
run_e2e_tests.py — Simple E2E test runner
"""

import subprocess
import sys

print("=" * 70)
print("EXECUTANDO E2E TESTS (Task 6)")
print("=" * 70)

result = subprocess.run(
    ["python", "-m", "pytest", "tests/integration/test_score_e2e_integration.py", "-v"],
    capture_output=False
)

sys.exit(result.returncode)
