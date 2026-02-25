#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite E2E para validar persistência de trades (TASK-CRÍTICA-0 Phase 3)

Cenários testados:
1. Happy path: Ordem enfileirada → MT5 enviada → BD persistida
2. Retry logic: Desconexão durante save() → 3x retry → sucesso
3. Failure handling: Todas as retentativas falham → dead-letter queue
4. Reconciliation: 24/02 trades agora aparecem em BD
"""

import pytest
import asyncio
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4

# Domain imports
from src.domain.entities import Trade, Order
from src.domain.value_objects import Symbol, Quantity, Price, Money
from src.domain.enums.trading_enums import OrderSide, OrderType, TradeStatus

# Application imports
from src.application.orders_executor import (
    ExecutionOrder,
    OrderState,
    SendToMT5Command,
)

# Infrastructure imports
from src.infrastructure.repositories.trade_repository import ITradeRepository


@pytest.fixture
def mock_mt5_adapter():
    """Mock do MT5Adapter que simula execução bem-sucedida"""
    adapter = Mock()
    adapter.send_order = Mock(return_value="2276014161")  # Simulate ticket
    adapter.is_connected = Mock(return_value=True)
    return adapter


@pytest.fixture
def mock_trade_repository():
    """Mock do TradeRepository para capturar calls de save()"""
    repo = Mock(spec=ITradeRepository)
    repo.save = Mock()  # Simula save bem-sucedido por padrão
    return repo


@pytest.fixture
def sample_execution_order():
    """ExecutionOrder de exemplo"""
    return ExecutionOrder(
        order_id="ORD-TEST001",
        symbol="WINJ26",
        order_type="BUY",
        volume=1,  # Inteiro para Quantity
        entry_price=193245.00,
        stop_loss=193450.00,
        take_profit=192890.00,
        detector_spike=2.5,
        ml_classifier_score=0.85,
        trader_approval=True,
    )


class TestSendToMT5CommandHappyPath:
    """Teste do caminho feliz: MT5 send → BD persist"""

    @pytest.mark.asyncio
    async def test_execute_sends_to_mt5_and_persists(
        self, mock_mt5_adapter, mock_trade_repository, sample_execution_order
    ):
        """
        Cenário: Ordem enfileirada é enviada a MT5 e persistida em BD
        Esperado:
          - send_order() é chamado uma vez
          - save() é chamado uma vez
          - ExecutionOrder.mt5_ticket é atualizado
          - Estado final: EXECUTED
        """
        # Setup
        command = SendToMT5Command(mock_mt5_adapter, mock_trade_repository)
        order = sample_execution_order

        # Execute
        result = await command.execute(order)

        # Assert
        assert result is True, "Execução deveria retornar True"
        assert order.mt5_ticket == "2276014161", "Ticket deveria ser atualizado"
        assert order.state == OrderState.EXECUTED, "Estado deveria ser EXECUTED"

        # Verify chamadas
        mock_mt5_adapter.send_order.assert_called_once()
        mock_trade_repository.save.assert_called_once()  # Persistência chamada

    @pytest.mark.asyncio
    async def test_audit_log_contains_all_checkpoints(
        self, mock_mt5_adapter, mock_trade_repository, sample_execution_order
    ):
        """
        Cenário: Audit log contém todos os passos da execução
        Esperado:
          - SENT_TO_MT5
          - ACCEPTED_BY_MT5
          - EXECUTED
        """
        # Setup
        command = SendToMT5Command(mock_mt5_adapter, mock_trade_repository)
        order = sample_execution_order

        # Execute
        await command.execute(order)

        # Assert audit log
        states = [log.state for log in order.audit_log]
        assert OrderState.SENT_TO_MT5 in states
        assert OrderState.ACCEPTED_BY_MT5 in states
        assert OrderState.EXECUTED in states

        # Audit log deveria ter pelo menos 3 entradas
        assert len(order.audit_log) >= 3


class TestSendToMT5CommandRetryLogic:
    """Teste do retry logic com exponential backoff"""

    @pytest.mark.asyncio
    async def test_retry_on_persistence_failure(
        self, mock_mt5_adapter, sample_execution_order
    ):
        """
        Cenário: save() falha no primeiro retry, sucede no segundo
        Esperado:
          - _persist_with_retry() é chamado com max_retries=3
          - Deveria aguardar 0.5s, 1s antes de suceder
          - Resultado final: True (sucesso)
        """
        # Setup
        repo = Mock(spec=ITradeRepository)
        # Falha 1x, sucede 2ª vez
        repo.save = Mock(side_effect=[Exception("Connection lost"), None])

        command = SendToMT5Command(mock_mt5_adapter, repo, max_retries=3)
        order = sample_execution_order

        # Execute
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await command.execute(order)

        # Assert
        assert result is True, "Deveria suceder após retry"
        assert repo.save.call_count == 2, "save() deveria ser chamado 2x"
        assert order.state == OrderState.EXECUTED

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_returns_false(
        self, mock_mt5_adapter, sample_execution_order
    ):
        """
        Cenário: Todas as 3 tentativas de save() falham
        Esperado:
          - Resultado: False
          - Estado: REJECTED
          - save() chamado 3x
        """
        # Setup
        repo = Mock(spec=ITradeRepository)
        repo.save = Mock(side_effect=Exception("Permanent connection failure"))

        command = SendToMT5Command(mock_mt5_adapter, repo, max_retries=3)
        order = sample_execution_order

        # Execute
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await command.execute(order)

        # Assert
        assert result is False, "Deveria retornar False após todas falharem"
        assert order.state == OrderState.REJECTED
        assert repo.save.call_count == 3, "save() deveria ser tentado 3x"


class TestExecutionOrderToTrade:
    """Teste da conversão ExecutionOrder → Trade entity"""

    def test_to_trade_creates_valid_trade_entity(self, sample_execution_order):
        """
        Cenário: ExecutionOrder.to_trade() cria Trade entity válida
        Esperado:
          - Trade entity com todos os campos mapeados
          - broker_trade_id = ticket
          - status = OPEN
        """
        # Setup
        order = sample_execution_order
        ticket = "2276014161"

        # Execute
        trade = order.to_trade(ticket)

        # Assert
        assert isinstance(trade, Trade)
        assert trade.symbol.code == "WINJ26"
        assert trade.side == OrderSide.BUY
        assert trade.quantity.value == 1  # Inteiro
        assert trade.broker_trade_id == ticket
        assert trade.status == TradeStatus.OPEN

        # Notes devem conter metadata do detector
        assert "2.50σ" in trade.notes or "2.5" in trade.notes  # Detector spike
        assert "85" in trade.notes  # ML score (85.00%)

    def test_to_trade_sell_order(self):
        """
        Cenário: Ordem SELL é convertida com side correto
        """
        # Setup
        order = ExecutionOrder(
            order_id="ORD-SELL",
            symbol="WINJ26",
            order_type="SELL",  # SELL
            volume=1,  # Inteiro
            entry_price=193400.00,
            stop_loss=193200.00,
            take_profit=193600.00,
            detector_spike=1.8,
            ml_classifier_score=0.92,
        )

        # Execute
        trade = order.to_trade("2276014162")

        # Assert
        assert trade.side == OrderSide.SELL


class TestIntegrationE2E:
    """Testes de integração E2E"""

    @pytest.mark.asyncio
    async def test_full_execution_pipeline(
        self, mock_mt5_adapter, mock_trade_repository, sample_execution_order
    ):
        """
        Cenário: Pipeline completa de execução

        Fluxo:
        1. ExecutionOrder enfileirada
        2. SendToMT5Command.execute()
        3. MT5Adapter.send_order() chamado
        4. Trade persistido em BD
        5. Audit log completo

        Esperado: Sucesso em todas as etapas
        """
        # Setup
        command = SendToMT5Command(mock_mt5_adapter, mock_trade_repository)
        order = sample_execution_order

        # Execute
        result = await command.execute(order)

        # Assert
        assert result is True
        assert order.state == OrderState.EXECUTED

        # Capturar o Trade que foi persistido
        saved_trade = mock_trade_repository.save.call_args[0][0]
        assert saved_trade.broker_trade_id == "2276014161"
        assert saved_trade.symbol.code == "WINJ26"

    @pytest.mark.asyncio
    async def test_mt5_connection_error_handling(
        self, mock_trade_repository, sample_execution_order
    ):
        """
        Cenário: MT5 não está conectado
        Esperado: OrderExecutionError, ordem rejeitada
        """
        # Setup
        adapter = Mock()
        adapter.send_order = Mock(side_effect=Exception("Not connected to MT5"))

        command = SendToMT5Command(adapter, mock_trade_repository)
        order = sample_execution_order

        # Execute
        result = await command.execute(order)

        # Assert
        assert result is False
        assert order.state == OrderState.REJECTED


class TestReconciliation:
    """Testes de reconciliação para 24/02 trades"""

    @pytest.mark.asyncio
    async def test_24feb_trades_now_persist(self):
        """
        Cenário: 4 trades de 24/02 são simulados e persistem em BD
        Esperado:
          - 4 trades são salvos
          - Cada um com ticket correto
          - Status: OPEN (pois não foram fechados)
        """
        # Setup: Simular os 4 trades reais de 24/02
        trades_24feb = [
            ("2276014161", "WINJ26", "SELL", 193245.00),
            ("2276015509", "WINJ26", "BUY", 193435.00),
            ("2276015907", "WINJ26", "BUY", 193490.00),
            ("2276016015", "WINJ26", "SELL", 193475.00),
        ]

        # Mock persistent storage
        persisted_trades = []

        def capture_trade(trade):
            persisted_trades.append(trade)

        repo = Mock(spec=ITradeRepository)
        repo.save = Mock(side_effect=capture_trade)

        adapter = Mock()

        # Execute: Simular cada trade
        for ticket, symbol, side, price in trades_24feb:
            order = ExecutionOrder(
                order_id=f"ORD-24FEB-{ticket}",
                symbol=symbol,
                order_type=side,
                volume=1,  # Inteiro
                entry_price=price,
                stop_loss=price + 200,
                take_profit=price - 400,
                detector_spike=2.0,
                ml_classifier_score=0.80,
            )

            adapter.send_order = Mock(return_value=ticket)
            command = SendToMT5Command(adapter, repo)

            await command.execute(order)

        # Assert
        assert len(persisted_trades) == 4, "Deveria persistir 4 trades"

        # Verificar cada trade
        for i, (ticket, symbol, side, price) in enumerate(trades_24feb):
            trade = persisted_trades[i]
            assert trade.broker_trade_id == ticket
            assert trade.symbol.code == symbol
            assert trade.status == TradeStatus.OPEN


if __name__ == "__main__":
    # pytest tests/test_send_to_mt5_command_e2e.py -v --tb=short
    pytest.main([__file__, "-v", "--tb=short"])
