"""
Check P0-2 Status - Verifica se P0-2 completou e qual é a decisão GATE 2.

Uso:
- Em scripts: from scripts.check_p0_2_status import is_p0_2_complete, get_gate2_decision
- Em .bat: python scripts/check_p0_2_status.py (retorna exit code)
"""

import json
import sys
from pathlib import Path
from typing import Optional


STATUS_FILE = Path("data/backtest/p0_2_status.json")
DECISION_FILE = Path("data/backtest/gate2_decision.json")


def is_p0_2_complete() -> bool:
    """
    Verifica se P0-2 foi executado completamente.

    Returns:
        True se arquivo de status existe, False senão
    """
    return STATUS_FILE.exists()


def has_final_gate2_decision() -> bool:
    """Retorna True apenas quando a decisao e auditavel e final."""
    if not STATUS_FILE.exists() or not DECISION_FILE.exists():
        return False

    summary = get_p0_2_status_summary()
    if not summary.get("completed", False):
        return False

    if not summary.get("decision_is_final", False):
        return False

    dataset_audit = summary.get("dataset_audit", {})
    if dataset_audit and not dataset_audit.get("audit_passed", False):
        return False

    summary_decision = summary.get("decision")
    decision_file_decision = get_gate2_decision()
    if summary_decision not in {"PASS", "FAIL"}:
        return False
    if decision_file_decision not in {"PASS", "FAIL"}:
        return False
    if summary_decision != decision_file_decision:
        return False

    return True


def get_gate2_decision() -> Optional[str]:
    """
    Retorna decisão GATE 2 (PASS/FAIL).

    Returns:
        "PASS", "FAIL", ou None se não completou

    Raises:
        json.JSONDecodeError: Se arquivo JSON inválido
    """
    if not DECISION_FILE.exists():
        return None

    with open(DECISION_FILE) as f:
        data = json.load(f)
    return data.get("decision")


def get_p0_2_status_summary() -> dict:
    """
    Retorna sumário completo do status P0-2.

    Returns:
        Dict com informações de execução ou {} se não completou

    Raises:
        json.JSONDecodeError: Se arquivo JSON inválido
    """
    if not STATUS_FILE.exists():
        return {}

    with open(STATUS_FILE) as f:
        return json.load(f)


def should_skip_p0_2() -> bool:
    """
    Verifica se P0-2 ainda está rodando (útil para .bat não esperar).

    Returns:
        True se P0-2 completou, False se ainda rodando
    """
    return is_p0_2_complete()


def wait_for_p0_2_completion(timeout_seconds: int = 600) -> bool:
    """
    Aguarda P0-2 completar (máximo timeout_seconds).

    Args:
        timeout_seconds: Tempo máximo a esperar (padrão 10 min)

    Returns:
        True se completou, False se timeout
    """
    import time

    elapsed = 0
    while elapsed < timeout_seconds:
        if is_p0_2_complete():
            return True
        time.sleep(5)  # Check a cada 5 segundos
        elapsed += 5

    return False


# ============================================================================
# UTILITÁRIOS PARA .BAT
# ============================================================================


def main_for_bat() -> int:
    """
    Entry point para uso em .bat (retorna exit codes).

    Exit codes:
    - 0: P0-2 completou AND GATE 2 PASS → pode iniciar agente
    - 1: P0-2 completou AND GATE 2 FAIL → pode iniciar agente (capital menor)
    - 2: P0-2 ainda rodando → não tenta iniciar agente ainda
    - 3: Erro ao checar status
    """
    try:
        if not is_p0_2_complete():
            # P0-2 ainda rodando - não bloqueia operador
            print("[P0-2] Backtest ainda em execucao (background)...")
            return 2

        summary = get_p0_2_status_summary()
        if not has_final_gate2_decision():
            error_code = summary.get("error_code", "STATUS_INDEFINIDO")
            print(
                "[P0-2] [ERROR] Status sem decisao final auditavel "
                f"({error_code}) - mantendo capital conservador"
            )
            return 3

        decision = get_gate2_decision()
        if decision == "PASS":
            print("[P0-2] [OK] GATE 2 PASSOU - Escalando para R$ 100k")
            return 0
        elif decision == "FAIL":
            print("[P0-2] [FAIL] GATE 2 FALHOU - Mantendo em R$ 50k")
            return 1
        else:
            print("[P0-2] [?] Status indefinido")
            return 3

    except Exception as e:
        print(f"[P0-2] [ERROR] Erro ao checar status: {e}")
        return 3


# ============================================================================
# UTILITÁRIOS PARA DEBUG
# ============================================================================


def print_p0_2_status() -> None:
    """Imprime status P0-2 formatado (útil para debug)."""
    print("\n" + "=" * 70)
    print("P0-2 STATUS CHECK")
    print("=" * 70)

    if not is_p0_2_complete():
        print("Status: ⏳ RODANDO EM BACKGROUND")
        print("Console: Ver data/logs/p0_2_execution_*.log")
        return

    summary = get_p0_2_status_summary()
    print(f"Status: ✓ COMPLETO")
    print(f"Timestamp: {summary.get('timestamp', 'N/A')}")
    print(f"GATE 2 Decision: {summary.get('decision', 'N/A')}")
    print(f"Decision Final: {summary.get('decision_is_final', 'N/A')}")
    print(f"Backtest Results: {summary.get('backtest_results', 'N/A')}")
    print(f"Reports Dir: {summary.get('reports_dir', 'N/A')}")
    dataset_audit = summary.get("dataset_audit", {})
    if dataset_audit:
        print(f"Dataset Audit: {dataset_audit.get('audit_passed', False)}")
        if dataset_audit.get("audit_issues"):
            print(f"Audit Issues: {', '.join(dataset_audit['audit_issues'])}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Verifica status P0-2")
    parser.add_argument("--debug", action="store_true", help="Imprime status formatado")
    parser.add_argument(
        "--wait", action="store_true", help="Aguarda P0-2 completar (timeout 10min)"
    )

    args = parser.parse_args()

    if args.debug:
        print_p0_2_status()
        sys.exit(0)

    if args.wait:
        print("[P0-2] Aguardando conclusão (timeout 10 min)...")
        if wait_for_p0_2_completion():
            print("[P0-2] ✓ Completou!")
            sys.exit(main_for_bat())
        else:
            print("[P0-2] ✗ Timeout aguardando conclusão")
            sys.exit(3)

    # Default: retorna exit code para .bat
    sys.exit(main_for_bat())
