"""
Test Suite for AC3: Signal Tracker - Lifecycle Management

Tests de validação para AC3 (Rastreamento do ciclo de vida de sinais).

Cobertura:
1. Link signal to trade (AC3.1)
2. Update signal outcome when trade closes (AC3.2)
3. Mark signal as missed/expired (AC3.3)
4. Query open signals (AC3.4)
5. Calculate performance metrics (AC3.5)

Status: ✅ 8/8 TESTS IMPLEMENTED
"""

import pytest
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import sys

# Importar módulos a testar
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.application.signal_tracker import (
    SignalTracker,
    SignalOutcome,
    SignalStatus,
    SignalOutcomeType,
    SignalMetrics,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_db():
    """Cria DB temporário para testes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")

        # Criar tabela signals
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT UNIQUE NOT NULL,
                timestamp DATETIME NOT NULL,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                smc_score REAL NOT NULL,
                smc_detector TEXT NOT NULL,
                entry_price REAL NOT NULL,
                candle_index INTEGER,
                market_context_json TEXT,
                outcome_trade_id INTEGER,
                outcome_pnl REAL,
                outcome_days_open REAL,
                outcome_type TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                closed_at DATETIME,
                status TEXT DEFAULT 'OPEN',
                CHECK(signal_type IN ('BUY', 'SELL')),
                UNIQUE(timestamp, symbol, signal_type)
            )
        """)

        # Criar tabela trades para referência
        cursor.execute("""
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                volume INTEGER NOT NULL,
                entry_time DATETIME NOT NULL,
                exit_time DATETIME,
                pnl REAL,
                status TEXT DEFAULT 'OPEN'
            )
        """)

        conn.commit()
        conn.close()

        yield db_path


@pytest.fixture
def signal_tracker(temp_db):
    """Cria instância de SignalTracker com DB temporário."""
    tracker = SignalTracker(db_path=temp_db)
    yield tracker
    tracker.close()


@pytest.fixture
def sample_signal(signal_tracker, temp_db):
    """Insere um sinal de exemplo no DB."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    signal_id = "sig-001-test"
    now = datetime.utcnow()

    cursor.execute("""
        INSERT INTO signals (
            signal_id, timestamp, symbol, signal_type, smc_score,
            smc_detector, entry_price, candle_index, market_context_json,
            created_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        signal_id, now, "WIN", "BUY", 1.5,
        "BOS", 100.0, 2845, '{"rsi": 65.5}',
        now, "OPEN"
    ))

    conn.commit()
    conn.close()

    return signal_id


# ============================================================================
# TEST CASES
# ============================================================================


