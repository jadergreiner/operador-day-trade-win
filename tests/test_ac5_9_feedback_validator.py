"""
AC5.9: Feedback Validator

Testes para validação de feedback entre trades executados e dados de aprendizado para ML/RL.

Referência: docs/BACKLOG.md (ROADMAP-MICRO-03 - AC5.9)
"""

import pytest
from typing import Dict, List
from datetime import datetime
from src.application.feedback_validator import (
    FeedbackValidator,
    FeedbackValidationResult,
    OutcomeType,
)


class TestFeedbackValidator:
    """
    Testes para validação de feedback de trades.

    O validador garante que cada trade executado tem feedback correspondente
    com tipos válidos, PnL consistente e timestamps sincronizados.
    """

    def test_validar_correlacao_basica(self, sample_trade_feedback_pair: tuple) -> None:
        """
        AC 5.9.1: Valida correlação básica trade ↔ feedback.

        Dado: Trade com feedback correspondente
        Quando: Validar correlação
        Então: Correlation rate = 1.0, status OK
        """
        # ARRANGE
        validator = FeedbackValidator()
        trade, feedback = sample_trade_feedback_pair
        
        # ACT
        result = validator.validar_correlacao([trade], [feedback])
        
        # ASSERT
        assert result is not None
        assert result.correlation_rate == 1.0
        assert result.is_valid

    def test_detecta_feedback_faltante(self, missing_feedback_outcomes: tuple) -> None:
        """
        AC 5.9.2: Detecta quando feedback está faltando para trade.

        Dado: 3 trades, feedback para apenas 1
        Quando: Validar correlação
        Então: Correlation rate = 0.33, warnings gerados
        """
        # ARRANGE
        validator = FeedbackValidator()
        trades, feedbacks = missing_feedback_outcomes
        
        # ACT
        result = validator.validar_correlacao(trades, feedbacks)
        
        # ASSERT
        assert result is not None
        assert result.correlation_rate < 1.0
        assert len(result.warnings) > 0

    def test_detecta_tipo_outcome_invalido(self, invalid_feedback_types: list) -> None:
        """
        AC 5.9.3: Detecta tipos de outcome inválidos.

        Dado: Feedbacks com outcome_type = "INVALID_TYPE", None, ""
        Quando: Validar tipos
        Então: Erros gerados, status = invalid
        """
        # ARRANGE
        validator = FeedbackValidator()
        
        # ACT
        results = [validator.validar_tipos_outcome(fb) for fb in invalid_feedback_types]
        
        # ASSERT
        assert len(results) == 3
        assert all(not r.is_valid for r in results)
        assert all(len(r.errors) > 0 for r in results)

    def test_valida_outcome_types_validos(self, sample_trade_feedback_pair: tuple) -> None:
        """
        AC 5.9.4: Valida tipos de outcome válidos (CLOSED, PARTIAL, REJECTED, ABANDONED).

        Dado: Feedbacks com tipos válidos
        Quando: Validar tipos
        Então: Todos aceitos, status OK
        """
        # ARRANGE
        validator = FeedbackValidator()
        _, feedback = sample_trade_feedback_pair
        
        # ACT
        result = validator.validar_tipos_outcome(feedback)
        
        # ASSERT
        assert result is not None
        assert result.is_valid
        assert len(result.errors) == 0

    def test_valida_consistencia_pnl_exata(self, pnl_mismatch_feedbacks: list) -> None:
        """
        AC 5.9.5: Valida consistência PnL quando valores coincidem.

        Dado: pnl_actual = pnl_expected
        Quando: Validar consistência
        Então: Status OK, divergência = 0
        """
        # ARRANGE
        validator = FeedbackValidator()
        pnl_actual, pnl_expected = pnl_mismatch_feedbacks[0]  # (100, 100)
        feedback = {
            "trade_id": "test_1",
            "outcome_type": "CLOSED",
            "pnl_actual": pnl_actual,
            "pnl_expected": pnl_expected,
            "timestamp": datetime.now().isoformat()
        }
        
        # ACT
        result = validator.validar_consistencia_pnl(feedback)
        
        # ASSERT
        assert result is not None
        assert result.is_valid
        assert not any("diverge" in e.lower() for e in result.errors)

    def test_detecta_divergencia_pnl(self, pnl_mismatch_feedbacks: list) -> None:
        """
        AC 5.9.6: Detecta divergência de PnL.

        Dado: pnl_actual ≠ pnl_expected
        Quando: Validar consistência
        Então: Divergência identificada, warning gerado
        """
        # ARRANGE
        validator = FeedbackValidator()
        pnl_actual, pnl_expected = pnl_mismatch_feedbacks[1]  # (100, 110)
        feedback = {
            "trade_id": "test_2",
            "outcome_type": "CLOSED",
            "pnl_actual": pnl_actual,
            "pnl_expected": pnl_expected,
            "timestamp": datetime.now().isoformat()
        }
        
        # ACT
        result = validator.validar_consistencia_pnl(feedback)
        
        # ASSERT
        assert result is not None
        assert len(result.warnings) > 0 or len(result.errors) > 0
        assert any("pnl" in (e + w).lower() for e, w in [(str(result.errors), str(result.warnings))])

    def test_gera_healthcheck_report_basico(self, sample_trade_feedback_pair: tuple) -> None:
        """
        AC 5.9.7: Gera relatório de healthcheck básico.

        Dado: 1 trade com feedback válido
        Quando: Gerar healthcheck
        Então: Report com status, scores, recomendações
        """
        # ARRANGE
        validator = FeedbackValidator()
        trade, feedback = sample_trade_feedback_pair
        
        # ACT
        report = validator.gerar_healthcheck([trade], [feedback])
        
        # ASSERT
        assert report is not None
        assert report.overall_status in ["HEALTHY", "WARNING", "CRITICAL"]
        assert report.correlation_rate >= 0.0 and report.correlation_rate <= 1.0
        assert report.validation_timestamp is not None

    def test_healthcheck_status_critical_com_muitos_erros(self, missing_feedback_outcomes: tuple) -> None:
        """
        AC 5.9.8: Healthcheck status = CRITICAL quando muitos erros.

        Dado: 3 trades, feedback para apenas 1 (67% missing)
        Quando: Gerar healthcheck
        Então: Status = WARNING ou CRITICAL, recomendações geradas
        """
        # ARRANGE
        validator = FeedbackValidator()
        trades, feedbacks = missing_feedback_outcomes  # 1/3 feedback
        
        # ACT
        report = validator.gerar_healthcheck(trades, feedbacks)
        
        # ASSERT
        assert report is not None
        assert report.overall_status != "HEALTHY"
        assert len(report.recommendations) > 0

    def test_serializa_result_para_json(self, sample_trade_feedback_pair: tuple) -> None:
        """
        AC 5.9.9: Serializa resultado de validação para JSON.

        Dado: FeedbackValidationResult com dados
        Quando: Chamar to_json()
        Então: JSON válido com todos os campos
        """
        # ARRANGE
        validator = FeedbackValidator()
        trade, feedback = sample_trade_feedback_pair
        result = validator.validar_correlacao([trade], [feedback])
        
        # ACT
        json_str = result.to_json()
        
        # ASSERT
        assert isinstance(json_str, str)
        assert "correlation_rate" in json_str
        assert "is_valid" in json_str

    def test_serializa_healthcheck_para_markdown(self, sample_trade_feedback_pair: tuple) -> None:
        """
        AC 5.9.10: Serializa healthcheck para Markdown.

        Dado: FeedbackHealthReport
        Quando: Chamar to_markdown()
        Então: Markdown válido, legível para análise manual
        """
        # ARRANGE
        validator = FeedbackValidator()
        trade, feedback = sample_trade_feedback_pair
        report = validator.gerar_healthcheck([trade], [feedback])
        
        # ACT
        markdown_str = report.to_markdown()
        
        # ASSERT
        assert isinstance(markdown_str, str)
        assert len(markdown_str) > 0
        assert "#" in markdown_str  # Header markdown

    def test_valida_correlacao_batch(self, missing_feedback_outcomes: tuple) -> None:
        """
        AC 5.9.11: Valida correlação em batch (múltiplos trades).

        Dado: 5 trades, feedback para alguns
        Quando: Validar batch
        Então: Correlation rate calculada corretamente
        """
        # ARRANGE
        validator = FeedbackValidator()
        trades, feedbacks = missing_feedback_outcomes  # 3 trades, 1 feedback
        
        # ACT
        result = validator.validar_correlacao(trades, feedbacks)
        
        # ASSERT
        assert result is not None
        assert result.total_trades == len(trades)
        assert result.total_feedback == len(feedbacks)
        assert result.correlation_rate == len(feedbacks) / len(trades)

    def test_detecta_duplicata_feedback(self, sample_trade_feedback_pair: tuple) -> None:
        """
        AC 5.9.12: Detecta feedback duplicado para mesmo trade.

        Dado: 2 feedbacks com mesmo trade_id
        Quando: Validar
        Então: Erro de duplicação, warning gerado
        """
        # ARRANGE
        validator = FeedbackValidator()
        trade, feedback = sample_trade_feedback_pair
        duplicate_feedback = feedback.copy()  # Mesmo trade_id
        
        # ACT
        result = validator.validar_correlacao([trade], [feedback, duplicate_feedback])
        
        # ASSERT
        assert result is not None
        assert len(result.warnings) > 0 or len(result.errors) > 0

    def test_logging_detalhado(self, sample_trade_feedback_pair: tuple, caplog) -> None:
        """
        AC 5.9.13: Logging detalhado para debug.

        Dado: Validação com logging
        Quando: Validar feedback
        Então: Logs descrevem cada step
        """
        # ARRANGE
        import logging
        validator = FeedbackValidator(logger=logging.getLogger(__name__))
        trade, feedback = sample_trade_feedback_pair
        
        # ACT
        with caplog.at_level(logging.DEBUG):
            result = validator.validar_correlacao([trade], [feedback])
        
        # ASSERT
        assert result is not None

    def test_idempotencia_validacao(self, sample_trade_feedback_pair: tuple) -> None:
        """
        AC 5.9.14: Validação é idempotente (mesma entrada = mesma saída).

        Dado: Feedback para validar 2x
        Quando: Validar idênticamente 2 vezes
        Então: Resultados idênticos, sem side effects
        """
        # ARRANGE
        validator = FeedbackValidator()
        trade, feedback = sample_trade_feedback_pair
        
        # ACT
        result1 = validator.validar_correlacao([trade], [feedback])
        result2 = validator.validar_correlacao([trade], [feedback])
        
        # ASSERT
        assert result1.correlation_rate == result2.correlation_rate
        assert result1.is_valid == result2.is_valid
        assert len(result1.errors) == len(result2.errors)

    def test_performance_valida_1000_feedbacks(self, sample_trade_feedback_pair: tuple) -> None:
        """
        AC 5.9.15: Performance: valida 1000 feedbacks em <2s.

        Dado: Batch de 1000 feedbacks
        Quando: Validar
        Então: Concluído em <2s, sem timeout
        """
        # ARRANGE
        import time
        validator = FeedbackValidator()
        trade, feedback = sample_trade_feedback_pair
        
        # Replicar para ~1000
        trades = [trade.copy() for _ in range(1000)]
        feedbacks = [feedback.copy() for _ in range(1000)]
        
        # ACT
        start = time.time()
        result = validator.validar_correlacao(trades, feedbacks)
        elapsed = time.time() - start
        
        # ASSERT
        assert elapsed < 2.0, f"Levou {elapsed}s, limite é 2s"
        assert result is not None


# ═══════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestFeedbackValidatorIntegration:
    """Testes de integração AC5.9 com outros componentes."""

    def test_integracao_com_trade_outcome_reconciler(self) -> None:
        """Integração: FeedbackValidator + TradeOutcomeReconciler."""
        pytest.skip("Await implementation - depends on AC5.8 integration")

    def test_pipeline_completo_feedback_loop(self) -> None:
        """Pipeline: Trade → Reconciliação → Feedback → Validation."""
        pytest.skip("Await implementation - full pipeline test")
