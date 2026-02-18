"""Servico de Analise Fundamental - avaliacao economica do Brasil."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class BrazilRiskRating(str, Enum):
    """Classificacao de risco do Brasil para investidores estrangeiros."""

    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class FiscalHealth(str, Enum):
    """Avaliacao de saude fiscal."""

    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    CONCERNING = "CONCERNING"
    CRITICAL = "CRITICAL"


class CapitalFlow(str, Enum):
    """Direcao do fluxo de capital."""

    STRONG_INFLOW = "STRONG_INFLOW"
    MODERATE_INFLOW = "MODERATE_INFLOW"
    NEUTRAL = "NEUTRAL"
    MODERATE_OUTFLOW = "MODERATE_OUTFLOW"
    STRONG_OUTFLOW = "STRONG_OUTFLOW"


@dataclass
class BrazilFundamentals:
    """Analise fundamental da posicao economica do Brasil."""

    timestamp: datetime

    # Indicadores-chave
    selic_rate: Optional[Decimal]  # Taxa SELIC atual
    inflation_ipca: Optional[Decimal]  # IPCA anual
    gdp_growth: Optional[Decimal]  # Crescimento PIB %
    unemployment_rate: Optional[Decimal]  # Desemprego %
    debt_to_gdp: Optional[Decimal]  # Razao divida/PIB

    # Metricas de mercado
    country_risk_embi: Optional[int]  # Spread EMBI+ Brasil
    brl_usd_rate: Optional[Decimal]  # Taxa de cambio USD/BRL
    bovespa_level: Optional[int]  # Nivel do Ibovespa

    # Investimento estrangeiro
    capital_flow: CapitalFlow
    foreign_interest: str  # "HIGH", "MODERATE", "LOW"

    # Avaliacao de risco
    brazil_risk_rating: BrazilRiskRating
    fiscal_health: FiscalHealth

    # Analise
    summary: str
    key_factors: list[str]
    trading_implications: str


class FundamentalAnalysisService:
    """
    Servico de analise fundamental economica do Brasil.

    Avalia como investidores estrangeiros veem o Brasil e a dinamica do fluxo de capital.
    """

    def __init__(self):
        """Inicializa servico de analise fundamental."""
        self._last_analysis: Optional[BrazilFundamentals] = None

    def analyze_brazil_fundamentals(
        self,
        selic: Optional[Decimal] = None,
        ipca: Optional[Decimal] = None,
        usd_brl: Optional[Decimal] = None,
        embi_spread: Optional[int] = None,
    ) -> BrazilFundamentals:
        """
        Analisa a posicao fundamental do Brasil.

        Em producao, buscaria dados ao vivo de:
        - API do Banco Central do Brasil
        - IBGE
        - Bloomberg
        - B3

        Args:
            selic: Taxa SELIC atual
            ipca: Inflacao atual (IPCA)
            usd_brl: Taxa de cambio USD/BRL
            embi_spread: Spread EMBI+ Brasil (pontos base)

        Returns:
            BrazilFundamentals com analise completa
        """
        # Avaliar fluxo de capital com base nos indicadores
        capital_flow = self._assess_capital_flow(
            embi_spread=embi_spread,
            usd_brl=usd_brl,
        )

        # Avaliar risco Brasil para investidores estrangeiros
        risk_rating = self._assess_brazil_risk(
            embi_spread=embi_spread,
            selic=selic,
        )

        # Avaliar saude fiscal
        fiscal_health = self._assess_fiscal_health()

        # Determinar nivel de interesse estrangeiro
        foreign_interest = self._assess_foreign_interest(
            capital_flow=capital_flow,
            risk_rating=risk_rating,
        )

        # Gerar resumo e implicacoes
        summary = self._generate_fundamental_summary(
            capital_flow=capital_flow,
            risk_rating=risk_rating,
            selic=selic,
        )

        key_factors = self._extract_key_factors(
            capital_flow=capital_flow,
            risk_rating=risk_rating,
            selic=selic,
            ipca=ipca,
        )

        trading_implications = self._generate_trading_implications(
            capital_flow=capital_flow,
            foreign_interest=foreign_interest,
        )

        fundamentals = BrazilFundamentals(
            timestamp=datetime.now(),
            selic_rate=selic,
            inflation_ipca=ipca,
            gdp_growth=None,  # Seria buscado de API
            unemployment_rate=None,  # Seria buscado de API
            debt_to_gdp=None,  # Seria buscado de API
            country_risk_embi=embi_spread,
            brl_usd_rate=usd_brl,
            bovespa_level=None,  # Seria buscado de API
            capital_flow=capital_flow,
            foreign_interest=foreign_interest,
            brazil_risk_rating=risk_rating,
            fiscal_health=fiscal_health,
            summary=summary,
            key_factors=key_factors,
            trading_implications=trading_implications,
        )

        self._last_analysis = fundamentals
        return fundamentals

    def _assess_capital_flow(
        self,
        embi_spread: Optional[int],
        usd_brl: Optional[Decimal],
    ) -> CapitalFlow:
        """Avalia direcao do fluxo de capital."""
        # Spread EMBI: < 200 e risco baixo, > 400 e risco alto
        # USD/BRL subindo sugere saida de capital

        if embi_spread:
            if embi_spread < 200:
                return CapitalFlow.STRONG_INFLOW
            elif embi_spread < 300:
                return CapitalFlow.MODERATE_INFLOW
            elif embi_spread > 400:
                return CapitalFlow.MODERATE_OUTFLOW
            elif embi_spread > 500:
                return CapitalFlow.STRONG_OUTFLOW

        return CapitalFlow.NEUTRAL

    def _assess_brazil_risk(
        self,
        embi_spread: Optional[int],
        selic: Optional[Decimal],
    ) -> BrazilRiskRating:
        """Avalia rating de risco do Brasil."""
        if embi_spread:
            if embi_spread < 200:
                return BrazilRiskRating.LOW
            elif embi_spread < 300:
                return BrazilRiskRating.MODERATE
            elif embi_spread < 400:
                return BrazilRiskRating.HIGH
            else:
                return BrazilRiskRating.VERY_HIGH

        return BrazilRiskRating.MODERATE

    def _assess_fiscal_health(self) -> FiscalHealth:
        """Avalia saude fiscal do Brasil."""
        # Em producao, analisaria:
        # - Superavit/deficit primario
        # - Trajetoria da divida
        # - Cumprimento do arcabouco fiscal
        # - Gastos do governo

        # Placeholder - seria determinado por dados reais
        return FiscalHealth.CONCERNING

    def _assess_foreign_interest(
        self,
        capital_flow: CapitalFlow,
        risk_rating: BrazilRiskRating,
    ) -> str:
        """Avalia nivel de interesse de investidores estrangeiros."""
        if capital_flow in [CapitalFlow.STRONG_INFLOW, CapitalFlow.MODERATE_INFLOW]:
            return "HIGH"
        elif capital_flow in [
            CapitalFlow.MODERATE_OUTFLOW,
            CapitalFlow.STRONG_OUTFLOW,
        ]:
            return "LOW"
        return "MODERATE"

    def _generate_fundamental_summary(
        self,
        capital_flow: CapitalFlow,
        risk_rating: BrazilRiskRating,
        selic: Optional[Decimal],
    ) -> str:
        """Gera resumo fundamental legivel."""
        flow_text = {
            CapitalFlow.STRONG_INFLOW: "Forte entrada de capital estrangeiro",
            CapitalFlow.MODERATE_INFLOW: "Entrada moderada de capital estrangeiro",
            CapitalFlow.NEUTRAL: "Fluxo de capital neutro",
            CapitalFlow.MODERATE_OUTFLOW: "Saída moderada de capital estrangeiro",
            CapitalFlow.STRONG_OUTFLOW: "Forte saída de capital estrangeiro",
        }

        risk_text = {
            BrazilRiskRating.VERY_LOW: "risco muito baixo",
            BrazilRiskRating.LOW: "risco baixo",
            BrazilRiskRating.MODERATE: "risco moderado",
            BrazilRiskRating.HIGH: "risco elevado",
            BrazilRiskRating.VERY_HIGH: "risco muito elevado",
        }

        selic_text = f" SELIC em {selic}%." if selic else ""

        return (
            f"{flow_text[capital_flow]}. "
            f"Investidores avaliam Brasil com {risk_text[risk_rating]}.{selic_text}"
        )

    def _extract_key_factors(
        self,
        capital_flow: CapitalFlow,
        risk_rating: BrazilRiskRating,
        selic: Optional[Decimal],
        ipca: Optional[Decimal],
    ) -> list[str]:
        """Extrai fatores fundamentais chave."""
        factors = []

        # Fluxo de capital
        if capital_flow in [CapitalFlow.STRONG_INFLOW, CapitalFlow.MODERATE_INFLOW]:
            factors.append("💰 Capital estrangeiro fluindo para o Brasil")
        elif capital_flow in [
            CapitalFlow.MODERATE_OUTFLOW,
            CapitalFlow.STRONG_OUTFLOW,
        ]:
            factors.append("⚠️ Capital estrangeiro saindo do Brasil")

        # Taxas de juros
        if selic and selic > Decimal("10"):
            factors.append(f"📊 SELIC elevada ({selic}%) atrai capital carry trade")
        elif selic and selic < Decimal("8"):
            factors.append(f"📉 SELIC baixa ({selic}%) reduz atratividade")

        # Inflacao
        if ipca and ipca > Decimal("6"):
            factors.append(f"🔴 Inflação acima da meta ({ipca}%)")
        elif ipca and ipca < Decimal("4.5"):
            factors.append(f"🟢 Inflação controlada ({ipca}%)")

        # Percepcao de risco
        if risk_rating in [BrazilRiskRating.HIGH, BrazilRiskRating.VERY_HIGH]:
            factors.append("⚠️ Percepção de risco elevada afasta investidores")

        return factors

    def _generate_trading_implications(
        self,
        capital_flow: CapitalFlow,
        foreign_interest: str,
    ) -> str:
        """Gera implicacoes de trading a partir dos fundamentos."""
        if capital_flow in [CapitalFlow.STRONG_INFLOW, CapitalFlow.MODERATE_INFLOW]:
            return (
                "BULLISH: Entrada de capital favorece ativos brasileiros (Ibov, WIN)"
            )
        elif capital_flow in [
            CapitalFlow.MODERATE_OUTFLOW,
            CapitalFlow.STRONG_OUTFLOW,
        ]:
            return "BEARISH: Saída de capital pressiona ativos brasileiros"

        return "NEUTRAL: Aguardar direção clara do fluxo de capital"

    def get_trading_bias_from_fundamentals(self) -> str:
        """
        Retorna bias de trading baseado na analise fundamental.

        Returns:
            "BULLISH", "BEARISH" ou "NEUTRAL"
        """
        if not self._last_analysis:
            return "NEUTRAL"

        if self._last_analysis.capital_flow in [
            CapitalFlow.STRONG_INFLOW,
            CapitalFlow.MODERATE_INFLOW,
        ]:
            return "BULLISH"
        elif self._last_analysis.capital_flow in [
            CapitalFlow.MODERATE_OUTFLOW,
            CapitalFlow.STRONG_OUTFLOW,
        ]:
            return "BEARISH"

        return "NEUTRAL"
