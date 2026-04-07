"""Testes de fechamento manual e reconciliação de saída."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from src.application.ac5_8_position_monitor import (
    MonitorPositionManager,
    StatusOrdem,
)
from src.application.position_closure_detector import (
    ClosureOrigin,
    ClosureReason,
    PositionClosureDetector,
)


class _MT5Stub:
    """Stub mínimo do broker para validar reconciliação externa."""

    def get_positions(self, _symbol: object) -> list[object]:
        return []

    def obter_preco_saida_por_ticket(
        self,
        _ticket: int,
        *,
        symbol: object,
        side: object,
    ) -> float:
        del symbol, side
        return 100.8

    def obter_pnl_fechado(self, _ticket: int, _magic_number: int) -> float:
        return 0.8


def test_deve_detectar_fechamento_manual_do_operador() -> None:
    """Quando não bateu TP/SL, a origem deve ser do operador."""
    detector = PositionClosureDetector()

    motivo, origem = detector.classificar_fechamento_externo(
        preco_entrada=100.0,
        preco_saida=100.8,
        take_profit=102.0,
        stop_loss=99.0,
        direcao="BUY",
        timestamp_abertura=datetime.now() - timedelta(minutes=5),
        timestamp_fechamento=datetime.now(),
    )

    assert motivo == ClosureReason.MANUAL_CLOSE
    assert origem == ClosureOrigin.OPERADOR


def test_deve_distinguir_take_profit_do_fechamento_manual() -> None:
    """Se o preço final bate TP, a origem deve ser de mercado."""
    detector = PositionClosureDetector()

    motivo, origem = detector.classificar_fechamento_externo(
        preco_entrada=100.0,
        preco_saida=102.0,
        take_profit=102.0,
        stop_loss=99.0,
        direcao="BUY",
        timestamp_abertura=datetime.now() - timedelta(minutes=5),
        timestamp_fechamento=datetime.now(),
    )

    assert motivo == ClosureReason.TP_HIT
    assert origem == ClosureOrigin.MERCADO


def test_monitor_deve_persistir_motivo_e_origem_do_encerramento() -> None:
    """O monitor precisa salvar motivo, origem e PnL final do fechamento."""
    monitor = MonitorPositionManager(db_caminho=":memory:")

    monitor.registrar_ordem(
        {
            "trade_id": "TRADE_123",
            "signal_id": "SIG_123",
            "symbol": "WIN$N",
            "direcao": "BUY",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 99.0,
            "tp": 102.0,
        }
    )
    monitor.atualizar_status_ordem("TRADE_123", StatusOrdem.FILLED)

    resultado = monitor.encerrar_posicao(
        trade_id="TRADE_123",
        preco_encerramento=100.8,
        motivo_encerramento="MANUAL_CLOSE",
        encerrado_por="OPERADOR",
        pl_final_override=0.8,
    )

    assert resultado is True
    fechadas = monitor.listar_posicoes_encerradas()
    assert len(fechadas) == 1
    assert fechadas[0]["motivo_encerramento"] == "MANUAL_CLOSE"
    assert fechadas[0]["encerrado_por"] == "OPERADOR"
    assert fechadas[0]["pl_final"] == pytest.approx(0.8)


def test_manager_deve_reconciliar_trade_fechado_fora_do_fluxo_local() -> None:
    """Quando o broker não retorna mais o ticket, o agente deve encerrar a posição."""
    pytest.importorskip("pydantic_settings")
    from scripts.agente_micro_tendencia_winfut import MicroTradingManager, OpenTrade

    monitor = MonitorPositionManager(db_caminho=":memory:")
    monitor.registrar_ordem(
        {
            "trade_id": "TRADE_SYNC",
            "signal_id": "SIG_SYNC",
            "symbol": "WIN$N",
            "direcao": "BUY",
            "volume": 1,
            "preco_entrada": 100.0,
            "sl": 99.0,
            "tp": 102.0,
        }
    )
    monitor.atualizar_status_ordem("TRADE_SYNC", StatusOrdem.FILLED)

    gerenciador = MicroTradingManager(
        mt5=_MT5Stub(),
        symbol_code="WIN$N",
        monitor_posicao=monitor,
    )
    gerenciador.open_trades = [
        OpenTrade(
            ticket="TRADE_SYNC",
            position_ticket=321,
            direction="COMPRA",
            entry_price=Decimal("100.0"),
            stop_loss=Decimal("99.0"),
            take_profit=Decimal("102.0"),
            quantity=1,
            opened_at=datetime.now() - timedelta(minutes=3),
            trailing_stop=Decimal("99.0"),
            reason="teste",
            context_entrada={"origem": "teste"},
        )
    ]

    gerenciador._sync_open_trades_with_broker()

    assert gerenciador.open_trades == []
    assert len(gerenciador.closed_trades) == 1
    assert gerenciador.closed_trades[0]["reason"] == "MANUAL_CLOSE"
    assert gerenciador.closed_trades[0]["closed_by"] == "OPERADOR"

    fechadas = monitor.listar_posicoes_encerradas()
    assert len(fechadas) == 1
    assert fechadas[0]["motivo_encerramento"] == "MANUAL_CLOSE"
    assert fechadas[0]["encerrado_por"] == "OPERADOR"
    assert fechadas[0]["pl_final"] == pytest.approx(0.8)
