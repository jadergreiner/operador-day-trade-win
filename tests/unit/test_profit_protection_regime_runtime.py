"""Testes unitarios para decisor runtime de perfil do Profit Protection."""

from src.application.profit_protection_regime_runtime import (
    aplicar_guardrail_cooldown_switch,
    decidir_switch_perfil_profit_protection,
    validar_sessao_runtime_profit_protection,
)


def _trades_from_pnl(values: list[float]) -> list[dict[str, float]]:
    return [{"pnl": v} for v in values]


def test_nao_troca_com_amostra_insuficiente() -> None:
    decisao = decidir_switch_perfil_profit_protection(
        trades_fechados=_trades_from_pnl([1.0, -1.0, 2.0]),
        perfil_atual="baseline",
        perfis_disponiveis=["baseline", "conservador", "agressivo"],
    )
    assert decisao.deve_trocar is False
    assert decisao.perfil_sugerido == "baseline"
    assert "Amostra insuficiente" in decisao.motivo


def test_troca_para_conservador_quando_regime_degrada() -> None:
    # Bloco anterior com 100% wins, bloco recente com 0% wins.
    trades = _trades_from_pnl(([1.0] * 12) + ([-1.0] * 12))
    decisao = decidir_switch_perfil_profit_protection(
        trades_fechados=trades,
        perfil_atual="baseline",
        perfis_disponiveis=["baseline", "conservador", "agressivo"],
    )
    assert decisao.regime_shift_detectado is True
    assert decisao.deve_trocar is True
    assert decisao.perfil_sugerido == "conservador"


def test_troca_para_agressivo_quando_regime_melhora() -> None:
    # Bloco anterior com 0% wins, bloco recente com 100% wins.
    trades = _trades_from_pnl(([-1.0] * 12) + ([1.0] * 12))
    decisao = decidir_switch_perfil_profit_protection(
        trades_fechados=trades,
        perfil_atual="baseline",
        perfis_disponiveis=["baseline", "conservador", "agressivo"],
    )
    assert decisao.regime_shift_detectado is True
    assert decisao.deve_trocar is True
    assert decisao.perfil_sugerido == "agressivo"


def test_troca_para_conservador_por_quebra_correlacao_sem_shift_win_rate() -> None:
    trades = [
        {"pnl": 1.0, "correlacao_rolling": 0.82},
        {"pnl": -1.0, "correlacao_rolling": 0.78},
        {"pnl": 1.0, "correlacao_rolling": 0.75},
        {"pnl": -1.0, "correlacao_rolling": 0.20},
        {"pnl": 1.0, "correlacao_rolling": 0.18},
        {"pnl": -1.0, "correlacao_rolling": 0.22},
    ]
    decisao = decidir_switch_perfil_profit_protection(
        trades_fechados=trades,
        perfil_atual="agressivo",
        perfis_disponiveis=["baseline", "conservador", "agressivo"],
        janela_recente=3,
        delta_regime_pp=99.0,
        limiar_quebra_correlacao=0.30,
        min_eventos_quebra_correlacao=2,
        min_sinais_degradacao=4,
    )
    assert decisao.regime_shift_detectado is True
    assert decisao.deve_trocar is True
    assert decisao.perfil_sugerido == "conservador"
    assert "correlacao" in decisao.motivo.lower()


def test_quebra_correlacao_sem_perfil_conservador_faz_fallback_baseline() -> None:
    trades = [
        {"pnl": 1.0, "correlacao_rolling": 0.85},
        {"pnl": -1.0, "correlacao_rolling": 0.87},
        {"pnl": 1.0, "correlacao_rolling": 0.81},
        {"pnl": -1.0, "correlacao_rolling": 0.10},
        {"pnl": 1.0, "correlacao_rolling": 0.12},
        {"pnl": -1.0, "correlacao_rolling": 0.15},
    ]
    decisao = decidir_switch_perfil_profit_protection(
        trades_fechados=trades,
        perfil_atual="agressivo",
        perfis_disponiveis=["baseline", "agressivo"],
        janela_recente=3,
        delta_regime_pp=99.0,
        limiar_quebra_correlacao=0.30,
        min_eventos_quebra_correlacao=2,
    )
    assert decisao.regime_shift_detectado is True
    assert decisao.deve_trocar is True
    assert decisao.perfil_sugerido == "baseline"


def test_troca_para_conservador_por_degradacao_intraday_critica_sem_shift() -> None:
    # Win rate parecido entre blocos, mas bloco recente com pior sequencia de perdas
    # e resultado acumulado fortemente negativo.
    trades = _trades_from_pnl(
        [-1.0, 1.0, -1.0, -1.0, -1.0, 1.0] + [-1.0, -1.0, -1.0, 1.0, -1.0, -1.0]
    )
    decisao = decidir_switch_perfil_profit_protection(
        trades_fechados=trades,
        perfil_atual="agressivo",
        perfis_disponiveis=["baseline", "conservador", "agressivo"],
        janela_recente=6,
        delta_regime_pp=99.0,
        min_eventos_quebra_correlacao=99,
        limiar_win_rate_degradado=0.35,
        min_loss_streak_degradado=3,
        limiar_resultado_acumulado_degradado=-2.0,
        min_sinais_degradacao=2,
    )
    assert decisao.regime_shift_detectado is True
    assert decisao.deve_trocar is True
    assert decisao.perfil_sugerido == "conservador"
    assert "degradacao intraday critica" in decisao.motivo.lower()


