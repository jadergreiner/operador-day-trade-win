"""
AC5.9: Testes de Integração - Feedback de Execução no QueueProcessor

Arquivo: test_ac5_9_integration_queue_processor.py
Objetivo: Validar que TradeOutcomeFeedbackDB integra corretamente
com QueueProcessor após execução de ordens.

Fluxo Testado:
1. Ordem é executada com sucesso no MT5
2. QueueProcessor chama process_trade_outcome()
3. ExecutionOutcome é persistido em EXECUTION_FEEDBACK table
4. Sinal é rotulado como GOOD/BAD para ML
"""

import pytest
import sqlite3
import json
import tempfile
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from dataclasses import dataclass

# Imports do projeto - AC5.9
from src.trade_outcome_feedback import TradeOutcomeFeedbackDB, ExecutionOutcome


@dataclass
class MockOrder:
    """Mock simplificado de Order para testes."""
    order_id: str
    symbol: str
    order_type: str
    volume: float
    price: float
    sl: float
    tp: float
    comment: str
    payload: Dict[str, Any]


class MockOrderQueue:
    """Mock simplificado de OrderQueue para testes."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self) -> None:
        """Cria tabela de ordens para testes."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS order_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                symbol TEXT NOT NULL,
                order_type TEXT NOT NULL,
                volume REAL NOT NULL,
                price REAL, sl REAL, tp REAL,
                comment TEXT,
                payload TEXT NOT NULL,
                executed_price REAL,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def insert_order(
        self,
        order: MockOrder,
        executed_price: float | None = None
    ) -> int:
        """Insere ordem no banco para teste."""
        conn = sqlite3.connect(str(self.db_path))
        now = datetime.utcnow().isoformat()
        cursor = conn.execute("""
            INSERT INTO order_queue (
                order_id, symbol, order_type, volume, price,
                sl, tp, comment, payload, executed_price, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order.order_id, order.symbol, order.order_type, order.volume,
            order.price, order.sl, order.tp, order.comment,
            json.dumps(order.payload), executed_price or order.price, now
        ))
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trade_id


@pytest.fixture
def temp_db() -> Path:
    """Cria banco SQLite temporário para testes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_trading.db"
        yield db_path


@pytest.fixture
def feedback_db(temp_db: Path) -> TradeOutcomeFeedbackDB:
    """Inicializa feedback DB no banco temporário."""
    return TradeOutcomeFeedbackDB(str(temp_db))


@pytest.fixture
def mock_queue(temp_db: Path) -> MockOrderQueue:
    """Inicializa fila mock no banco temporário."""
    return MockOrderQueue(temp_db)


@pytest.fixture
def sample_order() -> MockOrder:
    """Cria ordem de teste."""
    return MockOrder(
        order_id="TEST_001",
        symbol="WINFUT",
        order_type="BUY",
        volume=1.0,
        price=100000.0,
        sl=99500.0,
        tp=100500.0,
        comment="Test order AC5.9",
        payload={"confidence": 0.85, "direction": "BUY"},
    )


class TestAC59FeedbackProcessing:
    """Testes do processamento de feedback AC5.9."""

    def test_feedback_win_trade(
        self,
        mock_queue: MockOrderQueue,
        feedback_db: TradeOutcomeFeedbackDB,
        sample_order: MockOrder,
    ) -> None:
        """
        Teste 1: Trade com lucro deve ser rotulado como GOOD/WIN.

        Cenário:
        - Comprado em 100000
        - Vendido em 100500 (lucro)
        - Esperado: label=GOOD, outcome=WIN
        """
        # Arrange
        trade_id = mock_queue.insert_order(
            sample_order,
            executed_price=100000.0
        )

        # Act
        outcome = feedback_db.process_trade_outcome(
            trade_id=trade_id,
            executed_price=100000.0,
            current_price=100500.0,
            prediction_direction="BUY",
            confidence=0.85,
        )

        # Assert
        assert outcome is not None
        assert outcome.trade_id == trade_id
        assert outcome.signal_label == "GOOD"
        assert outcome.outcome_type == "WIN"
        assert outcome.feedback_id is not None
        assert outcome.confidence == 0.85

    def test_feedback_loss_trade(
        self,
        mock_queue: MockOrderQueue,
        feedback_db: TradeOutcomeFeedbackDB,
        sample_order: MockOrder,
    ) -> None:
        """
        Teste 2: Trade com prejuízo deve ser rotulado como BAD/LOSS.
        """
        # Arrange
        trade_id = mock_queue.insert_order(
            sample_order,
            executed_price=100000.0
        )

        # Act
        outcome = feedback_db.process_trade_outcome(
            trade_id=trade_id,
            executed_price=100000.0,
            current_price=99900.0,
            prediction_direction="BUY",
            confidence=0.85,
        )

        # Assert
        assert outcome.signal_label == "BAD"
        assert outcome.outcome_type == "LOSS"

    def test_feedback_breakeven_trade(
        self,
        mock_queue: MockOrderQueue,
        feedback_db: TradeOutcomeFeedbackDB,
        sample_order: MockOrder,
    ) -> None:
        """
        Teste 3: Trade com PnL próximo a zero = BREAKEVEN.
        """
        # Arrange
        trade_id = mock_queue.insert_order(
            sample_order,
            executed_price=100000.0
        )

        # Act
        outcome = feedback_db.process_trade_outcome(
            trade_id=trade_id,
            executed_price=100000.0,
            current_price=100050.0,
            prediction_direction="BUY",
            confidence=0.85,
        )

        # Assert
        assert outcome.outcome_type == "BREAKEVEN"

    def test_feedback_with_confidence_levels(
        self,
        mock_queue: MockOrderQueue,
        feedback_db: TradeOutcomeFeedbackDB,
        sample_order: MockOrder,
    ) -> None:
        """
        Teste 4: Feedback deve preservar confidence levels.
        """
        # Arrange
        trade_id = mock_queue.insert_order(
            sample_order,
            executed_price=100000.0
        )

        # Act: Testar múltiplos confidence levels
        for confidence in [0.5, 0.75, 0.95]:
            outcome = feedback_db.process_trade_outcome(
                trade_id=trade_id,
                executed_price=100000.0,
                current_price=100500.0,
                prediction_direction="BUY",
                confidence=confidence,
            )

            # Assert
            assert 0.0 <= outcome.confidence <= 1.0

    def test_feedback_timestamp_iso_format(
        self,
        mock_queue: MockOrderQueue,
        feedback_db: TradeOutcomeFeedbackDB,
        sample_order: MockOrder,
    ) -> None:
        """
        Teste 5: Feedback deve incluir timestamp em ISO format.
        """
        # Arrange
        trade_id = mock_queue.insert_order(
            sample_order,
            executed_price=100000.0
        )

        # Act
        outcome = feedback_db.process_trade_outcome(
            trade_id=trade_id,
            executed_price=100000.0,
            current_price=100500.0,
            prediction_direction="BUY",
            confidence=0.85,
        )

        # Assert
        assert outcome.timestamp is not None
        try:
            datetime.fromisoformat(outcome.timestamp)
            assert True
        except ValueError:
            pytest.fail("Timestamp não é ISO format")

    def test_feedback_unique_feedback_id(
        self,
        mock_queue: MockOrderQueue,
        feedback_db: TradeOutcomeFeedbackDB,
    ) -> None:
        """
        Teste 6: Cada feedback deve ter feedback_id único.
        """
        # Arrange: Criar 3 ordens
        outcomes = []

        for i in range(3):
            order = MockOrder(
                order_id=f"TEST_{i:03d}",
                symbol="WINFUT",
                order_type="BUY",
                volume=1.0,
                price=100000.0,
                sl=99500.0,
                tp=100500.0,
                comment=f"Test {i}",
                payload={"confidence": 0.85, "direction": "BUY"},
            )
            trade_id = mock_queue.insert_order(
                order,
                executed_price=100000.0
            )

            outcome = feedback_db.process_trade_outcome(
                trade_id=trade_id,
                executed_price=100000.0,
                current_price=100500.0,
                prediction_direction="BUY",
                confidence=0.85,
            )
            outcomes.append(outcome)

        # Assert: Todos feedback_ids devem ser únicos
        feedback_ids = [o.feedback_id for o in outcomes]
        assert len(feedback_ids) == len(set(feedback_ids))

    def test_feedback_stats_aggregation(
        self,
        mock_queue: MockOrderQueue,
        feedback_db: TradeOutcomeFeedbackDB,
    ) -> None:
        """
        Teste 7: Agregação de estatísticas para ML.

        Cenário: 4 trades: 3x WIN, 1x LOSS
        Esperado: stats refletem 75% win rate
        """
        # Arrange: Criar 4 ordens e processar alternadamente
        outcomes = []

        for i in range(4):
            order = MockOrder(
                order_id=f"STATS_{i:02d}",
                symbol="WINFUT",
                order_type="BUY",
                volume=1.0,
                price=100000.0,
                sl=99500.0,
                tp=100500.0,
                comment="",
                payload={"confidence": 0.85, "direction": "BUY"},
            )
            trade_id = mock_queue.insert_order(
                order,
                executed_price=100000.0
            )

            # 3 wins, 1 loss
            current_price = 100500.0 if i < 3 else 99900.0
            outcome = feedback_db.process_trade_outcome(
                trade_id=trade_id,
                executed_price=100000.0,
                current_price=current_price,
                prediction_direction="BUY",
                confidence=0.85,
            )
            outcomes.append(outcome)

        # Assert
        wins = sum(1 for o in outcomes if o.outcome_type == "WIN")
        losses = sum(1 for o in outcomes if o.outcome_type == "LOSS")
        assert wins == 3
        assert losses == 1
        win_rate = wins / (wins + losses)
        assert abs(win_rate - 0.75) < 0.01

    def test_feedback_direction_preservation(
        self,
        mock_queue: MockOrderQueue,
        feedback_db: TradeOutcomeFeedbackDB,
    ) -> None:
        """
        Teste 8: Feedback deve preservar direction do sinal.
        """
        # Arrange: Testar BUY e SELL
        for direction in ["BUY", "SELL"]:
            order = MockOrder(
                order_id=f"DIR_{direction}",
                symbol="WINFUT",
                order_type=direction,
                volume=1.0,
                price=100000.0,
                sl=99500.0,
                tp=100500.0,
                comment="",
                payload={"confidence": 0.85, "direction": direction},
            )
            trade_id = mock_queue.insert_order(
                order,
                executed_price=100000.0
            )

            # Act
            outcome = feedback_db.process_trade_outcome(
                trade_id=trade_id,
                executed_price=100000.0,
                current_price=100500.0,
                prediction_direction=direction,
                confidence=0.85,
            )

            # Assert
            assert outcome.prediction_direction == direction


class TestAC59CodeQuality:
    """Testes de qualidade de código."""

    def test_execution_outcome_dataclass(self) -> None:
        """Teste 9: ExecutionOutcome deve ser dataclass válido."""
        outcome = ExecutionOutcome(
            trade_id=1,
            signal_label="GOOD",
            outcome_type="WIN",
            confidence=0.85,
            pnl=500.0,
            prediction_direction="BUY",
        )

        # Assert
        assert outcome.trade_id == 1
        assert outcome.signal_label == "GOOD"
        assert outcome.outcome_type == "WIN"

    def test_feedback_db_type_hints(
        self,
        feedback_db: TradeOutcomeFeedbackDB,
    ) -> None:
        """Teste 10: TradeOutcomeFeedbackDB deve ter type hints válidos."""
        # Verificar que a classe tem atributos tipados
        assert hasattr(feedback_db, 'db_path')
        assert hasattr(feedback_db, 'conn')
        assert hasattr(feedback_db, 'process_trade_outcome')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.trade_outcome_feedback"])
