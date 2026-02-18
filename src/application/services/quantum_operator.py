"""
Motor de Decisao - O Cerebro do Operador Quantico.

Sintetiza analise macro, fundamentalista, sentimento e tecnica
para tomar decisoes inteligentes de trading como Head Financeiro.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.application.services.fundamental_analysis import (
    BrazilFundamentals,
    FundamentalAnalysisService,
)
from src.application.services.macro_analysis import (
    MacroAnalysisService,
    MacroSnapshot,
)
from src.application.services.macro_score.engine import (
    MacroScoreEngine,
    MacroScoreResult,
)
from src.application.services.sentiment_analysis import (
    SentimentAnalysis,
    SentimentAnalysisService,
)
from src.application.services.technical_analysis import (
    EntryPoint,
    TechnicalAnalysis,
    TechnicalAnalysisService,
)
from src.domain.enums.trading_enums import TradeSignal
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter


@dataclass
class MarketContext:
    """Contexto completo de mercado de todas as dimensoes de analise."""

    macro: MacroSnapshot
    fundamental: BrazilFundamentals
    sentiment: SentimentAnalysis
    technical: TechnicalAnalysis


@dataclass
class TradingDecision:
    """Decisao final de trading do Operador Quantico."""

    timestamp: datetime
    symbol: Symbol

    # Decisao
    action: TradeSignal  # BUY, SELL, HOLD
    confidence: Decimal  # 0-1
    urgency: str  # "IMMEDIATE", "OPPORTUNISTIC", "PATIENT", "AVOID"

    # Detalhes de entrada (se acao for BUY/SELL)
    recommended_entry: Optional[EntryPoint]

    # Analise Multi-dimensional
    macro_bias: str  # BULLISH, BEARISH, NEUTRAL
    fundamental_bias: str
    sentiment_bias: str
    technical_bias: str

    # Score de alinhamento (quanto todas as dimensoes concordam)
    alignment_score: Decimal  # 0-1 (1 = alinhamento perfeito)

    # Avaliacao de Risco
    risk_level: str  # LOW, MODERATE, HIGH
    market_regime: str  # TRENDING, RANGING, VOLATILE, UNCERTAIN

    # Raciocinio
    primary_reason: str
    supporting_factors: list[str]
    warning_factors: list[str]

    # Resumo Executivo
    executive_summary: str


class QuantumOperatorEngine:
    """
    O Operador Quantico - Motor de Decisao do Head Financeiro.

    Sintetiza e relaciona analise macro, fundamentalista, sentimento e tecnica
    para tomar decisoes de trading de nivel mundial.

    Utiliza o MacroScoreEngine (85 itens) para analise macro em tempo real
    quando um MT5Adapter esta disponivel. Caso contrario, usa o
    MacroAnalysisService legado como fallback.
    """

    def __init__(
        self,
        mt5_adapter: Optional[MT5Adapter] = None,
        macro_score_repository=None,
        rl_persistence_service=None,
    ):
        """Inicializa o Operador Quantico.

        Args:
            mt5_adapter: Adaptador MT5 para macro score em tempo real.
                Se fornecido, habilita o MacroScoreEngine (85 itens).
                Se None, usa MacroAnalysisService legado.
            macro_score_repository: Repositorio para persistencia do macro score.
            rl_persistence_service: Servico de persistencia para RL.
        """
        self._rl_service = rl_persistence_service
        # Macro: usa MacroScoreEngine se MT5 disponivel, senao fallback legado
        self._mt5_adapter = mt5_adapter
        if mt5_adapter is not None:
            self.macro_score_engine = MacroScoreEngine(
                mt5_adapter=mt5_adapter,
                repository=macro_score_repository,
            )
            self.macro_service = None  # Nao usa o legado
        else:
            self.macro_score_engine = None
            self.macro_service = MacroAnalysisService()

        self.fundamental_service = FundamentalAnalysisService()
        self.sentiment_service = SentimentAnalysisService()
        self.technical_service = TechnicalAnalysisService()

        self._last_decision: Optional[TradingDecision] = None
        self._last_macro_score: Optional[MacroScoreResult] = None

    def analyze_and_decide(
        self,
        symbol: Symbol,
        candles: list,
        # Inputs macro (seriam obtidos de APIs em producao)
        us_futures: Optional[Decimal] = None,
        treasury_yield: Optional[Decimal] = None,
        dollar_index: Optional[Decimal] = None,
        vix: Optional[Decimal] = None,
        # Inputs Brasil
        selic: Optional[Decimal] = None,
        ipca: Optional[Decimal] = None,
        usd_brl: Optional[Decimal] = None,
        embi_spread: Optional[int] = None,
        # Inputs de correlacao especifica
        petr4: Optional[Decimal] = None,
        vale3: Optional[Decimal] = None,
        bewz39: Optional[Decimal] = None,
    ) -> TradingDecision:
        """
        Analise completa e decisao como Operador Quantico.

        Este e o METODO PRINCIPAL que sintetiza tudo.

        Args:
            symbol: Simbolo de trading
            candles: Dados de mercado
            [Diversos parametros macro e fundamentalistas]

        Returns:
            TradingDecision com raciocinio completo
        """
        # 1. ANALISE MACRO - Usa MacroScoreEngine (85 itens) ou legado
        if self.macro_score_engine is not None:
            # NOVO: MacroScoreEngine com 85 itens em tempo real
            macro_score_result = self.macro_score_engine.analyze()
            self._last_macro_score = macro_score_result
            # Criar MacroSnapshot compativel a partir do score
            macro = self._macro_score_to_snapshot(macro_score_result)
        else:
            # LEGADO: MacroAnalysisService com dados manuais
            macro = self.macro_service.analyze_current_macro_conditions(
                us_futures=us_futures,
                treasury_yield=treasury_yield,
                dollar_index=dollar_index,
                vix=vix,
                bewz39=bewz39,
            )

        # 2. ANALISE FUNDAMENTALISTA - Brasil no mundo
        fundamental = self.fundamental_service.analyze_brazil_fundamentals(
            selic=selic,
            ipca=ipca,
            usd_brl=usd_brl,
            embi_spread=embi_spread,
        )

        # 3. ANALISE DE SENTIMENTO - Sentimento de mercado HOJE
        sentiment = self.sentiment_service.analyze_market_sentiment(
            candles=candles,
            symbol=symbol,
            petr4=petr4,
            vale3=vale3,
        )

        # 4. ANALISE TECNICA - Melhores pontos de entrada
        technical = self.technical_service.analyze_technical(
            candles=candles,
            symbol=symbol,
        )

        # 5. SINTETIZAR - A magia acontece aqui
        decision = self._synthesize_decision(
            symbol=symbol,
            macro=macro,
            fundamental=fundamental,
            sentiment=sentiment,
            technical=technical,
        )

        self._last_decision = decision

        # 6. PERSISTIR EPISODIO RL - Dados para aprendizagem por reforco
        if self._rl_service:
            try:
                self._rl_service.persist_quantum_decision(
                    decision=decision,
                    macro_score_result=self._last_macro_score,
                    technical=technical,
                    sentiment=sentiment,
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    f"Erro ao persistir episodio RL: {e}"
                )

        return decision

    def _synthesize_decision(
        self,
        symbol: Symbol,
        macro: MacroSnapshot,
        fundamental: BrazilFundamentals,
        sentiment: SentimentAnalysis,
        technical: TechnicalAnalysis,
    ) -> TradingDecision:
        """
        METODO PRINCIPAL DE SINTESE.

        Aqui e onde o Operador Quantico pensa como um Head Financeiro,
        ponderando todas as dimensoes e tomando a melhor decisao.
        """
        # Obter vies de cada dimensao
        if self.macro_score_engine is not None:
            macro_bias = self.macro_score_engine.get_trading_bias()
        else:
            macro_bias = self.macro_service.get_trading_bias_from_macro()
        fundamental_bias = (
            self.fundamental_service.get_trading_bias_from_fundamentals()
        )
        sentiment_bias = self.sentiment_service.get_trading_bias_from_sentiment()
        technical_bias = technical.technical_bias

        # Calcula alinhamento (quanto todas as dimensoes concordam)
        alignment_score = self._calculate_alignment(
            macro_bias, fundamental_bias, sentiment_bias, technical_bias
        )

        # Determina o regime de mercado atual
        market_regime = self._determine_market_regime(
            sentiment=sentiment,
            technical=technical,
        )

        # Avalia nivel de risco
        risk_level = self._assess_overall_risk(
            macro=macro,
            fundamental=fundamental,
            sentiment=sentiment,
            alignment=alignment_score,
        )

        # Toma a decisao
        action, confidence, urgency = self._make_final_decision(
            macro_bias=macro_bias,
            fundamental_bias=fundamental_bias,
            sentiment_bias=sentiment_bias,
            technical_bias=technical_bias,
            technical=technical,
            alignment=alignment_score,
            risk_level=risk_level,
            market_regime=market_regime,
        )

        # Gera raciocinio
        primary_reason = self._generate_primary_reason(
            action=action,
            macro_bias=macro_bias,
            fundamental_bias=fundamental_bias,
            sentiment_bias=sentiment_bias,
            technical=technical,
            alignment=alignment_score,
        )

        supporting_factors = self._extract_supporting_factors(
            macro=macro,
            fundamental=fundamental,
            sentiment=sentiment,
            technical=technical,
            action=action,
        )

        warning_factors = self._extract_warning_factors(
            macro=macro,
            fundamental=fundamental,
            sentiment=sentiment,
            risk_level=risk_level,
            alignment=alignment_score,
        )

        # Resumo executivo
        executive_summary = self._generate_executive_summary(
            action=action,
            confidence=confidence,
            primary_reason=primary_reason,
            alignment=alignment_score,
            risk_level=risk_level,
        )

        decision = TradingDecision(
            timestamp=datetime.now(),
            symbol=symbol,
            action=action,
            confidence=confidence,
            urgency=urgency,
            recommended_entry=technical.best_entry,
            macro_bias=macro_bias,
            fundamental_bias=fundamental_bias,
            sentiment_bias=sentiment_bias,
            technical_bias=technical_bias,
            alignment_score=alignment_score,
            risk_level=risk_level,
            market_regime=market_regime,
            primary_reason=primary_reason,
            supporting_factors=supporting_factors,
            warning_factors=warning_factors,
            executive_summary=executive_summary,
        )

        return decision

    def _calculate_alignment(
        self, macro: str, fundamental: str, sentiment: str, technical: str
    ) -> Decimal:
        """
        Calcula alinhamento com pesos hierarquicos para DAY TRADE.

        MODELO DAY TRADE:
        - Sentimento (50%) + Técnica (30%) = 80% do peso (decisão intraday)
        - Fundamentos (15%) + Macro (5%) = 20% do peso (contexto/filtro)

        Quando Sentimento + Técnica alinham = core day trade ativo
        Fundamentos/Macro alinhados = "cereja do bolo" (aumenta confiança)
        Fundamentos/Macro contra = penalidade moderada (não veta operação)
        """
        # Pesos hierárquicos para day trade
        PESO_SENTIMENTO = Decimal("0.50")
        PESO_TECNICA = Decimal("0.30")
        PESO_FUNDAMENTOS = Decimal("0.15")
        PESO_MACRO = Decimal("0.05")

        # Determinar direção dominante (BULLISH vs BEARISH)
        biases = [macro, fundamental, sentiment, technical]
        bullish_count = sum(1 for b in biases if b == "BULLISH")
        bearish_count = sum(1 for b in biases if b == "BEARISH")

        # Direção target (mais votos)
        target_direction = "BULLISH" if bullish_count >= bearish_count else "BEARISH"

        # Calcular score ponderado baseado no alinhamento com target
        alignment_score = Decimal("0")

        if sentiment == target_direction:
            alignment_score += PESO_SENTIMENTO
        if technical == target_direction:
            alignment_score += PESO_TECNICA
        if fundamental == target_direction:
            alignment_score += PESO_FUNDAMENTOS
        elif fundamental == "NEUTRAL":
            alignment_score += PESO_FUNDAMENTOS / 2  # Neutro = metade do peso
        # Se contra: não soma (penalidade)

        if macro == target_direction:
            alignment_score += PESO_MACRO
        elif macro == "NEUTRAL":
            alignment_score += PESO_MACRO / 2

        return alignment_score

    def _determine_market_regime(
        self,
        sentiment: SentimentAnalysis,
        technical: TechnicalAnalysis,
    ) -> str:
        """Determina o regime de mercado atual."""
        if sentiment.volatility == "HIGH":
            return "VOLATILE"
        elif technical.trend_strength.value in ["STRONG", "VERY_STRONG"]:
            return "TRENDING"
        elif sentiment.market_condition.value == "RANGING":
            return "RANGING"

        return "UNCERTAIN"

    def _assess_overall_risk(
        self,
        macro: MacroSnapshot,
        fundamental: BrazilFundamentals,
        sentiment: SentimentAnalysis,
        alignment: Decimal,
    ) -> str:
        """Avalia nivel geral de risco para trading."""
        risk_factors = 0

        # Risco macro
        if macro.impact_on_brazil == "NEGATIVE":
            risk_factors += 1

        # Risco fundamentalista
        if fundamental.brazil_risk_rating.value in ["HIGH", "VERY_HIGH"]:
            risk_factors += 1

        # Risco de sentimento (volatilidade)
        if sentiment.volatility == "HIGH":
            risk_factors += 1

        # Risco de alinhamento (baixa confianca quando desalinhado)
        if alignment < Decimal("0.5"):
            risk_factors += 1

        if risk_factors == 0:
            return "LOW"
        elif risk_factors <= 1:
            return "MODERATE"
        else:
            return "HIGH"

    def _make_final_decision(
        self,
        macro_bias: str,
        fundamental_bias: str,
        sentiment_bias: str,
        technical_bias: str,
        technical: TechnicalAnalysis,
        alignment: Decimal,
        risk_level: str,
        market_regime: str,
    ) -> tuple[TradeSignal, Decimal, str]:
        """
        Toma a decisao final de trading com modelo hierarquico de DAY TRADE.

        NOVO MODELO (Day Trade Focus):
        - Sentimento (50%) + Técnica (30%) = CORE decision (80%)
        - Fundamentos (15%) + Macro (5%) = Context/Filter (20%)
        - Threshold: 65% (reduzido de 75% para day trade)

        Retorna: (action, confidence, urgency)
        """
        # High risk = HOLD (proteção fundamental)
        if risk_level == "HIGH":
            return TradeSignal.HOLD, Decimal("0.3"), "AVOID"

        # No technical setup = HOLD (sem ponto de entrada claro)
        # FIX: Confiança gradual baseada no alignment em vez de valor fixo 0.4
        if not technical.best_entry:
            partial_conf = max(Decimal("0.25"), alignment * Decimal("0.5"))
            return TradeSignal.HOLD, partial_conf, "PATIENT"

        # CORE DAY TRADE: Sentimento + Técnica devem alinhar
        sentiment_technical_aligned = (
            sentiment_bias == technical_bias and sentiment_bias != "NEUTRAL"
        )

        if not sentiment_technical_aligned:
            # Sentimento e Técnica brigando = confiança reduzida (não hardcoded)
            # FIX: Usar alignment como base, com penalidade por desalinhamento
            partial_conf = max(Decimal("0.30"), alignment * Decimal("0.6"))
            return TradeSignal.HOLD, partial_conf, "PATIENT"

        # Direção do trade (Sentimento + Técnica determinam)
        trade_direction = sentiment_bias  # BULLISH ou BEARISH

        # Calcular confiança usando alignment score (já ponderado)
        # Alignment já reflete os pesos hierárquicos
        confidence = alignment

        # Bônus por market regime favorável
        if market_regime == "TRENDING":
            confidence += Decimal("0.05")

        # Penalidade por volatilidade (mesmo alinhado, reduz confiança)
        if market_regime == "VOLATILE":
            confidence -= Decimal("0.10")

        # Cap confidence em 0.95
        confidence = min(confidence, Decimal("0.95"))

        # Determinar urgência
        urgency = "OPPORTUNISTIC"
        if alignment >= Decimal("0.90"):  # Tudo alinhado = cereja do bolo
            urgency = "IMMEDIATE"
        elif alignment >= Decimal("0.80"):  # Core + 1 dimensão
            urgency = "OPPORTUNISTIC"

        # Threshold para operar: 65% (day trade)
        THRESHOLD_DAY_TRADE = Decimal("0.65")

        if confidence < THRESHOLD_DAY_TRADE:
            return TradeSignal.HOLD, confidence, "PATIENT"

        # DECISÃO FINAL
        if trade_direction == "BULLISH":
            action = TradeSignal.BUY
        elif trade_direction == "BEARISH":
            action = TradeSignal.SELL
        else:
            # Fallback (não deveria chegar aqui)
            action = TradeSignal.HOLD
            confidence = Decimal("0.4")
            urgency = "PATIENT"

        return action, confidence, urgency

    def _generate_primary_reason(
        self,
        action: TradeSignal,
        macro_bias: str,
        fundamental_bias: str,
        sentiment_bias: str,
        technical: TechnicalAnalysis,
        alignment: Decimal,
    ) -> str:
        """Gera razao principal da decisao."""
        if action == TradeSignal.HOLD:
            if alignment < Decimal("0.5"):
                return "Sinais conflitantes entre as análises. Aguardando alinhamento."
            elif not technical.best_entry:
                return "Sem setup técnico claro no momento. Aguardando melhor ponto de entrada."
            else:
                return "Condições não favoráveis para operação no momento."

        # BUY ou SELL
        aligned_dimensions = []
        if macro_bias == action.value or (
            action == TradeSignal.BUY and macro_bias == "BULLISH"
        ):
            aligned_dimensions.append("Macro")
        if fundamental_bias == action.value or (
            action == TradeSignal.BUY and fundamental_bias == "BULLISH"
        ):
            aligned_dimensions.append("Fundamentos")
        if sentiment_bias == action.value or (
            action == TradeSignal.BUY and sentiment_bias == "BULLISH"
        ):
            aligned_dimensions.append("Sentimento")
        if technical.technical_bias == action.value or (
            action == TradeSignal.BUY and technical.technical_bias == "BULLISH"
        ):
            aligned_dimensions.append("Técnica")

        dimensions_text = ", ".join(aligned_dimensions)

        if alignment >= Decimal("0.75"):
            return f"Forte alinhamento entre {dimensions_text} favorecendo {action.value}"
        else:
            return f"Convergência de {dimensions_text} com setup técnico identificado"

    def _extract_supporting_factors(
        self,
        macro: MacroSnapshot,
        fundamental: BrazilFundamentals,
        sentiment: SentimentAnalysis,
        technical: TechnicalAnalysis,
        action: TradeSignal,
    ) -> list[str]:
        """Extrai fatores que suportam a decisao."""
        factors = []

        # Fatores macro
        for point in macro.key_points:
            factors.append(f"🌍 Macro: {point}")

        # Fatores fundamentalistas
        for factor in fundamental.key_factors[:2]:
            factors.append(f"🇧🇷 Fundamentos: {factor}")

        # Fatores de sentimento
        for signal in sentiment.key_signals[:2]:
            factors.append(f"📊 Sentimento: {signal}")

        # Fatores tecnicos
        if technical.best_entry and action != TradeSignal.HOLD:
            factors.append(
                f"📈 Técnica: {technical.best_entry.reason} - R/R {technical.best_entry.risk_reward_ratio:.2f}"
            )

        return factors[:5]  # Top 5 fatores

    def _extract_warning_factors(
        self,
        macro: MacroSnapshot,
        fundamental: BrazilFundamentals,
        sentiment: SentimentAnalysis,
        risk_level: str,
        alignment: Decimal,
    ) -> list[str]:
        """Extrai fatores de alerta a monitorar."""
        warnings = []

        # Alertas de risco
        if risk_level == "HIGH":
            warnings.append("⚠️ Nível de risco elevado no mercado")

        # Alerta de alinhamento
        if alignment < Decimal("0.5"):
            warnings.append("⚠️ Baixo alinhamento entre análises")

        # Alertas macro
        if macro.impact_on_brazil == "NEGATIVE":
            warnings.append("⚠️ Cenário macro desfavorável para Brasil")

        # Alertas fundamentalistas
        if fundamental.capital_flow.value in ["MODERATE_OUTFLOW", "STRONG_OUTFLOW"]:
            warnings.append("⚠️ Saída de capital estrangeiro")

        # Alertas de sentimento
        if sentiment.volatility == "HIGH":
            warnings.append("⚠️ Alta volatilidade intraday")

        return warnings

    def _generate_executive_summary(
        self,
        action: TradeSignal,
        confidence: Decimal,
        primary_reason: str,
        alignment: Decimal,
        risk_level: str,
    ) -> str:
        """Gera resumo executivo para o Head Financeiro."""
        action_text = {
            TradeSignal.BUY: "COMPRA RECOMENDADA",
            TradeSignal.SELL: "VENDA RECOMENDADA",
            TradeSignal.HOLD: "AGUARDAR - SEM OPERAÇÃO",
        }

        summary = f"""
