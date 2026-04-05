"""
Unit + E2E Tests para TODO-2,3,4: OrdersExecutor (Issue #7 - ENG-201)

Testar os 3 métodos críticos:
- execute_order() (TODO-2, AC-1 a AC-4)
- monitor_positions() (TODO-3, AC-5 a AC-8)
- handle_stop_loss() (TODO-4, AC-9 a AC-11)
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from src.application.orders_executor import (
    OrdersExecutor,
    Order,
    OrderState,
    Position,
    OrderStatus,
)


class TestOrdersExecutor:
    """Test suite para OrdersExecutor - Issue #7"""

    @pytest.fixture
    def mock_risk_validator(self):
        """Mock RiskValidationProcessor com validate_order padrão aprovado."""
        from src.application.risk_validator import GateResult, GateStatus

        validator = MagicMock()
        gate_ok = GateResult(
            gate_name="capital_adequacy",
            status=GateStatus.PASS,
            message="Capital adequado",
        )
        validator.validate_order = MagicMock(return_value=(True, [gate_ok]))
        return validator

    @pytest.fixture
    def mock_mt5_adapter(self):
        """Mock MT5Adapter com todos os métodos usados na implementação."""
        adapter = MagicMock()
        adapter.is_connected = True
        adapter.send_order = AsyncMock(
            return_value={"status": "EXECUTED", "order_id": "MT5-001"}
        )
        adapter.get_open_positions = AsyncMock(return_value=[])
        adapter.get_positions = AsyncMock(return_value=[])
        adapter.get_price = AsyncMock(return_value=100.5)
        adapter.get_current_price = AsyncMock(return_value=100.5)
        adapter.close_position_by_id = AsyncMock(return_value={"success": True})
        return adapter

    @pytest.fixture
    def mock_trade_repository(self):
        """Mock ITradeRepository instance."""
        repo = MagicMock()
        repo.save = AsyncMock(return_value=True)
        repo.find_by_id = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def executor(self, mock_risk_validator, mock_mt5_adapter, mock_trade_repository):
        """Create OrdersExecutor instance with mocks."""
        return OrdersExecutor(mock_risk_validator, mock_mt5_adapter, mock_trade_repository)

    def _criar_ordem(self, order_id: str = "ORD-TEST-001", symbol: str = "WIN$N") -> Order:
        """Cria uma ordem válida para uso nos testes."""
        return Order(
            order_id=order_id,
            symbol=symbol,
            order_type="BUY",
            volume=1.0,
            entry_price=100000.0,
            stop_loss=99500.0,
            take_profit=101000.0,
            detector_spike=2.5,
            ml_classifier_score=0.75,
        )

    def _criar_mock_posicao(
        self,
        position_id: str = "POS-001",
        symbol: str = "WIN$N",
        entry_price: float = 100000.0,
        stop_loss: float = 99000.0,
    ) -> MagicMock:
        """Cria um mock de posição aberta para uso nos testes."""
        mock_posicao = MagicMock()
        mock_posicao.symbol = symbol
        mock_posicao.volume = 1.0
        mock_posicao.entry_price = entry_price
        mock_posicao.type = "BUY"
        mock_posicao.order_id = position_id
        mock_posicao.stop_loss = stop_loss
        mock_posicao.price_current = None
        mock_posicao.profit_loss = None
        mock_posicao.profit = None
        mock_posicao.size = None
        mock_posicao.price_open = None
        mock_posicao.order_type = None
        mock_posicao.position_id = None
        mock_posicao.ticket = None
        mock_posicao.sl = None
        return mock_posicao

    # ==================== TEST TODO-2: EXECUTE_ORDER ====================

    @pytest.mark.asyncio
    async def test_execute_order_success(self, executor, mock_risk_validator):
        """
        AC-1, AC-2: Executa ordem com sucesso.

        Dado: ordem válida passa na validação
        Quando: execute_order(order) é chamado
        Então: retorna success=True com mt5_ticket
        """
        order = self._criar_ordem("ORD-SUCCESS-001")

        result = await executor.execute_order(order)

        assert result["success"] is True
        assert result["order_id"] == "ORD-SUCCESS-001"
        assert result["mt5_ticket"] == "MT5-001"
        assert "gates_passed" in result
        assert "execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_execute_order_validation_reject(
        self, executor, mock_risk_validator, mock_mt5_adapter
    ):
        """
        AC-1: Ordem rejeitada na validação de risco.

        Dado: ordem falha na validação do Risk Framework
        Quando: execute_order(order) é chamado
        Então: retorna success=False sem enviar ao MT5
        """
        from src.application.risk_validator import GateResult, GateStatus

        gate_fail = GateResult(
            gate_name="capital_adequacy",
            status=GateStatus.FAIL,
            message="Capital insuficiente para a operação",
        )
        mock_risk_validator.validate_order = MagicMock(return_value=(False, [gate_fail]))

        order = self._criar_ordem("ORD-REJECT-001")

        result = await executor.execute_order(order)

        assert result["success"] is False
        assert "rejection_reason" in result
        assert result["rejection_reason"] == "Capital insuficiente para a operação"
        mock_mt5_adapter.send_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_order_retry_logic(
        self, executor, mock_risk_validator, mock_mt5_adapter
    ):
        """
        AC-3: Retry com backoff exponencial.

        Dado: MT5 falha na 1ª tentativa com retcode 10006, sucede na 2ª
        Quando: execute_order(order) é chamado
        Então: realiza retry e retorna success=True
        """
        # Símbolo não-WIN para evitar verificação de rollover de contrato
        order = self._criar_ordem("ORD-RETRY-001", symbol="PETR4")

        # 1ª chamada lança exceção com 10006, 2ª retorna sucesso
        mock_mt5_adapter.send_order.side_effect = [
            Exception("10006: order execution failed"),
            {"status": "EXECUTED", "order_id": "MT5-RETRY-001"},
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await executor.execute_order(order)

        assert result["success"] is True
        assert mock_mt5_adapter.send_order.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_order_logging(self, executor):
        """
        AC-4: Logging e trilha de auditoria.

        Dado: ordem executada com sucesso
        Quando: execute_order(order) é chamado
        Então: audit_log da ordem contém entradas com timestamp e estado
        """
        order = self._criar_ordem("ORD-LOG-001")

        await executor.execute_order(order)

        assert len(order.audit_log) >= 1
        for entrada in order.audit_log:
            assert hasattr(entrada, "timestamp")
            assert isinstance(entrada.timestamp, datetime)
            assert hasattr(entrada, "state")
            assert hasattr(entrada, "message")

    # ==================== TEST TODO-3: MONITOR_POSITIONS ====================

    @pytest.mark.asyncio
    async def test_monitor_positions_polling(self, executor, mock_mt5_adapter):
        """
        AC-5: Faz polling de posições no MT5.

        Dado: monitor_positions() é chamado
        Quando: executa uma iteração
        Então: busca posições via mt5_adapter.get_positions()
        """
        mock_mt5_adapter.get_positions = AsyncMock(return_value=[])

        result = await executor.monitor_positions()

        assert result is not None
        assert result["total_positions"] == 0
        assert "positions" in result
        mock_mt5_adapter.get_positions.assert_called_once()

    @pytest.mark.asyncio
    async def test_monitor_positions_sl_detection(self, executor, mock_mt5_adapter):
        """
        AC-6: Detecta acionamento de stop-loss.

        Dado: posição com preço abaixo do SL
        Quando: monitor_positions() é chamado
        Então: chama handle_stop_loss() e registra o evento
        """
        mock_posicao = self._criar_mock_posicao(
            position_id="POS-SL-001",
            stop_loss=99000.0,
        )

        mock_mt5_adapter.get_positions = AsyncMock(return_value=[mock_posicao])
        # Preço atual abaixo do SL → aciona stop-loss
        mock_mt5_adapter.get_current_price = AsyncMock(return_value=98000.0)
        mock_mt5_adapter.close_position_by_id = AsyncMock(
            return_value={"success": True}
        )

        result = await executor.monitor_positions()

        assert result is not None
        assert len(result["stop_loss_events"]) == 1
        assert result["stop_loss_events"][0]["position_id"] == "POS-SL-001"
        assert result["stop_loss_events"][0]["close_success"] is True
        mock_mt5_adapter.close_position_by_id.assert_called_once_with("POS-SL-001")

    @pytest.mark.asyncio
    async def test_monitor_positions_history(self, executor, mock_mt5_adapter):
        """
        AC-7: Mantém snapshot do último monitoramento.

        Dado: monitor_positions() executado
        Quando: polling é concluído
        Então: last_monitoring_snapshot é atualizado no executor
        """
        mock_mt5_adapter.get_positions = AsyncMock(return_value=[])

        assert executor.last_monitoring_snapshot is None

        await executor.monitor_positions()

        assert executor.last_monitoring_snapshot is not None
        assert "total_positions" in executor.last_monitoring_snapshot
        assert "positions" in executor.last_monitoring_snapshot
        assert "monitoring_time_ms" in executor.last_monitoring_snapshot

    @pytest.mark.asyncio
    async def test_monitor_positions_performance(self, executor, mock_mt5_adapter):
        """
        AC-8: Performance < 500ms por ciclo.

        Dado: monitor_positions() executado
        Quando: ciclo de polling completa
        Então: tempo de execução é inferior a 500ms
        """
        mock_mt5_adapter.get_positions = AsyncMock(return_value=[])

        result = await executor.monitor_positions()

        assert result is not None
        assert "monitoring_time_ms" in result
        assert result["monitoring_time_ms"] < 500

    # ==================== TEST TODO-4: HANDLE_STOP_LOSS ====================

    @pytest.mark.asyncio
    async def test_handle_stop_loss_close_order(self, executor, mock_mt5_adapter):
        """
        AC-9: Fecha posição a preço de mercado.

        Dado: stop-loss acionado para uma posição
        Quando: handle_stop_loss() é chamado
        Então: chama close_position_by_id no mt5_adapter
        """
        mock_mt5_adapter.close_position_by_id = AsyncMock(
            return_value={"success": True}
        )

        result = await executor.handle_stop_loss("POS-CLOSE-001")

        assert result["success"] is True
        mock_mt5_adapter.close_position_by_id.assert_called_once_with("POS-CLOSE-001")

    @pytest.mark.asyncio
    async def test_handle_stop_loss_audit_log(self, executor, mock_mt5_adapter):
        """
        AC-10: Registra evento no log de auditoria.

        Dado: posição fechada por stop-loss
        Quando: handle_stop_loss() completa
        Então: evento é registrado em stop_loss_events com dados do fechamento
        """
        mock_mt5_adapter.close_position_by_id = AsyncMock(
            return_value={"success": True}
        )

        result = await executor.handle_stop_loss("POS-AUDIT-001")

        assert result["success"] is True
        assert "event" in result
        assert result["event"]["order_id"] == "POS-AUDIT-001"
        assert "closed_at" in result["event"]
        assert len(executor.stop_loss_events) == 1
        assert executor.stop_loss_events[0]["order_id"] == "POS-AUDIT-001"

    @pytest.mark.asyncio
    async def test_handle_stop_loss_atomic_update(self, executor, mock_mt5_adapter):
        """
        AC-11: Atualiza estado da ordem atomicamente para CLOSED.

        Dado: ordem registrada no executor com ticket correspondente
        Quando: handle_stop_loss() é executado
        Então: estado da ordem é atualizado para CLOSED
        """
        mock_mt5_adapter.close_position_by_id = AsyncMock(
            return_value={"success": True}
        )

        ordem = self._criar_ordem("ORD-ATOMIC-001")
        ordem.mt5_ticket = "ORD-ATOMIC-001"
        executor.orders["ORD-ATOMIC-001"] = ordem

        result = await executor.handle_stop_loss("ORD-ATOMIC-001")

        assert result["success"] is True
        assert ordem.state == OrderState.CLOSED

    # ==================== E2E TESTS ====================

    @pytest.mark.asyncio
    async def test_e2e_order_execution_flow(self, executor, mock_mt5_adapter):
        """
        E2E: Fluxo completo de execução de ordem.

        Dado: nova ordem submetida
        Quando: execute_order() é chamado
        Então: ordem executada, ticket atribuído e log de auditoria atualizado
        """
        mock_mt5_adapter.get_positions = AsyncMock(return_value=[])

        order = self._criar_ordem("ORD-E2E-001")

        exec_result = await executor.execute_order(order)
        assert exec_result["success"] is True
        assert exec_result["mt5_ticket"] == "MT5-001"
        assert len(order.audit_log) >= 1

        monitor_result = await executor.monitor_positions()
        assert monitor_result is not None
        assert monitor_result["total_positions"] == 0

    @pytest.mark.asyncio
    async def test_e2e_monitor_and_stop_loss(self, executor, mock_mt5_adapter):
        """
        E2E: Monitoramento + stop-loss automático.

        Dado: posição aberta com SL definido
        Quando: monitor_positions() detecta preço no SL
        Então: posição é fechada automaticamente
        """
        mock_posicao = self._criar_mock_posicao(
            position_id="POS-E2E-001",
            stop_loss=99000.0,
        )

        mock_mt5_adapter.get_positions = AsyncMock(return_value=[mock_posicao])
        # Preço abaixo do SL — aciona fechamento
        mock_mt5_adapter.get_current_price = AsyncMock(return_value=98500.0)
        mock_mt5_adapter.close_position_by_id = AsyncMock(
            return_value={"success": True}
        )

        result = await executor.monitor_positions()

        assert result is not None
        assert len(result["stop_loss_events"]) == 1
        assert result["stop_loss_events"][0]["close_success"] is True
        mock_mt5_adapter.close_position_by_id.assert_called_once_with("POS-E2E-001")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
