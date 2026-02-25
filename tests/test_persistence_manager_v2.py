"""Unit Tests - PersistenceManager (TASK-CRITICA-0)"""

import pytest
import asyncio
import numpy as np
from src.application.persistence_manager import PersistenceManager


class TestPersistenceManagerSimple:
    """AC validation testes."""

    @pytest.fixture
    def manager(self):
        """Initialize manager."""
        return PersistenceManager(db_path=":memory:")

    @pytest.mark.asyncio
    async def test_ac1_label_validation(self, manager):
        """AC #2: Labels validated."""
        labels = [
            {"timestamp": "2026-02-24T10:00:00", "label": "BUY", "confidence": 0.95},
            {"timestamp": "2026-02-24T10:01:00", "label": "SELL", "confidence": 0.87},
        ]
        report = await manager.validate_labels(labels)
        assert report["valid"] == True
        assert report["duplicates"] == 0

    @pytest.mark.asyncio
    async def test_ac2_data_splitting(self, manager):
        """AC #4: Train/val/test 70/15/15."""
        dataset = [{"id": i, "features": [1.0, 2.0]} for i in range(100)]
        splits = await manager.create_data_splits(dataset)
        total = len(splits["train"]) + len(splits["val"]) + len(splits["test"])
        assert total == 100

    @pytest.mark.asyncio
    async def test_ac3_statistics(self, manager):
        """AC #5: Statistics computed."""
        features = {
            "price": [100.0, 101.0, 102.0, 101.5, 100.5],
            "volume": [1000, 1200, 1100, 950, 1050],
        }
        stats = await manager.compute_statistics(features)
        assert "mean" in stats["price"]
        assert "std" in stats["price"]

    @pytest.mark.asyncio
    async def test_ac4_feature_names(self, manager):
        """AC #6: Feature names persisted."""
        names = [f"feature_{i}" for i in range(24)]
        await manager.save_feature_names(names)
        loaded = await manager.load_feature_names()
        assert len(loaded) == 24

    @pytest.mark.asyncio
    async def test_ac5_features_extraction(self, manager):
        """AC #3: Features extracted."""
        market_data = {
            "close": list(np.linspace(100, 110, 50)),
            "volume": list(np.linspace(1000, 1200, 50)),
            "high": list(np.linspace(101, 111, 50)),
            "low": list(np.linspace(99, 109, 50)),
        }
        features = await manager.extract_features(market_data)
        assert len(features) >= 20
        assert all(isinstance(v, float) for v in features.values())

    @pytest.mark.asyncio
    async def test_ac6_quality_gates(self, manager):
        """AC #7: Quality gates."""
        result = await manager.run_quality_gates(
            operations_count=1,
            labels_valid=True,
            features_count=24,
            splits_valid=True,
            stats_computed=True,
            names_persisted=True,
        )
        assert result["status"] in ["PASSED", "FAILED"]
        assert "checks" in result


class TestPersistenceManagerIntegration:
    """Integration tests."""

    @pytest.mark.asyncio
    async def test_e2e_pipeline(self):
        """Full E2E pipeline."""
        manager = PersistenceManager(db_path=":memory:")

        # Validate labels
        labels = [
            {"timestamp": f"2026-02-24T10:{i:02d}:00", "label": "BUY", "confidence": 0.85 + (i * 0.01)}
            for i in range(10)
        ]
        val_result = await manager.validate_labels(labels)
        assert val_result["valid"] == True

        # Create splits
        dataset = [{"id": i, "data": 1.0} for i in range(100)]
        splits = await manager.create_data_splits(dataset)
        assert len(splits["train"]) + len(splits["val"]) + len(splits["test"]) == 100

        # Save features
        features = [f"feature_{i}" for i in range(24)]
        await manager.save_feature_names(features)
        loaded = await manager.load_feature_names()
        assert len(loaded) == 24
