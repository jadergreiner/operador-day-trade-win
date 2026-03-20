from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.orders_executor import (
    ExecutionOrder,
    OrdersExecutor,
    OrderState,
)


@pytest.fixture
def executor() -> OrdersExecutor:
    risk_processor = MagicMock()
    mt5_adapter = MagicMock()
    trade_repository = MagicMock()
    return OrdersExecutor(risk_processor, mt5_adapter, trade_repository)


@pytest.mark.asyncio
async def test_monitor_positions_calcula_pnl_e_aciona_stop_loss_com_adapter_sincrono(
    executor: OrdersExecutor,
) -> None:
    posicao = SimpleNamespace(
        symbol="WINJ26",
        volume=1.0,
        entry_price=100.0,
        stop_loss=99.0,
        type="BUY",
        ticket=12345,
    )
    executor.mt5_adapter.get_positions.return_value = [posicao]
    executor.mt5_adapter.get_current_price.return_value = 98.5
    executor.handle_stop_loss = AsyncMock(return_value={"success": True})

    resultado = await executor.monitor_positions()

    assert resultado is not None
    assert resultado["total_positions"] == 1
    assert resultado["total_pnl_unrealized"] == pytest.approx(-1.5)
    assert resultado["positions"][0]["current_price"] == pytest.approx(98.5)
    assert resultado["stop_loss_events"] == [
        {
            "position_id": "12345",
            "symbol": "WINJ26",
            "close_success": True,
        }
    ]
    executor.handle_stop_loss.assert_awaited_once_with("12345")


@pytest.mark.asyncio
async def test_handle_stop_loss_fecha_ordem_conhecida_por_ticket(
    executor: OrdersExecutor,
) -> None:
    ordem = ExecutionOrder(
        order_id="ORD-STOP-1",
        symbol="WINJ26",
        order_type="BUY",
        volume=1.0,
        entry_price=100000.0,
        stop_loss=99900.0,
        take_profit=100200.0,
        detector_spike=2.0,
        ml_classifier_score=0.85,
        mt5_ticket="777",
    )
    executor.orders[ordem.order_id] = ordem
    executor.mt5_adapter.close_position_by_id = AsyncMock(
        return_value={"success": True}
    )

    resultado = await executor.handle_stop_loss("777")

    assert resultado["success"] is True
    assert ordem.state == OrderState.CLOSED
    assert ordem.audit_log[-1].metadata["trigger"] == "stop_loss"
    assert executor.stop_loss_events[-1]["order_id"] == "777"


@pytest.mark.asyncio
async def test_monitor_positions_retorna_none_em_falha_do_adapter(
    executor: OrdersExecutor,
) -> None:
    executor.mt5_adapter.get_positions = AsyncMock(
        side_effect=RuntimeError("mt5 offline")
    )

    resultado = await executor.monitor_positions()

    assert resultado is None