def test_troca_por_degradacao_critica_com_amostra_parcial() -> None:
    # Menos trades que 2 * janela_recente, mas com degradacao clara.
    trades = _trades_from_pnl([-0.22, -0.19, -0.12, -0.11, -0.08])
    decisao = decidir_switch_perfil_profit_protection(
        trades_fechados=trades,
        perfil_atual="baseline",
        perfis_disponiveis=["baseline", "conservador", "agressivo"],
        janela_recente=12,
        delta_regime_pp=10.0,
        limiar_win_rate_degradado=0.35,
        min_loss_streak_degradado=3,
        limiar_resultado_acumulado_degradado=-0.10,
        min_sinais_degradacao=2,
        min_trades_degradacao_critica=4,
    )
    assert decisao.deve_trocar is True
    assert decisao.perfil_sugerido == "conservador"
    assert "amostra parcial" in decisao.motivo.lower()


def test_cooldown_permite_primeira_troca() -> None:
    permitido, motivo = aplicar_guardrail_cooldown_switch(
        ciclo_atual=40,
        ultimo_ciclo_switch=None,
        min_ciclos_entre_switches=30,
    )
    assert permitido is True
    assert "Primeira troca" in motivo


def test_cooldown_bloqueia_troca_antes_do_minimo() -> None:
    permitido, motivo = aplicar_guardrail_cooldown_switch(
        ciclo_atual=45,
        ultimo_ciclo_switch=40,
        min_ciclos_entre_switches=30,
    )
    assert permitido is False
    assert "faltam" in motivo


def test_validacao_sessao_bloqueia_thrashing_via_cooldown() -> None:
    # Sequencia com alternancia frequente de regime para pressionar switches.
    bloco_a = [1.0, 1.0, 1.0, -1.0, -1.0, -1.0]
    bloco_b = [-1.0, -1.0, -1.0, 1.0, 1.0, 1.0]
    valores = (bloco_a + bloco_b) * 6
    trades_por_ciclo = [[{"pnl": valor}] for valor in valores]

    resultado = validar_sessao_runtime_profit_protection(
        trades_por_ciclo=trades_por_ciclo,
        perfil_inicial="baseline",
        perfis_disponiveis=["baseline", "conservador", "agressivo"],
        min_ciclos_entre_switches=8,
        avaliar_a_cada_n_ciclos=1,
        janela_recente=3,
        delta_regime_pp=20.0,
        limite_switches_por_100_avaliacoes=15.0,
    )
    assert resultado.total_avaliacoes > 0
    assert resultado.total_switches_bloqueados_cooldown > 0
    assert resultado.thrashing_detectado is False
    assert "dentro do limite" in resultado.motivo_thrashing


def test_validacao_sessao_detecta_thrashing_sem_cooldown() -> None:
    bloco_a = [1.0, 1.0, 1.0, -1.0, -1.0, -1.0]
    bloco_b = [-1.0, -1.0, -1.0, 1.0, 1.0, 1.0]
    valores = (bloco_a + bloco_b) * 5
    trades_por_ciclo = [[{"pnl": valor}] for valor in valores]

    resultado = validar_sessao_runtime_profit_protection(
        trades_por_ciclo=trades_por_ciclo,
        perfil_inicial="baseline",
        perfis_disponiveis=["baseline", "conservador", "agressivo"],
        min_ciclos_entre_switches=0,
        avaliar_a_cada_n_ciclos=1,
        janela_recente=3,
        delta_regime_pp=20.0,
        limite_switches_por_100_avaliacoes=10.0,
    )
    assert resultado.total_switches_realizados > 0
    assert resultado.thrashing_detectado is True
    assert "acima do limite" in resultado.motivo_thrashing


def test_validacao_sessao_parametros_invalidos() -> None:
    try:
        validar_sessao_runtime_profit_protection(
            trades_por_ciclo=[],
            perfil_inicial="baseline",
            perfis_disponiveis=["baseline"],
            min_ciclos_entre_switches=0,
            avaliar_a_cada_n_ciclos=0,
        )
        assert False, "Era esperado ValueError para avaliar_a_cada_n_ciclos=0."
    except ValueError:
        pass

    try:
        validar_sessao_runtime_profit_protection(
            trades_por_ciclo=[],
            perfil_inicial="baseline",
            perfis_disponiveis=["baseline"],
            min_ciclos_entre_switches=0,
            limiar_win_rate_degradado=1.5,
        )
        assert False, "Era esperado ValueError para limiar_win_rate_degradado fora de faixa."
    except ValueError:
        pass

    try:
        validar_sessao_runtime_profit_protection(
            trades_por_ciclo=[],
            perfil_inicial="baseline",
            perfis_disponiveis=["baseline"],
            min_ciclos_entre_switches=0,
            min_trades_degradacao_critica=0,
        )
        assert False, "Era esperado ValueError para min_trades_degradacao_critica=0."
    except ValueError:
        pass
