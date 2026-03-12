# -*- coding: utf-8 -*-
"""
Tests for ForcedActivationManager - P0-URGENT-2 Validation Tests

Cobertura: 5 Acceptance Criteria com 20+ testes
- AC1: Função should_force_activation() implementada
- AC2: Ativa quando confidence < 0.35 AND dias_inativos >= 3
- AC3: Ativa quando cost_operacional_acumulado > R$ 1.000
- AC4: Log mostra "⚠️ FORCED ACTIVATION TRIGGERED"
- AC5: Signal threshold relaxado de 0.65 → 0.40 durante activation
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
import logging

from src.application.services.forced_activation_manager import (
    ForcedActivationManager,
    ForcedActivationConfig,
    ForceActivationReason,
    ForcedActivationMetrics,
)


class TestForcedActivationManagerAC1:
    """AC1: Função should_force_activation() implementada com assinatura correta."""

    def test_ac1_function_exists(self):
        """should_force_activation() existe e é callable."""
        config = ForcedActivationConfig()
        manager = ForcedActivationManager(config)
        assert hasattr(manager, 'should_force_activation')
        assert callable(manager.should_force_activation)

    def test_ac1_function_signature(self):
        """Função aceita parâmetros corretos."""
        config = ForcedActivationConfig()
        manager = ForcedActivationManager(config)
        manager.start_session()

        # Deve aceitar estes parâmetros
        should_force, reason, threshold = manager.should_force_activation(
            confidence_current=Decimal("0.75"),
            days_inactive=0,
            cost_accumulated=Decimal("0"),
        )

        assert isinstance(should_force, bool)
        assert isinstance(reason, ForceActivationReason)
        assert isinstance(threshold, Decimal)

    def test_ac1_returns_tuple(self):
        """Retorna tuple (bool, reason, threshold)."""
        config = ForcedActivationConfig()
        manager = ForcedActivationManager(config)
        manager.start_session()

        result = manager.should_force_activation(
            confidence_current=Decimal("0.5"),
            days_inactive=1,
            cost_accumulated=Decimal("500"),
        )

        assert isinstance(result, tuple)
        assert len(result) == 3


class TestForcedActivationManagerAC2:
    """AC2: Ativa quando confidence < 0.35 AND dias_inativos >= 3."""

    def test_ac2_no_activation_high_confidence(self):
        """Não ativa com confidence alta (mesmo dias inativo)."""
        config = ForcedActivationConfig(
            confidence_threshold_low=Decimal("0.35"),
            days_inactive_threshold=3,
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        should_force, reason, _ = manager.should_force_activation(
            confidence_current=Decimal("0.75"),
            days_inactive=5,
            cost_accumulated=Decimal("500"),
        )

        assert not should_force
        assert reason == ForceActivationReason.NONE

    def test_ac2_no_activation_low_confidence_but_short_inactive(self):
        """Não ativa mesmo com confidence baixa se dias inativo < threshold."""
        config = ForcedActivationConfig(
            confidence_threshold_low=Decimal("0.35"),
            days_inactive_threshold=3,
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        should_force, reason, _ = manager.should_force_activation(
            confidence_current=Decimal("0.25"),  # < 0.35
            days_inactive=2,  # < 3
            cost_accumulated=Decimal("500"),
        )

        assert not should_force

    def test_ac2_activation_low_confidence_long_inactive(self):
        """ATIVA quando confidence < 0.35 AND dias_inativo >= 3."""
        config = ForcedActivationConfig(
            confidence_threshold_low=Decimal("0.35"),
            days_inactive_threshold=3,
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        should_force, reason, _ = manager.should_force_activation(
            confidence_current=Decimal("0.25"),  # < 0.35
            days_inactive=3,  # >= 3
            cost_accumulated=Decimal("500"),
        )

        assert should_force
        assert reason == ForceActivationReason.CONFIDENCE_CRASH

    def test_ac2_boundary_confidence_exactly_at_threshold(self):
        """Não ativa com confidence = threshold (boundary)."""
        config = ForcedActivationConfig(
            confidence_threshold_low=Decimal("0.35"),
            days_inactive_threshold=3,
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        should_force, reason, _ = manager.should_force_activation(
            confidence_current=Decimal("0.35"),  # = threshold (não <)
            days_inactive=3,
            cost_accumulated=Decimal("500"),
        )

        assert not should_force


class TestForcedActivationManagerAC3:
    """AC3: Ativa quando cost_operacional_acumulado > R$ 1.000."""

    def test_ac3_no_activation_low_cost(self):
        """Não ativa com custo baixo."""
        config = ForcedActivationConfig(
            cost_threshold_breach=Decimal("1000"),
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        should_force, reason, _ = manager.should_force_activation(
            confidence_current=Decimal("0.75"),
            days_inactive=1,
            cost_accumulated=Decimal("500"),
        )

        assert not should_force
        assert reason == ForceActivationReason.NONE

    def test_ac3_no_activation_exact_threshold(self):
        """Não ativa com cost = threshold (boundary)."""
        config = ForcedActivationConfig(
            cost_threshold_breach=Decimal("1000"),
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        should_force, reason, _ = manager.should_force_activation(
            confidence_current=Decimal("0.75"),
            days_inactive=1,
            cost_accumulated=Decimal("1000"),  # = threshold (não >)
        )

        assert not should_force

    def test_ac3_activation_above_threshold(self):
        """ATIVA quando cost > threshold."""
        config = ForcedActivationConfig(
            cost_threshold_breach=Decimal("1000"),
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        should_force, reason, _ = manager.should_force_activation(
            confidence_current=Decimal("0.75"),
            days_inactive=1,
            cost_accumulated=Decimal("1001"),  # > 1000
        )

        assert should_force
        assert reason == ForceActivationReason.COST_THRESHOLD_BREACH

    def test_ac3_large_cost_accumulated(self):
        """Ativa com costo muito alto (custo real)."""
        config = ForcedActivationConfig(
            cost_threshold_breach=Decimal("1000"),
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        should_force, reason, _ = manager.should_force_activation(
            confidence_current=Decimal("0.5"),
            days_inactive=2,
            cost_accumulated=Decimal("5000"),  # R$ 5.000 prejuízo
        )

        assert should_force
        assert reason == ForceActivationReason.COST_THRESHOLD_BREACH


class TestForcedActivationManagerAC4:
    """AC4: Log mostra "⚠️ FORCED ACTIVATION TRIGGERED"."""

    def test_ac4_log_message_on_activation(self, caplog):
        """Log contém "⚠️ FORCED ACTIVATION TRIGGERED" ao ativar."""
        config = ForcedActivationConfig(
            confidence_threshold_low=Decimal("0.35"),
            days_inactive_threshold=3,
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        with caplog.at_level(logging.WARNING):
            should_force, _, _ = manager.should_force_activation(
                confidence_current=Decimal("0.25"),
                days_inactive=3,
                cost_accumulated=Decimal("500"),
            )

        assert should_force
        assert any("⚠️ FORCED ACTIVATION TRIGGERED" in record.message for record in caplog.records)

    def test_ac4_log_contains_reason(self, caplog):
        """Log contém razão da ativação."""
        config = ForcedActivationConfig(
            confidence_threshold_low=Decimal("0.35"),
            days_inactive_threshold=3,
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        with caplog.at_level(logging.WARNING):
            manager.should_force_activation(
                confidence_current=Decimal("0.25"),
                days_inactive=3,
                cost_accumulated=Decimal("500"),
            )

        assert any("confidence_crash" in record.message for record in caplog.records)

    def test_ac4_no_log_without_activation(self, caplog):
        """Log NÃO contém "FORCED ACTIVATION" se não ativar."""
        config = ForcedActivationConfig()
        manager = ForcedActivationManager(config)
        manager.start_session()

        with caplog.at_level(logging.WARNING):
            manager.should_force_activation(
                confidence_current=Decimal("0.75"),
                days_inactive=1,
                cost_accumulated=Decimal("500"),
            )

        assert not any("⚠️ FORCED ACTIVATION TRIGGERED" in record.message for record in caplog.records)

    def test_ac4_anti_spam_logging(self, caplog):
        """Log anti-spam: máximo 1 por minuto por tipo."""
        config = ForcedActivationConfig(
            confidence_threshold_low=Decimal("0.35"),
            days_inactive_threshold=3,
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        with caplog.at_level(logging.WARNING):
            # Primeira ativação
            manager.should_force_activation(
                confidence_current=Decimal("0.25"),
                days_inactive=3,
                cost_accumulated=Decimal("500"),
            )

            # Segunda tentativa logo após
            manager.should_force_activation(
                confidence_current=Decimal("0.25"),
                days_inactive=3,
                cost_accumulated=Decimal("600"),
            )

        # Deve ter apenas 1 log (spam suprimido)
        activation_logs = [r for r in caplog.records if "⚠️ FORCED ACTIVATION TRIGGERED" in r.message]
        assert len(activation_logs) == 1


class TestForcedActivationManagerAC5:
    """AC5: Signal threshold relaxado de 0.65 → 0.40 durante activation."""

    def test_ac5_threshold_during_activation(self):
        """Retorna threshold relaxado (0.40) quando ativa."""
        config = ForcedActivationConfig(
            confidence_threshold_low=Decimal("0.35"),
            days_inactive_threshold=3,
            relaxed_signal_threshold=Decimal("0.40"),
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        should_force, _, threshold = manager.should_force_activation(
            confidence_current=Decimal("0.25"),
            days_inactive=3,
            cost_accumulated=Decimal("500"),
        )

        assert should_force
        assert threshold == Decimal("0.40")

    def test_ac5_threshold_normal_no_activation(self):
        """Retorna threshold normal (0.65) quando não ativa."""
        config = ForcedActivationConfig(
            normal_signal_threshold=Decimal("0.65"),
            relaxed_signal_threshold=Decimal("0.40"),
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        should_force, _, threshold = manager.should_force_activation(
            confidence_current=Decimal("0.75"),
            days_inactive=1,
            cost_accumulated=Decimal("500"),
        )

        assert not should_force
        assert threshold == Decimal("0.65")

    def test_ac5_threshold_during_activation_window(self):
        """Mantém threshold relaxado durante janela de ativação."""
        config = ForcedActivationConfig(
            confidence_threshold_low=Decimal("0.35"),
            days_inactive_threshold=3,
            relaxed_signal_threshold=Decimal("0.40"),
            activation_window_minutes=60,
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        # Primeira chamada ativa
        should_force_1, _, threshold_1 = manager.should_force_activation(
            confidence_current=Decimal("0.25"),
            days_inactive=3,
            cost_accumulated=Decimal("500"),
        )

        # Segunda chamada (ainda dentro da janela)
        should_force_2, _, threshold_2 = manager.should_force_activation(
            confidence_current=Decimal("0.75"),  # Confidence voltou normal
            days_inactive=3,
            cost_accumulated=Decimal("500"),
        )

        assert should_force_1
        assert should_force_2  # Continua ativado (dentro da janela)
        assert threshold_1 == Decimal("0.40")
        assert threshold_2 == Decimal("0.40")  # Mantém relaxado

    def test_ac5_threshold_reset_after_entry(self):
        """Reseta threshold após entrada registrada."""
        config = ForcedActivationConfig(
            confidence_threshold_low=Decimal("0.35"),
            days_inactive_threshold=3,
            normal_signal_threshold=Decimal("0.65"),
            relaxed_signal_threshold=Decimal("0.40"),
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        # Ativa
        should_force, _, threshold_1 = manager.should_force_activation(
            confidence_current=Decimal("0.25"),
            days_inactive=3,
            cost_accumulated=Decimal("500"),
        )

        assert threshold_1 == Decimal("0.40")

        # Registra entrada
        manager.record_activation_entry(is_forced=True)

        # Próxima chamada retorna threshold normal novamente
        should_force_2, _, threshold_2 = manager.should_force_activation(
            confidence_current=Decimal("0.75"),
            days_inactive=4,
            cost_accumulated=Decimal("600"),
        )

        assert not should_force_2
        assert threshold_2 == Decimal("0.65")


class TestForcedActivationManagerIntegration:
    """Testes de integração com fluxos realistas."""

    def test_integration_realistic_session_flow(self):
        """Fluxo realista: inativa → ativa → entrada → reset."""
        config = ForcedActivationConfig()
        manager = ForcedActivationManager(config)
        manager.start_session()

        # Fase 1: Modelo com confiança normal
        should_force, _, _ = manager.should_force_activation(
            confidence_current=Decimal("0.70"),
            days_inactive=0,
            cost_accumulated=Decimal("100"),
        )
        assert not should_force

        # Fase 2: Modelo fica inativo + confidence cai
        should_force, reason, threshold = manager.should_force_activation(
            confidence_current=Decimal("0.25"),
            days_inactive=4,
            cost_accumulated=Decimal("800"),
        )
        assert should_force
        assert reason == ForceActivationReason.CONFIDENCE_CRASH
        assert threshold == config.relaxed_signal_threshold

        # Fase 3: Registra entrada
        manager.record_activation_entry(is_forced=True)

        # Fase 4: Voltou ao normal
        stats = manager.get_activation_stats()
        assert stats.total_activations >= 1

    def test_integration_multiple_activation_reasons(self):
        """Teste com múltiplos motivos de ativação registrados."""
        config = ForcedActivationConfig(
            activation_window_minutes=0,  # Sem janela para testar ativações independentes
        )
        manager = ForcedActivationManager(config)
        manager.start_session()

        # Primeira ativação por confiança
        should_force_1, reason_1, _ = manager.should_force_activation(
            confidence_current=Decimal("0.25"),
            days_inactive=3,
            cost_accumulated=Decimal("500"),
        )

        # Reseta ativação (simula entrada registrada)
        manager.record_activation_entry(is_forced=True)

        # Segunda ativação por custo (agora sem estar em janela)
        should_force_2, reason_2, _ = manager.should_force_activation(
            confidence_current=Decimal("0.75"),
            days_inactive=1,
            cost_accumulated=Decimal("1500"),
        )

        assert should_force_1
        assert reason_1 == ForceActivationReason.CONFIDENCE_CRASH
        assert should_force_2
        assert reason_2 == ForceActivationReason.COST_THRESHOLD_BREACH

        stats = manager.get_activation_stats()
        assert stats.total_activations >= 2
        assert len(stats.activations_by_reason) >= 2

    def test_integration_get_status(self):
        """Método get_status() retorna status esperado."""
        config = ForcedActivationConfig()
        manager = ForcedActivationManager(config)
        manager.start_session()

        status = manager.get_status()

        assert isinstance(status, dict)
        assert "session_active" in status
        assert "activation_active" in status
        assert "last_confidence" in status
        assert "total_activations" in status
        assert status["session_active"]
        assert not status["activation_active"]  # Inicialmente
        assert status["total_activations"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
