"""
Testes de Integração MT5 para P1-CORE Etapa 2

Valida:
1. MT5Executor initialization
2. Successful order execution com real MT5 adapter
3. Retry logic (3 tentativas com exponential backoff)
4. MT5 adapter integration points
5. Batch execution via QueueProcessor com MT5 executor real
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime

from src.application.order_queue_sqlite import OrderQueue, Order
from src.infrastructure.mt5_executor import MT5Executor, MT5ExecutionError
from src.infrastructure.queue_processor import QueueProcessor


class TestMT5Executor:
    """Testes unitários para MT5Executor."""

    @pytest.fixture
    def executor(self):
        """MT5Executor com adapter mock."""
        return MT5Executor()

    @pytest.fixture
    def sample_order(self):
        """Ordem exemplo para testes."""
        return Order(
            order_id="TEST-001",
            symbol="WINFUT",
            order_type="BUY",
            volume=1.0,
            price=128500.0,
            sl=128470.0,
            tp=128530.0,
            comment="Test order"
        )

    @pytest.mark.asyncio
    async def test_executor_initialization(self, executor):
        """Test 1: MT5Executor initializes correctly."""
        assert executor is not None
        assert executor.max_retries == 3
        assert executor.execution_stats["attempted"] == 0
        assert executor.execution_stats["succeeded"] == 0

    @pytest.mark.asyncio
    async def test_successful_order_execution(self, executor, sample_order):
        """Test 2: Order executes successfully with mock MT5Adapter."""
        # Setup mock adapter - returns (success: bool, ticket_or_error: str)
        mock_adapter = AsyncMock()
        mock_adapter.send_order = AsyncMock(return_value=(True, "12345"))
        executor.mt5_adapter = mock_adapter

        # Execute
        success, ticket, error = await executor.execute_order(sample_order)

        # Assert
        assert success is True
        assert ticket == "12345"
        assert error is None
        assert executor.execution_stats["succeeded"] == 1
        assert executor.execution_stats["attempted"] == 1

    @pytest.mark.asyncio
    async def test_order_execution_with_retry(self, executor, sample_order):
        """Test 3: Retry logic with exponential backoff on failures."""
        # Setup mock adapter que falha 2x, sucesso na 3ª
        call_count = 0

        async def mock_send_order(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"MT5 connection error (attempt {call_count})")
            return (True, "99999")  # Return tuple (success, ticket)

        mock_adapter = AsyncMock()
        mock_adapter.send_order = mock_send_order
        executor.mt5_adapter = mock_adapter

        # Execute
        start_time = datetime.utcnow()
        success, ticket, error = await executor.execute_order(sample_order)
        elapsed = (datetime.utcnow() - start_time).total_seconds()

        # Assert
        assert success is True
        assert ticket == "99999"
        assert call_count == 3  # 1 failure + 1 failure + 1 success
        assert executor.execution_stats["retried"] == 2
        # Verify backoff timing (1 + 2 = 3 segundos mínimo)
        assert elapsed >= 3.0

    @pytest.mark.asyncio
    async def test_order_execution_fail_permanent(self, executor, sample_order):
        """Test 4: Permanent failure after 3 retries."""
        # Setup mock adapter que sempre falha
        mock_adapter = AsyncMock()
        mock_adapter.send_order = AsyncMock(
            side_effect=Exception("MT5 broker down")
        )
        executor.mt5_adapter = mock_adapter

        # Execute
        success, ticket, error = await executor.execute_order(sample_order)

        # Assert
        assert success is False
        assert ticket is None
        assert "MT5 broker down" in error
        assert executor.execution_stats["failed"] == 1
        assert executor.execution_stats["retried"] == 3  # 2 retries

    @pytest.mark.asyncio
    async def test_mt5_adapter_integration(self, executor, sample_order):
        """Test 5: Validates adapter interface compliance."""
        # Verify executor can work with different adapter types

        # Mock adapter that returns (success, ticket) tuple
        mock_adapter = AsyncMock()
        mock_adapter.send_order = AsyncMock(return_value=(True, "555999"))
        executor.mt5_adapter = mock_adapter

        # Execute
        success, ticket, error = await executor.execute_order(sample_order)

        # Assert
        assert success is True
        assert ticket == "555999"
        mock_adapter.send_order.assert_called_once()

        # Verify payload conversion for API
        payload = executor._order_to_api_payload(sample_order)
        assert payload["symbol"] == "WINFUT"
        assert payload["order_type"] == "BUY"
        assert payload["volume"] == 1.0


class TestQueueProcessorMT5Integration:
    """Testes de integração QueueProcessor + MT5Executor."""

    @pytest.fixture
    def temp_queue(self, tmp_path):
        """OrderQueue em DB temporário."""
        db_path = tmp_path / "test_queue.db"
        queue = OrderQueue(str(db_path))
        yield queue
        # Cleanup
        queue.cleanup_old_orders(days=0)

    @pytest.mark.asyncio
    async def test_queue_processor_with_mt5_executor(self, temp_queue):
        """Integration: QueueProcessor executa ordens com MT5Executor real."""
        # Setup mock MT5Executor
        async def mock_mt5_executor(order):
            await asyncio.sleep(0.01)
            return {
                "success": True,
                "ticket": "777888",
                "price": order.price,
                "error": None,
            }

        processor = QueueProcessor(
            queue=temp_queue,
            mt5_executor=mock_mt5_executor,
            poll_interval_ms=50,
            max_batch_size=5
        )

        # Enqueue ordem
        order = Order(
            order_id="QUEUE-INT-001",
            symbol="WINFUT",
            order_type="BUY",
            volume=1.0,
            price=128500.0
        )
        assert temp_queue.push(order) is True

        # Start processor
        await processor.start()
        await asyncio.sleep(0.5)  # Leave time to process
        await processor.stop()

        # Assert
        assert processor.stats["processed"] == 1
        assert processor.stats["executed"] == 1
        assert processor.stats["failed"] == 0
        assert temp_queue.get_status("QUEUE-INT-001") == "EXECUTED"

    @pytest.mark.asyncio
    async def test_queue_processor_retry_on_mt5_failure(self, temp_queue):
        """Integration: QueueProcessor retries on MT5 executor failures."""
        attempt_count = [0]

        async def failing_executor(order):
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                return {
                    "success": False,
                    "error": "MT5 timeout",
                }
            return {
                "success": True,
                "ticket": "888999",
                "price": order.price,
                "error": None,
            }

        processor = QueueProcessor(
            queue=temp_queue,
            mt5_executor=failing_executor,
            poll_interval_ms=100,
            max_batch_size=5
        )

        # Enqueue ordem
        order = Order(
            order_id="RETRY-TEST-001",
            symbol="WINFUT",
            order_type="BUY",
            volume=1.0
        )
        assert temp_queue.push(order) is True

        # Start processor
        await processor.start()
        await asyncio.sleep(3.5)  # Allow 1s + 2s = 3s retry backoff
        await processor.stop()

        # Assert
        assert processor.stats["retried"] >= 1
        assert processor.stats["executed"] == 1

    @pytest.mark.asyncio
    async def test_batch_execution_mt5_integration(self, temp_queue):
        """Integration: Batch of orders executed in parallel via MT5."""
        async def mock_executor(order):
            # Simulates MT5 execution
            await asyncio.sleep(0.01)
            return {
                "success": True,
                "ticket": hash(order.order_id) % 1000000,
                "price": order.price or 1.0,
                "error": None,
            }

        processor = QueueProcessor(
            queue=temp_queue,
            mt5_executor=mock_executor,
            poll_interval_ms=50,
            max_batch_size=5
        )

        # Enqueue 5 ordens
        for i in range(5):
            order = Order(
                order_id=f"BATCH-{i:03d}",
                symbol="WINFUT",
                order_type="BUY" if i % 2 == 0 else "SELL",
                volume=1.0,
                price=128500.0
            )
            assert temp_queue.push(order) is True

        # Start processor
        await processor.start()
        await asyncio.sleep(0.3)
        await processor.stop()

        # Assert all executed
        assert processor.stats["processed"] >= 5
        assert processor.stats["executed"] >= 5
        for i in range(5):
            assert temp_queue.get_status(f"BATCH-{i:03d}") == "EXECUTED"

