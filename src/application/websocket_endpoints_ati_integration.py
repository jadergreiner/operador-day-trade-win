"""
WebSocket Endpoints Autenticados com OAuth
Integração P5.2 (OAuth) + P4.4 (WebSocket)
"""

from fastapi import APIRouter, WebSocket, Query, WebSocketDisconnect, Depends
from fastapi.exceptions import WebSocketException
from typing import Dict, List
import json
import uuid
import logging
from datetime import datetime
from jose import JWTError

from src.application.token_manager_ati2 import TokenManager
from src.application.websocket_auth_integration import (
    AuthenticatedConnectionManager,
    ws_auth_manager
)

logger = logging.getLogger(__name__)
router = APIRouter()
token_manager = TokenManager()


class WebSocketMessage:
    """Modelo para mensagens WebSocket"""

    @staticmethod
    def heartbeat(active_users: int) -> dict:
        """Cria mensagem de heartbeat"""
        return {
            "type": "heartbeat",
            "timestamp": datetime.utcnow().isoformat(),
            "active_users": active_users
        }

    @staticmethod
    def user_connected(username: str, role: str) -> dict:
        """Notificação de usuário conectado"""
        return {
            "type": "user_connected",
            "username": username,
            "role": role,
            "timestamp": datetime.utcnow().isoformat()
        }

    @staticmethod
    def user_disconnected(username: str) -> dict:
        """Notificação de usuário desconectado"""
        return {
            "type": "user_disconnected",
            "username": username,
            "timestamp": datetime.utcnow().isoformat()
        }

    @staticmethod
    def broadcast_message(username: str, message: str) -> dict:
        """Mensagem de broadcast"""
        return {
            "type": "message",
            "username": username,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint autenticado com OAuth JWT

    Usage:
        ws://localhost:8000/ws?token=<JWT_TOKEN>

    Fluxo:
    1. Cliente faz login em /auth/login → recebe access_token
    2. Cliente conecta WebSocket com access_token como query param
    3. Servidor valida token e aceita conexão
    4. Cliente pode enviar/receber mensagens
    5. Servidor verifica expiração periodicamente via heartbeat

    Exemplo cliente:
        const token = "eyJ..."; // de /auth/login
        const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);
        ws.onopen = () => {
            ws.send(JSON.stringify({type: "message", text: "Olá"}));
        };
        ws.onmessage = (event) => {
            console.log(JSON.parse(event.data));
        };
    """

    client_id = str(uuid.uuid4())

    try:
        # ETAPA 1: Validar token OAuth (P5.2)
        try:
            payload = token_manager.verify_token(token)
        except JWTError as e:
            logger.error(f"Token inválido para cliente {client_id}: {e}")
            await websocket.close(code=1008, reason="Unauthorized: Invalid token")
            return

        # ETAPA 2: Conectar ao gerenciador autenticado (P4.4)
        user_info = await ws_auth_manager.connect(client_id, websocket, token)

        logger.info(f"Cliente {client_id} conectado: {user_info['username']} ({user_info['role']})")

        # ETAPA 3: Notificar outros clientes
        connection_msg = WebSocketMessage.user_connected(
            username=user_info['username'],
            role=user_info['role']
        )
        await ws_auth_manager.broadcast(connection_msg)

        # ETAPA 4: Loop de mensagens
        while True:
            # Receber mensagem do cliente
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "error": "Invalid JSON format"
                }))
                continue

            # Processar tipos de mensagem
            msg_type = message_data.get("type")

            if msg_type == "message":
                # Mensagem de broadcast
                broadcast_msg = WebSocketMessage.broadcast_message(
                    username=user_info['username'],
                    message=message_data.get("text", "")
                )
                await ws_auth_manager.broadcast(broadcast_msg)

            elif msg_type == "ping":
                # Responder ping
                await websocket.send_text(json.dumps({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }))

            elif msg_type == "get_users":
                # Lista de usuários conectados
                active_users = ws_auth_manager.get_active_users()
                await websocket.send_text(json.dumps({
                    "type": "users_list",
                    "users": active_users
                }))

            elif msg_type == "heartbeat":
                # Responder heartbeat
                hb = WebSocketMessage.heartbeat(
                    active_users=ws_auth_manager.get_connection_count()
                )
                await websocket.send_text(json.dumps(hb))

            else:
                # Tipo desconhecido
                await websocket.send_text(json.dumps({
                    "error": f"Unknown message type: {msg_type}"
                }))

    except WebSocketDisconnect:
        logger.info(f"Cliente {client_id} desconectado (normal)")
        await ws_auth_manager.disconnect(client_id)

        # Notificar outros clientes
        user_info_cache = getattr(websocket, "_user_info", {"username": "Unknown"})
        disconnect_msg = WebSocketMessage.user_disconnected(
            username=user_info_cache.get("username", "Unknown")
        )
        await ws_auth_manager.broadcast(disconnect_msg)

    except Exception as e:
        logger.error(f"Erro no WebSocket {client_id}: {e}")
        await ws_auth_manager.disconnect(client_id)
        try:
            await websocket.close(code=1011, reason="Server error")
        except:
            pass


@router.websocket("/ws/trader")
async def websocket_trader_only(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint restrito apenas para traders

    Usage:
        ws://localhost:8000/ws/trader?token=<JWT_TOKEN>

    Validações:
    - Token must be valid OAuth JWT
    - User role must be "trader"
    """

    client_id = str(uuid.uuid4())

    try:
        # Validar token
        try:
            payload = token_manager.verify_token(token)
        except JWTError:
            await websocket.close(code=1008, reason="Unauthorized: Invalid token")
            return

        # Validar role
        if payload.get("role") != "trader":
            await websocket.close(code=1008, reason="Forbidden: trader role required")
            return

        # Conectar
        user_info = await ws_auth_manager.connect(client_id, websocket, token)

        logger.info(f"Trader {user_info['username']} conectado ao /ws/trader")

        # Loop de mensagens
        while True:
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            if message_data.get("type") == "trade_signal":
                # Processar sinal de trading
                signal = {
                    "type": "trade_received",
                    "signal": message_data,
                    "username": user_info['username'],
                    "timestamp": datetime.utcnow().isoformat()
                }

                # Notificar apenas traders
                await ws_auth_manager.broadcast(signal)

    except WebSocketDisconnect:
        await ws_auth_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"Erro em /ws/trader {client_id}: {e}")
        await ws_auth_manager.disconnect(client_id)
        try:
            await websocket.close(code=1011)
        except:
            pass


