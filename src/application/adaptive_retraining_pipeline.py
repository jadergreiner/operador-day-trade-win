"""
Pipeline adaptativo para decidir quando retreinar modelos.

O modulo consolida sinais de degradacao de performance, drift e vies
direcional para produzir um diagnostico estruturado e um plano de
retreinamento com prioridade.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Iterable, Mapping


class TriggerPriority(str, Enum):
    """Prioridade operacional do retrain."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    NONE = "none"


class TriggerSeverity(str, Enum):
    """Severidade agregada do diagnostico."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class AdaptiveRetrainingPolicy:
    """Parametros configuraveis do pipeline adaptativo."""

    max_win_rate_drop_pct: float = 5.0
    max_f1_drop_pct: float = 0.05
    min_sharpe: float = 0.8
    max_drift_score: float = 0.5
    max_bias_imbalance_pct: float = 60.0
    high_bias_level: str = "alto"
    medium_bias_level: str = "moderado"
    high_priority_reasons: tuple[str, ...] = (
        "performance_critical",
        "drift_critical",
        "bias_critical",
    )


@dataclass(frozen=True)
class TriggerEvaluation:
    """Resultado estruturado da avaliacao do gatilho."""

    trigger: bool
    reasons: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    severity: TriggerSeverity = TriggerSeverity.LOW
    priority: TriggerPriority = TriggerPriority.NONE
    evaluated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Converte a avaliacao para um dicionario serializavel."""
        payload = asdict(self)
        payload["severity"] = self.severity.value
        payload["priority"] = self.priority.value
        payload["evaluated_at"] = self.evaluated_at.isoformat()
        return payload


