"""Bridge runtime entre storytelling diario e MLOps."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Mapping

from src.application.adaptive_retraining_pipeline import AdaptiveRetrainingPipeline
from src.application.market_regime_adapter import MarketRegimeAdapter
from src.application.order_manager_learner import OrderManagerLearner
from src.application.universal_kill_switch import UniversalKillSwitch


def _safe_mapping(source: Any) -> dict[str, Any]:
    """Normaliza um mapping ou objeto para dict."""
    if source is None:
        return {}
    if isinstance(source, Mapping):
        return dict(source)
    if is_dataclass(source):
        return asdict(source)
    if hasattr(source, "__dict__"):
        return {
            key: value
            for key, value in vars(source).items()
            if not key.startswith("_")
        }
    return {}


def _first_value(source: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    """Retorna o primeiro valor util encontrado."""
    for name in names:
        if name in source and source[name] is not None:
            return source[name]
    return default


def _to_float(value: Any, default: float | None = None) -> float | None:
    """Converte valor para float de forma segura."""
    if value is None:
        return default
    try:
        coerced = float(value)
    except (TypeError, ValueError):
        return default
    if coerced != coerced:
        return default
    return coerced


def _to_bool(value: Any) -> bool:
    """Converte valor para bool com tolerancia a texto."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "f", "no", "n", "off", ""}:
            return False
    return bool(value)


def _normalize_text(value: Any, default: str = "") -> str:
    """Converte valor para texto simples."""
    if value is None:
        return default
    return str(value)


