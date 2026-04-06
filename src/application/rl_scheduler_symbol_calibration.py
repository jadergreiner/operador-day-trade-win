"""Calibracao de thresholds do scheduler runtime por simbolo via replay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from src.application.rl_scheduler_runtime_adapter import (
    construir_contexto_operacional_para_scheduler,
    obter_calibracao_simbolo,
)


@dataclass(frozen=True)
class ReplayScenario:
    nome: str
    simbolo: str
    trades: list[dict[str, float]]
    esperado_regime: str
    fonte: str


@dataclass(frozen=True)
class CalibrationCandidate:
    stress_score_trigger: float
    volatilidade_trigger: float
    loss_streak_divisor: float
    media_negativa_scale: float

    def to_dict(self) -> dict[str, float]:
        return {
            "stress_score_trigger": self.stress_score_trigger,
            "volatilidade_trigger": self.volatilidade_trigger,
            "loss_streak_divisor": self.loss_streak_divisor,
            "media_negativa_scale": self.media_negativa_scale,
        }


@dataclass(frozen=True)
class CandidateEvaluation:
    simbolo: str
    candidate: CalibrationCandidate
    total_cenarios: int
    acertos: int
    score: float


def build_default_grid_for_symbol(simbolo: str) -> list[CalibrationCandidate]:
    normalizado = simbolo.upper()
    if "WDO" in normalizado:
        stress_values = (0.55, 0.60, 0.65)
        vol_values = (55.0, 60.0, 65.0)
        streak_values = (2.5, 3.0, 3.5)
        mean_values = (2.2, 2.5, 2.8)
    else:
        stress_values = (0.68, 0.70, 0.72)
        vol_values = (70.0, 75.0, 80.0)
        streak_values = (3.5, 4.0, 4.5)
        mean_values = (1.8, 2.0, 2.2)

    grid: list[CalibrationCandidate] = []
    for stress in stress_values:
        for vol in vol_values:
            for streak in streak_values:
                for mean_scale in mean_values:
                    grid.append(
                        CalibrationCandidate(
                            stress_score_trigger=stress,
                            volatilidade_trigger=vol,
                            loss_streak_divisor=streak,
                            media_negativa_scale=mean_scale,
                        )
                    )
    return grid


def evaluate_candidate(
    *,
    simbolo: str,
    candidate: CalibrationCandidate,
    cenarios: Sequence[ReplayScenario],
) -> CandidateEvaluation:
    default_cfg = obter_calibracao_simbolo(simbolo)
    acertos = 0
    score = 0.0
    for scenario in cenarios:
        contexto = construir_contexto_operacional_para_scheduler(
            scenario.trades,
            simbolo=simbolo,
            calibracao_override=candidate.to_dict(),
        )
        regime = str(contexto.get("regime_mercado", "estavel"))
        if regime == scenario.esperado_regime:
            acertos += 1
            score += 1.0
        else:
            score -= 2.0

    # Priorizamos candidatos bons, mas mantendo proximidade do baseline atual.
    distance = (
        abs(candidate.stress_score_trigger - default_cfg["stress_score_trigger"])
        + abs(candidate.volatilidade_trigger - default_cfg["volatilidade_trigger"]) / 100.0
        + abs(candidate.loss_streak_divisor - default_cfg["loss_streak_divisor"])
        + abs(candidate.media_negativa_scale - default_cfg["media_negativa_scale"])
    )
    final_score = score - (distance * 0.1)
    return CandidateEvaluation(
        simbolo=simbolo,
        candidate=candidate,
        total_cenarios=len(cenarios),
        acertos=acertos,
        score=round(final_score, 6),
    )


def calibrate_symbol(
    *,
    simbolo: str,
    cenarios: Sequence[ReplayScenario],
    candidates: Iterable[CalibrationCandidate] | None = None,
) -> CandidateEvaluation:
    candidate_list = list(candidates or build_default_grid_for_symbol(simbolo))
    if not candidate_list:
        raise ValueError("Lista de candidatos vazia.")
    if not cenarios:
        raise ValueError("Lista de cenarios vazia.")
    best: CandidateEvaluation | None = None
    for candidate in candidate_list:
        evaluation = evaluate_candidate(
            simbolo=simbolo,
            candidate=candidate,
            cenarios=cenarios,
        )
        if best is None or evaluation.score > best.score:
            best = evaluation
    assert best is not None
    return best


def group_scenarios_by_symbol(
    scenarios: Sequence[ReplayScenario],
) -> dict[str, list[ReplayScenario]]:
    grouped: dict[str, list[ReplayScenario]] = {}
    for scenario in scenarios:
        key = "WDO" if "WDO" in scenario.simbolo.upper() else "WIN"
        grouped.setdefault(key, []).append(scenario)
    return grouped


def calibrate_all_symbols(
    scenarios: Sequence[ReplayScenario],
) -> dict[str, CandidateEvaluation]:
    grouped = group_scenarios_by_symbol(scenarios)
    resultado: dict[str, CandidateEvaluation] = {}
    for simbolo, cenarios in grouped.items():
        resultado[simbolo] = calibrate_symbol(simbolo=simbolo, cenarios=cenarios)
    return resultado
