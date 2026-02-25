"""
Unit Tests para Transaction Log Service e MT5 Synchronization

Status: TASK-CRÍTICA-0 - Testes para Persistência Fix
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import sqlite3

from src.infrastructure.persistence.transaction_log_service import (
    TransactionLogService,
    TransactionType,
    TransactionStatus,
)


class TestTransactionLogService:
    """Testes do serviço de transaction log"""

    @pytest.fixture
    def service(self):
        """Cria serviço com BD temporária"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            service = TransactionLogService(db_path=str(db_path))
            yield service

    def test_schema_creation(self, service):
        """Verifica se schema foi criado corretamente"""
        conn = sqlite3.connect(service.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='transaction_journal'"
        )
        assert cursor.fetchone() is not None, "transaction_journal não foi criada"

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='dead_letter_queue'"
        )
        assert cursor.fetchone() is not None, "dead_letter_queue não foi criada"

        conn.close()

    def test_log_transaction(self, service):
        """Testa registro de nova transação"""
        # Arrange
        tx_id = "TX-001"
        entity_id = "ORDER-123"
        data = {"symbol": "WINJ26", "volume": 1.0}

        # Act
        entry = service.log_transaction(
            tx_id=tx_id,
            tx_type=TransactionType.ORDER_SENT,
            entity_id=entity_id,
            data=data
        )

        # Assert
        assert entry.tx_id == tx_id
        assert entry.entity_id == entity_id
        assert entry.status == TransactionStatus.PENDING
        assert entry.data == data
        assert entry.checksum is not None

    def test_commit_transaction(self, service):
        """Testa commit de transação"""
        # Arrange
        tx_id = "TX-002"
        service.log_transaction(
            tx_id, TransactionType.ORDER_SENT, "ORDER-456", {}
        )

        # Act
        service.commit_transaction(tx_id)

        # Assert - verificar no DB
        conn = sqlite3.connect(service.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM transaction_journal WHERE tx_id = ?", (tx_id,)
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == TransactionStatus.COMMITTED.value

    def test_fail_transaction_with_retry(self, service):
        """Testa falha com adição a dead-letter queue"""
        # Arrange
        tx_id = "TX-003"
        service.log_transaction(
            tx_id, TransactionType.TRADE_PERSISTED, "TRADE-789", {}
        )
        error_msg = "Database connection failed"

        # Act
        service.fail_transaction(tx_id, error_msg, retry=True)

        # Assert - verificar status FAILED e DLQ
        conn = sqlite3.connect(service.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT status FROM transaction_journal WHERE tx_id = ?", (tx_id,)
        )
        status = cursor.fetchone()[0]
        assert status == TransactionStatus.DEAD_LETTERED.value

        cursor.execute(
            "SELECT COUNT(*) FROM dead_letter_queue WHERE tx_id = ?", (tx_id,)
        )
        dlq_count = cursor.fetchone()[0]
        assert dlq_count == 1

        conn.close()

    def test_checksum_integrity(self, service):
        """Verifica integridade de checksum"""
        # Arrange
        data = {"order": 123, "price": 193245.50}
        service.log_transaction(
            "TX-004", TransactionType.ORDER_SENT, "ORDER-CKSUM", data
        )

        # Act
        history = service.get_transaction_history(entity_id="ORDER-CKSUM", days=1)

        # Assert
        assert len(history) == 1
        entry = history[0]
        assert entry.checksum is not None
        assert len(entry.checksum) == 64  # SHA256

        # Verifica se checksum é determinístico
        computed = entry.compute_checksum()
        assert computed == entry.checksum

    def test_get_pending_transactions(self, service):
        """Testa recuperação de transações PENDING"""
        # Arrange - criar várias transações
        service.log_transaction("TX-10", TransactionType.ORDER_SENT, "O-1", {})
        service.log_transaction("TX-11", TransactionType.ORDER_SENT, "O-2", {})
        service.log_transaction("TX-12", TransactionType.ORDER_SENT, "O-3", {})

        # Commit uma delas
        service.commit_transaction("TX-11")

        # Act
        pending = service.get_pending_transactions()

        # Assert
        assert len(pending) == 2  # TX-10 e TX-12 estão PENDING
        tx_ids = [tx.tx_id for tx in pending]
        assert "TX-10" in tx_ids
        assert "TX-12" in tx_ids
        assert "TX-11" not in tx_ids

    def test_get_dead_lettered_transactions(self, service):
        """Testa recuperação de dead-letter queue"""
        # Arrange
        service.log_transaction("TX-20", TransactionType.TRADE_PERSISTED, "T-1", {})
        service.log_transaction("TX-21", TransactionType.TRADE_PERSISTED, "T-2", {})

        service.fail_transaction("TX-20", "Connection timeout", retry=True)
        service.fail_transaction("TX-21", "Invalid data", retry=True)

        # Act
        dlq = service.get_dead_lettered_transactions()

        # Assert
        assert len(dlq) >= 2
        tx_ids = [item["tx_id"] for item in dlq]
        assert "TX-20" in tx_ids
        assert "TX-21" in tx_ids

    def test_transaction_history_filtering(self, service):
        """Testa filtragem de histórico por entity"""
        # Arrange
        service.log_transaction("TX-30", TransactionType.ORDER_SENT, "ORDER-100", {})
        service.log_transaction("TX-31", TransactionType.ORDER_SENT, "ORDER-101", {})
        service.log_transaction("TX-32", TransactionType.ORDER_SENT, "ORDER-100", {})

        # Act
        history_100 = service.get_transaction_history(entity_id="ORDER-100", days=7)
        history_101 = service.get_transaction_history(entity_id="ORDER-101", days=7)

        # Assert
        assert len(history_100) == 2
        assert len(history_101) == 1
        assert all(tx.entity_id == "ORDER-100" for tx in history_100)
        assert all(tx.entity_id == "ORDER-101" for tx in history_101)


class TestMT5SynchronizationService:
    """Testes do serviço de sincronização MT5"""

    @pytest.fixture
    def mocks(self):
        """Setup de mocks para testes"""
        class MockMT5Adapter:
            def get_orders(self, lookback_days=7):
                return [
                    {
                        "ticket": "2276014161",
                        "symbol": "WINJ26",
                        "type": "SELL",
                        "volume": 1.0,
                        "price": 193245.0,
                        "time": datetime.utcnow() - timedelta(days=1)
                    }
                ]

            def get_deals(self, lookback_days=7):
                return [
                    {
                        "deal_id": "DEAL-001",
                        "ticket": "TKT-001",
                        "symbol": "WINJ26",
                        "type": "SELL",
                        "price": 193245.0,
                        "volume": 1.0,
                        "commission": 832.0,
                        "time": datetime.utcnow() - timedelta(days=1)
                    }
                ]

            def get_positions(self):
                return []

            def get_deals_in_range(self, start, end):
                return [
                    {
                        "deal_id": "DEAL-24FEV-001",
                        "ticket": "TKT-24FEV-001",
                        "symbol": "WINJ26",
                        "status": "CLOSED",
                        "price": 193245.0,
                        "volume": 1.0,
                        "commission": 832.0,
                        "time": start + timedelta(hours=3)
                    }
                ]

        class MockTradeRepository:
            def save(self, trade):
                pass

        return {
            "mt5_adapter": MockMT5Adapter(),
            "trade_repository": MockTradeRepository()
        }

    def test_sync_all_data(self, mocks):
        """Testa sincronização geral"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            tx_log = TransactionLogService(db_path=str(db_path))

            from src.infrastructure.persistence.mt5_synchronization_service import (
                MT5SynchronizationService
            )

            sync_service = MT5SynchronizationService(
                mt5_adapter=mocks["mt5_adapter"],
                trade_repository=mocks["trade_repository"],
                transaction_log_service=tx_log,
                db_path=str(db_path)
            )

            # This would be a full integration test
            # For now, just verify the service initializes
            assert sync_service is not None
            assert sync_service.tx_log is not None


class TestPersistenceIntegration:
    """Testes de integração ponta-a-ponta"""

    def test_order_execution_flow_with_persistence(self):
        """Testa fluxo completo: ordem → execução → persistência"""
        # Este teste seria executado após a integração completa
        # com orders_executor.py e trade_repository
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
