"""
Signal Tracker - AC3: Signal Lifecycle Management (Camada 3)

Sistema de rastreamento completo do ciclo de vida de sinais operacionais.

Responsabilidades:
    - Rastrear sinais desde geração (AC1) até fechamento (AC3)
    - Vincular sinais a trades (quando executada com base em sinal)
    - Atualizar outcomes dos sinais (P&L, status, duração)
    - Permitir análise retroativa de desempenho de sinais
    - Feedback loop para ML training (features vs outcomes)

Arquitetura AC1→AC2→AC3:
    AC1: SignalGenerator gera Signal com MarketContext
    AC2: SignalPersistence persiste Signal em DB (signals table)
    AC3: SignalTracker rastreia ciclo de vida + outcomes (ESTA CLASSE)

Status: Implementação v1.0 (05/03/2026)
Referência: docs/MODELAGEM_DADOS.md (Tabela 11: SIGNALS)
           docs/ARCHITECTURE.md (Section 4, 3-Layer Independent Architecture)
           docs/STATUS_ENTREGAS.md (AC3 Signal Tracking)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Tuple, Any
from uuid import UUID
import sqlite3
import logging
import json
from decimal import Decimal

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============================================================================
# ENUMS & TYPE DEFINITIONS
# ============================================================================


class SignalStatus(str, Enum):
    """Status do ciclo de vida do sinal."""
    OPEN = "OPEN"  # Sinal gerado, aguardando trade
    LINKED = "LINKED"  # Sinal vinculado a uma trade
    CLOSED = "CLOSED"  # Trade fechada, outcome calculado
    WHIPSAW = "WHIPSAW"  # Trade aberta mas logo revertida
    MISSED = "MISSED"  # Nunca foi executada (expirada)


class SignalOutcomeType(str, Enum):
    """Classificação final do sinal após seu ciclo de vida."""
    WINNING_SIGNAL = "WINNING_SIGNAL"  # P&L positivo
    LOSING_SIGNAL = "LOSING_SIGNAL"  # P&L negativo
    BREAKEVEN_SIGNAL = "BREAKEVEN_SIGNAL"  # P&L ≈ 0
    WHIPSAW_SIGNAL = "WHIPSAW_SIGNAL"  # Abriu mas reverteu rápido
    MISSED_SIGNAL = "MISSED_SIGNAL"  # Nunca executada
    PARTIAL_SIGNAL = "PARTIAL_SIGNAL"  # Parcialmente executada


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class SignalOutcome:
    """Resultado final de um sinal após seu ciclo de vida."""
    signal_id: str
    trade_id: Optional[int]
    status: SignalStatus
    outcome_type: SignalOutcomeType
    pnl: float  # Resultado em pontos
    pnl_percent: float  # Resultado em %
    days_open: float  # Duração em dias
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    volume: int
    notes: Optional[str] = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()


@dataclass
class SignalMetrics:
    """Métricas agregadas sobre desempenho de sinais."""
    total_signals: int
    winning_signals: int
    losing_signals: int
    missed_signals: int
    whipsaw_signals: int
    win_rate: float  # %
    avg_pnl_winner: float  # Pontos
    avg_pnl_loser: float  # Pontos
    total_pnl: float  # Pontos
    avg_holding_time: float  # Dias
    profit_factor: float  # (sum winners / abs(sum losers))
    recovery_factor: float  # (total_pnl / max_drawdown)


# ============================================================================
# SIGNAL TRACKER CLASS
# ============================================================================


class SignalTracker:
    """
    AC3: Rastreador de ciclo de vida completo de sinais.

    Responsabilidades:
    1. Vincular sinais gerados (AC1) a trades executadas
    2. Atualizar status e outcomes quando trades fecham
    3. Calcular P&L e duração do sinal
    4. Manter histórico para análise e feedback ML
    5. Gerar relatórios de desempenho de sinais
    """

    def __init__(self, db_path: str = "data/db/trading.db"):
        """
        Inicializa tracker de sinais.

        Args:
            db_path: Caminho do banco SQLite
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self._connect()
        logger.info(f"[AC3-INIT] Signal Tracker initialized at {db_path}")

    def _connect(self) -> None:
        """Estabelece conexão com DB."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"[AC3-DB] Connected to {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"[AC3-DB-ERROR] Connection failed: {e}")
            raise

    def link_signal_to_trade(
        self,
        signal_id: str,
        trade_id: int,
        execution_price: float,
        execution_time: datetime,
    ) -> bool:
        """
        Vincula um sinal gerado a uma trade executada.

        AC3.1: Quando uma trade é executada com base em um sinal,
        vincular o sinal à trade para rastreamento.

        Args:
            signal_id: ID único do sinal (UUID)
            trade_id: ID da trade executada
            execution_price: Preço de execução da trade
            execution_time: Timestamp de execução

        Returns:
            True se vínculo foi bem-sucedido
        """
        try:
            cursor = self.connection.cursor()

            # Validar que o sinal existe
            cursor.execute(
                "SELECT id, symbol, signal_type FROM signals WHERE signal_id = ?",
                (signal_id,),
            )
            signal_row = cursor.fetchone()
            if not signal_row:
                logger.warning(
                    f"[AC3-LINK-ERROR] Signal {signal_id} not found in DB"
                )
                return False

            # Atualizar a trade com referência ao sinal
            cursor.execute(
                """
                UPDATE signals
                SET outcome_trade_id = ?, status = 'LINKED'
                WHERE signal_id = ?
                """,
                (trade_id, signal_id),
            )

            self.connection.commit()
            logger.info(
                f"[AC3-LINK-OK] Signal {signal_id} linked to trade {trade_id}"
            )
            return True

        except sqlite3.Error as e:
            logger.error(f"[AC3-LINK-ERROR] Failed to link signal: {e}")
            self.connection.rollback()
            return False

    def update_signal_outcome(
        self,
        signal_id: str,
        trade_id: int,
        entry_price: float,
        exit_price: float,
        entry_time: datetime,
        exit_time: datetime,
        volume: int,
        side: str,  # BUY or SELL
        notes: Optional[str] = None,
    ) -> SignalOutcome:
        """
        Atualiza o outcome de um sinal quando a trade correspondente fecha.

        AC3.2: Quando uma trade fechada (com gain/loss), atualizar outcome
        do sinal e classificar como winner/loser/whipsaw.

        Args:
            signal_id: ID único do sinal
            trade_id: ID da trade
            entry_price: Preço de entrada
            exit_price: Preço de saída
            entry_time: Timestamp entrada
            exit_time: Timestamp saída
            volume: Volume negociado em unidades
            side: BUY or SELL
            notes: Notas opcionais

        Returns:
            SignalOutcome com resultado calculado
        """
        try:
            cursor = self.connection.cursor()

            # Validar que o sinal existe
            cursor.execute(
                "SELECT signal_type FROM signals WHERE signal_id = ?",
                (signal_id,),
            )
            signal_row = cursor.fetchone()
            if not signal_row:
                logger.warning(f"[AC3-UPDATE-ERROR] Signal {signal_id} not found")
                raise ValueError(f"Signal {signal_id} not found")

            signal_type = signal_row["signal_type"]

            # Calcular P&L
            if side == "BUY":
                points_pnl = exit_price - entry_price
            else:  # SELL
                points_pnl = entry_price - exit_price

            pnl_percent = (points_pnl / entry_price) * 100
            days_open = (exit_time - entry_time).total_seconds() / (24 * 3600)

            # Classificar sinal
            outcome_type = self._classify_outcome(
                points_pnl, pnl_percent, days_open, signal_type
            )

            # Atualizar DB
            cursor.execute(
                """
                UPDATE signals
                SET outcome_trade_id = ?,
                    outcome_pnl = ?,
                    outcome_days_open = ?,
                    outcome_type = ?,
                    closed_at = ?,
                    status = 'CLOSED'
                WHERE signal_id = ?
                """,
                (
                    trade_id,
                    points_pnl,
                    days_open,
                    outcome_type.value,
                    exit_time.isoformat(),
                    signal_id,
                ),
            )

            self.connection.commit()

            # Criar objeto outcome
            outcome = SignalOutcome(
                signal_id=signal_id,
                trade_id=trade_id,
                status=SignalStatus.CLOSED,
                outcome_type=outcome_type,
                pnl=points_pnl,
                pnl_percent=pnl_percent,
                days_open=days_open,
                entry_time=entry_time,
                exit_time=exit_time,
                entry_price=entry_price,
                exit_price=exit_price,
                volume=volume,
                notes=notes,
            )

            logger.info(
                f"[AC3-UPDATE-OK] Signal {signal_id} outcome: "
                f"{outcome_type.value} (P&L: {points_pnl:.2f} pts, {pnl_percent:.2f}%)"
            )

            return outcome

        except sqlite3.Error as e:
            logger.error(f"[AC3-UPDATE-ERROR] Failed to update outcome: {e}")
            self.connection.rollback()
            raise

    def mark_signal_missed(
        self, signal_id: str, expiration_time: datetime
    ) -> bool:
        """
        Marca um sinal como não-executado (expirado).

        AC3.3: Sinais que passam expectativa de vida sem
        ser vinculados a trades são marcados como MISSED.

        Args:
            signal_id: ID do sinal
            expiration_time: Quando o sinal expirou

        Returns:
            True se marcado com sucesso
        """
        try:
            cursor = self.connection.cursor()

            cursor.execute(
                """
                UPDATE signals
                SET outcome_type = 'MISSED_SIGNAL',
                    status = 'MISSED',
                    closed_at = ?
                WHERE signal_id = ? AND outcome_trade_id IS NULL
                """,
                (expiration_time.isoformat(), signal_id),
            )

            self.connection.commit()

            if cursor.rowcount > 0:
                logger.info(f"[AC3-MISSED] Signal {signal_id} marked as MISSED")
                return True
            else:
                logger.warning(f"[AC3-MISSED-ERROR] Signal {signal_id} not found")
                return False

        except sqlite3.Error as e:
            logger.error(f"[AC3-MISSED-ERROR] Failed to mark missed: {e}")
            self.connection.rollback()
            return False

    def get_signal_outcome(self, signal_id: str) -> Optional[SignalOutcome]:
        """
        Recupera o outcome de um sinal.

        Args:
            signal_id: ID do sinal

        Returns:
            SignalOutcome se encontrado, None caso contrário
        """
        try:
            cursor = self.connection.cursor()

            cursor.execute(
                """
                SELECT outcome_pnl, outcome_days_open, outcome_type,
                       created_at, closed_at
                FROM signals
                WHERE signal_id = ?
                """,
                (signal_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            # Aqui seria necessário mais dados, simplificado para exemplo
            outcome = SignalOutcome(
                signal_id=signal_id,
                trade_id=None,
                status=SignalStatus.CLOSED,
                outcome_type=SignalOutcomeType(row["outcome_type"]),
                pnl=row["outcome_pnl"] or 0,
                pnl_percent=0,  # Simplificado
                days_open=row["outcome_days_open"] or 0,
                entry_time=datetime.fromisoformat(row["created_at"]),
                exit_time=(
                    datetime.fromisoformat(row["closed_at"])
                    if row["closed_at"]
                    else None
                ),
                entry_price=0,  # Simplificado
                exit_price=None,  # Simplificado
                volume=0,  # Simplificado
            )

            return outcome

        except sqlite3.Error as e:
            logger.error(f"[AC3-GET-ERROR] Failed to get outcome: {e}")
            return None

    def get_open_signals(
        self, symbol: Optional[str] = None, max_age_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Recupera sinais ainda abertos (OPEN ou LINKED).

        AC3.4: Listar sinais pendentes para rastreamento.

        Args:
            symbol: Símbolo específico (opcional)
            max_age_hours: Idade máxima em horas (default 24h)

        Returns:
            Lista de sinais abertos
        """
        try:
            cursor = self.connection.cursor()

            cutoff_time = (
                datetime.utcnow() - timedelta(hours=max_age_hours)
            ).isoformat()

            if symbol:
                cursor.execute(
                    """
                    SELECT signal_id, symbol, signal_type, smc_score,
                           entry_price, created_at, status
                    FROM signals
                    WHERE status IN ('OPEN', 'LINKED')
                      AND symbol = ?
                      AND created_at > ?
                    ORDER BY created_at DESC
                    """,
                    (symbol, cutoff_time),
                )
            else:
                cursor.execute(
                    """
                    SELECT signal_id, symbol, signal_type, smc_score,
                           entry_price, created_at, status
                    FROM signals
                    WHERE status IN ('OPEN', 'LINKED')
                      AND created_at > ?
                    ORDER BY created_at DESC
                    """,
                    (cutoff_time,),
                )

            rows = cursor.fetchall()
            signals = [dict(row) for row in rows]

            logger.info(
                f"[AC3-LIST] Found {len(signals)} open signals "
                f"(symbol={symbol}, max_age={max_age_hours}h)"
            )

            return signals

        except sqlite3.Error as e:
            logger.error(f"[AC3-LIST-ERROR] Failed to list signals: {e}")
            return []

    def calculate_metrics(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> SignalMetrics:
        """
        Calcula métricas agregadas sobre desempenho de sinais.

        AC3.5: Análise de desempenho para feedback ML.

        Args:
            symbol: Símbolo específico (opcional)
            start_date: Data inicial (opcional)
            end_date: Data final (opcional)

        Returns:
            SignalMetrics com estatísticas agregadas
        """
        try:
            cursor = self.connection.cursor()

            # Construir query
            where_clauses = ["status = 'CLOSED'"]
            params = []

            if symbol:
                where_clauses.append("symbol = ?")
                params.append(symbol)

            if start_date:
                where_clauses.append("created_at >= ?")
                params.append(start_date.isoformat())

            if end_date:
                where_clauses.append("created_at <= ?")
                params.append(end_date.isoformat())

            where_clause = " AND ".join(where_clauses)

            # Query sinais fechados
            cursor.execute(
                f"""
                SELECT outcome_type, outcome_pnl, outcome_days_open
                FROM signals
                WHERE {where_clause}
                """,
                params,
            )

            rows = cursor.fetchall()

            if not rows:
                logger.warning(f"[AC3-METRICS] No closed signals found")
                return self._create_empty_metrics()

            # Calcular métricas
            metrics = self._calculate_metrics_from_rows(rows)

            logger.info(
                f"[AC3-METRICS] Calculated metrics: "
                f"WinRate={metrics.win_rate:.1f}%, "
                f"AvgPnL={metrics.total_pnl/len(rows):.2f} pts"
            )

            return metrics

        except sqlite3.Error as e:
            logger.error(f"[AC3-METRICS-ERROR] Failed to calculate metrics: {e}")
            return self._create_empty_metrics()

    # ========================================================================
    # MÉTODOS PRIVADOS
    # ========================================================================

    def _classify_outcome(
        self,
        points_pnl: float,
        pnl_percent: float,
        days_open: float,
        signal_type: str,
    ) -> SignalOutcomeType:
        """Classifica um sinal como winner/loser/whipsaw."""
        if points_pnl > 0:
            # Verificar se é whipsaw (abriu mas reverteu rápido)
            if days_open < 0.01:  # Menos de 15 minutos
                return SignalOutcomeType.WHIPSAW_SIGNAL
            return SignalOutcomeType.WINNING_SIGNAL
        elif points_pnl < 0:
            if days_open < 0.01:
                return SignalOutcomeType.WHIPSAW_SIGNAL
            return SignalOutcomeType.LOSING_SIGNAL
        else:
            return SignalOutcomeType.BREAKEVEN_SIGNAL

    def _calculate_metrics_from_rows(
        self, rows: List[sqlite3.Row]
    ) -> SignalMetrics:
        """Calcula métricas a partir de linhas de resultado."""
        total_signals = len(rows)
        winning_signals = 0
        losing_signals = 0
        missed_signals = 0
        whipsaw_signals = 0
        total_pnl = 0
        total_pnl_winners = 0
        total_pnl_losers = 0
        total_holding_days = 0

        for row in rows:
            outcome_type = row["outcome_type"]
            pnl = row["outcome_pnl"] or 0
            days_open = row["outcome_days_open"] or 0

            if outcome_type == "WINNING_SIGNAL":
                winning_signals += 1
                total_pnl += pnl
                total_pnl_winners += pnl
            elif outcome_type == "LOSING_SIGNAL":
                losing_signals += 1
                total_pnl += pnl
                total_pnl_losers += pnl
            elif outcome_type == "MISSED_SIGNAL":
                missed_signals += 1
            elif outcome_type == "WHIPSAW_SIGNAL":
                whipsaw_signals += 1

            total_holding_days += days_open

        win_rate = (
            (winning_signals / (winning_signals + losing_signals) * 100)
            if (winning_signals + losing_signals) > 0
            else 0
        )

        avg_pnl_winner = (
            total_pnl_winners / winning_signals if winning_signals > 0 else 0
        )
        avg_pnl_loser = (
            abs(total_pnl_losers) / losing_signals if losing_signals > 0 else 0
        )

        profit_factor = (
            (total_pnl_winners / abs(total_pnl_losers))
            if total_pnl_losers != 0
            else 1.0
        )
        recovery_factor = 1.0  # Simplificado

        return SignalMetrics(
            total_signals=total_signals,
            winning_signals=winning_signals,
            losing_signals=losing_signals,
            missed_signals=missed_signals,
            whipsaw_signals=whipsaw_signals,
            win_rate=win_rate,
            avg_pnl_winner=avg_pnl_winner,
            avg_pnl_loser=avg_pnl_loser,
            total_pnl=total_pnl,
            avg_holding_time=total_holding_days / total_signals
            if total_signals > 0
            else 0,
            profit_factor=profit_factor,
            recovery_factor=recovery_factor,
        )

    def _create_empty_metrics(self) -> SignalMetrics:
        """Cria objeto de métricas vazio."""
        return SignalMetrics(
            total_signals=0,
            winning_signals=0,
            losing_signals=0,
            missed_signals=0,
            whipsaw_signals=0,
            win_rate=0,
            avg_pnl_winner=0,
            avg_pnl_loser=0,
            total_pnl=0,
            avg_holding_time=0,
            profit_factor=0,
            recovery_factor=0,
        )

    def close(self) -> None:
        """Fecha conexão com DB."""
        if self.connection:
            self.connection.close()
            logger.info("[AC3-DB] Connection closed")
