"""
MT5 REST API Adapter - Camada de Integração com MetaTrader 5

Padrão: Adapter Pattern
Responsabilidade: Traduzir chamadas internas em REST calls para MT5 via REST Gateway

Status: SPRINT 1 - Eng Sr
"""

from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import httpx
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Tipos de operação permitidos"""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Estado da ordem no MT5"""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"


@dataclass
class MTOrder:
    """Representação de ordem para MT5"""
    ticket: str
    symbol: str
    order_type: OrderType
    volume: float  # Lotes
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    comment: str = ""
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class MTPosition:
    """Representação de posição aberta no MT5"""
    ticket: str
    symbol: str
    volume: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    open_time: datetime
    profit_loss: float  # Em conta currency


class MT5Adapter:
    """
    Adapter para integração com MT5 via REST Gateway.

    Arquitetura:
    ┌────────────────────────────────┐
    │  Risk Validators (próxima)     │
    │                                 │
    │  Valida regras de negócio      │
    └────────────┬────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │     MT5Adapter (AQUI)          │
    │                                 │
    │  Traduz para REST calls        │
    └────────────┬────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │   REST Gateway (MT5 plugin)    │
    │   localhost:8000/api/v1/       │
    └────────────────────────────────┘
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: str = None,
        timeout: float = 10.0,
        max_retries: int = 3
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def health_check(self) -> bool:
        """
        Verifica se REST Gateway está disponível.

        Returns:
            bool: True se gateway está ok
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/health",
                headers=self._get_headers()
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"MT5 health check failed: {e}")
            return False

    async def get_account_info(self) -> Dict:
        """
        Obtém informações da conta (saldo, margem, etc).

        Returns:
            Dict com: {
                'balance': float,
                'equity': float,
                'margin': float,
                'margin_free': float,
                'margin_level': float
            }
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/account",
                headers=self._get_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {}

    async def get_positions(self, symbol: Optional[str] = None) -> List[MTPosition]:
        """
        Obtém posições abertas.

        Args:
            symbol: Símbolo específico ou None para todas

        Returns:
            Lista de MTPosition
        """
        try:
            params = {"symbol": symbol} if symbol else {}
            response = await self.client.get(
                f"{self.base_url}/api/v1/positions",
                params=params,
                headers=self._get_headers()
            )
            response.raise_for_status()

            positions_data = response.json()
            return [
                MTPosition(
                    ticket=p['ticket'],
                    symbol=p['symbol'],
                    volume=p['volume'],
                    entry_price=p['entry_price'],
                    current_price=p['current_price'],
                    stop_loss=p.get('stop_loss'),
                    take_profit=p.get('take_profit'),
                    open_time=datetime.fromisoformat(p['open_time']),
                    profit_loss=p['profit_loss']
                )
                for p in positions_data
            ]
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []

    async def send_order(self, order: MTOrder) -> Tuple[bool, str]:
        """
        Envia ordem para MT5.

        Args:
            order: MTOrder a ser enviada

        Returns:
            Tuple[bool, str]: (sucesso, ticket_ou_erro)

        Exemplo de falha:
            (False, "Insufficient margin for BUY 1 WINFUT @ 128500")
        """
        try:
            payload = {
                "symbol": order.symbol,
                "order_type": order.order_type.value,
                "volume": order.volume,
                "entry_price": order.entry_price,
                "stop_loss": order.stop_loss,
                "take_profit": order.take_profit,
                "comment": order.comment,
                "timestamp": order.timestamp.isoformat()
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/orders",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()

            result = response.json()
            if result.get("status") == "accepted":
                ticket = result.get("ticket")
                logger.info(
                    f"Order accepted: {order.order_type.value} "
                    f"{order.volume} {order.symbol} @ {order.entry_price} "
                    f"(Ticket: {ticket})"
                )
                return True, ticket
            else:
                error = result.get("error", "Unknown error")
                logger.warning(f"Order rejected: {error}")
                return False, error

        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending order: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Unexpected error sending order: {e}")
            return False, str(e)

    async def close_position(
        self,
        ticket: str,
        volume: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Fecha posição aberta.

        Args:
            ticket: ID da posição
            volume: Volume a fechar (default: 100%)

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            payload = {
                "ticket": ticket,
                "volume": volume
            }

            response = await self.client.post(
                f"{self.base_url}/api/v1/positions/close",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()

            result = response.json()
            if result.get("status") == "closed":
                logger.info(f"Position {ticket} closed successfully")
                return True, f"Position {ticket} closed"
            else:
                error = result.get("error", "Unknown error")
                return False, error

        except Exception as e:
            logger.error(f"Failed to close position {ticket}: {e}")
            return False, str(e)

    async def modify_position(
        self,
        ticket: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Modifica stop loss ou take profit de posição.

        Args:
            ticket: ID da posição
            stop_loss: Novo SL (opcional)
            take_profit: Novo TP (opcional)

        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            payload = {
                "ticket": ticket
            }
            if stop_loss is not None:
                payload["stop_loss"] = stop_loss
            if take_profit is not None:
                payload["take_profit"] = take_profit

            response = await self.client.patch(
                f"{self.base_url}/api/v1/positions/{ticket}",
                json=payload,
                headers=self._get_headers()
            )
            response.raise_for_status()

            result = response.json()
            if result.get("status") == "modified":
                logger.info(f"Position {ticket} modified")
                return True, f"Position {ticket} modified"
            else:
                error = result.get("error", "Unknown error")
                return False, error

        except Exception as e:
            logger.error(f"Failed to modify position {ticket}: {e}")
            return False, str(e)

    def _get_headers(self) -> Dict[str, str]:
        """
        Monta headers para requisições.
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AutoTrader-v1.2/Eng-Sr"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def close(self):
        """Fecha conexão HTTP."""
        await self.client.aclose()


# ============================================================================
# EXEMPLOS DE USO (após implementar Risk Validators)
# ============================================================================

async def example_order_flow():
    """Exemplo de fluxo completo de ordem."""
    adapter = MT5Adapter()

    # 1. Checar saúde
    if not await adapter.health_check():
        logger.error("MT5 REST Gateway não está disponível")
        return

    # 2. Obter info conta
    account = await adapter.get_account_info()
    logger.info(f"Account balance: R$ {account.get('balance', 0):,.2f}")

    # 3. Obter posições abertas
    positions = await adapter.get_positions()
    logger.info(f"Open positions: {len(positions)}")

    # 4. Enviar ordem (será integrado com Risk Validators)
    order = MTOrder(
        ticket="TRD-001",  # Será gerado pelo Risk Validator
        symbol="WINFUT",
        order_type=OrderType.BUY,
        volume=1.0,
        entry_price=128500.0,
        stop_loss=128470.0,
        take_profit=128530.0,
        comment="Spike detect: σ=2.1, ML score: 0.91"
    )
    success, ticket = await adapter.send_order(order)

    if success:
        logger.info(f"Order sent successfully: {ticket}")
    else:
        logger.error(f"Order rejected: {ticket}")

    await adapter.close()


if __name__ == "__main__":
    # Para testes futuros
    print("MT5Adapter module loaded (use via Risk Validators)")
