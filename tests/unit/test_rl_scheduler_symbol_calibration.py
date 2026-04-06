"""Testes para calibracao por simbolo do scheduler runtime."""

from src.application.rl_scheduler_symbol_calibration import (
    CalibrationCandidate,
    ReplayScenario,
    calibrate_all_symbols,
    calibrate_symbol,
    evaluate_candidate,
)


def test_evaluate_candidate_pontua_acertos_e_erros() -> None:
    candidate = CalibrationCandidate(
        stress_score_trigger=0.70,
        volatilidade_trigger=75.0,
        loss_streak_divisor=4.0,
        media_negativa_scale=2.0,
    )
    cenarios = [
        ReplayScenario(
            nome="win_stress",
            simbolo="WIN",
            trades=[{"pnl": -0.12}, {"pnl": -0.10}, {"pnl": -0.07}, {"pnl": 0.01}],
            esperado_regime="stress_high_vol",
            fonte="teste",
        ),
        ReplayScenario(
            nome="win_stable",
            simbolo="WIN",
            trades=[{"pnl": 0.08}, {"pnl": -0.01}, {"pnl": 0.07}, {"pnl": 0.04}],
            esperado_regime="estavel",
            fonte="teste",
        ),
    ]
    evaluation = evaluate_candidate(simbolo="WIN", candidate=candidate, cenarios=cenarios)
    assert evaluation.total_cenarios == 2
    assert 0 <= evaluation.acertos <= 2


def test_calibrate_symbol_retorna_melhor_candidato() -> None:
    cenarios = [
        ReplayScenario(
            nome="wdo_stress",
            simbolo="WDO",
            trades=[{"pnl": -0.11}, {"pnl": -0.09}, {"pnl": -0.06}, {"pnl": 0.01}],
            esperado_regime="stress_high_vol",
            fonte="teste",
        ),
        ReplayScenario(
            nome="wdo_stable",
            simbolo="WDO",
            trades=[{"pnl": 0.07}, {"pnl": -0.01}, {"pnl": 0.06}, {"pnl": 0.03}],
            esperado_regime="estavel",
            fonte="teste",
        ),
    ]
    best = calibrate_symbol(simbolo="WDO", cenarios=cenarios)
    assert best.simbolo == "WDO"
    assert best.total_cenarios == 2
    assert best.acertos >= 1


def test_calibrate_all_symbols_agrupar_por_win_wdo() -> None:
    cenarios = [
        ReplayScenario(
            nome="win_stable",
            simbolo="WINJ26",
            trades=[{"pnl": 0.06}, {"pnl": -0.01}, {"pnl": 0.05}, {"pnl": 0.03}],
            esperado_regime="estavel",
            fonte="teste",
        ),
        ReplayScenario(
            nome="wdo_stable",
            simbolo="WDOF26",
            trades=[{"pnl": 0.04}, {"pnl": -0.01}, {"pnl": 0.03}, {"pnl": 0.02}],
            esperado_regime="estavel",
            fonte="teste",
        ),
    ]
    result = calibrate_all_symbols(cenarios)
    assert "WIN" in result
    assert "WDO" in result
