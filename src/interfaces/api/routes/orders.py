"""Routes para operações de ordem (P0-1)."""

from fastapi import APIRouter, HTTPException, Depends
from src.interfaces.api.models import CreateOrderRequest, CreateOrderResponse
from src.interfaces.api.fastapi_server import get_orders_executor
from src.application.orders_executor import OrdersExecutor
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/orders", response_model=CreateOrderResponse)
async def create_order(
    request: CreateOrderRequest,
    executor: OrdersExecutor = Depends(get_orders_executor)
) -> CreateOrderResponse:
    """
    Cria nova ordem via queue.
    
    Resposta: JSON com order_id + audit_trail
    """
    try:
        # Validar entrada
        if request.order_type not in ["BUY", "SELL"]:
            raise HTTPException(status_code=400, detail="order_type deve ser BUY ou SELL")
        
        # Enfileira ordem
        order = await executor.enqueue_order(
            symbol=request.symbol,
            order_type=request.order_type,
            volume=request.volume,
            entry_price=request.entry_price,
            stop_loss=request.stop_loss,
            take_profit=request.take_profit,
            detector_spike=request.detector_spike,
            ml_score=request.ml_score,
            trader_approval=request.trader_approval
        )
        
        # Mapear audit trail
        audit_items = [
            {
                "state": log.state.name,
                "timestamp": log.timestamp,
                "message": log.message,
                "metadata": log.metadata
            }
            for log in order.audit_trail
        ]
        
        return CreateOrderResponse(
            order_id=order.order_id,
            symbol=order.symbol,
            order_type=order.order_type,
            volume=order.volume,
            status=order.state.name,
            created_at=order.created_at,
            audit_trail=audit_items
        )
        
    except Exception as e:
        logger.error(f"Erro criando ordem: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    executor: OrdersExecutor = Depends(get_orders_executor)
):
    """Obter status de uma ordem."""
    if order_id not in executor.orders:
        raise HTTPException(status_code=404, detail=f"Ordem {order_id} não encontrada")
    
    order = executor.orders[order_id]
    return {
        "order_id": order_id,
        "symbol": order.symbol,
        "state": order.state.name,
        "audit_trail": [
            {
                "state": log.state.name,
                "timestamp": log.timestamp.isoformat(),
                "message": log.message
            }
            for log in order.audit_trail
        ]
    }


@router.post("/orders/{order_id}/process")
async def process_order(
    order_id: str,
    executor: OrdersExecutor = Depends(get_orders_executor)
):
    """Processa uma ordem enfileirada (vai p/ validação → MT5 → monitoramento)."""
    try:
        result = await executor.process_order(order_id)
        return {
            "order_id": order_id,
            "processed": result,
            "status": executor.orders[order_id].state.name if order_id in executor.orders else "UNKNOWN"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
