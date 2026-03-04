"""
Modulo de relatorios para P0-2 backtest.

Exporta componentes de reporting e visualizacoes.
"""

from src.infrastructure.reports.backtest_reporter import BacktestReporter, ReportConfig
from src.infrastructure.reports.backtest_visualizer import BacktestVisualizer, ChartConfig

__all__ = [
    "BacktestReporter",
    "BacktestVisualizer",
]
