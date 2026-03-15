"""
AC5.9 Cobertura de Código - Feedback de Execução

Este arquivo testa diretamente a importação normal para medir cobertura.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
import sqlite3
import sys

from src.trade_outcome_feedback import TradeOutcomeFeedbackDB, ExecutionOutcome


@pytest.fixture
def temp_db():
    """Criar banco temporário com schema completo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Tabela trades
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE,
                symbol TEXT,
                pnl REAL,
                decisions_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela predictions
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                direction TEXT,
                confidence_score REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

        yield db_path


class TestAC59Coverage:
    """Testes para cobertura de AC5.9."""

    def test_initialize_db(self, temp_db):
        """Teste: Inicializar DB com execution_feedback table."""
        db = TradeOutcomeFeedbackDB(str(temp_db))
        assert db.db_path == temp_db

        # Verificar que execution_feedback foi criada
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='execution_feedback'")
        assert cursor.fetchone() is not None
        db.conn.close()

    def test_win_trade_processing(self, temp_db):
        """Teste: Processar e rotular trade WIN."""
        conn = sqlite3.connect(str(temp_db))

        # Inserir dados
        conn.execute(
            "INSERT INTO trades (order_id, pnl) VALUES (?, ?)",
            ("ORDER_001", 500.0)
        )
        conn.execute(
            "INSERT INTO predictions (direction, confidence_score) VALUES (?, ?)",
            ("BUY", 0.85)
        )
        conn.commit()
        conn.close()

        # Processar
        db = TradeOutcomeFeedbackDB(str(temp_db))
        outcome = db.process_trade_outcome(trade_id=1)

        assert outcome.signal_label == "GOOD"
        assert outcome.outcome_type == "WIN"
        assert outcome.pnl == 500.0
        assert outcome.confidence == 0.85
        assert outcome.prediction_direction == "BUY"
        db.conn.close()

    def test_loss_trade_processing(self, temp_db):
        """Teste: Processar e rotular trade LOSS."""
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO trades (order_id, pnl) VALUES (?, ?)",
            ("ORDER_002", -250.0)
        )
        conn.execute(
            "INSERT INTO predictions (direction, confidence_score) VALUES (?, ?)",
            ("SELL", 0.75)
        )
        conn.commit()
        conn.close()

        db = TradeOutcomeFeedbackDB(str(temp_db))
        outcome = db.process_trade_outcome(trade_id=1)

        assert outcome.signal_label == "BAD"
        assert outcome.outcome_type == "LOSS"
        assert outcome.pnl == -250.0
        db.conn.close()

    def test_breakeven_trade(self, temp_db):
        """Teste: Processar trade BREAKEVEN."""
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO trades (order_id, pnl) VALUES (?, ?)",
            ("ORDER_003", 0.0)
        )
        conn.execute(
            "INSERT INTO predictions (direction, confidence_score) VALUES (?, ?)",
            ("BUY", 0.50)
        )
        conn.commit()
        conn.close()

        db = TradeOutcomeFeedbackDB(str(temp_db))
        outcome = db.process_trade_outcome(trade_id=1)

        assert outcome.outcome_type == "BREAKEVEN"
        assert outcome.signal_label == "BAD"  # PnL == 0 é BAD
        db.conn.close()

    def test_execution_feedback_persistence(self, temp_db):
        """Teste: Persistência em EXECUTION_FEEDBACK."""
        conn = sqlite3.connect(str(temp_db))
        conn.execute(
            "INSERT INTO trades (order_id, pnl) VALUES (?, ?)",
            ("ORDER_004", 1000.0)
        )
        conn.execute(
            "INSERT INTO predictions (direction, confidence_score) VALUES (?, ?)",
            ("BUY", 0.95)
        )
        conn.commit()
        conn.close()

        db = TradeOutcomeFeedbackDB(str(temp_db))
        outcome = db.process_trade_outcome(trade_id=1)

        # Verificar persistência
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM execution_feedback WHERE trade_id = ?",
            (outcome.trade_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        conn.close()
        db.conn.close()

    def test_get_connection_lazy(self, temp_db):
        """Teste: _get_connection lazy initialization."""
        db = TradeOutcomeFeedbackDB(str(temp_db))
        assert db.conn is None

        conn = db._get_connection()
        assert conn is not None
        assert db.conn is not None
        db.conn.close()

    def test_determine_outcome_type_win(self, temp_db):
        """Teste: _determine_outcome_type para WIN."""
        db = TradeOutcomeFeedbackDB(str(temp_db))

        assert db._determine_outcome_type(100.0) == "WIN"
        assert db._determine_outcome_type(0.01) == "WIN"
        assert db._determine_outcome_type(1000.0) == "WIN"
        db.conn.close()

    def test_determine_outcome_type_loss(self, temp_db):
        """Teste: _determine_outcome_type para LOSS."""
        db = TradeOutcomeFeedbackDB(str(temp_db))

        assert db._determine_outcome_type(-100.0) == "LOSS"
        assert db._determine_outcome_type(-0.01) == "LOSS"
        assert db._determine_outcome_type(-1000.0) == "LOSS"
        db.conn.close()

    def test_determine_outcome_type_breakeven(self, temp_db):
        """Teste: _determine_outcome_type para BREAKEVEN."""
        db = TradeOutcomeFeedbackDB(str(temp_db))

        assert db._determine_outcome_type(0.0) == "BREAKEVEN"
        db.conn.close()

    def test_execution_outcome_dataclass(self):
        """Teste: ExecutionOutcome dataclass fields."""
        outcome = ExecutionOutcome(
            trade_id=42,
            signal_label="GOOD",
            outcome_type="WIN",
            confidence=0.88,
            pnl=750.0,
            prediction_direction="SELL",
            feedback_id=1,
            timestamp="2026-03-15T10:30:45.123456"
        )

        assert outcome.trade_id == 42
        assert outcome.signal_label == "GOOD"
        assert outcome.outcome_type == "WIN"
        assert outcome.confidence == 0.88
        assert outcome.pnl == 750.0
        assert outcome.prediction_direction == "SELL"
        assert outcome.feedback_id == 1
        assert outcome.timestamp == "2026-03-15T10:30:45.123456"
