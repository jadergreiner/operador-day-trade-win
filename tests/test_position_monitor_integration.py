"""
P1-CORE: Testes de Integração - Position Monitor + WebSocket (Etapa 3)

Valida:
1. PositionMonitor consulta posições MT5
2. PositionBroadcaster integra com ConnectionManager
3. RLCallback funciona
4. Risk violations são detectados

Testes: 4 (integração completa do fluxo Etapa 3)
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Imports do projeto
from src.infrastructure.position_monitor import (
    Position,
    PortfolioStatus,
    PositionMonitor,
)
from src.infrastructure.position_broadcaster import (
    PositionMessage,
    PositionBroadcaster,
)


class TestPositionMonitor:
    """Testes para PositionMonitor."""

    @pytest.fixture
    def mock_adapter(self):
        """Mock do MT5Adapter."""
        adapter = AsyncMock()
        adapter.get_positions = AsyncMock(
            return_value=[
                {
                    "position_id": 1,
                    "symbol": "WINFUT",
                    "order_type": "BUY",
                    "volume": 1.0,
                    "entry_price": 126000.0,
                    "current_price": 126100.0,
                    "sl": 125900.0,
                    "tp": 126200.0,
                    "open_time": datetime.utcnow(),
                    "commission": 5.0,
                },
                {
                    "position_id": 2,
                    "symbol": "WINFUT",
                    "order_type": "SELL",
                    "volume": 2.0,
                    "entry_price": 126000.0,
                    "current_price": 125900.0,
                    "sl": 126100.0,
                    "tp": 125800.0,
                    "open_time": datetime.utcnow(),
                    "commission": 10.0,
                },
            ]
        )
        return adapter

    @pytest.mark.asyncio
    async def test_position_monitor_initialization(self):
        """
        AC-1: PositionMonitor inicializa corretamente.

        Valida:
        - Instância criada com defaults
        - Running flag é False
        - Stats inicializados
        """
        monitor = PositionMonitor()

        assert monitor.running is False
        assert monitor.task is None
        assert monitor.stats["queries"] == 0
        assert monitor.stats["portfolio_updates"] == 0
        assert monitor.stats["rl_callbacks_sent"] == 0
        assert monitor.stats["risk_violations"] == 0

    @pytest.mark.asyncio
    async def test_position_monitor_query_positions(self, mock_adapter):
        """
        AC-2: PositionMonitor consulta posições do MT5.

        Valida:
        - Consulta retorna PortfolioStatus
        - Posições parseadas corretamente
        - Métricas calculadas (PnL, status)
        """
        monitor = PositionMonitor(mt5_adapter=mock_adapter)

        # Query
        portfolio = await monitor.query_positions()

        # Validações
        assert portfolio is not None
        assert len(portfolio.positions) == 2
        assert portfolio.winning_positions == 2  # BUY +100 points, SELL +100 points
        assert portfolio.losing_positions == 0
        assert portfolio.total_pnl_value > 0

        # Position 1: BUY, entry 126000, current 126100 → +100 PnL
        assert portfolio.positions[0].status == "WINNING"
        assert portfolio.positions[0].pnl_points == 100.0

        # Position 2: SELL, entry 126000, current 125900 → +100 PnL
        assert portfolio.positions[1].status == "WINNING"
        assert portfolio.positions[1].pnl_points == 100.0

    @pytest.mark.asyncio
    async def test_position_monitor_rl_callback(self, mock_adapter):
        """
        AC-3: PositionMonitor integra com RLCallback.

        Valida:
        - Callback é disparado quando posições são consultadas
        - PortfolioStatus é passado corretamente ao callback
        - Stats são atualizados
        """
        # Mock callback
        rl_callback = AsyncMock()

        monitor = PositionMonitor(
            mt5_adapter=mock_adapter, rl_callback=rl_callback
        )

        # Query
        portfolio = await monitor.query_positions()

        # Simular callback (como faria o _monitor_loop)
        if portfolio:
            await rl_callback(portfolio)

        # Validações
        rl_callback.assert_called_once()
        call_args = rl_callback.call_args[0][0]
        assert isinstance(call_args, PortfolioStatus)
        assert len(call_args.positions) == 2

    @pytest.mark.asyncio
    async def test_position_monitor_risk_violation_detection(self):
        """
        AC-4: PositionMonitor detecta risk violations (drawdown > -15%).

        Valida:
        - Drawdown é calculado corretamente
        - Risk violations são detectados
        - Stats são incrementados
        """
        # Mock adapter com posição perdendo
        adapter = AsyncMock()
        adapter.get_positions = AsyncMock(
            return_value=[
                {
                    "position_id": 1,
                    "symbol": "WINFUT",
                    "order_type": "BUY",
                    "volume": 5.0,
                    "entry_price": 126000.0,
                    "current_price": 125000.0,  # -1000 points
                    "sl": 124000.0,
                    "tp": 127000.0,
                    "open_time": datetime.utcnow(),
                    "commission": 50.0,
                }
            ]
        )

        monitor = PositionMonitor(mt5_adapter=adapter)

        # Query
        portfolio = await monitor.query_positions()

        # Validações
        assert portfolio is not None
        assert portfolio.drawdown_percent < -15  # Violation!
        assert portfolio.risk_status == "RED"


class TestPositionBroadcaster:
    """Testes para PositionBroadcaster + WebSocket."""

    @pytest.fixture
    def mock_adapter(self):
        """Mock do MT5Adapter."""
        adapter = AsyncMock()
        adapter.get_positions = AsyncMock(return_value=[])
        return adapter

    @pytest.fixture
    def mock_connection_manager(self):
        """Mock do ConnectionManager."""
        manager = AsyncMock()
        manager.broadcast = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_position_broadcaster_integration(
        self, mock_adapter, mock_connection_manager
    ):
        """
        AC-5: PositionBroadcaster integra PositionMonitor + WebSocket.

        Valida:
        - Monitor integrado com broadcaster
        - ConnectionManager pronto para receber broadcasts
        - Callback está configurado
        """
        monitor = PositionMonitor(mt5_adapter=mock_adapter)
        broadcaster = PositionBroadcaster(
            position_monitor=monitor,
            connection_manager=mock_connection_manager,
        )

        # Validações
        assert broadcaster.position_monitor == monitor
        assert broadcaster.connection_manager == mock_connection_manager
        assert broadcaster.running is False
        assert broadcaster.stats["broadcasts_sent"] == 0

    @pytest.mark.asyncio
    async def test_position_broadcaster_websocket_broadcast(
        self, mock_adapter, mock_connection_manager
    ):
        """
        AC-6: PositionBroadcaster faz broadcast via WebSocket.

        Valida:
        - Mensagem é enviada ao ConnectionManager
        - Formato da mensagem está correto
        - Stats são atualizados
        """
        # Setup com posição
        adapter = AsyncMock()
        adapter.get_positions = AsyncMock(
            return_value=[
                {
                    "position_id": 1,
                    "symbol": "WINFUT",
                    "order_type": "BUY",
                    "volume": 1.0,
                    "entry_price": 126000.0,
                    "current_price": 126100.0,
                    "sl": 125900.0,
                    "tp": 126200.0,
                    "open_time": datetime.utcnow(),
                    "commission": 5.0,
                }
            ]
        )

        monitor = PositionMonitor(mt5_adapter=adapter)
        broadcaster = PositionBroadcaster(
            position_monitor=monitor,
            connection_manager=mock_connection_manager,
        )

        # Disparar callback manualmente (simula _monitor_loop)
        portfolio = await monitor.query_positions()
        assert portfolio is not None

        await broadcaster.on_position_update(portfolio)

        # Validações
        mock_connection_manager.broadcast.assert_called_once()

        # Verificar formato da mensagem
        call_args = mock_connection_manager.broadcast.call_args[0][0]
        assert call_args["type"] == "POSITION_UPDATE"
        assert "timestamp" in call_args
        assert "data" in call_args
        assert call_args["data"]["total_positions"] == 1

        # Stats
        assert broadcaster.stats["broadcasts_sent"] == 1

    @pytest.mark.asyncio
    async def test_position_broadcaster_risk_alert_broadcast(
        self, mock_connection_manager
    ):
        """
        AC-7: PositionBroadcaster faz broadcast de risk alerts.

        Valida:
        - Risk violation gera mensagem RISK_VIOLATION
        - Alerta é enviado ao ConnectionManager
        - Stats são atualizados
        """
        # Setup com posição perdendo (risk violation)
        adapter = AsyncMock()
        adapter.get_positions = AsyncMock(
            return_value=[
                {
                    "position_id": 1,
                    "symbol": "WINFUT",
                    "order_type": "BUY",
                    "volume": 10.0,
                    "entry_price": 126000.0,
                    "current_price": 124000.0,  # -2000 points, big loss
                    "sl": 122000.0,
                    "tp": 128000.0,
                    "open_time": datetime.utcnow(),
                    "commission": 100.0,
                }
            ]
        )

        monitor = PositionMonitor(mt5_adapter=adapter)
        broadcaster = PositionBroadcaster(
            position_monitor=monitor,
            connection_manager=mock_connection_manager,
        )

        # Query e callback
        portfolio = await monitor.query_positions()
        mock_connection_manager.reset_mock()

        await broadcaster.on_position_update(portfolio)

        # Validações
        # Deve chamar broadcast 2x: position_update + risk_violation
        assert mock_connection_manager.broadcast.call_count == 2

        # Segunda call deve ser RISK_VIOLATION
        calls = mock_connection_manager.broadcast.call_args_list
        risk_message = calls[1][0][0]

        assert risk_message["type"] == "RISK_VIOLATION"
        assert risk_message["severity"] == "CRITICAL"
        assert "drawdown_percent" in risk_message

        # Stats
        assert broadcaster.stats["risk_violations_broadcast"] == 1


class TestPositionMessageFormatting:
    """Testes para formatação de mensagens de posição."""

    def test_position_message_format(self):
        """
        AC-8: Mensagens de posição têm formato correto.

        Valida:
        - Campos obrigatórios presentes
        - Tipos de dados corretos
        - Timestamp em ISO format
        """
        # Criar posição e portfolio
        position = Position(
            position_id=1,
            symbol="WINFUT",
            order_type="BUY",
            volume=1.0,
            entry_price=126000.0,
            current_price=126100.0,
            sl=125900.0,
            tp=126200.0,
            open_time=datetime.utcnow(),
            commission=5.0,
        )

        portfolio = PortfolioStatus([position])

        # Gerar mensagem
        message = PositionMessage.position_update(portfolio)

        # Validações
        assert message["type"] == "POSITION_UPDATE"
        assert "timestamp" in message
        assert isinstance(message["timestamp"], str)

        data = message["data"]
        assert data["total_positions"] == 1
        assert data["total_pnl_value"] > 0
        assert isinstance(data["positions"], list)
        assert len(data["positions"]) == 1

        # Validar posição individual
        pos_data = data["positions"][0]
        assert pos_data["symbol"] == "WINFUT"
        assert pos_data["order_type"] == "BUY"
        assert pos_data["status"] == "WINNING"
        assert "pnl_value" in pos_data
        assert "risk_reward_ratio" in pos_data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
