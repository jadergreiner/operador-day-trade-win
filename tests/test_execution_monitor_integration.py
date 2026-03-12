"""
AC5.8: Testes de integração - ExecutionMonitor
"""

import asyncio
import sqlite3
import tempfile
from datetime import datetime, timedelta

import pytest

from src.infrastructure.execution_monitor import ExecutionMonitor, ExecutionMonitorConfig


class FakeBroadcaster:
    def __init__(self):
        self.messages = []

    async def broadcast(self, message):
        self.messages.append(message)


class DummyClient:
    def broadcast(self, message, trader_id=None):
        return True


def _init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE order_queue (
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
        """
    )
    conn.commit()
    conn.close()


@pytest.mark.asyncio
async def test_execution_monitor_order_update_emits():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    _init_db(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute(
        """
        INSERT INTO order_queue (
            order_id, symbol, order_type, volume, payload,
            status, created_at, updated_at, attempt_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("ORD-1", "WIN", "BUY", 1.0, "{}", "PENDING", now, now, 0),
    )
    conn.commit()
    conn.close()

    monitor = ExecutionMonitor(
        ati1_client=DummyClient(),
        config=ExecutionMonitorConfig(db_path=db_path, trader_id="TRADER_001"),
    )
    monitor._broadcast = FakeBroadcaster()

    updates = monitor._fetch_order_updates()
    for row in updates:
        await monitor._emit_order_update(row)

    assert any(m.get("type") == "ORDER_STATUS_UPDATE" for m in monitor._broadcast.messages)
