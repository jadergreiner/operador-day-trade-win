"""Testes para adaptador runtime do scheduler RL."""

from src.application.rl_scheduler_runtime_adapter import (
    calcular_metricas_para_scheduler,
    construir_contexto_operacional_para_scheduler,
    extrair_pnls,
    obter_calibracao_simbolo,
)


def test_extrair_pnls_prioriza_chaves_conhecidas() -> None:
    trades = [
        {"pnl": -10.0},
        {"pnl_pct": -0.2},
        {"profit_loss": 5.5},
        {"resultado_final_pct": 0.3},
    ]
    pnls = extrair_pnls(trades)
    assert pnls == [-10.0, -0.2, 5.5, 0.3]


def test_calcular_metricas_para_scheduler_retorna_defaults_sem_trades() -> None:
    metricas = calcular_metricas_para_scheduler([])
    assert metricas == {"win_rate": 0.0, "sharpe": 0.0, "f1": 0.0}


def test_calcular_metricas_para_scheduler_calcula_win_rate_e_sharpe() -> None:
    metricas = calcular_metricas_para_scheduler(
        [{"pnl": 1.0}, {"pnl": -1.0}, {"pnl": 2.0}, {"pnl": -0.5}]
    )
    assert 0.0 <= metricas["win_rate"] <= 100.0
    assert metricas["win_rate"] == 50.0
    assert "sharpe" in metricas
    assert 0.0 <= metricas["f1"] <= 1.0


def test_construir_contexto_operacional_identifica_estresse() -> None:
    contexto = construir_contexto_operacional_para_scheduler(
        [{"pnl": -1.2}, {"pnl": -1.0}, {"pnl": -0.8}, {"pnl": -0.9}]
    )
    assert contexto["regime_mercado"] == "stress_high_vol"
    assert float(contexto["stress_score"]) >= 0.70


def test_construir_contexto_operacional_estavel_em_sessao_controlada() -> None:
    contexto = construir_contexto_operacional_para_scheduler(
        [{"pnl": 0.2}, {"pnl": -0.05}, {"pnl": 0.15}, {"pnl": 0.10}]
    )
    assert contexto["regime_mercado"] == "estavel"
    assert float(contexto["stress_score"]) < 0.70


def test_obter_calibracao_simbolo_aplica_normalizacao() -> None:
    calibracao_win = obter_calibracao_simbolo("WINJ26")
    calibracao_wdo = obter_calibracao_simbolo("wdok26")
    calibracao_default = obter_calibracao_simbolo("DOLX99")

    assert calibracao_win["stress_score_trigger"] == 0.70
    assert calibracao_wdo["stress_score_trigger"] == 0.60
    assert calibracao_default["stress_score_trigger"] == 0.70


def test_construir_contexto_operacional_diferencia_win_e_wdo() -> None:
    trades = [{"pnl": -0.05}, {"pnl": -0.04}, {"pnl": 0.01}, {"pnl": 0.02}]

    contexto_win = construir_contexto_operacional_para_scheduler(
        trades,
        simbolo="WINJ26",
    )
    contexto_wdo = construir_contexto_operacional_para_scheduler(
        trades,
        simbolo="WDOF26",
    )

    assert contexto_win["simbolo_contexto"] == "WIN"
    assert contexto_wdo["simbolo_contexto"] == "WDO"
    assert contexto_win["regime_mercado"] == "estavel"
    assert contexto_wdo["regime_mercado"] == "stress_high_vol"


def test_construir_contexto_operacional_aceita_calibracao_override() -> None:
    trades = [{"pnl": -0.04}, {"pnl": -0.03}, {"pnl": 0.01}, {"pnl": 0.02}]
    contexto_default = construir_contexto_operacional_para_scheduler(
        trades,
        simbolo="WINJ26",
    )
    contexto_override = construir_contexto_operacional_para_scheduler(
        trades,
        simbolo="WINJ26",
        calibracao_override={"stress_score_trigger": 0.40},
    )
    assert contexto_default["regime_mercado"] == "estavel"
    assert contexto_override["regime_mercado"] == "stress_high_vol"
