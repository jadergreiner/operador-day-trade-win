"""FastAPI Server para P0-1: API REST MT5"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import logging
from src.application.orders_executor import OrdersExecutor

logger = logging.getLogger(__name__)

# Singleton instance
_orders_executor: OrdersExecutor = None


def create_app(orders_executor: OrdersExecutor) -> FastAPI:
    """Factory para criar FastAPI app com dependency injection."""
    global _orders_executor
    _orders_executor = orders_executor

    app = FastAPI(
        title="API REST MT5 - P0-1",
        description="Execução de ordens via ExecutionOrder queue",
        version="1.0.0"
    )

    # Health check
    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "api-rest-mt5",
            "version": "1.0.0"
        }

    # Listar ordens
    @app.get("/api/v1/orders")
    async def list_orders():
        return {
            "total": len(_orders_executor.orders),
            "orders": [
                {
                    "order_id": oid,
                    "symbol": order.symbol,
                    "state": order.state.name,
                    "created_at": order.created_at.isoformat()
                }
                for oid, order in _orders_executor.orders.items()
            ]
        }

    # Registra rotas
    from src.interfaces.api.routes import orders
    app.include_router(orders.router, prefix="/api/v1", tags=["orders"])

    from src.interfaces.api.routes import dashboard
    app.include_router(dashboard.roteador, prefix="/api/v1", tags=["dashboard"])

    return app


def get_orders_executor() -> OrdersExecutor:
    """Getter para injetar em testes."""
    return _orders_executor
