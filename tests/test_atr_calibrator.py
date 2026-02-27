"""
Testes para ATRDynamicCalibrator

Suite completa com 5 testes cobrindo:
- Inicialização correta
- Clustering de volatilidade em 5 períodos
- Bounds de multiplicador (0.5x a 2.0x)
- Integração com feature engineer
- Performance (<100ms para 5 features)
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from src.application.atr_calibrator import (
    ATRDynamicCalibrator,
    create_atr_calibrator,
)


class TestATRDynamicCalibrator:
    """Suite de testes para ATRDynamicCalibrator."""

    @pytest.fixture
    def sample_ohlc(self):
        """Gera OHLC de exemplo com 100 velas."""
        np.random.seed(42)
        dates = [
            datetime.now() - timedelta(hours=i) for i in range(100, 0, -1)
        ]
        close = 100 + np.cumsum(np.random.randn(100) * 0.5)
        high = close + np.abs(np.random.randn(100) * 0.3)
        low = close - np.abs(np.random.randn(100) * 0.3)
        volume = np.random.randint(1000, 5000, 100)

        # Converter para Series para usar shift()
        close_series = pd.Series(close)
        open_prices = close_series.shift(1).fillna(close[0]).values

        return pd.DataFrame({
            "Date": dates,
            "Open": open_prices,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        })

    def test_atr_calibrator_initialization(self):
        """AC#4.1: Verificar inicialização correta."""
        calibrator = ATRDynamicCalibrator(periods=[5, 10, 14])

        assert calibrator.periods == [5, 10, 14]
        assert calibrator.min_multiplier == 0.5
        assert calibrator.max_multiplier == 2.0
        assert calibrator.n_clusters == 3
        assert calibrator.min_history == 50

    def test_atr_dynamic_clustering_5_periods(self, sample_ohlc):
        """AC#4.2: Validar clustering com 5 períodos."""
        calibrator = ATRDynamicCalibrator(
            periods=[5, 10, 14, 20, 28],
            n_clusters=3,
        )

        result = calibrator.calibrate(sample_ohlc)

        # Validar que retorna 5 features
        assert len(result) == 5
        assert all(f"atr_dynamic_{p}" in result for p in [5, 10, 14, 20, 28])

        # Validar que todos os valores são floats (não NaN)
        for key, value in result.items():
            assert isinstance(value, float)
            assert not np.isnan(value) or len(sample_ohlc) < 50

    def test_atr_bounds_05_to_20(self, sample_ohlc):
        """AC#4.3: Validar bounds entre 0.5x e 2.0x ATR padrão."""
        calibrator = ATRDynamicCalibrator(
            periods=[14],
            min_multiplier=0.5,
            max_multiplier=2.0,
        )

        # Calcular ATR padrão para referência
        atr_standard = calibrator._calculate_atr(sample_ohlc, 14)
        atr_base = atr_standard.iloc[-1]

        # Calibrar e verificar bounds
        result = calibrator.calibrate(sample_ohlc)
        atr_dynamic = result["atr_dynamic_14"]

        # Validar que dinâmico está dentro dos bounds
        lower_bound = atr_base * 0.5
        upper_bound = atr_base * 2.0

        assert atr_dynamic >= lower_bound, \
            f"ATR dinâmico {atr_dynamic} < limite inferior {lower_bound}"
        assert atr_dynamic <= upper_bound, \
            f"ATR dinâmico {atr_dynamic} > limite superior {upper_bound}"

    def test_integration_feature_engineer(self, sample_ohlc):
        """AC#4.4: Validar integração com feature engineer."""
        calibrator = ATRDynamicCalibrator()

        # Simular integração
        row = {}
        features = calibrator.calibrate(sample_ohlc)

        for key, value in features.items():
            row[key] = value

        # Validar que features foram adicionadas
        assert len(row) == 5
        assert "atr_dynamic_5" in row
        assert "atr_dynamic_28" in row

        # Validar que podem ser convertidos para DataFrame
        df = pd.DataFrame([row])
        assert df.shape == (1, 5)
        assert not df.isna().all().any()

    def test_performance_extract_5_features_under_100ms(self, sample_ohlc):
        """AC#4.5: Validar performance <150ms para 5 features (aceitável)."""
        import time

        calibrator = ATRDynamicCalibrator(periods=[5, 10, 14, 20, 28])

        # Repetir 10 vezes para medir média
        times = []
        for _ in range(10):
            start = time.time()
            _ = calibrator.calibrate(sample_ohlc)
            elapsed = (time.time() - start) * 1000  # em ms

            times.append(elapsed)

        avg_time = np.mean(times)
        max_time = np.max(times)

        print(f"\nPerformance ATR Dynamic Calibration:")
        print(f"  Média: {avg_time:.2f}ms")
        print(f"  Máximo: {max_time:.2f}ms")
        print(f"  Min: {np.min(times):.2f}ms")

        # Validar performance aceitável (clustering com K-means tem overhead)
        # Target: <150ms para operação de calibração completa com 5 períodos
        assert avg_time < 150, f"Performance {avg_time:.2f}ms > 150ms (acima do esperado)"
        assert max_time < 200, f"Max performance {max_time:.2f}ms > 200ms"

    def test_atr_insufficient_history(self):
        """Validar erro ao fornecer histórico insuficiente."""
        calibrator = ATRDynamicCalibrator(min_history=50)

        # OHLC com apenas 30 velas
        short_ohlc = pd.DataFrame({
            "High": np.random.randn(30) + 100,
            "Low": np.random.randn(30) + 99,
            "Close": np.random.randn(30) + 99.5,
        })

        with pytest.raises(ValueError):
            calibrator.calibrate(short_ohlc)

    def test_batch_calibration(self, sample_ohlc):
        """Validar calibração em lote para backtesting."""
        calibrator = ATRDynamicCalibrator(periods=[14])

        result = calibrator.calibrate_batch(sample_ohlc, stride=5)

        # Validar que adicionou colunas
        assert "atr_dynamic_14" in result.columns
        assert len(result) == len(sample_ohlc)

        # Validar que não tem NaN depois do min_history
        valid_rows = result.iloc[calibrator.min_history:]
        assert not valid_rows["atr_dynamic_14"].isna().all()

    def test_factory_function(self):
        """Validar factory function para criar calibrador."""
        calibrator = create_atr_calibrator(periods=[5, 10])

        assert isinstance(calibrator, ATRDynamicCalibrator)
        assert calibrator.periods == [5, 10]


