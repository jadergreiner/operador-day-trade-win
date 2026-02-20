"""
Testes de Integração - WebSocket Server (INTEGRATION-ENG-002)

Valida:
1. Ativação do servidor FastAPI
2. ConnectionManager funcionalidade
3. Broadcast de alertas
4. Health check endpoint
5. Integração com fila de alertas
"""

import asyncio
import json
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Imports do APP
from src.interfaces.websocket_server import (
    app,
    ConnectionManager,
    broadcast_alert,
)
from src.domain.entities.alerta import AlertaOportunidade
from src.domain.enums.alerta_enums import NivelAlerta, PatraoAlerta

logger = logging.getLogger(__name__)


class TestConnectionManager:
    """Testa a classe ConnectionManager."""

    @pytest.fixture
    def manager(self):
        """Fixture para ConnectionManager."""
        return ConnectionManager()

    @pytest.mark.asyncio
    async def test_connect_cliente(self, manager):
        """Testa conexão de um cliente."""
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()

        await manager.connect(mock_websocket)

        assert mock_websocket in manager.active_connections
        assert manager.get_active_count() == 1
        mock_websocket.accept.assert_called_once()

    def test_disconnect_cliente(self, manager):
        """Testa desconexão de um cliente."""
        mock_websocket = MagicMock()

        manager.active_connections.add(mock_websocket)
        assert manager.get_active_count() == 1

        manager.disconnect(mock_websocket)

        assert mock_websocket not in manager.active_connections
        assert manager.get_active_count() == 0

    @pytest.mark.asyncio
    async def test_broadcast_para_multiplos_clientes(self, manager):
        """Testa broadcast para múltiplos clientes simultaneamente."""
        # Criar 3 mock clients
        clients = [AsyncMock() for _ in range(3)]
        for client in clients:
            client.send_json = AsyncMock()
            manager.active_connections.add(client)

        # Alerta de teste
        alerta_dict = {
            "id": "test-uuid-123",
            "ativo": "WIN$N",
            "padrão": "VOLATILIDADE_EXTREMA",
            "nível": "CRÍTICO",
            "timestamp": "2026-02-23T14:30:00Z",
        }

        # Broadcast
        await manager.broadcast(alerta_dict)

        # Verificar que todos receberam
        for client in clients:
            client.send_json.assert_called_once_with(alerta_dict)

    @pytest.mark.asyncio
    async def test_broadcast_remove_conexoes_falhas(self, manager):
        """Testa que broadcast remove conexões com erro."""
        # 2 clientes bons, 1 com erro
        good_client = AsyncMock()
        good_client.send_json = AsyncMock()

        bad_client = AsyncMock()
        bad_client.send_json = AsyncMock(side_effect=Exception("Connection lost"))

        manager.active_connections.add(good_client)
        manager.active_connections.add(bad_client)

        assert manager.get_active_count() == 2

        alerta = {"id": "test-123", "ativo": "WIN$N"}
        await manager.broadcast(alerta)

        # Good client deve receber
        good_client.send_json.assert_called_once()

        # Bad client deve ser removido
        assert bad_client not in manager.active_connections
        assert manager.get_active_count() == 1


