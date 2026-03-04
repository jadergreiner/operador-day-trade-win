"""Testes unitários para P0-1 API REST MT5"""

import pytest
from fastapi.testclient import TestClient
from src.application.orders_executor import OrdersExecutor
from src.interfaces.api.fastapi_server import create_app
from src.interfaces.api.models import CreateOrderRequest


@pytest.fixture
def executor():
    """Cria executor para testes."""
    return OrdersExecutor()


@pytest.fixture
def client(executor):
    """Cria cliente FastAPI para testes."""
    app = create_app(executor)
    return TestClient(app)


def test_health_check(client):
    """Testa endpoint /health."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_order_valid_request(client):
    """Testa POST /api/v1/orders com request válido."""
    request_data = {
        "symbol": "WINJ26",
        "order_type": "BUY",
        "volume": 1.0,
        "entry_price": 123.45,
        "stop_loss": 122.45,
        "take_profit": 125.45,
        "ml_score": 0.85,
        "detector_spike": 45.2
    }
    
    response = client.post("/api/v1/orders", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert "order_id" in data
    assert data["symbol"] == "WINJ26"
    assert data["status"] == "ENQUEUED"
    assert len(data["audit_trail"]) > 0


def test_create_order_invalid_order_type(client):
    """Testa POST /api/v1/orders com order_type inválido."""
    request_data = {
        "symbol": "WINJ26",
        "order_type": "INVALID",
        "volume": 1.0,
        "entry_price": 123.45,
        "stop_loss": 122.45,
        "take_profit": 125.45,
        "ml_score": 0.85
    }
    
    response = client.post("/api/v1/orders", json=request_data)
    assert response.status_code == 400


def test_list_orders_empty(client):
    """Testa GET /api/v1/orders (vazio)."""
    response = client.get("/api/v1/orders")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["orders"] == []


def test_list_orders_multiple(client):
    """Testa GET /api/v1/orders com múltiplas ordens."""
    # Criar 2 ordens
    request_data = {
        "symbol": "WINJ26",
        "order_type": "BUY",
        "volume": 1.0,
        "entry_price": 123.45,
        "stop_loss": 122.45,
        "take_profit": 125.45,
        "ml_score": 0.85
    }
    
    client.post("/api/v1/orders", json=request_data)
    client.post("/api/v1/orders", json=request_data)
    
    # Listar
    response = client.get("/api/v1/orders")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["orders"]) == 2


def test_get_order_found(client):
    """Testa GET /api/v1/orders/{order_id}."""
    # Criar ordem
    request_data = {
        "symbol": "WINJ26",
        "order_type": "BUY",
        "volume": 1.0,
        "entry_price": 123.45,
        "stop_loss": 122.45,
        "take_profit": 125.45,
        "ml_score": 0.85
    }
    
    create_response = client.post("/api/v1/orders", json=request_data)
    order_id = create_response.json()["order_id"]
    
    # Obter ordem
    response = client.get(f"/api/v1/orders/{order_id}")
    assert response.status_code == 200
    assert response.json()["order_id"] == order_id
    assert response.json()["state"] == "ENQUEUED"


def test_get_order_not_found(client):
    """Testa GET /api/v1/orders/{order_id} não encontrado."""
    response = client.get("/api/v1/orders/INVALID_ID")
    assert response.status_code == 404
