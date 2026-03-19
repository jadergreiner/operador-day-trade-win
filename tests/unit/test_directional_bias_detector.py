"""Testes unitarios para `src.application.directional_bias_detector`."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from src.application.directional_bias_detector import (
    BiasLevel,
    DirectionalBiasDetector,
    DirectionalBiasReport,
)


def test_empty_sequence_returns_low_bias() -> None:
    detector = DirectionalBiasDetector()

    report = detector.detect_bias([])

    assert report.total_signals == 0
    assert report.buy_count == 0
    assert report.sell_count == 0
    assert report.dominant_side == "neutral"
    assert report.directional_concentration_pct == 0.0
    assert report.bias_level == BiasLevel.BAIXO


def test_balanced_sequence_is_low_bias() -> None:
    detector = DirectionalBiasDetector()

    report = detector.detect_bias(["buy", "sell"])

    assert report.total_signals == 2
    assert report.buy_count == 1
    assert report.sell_count == 1
    assert report.dominant_side == "neutral"
    assert report.directional_concentration_pct == 50.0
    assert report.directional_imbalance_pct == 0.0
    assert report.bias_level == BiasLevel.BAIXO


def test_moderate_bias_uses_default_thresholds() -> None:
    detector = DirectionalBiasDetector()

    report = detector.detect_bias(["buy", "buy", "buy", "sell", "sell"])

    assert report.dominant_side == "buy"
    assert report.dominant_count == 3
    assert report.directional_concentration_pct == 60.0
    assert report.bias_level == BiasLevel.MODERADO


def test_high_bias_is_classified_as_high() -> None:
    detector = DirectionalBiasDetector()

    report = detector.detect_bias(["sell", "sell", "sell", "sell"])

    assert report.dominant_side == "sell"
    assert report.dominant_count == 4
    assert report.directional_concentration_pct == 100.0
    assert report.bias_level == BiasLevel.ALTO


def test_custom_thresholds_change_classification() -> None:
    detector = DirectionalBiasDetector(
        moderate_threshold_pct=70.0,
        high_threshold_pct=90.0,
    )

    report = detector.detect_bias(["buy", "buy", "buy", "buy", "sell"])

    assert report.directional_concentration_pct == 80.0
    assert report.bias_level == BiasLevel.MODERADO


def test_detectar_vies_direcional_alias_works() -> None:
    detector = DirectionalBiasDetector()

    report = detector.detectar_vies_direcional(["long", "bullish", "sell"])

    assert report.buy_count == 2
    assert report.sell_count == 1
    assert report.dominant_side == "buy"


def test_dict_signal_normalization_handles_common_keys() -> None:
    detector = DirectionalBiasDetector()

    report = detector.detect_bias(
        [
            {"side": "BUY"},
            {"direction": "short"},
            {"action": "long"},
            {"signal": "sell"},
        ]
    )

    assert report.buy_count == 2
    assert report.sell_count == 2
    assert report.dominant_side == "neutral"


def test_invalid_signal_raises_value_error() -> None:
    detector = DirectionalBiasDetector()

    with pytest.raises(ValueError, match="Valor direcional invalido"):
        detector.detect_bias(["buy", "hold"])


def test_invalid_thresholds_raise_value_error() -> None:
    with pytest.raises(ValueError, match="Limiar moderado"):
        DirectionalBiasDetector(moderate_threshold_pct=80.0, high_threshold_pct=60.0)


def test_report_to_dict_is_json_serializable() -> None:
    detector = DirectionalBiasDetector()
    report = detector.detect_bias(["buy", "buy", "sell"])

    payload = report.to_dict()
    encoded = json.dumps(payload, ensure_ascii=False)

    assert payload["bias_level"] == BiasLevel.MODERADO.value
    assert payload["total_signals"] == 3
    assert payload["timestamp"]
    assert "\"bias_level\": \"moderado\"" in encoded


def test_build_report_returns_dict_alias() -> None:
    detector = DirectionalBiasDetector()

    payload = detector.build_report(["sell", "sell", "buy"])

    assert payload["dominant_side"] == "sell"
    assert payload["bias_level"] == BiasLevel.MODERADO.value
    assert payload["directional_imbalance_pct"] == 33.3333


def test_report_dataclass_can_be_created_explicitly() -> None:
    report_time = datetime.now()
    report = DirectionalBiasReport(
        total_signals=1,
        buy_count=1,
        sell_count=0,
        dominant_side="buy",
        dominant_count=1,
        directional_concentration_pct=100.0,
        directional_imbalance_pct=100.0,
        bias_level=BiasLevel.ALTO,
        moderate_threshold_pct=60.0,
        high_threshold_pct=75.0,
        timestamp=report_time,
    )

    payload = report.to_dict()

    assert payload["timestamp"] == report_time.isoformat()
    assert payload["dominant_side"] == "buy"
