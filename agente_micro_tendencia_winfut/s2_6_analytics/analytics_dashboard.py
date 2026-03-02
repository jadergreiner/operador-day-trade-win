"""
Analytics Dashboard - S2-6

Dashboard em tempo real com:
- Metricas de performance
- Sinais em progresso
- Intervencoes manuais
- Risco monitor
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from collections import defaultdict

from .config import AnalyticsConfig
from .models import (
    Signal,
    PerformanceMetrics,
    SignalStatus,
    InterventionType,
)
from .manual_override_logger import ManualOverrideLogger
from .trader_feedback_api import TraderFeedbackAPI


class AnalyticsDashboard:
    """Dashboard central de analytics"""

    def __init__(self, config: Optional[AnalyticsConfig] = None) -> None:
        """
        Inicializa o dashboard

        Args:
            config: Configuracao do modulo
        """
        self.config = config or AnalyticsConfig()
        self.override_logger = ManualOverrideLogger(config)
        self.feedback_api = TraderFeedbackAPI(config)

        # Armazenamento de historico
        self.signal_history: Dict[str, Signal] = {}
        self.performance_cache: Dict[str, PerformanceMetrics] = {}

        # Metricas atuais
        self.current_open_positions: Dict[str, Signal] = {}
        self.daily_stats: Dict[str, Any] = self._init_daily_stats()

    def _init_daily_stats(self) -> Dict[str, Any]:
        """Inicializa estatisticas diarias"""
        return {
            "date": datetime.now().date(),
            "total_signals": 0,
            "approved": 0,
            "rejected": 0,
            "executed": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl_points": 0.0,
            "max_drawdown": 0.0,
            "manual_interventions": 0,
        }

    def register_signal(self, signal: Signal) -> None:
        """
        Registra um novo sinal

        Args:
            signal: Sinal a registrar
        """
        self.signal_history[signal.signal_id] = signal
        self.daily_stats["total_signals"] += 1

        # Submeter para aprovacao do trader
        self.feedback_api.submit_signal_for_approval(
            signal,
            timeout_seconds=self.config.api_timeout_seconds,
        )

    def execute_signal(
        self,
        signal_id: str,
        execution_price: float,
    ) -> Optional[Signal]:
        """
        Executa um sinal aprovado

        Args:
            signal_id: ID do sinal
            execution_price: Preco de execucao

        Returns:
            Sinal executado ou None
        """
        if signal_id not in self.signal_history:
            return None

        signal = self.signal_history[signal_id]
        signal.status = SignalStatus.EXECUTED
        signal.execution_price = execution_price
        signal.execution_timestamp = datetime.now()

        # Adicionar a posicoes abertas
        self.current_open_positions[signal_id] = signal
        self.daily_stats["executed"] += 1

        return signal

    def close_position(
        self,
        signal_id: str,
        close_price: float,
    ) -> bool:
        """
        Fecha uma posicao aberta

        Args:
            signal_id: ID do sinal
            close_price: Preco de fechamento

        Returns:
            True se posicao foi fechada
        """
        if signal_id not in self.current_open_positions:
            return False

        signal = self.current_open_positions.pop(signal_id)

        # Calcular P&L
        if signal.direction == "BULLISH":
            pnl_points = close_price - signal.execution_price
        else:
            pnl_points = signal.execution_price - close_price

        pnl_percentage = (pnl_points / signal.execution_price) * 100

        signal.pnl_points = pnl_points
        signal.pnl_percentage = pnl_percentage

        # Atualizar stats
        self.daily_stats["total_pnl_points"] += pnl_points

        if pnl_points > 0:
            self.daily_stats["winning_trades"] += 1
        else:
            self.daily_stats["losing_trades"] += 1

        return True

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Obtem dados completos do dashboard

        Returns:
            Dicionario com todos dados para visualizacao
        """
        pending_signals = self.feedback_api.get_pending_signals()
        connected_traders = self.feedback_api.get_connected_traders()

        # Calcular metricas
        total_trades = (
            self.daily_stats["winning_trades"] + self.daily_stats["losing_trades"]
        )
        win_rate = (
            self.daily_stats["winning_trades"] / total_trades * 100
            if total_trades > 0
            else 0.0
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "RUNNING",

            # Sinais
            "signals": {
                "pending": len(pending_signals),
                "open_positions": len(self.current_open_positions),
                "pending_details": [
                    {
                        "id": s.signal_id,
                        "direction": s.direction,
                        "confidence": s.confidence_score,
                        "smc_confluence": s.smc_confluence_score,
                    }
                    for s in pending_signals.values()
                ],
            },

            # Performance
            "performance": {
                "total_signals_today": self.daily_stats["total_signals"],
                "executed_signals": self.daily_stats["executed"],
                "approved": self.daily_stats["approved"],
                "rejected": self.daily_stats["rejected"],
                "winning_trades": self.daily_stats["winning_trades"],
                "losing_trades": self.daily_stats["losing_trades"],
                "win_rate_pct": win_rate,
                "total_pnl_points": self.daily_stats["total_pnl_points"],
            },

            # Risco
            "risk": {
                "open_positions_count": len(self.current_open_positions),
                "max_drawdown_pct": self.daily_stats["max_drawdown"],
                "current_exposure": self._calculate_current_exposure(),
            },

            # Intervencoes
            "interventions": {
                "manual_overrides": self.daily_stats["manual_interventions"],
                "override_stats": self.override_logger.get_override_statistics(),
            },

            # Conectividade
            "connectivity": {
                "connected_traders": len(connected_traders),
                "trader_ids": list(connected_traders),
            },
        }

    def _calculate_current_exposure(self) -> Dict[str, Any]:
        """
        Calcula exposicao atual de mercado

        Returns:
            Dicionario com dados de exposicao
        """
        bullish_positions = sum(
            1 for s in self.current_open_positions.values()
            if s.direction == "BULLISH"
        )
        bearish_positions = sum(
            1 for s in self.current_open_positions.values()
            if s.direction == "BEARISH"
        )

        return {
            "bullish": bullish_positions,
            "bearish": bearish_positions,
            "total": len(self.current_open_positions),
            "net_exposure": bullish_positions - bearish_positions,
        }

    def get_trader_summary(self, trader_id: str) -> Dict[str, Any]:
        """
        Obtem sumario de performance de um trader

        Args:
            trader_id: ID do trader

        Returns:
            Dicionario com dados do trader
        """
        override_stats = self.override_logger.get_override_statistics(
            trader_id=trader_id
        )

        return {
            "trader_id": trader_id,
            "is_connected": trader_id in self.feedback_api.get_connected_traders(),
            "interventions": override_stats["total_overrides"],
            "by_type": override_stats.get("by_type", {}),
            "timestamp": datetime.now().isoformat(),
        }

    def get_performance_report(
        self,
        days: int = 1,
    ) -> PerformanceMetrics:
        """
        Gera relatorio de performance

        Args:
            days: Numero de dias a relatar

        Returns:
            Metricas de performance agregadas
        """
        now = datetime.now()
        start_date = now - timedelta(days=days)

        # Agregar dados do periodo
        metrics = PerformanceMetrics(
            period_start=start_date,
            period_end=now,
            total_signals=self.daily_stats["total_signals"],
            executed_signals=self.daily_stats["executed"],
            winning_trades=self.daily_stats["winning_trades"],
            losing_trades=self.daily_stats["losing_trades"],
            total_pnl_points=self.daily_stats["total_pnl_points"],
            manual_interventions=self.daily_stats["manual_interventions"],
        )

        # Calcular metricas derivadas
        if metrics.total_signals > 0:
            metrics.win_rate = (
                metrics.winning_trades / metrics.total_signals
            )

        if metrics.winning_trades > 0:
            metrics.avg_profit_per_trade = (
                metrics.total_pnl_points / metrics.winning_trades
            )

        if metrics.losing_trades > 0:
            metrics.avg_loss_per_trade = (
                -1 * metrics.total_pnl_points / metrics.losing_trades
            )

        if metrics.avg_loss_per_trade != 0:
            metrics.profit_factor = (
                metrics.avg_profit_per_trade / abs(metrics.avg_loss_per_trade)
            )

        return metrics
