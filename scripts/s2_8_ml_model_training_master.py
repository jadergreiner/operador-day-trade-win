#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

"""S2-8: ML Model Training — Master Orchestrator"""

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
            timeout=timeout
        )
        return (result.returncode == 0, result.stdout + result.stderr)
    except Exception as e:
        return (False, str(e))


def main():
    print("=" * 100)
    print(" " * 25 + "[S2-8] ML MODEL TRAINING MASTER SCRIPT")
    print("=" * 100)
    print()
    print("Objetivo: Treinar modelo com 40 features otimizadas")
    print()
    print("Cronograma:")
    print("  AC-1: Model Training (Grid Search) — 06/03 (16h)")
    print("  AC-2: Cross-Validation + Stability — 07/03 (16h)")
    print("  AC-3: Model Serialization — 08/03 (16h)")
    print("  AC-4: Production Inference Test — 09/03 (16h)")
    print()
    print("Total Estimado: 64 horas | Deadline: 12/03 17:00 BRT (GATE 2)")
    print()
    print("=" * 100)
    print()

    scripts_to_run = [
        {
            "ac_id": "AC-1",
            "name": "Model Training",
            "script": "scripts/s2_8_model_training.py",
            "timeout": 600,
        },
        {
            "ac_id": "AC-2",
            "name": "Cross-Validation",
            "script": "scripts/s2_8_crossvalidation.py",
            "timeout": 600,
        },
        {
            "ac_id": "AC-3",
            "name": "Model Serialization",
            "script": "scripts/s2_8_model_serialization.py",
            "timeout": 300,
        },
        {
            "ac_id": "AC-4",
            "name": "Production Inference Test",
            "script": "scripts/s2_8_production_inference.py",
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
        "scripts/s2_8_ac1_training_results.json",
        "scripts/s2_8_ac2_crossval_results.json",
        "scripts/s2_8_ac3_serialization_validation.json",
        "scripts/s2_8_ac4_inference_test.json",
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
        print("[SUCCESS] S2-8 ESTA 100% PRONTO PARA COMMIT!")
        print("=" * 100)
        print()
        print("Proxima acao: GIT COMMIT & TAG")
        print()
        print("Executar:")
        print("  cd c:\\repo\\operador-day-trade-win")
        print("  git add scripts/s2_8_*.py models/s2_8_* docs/TASK_S2_8_*.md")
        print("  git commit -m \"feat: S2-8 ML Model Training - 40 features, ensemble trained, 4/4 ACs PASSED\"")
        print("  git tag -a v1.3.3-s2-8-ml-model-training -m 'S2-8 ML Model Training completo'")
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
