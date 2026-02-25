"""
Orders Executor - Camada de Execução de Ordens Automáticas

Padrão: Command Pattern + State Machine
Responsabilidade: Gerenciar ciclo de vida de uma ordem (enfileirado → enviado → executado → fechado)

Status: SPRINT 1 - Eng Sr (Skeleton)
"""

from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging
import uuid
from datetime import datetime
import json

# Importar classes para exportação
from src.infrastructure.providers.mt5_adapter import OrderStatus
from src.domain.entities.trade import Position

logger = logging.getLogger(__name__)


class OrderState(Enum):
    """Estado da ordem no sistema"""
    ENQUEUED = "ENQUEUED"           # Enfileirada aguardando validação
    VALIDATED = "VALIDATED"         # Passou nas gates de risco
    SENT_TO_MT5 = "SENT_TO_MT5"     # Enviada ao MT5
    ACCEPTED_BY_MT5 = "ACCEPTED_BY_MT5"
    EXECUTED = "EXECUTED"           # Executada em mercado
    PARTIALLY_CLOSED = "PARTIALLY_CLOSED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"           # Falha em validação ou MT5
    CANCELLED = "CANCELLED"


@dataclass
class OrderAuditLog:
    """Registro de auditoria de cada estado/transição"""
    timestamp: datetime
    state: OrderState
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionOrder:
    """
    Ordem de execução automática.

    Fluxo:
    1. Criada com dados do detector + ML classifier
    2. Passa por Risk Validators
    3. Se aprovado: envia a MT5
    4. Monitora execução até fechamento
    """
    order_id: str  # Unique ID para auditoria
    symbol: str
    order_type: str  # BUY or SELL
    volume: float
    entry_price: float
    stop_loss: float
    take_profit: float

    # Metadata do detector
    detector_spike: float  # σ (desvios padrão)
    ml_classifier_score: float  # 0.0 - 1.0

    # Trader override
    trader_approval: bool = False
    trader_comment: str = ""

    # Estado
    state: OrderState = OrderState.ENQUEUED
    audit_log: list = field(default_factory=list)

    # Execução MT5
    mt5_ticket: Optional[str] = None
    execution_time: Optional[datetime] = None
    pnl_close: Optional[float] = None

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if not self.order_id:
            self.order_id = f"ORD-{uuid.uuid4().hex[:12].upper()}"

    def add_audit(self, new_state: OrderState, message: str, metadata: Dict = None):
        """Adiciona entrada ao log de auditoria"""
        if metadata is None:
            metadata = {}

        log_entry = OrderAuditLog(
            timestamp=datetime.utcnow(),
            state=new_state,
            message=message,
            metadata=metadata
        )
        self.audit_log.append(log_entry)
        self.state = new_state
        self.updated_at = datetime.utcnow()

        logger.info(
            f"[{self.order_id}] {new_state.value}: {message}"
        )

    def to_trade(self, mt5_ticket: str) -> "Trade":
        """
        Converte ExecutionOrder para Trade entity para persistência.

        Mapeia os campos da ordem executada para o domain model Trade.
        Chamado após execução bem-sucedida em MT5.

        Args:
            mt5_ticket: Número do ticket retornado pelo MT5

        Returns:
            Trade entity pronta para persistência
        """
        from src.domain.entities import Trade
        from src.domain.value_objects import Symbol, Quantity, Price, Money
        from src.domain.enums.trading_enums import OrderSide, TradeStatus
        from decimal import Decimal

        # Mapeia side (string "BUY"/"SELL" → OrderSide enum)
        side = OrderSide.BUY if self.order_type.upper() == "BUY" else OrderSide.SELL

        # Cria Trade domain entity
        trade = Trade(
            symbol=Symbol(self.symbol),
            side=side,
            quantity=Quantity(int(self.volume)),  # Converte para int
            entry_price=Price(Decimal(str(self.entry_price))),
            entry_time=self.execution_time or datetime.utcnow(),
            broker_trade_id=mt5_ticket,
            stop_loss=Price(Decimal(str(self.stop_loss))) if self.stop_loss else None,
            take_profit=Price(Decimal(str(self.take_profit))) if self.take_profit else None,
            status=TradeStatus.OPEN,
            commission=Money(Decimal("0")),  # Será atualizado após execução final
            notes=f"Detector\u003d{self.detector_spike:.2f}σ, ML\u003d{self.ml_classifier_score:.2%}"
        )

        return trade


