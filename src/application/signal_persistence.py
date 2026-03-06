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


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass
class Signal:
    """
    Representação de um sinal gerado por Camada 1.

    Um sinal é gerado quando M5 detecta estrutura SMC (BOS/CHoCH/FVG).
    Sinal é INDEPENDENTE de qualquer decisão de entrada.

    Atributos:
        signal_id: UUID único (rastreamento global)
        timestamp: Quando M5 candle fechou (tempo exato)
        symbol: Código do ativo (WIN, WDO)
        signal_type: BUY ou SELL (direção do sinal)
        smc_score: Score SMC consolidado [-3, +3] (força)
        smc_detector: Qual estrutura detectou (BOS/CHoCH/FVG)
        entry_price: Preço no momento da geração
        candle_index: Índice do candle M5 (auditoria)
    """

    signal_id: str
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    smc_score: float
    smc_detector: SMCDetector
    entry_price: float
    candle_index: int
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
        candle_index: int = 0,
    ) -> Optional[Signal]:
        """
        Procura estrutura SMC nos candles M5.

        Lógica simplificada para exemplo:
            - BOS: close > previous high (bullish) ou close < previous low (bearish)
            - Valida SMC score (deve estar >= |1.0| para gerar sinal)

        Args:
            candles_m5: Dict com OHLC (open, high, low, close, volume)
            symbol: Código do ativo
            current_price: Preço atual (entry_price)
            candle_index: Índice do candle (auditoria)

        Returns:
            Signal object se detectado, None caso contrário
        """
        try:
            # Validações de entrada
            if not candles_m5 or "close" not in candles_m5:
                return None

            current_close = candles_m5.get("close", 0.0)
            previous_high = candles_m5.get("prev_high", 0.0)
            previous_low = candles_m5.get("prev_low", 0.0)

            # Detectar BOS (Break of Structure)
            smc_score = 0.0
            smc_detector = None

            if current_close > previous_high:
                # Bullish BOS
                smc_score = 1.5  # Score base para BOS
                smc_detector = SMCDetector.BOS
                signal_type = SignalType.BUY
            elif current_close < previous_low:
                # Bearish BOS
                smc_score = -1.5  # Score negativo para SELL
                smc_detector = SMCDetector.BOS
                signal_type = SignalType.SELL
            else:
                # Sem estrutura detectada
                return None

            # Validar se score está >= limite (|1.0|)
            if abs(smc_score) < 1.0:
                return None

            # Gerar signal com UUID
            signal = Signal(
                signal_id=str(uuid4()),
                timestamp=datetime.now(),
                symbol=symbol,
                signal_type=signal_type,
                smc_score=smc_score,
                smc_detector=smc_detector,
                entry_price=current_price,
                candle_index=candle_index,
                created_at=datetime.now(),
            )

            self.logger.info(
                f"Signal detectado: {signal.signal_type} "
                f"({signal.smc_detector}, score={signal.smc_score:.2f})"
            )
            return signal

        except Exception as e:
            self.logger.error(f"Erro detectando SMC: {e}")
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
