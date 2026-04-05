"""
Testes para WebSocket Server

Testes unitários e integração para websocket_server.py
TODO-8: WebSocketTestClient implementado via TestClient.websocket_connect()
Cobertura alvo: > 85%
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, MagicMock, patch
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

    def test_websocket_conecta_e_desconecta(self):
        """Valida que WebSocket aceita conexão — ConnectionManager rastreia a conexão."""
        from interfaces.websocket_server import manager

        contagem_antes = manager.get_active_count()
        client = TestClient(app)
        with client.websocket_connect("/alertas") as ws:
            assert ws is not None
            # Servidor deve ter ao menos a conexão atual registrada
            assert manager.get_active_count() >= contagem_antes + 1

    def test_websocket_aceita_mensagem_ping(self):
        """Valida que o servidor aceita mensagem do cliente sem encerrar a conexão."""
        from interfaces.websocket_server import manager

        client = TestClient(app)
        with client.websocket_connect("/alertas") as ws:
            contagem_durante = manager.get_active_count()
            ws.send_text("ping")
            # Conexão deve permanecer ativa após a mensagem
            assert manager.get_active_count() == contagem_durante

    def test_websocket_aceita_json_do_cliente(self):
        """Valida que o servidor aceita mensagem JSON enviada pelo cliente."""
        client = TestClient(app)
        with client.websocket_connect("/alertas") as ws:
            ws.send_json({"tipo": "keep-alive", "timestamp": "2026-04-05T00:00:00Z"})

    @pytest.mark.asyncio
    async def test_websocket_broadcast_envia_para_cliente_conectado(self):
        """Valida que broadcast_alert entrega alerta ao cliente WebSocket conectado."""
        from interfaces.websocket_server import broadcast_alert, manager

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        await manager.connect(mock_ws)

        alerta = {
            "id": "ws-broadcast-test",
            "ativo": "WIN$N",
            "padrao": "VOLATILIDADE_EXTREMA",
            "nivel": "CRITICO",
            "timestamp": "2026-04-05T10:00:00Z",
        }
        await broadcast_alert(alerta)

        mock_ws.send_json.assert_called_once_with(alerta)
        manager.disconnect(mock_ws)

    def test_websocket_multiplos_clientes_conectam_simultaneamente(self):
        """Valida que múltiplos clientes conseguem se conectar."""
        client1 = TestClient(app)
        client2 = TestClient(app)

        with client1.websocket_connect("/alertas") as ws1:
            with client2.websocket_connect("/alertas") as ws2:
                assert ws1 is not None
                assert ws2 is not None


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


class TestDashboard:
    """Testes para endpoint HTML do dashboard."""

    def test_dashboard_retorna_html(self):
        """Valida que o dashboard retorna HTML com status 200."""
        client = TestClient(app)
        response = client.get("/dashboard")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "<html" in response.text.lower()

    def test_dashboard_contem_websocket_url(self):
        """Valida que o HTML do dashboard referencia o endpoint WebSocket."""
        client = TestClient(app)
        response = client.get("/dashboard")

        assert "alertas" in response.text


class TestAnalyticsEndpoints:
    """Testes para endpoints REST de analytics (S2-6) com mocks."""

    def test_intervention_log_sem_collector_retorna_503(self):
        """Valida que /api/intervention/log retorna 503 quando collector não inicializado."""
        import interfaces.websocket_server as ws_module
        ws_module.analytics_collector = None

        client = TestClient(app)
        response = client.post(
            "/api/intervention/log",
            json={
                "symbol": "WINFUT",
                "action": "OVERRIDE",
                "reason": "Teste",
                "ml_signal": 0.75,
                "trader_decision": "Aumentar 25%",
            },
        )
        assert response.status_code == 503

    def test_intervention_result_sem_collector_retorna_503(self):
        """Valida que /api/intervention/{id}/result retorna 503 sem collector."""
        import interfaces.websocket_server as ws_module
        ws_module.analytics_collector = None

        client = TestClient(app)
        response = client.post(
            "/api/intervention/1/result",
            json={"result": "success", "pnl": 250.0},
        )
        assert response.status_code == 503

    def test_analytics_stats_sem_collector_retorna_503(self):
        """Valida que /api/analytics/stats retorna 503 sem collector."""
        import interfaces.websocket_server as ws_module
        ws_module.analytics_collector = None

        client = TestClient(app)
        response = client.get("/api/analytics/stats")
        assert response.status_code == 503

    def test_analytics_dashboard_sem_collector_retorna_503(self):
        """Valida que /api/analytics/dashboard retorna 503 sem collector."""
        import interfaces.websocket_server as ws_module
        ws_module.analytics_collector = None

        client = TestClient(app)
        response = client.get("/api/analytics/dashboard")
        assert response.status_code == 503

    def test_intervention_log_com_collector_mock(self):
        """Valida que /api/intervention/log funciona com collector mockado."""
        import interfaces.websocket_server as ws_module

        mock_collector = MagicMock()
        mock_collector.log_intervention.return_value = 42
        ws_module.analytics_collector = mock_collector

        client = TestClient(app)
        response = client.post(
            "/api/intervention/log",
            json={
                "symbol": "WINFUT",
                "action": "OVERRIDE",
                "reason": "Confluência SMC",
                "ml_signal": 0.80,
                "trader_decision": "Aumentar ticket",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intervention_id"] == 42
        assert data["status"] == "logged"

        # Restaurar estado
        ws_module.analytics_collector = None

    def test_intervention_result_com_collector_mock(self):
        """Valida que /api/intervention/{id}/result atualiza corretamente."""
        import interfaces.websocket_server as ws_module

        mock_collector = MagicMock()
        mock_collector.update_intervention_result.return_value = True
        ws_module.analytics_collector = mock_collector

        client = TestClient(app)
        response = client.post(
            "/api/intervention/42/result",
            json={"result": "WIN", "p_and_l": 475.50},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "updated"

        ws_module.analytics_collector = None

    def test_intervention_result_nao_encontrado(self):
        """Valida que retorna 404 quando intervenção não encontrada."""
        import interfaces.websocket_server as ws_module

        mock_collector = MagicMock()
        mock_collector.update_intervention_result.return_value = False
        ws_module.analytics_collector = mock_collector

        client = TestClient(app)
        response = client.post(
            "/api/intervention/999/result",
            json={"result": "WIN", "p_and_l": 0.0},
        )
        assert response.status_code == 404

        ws_module.analytics_collector = None

    def test_analytics_dashboard_com_collector_mock(self):
        """Valida que /api/analytics/dashboard retorna estrutura completa."""
        import interfaces.websocket_server as ws_module

        mock_collector = MagicMock()
        mock_collector.get_intervention_stats.return_value = {
            "total_interventions": 10,
            "wins": 6,
            "win_rate": 60.0,
            "total_pnl": 1505.0,
        }
        mock_collector.get_interventions_by_action.return_value = []
        ws_module.analytics_collector = mock_collector

        client = TestClient(app)
        response = client.get("/api/analytics/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert "global" in data
        assert "by_action" in data
        assert data["global"]["total_interventions"] == 10

        ws_module.analytics_collector = None

    def test_analytics_stats_com_collector_mock(self):
        """Valida que /api/analytics/stats retorna dados do collector mockado."""
        import interfaces.websocket_server as ws_module

        mock_collector = MagicMock()
        mock_collector.get_intervention_stats.return_value = {
            "total": 5,
            "win_rate": 0.6,
        }
        ws_module.analytics_collector = mock_collector

        client = TestClient(app)
        response = client.get("/api/analytics/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert data["total"] == 5

        ws_module.analytics_collector = None

    def test_analytics_stats_com_symbol_parametro(self):
        """Valida que /api/analytics/stats aceita filtro por símbolo."""
        import interfaces.websocket_server as ws_module

        mock_collector = MagicMock()
        mock_collector.get_intervention_stats.return_value = {"total": 2, "symbol": "WIN$N"}
        ws_module.analytics_collector = mock_collector

        client = TestClient(app)
        response = client.get("/api/analytics/stats?symbol=WIN%24N")

        assert response.status_code == 200
        mock_collector.get_intervention_stats.assert_called_once_with(symbol="WIN$N")

        ws_module.analytics_collector = None

    def test_intervention_log_retorna_400_quando_id_none(self):
        """Valida que /api/intervention/log retorna 400 quando log_intervention retorna None."""
        import interfaces.websocket_server as ws_module

        mock_collector = MagicMock()
        mock_collector.log_intervention.return_value = None
        ws_module.analytics_collector = mock_collector

        client = TestClient(app)
        response = client.post(
            "/api/intervention/log",
            json={"symbol": "WINFUT", "action": "OVERRIDE"},
        )
        assert response.status_code == 400

        ws_module.analytics_collector = None

    def test_intervention_log_value_error_retorna_400(self):
        """Valida que /api/intervention/log retorna 400 ao receber ValueError."""
        import interfaces.websocket_server as ws_module

        mock_collector = MagicMock()
        mock_collector.log_intervention.side_effect = ValueError("ação inválida")
        ws_module.analytics_collector = mock_collector

        client = TestClient(app)
        response = client.post(
            "/api/intervention/log",
            json={"symbol": "WINFUT", "action": "INVALIDA"},
        )
        assert response.status_code == 400
        assert "ação inválida" in response.json()["detail"]

        ws_module.analytics_collector = None

    def test_intervention_result_value_error_retorna_400(self):
        """Valida que /api/intervention/{id}/result retorna 400 ao receber ValueError."""
        import interfaces.websocket_server as ws_module

        mock_collector = MagicMock()
        mock_collector.update_intervention_result.side_effect = ValueError("resultado inválido")
        ws_module.analytics_collector = mock_collector

        client = TestClient(app)
        response = client.post(
            "/api/intervention/1/result",
            json={"result": "INVALIDO", "p_and_l": 0.0},
        )
        assert response.status_code == 400

        ws_module.analytics_collector = None

    def test_analytics_stats_exception_retorna_500(self):
        """Valida que /api/analytics/stats retorna 500 em caso de erro inesperado."""
        import interfaces.websocket_server as ws_module

        mock_collector = MagicMock()
        mock_collector.get_intervention_stats.side_effect = RuntimeError("Erro no BD")
        ws_module.analytics_collector = mock_collector

        client = TestClient(app)
        response = client.get("/api/analytics/stats")
        assert response.status_code == 500

        ws_module.analytics_collector = None

    def test_analytics_dashboard_exception_retorna_500(self):
        """Valida que /api/analytics/dashboard retorna 500 em caso de erro inesperado."""
        import interfaces.websocket_server as ws_module

        mock_collector = MagicMock()
        mock_collector.get_intervention_stats.side_effect = RuntimeError("Erro no BD")
        ws_module.analytics_collector = mock_collector

        client = TestClient(app)
        response = client.get("/api/analytics/dashboard")
        assert response.status_code == 500

        ws_module.analytics_collector = None

    def test_shutdown_com_collector_lanca_excecao(self):
        """Valida que shutdown trata exceção ao fechar collector."""
        import interfaces.websocket_server as ws_module

        mock_collector = MagicMock()
        mock_collector.close.side_effect = RuntimeError("Erro ao fechar DB")
        ws_module.analytics_collector = mock_collector

        # Deve executar sem propagar a exceção
        import asyncio
        from interfaces.websocket_server import shutdown

        asyncio.run(shutdown())
        # Se chegou aqui, o erro foi tratado corretamente


class TestStartupShutdown:
    """Testes de ciclo de vida do servidor."""

    @pytest.mark.asyncio
    async def test_startup_inicializa_analytics_collector(self):
        """Valida que startup tenta inicializar AnalyticsCollector."""
        from interfaces.websocket_server import startup
        import interfaces.websocket_server as ws_module

        ws_module.analytics_collector = None

        mock_collector = MagicMock()
        mock_collector.connect.return_value = True

        with patch("interfaces.websocket_server.AnalyticsCollector", return_value=mock_collector):
            await startup()

        assert ws_module.analytics_collector is not None
        ws_module.analytics_collector = None

    @pytest.mark.asyncio
    async def test_shutdown_desconecta_clientes(self):
        """Valida que shutdown remove todos os clientes conectados."""
        from interfaces.websocket_server import shutdown, manager

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        await manager.connect(mock_ws)
        assert manager.get_active_count() >= 1

        import interfaces.websocket_server as ws_module
        ws_module.analytics_collector = None

        await shutdown()
        assert manager.get_active_count() == 0


if __name__ == "__main__":
    # Rodar testes
    pytest.main([__file__, "-v", "--tb=short"])
