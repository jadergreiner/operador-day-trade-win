"""
P1-CORE: Position Broadcaster - Broadcast de Posições via WebSocket

Responsabilidades:
- Integração entre PositionMonitor e ConnectionManager (WebSocket)
- Broadcast de UpdatePositionMonitor para todos os clientes conectados
- Notificação de risk events (drawdown violation)
- Auditoria de broadcasts

Etapa 3: WebSocket Integration
"""

import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class PositionMessage:
    """Modelo para mensagem de posição via WebSocket."""

    @staticmethod
    def position_update(portfolio_status) -> Dict[str, Any]:
        """Cria mensagem de atualização de posições."""
        return {
            "type": "POSITION_UPDATE",
            "timestamp": datetime.utcnow().isoformat(),
            "data": portfolio_status.to_dict(),
        }

    @staticmethod
    def risk_violation(portfolio_status) -> Dict[str, Any]:
        """Cria mensagem de risk violation."""
        return {
            "type": "RISK_VIOLATION",
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "CRITICAL",
            "drawdown_percent": round(portfolio_status.drawdown_percent, 2),
            "action": "OPERATOR_ALERT",
            "data": portfolio_status.to_dict(),
        }

    @staticmethod
    def monitor_status(stats: Dict[str, int]) -> Dict[str, Any]:
        """Cria mensagem de status do monitor."""
        return {
            "type": "MONITOR_STATUS",
            "timestamp": datetime.utcnow().isoformat(),
            "stats": stats,
        }


class PositionBroadcaster:
    """
    Broadcaster de posições via WebSocket.

    Integra PositionMonitor com ConnectionManager para fazer
    broadcast em tempo real do status de posições.

    Fluxo:
    1. PositionMonitor consulta MT5 a cada 500ms
    2. Envia callback com PortfolioStatus ao Broadcaster
    3. Broadcaster envia mensagem JSON via WebSocket
    4. Todos os clientes conectados recebem atualização
    """

    def __init__(
        self,
        position_monitor,
        connection_manager,
        broadcast_interval_ms: float = 500,
    ):
        """
        Args:
            position_monitor: PositionMonitor instance
            connection_manager: ConnectionManager do WebSocket
            broadcast_interval_ms: Intervalo entre broadcasts (default: 500ms)
        """
        self.position_monitor = position_monitor
        self.connection_manager = connection_manager
        self.broadcast_interval_ms = broadcast_interval_ms / 1000
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.stats = {
            "broadcasts_sent": 0,
            "risk_violations_broadcast": 0,
            "monitor_status_broadcasts": 0,
            "broadcast_errors": 0,
        }

    async def start(self) -> None:
        """Inicia broadcaster em background."""
        if self.running:
            logger.warning("PositionBroadcaster already running")
            return

        self.running = True

        # Configurar callback do monitor para chamar este broadcaster
        self.position_monitor.rl_callback = self.on_position_update

        # Iniciar monitor
        if not self.position_monitor.running:
            await self.position_monitor.start()

        # Iniciar broadcast loop
        self.task = asyncio.create_task(self._broadcast_loop())
        logger.info("PositionBroadcaster started")

    async def stop(self) -> None:
        """Para broadcaster gracefully."""
        self.running = False
        if self.task:
            await self.task

        # Parar monitor
        await self.position_monitor.stop()

        logger.info("PositionBroadcaster stopped")

    async def on_position_update(self, portfolio_status) -> None:
        """
        Callback chamado quando monitor consulta posições.

        Args:
            portfolio_status: PortfolioStatus com atualização
        """
        try:
            # Broadcast principal: atualização de posições
            message = PositionMessage.position_update(portfolio_status)
            await self.connection_manager.broadcast(message)
            self.stats["broadcasts_sent"] += 1

            # Se risk violation, enviar alerta específico
            if portfolio_status.drawdown_percent <= -15:
                risk_message = PositionMessage.risk_violation(portfolio_status)
                await self.connection_manager.broadcast(risk_message)
                self.stats["risk_violations_broadcast"] += 1
                logger.error(
                    f"RISK VIOLATION BROADCAST: drawdown "
                    f"{portfolio_status.drawdown_percent:.2f}%"
                )

        except Exception as e:
            logger.error(f"Error in position update callback: {e}")
            self.stats["broadcast_errors"] += 1

    async def _broadcast_loop(self) -> None:
        """
        Loop de broadcast de status do monitor.

        Envia periodicamente o status do monitor (queries, callbacks, etc)
        para que o operador possa monitorar a saúde do sistema.
        """
        while self.running:
            try:
                # Broadcast de status do monitor (para observabilidade)
                monitor_stats = self.position_monitor.get_stats()
                status_message = PositionMessage.monitor_status(monitor_stats)

                await self.connection_manager.broadcast(status_message)
                self.stats["monitor_status_broadcasts"] += 1

                await asyncio.sleep(self.broadcast_interval_ms)

            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
                self.stats["broadcast_errors"] += 1
                await asyncio.sleep(self.broadcast_interval_ms)

    async def broadcast_position_snapshot(self) -> None:
        """
        Broadcast imediato do snapshot atual de posições.

        Útil para refresh após conectar ao WebSocket.
        """
        try:
            portfolio_status = self.position_monitor.get_last_status()

            if portfolio_status:
                message = PositionMessage.position_update(portfolio_status)
                await self.connection_manager.broadcast(message)
                self.stats["broadcasts_sent"] += 1
                logger.info("Position snapshot broadcasted")

        except Exception as e:
            logger.error(f"Error broadcasting snapshot: {e}")
            self.stats["broadcast_errors"] += 1

    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas de broadcast."""
        return self.stats.copy()

    def get_monitor_link(self) -> Dict[str, Any]:
        """Retorna informações de conexão monitor-broadcaster."""
        return {
            "broadcaster_active": self.running,
            "monitor_active": self.position_monitor.running,
            "monitor_stats": self.position_monitor.get_stats(),
            "broadcaster_stats": self.stats,
            "last_portfolio_status": (
                self.position_monitor.get_last_status().to_dict()
                if self.position_monitor.get_last_status()
                else None
            ),
        }
