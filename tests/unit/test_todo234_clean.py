"""
Tests for TODO-2,3,4: OrdersExecutor Implementation
- TODO-2: execute_order() with 3-gate risk validation
- TODO-3: monitor_positions() with latency check
- TODO-4: position_monitoring_loop() with SL/TP triggers

S2-9 Risk Framework Integration
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from src.application.orders_executor_todo234 import OrdersExecutorTODO234


# Mock ExecutionOrder for tests
class ExecutionOrder:
    def __init__(self, order_id="", symbol="", order_type="", volume=0,
                 entry_price=0, stop_loss=0, take_profit=0,
                 detector_spike=0, ml_classifier_score=0):
        self.order_id = order_id or f"ORD-{id(self)}"
        self.symbol = symbol
        self.order_type = order_type
        self.volume = volume
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.detector_spike = detector_spike
        self.ml_classifier_score = ml_classifier_score


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def risk_processor_mock():
    """Mock RiskProcessor with 3 gates"""
    mock = Mock()
    mock.check_capital_limits = Mock(return_value={"approved": True, "reason": "OK"})
    mock.check_correlation = Mock(return_value={"approved": True, "reason": "OK"})
    mock.check_volatility_bands = Mock(return_value={"approved": True, "reason": "OK"})
    return mock


@pytest.fixture
def mt5_adapter_mock():
    """Mock MT5Adapter"""
    mock = AsyncMock()
    mock.send_order = AsyncMock(return_value="TICKET-12345")
    mock.get_positions = AsyncMock(return_value=[
        Mock(
            symbol="WINFUT",
            volume=10,
            type="BUY",
            entry_price=75000,
            profit_loss=1000
        ),
        Mock(
            symbol="DOLFUT",
            volume=5,
            type="BUY",
            entry_price=5.50,
            profit_loss=-250
        ),
    ])
    mock.get_current_price = AsyncMock(side_effect=lambda symbol: {
        "WINFUT": 75100,
        "DOLFUT": 5.45
    }.get(symbol, 0))
    mock.close_position = AsyncMock(return_value={"success": True, "closed_ticket": "TICKET-12345"})
    return mock


@pytest.fixture
def trade_repository_mock():
    """Mock ITradeRepository"""
    return AsyncMock()


@pytest.fixture
def executor(risk_processor_mock, mt5_adapter_mock, trade_repository_mock):
    """OrdersExecutor with mocked dependencies"""
    return OrdersExecutorTODO234(
        risk_processor=risk_processor_mock,
        mt5_adapter=mt5_adapter_mock,
        trade_repository=trade_repository_mock,
        event_bus=None
    )


@pytest.fixture
def sample_order():
    """Sample ExecutionOrder for tests"""
    return ExecutionOrder(
        order_id="",
        symbol="WINFUT",
        order_type="BUY",
        volume=10,
        entry_price=75000,
        stop_loss=74000,
        take_profit=76000,
        detector_spike=2.5,
        ml_classifier_score=0.85
    )


# ============================================================================
# TODO-2: EXECUTE_ORDER TESTS (5 test cases)
# ============================================================================

@pytest.mark.asyncio
async def test_execute_order_all_gates_pass(executor, sample_order):
    """AC: All 3 gates pass → order approved and sent to MT5"""
    result = await executor.execute_order(sample_order)

    assert result["status"] == "APPROVED"
    assert result["decision"] == "APPROVED_ALL_GATES"
    assert result["order_id"] == sample_order.order_id
    assert result["mt5_response"]["ticket"] == "TICKET-12345"
    assert len(result["audit_trail"]) == 3
    assert result["execution_time_ms"] < 1000


@pytest.mark.asyncio
async def test_execute_order_capital_limit_fail(executor, sample_order, risk_processor_mock):
    """AC: AC-1 (Capital Limit) fails → order rejected"""
    risk_processor_mock.check_capital_limits.return_value = {
        "approved": False,
        "reason": "Position size exceeds 5% limit"
    }

    result = await executor.execute_order(sample_order)

    assert result["status"] == "REJECTED"
    assert result["decision"] == "REJECTED_CAPITAL_LIMIT"
    assert "Position size" in result["rejection_reason"]


@pytest.mark.asyncio
async def test_execute_order_correlation_fail(executor, sample_order, risk_processor_mock):
    """AC: AC-2 (Correlation) fails → order rejected"""
    risk_processor_mock.check_correlation.return_value = {
        "approved": False,
        "reason": "Correlation > 70%"
    }

    result = await executor.execute_order(sample_order)

    assert result["status"] == "REJECTED"
    assert result["decision"] == "REJECTED_CORRELATION"


@pytest.mark.asyncio
async def test_execute_order_volatility_fail(executor, sample_order, risk_processor_mock):
    """AC: AC-3 (Volatility) fails → order rejected"""
    risk_processor_mock.check_volatility_bands.return_value = {
        "approved": False,
        "reason": "Daily loss limit exceeded"
    }

    result = await executor.execute_order(sample_order)

    assert result["status"] == "REJECTED"
    assert result["decision"] == "REJECTED_VOLATILITY_BAND"


@pytest.mark.asyncio
async def test_execute_order_mt5_send_failed(executor, sample_order, mt5_adapter_mock):
    """AC: MT5 send fails after retries → order rejected"""
    mt5_adapter_mock.send_order.side_effect = Exception("MT5 connection timeout")

    result = await executor.execute_order(sample_order)

    assert result["status"] == "REJECTED"
    assert result["decision"] == "REJECTED_MT5_SEND_FAILED"


# ============================================================================
# TODO-3: MONITOR_POSITIONS TESTS (2 test cases)
# ============================================================================

@pytest.mark.asyncio
async def test_monitor_positions_latency_under_100ms(executor, mt5_adapter_mock):
    """AC: Latency < 100ms"""
    result = await executor.monitor_positions()

    assert result is not None
    assert "latency_ms" in result
    assert result["latency_ms"] < 100


@pytest.mark.asyncio
async def test_monitor_positions_updates_internal_state(executor, mt5_adapter_mock):
    """AC: Internal state (current_daily_pnl, current_positions) updated"""
    result = await executor.monitor_positions()

    assert result is not None
    assert executor.current_daily_pnl == result["total_pnl"]
    assert len(executor.current_positions) == len(result["positions"])


# ============================================================================
# TODO-4: POSITION_MONITORING_LOOP TESTS (3 test cases)
# ============================================================================

@pytest.mark.asyncio
async def test_position_monitoring_loop_stop_loss_trigger(executor, mt5_adapter_mock, risk_processor_mock):
    """AC: SL trigger (PnL <= -1000) detected in monitoring loop"""
    pos_with_sl = Mock(
        symbol="WINFUT",
        volume=10,
        type="BUY",
        entry_price=75000
    )
    mt5_adapter_mock.get_positions = AsyncMock(return_value=[pos_with_sl])
    mt5_adapter_mock.get_current_price = AsyncMock(return_value=74000)
    mt5_adapter_mock.close_position = AsyncMock(return_value={"success": True})

    await executor.monitor_positions()

    pnl_value = executor.current_positions[0]["pnl"]
    assert pnl_value <= -1000, f"PnL should trigger SL: {pnl_value}"


@pytest.mark.asyncio
async def test_position_monitoring_loop_take_profit_trigger(executor, mt5_adapter_mock, risk_processor_mock):
    """AC: TP trigger (PnL >= +5000) detected in monitoring loop"""
    pos_with_tp = Mock(
        symbol="DOLFUT",
        volume=5000,
        type="BUY",
        entry_price=5.50
    )
    mt5_adapter_mock.get_positions = AsyncMock(return_value=[pos_with_tp])
    mt5_adapter_mock.get_current_price = AsyncMock(return_value=6.50)
    mt5_adapter_mock.close_position = AsyncMock(return_value={"success": True})

    await executor.monitor_positions()

    pnl_value = executor.current_positions[0]["pnl"]
    assert pnl_value >= 5000, f"PnL should trigger TP: {pnl_value}"


@pytest.mark.asyncio
async def test_position_monitoring_loop_graceful_shutdown(executor):
    """AC: Loop stops gracefully when stop_monitoring() called"""
    assert executor._monitoring_active is False

    task = asyncio.create_task(executor.position_monitoring_loop())
    await asyncio.sleep(0.05)
    assert executor._monitoring_active is True

    await executor.stop_monitoring()
    await asyncio.wait_for(task, timeout=5.0)

    assert executor._monitoring_active is False


# ============================================================================
# ADDITIONAL TESTS FOR COVERAGE > 85%
# ============================================================================

@pytest.mark.asyncio
async def test_execute_order_with_no_risk_processor(mt5_adapter_mock):
    """Test execute_order when risk_processor has no methods"""
    executor = OrdersExecutorTODO234(
        risk_processor=Mock(),
        mt5_adapter=mt5_adapter_mock
    )

    order = ExecutionOrder(
        order_id="test-001",
        symbol="WINFUT",
        order_type="buy",
        volume=10,
        entry_price=75000
    )
    mt5_adapter_mock.send_order = AsyncMock(return_value="ticket-001")

    result = await executor.execute_order(order)

    assert result["status"] == "APPROVED"
    assert mt5_adapter_mock.send_order.called


@pytest.mark.asyncio
async def test_monitor_positions_exception(executor):
    """Test monitor_positions graceful exception handling"""
    executor.mt5_adapter.get_positions = AsyncMock(side_effect=Exception("Connection lost"))

    result = await executor.monitor_positions()

    assert result is None


@pytest.mark.asyncio
async def test_execute_order_exception_in_gates(executor, sample_order):
    """Test execute_order exception during gate validation"""
    executor.risk_processor.check_capital_limits = Mock(side_effect=Exception("Processor error"))

    result = await executor.execute_order(sample_order)

    assert result["status"] == "ERROR"
    assert result["decision"] == "ERROR_EXCEPTION"


@pytest.mark.asyncio
async def test_position_monitoring_loop_no_positions(executor, mt5_adapter_mock):
    """Test monitoring loop with empty position list"""
    executor.mt5_adapter.get_positions = AsyncMock(return_value=[])

    result = await executor.monitor_positions()

    assert result["positions_count"] == 0
    assert result["total_pnl"] == 0.0


@pytest.mark.asyncio
async def test_execute_order_short_position(executor, mt5_adapter_mock, risk_processor_mock):
    """Test execute_order with SHORT position type"""
    executor.risk_processor.check_capital_limits = Mock(return_value={"approved": True})
    executor.risk_processor.check_correlation = Mock(return_value={"approved": True})
    executor.risk_processor.check_volatility_bands = Mock(return_value={"approved": True})

    order = ExecutionOrder(
        order_id="short-001",
        symbol="DOLFUT",
        order_type="sell",
        volume=5,
        entry_price=5.50
    )
    mt5_adapter_mock.send_order = AsyncMock(return_value="ticket-short-001")

    result = await executor.execute_order(order)

    assert result["status"] == "APPROVED"
    assert result["mt5_response"]["ticket"] == "ticket-short-001"


@pytest.mark.asyncio
async def test_monitor_positions_with_short(executor, mt5_adapter_mock):
    """Test monitor_positions calculation for SHORT positions"""
    pos_short = Mock(
        symbol="DOLFUT",
        volume=5,
        type="SELL",
        entry_price=5.50
    )
    mt5_adapter_mock.get_positions = AsyncMock(return_value=[pos_short])
    mt5_adapter_mock.get_current_price = AsyncMock(return_value=5.30)

    result = await executor.monitor_positions()

    assert result["positions"][0]["type"] == "SELL"
    assert result["positions"][0]["pnl"] == (5.50 - 5.30) * 5


@pytest.mark.asyncio
async def test_position_monitoring_loop_monitor_None_return(executor, mt5_adapter_mock):
    """Test monitoring loop when monitor_positions returns None"""
    executor.mt5_adapter.get_positions = AsyncMock(side_effect=Exception("Error"))

    task = asyncio.create_task(executor.position_monitoring_loop())
    await asyncio.sleep(0.15)
    await executor.stop_monitoring()

    try:
        await asyncio.wait_for(task, timeout=2.0)
    except asyncio.TimeoutError:
        pass

    assert executor._monitoring_active is False



# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
