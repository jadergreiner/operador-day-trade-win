"""
AC1: Signal Generator - Camada de Geração de Sinais (M5 SMC Detector)

Responsabilidades:
    - Detectar estruturas SMC em timeframe M5 (BOS, CHoCH, FVG)
    - Gerar sinais com score SMC consolidado [-3, +3]
    - Capturar contexto completo de mercado (RSI, ATR, Bollinger, etc)
    - Validar confluência de indicadores

Pipeline AC1→AC2→AC3:
    AC1: SignalGenerator (THIS) gera Signal com MarketContext
    ↓
    AC2: SignalPersistence persiste em DB
    ↓
    AC3: SignalTracker rastreia lifecycle

Status: v1.0 (06/03/2026)
Referência: docs/DIAGRAMA_CLASSES.md (SignalGenerator class)
           docs/ARCHITECTURE.md (Analysis Layer)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
from uuid import uuid4
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============================================================================
# ENUMS & TYPE DEFINITIONS
# ============================================================================


class SMCPattern(str, Enum):
    """Padrões SMC detectáveis em M5."""
    BOS = "BOS"  # Break of Structure
    CHOCH = "CHoCH"  # Change of Character
    FVG = "FVG"  # Fair Value Gap
    IMPULSE = "IMPULSE"  # Impulso + Pullback


class TrendDirection(str, Enum):
    """Direção de tendência."""
    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"


@dataclass
class Candle:
    """Candle de preço (OHLCV)."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class MarketContext:
    """
    Contexto de mercado capturado no momento do sinal.

    AC1 captura TODOS os indicadores em tempo real para auditoria
    e análise posterior.
    """
    rsi: Optional[float] = None  # 0-100
    atr: Optional[float] = None  # Volatilidade
    bb_upper: Optional[float] = None  # Bollinger upper
    bb_lower: Optional[float] = None  # Bollinger lower
    volume: Optional[int] = None  # Volume
    spread: Optional[float] = None  # Bid-ask diff
    trend_direction: Optional[str] = None  # UP/DOWN/FLAT
    last_close: Optional[float] = None  # Preço anterior


@dataclass
class Signal:
    """
    Sinal gerado por AC1 (SignalGenerator).

    Um sinal é gerado quando M5 detecta estrutura SMC (BOS/CHoCH/FVG).
    Sinal é INDEPENDENTE de qualquer decisão de entrada.
    """
    signal_id: str
    timestamp: datetime
    symbol: str
    signal_type: str  # BUY ou SELL
    smc_score: float  # [-3, +3]
    smc_detector: str  # BOS, CHoCH, FVG, IMPULSE
    entry_price: float
    candle_index: int
    market_context: Optional[MarketContext] = None
    outcome_trade_id: Optional[int] = None
    outcome_pnl: Optional[float] = None
    outcome_days_open: Optional[float] = None
    outcome_type: Optional[str] = None
    created_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        """Signal está completo (tem outcome definido)."""
        return self.outcome_type is not None and self.outcome_type != "OPEN"


# ============================================================================
# AC1: SIGNAL GENERATOR
# ============================================================================


