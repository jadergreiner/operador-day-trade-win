# -*- coding: utf-8 -*-
"""
Forced Activation Manager - P0-URGENT-2 Implementation

Especificação: docs/BACKLOG_UNIFICADO.md :: P0-URGENT-2

Objetivo:
--------
Evitar que o modelo caia em "trap de inatividade" onde confidence → 0.
Quando dano operacional fica muito alto, força o modelo a tentar trades
mesmo com confidence baixa, relaxando threshold temporariamente.

Lógica:
-------
1. Monitora 3 condições de ativação:
   - confidence < 0.35 AND dias_inativos >= 3
   - cost_operacional_acumulado > R$ 1.000
   - confidence degradação > 50% em 24h

2. Quando ativado:
   - Log: "⚠️ FORCED ACTIVATION TRIGGERED"
   - Relaxa threshold: 0.65 → 0.40
   - Período: 60 minutos ou até próxima entrada
   - Cancela após primeira entrada bem-sucedida

3. Métricas:
   - Registra quantas vezes ativou
   - Rastreia trades forçados vs voluntários
   - Analisa performance (W/L) de trades forçados

Aceitação Critérios:
-------------------
AC1: Função should_force_activation() implementada
AC2: Ativa quando confidence < 0.35 AND dias_inativos >= 3
AC3: Ativa quando cost_operacional_acumulado > R$ 1.000
AC4: Log mostra "⚠️ FORCED ACTIVATION TRIGGERED"
AC5: Signal threshold relaxado de 0.65 → 0.40 durante activation

Uso:
----
    from src.application.services.forced_activation_manager import (
        ForcedActivationManager,
        ForcedActivationConfig,
        ForceActivationReason,
    )

    config = ForcedActivationConfig(
        confidence_threshold_low=0.35,
        days_inactive_threshold=3,
        cost_threshold_breach=1000.0,
        relaxed_signal_threshold=0.40,
        normal_signal_threshold=0.65,
        activation_window_minutes=60,
    )

    manager = ForcedActivationManager(config)

    # A cada decisão:
    should_force, reason, new_threshold = manager.should_force_activation(
        confidence_current=0.25,
        days_inactive=4,
        cost_accumulated=1200.0,
    )

    if should_force:
        # Log do sistema:
        print(f"⚠️ FORCED ACTIVATION TRIGGERED: {reason}")
        # Usa new_threshold (0.40) em vez de normal (0.65)
        apply_threshold = new_threshold

    # Reset após entrada (voluntária ou forçada):
    manager.record_activation_entry()
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional
import logging


logger = logging.getLogger(__name__)


class ForceActivationReason(Enum):
    """Razões para ativação forçada."""

    CONFIDENCE_CRASH = "confidence_crash"  # confidence < 0.35 AND dias >= 3
    COST_THRESHOLD_BREACH = "cost_breach"  # cost_accumulated > R$ 1k
    CONFIDENCE_DEGRADATION = "confidence_degradation"  # > 50% drop em 24h
    NONE = "none"  # Sem ativação


@dataclass
class ForcedActivationConfig:
    """Configuração do Forced Activation Manager."""

    confidence_threshold_low: Decimal = Decimal("0.35")
    """Threshold baixo de confiança para ativação."""

    days_inactive_threshold: int = 3
    """Dias de inatividade antes de forçar."""

    cost_threshold_breach: Decimal = Decimal("1000.00")
    """Custo operacional (R$) que dispara forced activation."""

    relaxed_signal_threshold: Decimal = Decimal("0.40")
    """Threshold relaxado durante forced activation (vs normal 0.65)."""

    normal_signal_threshold: Decimal = Decimal("0.65")
    """Threshold normal (baseline)."""

    activation_window_minutes: int = 60
    """Janela de ativação (minutos) — durará até próxima entrada."""

    confidence_degradation_threshold: Decimal = Decimal("0.50")
    """% de degradação confiança em 24h que dispara."""


@dataclass
class ForcedActivationMetrics:
    """Métricas de ativação forçada."""

    should_activate: bool = False
    """Deve ativar agora?"""

    activation_reason: ForceActivationReason = ForceActivationReason.NONE
    """Por que ativar?"""

    new_threshold: Decimal = Decimal("0.65")
    """Novo threshold a aplicar."""

    message: str = ""
    """Mensagem descritiva."""

    confidence_delta: Decimal = Decimal("0.00")
    """Mudança de confiança esperada após ativação."""

    activation_count: int = 0
    """Número de vezes que foi ativado nesta sessão."""

    last_activation_time: Optional[datetime] = None
    """Timestamp da última ativação."""


@dataclass
class ForcedActivationStats:
    """Estatísticas de sessão para análise."""

    total_activations: int = 0
    """Total de vezes ativado."""

    activations_by_reason: dict = field(default_factory=dict)
    """Quebra: { reason_name → count }"""

    trades_during_activation: int = 0
    """Trades executados durante janela de ativação."""

    trades_forced_duration: int = 0
    """Trades durante período forçado."""

    win_rate_forced_trades: Decimal = Decimal("0.00")
    """% vitórias em trades forçados."""

    win_rate_normal_trades: Decimal = Decimal("0.00")
    """% vitórias em trades normais (para comparação)."""


class ForcedActivationManager:
    """
    Gerenciador de Ativação Forçada (P0-URGENT-2).

    Monitora condições que indicam "paralisia de confiança" e força
    o modelo a tentar trades para evitar collapse.
    """

    def __init__(self, config: ForcedActivationConfig):
        """Inicializa manager."""
        self.config = config

        # Rastreamento de sessão
        self._session_start: Optional[datetime] = None
        self._activation_active: bool = False
        self._activation_start_time: Optional[datetime] = None
        self._last_entry_time: Optional[datetime] = None
        self._last_confidence: Decimal = Decimal("0.75")  # Baseline
        self._confidence_at_24h_ago: Optional[Decimal] = None

        # Histórico
        self._activation_history: list = []
        self._activation_counts: dict = {}  # reason → count
        self._forced_trade_count: int = 0

        # Anti-spam logging
        self._last_log_reason: Optional[ForceActivationReason] = None
        self._last_log_time: Optional[datetime] = None

    def start_session(self, session_start: datetime = None) -> None:
        """Inicia sessão de monitoramento."""
        self._session_start = session_start or datetime.now()
        self._activation_active = False
        self._last_entry_time = None
        self._last_confidence = Decimal("0.75")
        logger.info(f"Forced Activation Manager: Sessão iniciada")

    def should_force_activation(
        self,
        confidence_current: Decimal,
        days_inactive: int,
        cost_accumulated: Decimal,
        confidence_24h_ago: Optional[Decimal] = None,
    ) -> tuple[bool, ForceActivationReason, Decimal]:
        """
        Verifica se deve ativar forced activation.

        Returns:
            (should_activate, reason, new_threshold)
        """
        self._last_confidence = confidence_current

        # Se já está em janela de ativação, continua até timeout
        if self._activation_active:
            time_since_activation = (datetime.now() - self._activation_start_time).total_seconds() / 60
            if time_since_activation < self.config.activation_window_minutes:
                # Ainda dentro da janela
                return (
                    True,
                    ForceActivationReason.NONE,  # Já foi ativado antes
                    self.config.relaxed_signal_threshold,
                )
            else:
                # Expirou janela
                self._activation_active = False
                self._activation_start_time = None

        # Avalia condições de ativação
        reason = ForceActivationReason.NONE
        should_activate = False

        # AC2: Confidence crash + inatividade prolongada
        if (
            confidence_current < self.config.confidence_threshold_low
            and days_inactive >= self.config.days_inactive_threshold
        ):
            reason = ForceActivationReason.CONFIDENCE_CRASH
            should_activate = True

        # AC3: Custo operacional breached
        if cost_accumulated > self.config.cost_threshold_breach:
            reason = ForceActivationReason.COST_THRESHOLD_BREACH
            should_activate = True

        # AC AC5: Degradação de confiança em 24h
        if confidence_24h_ago is not None:
            degradation = (
                (self._last_confidence - confidence_24h_ago) / confidence_24h_ago
                if confidence_24h_ago > 0
                else Decimal("0")
            )
            if degradation > self.config.confidence_degradation_threshold:
                reason = ForceActivationReason.CONFIDENCE_DEGRADATION
                should_activate = True

        # Se ativando, registra
        if should_activate:
            self._activate_forced(reason, confidence_current, cost_accumulated)

        new_threshold = (
            self.config.relaxed_signal_threshold
            if should_activate
            else self.config.normal_signal_threshold
        )

        return should_activate, reason, new_threshold

    def _activate_forced(
        self,
        reason: ForceActivationReason,
        confidence: Decimal,
        cost: Decimal,
    ) -> None:
        """Registra ativação forçada."""
        now = datetime.now()

        # Anti-spam: máximo 1 ativação por minuto
        if self._last_log_reason == reason and self._last_log_time is not None:
            if (now - self._last_log_time).total_seconds() < 60:
                return  # Silencia spam

        self._activation_active = True
        self._activation_start_time = now
        self._last_log_time = now
        self._last_log_reason = reason

        # Contagem
        if reason not in self._activation_counts:
            self._activation_counts[reason] = 0
        self._activation_counts[reason] += 1
        total = sum(self._activation_counts.values())

        # Log
        message = (
            f"⚠️ FORCED ACTIVATION TRIGGERED #{total}: {reason.value} | "
            f"Confidence: {float(confidence):.0%} | "
            f"Cost accumulated: R$ {float(cost):.0f}"
        )
        logger.warning(message)
        self._activation_history.append({
            "timestamp": now,
            "reason": reason.value,
            "confidence": confidence,
            "cost": cost,
            "message": message,
        })

    def record_activation_entry(
        self,
        is_forced: bool = False,
    ) -> None:
        """Registra entrada (voluntária ou forçada) durante ativação."""
        now = datetime.now()
        self._last_entry_time = now

        # Se estava em période forçado, conta como trade forçado
        if self._activation_active and is_forced:
            self._forced_trade_count += 1

        # Reseta ativação após primeira entrada
        self._activation_active = False
        self._activation_start_time = None

        logger.info(
            f"Entry recorded during forced activation window: "
            f"is_forced={is_forced} | trades_forced={self._forced_trade_count}"
        )

    def get_activation_stats(self) -> ForcedActivationStats:
        """Retorna estatísticas de sessão."""
        return ForcedActivationStats(
            total_activations=sum(self._activation_counts.values()),
            activations_by_reason={
                k.value: v for k, v in self._activation_counts.items()
            },
            trades_during_activation=self._forced_trade_count,
            trades_forced_duration=self._forced_trade_count,
        )

    def get_status(self) -> dict:
        """Status atual para debug/logging."""
        return {
            "session_active": self._session_start is not None,
            "activation_active": self._activation_active,
            "last_confidence": float(self._last_confidence),
            "total_activations": sum(self._activation_counts.values()),
            "trades_forced": self._forced_trade_count,
            "activation_counts": {
                k.value: v for k, v in self._activation_counts.items()
            },
        }
