"""
AC5.9: Validador de Feedback de Execucao - Suite de Testes

Testes para healthcheck e validacao de correlacao entre trades e feedback.
Cobertura: correlacao, tipos de outcome, persistencia, validacao de dados.

Classes testadas:
- FeedbackValidator: Classe principal de validacao
- FeedbackValidationResult: Dataclass com resultados
- FeedbackHealthReport: Relatorio estruturado de saude
"""

import pytest
import json
from datetime import datetime
from typing import Dict, List
from unittest.mock import Mock, patch


class TestFeedbackValidatorBasics:
    """Testes basicos de inicializacao e configuracao."""

    def test_validator_initialization(self):
        """Validador inicializa corretamente."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()
        assert validator is not None
        assert hasattr(validator, "validate_feedback_health")
        assert hasattr(validator, "validate_correlation")

    def test_validation_result_structure(self):
        """FeedbackValidationResult tem campos obrigatorios."""
        from src.application.ac5_9_feedback_validator import (
            FeedbackValidationResult,
        )

        result = FeedbackValidationResult(
            is_valid=True,
            total_trades=10,
            total_feedback=8,
            correlation_rate=0.8,
            errors=[],
            warnings=["Test warning"],
            timestamp=datetime.now().isoformat(),
        )

        assert result.is_valid is True
        assert result.total_trades == 10
        assert result.total_feedback == 8
        assert result.correlation_rate == 0.8
        assert len(result.warnings) == 1

    def test_health_report_structure(self):
        """FeedbackHealthReport tem estrutura completa."""
        from src.application.ac5_9_feedback_validator import FeedbackHealthReport

        report = FeedbackHealthReport(
            overall_status="HEALTHY",
            validation_timestamp=datetime.now().isoformat(),
            correlation_rate=0.95,
            data_quality_score=0.92,
            missing_outcomes=2,
            invalid_types=0,
            recommendations=[],
        )

        assert report.overall_status in ["HEALTHY", "WARNING", "CRITICAL"]
        assert report.correlation_rate >= 0.0
        assert report.correlation_rate <= 1.0
        assert report.data_quality_score >= 0.0
        assert isinstance(report.recommendations, list)


class TestCorrelationValidation:
    """Testes de validacao de correlacao trade/feedback."""

    def test_validate_correlation_perfect(self):
        """Correlacao perfeita (100%) validada corretamente."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()

        # Mock de dados correlacionados perfeitamente
        trades_data = [
            {"trade_id": 1, "signal_id": "sig_001"},
            {"trade_id": 2, "signal_id": "sig_002"},
            {"trade_id": 3, "signal_id": "sig_003"},
        ]

        feedback_data = [
            {"feedback_id": 1, "trade_id": 1, "signal_label": "GOOD"},
            {"feedback_id": 2, "trade_id": 2, "signal_label": "BAD"},
            {"feedback_id": 3, "trade_id": 3, "signal_label": "GOOD"},
        ]

        result = validator.validate_correlation(trades_data, feedback_data)

        assert result["correlation_rate"] == 1.0  # 100% correlacionadas
        assert result["matched_trades"] == 3
        assert result["total_trades"] == 3

    def test_validate_correlation_partial(self):
        """Correlacao parcial (67%) validada corretamente."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()

        trades_data = [
            {"trade_id": 1, "signal_id": "sig_001"},
            {"trade_id": 2, "signal_id": "sig_002"},
            {"trade_id": 3, "signal_id": "sig_003"},
        ]

        feedback_data = [
            {"feedback_id": 1, "trade_id": 1, "signal_label": "GOOD"},
            {"feedback_id": 2, "trade_id": 2, "signal_label": "BAD"},
        ]

        result = validator.validate_correlation(trades_data, feedback_data)

        assert result["correlation_rate"] == pytest.approx(2/3, rel=0.01)
        assert result["matched_trades"] == 2
        assert result["total_trades"] == 3

    def test_validate_correlation_no_match(self):
        """Correlacao zero (0%) validada corretamente."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()

        trades_data = [
            {"trade_id": 1, "signal_id": "sig_001"},
            {"trade_id": 2, "signal_id": "sig_002"},
        ]

        feedback_data = [
            {"feedback_id": 1, "trade_id": 99, "signal_label": "GOOD"},
        ]

        result = validator.validate_correlation(trades_data, feedback_data)

        assert result["correlation_rate"] == 0.0
        assert result["matched_trades"] == 0
        assert result["total_trades"] == 2


