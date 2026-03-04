"""
Calculador de metricas para validacao P0-2.

Calcula metricas de performance: Sharpe, Win Rate, Drawdown, Sortino, etc.

Architecture: Domain Layer (DDD)
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Metricas de risco da estratégia."""

    max_drawdown: float
    avg_drawdown: float
    drawdown_duration: int
    calmar_ratio: float
    recovery_time: int


@dataclass
class ReturnMetrics:
    """Metricas de retorno da estratégia."""

    total_return: float
    annualized_return: float
    avg_daily_return: float
    std_daily_return: float
    skewness: float
    kurtosis: float


@dataclass
class TradeMetrics:
    """Metricas de trades (win rate, P&L, etc)."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    expectancy: float
    consecutive_wins: int
    consecutive_losses: int


class MetricsCalculator:
    """
    Calculador de metricas de performance para backtests.

    Calcula 15+ metricas financeiras:
    - Sharpe Ratio
    - Sortino Ratio
    - Max Drawdown + duração
    - Win Rate + P&L
    - Consistência mensal
    - Calmar Ratio
    - Recovery Factor
    - etc

    Attributes:
        risk_free_rate (float): Taxa livre de risco (default 4% a.a.)
        trading_days (int): Dias de trading por ano (252 dias)
    """

    def __init__(
        self,
        risk_free_rate: float = 0.04,
        trading_days: int = 252
    ) -> None:
        """
        Inicializa calculador de metricas.

        Args:
            risk_free_rate: Taxa livre de risco anual (default 4%)
            trading_days: Dias de trading por ano (default 252)
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days
        logger.debug(
            f"MetricsCalculator: rf={risk_free_rate:.2%}, "
            f"trading_days={trading_days}"
        )

    def sharpe_ratio(
        self,
        returns: np.ndarray,
        periods_per_year: Optional[int] = None
    ) -> float:
        """
        Calcula Sharpe Ratio.

        Formula:
            Sharpe = (E[R] - Rf) / std(R) * sqrt(T)

        Args:
            returns: Array de retornos (log-returns ou P&L)
            periods_per_year: Períodos por ano (default 252)

        Returns:
            Sharpe ratio anualizado
        """
        if len(returns) < 2:
            return 0.0

        periods = periods_per_year or self.trading_days
        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0 or np.isnan(std_return) or np.isinf(std_return):
            return 0.0

        daily_rf = self.risk_free_rate / periods
        sharpe = (avg_return - daily_rf) / std_return * np.sqrt(periods)

        return float(np.nan_to_num(sharpe, nan=0.0, posinf=0.0, neginf=0.0))

    def sortino_ratio(
        self,
        returns: np.ndarray,
        target_return: float = 0.0,
        periods_per_year: Optional[int] = None
    ) -> float:
        """
        Calcula Sortino Ratio.

        Como Sharpe, mas considera apenas desvio de downside.

        Formula:
            Sortino = (E[R] - T) / std(R_negative) * sqrt(T)

        Args:
            returns: Array de retornos
            target_return: Retorno alvo (default 0%)
            periods_per_year: Períodos por ano

        Returns:
            Sortino ratio anualizado
        """
        if len(returns) < 2:
            return 0.0

        periods = periods_per_year or self.trading_days
        excess_returns = returns - target_return
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0:
            return float('inf')

        downside_std = np.std(downside_returns, ddof=1)

        if downside_std == 0:
            return 0.0

        avg_return = np.mean(returns)
        daily_target = target_return / periods
        sortino = (avg_return - daily_target) / downside_std * np.sqrt(periods)

        return float(sortino)

    def max_drawdown(
        self,
        equity_curve: np.ndarray
    ) -> Tuple[float, int, int]:
        """
        Calcula máxima redução de patrimônio.

        Identifica pior redução percentual entre pico e vale.

        Args:
            equity_curve: Serie temporal de patrimonio

        Returns:
            (max_drawdown_pct, start_idx, end_idx)
        """
        if len(equity_curve) < 2:
            return 0.0, 0, 0

        cumulative = np.array(equity_curve)
        running_max = np.maximum.accumulate(cumulative)

        drawdown = (cumulative - running_max) / (running_max + 1e-8)
        max_dd = np.min(drawdown)
        max_dd_idx = np.argmin(drawdown)

        # Encontrar inicio do drawdown
        start_idx = np.argmax(running_max[:max_dd_idx + 1])

        return float(abs(max_dd)), int(start_idx), int(max_dd_idx)

    def avg_drawdown(
        self,
        equity_curve: np.ndarray
    ) -> float:
        """Calcula redução média (não só a máxima)."""
        if len(equity_curve) < 2:
            return 0.0

        cumulative = np.array(equity_curve)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / (running_max + 1e-8)
        negative_dd = drawdowns[drawdowns < 0]

        if len(negative_dd) == 0:
            return 0.0

        return float(np.mean(np.abs(negative_dd)))

    def calmar_ratio(
        self,
        returns: np.ndarray,
        equity_curve: np.ndarray
    ) -> float:
        """
        Calcula Calmar Ratio.

        Formula: Calmar = annual_return / max_drawdown

        Indica retorno por unidade de risco de drawdown.

        Args:
            returns: Retornos
            equity_curve: Patrimonio

        Returns:
            Calmar ratio
        """
        if len(returns) < 252:
            return 0.0

        annualized = np.mean(returns) * self.trading_days
        max_dd, _, _ = self.max_drawdown(equity_curve)

        if max_dd == 0:
            return 0.0

        calmar = annualized / max_dd

        return float(calmar)

    def win_rate(self, trades: List[float]) -> float:
        """
        Calcula taxa de vitoria.

        Args:
            trades: Lista de P&L de trades (+/-)

        Returns:
            Percentual de trades vencedores (0.0 a 1.0)
        """
        if len(trades) == 0:
            return 0.0

        winning = sum(1 for t in trades if t > 0)
        return float(winning / len(trades))

    def profit_factor(self, trades: List[float]) -> float:
        """
        Calcula fator lucro.

        Formula: Profit Factor = gross_profit / gross_loss

        Args:
            trades: Lista de P&L de trades

        Returns:
            Profit factor (> 1.0 é lucrativo)
        """
        if len(trades) == 0:
            return 0.0

        gross_profit = sum(t for t in trades if t > 0)
        gross_loss = abs(sum(t for t in trades if t < 0))

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return float(gross_profit / gross_loss)

    def expectancy(self, trades: List[float]) -> float:
        """
        Calcula valor esperado por trade.

        Formula: E = (Win% * AvgW) + (Loss% * AvgL)

        Args:
            trades: Lista de P&L de trades

        Returns:
            Valor esperado por trade
        """
        if len(trades) == 0:
            return 0.0

        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t < 0]

        win_rate = len(wins) / len(trades)
        loss_rate = len(losses) / len(trades)

        avg_win = np.mean(wins) if wins else 0.0
        avg_loss = np.mean(losses) if losses else 0.0

        expectancy = (win_rate * avg_win) + (loss_rate * avg_loss)

        return float(expectancy)

    def monthly_consistency(
        self,
        returns_series: pd.Series
    ) -> float:
        """
        Calcula desvio padrao dos retornos mensais.

        Métrica de consistência: baixo σ = estratégia previsível.

        Args:
            returns_series: Serie temporal de retornos (Index: datas)

        Returns:
            Desvio padrão dos retornos mensais
        """
        if len(returns_series) < 20:
            return 0.0

        monthly = returns_series.resample('ME').sum()

        if len(monthly) < 2:
            return 0.0

        return float(np.std(monthly, ddof=1))

    def recovery_factor(
        self,
        equity_curve: np.ndarray
    ) -> float:
        """
        Calcula Recovery Factor.

        Formula: RF = total_profit / max_drawdown

        Indica quanto profit recupera a pior redução.

        Args:
            equity_curve: Patrimonio

        Returns:
            Recovery factor
        """
        if len(equity_curve) < 2:
            return 0.0

        total_profit = equity_curve[-1] - equity_curve[0]
        max_dd, _, _ = self.max_drawdown(equity_curve)

        if max_dd == 0:
            return float('inf') if total_profit > 0 else 0.0

        recovery = total_profit / (max_dd * 100)

        return float(recovery)

    def hurst_exponent(
        self,
        returns: np.ndarray,
        lags: int = 100
    ) -> float:
        """
        Calcula Expoente de Hurst.

        Indica se serie é mean-reverting (<0.5), random (=0.5), ou trending (>0.5).

        Args:
            returns: Retornos
            lags: Número de lags para análise

        Returns:
            Expoente de Hurst (0.0 a 1.0)
        """
        if len(returns) < lags * 2:
            return 0.5

        cumsum = np.cumsum(returns)
        tau = []

        for lag in range(1, min(lags, len(returns) // 2)):
            # Separar em chunks
            chunks = len(cumsum) // lag
            if chunks < 2:
                continue

            variance = []
            for i in range(chunks):
                chunk = cumsum[i * lag:(i + 1) * lag]
                detrended = chunk - np.linspace(chunk[0], chunk[-1], len(chunk))
                variance.append(np.sum(detrended ** 2))

            if variance:
                tau.append(np.sqrt(np.mean(variance)))

        if len(tau) < 2:
            return 0.5

        # Linear regression em log-log
        try:
            log_lags = np.log(range(1, len(tau) + 1))
            log_tau = np.log(tau)
            hurst = np.polyfit(log_lags, log_tau, 1)[0]
            hurst = float(np.clip(hurst, 0.0, 1.0))
            return hurst if not np.isnan(hurst) else 0.5
        except Exception:
            return 0.5

    def calculate_all_metrics(
        self,
        pnl_trades: List[float],
        equity_curve: np.ndarray,
        daily_returns: np.ndarray,
        returns_series: Optional[pd.Series] = None
    ) -> Dict:
        """
        Calcula TODAS as metricas de uma vez.

        Args:
            pnl_trades: P&L de cada trade
            equity_curve: Patrimonio ao longo do tempo
            daily_returns: Retornos diarios
            returns_series: Serie pandas (para consistency mensal)

        Returns:
            Dict com todas as metricas calculadas
        """
        if returns_series is None:
            returns_series = pd.Series(daily_returns)

        max_dd, start_idx, end_idx = self.max_drawdown(equity_curve)

        metrics = {
            # Return metrics
            'total_return': float(np.sum(pnl_trades)),
            'annualized_return': float(np.mean(daily_returns) * self.trading_days),
            'avg_daily_return': float(np.mean(daily_returns)),
            'std_daily_return': float(np.std(daily_returns, ddof=1)),
            'skewness': float(pd.Series(daily_returns).skew()),
            'kurtosis': float(pd.Series(daily_returns).kurtosis()),

            # Risk metrics
            'max_drawdown': max_dd,
            'avg_drawdown': self.avg_drawdown(equity_curve),
            'drawdown_duration': int(end_idx - start_idx),
            'calmar_ratio': self.calmar_ratio(daily_returns, equity_curve),

            # Trade metrics
            'total_trades': len(pnl_trades),
            'winning_trades': sum(1 for t in pnl_trades if t > 0),
            'losing_trades': sum(1 for t in pnl_trades if t < 0),
            'win_rate': self.win_rate(pnl_trades),
            'avg_win': self._avg_win(pnl_trades),
            'avg_loss': self._avg_loss(pnl_trades),
            'profit_factor': self.profit_factor(pnl_trades),
            'expectancy': self.expectancy(pnl_trades),

            # Ratio metrics
            'sharpe_ratio': self.sharpe_ratio(daily_returns),
            'sortino_ratio': self.sortino_ratio(daily_returns),
            'recovery_factor': self.recovery_factor(equity_curve),

            # Consistency
            'monthly_std': self.monthly_consistency(returns_series),
            'hurst_exponent': self.hurst_exponent(daily_returns),
        }

        return metrics

    @staticmethod
    def _avg_win(trades: List[float]) -> float:
        """Retorna ganho médio."""
        wins = [t for t in trades if t > 0]
        return float(np.mean(wins)) if wins else 0.0

    @staticmethod
    def _avg_loss(trades: List[float]) -> float:
        """Retorna perda média."""
        losses = [t for t in trades if t < 0]
        return float(np.mean(losses)) if losses else 0.0
