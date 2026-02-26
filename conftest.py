"""
conftest.py - Configuração de fixtures compartilhadas para testes

Fornece fixtures reutilizáveis para:
- Banco de dados (PostgreSQL)
- Fila de mensagens (RabbitMQ)
- Cache (Redis)
- Aplicação FastAPI
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, AsyncMock
import os
from dotenv import load_dotenv

# Configurar variáveis de ambiente para testes
load_dotenv()

# ==============================================================================
# DATABASE FIXTURES
# ==============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Cria event loop para testes async"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def database_url() -> str:
    """URL do banco de dados para testes"""
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://operador:password123@localhost:5432/operador_db_test"
    )


@pytest.fixture(scope="function")
def mock_db_connection():
    """Mock de conexão com banco de dados"""
    mock_conn = MagicMock()
    mock_conn.execute = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    mock_conn.fetchrow = AsyncMock(return_value=None)
    return mock_conn


@pytest.fixture(scope="function")
def mock_db_session():
    """Mock de sessão SQLAlchemy"""
    from sqlalchemy.orm import Session
    mock_session = MagicMock(spec=Session)
    mock_session.query = MagicMock()
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.rollback = MagicMock()
    mock_session.close = MagicMock()
    return mock_session


# ==============================================================================
# MESSAGE QUEUE FIXTURES
# ==============================================================================

@pytest.fixture(scope="session")
def rabbitmq_url() -> str:
    """URL do RabbitMQ para testes"""
    return os.getenv(
        "TEST_RABBITMQ_URL",
        "amqp://operador:password123@localhost:5672/"
    )


@pytest.fixture(scope="function")
def mock_rabbitmq_connection():
    """Mock de conexão com RabbitMQ"""
    mock_conn = AsyncMock()
    mock_conn.connect = AsyncMock()
    mock_conn.create_channel = AsyncMock()
    mock_conn.close = AsyncMock()
    return mock_conn


@pytest.fixture(scope="function")
def mock_rabbitmq_channel():
    """Mock de channel RabbitMQ"""
    mock_channel = AsyncMock()
    mock_channel.queue_declare = AsyncMock()
    mock_channel.exchange_declare = AsyncMock()
    mock_channel.queue_bind = AsyncMock()
    mock_channel.basic_publish = AsyncMock()
    mock_channel.basic_consume = AsyncMock()
    return mock_channel


@pytest.fixture(scope="function")
def mock_message_queue():
    """Mock de fila de mensagens"""
    mock_queue = MagicMock()
    mock_queue.put = AsyncMock()
    mock_queue.get = AsyncMock(return_value=None)
    mock_queue.empty = MagicMock(return_value=True)
    mock_queue.qsize = MagicMock(return_value=0)
    return mock_queue


# ==============================================================================
# CACHE FIXTURES
# ==============================================================================

@pytest.fixture(scope="session")
def redis_url() -> str:
    """URL do Redis para testes"""
    return os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")


@pytest.fixture(scope="function")
def mock_redis():
    """Mock do cliente Redis"""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock()
    mock_redis.delete = AsyncMock()
    mock_redis.exists = AsyncMock(return_value=False)
    mock_redis.expire = AsyncMock()
    mock_redis.hgetall = AsyncMock(return_value={})
    return mock_redis


# ==============================================================================
# API FIXTURES
# ==============================================================================

@pytest.fixture(scope="function")
def mock_fastapi_app():
    """Mock de aplicação FastAPI"""
    from fastapi import FastAPI
    app = FastAPI()
    return app


@pytest.fixture(scope="function")
def http_client():
    """Client HTTP para testes (usando httpx)"""
    from httpx import AsyncClient

    @pytest.fixture
    async def get_client():
        async with AsyncClient() as client:
            yield client

    return get_client


@pytest.fixture(scope="function")
def mock_http_response():
    """Mock de resposta HTTP"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value={})
    mock_response.text = "OK"
    mock_response.headers = {}
    return mock_response


# ==============================================================================
# WEBSOCKET FIXTURES
# ==============================================================================

@pytest.fixture(scope="function")
def mock_websocket():
    """Mock de conexão WebSocket"""
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.recv = AsyncMock(return_value='{"type": "ping"}')
    mock_ws.accept = AsyncMock()
    mock_ws.close = AsyncMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.receive_json = AsyncMock(return_value={})
    return mock_ws


# ==============================================================================
# MT5 FIXTURES
# ==============================================================================

@pytest.fixture(scope="function")
def mock_mt5_account():
    """Mock de conta MT5"""
    mock_account = MagicMock()
    mock_account.balance = 50000.0
    mock_account.equity = 51000.0
    mock_account.free_margin = 48000.0
    mock_account.leverage = 100
    mock_account.currency = "USD"
    return mock_account


