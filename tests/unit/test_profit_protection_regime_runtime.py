"""Testes unitarios para decisor runtime de perfil do Profit Protection."""

from src.application.profit_protection_regime_runtime import (
    aplicar_guardrail_cooldown_switch,
    decidir_switch_perfil_profit_protection,
)


def _trades_from_pnl(values: list[float]) -> list[dict]:
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
