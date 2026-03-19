"""Scoring de qualidade por episodio para aprendizagem de execucao.

O objetivo deste modulo e transformar dados brutos de execucao em um score
simples, deterministico e facilmente serializavel, tanto para um episodio
isolado quanto para um lote de episodios.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

QUALITY_SCORE_MIN = 0.0
QUALITY_SCORE_MAX = 100.0
DEFAULT_LATENCY_CEILING_MS = 1000.0
DEFAULT_SLIPPAGE_CEILING_POINTS = 10.0


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _coerce_float(value: Any, field_name: str) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} deve ser numerico") from exc
    if coerced != coerced:  # NaN
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


def _normalize_status(value: Optional[str]) -> str:
    if not value:
        return "UNKNOWN"
    return str(value).strip().upper()


def _normalize_outcome(value: Optional[str]) -> str:
    if not value:
        return "UNKNOWN"
    return str(value).strip().upper()


def _normalize_failure_reason(value: Optional[str]) -> str:
    if not value:
        return ""
    return str(value).strip().lower()


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


@dataclass(frozen=True)
class EpisodeQualityInput:
    """Entrada normalizada para o score de qualidade do episodio."""

    episode_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    requested_qty: float = 1.0
    filled_qty: float = 1.0
    slippage_points: float = 0.0
    latency_ms: float = 0.0
    confidence: float = 0.0
    status: str = "FILLED"
    failure_reason: Optional[str] = None
    outcome: Optional[str] = None
    pnl_points: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.episode_id:
            raise ValueError("episode_id e obrigatorio")
        if self.requested_qty < 0:
            raise ValueError("requested_qty nao pode ser negativo")
        if self.filled_qty < 0:
            raise ValueError("filled_qty nao pode ser negativo")
        if self.latency_ms < 0:
            raise ValueError("latency_ms nao pode ser negativo")
        if self.confidence < 0:
            raise ValueError("confidence nao pode ser negativo")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    para_dict = to_dict

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EpisodeQualityInput":
        if not isinstance(data, Mapping):
            raise ValueError("dados invalidos para EpisodeQualityInput")
        return cls(
            episode_id=str(data.get("episode_id", "")).strip(),
            timestamp=_coerce_timestamp(data.get("timestamp")),
            requested_qty=_coerce_float(data.get("requested_qty", 1.0), "requested_qty"),
            filled_qty=_coerce_float(data.get("filled_qty", data.get("requested_qty", 1.0)), "filled_qty"),
            slippage_points=_coerce_float(data.get("slippage_points", 0.0), "slippage_points"),
            latency_ms=_coerce_float(data.get("latency_ms", 0.0), "latency_ms"),
            confidence=_coerce_float(data.get("confidence", 0.0), "confidence"),
            status=_normalize_status(data.get("status", "FILLED")),
            failure_reason=data.get("failure_reason"),
            outcome=data.get("outcome"),
            pnl_points=_coerce_float(data.get("pnl_points", 0.0), "pnl_points"),
            metadata=dict(data.get("metadata", {}) or {}),
        )


@dataclass
class EpisodeQualityScore:
    """Score detalhado de um episodio individual."""

    episode_id: str
    timestamp: datetime
    requested_qty: float
    filled_qty: float
    latency_ms: float
    slippage_points: float
    quality_score: float
    fill_rate: float
    latency_score: float
    slippage_score: float
    confidence_score: float
    outcome_score: float
    pnl_score: float
    status: str
    failure_reason: str
    outcome: str
    component_scores: Dict[str, float]
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    para_dict = to_dict

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EpisodeQualityScore":
        if not isinstance(data, Mapping):
            raise ValueError("dados invalidos para EpisodeQualityScore")
        return cls(
            episode_id=str(data.get("episode_id", "")).strip(),
            timestamp=_coerce_timestamp(data.get("timestamp")),
            requested_qty=_coerce_float(data.get("requested_qty", 0.0), "requested_qty"),
            filled_qty=_coerce_float(data.get("filled_qty", 0.0), "filled_qty"),
            latency_ms=_coerce_float(data.get("latency_ms", 0.0), "latency_ms"),
            slippage_points=_coerce_float(data.get("slippage_points", 0.0), "slippage_points"),
            quality_score=_coerce_float(data.get("quality_score", 0.0), "quality_score"),
            fill_rate=_coerce_float(data.get("fill_rate", 0.0), "fill_rate"),
            latency_score=_coerce_float(data.get("latency_score", 0.0), "latency_score"),
            slippage_score=_coerce_float(data.get("slippage_score", 0.0), "slippage_score"),
            confidence_score=_coerce_float(data.get("confidence_score", 0.0), "confidence_score"),
            outcome_score=_coerce_float(data.get("outcome_score", 0.0), "outcome_score"),
            pnl_score=_coerce_float(data.get("pnl_score", 0.0), "pnl_score"),
            status=_normalize_status(data.get("status", "UNKNOWN")),
            failure_reason=_normalize_failure_reason(data.get("failure_reason")),
            outcome=_normalize_outcome(data.get("outcome")),
            component_scores=dict(data.get("component_scores", {}) or {}),
            flags=list(data.get("flags", []) or []),
        )


@dataclass
class BatchQualitySummary:
    """Agregacao de qualidade para um lote de episodios."""

    batch_size: int
    scored_episodes: int
    average_score: float
    median_score: float
    min_score: float
    max_score: float
    quality_index: float
    win_rate: float
    loss_rate: float
    breakeven_rate: float
    average_fill_rate: float
    average_latency_ms: float
    average_slippage_points: float
    failure_rate: float
    top_failure_reasons: Dict[str, int]
    episode_scores: List[EpisodeQualityScore] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["episode_scores"] = [score.to_dict() for score in self.episode_scores]
        return data

    para_dict = to_dict


class RLEpisodeQualityScorer:
    """Calcula score de qualidade por episodio e por lote."""

    def __init__(
        self,
        latency_ceiling_ms: float = DEFAULT_LATENCY_CEILING_MS,
        slippage_ceiling_points: float = DEFAULT_SLIPPAGE_CEILING_POINTS,
    ) -> None:
        if latency_ceiling_ms <= 0:
            raise ValueError("latency_ceiling_ms deve ser > 0")
        if slippage_ceiling_points <= 0:
            raise ValueError("slippage_ceiling_points deve ser > 0")
        self.latency_ceiling_ms = float(latency_ceiling_ms)
        self.slippage_ceiling_points = float(slippage_ceiling_points)

    def _coerce_episode(self, episode: Any) -> EpisodeQualityInput:
        if isinstance(episode, EpisodeQualityInput):
            return episode
        if isinstance(episode, Mapping):
            return EpisodeQualityInput.from_dict(episode)
        raise ValueError("episodio invalido")

    def _score_outcome(self, outcome: str) -> float:
        mapping = {
            "WIN": 100.0,
            "BREAKEVEN": 70.0,
            "LOSS": 25.0,
        }
        return mapping.get(outcome, 50.0)

    def _score_pnl(self, pnl_points: float) -> float:
        if pnl_points == 0:
            return 60.0
        if pnl_points > 0:
            return _clamp(70.0 + min(30.0, pnl_points * 0.15), 0.0, 100.0)
        return _clamp(60.0 + max(-55.0, pnl_points * 0.2), 0.0, 100.0)

    def score_episode(self, episode: Any) -> EpisodeQualityScore:
        """Calcula score de um episodio individual."""
        item = self._coerce_episode(episode)
        requested_qty = max(0.0, float(item.requested_qty))
        filled_qty = max(0.0, min(float(item.filled_qty), requested_qty if requested_qty > 0 else float(item.filled_qty)))
        fill_rate = filled_qty / requested_qty if requested_qty > 0 else 0.0
        fill_rate = _clamp(fill_rate, 0.0, 1.0)

        abs_slippage = abs(float(item.slippage_points))
        slippage_score = _clamp(
            100.0 - (min(abs_slippage, self.slippage_ceiling_points) / self.slippage_ceiling_points) * 100.0,
            0.0,
            100.0,
        )

        latency_score = _clamp(
            100.0 - (min(float(item.latency_ms), self.latency_ceiling_ms) / self.latency_ceiling_ms) * 100.0,
            0.0,
            100.0,
        )
        confidence_score = _clamp(float(item.confidence) * 100.0, 0.0, 100.0)
        outcome_score = self._score_outcome(_normalize_outcome(item.outcome))
        pnl_score = self._score_pnl(float(item.pnl_points))

        component_scores = {
            "fill_rate": fill_rate * 100.0,
            "slippage": slippage_score,
            "latency": latency_score,
            "confidence": confidence_score,
            "outcome": outcome_score,
            "pnl": pnl_score,
        }
        quality_score = (
            component_scores["fill_rate"] * 0.30
            + component_scores["slippage"] * 0.25
            + component_scores["latency"] * 0.20
            + component_scores["outcome"] * 0.15
            + component_scores["confidence"] * 0.05
            + component_scores["pnl"] * 0.05
        )

        status = _normalize_status(item.status)
        status_penalties = {
            "FILLED": 0.0,
            "PARTIAL": 8.0,
            "PENDING": 12.0,
            "QUEUED": 10.0,
            "REJECTED": 35.0,
            "CANCELLED": 25.0,
            "ERROR": 40.0,
        }
        quality_score -= status_penalties.get(status, 15.0)

        failure_reason = _normalize_failure_reason(item.failure_reason)
        failure_penalty = 0.0
        flags: List[str] = []
        if failure_reason:
            flags.append(f"failure:{failure_reason}")
            keywords = {
                "timeout": 8.0,
                "latency": 8.0,
                "slippage": 6.0,
                "reject": 12.0,
                "insufficient": 12.0,
                "liquidity": 10.0,
                "margin": 12.0,
            }
            failure_penalty = next(
                (penalty for keyword, penalty in keywords.items() if keyword in failure_reason),
                5.0,
            )
            quality_score -= failure_penalty

        if requested_qty <= 0:
            flags.append("requested_qty_zero")
        if item.filled_qty > requested_qty and requested_qty > 0:
            flags.append("filled_qty_clamped")
        if abs_slippage >= self.slippage_ceiling_points:
            flags.append("slippage_outlier")
        if item.latency_ms >= self.latency_ceiling_ms:
            flags.append("latency_outlier")
        if status not in {"FILLED", "PARTIAL"}:
            flags.append(f"status:{status.lower()}")

        quality_score = _clamp(quality_score, QUALITY_SCORE_MIN, QUALITY_SCORE_MAX)

        return EpisodeQualityScore(
            episode_id=item.episode_id,
            timestamp=item.timestamp,
            requested_qty=requested_qty,
            filled_qty=filled_qty,
            latency_ms=float(item.latency_ms),
            slippage_points=float(item.slippage_points),
            quality_score=quality_score,
            fill_rate=fill_rate,
            latency_score=latency_score,
            slippage_score=slippage_score,
            confidence_score=confidence_score,
            outcome_score=outcome_score,
            pnl_score=pnl_score,
            status=status,
            failure_reason=failure_reason,
            outcome=_normalize_outcome(item.outcome),
            component_scores=component_scores,
            flags=flags,
        )

    def score_batch(self, episodes: Iterable[Any]) -> BatchQualitySummary:
        """Agrega o score de um lote de episodios."""
        items = list(episodes or [])
        if not items:
            return BatchQualitySummary(
                batch_size=0,
                scored_episodes=0,
                average_score=0.0,
                median_score=0.0,
                min_score=0.0,
                max_score=0.0,
                quality_index=0.0,
                win_rate=0.0,
                loss_rate=0.0,
                breakeven_rate=0.0,
                average_fill_rate=0.0,
                average_latency_ms=0.0,
                average_slippage_points=0.0,
                failure_rate=0.0,
                top_failure_reasons={},
                episode_scores=[],
            )

        scored: List[EpisodeQualityScore] = [self.score_episode(item) for item in items]
        scores = [entry.quality_score for entry in scored]
        fill_rates = [entry.fill_rate for entry in scored]
        latencies = [entry.latency_ms for entry in scored]
        slippages = [abs(entry.slippage_points) for entry in scored]

        total = len(scored)
        win_rate = sum(1 for entry in scored if entry.outcome == "WIN") / total
        loss_rate = sum(1 for entry in scored if entry.outcome == "LOSS") / total
        breakeven_rate = sum(1 for entry in scored if entry.outcome == "BREAKEVEN") / total
        failure_rate = sum(1 for entry in scored if entry.failure_reason or entry.status not in {"FILLED", "PARTIAL"}) / total

        failure_reasons: Dict[str, int] = {}
        for entry in scored:
            if entry.failure_reason:
                failure_reasons[entry.failure_reason] = failure_reasons.get(entry.failure_reason, 0) + 1

        return BatchQualitySummary(
            batch_size=total,
            scored_episodes=total,
            average_score=mean(scores),
            median_score=median(scores),
            min_score=min(scores),
            max_score=max(scores),
            quality_index=mean(scores) / QUALITY_SCORE_MAX,
            win_rate=win_rate,
            loss_rate=loss_rate,
            breakeven_rate=breakeven_rate,
            average_fill_rate=mean(fill_rates),
            average_latency_ms=mean(latencies),
            average_slippage_points=mean(slippages),
            failure_rate=failure_rate,
            top_failure_reasons=failure_reasons,
            episode_scores=scored,
        )

    def aggregate_batch(self, episodes: Iterable[Any]) -> BatchQualitySummary:
        """Alias amigavel para score_batch."""
        return self.score_batch(episodes)


__all__ = [
    "QUALITY_SCORE_MIN",
    "QUALITY_SCORE_MAX",
    "DEFAULT_LATENCY_CEILING_MS",
    "DEFAULT_SLIPPAGE_CEILING_POINTS",
    "EpisodeQualityInput",
    "EpisodeQualityScore",
    "BatchQualitySummary",
    "RLEpisodeQualityScorer",
]
