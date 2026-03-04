"""
Testes unitarios para P0-2 backtest engine.

Test Suite para BacktestEngine e MetricsCalculator.
"""

import pytest
import numpy as np
import pandas as pd
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from src.infrastructure.backtests.backtest_engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestMetrics
)
from src.infrastructure.backtests.metrics_calculator import MetricsCalculator


class TestBacktestEngineBasics:
    """Testes basicos do BacktestEngine."""

    @pytest.fixture
    def engine(self):
        """Fixture: engine com configuracao padrao."""
        return BacktestEngine()

    @pytest.fixture
    def sample_dataset(self, tmp_path):
        """Fixture: dataset de teste (252 dias, 24 features)."""
        # Gerar 1000+ amostras
        dates = pd.date_range('2023-01-01', periods=1000, freq='D')
        features = {f'feature_{i}': np.random.randn(1000) for i in range(24)}
        features['label'] = np.random.binomial(1, 0.55, 1000)  # 55% BUY
        features['close'] = np.random.uniform(100, 110, 1000)

        df = pd.DataFrame(features, index=dates)
        csv_path = tmp_path / "test_dataset.csv"
        df.to_csv(csv_path)

        return str(csv_path)

    def test_engine_initialization(self, engine):
        """AC1: Engine inicializa sem erros."""
        assert engine is not None
        assert engine.config.cv_folds == 5
        assert engine.config.lookback_period == 252
        assert engine.dataset is None

    def test_load_dataset_success(self, engine, sample_dataset):
        """AC2: Dataset carregado (1000+ samples, 24 features)."""
        engine.config.dataset_path = sample_dataset
        df = engine.load_dataset()

        assert df is not None
        assert len(df) >= 1000
        assert 'label' in df.columns
        assert df.shape[1] >= 24
        assert engine.dataset is not None

    def test_load_dataset_missing_file(self, engine):
        """AC2: Erro se arquivo nao existe."""
        engine.config.dataset_path = "/nonexistent/path.csv"

        with pytest.raises(FileNotFoundError):
            engine.load_dataset()

    def test_load_dataset_incomplete(self, engine, tmp_path):
        """AC2: Erro se dataset < 1000 samples."""
        # Criar dataset pequeno
        df = pd.DataFrame(
            {'feature_0': np.random.randn(100), 'label': np.random.binomial(1, 0.5, 100)}
        )
        csv_path = tmp_path / "small_dataset.csv"
        df.to_csv(csv_path)

        engine.config.dataset_path = str(csv_path)

        with pytest.raises(ValueError, match="incompleto"):
            engine.load_dataset()

    def test_run_backtest_requires_dataset(self, engine):
        """AC3: Backtest requer dataset carregado."""
        with pytest.raises(ValueError, match="Dataset nao carregado"):
            engine.run_backtest()

    def test_run_backtest_success(self, engine, sample_dataset):
        """AC3: Backtest roda e retorna 5 folds."""
        engine.config.dataset_path = sample_dataset
        engine.load_dataset()

        results = engine.run_backtest()

        assert len(results) == 5
        assert all(isinstance(r, BacktestMetrics) for r in results)
        assert all(r.total_trades > 0 for r in results)

    def test_metrics_calculated(self, engine, sample_dataset):
        """AC4: Métricas GATE 2 calculadas."""
        engine.config.dataset_path = sample_dataset
        engine.load_dataset()
        results = engine.run_backtest()

        for r in results:
            assert isinstance(r.sharpe_ratio, float)
            assert isinstance(r.win_rate, float)
            assert isinstance(r.max_drawdown, float)
            assert 0.0 <= r.win_rate <= 1.0
            assert 0.0 <= r.max_drawdown <= 1.0

    def test_cross_validation_stability(self, engine, sample_dataset):
        """AC5: Cross-val stability (std < 2pp)."""
        engine.config.dataset_path = sample_dataset
        engine.load_dataset()
        results = engine.run_backtest()

        sharpes = [r.sharpe_ratio for r in results]
        std_sharpe = np.std(sharpes)

        # Verificar que não é absurdamente instável
        assert std_sharpe < 2.0  # < 2pp de desvio

    def test_walk_forward_no_lookahead(self, engine, sample_dataset):
        """AC6: TimeSeriesSplit sem lookahead bias."""
        engine.config.dataset_path = sample_dataset
        engine.load_dataset()

        # Verificar que cada fold é sequencial (não há overlap)
        for train_idx, test_idx in engine.tscv.split(engine.dataset):
            assert max(train_idx) < min(test_idx), \
                "Lookahead bias detectado: train sobrepõe test"

    def test_save_results(self, engine, sample_dataset, tmp_path):
        """AC7: Relatório salvo em JSON."""
        engine.config.dataset_path = sample_dataset
        engine.config.output_path = str(tmp_path / "backtest")
        engine.load_dataset()
        engine.run_backtest()

        output_file = engine.save_results()

        assert Path(output_file).exists()
        assert output_file.endswith(".json")

        # Verificar conteúdo JSON
        import json
        with open(output_file, 'r') as f:
            data = json.load(f)
            assert 'summary' in data
            assert 'mean_sharpe' in data['summary']
            assert 'folds' in data
            assert len(data['folds']) == 5

    def test_get_results_summary(self, engine, sample_dataset):
        """Resultado summary contém metricas corretas."""
        engine.config.dataset_path = sample_dataset
        engine.load_dataset()
        engine.run_backtest()

        summary = engine.get_results_summary()

        assert 'mean_sharpe' in summary
        assert 'mean_win_rate' in summary
        assert 'mean_max_drawdown' in summary
        assert 'consistency_std' in summary
        assert 'total_folds' in summary
        assert summary['total_folds'] == 5