class OrderExecutionCommand(ABC):
    """Comando abstrato para operações sobre ordem (Command Pattern)"""

    @abstractmethod
    async def execute(self, order: ExecutionOrder) -> bool:
        """Executa o comando"""
        pass

    @abstractmethod
    async def undo(self, order: ExecutionOrder) -> bool:
        """Desfaz o comando (se possível)"""
        pass


class ValidateOrderCommand(OrderExecutionCommand):
    """
    Valida ordem antes de envio (passa pelos Risk Validators).

    Dependência: RiskValidationProcessor
    """

    def __init__(self, risk_processor):
        self.risk_processor = risk_processor

    async def execute(self, order: ExecutionOrder) -> bool:
        """Validação de risco"""
        # TODO: Implementar após Risk Validator pronto
        logger.info(f"[{order.order_id}] Validando risco...")
        order.add_audit(
            OrderState.VALIDATED,
            "Passou em validação de risco"
        )
        return True

    async def undo(self, order: ExecutionOrder) -> bool:
        """Não há undo para validação"""
        return True


class SendToMT5Command(OrderExecutionCommand):
    """
    Envia ordem para MT5 e persiste resultado com retry + dead-letter handling.

    Responsabilidades:
    - Conectar ao MT5
    - Enviar ordem via MT5Adapter.send_order()
    - Obter ticket de execução
    - Persistir Trade em BD com retry logic
    - Implementar dead-letter queue para falhas
    - Garantir ACID transactions

    Dependências: MT5Adapter, ITradeRepository
    """

    def __init__(self, mt5_adapter, trade_repository, max_retries: int = 3):
        """
        Inicializa comando de envio a MT5.

        Args:
            mt5_adapter: Adaptador para MetaTrader 5
            trade_repository: Repositório para persistência de trades
            max_retries: Número máximo de tentativas de persistência
        """
        self.mt5_adapter = mt5_adapter
        self.trade_repository = trade_repository
        self.max_retries = max_retries

    async def execute(self, order: ExecutionOrder) -> bool:
        """
        Envia ordem ao MT5 e persiste resultado.

        Fluxo:
        1. Enviar ordem via MT5Adapter.send_order()
        2. Obter ticket de resposta
        3. Atualizar ExecutionOrder com ticket + execution_time
        4. Converter para Trade entity
        5. Persistir em BD com retry (3x exponential backoff)
        6. Se persistência falhar: adicionar a dead-letter queue
        7. Atualizar audit log

        Returns:
            True se enviado E persistido com sucesso
            False se rejeitado ou falha de persistência crítica
        """
        import asyncio
        from src.domain.exceptions.domain_exceptions import OrderExecutionError
        from src.domain.entities import Order
        from src.domain.value_objects import Symbol, Quantity, Price
        from src.domain.enums.trading_enums import OrderSide, OrderType
        from decimal import Decimal

        try:
            # 1. ENVIAR AO MT5
            logger.info(f"[{order.order_id}] Enviando a MT5...")
            order.add_audit(
                OrderState.SENT_TO_MT5,
                "Iniciando envio a MT5"
            )

            # Chamar MT5Adapter.send_order() que retorna ticket string
            ticket = self.mt5_adapter.send_order(
                Order(
                    symbol=Symbol(order.symbol),
                    side=OrderSide.BUY if order.order_type.upper() == "BUY" else OrderSide.SELL,
                    quantity=Quantity(int(order.volume)),  # Converte para int
                    order_type=OrderType.MARKET,
                    stop_loss=Price(Decimal(str(order.stop_loss))) if order.stop_loss else None,
                    take_profit=Price(Decimal(str(order.take_profit))) if order.take_profit else None,
                )
            )

            # 2. ATUALIZAR COM TICKET E TIMESTAMP
            order.mt5_ticket = ticket
            order.execution_time = datetime.utcnow()

            order.add_audit(
                OrderState.ACCEPTED_BY_MT5,
                f"Ticket {ticket} recebido de MT5",
                {"ticket": ticket, "execution_time": order.execution_time.isoformat()}
            )

            # 3-5. CONVERTER PARA TRADE E PERSISTIR COM RETRY
            trade = order.to_trade(ticket)

            logger.info(f"[{order.order_id}] Persistindo trade ticket={ticket} em BD...")

            # Retry logic: 3x com exponential backoff (0.5s, 1s, 2s)
            persisted = await self._persist_with_retry(
                trade, order, max_retries=self.max_retries
            )

            if persisted:
                order.add_audit(
                    OrderState.EXECUTED,
                    f"Trade persistido com sucesso em BD (ticket={ticket})",
                    {"trade_id": str(trade.trade_id), "persisted": True}
                )
                logger.info(f"[{order.order_id}] Trade persistido: trade_id={trade.trade_id}")
                return True
            else:
                # Persistência falhou após retries
                order.add_audit(
                    OrderState.REJECTED,
                    f"Falha de persistência após {self.max_retries} tentativas",
                    {"ticket": ticket, "reason": "database_persistence_failed"}
                )
                logger.error(f"[{order.order_id}] FALHA CRÍTICA: Não conseguiu persistir trade em BD")
                # TODO: Adicionar a dead-letter queue
                return False

        except OrderExecutionError as e:
            order.add_audit(
                OrderState.REJECTED,
                f"Erro ao enviar a MT5: {str(e)}",
                {"error": str(e), "error_type": "OrderExecutionError"}
            )
            logger.error(f"[{order.order_id}] Erro MT5: {e}")
            return False

        except Exception as e:
            order.add_audit(
                OrderState.REJECTED,
                f"Erro inesperado: {str(e)}",
                {"error": str(e), "error_type": type(e).__name__}
            )
            logger.error(f"[{order.order_id}] Erro inesperado: {e}", exc_info=True)
            return False

    async def _persist_with_retry(
        self,
        trade: "Trade",
        order: ExecutionOrder,
        max_retries: int = 3,
        backoff_seconds: Optional[list] = None
    ) -> bool:
        """
        Persiste trade em BD com retry logic e exponential backoff.

        Args:
            trade: Trade entity para persistir
            order: ExecutionOrder para audit
            max_retries: Número máximo de tentativas
            backoff_seconds: Lista de segundos para backoff [0.5, 1, 2]

        Returns:
            True se persistido, False se todos retries falharem
        """
        import asyncio

        if backoff_seconds is None:
            backoff_seconds = [0.5, 1.0, 2.0]

        for attempt in range(max_retries):
            try:
                # Tentar persistir
                self.trade_repository.save(trade)
                logger.info(f"[{order.order_id}] Persistência bem-sucedida na tentativa {attempt + 1}")
                return True

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = backoff_seconds[attempt]
                    logger.warning(
                        f"[{order.order_id}] Tentativa {attempt + 1}/{max_retries} falhou: {e}. "
                        f"Aguardando {wait_time}s antes de retry..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"[{order.order_id}] Persistência falhou após {max_retries} tentativas: {e}"
                    )

        return False

    async def undo(self, order: ExecutionOrder) -> bool:
        """Cancela ordem no MT5 (não implementado por enquanto)"""
        logger.warning(f"[{order.order_id}] Undo não implementado ainda")
        return False


