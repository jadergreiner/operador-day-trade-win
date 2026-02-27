#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import subprocess
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict

def executar_script(script_name: str, tempo_estimado: str) -> Tuple[bool, str]:
    """Executa um script AC e captura output."""
    print("=" * 100)
    print(f"[EXEC] Executando {script_name}")
    print(f"Script: scripts/{script_name}")
    print(f"Tempo estimado: {tempo_estimado}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 100)
    print()
    
    try:
        result = subprocess.run(
            [sys.executable, f"scripts/{script_name}"],
            capture_output=True,
            text=True,
            timeout=300
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0, result.stdout
    except Exception as e:
        print(f"[ERROR] {script_name}: {e}")
        return False, str(e)

def validar_arquivos_saida() -> bool:
    """Valida se todos 4 arquivos foram criados."""
    files = [Path(f"scripts/s2_7_ac{i}_validation.json") for i in range(1, 5)]
    return all(f.exists() for f in files)

def main():
    print("=" * 100)
    print("                         [S2-7] FEATURE SCALING MASTER SCRIPT")
    print("=" * 100)
    print()
    print("Objetivo: Expandir features de 25 para 40-45 otimizadas")
    print()
    print("Cronograma:")
    print("  AC-1: Feature Engineering (01/03 — 8h)")
    print("  AC-2: Feature Selection (02/03 — 8h)")
    print("  AC-3: Feature Validation (03/03 — 8h)")
    print("  AC-4: Performance Analysis (04/03 — 8h)")
    print()
    print("Total Estimado: 32 horas | Deadline: 05/03 17:00 BRT")
    print()
    print("=" * 100)
    print()
    
    results = {}
    
    # AC-1: Feature Engineering
    ac1_ok, _ = executar_script("s2_7_feature_engineering.py", "120 minutos")
    results["AC-1"] = {
        "name": "Feature Engineering",
        "status": "PASSED" if ac1_ok else "FAILED",
        "exists": Path("scripts/s2_7_ac1_validation.json").exists()
    }
    print()
    print(f"[RESULT] AC-1 COMPLETADO COM {'SUCESSO' if ac1_ok else 'ERRO'}")
    print()
    
    # AC-2: Feature Selection
    ac2_ok, _ = executar_script("s2_7_feature_selection.py", "120 minutos")
    results["AC-2"] = {
        "name": "Feature Selection",
        "status": "PASSED" if ac2_ok else "FAILED",
        "exists": Path("scripts/s2_7_ac2_validation.json").exists()
    }
    print()
    print(f"[RESULT] AC-2 COMPLETADO COM {'SUCESSO' if ac2_ok else 'ERRO'}")
    print()
    
    # AC-3: Feature Validation
    ac3_ok, _ = executar_script("s2_7_feature_validation.py", "120 minutos")
    results["AC-3"] = {
        "name": "Feature Validation",
        "status": "PASSED" if ac3_ok else "FAILED",
        "exists": Path("scripts/s2_7_ac3_validation.json").exists()
    }
    print()
    print(f"[RESULT] AC-3 COMPLETADO COM {'SUCESSO' if ac3_ok else 'ERRO'}")
    print()
    
    # AC-4: Performance Analysis
    ac4_ok, _ = executar_script("s2_7_performance_analysis.py", "120 minutos")
    results["AC-4"] = {
        "name": "Performance Analysis",
        "status": "PASSED" if ac4_ok else "FAILED",
        "exists": Path("scripts/s2_7_ac4_validation.json").exists()
    }
    print()
    print(f"[RESULT] AC-4 COMPLETADO COM {'SUCESSO' if ac4_ok else 'ERRO'}")
    print()
    
    # Summary
    print("=" * 100)
    print("[SUMMARY] Validando arquivos de saida...")
    print("=" * 100)
    print()
    
    all_passed = validar_arquivos_saida() and ac1_ok and ac2_ok and ac3_ok and ac4_ok
    
    for i in range(1, 5):
        json_file = Path(f"scripts/s2_7_ac{i}_validation.json")
        status = "[OK]" if json_file.exists() else "[FAIL]"
        print(f"  {status} AC-{i}: s2_7_ac{i}_validation.json")
    
    print()
    print("=" * 100)
    print("[REPORT] RELATORIO FINAL")
    print("=" * 100)
    print()
    
    print("Status das ACs:")
    for i in range(1, 5):
        status = "[PASS]" if results[f"AC-{i}"]["status"] == "PASSED" else "[FAIL]"
        name = results[f"AC-{i}"]["name"]
        print(f"  {status} AC-{i}: {name}")
    
    print()
    
    if all_passed:
        print("=" * 100)
        print("[SUCCESS] S2-7 ESTA 100% PRONTO PARA COMMIT!")
        print("=" * 100)
        print()
        print("Proxima acao: GIT COMMIT & TAG")
        print()
        print("Executar:")
        print("  cd c:\\repo\\operador-day-trade-win")
        print("  git add scripts/ models/")
        print('  git commit -m "feat: S2-7 Feature Scaling - 40 new features, 4/4 ACs PASSED"')
        print("  git tag -a v1.3.2-s2-7-feature-scaling -m 'S2-7 Feature Scaling completo'")
        print("  git push origin main --tags")
        print()
        return 0
    else:
        print("=" * 100)
        print("[ALERT] ALGUNS ACS NAO PASSARAM - REVISAR LOGS ACIMA")
        print("=" * 100)
        print()
        return 1

if __name__ == "__main__":
    exit(main())
