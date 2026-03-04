"""
Modulo de backtesting para validacao P0-2.

Exporta componentes principais para backtest ML.
"""

from src.infrastructure.backtests.backtest_engine import BacktestEngine
from src.infrastructure.backtests.metrics_calculator import MetricsCalculator

__all__ = [
    "BacktestEngine",
    "MetricsCalculator",
]
