"""
Unit Tests para TODO-5: Pattern Detection (Issue #8 - ML-102)

Testar a função detect_patterns() que analisa distribuição de labels
e detecta padrões nas features.

Acceptance Criteria (Issue #8):
☐ AC-1: Analyze label distribution
☐ AC-2: Detect feature patterns
☐ AC-3: Generate insights report
☐ AC-4: Plot histogram
☐ AC-5: Top 10 features
☐ AC-6: Unit tests with fixtures
"""

from pathlib import Path

import numpy as np
import pytest

from src.application.ml_feature_engineer import FeatureEngineer


class TestDetectPatterns:
    """Test suite para detect_patterns() - Issue #8"""

    @pytest.fixture(autouse=True)
    def isolated_output_dir(self, tmp_path, monkeypatch):
        """Mantém artefatos de saída isolados por teste."""
        monkeypatch.chdir(tmp_path)

    @pytest.fixture
    def engineer(self):
        """Create FeatureEngineer instance."""
        return FeatureEngineer()

    @pytest.fixture
    def sample_data(self):
        """Create sample dataset (17280 samples, 26 features)."""
        np.random.seed(42)
        X = np.random.randn(17280, 26)
        # Create imbalanced labels: 60% positive, 40% negative
        y = np.concatenate([
            np.ones(10368, dtype=int),
            np.zeros(6912, dtype=int)
        ])
        np.random.shuffle(y)  # Shuffle labels
        return X, y

    def _build_correlated_data(self, sample_data):
        """Cria dataset com features fortemente correlacionadas ao label."""
        X, y = sample_data
        X = X.copy()
        y_float = y.astype(float)

        # Garante ranking previsível para testar ordenação/importance.
        X[:, 0] = y_float
        X[:, 1] = 1.0 - y_float

        rng = np.random.default_rng(123)
        X[:, 2] = y_float * 0.75 + rng.normal(0.0, 0.05, size=len(y))
        return X, y

    # ==================== TEST AC-1: LABEL DISTRIBUTION ====================

    def test_detect_patterns_label_distribution(self, engineer, sample_data):
        """
        AC-1: Analyze label distribution (captured vs uncaptured).

        Given: dataset with 60/40 label split
        When: detect_patterns(X, y) called
        Then: returns label_distribution with counts and ratio
        """
        X, y = sample_data

        result = engineer.detect_patterns(X, y)

        assert isinstance(result, dict)
        assert "label_distribution" in result

        label_distribution = result["label_distribution"]
        assert label_distribution["positive"] == 10368
        assert label_distribution["negative"] == 6912
        assert label_distribution["ratio"] == pytest.approx(0.6)

    # ==================== TEST AC-2: FEATURE PATTERNS ====================

    def test_detect_patterns_feature_importance(self, engineer, sample_data):
        """
        AC-2: Detect patterns correlated with features.

        Given: dataset with some correlated features
        When: detect_patterns(X, y) called
        Then: returns feature importance scores
        """
        X, y = self._build_correlated_data(sample_data)

        result = engineer.detect_patterns(X, y)

        assert result["feature_importance"]
        assert result["feature_importance"][:2] == [
            ("close", 1.0),
            ("high", -1.0),
        ]
        assert result["top_features"][:2] == ["close", "high"]

    # ==================== TEST AC-3: INSIGHTS ====================

    def test_detect_patterns_insights(self, engineer, sample_data):
        """
        AC-3: Generate markdown insights report.

        Given: dataset analyzed
        When: detect_patterns(X, y) called
        Then: returns text insights list
        """
        X, y = self._build_correlated_data(sample_data)

        result = engineer.detect_patterns(X, y)

        insights = result["insights"]
        assert isinstance(insights, list)
        assert len(insights) >= 3
        assert any("Distribuicao de labels" in insight for insight in insights)
        assert any("Feature mais correlacionada" in insight for insight in insights)
        assert any("Multicolinearidade alta detectada" in insight for insight in insights)

    # ==================== TEST AC-4: HISTOGRAM ====================

    def test_detect_patterns_histogram(self, engineer, sample_data):
        """
        AC-4: Plot histogram of label distribution.

        Given: dataset analyzed
        When: detect_patterns(X, y) called
        Then: saves histogram to file
        """
        X, y = sample_data

        result = engineer.detect_patterns(X, y)

        plot_path = Path(result["plot_path"])
        assert plot_path.is_absolute()
        assert plot_path.exists()
        assert plot_path.suffix == ".png"
        assert plot_path.stat().st_size > 0

    # ==================== TEST AC-5: TOP 10 FEATURES ====================

    def test_detect_patterns_top_features(self, engineer, sample_data):
        """
        AC-5: Identify top 10 most relevant features.

        Given: dataset with feature importance
        When: detect_patterns(X, y) called
        Then: returns top 10 feature names
        """
        X, y = self._build_correlated_data(sample_data)

        result = engineer.detect_patterns(X, y)

        top_features = result["top_features"]
        assert isinstance(top_features, list)
        assert len(top_features) == 10
        assert top_features[:2] == ["close", "high"]
        assert all(feature in engineer.feature_columns for feature in top_features)

    # ==================== TEST AC-6: COVERAGE ====================

    def test_detect_patterns_execution_time(self, engineer, sample_data):
        """
        AC-6: Return execution_time in metadata.

        Given: detect_patterns() executed
        When: function returns
        Then: includes execution_time in dict
        """
        X, y = sample_data

        result = engineer.detect_patterns(X, y)

        assert "execution_time" in result
        assert isinstance(result["execution_time"], float)
        assert result["execution_time"] > 0.0

    def test_detect_patterns_complete_return(self, engineer, sample_data):
        """
        AC-6: Return dict has all required keys.

        Given: detect_patterns() executed
        When: function returns
        Then: dict has all expected keys
        """
        X, y = sample_data

        result = engineer.detect_patterns(X, y)

        expected_keys = {
            "label_distribution",
            "feature_importance",
            "top_features",
            "insights",
            "plot_path",
            "execution_time",
        }
        assert set(result.keys()) == expected_keys


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
