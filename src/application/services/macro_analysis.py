"""Servico de Analise Macroeconomica - Condicoes globais de mercado."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class GlobalRiskSentiment(str, Enum):
    """Classificacao de sentimento de risco global."""

    RISK_ON = "RISK_ON"  # Apetite por risco, mercados emergentes se beneficiam
    RISK_OFF = "RISK_OFF"  # Aversão ao risco, fuga para ativos seguros
    NEUTRAL = "NEUTRAL"  # Sem direção clara


class MarketDriver(str, Enum):
    """Principais drivers de mercado."""

    FED_POLICY = "FED_POLICY"
    INFLATION = "INFLATION"
    GEOPOLITICS = "GEOPOLITICS"
    COMMODITIES = "COMMODITIES"
    CHINA_GROWTH = "CHINA_GROWTH"
    US_DATA = "US_DATA"
    CENTRAL_BANKS = "CENTRAL_BANKS"


@dataclass
class MacroSnapshot:
    """Snapshot das condicoes macro impactando o trading de hoje."""

    timestamp: datetime

    # Sentimento Global
    global_risk_sentiment: GlobalRiskSentiment
    main_driver: MarketDriver

    # Mercados Principais
    us_futures_trend: str  # "UP", "DOWN", "FLAT"
    us_10y_yield: Optional[Decimal]  # Rendimento do Treasury
    dxy_dollar_index: Optional[Decimal]  # Forca do dolar
    vix_fear_index: Optional[Decimal]  # Volatilidade/medo
    bewz39_level: Optional[Decimal]  # EWZ BDR

    # Commodities (impacto no Brasil)
    oil_price_trend: str  # "UP", "DOWN", "FLAT"
    iron_ore_trend: str  # Demanda da China

    # Avaliacao de Impacto
    impact_on_brazil: str  # "POSITIVE", "NEGATIVE", "NEUTRAL"
    confidence: Decimal  # 0-1

    # Resumo
    summary: str
    key_points: list[str]


class MacroAnalysisService:
    """
    Servico para analise de condicoes macroeconomicas globais.

    Sintetiza dados de mercados globais para entender o contexto
    de HOJE para trading no mercado brasileiro.
    """

    def __init__(self):
        """Inicializa o servico de analise macro."""
        self._last_analysis: Optional[MacroSnapshot] = None

    def analyze_current_macro_conditions(
        self,
        us_futures: Optional[Decimal] = None,
        treasury_yield: Optional[Decimal] = None,
        dollar_index: Optional[Decimal] = None,
        vix: Optional[Decimal] = None,
        bewz39: Optional[Decimal] = None,
    ) -> MacroSnapshot:
        """
        Analisa as condicoes macroeconomicas globais atuais.

        Na implementacao real, isso buscaria dados ao vivo de:
        - APIs Bloomberg/Reuters
        - Calendarios economicos
        - Declaracoes do Fed
        - Noticias geopoliticas

        Args:
            us_futures: Nivel dos futuros de acoes dos EUA
            treasury_yield: Rendimento do Treasury 10Y dos EUA
            dollar_index: Indice do dolar DXY
            vix: Indice de volatilidade VIX

        Returns:
            MacroSnapshot com a analise
        """
        # Por enquanto, criamos um framework que pode ser populado com dados reais

        # Determina sentimento de risco global
        risk_sentiment = self._assess_risk_sentiment(
            vix=vix,
            dollar_index=dollar_index,
        )

        # Avalia impacto no Brasil
        impact_on_brazil = self._assess_brazil_impact(
            risk_sentiment=risk_sentiment,
            dollar_index=dollar_index,
        )

        # Gera resumo
        summary = self._generate_macro_summary(
            risk_sentiment=risk_sentiment,
            impact_on_brazil=impact_on_brazil,
        )

        key_points = self._extract_key_points(
            risk_sentiment=risk_sentiment,
            impact_on_brazil=impact_on_brazil,
            bewz39=bewz39,
        )

        snapshot = MacroSnapshot(
            timestamp=datetime.now(),
            global_risk_sentiment=risk_sentiment,
            main_driver=MarketDriver.FED_POLICY,  # Seria determinado dinamicamente
            us_futures_trend="FLAT",  # Seria calculado a partir de dados reais
            us_10y_yield=treasury_yield,
            dxy_dollar_index=dollar_index,
            vix_fear_index=vix,
            bewz39_level=bewz39,
            oil_price_trend="FLAT",  # Seria buscado
            iron_ore_trend="FLAT",  # Seria buscado
            impact_on_brazil=impact_on_brazil,
            confidence=Decimal("0.75"),
            summary=summary,
            key_points=key_points,
        )

        self._last_analysis = snapshot
        return snapshot

    def _assess_risk_sentiment(
        self,
        vix: Optional[Decimal],
        dollar_index: Optional[Decimal],
    ) -> GlobalRiskSentiment:
        """Avalia sentimento de risco global."""
        # VIX > 20 tipicamente indica medo/risk-off
        # Dolar forte tipicamente significa risk-off para mercados emergentes

        if vix and vix > Decimal("20"):
            return GlobalRiskSentiment.RISK_OFF

        if dollar_index and dollar_index > Decimal("105"):
            return GlobalRiskSentiment.RISK_OFF

        if vix and vix < Decimal("15"):
            return GlobalRiskSentiment.RISK_ON

        return GlobalRiskSentiment.NEUTRAL

    def _assess_brazil_impact(
        self,
        risk_sentiment: GlobalRiskSentiment,
        dollar_index: Optional[Decimal],
    ) -> str:
        """Avalia impacto macro nos mercados brasileiros."""
        if risk_sentiment == GlobalRiskSentiment.RISK_ON:
            return "POSITIVE"
        elif risk_sentiment == GlobalRiskSentiment.RISK_OFF:
            return "NEGATIVE"
        return "NEUTRAL"

    def _generate_macro_summary(
        self,
        risk_sentiment: GlobalRiskSentiment,
        impact_on_brazil: str,
    ) -> str:
        """Gera resumo macro legivel por humanos."""
        sentiment_text = {
            GlobalRiskSentiment.RISK_ON: "Apetite por risco elevado nos mercados globais",
            GlobalRiskSentiment.RISK_OFF: "Aversão ao risco predomina nos mercados globais",
            GlobalRiskSentiment.NEUTRAL: "Mercados globais sem direção clara",
        }

        impact_text = {
            "POSITIVE": "Cenário favorável para ativos brasileiros",
            "NEGATIVE": "Cenário desafiador para ativos brasileiros",
            "NEUTRAL": "Impacto neutro para ativos brasileiros",
        }

        return f"{sentiment_text[risk_sentiment]}. {impact_text[impact_on_brazil]}."

    def _extract_key_points(
        self,
        risk_sentiment: GlobalRiskSentiment,
        impact_on_brazil: str,
        bewz39: Optional[Decimal] = None,
    ) -> list[str]:
        """Extrai pontos-chave da analise macro."""
        points = []

        if bewz39:
            points.append(f"📡 EWZ (BEWZ39) monitorado em real-time: R$ {bewz39:,.2f}")

        if risk_sentiment == GlobalRiskSentiment.RISK_OFF:
            points.append("⚠️ Fluxo de capital para ativos seguros (Treasuries, Dollar)")
            points.append("📉 Pressão vendedora em mercados emergentes")
        elif risk_sentiment == GlobalRiskSentiment.RISK_ON:
            points.append("✅ Fluxo de capital para mercados emergentes")
            points.append("📈 Busca por retornos mais altos")

        if impact_on_brazil == "NEGATIVE":
            points.append("🇧🇷 Brasil: Expectativa de saída de capital estrangeiro")
        elif impact_on_brazil == "POSITIVE":
            points.append("🇧🇷 Brasil: Expectativa de entrada de capital estrangeiro")

        return points

    def get_trading_bias_from_macro(self) -> str:
        """
        Obtem vies de trading baseado nas condicoes macro.

        Returns:
            "BULLISH", "BEARISH", ou "NEUTRAL"
        """
        if not self._last_analysis:
            return "NEUTRAL"

        if self._last_analysis.impact_on_brazil == "POSITIVE":
            return "BULLISH"
        elif self._last_analysis.impact_on_brazil == "NEGATIVE":
            return "BEARISH"

        return "NEUTRAL"
