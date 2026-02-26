"""
WebSocket Autenticado com OAuth/JWT
Integração P5.2 (OAuth) + P4.4 (WebSocket Server)
"""

from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Query
from typing import Dict, Set
import json
from datetime import datetime
from src.application.token_manager_ati2 import TokenManager
from jose import JWTError, jwt


class AuthenticatedConnectionManager:
    """Gerencia conexões WebSocket autenticadas com OAuth"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_tokens: Dict[str, str] = {}  # client_id -> token
        self.token_manager = TokenManager()

    async def connect(
        self,
        client_id: str,
        websocket: WebSocket,
        token: str
    ) -> Dict:
        """
        Conectar cliente com validação de token JWT

        Args:
            client_id: ID único do cliente
            websocket: Objeto WebSocket do FastAPI
            token: JWT token para autenticação

        Returns:
            Dict com informações do usuário autenticado

        Raises:
            HTTPException: Se token inválido
        """
        # Validar token
        try:
            payload = self.token_manager.verify_token(token)

            if payload.get('type') != 'access':
                raise HTTPException(status_code=401, detail="Token type inválido")

            username = payload.get('sub')
            user_id = payload.get('user_id')
            role = payload.get('role', 'user')

        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"Token inválido: {str(e)}")

        # Conectar
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.user_tokens[client_id] = token

        user_info = {
            'username': username,
            'user_id': user_id,
            'role': role,
            'connected_at': datetime.utcnow().isoformat(),
            'client_id': client_id
        }

        print(f"✅ Cliente conectado: {client_id} (user: {username}, role: {role})")

        return user_info

    async def disconnect(self, client_id: str) -> None:
        """Desconectar cliente"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.user_tokens:
            del self.user_tokens[client_id]

        print(f"❌ Cliente desconectado: {client_id}")

    async def broadcast(self, message: Dict) -> None:
        """
        Enviar mensagem para todos os clientes conectados

        Args:
            message: Dict com dados para enviar
        """
        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"❌ Erro enviando para {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Limpar clientes desconectados
        for client_id in disconnected_clients:
            await self.disconnect(client_id)

    async def send_to_user(self, user_id: str, message: Dict) -> bool:
        """
        Enviar mensagem apenas para cliente específico

        Args:
            user_id: ID do usuário
            message: Mensagem a enviar

        Returns:
            True se enviado, False se não encontrado
        """
        for client_id, websocket in self.active_connections.items():
            token = self.user_tokens.get(client_id)
            if token:
                try:
                    payload = self.token_manager.verify_token(token)
                    if payload.get('user_id') == user_id:
                        await websocket.send_json(message)
                        return True
                except:
                    pass

        return False

    def get_active_users(self) -> Dict[str, str]:
        """
        Obter lista de usuários ativos com suas informações

        Returns:
            Dict {username: role} de usuários conectados
        """
        users = {}
        for client_id, token in self.user_tokens.items():
            try:
                payload = self.token_manager.verify_token(token)
                username = payload.get('sub', 'unknown')
                role = payload.get('role', 'user')
                users[username] = role
            except:
                pass

        return users

    def get_connection_count(self) -> int:
        """Obter quantidade de conexões ativas"""
        return len(self.active_connections)

    async def send_heartbeat(self) -> None:
        """
        Enviar heartbeat para todos os clientes
        Verifica se tokens estão válidos
        """
        expired_clients = []

        for client_id, token in list(self.user_tokens.items()):
            try:
                # Verificar se token é válido
                payload = self.token_manager.verify_token(token)

                # Enviar heartbeat
                if client_id in self.active_connections:
                    await self.active_connections[client_id].send_json({
                        'type': 'heartbeat',
                        'timestamp': datetime.utcnow().isoformat(),
                        'user': payload.get('sub'),
                        'active_users': len(self.active_connections)
                    })
            except:
                # Token expirado ou inválido
                expired_clients.append(client_id)

        # Desconectar clientes com tokens expirados
        for client_id in expired_clients:
            try:
                if client_id in self.active_connections:
                    await self.active_connections[client_id].close(code=1008, reason="Token expirado")
            except:
                pass

            await self.disconnect(client_id)


# Instância global
ws_auth_manager = AuthenticatedConnectionManager()
