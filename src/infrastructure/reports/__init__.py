"""
Modulo de relatorios para P0-2 backtest.

Exporta componentes de reporting e visualizacoes.
"""

from src.infrastructure.reports.backtest_reporter import BacktestReporter
from src.infrastructure.reports.visualizations import BacktestVisualizer

__all__ = [
    "BacktestReporter",
    "BacktestVisualizer",
]
