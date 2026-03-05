"""
P1-CORE: Order Queue baseado em SQLite

Fila assíncrona de ordens para execução em MT5.
Persiste em data/db/trading.db para auditoria completa.

Windows-compatible com timeout para locks.
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
from dataclasses import dataclass, asdict
import sqlite3
from pathlib import Path
import time

logger = logging.getLogger(__name__)


class OrderStatus(str, Enum):
    """Estado de uma ordem no fluxo."""
    PENDING = "PENDING"          # Aguardando execução
    PROCESSING = "PROCESSING"    # Sendo enviada para MT5
    EXECUTED = "EXECUTED"        # Executada com sucesso
    FAILED = "FAILED"            # Falha na execução
    CANCELLED = "CANCELLED"      # Cancelada pelo operador


@dataclass
class Order:
    """Modelo de uma ordem para fila."""
    order_id: str                 # UUID único
    symbol: str                   # "WINFUT" ou ticker
    order_type: str               # "BUY", "SELL"
    volume: float                 # Quantidade (ex: 1.0)
    price: Optional[float] = None # Preço (None = market)
    sl: Optional[float] = None    # Stop Loss
    tp: Optional[float] = None    # Take Profit
    comment: str = ""             # Observação
    created_at: Optional[str] = None
    attempt_count: int = 0        # Quantas vezes tentou
    last_error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Serializa para JSON."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Order":
        """Desserializa de JSON."""
        return cls(**data)


class OrderQueue:
    """Fila de ordens persistente em SQLite."""

    def __init__(self, db_path: str = "data/db/trading.db"):
        """Inicializa queue com conexão ao banco."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Retorna conexão SQLite com timeout para Windows locks."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=10.0,
            check_same_thread=False
        )
        conn.isolation_level = None  # Autocommit
        return conn

    def _init_schema(self) -> None:
        """Cria tabela se não existir."""
        time.sleep(0.05)
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS order_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    volume REAL NOT NULL,
                    price REAL, sl REAL, tp REAL,
                    comment TEXT,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    attempt_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    mt5_ticket INTEGER,
                    executed_price REAL,
                    executed_at TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON order_queue(status)
            """)
            logger.info(f"OrderQueue initialized: {self.db_path}")
        finally:
            conn.close()

    def push(self, order: Order) -> bool:
        """Insere ordem na fila com status PENDING."""
        conn = None
        try:
            now = datetime.utcnow().isoformat()
            order.created_at = now
            conn = self._get_connection()
            conn.execute("""
                INSERT INTO order_queue (
                    order_id, symbol, order_type, volume, price,
                    sl, tp, comment, payload, status, created_at,
                    updated_at, attempt_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.order_id, order.symbol, order.order_type, order.volume,
                order.price, order.sl, order.tp, order.comment,
                json.dumps(order.to_dict()), OrderStatus.PENDING.value,
                now, now, 0
            ))
            logger.info(f"Order pushed: {order.order_id}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Order {order.order_id} already exists (duplicate)")
            return False
        except Exception as e:
            logger.error(f"Error pushing order: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def poll(self, limit: int = 10) -> List[Order]:
        """Busca PENDING orders (não bloqueia)."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT * FROM order_queue
                WHERE status = ? ORDER BY created_at ASC LIMIT ?
            """, (OrderStatus.PENDING.value, limit))
            rows = cursor.fetchall()
            orders = []
            for row in rows:
                payload = json.loads(row[10])  # payload field
                orders.append(Order.from_dict(payload))
            return orders
        except Exception as e:
            logger.error(f"Error polling orders: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def mark_processing(self, order_id: str) -> bool:
        """Marca ordem como PROCESSING."""
        return self._update_status(order_id, OrderStatus.PROCESSING.value)

    def mark_executed(self, order_id: str, mt5_ticket: int, executed_price: float) -> bool:
        """Marca ordem como EXECUTED com detalhe MT5."""
        conn = None
        try:
            now = datetime.utcnow().isoformat()
            conn = self._get_connection()
            conn.execute("""
                UPDATE order_queue
                SET status = ?, mt5_ticket = ?, executed_price = ?,
                    executed_at = ?, updated_at = ?
                WHERE order_id = ?
            """, (OrderStatus.EXECUTED.value, mt5_ticket, executed_price, now, now, order_id))
            logger.info(f"Order executed: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error marking executed: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def mark_failed(self, order_id: str, error: str, retry: bool = True) -> bool:
        """Marca ordem como FAILED."""
        conn = None
        try:
            now = datetime.utcnow().isoformat()
            status = OrderStatus.PENDING.value if retry else OrderStatus.FAILED.value
            conn = self._get_connection()
            conn.execute("""
                UPDATE order_queue
                SET status = ?, last_error = ?, attempt_count = attempt_count + 1,
                    updated_at = ?
                WHERE order_id = ?
            """, (status, error, now, order_id))
            logger.warning(f"Order failed: {order_id} | Retry={retry}")
            return True
        except Exception as e:
            logger.error(f"Error marking failed: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def _update_status(self, order_id: str, new_status: str) -> bool:
        """Helper para atualizar status."""
        conn = None
        try:
            now = datetime.utcnow().isoformat()
            conn = self._get_connection()
            conn.execute(
                "UPDATE order_queue SET status = ?, updated_at = ? WHERE order_id = ?",
                (new_status, now, order_id)
            )
            return True
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def get_status(self, order_id: str) -> Optional[str]:
        """Retorna status de uma ordem."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.execute(
                "SELECT status FROM order_queue WHERE order_id = ?",
                (order_id,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def get_stats(self) -> Dict[str, int]:
        """Retorna estatísticas da fila."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM order_queue GROUP BY status
            """)
            stats = {row[0]: row[1] for row in cursor.fetchall()}
            logger.info(f"Queue stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
        finally:
            if conn:
                conn.close()

    def cleanup_old_orders(self, days: int = 7) -> int:
        """Remove ordens executadas com mais de N dias."""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.execute("""
                DELETE FROM order_queue
                WHERE status IN (?, ?)
                AND datetime(executed_at) < datetime('now', '-' || ? || ' days')
            """, (OrderStatus.EXECUTED.value, OrderStatus.FAILED.value, days))
            deleted = cursor.rowcount
            logger.info(f"Cleanup: deleted {deleted} old orders")
            return deleted
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")
            return 0
        finally:
            if conn:
                conn.close()
