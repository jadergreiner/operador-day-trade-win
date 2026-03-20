"""
Execution Monitor - AC5.8
Monitora transicoes de ordens, posicoes e risco em tempo real.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.infrastructure.database.db_paths import resolve_operational_db_path
from src.infrastructure.position_monitor import PositionMonitor
from src.infrastructure.position_broadcaster import PositionBroadcaster, PositionMessage

logger = logging.getLogger(__name__)


@dataclass
class ExecutionMonitorConfig:
    db_path: str | None = None
    trader_id: str = "TRADER_001"
    order_poll_interval_ms: int = 500
    status_broadcast_interval_ms: int = 2000

    def __post_init__(self) -> None:
        if not self.db_path:
            repo_root = Path(__file__).resolve().parent.parent.parent
            self.db_path = str(resolve_operational_db_path(repo_root))


class _BroadcastAdapter:
    """Adapter async para broadcast usando cliente ATI-1 HTTP."""

    def __init__(self, ati1_client, trader_id: str):
        self.ati1_client = ati1_client
        self.trader_id = trader_id

    async def broadcast(self, message: Dict[str, Any]):
        # Envia de forma síncrona em thread pool para não travar o loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, self.ati1_client.broadcast, message, self.trader_id
        )


class ExecutionMonitor:
    """
    Monitor de execução em tempo real.

    - Observa mudanças no order_queue (SQLite).
    - Integra PositionMonitor + PositionBroadcaster.
    - Emite eventos via ATI-1 WebSocket.
    """

    def __init__(
        self,
        ati1_client,
        config: ExecutionMonitorConfig,
        position_monitor: Optional[PositionMonitor] = None,
    ):
        self.config = config
        self.ati1_client = ati1_client
        self._broadcast = _BroadcastAdapter(ati1_client, config.trader_id)

        self.position_monitor = position_monitor or PositionMonitor()
        self.position_broadcaster = PositionBroadcaster(
            position_monitor=self.position_monitor,
            connection_manager=self._broadcast,
        )

        self.running = False
        self._tasks: List[asyncio.Task] = []
        self._last_status_by_order: Dict[str, str] = {}
        self._last_updated_at: Optional[str] = None
        self.stats = {
            "order_updates": 0,
            "position_updates": 0,
            "risk_violations": 0,
            "broadcast_errors": 0,
        }

    async def start(self) -> None:
        if self.running:
            logger.warning("ExecutionMonitor already running")
            return
        self.running = True

        # Start position broadcaster (starts position monitor too)
        await self.position_broadcaster.start()

        self._tasks = [
            asyncio.create_task(self._order_poll_loop()),
            asyncio.create_task(self._status_loop()),
        ]
        logger.info("ExecutionMonitor started")

    async def stop(self) -> None:
        self.running = False
        for task in self._tasks:
            task.cancel()
        await self.position_broadcaster.stop()
        logger.info("ExecutionMonitor stopped")

    async def _order_poll_loop(self) -> None:
        interval = self.config.order_poll_interval_ms / 1000.0
        while self.running:
            try:
                updates = self._fetch_order_updates()
                for update in updates:
                    await self._emit_order_update(update)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"ExecutionMonitor order poll error: {e}")
                await asyncio.sleep(interval)

    def _fetch_order_updates(self) -> List[Dict[str, Any]]:
        db_path = Path(self.config.db_path)
        if not db_path.exists():
            return []

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            if self._last_updated_at:
                cursor.execute(
                    """
                    SELECT order_id, status, updated_at, created_at, attempt_count,
                           last_error, mt5_ticket, executed_price, executed_at
                    FROM order_queue
                    WHERE updated_at > ?
                    ORDER BY updated_at ASC
                    """,
                    (self._last_updated_at,),
                )
            else:
                cursor.execute(
                    """
                    SELECT order_id, status, updated_at, created_at, attempt_count,
                           last_error, mt5_ticket, executed_price, executed_at
                    FROM order_queue
                    ORDER BY updated_at ASC
                    """
                )

            rows = [dict(r) for r in cursor.fetchall()]
            if rows:
                self._last_updated_at = rows[-1].get("updated_at")
            return rows
        finally:
            conn.close()

    async def _emit_order_update(self, row: Dict[str, Any]) -> None:
        order_id = row.get("order_id")
        status = row.get("status")
        prev_status = self._last_status_by_order.get(order_id)

        if prev_status == status:
            return

        self._last_status_by_order[order_id] = status
        self.stats["order_updates"] += 1

        payload = {
            "type": "ORDER_STATUS_UPDATE",
            "timestamp": datetime.utcnow().isoformat(),
            "trader_id": self.config.trader_id,
            "data": {
                "order_id": order_id,
                "status": status,
                "prev_status": prev_status,
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
                "attempt_count": row.get("attempt_count"),
                "last_error": row.get("last_error"),
                "mt5_ticket": row.get("mt5_ticket"),
                "executed_price": row.get("executed_price"),
                "executed_at": row.get("executed_at"),
            },
        }

        try:
            await self._broadcast.broadcast(payload)
        except Exception as e:
            self.stats["broadcast_errors"] += 1
            logger.error(f"Order update broadcast error: {e}")

    async def _status_loop(self) -> None:
        interval = self.config.status_broadcast_interval_ms / 1000.0
        while self.running:
            try:
                status_message = PositionMessage.monitor_status(self.get_stats())
                await self._broadcast.broadcast(status_message)
                await asyncio.sleep(interval)
            except Exception as e:
                self.stats["broadcast_errors"] += 1
                logger.error(f"Monitor status broadcast error: {e}")
                await asyncio.sleep(interval)

    def get_stats(self) -> Dict[str, int]:
        stats = dict(self.stats)
        stats.update(self.position_broadcaster.get_stats())
        return stats