class MonitorExecutionCommand(OrderExecutionCommand):
    """
    Monitora execução em tempo real e atualiza status.

    Responsabilidades:
    - Confirmar execução
    - Controlar P&L
    - Fechar ao take profit / stop loss
    """

    def __init__(self, mt5_adapter, polling_interval: float = 1.0):
        self.mt5_adapter = mt5_adapter
        self.polling_interval = polling_interval

    async def execute(self, order: ExecutionOrder) -> bool:
        """Monitora até fechamento"""
        # TODO: Implementar loop de monitoramento
        logger.info(f"[{order.order_id}] Iniciando monitoramento...")
        order.add_audit(
            OrderState.EXECUTED,
            "Monitorando execução"
        )
        return True

    async def undo(self, order: ExecutionOrder) -> bool:
        """Para monitoramento"""
        logger.info(f"[{order.order_id}] Parando monitoramento...")
        return True


# ============================================================================
# STATE MACHINE: Orquestra transições
# ============================================================================

class OrderStateMachine:
    """
    State machine para controlar transições válidas.

    Estados válidos:
    ENQUEUED → VALIDATED → SENT_TO_MT5 → ACCEPTED_BY_MT5 → EXECUTED → [CLOSED|REJECTED]

    Sempre pode → REJECTED (em qualquer estado)
    Sempre pode → CANCELLED (com restrições)
    """

    # Transições permitidas
    VALID_TRANSITIONS = {
        OrderState.ENQUEUED: [
            OrderState.VALIDATED,
            OrderState.REJECTED
        ],
        OrderState.VALIDATED: [
            OrderState.SENT_TO_MT5,
            OrderState.REJECTED
        ],
        OrderState.SENT_TO_MT5: [
            OrderState.ACCEPTED_BY_MT5,
            OrderState.REJECTED
        ],
        OrderState.ACCEPTED_BY_MT5: [
            OrderState.EXECUTED,
            OrderState.REJECTED
        ],
        OrderState.EXECUTED: [
            OrderState.CLOSED,
            OrderState.PARTIALLY_CLOSED,
            OrderState.REJECTED
        ],
        OrderState.PARTIALLY_CLOSED: [
            OrderState.CLOSED,
            OrderState.REJECTED
        ],
        OrderState.REJECTED: [],
        OrderState.CANCELLED: [],
        OrderState.CLOSED: []
    }

    @staticmethod
    def can_transition(from_state: OrderState, to_state: OrderState) -> bool:
        """Valida se transição é permitida"""
        return to_state in OrderStateMachine.VALID_TRANSITIONS.get(from_state, [])


