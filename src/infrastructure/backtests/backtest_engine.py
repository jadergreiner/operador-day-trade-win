"""
Engine de backtest para validacao ML - P0-2.

Simula 252 dias de trading com dataset historico.
Implementa cross-validation 5-fold sem lookahead bias.

Architecture: Data Layer (DDD)
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

from src.application.services.sl_tp_ab_backtest import CostProfile, get_cost_profile
from src.infrastructure.backtests.metrics_calculator import MetricsCalculator

logger = logging.getLogger(__name__)


@dataclass
class BacktestMetrics:
    """Metricas de um fold de backtest."""

    fold_id: int
    sharpe_ratio: float
    win_rate: float
    max_drawdown: float
    total_trades: int
    winning_trades: int
    avg_return: float
    pnl_total: float
    pnl_monthly_std: float
    sortino_ratio: float
    recovery_factor: float
    profit_factor: float
    expectancy: float


@dataclass
class BacktestConfig:
    """Configuracao para execucao de backtest."""

    dataset_path: str = "data/training_dataset.csv"
    lookback_period: int = 252
    test_split: float = 0.2
    cv_folds: int = 5
    features_count: int = 24
    output_path: str = "data/backtest"
    model_path: Optional[str] = None
    random_seed: int = 42
    min_confidence: float = 0.55
    cost_profile_name: str = "realista"


class BacktestEngine:
    """
    Engine de backtest para validacao de modelo ML.

    - Carrega dataset historico (252 dias)
    - Implementa 5-fold cross-validation (TimeSeriesSplit)
    - Calcula metricas GATE 2 (Sharpe, Win Rate, Drawdown, Consistency)
    - Persiste resultados em JSON + SQLite
    - Sem lookahead bias (data futura nao vis entre treino/teste)

    Attributes:
        config (BacktestConfig): Configuracao do backtest
        dataset (pd.DataFrame): Dataset carregado (252 dias, 24 features)
        tscv (TimeSeriesSplit): Cross-validator temporal
        results (List[BacktestMetrics]): Metricas de cada fold
    """

    def __init__(self, config: Optional[BacktestConfig] = None) -> None:
        """
        Inicializa engine de backtest.

        Args:
            config: Configuracao (usa defaults se None)

        Raises:
            FileNotFoundError: Se dataset nao encontrado
        """
        self.config = config or BacktestConfig()
        self.dataset: Optional[pd.DataFrame] = None
        self.tscv = TimeSeriesSplit(n_splits=self.config.cv_folds)
        self.results: List[BacktestMetrics] = []
        self.fold_trades: Dict[int, List[Dict]] = {}
        self.equity_curve_compact: List[float] = []
        self.metrics_calculator = MetricsCalculator()
        self.cost_profile = get_cost_profile(self.config.cost_profile_name)

        logger.info(
            f"BacktestEngine inicializado: "
            f"lookback={self.config.lookback_period}, "
            f"folds={self.config.cv_folds}"
        )

    def load_dataset(self) -> pd.DataFrame:
        """
        Carrega dataset historico.

        Formato esperado:
        - 1.000+ amostras
        - 24 features (volatility, momentum, patterns)
        - Coluna 'label' com 0 (SKIP) ou 1 (BUY)
        - Index temporal (date)

        Returns:
            DataFrame carregado com 252 dias

        Raises:
            FileNotFoundError: Dataset nao encontrado
            ValueError: Dataset incompleto (< 1000 samples)
        """
        dataset_path = Path(self.config.dataset_path)

        if not dataset_path.exists():
            raise FileNotFoundError(
                f"Dataset nao encontrado em {dataset_path}"
            )

        try:
            df = pd.read_csv(dataset_path, index_col=0, parse_dates=True)
            logger.info(f"Dataset carregado: {len(df)} samples, "
                       f"{df.shape[1]} features")

            if len(df) < 1000:
                raise ValueError(
                    f"Dataset incompleto: {len(df)} < 1000 samples"
                )

            if 'label' not in df.columns:
                raise ValueError(
                    "Dataset deve ter coluna 'label' (0=SKIP, 1=BUY)"
                )
            if 'close' not in df.columns:
                raise ValueError(
                    "Dataset deve ter coluna 'close' (preco de referencia)"
                )

            self.dataset = df.sort_index()
            return self.dataset

        except Exception as e:
            logger.error(f"Erro ao carregar dataset: {e}")
            raise

    def run_backtest(self) -> List[BacktestMetrics]:
        """
        Executa backtest completo com 5-fold cross-validation.

        Fluxo:
        1. Valida dataset carregado
        2. Para cada fold (TimeSeriesSplit):
           - Treina em dados historicos
           - Testa em dados futuros (sem lookahead)
           - Calcula metricas (Sharpe, Win Rate, etc)
        3. Persiste resultados por fold

        Returns:
            Lista com metricas de cada fold

        Raises:
            ValueError: Se dataset nao esta carregado
        """
        if self.dataset is None:
            raise ValueError(
                "Dataset nao carregado. Execute load_dataset() primeiro"
            )

        logger.info("Iniciando backtest 5-fold cross-validation...")
        self.results = []
        self.fold_trades = {}
        all_trade_returns: List[float] = []

        fold_id = 0
        for train_idx, test_idx in self.tscv.split(self.dataset):
            logger.info(f"  Fold {fold_id + 1}/5: "
                       f"treino={len(train_idx)}, "
                       f"teste={len(test_idx)}")

            train_data = self.dataset.iloc[train_idx]
            test_data = self.dataset.iloc[test_idx]

            metrics, trade_returns = self._simulate_fold(
                fold_id=fold_id,
                train_data=train_data,
                test_data=test_data,
            )

            self.results.append(metrics)
            all_trade_returns.extend(trade_returns)
            fold_id += 1

        logger.info(
            f"Backtest concluido: {len(self.results)} folds, "
            f"media Sharpe = {self.get_mean_sharpe():.2f}"
        )

        self.equity_curve_compact = self._build_compact_equity_curve(all_trade_returns)

        return self.results

    def _simulate_fold(
        self,
        fold_id: int,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
    ) -> Tuple[BacktestMetrics, List[float]]:
        """
        Simula um fold de backtest.

        Algoritmo simplificado:
        1. Treina classifier em train_data (StandardScaler + LogisticRegression)
        2. Prediz em test_data
        3. Simula trades baseado em probas (long-only)
        4. Calcula metricas (P&L, Win Rate, Sharpe, etc)

        Args:
            fold_id: ID do fold (0-4)
            train_data: Dados de treino
            test_data: Dados de teste

        Returns:
            Tuple[BacktestMetrics, trade_returns]
        """
        feature_cols = self._select_feature_columns(train_data)
        X_train = train_data[feature_cols].to_numpy(dtype=float)
        y_train = train_data["label"].to_numpy(dtype=int)

        X_test = test_data[feature_cols].to_numpy(dtype=float)
        close_test = test_data["close"].to_numpy(dtype=float)
        timestamps = test_data.index.to_list()

        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=self.config.random_seed,
            ),
        )
        model.fit(X_train, y_train)
        probas = model.predict_proba(X_test)[:, 1]

        cost_points = self._compute_cost_points(self.cost_profile)
        trades: List[Dict[str, Any]] = []
        trade_returns: List[float] = []
        trade_pnls: List[float] = []
        trade_dates: List[pd.Timestamp] = []

        for i in range(len(close_test) - 1):
            if probas[i] < self.config.min_confidence:
                continue

            entry_price = close_test[i]
            exit_price = close_test[i + 1]
            if entry_price == 0:
                continue

            gross_points = exit_price - entry_price
            net_points = gross_points - cost_points
            net_return = net_points / entry_price
            is_win = net_points > 0

            trades.append(
                {
                    "date": timestamps[i],
                    "entry_price": float(entry_price),
                    "exit_price": float(exit_price),
                    "pnl_points": float(net_points),
                    "pnl_return": float(net_return),
                    "is_win": is_win,
                    "confidence": float(probas[i]),
                }
            )
            trade_returns.append(float(net_return))
            trade_pnls.append(float(net_points))
            trade_dates.append(pd.Timestamp(timestamps[i]))

        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t["is_win"])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        pnl_total = float(np.sum(trade_pnls)) if trade_pnls else 0.0
        avg_return = pnl_total / total_trades if total_trades > 0 else 0.0

        equity_curve = self._build_equity_curve(trade_returns)
        returns_array = np.array(trade_returns, dtype=float)
        returns_series = (
            pd.Series(trade_returns, index=pd.DatetimeIndex(trade_dates))
            if trade_returns
            else pd.Series(dtype=float)
        )
        metrics = self.metrics_calculator.calculate_all_metrics(
            pnl_trades=trade_pnls,
            equity_curve=np.array(equity_curve, dtype=float),
            daily_returns=returns_array,
            returns_series=returns_series if not returns_series.empty else None,
        )

        sharpe = float(metrics.get("sharpe_ratio", 0.0))
        sortino = float(metrics.get("sortino_ratio", 0.0))
        max_drawdown = float(metrics.get("max_drawdown", 0.0))
        pnl_monthly_std = float(metrics.get("monthly_std", 0.0))
        recovery = float(metrics.get("recovery_factor", 0.0))
        profit_factor = float(metrics.get("profit_factor", 0.0))
        expectancy = float(metrics.get("expectancy", 0.0))

        metrics = BacktestMetrics(
            fold_id=fold_id,
            sharpe_ratio=sharpe,
            win_rate=win_rate,
            max_drawdown=abs(max_drawdown),
            total_trades=total_trades,
            winning_trades=winning_trades,
            avg_return=avg_return,
            pnl_total=pnl_total,
            pnl_monthly_std=pnl_monthly_std,
            sortino_ratio=sortino,
            recovery_factor=recovery,
            profit_factor=profit_factor,
            expectancy=expectancy,
        )

        self.fold_trades[fold_id] = trades

        logger.debug(
            f"  Fold {fold_id}: Sharpe={sharpe:.2f}, "
            f"WR={win_rate:.1%}, DD={max_drawdown:.1%}"
        )

        return metrics, trade_returns

    def _select_feature_columns(self, df: pd.DataFrame) -> List[str]:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = [c for c in numeric_cols if c not in {"label", "close"}]
        if not feature_cols:
            raise ValueError("Dataset sem features numéricas válidas")
        return feature_cols

    @staticmethod
    def _compute_cost_points(cost_profile: CostProfile) -> float:
        fixed_brl = (cost_profile.fees_per_side_brl + cost_profile.commission_per_side_brl) * 2
        fixed_pts = fixed_brl / cost_profile.point_value_brl
        slippage_pts = cost_profile.slippage_points_per_side * 2
        return float(fixed_pts + slippage_pts)

    @staticmethod
    def _build_equity_curve(returns: List[float]) -> List[float]:
        equity = 1.0
        curve = [equity]
        for r in returns:
            equity *= (1.0 + r)
            curve.append(float(equity))
        return curve

    def _build_compact_equity_curve(self, returns: List[float]) -> List[float]:
        curve = self._build_equity_curve(returns)
        if len(curve) <= 200:
            return curve
        # Amostrar no maximo 200 pontos para manter JSON compacto
        step = max(1, len(curve) // 200)
        sampled = curve[::step]
        if sampled[-1] != curve[-1]:
            sampled.append(curve[-1])
        return sampled

    def get_mean_sharpe(self) -> float:
        """Retorna Sharpe medio entre folds."""
        if not self.results:
            return 0.0
        return np.mean([r.sharpe_ratio for r in self.results])

    def get_mean_win_rate(self) -> float:
        """Retorna Win Rate média entre folds."""
        if not self.results:
            return 0.0
        return np.mean([r.win_rate for r in self.results])

    def get_mean_max_drawdown(self) -> float:
        """Retorna Max Drawdown medio entre folds."""
        if not self.results:
            return 0.0
        return np.mean([r.max_drawdown for r in self.results])

    def get_consistency_std(self) -> float:
        """Retorna desvio padrao da consistencia mensal."""
        if not self.results:
            return 0.0
        return np.std([r.pnl_monthly_std for r in self.results])

    def save_results(self, output_path: Optional[str] = None) -> str:
        """
        Persiste resultados do backtest em JSON.

        Formato:
        {
            "summary": {
                "mean_sharpe": 1.2,
                "mean_win_rate": 0.62,
                "mean_max_drawdown": 0.098,
                "consistency_std": 0.28,
                "total_folds": 5,
                "total_trades": 123,
                "mean_pnl": 45.6
            },
            "folds": [...]
        }

        Args:
            output_path: Caminho para salvar (usa config se None)

        Returns:
            Caminho do arquivo salvo
        """
        output_path = output_path or self.config.output_path
        output_path_obj = Path(output_path)

        # Suporta tanto "diretorio" quanto "arquivo .json" como destino.
        if output_path_obj.suffix.lower() == ".json":
            # Remedia bug legado: caminho .json salvo como diretório.
            if output_path_obj.exists() and output_path_obj.is_dir():
                legacy_dir = output_path_obj.parent / (
                    f"{output_path_obj.name}_legacy_dir_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                output_path_obj.replace(legacy_dir)
                logger.warning(
                    "Diretorio legado em caminho .json movido para %s",
                    legacy_dir
                )
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            output_file = output_path_obj
        else:
            output_path_obj.mkdir(parents=True, exist_ok=True)
            output_file = output_path_obj / "backtest_results.json"

        results_dict = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "mean_sharpe": float(self.get_mean_sharpe()),
                "mean_win_rate": float(self.get_mean_win_rate()),
                "mean_max_drawdown": float(self.get_mean_max_drawdown()),
                "consistency_std": float(self.get_consistency_std()),
                # Campo legado para compatibilidade com consumidores antigos.
                "mean_monthly_consistency": float(self.get_consistency_std()),
                "total_folds": len(self.results),
                "total_trades": sum(r.total_trades for r in self.results),
                "mean_pnl": sum(r.pnl_total for r in self.results) / len(self.results) if self.results else 0.0,
                "total_pnl": sum(r.pnl_total for r in self.results),
                "mean_sortino_ratio": float(np.mean([r.sortino_ratio for r in self.results])) if self.results else 0.0,
                "mean_profit_factor": float(np.mean([r.profit_factor for r in self.results])) if self.results else 0.0,
                "mean_recovery_factor": float(np.mean([r.recovery_factor for r in self.results])) if self.results else 0.0,
                "mean_expectancy": float(np.mean([r.expectancy for r in self.results])) if self.results else 0.0,
                "min_confidence": self.config.min_confidence,
                "hold_period_bars": 1,
                "trade_count": sum(r.total_trades for r in self.results),
                "mean_return_per_trade": float(np.mean([r.avg_return for r in self.results])) if self.results else 0.0,
                "cost_profile": asdict(self.cost_profile),
                "equity_curve": self.equity_curve_compact,
            },
            "folds": [asdict(r) for r in self.results],
        }

        with open(output_file, 'w') as f:
            json.dump(results_dict, f, indent=2)

        logger.info(f"Resultados salvos em {output_file}")
        return str(output_file)

    def get_results_summary(self) -> Dict:
        """Retorna sumario dos resultados."""
        return {
            "mean_sharpe": self.get_mean_sharpe(),
            "mean_win_rate": self.get_mean_win_rate(),
            "mean_max_drawdown": self.get_mean_max_drawdown(),
            "consistency_std": self.get_consistency_std(),
            "total_folds": len(self.results),
            "total_trades": sum(r.total_trades for r in self.results),
            "timestamp": datetime.now().isoformat(),
        }
