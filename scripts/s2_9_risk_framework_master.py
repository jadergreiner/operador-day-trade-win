#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

"""S2-9: Risk Framework Validation — Master Orchestrator"""

import subprocess
from pathlib import Path
from datetime import datetime


def run_ac_script(ac_name: str, script_path: str, timeout: int = 600) -> tuple:
    """Execute AC script and return (success, output)"""
    try:
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout
        )
        stdout = result.stdout if result.stdout else ""
        stderr = result.stderr if result.stderr else ""
        return (result.returncode == 0, stdout + stderr)
    except Exception as e:
        return (False, str(e))


def main():
    print("=" * 100)
    print(" " * 25 + "[S2-9] RISK FRAMEWORK VALIDATION MASTER SCRIPT")
    print("=" * 100)
    print()
    print("Objetivo: Implementar 4 validadores de risk management")
    print()
    print("Cronograma:")
    print("  AC-1: Capital Limits Validator — 13/03 (16h)")
    print("  AC-2: Correlation Checker — 14/03 (16h)")
    print("  AC-3: Volatility Bands (Circuit Breakers) — 15/03 (16h)")
    print("  AC-4: Manual Override Framework — 15/03 (16h)")
    print()
    print("Total Estimado: 64 horas | Deadline: 16/03 23:59 BRT (S2-10 blocker)")
    print()
    print("=" * 100)
    print()

    scripts_to_run = [
        {
            "ac_id": "AC-1",
            "name": "Capital Limits Validator",
            "script": "scripts/s2_9_capital_limits.py",
            "timeout": 600,
        },
        {
            "ac_id": "AC-2",
            "name": "Correlation Checker",
            "script": "scripts/s2_9_correlation_checker.py",
            "timeout": 600,
        },
        {
            "ac_id": "AC-3",
            "name": "Volatility Bands",
            "script": "scripts/s2_9_volatility_bands.py",
            "timeout": 300,
        },
        {
            "ac_id": "AC-4",
            "name": "Manual Override Framework",
            "script": "scripts/s2_9_manual_override.py",
            "timeout": 300,
        },
    ]

    results = {}

    for script_config in scripts_to_run:
        ac_id = script_config["ac_id"]
        name = script_config["name"]
        script = script_config["script"]
        timeout = script_config["timeout"]

        print("=" * 100)
        print(f"[EXEC] Executando {script}")
        print(f"Script: {script}")
        print(f"Tempo estimado: {timeout} segundos")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 100)
        print()

        success, output = run_ac_script(name, script, timeout)

        print(output)
        print()

        results[ac_id] = "COMPLETADO COM SUCESSO" if success else "COMPLETADO COM ERRO"

    # Validate output files
    print("=" * 100)
    print("[SUMMARY] Validando arquivos de saida...")
    print("=" * 100)
    print()

    validation_files = [
        "scripts/s2_9_ac1_capital_validation.json",
        "scripts/s2_9_ac2_correlation_validation.json",
        "scripts/s2_9_ac3_volatility_validation.json",
        "scripts/s2_9_ac4_override_validation.json",
    ]

    for file_path in validation_files:
        path = Path(file_path)
        status = "[OK]" if path.exists() else "[MISSING]"
        print(f"  {status} {path.name}")

    print()

    # Final report
    print("=" * 100)
    print("[REPORT] RELATORIO FINAL")
    print("=" * 100)
    print()

    print("Status das ACs:")
    for ac_id, status in results.items():
        status_icon = "[PASS]" if "SUCESSO" in status else "[FAIL]"
        print(f"  {status_icon} {ac_id}: {status}")

    print()

    all_pass = all("SUCESSO" in s for s in results.values())

    if all_pass:
        print("=" * 100)
        print("[SUCCESS] S2-9 ESTA 100% PRONTO PARA COMMIT!")
        print("=" * 100)
        print()
        print("Proxima acao: GIT COMMIT & TAG")
        print()
        print("Executar:")
        print("  cd c:\\repo\\operador-day-trade-win")
        print("  git add scripts/s2_9_*.py docs/TASK_S2_9_*.md")
        print("  git commit -m \"feat: S2-9 Risk Framework - capital limits, correlation, volatility, override\"")
        print("  git tag -a v1.3.4-s2-9-risk-framework -m 'S2-9 Risk Framework completo'")
        print("  git push origin main --tags")
        print()
    else:
        print("=" * 100)
        print("[ALERT] ALGUNS ACS NAO PASSARAM - REVISAR LOGS ACIMA")
        print("=" * 100)
        print()

    return 0 if all_pass else 1


if __name__ == "__main__":
    exit(main())
