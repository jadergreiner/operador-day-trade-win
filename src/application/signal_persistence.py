"""
Signal Persistence Layer (Camada 1)

Sistema de geração, persistência e rastreamento de sinais operacionais.

Responsabilidades:
    - Gerar sinais SMC em timeframe M5
    - Persistir sinais em DB (tabela `signals`)
    - Rastrear sinais até conclusão (outcome_pnl, outcome_type)
    - Permitir auditoria completa do histórico

Arquitetura:
    SignalGenerator (M5 detector) → SignalPersistence (DB) → SignalTracker (lifecycle)

Status: Implementação v1.0 (05/03/2026)
Referência: docs/MODELAGEM_DADOS.md (Tabela 11: SIGNALS)
           docs/ARCHITECTURE.md (Section 4, 3-Layer Independent Architecture)
           docs/prompts/OPERATIVE_BRIEF_BACKTEST_V1_2.md (AC1-AC3)
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Tuple
from uuid import uuid4
import sqlite3
import logging

# ============================================================================
# ENUMS & TYPE DEFINITIONS
# ============================================================================


class SignalType(str, Enum):
    """Direção do sinal gerado pelo SMC M5 detector."""
    BUY = "BUY"
    SELL = "SELL"


class SMCDetector(str, Enum):
    """Qual estrutura SMC foi detectada."""
    BOS = "BOS"  # Break of Structure
    CHOCH = "CHoCH"  # Change of Character
    FVG = "FVG"  # Fair Value Gap


class SignalOutcomeType(str, Enum):
    """Classificação final do sinal após seu ciclo de vida."""
    WINNING_SIGNAL = "WINNING_SIGNAL"  # Teria sido vencedor
    WHIPSAW = "WHIPSAW"  # Reversão rápida
    MISSED_OPPORTUNITY = "MISSED_OPPORTUNITY"  # Falsa geração
    OPEN = "OPEN"  # Ainda em aberto


class DecisionType(str, Enum):
    """Tipo de decisão tomada na Camada 2."""
    ENTRAR = "ENTRAR"  # Execute trade
    FICAR_DE_FORA = "FICAR_DE_FORA"  # Reject signal


class DecisionCorrectnessStage1(str, Enum):
    """Etapa 1: A decisão foi correta (qualidade do acerto/erro)?"""
    CORRETA = "CORRETA"  # Decisão tomada foi correta
    ERRADA = "ERRADA"  # Decisão tomada foi errada


class DecisionQualityStage2(str, Enum):
    """Etapa 2: A decisão foi correta pelos motivos corretos?"""
    CORRETO_COM_RAZOES_CERTAS = "CORRETO_COM_RAZOES_CERTAS"  # Acertou e motivos confirmados
    CORRETO_POR_ACASO = "CORRETO_POR_ACASO"  # Acertou mas motivadores falsos
    ERRADO_MAS_MOTIVADORES_CONFIRMADOS = "ERRADO_MAS_MOTIVADORES_CONFIRMADOS"
    ERRADO_COM_RAZOES_ERRADAS = "ERRADO_COM_RAZOES_ERRADAS"  # Errou tudo


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class MarketContext:
    """
    Contexto de mercado capturado no momento do sinal.

    Camada 1 captura TODOS os indicadores em tempo real
    para auditoria e análise posterior.

    Atributos:
        rsi: Relative Strength Index (0-100)
        atr: Average True Range (volatilidade)
        bb_upper: Bollinger Band superior
        bb_lower: Bollinger Band inferior
        volume: Volume de negociação
        spread: Diferença bid-ask em pontos
        trend_direction: Direção da tendência (UP/DOWN/FLAT)
        last_close: Último close antes do sinal
    """

    rsi: Optional[float] = None  # 0-100
    atr: Optional[float] = None  # Volatilidade
    bb_upper: Optional[float] = None  # Bollinger upper
    bb_lower: Optional[float] = None  # Bollinger lower
    volume: Optional[int] = None  # Negócios
    spread: Optional[float] = None  # Bid-ask diff
    trend_direction: Optional[str] = None  # UP/DOWN/FLAT
    last_close: Optional[float] = None  # Preço anterior


@dataclass
class DecisionReasoning:
    """
    Motivos/explicação da decisão tomada na Camada 2.

    Camada 2 persiste NÃO APENAS a decisão (ENTRAR/FICAR),
    mas os MOTIVOS que levaram à decisão.

    Atributos:
        decision: ENTRAR ou FICAR_DE_FORA
        ml_confidence: Score do modelo (0-100%)
        top_features: Top 3 features que influenciaram
        feature_scores: Dict com scores de cada feature
        reasoning_text: Explicação em texto livre
    """

    decision: DecisionType
    ml_confidence: float  # 0-100
    top_features: list = None  # Top 3 ['rsi_bullish', 'volume_spike', 'atr_low']
    feature_scores: dict = None  # {'rsi': 0.75, 'volume': 0.60, 'atr': 0.45}
    reasoning_text: str = None  # "Alta confiança RSI, mas volume baixo"

    def __post_init__(self):
        if self.top_features is None:
            self.top_features = []
        if self.feature_scores is None:
            self.feature_scores = {}


@dataclass
class Signal:
    """
    Representação de um sinal gerado por Camada 1.

    Um sinal é gerado quando M5 detecta estrutura SMC (BOS/CHoCH/FVG).
    Sinal é INDEPENDENTE de qualquer decisão de entrada.

    **REFINADO (05/03/2026):**
    Agora captura TODO o contexto de mercado no momento do sinal
    para auditoria, análise posterior e aprendizado (Camada 3).

    Atributos:
        signal_id: UUID único (rastreamento global)
        timestamp: Quando M5 candle fechou (tempo exato)
        symbol: Código do ativo (WIN, WDO)
        signal_type: BUY ou SELL (direção do sinal)
        smc_score: Score SMC consolidado [-3, +3] (força)
        smc_detector: Qual estrutura detectou (BOS/CHoCH/FVG)
        entry_price: Preço no momento da geração
        candle_index: Índice do candle M5 (auditoria)
        market_context: **NOVO** Indicadores de mercado em tempo real
    """

    signal_id: str
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    smc_score: float
    smc_detector: SMCDetector
    entry_price: float
    candle_index: int
    market_context: Optional[MarketContext] = None  # **NOVO**: Contexto completo
    outcome_trade_id: Optional[int] = None
    outcome_pnl: Optional[float] = None
    outcome_days_open: Optional[float] = None
    outcome_type: Optional[SignalOutcomeType] = None
    created_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        """Signal está completo (tem outcome defini dado)."""
        return self.outcome_type is not None and self.outcome_type != SignalOutcomeType.OPEN


# ============================================================================
# CAMADA 2: DECISION (Motor de Decisão Independente)
# ============================================================================


@dataclass
class Decision:
    """
    Decisão tomada por Camada 2 (Motor de Decisão).

    Camada 2 toma decisão INDEPENDENTE: ENTRAR ou FICAR_DE_FORA.
    Persiste NÃO APENAS a decisão, mas os MOTIVOS da decisão.

    **REFINADO (05/03/2026):**
    - Persiste DecisionReasoning (explainability)
    - Vinculação com Signal ID (rastreamento)

    Atributos:
        decision_id: UUID único
        signal_id: Referência ao sinal (FK)
        timestamp: Quando a decisão foi tomada
        decision: ENTRAR ou FICAR_DE_FORA
        ml_confidence: Score do modelo (0-100%)
        reasoning: **NOVO** Motivos da decisão
        outcome_pnl: P&L resultado (preenchido em Camada 3)
        outcome_correct: **NOVO** Etapa 1 - Decision correctness
        outcome_quality: **NOVO** Etapa 2 - Decision quality
    """

    decision_id: str
    signal_id: str  # FK para signals
    timestamp: datetime
    decision: DecisionType  # ENTRAR ou FICAR_DE_FORA
    ml_confidence: float  # 0-100
    reasoning: Optional[DecisionReasoning] = None  # Motivos da decisão
    outcome_pnl: Optional[float] = None
    outcome_correct: Optional[DecisionCorrectnessStage1] = None  # Etapa 1
    outcome_quality: Optional[DecisionQualityStage2] = None  # Etapa 2
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ============================================================================
# CAMADA 3: LEARNING FEEDBACK (2 Etapas de Validação)
# ============================================================================


@dataclass
class LearningFeedback:
    """
    Feedback de aprendizado em 2 etapas (Camada 3).

    Sinal encerrado após acompanhamento.
    Feedback ocorre em DUAS ETAPAS INDEPENDENTES.

    **Etapa 1: Decision Correctness**
    - A decisão foi CORRETA ou ERRADA?
    - ENTROU e PROFITABLE → CORRETA
    - ENTROU e LOSS → ERRADA
    - FICOU_DE_FORA e teria P+ → ERRADA
    - FICOU_DE_FORA e teria L → CORRETA

    **Etapa 2: Decision Quality**
    - A decisão foi correta pelos corretos MOTIVOS?
    - CORRETO_COM_RAZOES_CERTAS: Acertou e motivadores confirmados
    - CORRETO_POR_ACASO: Acertou mas motivadores falsos
    - ERRADO_MAS_MOTIVADORES_CONFIRMADOS: Errou, mas razões eram válidas (mercado foi contra)
    - ERRADO_COM_RAZOES_ERRADAS: Errou tudo

    Atributos:
        feedback_id: UUID único
        decision_id: FK para Decision
        signal_id: FK para Signal
        stage_1_correctness: CORRETA ou ERRADA (resultado)
        stage_2_quality: Qualidade da decisão (motivadores confirmados?)
        trade_pnl: P&L final do trade
        motivators_analysis: Análise dos motivadores (confirmados ou não?)
        recommendations: Recomendações para próximas decisões
    """

    feedback_id: str
    decision_id: str  # FK
    signal_id: str  # FK
    stage_1_correctness: DecisionCorrectnessStage1
    stage_2_quality: DecisionQualityStage2
    trade_pnl: float
    motivators_analysis: Optional[str] = None  # Confirmaram? Falharam?
    recommendations: Optional[str] = None  # Lições aprendidas
    created_at: Optional[datetime] = None


# ============================================================================
# SIGNAL GENERATOR (Camada 1 - Primeira Parte)
# ============================================================================


class SignalGenerator:
    """
    Gerador de sinais SMC em timeframe M5.

    Responsabilidades:
        - Detectar estruturas SMC em candles M5
        - Calcular SMC score consolidado [-3, +3]
        - Criar objetos Signal

    Não persiste - apenas gera!
    Persistência é responsabilidade de SignalPersistence.

    Exemplo:
        generator = SignalGenerator()
        signal = generator.detect_smc(
            candles_m5=df_m5,
            symbol="WIN",
            current_price=123456.50
        )
        if signal:
            persistence.insert(signal)  # Camada 1 → DB
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Inicializa detector.

        Args:
            logger: Logger para debug/info (opcional)
        """
        self.logger = logger or logging.getLogger(__name__)

    def detect_smc(
        self,
        candles_m5: dict,
        symbol: str,
        current_price: float,
        market_context: Optional[MarketContext] = None,
        candle_index: int = 0,
    ) -> Optional[Signal]:
        """
        Procura estrutura SMC nos candles M5 e captura contexto de mercado.

        **REFINADO (05/03/2026) - AC1 Implementation:**
        - Detecta BOS, CHoCH, FVG
        - Score produzido em range [-3, +3]
        - Captura COMPLETO contexto de mercado
        - Sinal INDEPENDENTE de decisão de entrada

        Detecção SMC:
            BOS (Break of Structure): Close > High anterior ou < Low anterior
            CHoCH (Change of Character): Reversão da estrutura anterior
            FVG (Fair Value Gap): Gap entre candles (abertura de espaço)

        Args:
            candles_m5: Dict com OHLC (open, high, low, close, volume)
                        KEYS: open, high, low, close, volume, prev_high, prev_low
            symbol: Código do ativo (ex: WIN, WDO)
            current_price: Preço atual (entry_price)
            market_context: Indicadores de mercado (RSI, ATR, volume, etc)
            candle_index: Índice do candle (auditoria)

        Returns:
            Signal object se detectado, None caso contrário (fraco demais)
        """
        try:
            # Validações de entrada
            if not candles_m5 or "close" not in candles_m5:
                return None

            current_open = candles_m5.get("open", 0.0)
            current_high = candles_m5.get("high", 0.0)
            current_low = candles_m5.get("low", 0.0)
            current_close = candles_m5.get("close", 0.0)
            current_volume = candles_m5.get("volume", 0)

            prev_high = candles_m5.get("prev_high", 0.0)
            prev_low = candles_m5.get("prev_low", 0.0)
            prev_close = candles_m5.get("prev_close", current_close)

            # Inicializar variáveis de sinal
            smc_score = 0.0
            smc_detector = None
            signal_type = None

            # ================================================================
            # 1. DETECTAR BOS (Break of Structure)
            # ================================================================

            if current_close > prev_high:
                # Bullish BOS: close rompe high anterior
                smc_score = 1.5
                smc_detector = SMCDetector.BOS
                signal_type = SignalType.BUY

            elif current_close < prev_low:
                # Bearish BOS: close quebra low anterior
                smc_score = -1.5
                smc_detector = SMCDetector.BOS
                signal_type = SignalType.SELL

            # ================================================================
            # 2. DETECTAR CHoCH (Change of Character)
            # ================================================================

            # CHoCH: Reversão da estrutura (low mais baixo em uptrend, ou high mais alto em downtrend)
            elif current_low < prev_low:
                # Bearish CHoCH: novo low
                smc_score = -2.0  # CHoCH score mais forte que BOS puro
                smc_detector = SMCDetector.CHOCH
                signal_type = SignalType.SELL

            elif current_high > prev_high:
                # Bullish CHoCH: novo high
                smc_score = 2.0  # CHoCH score mais forte
                smc_detector = SMCDetector.CHOCH
                signal_type = SignalType.BUY

            # ================================================================
            # 3. DETECTAR FVG (Fair Value Gap)
            # ================================================================

            # FVG Bullish: gap acima (atual low > prev high, com volume baixo)
            elif current_low > prev_high and current_volume < 150:
                # Gap bullish: espaço não preenchido
                smc_score = 1.0  # FVG score base
                smc_detector = SMCDetector.FVG
                signal_type = SignalType.BUY

            # FVG Bearish: gap abaixo (atual high < prev low, com volume baixo)
            elif current_high < prev_low and current_volume < 150:
                # Gap bearish: espaço não preenchido
                smc_score = -1.0  # FVG score negativo
                smc_detector = SMCDetector.FVG
                signal_type = SignalType.SELL

            else:
                # Nenhuma estrutura detectada
                return None

            # ================================================================
            # 4. VALIDAÇÃO DE SCORE MÍNIMO
            # ================================================================

            # Rejeitar sinais muito fracos (|score| < 1.0)
            if abs(smc_score) < 1.0:
                self.logger.debug(
                    f"Signal rejeitado: score {smc_score:.2f} > limite 1.0"
                )
                return None

            # Garantir que score está em [-3, +3]
            smc_score = max(-3.0, min(3.0, smc_score))

            # ================================================================
            # 5. CAPTURAR CONTEXTO DE MERCADO
            # ================================================================

            # Criar market_context se não fornecido
            if market_context is None:
                market_context = MarketContext()

            # ================================================================
            # 6. GERAR SIGNAL (Camada 1 - INDEPENDENTE de decisão)
            # ================================================================

            signal = Signal(
                signal_id=str(uuid4()),  # UUID único para cada sinal
                timestamp=datetime.now(),
                symbol=symbol,
                signal_type=signal_type,
                smc_score=smc_score,
                smc_detector=smc_detector,
                entry_price=current_price,
                candle_index=candle_index,
                market_context=market_context,  # Contexto capturado
                created_at=datetime.now(),
            )

            self.logger.info(
                f"[AC1-Signal] {signal.signal_type} "
                f"({smc_detector.value}, score={smc_score:+.2f}) "
                f"@{symbol} - Context captured"
            )
            return signal

        except Exception as e:
            self.logger.error(f"[AC1-Error] Erro detectando SMC: {e}")
            return None


# ============================================================================
# SIGNAL PERSISTENCE (Camada 1 - Persistência)
# ============================================================================


class SignalPersistence:
    """
    Persistência de sinais em SQLite (tabela `signals`).

    Responsabilidades:
        - Inserir novos sinais
        - Atualizar sinais com outcome (quando trade fecha)
        - Consultar histórico de sinais
        - Validação de integridade

    Padrão Repository: abstrai SQL da lógica de negócio.

    Exemplo:
        persistence = SignalPersistence(db_path="/data/db/trading.db")
        persistence.insert(signal)  # Camada 1 → DB
        persistence.update_outcome(signal_id, trade_id, pnl)  # Após trade
    """

    def __init__(self, db_path: str = "data/db/trading.db"):
        """
        Inicializa conexão com DB.

        Args:
            db_path: Caminho para arquivo SQLite
        """
        self.db_path = db_path
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        """Cria tabela `signals` se não existir."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT UNIQUE NOT NULL,
                    timestamp DATETIME NOT NULL,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    smc_score REAL NOT NULL,
                    smc_detector TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    candle_index INTEGER,
                    outcome_trade_id INTEGER,
                    outcome_pnl REAL,
                    outcome_days_open REAL,
                    outcome_type TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    closed_at DATETIME,

                    FOREIGN KEY(outcome_trade_id) REFERENCES trades(id),
                    CHECK(signal_type IN ('BUY', 'SELL')),
                    CHECK(outcome_type IN ('WINNING_SIGNAL', 'WHIPSAW',
                                          'MISSED_OPPORTUNITY', 'OPEN')),
                    CHECK(smc_score >= -3.0 AND smc_score <= 3.0),
                    UNIQUE(timestamp, symbol, signal_type)
                )
                """
            )

            # Criar índices
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_signals_timestamp "
                "ON signals(timestamp DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_signals_symbol_timestamp "
                "ON signals(symbol, timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_signals_outcome_type "
                "ON signals(outcome_type)"
            )

            conn.commit()
            conn.close()

        except sqlite3.Error as e:
            logging.error(f"Erro criando tabela signals: {e}")
            raise

    def insert(self, signal: Signal) -> bool:
        """
        Insere novo sinal em DB.

        Args:
            signal: Signal object a persistir

        Returns:
            True se inserção bem-sucedida, False caso contrário
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO signals (
                    signal_id, timestamp, symbol, signal_type,
                    smc_score, smc_detector, entry_price, candle_index,
                    outcome_type, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal.signal_id,
                    signal.timestamp,
                    signal.symbol,
                    signal.signal_type.value,
                    signal.smc_score,
                    signal.smc_detector.value,
                    signal.entry_price,
                    signal.candle_index,
                    SignalOutcomeType.OPEN.value,  # Sempre começa OPEN
                    signal.created_at,
                ),
            )

            conn.commit()
            conn.close()

            logging.info(f"Signal {signal.signal_id} persistido")
            return True

        except sqlite3.IntegrityError as e:
            logging.warning(f"Sinal duplicado (esperado): {e}")
            return False
        except sqlite3.Error as e:
            logging.error(f"Erro inserindo signal: {e}")
            return False

    def update_outcome(
        self,
        signal_id: str,
        trade_id: int,
        pnl: float,
        outcome_type: SignalOutcomeType,
        days_open: float = 0.0,
    ) -> bool:
        """
        Atualiza sinal com outcome após trade ser fechado.

        Chamado por Camada 3 (aprendizado) quando P&L fica conhecido.

        Args:
            signal_id: UUID do sinal
            trade_id: ID do trade que executou o sinal
            pnl: P&L resultado (-1000 = LOSS, +500 = PROFIT)
            outcome_type: Classificação final (WINNING/WHIPSAW/MISSED)
            days_open: Quantos dias o sinal ficou aberto

        Returns:
            True se atualização bem-sucedida
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE signals
                SET outcome_trade_id = ?,
                    outcome_pnl = ?,
                    outcome_days_open = ?,
                    outcome_type = ?,
                    closed_at = ?
                WHERE signal_id = ?
                """,
                (
                    trade_id,
                    pnl,
                    days_open,
                    outcome_type.value,
                    datetime.now(),
                    signal_id,
                ),
            )

            conn.commit()
            conn.close()

            logging.info(f"Signal {signal_id} outcome atualizado: {outcome_type.value}")
            return True

        except sqlite3.Error as e:
            logging.error(f"Erro atualizando signal outcome: {e}")
            return False

    def get_signal(self, signal_id: str) -> Optional[Signal]:
        """Recupera sinal por ID."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM signals WHERE signal_id = ?", (signal_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            return self._row_to_signal(row)

        except sqlite3.Error as e:
            logging.error(f"Erro consultando signal: {e}")
            return None

    def get_signals_by_symbol(self, symbol: str, limit: int = 100) -> list[Signal]:
        """Recupera últimos sinais de um símbolo."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM signals
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (symbol, limit),
            )
            rows = cursor.fetchall()
            conn.close()

            return [self._row_to_signal(row) for row in rows]

        except sqlite3.Error as e:
            logging.error(f"Erro consultando signals: {e}")
            return []

    @staticmethod
    def _row_to_signal(row: sqlite3.Row) -> Signal:
        """Converte sqlite3.Row para objeto Signal."""
        return Signal(
            signal_id=row["signal_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            symbol=row["symbol"],
            signal_type=SignalType(row["signal_type"]),
            smc_score=row["smc_score"],
            smc_detector=SMCDetector(row["smc_detector"]),
            entry_price=row["entry_price"],
            candle_index=row["candle_index"],
            outcome_trade_id=row["outcome_trade_id"],
            outcome_pnl=row["outcome_pnl"],
            outcome_days_open=row["outcome_days_open"],
            outcome_type=(
                SignalOutcomeType(row["outcome_type"])
                if row["outcome_type"]
                else None
            ),
            created_at=(
                datetime.fromisoformat(row["created_at"])
                if row["created_at"]
                else None
            ),
            closed_at=(
                datetime.fromisoformat(row["closed_at"]) if row["closed_at"] else None
            ),
        )


# ============================================================================
# SIGNAL TRACKER (Ciclo de Vida)
# ============================================================================


class SignalTracker:
    """
    Rastreamento do ciclo de vida completo de sinais.

    Responsabilidades:
        - Abrir novo sinal (Signal.OPEN)
        - Fechar sinal com outcome (Signal.CLOSED)
        - Calcular P&L hipotético vs real
        - Classificar como WINNING/WHIPSAW/MISSED

    Integração com Camada 1 → Camada 2 → Camada 3.

    Exemplo:
        tracker = SignalTracker(persistence)
        signal = tracker.open_signal(...)  # Camada 1
        ...  # Camada 2: ML decision ENTRAR/FICAR_DE_FORA
        tracker.close_signal(signal_id, trade_pnl)  # Camada 3
    """

    def __init__(self, persistence: SignalPersistence):
        """
        Inicializa tracker com banco de dados.

        Args:
            persistence: SignalPersistence para acesso a DB
        """
        self.persistence = persistence
        self.logger = logging.getLogger(__name__)

    def open_signal(
        self, signal: Signal
    ) -> bool:
        """
        Abre novo sinal (insere em DB).

        Args:
            signal: Signal object

        Returns:
            True se bem-sucedido
        """
        return self.persistence.insert(signal)

    def close_signal(
        self,
        signal_id: str,
        trade_id: Optional[int] = None,
        trade_pnl: Optional[float] = None,
        days_open: float = 0.0,
    ) -> bool:
        """
        Fecha sinal com outcome.

        Lógica de classificação:
            - WINNING_SIGNAL: trade_pnl > 0
            - MISS_OPPORTUNITY: trade_pnl < 0 (falha na geração)
            - WHIPSAW: trade reverso rápido (muito dias_open pequeno)

        Args:
            signal_id: UUID do sinal
            trade_id: ID do trade (se executou)
            trade_pnl: P&L do trade
            days_open: Duração em dias

        Returns:
            True se bem-sucedido
        """
        if trade_pnl is None:
            # Sinal não foi executado (Camada 2: FICAR_DE_FORA)
            outcome_type = SignalOutcomeType.OPEN
            return self.persistence.update_outcome(
                signal_id, None, 0.0, outcome_type, days_open
            )

        # Classificar outcome
        if trade_pnl > 0:
            outcome = SignalOutcomeType.WINNING_SIGNAL
        elif days_open < 0.1:  # Menos de 2 horas
            outcome = SignalOutcomeType.WHIPSAW
        else:
            outcome = SignalOutcomeType.MISSED_OPPORTUNITY

        self.logger.info(f"Signal {signal_id} fechado: {outcome.value} (P&L={trade_pnl})")
        return self.persistence.update_outcome(signal_id, trade_id, trade_pnl, outcome, days_open)


# ============================================================================
# EXEMPLO DE USO (Doctest)
# ============================================================================

if __name__ == "__main__":
    """
    Exemplo de uso da Camada 1 (Signal Generation & Persistence)

    Fluxo:
        1. Gerar signal com SMC detector
        2. Persistir em DB
        3. Simular decisão Camada 2 (ENTRAR/FICAR_DE_FORA)
        4. Simular trade fechado Camada 3
        5. Atualizar outcome e aprender
    """

    # Setup
    generator = SignalGenerator()
    persistence = SignalPersistence()
    tracker = SignalTracker(persistence)

    # Passo 1: Gerar signal (Camada 1)
    candles = {"close": 123500.0, "prev_high": 123400.0, "prev_low": 123200.0}
    signal = generator.detect_smc(
        candles_m5=candles, symbol="WIN", current_price=123500.0, candle_index=0
    )

    if signal:
        # Passo 2: Persistir em DB
        tracker.open_signal(signal)
        print(f"✓ Signal criado: {signal.signal_id} ({signal.signal_type})")

        # Passo 3: Simular Camada 2 (ML decision) - ENTROU
        # Passo 4: Simular Camada 3 - trade executado com profit
        trade_outcome_pnl = 250.0  # Lucrou R$ 250
        tracker.close_signal(
            signal.signal_id, trade_id=1, trade_pnl=trade_outcome_pnl, days_open=0.5
        )
        print(f"✓ Signal outcome: {signal_id} WINNING_SIGNAL (+R${trade_outcome_pnl})")
