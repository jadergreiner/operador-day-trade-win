#!/usr/bin/env python3
"""Orquestra fluxo único de encerramento:
1) Sessão Head (diretiva + feedback + diário) para próximo pregão útil
2) Registro de lições em reflections
3) Refresh ML (dataset supervisionado + treino incremental)

Uso:
  python scripts/executar_fluxo_head_encerramento.py --base-date 2026-02-13
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa fluxo único Head + persistência + refresh ML.")
    parser.add_argument("--base-date", required=True, help="Data base do pregão encerrado (YYYY-MM-DD).")
    parser.add_argument("--python", default=sys.executable, help="Executável Python a usar.")
    return parser.parse_args()


def _run_step(cmd: list[str], name: str) -> None:
    print(f"[STEP] {name}")
    result = subprocess.run(cmd, cwd=str(ROOT_DIR), check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Falha em {name} (exit={result.returncode})")


def _append_reflection(base_date: str) -> None:
    p = ROOT_DIR / "data" / "db" / "reflections" / "reflections_log.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "timestamp": datetime.now().isoformat(),
        "entry_id": f"HEAD_ENCERRAMENTO_{base_date.replace('-', '')}_{datetime.now().strftime('%H%M%S')}",
        "date": base_date,
        "source": f"head_encerramento_{base_date.replace('-', '')}",
        "type": "head_learning",
        "title": "Lições de encerramento (fluxo automático)",
        "summary": "Sessão Head persistida e refresh ML executado no encerramento.",
        "plan_today": [
            "Reforçar continuidade em pullback com confirmação.",
            "Evitar reversão prematura em tendência forte.",
            "Manter disciplina de risco e limite de trades.",
        ],
        "critical_points_immediate": [
            "Penalizar reversão sem confluência.",
            "Reduzir agressividade em repiques sem continuidade.",
        ],
    }

    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    print(f"[OK] Reflection anexada em {p}")


def main() -> int:
    args = _parse_args()

    try:
        datetime.strptime(args.base_date, "%Y-%m-%d")
    except ValueError:
        print("[ERRO] --base-date inválida. Use YYYY-MM-DD.")
        return 2

    py = args.python

    try:
        _run_step(
            [py, "scripts/aplicar_diretiva_pos_pregao.py", "--base-date", args.base_date],
            "Sessão Head e persistência (head + diário)",
        )

        _append_reflection(args.base_date)

        _run_step(
            [py, "scripts/ml/gerar_dataset_trade_supervisionado.py", "--date", args.base_date],
            "Geração dataset supervisionado",
        )

        _run_step(
            [py, "scripts/ml/treinar_incremental_trade_supervisionado.py", "--as-of-date", args.base_date],
            "Treino incremental",
        )

    except Exception as exc:
        print(f"[ERRO] Fluxo de encerramento falhou: {exc}")
        return 1

    print("[OK] Fluxo de encerramento Head concluído com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