class TestAC3SignalTracker:
    """Suite de testes para AC3 Signal Tracking."""

    def test_ac3_001_init_tracker(self, temp_db):
        """AC3.001: Inicializa rastreador de sinais com sucesso."""
        tracker = SignalTracker(db_path=temp_db)

        assert tracker.db_path == temp_db
        assert tracker.connection is not None

        tracker.close()

    def test_ac3_002_link_signal_to_trade_success(
        self, signal_tracker, sample_signal, temp_db
    ):
        """AC3.002: Vincula sinal a trade com sucesso."""
        # Arrange
        trade_id = 1
        execution_price = 100.5
        execution_time = datetime.utcnow()

        # Inserir trade
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO trades (symbol, side, entry_price, volume, entry_time, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("WIN", "BUY", execution_price, 100, execution_time, "OPEN"))
        conn.commit()
        conn.close()

        # Act
        result = signal_tracker.link_signal_to_trade(
            signal_id=sample_signal,
            trade_id=trade_id,
            execution_price=execution_price,
            execution_time=execution_time,
        )

        # Assert
        assert result is True

        # Validar DB
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT outcome_trade_id, status FROM signals WHERE signal_id = ?",
            (sample_signal,),
        )
        row = cursor.fetchone()
        conn.close()

        assert row[0] == trade_id
        assert row[1] == "LINKED"

    def test_ac3_003_link_nonexistent_signal_fails(self, signal_tracker):
        """AC3.003: Falha ao vincular sinal inexistente."""
        # Act
        result = signal_tracker.link_signal_to_trade(
            signal_id="nonexistent",
            trade_id=1,
            execution_price=100.0,
            execution_time=datetime.utcnow(),
        )

        # Assert
        assert result is False

    def test_ac3_004_update_signal_outcome_winning(
        self, signal_tracker, sample_signal
    ):
        """AC3.004: Atualiza outcome de sinal vencedor."""
        # Arrange
        entry_time = datetime.utcnow()
        exit_time = entry_time + timedelta(hours=2)
        entry_price = 100.0
        exit_price = 102.0  # +2 pontos

        # Act
        outcome = signal_tracker.update_signal_outcome(
            signal_id=sample_signal,
            trade_id=1,
            entry_price=entry_price,
            exit_price=exit_price,
            entry_time=entry_time,
            exit_time=exit_time,
            volume=100,
            side="BUY",
        )

        # Assert
        assert outcome is not None
        assert outcome.outcome_type == SignalOutcomeType.WINNING_SIGNAL
        assert outcome.pnl == 2.0
        assert outcome.pnl_percent == 2.0
        assert outcome.status == SignalStatus.CLOSED

    def test_ac3_005_update_signal_outcome_losing(
        self, signal_tracker, sample_signal
    ):
        """AC3.005: Atualiza outcome de sinal perdedor."""
        # Arrange
        entry_time = datetime.utcnow()
        exit_time = entry_time + timedelta(hours=1)
        entry_price = 100.0
        exit_price = 98.0  # -2 pontos

        # Act
        outcome = signal_tracker.update_signal_outcome(
            signal_id=sample_signal,
            trade_id=1,
            entry_price=entry_price,
            exit_price=exit_price,
            entry_time=entry_time,
            exit_time=exit_time,
            volume=100,
            side="BUY",
        )

        # Assert
        assert outcome.outcome_type == SignalOutcomeType.LOSING_SIGNAL
        assert outcome.pnl == -2.0
        assert outcome.pnl_percent == -2.0

    def test_ac3_006_mark_signal_missed(self, signal_tracker, sample_signal, temp_db):
        """AC3.006: Marca sinal como não-executado."""
        # Act
        result = signal_tracker.mark_signal_missed(
            signal_id=sample_signal,
            expiration_time=datetime.utcnow(),
        )

        # Assert
        assert result is True

        # Validar DB
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT outcome_type, status FROM signals WHERE signal_id = ?",
            (sample_signal,),
        )
        row = cursor.fetchone()
        conn.close()

        assert row[0] == "MISSED_SIGNAL"
        assert row[1] == "MISSED"

    def test_ac3_007_get_open_signals(self, signal_tracker, sample_signal, temp_db):
        """AC3.007: Lista sinais ainda abertos."""
        # Arrange - Inserir outro sinal
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        now = datetime.utcnow()

        cursor.execute("""
            INSERT INTO signals (
                signal_id, timestamp, symbol, signal_type, smc_score,
                smc_detector, entry_price, candle_index, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "sig-002-test", now, "WIN", "SELL", 2.0,
            "CHOCH", 101.0, 2846, now, "OPEN"
        ))
        conn.commit()
        conn.close()

        # Act
        open_signals = signal_tracker.get_open_signals(symbol="WIN")

        # Assert
        assert len(open_signals) == 2
        assert open_signals[0]["status"] in ["OPEN", "LINKED"]

    def test_ac3_008_calculate_metrics(self, signal_tracker, temp_db):
        """AC3.008: Calcula métricas agregadas de desempenho."""
        # Arrange - Inserir sinais com outcomes
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        now = datetime.utcnow()

        # 3 sinais vencedores
        for i in range(3):
            cursor.execute("""
                INSERT INTO signals (
                    signal_id, timestamp, symbol, signal_type, smc_score,
                    smc_detector, entry_price, candle_index, created_at, status,
                    outcome_type, outcome_pnl, outcome_days_open
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"sig-win-{i}", now - timedelta(days=i), "WIN", "BUY", 1.5,
                "BOS", 100.0, 2845, now, "CLOSED",
                "WINNING_SIGNAL", 5.0, 0.5
            ))

        # 1 sinal perdedor
        cursor.execute("""
            INSERT INTO signals (
                signal_id, timestamp, symbol, signal_type, smc_score,
                smc_detector, entry_price, candle_index, created_at, status,
                outcome_type, outcome_pnl, outcome_days_open
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "sig-loss-0", now, "WIN", "SELL", 1.0,
            "FVG", 101.0, 2846, now, "CLOSED",
            "LOSING_SIGNAL", -3.0, 0.25
        ))

        conn.commit()
        conn.close()

        # Act
        metrics = signal_tracker.calculate_metrics(symbol="WIN")

        # Assert
        assert metrics.total_signals == 4
        assert metrics.winning_signals == 3
        assert metrics.losing_signals == 1
        assert metrics.win_rate == 75.0  # 3/4
        assert metrics.total_pnl == 12.0  # 15 - 3
        assert metrics.avg_pnl_winner == 5.0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestAC3Integration:
    """Testes de integração AC1→AC2→AC3."""

    def test_ac3_integration_complete_signal_lifecycle(
        self, signal_tracker, temp_db
    ):
        """AC3.INT.001: Ciclo de vida completo de sinal (OPEN→LINKED→CLOSED)."""
        # Arrange
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        signal_id = "sig-lifecycle"
        now = datetime.utcnow()

        # AC1: Gerar sinal (simulado)
        cursor.execute("""
            INSERT INTO signals (
                signal_id, timestamp, symbol, signal_type, smc_score,
                smc_detector, entry_price, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal_id, now, "WIN", "BUY", 2.0,
            "BOS", 100.0, now, "OPEN"
        ))

        # AC2: Persistir sinal
        cursor.execute(
            "UPDATE signals SET market_context_json = ? WHERE signal_id = ?",
            ('{"rsi": 65.5, "atr": 45.0}', signal_id)
        )

        conn.commit()
        conn.close()

        # AC3: Linkar a trade
        link_result = signal_tracker.link_signal_to_trade(
            signal_id=signal_id,
            trade_id=1,
            execution_price=100.5,
            execution_time=now + timedelta(minutes=5),
        )
        assert link_result is True

        # AC3: Fechar a trade e atualizar outcome
        exit_time = now + timedelta(hours=2)
        outcome = signal_tracker.update_signal_outcome(
            signal_id=signal_id,
            trade_id=1,
            entry_price=100.0,
            exit_price=105.0,
            entry_time=now,
            exit_time=exit_time,
            volume=100,
            side="BUY",
        )

        # Assert
        assert outcome.outcome_type == SignalOutcomeType.WINNING_SIGNAL
        assert outcome.pnl == 5.0


# ============================================================================
# EXECUTION
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
