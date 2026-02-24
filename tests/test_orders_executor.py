"""
Unit tests for Orders Executor.
S1-1: Configuração MT5 Production.
"""

import pytest
from src.application.orders_executor import ExecutionOrder, OrderState

def test_order_state_transitions():
    order = ExecutionOrder(
        order_id="ORD-TEST",
        symbol="WIN$N",
        order_type="BUY",
        volume=1.0,
        entry_price=120000.0,
        stop_loss=119800.0,
        take_profit=120500.0,
        detector_spike=2.0,
        ml_classifier_score=0.85
    )

    assert order.state == OrderState.ENQUEUED

    order.add_audit(OrderState.VALIDATED, "Passed risk gates")
    assert order.state == OrderState.VALIDATED
    assert len(order.audit_log) == 1
    assert order.audit_log[0].message == "Passed risk gates"
