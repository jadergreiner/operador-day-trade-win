"""Analise de padroes de execucao.

O modulo observa execucoes de ordens e transforma os sinais mais simples
em insights estruturados sobre slippage, fill rate, latencia e motivos de
falha. A intencao e servir de base para aprendizagem operacional enxuta.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

DEFAULT_SLIPPAGE_ALERT_POINTS = 2.0
DEFAULT_FILL_RATE_ALERT = 0.90
DEFAULT_LATENCY_ALERT_MS = 400.0
DEFAULT_LATENCY_CRITICAL_MS = 1000.0


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


def _coerce_timestamp(value: Any) -> datetime:
    if value is None:
        return datetime.now()
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("timestamp invalido") from exc
    raise ValueError("timestamp invalido")


def _normalize_text(value: Optional[str], default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _normalize_status(value: Optional[str]) -> str:
    if not value:
        return "UNKNOWN"
    return str(value).strip().upper()


def _percentile(values: Sequence[float], percentile_rank: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * percentile_rank
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _iqr_outlier_count(values: Sequence[float]) -> int:
    if len(values) < 4:
        return 0
    q1 = _percentile(values, 0.25)
    q3 = _percentile(values, 0.75)
    iqr = q3 - q1
    if iqr <= 0:
        return 0
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return sum(1 for value in values if value < lower or value > upper)


@dataclass(frozen=True)
class ExecutionEvent:
    """Evento de execucao bruto."""

    order_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    requested_qty: float = 1.0
    filled_qty: float = 1.0
    requested_price: float = 0.0
    filled_price: Optional[float] = None
    latency_ms: float = 0.0
    side: str = "BUY"
    status: str = "FILLED"
    failure_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("order_id e obrigatorio")
        if self.requested_qty < 0:
            raise ValueError("requested_qty nao pode ser negativo")
        if self.filled_qty < 0:
            raise ValueError("filled_qty nao pode ser negativo")
        if self.latency_ms < 0:
            raise ValueError("latency_ms nao pode ser negativo")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    para_dict = to_dict

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExecutionEvent":
        if not isinstance(data, Mapping):
            raise ValueError("dados invalidos para ExecutionEvent")
        filled_price = data.get("filled_price")
        return cls(
            order_id=str(data.get("order_id", "")).strip(),
            timestamp=_coerce_timestamp(data.get("timestamp")),
            requested_qty=_coerce_float(data.get("requested_qty", 1.0), "requested_qty"),
            filled_qty=_coerce_float(data.get("filled_qty", data.get("requested_qty", 1.0)), "filled_qty"),
            requested_price=_coerce_float(data.get("requested_price", 0.0), "requested_price"),
            filled_price=None if filled_price is None else _coerce_float(filled_price, "filled_price"),
            latency_ms=_coerce_float(data.get("latency_ms", 0.0), "latency_ms"),
            side=_normalize_text(data.get("side", "BUY"), "BUY").upper(),
            status=_normalize_status(data.get("status", "FILLED")),
            failure_reason=data.get("failure_reason"),
            metadata=dict(data.get("metadata", {}) or {}),
        )


@dataclass
class ExecutionPatternInsight:
    """Insight estruturado de um padrao detectado."""

    pattern: str
    severity: str
    message: str
    evidence: Dict[str, Any]
    recommendation: str
    score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    para_dict = to_dict


@dataclass
class ExecutionPatternSummary:
    """Resumo consolidado da execucao."""

    event_count: int
    total_requested_qty: float
    total_filled_qty: float
    fill_rate: float
    avg_slippage_points: float
    median_slippage_points: float
    avg_latency_ms: float
    p95_latency_ms: float
    rejection_rate: float
    failure_reasons: Dict[str, int]
    outlier_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    para_dict = to_dict


@dataclass
class ExecutionPatternAnalysis:
    """Resultado completo da analise de padroes."""

    timestamp: datetime
    summary: ExecutionPatternSummary
    insights: List[ExecutionPatternInsight]
    patterns_detected: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "summary": self.summary.to_dict(),
            "insights": [insight.to_dict() for insight in self.insights],
            "patterns_detected": list(self.patterns_detected),
        }

    para_dict = to_dict


class ExecutionPatternAnalyzer:
    """Detecta padroes simples de execucao e produz insights."""

    def __init__(
        self,
        slippage_alert_points: float = DEFAULT_SLIPPAGE_ALERT_POINTS,
        fill_rate_alert: float = DEFAULT_FILL_RATE_ALERT,
        latency_alert_ms: float = DEFAULT_LATENCY_ALERT_MS,
        latency_critical_ms: float = DEFAULT_LATENCY_CRITICAL_MS,
    ) -> None:
        if slippage_alert_points <= 0:
            raise ValueError("slippage_alert_points deve ser > 0")
        if not (0.0 < fill_rate_alert <= 1.0):
            raise ValueError("fill_rate_alert deve estar entre 0 e 1")
        if latency_alert_ms <= 0 or latency_critical_ms <= 0:
            raise ValueError("latency thresholds devem ser > 0")
        self.slippage_alert_points = float(slippage_alert_points)
        self.fill_rate_alert = float(fill_rate_alert)
        self.latency_alert_ms = float(latency_alert_ms)
        self.latency_critical_ms = float(latency_critical_ms)

    def _coerce_event(self, event: Any) -> ExecutionEvent:
        if isinstance(event, ExecutionEvent):
            return event
        if isinstance(event, Mapping):
            return ExecutionEvent.from_dict(event)
        raise ValueError("evento de execucao invalido")

    def _adverse_slippage(self, event: ExecutionEvent) -> float:
        if event.filled_price is None:
            return 0.0
        side = str(event.side).strip().upper()
        if side == "SELL":
            return max(0.0, float(event.requested_price) - float(event.filled_price))
        return max(0.0, float(event.filled_price) - float(event.requested_price))

    def _normalize_failure_reason(self, event: ExecutionEvent) -> str:
        reason = _normalize_text(event.failure_reason, "").strip().lower()
        if reason:
            return reason
        status = _normalize_status(event.status)
        if status in {"REJECTED", "CANCELLED", "ERROR", "PARTIAL"}:
            return status.lower()
        return ""

    def analyze(self, events: Iterable[Any]) -> ExecutionPatternAnalysis:
        """Analisa uma sequencia de eventos de execucao."""
        items = [self._coerce_event(event) for event in (events or [])]
        if not items:
            summary = ExecutionPatternSummary(
                event_count=0,
                total_requested_qty=0.0,
                total_filled_qty=0.0,
                fill_rate=0.0,
                avg_slippage_points=0.0,
                median_slippage_points=0.0,
                avg_latency_ms=0.0,
                p95_latency_ms=0.0,
                rejection_rate=0.0,
                failure_reasons={},
                outlier_count=0,
            )
            return ExecutionPatternAnalysis(
                timestamp=datetime.now(),
                summary=summary,
                insights=[],
                patterns_detected=[],
            )

        filled_qty = 0.0
        requested_qty = 0.0
        latencies = []
        slippages = []
        failure_reasons: Dict[str, int] = {}
        rejected_count = 0
        for event in items:
            if event.requested_qty < 0 or event.filled_qty < 0 or event.latency_ms < 0:
                raise ValueError("valores negativos nao sao permitidos")
            qty_requested = float(event.requested_qty)
            qty_filled = min(float(event.filled_qty), qty_requested if qty_requested > 0 else float(event.filled_qty))
            requested_qty += qty_requested
            filled_qty += qty_filled
            latencies.append(float(event.latency_ms))

            slippage = self._adverse_slippage(event)
            slippages.append(slippage)

            reason = self._normalize_failure_reason(event)
            if reason:
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

            status = _normalize_status(event.status)
            if status in {"REJECTED", "CANCELLED", "ERROR"}:
                rejected_count += 1

        fill_rate = filled_qty / requested_qty if requested_qty > 0 else 0.0
        avg_slippage = mean(slippages) if slippages else 0.0
        median_slippage = median(slippages) if slippages else 0.0
        p95_slippage = _percentile(slippages, 0.95) if slippages else 0.0
        avg_latency = mean(latencies) if latencies else 0.0
        p95_latency = _percentile(latencies, 0.95)
        outlier_count = _iqr_outlier_count(latencies) + _iqr_outlier_count(slippages)
        rejection_rate = rejected_count / len(items)

        summary = ExecutionPatternSummary(
            event_count=len(items),
            total_requested_qty=requested_qty,
            total_filled_qty=filled_qty,
            fill_rate=fill_rate,
            avg_slippage_points=avg_slippage,
            median_slippage_points=median_slippage,
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            rejection_rate=rejection_rate,
            failure_reasons=failure_reasons,
            outlier_count=outlier_count,
        )

        insights: List[ExecutionPatternInsight] = []
        patterns_detected: List[str] = []

        if fill_rate < self.fill_rate_alert:
            severity = "HIGH" if fill_rate < 0.85 else "MEDIUM"
            insights.append(
                ExecutionPatternInsight(
                    pattern="LOW_FILL_RATE",
                    severity=severity,
                    message="Taxa de preenchimento abaixo do esperado.",
                    evidence={
                        "fill_rate": round(fill_rate, 4),
                        "threshold": self.fill_rate_alert,
                        "requested_qty": round(requested_qty, 4),
                        "filled_qty": round(filled_qty, 4),
                    },
                    recommendation="Reduzir agressividade, validar liquidez e considerar ordens menores.",
                    score=_clamp((self.fill_rate_alert - fill_rate) * 100.0, 0.0, 100.0),
                )
            )
            patterns_detected.append("LOW_FILL_RATE")

        if avg_slippage >= self.slippage_alert_points or p95_slippage >= self.slippage_alert_points:
            slippage_signal = max(avg_slippage, p95_slippage)
            severity = "HIGH" if slippage_signal >= self.slippage_alert_points * 1.5 else "MEDIUM"
            insights.append(
                ExecutionPatternInsight(
                    pattern="HIGH_SLIPPAGE",
                    severity=severity,
                    message="Slippage medio acima do limite desejado.",
                    evidence={
                        "avg_slippage_points": round(avg_slippage, 4),
                        "median_slippage_points": round(median_slippage, 4),
                        "p95_slippage_points": round(p95_slippage, 4),
                        "threshold": self.slippage_alert_points,
                    },
                    recommendation="Aumentar conservadorismo e revisar liquidez, horario e tamanho da ordem.",
                    score=_clamp((slippage_signal - self.slippage_alert_points) * 20.0, 0.0, 100.0),
                )
            )
            patterns_detected.append("HIGH_SLIPPAGE")

        if avg_latency >= self.latency_alert_ms or p95_latency >= self.latency_critical_ms:
            severity = "HIGH" if p95_latency >= self.latency_critical_ms else "MEDIUM"
            insights.append(
                ExecutionPatternInsight(
                    pattern="HIGH_LATENCY",
                    severity=severity,
                    message="Latencia de execucao acima do tolerado.",
                    evidence={
                        "avg_latency_ms": round(avg_latency, 4),
                        "p95_latency_ms": round(p95_latency, 4),
                        "alert_threshold_ms": self.latency_alert_ms,
                        "critical_threshold_ms": self.latency_critical_ms,
                    },
                    recommendation="Investigar fila, conectividade e rotas de envio da ordem.",
                    score=_clamp((avg_latency - self.latency_alert_ms) / max(self.latency_alert_ms, 1.0) * 100.0, 0.0, 100.0),
                )
            )
            patterns_detected.append("HIGH_LATENCY")

        if failure_reasons:
            top_reason = max(failure_reasons.items(), key=lambda item: item[1])
            insights.append(
                ExecutionPatternInsight(
                    pattern="FAILURE_REASON_CLUSTER",
                    severity="MEDIUM" if top_reason[1] == 1 else "HIGH",
                    message="Motivo de falha recorrente identificado.",
                    evidence={
                        "top_reason": top_reason[0],
                        "count": top_reason[1],
                        "all_reasons": dict(sorted(failure_reasons.items(), key=lambda item: (-item[1], item[0]))),
                    },
                    recommendation="Tratar a causa raiz do motivo recorrente antes de aumentar volume.",
                    score=min(100.0, top_reason[1] * 25.0),
                )
            )
            patterns_detected.append("FAILURE_REASON_CLUSTER")

        if outlier_count:
            insights.append(
                ExecutionPatternInsight(
                    pattern="OUTLIERS_PRESENT",
                    severity="LOW" if outlier_count < 3 else "MEDIUM",
                    message="Foram encontrados eventos fora do padrao esperado.",
                    evidence={
                        "outlier_count": outlier_count,
                        "event_count": len(items),
                    },
                    recommendation="Verificar se os outliers sao eventos reais ou problemas de integracao.",
                    score=min(100.0, outlier_count * 20.0),
                )
            )
            patterns_detected.append("OUTLIERS_PRESENT")

        return ExecutionPatternAnalysis(
            timestamp=datetime.now(),
            summary=summary,
            insights=insights,
            patterns_detected=patterns_detected,
        )

    def detect_patterns(self, events: Iterable[Any]) -> ExecutionPatternAnalysis:
        """Alias para `analyze`, mantido por legibilidade."""
        return self.analyze(events)


__all__ = [
    "DEFAULT_SLIPPAGE_ALERT_POINTS",
    "DEFAULT_FILL_RATE_ALERT",
    "DEFAULT_LATENCY_ALERT_MS",
    "DEFAULT_LATENCY_CRITICAL_MS",
    "ExecutionEvent",
    "ExecutionPatternInsight",
    "ExecutionPatternSummary",
    "ExecutionPatternAnalysis",
    "ExecutionPatternAnalyzer",
]