@pytest.fixture(scope="function")
def mock_mt5_position():
    """Mock de posição aberta no MT5"""
    mock_position = MagicMock()
    mock_position.ticket = 123456
    mock_position.symbol = "EURUSD"
    mock_position.type = 0  # 0=BUY, 1=SELL
    mock_position.volume = 1.0
    mock_position.price_open = 1.0850
    mock_position.price_current = 1.0860
    mock_position.profit = 100.0
    mock_position.sl = 1.0840
    mock_position.tp = 1.0880
    return mock_position


@pytest.fixture(scope="function")
def mock_mt5_order():
    """Mock de ordem pendente"""
    mock_order = MagicMock()
    mock_order.ticket = 789456
    mock_order.symbol = "EURUSD"
    mock_order.type = 0  # 0=Buy limit, 1=Sell limit, etc
    mock_order.price_open = 1.0850
    mock_order.price_current = 1.0860
    mock_order.volume_initial = 1.0
    mock_order.volume_current = 1.0
    return mock_order


# ==============================================================================
# ML/DATA FIXTURES
# ==============================================================================

@pytest.fixture(scope="function")
def sample_market_data():
    """Dados de mercado de exemplo para testes"""
    import pandas as pd
    import numpy as np

    n_samples = 100
    timestamps = pd.date_range(start="2024-01-01", periods=n_samples, freq="1H")

    data = {
        "timestamp": timestamps,
        "open": np.random.uniform(1.08, 1.09, n_samples),
        "high": np.random.uniform(1.085, 1.095, n_samples),
        "low": np.random.uniform(1.075, 1.085, n_samples),
        "close": np.random.uniform(1.08, 1.09, n_samples),
        "volume": np.random.uniform(1000, 5000, n_samples),
    }

    return pd.DataFrame(data)


@pytest.fixture(scope="function")
def sample_features():
    """Features de exemplo para testes ML"""
    import pandas as pd
    import numpy as np

    n_samples = 100
    features = {
        f"feature_{i}": np.random.normal(0, 1, n_samples)
        for i in range(24)  # 24 features como especificado
    }

    return pd.DataFrame(features)


@pytest.fixture(scope="function")
def sample_labels():
    """Labels de exemplo para testes ML"""
    import numpy as np
    return np.random.randint(0, 2, 100)


@pytest.fixture(scope="function")
def mock_xgboost_model():
    """Mock de modelo XGBoost"""
    mock_model = MagicMock()
    mock_model.predict = MagicMock(
        return_value=[0.1, 0.5, 0.8, 0.3, 0.9]
    )
    mock_model.predict_proba = MagicMock(
        return_value=[[0.9, 0.1], [0.5, 0.5], [0.2, 0.8], [0.7, 0.3], [0.1, 0.9]]
    )
    mock_model.score = MagicMock(return_value=0.85)
    return mock_model


# ==============================================================================
# CONFIGURATION FIXTURES
# ==============================================================================

@pytest.fixture(scope="function")
def test_config():
    """Configuração de teste"""
    return {
        "env": "test",
        "debug": True,
        "log_level": "DEBUG",
        "database_url": "postgresql://operador:password123@localhost:5432/operador_db_test",
        "rabbitmq_url": "amqp://operador:password123@localhost:5672/",
        "redis_url": "redis://localhost:6379/1",
        "api_host": "0.0.0.0",
        "api_port": 8000,
        "ws_host": "0.0.0.0",
        "ws_port": 8001,
    }


@pytest.fixture(scope="function")
def test_credentials():
    """Credenciais de teste"""
    return {
        "mt5_login": 123456,
        "mt5_password": "password",
        "mt5_server": "ICMarketsDemos",
        "email_user": "test@example.com",
        "email_password": "test_password",
    }


# ==============================================================================
# UTILITY FIXTURES
# ==============================================================================

@pytest.fixture(scope="function")
def caplog_higher_level(caplog):
    """Captura logs em nível DEBUG"""
    caplog.set_level("DEBUG")
    return caplog


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset automático de mocks entre testes"""
    yield
    # Cleanup após cada teste


# ==============================================================================
# MARKERS
# ==============================================================================

def pytest_configure(config):
    """Registra markers customizados"""
    config.addinivalue_line(
        "markers", "unit: marca teste como unitário"
    )
    config.addinivalue_line(
        "markers", "integration: marca teste como integração"
    )
    config.addinivalue_line(
        "markers", "slow: marca teste como lento"
    )
    config.addinivalue_line(
        "markers", "critical: marca teste como crítico para GATE"
    )
    config.addinivalue_line(
        "markers", "orders: marca teste relacionado a ordens"
    )
    config.addinivalue_line(
        "markers", "risk: marca teste relacionado a risco"
    )
    config.addinivalue_line(
        "markers", "ml: marca teste relacionado a machine learning"
    )
