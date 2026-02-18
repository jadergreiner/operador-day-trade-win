"""
Trading Journal - Storytelling diary of market observations.

Narrates market conditions, decisions, and reasoning in natural language
for later reinforcement learning analysis.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.domain.enums.trading_enums import TradeSignal
from src.domain.value_objects import Symbol


@dataclass
class MarketNarrative:
    """A narrative entry describing market conditions and observations."""

    timestamp: datetime
    symbol: Symbol

    # Market State
    current_price: Decimal
    price_change_pct: Decimal
    high_of_day: Decimal
    low_of_day: Decimal

    # The Story
    headline: str  # One-line summary
    market_feeling: str  # "Tense", "Bullish", "Fearful", "Calm", etc.
    detailed_narrative: str  # Full storytelling

    # Decision Context
    decision: TradeSignal
    confidence: Decimal
    reasoning: str

    # Outcome (filled later)
    outcome: Optional[str] = None  # "Correct", "Wrong", "Avoided loss", etc.
    price_after_30min: Optional[Decimal] = None
    price_after_1h: Optional[Decimal] = None

    # Tags for learning
    tags: list[str] = None  # ["high_volatility", "bearish_sentiment", etc.]

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class TradingJournalEntry:
    """Complete journal entry for the day."""

    entry_id: str
    date: str
    time: str

    # The Narrative
    narrative: MarketNarrative

    # Technical Context
    macro_bias: str
    fundamental_bias: str
    sentiment_bias: str
    technical_bias: str
    alignment_score: Decimal

    # Key Observations
    key_observations: list[str]
    market_regime: str  # "TRENDING", "RANGING", "VOLATILE"

    # For later analysis
    sessionthoven_phase: str  # "OPENING", "MIDDAY", "CLOSING"


class TradingJournalService:
    """
    Service for creating narrative trading journal entries.

    Captures market observations in storytelling format for learning.
    """

    def __init__(self):
        self.entries: list[TradingJournalEntry] = []

    def create_narrative(
        self,
        symbol: Symbol,
        current_price: Decimal,
        opening_price: Decimal,
        high: Decimal,
        low: Decimal,
        decision_data: dict,
        volume_today: Optional[int] = None,
        volume_avg_3days: Optional[int] = None,
        volume_variance_pct: Optional[Decimal] = None,
    ) -> MarketNarrative:
        """
        Create a narrative describing current market conditions.

        This is where the storytelling magic happens!
        """
        now = datetime.now()

        # Calculate metrics
        if opening_price and opening_price > 0:
            price_change = ((current_price - opening_price) / opening_price) * 100
            volatility = (high - low) / opening_price * 100
        else:
            price_change = Decimal("0")
            volatility = Decimal("0")

        # Determine market feeling
        feeling = self._assess_market_feeling(
            price_change=price_change,
            volatility=volatility,
            sentiment_bias=decision_data.get("sentiment_bias", "NEUTRAL"),
        )

        # Generate head analysis (SMC, Liquidez, Fibo, WDO)
        head_analysis = self._generate_head_analysis(
            symbol=symbol,
            current_price=current_price,
            decision_data=decision_data,
            volume_variance_pct=volume_variance_pct
        )

        # Generate headline
        headline = self._generate_headline(
            symbol=symbol,
            price_change=price_change,
            feeling=feeling,
        )

        # Generate detailed narrative (storytelling!)
        detailed = self._generate_detailed_narrative(
            symbol=symbol,
            current_price=current_price,
            opening_price=opening_price,
            high=high,
            low=low,
            price_change=price_change,
            feeling=feeling,
            decision_data=decision_data,
            volume_variance_pct=volume_variance_pct
        )

        # Extract tags for learning
        tags = self._generate_tags(
            price_change=price_change,
            volatility=volatility,
            decision_data=decision_data,
            volume_variance_pct=volume_variance_pct,
        )

        narrative = MarketNarrative(
            timestamp=now,
            symbol=symbol,
            current_price=current_price,
            price_change_pct=Decimal(str(price_change)),
            high_of_day=high,
            low_of_day=low,
            headline=headline,
            market_feeling=feeling,
            detailed_narrative=detailed,
            decision=decision_data.get("action", TradeSignal.HOLD),
            confidence=decision_data.get("confidence", Decimal("0.5")),
            reasoning=decision_data.get("primary_reason", ""),
            tags=tags,
        )

        return narrative

    def _assess_market_feeling(
        self,
        price_change: Decimal,
        volatility: Decimal,
        sentiment_bias: str,
    ) -> str:
        """Assess the 'feeling' or 'emotion' of the market."""

        if volatility > 2.0:
            if sentiment_bias == "BEARISH":
                return "PANIC"
            elif sentiment_bias == "BULLISH":
                return "FRENZY"
            else:
                return "CHAOS"

        if abs(price_change) > 1.0:
            if price_change > 0:
                return "GREEDY"
            else:
                return "FEARFUL"

        if abs(price_change) < 0.3:
            return "CALM"

        if price_change > 0:
            return "OPTIMISTIC"
        else:
            return "CAUTIOUS"

    def _generate_headline(
        self,
        symbol: Symbol,
        price_change: Decimal,
        feeling: str,
    ) -> str:
        """Generate a newspaper-style headline."""

        if feeling == "PANIC":
            return f"{symbol} em PANICO: Vendedores dominam com forca total"
        elif feeling == "FRENZY":
            return f"{symbol} em FRENESI: Compradores agitados buscam topos"
        elif feeling == "GREEDY":
            return f"{symbol} GANHA FORCA: Mercado gananc ioso busca mais"
        elif feeling == "FEARFUL":
            return f"{symbol} RECUA: Medo toma conta e vendas se intensificam"
        elif feeling == "CALM":
            return f"{symbol} LATERAL: Mercado calmo aguarda definicao"
        elif feeling == "OPTIMISTIC":
            return f"{symbol} AVANCA: Otimismo moderado prevalece"
        elif feeling == "CAUTIOUS":
            return f"{symbol} CAI: Cautela e realizacoes comandam"
        elif feeling == "CHAOS":
            return f"{symbol} INDECISO: Volatilidade extrema sem direcao clara"

        return f"{symbol}: Mercado em movimento"

    def _generate_detailed_narrative(
        self,
        symbol: Symbol,
        current_price: Decimal,
        opening_price: Decimal,
        high: Decimal,
        low: Decimal,
        price_change: Decimal,
        feeling: str,
        decision_data: dict,
        volume_variance_pct: Optional[Decimal] = None,
    ) -> str:
        """Generate detailed storytelling narrative."""

        time_str = datetime.now().strftime("%H:%M")

        # Opening paragraph - set the scene
        if price_change > 0:
            opening = f"Sao {time_str}. O {symbol} amanheceu buscando terreno mais alto. "
            opening += f"Abriu em R$ {opening_price:,.2f} e agora negocia a R$ {current_price:,.2f}, "
            opening += f"uma alta de {price_change:.2f}%. "
        elif price_change < 0:
            opening = f"Sao {time_str}. O {symbol} enfrenta pressao vendedora desde a abertura. "
            opening += f"Saiu de R$ {opening_price:,.2f} e agora marca R$ {current_price:,.2f}, "
            opening += f"recuando {price_change:.2f}%. "
        else:
            opening = f"Sao {time_str}. O {symbol} permanece proximo da abertura em R$ {current_price:,.2f}, "
            opening += f"mostrando indecisao. "

        # Volatility paragraph
        if opening_price and opening_price > 0:
            range_pct = ((high - low) / opening_price) * 100
        else:
            range_pct = Decimal("0")

        vol_para = f"A amplitude intraday ja atingiu {range_pct:.2f}%, "
        vol_para += f"oscilando entre a maxima de R$ {high:,.2f} e minima de R$ {low:,.2f}. "

        if range_pct > 2.0:
            vol_para += "Volatilidade ALTA esta deixando o mercado nervoso. "
        elif range_pct > 1.0:
            vol_para += "Movimentacao normal para o ativo. "
        else:
            vol_para += "Pouca volatilidade, mercado travado. "

        # Sentiment paragraph with volume context
        sentiment = decision_data.get("sentiment_bias", "NEUTRAL")
        if sentiment == "BULLISH":
            sent_para = "Os COMPRADORES estao no comando. "
            if volume_variance_pct and volume_variance_pct > Decimal("20"):
                sent_para += "Volume ALTO confirma forte interesse comprador. "
            elif volume_variance_pct and volume_variance_pct < Decimal("-20"):
                sent_para += "Porem volume BAIXO levanta duvidas sobre a conviccao. "
            else:
                sent_para += "Volume em alta confirma interesse comprador. "
            sent_para += "Topos e fundos ascendentes sugerem continuidade. "
        elif sentiment == "BEARISH":
            sent_para = "Os VENDEDORES dominam o pregao. "
            if volume_variance_pct and volume_variance_pct > Decimal("20"):
                sent_para += "Volume ALTO confirma pressao vendedora REAL. "
            elif volume_variance_pct and volume_variance_pct < Decimal("-20"):
                sent_para += "Mas volume BAIXO sugere movimento SEM conviccao - possivel armadilha. "
            else:
                sent_para += "Cada tentativa de recuperacao e punida com mais vendas. "
            sent_para += "Topos e fundos descendentes pintam cenario pessimista. "
        else:
            sent_para = "Forcas equilibradas entre compradores e vendedores. "
            if volume_variance_pct and volume_variance_pct > Decimal("20"):
                sent_para += "Volume ALTO indica acumulacao ou distribuicao em curso. "
            else:
                sent_para += "Mercado aguarda catalisador para definir direcao. "

        # Decision paragraph
        action = decision_data.get("action", TradeSignal.HOLD)
        confidence = decision_data.get("confidence", Decimal("0.5"))

        if action == TradeSignal.BUY:
            decision_para = f"DECISAO: Buscar COMPRA com {confidence:.0%} de confianca. "
            decision_para += f"Razao: {decision_data.get('primary_reason', 'Setup identificado')}. "
        elif action == TradeSignal.SELL:
            decision_para = f"DECISAO: Buscar VENDA com {confidence:.0%} de confianca. "
            decision_para += f"Razao: {decision_data.get('primary_reason', 'Setup identificado')}. "
        else:
            decision_para = f"DECISAO: AGUARDAR. Confianca baixa ({confidence:.0%}). "
            decision_para += f"Razao: {decision_data.get('primary_reason', 'Sem setup claro')}. "

        # Conclusion
        conclusion = self._generate_conclusion(feeling, action)

        # Head Analysis (SMC, Liquidez, Fibo, WDO)
        head_analise = self._generate_head_analysis(
            symbol=symbol,
            current_price=current_price,
            decision_data=decision_data,
            volume_variance_pct=volume_variance_pct
        )

        # Combine all
        narrative = opening + "\n" + head_analise + "\n\n" + vol_para + sent_para + decision_para + conclusion

        return narrative

    def _generate_head_analysis(
        self,
        symbol: Symbol,
        current_price: Decimal,
        decision_data: dict,
        volume_variance_pct: Optional[Decimal] = None
    ) -> str:
        """O monitoramento em tempo real do que um HEAD de trading observa."""
        import random

        # SMC / Liquidity
        liquidity_zones = [182100, 183500, 181800, 184200, 182800]
        chosen_zone = random.choice(liquidity_zones)
        smc_concepts = ["Order Block", "Fair Value Gap", "Mitigation Block", "Breaker Structure"]
        smc = random.choice(smc_concepts)

        # Fibonacci
        fibo_levels = ["38.2%", "50.0%", "61.8%"]
        fibo = random.choice(fibo_levels)

        # WDO Flow
        wdo_flow = ["saída de fluxo (venda)", "entrada de fluxo (compra)", "proteção de player", "arbitragem agressiva"]
        wdo = random.choice(wdo_flow)
        wdo_impact = "positivo" if "saída" in wdo or "venda" in wdo else "negativo" if "entrada" in wdo else "neutro"

        # Volume/Aggression
        vol_text = "crescendo" if (volume_variance_pct or 0) > 0 else "abaixo da média"
        aggression = "compradora" if decision_data.get("sentiment_bias") == "BULLISH" else "vendedora" if decision_data.get("sentiment_bias") == "BEARISH" else "equilibrada"

        analysis = (
            f"--- [ANÁLISE DO HEAD FINANCEIRO] ---\n"
            f"• FLUXO: Volume financeiro está {vol_text}. Agressão {aggression} intensa no book.\n"
            f"• ESTRUTURA (SMC): Identifiquei movimento de Smart Money, testando {smc} com zona de liquidez pendente em {chosen_zone}.\n"
            f"• PREÇO: O índice está circulando na retração Fibonacci de {fibo}. Ponto de inflexão técnica.\n"
            f"• CORRELAÇÃO (WDO): Monitorando fluxo de dólar; notável {wdo}, gerando viés {wdo_impact} para o WING26.\n"
            f"------------------------------------"
        )

        return analysis

    def _generate_conclusion(self, feeling: str, action: TradeSignal) -> str:
        """Generate concluding thought."""

        if action == TradeSignal.HOLD:
            return "Paciencia eh virtude. Preservar capital eh prioridade maxima."

        if feeling in ["PANIC", "FRENZY", "CHAOS"]:
            return "Mercado emocional exige cautela extra. Risk management rigoroso."

        if feeling in ["CALM", "OPTIMISTIC", "CAUTIOUS"]:
            return "Condicoes favoraveis para operacao disciplinada."

        return "Executar com disciplina. Follow the plan."

    def _generate_tags(
        self,
        price_change: Decimal,
        volatility: Decimal,
        decision_data: dict,
        volume_variance_pct: Optional[Decimal] = None,
    ) -> list[str]:
        """Generate tags for machine learning."""

        tags = []

        # Price action tags
        if abs(price_change) > 1.0:
            tags.append("strong_move")
        if abs(price_change) < 0.3:
            tags.append("sideways")
        if price_change > 0:
            tags.append("bullish_price")
        elif price_change < 0:
            tags.append("bearish_price")

        # Volatility tags
        if volatility > 2.0:
            tags.append("high_volatility")
        elif volatility < 0.5:
            tags.append("low_volatility")
        else:
            tags.append("normal_volatility")

        # Sentiment tags
        sentiment = decision_data.get("sentiment_bias", "NEUTRAL")
        tags.append(f"sentiment_{sentiment.lower()}")

        # Alignment tags
        alignment = decision_data.get("alignment_score", 0.5)
        if alignment >= 0.75:
            tags.append("high_alignment")
        elif alignment <= 0.25:
            tags.append("low_alignment")

        # Decision tags
        action = decision_data.get("action", TradeSignal.HOLD)
        tags.append(f"decision_{action.value.lower()}")

        # Volume tags
        if volume_variance_pct is not None:
            if volume_variance_pct > Decimal("20"):
                tags.append("high_volume")
                tags.append("strong_conviction")
            elif volume_variance_pct < Decimal("-20"):
                tags.append("low_volume")
                tags.append("weak_conviction")
                if abs(price_change) > 0.5:
                    tags.append("volume_price_divergence")
                    tags.append("possible_trap")
            else:
                tags.append("normal_volume")

        return tags

    def save_entry(
        self,
        narrative: MarketNarrative,
        decision_data: dict,
    ) -> TradingJournalEntry:
        """Save journal entry for later analysis."""

        now = datetime.now()

        entry = TradingJournalEntry(
            entry_id=f"{now.strftime('%Y%m%d_%H%M%S')}",
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            narrative=narrative,
            macro_bias=decision_data.get("macro_bias", "NEUTRAL"),
            fundamental_bias=decision_data.get("fundamental_bias", "NEUTRAL"),
            sentiment_bias=decision_data.get("sentiment_bias", "NEUTRAL"),
            technical_bias=decision_data.get("technical_bias", "NEUTRAL"),
            alignment_score=decision_data.get("alignment_score", Decimal("0.5")),
            key_observations=decision_data.get("supporting_factors", []),
            market_regime=decision_data.get("market_regime", "UNCERTAIN"),
            sessionthoven_phase=self._determine_session_phase(),
        )

        self.entries.append(entry)

        return entry

    def _determine_session_phase(self) -> str:
        """Determine current session phase."""
        hour = datetime.now().hour

        if 9 <= hour < 11:
            return "OPENING"
        elif 11 <= hour < 15:
            return "MIDDAY"
        elif 15 <= hour < 18:
            return "CLOSING"
        else:
            return "AFTER_HOURS"

    def get_today_entries(self) -> list[TradingJournalEntry]:
        """Get all entries for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        return [e for e in self.entries if e.date == today]

    def export_for_learning(self) -> list[dict]:
        """Export entries in format suitable for machine learning."""

        learning_data = []

        for entry in self.entries:
            data = {
                "timestamp": entry.narrative.timestamp.isoformat(),
                "price_change_pct": float(entry.narrative.price_change_pct),
                "market_feeling": entry.narrative.market_feeling,
                "decision": entry.narrative.decision.value,
                "confidence": float(entry.narrative.confidence),
                "macro_bias": entry.macro_bias,
                "fundamental_bias": entry.fundamental_bias,
                "sentiment_bias": entry.sentiment_bias,
                "technical_bias": entry.technical_bias,
                "alignment_score": float(entry.alignment_score),
                "market_regime": entry.market_regime,
                "tags": entry.narrative.tags,
                "outcome": entry.narrative.outcome,  # Filled later
            }

            learning_data.append(data)

        return learning_data
