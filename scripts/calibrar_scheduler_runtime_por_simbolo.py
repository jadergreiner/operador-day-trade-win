"""Replay/calibracao de thresholds do scheduler runtime por simbolo.

Uso:
    python scripts/calibrar_scheduler_runtime_por_simbolo.py --date 20260406
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

from src.application.rl_scheduler_symbol_calibration import (
    ReplayScenario,
    calibrate_all_symbols,
)
from src.application.rl_scheduler_runtime_adapter import obter_calibracao_simbolo

OUTPUTS_DIR = Path("outputs")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_trades_from_history(path: Path) -> list[dict[str, float]]:
    payload = _load_json(path)
    if not isinstance(payload, list):
        return []
    trades: list[dict[str, float]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        pnl = item.get("pnl_pct")
        if isinstance(pnl, (int, float)):
            trades.append({"pnl": float(pnl)})
    return trades


def _max_loss_streak(pnls: list[float]) -> int:
    streak = 0
    max_streak = 0
    for value in pnls:
        if value < 0:
            streak += 1
            if streak > max_streak:
                max_streak = streak
        else:
            streak = 0
    return max_streak


def _classificar_esperado(trades: list[dict[str, float]]) -> str:
    pnls = [float(t["pnl"]) for t in trades]
    if not pnls:
        return "estavel"
    win_rate = sum(1 for p in pnls if p > 0.0) / len(pnls)
    mean = sum(pnls) / len(pnls)
    if win_rate < 0.45 or mean < -0.03 or _max_loss_streak(pnls) >= 3:
        return "stress_high_vol"
    return "estavel"


def _build_real_win_scenarios(date_tag: str) -> list[ReplayScenario]:
    files = sorted(OUTPUTS_DIR.glob(f"historico_fechamentos_*{date_tag}_*.json"))
    scenarios: list[ReplayScenario] = []
    for path in files:
        trades = _extract_trades_from_history(path)
        if len(trades) < 4:
            continue
        scenarios.append(
            ReplayScenario(
                nome=path.stem,
                simbolo="WIN",
                trades=trades,
                esperado_regime=_classificar_esperado(trades),
                fonte="replay_real_outputs",
            )
        )
    return scenarios


def _build_synthetic_wdo_scenarios() -> list[ReplayScenario]:
    degraded = ReplayScenario(
        nome="wdo_degradado_sintetico",
        simbolo="WDO",
        trades=[
            {"pnl": -0.11},
            {"pnl": -0.09},
            {"pnl": -0.06},
            {"pnl": 0.01},
            {"pnl": -0.04},
        ],
        esperado_regime="stress_high_vol",
        fonte="sintetico_controlado",
    )
    stable = ReplayScenario(
        nome="wdo_estavel_sintetico",
        simbolo="WDO",
        trades=[
            {"pnl": 0.06},
            {"pnl": -0.01},
            {"pnl": 0.05},
            {"pnl": -0.01},
            {"pnl": 0.04},
        ],
        esperado_regime="estavel",
        fonte="sintetico_controlado",
    )
    return [degraded, stable]


def _ensure_win_coverage(scenarios: list[ReplayScenario]) -> list[ReplayScenario]:
    enriched = list(scenarios)
    has_stress = any(s.esperado_regime == "stress_high_vol" for s in enriched)
    has_stable = any(s.esperado_regime == "estavel" for s in enriched)

    if not has_stress:
        enriched.append(
            ReplayScenario(
                nome="win_degradado_sintetico",
                simbolo="WIN",
                trades=[
                    {"pnl": -0.10},
                    {"pnl": -0.08},
                    {"pnl": -0.06},
                    {"pnl": 0.01},
                    {"pnl": -0.05},
                ],
                esperado_regime="stress_high_vol",
                fonte="sintetico_controlado",
            )
        )
    if not has_stable:
        enriched.append(
            ReplayScenario(
                nome="win_estavel_sintetico",
                simbolo="WIN",
                trades=[
                    {"pnl": 0.08},
                    {"pnl": -0.02},
                    {"pnl": 0.07},
                    {"pnl": -0.01},
                    {"pnl": 0.05},
                ],
                esperado_regime="estavel",
                fonte="sintetico_controlado",
            )
        )
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"))
    args = parser.parse_args()

    win_scenarios = _ensure_win_coverage(_build_real_win_scenarios(args.date))
    wdo_scenarios = _build_synthetic_wdo_scenarios()
    scenarios = [*win_scenarios, *wdo_scenarios]

    resultado = calibrate_all_symbols(scenarios)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    report: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "date_replay": args.date,
        "modo": "scheduler_runtime_symbol_calibration",
        "cenarios_total": len(scenarios),
        "cenarios": [
            {
                "nome": s.nome,
                "simbolo": s.simbolo,
                "esperado_regime": s.esperado_regime,
                "fonte": s.fonte,
                "trades": len(s.trades),
            }
            for s in scenarios
        ],
        "recomendacao_por_simbolo": {},
    }

    for symbol, evaluation in resultado.items():
        report["recomendacao_por_simbolo"][symbol] = {
            "calibracao_atual": obter_calibracao_simbolo(symbol),
            "calibracao_recomendada": evaluation.candidate.to_dict(),
            "acertos": evaluation.acertos,
            "total_cenarios": evaluation.total_cenarios,
            "score": evaluation.score,
        }

    path = OUTPUTS_DIR / f"scheduler_symbol_calibration_{timestamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(path))


if __name__ == "__main__":
    main()
