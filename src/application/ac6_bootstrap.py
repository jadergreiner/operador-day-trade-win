"""Bootstrap compartilhado para os modulos AC6 dos agentes operacionais."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_AC6_BASELINE_METRICS: dict[str, float] = {
    "win_rate": 0.65,
    "f1_score": 0.68,
    "sharpe_ratio": 1.2,
}


@dataclass(slots=True)
class AC6BootstrapResult:
    """Container com instancias AC6 inicializadas."""

    drift_detector: Any = None
    online_learning: Any = None
    baseline_comparator: Any = None


def build_ac6_components(
    *,
    drift_detector_cls: Any | None,
    online_learning_cls: Any | None,
    baseline_comparator_cls: Any | None,
    model_name: str,
    models_dir_root: str | Path,
    baseline_metrics: dict[str, float] | None = None,
    drift_threshold_zscore: float = 2.0,
    window_size: int = 100,
    z_score_threshold: float = 2.0,
) -> AC6BootstrapResult:
    """Cria os componentes AC6 com parametros consistentes e fallback seguro."""
    def _as_float(value: object, default: float) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _as_int(value: object, default: int) -> int:
        try:
            if value is None:
                return default
            return int(float(value))
        except (TypeError, ValueError):
            return default

    metrics = dict(DEFAULT_AC6_BASELINE_METRICS)
    if baseline_metrics:
        metrics.update({k: _as_float(v, metrics.get(k, 0.0)) for k, v in baseline_metrics.items() if v is not None})

    models_dir_root = Path(models_dir_root)
    drift_threshold_zscore = _as_float(drift_threshold_zscore, 2.0)
    window_size = _as_int(window_size, 100)
    z_score_threshold = _as_float(z_score_threshold, 2.0)
    drift_detector = None
    online_learning = None
    baseline_comparator = None

    if drift_detector_cls is not None:
        drift_detector = drift_detector_cls(
            baseline_f1=metrics["f1_score"],
            baseline_win_rate=metrics["win_rate"],
            baseline_sharpe=metrics["sharpe_ratio"],
            drift_threshold_zscore=drift_threshold_zscore,
            window_size=window_size,
        )

    if online_learning_cls is not None:
        online_learning = online_learning_cls(
            model_name=model_name,
            baseline_metrics=metrics,
            models_dir=str(models_dir_root / "ac6_8_online_learning"),
        )

    if baseline_comparator_cls is not None:
        baseline_comparator = baseline_comparator_cls(
            baseline_metrics=metrics,
            z_score_threshold=z_score_threshold,
            models_dir=str(models_dir_root / "ac6_9_baseline"),
        )

    return AC6BootstrapResult(
        drift_detector=drift_detector,
        online_learning=online_learning,
        baseline_comparator=baseline_comparator,
    )


__all__ = [
    "AC6BootstrapResult",
    "DEFAULT_AC6_BASELINE_METRICS",
    "build_ac6_components",
]
