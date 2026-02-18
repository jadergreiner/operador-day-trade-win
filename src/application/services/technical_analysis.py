"""Servico de Analise Tecnica - identificacao de pontos de entrada/saida."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

import numpy as np

from src.domain.enums.trading_enums import TradeSignal
from src.domain.value_objects import Price, Symbol
from src.infrastructure.adapters.mt5_adapter import Candle


class TrendStrength(str, Enum):
    """Classificacao de forca da tendencia."""

    VERY_STRONG = "VERY_STRONG"
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    NO_TREND = "NO_TREND"


class SetupQuality(str, Enum):
    """Qualidade do setup de trading."""

    EXCELLENT = "EXCELLENT"  # Alta probabilidade
    GOOD = "GOOD"  # Boa probabilidade
    ACCEPTABLE = "ACCEPTABLE"  # Probabilidade moderada
    POOR = "POOR"  # Baixa probabilidade
    NO_SETUP = "NO_SETUP"  # Sem setup identificado


@dataclass
class TechnicalIndicators:
    """Indicadores tecnicos calculados."""

    # Medias Moveis
    sma_20: Optional[Decimal] = None
    sma_50: Optional[Decimal] = None
    ema_9: Optional[Decimal] = None
    ema_21: Optional[Decimal] = None

    # Momentum
    rsi_14: Optional[Decimal] = None
    macd: Optional[Decimal] = None
    macd_signal: Optional[Decimal] = None
    macd_histogram: Optional[Decimal] = None

    # Volatilidade
    bb_upper: Optional[Decimal] = None
    bb_middle: Optional[Decimal] = None
    bb_lower: Optional[Decimal] = None
    atr_14: Optional[Decimal] = None

    # Tendencia
    adx: Optional[Decimal] = None


@dataclass
class EntryPoint:
    """Ponto de entrada identificado para trade."""

    signal: TradeSignal
    entry_price: Price
    stop_loss: Price
    take_profit: Price
    setup_type: str  # "TREND", "REVERSAL", "BREAKOUT", "RANGE"
    setup_quality: SetupQuality
    confidence: Decimal  # 0-1
    reason: str
    risk_reward_ratio: Decimal


@dataclass
class TechnicalAnalysis:
    """Resultado completo da analise tecnica."""

    timestamp: datetime
    symbol: Symbol
    current_price: Price

    # Indicadores
    indicators: TechnicalIndicators

    # Analise de tendencia
    trend_direction: str  # "UP", "DOWN", "SIDEWAYS"
    trend_strength: TrendStrength

    # Pontos de entrada
    best_entry: Optional[EntryPoint]
    alternative_entries: list[EntryPoint]

    # Niveis-chave
    support_levels: list[Decimal]
    resistance_levels: list[Decimal]

    # Avaliacao geral
    technical_bias: str  # "BULLISH", "BEARISH", "NEUTRAL"
    summary: str
    key_observations: list[str]


class TechnicalAnalysisService:
    """
    Servico de analise tecnica e identificacao de pontos de entrada.

    Identifica melhores pontos de entrada para:
    - Seguimento de tendencia
    - Reversoes em extremos
    - Trading em faixa lateral
    """

    def __init__(self):
        """Inicializa servico de analise tecnica."""
        self._last_analysis: Optional[TechnicalAnalysis] = None

    def analyze_technical(
        self,
        candles: list[Candle],
        symbol: Symbol,
    ) -> TechnicalAnalysis:
        """
        Executa analise tecnica completa.

        Args:
            candles: Candles historicos para analise
            symbol: Simbolo sendo analisado

        Returns:
            TechnicalAnalysis com pontos de entrada e avaliacao
        """
        if len(candles) < 50:
            raise ValueError(
                "Need at least 50 candles for technical analysis"
            )

        current_price = Price(candles[-1].close.value)

        # Calcular todos os indicadores
        indicators = self._calculate_indicators(candles)

        # Analisar tendencia
        trend_direction, trend_strength = self._analyze_trend(
            candles=candles,
            indicators=indicators,
        )

        # Identificar suportes e resistencias
        support_levels = self._identify_support_levels(candles)
        resistance_levels = self._identify_resistance_levels(candles)

        # Encontrar pontos de entrada baseado na condicao do mercado
        if trend_strength in [TrendStrength.STRONG, TrendStrength.VERY_STRONG]:
            # Setups de seguimento de tendencia
            entries = self._find_trend_entries(
                candles=candles,
                indicators=indicators,
                trend_direction=trend_direction,
                current_price=current_price,
            )
        elif trend_strength == TrendStrength.WEAK:
            # Setups de reversao
            entries = self._find_reversal_entries(
                candles=candles,
                indicators=indicators,
                current_price=current_price,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
            )
        else:  # NO_TREND
            # Setups de trading em faixa
            entries = self._find_range_entries(
                candles=candles,
                current_price=current_price,
                support_levels=support_levels,
                resistance_levels=resistance_levels,
            )

        # Selecionar melhor entrada
        best_entry = self._select_best_entry(entries)

        # Determinar bias tecnico
        technical_bias = self._determine_technical_bias(
            trend_direction=trend_direction,
            indicators=indicators,
            best_entry=best_entry,
        )

        # Gerar resumo
        summary = self._generate_technical_summary(
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            indicators=indicators,
            best_entry=best_entry,
        )

        key_observations = self._extract_key_observations(
            indicators=indicators,
            trend_direction=trend_direction,
            best_entry=best_entry,
        )

        analysis = TechnicalAnalysis(
            timestamp=datetime.now(),
            symbol=symbol,
            current_price=current_price,
            indicators=indicators,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            best_entry=best_entry,
            alternative_entries=entries if best_entry else [],
            support_levels=support_levels,
            resistance_levels=resistance_levels,
            technical_bias=technical_bias,
            summary=summary,
            key_observations=key_observations,
        )

        self._last_analysis = analysis
        return analysis

    def _calculate_indicators(self, candles: list[Candle]) -> TechnicalIndicators:
        """Calcula todos os indicadores tecnicos."""
        closes = np.array([float(c.close.value) for c in candles])
        highs = np.array([float(c.high.value) for c in candles])
        lows = np.array([float(c.low.value) for c in candles])

        indicators = TechnicalIndicators()

        # Medias Moveis
        if len(closes) >= 50:
            indicators.sma_50 = Decimal(str(closes[-50:].mean()))
        if len(closes) >= 20:
            indicators.sma_20 = Decimal(str(closes[-20:].mean()))

        indicators.ema_21 = self._calculate_ema(closes, 21)
        indicators.ema_9 = self._calculate_ema(closes, 9)

        # RSI
        indicators.rsi_14 = self._calculate_rsi(closes, 14)

        # MACD
        indicators.macd, indicators.macd_signal, indicators.macd_histogram = (
            self._calculate_macd(closes)
        )

        # Bandas de Bollinger
        indicators.bb_upper, indicators.bb_middle, indicators.bb_lower = (
            self._calculate_bollinger_bands(closes, 20, 2)
        )

        # ATR
        indicators.atr_14 = self._calculate_atr(highs, lows, closes, 14)

        # ADX (simplificado - usaria calculo ADX completo em producao)
        indicators.adx = self._calculate_simple_adx(highs, lows, closes)

        return indicators

    def _calculate_ema(self, prices: np.ndarray, period: int) -> Decimal:
        """Calcula Media Movel Exponencial."""
        if len(prices) < period:
            return Decimal(str(prices.mean()))

        ema = prices[0]
        multiplier = 2 / (period + 1)

        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema

        return Decimal(str(ema))

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> Decimal:
        """Calcula Indice de Forca Relativa (RSI)."""
        if len(prices) < period + 1:
            return Decimal("50")

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = gains[-period:].mean()
        avg_loss = losses[-period:].mean()

        if avg_loss == 0:
            return Decimal("100")

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return Decimal(str(rsi))

    def _calculate_macd(
        self,
        prices: np.ndarray,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Calcula indicador MACD."""
        if len(prices) < slow:
            return Decimal("0"), Decimal("0"), Decimal("0")

        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)

        macd = ema_fast - ema_slow

        # Linha de sinal (simplificado)
        macd_signal = macd  # Precisaria de valores historicos do MACD

        histogram = macd - macd_signal

        return macd, macd_signal, histogram

    def _calculate_bollinger_bands(
        self,
        prices: np.ndarray,
        period: int = 20,
        std_dev: int = 2,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Calcula Bandas de Bollinger."""
        if len(prices) < period:
            mean = prices.mean()
            return Decimal(str(mean)), Decimal(str(mean)), Decimal(str(mean))

        middle = prices[-period:].mean()
        std = prices[-period:].std()

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)

        return Decimal(str(upper)), Decimal(str(middle)), Decimal(str(lower))

    def _calculate_atr(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        period: int = 14,
    ) -> Decimal:
        """Calcula Average True Range (ATR)."""
        if len(highs) < period + 1:
            return Decimal(str((highs[-period:] - lows[-period:]).mean()))

        true_ranges = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            true_ranges.append(tr)

        atr = np.array(true_ranges[-period:]).mean()
        return Decimal(str(atr))

    def _calculate_simple_adx(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
    ) -> Decimal:
        """Calculo simplificado do ADX."""
        # Simplificado - mede forca da tendencia
        if len(closes) < 14:
            return Decimal("20")

        # Calcular movimento direcional
        moves_up = 0
        moves_down = 0

        for i in range(1, 14):
            if closes[-i] > closes[-i - 1]:
                moves_up += 1
            elif closes[-i] < closes[-i - 1]:
                moves_down += 1

        # Forca de tendencia simples
        directional = abs(moves_up - moves_down)
        strength = (directional / 14) * 100

        return Decimal(str(min(strength * 7, 100)))  # Escala 0-100

    def _analyze_trend(
        self,
        candles: list[Candle],
        indicators: TechnicalIndicators,
    ) -> tuple[str, TrendStrength]:
        """Analisa direcao e forca da tendencia."""
        current = candles[-1].close.value

        # Determinar direcao
        direction = "SIDEWAYS"
        if indicators.sma_20 and indicators.sma_50:
            if current > indicators.sma_20 and indicators.sma_20 > indicators.sma_50:
                direction = "UP"
            elif (
                current < indicators.sma_20 and indicators.sma_20 < indicators.sma_50
            ):
                direction = "DOWN"

        # Determinar forca usando ADX
        strength = TrendStrength.NO_TREND
        if indicators.adx:
            if indicators.adx > 50:
                strength = TrendStrength.VERY_STRONG
            elif indicators.adx > 30:
                strength = TrendStrength.STRONG
            elif indicators.adx > 20:
                strength = TrendStrength.MODERATE
            elif indicators.adx > 10:
                strength = TrendStrength.WEAK

        return direction, strength

    def _identify_support_levels(self, candles: list[Candle]) -> list[Decimal]:
        """Identifica niveis de suporte."""
        lows = [c.low.value for c in candles[-50:]]
        # Simplificado - encontra minimas recentes
        sorted_lows = sorted(set(lows))[:3]
        return sorted_lows

    def _identify_resistance_levels(self, candles: list[Candle]) -> list[Decimal]:
        """Identifica niveis de resistencia."""
        highs = [c.high.value for c in candles[-50:]]
        # Simplificado - encontra maximas recentes
        sorted_highs = sorted(set(highs), reverse=True)[:3]
        return sorted_highs

    def _find_trend_entries(
        self,
        candles: list[Candle],
        indicators: TechnicalIndicators,
        trend_direction: str,
        current_price: Price,
    ) -> list[EntryPoint]:
        """Encontra pontos de entrada para seguimento de tendencia."""
        entries = []

        if not indicators.ema_9 or not indicators.ema_21:
            return entries

        # Pullback para EMA em tendencia de alta
        if trend_direction == "UP":
            if (
                current_price.value < indicators.ema_21
                and current_price.value > indicators.ema_21 * Decimal("0.995")
            ):
                stop_loss = Price(indicators.ema_21 * Decimal("0.99"))
                take_profit = Price(
                    current_price.value + (current_price.value - stop_loss.value) * 2
                )

                entry = EntryPoint(
                    signal=TradeSignal.BUY,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    setup_type="TREND",
                    setup_quality=SetupQuality.GOOD,
                    confidence=Decimal("0.75"),
                    reason="Pullback to EMA21 in uptrend",
                    risk_reward_ratio=Decimal("2.0"),
                )
                entries.append(entry)

        # Pullback para EMA em tendencia de baixa
        elif trend_direction == "DOWN":
            if (
                current_price.value > indicators.ema_21
                and current_price.value < indicators.ema_21 * Decimal("1.005")
            ):
                stop_loss = Price(indicators.ema_21 * Decimal("1.01"))
                take_profit = Price(
                    current_price.value - (stop_loss.value - current_price.value) * 2
                )

                entry = EntryPoint(
                    signal=TradeSignal.SELL,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    setup_type="TREND",
                    setup_quality=SetupQuality.GOOD,
                    confidence=Decimal("0.75"),
                    reason="Pullback to EMA21 in downtrend",
                    risk_reward_ratio=Decimal("2.0"),
                )
                entries.append(entry)

        return entries

    def _find_reversal_entries(
        self,
        candles: list[Candle],
        indicators: TechnicalIndicators,
        current_price: Price,
        support_levels: list[Decimal],
        resistance_levels: list[Decimal],
    ) -> list[EntryPoint]:
        """Encontra pontos de entrada de reversao em extremos."""
        entries = []

        if not indicators.rsi_14:
            return entries

        # Reversao sobrevendido no suporte
        if indicators.rsi_14 < 30 and support_levels:
            nearest_support = min(support_levels, key=lambda x: abs(x - current_price.value))

            if abs(current_price.value - nearest_support) / current_price.value < Decimal("0.01"):
                stop_loss = Price(nearest_support * Decimal("0.995"))
                take_profit = Price(
                    current_price.value + (current_price.value - stop_loss.value) * 3
                )

                entry = EntryPoint(
                    signal=TradeSignal.BUY,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    setup_type="REVERSAL",
                    setup_quality=SetupQuality.GOOD,
                    confidence=Decimal("0.70"),
                    reason=f"RSI oversold ({indicators.rsi_14:.1f}) at support",
                    risk_reward_ratio=Decimal("3.0"),
                )
                entries.append(entry)

        # Reversao sobrecomprado na resistencia
        if indicators.rsi_14 > 70 and resistance_levels:
            nearest_resistance = min(
                resistance_levels, key=lambda x: abs(x - current_price.value)
            )

            if (
                abs(current_price.value - nearest_resistance) / current_price.value
                < Decimal("0.01")
            ):
                stop_loss = Price(nearest_resistance * Decimal("1.005"))
                take_profit = Price(
                    current_price.value - (stop_loss.value - current_price.value) * 3
                )

                entry = EntryPoint(
                    signal=TradeSignal.SELL,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    setup_type="REVERSAL",
                    setup_quality=SetupQuality.GOOD,
                    confidence=Decimal("0.70"),
                    reason=f"RSI overbought ({indicators.rsi_14:.1f}) at resistance",
                    risk_reward_ratio=Decimal("3.0"),
                )
                entries.append(entry)

        return entries

    def _find_range_entries(
        self,
        candles: list[Candle],
        current_price: Price,
        support_levels: list[Decimal],
        resistance_levels: list[Decimal],
    ) -> list[EntryPoint]:
        """Encontra entradas de trading em faixa lateral."""
        entries = []

        if not support_levels or not resistance_levels:
            return entries

        range_bottom = min(support_levels)
        range_top = max(resistance_levels)

        # Compra no fundo da faixa
        if abs(current_price.value - range_bottom) / current_price.value < Decimal("0.015"):
            stop_loss = Price(range_bottom * Decimal("0.995"))
            take_profit = Price(range_top * Decimal("0.995"))

            entry = EntryPoint(
                signal=TradeSignal.BUY,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                setup_type="RANGE",
                setup_quality=SetupQuality.ACCEPTABLE,
                confidence=Decimal("0.65"),
                reason="Near bottom of trading range",
                risk_reward_ratio=(take_profit.value - current_price.value) / (current_price.value - stop_loss.value),
            )
            entries.append(entry)

        # Venda no topo da faixa
        if abs(current_price.value - range_top) / current_price.value < Decimal("0.015"):
            stop_loss = Price(range_top * Decimal("1.005"))
            take_profit = Price(range_bottom * Decimal("1.005"))

            entry = EntryPoint(
                signal=TradeSignal.SELL,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                setup_type="RANGE",
                setup_quality=SetupQuality.ACCEPTABLE,
                confidence=Decimal("0.65"),
                reason="Near top of trading range",
                risk_reward_ratio=(current_price.value - take_profit.value) / (stop_loss.value - current_price.value),
            )
            entries.append(entry)

        return entries

    def _select_best_entry(self, entries: list[EntryPoint]) -> Optional[EntryPoint]:
        """Seleciona melhor entrada entre as candidatas."""
        if not entries:
            return None

        # Ordena por qualidade do setup e confianca
        sorted_entries = sorted(
            entries,
            key=lambda e: (e.setup_quality.value, e.confidence),
            reverse=True,
        )

        return sorted_entries[0]

    def _determine_technical_bias(
        self,
        trend_direction: str,
        indicators: TechnicalIndicators,
        best_entry: Optional[EntryPoint],
    ) -> str:
        """Determina bias tecnico geral."""
        if best_entry:
            if best_entry.signal == TradeSignal.BUY:
                return "BULLISH"
            elif best_entry.signal == TradeSignal.SELL:
                return "BEARISH"

        if trend_direction == "UP":
            return "BULLISH"
        elif trend_direction == "DOWN":
            return "BEARISH"

        return "NEUTRAL"

    def _generate_technical_summary(
        self,
        trend_direction: str,
        trend_strength: TrendStrength,
        indicators: TechnicalIndicators,
        best_entry: Optional[EntryPoint],
    ) -> str:
        """Gera resumo da analise tecnica."""
        trend_text = f"Tendência {trend_direction.lower()} com força {trend_strength.value.lower()}"

        if best_entry:
            entry_text = f" Setup {best_entry.setup_type} identificado ({best_entry.signal.value})"
        else:
            entry_text = " Sem setup claro no momento"

        rsi_text = ""
        if indicators.rsi_14:
            rsi_text = f". RSI: {indicators.rsi_14:.1f}"

        return trend_text + entry_text + rsi_text

    def _extract_key_observations(
        self,
        indicators: TechnicalIndicators,
        trend_direction: str,
        best_entry: Optional[EntryPoint],
    ) -> list[str]:
        """Extrai observacoes tecnicas chave."""
        observations = []

        # Tendencia
        observations.append(f"📊 Tendência: {trend_direction}")

        # RSI
        if indicators.rsi_14:
            if indicators.rsi_14 < 30:
                observations.append(f"🔵 RSI oversold: {indicators.rsi_14:.1f}")
            elif indicators.rsi_14 > 70:
                observations.append(f"🔴 RSI overbought: {indicators.rsi_14:.1f}")
            else:
                observations.append(f"⚪ RSI neutro: {indicators.rsi_14:.1f}")

        # Setup de entrada
        if best_entry:
            observations.append(
                f"✅ Setup: {best_entry.setup_type} - {best_entry.reason}"
            )
            observations.append(
                f"📈 R/R: {best_entry.risk_reward_ratio:.2f} - Confiança: {best_entry.confidence:.0%}"
            )

        return observations

    def get_trading_bias_from_technical(self) -> str:
        """Retorna bias de trading da analise tecnica."""
        if not self._last_analysis:
            return "NEUTRAL"

        return self._last_analysis.technical_bias