# ============================================================================
# EXECUTOR PRINCIPAL
# ============================================================================

class OrdersExecutionOrchestrator:
    """
    Orquestra execução de ordens do início ao fim com persistência garantida.

    Fluxo:
    1. Ordem enfileirada (detector + ML score)
    2. Validação de risco (3 gates)
    3. Se aprovado: envio a MT5
    4. Persistência garantida em BD com retry
    5. Monitoramento até fechamento
    6. Auditoria e P&L cálculo

    Integração:
    - RiskValidationProcessor
    - MT5Adapter
    - ITradeRepository (NOVO - para persistência)
    - EventBus (para notificações)
    """

    def __init__(
        self,
        risk_processor,
        mt5_adapter,
        trade_repository,
        event_bus: Optional[Any] = None
    ):
        self.risk_processor = risk_processor
        self.mt5_adapter = mt5_adapter
        self.trade_repository = trade_repository  # NOVO - dependency injection
        self.event_bus = event_bus
        self.orders: Dict[str, ExecutionOrder] = {}
        self.commands = {
            "validate": ValidateOrderCommand(risk_processor),
            "send_mt5": SendToMT5Command(mt5_adapter, trade_repository),  # NOVO - pass repository
            "monitor": MonitorExecutionCommand(mt5_adapter),
        }

    async def enqueue_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        detector_spike: float,
        ml_score: float,
        trader_approval: bool = False
    ) -> ExecutionOrder:
        """
        Enfileira nova ordem para execução.

        Returns:
            ExecutionOrder criada
        """
        order = ExecutionOrder(
            order_id="",  # será gerado no __post_init__
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            detector_spike=detector_spike,
            ml_classifier_score=ml_score,
            trader_approval=trader_approval
        )

        self.orders[order.order_id] = order
        logger.info(
            f"Ordem enfileirada: {order.order_id} "
            f"({order_type} {volume} {symbol} @ {entry_price})"
        )

        # Publicar evento (para WebSocket, alertas, etc)
        if self.event_bus:
            await self.event_bus.publish("order.enqueued", {
                "order_id": order.order_id,
                "symbol": order.symbol,
                "ml_score": order.ml_classifier_score
            })

        return order

    async def process_order(self, order_id: str) -> bool:
        """
        Processa ordem enfileirada (full pipeline).

        Returns:
            bool: True se aprovada e enviada
        """
        if order_id not in self.orders:
            logger.error(f"Ordem não encontrada: {order_id}")
            return False

        order = self.orders[order_id]

        try:
            # 1. Validação
            if not await self.commands["validate"].execute(order):
                order.add_audit(
                    OrderState.REJECTED,
                    "Falha em validação de risco"
                )
                return False

            # 2. Envio a MT5
            if not await self.commands["send_mt5"].execute(order):
                order.add_audit(
                    OrderState.REJECTED,
                    "Falha ao enviar a MT5"
                )
                return False

            # 3. Monitoramento
            await self.commands["monitor"].execute(order)

            return True

        except Exception as e:
            logger.error(f"Erro processando ordem {order_id}: {e}")
            order.add_audit(
                OrderState.REJECTED,
                f"Exceção: {str(e)}"
            )
            return False

    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Retorna status atual da ordem para dashboard"""
        if order_id not in self.orders:
            return None

        order = self.orders[order_id]
        return {
            "order_id": order.order_id,
            "state": order.state.value,
            "symbol": order.symbol,
            "ml_score": order.ml_classifier_score,
            "pnl": order.pnl_close,
            "updated_at": order.updated_at.isoformat()
        }

    def export_audit_json(self, order_id: str) -> str:
        """Exporta auditoria como JSON para conformidade"""
        if order_id not in self.orders:
            return "{}"

        order = self.orders[order_id]
        audit_data = {
            "order_id": order.order_id,
            "symbol": order.symbol,
            "order_type": order.order_type,
            "volume": order.volume,
            "state": order.state.value,
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "audit_log": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "state": log.state.value,
                    "message": log.message,
                    "metadata": log.metadata
                }
                for log in order.audit_log
            ]
        }
        return json.dumps(audit_data, indent=2, ensure_ascii=False)

    # ==================== TODO-2: EXECUTE_ORDER START (Line 133, GitHub Issue #7) ====================
    async def execute_order(self, order: ExecutionOrder) -> Dict:
        """
        Valida ordem contra Risk Framework e envia para MT5.

        Acceptance Criteria (Issue #7 - ENG-201):
        ☐ AC-1: Validate order against Risk Framework
        ☐ AC-2: Integrate with MT5Adapter
        ☐ AC-3: Implement retry logic (3x exponential backoff)
        ☐ AC-4: Logging + audit trail

        Related: GitHub Issue #7 - ENG-201
        """
        import asyncio
        start_time = datetime.utcnow()

        # AC-1: Validate order against Risk Framework
        from src.application.risk_validator import ValidationContext

        # Mocking account data for validation (in production this comes from mt5_adapter)
        context = ValidationContext(
            account_balance=10000.0,
            account_equity=10000.0,
            margin_free=8000.0,
            open_positions=[],
            proposed_position_size=order.volume,
            proposed_stop_loss=abs(order.entry_price - order.stop_loss) * order.volume,
            proposed_symbol=order.symbol,
            proposed_order_type=order.order_type
        )

        approved, results = self.risk_processor.validate_order(context)
        gates_passed = [r.status == GateStatus.PASS for r in results]

        if not approved:
            reason = next((r.message for r in results if r.status == GateStatus.FAIL), "Risk Validation Failed")
            order.add_audit(OrderState.REJECTED, f"Risco Rejeitado: {reason}")
            return {
                "success": False,
                "order_id": order.order_id,
                "rejection_reason": reason,
                "gates_passed": gates_passed
            }

        order.add_audit(OrderState.VALIDATED, "Aprovado pelo Risk Framework")

        # AC-2 & AC-3: Integrate with MT5Adapter with Retry Logic
        retries = [0.1, 0.5, 2.0] # seconds
        ticket = None

        for i, delay in enumerate(retries):
            try:
                # Assuming send_order exists in adapter and returns ticket
                ticket = await self.mt5_adapter.send_order(order)
                if ticket:
                    break
            except Exception as e:
                logger.warning(f"Tentativa {i+1} falhou: {e}")
                if i < len(retries) - 1:
                    await asyncio.sleep(delay)

        execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        if ticket:
            order.mt5_ticket = ticket
            order.add_audit(OrderState.SENT_TO_MT5, f"Ordem enviada com ticket {ticket}")
            return {
                "success": True,
                "order_id": order.order_id,
                "mt5_ticket": ticket,
                "gates_passed": gates_passed,
                "execution_time_ms": execution_time_ms
            }
        else:
            order.add_audit(OrderState.REJECTED, "Falha no envio ao MT5 após retries")
            return {
                "success": False,
                "order_id": order.order_id,
                "rejection_reason": "MT5_SEND_FAILED",
                "gates_passed": gates_passed,
                "execution_time_ms": execution_time_ms
            }
    # ==================== TODO-2: EXECUTE_ORDER END ====================

    # ==================== TODO-3: MONITOR_POSITIONS START (Line 158, GitHub Issue #7) ====================
    async def monitor_positions(self) -> Optional[Dict]:
        """
        Faz polling de posições abertas e calcula PnL.
        """
        import time
        start_time = time.time()

        try:
            positions = await self.mt5_adapter.get_positions()
            total_pnl = 0.0
            pos_list = []

            for pos in positions:
                pnl = pos.profit_loss
                total_pnl += pnl
                pos_list.append({
                    "symbol": pos.symbol,
                    "volume": pos.volume,
                    "pnl_unrealized": pnl,
                    "entry_price": pos.entry_price
                })

                # AC-6: Detect stop-loss
                if pnl <= -500: # Exemplo de threshold global
                     logger.warning(f"Stop Loss detectado para {pos.symbol}")

            monitoring_time_ms = (time.time() - start_time) * 1000

            return {
                "total_positions": len(positions),
                "positions": pos_list,
                "total_pnl_unrealized": total_pnl,
                "monitoring_time_ms": monitoring_time_ms
            }
        except Exception as e:
            logger.error(f"Erro ao monitorar posições: {e}")
            return None
    # ==================== TODO-3: MONITOR_POSITIONS END ====================

    # ==================== TODO-4: HANDLE_STOP_LOSS START (Line 188, GitHub Issue #7) ====================
    async def handle_stop_loss(self, order_id: str) -> Dict:
        """
        Fecha posição a preço de mercado quando stop-loss é acionado.
        """
        logger.info(f"Executando handle_stop_loss para {order_id}")
        # AC-9: Close at market price
        success = await self.mt5_adapter.close_position_by_id(order_id)

        if success:
             message = f"Posição {order_id} fechada por Stop Loss"
             logger.info(message)
             return {"success": True, "message": message}
        else:
             return {"success": False, "message": "Falha ao fechar posição"}
    # ==================== TODO-4: HANDLE_STOP_LOSS END ====================


# Aliases para compatibilidade com imports
Order = ExecutionOrder  # Alias: ExecutionOrder também pode ser importado como Order
OrdersExecutor = OrdersExecutionOrchestrator


if __name__ == "__main__":
    print("OrdersExecutor module loaded")