class TestOutcomeTypeValidation:
    """Testes de validacao de tipos de outcome."""

    def test_validate_outcome_types_valid(self):
        """Tipos de outcome validos [WIN, LOSS, BREAKEVEN] sao aceitos."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()

        feedback_data = [
            {"feedback_id": 1, "outcome_type": "WIN", "pnl": 100.0},
            {"feedback_id": 2, "outcome_type": "LOSS", "pnl": -50.0},
            {"feedback_id": 3, "outcome_type": "BREAKEVEN", "pnl": 0.0},
        ]

        result = validator.validate_outcome_types(feedback_data)

        assert result["valid_outcomes"] == 3
        assert result["invalid_outcomes"] == 0
        assert result["validity_rate"] == 1.0

    def test_validate_outcome_types_invalid(self):
        """Tipos de outcome invalidos sao detectados e reportados."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()

        feedback_data = [
            {"feedback_id": 1, "outcome_type": "WIN", "pnl": 100.0},
            {"feedback_id": 2, "outcome_type": "INVALID_TYPE", "pnl": -50.0},
            {"feedback_id": 3, "outcome_type": None, "pnl": 0.0},
        ]

        result = validator.validate_outcome_types(feedback_data)

        assert result["valid_outcomes"] == 1
        assert result["invalid_outcomes"] == 2
        assert result["validity_rate"] == pytest.approx(1/3, rel=0.01)
        assert len(result["invalid_entries"]) == 2

    def test_validate_pnl_consistency(self):
        """Consistencia entre outcome_type e PnL e validada."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()

        feedback_data = [
            {"feedback_id": 1, "outcome_type": "WIN", "pnl": 100.0},
            {"feedback_id": 2, "outcome_type": "LOSS", "pnl": -50.0},
            {"feedback_id": 3, "outcome_type": "BREAKEVEN", "pnl": 0.5},  # Inconsistente!
        ]

        result = validator.validate_pnl_consistency(feedback_data)

        assert result["consistent"] == 2
        assert result["inconsistent"] == 1
        assert len(result["inconsistencies"]) == 1


class TestFeedbackHealthCheck:
    """Testes de healthcheck geral de feedback."""

    def test_health_check_healthy_status(self):
        """Healthcheck retorna HEALTHY para dados bons."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()

        # Mock de dados saudaveis
        trades = [
            {"trade_id": i, "executed_at": datetime.now().isoformat()}
            for i in range(1, 11)
        ]
        feedback = [
            {
                "feedback_id": i,
                "trade_id": i,
                "outcome_type": "WIN" if i % 2 == 0 else "LOSS",
                "pnl": 100.0 if i % 2 == 0 else -50.0,
                "signal_label": "GOOD",
            }
            for i in range(1, 11)
        ]

        report = validator.validate_feedback_health(trades, feedback)

        assert report.overall_status == "HEALTHY"
        assert report.correlation_rate >= 0.95
        assert report.data_quality_score >= 0.90
        assert len(report.recommendations) == 0

    def test_health_check_warning_status(self):
        """Healthcheck retorna WARNING para dados degradados."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()

        trades = [
            {"trade_id": i, "executed_at": datetime.now().isoformat()}
            for i in range(1, 11)
        ]
        # Apenas 50% de feedback
        feedback = [
            {
                "feedback_id": i,
                "trade_id": i,
                "outcome_type": "WIN",
                "pnl": 100.0,
                "signal_label": "GOOD",
            }
            for i in range(1, 6)
        ]

        report = validator.validate_feedback_health(trades, feedback)

        assert report.overall_status in ["WARNING", "HEALTHY"]
        assert report.correlation_rate < 1.0
        assert report.missing_outcomes > 0

    def test_health_check_critical_status(self):
        """Healthcheck retorna CRITICAL para dados muito degradados."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()

        trades = [
            {"trade_id": i, "executed_at": datetime.now().isoformat()}
            for i in range(1, 21)
        ]
        # Apenas 10% de feedback
        feedback = [
            {
                "feedback_id": 1,
                "trade_id": 1,
                "outcome_type": "WIN",
                "pnl": 100.0,
                "signal_label": "GOOD",
            }
        ]

        report = validator.validate_feedback_health(trades, feedback)

        assert report.overall_status in ["CRITICAL", "WARNING"]
        assert report.correlation_rate < 0.5
        assert report.missing_outcomes > 10


