"""
P1-CORE: Queue Processor - Worker Assíncrono

Processa ordens da fila SQLite e as executa em MT5.
Roda em background (não bloqueia operador).

Padrão:
1. Poll a cada 100ms → busca PENDING orders
2. Marca como PROCESSING
3. Tenta executar em MT5 (async)
4. Marca EXECUTED ou FAILED (com retry)
5. Notifica via broadcast (WebSocket)

Retry strategy:
- 3 tentativas com backoff exponencial (1s, 2s, 4s)
- Após 3 falhas, marca FAILED e avisa operador
"""

import asyncio
import logging
from typing import Optional, Callable
from datetime import datetime

from src.application.order_queue_sqlite import OrderQueue, Order, OrderStatus

logger = logging.getLogger(__name__)


class QueueProcessor:
    """Processador assíncrono de ordens."""

    def __init__(
        self,
        queue: OrderQueue,
        mt5_executor: Optional[Callable] = None,
        poll_interval_ms: float = 100,
        max_batch_size: int = 10,
    ):
        """
        Args:
            queue: Instância da OrderQueue
            mt5_executor: Função async para executar ordem em MT5
            poll_interval_ms: Intervalo de polling (default: 100ms)
            max_batch_size: Max ordens processadas por batch
        """
        self.queue = queue
        self.mt5_executor = mt5_executor or self._default_executor
        self.poll_interval_ms = poll_interval_ms / 1000  # Converter para segundos
        self.max_batch_size = max_batch_size
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.stats = {
            "processed": 0,
            "executed": 0,
            "failed": 0,
            "retried": 0,
        }

    async def start(self) -> None:
        """Inicia processador em background."""
        if self.running:
            logger.warning("Processor already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._process_loop())
        logger.info("QueueProcessor started")

    async def stop(self) -> None:
        """Para processador gracefully."""
        self.running = False
        if self.task:
            await self.task
        logger.info("QueueProcessor stopped")

    async def _process_loop(self) -> None:
        """Loop principal: poll → execute → persist."""
        while self.running:
            try:
                # Poll de PENDING orders
                orders = self.queue.poll(limit=self.max_batch_size)

                if orders:
                    logger.debug(f"Processing {len(orders)} orders...")
                    await self._process_batch(orders)
                else:
                    # Sem ordens, aguarda antes de próximo poll
                    await asyncio.sleep(self.poll_interval_ms)

            except Exception as e:
                logger.error(f"Error in process loop: {e}")
                await asyncio.sleep(self.poll_interval_ms)

    async def _process_batch(self, orders: list[Order]) -> None:
        """Processa um batch de ordens em paralelo."""
        tasks = [self._execute_order(order) for order in orders]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_order(self, order: Order, attempt: int = 1) -> None:
        """Executa ordem individual com retry logic."""
        try:
            # Marca como PROCESSING
            self.queue.mark_processing(order.order_id)
            self.stats["processed"] += 1

            logger.info(f"Executing {order.order_id}: {order.symbol} "
                       f"{order.order_type} {order.volume} (attempt {attempt}/3)")

            # Executa em MT5
            result = await self.mt5_executor(order)

            if result.get("success"):
                # Sucesso: marca EXECUTED
                mt5_ticket = result.get("ticket", 0)
                executed_price = result.get("price", order.price or 0)

                self.queue.mark_executed(
                    order.order_id,
                    mt5_ticket,
                    executed_price
                )
                self.stats["executed"] += 1

                logger.info(f"Order executed: {order.order_id} "
                           f"(ticket={mt5_ticket})")

                # Notifica operador
                await self._notify_order_executed(order, mt5_ticket)

            else:
                # Falha: retry ou fail permanente
                error = result.get("error", "Unknown error")

                if attempt < 3:
                    # Retry com backoff exponencial (1s, 2s, 4s)
                    backoff = 2 ** (attempt - 1)
                    logger.warning(f"Order {order.order_id} failed: {error} "
                                 f"| Retrying in {backoff}s...")
                    self.stats["retried"] += 1

                    await asyncio.sleep(backoff)
                    await self._execute_order(order, attempt + 1)

                else:
                    # Falha permanente após 3 tentativas
                    self.queue.mark_failed(order.order_id, error, retry=False)
                    self.stats["failed"] += 1

                    logger.error(f"Order failed permanently: {order.order_id} | {error}")

                    # Notifica operador de falha crítica
                    await self._notify_order_failed(order, error)

        except Exception as e:
            logger.error(f"Exception executing {order.order_id}: {e}")
            self.queue.mark_failed(order.order_id, str(e), retry=True)

    async def _default_executor(self, order: Order) -> dict:
        """
        Executor real MT5 (default).
        Integra com MT5Executor para envio real ao broker.
        """
        from src.infrastructure.mt5_executor import MT5Executor

        executor = MT5Executor()
        success, ticket, error = await executor.execute_order(order)

        return {
            "success": success,
            "ticket": ticket or "",
            "price": order.price or 1.0,
            "error": error,
        }

    async def _notify_order_executed(self, order: Order, ticket: int) -> None:
        """Notifica operador (via WebSocket, logging, etc)."""
        logger.info(f"NOTIFICATION: Order {order.order_id} executed! "
                   f"Ticket={ticket} | Price={order.price}")
        # TODO: Broadcast via WebSocket se implementado

    async def _notify_order_failed(self, order: Order, error: str) -> None:
        """Notifica operador de falha crítica."""
        logger.warning(f"ALERT: Order {order.order_id} failed after 3 attempts! "
                      f"Error: {error}")
        # TODO: Broadcast via WebSocket + Alerta

    def get_stats(self) -> dict:
        """Retorna estatísticas de processamento."""
        queue_stats = self.queue.get_stats()
        return {
            "processor_stats": self.stats,
            "queue_stats": queue_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
