"""Testes unitarios para `src.application.adaptive_retraining_pipeline`."""

from __future__ import annotations

import json

from src.application.adaptive_retraining_pipeline import (
    AdaptiveRetrainingPipeline,
    AdaptiveRetrainingPolicy,
    TriggerPriority,
    TriggerSeverity,
)


def _base_metrics() -> dict[str, float]:
    return {
        "baseline_win_rate": 0.65,
        "current_win_rate": 0.65,
        "baseline_f1": 0.70,
        "current_f1": 0.70,
        "current_sharpe": 1.10,
        "drift_score": 0.20,
        "directional_imbalance_pct": 10.0,
    }


def test_evaluate_trigger_sem_gatilho() -> None:
    pipeline = AdaptiveRetrainingPipeline()

    result = pipeline.evaluate_trigger(_base_metrics())

    assert result["trigger"] is False
    assert result["reasons"] == []
    assert result["categories"] == []
    assert result["severity"] == TriggerSeverity.LOW.value
    assert result["priority"] == TriggerPriority.NONE.value


def test_trigger_por_queda_de_win_rate() -> None:
    pipeline = AdaptiveRetrainingPipeline()
    metrics = _base_metrics()
    metrics["current_win_rate"] = 0.58

    result = pipeline.evaluate_trigger(metrics)

    assert result["trigger"] is True
    assert "performance" in result["categories"]
    assert any(reason.startswith("performance_drop_win_rate") for reason in result["reasons"])


def test_trigger_por_queda_de_f1() -> None:
    pipeline = AdaptiveRetrainingPipeline()
    metrics = _base_metrics()
    metrics["current_f1"] = 0.60

    result = pipeline.evaluate_trigger(metrics)

    assert result["trigger"] is True
    assert any(reason.startswith("performance_drop_f1") for reason in result["reasons"])


def test_trigger_por_sharpe_abaixo_do_minimo() -> None:
    pipeline = AdaptiveRetrainingPipeline()
    metrics = _base_metrics()
    metrics["current_sharpe"] = 0.70

    result = pipeline.evaluate_trigger(metrics)

    assert result["trigger"] is True
    assert any(reason.startswith("performance_sharpe_below_min") for reason in result["reasons"])


def test_trigger_por_drift_score() -> None:
    pipeline = AdaptiveRetrainingPipeline()
    metrics = _base_metrics()
    metrics["drift_score"] = 0.60

    result = pipeline.evaluate_trigger(metrics)

    assert result["trigger"] is True
    assert "drift" in result["categories"]
    assert any(reason.startswith("drift_warning") for reason in result["reasons"])


def test_trigger_por_drift_critico_elevado() -> None:
    pipeline = AdaptiveRetrainingPipeline()
    metrics = _base_metrics()
    metrics["drift_score"] = 0.90

    result = pipeline.evaluate_trigger(metrics)

    assert result["trigger"] is True
    assert any(reason.startswith("drift_critical") for reason in result["reasons"])


def test_trigger_por_bias_imbalance() -> None:
    pipeline = AdaptiveRetrainingPipeline()
    metrics = _base_metrics()
    metrics["directional_imbalance_pct"] = 70.0

    result = pipeline.evaluate_trigger(metrics)

    assert result["trigger"] is True
    assert "bias" in result["categories"]
    assert any(reason.startswith("bias_critical") for reason in result["reasons"])


def test_trigger_por_bias_level_custom() -> None:
    pipeline = AdaptiveRetrainingPipeline()
    metrics = _base_metrics()
    metrics.pop("directional_imbalance_pct")
    metrics["bias_level"] = "alto"

    result = pipeline.evaluate_trigger(metrics)

    assert result["trigger"] is True
    assert any(reason.startswith("bias_critical") for reason in result["reasons"])


def test_trigger_combinado_resulta_em_prioridade_alta() -> None:
    pipeline = AdaptiveRetrainingPipeline()
    metrics = _base_metrics()
    metrics["current_win_rate"] = 0.55
    metrics["drift_score"] = 0.90
    metrics["directional_imbalance_pct"] = 80.0

    result = pipeline.evaluate_trigger(metrics)

    assert result["trigger"] is True
    assert result["severity"] == TriggerSeverity.HIGH.value
    assert result["priority"] == TriggerPriority.HIGH.value
    assert len(result["reasons"]) >= 3


def test_schedule_retraining_nao_agenda_sem_gatilho() -> None:
    pipeline = AdaptiveRetrainingPipeline()

    plan = pipeline.schedule_retraining(_base_metrics())

    assert plan["scheduled"] is False
    assert plan["priority"] == TriggerPriority.NONE.value
    assert plan["recommended_window"] == "none"
    assert plan["actions"] == []


def test_schedule_retraining_agenda_com_acoes() -> None:
    pipeline = AdaptiveRetrainingPipeline()
    metrics = _base_metrics()
    metrics["current_win_rate"] = 0.58
    metrics["drift_score"] = 0.60

    plan = pipeline.schedule_retraining(metrics)

    assert plan["scheduled"] is True
    assert plan["priority"] in {TriggerPriority.LOW.value, TriggerPriority.MEDIUM.value}
    assert plan["recommended_window"] == "off_peak"
    assert "gerar_plano_retrain" in plan["actions"]
    assert "revisar_metricas_modelo" in plan["actions"]
    assert "validar_drift_com_baseline" in plan["actions"]
    assert plan["trigger"]["trigger"] is True


def test_nested_metrics_are_supported() -> None:
    pipeline = AdaptiveRetrainingPipeline()

    result = pipeline.evaluate_trigger(
        {
            "current_metrics": {
                "win_rate": 0.58,
                "f1_score": 0.60,
                "sharpe_ratio": 0.70,
                "drift_score": 0.80,
                "directional_imbalance_pct": 75.0,
            },
            "baseline_metrics": {
                "win_rate": 0.65,
                "f1_score": 0.70,
            },
        }
    )

    assert result["trigger"] is True
    assert "performance" in result["categories"]
    assert "drift" in result["categories"]
    assert "bias" in result["categories"]


def test_custom_policy_changes_thresholds() -> None:
    pipeline = AdaptiveRetrainingPipeline(
        AdaptiveRetrainingPolicy(
            max_win_rate_drop_pct=15.0,
            max_f1_drop_pct=0.10,
            min_sharpe=0.5,
            max_drift_score=0.8,
            max_bias_imbalance_pct=90.0,
        )
    )
    metrics = _base_metrics()
    metrics["current_win_rate"] = 0.58

    result = pipeline.evaluate_trigger(metrics)

    assert result["trigger"] is False
    assert result["reasons"] == []


def test_evaluate_trigger_json_serializable_shape() -> None:
    pipeline = AdaptiveRetrainingPipeline()
    metrics = _base_metrics()
    metrics["current_win_rate"] = 0.50

    result = pipeline.evaluate_trigger(metrics)

    payload = json.dumps(result, ensure_ascii=False)

    assert "\"trigger\": true" in payload.lower()
    assert "\"priority\"" in payload
