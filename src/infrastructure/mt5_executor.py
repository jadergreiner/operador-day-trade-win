"""
MT5 Real Executor - Integração com MT5 via adapter existente

Executa ordens no MT5 real usando MT5Adapter.
Implementa retry logic com exponential backoff.
Compatible com queue_processor que aguarda este executor.
"""

import logging
from typing import Tuple, Optional, Dict, Any
import asyncio
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class MT5ExecutionError(Exception):
    """Erro de execução MT5."""
    pass


class MT5Executor:
    """
    Executor que envia ordens para MT5 real.

    Responsabilidades:
    - Converter Order genérica → formato MT5
    - Chamar MT5Adapter.send_order()
    - Implementar retry (3x exponential backoff)
    - Retornar (sucesso, ticket, erro)

    Integração com QueueProcessor:
    - Recebe Order do queue
    - Retorna (sucesso: bool, ticket: str ou None, erro: str ou None)
    """

    def __init__(self, mt5_adapter=None, max_retries: int = 3):
        """
        Inicializa executor MT5.

        Args:
            mt5_adapter: MT5Adapter existente (default: lazy init)
            max_retries: Número de tentativas (default: 3)
        """
        self.mt5_adapter = mt5_adapter
        self.max_retries = max_retries
        self.execution_stats = {
            "attempted": 0,
            "succeeded": 0,
            "failed": 0,
            "retried": 0
        }

    async def execute_order(self, order: Any) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Executa ordem no MT5 com retry logic.

        Args:
            order: Order dataclass com fields:
                - order_id (str)
                - symbol (str)
                - order_type (str) - "BUY" | "SELL"
                - volume (float)
                - price (Optional[float]) - None = market
                - sl (Optional[float])
                - tp (Optional[float])
                - comment (str)

        Returns:
            Tuple[bool, Optional[str], Optional[str]]:
            - (True, ticket, None) se sucesso
            - (False, None, error_msg) se falha após 3 tentativas

        Exemplo:
            success, ticket, error = await executor.execute_order(order)
            if success:
                print(f"Order executed: ticket={ticket}")
            else:
                print(f"Order failed: {error}")
        """
        self.execution_stats["attempted"] += 1

        # Validação básica
        if not order or not order.order_id:
            raise MT5ExecutionError("Order sem order_id")

        # Se adapter não está inicializado, lazy init
        if self.mt5_adapter is None:
            self._init_adapter()

        # Retry logic com exponential backoff: 1s, 2s, 4s
        backoff_times = [1.0, 2.0, 4.0]
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"[{order.order_id}] MT5 attempt {attempt}/{self.max_retries} | "
                    f"{order.order_type} {order.volume} {order.symbol}"
                )

                # Enviar para MT5
                ticket = await self._send_to_mt5(order)

                # Sucesso
                self.execution_stats["succeeded"] += 1
                logger.info(f"[{order.order_id}] ✅ Order executed: ticket={ticket}")
                return True, ticket, None

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"[{order.order_id}] ⚠️  Attempt {attempt} failed: {last_error}"
                )
                self.execution_stats["retried"] += 1

                # Se não é última tentativa, aguardar e retry
                if attempt < self.max_retries:
                    wait_time = backoff_times[attempt - 1]
                    logger.info(f"[{order.order_id}] Aguardando {wait_time}s antes retry...")
                    await asyncio.sleep(wait_time)

        # Falha após todas tentativas
        self.execution_stats["failed"] += 1
        logger.error(f"[{order.order_id}] ❌ All {self.max_retries} attempts failed")
        return False, None, last_error

    async def _send_to_mt5(self, order: Any) -> str:
        """
        Envia ordem ao MT5 e retorna ticket.

        Pode ser:
        1. Chamada ao MT5Adapter.send_order() existente
        2. Chamada a REST API MT5 Gateway
        3. Conexão direta MT5 (se disponível)

        Returns:
            ticket (str): Ticket MT5 da ordem

        Raises:
            Exception: Se falha no MT5
        """
        # Try 1: MT5Adapter.send_order() se existe
        if self.mt5_adapter and hasattr(self.mt5_adapter, 'send_order'):
            # MT5Adapter pode ser sync ou async
            if asyncio.iscoroutinefunction(self.mt5_adapter.send_order):
                result = await self.mt5_adapter.send_order(order)
            else:
                result = self.mt5_adapter.send_order(order)

            # Validar resultado
            if isinstance(result, tuple):
                # (sucesso: bool, ticket_ou_erro: str)
                success, ticket_or_error = result
                if success:
                    return ticket_or_error
                else:
                    raise Exception(ticket_or_error)
            elif isinstance(result, str):
                # Direct ticket return
                return result
            else:
                raise Exception(f"Invalid MT5Adapter response: {result}")

        # Try 2: REST API (fallback)
        if self.mt5_adapter and hasattr(self.mt5_adapter, 'client'):
            return await self._send_via_rest_api(order)

        # Try 3: Direct MT5 (última tentativa)
        return await self._send_via_direct_mt5(order)

    async def _send_via_rest_api(self, order: Any) -> str:
        """Envia via REST API MT5 Gateway."""
        import httpx

        try:
            payload = self._order_to_api_payload(order)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "http://localhost:8000/api/v1/orders",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

                if result.get("success"):
                    return result.get("ticket")
                else:
                    raise Exception(result.get("error", "API error"))
        except Exception as e:
            logger.error(f"REST API send failed: {e}")
            raise

    async def _send_via_direct_mt5(self, order: Any) -> str:
        """Envia diretamente ao MT5 (direct library call)."""
        try:
            import MetaTrader5 as mt5
            import os

            # Garantir conexão no terminal correto (se configurado)
            terminal_path = os.getenv("MT5_TERMINAL_PATH")
            if terminal_path:
                if not os.path.isfile(terminal_path):
                    raise MT5ExecutionError(f"MT5_TERMINAL_PATH inválido: {terminal_path}")
                if not mt5.initialize(path=terminal_path):
                    raise MT5ExecutionError(f"MT5 initialize failed: {mt5.last_error()}")
            else:
                if not mt5.initialize():
                    raise MT5ExecutionError("MT5 initialize failed")

            # Obter symbol info
            symbol = self._resolve_symbol(order.symbol)
            ticker = mt5.symbol_info(symbol)
            if ticker is None:
                raise MT5ExecutionError(f"Symbol {symbol} not found")

            # Mapear order_type
            if order.order_type.upper() == "BUY":
                action_type = mt5.ORDER_TYPE_BUY
            else:
                action_type = mt5.ORDER_TYPE_SELL

            # Usar preço market se não informado
            price = order.price if order.price else (ticker.ask if order.order_type.upper() == "BUY" else ticker.bid)

            # Montar request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": float(order.volume),
                "type": action_type,
                "price": price,
                "deviation": 10,
                "magic": 234000,
                "comment": order.comment or "P1-CORE Order",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # Add SL/TP se fornecidos
            if order.sl:
                request["sl"] = float(order.sl)
            if order.tp:
                request["tp"] = float(order.tp)

            # Send order
            result = mt5.order_send(request)

            if result is None:
                raise MT5ExecutionError(f"order_send returned None: {mt5.last_error()}")

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                raise MT5ExecutionError(
                    f"order_send returned {result.retcode}: {result.comment}"
                )

            return str(result.order)

        except Exception as e:
            logger.error(f"Direct MT5 send failed: {e}")
            raise

    def _order_to_api_payload(self, order: Any) -> Dict[str, Any]:
        """Converte Order para payload REST API."""
        return {
            "order_id": order.order_id,
            "symbol": order.symbol,
            "order_type": order.order_type.upper(),
            "volume": float(order.volume),
            "price": float(order.price) if order.price else None,
            "sl": float(order.sl) if order.sl else None,
            "tp": float(order.tp) if order.tp else None,
            "comment": order.comment or ""
        }

    def _resolve_symbol(self, symbol: str) -> str:
        """Resolve símbolo para formato MT5."""
        # WIN$N → WINJ26, etc.
        symbol_map = {
            "WIN": "WINJ26",
            "WINFUT": "WINJ26",
            "WIN$N": "WINJ26"
        }
        return symbol_map.get(symbol.upper(), symbol)

    def _init_adapter(self) -> None:
        """Lazy init MT5Adapter se não fornecido."""
        try:
            # Try import MT5Adapter
            from src.infrastructure.adapters.mt5_adapter import MT5Adapter
            self.mt5_adapter = MT5Adapter()
            logger.info("MT5Adapter lazy initialized")
        except Exception as e:
            logger.warning(f"Could not initialize MT5Adapter: {e}")
            # Continue sem adapter (will use direct MT5)

    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas de execução."""
        return self.execution_stats.copy()
