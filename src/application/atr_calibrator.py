"""
Calibrador Dinâmico de ATR (Average True Range)

Otimiza detecção de volatilidade adaptativa em múltiplos períodos
para melhorar stop-loss/take-profit em tempo real.

Módulo: S2-2 (Sprint 2 - Implementação obrigatória)
Issue: https://github.com/jadergreiner/operador-day-trade-win/issues/21
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
import logging

logger = logging.getLogger(__name__)


class ATRDynamicCalibrator:
    """
    Calibrador dinâmico de ATR com clustering de volatilidade.

    Adapta automaticamente o ATR padrão (14) para múltiplos períodos
    baseado em padrões de volatilidade observados no histórico.

    Atributos:
        periods: Lista de períodos a calcular (padrão: [5, 10, 14, 20, 28])
        min_multiplier: Limite inferior de ajuste (padrão: 0.5)
        max_multiplier: Limite superior de ajuste (padrão: 2.0)
        n_clusters: Número de clusters para K-means (padrão: 3)
        min_history: Mínimo de velas para calibração (padrão: 50)
    """

    def __init__(
        self,
        periods: Optional[List[int]] = None,
        min_multiplier: float = 0.5,
        max_multiplier: float = 2.0,
        n_clusters: int = 3,
        min_history: int = 50,
    ):
        """
        Inicializa o calibrador ATR.

        Args:
            periods: Períodos a calcular. Padrão: [5, 10, 14, 20, 28]
            min_multiplier: Mínimo multiplicador (padrão: 0.5x)
            max_multiplier: Máximo multiplicador (padrão: 2.0x)
            n_clusters: Clusters para K-means (padrão: 3 = low/mid/high volatilidade)
            min_history: Mínimo histórico necessário (padrão: 50 velas)
        """
        self.periods = periods or [5, 10, 14, 20, 28]
        self.min_multiplier = min_multiplier
        self.max_multiplier = max_multiplier
        self.n_clusters = n_clusters
        self.min_history = min_history

        logger.info(
            f"ATRDynamicCalibrator initialized with periods={self.periods}, "
            f"bounds=[{self.min_multiplier}x, {self.max_multiplier}x]"
        )

    def _calculate_tr(self, ohlc: pd.DataFrame) -> pd.Series:
        """
        Calcula True Range.

        True Range = max(
            H - L,
            abs(H - Close[-1]),
            abs(L - Close[-1])
        )

        Args:
            ohlc: DataFrame com colunas 'High', 'Low', 'Close'

        Returns:
            Series com True Range para cada vela
        """
        high = ohlc["High"].values
        low = ohlc["Low"].values
        close = ohlc["Close"].values

        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))

        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        return pd.Series(tr, index=ohlc.index)

    def _calculate_atr(
        self, ohlc: pd.DataFrame, period: int
    ) -> pd.Series:
        """
        Calcula ATR padrão (SMA de True Range).

        Args:
            ohlc: DataFrame com OHLC
            period: Período do ATR

        Returns:
            Series com ATR calculado
        """
        tr = self._calculate_tr(ohlc)
        atr = tr.rolling(window=period).mean()
        return atr

    def _calculate_volatility_clusters(
        self, atr_values: np.ndarray
    ) -> np.ndarray:
        """
        Agrupa ATRs em clusters de volatilidade com K-means.

        Padrão esperado:
        - Cluster 0: Baixa volatilidade (ATR ~0.3x média)
        - Cluster 1: Volatilidade média (ATR ~1.0x média)
        - Cluster 2: Alta volatilidade (ATR ~1.8x média)

        Args:
            atr_values: Array 1D com valores de ATR

        Returns:
            Labels de cluster para cada valor de ATR
        """
        # Remove NaN
        valid_mask = ~np.isnan(atr_values)
        valid_values = atr_values[valid_mask].reshape(-1, 1)

        if len(valid_values) < self.n_clusters:
            logger.warning(
                f"Insufficient data for clustering: "
                f"{len(valid_values)} < {self.n_clusters}"
            )
            return np.zeros(len(atr_values), dtype=int)

        kmeans = KMeans(
            n_clusters=self.n_clusters,
            random_state=42,
            n_init=10,
        )
        clusters = kmeans.fit_predict(valid_values)

        # Mapear de volta para o array original
        full_clusters = np.full(len(atr_values), -1, dtype=int)
        full_clusters[valid_mask] = clusters

        return full_clusters

    def _calculate_adjustment_factors(
        self, atr_values: np.ndarray, clusters: np.ndarray
    ) -> Dict[str, float]:
        """
        Calcula fatores de ajuste por cluster.

        Lógica:
        - Cluster com menor ATR médio → fator ~0.8 (baixa vol)
        - Cluster mediano → fator ~1.0 (vol média)
        - Cluster com maior ATR médio → fator ~1.3 (alta vol)

        Args:
            atr_values: Array com valores de ATR
            clusters: Array com labels de cluster

        Returns:
            Dict com fator de ajuste por cluster
        """
        factors = {}
        valid_mask = ~np.isnan(atr_values)

        for cluster_id in range(self.n_clusters):
            cluster_mask = (clusters == cluster_id) & valid_mask
            if cluster_mask.sum() == 0:
                factors[cluster_id] = 1.0
                continue

            cluster_mean = atr_values[cluster_mask].mean()
            global_mean = atr_values[valid_mask].mean()

            if global_mean > 0:
                factors[cluster_id] = cluster_mean / global_mean
            else:
                factors[cluster_id] = 1.0

        return factors

    def calibrate(
        self, ohlc: pd.DataFrame, close_idx: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Calibra ATR dinâmico em múltiplos períodos.

        Args:
            ohlc: DataFrame com OHLC histórico (mín. 50 velas)
            close_idx: Índice da vela atual (padrão: última vela)

        Returns:
            Dict com 'atr_dynamic_{period}' para cada período
            Exemplo: {
                'atr_dynamic_5': 1.2,
                'atr_dynamic_10': 0.95,
                'atr_dynamic_14': 1.0,
                'atr_dynamic_20': 1.15,
                'atr_dynamic_28': 0.85
            }

        Raises:
            ValueError: Se histórico insuficiente ou dados inválidos
        """
        # Validações
        if len(ohlc) < self.min_history:
            raise ValueError(
                f"Histórico insuficiente: "
                f"{len(ohlc)} < {self.min_history}"
            )

        if not all(col in ohlc.columns for col in ["High", "Low", "Close"]):
            raise ValueError("OHLC deve conter colunas: High, Low, Close")

        if close_idx is None:
            close_idx = len(ohlc) - 1

        result = {}

        # Calcular ATR para cada período
        for period in self.periods:
            if period > len(ohlc):
                logger.warning(
                    f"Período {period} > histórico ({len(ohlc)}), "
                    f"usando máximo disponível"
                )
                period = len(ohlc) - 1

            atr = self._calculate_atr(ohlc, period)
            atr_values = atr.values

            # Aplicar clustering apenas se houver dados suficientes
            # Usar todo o histórico até close_idx (inclusive)
            history_data = atr_values[: close_idx + 1]
            nan_count = np.isnan(history_data).sum()

            if len(history_data) > self.n_clusters and nan_count < len(history_data) / 2:
                clusters = self._calculate_volatility_clusters(history_data)
                factors = self._calculate_adjustment_factors(
                    history_data, clusters
                )

                # Obter fator para vela atual (último índice do array)
                current_cluster = clusters[-1]
                if current_cluster >= 0:
                    adjustment = factors[current_cluster]
                else:
                    adjustment = 1.0
            else:
                adjustment = 1.0

            # Aplicar bounds [0.5x, 2.0x]
            current_atr = atr_values[close_idx]
            if not np.isnan(current_atr):
                adjusted_atr = current_atr * adjustment
                adjusted_atr = np.clip(
                    adjusted_atr,
                    current_atr * self.min_multiplier,
                    current_atr * self.max_multiplier,
                )
            else:
                adjusted_atr = np.nan

            result[f"atr_dynamic_{period}"] = float(adjusted_atr)

        return result

    def calibrate_batch(
        self, ohlc: pd.DataFrame, stride: int = 1
    ) -> pd.DataFrame:
        """
        Calibra ATR dinâmico para múltiplas velas (para backtesting).

        Args:
            ohlc: DataFrame com histórico completo
            stride: Passo entre calibrações (padrão: 1 = cada vela)

        Returns:
            DataFrame original + colunas 'atr_dynamic_{period}'
        """
        result = ohlc.copy()

        # Inicializar colunas
        for period in self.periods:
            result[f"atr_dynamic_{period}"] = np.nan

        # Calibrar para cada vela
        for i in range(self.min_history, len(ohlc), stride):
            window = ohlc.iloc[:i]
            calibration = self.calibrate(window, close_idx=len(window) - 1)

            for key, value in calibration.items():
                result.loc[result.index[i], key] = value

        return result


# Factory para backward compatibility
def create_atr_calibrator(
    periods: Optional[List[int]] = None,
) -> ATRDynamicCalibrator:
    """
    Factory para criar calibrador ATR com configurações padrão.

    Args:
        periods: Períodos opcionais (padrão: [5, 10, 14, 20, 28])

    Returns:
        Instância de ATRDynamicCalibrator
    """
    return ATRDynamicCalibrator(periods=periods)
