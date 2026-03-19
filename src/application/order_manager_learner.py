"""Aprendizado de ajustes de execucao para o Order Manager.

O learner consome historico de qualidade de episodios e padroes de
execucao para sugerir ajustes simples: modo conservador/agressivo e
multiplicadores de SL/TP.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Mapping, Optional


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _coerce_float(value: Any, field_name: str) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} deve ser numerico") from exc
    if coerced != coerced:
        raise ValueError(f"{field_name} nao pode ser NaN")
    return coerced


def _normalize_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _get_value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _extract_summary(patterns: Any) -> Dict[str, Any]:
    if patterns is None:
        return {}
    if isinstance(patterns, Mapping):
        if "summary" in patterns and isinstance(patterns["summary"], Mapping):
            return dict(patterns["summary"])
        return dict(patterns)
    summary = _get_value(patterns, "summary", None)
    if summary is None:
        return {}
    if isinstance(summary, Mapping):
        return dict(summary)
    return {
        "event_count": _get_value(summary, "event_count", 0),
        "fill_rate": _get_value(summary, "fill_rate", 0.0),
        "avg_slippage_points": _get_value(summary, "avg_slippage_points", 0.0),
        "avg_latency_ms": _get_value(summary, "avg_latency_ms", 0.0),
        "rejection_rate": _get_value(summary, "rejection_rate", 0.0),
        "failure_reasons": _get_value(summary, "failure_reasons", {}),
    }


@dataclass
class ExecutionAdjustmentRecommendation:
    """Recomendacao de ajuste de execucao."""

    mode: str
    sl_multiplier: float
    tp_multiplier: float
    confidence: float
    reasons: List[str]
    signals: Dict[str, float]
    history_size: int
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    para_dict = to_dict


class OrderManagerLearner:
    """Aprende ajustes de execucao a partir de episodios e padroes."""

    def __init__(
        self,
        base_sl_multiplier: float = 1.0,
        base_tp_multiplier: float = 1.0,
    ) -> None:
        if base_sl_multiplier <= 0:
            raise ValueError("base_sl_multiplier deve ser > 0")
        if base_tp_multiplier <= 0:
            raise ValueError("base_tp_multiplier deve ser > 0")
        self.base_sl_multiplier = float(base_sl_multiplier)
        self.base_tp_multiplier = float(base_tp_multiplier)

    def _extract_history_metrics(self, history: Iterable[Any]) -> Dict[str, Any]:
        items = list(history or [])
        if not items:
            return {
                "history_size": 0,
                "quality_scores": [],
                "fill_rates": [],
                "latencies": [],
                "slippages": [],
                "failure_count": 0,
                "win_count": 0,
                "loss_count": 0,
                "breakeven_count": 0,
            }

        quality_scores: List[float] = []
        fill_rates: List[float] = []
        latencies: List[float] = []
        slippages: List[float] = []
        failure_count = 0
        win_count = 0
        loss_count = 0
        breakeven_count = 0

        for item in items:
            if item is None:
                raise ValueError("historico contem item invalido")

            quality = _get_value(item, "quality_score", _get_value(item, "score", None))
            if quality is not None:
                quality_scores.append(_clamp(_coerce_float(quality, "quality_score"), 0.0, 100.0))

            fill_rate = _get_value(item, "fill_rate", None)
            if fill_rate is not None:
                fill_rates.append(_clamp(_coerce_float(fill_rate, "fill_rate"), 0.0, 1.0))

            latency = _get_value(item, "latency_ms", None)
            if latency is not None:
                latency_value = _coerce_float(latency, "latency_ms")
                if latency_value < 0:
                    raise ValueError("latency_ms nao pode ser negativo")
                latencies.append(latency_value)

            slippage = _get_value(item, "slippage_points", None)
            if slippage is not None:
                slippages.append(abs(_coerce_float(slippage, "slippage_points")))

            failure_reason = _normalize_text(_get_value(item, "failure_reason", ""), "").strip().lower()
            status = _normalize_text(_get_value(item, "status", ""), "").strip().upper()
            outcome = _normalize_text(_get_value(item, "outcome", ""), "").strip().upper()
            if failure_reason or status in {"REJECTED", "CANCELLED", "ERROR"}:
                failure_count += 1
            if outcome == "WIN":
                win_count += 1
            elif outcome == "LOSS":
                loss_count += 1
            elif outcome == "BREAKEVEN":
                breakeven_count += 1

        return {
            "history_size": len(items),
            "quality_scores": quality_scores,
            "fill_rates": fill_rates,
            "latencies": latencies,
            "slippages": slippages,
            "failure_count": failure_count,
            "win_count": win_count,
            "loss_count": loss_count,
            "breakeven_count": breakeven_count,
        }

    def recommend(self, history: Iterable[Any], patterns: Any = None) -> ExecutionAdjustmentRecommendation:
        """Gera recomendacao de ajuste de execucao."""
        metrics = self._extract_history_metrics(history)
        summary = _extract_summary(patterns)

        history_size = int(metrics["history_size"])
        quality_scores = metrics["quality_scores"]
        fill_rates = metrics["fill_rates"]
        latencies = metrics["latencies"]
        slippages = metrics["slippages"]
        failure_count = int(metrics["failure_count"])

        pattern_event_count = int(summary.get("event_count", 0) or 0)
        effective_samples = max(history_size, pattern_event_count)

        avg_quality = mean(quality_scores) if quality_scores else 0.0
        avg_fill_rate = (
            float(summary.get("fill_rate"))
            if "fill_rate" in summary
            else (mean(fill_rates) if fill_rates else 0.0)
        )
        avg_latency = (
            float(summary.get("avg_latency_ms"))
            if "avg_latency_ms" in summary
            else (mean(latencies) if latencies else 0.0)
        )
        avg_slippage = (
            float(summary.get("avg_slippage_points"))
            if "avg_slippage_points" in summary
            else (mean(slippages) if slippages else 0.0)
        )
        rejection_rate = float(summary.get("rejection_rate", 0.0) or 0.0)
        failure_reasons = summary.get("failure_reasons", {}) or {}
        top_failure_reason = None
        if isinstance(failure_reasons, Mapping) and failure_reasons:
            top_failure_reason = max(
                ((str(key), int(value)) for key, value in failure_reasons.items()),
                key=lambda item: item[1],
            )

        if effective_samples == 0 and not summary:
            return ExecutionAdjustmentRecommendation(
                mode="BALANCED",
                sl_multiplier=self.base_sl_multiplier,
                tp_multiplier=self.base_tp_multiplier,
                confidence=0.0,
                reasons=["Historico vazio, mantendo configuracao neutra."],
                signals={
                    "history_size": 0.0,
                    "avg_quality": 0.0,
                    "fill_rate": 0.0,
                    "avg_slippage_points": 0.0,
                    "avg_latency_ms": 0.0,
                    "rejection_rate": 0.0,
                },
                history_size=0,
            )

        conservative_points = 0
        aggressive_points = 0

        if avg_fill_rate < 0.90:
            conservative_points += 1
        if avg_slippage > 2.0:
            conservative_points += 1
        if avg_latency > 400.0:
            conservative_points += 1
        if rejection_rate > 0.10:
            conservative_points += 1
        if avg_quality and avg_quality < 60.0:
            conservative_points += 1
        if failure_count > max(1, effective_samples // 6):
            conservative_points += 1

        if avg_fill_rate >= 0.97:
            aggressive_points += 1
        if avg_slippage <= 1.0:
            aggressive_points += 1
        if avg_latency <= 250.0:
            aggressive_points += 1
        if rejection_rate < 0.05:
            aggressive_points += 1
        if avg_quality >= 75.0:
            aggressive_points += 1
        if failure_count == 0:
            aggressive_points += 1

        if conservative_points >= 3 and conservative_points > aggressive_points:
            mode = "CONSERVATIVE"
        elif aggressive_points >= 4 and aggressive_points >= conservative_points:
            mode = "AGGRESSIVE"
        else:
            mode = "BALANCED"

        reasons: List[str] = []
        if avg_fill_rate < 0.90:
            reasons.append(f"Fill rate baixo ({avg_fill_rate:.2%}).")
        if avg_slippage > 2.0:
            reasons.append(f"Slippage alto ({avg_slippage:.2f} pts).")
        if avg_latency > 400.0:
            reasons.append(f"Latencia acima do alvo ({avg_latency:.1f} ms).")
        if rejection_rate > 0.10:
            reasons.append(f"Rejeicoes recorrentes ({rejection_rate:.2%}).")
        if top_failure_reason:
            reasons.append(f"Motivo predominante: {top_failure_reason[0]} ({top_failure_reason[1]}x).")
        if not reasons:
            reasons.append("Historico consistente com a configuracao atual.")

        if mode == "CONSERVATIVE":
            sl_multiplier = self.base_sl_multiplier * _clamp(
                1.10 + min(0.25, (avg_slippage / 20.0) + (rejection_rate * 0.5) + max(0.0, 0.90 - avg_fill_rate)),
                1.05,
                1.50,
            )
            tp_multiplier = self.base_tp_multiplier * _clamp(
                0.95 - min(0.20, (rejection_rate * 0.4) + (avg_latency / 3000.0)),
                0.70,
                1.00,
            )
        elif mode == "AGGRESSIVE":
            quality_bonus = _clamp((avg_quality - 70.0) / 200.0, 0.0, 0.15)
            fill_bonus = _clamp((avg_fill_rate - 0.95) * 0.6, 0.0, 0.10)
            sl_multiplier = self.base_sl_multiplier * _clamp(0.95 - quality_bonus, 0.75, 1.00)
            tp_multiplier = self.base_tp_multiplier * _clamp(1.05 + quality_bonus + fill_bonus, 1.00, 1.35)
        else:
            sl_adjustment = _clamp((avg_slippage - 1.0) / 50.0, -0.05, 0.05)
            tp_adjustment = _clamp((avg_quality - 60.0) / 500.0, -0.03, 0.08)
            sl_multiplier = self.base_sl_multiplier * (1.0 + sl_adjustment)
            tp_multiplier = self.base_tp_multiplier * (1.0 + tp_adjustment)

        sample_factor = _clamp(effective_samples / 5.0, 0.0, 1.0)
        spread_factor = 1.0 - _clamp((abs(avg_slippage) / 10.0) + abs(avg_fill_rate - 0.95) + (avg_latency / 2000.0), 0.0, 1.0)
        consistency = 1.0
        if quality_scores:
            deviation = pstdev(quality_scores) if len(quality_scores) > 1 else 0.0
            consistency = 1.0 - _clamp(deviation / 40.0, 0.0, 1.0)
        confidence = _clamp(0.25 + 0.75 * sample_factor * _clamp((spread_factor + consistency) / 2.0, 0.0, 1.0), 0.0, 1.0)

        return ExecutionAdjustmentRecommendation(
            mode=mode,
            sl_multiplier=round(sl_multiplier, 4),
            tp_multiplier=round(tp_multiplier, 4),
            confidence=round(confidence, 4),
            reasons=reasons,
            signals={
                "history_size": float(history_size),
                "avg_quality": round(avg_quality, 4),
                "fill_rate": round(avg_fill_rate, 4),
                "avg_slippage_points": round(avg_slippage, 4),
                "avg_latency_ms": round(avg_latency, 4),
                "rejection_rate": round(rejection_rate, 4),
                "failure_count": float(failure_count),
                "conservative_points": float(conservative_points),
                "aggressive_points": float(aggressive_points),
            },
            history_size=history_size,
        )

    def recommend_adjustments(self, history: Iterable[Any], patterns: Any = None) -> ExecutionAdjustmentRecommendation:
        """Alias para `recommend`."""
        return self.recommend(history, patterns)


__all__ = [
    "ExecutionAdjustmentRecommendation",
    "OrderManagerLearner",
]
