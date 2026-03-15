"""
AC5.9: Feedback de Execução para ML

Componente que converte outcomes de trades executadas em sinais rotulados
persistidos em SQLite para retraining online de modelos ML/RL.

Fluxo:
1. Trade é executada em INICIAR_MICRO_TENDENCIA_AUTO_TRADE
2. TradeOutcomeFeedback processa outcome (PnL)
3. Sinal é rotulado (GOOD/BAD) com base em resultado
4. Persistido em rl_episodes ou tabela dedicada para ML usar

Tabelas SQLite:
- TRADES: entrada, saída, PnL, prediction_id
- PREDICTIONS: confidence, direction
- EXECUTION_FEEDBACK (nova): trade_id, signal_label, outcome_type, confidence
"""

import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExecutionOutcome:
    """Resultado de uma execução de trade."""

    trade_id: int
    signal_label: str  # "GOOD" ou "BAD"
    outcome_type: str  # "WIN", "LOSS", "BREAKEVEN"
    confidence: float  # 0.0 a 1.0
    pnl: float
    prediction_direction: str  # "BUY", "SELL", "HOLD"
    feedback_id: Optional[int] = None
    timestamp: Optional[str] = None


class TradeOutcomeFeedbackDB:
    """
    Processador de feedback de execução com persistência em SQLite.

    Responsabilidades:
    - Ler trades executadas
    - Correlacionar com predictions
    - Rotular como GOOD/BAD
    - Persistir para ML
    """

    LABEL_GOOD = "GOOD"
    LABEL_BAD = "BAD"

    def __init__(self, db_path: str = "data/db/trading.db"):
        """
        Inicializar com caminho do banco SQLite.

        Args:
            db_path: Path para trading.db (SQLite)
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self._ensure_execution_feedback_table()

    def _get_connection(self) -> sqlite3.Connection:
        """Obter conexão SQLite (lazy initialization)."""
        if self.conn is None:
            self.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
            )
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def _ensure_execution_feedback_table(self) -> None:
        """Criar tabela EXECUTION_FEEDBACK se não existir."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Criar tabela é idempotente
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER NOT NULL UNIQUE,
                signal_label TEXT NOT NULL,
                outcome_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                pnl REAL NOT NULL,
                prediction_direction TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(trade_id) REFERENCES trades(id),
                CHECK(signal_label IN ('GOOD', 'BAD')),
                CHECK(outcome_type IN ('WIN', 'LOSS', 'BREAKEVEN')),
                CHECK(confidence >= 0.0 AND confidence <= 1.0)
            )
        """)

        # Índice para queries rápidas
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_execution_feedback_trade_id
            ON execution_feedback(trade_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_execution_feedback_label
            ON execution_feedback(signal_label)
        """)

        conn.commit()
        logger.info("Tabela execution_feedback validada")

    def process_trade_outcome(self, trade_id: int) -> ExecutionOutcome:
        """
        Processar outcome de um trade específico.

        Args:
            trade_id: ID da trade em TRADES table

        Returns:
            ExecutionOutcome com feedback rotulado e persistido

        Raises:
            ValueError: Se trade não encontrado ou dados inválidos
            KeyError: Se prediction não encontrado
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Step 1: Recuperar trade
        cursor.execute("""
            SELECT id, pnl, decisions_id
            FROM trades
            WHERE id = ?
        """, (trade_id,))

        trade_row = cursor.fetchone()
        if not trade_row:
            raise ValueError(f"Trade {trade_id} não encontrado em TRADES")

        pnl: float = trade_row["pnl"]

        # Step 2: Recuperar prediction mais recente por trade
        # Estratégia simplificad: obter prediction mais recente anterior ao trade
        # (Em produção, haveria uma tabela de junção ou FK explícita)
        cursor.execute("""
            SELECT direction, confidence_score
            FROM predictions
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        pred_row = cursor.fetchone()
        if not pred_row:
            raise KeyError(
                f"Prediction não encontrado para trade {trade_id}"
            )

        prediction_direction: str = pred_row["direction"]
        confidence: float = pred_row["confidence_score"]

        # Step 3: Rotular baseado em PnL
        signal_label = self.LABEL_GOOD if pnl > 0 else self.LABEL_BAD

        # Step 4: Determinar tipo de outcome
        outcome_type = self._determine_outcome_type(pnl)

        # Step 5: Persistir em EXECUTION_FEEDBACK
        feedback_id = self._save_execution_feedback(
            trade_id=trade_id,
            signal_label=signal_label,
            outcome_type=outcome_type,
            confidence=confidence,
            pnl=pnl,
            prediction_direction=prediction_direction,
        )

        logger.info(
            f"Trade {trade_id} processado: label={signal_label}, "
            f"outcome={outcome_type}, pnl={pnl:.2f}, confidence={confidence:.2f}"
        )

        return ExecutionOutcome(
            trade_id=trade_id,
            signal_label=signal_label,
            outcome_type=outcome_type,
            confidence=confidence,
            pnl=pnl,
            prediction_direction=prediction_direction,
            feedback_id=feedback_id,
            timestamp=datetime.utcnow().isoformat(),
        )

    def _determine_outcome_type(self, pnl: float) -> str:
        """
        Classificar tipo de outcome.

        Args:
            pnl: Profit/Loss do trade

        Returns:
            "WIN", "LOSS", ou "BREAKEVEN"
        """
        if pnl > 0:
            return "WIN"
        elif pnl < 0:
            return "LOSS"
        else:
            return "BREAKEVEN"

    def _save_execution_feedback(
        self,
        trade_id: int,
        signal_label: str,
        outcome_type: str,
        confidence: float,
        pnl: float,
        prediction_direction: str,
    ) -> int:
        """
        Persistir feedback em EXECUTION_FEEDBACK.

        Args:
            trade_id: ID do trade
            signal_label: "GOOD" ou "BAD"
            outcome_type: "WIN", "LOSS", ou "BREAKEVEN"
            confidence: Score de confiança [0, 1]
            pnl: Profit/Loss em R$
            prediction_direction: Direção original

        Returns:
            ID do feedback inserido
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO execution_feedback (
                    trade_id, signal_label, outcome_type,
                    confidence, pnl, prediction_direction
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                trade_id, signal_label, outcome_type,
                confidence, pnl, prediction_direction
            ))
            conn.commit()
            feedback_id = cursor.lastrowid
            return feedback_id
        except sqlite3.IntegrityError as e:
            logger.warning(f"Feedback já existe para trade {trade_id}: {e}")
            # Recuperar ID existente
            cursor.execute(
                "SELECT id FROM execution_feedback WHERE trade_id = ?",
                (trade_id,)
            )
            row = cursor.fetchone()
            return row["id"] if row else -1

    def process_multiple_trades(
        self, trade_ids: List[int]
    ) -> List[ExecutionOutcome]:
        """
        Processar múltiplos trades (batch).

        Args:
            trade_ids: Lista de IDs de trades

        Returns:
            Lista de ExecutionOutcome (sucesso ou erro capturado)
        """
        results = []
        for trade_id in trade_ids:
            try:
                outcome = self.process_trade_outcome(trade_id)
                results.append(outcome)
            except (ValueError, KeyError) as e:
                logger.error(f"Erro ao processar trade {trade_id}: {e}")
                results.append(
                    ExecutionOutcome(
                        trade_id=trade_id,
                        signal_label="ERROR",
                        outcome_type="ERROR",
                        confidence=0.0,
                        pnl=0.0,
                        prediction_direction="UNKNOWN",
                    )
                )

        return results

    def get_feedback_stats(self) -> Dict[str, any]:
        """
        Obter estatísticas de feedback persistido.

        Returns:
            Dict com contagem good/bad, win rate, avg confidence
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN signal_label = 'GOOD' THEN 1 ELSE 0 END) as good_count,
                SUM(CASE WHEN signal_label = 'BAD' THEN 1 ELSE 0 END) as bad_count,
                AVG(confidence) as avg_confidence,
                AVG(pnl) as avg_pnl,
                MAX(pnl) as max_pnl,
                MIN(pnl) as min_pnl
            FROM execution_feedback
        """)

        row = cursor.fetchone()
        total = row["total"] or 0
        good = row["good_count"] or 0
        bad = row["bad_count"] or 0

        return {
            "total_feedbacks": total,
            "good_count": good,
            "bad_count": bad,
            "good_rate_percent": (good / total * 100) if total > 0 else 0.0,
            "avg_confidence": row["avg_confidence"] or 0.0,
            "avg_pnl": row["avg_pnl"] or 0.0,
            "max_pnl": row["max_pnl"] or 0.0,
            "min_pnl": row["min_pnl"] or 0.0,
        }

    def close(self) -> None:
        """Fechar conexão SQLite."""
        if self.conn:
            self.conn.close()
            self.conn = None