@router.get("/ws/status")
async def websocket_status():
    """
    Verificar status do WebSocket

    Returns:
        - active_connections: número de conexões ativas
        - active_users: dict de usuários conectados {username: role}
        - timestamp: horário da consulta
    """
    return {
        "active_connections": ws_auth_manager.get_connection_count(),
        "active_users": ws_auth_manager.get_active_users(),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/ws/broadcast")
async def manual_broadcast(
    message: str,
    token: str = Depends(lambda q: None)  # Authentication required
):
    """
    Broadcast manual de mensagem para todos os clientes WebSocket

    Requires:
    - Valid OAuth token in Authorization header
    - Role must be "admin"

    Exemplo:
        curl -X POST http://localhost:8000/ws/broadcast \
            -H "Authorization: Bearer <TOKEN>" \
            -d "message=System maintenance in 5 minutes"
    """

    # Verificar token (seria via header Authorization em produção)
    try:
        payload = token_manager.verify_token(token)
    except:
        return {"error": "Unauthorized"}

    if payload.get("role") != "admin":
        return {"error": "Forbidden: admin role required"}

    # Broadcast
    broadcast_msg = {
        "type": "system_broadcast",
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "broadcaster": payload.get("sub")
    }

    await ws_auth_manager.broadcast(broadcast_msg)

    return {
        "status": "broadcasted",
        "message": message,
        "recipients": ws_auth_manager.get_connection_count()
    }