class SignalGenerator:
    """
    AC1: Gerador de sinais baseado em estruturas SMC (M5).

    Responsabilidades:
        - Analisar candles consecutivos
        - Detectar padrões BOS, CHoCH, FVG
        - Calcular score SMC consolidado
        - Gerar Signal com contexto completo
        - Validar confluência de indicadores

    Architecture:
        - Stateless: Cada chamada é independente
        - Market Data → Analysis → Signal
        - Format: OHLCV candles lista

    Padrões SMC Detectáveis:
        1. BOS (Break of Structure): Rompe último high/low significativo
        2. CHoCH (Change of Character): Reversão de padrão de impulso/pullback
        3. FVG (Fair Value Gap): Gap de preço não preenchido
        4. IMPULSE: Impulso + Pullback com confluência
    """

    def __init__(self):
        """Inicializa SerializerGenerador."""
        self.logger = logger

    # ========================================================================
    # AC1.1: DETECÇÃO DE PADRÕES SMC
    # ========================================================================

    def detect_bos(self, candles: List[Candle]) -> List[Dict[str, Any]]:
        """
        AC1.1a: Detecta Break of Structure (BOS).

        BOS = Romper o último high (uptrend) ou low (downtrend) significativo.

        Args:
            candles: Lista de candles ordenados cronologicamente

        Returns:
            Lista de dicts com {'pattern': 'BOS', 'type': 'BUY'|'SELL', 'price': float}
        """
        if len(candles) < 3:
            return []

        detections = []
        for i in range(2, len(candles)):
            prev_candle = candles[i - 1]
            curr_candle = candles[i]

            # BOS BUY: Current high > Previous high (depois de pullback)
            if curr_candle.high > prev_candle.high and prev_candle.close < prev_candle.open:
                detections.append({
                    "pattern": "BOS",
                    "type": "BUY",
                    "price": curr_candle.high,
                    "candle_index": i,
                })

            # BOS SELL: Current low < Previous low (depois de pullback)
            if curr_candle.low < prev_candle.low and prev_candle.close > prev_candle.open:
                detections.append({
                    "pattern": "BOS",
                    "type": "SELL",
                    "price": curr_candle.low,
                    "candle_index": i,
                })

        return detections

    def detect_choch(self, candles: List[Candle]) -> List[Dict[str, Any]]:
        """
        AC1.1b: Detecta Change of Character (CHoCH).

        CHoCH = Reversão do padrão de impulso/pullback.

        Args:
            candles: Lista de candles

        Returns:
            Lista de dicts com CHoCH detections
        """
        if len(candles) < 5:
            return []

        detections = []
        for i in range(4, len(candles)):
            # Analisa últimos 5 candles para reversal
            recent = candles[i - 4 : i + 1]

            # CHoCH BUY: Down -> Up reversal (série baixas → série altas)
            lows = [c.low for c in recent]
            highs = [c.high for c in recent]

            if (lows[0] > lows[1] and lows[1] < lows[2] and
                    lows[2] > lows[3] and lows[3] > lows[4]):
                detections.append({
                    "pattern": "CHoCH",
                    "type": "BUY",
                    "price": recent[-1].low,
                    "candle_index": i,
                })

            # CHoCH SELL: Up -> Down reversal (série altas → série baixas)
            if (highs[0] < highs[1] and highs[1] > highs[2] and
                    highs[2] < highs[3] and highs[3] < highs[4]):
                detections.append({
                    "pattern": "CHoCH",
                    "type": "SELL",
                    "price": recent[-1].high,
                    "candle_index": i,
                })

        return detections

    def detect_fvg(self, candles: List[Candle]) -> List[Dict[str, Any]]:
        """
        AC1.1c: Detecta Fair Value Gap (FVG).

        FVG = Gap não preenchido entre candles (low candle N > high candle N-2).

        Args:
            candles: Lista de candles

        Returns:
            Lista de dicts com FVG detections
        """
        if len(candles) < 3:
            return []

        detections = []
        for i in range(2, len(candles)):
            candle_n_minus_2 = candles[i - 2]
            candle_n_minus_1 = candles[i - 1]
            candle_n = candles[i]

            # FVG BULLISH: Candle N low > Candle N-2 high (gap não preenchido)
            if candle_n.low > candle_n_minus_2.high:
                detections.append({
                    "pattern": "FVG",
                    "type": "BUY",
                    "price": candle_n.low,
                    "gap_top": candle_n_minus_2.high,
                    "candle_index": i,
                })

            # FVG BEARISH: Candle N high < Candle N-2 low
            if candle_n.high < candle_n_minus_2.low:
                detections.append({
                    "pattern": "FVG",
                    "type": "SELL",
                    "price": candle_n.high,
                    "gap_bottom": candle_n_minus_2.low,
                    "candle_index": i,
                })

        return detections

    # ========================================================================
    # AC1.2: ANÁLISE DE CONTEXTO E SCORING
    # ========================================================================

    def calculate_smc_score(self, detections: List[Dict[str, Any]]) -> float:
        """
        AC1.2: Calcula score SMC consolidado [-3, +3].

        Score aumenta com:
        - Multiplos padrões detectados
        - Confluência de indicadores
        - Força do padrão

        Args:
            detections: Lista de detections com scores

        Returns:
            Score consolidado [-3, +3]
        """
        if not detections:
            return 0.0

        # Padrão BOS = +1.0, CHoCH = +0.8, FVG = +0.6
        pattern_weights = {"BOS": 1.0, "CHoCH": 0.8, "FVG": 0.6}
        score = sum(pattern_weights.get(d["pattern"], 0.5) for d in detections)

        # Limita a [-3, +3]
        return max(-3.0, min(3.0, score))

    def validate_signal_confluence(
        self,
        signal: Signal,
        rsi: float,
        atr: float,
        volatility: float,
    ) -> bool:
        """
        AC1.3: Valida confluência de indicadores.

        Um sinal é válido se:
        - RSI não está em nível extremo (20-80)
        - ATR > threshold (mínimo movimento esperado)
        - Volatilidade em range aceitável (<200%)

        Args:
            signal: Signal para validar
            rsi: Relative Strength Index (0-100)
            atr: Average True Range
            volatility: Volatilidade (%)

        Returns:
            True se sinal é válido
        """
        # Validações
        rsi_valid = 20 < rsi < 80
        atr_valid = atr > 0.1  # Mínimo ATR
        volatility_valid = volatility < 200  # Máximo de volatilidade

        return rsi_valid and atr_valid and volatility_valid

    # ========================================================================
    # AC1.4: GERAÇÃO DE SINAIS
    # ========================================================================

    def generate_signal(
        self,
        symbol: str,
        signal_type: str,  # BUY ou SELL
        smc_score: float,
        smc_detector: str,
        entry_price: float,
        candle_index: int,
        market_context: Optional[MarketContext] = None,
        timestamp: Optional[datetime] = None,
    ) -> Signal:
        """
        AC1.4: Gera um Signal completo com contexto.

        Args:
            symbol: Código do ativo (WIN, WDO)
            signal_type: BUY ou SELL
            smc_score: Score SMC [-3, +3]
            smc_detector: Padrão detectado (BOS, CHoCH, FVG)
            entry_price: Preço no momento
            candle_index: Índice do candle M5
            market_context: Contexto de mercado (opcional)
            timestamp: Timestamp (default: agora)

        Returns:
            Signal gerado com ID único
        """
        return Signal(
            signal_id=f"SIG-{uuid4().hex[:12].upper()}",
            timestamp=timestamp or datetime.now(),
            symbol=symbol,
            signal_type=signal_type,
            smc_score=smc_score,
            smc_detector=smc_detector,
            entry_price=entry_price,
            candle_index=candle_index,
            market_context=market_context or MarketContext(),
            created_at=datetime.now(),
        )

    # ========================================================================
    # AC1.5: ANÁLISE COMPLETA
    # ========================================================================

    def analyze_candles(
        self,
        candles: List[Candle],
        symbol: str,
        market_context: Optional[MarketContext] = None,
    ) -> List[Signal]:
        """
        AC1.5: Análise completa de candles → Sinais.

        Pipeline de análise:
        1. Detectar padrões SMC (BOS, CHoCH, FVG)
        2. Consolidar detections com score
        3. Validar confluência de indicadores
        4. Gerar Signal(s)

        Args:
            candles: Lista de candles M5 (mínimo 5)
            symbol: Código do ativo
            market_context: Contexto de mercado

        Returns:
            Lista de Signals gerados
        """
        if len(candles) < 5:
            self.logger.warning(f"AC1: Mínimo 5 candles necessários (temos {len(candles)})")
            return []

        signals = []
        bos_detections = self.detect_bos(candles)
        choch_detections = self.detect_choch(candles)
        fvg_detections = self.detect_fvg(candles)

        # Processa cada tipo de detecção
        for detection in bos_detections + choch_detections + fvg_detections:
            score = self.calculate_smc_score([detection])

            # Valida confluência
            if market_context:
                is_valid = self.validate_signal_confluence(
                    signal=None,
                    rsi=market_context.rsi or 50,
                    atr=market_context.atr or 10,
                    volatility=20,
                )
            else:
                is_valid = True

            if is_valid:
                signal = self.generate_signal(
                    symbol=symbol,
                    signal_type=detection["type"],
                    smc_score=score,
                    smc_detector=detection["pattern"],
                    entry_price=detection["price"],
                    candle_index=detection["candle_index"],
                    market_context=market_context,
                    timestamp=candles[detection["candle_index"]].timestamp,
                )
                signals.append(signal)
                self.logger.info(
                    f"[AC1-SIGNAL] {signal.signal_id}: {detection['pattern']} "
                    f"{signal.signal_type} @ {signal.entry_price} "
                    f"(score: {score:.2f})"
                )

        return signals