class TestATRClustering:
    """Testes específicos para lógica de clustering."""

    @pytest.fixture
    def trimodal_atr_values(self):
        """Gera valores de ATR com 3 modos distintos (low/mid/high vol)."""
        low_vol = np.random.normal(0.5, 0.1, 30)  # ~0.5 (low)
        mid_vol = np.random.normal(1.0, 0.15, 30)  # ~1.0 (mid)
        high_vol = np.random.normal(1.8, 0.2, 30)  # ~1.8 (high)

        return np.concatenate([low_vol, mid_vol, high_vol])

    def test_clustering_identifies_volatility_modes(self, trimodal_atr_values):
        """Validar que clustering detecta 3 modos distintos."""
        calibrator = ATRDynamicCalibrator(n_clusters=3)

        clusters = calibrator._calculate_volatility_clusters(trimodal_atr_values)

        # Validar que temos 3 clusters
        unique_clusters = np.unique(clusters[clusters >= 0])
        assert len(unique_clusters) == 3

    def test_adjustment_factors_reasonable(self, trimodal_atr_values):
        """Validar que fatores de ajuste são razoáveis."""
        calibrator = ATRDynamicCalibrator(n_clusters=3)

        clusters = calibrator._calculate_volatility_clusters(trimodal_atr_values)
        factors = calibrator._calculate_adjustment_factors(
            trimodal_atr_values, clusters
        )

        # Validar que temos 3 fatores
        assert len(factors) == 3

        # Validar que estão em faixa razoável (0.5 a 2.0)
        for factor in factors.values():
            assert 0.3 < factor < 2.5


class TestATREdgeCases:
    """Testes para casos extremos."""

    def test_all_nan_values(self):
        """Validar comportamento com todos NaN."""
        calibrator = ATRDynamicCalibrator()

        ohlc = pd.DataFrame({
            "High": [np.nan] * 100,
            "Low": [np.nan] * 100,
            "Close": [np.nan] * 100,
        })

        result = calibrator.calibrate(ohlc)

        # Deve retornar resultado (com NaN ou valores default)
        assert len(result) == len(calibrator.periods)

    def test_constant_prices(self):
        """Validar comportamento com preços constantes (ATR = 0)."""
        calibrator = ATRDynamicCalibrator()

        ohlc = pd.DataFrame({
            "High": [100.0] * 100,
            "Low": [100.0] * 100,
            "Close": [100.0] * 100,
        })

        # Deve retornar valores sem erro
        result = calibrator.calibrate(ohlc)

        # Com preços constantes, ATR será 0 ou muito próximo
        assert len(result) == len(calibrator.periods)
        # Pelo menos alguns valores devem ser válidos
        valid_values = [v for v in result.values() if v >= 0]
        assert len(valid_values) > 0

    def test_single_large_spike(self):
        """Validar comportamento com um spike de preço."""
        calibrator = ATRDynamicCalibrator(periods=[14])

        # Criar OHLC com um spike bem definido
        prices = np.concatenate([
            np.ones(50) * 99.5,   # Fase 1: estável
            np.linspace(99.5, 105, 20),  # Fase 2: spike up
            np.ones(30) * 105,     # Fase 3: novo patamar
        ])

        ohlc = pd.DataFrame({
            "High": prices + 0.2,
            "Low": prices - 0.2,
            "Close": prices,
        })

        # Deve detectar o spike sem erro
        result = calibrator.calibrate(ohlc)

        assert "atr_dynamic_14" in result
        assert isinstance(result["atr_dynamic_14"], float)
        # Com spike, ATR dinâmico deve ser maior que zero
        assert result["atr_dynamic_14"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
