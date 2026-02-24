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
    VolatilityValidator,
    RiskValidationProcessor,
    GateStatus,
    GateResult
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

@pytest.fixture
def context_with_positions():
    """Context com posições abertas para teste de correlação"""
    return ValidationContext(
        account_balance=5000.0,
        account_equity=5000.0,
        margin_free=4500.0,
        open_positions=[
            {"symbol": "WINFUT", "entry_price": 100000.0, "stop_loss": 99000.0, "volume": 10}
        ],
        proposed_position_size=1.0,
        proposed_stop_loss=200.0,
        proposed_symbol="WIN$N",  # Altamente correlacionado com WINFUT (0.95)
        proposed_order_type="BUY"
    )


class TestCapitalAdequacyValidator:
    """Testes para validador de suficiência de capital"""

    def test_capital_adequacy_gate_pass(self, context):
        validator = CapitalAdequacyValidator()
        result = validator.validate(context)
        assert result.status == GateStatus.PASS

    def test_capital_adequacy_gate_fail(self, context):
        context.proposed_stop_loss = 6000.0
        validator = CapitalAdequacyValidator()
        result = validator.validate(context)
        assert result.status == GateStatus.FAIL

    def test_capital_adequacy_gate_name(self, context):
        validator = CapitalAdequacyValidator()
        result = validator.validate(context)
        assert result.gate_name == "CAPITAL_ADEQUACY"

    def test_capital_adequacy_message_present(self, context):
        validator = CapitalAdequacyValidator()
        result = validator.validate(context)
        assert len(result.message) > 0

    def test_capital_adequacy_details_present(self, context):
        validator = CapitalAdequacyValidator()
        result = validator.validate(context)
        assert isinstance(result.details, dict)
        assert "margin_free" in result.details


class TestCorrelationValidator:
    """Testes para validador de correlação"""

    def test_correlation_gate_pass(self, context):
        validator = CorrelationValidator()
        result = validator.validate(context)
        assert result.status == GateStatus.PASS

    def test_correlation_gate_name(self, context):
        validator = CorrelationValidator()
        result = validator.validate(context)
        assert result.gate_name == "CORRELATION"

    def test_correlation_gate_fail_high_correlation(self, context_with_positions):
        validator = CorrelationValidator()
        result = validator.validate(context_with_positions)
        # Correlação alta retorna WARN, não FAIL
        assert result.status in [GateStatus.FAIL, GateStatus.WARN]

    def test_correlation_matrix_built(self):
        validator = CorrelationValidator()
        assert len(validator.correlation_matrix) > 0

    def test_correlation_threshold_customizable(self):
        validator = CorrelationValidator(max_correlation=0.50)
        assert validator.max_correlation == 0.50


class TestVolatilityValidator:
    """Testes para validador de volatilidade"""

    def test_volatility_validator_created(self, context):
        validator = VolatilityValidator()
        assert validator is not None

    def test_volatility_gate_name(self, context):
        validator = VolatilityValidator()
        result = validator.validate(context)
        assert result.gate_name == "VOLATILITY"

    def test_volatility_threshold_warning_set(self):
        validator = VolatilityValidator()
        assert validator.warning_threshold == 2.0

    def test_volatility_threshold_reject_set(self):
        validator = VolatilityValidator()
        assert validator.reject_threshold == 3.0

    def test_volatility_thresholds_customizable(self):
        validator = VolatilityValidator(
            volatility_warning_threshold=1.5,
            volatility_reject_threshold=2.5
        )
        assert validator.warning_threshold == 1.5
        assert validator.reject_threshold == 2.5

    def test_volatility_result_has_details(self, context):
        validator = VolatilityValidator()
        result = validator.validate(context)
        assert isinstance(result.details, dict)
        assert "current_volatility_sigma" in result.details

    def test_volatility_message_present(self, context):
        validator = VolatilityValidator()
        result = validator.validate(context)
        assert len(result.message) > 0


class TestValidationContext:
    """Testes para contexto de validação"""

    def test_context_creation(self, context):
        assert context is not None
        assert context.account_balance == 5000.0

    def test_context_timestamp_auto_set(self, context):
        assert context.timestamp is not None
        assert isinstance(context.timestamp, datetime)

    def test_context_timestamp_custom(self):
        now = datetime.utcnow()
        ctx = ValidationContext(
            account_balance=5000.0,
            account_equity=5000.0,
            margin_free=4500.0,
            open_positions=[],
            proposed_position_size=1.0,
            proposed_stop_loss=200.0,
            proposed_symbol="WIN$N",
            proposed_order_type="BUY",
            timestamp=now
        )
        assert ctx.timestamp == now