class TestMetricsCalculator:
    """Testes do MetricsCalculator."""

    @pytest.fixture
    def calc(self):
        """Fixture: calculador de metricas."""
        return MetricsCalculator()

    def test_calculator_initialization(self, calc):
        """Calculador inicializa corretamente."""
        assert calc.risk_free_rate == 0.04
        assert calc.trading_days == 252

    def test_sharpe_ratio_positive_returns(self, calc):
        """Sharpe ratio para retornos positivos constantes."""
        returns = np.array([0.01] * 252)  # 1% diário = ~252% anual
        sharpe = calc.sharpe_ratio(returns)

        # Com retornos constantes, desvio é minimo
        assert isinstance(sharpe, float)

    def test_sharpe_ratio_zero_variance(self, calc):
        """Sharpe é 0 se variancia é nula."""
        returns = np.array([0.0] * 100)
        sharpe = calc.sharpe_ratio(returns)

        assert sharpe == 0.0

    def test_sortino_ratio(self, calc):
        """Sortino ignora upside volatility."""
        returns = np.array([0.01] * 100 + [-0.02] * 10)  # Mostly positive
        sortino = calc.sortino_ratio(returns)

        assert isinstance(sortino, float)
        assert sortino > 0.0

    def test_max_drawdown(self, calc):
        """Max drawdown detecta pior redução."""
        equity = np.array([100, 120, 110, 90, 95, 100, 105])
        max_dd, start, end = calc.max_drawdown(equity)

        assert max_dd > 0.0
        assert start < end
        assert max_dd < 1.0  # Percentual

    def test_win_rate_all_wins(self, calc):
        """Win rate 100% para todos vencedores."""
        trades = [10, 20, 30, 40]
        win_rate = calc.win_rate(trades)

        assert win_rate == 1.0

    def test_win_rate_all_losses(self, calc):
        """Win rate 0% para todos perdedores."""
        trades = [-10, -20, -30, -40]
        win_rate = calc.win_rate(trades)

        assert win_rate == 0.0

    def test_win_rate_mixed(self, calc):
        """Win rate para mix de trades."""
        trades = [10, -20, 30, -40, 50]
        win_rate = calc.win_rate(trades)

        assert win_rate == 0.6  # 3/5 vencedores

    def test_profit_factor(self, calc):
        """Profit factor > 1 para estratégia lucrativa."""
        trades = [100, 120, -50, -30]  # Profit: 220, Loss: 80
        pf = calc.profit_factor(trades)

        assert pf == pytest.approx(220.0 / 80.0, rel=0.01)

    def test_expectancy(self, calc):
        """Expectancy = (WR% * AvgW) + (LR% * AvgL)."""
        trades = [100, 100, -50, -50]  # WR=50%, AvgW=100, AvgL=-50
        exp = calc.expectancy(trades)

        expected = (0.5 * 100) + (0.5 * -50)
        assert exp == pytest.approx(expected, rel=0.01)

    def test_recovery_factor(self, calc):
        """Recovery factor = profit / max_drawdown."""
        equity = np.array([100, 120, 110, 90, 95, 100, 105])
        rf = calc.recovery_factor(equity)

        assert isinstance(rf, float)
        assert rf > 0.0

    def test_hurst_exponent_range(self, calc):
        """Hurst exponent entre 0 e 1."""
        returns = np.random.randn(500)
        hurst = calc.hurst_exponent(returns, lags=100)

        assert 0.0 <= hurst <= 1.0

    def test_calculate_all_metrics(self, calc):
        """Calcula todas as metricas de uma vez."""
        pnl_trades = [10, -5, 20, -10, 15] * 50
        equity_curve = np.cumsum([0] + pnl_trades)
        daily_returns = np.random.randn(252) * 0.01
        # Criar Series com DatetimeIndex
        dates = pd.date_range('2024-01-01', periods=252, freq='D')
        returns_series = pd.Series(daily_returns, index=dates)

        metrics = calc.calculate_all_metrics(
            pnl_trades=pnl_trades,
            equity_curve=equity_curve,
            daily_returns=daily_returns,
            returns_series=returns_series
        )

        assert 'sharpe_ratio' in metrics
        assert 'sortino_ratio' in metrics
        assert 'max_drawdown' in metrics
        assert 'win_rate' in metrics
        assert 'profit_factor' in metrics
        assert 'expectancy' in metrics
        assert metrics['total_trades'] == len(pnl_trades)
