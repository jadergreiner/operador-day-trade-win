"""
AC5: Trade Executor - Camada de Execução (Decision → Trade)

Executa trades baseadas em decisões de AC4.

Pipeline Completo:
    AC1: SignalGenerator cria sinais (M5 SMC patterns)
    ↓
    AC2: SignalPersistence persiste em DB
    ↓
    AC3: SignalTracker rastreia lifecycle
    ↓
    AC4: BDIDecisionFilter decide ENTRAR vs FICAR_FORA
    ↓
    AC5: TradeExecutor envia ordem para MT5 (THIS LAYER)

Responsabilidades:
    - Receber decisão de AC4 (EXECUTE/REJECT)
    - Preparar ordem (SL, TP, volume, tipo)
    - Validar ordem (risk checks)
    - Enviar para ProcessadorBDI/MT5
    - Registrar execução em BD
    - Retornar trade_id para fechar loop AC3→AC5

Status: Implementação v1.0 (05/03/2026)
Referência: docs/BACKLOG_UNIFICADO.md (AC5 Trade Executor)
           src/application/services/processador_bdi.py (integration point)
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
import sqlite3
import logging
from decimal import Decimal
import time

from src.application.services.processador_bdi import get_processador_bdi, ProcessadorBDI
from src.domain.entities import Order
from src.domain.enums.trading_enums import OrderSide as DomainOrderSide, OrderType as DomainOrderType
from src.domain.value_objects import Symbol, Quantity, Price

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ============================================================================
# ENUMS & TYPE DEFINITIONS
# ============================================================================


class OrderType(str, Enum):
    """Tipo de ordem."""
    MARKET = "MARKET"  # Executa ao preço de mercado
    LIMIT = "LIMIT"  # Executa ao preço especificado
    STOP_MARKET = "STOP_MARKET"  # Ordem stop


class OrderStatus(str, Enum):
    """Status de uma ordem."""
    PENDING = "PENDING"  # Preparada mas não enviada
    SENT = "SENT"  # Enviada para MT5
    FILLED = "FILLED"  # Executada
    PARTIAL = "PARTIAL"  # Parcialmente executada
    CANCELLED = "CANCELLED"  # Cancelada
    REJECTED = "REJECTED"  # Rejeitada por MT5


class TradeDirection(str, Enum):
    """Direção da trade."""
    BUY = "BUY"
    SELL = "SELL"


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class OrderSpecification:
    """Especificação de uma ordem."""
    order_id: str
    signal_id: str
    symbol: str
    direction: TradeDirection
    volume: int  # Número de contratos
    entry_price: float  # Preço de entrada (para LIMIT) ou None (para MARKET)
    stop_loss: float  # Preço SL
    take_profit: float  # Preço TP
    order_type: OrderType
    created_at: datetime
    notes: str = ""


@dataclass
class ExecutionResult:
    """Resultado da execução de uma ordem."""
    order_id: str
    trade_id: int  # ID da trade em MT5
    signal_id: str
    status: OrderStatus
    execution_price: Optional[float]
    execution_time: Optional[datetime]
    volume_filled: int
    volume_requested: int
    commission: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class TradeOutcome:
    """Resultado final de uma trade."""
    trade_id: int
    signal_id: str
    order_id: str
    pnl: float  # P&L em pontos
    pnl_percent: float  # P&L em %
    duration_days: float
    entry_price: float
    exit_price: float
    closed_at: datetime


# ============================================================================
# TRADE EXECUTOR CLASS
# ============================================================================


class TradeExecutor:
    """
    AC5: Executor de trades.

    Recebe decisões de AC4 e executa trades no MT5.

    Fluxo:
    1. Receber decisão de AC4 (EXECUTE/REJECT)
    2. Preparar especificação de ordem (SL, TP, volume)
    3. Validar contra risk limits
    4. Enviar para ProcessadorBDI/MT5
    5. Registrar execução em BD
    6. Retornar trade_id para AC3 (linkage)
    """

    def __init__(
        self,
        db_path: str = "data/db/trading.db",
        processador_bdi: Optional["ProcessadorBDI"] = None,
    ):
        """
        Inicializa executor.

        Args:
            db_path: Caminho do banco SQLite
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self.processador_bdi = processador_bdi or get_processador_bdi()
        self._connect()
        logger.info(f"[AC5-INIT] Trade Executor initialized at {db_path}")

    def _connect(self) -> None:
        """Estabelece connexão com DB."""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            logger.info(f"[AC5-DB] Connected to {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"[AC5-DB-ERROR] Connection failed: {e}")
            raise

    def _commit_with_retry(self, max_attempts: int = 5, base_delay: float = 0.15) -> None:
        """Commit com retry para reduzir lock do SQLite."""
        last_exc: Exception | None = None
        for attempt in range(max_attempts):
            try:
                if self.connection is None:
                    raise sqlite3.OperationalError("Connection unavailable")
                self.connection.commit()
                return
            except sqlite3.OperationalError as exc:
                last_exc = exc
                msg = str(exc).lower()
                if "database is locked" not in msg and "database is busy" not in msg:
                    raise
                time.sleep(base_delay * (attempt + 1))
        if last_exc:
            raise last_exc

    def prepare_order_specification(
        self,
        signal_id: str,
        symbol: str,
        direction: TradeDirection,
        entry_price: float,
        atr_value: float,
        base_volume: int = 1,
    ) -> OrderSpecification:
        """
        AC5.1: Preparar especificação de ordem.

        Calcula SL, TP, volume baseado em ATR e risco padrão.

        Args:
            signal_id: ID do sinal que gerou a ordem
            symbol: Símbolo do ativo (ex: WINFUT)
            direction: Direção BUY ou SELL
            entry_price: Preço de entrada
            atr_value: ATR para cálculo de SL/TP
            base_volume: Volume base (1 contrato)

        Returns:
            OrderSpecification pronta para enviar
        """
        try:
            order_id = str(uuid4())

            # Calcular SL e TP baseado em ATR
            # Regra: SL = ATR * 1.5, TP = ATR * 3.0
            sl_distance = atr_value * 1.5
            tp_distance = atr_value * 3.0

            if direction == TradeDirection.BUY:
                stop_loss = entry_price - sl_distance
                take_profit = entry_price + tp_distance
            else:  # SELL
                stop_loss = entry_price + sl_distance
                take_profit = entry_price - tp_distance

            order_spec = OrderSpecification(
                order_id=order_id,
                signal_id=signal_id,
                symbol=symbol,
                direction=direction,
                volume=base_volume,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                order_type=OrderType.MARKET,
                created_at=datetime.now(),
                notes=f"ATR-based SL/TP (ATR={atr_value:.2f})",
            )

            logger.info(
                f"[AC5-ORDER] Prepared order {order_id}: {direction.value} "
                f"{symbol} @ {entry_price:.2f} SL={stop_loss:.2f} TP={take_profit:.2f}"
            )
            return order_spec

        except Exception as e:
            logger.error(f"[AC5-ORDER-ERROR] Failed to prepare order: {e}")
            raise

    def validate_order(self, order_spec: OrderSpecification) -> Tuple[bool, str]:
        """
        AC5.2: Validar ordem contra risk limits.

        Checks:
        1. Volume mínimo/máximo (1-10 contratos)
        2. SL deve estar abaixo de entry (BUY) ou acima (SELL)
        3. TP deve estar acima de entry (BUY) ou abaixo (SELL)
        4. Risk-reward ratio mínimo de 1:2

        Args:
            order_spec: Especificação para validar

        Returns:
            (passed: bool, reason: str)
        """
        try:
            # Check 1: Volume válido
            if order_spec.volume < 1 or order_spec.volume > 10:
                return False, f"Invalid volume {order_spec.volume} (1-10 required)"

            # Check 2: SL posicionado corretamente
            if order_spec.direction == TradeDirection.BUY:
                if order_spec.stop_loss >= order_spec.entry_price:
                    return (
                        False,
                        f"BUY SL {order_spec.stop_loss} must be below entry "
                        f"{order_spec.entry_price}",
                    )
            else:  # SELL
                if order_spec.stop_loss <= order_spec.entry_price:
                    return (
                        False,
                        f"SELL SL {order_spec.stop_loss} must be above entry "
                        f"{order_spec.entry_price}",
                    )

            # Check 3: TP posicionado corretamente
            if order_spec.direction == TradeDirection.BUY:
                if order_spec.take_profit <= order_spec.entry_price:
                    return (
                        False,
                        f"BUY TP {order_spec.take_profit} must be above entry "
                        f"{order_spec.entry_price}",
                    )
            else:  # SELL
                if order_spec.take_profit >= order_spec.entry_price:
                    return (
                        False,
                        f"SELL TP {order_spec.take_profit} must be below entry "
                        f"{order_spec.entry_price}",
                    )

            # Check 4: Risk-reward ratio
            if order_spec.direction == TradeDirection.BUY:
                risk = order_spec.entry_price - order_spec.stop_loss
                reward = order_spec.take_profit - order_spec.entry_price
            else:  # SELL
                risk = order_spec.stop_loss - order_spec.entry_price
                reward = order_spec.entry_price - order_spec.take_profit

            if reward < risk * 2:  # Mínimo 1:2 ratio
                return (
                    False,
                    f"Risk-reward ratio {reward/risk:.2f}:1 below 2:1 minimum",
                )

            logger.info(
                f"[AC5-VALIDATE] Order {order_spec.order_id} validation PASSED"
            )
            return True, "Order validation passed"

        except Exception as e:
            logger.error(f"[AC5-VALIDATE-ERROR] Validation failed: {e}")
            return False, f"Validation error: {str(e)}"

    def send_order_to_broker(self, order_spec: OrderSpecification) -> ExecutionResult:
        """
        AC5.3: Enviar ordem para MT5 via ProcessadorBDI.

        Integra com ProcessadorBDI.enviar_ordem().

        Args:
            order_spec: Ordem para enviar

        Returns:
            ExecutionResult com status de execução
        """
        try:
            # Converter OrderSpecification para Order domain
            side = DomainOrderSide.BUY if order_spec.direction == TradeDirection.BUY else DomainOrderSide.SELL
            order = Order(
                symbol=Symbol(order_spec.symbol),
                side=side,
                quantity=Quantity(int(order_spec.volume)),
                order_type=DomainOrderType.MARKET,
                price=Price(Decimal(str(order_spec.entry_price))),
                stop_loss=Price(Decimal(str(order_spec.stop_loss))) if order_spec.stop_loss else None,
                take_profit=Price(Decimal(str(order_spec.take_profit))) if order_spec.take_profit else None,
                execution_method="automated",
            )

            success, ticket_or_error = self.processador_bdi.enviar_ordem(order)
            if not success:
                logger.warning(
                    f"[AC5-SEND] Order {order_spec.order_id} rejected: {ticket_or_error}"
                )
                return ExecutionResult(
                    order_id=order_spec.order_id,
                    trade_id=-1,
                    signal_id=order_spec.signal_id,
                    status=OrderStatus.REJECTED,
                    execution_price=None,
                    execution_time=None,
                    volume_filled=0,
                    volume_requested=order_spec.volume,
                    error_message=str(ticket_or_error),
                )

            try:
                trade_id = int(str(ticket_or_error).strip())
            except (ValueError, TypeError) as e:
                logger.error(
                    f"[AC5-SEND-ERROR] Non-numeric MT5 ticket: {ticket_or_error}"
                )
                return ExecutionResult(
                    order_id=order_spec.order_id,
                    trade_id=-1,
                    signal_id=order_spec.signal_id,
                    status=OrderStatus.REJECTED,
                    execution_price=None,
                    execution_time=None,
                    volume_filled=0,
                    volume_requested=order_spec.volume,
                    error_message=f"Non-numeric MT5 ticket: {ticket_or_error} ({e})",
                )

            execution_price = order_spec.entry_price
            execution_time = datetime.now()

            result = ExecutionResult(
                order_id=order_spec.order_id,
                trade_id=trade_id,
                signal_id=order_spec.signal_id,
                status=OrderStatus.FILLED,
                execution_price=execution_price,
                execution_time=execution_time,
                volume_filled=order_spec.volume,
                volume_requested=order_spec.volume,
                commission=0.0,
            )

            logger.info(
                f"[AC5-SEND] Order {order_spec.order_id} sent to broker. "
                f"Trade ID: {trade_id}"
            )
            return result

        except Exception as e:
            logger.error(f"[AC5-SEND-ERROR] Failed to send order: {e}")
            return ExecutionResult(
                order_id=order_spec.order_id,
                trade_id=-1,
                signal_id=order_spec.signal_id,
                status=OrderStatus.REJECTED,
                execution_price=None,
                execution_time=None,
                volume_filled=0,
                volume_requested=order_spec.volume,
                error_message=str(e),
            )

    def register_execution(
        self, execution_result: ExecutionResult
    ) -> bool:
        """
        AC5.4: Registrar execução em BD.

        Insere em tabela `trades` com referência ao sinal (AC3).

        Args:
            execution_result: Resultado da execução

        Returns:
            True se registrado com sucesso
        """
        try:
            def _to_sql_number(value):
                if isinstance(value, Decimal):
                    return float(value)
                return value

            cursor = self.connection.cursor()

            if execution_result.status == OrderStatus.FILLED:
                cursor.execute("""
                    INSERT INTO trades (
                        order_id, signal_id, trade_id,
                        entry_price, execution_time,
                        volume, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_result.order_id,
                    execution_result.signal_id,
                    execution_result.trade_id,
                    _to_sql_number(execution_result.execution_price),
                    execution_result.execution_time,
                    _to_sql_number(execution_result.volume_filled),
                    "OPEN",
                    datetime.now(),
                ))

                # Atualizar signal com trade_id (AC3 linkage)
                cursor.execute("""
                    UPDATE signals
                    SET outcome_trade_id = ?
                    WHERE signal_id = ?
                """, (execution_result.trade_id, execution_result.signal_id))

                self._commit_with_retry()
                logger.info(
                    f"[AC5-REGISTER] Registered trade {execution_result.trade_id} "
                    f"for signal {execution_result.signal_id}"
                )
                return True
            else:
                logger.warning(
                    f"[AC5-REGISTER] Order {execution_result.order_id} not filled "
                    f"({execution_result.status.value}), skipping registration"
                )
                return False

        except sqlite3.Error as e:
            logger.error(f"[AC5-REGISTER-ERROR] Failed to register: {e}")
            return False

    def execute_trade(
        self,
        signal_id: str,
        symbol: str,
        direction: TradeDirection,
        entry_price: float,
        atr_value: float,
    ) -> ExecutionResult:
        """
        AC5.5: Executar trade completo (pipeline AC5).

        Process:
        1. Preparar ordem (SL, TP, volume)
        2. Validar ordem
        3. Enviar para broker
        4. Registrar em BD

        Args:
            signal_id: ID do sinal
            symbol: Símbolo do ativo
            direction: Direção BUY/SELL
            entry_price: Preço de entrada
            atr_value: ATR para cálculo de SL/TP

        Returns:
            ExecutionResult com trade_id ou erro
        """
        try:
            # 1. Preparar ordem
            order_spec = self.prepare_order_specification(
                signal_id=signal_id,
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                atr_value=atr_value,
            )

            # 2. Validar ordem
            passed, reason = self.validate_order(order_spec)
            if not passed:
                logger.warning(f"[AC5-EXECUTE] Order validation failed: {reason}")
                return ExecutionResult(
                    order_id=order_spec.order_id,
                    trade_id=-1,
                    signal_id=signal_id,
                    status=OrderStatus.REJECTED,
                    execution_price=None,
                    execution_time=None,
                    volume_filled=0,
                    volume_requested=order_spec.volume,
                    error_message=reason,
                )

            # 3. Enviar para broker
            exec_result = self.send_order_to_broker(order_spec)

            # 4. Registrar em BD
            if exec_result.status == OrderStatus.FILLED:
                self.register_execution(exec_result)

            logger.info(
                f"[AC5-EXECUTE] Trade execution complete for signal {signal_id}"
            )
            return exec_result

        except Exception as e:
            logger.error(f"[AC5-EXECUTE-ERROR] Execution failed: {e}")
            return ExecutionResult(
                order_id="ERROR",
                trade_id=-1,
                signal_id=signal_id,
                status=OrderStatus.REJECTED,
                execution_price=None,
                execution_time=None,
                volume_filled=0,
                volume_requested=0,
                error_message=str(e),
            )

    def get_execution_stats(self) -> Dict[str, Any]:
        """
        AC5.6: Estatísticas de execução.

        Returns:
            Dict com métricas agregadas
        """
        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_trades,
                    SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed_trades,
                    AVG(CAST((exit_price - entry_price) AS FLOAT)) as avg_pnl
                FROM trades
            """)

            row = cursor.fetchone()
            if row:
                return {
                    "total": row[0] or 0,
                    "open": row[1] or 0,
                    "closed": row[2] or 0,
                    "avg_pnl": round(row[3] or 0, 4),
                }
            else:
                return {
                    "total": 0,
                    "open": 0,
                    "closed": 0,
                    "avg_pnl": 0.0,
                }

        except sqlite3.Error as e:
            logger.error(f"[AC5-STATS-ERROR] Failed to get stats: {e}")
            return {}
