"""
Unit tests for MT5 REST Adapter.
S1-1: Configuração MT5 Production.
"""

import pytest
from src.infrastructure.providers.mt5_adapter import MT5Adapter, MTOrder, OrderType

@pytest.fixture
def adapter():
    return MT5Adapter(base_url="http://localhost:8000")

def test_adapter_initialization(adapter):
    assert adapter.base_url == "http://localhost:8000"

def test_order_creation():
    order = MTOrder(
        ticket="123",
        symbol="WIN$N",
        order_type=OrderType.BUY,
        volume=1.0,
        entry_price=120000
    )
    assert order.symbol == "WIN$N"
    assert order.volume == 1.0

# Mocking connection tests if necessary
