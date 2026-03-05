"""
P1-CORE: Position Monitor - Monitora Posições Abertas em MT5

Responsabilidades:
- Consultar posições abertas no MT5 em tempo real
- Calcular PnL atual, drawdown, exposição
- Integrar com MT5 real (via adapter)
- Suportar callbacks para RL learning

Etapa 3: QueryPositionStatus + RL Integration
"""

import logging
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class Position:
    """Modelo de posição aberta."""

    def __init__(
        self,
        position_id: int,
        symbol: str,
        order_type: str,  # BUY ou SELL
        volume: float,
        entry_price: float,
        current_price: float,
        sl: float,
        tp: float,
        open_time: datetime,
        commission: float = 0.0,
    ):
        self.position_id = position_id
        self.symbol = symbol
        self.order_type = order_type
        self.volume = volume
        self.entry_price = entry_price
        self.current_price = current_price
        self.sl = sl
        self.tp = tp
        self.open_time = open_time
        self.commission = commission

    @property
    def pnl_points(self) -> float:
        """PnL em pontos (não em valor)."""
        if self.order_type == "BUY":
            return self.current_price - self.entry_price
        else:
            return self.entry_price - self.current_price

    @property
    def pnl_percent(self) -> float:
        """PnL em percentual."""
        if self.entry_price == 0:
            return 0.0
        return (self.pnl_points / self.entry_price) * 100

    @property
    def pnl_value(self) -> float:
        """PnL em valor (R$) - assume 1 ponto = 1 real por contrato."""
        return self.pnl_points * self.volume - self.commission

    @property
    def status(self) -> str:
        """Status: WINNING, LOSING, BREAKEVEN."""
        if self.pnl_points > 0.1:
            return "WINNING"
        elif self.pnl_points < -0.1:
            return "LOSING"
        else:
            return "BREAKEVEN"

    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dicionário."""
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "order_type": self.order_type,
            "volume": self.volume,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "sl": self.sl,
            "tp": self.tp,
            "pnl_points": round(self.pnl_points, 2),
            "pnl_percent": round(self.pnl_percent, 2),
            "pnl_value": round(self.pnl_value, 2),
            "status": self.status,
            "open_time": self.open_time.isoformat(),
            "risk_reward_ratio": self._calculate_rr(),
        }

    def _calculate_rr(self) -> float:
        """Calculate risk/reward ratio."""
        if self.order_type == "BUY":
            risk = self.entry_price - self.sl
            reward = self.tp - self.entry_price
        else:
            risk = self.sl - self.entry_price
            reward = self.entry_price - self.tp

        if risk == 0:
            return 0.0
        return reward / risk


class PortfolioStatus:
    """Status agregado de todas as posições abertas."""

    def __init__(self, positions: List[Position]):
        self.positions = positions
        self.timestamp = datetime.utcnow()

    @property
    def total_pnl_value(self) -> float:
        """PnL total em valor (R$)."""
        return sum(p.pnl_value for p in self.positions)

    @property
    def total_pnl_percent(self) -> float:
        """PnL médio em percentual."""
        if not self.positions:
            return 0.0
        return sum(p.pnl_percent for p in self.positions) / len(self.positions)

    @property
    def winning_positions(self) -> int:
        """Número de posições com lucro."""
        return sum(1 for p in self.positions if p.status == "WINNING")

    @property
    def losing_positions(self) -> int:
        """Número de posições com loss."""
        return sum(1 for p in self.positions if p.status == "LOSING")

    @property
    def total_volume(self) -> float:
        """Volume total aberto."""
        return sum(p.volume for p in self.positions)

    @property
    def drawdown_percent(self) -> float:
        """Drawdown máximo (assumindo capital inicial 100)."""
        if self.total_pnl_value >= 0:
            return 0.0
        return (self.total_pnl_value / 100) * 100  # Simplificado

    @property
    def risk_status(self) -> str:
        """Status de risco: GREEN, YELLOW, RED."""
        if self.drawdown_percent <= -15:
            return "RED"  # Critério P0: drawdown <= -15%
        elif self.drawdown_percent <= -10:
            return "YELLOW"
        else:
            return "GREEN"

    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dicionário."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_positions": len(self.positions),
            "winning_positions": self.winning_positions,
            "losing_positions": self.losing_positions,
            "total_volume": round(self.total_volume, 2),
            "total_pnl_value": round(self.total_pnl_value, 2),
            "total_pnl_percent": round(self.total_pnl_percent, 2),
            "drawdown_percent": round(self.drawdown_percent, 2),
            "risk_status": self.risk_status,
            "positions": [p.to_dict() for p in self.positions],
        }


class PositionMonitor:
    """
    Monitor de posições em tempo real.

    Responsabilidades:
    - Consultar posições abertas do MT5
    - Calcular PnL e métricas
    - Disparar callbacks para RL learning
    - Detectar risk violations (drawdown > -15%)

    Integração com MT5Executor:
    - Usa MT5Adapter.get_positions() para consultar
    - Compatible com QueueProcessor's async model
    """

    def __init__(
        self,
        mt5_adapter=None,
        rl_callback: Optional[Callable] = None,
        poll_interval_ms: float = 500,
    ):
        """
        Args:
            mt5_adapter: MT5Adapter para consultar MT5
            rl_callback: Função async para callback do RL (posição updated)
            poll_interval_ms: Intervalo de polling (default: 500ms)
        """
        self.mt5_adapter = mt5_adapter
        self.rl_callback = rl_callback
        self.poll_interval_ms = poll_interval_ms / 1000  # Converter para segundos
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.last_portfolio_status: Optional[PortfolioStatus] = None
        self.stats = {
            "queries": 0,
            "portfolio_updates": 0,
            "rl_callbacks_sent": 0,
            "risk_violations": 0,
        }

    async def start(self) -> None:
        """Inicia monitor em background."""
        if self.running:
            logger.warning("PositionMonitor already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._monitor_loop())
        logger.info("PositionMonitor started")

    async def stop(self) -> None:
        """Para monitor gracefully."""
        self.running = False
        if self.task:
            await self.task
        logger.info("PositionMonitor stopped")

    async def _monitor_loop(self) -> None:
        """Loop principal: poll → calc → callback."""
        while self.running:
            try:
                portfolio_status = await self.query_positions()
                self.stats["queries"] += 1

                if portfolio_status:
                    self.last_portfolio_status = portfolio_status

                    # Atualizar stats
                    self.stats["portfolio_updates"] += 1

                    # Enviar callback ao RL
                    if self.rl_callback:
                        await self.rl_callback(portfolio_status)
                        self.stats["rl_callbacks_sent"] += 1

                    # Verificar risk violations
                    if portfolio_status.drawdown_percent <= -15:
                        logger.error(
                            f"RISK VIOLATION: Drawdown {portfolio_status.drawdown_percent:.2f}% < -15%"
                        )
                        self.stats["risk_violations"] += 1

                await asyncio.sleep(self.poll_interval_ms)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(self.poll_interval_ms)

    async def query_positions(self) -> Optional[PortfolioStatus]:
        """
        Consulta posições abertas do MT5.

        Retorna:
            PortfolioStatus com todas as posições abertas
            None se não conseguir consultar
        """
        try:
            if not self.mt5_adapter:
                # Lazy init: tentar carregar adapter
                self._init_adapter()

            if not self.mt5_adapter:
                logger.warning("MT5Adapter not available")
                return None

            # Consultar posições via adapter
            positions_data = await self._get_mt5_positions()

            if not positions_data:
                logger.debug("No open positions")
                return PortfolioStatus([])

            # Converter para Position objects
            positions = [self._create_position(p) for p in positions_data]

            # Retornar status agregado
            return PortfolioStatus(positions)

        except Exception as e:
            logger.error(f"Error querying positions: {e}")
            return None

    async def _get_mt5_positions(self) -> List[Dict[str, Any]]:
        """
        Consulta posições do MT5 via adapter.

        Retorna lista de dicts com posição info.
        """
        if hasattr(self.mt5_adapter, "get_positions"):
            # Adapter moderno com async
            if asyncio.iscoroutinefunction(self.mt5_adapter.get_positions):
                return await self.mt5_adapter.get_positions()
            else:
                # Fallback síncrono
                return self.mt5_adapter.get_positions()
        else:
            # Fallback: mock data para testes
            logger.debug("MT5Adapter.get_positions() not available, using mock")
            return []

    def _create_position(self, data: Dict[str, Any]) -> Position:
        """Converte dict MT5 em Position object."""
        return Position(
            position_id=data.get("position_id", 0),
            symbol=data.get("symbol", "WINFUT"),
            order_type=data.get("order_type", "BUY"),
            volume=float(data.get("volume", 1.0)),
            entry_price=float(data.get("entry_price", 100.0)),
            current_price=float(data.get("current_price", 100.0)),
            sl=float(data.get("sl", 99.0)),
            tp=float(data.get("tp", 101.0)),
            open_time=data.get("open_time", datetime.utcnow()),
            commission=float(data.get("commission", 0.0)),
        )

    def _init_adapter(self) -> None:
        """Lazy initialization de MT5Adapter."""
        try:
            # Tentar carregar adapter do projeto
            from src.infrastructure.adapters.mt5_adapter import MT5Adapter

            self.mt5_adapter = MT5Adapter()
            logger.info("MT5Adapter initialized")
        except Exception as e:
            logger.warning(f"Could not initialize MT5Adapter: {e}")
            self.mt5_adapter = None

    def get_last_status(self) -> Optional[PortfolioStatus]:
        """Retorna último status consultado."""
        return self.last_portfolio_status

    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas de monitoramento."""
        return self.stats.copy()
