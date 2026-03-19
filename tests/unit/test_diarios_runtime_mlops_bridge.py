"""Testes unitarios para `src.application.diarios_runtime_mlops_bridge`."""

from __future__ import annotations

import json
from types import SimpleNamespace

from src.application.diarios_runtime_mlops_bridge import DiarioRuntimeMlOpsBridge


def _complete_input() -> dict[str, object]:
    return {
        "perf": {
            "current_win_rate": 0.65,
            "baseline_win_rate": 0.65,
            "current_f1": 0.70,
            "baseline_f1": 0.70,
            "current_sharpe": 1.20,
            "drift_score": 0.20,
            "directional_imbalance_pct": 10.0,
            "trend_strength": 78.0,
            "directional_bias": 62.0,
            "adx": 34.0,
            "volatility": 24.0,
            "atr_percent": 1.4,
            "range_compression": 18.0,
        },
        "coherence": {
            "directional_imbalance_pct": 12.0,
            "drift_score": 0.15,
        },
        "dir_analysis": {
            "confianca_ajustada": 72.0,
            "directional_imbalance_pct": 11.0,
        },
        "guardian_state": {
            "active_kill_switch": False,
            "kill_switch_reason": "",
            "confidence_penalty": 0.0,
        },
        "order_history": [
            {
                "quality_score": 92.0,
                "fill_rate": 1.0,
                "latency_ms": 75.0,
                "slippage_points": 0.2,
                "status": "FILLED",
                "outcome": "WIN",
            },
            {
                "quality_score": 88.0,
                "fill_rate": 0.98,
                "latency_ms": 85.0,
                "slippage_points": 0.3,
                "status": "FILLED",
                "outcome": "WIN",
            },
        ],
        "execution_patterns": {
            "summary": {
                "event_count": 2,
                "fill_rate": 0.99,
                "avg_slippage_points": 0.25,
                "avg_latency_ms": 80.0,
                "rejection_rate": 0.0,
            }
        },
    }


def test_process_cycle_nominal_com_dados_completos() -> None:
    bridge = DiarioRuntimeMlOpsBridge()

    result = bridge.process_cycle(_complete_input())

    assert set(result) == {
        "regime",
        "retraining_trigger",
        "retraining_plan",
        "kill_switch",
        "execution_recommendation",
        "summary",
    }
    assert result["regime"]["regime"] == "TRENDING_UP"
    assert result["retraining_trigger"]["trigger"] is False
    assert result["retraining_plan"]["scheduled"] is False
    assert result["kill_switch"]["active"] is False
    assert result["execution_recommendation"]["history_size"] == 2
    assert result["summary"]["regime"] == "TRENDING_UP"
    assert result["summary"]["kill_switch_active"] is False


def test_process_cycle_input_vazio_nao_explode() -> None:
    bridge = DiarioRuntimeMlOpsBridge()

    result = bridge.process_cycle({})

    assert result["regime"]["regime"] == "RANGING"
    assert result["retraining_trigger"]["trigger"] is False
    assert result["kill_switch"]["active"] is False
    assert result["execution_recommendation"]["mode"] == "BALANCED"
    assert result["summary"]["kill_switch_active"] is False


def test_process_cycle_respeita_kill_switch_do_guardian_state() -> None:
    bridge = DiarioRuntimeMlOpsBridge()
    guardian_state = SimpleNamespace(
        active_kill_switch=True,
        kill_switch_reason="guardian risk gate",
        confidence_penalty=15.0,
    )

    result = bridge.process_cycle({"guardian_state": guardian_state})

    assert result["kill_switch"]["active"] is True
    assert result["kill_switch"]["audit"]["kill_switch_ativo_detectado"] is True
    assert result["kill_switch"]["audit"]["normalized_events"][0]["source"] == "guardian_state"
    assert result["summary"]["kill_switch_active"] is True


def test_process_cycle_dispara_retrain_por_drift_e_bias() -> None:
    bridge = DiarioRuntimeMlOpsBridge()
    payload = {
        "perf": {
            "current_win_rate": 0.65,
            "baseline_win_rate": 0.65,
            "current_f1": 0.70,
            "baseline_f1": 0.70,
            "current_sharpe": 1.10,
            "drift_score": 0.90,
            "directional_imbalance_pct": 82.0,
        },
        "coherence": {"directional_imbalance_pct": 81.0},
        "dir_analysis": {"directional_imbalance_pct": 80.0},
    }

    result = bridge.process_cycle(payload)

    assert result["retraining_trigger"]["trigger"] is True
    assert "drift" in result["retraining_trigger"]["categories"]
    assert "bias" in result["retraining_trigger"]["categories"]
    assert result["retraining_plan"]["scheduled"] is True
    assert result["retraining_plan"]["priority"] != "none"


def test_process_cycle_retorna_payload_serializavel() -> None:
    bridge = DiarioRuntimeMlOpsBridge()

    result = bridge.process_cycle(_complete_input())

    encoded = json.dumps(result, ensure_ascii=False)

    assert isinstance(encoded, str)
    assert "\"regime\"" in encoded
    assert "\"summary\"" in encoded
