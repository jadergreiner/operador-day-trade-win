"""Testes da politica estruturada de contexto de abertura."""

from src.application.opening_context_policy import (
    evaluate_opening_context_gate,
    normalize_opening_context,
)


def test_normalize_opening_context_prioriza_watchlist_e_bias() -> None:
    policy = normalize_opening_context(
        {
            "regime_macro": "CAUTELOSO",
            "vies_intraday": "NEUTRO_LEVEMENTE_BAIXISTA",
            "watchlist": ["PETR4", "VALE3", "DOL"],
            "prompt_abertura_agentes": "Prompt curto",
        }
    )

    assert policy.regime_macro == "CAUTELOSO"
    assert policy.vies_intraday == "NEUTRO_LEVEMENTE_BAIXISTA"
    assert policy.heavyweights == ["PETR4", "VALE3"]
    assert policy.watchlist == ["PETR4", "VALE3", "DOL"]


def test_gate_bloqueia_compra_contra_vies_baixista_sem_confirmacao() -> None:
    result = evaluate_opening_context_gate(
        "Comprar",
        {
            "vies_intraday": "NEUTRO_LEVEMENTE_BAIXISTA",
            "watchlist": ["PETR4", "VALE3", "DOL"],
        },
        confidence=0.68,
        alignment=0.61,
    )

    assert result.allow_entry is False
    assert result.normalized_action == "BUY"
    assert "vies_intraday_baixista" in result.reasons
    assert "compra_sem_confirmacao_contextual" in result.reasons
    assert result.required_confirmations == ["PETR4", "VALE3", "DOL", "IBOV", "EWZ"]


def test_gate_compra_permite_sem_confirmacao_forte_mas_com_monitores_positivos() -> None:
    result = evaluate_opening_context_gate(
        "Comprar",
        {
            "vies_intraday": "NEUTRO",
            "watchlist": ["PETR4", "VALE3", "DOL"],
        },
        confidence=0.85,
        alignment=0.8,
        market_confirmation={
            "buy_confirmed": False,
            "monitors_positive": ["EWZ"],
            "monitors_negative": [],
        },
    )

    assert result.allow_entry is True
    assert "compra_sem_confirmacao_live" in result.reasons
    assert "monitores_favoraveis:EWZ" in result.reasons
    assert result.to_context_payload()["live_market_confirmation"]["buy_confirmed"] is False


def test_gate_compra_bloqueia_sem_confirmacao_forte_com_monitores_contrarios() -> None:
    result = evaluate_opening_context_gate(
        "Comprar",
        {
            "vies_intraday": "NEUTRO",
            "watchlist": ["PETR4", "VALE3", "DOL"],
        },
        confidence=0.85,
        alignment=0.8,
        market_confirmation={
            "buy_confirmed": False,
            "monitors_positive": ["EWZ"],
            "monitors_negative": ["IBOV"],
        },
    )

    assert result.allow_entry is False
    assert "compra_sem_confirmacao_live" in result.reasons
    assert "monitores_contrarios:IBOV" in result.reasons
    assert "compra_contraria_contexto_abertura" in result.reasons


def test_gate_bloqueia_quando_kill_switch_da_abertura_esta_ativo() -> None:
    result = evaluate_opening_context_gate(
        "Vender",
        {
            "kill_switch_ativo": True,
            "kill_switch_reason": "macro_evento_critico",
        },
        confidence=0.9,
    )

    assert result.allow_entry is False
    assert "kill_switch_abertura_ativo" in result.reasons
    assert "macro_evento_critico" in result.reasons
