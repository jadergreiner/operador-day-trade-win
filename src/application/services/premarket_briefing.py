"""
Pre-Market Briefing Service - Morning market analysis.

Analyzes overnight global markets and provides trading context for the day.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class GlobalMarketSnapshot:
    """Snapshot of overnight global markets."""

    # US Markets (close previous day)
    sp500_change: Optional[Decimal] = None
    nasdaq_change: Optional[Decimal] = None
    dow_change: Optional[Decimal] = None

    # Asian Markets
    nikkei_change: Optional[Decimal] = None
    hang_seng_change: Optional[Decimal] = None
    shanghai_change: Optional[Decimal] = None

    # European Markets (if open)
    dax_change: Optional[Decimal] = None
    ftse_change: Optional[Decimal] = None

    # Futures (current pre-market)
    sp500_futures: Optional[Decimal] = None
    nasdaq_futures: Optional[Decimal] = None

    # Commodities
    oil_wti_price: Optional[Decimal] = None
    oil_change: Optional[Decimal] = None
    gold_price: Optional[Decimal] = None

    # Forex
    dxy_dollar: Optional[Decimal] = None
    usd_brl: Optional[Decimal] = None
    usd_brl_change: Optional[Decimal] = None

    # Fear Gauge
    vix_level: Optional[Decimal] = None

    # Treasuries
    us_10y_yield: Optional[Decimal] = None


@dataclass
class MarketDrivers:
    """Key market drivers for the day."""

    primary_driver: str
    secondary_drivers: list[str]
    risk_events: list[str]
    economic_data: list[str]


@dataclass
class BrazilImpact:
    """Assessment of impact on Brazil."""

    overall_sentiment: str  # POSITIVE, NEGATIVE, NEUTRAL
    capital_flow_expectation: str  # INFLOW, OUTFLOW, NEUTRAL
    ibovespa_bias: str  # UP, DOWN, MIXED
    win_bias: str  # BULLISH, BEARISH, NEUTRAL
    key_factors: list[str]


@dataclass
class PreMarketBriefing:
    """Complete pre-market briefing."""

    timestamp: datetime
    date: str

    # Market Overview
    global_markets: GlobalMarketSnapshot
    market_drivers: MarketDrivers
    brazil_impact: BrazilImpact

    # Executive Summary
    headline: str
    summary: str
    trading_bias: str  # BULLISH, BEARISH, NEUTRAL, CAUTIOUS
    confidence: Decimal

    # Key Points
    bullish_factors: list[str]
    bearish_factors: list[str]
    watch_points: list[str]

    # Recommendations
    strategy_recommendation: str
    risk_level: str


class PreMarketBriefingService:
    """
    Service for generating pre-market briefings.

    Analyzes overnight global markets and provides context for the day.
    """

    def generate_briefing(
        self,
        # In production, these would be fetched from APIs
        sp500_change: Optional[Decimal] = None,
        nasdaq_change: Optional[Decimal] = None,
        asia_sentiment: str = "MIXED",
        us_futures: Optional[Decimal] = None,
        dollar_index: Optional[Decimal] = None,
        vix: Optional[Decimal] = None,
    ) -> PreMarketBriefing:
        """
        Generate complete pre-market briefing.

        In production, this would fetch real-time data from:
        - Bloomberg/Reuters APIs
        - Yahoo Finance
        - Investing.com
        - Economic calendars
        """
        now = datetime.now()

        # Simulate realistic market data (in production, fetch real data)
        global_markets = self._get_global_markets(
            sp500_change=sp500_change,
            nasdaq_change=nasdaq_change,
            us_futures=us_futures,
            dollar_index=dollar_index,
            vix=vix,
        )

        # Identify market drivers
        market_drivers = self._identify_market_drivers(global_markets)

        # Assess Brazil impact
        brazil_impact = self._assess_brazil_impact(
            global_markets=global_markets,
            us_futures=us_futures,
            asia_sentiment=asia_sentiment,
        )

        # Generate executive summary
        headline = self._generate_headline(
            global_markets=global_markets,
            brazil_impact=brazil_impact,
        )

        summary = self._generate_summary(
            global_markets=global_markets,
            market_drivers=market_drivers,
            brazil_impact=brazil_impact,
        )

        # Determine trading bias
        trading_bias = brazil_impact.win_bias
        confidence = self._calculate_confidence(global_markets)

        # Extract factors
        bullish_factors = self._extract_bullish_factors(
            global_markets=global_markets,
            brazil_impact=brazil_impact,
        )

        bearish_factors = self._extract_bearish_factors(
            global_markets=global_markets,
            brazil_impact=brazil_impact,
        )

        watch_points = self._extract_watch_points(market_drivers)

        # Generate recommendation
        strategy_recommendation = self._generate_strategy_recommendation(
            trading_bias=trading_bias,
            confidence=confidence,
        )

        risk_level = self._assess_risk_level(global_markets, vix)

        briefing = PreMarketBriefing(
            timestamp=now,
            date=now.strftime("%Y-%m-%d"),
            global_markets=global_markets,
            market_drivers=market_drivers,
            brazil_impact=brazil_impact,
            headline=headline,
            summary=summary,
            trading_bias=trading_bias,
            confidence=confidence,
            bullish_factors=bullish_factors,
            bearish_factors=bearish_factors,
            watch_points=watch_points,
            strategy_recommendation=strategy_recommendation,
            risk_level=risk_level,
        )

        return briefing

    def _get_global_markets(
        self,
        sp500_change: Optional[Decimal],
        nasdaq_change: Optional[Decimal],
        us_futures: Optional[Decimal],
        dollar_index: Optional[Decimal],
        vix: Optional[Decimal],
    ) -> GlobalMarketSnapshot:
        """Get global market snapshot."""
        # In production, fetch from APIs
        # For now, use provided data or simulate realistic values

        return GlobalMarketSnapshot(
            sp500_change=sp500_change or Decimal("0.4"),
            nasdaq_change=nasdaq_change or Decimal("0.6"),
            dow_change=Decimal("0.3"),
            nikkei_change=Decimal("1.2"),
            hang_seng_change=Decimal("-0.5"),
            shanghai_change=Decimal("-0.8"),
            dax_change=Decimal("0.5"),
            ftse_change=Decimal("0.3"),
            sp500_futures=us_futures or Decimal("0.2"),
            nasdaq_futures=Decimal("0.3"),
            oil_wti_price=Decimal("73.5"),
            oil_change=Decimal("1.2"),
            gold_price=Decimal("2650"),
            dxy_dollar=dollar_index or Decimal("104.5"),
            usd_brl=Decimal("5.85"),
            usd_brl_change=Decimal("-0.3"),
            vix_level=vix or Decimal("16.8"),
            us_10y_yield=Decimal("4.45"),
        )

    def _identify_market_drivers(
        self, markets: GlobalMarketSnapshot
    ) -> MarketDrivers:
        """Identify key market drivers."""
        primary = "Dados econômicos dos EUA"
        secondary = [
            "Política monetária do Fed",
            "Crescimento da China",
            "Preços de commodities",
        ]

        risk_events = [
            "Decisão de juros do Fed (próxima semana)",
            "Dados de inflação PCE",
        ]

        economic_data = [
            "Payroll nos EUA (sexta-feira)",
            "PMI Manufacturing",
        ]

        return MarketDrivers(
            primary_driver=primary,
            secondary_drivers=secondary,
            risk_events=risk_events,
            economic_data=economic_data,
        )

    def _assess_brazil_impact(
        self,
        global_markets: GlobalMarketSnapshot,
        us_futures: Optional[Decimal],
        asia_sentiment: str,
    ) -> BrazilImpact:
        """Assess impact on Brazil."""
        # Determine sentiment
        if (
            global_markets.sp500_futures
            and global_markets.sp500_futures > Decimal("0.3")
        ):
            sentiment = "POSITIVE"
            capital_flow = "INFLOW"
            ibov_bias = "UP"
            win_bias = "BULLISH"
        elif (
            global_markets.sp500_futures
            and global_markets.sp500_futures < Decimal("-0.3")
        ):
            sentiment = "NEGATIVE"
            capital_flow = "OUTFLOW"
            ibov_bias = "DOWN"
            win_bias = "BEARISH"
        else:
            sentiment = "NEUTRAL"
            capital_flow = "NEUTRAL"
            ibov_bias = "MIXED"
            win_bias = "NEUTRAL"

        # Dollar impact
        key_factors = []
        if (
            global_markets.usd_brl_change
            and global_markets.usd_brl_change < Decimal("-0.2")
        ):
            key_factors.append("Dólar em queda favorece ativos brasileiros")
        elif (
            global_markets.usd_brl_change
            and global_markets.usd_brl_change > Decimal("0.2")
        ):
            key_factors.append("Dólar em alta pressiona ativos brasileiros")

        # Commodity impact
        if (
            global_markets.oil_change
            and global_markets.oil_change > Decimal("1.0")
        ):
            key_factors.append("Petróleo em alta beneficia Petrobras/Ibov")

        # Risk sentiment
        if global_markets.vix_level and global_markets.vix_level < Decimal("18"):
            key_factors.append("VIX baixo indica apetite por risco")
        elif global_markets.vix_level and global_markets.vix_level > Decimal("25"):
            key_factors.append("VIX elevado indica aversão ao risco")

        return BrazilImpact(
            overall_sentiment=sentiment,
            capital_flow_expectation=capital_flow,
            ibovespa_bias=ibov_bias,
            win_bias=win_bias,
            key_factors=key_factors,
        )

    def _generate_headline(
        self,
        global_markets: GlobalMarketSnapshot,
        brazil_impact: BrazilImpact,
    ) -> str:
        """Generate briefing headline."""
        if brazil_impact.overall_sentiment == "POSITIVE":
            return "Mercados globais positivos favorecem Brasil; abertura em alta esperada"
        elif brazil_impact.overall_sentiment == "NEGATIVE":
            return "Aversão ao risco global pressiona emergentes; cautela na abertura"
        else:
            return "Mercados globais mistos; abertura sem direção clara"

    def _generate_summary(
        self,
        global_markets: GlobalMarketSnapshot,
        market_drivers: MarketDrivers,
        brazil_impact: BrazilImpact,
    ) -> str:
        """Generate executive summary."""
        us_text = (
            f"S&P500 fechou com {global_markets.sp500_change:+.1f}%, "
            f"Nasdaq {global_markets.nasdaq_change:+.1f}%."
        )

        asia_text = f"Ásia mista: Nikkei {global_markets.nikkei_change:+.1f}%, "
        asia_text += f"Hang Seng {global_markets.hang_seng_change:+.1f}%."

        futures_text = f"Futuros dos EUA {global_markets.sp500_futures:+.1f}%."

        brazil_text = f"Para o Brasil, expectativa de {brazil_impact.capital_flow_expectation.lower()}."

        return f"{us_text} {asia_text} {futures_text} {brazil_text}"

    def _calculate_confidence(self, markets: GlobalMarketSnapshot) -> Decimal:
        """Calculate confidence in the assessment."""
        # Higher confidence when markets are aligned
        if markets.sp500_futures and abs(markets.sp500_futures) > Decimal("0.5"):
            return Decimal("0.80")
        elif markets.sp500_futures and abs(markets.sp500_futures) > Decimal("0.2"):
            return Decimal("0.65")
        else:
            return Decimal("0.50")

    def _extract_bullish_factors(
        self,
        global_markets: GlobalMarketSnapshot,
        brazil_impact: BrazilImpact,
    ) -> list[str]:
        """Extract bullish factors."""
        factors = []

        if global_markets.sp500_futures and global_markets.sp500_futures > Decimal("0"):
            factors.append(
                f"Futuros dos EUA positivos (+{global_markets.sp500_futures:.2f}%)"
            )

        if (
            global_markets.usd_brl_change
            and global_markets.usd_brl_change < Decimal("0")
        ):
            factors.append(
                f"Dólar em queda ({global_markets.usd_brl_change:+.2f}%)"
            )

        if global_markets.vix_level and global_markets.vix_level < Decimal("18"):
            factors.append(f"VIX baixo ({global_markets.vix_level:.1f})")

        if global_markets.oil_change and global_markets.oil_change > Decimal("1"):
            factors.append(
                f"Petróleo em alta (+{global_markets.oil_change:.1f}%)"
            )

        return factors if factors else ["Nenhum fator bullish significativo"]

    def _extract_bearish_factors(
        self,
        global_markets: GlobalMarketSnapshot,
        brazil_impact: BrazilImpact,
    ) -> list[str]:
        """Extract bearish factors."""
        factors = []

        if (
            global_markets.sp500_futures
            and global_markets.sp500_futures < Decimal("0")
        ):
            factors.append(
                f"Futuros dos EUA negativos ({global_markets.sp500_futures:+.2f}%)"
            )

        if (
            global_markets.usd_brl_change
            and global_markets.usd_brl_change > Decimal("0")
        ):
            factors.append(
                f"Dólar em alta ({global_markets.usd_brl_change:+.2f}%)"
            )

        if global_markets.vix_level and global_markets.vix_level > Decimal("22"):
            factors.append(f"VIX elevado ({global_markets.vix_level:.1f})")

        if (
            global_markets.shanghai_change
            and global_markets.shanghai_change < Decimal("-1")
        ):
            factors.append(
                f"China em queda ({global_markets.shanghai_change:+.1f}%)"
            )

        return factors if factors else ["Nenhum fator bearish significativo"]

    def _extract_watch_points(self, drivers: MarketDrivers) -> list[str]:
        """Extract key watch points."""
        points = []

        points.append(f"Driver principal: {drivers.primary_driver}")

        if drivers.risk_events:
            points.append(f"Atenção: {drivers.risk_events[0]}")

        if drivers.economic_data:
            points.append(f"Dados econômicos: {drivers.economic_data[0]}")

        return points

    def _generate_strategy_recommendation(
        self,
        trading_bias: str,
        confidence: Decimal,
    ) -> str:
        """Generate strategy recommendation."""
        if trading_bias == "BULLISH" and confidence > Decimal("0.7"):
            return "Buscar setups de compra em pullbacks. Favor tendência de alta."
        elif trading_bias == "BEARISH" and confidence > Decimal("0.7"):
            return "Buscar setups de venda em rallies. Favor tendência de baixa."
        elif trading_bias == "NEUTRAL":
            return "Mercado lateral. Operar ranges entre suporte e resistência."
        else:
            return "Cenário incerto. Aguardar confirmação de direção antes de operar."

    def _assess_risk_level(
        self,
        markets: GlobalMarketSnapshot,
        vix: Optional[Decimal],
    ) -> str:
        """Assess overall risk level."""
        if vix and vix > Decimal("25"):
            return "HIGH"
        elif vix and vix < Decimal("15"):
            return "LOW"
        else:
            return "MODERATE"
