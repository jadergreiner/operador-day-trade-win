from __future__ import annotations

import logging
from datetime import datetime
from datetime import time as dtime
from unittest.mock import MagicMock, patch

from scripts.agente_rl_direto_independente import (
    MAX_TRADES_PER_SESSION,
    AntiOvertradingProtection,
    enviar_ordem,
    registrar_bloqueio_anti_overtrading,
    verificar_horario_trading,
    verificar_janela_novas_entradas,
)


def test_janelas_operacionais_do_agente_direto_respeitam_prd() -> None:
    assert verificar_horario_trading(dtime(9, 0)) is True
    assert verificar_horario_trading(dtime(17, 55)) is True
    assert verificar_horario_trading(dtime(17, 56)) is False

    assert verificar_janela_novas_entradas(dtime(17, 25)) is True
    assert verificar_janela_novas_entradas(dtime(17, 26)) is False


def test_anti_overtrading_respeita_limite_diario_do_prd() -> None:
    protecao = AntiOvertradingProtection(max_trades_per_hour=99)
    base = datetime(2026, 3, 19, 10, 0)

    for idx in range(MAX_TRADES_PER_SESSION):
        protecao.registrar_trade(base.replace(minute=idx))

    permitido, motivo = protecao.pode_tradear(base.replace(hour=11, minute=0))

    assert permitido is False
    assert "Limite diário" in motivo


def test_anti_overtrading_ativa_cooldown_pos_loss_por_30_minutos() -> None:
    protecao = AntiOvertradingProtection()
    agora = datetime(2026, 3, 19, 11, 0)

    protecao.registrar_perda(agora)
    permitido, motivo = protecao.pode_tradear(agora.replace(minute=10))

    assert permitido is False
    assert protecao.cooldown_until == agora.replace(minute=30)
    assert "cooldown global" in motivo.lower()


def test_anti_overtrading_libera_pos_cooldown_sem_bloqueio_permanente() -> None:
    protecao = AntiOvertradingProtection()
    agora = datetime(2026, 3, 19, 11, 0)

    protecao.registrar_perda(agora)
    protecao.registrar_perda(agora.replace(minute=1))

    permitido, motivo = protecao.pode_tradear(agora.replace(minute=31))

    assert permitido is True
    assert protecao.consecutive_losses == 0
    assert "permitido" in motivo.lower()


def test_enviar_ordem_bloqueia_fora_da_janela_de_novas_entradas() -> None:
    mt5_adapter = MagicMock()
    posicao_tracker = MagicMock()
    motor_decisao = MagicMock()

    with patch("scripts.agente_rl_direto_independente.datetime") as mock_dt:
        fake_now = MagicMock()
        fake_now.time.return_value = dtime(17, 26)
        mock_dt.now.return_value = fake_now

        ok = enviar_ordem(
            mt5_adapter=mt5_adapter,
            acao="Comprar",
            preco_atual=100000.0,
            posicao_tracker=posicao_tracker,
            rl_repo=None,
            trade_tracker=None,
            motor_decisao=motor_decisao,
            confidence=0.68,
        )

    assert ok is False
    mt5_adapter.get_positions.assert_not_called()


def test_registrar_bloqueio_anti_overtrading_destaca_cooldown_em_log(
    caplog,
) -> None:
    with caplog.at_level(
        logging.WARNING, logger="scripts.agente_rl_direto_independente"
    ):
        registrar_bloqueio_anti_overtrading(
            1661,
            "Vender",
            "❌ Em cooldown global (299s restantes)",
        )

    assert any(
        "SINAL CONFIRMADO: Vender" in record.message
        and "cooldown pós-loss" in record.message
        for record in caplog.records
    )
