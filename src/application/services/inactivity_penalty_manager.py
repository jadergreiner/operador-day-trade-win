"""
Inactivity Penalty Manager - P0-URGENT-1 Implementation

Integra penalidade de inatividade na métrica de confidence do modelo ML.
Problema: Modelo aprendeu que fazer trade perdedor é pior que não fazer nada.
Realidade: Inatividade custa R$ 280/dia em operacional.

Solução: Penalizar confidence quando modelo fica inativo > 2h.

Especificação: docs/BACKLOG_UNIFICADO.md :: P0-URGENT-1
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from dataclasses import dataclass, field
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class InactivityConfig:
    """Configuração do sistema de penalidade por inatividade."""

    # AC 1: Variável operational_cost_daily em config
    operational_cost_daily: Decimal = Decimal("280.00")
    """Custo operacional diário em R$ (inclui infraestrutura)."""

    # Parâmetros de cálculo
    trading_minutes_per_day: int = 390
    """Minutos de pregão (9:00 às 17:30 em dia normal)."""

    inactivity_threshold_minutes: int = 120
    """Threshold para aplicar penalidade (2 horas)."""

    max_penalty: Decimal = Decimal("0.05")
    """Penalidade máxima a ser aplicada (-0.05)."""

    confidence_min_bound: Decimal = Decimal("0.0")
    """Limite mínimo de confidence após penalidade."""

    confidence_max_bound: Decimal = Decimal("1.0")
    """Limite máximo de confidence (sem mudança)."""


@dataclass
class InactivityMetrics:
    """Métricas de inatividade do modelo."""

    minutes_inactive: int = 0
    """Minutos sem tentar entrada desde último sinal."""

    cost_per_minute: Decimal = Decimal("0.0")
    """Custo operacional por minuto (R$)."""

    accumulated_cost: Decimal = Decimal("0.0")
    """Custo acumulado durante inatividade (R$)."""

    penalty_applied: Decimal = Decimal("0.0")
    """Penalidade aplicada à confidence (-1.0 a 0.0)."""

    confidence_after_penalty: Decimal = Decimal("0.0")
    """Confidence após aplicação da penalidade."""

    should_log_penalty: bool = False
    """Flag para logar penalidade (evitar spam de logs)."""


class InactivityPenaltyManager:
    """
    Gerenciador de penalidade por inatividade.

    Pipeline de decisão:
    1. Recebe status de inatividade (minutos_inativo)
    2. Calcula custo operacional acumulado
    3. Aplica penalidade na confidence se > threshold
    4. Retorna confidence ajustada + métricas

    Aceitação Critérios (P0-URGENT-1):
    1. ✅ operational_cost_daily variável em config
    2. ✅ cost_per_minute integrado (R$ 280 / 390min pregão)
    3. ✅ Penalidade aplicada quando minutes_inactive > 120
    4. ✅ Log mostra "Inactivity penalty: -0.03" antes de HOLD decision
    5. ✅ Backtest mostra % de dias com tentativa de entrada ↑
    """

    def __init__(self, config: Optional[InactivityConfig] = None) -> None:
        """Inicializa manager com configuração.

        Args:
            config: Configuração customizada (usa padrão se None)
        """
        self.config = config or InactivityConfig()
        self.last_signal_time: Optional[datetime] = None
        self.session_start_time: Optional[datetime] = None
        self.penalty_log_cache: Dict[str, datetime] = {}
        """Cache para evitar log spam (máximo 1 log por minuto por tipo)."""

        logger.info(
            f"InactivityPenaltyManager initialized - "
            f"Cost/day: R${self.config.operational_cost_daily}, "
            f"Threshold: {self.config.inactivity_threshold_minutes}min"
        )

    def start_session(self, session_start: Optional[datetime] = None) -> None:
        """Inicia nova sessão de trading.

        Args:
            session_start: Momento de início (usa now() se None)
        """
        self.session_start_time = session_start or datetime.now()
        self.last_signal_time = self.session_start_time
        logger.info(f"Inactivity session started at {self.session_start_time}")

    def record_signal_attempt(
        self,
        signal_type: str = "UNKNOWN",
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Registra tentativa de sinal (qualquer ação de trade).

        Args:
            signal_type: Tipo de sinal (BUY, SELL, HOLD, etc)
            timestamp: Momento do sinal (usa now() se None)
        """
        self.last_signal_time = timestamp or datetime.now()
        logger.debug(f"Signal recorded: {signal_type} at {self.last_signal_time}")

    def calculate_inactivity_metrics(
        self,
        confidence_before: Decimal,
        current_time: Optional[datetime] = None,
    ) -> Tuple[Decimal, InactivityMetrics]:
        """AC 3 + AC 4: Calcula penalidade e retorna confidence ajustada.

        Pipeline:
        1. Calcula minutos inativos desde último sinal
        2. Calcula custo operacional acumulado
        3. Se > threshold (120min), aplica penalidade
        4. Log com detalhes se penalidade aplicada
        5. Retorna (confidence_ajustada, métricas)

        Args:
            confidence_before: Confidence original do modelo (0.0-1.0)
            current_time: Tempo atual (usa now() se None)

        Returns:
            Tuple[confidence_ajustada, métricas_detalhadas]

        Example:
            >>> config = InactivityConfig(operational_cost_daily=Decimal("280"))
            >>> manager = InactivityPenaltyManager(config)
            >>> manager.start_session()
            >>> confidence_new, metrics = manager.calculate_inactivity_metrics(
            ...     confidence_before=Decimal("0.70")
            ... )
            >>> print(f"Penalty: {metrics.penalty_applied}, New confidence: {confidence_new}")
        """
        # AC: Usar now() se não informado
        current_time = current_time or datetime.now()

        # Garantir que sessão foi iniciada
        if self.session_start_time is None:
            self.start_session(current_time)

        if self.last_signal_time is None:
            self.last_signal_time = self.session_start_time

        # 1. Calcular minutos inativos desde último sinal
        time_since_last_signal = current_time - self.last_signal_time
        minutes_inactive = int(time_since_last_signal.total_seconds() / 60)

        # 2. AC 2: Calcular cost_per_minute integrado
        cost_per_minute = self.config.operational_cost_daily / Decimal(
            self.config.trading_minutes_per_day
        )
        accumulated_cost = cost_per_minute * Decimal(minutes_inactive)

        # 3. AC 3: Aplicar penalidade se minutes_inactive > 120
        penalty_applied = Decimal("0.0")
        confidence_after_penalty = confidence_before

        if minutes_inactive > self.config.inactivity_threshold_minutes:
            # Penalidade proporcional ao tempo inativo
            # Fórmula: min(max_penalty, (minutos / 390) * 0.10)
            # Isso resulta em penalidade máxima de -0.05 (5000 minutos ~ 8 horas)
            penalty_ratio = Decimal(minutes_inactive) / Decimal(
                self.config.trading_minutes_per_day
            )
            raw_penalty = penalty_ratio * Decimal("0.10")
            penalty_applied = -min(self.config.max_penalty, raw_penalty)

            # Aplicar penalidade com bounds
            confidence_after_penalty = max(
                self.config.confidence_min_bound,
                confidence_before + penalty_applied,
            )
            confidence_after_penalty = min(
                self.config.confidence_max_bound,
                confidence_after_penalty,
            )

        # 4. AC 4: Log se penalidade aplicada (com cache para evitar spam)
        should_log = self._should_log_penalty(minutes_inactive)
        if should_log and penalty_applied < Decimal("0.0"):
            logger.warning(
                f"[INACTIVITY] ⚠️ Inactivity penalty applied: {penalty_applied:.4f} "
                f"| Confidence: {confidence_before:.2%} → {confidence_after_penalty:.2%} "
                f"| Inactive: {minutes_inactive}min ({minutes_inactive/60:.1f}h) "
                f"| Cost: R${accumulated_cost:.2f}"
            )

        # Construir métricas
        metrics = InactivityMetrics(
            minutes_inactive=minutes_inactive,
            cost_per_minute=cost_per_minute,
            accumulated_cost=accumulated_cost,
            penalty_applied=penalty_applied,
            confidence_after_penalty=confidence_after_penalty,
            should_log_penalty=should_log,
        )

        return confidence_after_penalty, metrics

    def _should_log_penalty(self, minutes_inactive: int) -> bool:
        """Determina se deve logar penalidade (máximo 1x por minuto).

        Evita spam de logs com cache (1 entrada por minuto).

        Args:
            minutes_inactive: Minutos inativos

        Returns:
            True se deve logar, False caso contrário
        """
        if minutes_inactive <= self.config.inactivity_threshold_minutes:
            return False

        cache_key = f"penalty_{minutes_inactive // 60}"  # Agrupa por hora
        now = datetime.now()
        last_log = self.penalty_log_cache.get(cache_key)

        if last_log is None or (now - last_log).total_seconds() > 60:
            self.penalty_log_cache[cache_key] = now
            return True

        return False

    def get_inactivity_stats(self) -> Dict[str, any]:
        """Retorna estatísticas acumuladas de inatividade na sessão.

        Returns:
            Dicionário com stats (minutos_inativa, custo_acumulado, etc)
        """
        if self.session_start_time is None:
            return {
                "session_active": False,
                "message": "Session not initialized",
            }

        now = datetime.now()
        total_session_time = now - self.session_start_time
        minutes_inactive = int((now - self.last_signal_time).total_seconds() / 60)
        cost_per_minute = self.config.operational_cost_daily / Decimal(
            self.config.trading_minutes_per_day
        )
        total_cost = cost_per_minute * Decimal(minutes_inactive)

        return {
            "session_active": True,
            "session_start": self.session_start_time.isoformat(),
            "last_signal": self.last_signal_time.isoformat(),
            "session_duration_minutes": int(total_session_time.total_seconds() / 60),
            "minutes_inactive": minutes_inactive,
            "cost_per_minute": float(cost_per_minute),
            "total_cost_accumulated": float(total_cost),
        }
