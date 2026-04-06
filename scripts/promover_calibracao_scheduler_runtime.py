"""Promove calibracao por simbolo para runtime via gate manual.

Uso:
    python scripts/promover_calibracao_scheduler_runtime.py --report outputs/scheduler_symbol_calibration_*.json --approver operador
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

from src.application.rl_scheduler_calibration_promotion import (  # noqa: E402
    promote_runtime_calibration,
)

OUTPUTS_DIR = Path("outputs")
DEFAULT_DESTINATION = Path("data/scheduler/symbol_calibration_runtime.json")


def _latest_report_path() -> Path:
    reports = sorted(OUTPUTS_DIR.glob("scheduler_symbol_calibration_*.json"))
    if not reports:
        raise FileNotFoundError(
            "Nenhum relatorio scheduler_symbol_calibration_*.json encontrado em outputs/."
        )
    return reports[-1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="", help="Caminho do report de calibracao.")
    parser.add_argument("--approver", default="manual_gate", help="Responsavel pela aprovacao.")
    parser.add_argument("--destination", default=str(DEFAULT_DESTINATION))
    parser.add_argument("--min-scenarios", type=int, default=2)
    parser.add_argument("--min-accuracy", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report_path = Path(args.report) if args.report else _latest_report_path()
    decision = promote_runtime_calibration(
        report_path=report_path,
        destination_path=Path(args.destination),
        approver=args.approver,
        min_scenarios_per_symbol=args.min_scenarios,
        min_accuracy=args.min_accuracy,
        dry_run=args.dry_run,
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUTS_DIR / f"scheduler_symbol_promotion_{ts}.json"
    out_path.write_text(json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    print("APROVADO" if decision.get("aprovado") else "REPROVADO")


if __name__ == "__main__":
    main()