class DiarioRuntimeMlOpsBridge:
    """Bridge reutilizavel entre diario e rotinas de MLOps."""

    def __init__(
        self,
        *,
        retraining_pipeline: AdaptiveRetrainingPipeline | None = None,
        market_regime_adapter: MarketRegimeAdapter | None = None,
        kill_switch: UniversalKillSwitch | None = None,
        order_manager_learner: OrderManagerLearner | None = None,
    ) -> None:
        self.retraining_pipeline = retraining_pipeline or AdaptiveRetrainingPipeline()
        self.market_regime_adapter = market_regime_adapter or MarketRegimeAdapter()
        self.kill_switch = kill_switch or UniversalKillSwitch()
        self.order_manager_learner = order_manager_learner or OrderManagerLearner()

    def process_cycle(self, input_dict: Mapping[str, Any] | None) -> dict[str, Any]:
        """Processa um ciclo diario e retorna payload serializavel."""
        payload = _safe_mapping(input_dict)
        perf = _safe_mapping(payload.get("perf"))
        coherence = _safe_mapping(payload.get("coherence"))
        dir_analysis = _safe_mapping(payload.get("dir_analysis"))
        guardian_state = payload.get("guardian_state")
        guardian = _safe_mapping(guardian_state)
        order_history = list(payload.get("order_history") or [])
        execution_patterns = self._normalize_execution_patterns(
            payload.get("execution_patterns")
        )

        regime_metrics = self._build_regime_metrics(perf, coherence, dir_analysis)
        regime = self.market_regime_adapter.recommend(regime_metrics).to_dict()

        retraining_metrics = self._build_retraining_metrics(
            perf=perf,
            coherence=coherence,
            dir_analysis=dir_analysis,
            regime=regime,
        )
        retraining_trigger = self.retraining_pipeline.evaluate_trigger(retraining_metrics)
        retraining_plan = self.retraining_pipeline.schedule_retraining(retraining_metrics)

        kill_switch_events = self._build_kill_switch_events(
            guardian=guardian,
            perf=perf,
            coherence=coherence,
            dir_analysis=dir_analysis,
        )
        kill_switch = self.kill_switch.evaluate(kill_switch_events).to_dict()

        execution_recommendation = self.order_manager_learner.recommend(
            order_history,
            execution_patterns or None,
        ).to_dict()

        summary = self._build_summary(
            regime=regime,
            retraining_trigger=retraining_trigger,
            retraining_plan=retraining_plan,
            kill_switch=kill_switch,
            execution_recommendation=execution_recommendation,
        )

        return {
            "regime": regime,
            "retraining_trigger": retraining_trigger,
            "retraining_plan": retraining_plan,
            "kill_switch": kill_switch,
            "execution_recommendation": execution_recommendation,
            "summary": summary,
        }

    def _build_regime_metrics(
        self,
        perf: Mapping[str, Any],
        coherence: Mapping[str, Any],
        dir_analysis: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Coleta proxies para classificacao de regime."""
        sources = (perf, coherence, dir_analysis)
        trend_strength = self._pick_numeric(
            sources,
            "trend_strength",
            "trend_score",
            "trend",
            "directional_bias",
            "bias_strength",
        )
        directional_bias = self._pick_numeric(
            sources,
            "directional_bias",
            "bias",
            "macro_bias_score",
        )
        volatility = self._pick_numeric(
            sources,
            "volatility",
            "market_volatility",
            "volatility_pct",
            "atr_percent",
            "atr",
        )
        adx = self._pick_numeric(sources, "adx", "adx_medio")
        atr_percent = self._pick_numeric(
            sources,
            "atr_percent",
            "atr_pct",
            "atr",
        )
        range_compression = self._pick_numeric(
            sources,
            "range_compression",
            "compression_pct",
            "compression",
        )

        metrics: dict[str, Any] = {
            "trend_strength": trend_strength,
            "directional_bias": directional_bias,
            "volatility": volatility,
            "adx": adx,
            "atr_percent": atr_percent,
            "range_compression": range_compression,
        }

        return {key: value for key, value in metrics.items() if value is not None}

    def _build_retraining_metrics(
        self,
        *,
        perf: Mapping[str, Any],
        coherence: Mapping[str, Any],
        dir_analysis: Mapping[str, Any],
        regime: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Monta metricas para avaliacao de retreino."""
        current_metrics = {
            "win_rate": self._pick_numeric((perf,), "win_rate", "current_win_rate"),
            "f1_score": self._pick_numeric((perf,), "f1_score", "current_f1"),
            "sharpe_ratio": self._pick_numeric((perf,), "sharpe_ratio", "sharpe", "current_sharpe"),
            "drift_score": self._pick_numeric((perf, coherence, dir_analysis), "drift_score", "drift", "drift_value"),
            "directional_imbalance_pct": self._pick_numeric(
                (coherence, dir_analysis, perf),
                "directional_imbalance_pct",
                "imbalance_pct",
                "bias_imbalance_pct",
            ),
            "bias_level": _first_value(
                {**coherence, **dir_analysis, **perf},
                "bias_level",
                "direcional_vies",
                "directional_bias_level",
                default=None,
            ),
            "regime": regime.get("regime"),
            "regime_confidence": regime.get("confidence"),
        }
        current_metrics = {key: value for key, value in current_metrics.items() if value is not None}

        baseline_metrics = {
            "win_rate": self._pick_numeric((perf,), "baseline_win_rate"),
            "f1_score": self._pick_numeric((perf,), "baseline_f1"),
            "sharpe_ratio": self._pick_numeric((perf,), "baseline_sharpe"),
        }
        baseline_metrics = {
            key: value for key, value in baseline_metrics.items() if value is not None
        }

        if baseline_metrics:
            return {
                "current_metrics": current_metrics,
                "baseline_metrics": baseline_metrics,
                "drift_score": current_metrics.get("drift_score"),
                "directional_imbalance_pct": current_metrics.get("directional_imbalance_pct"),
                "bias_level": current_metrics.get("bias_level"),
            }

        return current_metrics

    def _build_kill_switch_events(
        self,
        *,
        guardian: Mapping[str, Any],
        perf: Mapping[str, Any],
        coherence: Mapping[str, Any],
        dir_analysis: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        """Consolida eventos de risco para o kill switch."""
        events: list[dict[str, Any]] = []

        guardian_active = _to_bool(
            _first_value(
                guardian,
                "active_kill_switch",
                "kill_switch_ativo",
                "guardian_kill_switch",
                default=False,
            )
        )
        guardian_reason = _normalize_text(
            _first_value(
                guardian,
                "kill_switch_reason",
                "guardian_kill_reason",
                "reason",
                default="",
            ),
            "",
        )
        if guardian or guardian_active or guardian_reason:
            events.append(
                {
                    "source": "guardian_state",
                    "severity": "CRITICAL" if guardian_active else "INFO",
                    "score_impacto": self._pick_numeric(
                        (guardian, perf, coherence, dir_analysis),
                        "confidence_penalty",
                        "guardian_confidence_penalty",
                        "score_impacto",
                        "risk_score",
                    ),
                    "kill_switch_ativo": guardian_active,
                    "category": "guardian",
                    "message": guardian_reason or "guardian snapshot",
                    "timestamp": _normalize_text(
                        _first_value(guardian, "timestamp", "generated_at", default=""),
                        "",
                    ),
                }
            )

        if _to_bool(_first_value(perf, "kill_switch_ativo", default=False)):
            events.append(
                {
                    "source": "perf",
                    "severity": "CRITICAL",
                    "score_impacto": self._pick_numeric((perf,), "risk_score", "score_impacto"),
                    "kill_switch_ativo": True,
                    "category": "performance",
                    "message": "perf sinalizou kill switch",
                }
            )

        if _to_bool(_first_value(coherence, "kill_switch_ativo", default=False)):
            events.append(
                {
                    "source": "coherence",
                    "severity": "CRITICAL",
                    "score_impacto": self._pick_numeric((coherence,), "risk_score", "score_impacto"),
                    "kill_switch_ativo": True,
                    "category": "coherence",
                    "message": "coherence sinalizou kill switch",
                }
            )

        if _to_bool(_first_value(dir_analysis, "kill_switch_ativo", default=False)):
            events.append(
                {
                    "source": "dir_analysis",
                    "severity": "CRITICAL",
                    "score_impacto": self._pick_numeric((dir_analysis,), "risk_score", "score_impacto"),
                    "kill_switch_ativo": True,
                    "category": "directional",
                    "message": "dir_analysis sinalizou kill switch",
                }
            )

        return events

    def _build_summary(
        self,
        *,
        regime: Mapping[str, Any],
        retraining_trigger: Mapping[str, Any],
        retraining_plan: Mapping[str, Any],
        kill_switch: Mapping[str, Any],
        execution_recommendation: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Cria um resumo curto do ciclo."""
        triggered = bool(retraining_trigger.get("trigger"))
        summary_parts = [
            f"regime={regime.get('regime', 'RANGING')}",
            f"retrain={'yes' if triggered else 'no'}",
            f"kill_switch={'active' if kill_switch.get('active') else 'inactive'}",
            f"exec_mode={execution_recommendation.get('mode', 'BALANCED')}",
        ]

        return {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "message": "; ".join(summary_parts),
            "regime": regime.get("regime", "RANGING"),
            "regime_confidence": regime.get("confidence", 0.0),
            "retraining_triggered": triggered,
            "retraining_priority": retraining_plan.get("priority", "none"),
            "kill_switch_active": bool(kill_switch.get("active")),
            "execution_mode": execution_recommendation.get("mode", "BALANCED"),
            "notes": [
                "Bridge consolidado com defaults seguros.",
            ],
        }

    def _pick_numeric(
        self,
        sources: tuple[Mapping[str, Any], ...],
        *names: str,
    ) -> float | None:
        """Busca o primeiro numero valido entre varias fontes."""
        for source in sources:
            for name in names:
                if name not in source:
                    continue
                value = _to_float(source.get(name))
                if value is not None:
                    return value
        return None

    def _normalize_execution_patterns(self, source: Any) -> dict[str, Any]:
        """Normaliza estrutura de padroes de execucao."""
        patterns = _safe_mapping(source)
        summary = patterns.get("summary")
        if summary is not None and not isinstance(summary, Mapping):
            patterns["summary"] = _safe_mapping(summary)
        return patterns


__all__ = ["DiarioRuntimeMlOpsBridge"]
