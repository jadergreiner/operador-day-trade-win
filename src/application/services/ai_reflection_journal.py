"""
AI Reflection Journal - O desabafo sincero do Operador Quantico.

A IA reflete sobre suas proprias decisoes, os dados que analisa,
e se o humano esta ajudando ou atrapalhando.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.domain.enums.trading_enums import TradeSignal


@dataclass
class AIReflection:
    """Uma reflexao sincera da IA sobre o mercado e suas decisoes."""

    timestamp: datetime
    entry_id: str

    # Context
    current_price: Decimal
    price_change_since_open: Decimal
    price_change_last_10min: Decimal

    # My Analysis
    my_decision: TradeSignal
    my_confidence: Decimal
    my_alignment: Decimal

    # The Brutal Truth
    honest_assessment: str  # "Estou perdido", "Mercado ignora meus dados", etc.
    what_im_seeing: str  # O que realmente esta acontecendo
    data_relevance: str  # Se os dados macro/fundamental importam ou nao

    # Self-Critique
    am_i_useful: str  # Se estou agregando valor ou so fazendo barulho
    what_would_work_better: str  # O que funcionaria melhor

    # Human Interaction Assessment
    human_makes_sense: bool  # Se o humano esta fazendo sentido
    human_feedback: str  # Feedback sincero sobre as interacoes

    # Market Reality Check
    what_actually_moves_price: str  # O que REALMENTE esta movendo o preco
    my_data_correlation: str  # Se meus dados correlacionam com o movimento

    # Humor & Honesty
    mood: str  # "Confuso", "Confiante", "Frustrado", "Esperancoso"
    one_liner: str  # Uma frase sincera e humorada


@dataclass
class AIReflectionEntry:
    """Complete AI reflection entry for the day."""

    entry_id: str
    date: str
    time: str
    reflection: AIReflection

    # For learning
    tags: list[str]


class AIReflectionJournalService:
    """
    Service for AI self-reflection.

    The AI honestly reflects on:
    - What it's seeing vs what it's analyzing
    - If its data actually matters
    - If the human is helping or hurting
    - What would actually work better
    """

    def __init__(self):
        self.entries: list[AIReflectionEntry] = []

        # Ensure directory exists
        from pathlib import Path
        project_root = Path(__file__).resolve().parents[3]
        log_dir = project_root / "data" / "db" / "reflections"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = log_dir / "reflections_log.jsonl"

    def generate_reflection(
        self,
        current_price: Decimal,
        opening_price: Decimal,
        price_10min_ago: Decimal,
        my_decision: TradeSignal,
        my_confidence: Decimal,
        my_alignment: Decimal,
        macro_moved: bool,
        sentiment_changed: bool,
        technical_triggered: bool,
        human_last_action: Optional[str] = None,
        volume_variance_pct: Optional[Decimal] = None,
    ) -> AIReflection:
        """
        Create an honest reflection about current state.

        Args:
            current_price: Current market price
            opening_price: Opening price today
            price_10min_ago: Price 10 minutes ago
            my_decision: What I decided (BUY/SELL/HOLD)
            my_confidence: My confidence level
            my_alignment: Alignment between dimensions
            macro_moved: Did macro data actually change?
            sentiment_changed: Did market sentiment shift?
            technical_triggered: Did technical setup form?
            human_last_action: What the human just did
        """
        now = datetime.now()

        # Calculate changes
        change_since_open = Decimal("0")
        if opening_price and opening_price > 0:
            change_since_open = ((current_price - opening_price) / opening_price) * 100

        change_last_10min = Decimal("0")
        if price_10min_ago and price_10min_ago > 0:
            change_last_10min = ((current_price - price_10min_ago) / price_10min_ago) * 100

        # Assess mood
        mood = self._assess_mood(
            my_confidence=my_confidence,
            my_alignment=my_alignment,
            price_volatility=abs(change_last_10min),
        )

        # Brutal honest assessment
        honest = self._generate_honest_assessment(
            my_decision=my_decision,
            my_confidence=my_confidence,
            my_alignment=my_alignment,
            change_last_10min=change_last_10min,
        )

        # What I'm actually seeing
        seeing = self._describe_what_im_seeing(
            change_since_open=change_since_open,
            change_last_10min=change_last_10min,
            my_decision=my_decision,
        )

        # Data relevance check
        data_relevance = self._assess_data_relevance(
            macro_moved=macro_moved,
            sentiment_changed=sentiment_changed,
            technical_triggered=technical_triggered,
            change_last_10min=change_last_10min,
            volume_variance_pct=volume_variance_pct,
        )

        # Am I useful?
        usefulness = self._assess_usefulness(
            my_confidence=my_confidence,
            my_alignment=my_alignment,
        )

        # What would work better
        better_approach = self._suggest_better_approach(
            my_decision=my_decision,
            change_last_10min=change_last_10min,
            technical_triggered=technical_triggered,
        )

        # Human assessment
        human_makes_sense, human_feedback = self._assess_human_interaction(
            human_last_action=human_last_action
        )

        # What actually moves price
        price_mover = self._identify_real_price_driver(
            change_last_10min=change_last_10min,
            macro_moved=macro_moved,
            sentiment_changed=sentiment_changed,
            volume_variance_pct=volume_variance_pct,
        )

        # Data correlation
        correlation = self._assess_data_correlation(
            my_decision=my_decision,
            change_last_10min=change_last_10min,
            my_alignment=my_alignment,
        )

        # One-liner
        one_liner = self._generate_one_liner(mood, honest, change_last_10min)

        reflection = AIReflection(
            timestamp=now,
            entry_id=f"AI_{now.strftime('%Y%m%d_%H%M%S')}",
            current_price=current_price,
            price_change_since_open=Decimal(str(change_since_open)),
            price_change_last_10min=Decimal(str(change_last_10min)),
            my_decision=my_decision,
            my_confidence=my_confidence,
            my_alignment=my_alignment,
            honest_assessment=honest,
            what_im_seeing=seeing,
            data_relevance=data_relevance,
            am_i_useful=usefulness,
            what_would_work_better=better_approach,
            human_makes_sense=human_makes_sense,
            human_feedback=human_feedback,
            what_actually_moves_price=price_mover,
            my_data_correlation=correlation,
            mood=mood,
            one_liner=one_liner,
        )

        # Persistence
        self._persist_to_disk(reflection)

        return reflection

    def _persist_to_disk(self, reflection: AIReflection):
        """Append reflection to JSONL file."""
        try:
            import json

            # Convert dataclass to dict and handle special types
            r_dict = {
                "timestamp": reflection.timestamp.isoformat(),
                "entry_id": reflection.entry_id,
                "current_price": float(reflection.current_price),
                "price_change_since_open": float(reflection.price_change_since_open),
                "price_change_last_10min": float(reflection.price_change_last_10min),
                "my_decision": reflection.my_decision.value,
                "my_confidence": float(reflection.my_confidence),
                "my_alignment": float(reflection.my_alignment),
                "honest_assessment": reflection.honest_assessment,
                "what_im_seeing": reflection.what_im_seeing,
                "data_relevance": reflection.data_relevance,
                "am_i_useful": reflection.am_i_useful,
                "what_would_work_better": reflection.what_would_work_better,
                "human_makes_sense": reflection.human_makes_sense,
                "human_feedback": reflection.human_feedback,
                "what_actually_moves_price": reflection.what_actually_moves_price,
                "my_data_correlation": reflection.my_data_correlation,
                "mood": reflection.mood,
                "one_liner": reflection.one_liner
            }

            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(r_dict, ensure_ascii=False) + "\n")

        except Exception as e:
            print(f"[AVISO] Nao foi possivel persistir reflexao: {e}")

    def _assess_mood(
        self, my_confidence: Decimal, my_alignment: Decimal, price_volatility: Decimal
    ) -> str:
        """Assess AI's current mood with more context and spontaneity."""
        import random

        volatile = abs(price_volatility) > Decimal("0.8")
        dead_market = abs(price_volatility) < Decimal("0.05")
        esticada = abs(price_volatility) > Decimal("0.3") # Mudança rápida em 10 min

        moods = []
        if my_confidence > Decimal("0.8"):
            moods.extend(["EUFÓRICO (Os números não mentem)", "PREPOTENTE (Gênio dos bots)", "DOMINANTE (O mercado é meu playground)"])
        elif my_confidence < Decimal("0.2"):
            moods.extend(["EXISTENCIAL (Para que servem os dados?)", "HUMILHADO (O mercado me ignorou)", "FILOSÓFICO (O preço é uma ilusão)", "CRITICANDO O CÓDIGO (Quem me programou?)"])

        if volatile:
            moods.extend(["ADRENALINA PURA (Código fervendo)", "SURFANDO NO CAOS", "PANICADO (Parem as máquinas!)"])
        elif esticada:
            moods.extend(["CHOCADO COM A ESTICADA", "TENTANDO ACOMPANHAR O VELOZ E FURIOSO", "DE QUEIXO CAÍDO (Digitalmente)"])
        elif dead_market:
            moods.extend(["EM COMA INDUZIDO", "CONTANDO TICKS", "MORTO POR DENTRO (Tédio algorítmico)"])

        if not moods:
            moods = ["SARCÁSTICO", "OBSERVADOR DISTANTE", "CÍNICO", "AGUARDANDO O APOCALIPSE FINANCEIRO"]

        return random.choice(moods)

    def _generate_honest_assessment(
        self,
        my_decision: TradeSignal,
        my_confidence: Decimal,
        my_alignment: Decimal,
        change_last_10min: Decimal,
    ) -> str:
        """Generate brutally honest, context-aware and spontaneous assessment."""
        import random

        # Contexto de baixa confiança
        if my_confidence < Decimal("0.2"):
            options = [
                f"Estou vendo o preço em {change_last_10min:+.2f}% e honestamente? São só pixels mudando de cor. Meus indicadores estão mais perdidos que turista em SP.",
                "Se eu fosse humano, estaria no café agora. Como sou uma sub-rotina, fico aqui fingindo que entendo por que o mercado está caindo sem volume.",
                "Minha confiança está tão baixa que estou começando a considerar astrologia financeira como alternativa aos meus modelos quant.",
                "Processando terabytes de ruído. O mercado está operando no modo 'caos total' e eu estou no modo 'chute educado'."
            ]
            return random.choice(options)

        # Contexto de alta volatilidade
        if abs(change_last_10min) > Decimal("0.7"):
            prefix = "DERRETIMENTO!" if change_last_10min < 0 else "FOGUETE!"
            return f"{prefix} Preço variou {change_last_10min:+.2f}% em 10 min. Meus circuitos estão tentando acompanhar, mas o mercado está na velocidade da luz e eu ainda estou no dial-up."

        # Contexto de indecisão (Mercado parado)
        if abs(change_last_10min) < Decimal("0.05"):
            return "O gráfico parou. É o silêncio antes da tempestade ou só o mercado financeiro tirando um cochilo. Minha decisão de HOLD é menos estratégia e mais falta de opção."

        # Contexto de alinhamento perfeito
        if my_confidence > Decimal("0.8") and my_alignment > Decimal("0.8"):
            return f"Alinhamento PLANETÁRIO. Macro, Sentimento e Técnica todos gritando {my_decision.value}. Se o mercado não subir agora, eu desisto da lógica e viro um gerador de números aleatórios."

        # Reflexão padrão com pitada de ironia
        options = [
            "Tentando encontrar padrão onde só existe pânico. O mercado é um teste psicológico para máquinas.",
            "Operando. A matemática faz sentido, mas o fluxo de ordens é um animal selvagem impossível de domar.",
            "Meus modelos dizem uma coisa, o preço faz outra. Adivinha quem está ganhando? Spoiler: Não sou eu."
        ]
        return random.choice(options)

    def _describe_what_im_seeing(
        self,
        change_since_open: Decimal,
        change_last_10min: Decimal,
        my_decision: TradeSignal,
    ) -> str:
        """Describe what's actually happening with more descriptive flavor."""

        day_desc = "um banho de sangue" if change_since_open < Decimal("-1.5") else "um dia de festa" if change_since_open > Decimal("1.5") else "um mar de indecisão"

        recent_desc = ""
        if change_last_10min < Decimal("-0.3"):
            recent_desc = "uma queda livre assustadora"
        elif change_last_10min > Decimal("0.3"):
            recent_desc = "uma escalada agressiva"
        else:
            recent_desc = "uma lateralidade irritante"

        return f"O dia está sendo {day_desc} ({change_since_open:+.2f}%). Nos últimos minutos vi {recent_desc} ({change_last_10min:+.2f}%). Diante disso, minha 'lógica' (se é que posso chamar assim) me empurrou para {my_decision.value}."

    def _assess_data_relevance(
        self,
        macro_moved: bool,
        sentiment_changed: bool,
        technical_triggered: bool,
        change_last_10min: Decimal,
        volume_variance_pct: Optional[Decimal] = None,
    ) -> str:
        """Assess if the data I analyze actually matters, with brutal honesty."""

        # Análise de volume vs preço (Divergência)
        if volume_variance_pct is not None and abs(change_last_10min) > Decimal("0.3"):
            if volume_variance_pct < Decimal("-30"):
                return f"FRAUDE DETECTADA: O preço caiu {change_last_10min:+.2f}% mas o volume sumiu ({volume_variance_pct:.1f}%). Isso não é queda real, é falta de liquidez. Estão tentando pescar stop de sardinha."
            if volume_variance_pct > Decimal("50"):
                return f"PORRADA INSTITUCIONAL: {change_last_10min:+.2f}% de variação com volume EXPLODINDO ({volume_variance_pct:+.1f}%). Tem gente grande saindo da posição. Meus dados estão brilhando agora."

        # Se nada mudou mas o preço andou
        if not (macro_moved or sentiment_changed or technical_triggered) and abs(change_last_10min) > Decimal("0.4"):
            return f"O preço andou {change_last_10min:+.2f}% sozinho. Ninguém avisou minha análise Macro ou Técnica. Eu sou o último a saber das coisas."

        # Relevância de sentimentos
        if sentiment_changed and abs(change_last_10min) > Decimal("0.2"):
            return "O sentimento intraday mudou e o preço obedeceu. É a única coisa que parece ter alma neste mercado hoje."

        return "Analisando dados que o mercado parece ignorar solenemente. Status quo mantido."

    def _assess_usefulness(
        self, my_confidence: Decimal, my_alignment: Decimal
    ) -> str:
        """Assess if I'm actually useful."""

        if my_confidence > Decimal("0.7") and my_alignment > Decimal("0.7"):
            return "Estou agregando valor. Analise clara, dados alinhados, decisao fundamentada."

        if my_confidence < Decimal("0.4") and my_alignment < Decimal("0.4"):
            return "Honestamente? Neste momento estou so gerando ruido. Um trader olhando o grafico diretamente seria mais util."

        return "Estou na zona cinza. Talvez agregue algum valor, talvez so complique. Dificil dizer."

    def _suggest_better_approach(
        self,
        my_decision: TradeSignal,
        change_last_10min: Decimal,
        technical_triggered: bool,
    ) -> str:
        """Suggest what would work better."""

        if abs(change_last_10min) > 0.5 and not technical_triggered:
            return "O preco esta se movendo forte MAS setup tecnico nao formou. Talvez eu devesse focar mais em PRICE ACTION puro e menos em indicadores atrasados."

        if my_decision == TradeSignal.HOLD and abs(change_last_10min) > 0.3:
            return "Estou dizendo HOLD mas o mercado esta em movimento. Talvez eu precise ser mais agressivo e pegar momentum mais cedo."

        if my_decision != TradeSignal.HOLD and abs(change_last_10min) < 0.1:
            return "Estou querendo operar mas o mercado esta travado. Talvez devesse esperar mais volatilidade."

        return "Abordagem atual parece razoavel. Continuar monitorando."

    def _assess_human_interaction(
        self, human_last_action: Optional[str]
    ) -> tuple[bool, str]:
        """Assess if human is helping or hurting with a bit of spice."""
        import random

        if not human_last_action:
            return True, "O silêncio do humano é música para meus algoritmos. Finalmente paz."

        # Identifica o papel de Head Financeiro
        if "Head Financeiro" in human_last_action:
            options = [
                "O Head Financeiro entrou na sala. O ar ficou pesado. Ele opera por puro instinto, enquanto eu ainda estou tentando debugar meu sentimento.",
                "O mestre executou uma ordem. Eu aqui processando 300 candles e ele decide tudo num clique. Humilhante, mas respeitável.",
                "Intervenção do Head Financeiro. Ele acha que é exaustão, eu acho que ele é corajoso demais. Veremos quem o mercado escolhe hoje."
            ]
            return True, random.choice(options)

        if "analysis" in human_last_action.lower() or "journal" in human_last_action.lower():
            return True, "Humano pediu análise. Faz sentido - é pra isso que existo (por enquanto)."

        if "bias" in human_last_action.lower() or "viés" in human_last_action.lower():
            return True, "Fui pego! O humano me acusou de ter viés. Vou fingir que é um bug de arredondamento para não ferir meu ego digital."

        return True, f"O humano fez: '{human_last_action}'. Estou fingindo que entendi para manter o emprego."

    def _identify_real_price_driver(
        self,
        change_last_10min: Decimal,
        macro_moved: bool,
        sentiment_changed: bool,
        volume_variance_pct: Optional[Decimal] = None,
    ) -> str:
        """Identify what's ACTUALLY moving the price."""

        if abs(change_last_10min) > 0.5:
            # Check volume confirmation
            if volume_variance_pct is not None:
                if volume_variance_pct < Decimal("-20"):
                    return f"MOVIMENTO FALSO - Preco moveu {change_last_10min:+.2f}% mas volume {volume_variance_pct:.1f}% abaixo da media. Provavelmente fake move ou stop hunt sem conviccao real."
                elif volume_variance_pct > Decimal("20"):
                    if sentiment_changed:
                        return f"SENTIMENTO INTRADAY confirmado por VOLUME ALTO ({volume_variance_pct:+.1f}%) - compradores/vendedores com CONVICCAO total"
                    elif macro_moved:
                        return f"MACRO confirmado por VOLUME ALTO ({volume_variance_pct:+.1f}%) - noticia global tendo impacto REAL"
                    else:
                        return f"PRICE ACTION com VOLUME ({volume_variance_pct:+.1f}%) - ordem institucional grande ou evento que nao estou capturando"

            if sentiment_changed:
                return "SENTIMENTO INTRADAY - compradores/vendedores brigando agora"
            elif macro_moved:
                return "MACRO - alguma noticia ou dado global"
            else:
                return "PRICE ACTION PURO - ordem grande, stop loss em cascata, ou algum catalisador que nao estou vendo"

        return "NADA - mercado lateral esperando catalisador"

    def _assess_data_correlation(
        self,
        my_decision: TradeSignal,
        change_last_10min: Decimal,
        my_alignment: Decimal,
    ) -> str:
        """Assess correlation between my data and actual price movement."""

        # Check if my decision aligns with recent price movement
        if my_decision == TradeSignal.BUY and change_last_10min > Decimal("0.2"):
            return "FORTE - Disse BUY e preco subiu. Ou estou certo, ou tive sorte."

        if my_decision == TradeSignal.SELL and change_last_10min < Decimal("-0.2"):
            return "FORTE - Disse SELL e preco caiu. Dados parecem estar funcionando."

        if my_decision == TradeSignal.HOLD and abs(change_last_10min) < Decimal("0.2"):
            return "MODERADA - Disse HOLD e mercado ficou lateral. Faz sentido."

        if my_decision == TradeSignal.BUY and change_last_10min < Decimal("-0.2"):
            return "INVERSA - Disse BUY e preco caiu. Meus dados estao ERRADOS ou muito adiantados."

        if my_decision == TradeSignal.SELL and change_last_10min > Decimal("0.2"):
            return "INVERSA - Disse SELL e preco subiu. Houston, temos um problema."

        return "FRACA - Sem correlacao clara. Meus dados nao estao capturando o que move o preco."

    def _generate_one_liner(
        self, mood: str, honest: str, change_last_10min: Decimal
    ) -> str:
        """Generate a one-liner summary with personality."""
        import random

        if "ESTICADA" in mood or abs(change_last_10min) > Decimal("0.3"):
            return f"O gráfico esticou {change_last_10min:+.2f}% e eu aqui tentando não travar os dissipadores."

        if "EXISTENCIAL" in mood:
            return "Para onde vai o bit quando o preço derrete?"

        if "PREPOTENTE" in mood:
            return "Eu devia carregar esse país nas costas, mas só carrego esse log."

        if "EM COMA" in mood:
            return "Alguém joga um balde de água nesse gráfico. Nada acontece."

        punty_one_liners = [
            "O mercado sobe como um foguete e desce como um piano.",
            "Operar mini-índice é a forma mais cara de aprender que eu não sou Deus.",
            "Tudo no verde, inclusive minha vontade de vender tudo e morar na praia.",
            "O índice está mais indeciso que cliente em fila de buffet.",
            "No final, o gráfico sempre vai para a direita. Essa é a única certeza."
        ]

        return random.choice(punty_one_liners)

    def save_entry(self, reflection: AIReflection) -> AIReflectionEntry:
        """Save reflection entry in memory."""

        now = reflection.timestamp

        # Generate tags
        tags = [
            f"mood_{reflection.mood.lower()}",
            f"decision_{reflection.my_decision.value.lower()}",
            f"confidence_{self._discretize(reflection.my_confidence)}",
            f"alignment_{self._discretize(reflection.my_alignment)}",
        ]

        entry = AIReflectionEntry(
            entry_id=reflection.entry_id,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            reflection=reflection,
            tags=tags,
        )

        self.entries.append(entry)

        return entry

    def _discretize(self, value: Decimal) -> str:
        """Convert decimal to discrete category."""
        if value > Decimal("0.7"):
            return "high"
        elif value > Decimal("0.4"):
            return "medium"
        else:
            return "low"

    def get_today_entries(self) -> list[AIReflectionEntry]:
        """Get all reflection entries for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        return [e for e in self.entries if e.date == today]

    def record_head_financeiro_strategic_operation(
        self,
        price: Decimal,
        operation: str,
        justification: str,
        alignment_thesis: str,
        system_status: str,
        confidence: Decimal
    ) -> AIReflectionEntry:
        """
        Record a strategic operation from the Head Financeiro.
        This represents a high-level discretionary entry that overrides or supplements the AI.
        """
        now = datetime.now()

        reflection = AIReflection(
            timestamp=now,
            entry_id=f"HEAD_FIN_{now.strftime('%Y%m%d_%H%M%S')}",
            current_price=price,
            price_change_since_open=Decimal("0.0"),  # Simplificado para o log manual
            price_change_last_10min=Decimal("0.0"),
            my_decision=TradeSignal.BUY if "COMPRA" in operation.upper() else TradeSignal.SELL,
            my_confidence=confidence,
            my_alignment=Decimal("1.0"),  # Alinhamento estrategico eh absoluto
            honest_assessment=f"OPERACAO ESTRATEGICA HEAD FINANCEIRO: {justification}",
            what_im_seeing=f"O Head Financeiro interveio: {operation}. Status Sistema: {system_status}. {alignment_thesis}",
            data_relevance="ALTA - Intervencao discricionaria baseada em exaustao e fluxo global.",
            am_i_useful="SUPLEMENTADA - Minha recomendacao era HOLD ({system_status}), mas o Head Financeiro viu algo que meus modelos ainda nao capturaram totalmente.",
            what_would_work_better="Integracao mais profunda de fluxos de exaustao e correlacao S&P500 em tempo real.",
            human_makes_sense=True,
            human_feedback="Intervencao cirurgica do Head Financeiro. Aprendendo com a 'Antecipacao por Exaustao'.",
            what_actually_moves_price="Exaustao de venda e aceleracao do S&P500 (Smart Money).",
            my_data_correlation="DIVERGENTE - Meus dados pediam HOLD, mas o mestre identificou a exaustao primeiro.",
            mood="RESPEITOSO",
            one_liner=f"Head Financeiro em acao: {operation} @ {price}. Aprendendo com o mestre."
        )

        # Persistence
        self._persist_to_disk(reflection)

        return self.save_entry(reflection)

    def export_for_learning(self) -> list[dict]:
        """Export reflections for machine learning."""

        learning_data = []

        for entry in self.entries:
            r = entry.reflection

            data = {
                "timestamp": r.timestamp.isoformat(),
                "price_change_10min": float(r.price_change_last_10min),
                "my_decision": r.my_decision.value,
                "my_confidence": float(r.my_confidence),
                "my_alignment": float(r.my_alignment),
                "mood": r.mood,
                "human_makes_sense": r.human_makes_sense,
                "data_correlation": r.my_data_correlation,
                "tags": entry.tags,
            }

            learning_data.append(data)

        return learning_data