================================================================================
  OPERADOR QUANTICO - DECISAO DO HEAD FINANCEIRO
================================================================================

DECISAO: {action_text[action]}
CONFIANCA: {confidence:.0%}
ALINHAMENTO: {alignment:.0%}
RISCO: {risk_level}

RAZAO PRINCIPAL:
{primary_reason}

================================================================================
"""
        return summary.strip()

    def get_last_decision(self) -> Optional[TradingDecision]:
        """Obtem a ultima decisao de trading."""
        return self._last_decision

    def get_last_macro_score(self) -> Optional[MacroScoreResult]:
        """Obtem o ultimo resultado do macro score (se MacroScoreEngine esta ativo)."""
        return self._last_macro_score

    def _macro_score_to_snapshot(
        self, result: MacroScoreResult
    ) -> MacroSnapshot:
        """Converte MacroScoreResult para MacroSnapshot (compatibilidade).

        Permite que o restante do pipeline de decisao funcione sem mudancas,
        traduzindo o resultado do macro score para o formato legado.
        """
        from src.application.services.macro_analysis import (
            GlobalRiskSentiment,
            MarketDriver,
        )

        # Mapear sinal do score para risk sentiment
        bias = result.get_trading_bias()
        if bias == "BULLISH":
            risk_sentiment = GlobalRiskSentiment.RISK_ON
            impact = "POSITIVE"
        elif bias == "BEARISH":
            risk_sentiment = GlobalRiskSentiment.RISK_OFF
            impact = "NEGATIVE"
        else:
            risk_sentiment = GlobalRiskSentiment.NEUTRAL
            impact = "NEUTRAL"

        # Gerar key points a partir dos top items
        key_points = [
            f"Macro Score: {result.score_final:+.2f} ({result.signal})",
            f"Itens disponiveis: {result.items_available}/{result.total_items}",
            f"Confianca: {result.confidence:.0%}",
        ]

        # Adicionar top contribuidores
        sorted_items = sorted(
            [i for i in result.items if i.available and i.final_score != 0],
            key=lambda x: abs(x.weighted_score),
            reverse=True,
        )
        for item in sorted_items[:3]:
            direction = "Alta" if item.final_score > 0 else "Baixa"
            key_points.append(
                f"{item.name} ({item.symbol}): {direction} -> {item.final_score:+d}"
            )

        return MacroSnapshot(
            timestamp=result.timestamp,
            global_risk_sentiment=risk_sentiment,
            main_driver=MarketDriver.COMMODITIES,
            us_futures_trend="FLAT",
            us_10y_yield=None,
            dxy_dollar_index=None,
            vix_fear_index=None,
            bewz39_level=None,
            oil_price_trend="FLAT",
            iron_ore_trend="FLAT",
            impact_on_brazil=impact,
            confidence=result.confidence,
            summary=result.summary,
            key_points=key_points,
        )
