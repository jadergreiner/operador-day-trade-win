"""
WebSocket Server para Alertas Automáticos

FastAPI + WebSockets para real-time delivery de alertas.
"""

import asyncio
import logging
from typing import Set
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn

logger = logging.getLogger(__name__)

app = FastAPI(title="Alertas Automáticos - WebSocket Server")

# Connection manager (broadcast para múltiplos operadores)
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Cliente conectado. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"Cliente desconectado. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Envia alerta para todos os clientes conectados."""
        failed_connections = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Erro ao enviar para cliente: {e}")
                failed_connections.append(connection)

        # Remove conexões que falharam
        for conn in failed_connections:
            self.disconnect(conn)

    def get_active_count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()


# Rotas
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "active_connections": manager.get_active_count(),
        "timestamp": asyncio.get_running_loop().time()
    }


@app.get("/metrics")
async def metrics():
    """Métricas do servidor."""
    return {
        "active_connections": manager.get_active_count(),
        "status": "running"
    }


@app.websocket("/alertas")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint para receber e enviar alertas.

    Protocolo:
    - Cliente conecta a ws://localhost:8765/alertas?token=JWT_TOKEN
    - Servidor envia alertas no formato JSON
    - Formato: {
        "id": "uuid",
        "ativo": "WIN$N",
        "padrão": "VOLATILIDADE_EXTREMA",
        "nível": "CRÍTICO",
        "preco_atual": 127450.00,
        "entrada_minima": 127400.00,
        "entrada_maxima": 127500.00,
        "stop_loss": 127000.00,
        "take_profit": 128350.00,
        "confianca": 0.85,
        "timestamp": "2026-02-20T14:30:00Z"
    }
    """
    await manager.connect(websocket)

    try:
        while True:
            # Aguarda por mensagens do cliente (keep-alive)
            data = await asyncio.wait_for(websocket.receive_text(), timeout=300)  # 5 min timeout
            logger.debug(f"Mensagem do cliente: {data}")

    except asyncio.TimeoutError:
        logger.info("Cliente timeout (idle > 5 min)")
        manager.disconnect(websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Cliente desconectou")

    except Exception as e:
        logger.error(f"Erro WebSocket: {e}")
        manager.disconnect(websocket)


# API REST (para operações síncronas - v1.2)
@app.get("/alertas/historico")
async def get_alertas_historico(limit: int = 100, offset: int = 0):
    """
    GET histórico de alertas (v1.2 future).

    Query params:
    - limit: número de alertas (default 100)
    - offset: pagination offset
    - ativo: filtrar por ativo (ex: WIN$N)
    - padrão: filtrar por padrão (ex: VOLATILIDADE_EXTREMA)
    - data_inicio: ISO8601 (ex: 2026-02-20)
    - data_fim: ISO8601

    Returns:
    [{
        "id": "uuid",
        "ativo": "WIN$N",
        ...
    }]
    """
    return {
        "status": "not_implemented",
        "message": "Endpoint v1.2 - Implementação futura",
        "version": "1.1.0"
    }


@app.get("/config")
async def get_config():
    """Configuração ativa (public info apenas)."""
    return {
        "version": "1.1.0",
        "websocket_port": 8765,
        "active_connections": manager.get_active_count(),
        "features": {
            "volatility_detection": True,
            "pattern_detection": True,
            "websocket_delivery": True,
            "email_delivery": True,
            "sms_delivery": False  # v1.2
        }
    }


async def startup():
    """Startup event."""
    logger.info("🚀 WebSocket Server iniciando...")
    logger.info("📍 Ouvindo em ws://0.0.0.0:8765/alertas")


async def shutdown():
    """Shutdown event."""
    logger.info("🛑 WebSocket Server desligando...")
    for conn in list(manager.active_connections):
        manager.disconnect(conn)


app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)


async def broadcast_alert(alerta_json: dict):
    """
    Função pública para broadcast de alerta (chamada pela fila).

    Args:
        alerta_json: Alertas convertido para JSON (AlertaFormatter.formatar_json())
    """
    await manager.broadcast(alerta_json)


if __name__ == "__main__":
    # Development
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8765,
        log_level="info"
    )
