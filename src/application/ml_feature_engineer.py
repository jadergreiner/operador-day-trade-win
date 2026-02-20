"""
Feature Engineering para Classifier ML v1.2

Responsabilidade: Extrair features da série temporal de velas e contexto de mercado
para treinar classifier que detecta oportunidades com alta probabilidade de ganho.

Padrão: Feature Store + Lazy Loading
Pipeline: Raw Candles → Indicators → Features → Dataset → Training

Status: SPRINT 1 - ML Expert
"""

from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class TimeFrame(Enum):
    """Timeframes suportados"""
    M1 = 1
    M5 = 5
    M15 = 15
    M30 = 30
    H1 = 60


@dataclass
class Candle:
    """Representação de uma vela OHLCV"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    @property
    def hl_range(self) -> float:
        """High-Low range"""
        return self.high - self.low
    
    @property
    def oc_range(self) -> float:
        """Open-Close range (body)"""
        return abs(self.close - self.open)


@dataclass
class FeatureVector:
    """Vector de features para uma vela"""
    candle_index: int
    timestamp: datetime
    
    # Price action (raw)
    close: float
    high: float
    low: float
    volume: int
    
    # Returns
    ret_1: float  # Retorno 1 vela anterior
    ret_5: float  # Retorno 5 velas anterior
    
    # Volatilidade
    volatility_5: float  # DP dos retornos 5 velas
    volatility_20: float  # DP dos retornos 20 velas
    volatility_ratio: float  # vol_5 / vol_20
    
    # Volume
    volume_sma_5: float
    volume_ratio: float  # vol / vol_sma_5
    
    # Momentum
    rsi_14: float  # Relative Strength Index
    macd: float  # MACD signal
    macd_histogram: float
    
    # Bandas
    bb_upper: float  # Bollinger Bands upper
    bb_lower: float
    bb_middle: float
    bb_position: float  # posição relativa na banda
    
    # Pattern recognition (sujo para agora, refinado depois)
    is_spike: bool  # Detectado spike (v1.1 detector)
    spike_magnitude: float  # σ (desvios padrão)
    
    # Correlação (com outros ativos - delayed)
    correlation_win_n: float  # Correlação com WIN$N
    correlation_petr4: float  # Correlação com PETR4
    
    # Context (mercado)
    hour_of_day: int
    day_of_week: int
    is_market_open: bool  # Horário de abertura
    is_lunch_time: bool  # 11:30-13:00
    
    # Label (apenas para dados históricos com resultado conhecido)
    label: Optional[float] = None  # 1.0 (ganho), 0.0 (perda), None (unknown)
    label_pnl: Optional[float] = None  # P&L real da operação


class FeatureEngineer:
    """
    Pipeline de feature engineering.
    
    Fluxo:
    1. Load candles (raw OHLCV)
    2. Validação (sem gaps, timeframe correto)
    3. Cálculo de indicadores técnicos
    4. Extração de features
    5. Normalização / Scaling
    6. Dataset para treino
    """

    def __init__(
        self,
        lookback_window: int = 100,
        spike_threshold: float = 2.0
    ):
        self.lookback_window = lookback_window
        self.spike_threshold = spike_threshold
        self.feature_columns = self._get_feature_columns()

    def create_feature_vector(
        self,
        candles: List[Candle],
        candle_index: int,
        spike_detector_output: Optional[Dict] = None,
        correlation_data: Optional[Dict] = None
    ) -> Optional[FeatureVector]:
        """
        Cria feature vector para uma vela específica.
        
        Args:
            candles: Lista de candles (índice 0 = mais antiga)
            candle_index: Índice da vela para a qual criar features
            spike_detector_output: Output do ProcessadorBDI (spike info)
            correlation_data: Correlações calculadas externamente
            
        Returns:
            FeatureVector ou None (se dados insuficientes)
        """
        if candle_index < 20:  # Precisa de histórico mínimo
            return None

        candle = candles[candle_index]
        
        # 1. Returns
        ret_1 = self._calculate_return(
            candles[candle_index - 1].close,
            candle.close
        )
        ret_5 = self._calculate_return(
            candles[candle_index - 5].close if candle_index >= 5 else candles[0].close,
            candle.close
        )

        # 2. Volatilidade
        vol_5 = self._calculate_volatility(candles, candle_index, window=5)
        vol_20 = self._calculate_volatility(candles, candle_index, window=20)
        vol_ratio = vol_5 / vol_20 if vol_20 > 0 else 0.0

        # 3. Volume
        vol_sma_5 = np.mean([c.volume for c in candles[candle_index-5:candle_index+1]])
        vol_ratio = candle.volume / vol_sma_5 if vol_sma_5 > 0 else 0.0

        # 4. Indicators técnicos
        rsi_14 = self._calculate_rsi(candles, candle_index, period=14)
        macd, macd_hist = self._calculate_macd(candles, candle_index)
        
        # 5. Bollinger Bands
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(
            candles, candle_index, period=20
        )
        bb_position = (candle.close - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5

        # 6. Spike detection (do ProcessadorBDI v1.1)
        is_spike = False
        spike_magnitude = 0.0
        if spike_detector_output:
            is_spike = spike_detector_output.get("is_spike", False)
            spike_magnitude = spike_detector_output.get("sigma", 0.0)

        # 7. Correlações (com atraso)
        corr_win_n = correlation_data.get("WIN$N", 0.0) if correlation_data else 0.0
        corr_petr4 = correlation_data.get("PETR4", 0.0) if correlation_data else 0.0

        # 8. Context
        hour = candle.timestamp.hour
        day = candle.timestamp.weekday()  # 0=Monday, 4=Friday
        is_open = 9 <= hour < 18  # 09:00 - 18:00
        is_lunch = 11 <= hour <= 13  # 11:00 - 13:00

        return FeatureVector(
            candle_index=candle_index,
            timestamp=candle.timestamp,
            close=candle.close,
            high=candle.high,
            low=candle.low,
            volume=candle.volume,
            ret_1=ret_1,
            ret_5=ret_5,
            volatility_5=vol_5,
            volatility_20=vol_20,
            volatility_ratio=vol_ratio,
            volume_sma_5=vol_sma_5,
            volume_ratio=vol_ratio,
            rsi_14=rsi_14,
            macd=macd,
            macd_histogram=macd_hist,
            bb_upper=bb_upper,
            bb_lower=bb_lower,
            bb_middle=bb_middle,
            bb_position=bb_position,
            is_spike=is_spike,
            spike_magnitude=spike_magnitude,
            correlation_win_n=corr_win_n,
            correlation_petr4=corr_petr4,
            hour_of_day=hour,
            day_of_week=day,
            is_market_open=is_open,
            is_lunch_time=is_lunch
        )

    def dataframe_from_features(self, features: List[FeatureVector]) -> pd.DataFrame:
        """
        Converte lista de FeatureVector em DataFrame (pronto para treino).
        
        Returns:
            pd.DataFrame com todas as features como colunas
        """
        data = []
        for f in features:
            data.append({
                'timestamp': f.timestamp,
                'close': f.close,
                'high': f.high,
                'low': f.low,
                'volume': f.volume,
                'ret_1': f.ret_1,
                'ret_5': f.ret_5,
                'volatility_5': f.volatility_5,
                'volatility_20': f.volatility_20,
                'volatility_ratio': f.volatility_ratio,
                'volume_sma_5': f.volume_sma_5,
                'volume_ratio': f.volume_ratio,
                'rsi_14': f.rsi_14,
                'macd': f.macd,
                'macd_histogram': f.macd_histogram,
                'bb_upper': f.bb_upper,
                'bb_lower': f.bb_lower,
                'bb_middle': f.bb_middle,
                'bb_position': f.bb_position,
                'is_spike': f.is_spike,
                'spike_magnitude': f.spike_magnitude,
                'correlation_win_n': f.correlation_win_n,
                'correlation_petr4': f.correlation_petr4,
                'hour_of_day': f.hour_of_day,
                'day_of_week': f.day_of_week,
                'is_market_open': f.is_market_open,
                'is_lunch_time': f.is_lunch_time,
                'label': f.label
            })

        df = pd.DataFrame(data)
        return df

    # ========================================================================
    # Cálculos de Indicadores Técnicos
    # ========================================================================

    @staticmethod
    def _calculate_return(prev_close: float, current_close: float) -> float:
        """Retorno logarítmico"""
        if prev_close <= 0:
            return 0.0
        return np.log(current_close / prev_close)

    @staticmethod
    def _calculate_volatility(
        candles: List[Candle],
        index: int,
        window: int = 5
    ) -> float:
        """Volatilidade (desvio padrão dos retornos)"""
        start = max(0, index - window + 1)
        closes = [c.close for c in candles[start:index + 1]]
        
        if len(closes) < 2:
            return 0.0
        
        returns = [np.log(closes[i] / closes[i-1]) for i in range(1, len(closes))]
        return np.std(returns) if returns else 0.0

    @staticmethod
    def _calculate_rsi(
        candles: List[Candle],
        index: int,
        period: int = 14
    ) -> float:
        """Relative Strength Index (RSI)"""
        start = max(0, index - period)
        closes = [c.close for c in candles[start:index + 1]]
        
        if len(closes) < 2:
            return 50.0  # Neutro
        
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0
        
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)

    @staticmethod
    def _calculate_macd(
        candles: List[Candle],
        index: int,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> Tuple[float, float]:
        """MACD"""
        start = max(0, index - slow - signal)
        closes = [c.close for c in candles[start:index + 1]]
        
        if len(closes) < slow:
            return 0.0, 0.0
        
        ema_fast = FeatureEngineer._calculate_ema(closes, fast)
        ema_slow = FeatureEngineer._calculate_ema(closes, slow)
        macd_line = ema_fast - ema_slow
        
        return float(macd_line), 0.0  # Signal não calculado aqui por simplicidade

    @staticmethod
    def _calculate_bollinger_bands(
        candles: List[Candle],
        index: int,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[float, float, float]:
        """Bollinger Bands"""
        start = max(0, index - period + 1)
        closes = [c.close for c in candles[start:index + 1]]
        
        if len(closes) < period:
            mid = closes[-1] if closes else 0
            return mid, mid, mid
        
        sma = np.mean(closes)
        std = np.std(closes)
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        return float(upper), float(sma), float(lower)

    @staticmethod
    def _calculate_ema(closes: List[float], period: int) -> float:
        """Exponential Moving Average"""
        if len(closes) < period:
            return np.mean(closes) if closes else 0.0
        
        multiplier = 2 / (period + 1)
        ema = np.mean(closes[:period])
        
        for i in range(period, len(closes)):
            ema = (closes[i] - ema) * multiplier + ema
        
        return float(ema)

    @staticmethod
    def _get_feature_columns() -> List[str]:
        """Lista de nomes de colunas de features"""
        return [
            'close', 'high', 'low', 'volume',
            'ret_1', 'ret_5',
            'volatility_5', 'volatility_20', 'volatility_ratio',
            'volume_sma_5', 'volume_ratio',
            'rsi_14', 'macd', 'macd_histogram',
            'bb_upper', 'bb_lower', 'bb_middle', 'bb_position',
            'is_spike', 'spike_magnitude',
            'correlation_win_n', 'correlation_petr4',
            'hour_of_day', 'day_of_week',
            'is_market_open', 'is_lunch_time'
        ]


# ============================================================================
# DATASET LOADER (para backtest com labels)
# ============================================================================

class DatasetLoader:
    """
    Carrega dados históricos com labels para treinamento.
    
    Fonte: backtest_results.json / backtest_optimized_results.json
    
    Estrutura esperada:
    {
        "trades": [
            {
                "entry_price": 128500,
                "exit_price": 128530,
                "pnl": 150.0,
                "entry_time": "2026-02-15T14:30:00Z",
                "exit_time": "2026-02-15T14:35:00Z"
            }
        ]
    }
    """

    def __init__(self, backtest_results_path: str):
        self.results_path = Path(backtest_results_path)

    def load_and_label(
        self,
        feature_vectors: List[FeatureVector],
        win_threshold: float = 100.0
    ) -> List[FeatureVector]:
        """
        Carrega backtest results e associa labels às features.
        
        Args:
            feature_vectors: Features extraídas
            win_threshold: Ganho mínimo para considerar "ganho"
            
        Returns:
            Features com labels preenchidos
        """
        # TODO: Implementar após ter backtest_optimized_results.json
        logger.info("TODO: Implementar load_and_label com backtest results")
        return feature_vectors


if __name__ == "__main__":
    print("FeatureEngineer module loaded")