class TestWebSocketServerEndpoints:
    """Testa endpoints da API FastAPI."""

    @pytest.fixture
    def client(self):
        """Fixture para cliente HTTP de teste."""
        from fastapi.testclient import TestClient

        return TestClient(app)

    def test_health_check_endpoint(self, client):
        """Testa GET /health."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "active_connections" in data
        assert "timestamp" in data

    def test_metrics_endpoint(self, client):
        """Testa GET /metrics."""
        response = client.get("/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert data["status"] == "running"

    def test_config_endpoint(self, client):
        """Testa GET /config."""
        response = client.get("/config")

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.1.0"
        assert data["websocket_port"] == 8765
        assert "features" in data
        assert data["features"]["websocket_delivery"] is True

    def test_alertas_historico_endpoint(self, client):
        """Testa GET /alertas/historico (v1.2 stub)."""
        response = client.get("/alertas/historico?limit=50")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_implemented"
        assert data["version"] == "1.1.0"


class TestWebSocketConnection:
    """Testa conexão WebSocket com testclient."""

    @pytest.fixture
    def ws_client(self):
        """Fixture para cliente WebSocket."""
        from fastapi.testclient import TestClient

        return TestClient(app)

    def test_websocket_connect_disconnect(self, ws_client):
        """Testa conexão e desconexão WebSocket."""
        with ws_client.websocket_connect("/alertas") as websocket:
            # Verificar que conectou
            assert websocket is not None

            # Enviar mensagem de keep-alive (em produção, cliente envia periodicamente)
            websocket.send_text("ping")

            # Servidor NÃO envia resposta (só aguarda by timeout)
            # Então apenas verificamos que a conexão está aberta

        # Ao sair do contexto, desconecta automaticamente


class TestBroadcastAlertFunction:
    """Testa a função broadcast_alert de integração com fila."""

    @pytest.mark.asyncio
    async def test_broadcast_alert_integration(self):
        """Testa broadcast_alert chamado pela fila de alertas."""
        alerta_json = {
            "id": "alerta-001",
            "ativo": "WIN$N",
            "padrão": "VOLATILIDADE_EXTREMA",
            "nível": "CRÍTICO",
            "preco_atual": 127450.00,
            "entrada_minima": 127400.00,
            "entrada_maxima": 127500.00,
            "stop_loss": 127000.00,
            "take_profit": 128350.00,
            "confianca": 0.85,
            "timestamp": "2026-02-23T14:30:00Z",
        }

        # Mock do manager.broadcast
        with patch("src.interfaces.websocket_server.manager") as mock_manager:
            mock_manager.broadcast = AsyncMock()

            # Chamar função
            await broadcast_alert(alerta_json)

            # Verificar que foi chamada
            mock_manager.broadcast.assert_called_once_with(alerta_json)


@pytest.mark.asyncio
async def test_server_startup_shutdown():
    """Testa eventos de startup e shutdown."""
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # Fazer requisição (ativa startup automaticamente)
    response = client.get("/health")
    assert response.status_code == 200

    # Shutdown é chamado automaticamente ao sair do contexto


# ============================================================================
# TESTES DE PERFORMANCE
# ============================================================================


@pytest.mark.asyncio
async def test_broadcast_latencia_multiplos_clientes():
    """Testa latência de broadcast com múltiplos clientes."""
    import time

    manager = ConnectionManager()

    # Simular 50 clientes
    clients = [AsyncMock() for _ in range(50)]
    for client in clients:
        client.send_json = AsyncMock()
        manager.active_connections.add(client)

    alerta = {
        "id": "perf-test",
        "ativo": "WIN$N",
        "timestamp": time.time(),
    }

    # Medir tempo
    start = time.time()
    await manager.broadcast(alerta)
    elapsed = time.time() - start

    # Assertar latência < 100ms (mesmo com 50 clientes)
    assert elapsed < 0.1, f"Latência {elapsed*1000:.2f}ms > 100ms"

    # Todos devem ter recebido
    for client in clients:
        client.send_json.assert_called_once()


# ============================================================================
# INTEGRAÇÃO COM FILA (Mock)
# ============================================================================


@pytest.mark.asyncio
async def test_integracao_fila_para_websocket():
    """
    Testa integração: Fila → WebSocket Broadcast

    Simula o fluxo completo:
    1. Alerta é enfileirado (FilaAlertas.enfileirar)
    2. Consumer da fila chama broadcast_alert
    3. WebSocket entrega para clientes
    """
    manager = ConnectionManager()

    # Mock cliente WebSocket
    mock_client = AsyncMock()
    mock_client.send_json = AsyncMock()
    manager.active_connections.add(mock_client)

    # Simular alerta vindo da fila
    alerta_json = {
        "id": "fila-123",
        "ativo": "WIN$N",
        "padrão": "VOLATILIDADE_EXTREMA",
        "nível": "CRÍTICO",
        "timestamp": "2026-02-23T14:30:00Z",
    }

    # Broadcast (como seria feito pelo consumer da fila)
    await manager.broadcast(alerta_json)

    # Verificar entrega
    mock_client.send_json.assert_called_once_with(alerta_json)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