@dataclass(frozen=True)
class RetrainingPlan:
    """Plano de retreinamento derivado da avaliacao."""

    scheduled: bool
    priority: TriggerPriority
    recommended_window: str
    reasons: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    trigger: TriggerEvaluation | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Converte o plano para um dicionario serializavel."""
        payload = asdict(self)
        payload["priority"] = self.priority.value
        payload["created_at"] = self.created_at.isoformat()
        if self.trigger is not None:
            payload["trigger"] = self.trigger.to_dict()
        return payload


class AdaptiveRetrainingPipeline:
    """
    Pipeline adaptativo inicial para decidir quando retreinar.

    A estrategia combina tres familias de sinais:
    - performance: queda de win rate, F1 ou Sharpe
    - drift: score de drift acima do limiar
    - vies: concentracao direcional ou nivel de vies elevado
    """

    def __init__(self, policy: AdaptiveRetrainingPolicy | None = None) -> None:
        self.policy = policy or AdaptiveRetrainingPolicy()

    def evaluate_trigger(self, metrics: Mapping[str, Any]) -> dict[str, Any]:
        """
        Avalia se ha gatilho para retreinamento.

        A entrada pode ser plana ou aninhada. Exemplos aceitos:
        - {"current_win_rate": 0.58, "baseline_win_rate": 0.65}
        - {"current_metrics": {"win_rate": 0.58}, "baseline": {"win_rate": 0.65}}
        """
        current = self._resolve_metrics(metrics, "current")
        baseline = self._resolve_metrics(metrics, "baseline")
        signal_metrics = {**dict(metrics), **current}

        reasons: list[str] = []
        categories: list[str] = []
        severity_score = 0

        performance_reasons = self._evaluate_performance(current, baseline)
        if performance_reasons:
            reasons.extend(performance_reasons)
            categories.append("performance")
            severity_score += 1 if len(performance_reasons) == 1 else 2

        drift_reasons = self._evaluate_drift(signal_metrics)
        if drift_reasons:
            reasons.extend(drift_reasons)
            categories.append("drift")
            severity_score += 2 if any("critical" in reason for reason in drift_reasons) else 1

        bias_reasons = self._evaluate_bias(signal_metrics)
        if bias_reasons:
            reasons.extend(bias_reasons)
            categories.append("bias")
            severity_score += 2 if any("critical" in reason for reason in bias_reasons) else 1

        trigger = bool(reasons)
        severity = self._resolve_severity(severity_score, trigger)
        priority = self._resolve_priority(severity, categories, reasons)

        evaluation = TriggerEvaluation(
            trigger=trigger,
            reasons=reasons,
            categories=categories,
            severity=severity,
            priority=priority,
        )
        return evaluation.to_dict()

    def schedule_retraining(self, metrics: Mapping[str, Any]) -> dict[str, Any]:
        """
        Gera um plano de retreinamento com prioridade.

        Quando nao ha gatilho, o plano e retornado como nao agendado.
        """
        evaluation = self.evaluate_trigger(metrics)
        priority = TriggerPriority(evaluation["priority"])
        scheduled = bool(evaluation["trigger"])
        recommended_window = "off_peak" if scheduled else "none"
        actions = self._build_actions(evaluation["categories"], scheduled)

        plan = RetrainingPlan(
            scheduled=scheduled,
            priority=priority,
            recommended_window=recommended_window,
            reasons=list(evaluation["reasons"]),
            actions=actions,
            trigger=TriggerEvaluation(
                trigger=evaluation["trigger"],
                reasons=list(evaluation["reasons"]),
                categories=list(evaluation["categories"]),
                severity=TriggerSeverity(evaluation["severity"]),
                priority=priority,
                evaluated_at=datetime.fromisoformat(evaluation["evaluated_at"]),
            ),
        )
        return plan.to_dict()

    def _resolve_metrics(
        self,
        metrics: Mapping[str, Any],
        scope: str,
    ) -> dict[str, Any]:
        if scope not in {"current", "baseline"}:
            raise ValueError("scope invalido")

        aliases = {
            "current": ("current_metrics", "current", "metrics_atual", "atual"),
            "baseline": ("baseline_metrics", "baseline", "reference_metrics"),
        }
        candidate = self._find_first_mapping(metrics, aliases[scope])
        if candidate is not None:
            return dict(candidate)

        return dict(metrics)

    def _find_first_mapping(
        self,
        metrics: Mapping[str, Any],
        keys: Iterable[str],
    ) -> Mapping[str, Any] | None:
        for key in keys:
            value = metrics.get(key)
            if isinstance(value, Mapping):
                return value
        return None

    def _evaluate_performance(
        self,
        current: Mapping[str, Any],
        baseline: Mapping[str, Any],
    ) -> list[str]:
        reasons: list[str] = []

        current_win_rate = self._coerce_float(current, "win_rate", "current_win_rate")
        baseline_win_rate = self._coerce_float(
            baseline,
            "win_rate",
            "baseline_win_rate",
        )
        if current_win_rate is not None and baseline_win_rate is not None:
            drop_pct = (baseline_win_rate - current_win_rate) * 100.0
            if drop_pct > self.policy.max_win_rate_drop_pct:
                reasons.append(
                    f"performance_drop_win_rate:{drop_pct:.2f}"
                )

        current_f1 = self._coerce_float(current, "f1_score", "current_f1")
        baseline_f1 = self._coerce_float(baseline, "f1_score", "baseline_f1")
        if current_f1 is not None and baseline_f1 is not None:
            drop_abs = baseline_f1 - current_f1
            if drop_abs > self.policy.max_f1_drop_pct:
                reasons.append(f"performance_drop_f1:{drop_abs:.4f}")

        current_sharpe = self._coerce_float(
            current,
            "sharpe_ratio",
            "sharpe",
            "current_sharpe",
        )
        if current_sharpe is not None and current_sharpe < self.policy.min_sharpe:
            reasons.append(f"performance_sharpe_below_min:{current_sharpe:.4f}")

        return reasons

    def _evaluate_drift(self, metrics: Mapping[str, Any]) -> list[str]:
        reasons: list[str] = []
        drift_score = self._coerce_float(
            metrics,
            "drift_score",
            "drift",
            "drift_value",
        )
        if drift_score is not None and drift_score > self.policy.max_drift_score:
            if drift_score >= self.policy.max_drift_score * 1.5:
                reasons.append(f"drift_critical:{drift_score:.4f}")
            else:
                reasons.append(f"drift_warning:{drift_score:.4f}")
        return reasons

    def _evaluate_bias(self, metrics: Mapping[str, Any]) -> list[str]:
        reasons: list[str] = []
        imbalance_pct = self._coerce_float(
            metrics,
            "directional_imbalance_pct",
            "bias_imbalance_pct",
            "imbalance_pct",
        )
        if imbalance_pct is not None and imbalance_pct > self.policy.max_bias_imbalance_pct:
            reasons.append(f"bias_critical:{imbalance_pct:.2f}")
            return reasons

        bias_level = self._coerce_str(metrics, "bias_level", "directional_bias_level")
        if bias_level is not None:
            normalized = bias_level.strip().lower()
            if normalized == self.policy.high_bias_level:
                reasons.append(f"bias_critical:{normalized}")
            elif normalized == self.policy.medium_bias_level:
                reasons.append(f"bias_warning:{normalized}")

        return reasons

    def _resolve_severity(self, score: int, trigger: bool) -> TriggerSeverity:
        if not trigger:
            return TriggerSeverity.LOW
        if score >= 4:
            return TriggerSeverity.HIGH
        if score >= 2:
            return TriggerSeverity.MEDIUM
        return TriggerSeverity.LOW

    def _resolve_priority(
        self,
        severity: TriggerSeverity,
        categories: list[str],
        reasons: list[str],
    ) -> TriggerPriority:
        if not reasons:
            return TriggerPriority.NONE
        if severity == TriggerSeverity.HIGH:
            return TriggerPriority.HIGH
        if severity == TriggerSeverity.MEDIUM:
            return TriggerPriority.MEDIUM
        if len(categories) >= 2:
            return TriggerPriority.MEDIUM
        return TriggerPriority.LOW

    def _build_actions(self, categories: list[str], scheduled: bool) -> list[str]:
        if not scheduled:
            return []

        actions = ["gerar_plano_retrain", "reservar_janela_off_peak"]
        if "performance" in categories:
            actions.append("revisar_metricas_modelo")
        if "drift" in categories:
            actions.append("validar_drift_com_baseline")
        if "bias" in categories:
            actions.append("auditar_vies_direcional")
        return actions

    def _coerce_float(self, metrics: Mapping[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = metrics.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return None

    def _coerce_str(self, metrics: Mapping[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = metrics.get(key)
            if value is None:
                continue
            return str(value)
        return None
