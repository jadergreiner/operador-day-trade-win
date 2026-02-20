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
    Envia ordem ao MT5 via MT5Adapter.
    
    Dependência: MT5Adapter
    """

    def __init__(self, mt5_adapter):
        self.mt5_adapter = mt5_adapter

    async def execute(self, order: ExecutionOrder) -> bool:
        """Envia ao MT5"""
        # TODO: Implementar após MT5Adapter pronto
        logger.info(f"[{order.order_id}] Enviando a MT5...")
        order.add_audit(
            OrderState.SENT_TO_MT5,
            f"Ordem enviada a MT5"
        )
        return True

    async def undo(self, order: ExecutionOrder) -> bool:
        """Cancela ordem no MT5"""
        logger.warning(f"[{order.order_id}] Cancelando...")
        return True


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
    Orquestra execução de ordens do início ao fim.
    
    Fluxo:
    1. Ordem enfileirada (detector + ML score)
    2. Validação de risco (3 gates)
    3. Se aprovado: envio a MT5
    4. Monitoramento até fechamento
    5. Auditoria e P&L cálculo
    
    Integração:
    - RiskValidationProcessor
    - MT5Adapter
    - EventBus (para notificações)
    """

    def __init__(
        self,
        risk_processor,
        mt5_adapter,
        event_bus: Optional[Any] = None
    ):
        self.risk_processor = risk_processor
        self.mt5_adapter = mt5_adapter
        self.event_bus = event_bus
        self.orders: Dict[str, ExecutionOrder] = {}
        self.commands = {
            "validate": ValidateOrderCommand(risk_processor),
            "send_mt5": SendToMT5Command(mt5_adapter),
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


if __name__ == "__main__":
    print("OrdersExecutor module loaded")
