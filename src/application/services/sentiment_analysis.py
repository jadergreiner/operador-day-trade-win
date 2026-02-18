"""Servico de Analise de Sentimento - Deteccao de sentimento intraday."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from src.domain.enums.trading_enums import MarketCondition
from src.infrastructure.adapters.mt5_adapter import Candle
from src.domain.value_objects import Symbol


class IntradaySentiment(str, Enum):
    """Sentimento intraday do mercado."""

    STRONG_BUYERS = "STRONG_BUYERS"  # Compradores dominando
    MODERATE_BUYERS = "MODERATE_BUYERS"  # Leve viés comprador
    NEUTRAL = "NEUTRAL"  # Lateralizado, sem direção
    MODERATE_SELLERS = "MODERATE_SELLERS"  # Leve viés vendedor
    STRONG_SELLERS = "STRONG_SELLERS"  # Vendedores dominando


class SessionPhase(str, Enum):
    """Fase da sessao de trading."""

    PRE_MARKET = "PRE_MARKET"  # Antes da abertura
    OPENING = "OPENING"  # Primeira hora
    MIDDAY = "MIDDAY"  # Meio do dia
    AFTERNOON = "AFTERNOON"  # Tarde
    CLOSING = "CLOSING"  # Última hora
    AFTER_HOURS = "AFTER_HOURS"  # Após fechamento


@dataclass
class SentimentAnalysis:
    """Resultado da analise de sentimento de mercado."""

    timestamp: datetime
    symbol: Symbol

    # Sentimento
    intraday_sentiment: IntradaySentiment
    market_condition: MarketCondition
    session_phase: SessionPhase

    # Acao de Preco
    opening_price: Decimal
    current_price: Decimal
    high_of_day: Decimal
    low_of_day: Decimal
    price_change_percent: Decimal

    # Acoes Correlacionadas
    petr4_price: Optional[Decimal]
    vale3_price: Optional[Decimal]

    # Analise de Volume
    volume_vs_average: str  # "ABOVE", "NORMAL", "BELOW"
    volume_trend: str  # "INCREASING", "DECREASING", "STABLE"

    # Momentum
    momentum: str  # "STRONG_UP", "UP", "NEUTRAL", "DOWN", "STRONG_DOWN"
    volatility: str  # "HIGH", "NORMAL", "LOW"

    # Avaliacao de Probabilidade
    probability_up: Decimal  # 0-1
    probability_down: Decimal  # 0-1
    probability_neutral: Decimal  # 0-1

    # Estrategia de Trading
    recommended_approach: str  # "TREND_FOLLOWING", "REVERSAL", "RANGE", "WAIT"
    key_levels: dict[str, Decimal]  # suporte/resistencia

    # Resumo
    summary: str
    key_signals: list[str]


class SentimentAnalysisService:
    """
    Servico para analise de sentimento intraday do mercado.

    Determina se o mercado esta altista, baixista ou neutro para HOJE.
    """

    def __init__(self):
        """Inicializa servico de analise de sentimento."""
        self._last_analysis: Optional[SentimentAnalysis] = None

    def analyze_market_sentiment(
        self,
        candles: list[Candle],
        symbol: Symbol,
        petr4: Optional[Decimal] = None,
        vale3: Optional[Decimal] = None,
    ) -> SentimentAnalysis:
        """
        Analisa sentimento atual do mercado a partir dos candles.

        Args:
            candles: Candles recentes (dados intraday)
            symbol: Simbolo sendo analisado

        Returns:
            SentimentAnalysis com avaliacao completa
        """
        if not candles:
            raise ValueError("No candles provided for sentiment analysis")

        # Obtem candle mais recente
        latest = candles[-1]
        opening_candle = candles[0]

        # Calcula metricas de preco
        opening_price = opening_candle.open.value
        current_price = latest.close.value
        high_of_day = max(c.high.value for c in candles)
        low_of_day = min(c.low.value for c in candles)

        # Variacao de preco desde a abertura
        if opening_price and opening_price > 0:
            price_change = ((current_price - opening_price) / opening_price) * 100
        else:
            price_change = 0.0

        # Determina sentimento
        sentiment = self._determine_sentiment(
            price_change=price_change,
            candles=candles,
        )

        # Determina condicao de mercado
        market_condition = self._determine_market_condition(
            candles=candles,
            high=high_of_day,
            low=low_of_day,
        )

        # Avalia momentum
        momentum = self._assess_momentum(candles=candles)

        # Avalia volatilidade
        volatility = self._assess_volatility(
            high=high_of_day,
            low=low_of_day,
            opening=opening_price,
        )

        # Analise de volume
        volume_vs_avg = self._analyze_volume(candles=candles)
        volume_trend = self._analyze_volume_trend(candles=candles)

        # Calcula probabilidades
        prob_up, prob_down, prob_neutral = self._calculate_probabilities(
            sentiment=sentiment,
            market_condition=market_condition,
        )

        # Determina fase da sessao
        session_phase = self._determine_session_phase()

        # Abordagem recomendada
        approach = self._recommend_approach(
            sentiment=sentiment,
            market_condition=market_condition,
            volatility=volatility,
        )

        # Niveis chave
        key_levels = self._identify_key_levels(
            candles=candles,
            high=high_of_day,
            low=low_of_day,
        )

        # Gera resumo
        summary = self._generate_sentiment_summary(
            sentiment=sentiment,
            market_condition=market_condition,
            price_change=price_change,
        )

        key_signals = self._extract_key_signals(
            sentiment=sentiment,
            momentum=momentum,
            volatility=volatility,
            volume_vs_avg=volume_vs_avg,
            petr4=petr4,
            vale3=vale3,
        )

        analysis = SentimentAnalysis(
            timestamp=datetime.now(),
            symbol=symbol,
            intraday_sentiment=sentiment,
            market_condition=market_condition,
            session_phase=session_phase,
            opening_price=opening_price,
            current_price=current_price,
            high_of_day=high_of_day,
            low_of_day=low_of_day,
            price_change_percent=Decimal(str(price_change)),
            petr4_price=petr4,
            vale3_price=vale3,
            volume_vs_average=volume_vs_avg,
            volume_trend=volume_trend,
            momentum=momentum,
            volatility=volatility,
            probability_up=prob_up,
            probability_down=prob_down,
            probability_neutral=prob_neutral,
            recommended_approach=approach,
            key_levels=key_levels,
            summary=summary,
            key_signals=key_signals,
        )

        self._last_analysis = analysis
        return analysis

    def _determine_sentiment(
        self,
        price_change: Decimal,
        candles: list[Candle],
    ) -> IntradaySentiment:
        """Determina sentimento intraday."""
        # Conta candles de alta vs baixa
        bullish = sum(1 for c in candles if c.close.value > c.open.value)
        bearish = sum(1 for c in candles if c.close.value < c.open.value)
        total = len(candles)

        if price_change > 1.5:
            return IntradaySentiment.STRONG_BUYERS
        elif price_change > 0.5:
            return IntradaySentiment.MODERATE_BUYERS
        elif price_change < -1.5:
            return IntradaySentiment.STRONG_SELLERS
        elif price_change < -0.5:
            return IntradaySentiment.MODERATE_SELLERS

        # Verifica proporcao de candles
        if bullish / total > 0.65:
            return IntradaySentiment.MODERATE_BUYERS
        elif bearish / total > 0.65:
            return IntradaySentiment.MODERATE_SELLERS

        return IntradaySentiment.NEUTRAL

    def _determine_market_condition(
        self,
        candles: list[Candle],
        high: Decimal,
        low: Decimal,
    ) -> MarketCondition:
        """Determina condicao do mercado (tendencia vs lateralizado)."""
        # Calcula amplitude
        if low and low > 0:
            price_range = ((high - low) / low) * 100
        else:
            price_range = 0.0

        # Verifica direcao clara
        closes = [c.close.value for c in candles]
        if len(closes) < 10:
            return MarketCondition.UNKNOWN

        # Deteccao simples de tendencia
        first_half_avg = sum(closes[: len(closes) // 2]) / (len(closes) // 2)
        second_half_avg = sum(closes[len(closes) // 2 :]) / (
            len(closes) - len(closes) // 2
        )

        change = ((second_half_avg - first_half_avg) / first_half_avg) * 100

        if change > 0.5:
            return MarketCondition.BULLISH
        elif change < -0.5:
            return MarketCondition.BEARISH
        elif price_range > 2:
            return MarketCondition.VOLATILE

        return MarketCondition.RANGING

    def _assess_momentum(self, candles: list[Candle]) -> str:
        """Avalia momentum de preco."""
        if len(candles) < 5:
            return "NEUTRAL"

        # Analisa candles recentes
        recent = candles[-5:]
        bullish = sum(1 for c in recent if c.close.value > c.open.value)

        if bullish >= 4:
            return "STRONG_UP"
        elif bullish >= 3:
            return "UP"
        elif bullish <= 1:
            return "STRONG_DOWN"
        elif bullish <= 2:
            return "DOWN"

        return "NEUTRAL"

    def _assess_volatility(
        self,
        high: Decimal,
        low: Decimal,
        opening: Decimal,
    ) -> str:
        """Avalia volatilidade do mercado."""
        if opening and opening > 0:
            daily_range = ((high - low) / opening) * 100
        else:
            daily_range = 0.0

        if daily_range > 2.5:
            return "HIGH"
        elif daily_range < 1.0:
            return "LOW"

        return "NORMAL"

    def _analyze_volume(self, candles: list[Candle]) -> str:
        """Analisa volume vs media."""
        if len(candles) < 10:
            return "NORMAL"

        volumes = [c.volume for c in candles]
        avg_volume = sum(volumes) / len(volumes)
        latest_volume = candles[-1].volume

        if latest_volume > avg_volume * 1.5:
            return "ABOVE"
        elif latest_volume < avg_volume * 0.5:
            return "BELOW"

        return "NORMAL"

    def _analyze_volume_trend(self, candles: list[Candle]) -> str:
        """Analisa tendencia de volume."""
        if len(candles) < 10:
            return "STABLE"

        first_half = candles[: len(candles) // 2]
        second_half = candles[len(candles) // 2 :]

        avg_first = sum(c.volume for c in first_half) / len(first_half)
        avg_second = sum(c.volume for c in second_half) / len(second_half)

        if avg_second > avg_first * 1.2:
            return "INCREASING"
        elif avg_second < avg_first * 0.8:
            return "DECREASING"

        return "STABLE"

    def _calculate_probabilities(
        self,
        sentiment: IntradaySentiment,
        market_condition: MarketCondition,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Calcula probabilidades direcionais."""
        # Probabilidades base por sentimento
        if sentiment == IntradaySentiment.STRONG_BUYERS:
            return Decimal("0.7"), Decimal("0.2"), Decimal("0.1")
        elif sentiment == IntradaySentiment.MODERATE_BUYERS:
            return Decimal("0.55"), Decimal("0.30"), Decimal("0.15")
        elif sentiment == IntradaySentiment.STRONG_SELLERS:
            return Decimal("0.2"), Decimal("0.7"), Decimal("0.1")
        elif sentiment == IntradaySentiment.MODERATE_SELLERS:
            return Decimal("0.30"), Decimal("0.55"), Decimal("0.15")
        else:  # NEUTRAL
            return Decimal("0.33"), Decimal("0.33"), Decimal("0.34")

    def _determine_session_phase(self) -> SessionPhase:
        """Determina fase atual da sessao."""
        hour = datetime.now().hour

        if hour < 9:
            return SessionPhase.PRE_MARKET
        elif hour < 11:
            return SessionPhase.OPENING
        elif hour < 14:
            return SessionPhase.MIDDAY
        elif hour < 17:
            return SessionPhase.AFTERNOON
        elif hour < 18:
            return SessionPhase.CLOSING
        else:
            return SessionPhase.AFTER_HOURS

    def _recommend_approach(
        self,
        sentiment: IntradaySentiment,
        market_condition: MarketCondition,
        volatility: str,
    ) -> str:
        """Recomenda abordagem de trading."""
        if market_condition in [MarketCondition.BULLISH, MarketCondition.BEARISH]:
            return "TREND_FOLLOWING"
        elif market_condition == MarketCondition.RANGING:
            return "RANGE"
        elif volatility == "HIGH":
            return "WAIT"
        elif sentiment == IntradaySentiment.NEUTRAL:
            return "WAIT"

        return "REVERSAL"

    def _identify_key_levels(
        self,
        candles: list[Candle],
        high: Decimal,
        low: Decimal,
    ) -> dict[str, Decimal]:
        """Identifica niveis chave de suporte e resistencia."""
        # Simplificado - usaria metodos mais sofisticados em producao
        pivot = (high + low + candles[-1].close.value) / 3

        return {
            "resistance_strong": high,
            "resistance_pivot": pivot + (high - low) / 3,
            "pivot": pivot,
            "support_pivot": pivot - (high - low) / 3,
            "support_strong": low,
        }

    def _generate_sentiment_summary(
        self,
        sentiment: IntradaySentiment,
        market_condition: MarketCondition,
        price_change: Decimal,
    ) -> str:
        """Gera resumo de sentimento legivel."""
        sentiment_text = {
            IntradaySentiment.STRONG_BUYERS: "Compradores dominando fortemente",
            IntradaySentiment.MODERATE_BUYERS: "Viés comprador moderado",
            IntradaySentiment.NEUTRAL: "Mercado sem direção clara",
            IntradaySentiment.MODERATE_SELLERS: "Viés vendedor moderado",
            IntradaySentiment.STRONG_SELLERS: "Vendedores dominando fortemente",
        }

        condition_text = {
            MarketCondition.BULLISH: "tendência de alta",
            MarketCondition.BEARISH: "tendência de baixa",
            MarketCondition.RANGING: "lateralizado",
            MarketCondition.VOLATILE: "volátil",
            MarketCondition.UNKNOWN: "indefinido",
        }

        return (
            f"{sentiment_text[sentiment]}. "
            f"Mercado {condition_text[market_condition]}. "
            f"Variação: {price_change:+.2f}%"
        )

    def _extract_key_signals(
        self,
        sentiment: IntradaySentiment,
        momentum: str,
        volatility: str,
        volume_vs_avg: str,
        petr4: Optional[Decimal] = None,
        vale3: Optional[Decimal] = None,
    ) -> list[str]:
        """Extrai sinais chave da analise de sentimento."""
        signals = []

        if petr4:
            signals.append(f"🛢️ PETR4 monitorada: R$ {petr4:,.2f}")
        if vale3:
            signals.append(f"🏗️ VALE3 monitorada: R$ {vale3:,.2f}")

        # Sinais de sentimento
        if sentiment in [
            IntradaySentiment.STRONG_BUYERS,
            IntradaySentiment.MODERATE_BUYERS,
        ]:
            signals.append("📈 Pressão compradora presente")
        elif sentiment in [
            IntradaySentiment.STRONG_SELLERS,
            IntradaySentiment.MODERATE_SELLERS,
        ]:
            signals.append("📉 Pressão vendedora presente")
        else:
            signals.append("↔️ Mercado lateral, aguardar definição")

        # Momentum
        if momentum in ["STRONG_UP", "UP"]:
            signals.append("🚀 Momento positivo")
        elif momentum in ["STRONG_DOWN", "DOWN"]:
            signals.append("⬇️ Momento negativo")

        # Volume
        if volume_vs_avg == "ABOVE":
            signals.append("📊 Volume acima da média (confirmação)")
        elif volume_vs_avg == "BELOW":
            signals.append("⚠️ Volume baixo (falta confirmação)")

        # Volatilidade
        if volatility == "HIGH":
            signals.append("⚡ Alta volatilidade (cautela)")
        elif volatility == "LOW":
            signals.append("😴 Baixa volatilidade (esperar breakout)")

        return signals

    def get_trading_bias_from_sentiment(self) -> str:
        """
        Obtem vies de trading baseado no sentimento.

        Returns:
            "BULLISH", "BEARISH", ou "NEUTRAL"
        """
        if not self._last_analysis:
            return "NEUTRAL"

        if self._last_analysis.intraday_sentiment in [
            IntradaySentiment.STRONG_BUYERS,
            IntradaySentiment.MODERATE_BUYERS,
        ]:
            return "BULLISH"
        elif self._last_analysis.intraday_sentiment in [
            IntradaySentiment.STRONG_SELLERS,
            IntradaySentiment.MODERATE_SELLERS,
        ]:
            return "BEARISH"

        return "NEUTRAL"
