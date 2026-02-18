"""Gate automático de promoção de modelo com base em validação OOT rolling.

Regra principal (default):
- Promover somente se, nos últimos N dias consecutivos (default=2),
  o modelo novo tiver:
  1) PnL líquido > baseline
  2) Max drawdown <= baseline

Uso:
    python scripts/ml/promotion_gate.py
    python scripts/ml/promotion_gate.py --report logs/oot_rolling_3cuts_20260213_185128.json
    python scripts/ml/promotion_gate.py --required-consecutive-days 2 --candidate novo_20260213 --baseline baseline_20260212
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
LOGS_DIR = ROOT_DIR / "logs"


def _find_latest_rolling_report() -> Path | None:
    candidates = sorted(LOGS_DIR.glob("oot_rolling_3cuts_*.json"))
    return candidates[-1] if candidates else None


def _load_report(report_path: Path) -> dict[str, Any]:
    with open(report_path, encoding="utf-8") as f:
        return json.load(f)


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _evaluate_day(cut: dict[str, Any], candidate: str, baseline: str) -> dict[str, Any]:
    models = cut.get("models", {})
    candidate_model = models.get(candidate, {})
    baseline_model = models.get(baseline, {})

    candidate_trading = candidate_model.get("trading", {})
    baseline_trading = baseline_model.get("trading", {})

    candidate_pnl = _safe_float(candidate_trading.get("total_net_pnl_pts"))
    baseline_pnl = _safe_float(baseline_trading.get("total_net_pnl_pts"))
    candidate_dd = _safe_float(candidate_trading.get("max_drawdown_pts"))
    baseline_dd = _safe_float(baseline_trading.get("max_drawdown_pts"))

    pnl_ok = (
        candidate_pnl is not None
        and baseline_pnl is not None
        and candidate_pnl > baseline_pnl
    )
    dd_ok = (
        candidate_dd is not None
        and baseline_dd is not None
        and candidate_dd <= baseline_dd
    )

    return {
        "test_date": cut.get("test_date"),
        "candidate_pnl": candidate_pnl,
        "baseline_pnl": baseline_pnl,
        "candidate_drawdown": candidate_dd,
        "baseline_drawdown": baseline_dd,
        "pnl_ok": pnl_ok,
        "drawdown_ok": dd_ok,
        "passed": pnl_ok and dd_ok,
    }


def _compute_consecutive_passes(day_results: list[dict[str, Any]]) -> int:
    streak = 0
    for item in reversed(day_results):
        if item.get("passed"):
            streak += 1
        else:
            break
    return streak


def evaluate_promotion_gate(
    report_data: dict[str, Any],
    candidate: str,
    baseline: str,
    required_consecutive_days: int,
) -> dict[str, Any]:
    cuts = report_data.get("cuts", [])
    if not cuts:
        raise ValueError("Relatório sem cortes em 'cuts'.")

    day_results = [_evaluate_day(cut, candidate, baseline) for cut in cuts]
    consecutive_passes = _compute_consecutive_passes(day_results)
    approved = consecutive_passes >= required_consecutive_days

    decision = "PROMOVER" if approved else "MANTER_SHADOW"

    return {
        "generated_at": datetime.now().isoformat(),
        "rule": {
            "required_consecutive_days": required_consecutive_days,
            "condition": "candidate_pnl > baseline_pnl AND candidate_drawdown <= baseline_drawdown",
        },
        "candidate": candidate,
        "baseline": baseline,
        "decision": decision,
        "approved": approved,
        "consecutive_passes_from_latest": consecutive_passes,
        "day_results": day_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate automático de promoção de modelo")
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="Caminho para relatório OOT rolling JSON. Se omitido, usa o mais recente em logs/.",
    )
    parser.add_argument(
        "--candidate",
        type=str,
        default="novo_20260213",
        help="Nome do modelo candidato no relatório.",
    )
    parser.add_argument(
        "--baseline",
        type=str,
        default="baseline_20260212",
        help="Nome do modelo baseline no relatório.",
    )
    parser.add_argument(
        "--required-consecutive-days",
        type=int,
        default=2,
        help="Número mínimo de dias consecutivos aprovados (a partir do dia mais recente).",
    )
    args = parser.parse_args()

    report_path = Path(args.report) if args.report else _find_latest_rolling_report()
    if report_path is None or not report_path.exists():
        raise FileNotFoundError(
            "Nenhum relatório OOT rolling encontrado. Rode primeiro: scripts/ml/_tmp_oot_rolling_eval.py"
        )

    report_data = _load_report(report_path)
    result = evaluate_promotion_gate(
        report_data=report_data,
        candidate=args.candidate,
        baseline=args.baseline,
        required_consecutive_days=args.required_consecutive_days,
    )
    result["report_used"] = str(report_path)

    out_path = LOGS_DIR / f"promotion_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("PROMOTION GATE")
    print("=" * 60)
    print(f"Relatório: {report_path}")
    print(f"Candidato: {args.candidate}")
    print(f"Baseline:  {args.baseline}")
    print(f"Regra: {args.required_consecutive_days} dias consecutivos")
    print("-")

    for item in result["day_results"]:
        status = "PASS" if item["passed"] else "FAIL"
        print(
            f"{item['test_date']}: {status} | "
            f"PnL cand={item['candidate_pnl']} vs base={item['baseline_pnl']} | "
            f"DD cand={item['candidate_drawdown']} vs base={item['baseline_drawdown']}"
        )

    print("-")
    print(f"Consecutivos (mais recente): {result['consecutive_passes_from_latest']}")
    print(f"DECISÃO: {result['decision']}")
    print(f"Saída: {out_path}")


if __name__ == "__main__":
    main()
