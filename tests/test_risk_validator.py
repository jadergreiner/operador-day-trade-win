"""
Unit tests for Risk Validator.
S1-1: Configuração MT5 Production.
"""

import pytest
from datetime import datetime
from src.application.risk_validator import (
    ValidationContext,
    CapitalAdequacyValidator,
    CorrelationValidator,
    GateStatus
)

@pytest.fixture
def context():
    return ValidationContext(
        account_balance=5000.0,
        account_equity=5000.0,
        margin_free=4500.0,
        open_positions=[],
        proposed_position_size=1.0,
        proposed_stop_loss=200.0,
        proposed_symbol="WIN$N",
        proposed_order_type="BUY"
    )

def test_capital_adequacy_gate_pass(context):
    validator = CapitalAdequacyValidator()
    result = validator.validate(context)
    assert result.status == GateStatus.PASS

def test_capital_adequacy_gate_fail(context):
    context.proposed_stop_loss = 6000.0
    validator = CapitalAdequacyValidator()
    result = validator.validate(context)
    assert result.status == GateStatus.FAIL

def test_correlation_gate_pass(context):
    validator = CorrelationValidator()
    result = validator.validate(context)
    assert result.status == GateStatus.PASS