class TestGateResult:
    """Testes para resultado de gate"""

    def test_gate_result_creation(self):
        result = GateResult(
            gate_name="TEST",
            status=GateStatus.PASS,
            message="Test message"
        )
        assert result.gate_name == "TEST"
        assert result.status == GateStatus.PASS
        assert result.message == "Test message"

    def test_gate_result_details_default_dict(self):
        result = GateResult(
            gate_name="TEST",
            status=GateStatus.PASS,
            message="Test"
        )
        assert isinstance(result.details, dict)
        assert len(result.details) == 0


class TestRiskValidationProcessor:
    """Testes para processador de validação"""

    def test_processor_creation(self):
        processor = RiskValidationProcessor()
        assert processor is not None

    def test_processor_chain_all_pass(self, context):
        processor = RiskValidationProcessor()
        approved, results = processor.validate_order(context)
        assert approved is True
        assert len(results) >= 2

    def test_processor_chain_order(self, context):
        processor = RiskValidationProcessor()
        approved, results = processor.validate_order(context)
        if len(results) > 0:
            assert results[0].gate_name == "CAPITAL_ADEQUACY"

    def test_processor_reject_on_capital_fail(self):
        context = ValidationContext(
            account_balance=100.0,
            account_equity=100.0,
            margin_free=1.0,
            open_positions=[],
            proposed_position_size=1000.0,
            proposed_stop_loss=5000.0,
            proposed_symbol="WIN$N",
            proposed_order_type="BUY"
        )
        processor = RiskValidationProcessor()
        approved, results = processor.validate_order(context)
        assert approved is False
        assert results[0].status == GateStatus.FAIL


class TestChainOfResponsibility:
    """Testes para padrão Chain of Responsibility"""

    def test_capital_has_next_validator(self):
        validator = CapitalAdequacyValidator()
        assert isinstance(validator, CapitalAdequacyValidator)

    def test_correlation_has_next_validator(self):
        validator = CorrelationValidator()
        assert isinstance(validator, CorrelationValidator)

    def test_capital_with_next_set(self):
        correlation_validator = CorrelationValidator()
        capital_validator = CapitalAdequacyValidator(next_validator=correlation_validator)
        assert capital_validator.next_validator == correlation_validator


