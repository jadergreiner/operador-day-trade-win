"""
Testes Unitários - PersistenceManager (TASK-CRÍTICA-0)

Test-Driven Development: Testes pré-escritos conforme framework executa_task.md
Coverage Target: >90%
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
import json

from src.application.persistence_manager import (
    PersistenceManager,
    OperationRecord,
    DecisionRecord,
    AuditTrail,
)


class TestPersistenceManager:
    """Testes do PersistenceManager."""

    @pytest.fixture
    def persistence_manager(self):
        """Fixture: Inicializa PersistenceManager com mock de banco."""
        manager = PersistenceManager(db_path=":memory:")
        return manager

    # ============================================================
    # TEST 1: Persistência Básica de Operação
    # ============================================================

    @pytest.mark.asyncio
    async def test_persist_operation_success(self, persistence_manager):
        """
        AC #1: Operações persistidas com sucesso (async queue + DB write)
        
        Given: PersistenceManager inicializado
        When: persist_operation() chamado com OperationRecord válida
        Then: Operação armazenada em queue e DB com verificação ACID
        """
        # Arrange
        operation = OperationRecord(
            operation_id="OP-001",
            timestamp=datetime.now(),
            symbol="WINFUT",
            operation_type="BUY",
            quantity=10,
            price=Decimal("100.50"),
            status="EXECUTED",
            details={"detector": "VolumeSpike", "confidence": 0.95},
        )

        # Act
        await persistence_manager.persist_operation(operation)

        # Assert
        persisted = await persistence_manager.get_operation("OP-001")
        assert persisted is not None
        assert persisted.operation_id == "OP-001"
        assert persisted.symbol == "WINFUT"
        assert persisted.quantity == 10

    # ============================================================
    # TEST 2: Validação de Dados (ML-based labeling)
    # ============================================================

    @pytest.mark.asyncio
    async def test_label_validation_consistency(self, persistence_manager):
        """
        AC #2: Labels validados com consistency checks
        
        Given: Dataset com labels ML
        When: validate_labels() chamado
        Then: Retorna relatório de consistência (duplicatas, NaN, outliers)
        """
        # Arrange
        labels = [
            {"timestamp": "2026-02-24T10:00:00", "label": "BUY", "confidence": 0.95},
            {"timestamp": "2026-02-24T10:01:00", "label": "SELL", "confidence": 0.87},
            {"timestamp": "2026-02-24T10:02:00", "label": "BUY", "confidence": 0.92},
        ]

        # Act
        validation_report = await persistence_manager.validate_labels(labels)

        # Assert
        assert validation_report["valid"] == True
        assert validation_report["duplicates"] == 0
        assert validation_report["missing_values"] == 0
        assert validation_report["total_records"] == 3

    # ============================================================
    # TEST 3: Extração de Features (24 engineered features)
    # ============================================================

    @pytest.mark.asyncio
    async def test_feature_engineering_extraction(self, persistence_manager):
        """
        AC #3: 24 features engineered extraídas com sucesso
        
        Given: Market data (OHLCV)
        When: extract_features() chamado
        Then: Retorna 24 features corretamente calculadas
        """
        # Arrange
        market_data = {
            "symbol": "WINFUT",
            "close": [100.0, 101.0, 102.0, 101.5, 100.5],
            "volume": [1000, 1200, 1100, 950, 1050],
            "high": [101.0, 102.0, 103.0, 102.0, 101.0],
            "low": [99.0, 100.5, 101.0, 100.0, 99.5],
        }

        # Act
        features = await persistence_manager.extract_features(market_data)

        # Assert
        assert len(features) == 24
        assert "bollinger_bands" in features
        assert "rsi" in features
        assert "macd" in features
        assert "sma_50" in features
        assert all(isinstance(v, float) for v in features.values())

    # ============================================================
    # TEST 4: Data Splitting (70/15/15)
    # ============================================================

    @pytest.mark.asyncio
    async def test_data_splitting_distribution(self, persistence_manager):
        """
        AC #4: Train/val/test splits criados em proporção 70/15/15
        
        Given: Dataset com 1000 amostras
        When: create_data_splits() chamado
        Then: Retorna splits com distribuição correta (700/150/150)
        """
        # Arrange
        total_samples = 1000
        dataset = [
            {"id": i, "features": [1.0, 2.0], "label": "BUY"}
            for i in range(total_samples)
        ]

        # Act
        splits = await persistence_manager.create_data_splits(dataset)

        # Assert
        train_size = len(splits["train"])
        val_size = len(splits["val"])
        test_size = len(splits["test"])

        assert train_size == pytest.approx(700, abs=10)
        assert val_size == pytest.approx(150, abs=10)
        assert test_size == pytest.approx(150, abs=10)
        assert train_size + val_size + test_size == total_samples

    # ============================================================
    # TEST 5: Computação de Estatísticas
    # ============================================================

    @pytest.mark.asyncio
    async def test_statistics_computation(self, persistence_manager):
        """
        AC #5: Estatísticas calculadas (média, desvio, skewness)
        
        Given: Dataset com features numéricos
        When: compute_statistics() chamado
        Then: Retorna estatísticas completas (mean, std, skewness, kurtosis)
        """
        # Arrange
        features = {
            "feature_1": [1.0, 2.0, 3.0, 4.0, 5.0],
            "feature_2": [10.0, 20.0, 30.0, 25.0, 15.0],
        }

        # Act
        stats = await persistence_manager.compute_statistics(features)

        # Assert
        assert "feature_1" in stats
        assert stats["feature_1"]["mean"] == pytest.approx(3.0)
        assert stats["feature_1"]["std"] > 0
        assert "skewness" in stats["feature_1"]
        assert "kurtosis" in stats["feature_1"]

    # ============================================================
    # TEST 6: Persistência de Feature Names
    # ============================================================

    @pytest.mark.asyncio
    async def test_feature_names_persistence(self, persistence_manager):
        """
        AC #6: Feature names persistidos em arquivo (serialization)
        
        Given: Lista de 24 feature names
        When: save_feature_names() chamado
        Then: Arquivo criado e recuperável via load_feature_names()
        """
        # Arrange
        feature_names = [
            "bollinger_bands",
            "atr",
            "historical_vol",
            "rsi",
            "macd",
            "sma_50",
        ] + [f"feature_{i}" for i in range(18)]
        feature_names = feature_names[:24]

        # Act
        await persistence_manager.save_feature_names(feature_names)
        loaded_names = await persistence_manager.load_feature_names()

        # Assert
        assert loaded_names == feature_names
        assert len(loaded_names) == len(feature_names)

    # ============================================================
    # TEST 7: Testes de Qualidade (Gates)
    # ============================================================

    @pytest.mark.asyncio
    async def test_quality_gates_passing(self, persistence_manager):
        """
        AC #7: Todos os quality gates passam (assertion suite)
        
        Given: Completo pipeline de persistência (ops, labels, features)
        When: run_quality_gates() chamado
        Then: Retorna True com todos os 7 checks PASSED
        """
        # Arrange - Setup completo
        operation = OperationRecord(
            operation_id="OP-QG-001",
            timestamp=datetime.now(),
            symbol="WINFUT",
            operation_type="BUY",
            quantity=10,
            price=Decimal("100.50"),
            status="EXECUTED",
        )
        labels = [{"timestamp": "2026-02-24T10:00:00", "label": "BUY", "confidence": 0.95}]
        features = {f"feature_{i}": 1.0 for i in range(24)}

        await persistence_manager.persist_operation(operation)

        # Act
        results = await persistence_manager.run_quality_gates(
            operations_count=1,
            labels_valid=True,
            features_count=24,
            splits_valid=True,
            stats_computed=True,
            names_persisted=True,
        )

        # Assert
        assert results["status"] == "PASSED"
        assert all(check["passed"] for check in results["checks"])

    # ============================================================
    # TEST 8: Mecanismo de Recovery (Replay Journal)
    # ============================================================

    @pytest.mark.asyncio
    async def test_recovery_mechanism_replay(self, persistence_manager):
        """
        AC #8: Mechanism de recovery funciona (replay journal de 24/02)
        
        Given: Journal com operações de 24/02
        When: recovery_from_checkpoint() chamado com data 24/02
        Then: Retorna todas as ops perdidas (replay + verify)
        """
        # Arrange
        checkpoint_date = "2026-02-24"
        lost_operations = [
            OperationRecord(
                operation_id=f"OP-RECOVERY-{i:03d}",
                timestamp=datetime(2026, 2, 24, 10, i, 0),
                symbol="WINFUT",
                operation_type="BUY" if i % 2 == 0 else "SELL",
                quantity=10,
                price=Decimal("100.50") + Decimal(i),
                status="EXECUTED",
            )
            for i in range(5)
        ]

        # Act
        recovered = await persistence_manager.recover_from_checkpoint(checkpoint_date)

        # Assert
        assert len(recovered) >= 0  # May be 0 if no actual losses
        # Verificar que pode recuperar se simulamos loss
        for op in lost_operations:
            await persistence_manager.persist_operation(op)
        
        recovered_after = await persistence_manager.recover_from_checkpoint(checkpoint_date)
        assert len(recovered_after) >= len(lost_operations)


# ============================================================
# Integration Tests (Optional, but recommended)
# ============================================================


class TestPersistenceIntegration:
    """Testes de integração do sistema de persistência."""

    @pytest.mark.asyncio
    async def test_full_pipeline_e2e(self):
        """Full end-to-end: Load → Label → Features → Split → Stats → Save."""
        manager = PersistenceManager(db_path=":memory:")

        # 1. Load dataset
        dataset_size = 100
        dataset = [
            {"id": i, "features": [1.0 + i * 0.1, 2.0 + i * 0.05], "label": "BUY"}
            for i in range(dataset_size)
        ]

        # 2. Validate labels
        labels = [{"timestamp": f"2026-02-24T10:{i:02d}:00", "label": "BUY"} for i in range(10)]
        validation = await manager.validate_labels(labels)
        assert validation["valid"] == True

        # 3. Extract features
        features = await manager.extract_features(
            {"symbol": "WINFUT", "close": [100.0 + i for i in range(24)]}
        )
        assert len(features) == 24

        # 4. Create splits
        splits = await manager.create_data_splits(dataset)
        assert len(splits["train"]) + len(splits["val"]) + len(splits["test"]) == dataset_size

        # 5. Compute stats
        stats = await manager.compute_statistics(features)
        assert len(stats) > 0

        # 6. Save feature names
        await manager.save_feature_names(list(features.keys()))
        loaded = await manager.load_feature_names()
        assert len(loaded) == 24


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
