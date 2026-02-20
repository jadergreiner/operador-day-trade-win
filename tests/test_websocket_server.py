"""
Testes para WebSocket Server

Testes unitários e integração para websocket_server.py
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / ".." / "src"))

from interfaces.websocket_server import app, ConnectionManager


class TestConnectionManager:
    """Testes para ConnectionManager."""

    @pytest.mark.asyncio
    async def test_manager_conecta_cliente(self):
        """Valida que cliente é adicionado à lista ativa."""
        manager = ConnectionManager()

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws)

        assert mock_ws in manager.active_connections
        assert manager.get_active_count() == 1

    @pytest.mark.asyncio
    async def test_manager_desconecta_cliente(self):
        """Valida que cliente é removido da lista ativa."""
        manager = ConnectionManager()

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws)
        assert manager.get_active_count() == 1

        manager.disconnect(mock_ws)
        assert manager.get_active_count() == 0

    @pytest.mark.asyncio
    async def test_manager_broadcast_todos_clientes(self):
        """Valida que broadcast envia para todos os clientes."""
        manager = ConnectionManager()

        # Criar 3 clientes mock
        clientes = []
        for _ in range(3):
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            mock_ws.send_json = AsyncMock()
            clientes.append(mock_ws)
            await manager.connect(mock_ws)

        # Broadcast
        mensagem = {"alerta": "test"}
        await manager.broadcast(mensagem)

        # Verificar que todos receberam
        for cliente in clientes:
            cliente.send_json.assert_called_once_with(mensagem)

    @pytest.mark.asyncio
    async def test_manager_broadcast_remove_cliente_falhado(self):
        """Valida que clientes que falham são removidos."""
        manager = ConnectionManager()

        # Cliente que falha
        mock_ws_fail = AsyncMock()
        mock_ws_fail.accept = AsyncMock()
        mock_ws_fail.send_json = AsyncMock(side_effect=Exception("Erro envio"))

        # Cliente que funciona
        mock_ws_ok = AsyncMock()
        mock_ws_ok.accept = AsyncMock()
        mock_ws_ok.send_json = AsyncMock()

        await manager.connect(mock_ws_fail)
        await manager.connect(mock_ws_ok)

        # Broadcast com falha
        mensagem = {"alerta": "test"}
        await manager.broadcast(mensagem)

        # Cliente falhado deve ser removido
        assert manager.get_active_count() == 1
        assert mock_ws_ok in manager.active_connections
        assert mock_ws_fail not in manager.active_connections


class TestWebSocketAPI:
    """Testes para API REST do WebSocket server."""

    def test_health_check_ok(self):
        """Testa endpoint /health."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "active_connections" in data
        assert "timestamp" in data

    def test_metrics_endpoint(self):
        """Testa endpoint /metrics."""
        client = TestClient(app)
        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert data["status"] == "running"

    def test_config_endpoint(self):
        """Testa endpoint /config."""
        client = TestClient(app)
        response = client.get("/config")

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.1.0"
        assert "features" in data
        assert data["features"]["websocket_delivery"] is True
        assert data["features"]["email_delivery"] is True
        assert data["features"]["sms_delivery"] is False  # v1.2

    def test_historico_not_implemented(self):
        """Testa endpoint /alertas/historico (v1.2)."""
        client = TestClient(app)
        response = client.get("/alertas/historico?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_implemented"
        assert data["version"] == "1.1.0"


class TestWebSocketProtocol:
    """Testes para protocolo WebSocket."""

    @pytest.mark.asyncio
    async def test_websocket_conecta_e_recebe_dados(self):
        """Valida que WebSocket aceita conexão e recebe dados."""
        from fastapi.testclient import WebSocketTestClient

        # Este teste é simplificado - testes reais usariam WebSocketTestClient
        # ou bibliotecas como websockets/aiohttp

        # TODO: Implementar com WebSocketTestClient quando disponível
        pass


@pytest.mark.asyncio
async def test_broadcast_alert_funcao():
    """Testa função broadcast_alert com manager mock."""
    from interfaces.websocket_server import broadcast_alert, manager

    # Adicionar cliente mock
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_json = AsyncMock()

    await manager.connect(mock_ws)

    # Broadcast
    alerta = {
        "id": "test-123",
        "ativo": "WIN$N",
        "padrão": "VOLATILIDADE_EXTREMA",
        "nível": "CRÍTICO",
        "timestamp": "2026-02-20T14:30:00Z"
    }

    await broadcast_alert(alerta)

    # Verificar envio
    mock_ws.send_json.assert_called_once_with(alerta)

    # Cleanup
    manager.disconnect(mock_ws)


if __name__ == "__main__":
    # Rodar testes
    pytest.main([__file__, "-v", "--tb=short"])