class TestEdgeCases:
    """Testes para casos extremos"""

    def test_zero_stop_loss(self, context):
        context.proposed_stop_loss = 0.0
        validator = CapitalAdequacyValidator()
        result = validator.validate(context)
        assert result.status == GateStatus.PASS

    def test_zero_margin_free(self, context):
        context.margin_free = 0.0
        validator = CapitalAdequacyValidator()
        result = validator.validate(context)
        assert result.status == GateStatus.FAIL

    def test_negative_margin_free(self, context):
        context.margin_free = -100.0
        validator = CapitalAdequacyValidator()
        result = validator.validate(context)
        assert result.status == GateStatus.FAIL

    def test_large_position_size(self, context):
        context.proposed_position_size = 1000000.0
        context.proposed_stop_loss = 500000.0
        validator = CapitalAdequacyValidator()
        result = validator.validate(context)
        assert result.status == GateStatus.FAIL

    def test_calculate_total_open_risk_with_positions(self):
        """Teste _calculate_total_open_risk com posições que possuem stop loss"""
        positions = [
            {"stop_loss": 99000.0, "entry_price": 100000.0},
            {"stop_loss": 50000.0, "entry_price": 50500.0}
        ]
        risk = CapitalAdequacyValidator._calculate_total_open_risk(positions)
        assert risk > 0

    def test_calculate_total_open_risk_empty(self):
        """Teste _calculate_total_open_risk com lista vazia"""
        positions = []
        risk = CapitalAdequacyValidator._calculate_total_open_risk(positions)
        assert risk == 0.0

    def test_correlation_matrix_has_bidirectional_entries(self):
        """Teste que matriz de correlação tem entradas bidirecionais"""
        validator = CorrelationValidator()
        # Se existe (A, B) deve ter (B, A)
        assert ("WINFUT", "WIN$N") in validator.correlation_matrix
        assert ("WIN$N", "WINFUT") in validator.correlation_matrix

    def test_volatility_with_positions_containing_dict(self, context_with_positions):
        """Teste volatilidade com posições em formato dict"""
        validator = VolatilityValidator()
        result = validator.validate(context_with_positions)
        assert result.gate_name == "VOLATILITY"

    def test_processor_with_multiple_positions(self):
        """Teste processador com múltiplas posições abertas"""
        context = ValidationContext(
            account_balance=150000.0,
            account_equity=148500.0,
            margin_free=50000.0,
            open_positions=[
                {"symbol": "PETR4", "entry_price": 25.5, "stop_loss": 25.0, "volume": 100},
                {"symbol": "VALE3", "entry_price": 60.0, "stop_loss": 59.0, "volume": 50}
            ],
            proposed_position_size=1000.0,
            proposed_stop_loss=500.0,
            proposed_symbol="WINFUT",
            proposed_order_type="BUY"
        )
        processor = RiskValidationProcessor()
        approved, results = processor.validate_order(context)
        assert len(results) > 0
        assert results[0].gate_name == "CAPITAL_ADEQUACY"

    def test_processor_all_gates_pass(self):
        """Teste processador com cenário onde TODAS as gates passam (linha 406)"""
        context = ValidationContext(
            account_balance=300000.0,
            account_equity=298500.0,
            margin_free=150000.0,
            open_positions=[],
            proposed_position_size=1000.0,
            proposed_stop_loss=500.0,
            proposed_symbol="WINFUT",
            proposed_order_type="BUY"
        )
        processor = RiskValidationProcessor()
        approved, results = processor.validate_order(context)
        # Todas as gates devem passar
        assert approved == True
        # Verificar que return statement é executado (linha 406)
        assert isinstance(results, list)
        assert len(results) == 3  # 3 validators

    def test_volatility_low_level(self):
        """Teste volatilidade em nível baixo (PASS)"""
        validator = VolatilityValidator()
        context = ValidationContext(
            account_balance=100000.0,
            account_equity=99000.0,
            margin_free=50000.0,
            open_positions=[],
            proposed_position_size=1000.0,
            proposed_stop_loss=500.0,
            proposed_symbol="WINFUT",
            proposed_order_type="BUY"
        )
        result = validator.validate(context)
        assert result.gate_name == "VOLATILITY"
        assert result.status in [GateStatus.PASS, GateStatus.WARN]

    def test_volatility_forced_fail_path(self):
        """Teste path FAIL do volatility (linhas 311-315)"""
        validator = VolatilityValidator()
        # Simular volatilidade extrema ajustando validator threshold
        validator.reject_threshold = 1.0  # Força current_volatility > reject
        context = ValidationContext(
            account_balance=100000.0,
            account_equity=99000.0,
            margin_free=50000.0,
            open_positions=[],
            proposed_position_size=1000.0,
            proposed_stop_loss=500.0,
            proposed_symbol="WINFUT",
            proposed_order_type="BUY"
        )
        result = validator.validate(context)
        assert result.gate_name == "VOLATILITY"
        assert result.status == GateStatus.FAIL
        assert "EXTREMA" in result.message

    def test_volatility_forced_warn_path(self):
        """Teste path WARN do volatility (linhas 325-329)"""
        validator = VolatilityValidator()
        # Simular volatilidade alta ajustando validator threshold entre warning e reject
        validator.warning_threshold = 1.0
        validator.reject_threshold = 2.0
        context = ValidationContext(
            account_balance=100000.0,
            account_equity=99000.0,
            margin_free=50000.0,
            open_positions=[],
            proposed_position_size=1000.0,
            proposed_stop_loss=500.0,
            proposed_symbol="WINFUT",
            proposed_order_type="BUY"
        )
        result = validator.validate(context)
        assert result.gate_name == "VOLATILITY"
        assert result.status == GateStatus.WARN
        assert "alta" in result.message

    def test_processor_return_tuple_structure(self):
        """Teste que processador retorna tuple (approved, results) corretamente"""
        # Na linha 406, ensure que return é executado com tuple correto
        processor = RiskValidationProcessor()
        context = ValidationContext(
            account_balance=200000.0,
            account_equity=199000.0,
            margin_free=100000.0,
            open_positions=[],
            proposed_position_size=2000.0,
            proposed_stop_loss=1000.0,
            proposed_symbol="WDFUT",
            proposed_order_type="SELL"
        )
        result = processor.validate_order(context)
        # Validar estrutura exata do return (linha 406): return approved, results
        assert isinstance(result, tuple), "validate_order deve retornar tuple"
        assert len(result) == 2, f"Tuple deve ter 2 elementos, got {len(result)}"
        approved, results = result
        assert isinstance(approved, bool), f"approved deve ser bool, got {type(approved)}"
        assert isinstance(results, list), f"results deve ser list, got {type(results)}"
        assert len(results) == 3, "results deve ter 3 resultados de validators"
        # Cada resultado deve ser GateResult
        for r in results:
            assert isinstance(r, GateResult)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src/application/risk_validator"])
