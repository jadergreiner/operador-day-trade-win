"""Testes do runtime RL/MT5 do agente direto.

Cobertura:
- PnL coerente com preço de saída real
- Ticket/sessão atual sem contaminação entre sessões
- Backoff 10006 no caminho dinâmico
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from scripts.agente_rl_direto_independente import (
    AGENT_SESSION_ID,
    classificar_fechamento_trade,
    enviar_ordem,
    enviar_ordem_com_backoff,
    obter_contexto_fechamento_sessao_atual,
)
from src.application.motor_decisao_isolado import (
    DecisaoOperacional,
    MotorDecisaoIsolado,
    TipoPosicao,
)
from src.application.ordem_backoff_retry import GerenciadorRetryOrdem
from src.application.posicao_isolamento import PosicaoIsoladaManager


class TestRuntimeFechamento:
    def test_classificar_fechamento_trade_buy_usa_preco_saida_real(self) -> None:
        resultado, pnl = classificar_fechamento_trade(
            preco_entrada=100000.0,
            preco_saida=100500.0,
            tipo_posicao=TipoPosicao.COMPRADA,
            volume=1.0,
        )

        assert resultado == "WIN"
        assert pnl == pytest.approx(100.0, abs=0.01)

    def test_classificar_fechamento_trade_sell_usa_preco_saida_real(self) -> None:
        resultado, pnl = classificar_fechamento_trade(
            preco_entrada=100500.0,
            preco_saida=100000.0,
            tipo_posicao=TipoPosicao.VENDIDA,
            volume=2.0,
        )

        assert resultado == "WIN"
        assert pnl == pytest.approx(200.0, abs=0.01)

    def test_desconhecido_persistente_quando_ticket_nao_e_da_sessao_atual(
        self, tmp_path
    ) -> None:
        posicao_mgr = PosicaoIsoladaManager(
            session_id=AGENT_SESSION_ID,
            agent_version="rl_direto_v3.0",
            outputs_dir=tmp_path,
        )
        motor = MotorDecisaoIsolado(
            agent_id=AGENT_SESSION_ID,
            data_dir=tmp_path,
        )

        motor.abrir_posicao(
            ticket=1111,
            tipo=TipoPosicao.COMPRADA,
            preco_entrada=100000.0,
            volume=1.0,
            stop_loss=99900.0,
            take_profit=100200.0,
        )
        posicao_mgr.registrar_posicao_aberta(
            preco_entrada=100000.0,
            ticket=2222,
            lado="BUY",
            quantidade=1,
        )

        contexto = obter_contexto_fechamento_sessao_atual(posicao_mgr, motor)

        assert contexto is None

    def test_backoff_10006_no_caminho_dinamico(self) -> None:
        mt5_adapter = MagicMock()
        tentativas = {"count": 0}

        def send_order(_order):
            tentativas["count"] += 1
            if tentativas["count"] < 3:
                raise Exception("Order execution failed (code: 10006)")
            return "999999"

        mt5_adapter.send_order.side_effect = send_order

        retry_mgr = GerenciadorRetryOrdem(
            simbolo="WINJ26",
            limite_encerrar=5,
            verificar_rollover=False,
        )
        ordem = SimpleNamespace(symbol="WINJ26")

        with patch("time.sleep") as sleep_mock:
            ticket = enviar_ordem_com_backoff(
                mt5_adapter,
                ordem,
                retry_mgr=retry_mgr,
            )

        assert ticket == "999999"
        assert tentativas["count"] == 3
        sleep_mock.assert_any_call(5.0)
        sleep_mock.assert_any_call(15.0)


class TestRuntimeIsolationExtras:
    def test_contexto_fechamento_retorna_none_quando_session_diverge(
        self, tmp_path
    ) -> None:
        posicao_mgr = PosicaoIsoladaManager(
            session_id="sessao_a",
            agent_version="rl_direto_v3.0",
            outputs_dir=tmp_path,
        )
        motor = MotorDecisaoIsolado(
            agent_id="sessao_a",
            data_dir=tmp_path,
        )

        motor.abrir_posicao(
            ticket=3333,
            tipo=TipoPosicao.VENDIDA,
            preco_entrada=100200.0,
            volume=1.0,
            stop_loss=100300.0,
            take_profit=100000.0,
        )
        posicao_mgr.registrar_posicao_aberta(
            preco_entrada=100200.0,
            ticket=3333,
            lado="SELL",
            quantidade=1,
        )

        contexto = obter_contexto_fechamento_sessao_atual(posicao_mgr, motor)
        assert contexto is None

    def test_enviar_ordem_bloqueia_quando_contexto_abertura_contraria_compra(
        self,
        tmp_path,
    ) -> None:
        mt5_adapter = MagicMock()
        mt5_adapter.get_positions.return_value = []
        posicao_tracker = MagicMock()
        motor = MotorDecisaoIsolado(
            agent_id="sessao_b",
            data_dir=tmp_path,
        )

        with patch("scripts.agente_rl_direto_independente.datetime") as mock_dt:
            fake_now = MagicMock()
            fake_now.time.return_value = datetime(2026, 3, 19, 10, 30).time()
            mock_dt.now.return_value = fake_now

            ok = enviar_ordem(
                mt5_adapter=mt5_adapter,
                acao="Comprar",
                preco_atual=100000.0,
                posicao_tracker=posicao_tracker,
                rl_repo=None,
                trade_tracker=None,
                motor_decisao=motor,
                opening_context={
                    "vies_intraday": "NEUTRO_LEVEMENTE_BAIXISTA",
                    "watchlist": ["PETR4", "VALE3", "DOL"],
                },
                confidence=0.68,
            )

        assert ok is False
        assert motor.decisoes[-1].decisao == DecisaoOperacional.CANCELAR
        assert (
            motor.decisoes[-1].contexto_operacional["contexto_abertura_liberado"]
            is False
        )
        assert "live_market_confirmation" in motor.decisoes[-1].contexto_operacional