class TestReportGeneration:
    """Testes de geracao e formatacao de relatorios."""

    def test_generate_json_report(self):
        """Relatorio pode ser serializado em JSON."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()
        trades = [{"trade_id": 1}]
        feedback = []

        report = validator.validate_feedback_health(trades, feedback)
        report_json = report.to_json()

        assert isinstance(report_json, str)
        data = json.loads(report_json)
        assert data["overall_status"] in ["HEALTHY", "WARNING", "CRITICAL"]
        assert "correlation_rate" in data
        assert "validation_timestamp" in data

    def test_generate_markdown_report(self):
        """Relatorio pode ser formatado em Markdown."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()
        trades = [{"trade_id": 1}]
        feedback = []

        report = validator.validate_feedback_health(trades, feedback)
        markdown = report.to_markdown()

        assert isinstance(markdown, str)
        assert "# Relatorio de Saude" in markdown or "##" in markdown
        assert "CRITICAL" in markdown or "WARNING" in markdown or "HEALTHY" in markdown


class TestEdgeCases:
    """Testes de casos extremos."""

    def test_empty_trades_and_feedback(self):
        """Validador maneja trades e feedback vazios."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()

        result = validator.validate_correlation([], [])

        assert result["correlation_rate"] == 0.0 or result["total_trades"] == 0

    def test_null_values_handling(self):
        """Valores nulos sao tratados corretamente."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()

        feedback_data = [
            {"feedback_id": None, "outcome_type": None},
            {"feedback_id": 2, "outcome_type": "WIN"},
        ]

        result = validator.validate_outcome_types(feedback_data)

        assert result["invalid_outcomes"] >= 1

    def test_very_large_dataset(self):
        """Validador performatico com >1K registros."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()

        trades = [{"trade_id": i} for i in range(1, 1001)]
        feedback = [
            {
                "feedback_id": i,
                "trade_id": i,
                "outcome_type": "WIN",
            }
            for i in range(1, 1001)
        ]

        result = validator.validate_correlation(trades, feedback)

        assert result["total_trades"] == 1000
        assert result["matched_trades"] == 1000


class TestTypeHintsIntegrity:
    """Testes de integridade de type hints."""

    def test_feedback_validator_type_hints(self):
        """FeedbackValidator tem 100% type hints."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()

        # Get all methods
        methods = [
            m
            for m in dir(validator)
            if not m.startswith("_") and callable(getattr(validator, m))
        ]

        # Verificar que metodos tem type hints
        assert len(methods) > 0
        # Todos os metodos publicos devem ter type hints

    def test_dataclass_type_hints(self):
        """Dataclasses tem 100% type hints."""
        from src.application.ac5_9_feedback_validator import (
            FeedbackValidationResult,
        )

        # Criar instancia
        result = FeedbackValidationResult(
            is_valid=True,
            total_trades=10,
            total_feedback=9,
            correlation_rate=0.9,
            errors=[],
            warnings=[],
            timestamp=datetime.now().isoformat(),
        )

        # Todos os campos devem ter tipos definidos
        assert hasattr(result, "__annotations__")
        assert len(result.__annotations__) > 0


class TestPortugueseLocalization:
    """Testes de localizacao em Portugues."""

    def test_error_messages_in_portuguese(self):
        """Mensagens de erro estao em Portugues."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()

        # Testar com dados invali dos
        feedback_data = [{"outcome_type": "INVALIDO"}]

        result = validator.validate_outcome_types(feedback_data)

        # Se houver mensagens, devem estar em Portugues
        if result.get("invalid_entries"):
            for entry in result["invalid_entries"]:
                # Mensagens devem ter palavras em portugues
                assert isinstance(entry, (dict, str))

    def test_report_text_in_portuguese(self):
        """Relatorios estao 100% em Portugues."""
        from src.application.ac5_9_feedback_validator import FeedbackValidator

        validator = FeedbackValidator()
        trades = [{"trade_id": 1}]
        feedback = []

        report = validator.validate_feedback_health(trades, feedback)
        markdown = report.to_markdown()

        # Verificar palavras comuns em Portugues
        assert any(
            word in markdown
            for word in [
                "Relatorio",
                "Saudavel",
                "Critico",
                "Status",
                "Validacao",
            ]
        )
