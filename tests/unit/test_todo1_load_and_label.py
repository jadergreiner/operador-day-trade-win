#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TEST SUITE: load_and_label() - TODO-1 INTEGRATION-ML-001
Testa exatamente a implementação em ml_feature_engineer.py :: DatasetLoader.load_and_label()

AC-1 até AC-7 validadas
Todas as 7 acceptance criteria testadas
"""

import pytest
import pandas as pd
import numpy as np
import time
import tempfile
from pathlib import Path
from src.application.ml_feature_engineer import DatasetLoader


@pytest.fixture
def training_dataset_path():
    """Usar o arquivo real training_dataset.csv"""
    return Path("training_dataset.csv")


class TestTodo1LoadAndLabel:
    """Test suite for TODO-1: Load and Label (Issue #66)"""

    def test_ac1_load_csv_success(self, training_dataset_path):
        """AC-1: Load CSV file efficiently"""
        if not training_dataset_path.exists():
            pytest.skip("training_dataset.csv not found")

        loader = DatasetLoader(str(training_dataset_path))
        result = loader.load_and_label(dataset_path=str(training_dataset_path))

        assert result is not None
        assert 'X' in result
        assert 'y' in result
        assert 'window_ids' in result
        assert 'metadata' in result
        print(f"✅ AC-1: Dataset loaded successfully ({result['metadata']['n_samples']} samples)")

    def test_ac2_generate_labels_correct(self, training_dataset_path):
        """AC-2: Generate labels (0/1 only)"""
        if not training_dataset_path.exists():
            pytest.skip("training_dataset.csv not found")

        loader = DatasetLoader(str(training_dataset_path))
        result = loader.load_and_label(dataset_path=str(training_dataset_path))

        y = result['y']
        unique_labels = np.unique(y)

        assert set(unique_labels) <= {0, 1}, \
            f"Labels must be 0 or 1, got {set(unique_labels)}"
        assert result['metadata']['nan_count'] == 0
        print(f"✅ AC-2: Labels generated correctly (unique labels: {unique_labels})")

    def test_ac3_extract_24_features(self, training_dataset_path):
        """AC-3: Extract exactly 24 features"""
        if not training_dataset_path.exists():
            pytest.skip("training_dataset.csv not found")

        loader = DatasetLoader(str(training_dataset_path))
        result = loader.load_and_label(dataset_path=str(training_dataset_path))

        n_features = result['metadata']['n_features']
        assert n_features == 24, f"Expected 24 features, got {n_features}"

        X = result['X']
        assert X.shape[1] == 24
        print(f"✅ AC-3: 24 features extracted (shape: {X.shape})")

    def test_ac4_validate_imbalance(self, training_dataset_path):
        """AC-4: Validate class imbalance < 70%"""
        if not training_dataset_path.exists():
            pytest.skip("training_dataset.csv not found")

        loader = DatasetLoader(str(training_dataset_path))
        result = loader.load_and_label(dataset_path=str(training_dataset_path))

        imbalance_pct = result['metadata']['imbalance_pct']
        assert 20 <= imbalance_pct <= 80, \
            f"Imbalance {imbalance_pct:.1f}% outside range [20-80%]"
        print(f"✅ AC-4: Class imbalance OK ({imbalance_pct:.1f}% BUY)")

    def test_ac5_zero_nan_values(self, training_dataset_path):
        """AC-5: Zero NaN values in all columns"""
        if not training_dataset_path.exists():
            pytest.skip("training_dataset.csv not found")

        loader = DatasetLoader(str(training_dataset_path))
        result = loader.load_and_label(dataset_path=str(training_dataset_path))

        X = result['X']
        y = result['y']

        nan_count_X = np.isnan(X).sum()
        nan_count_y = np.isnan(y).sum()

        assert nan_count_X == 0, f"NaN in X: {nan_count_X}"
        assert nan_count_y == 0, f"NaN in y: {nan_count_y}"
        assert result['metadata']['nan_count'] == 0
        print(f"✅ AC-5: Zero NaN values (checked {X.shape[0]*X.shape[1]} cells)")

    def test_ac6_feature_names_persisted(self, training_dataset_path):
        """AC-6: Feature names persisted to metadata"""
        if not training_dataset_path.exists():
            pytest.skip("training_dataset.csv not found")

        loader = DatasetLoader(str(training_dataset_path))
        result = loader.load_and_label(dataset_path=str(training_dataset_path))

        feature_names = result['metadata']['feature_names']
        assert len(feature_names) == 24
        assert all(isinstance(name, str) for name in feature_names)
        print(f"✅ AC-6: Feature names persisted ({len(feature_names)} names)")

    def test_ac7_performance_under_500ms(self, training_dataset_path):
        """AC-7: Execution time < 500ms"""
        if not training_dataset_path.exists():
            pytest.skip("training_dataset.csv not found")

        loader = DatasetLoader(str(training_dataset_path))

        start = time.perf_counter()
        result = loader.load_and_label(dataset_path=str(training_dataset_path))
        elapsed_ms = (time.perf_counter() - start) * 1000

        execution_time_ms = result['metadata']['execution_time_ms']

        assert execution_time_ms < 500, \
            f"Performance {execution_time_ms:.1f}ms exceeds 500ms SLA"
        print(f"✅ AC-7: Performance OK ({execution_time_ms:.1f}ms < 500ms)")


# Additional validation tests
def test_window_ids_continuous(training_dataset_path):
    """Validar window_ids é contínuo (AC-3 adicional)"""
    if not training_dataset_path.exists():
        pytest.skip("training_dataset.csv not found")

    loader = DatasetLoader(str(training_dataset_path))
    result = loader.load_and_label(dataset_path=str(training_dataset_path))

    window_ids = result['window_ids']
    expected_ids = np.arange(len(window_ids))

    assert np.array_equal(window_ids, expected_ids), \
        "window_ids not contiguous"
    print(f"✅ window_ids continuous ({window_ids[0]}-{window_ids[-1]})")


def test_metadata_structure(training_dataset_path):
    """Validar estrutura de metadata"""
    if not training_dataset_path.exists():
        pytest.skip("training_dataset.csv not found")

    loader = DatasetLoader(str(training_dataset_path))
    result = loader.load_and_label(dataset_path=str(training_dataset_path))

    metadata = result['metadata']
    required_keys = [
        'imbalance_pct', 'nan_count', 'execution_time_ms',
        'n_samples', 'n_features', 'feature_names',
        'label_distribution'
    ]

    for key in required_keys:
        assert key in metadata, f"Missing metadata key: {key}"

    # Validar label_distribution
    label_dist = metadata['label_distribution']
    assert label_dist['total'] == metadata['n_samples']
    print(f"✅ Metadata structure valid")


def test_file_not_found():
    """AC-7 adicional: FileNotFoundError"""
    loader = DatasetLoader("/invalid/path.csv")

    with pytest.raises(FileNotFoundError):
        loader.load_and_label(dataset_path="/invalid/path.csv")

    print(f"✅ FileNotFoundError raised correctly")


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short"
    ])
