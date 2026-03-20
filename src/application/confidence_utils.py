"""Utilitarios para normalizacao, leitura e exibicao de confianca."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIDENCE_OVERRIDE_TODAY_FILE = PROJECT_ROOT / "config" / "confidence_override_today.json"


def safe_float(value: Any, fallback: float = 0.0) -> float:
    """Converte valor para float com fallback seguro."""
    try:
        if value is None:
            return fallback
        return float(value)
    except Exception:
        return fallback


def normalize_confidence(value: Any) -> float:
    """Normaliza confidence para escala 0-1.

    Aceita valores em 0-1 ou 0-100 e converte o segundo caso para fração.
    Valores negativos viram 0.
    """
    conf = safe_float(value, 0.0)
    if conf < 0:
        return 0.0
    if conf > 1.0:
        return conf / 100.0
    return conf


def load_daily_confidence_override(
    path: str | Path | None = None,
) -> float | None:
    """Carrega a confidence diaria persistida pelo P50-B.

    Retorna `None` se o arquivo nao existir ou estiver invalido.
    """
    override_path = Path(path) if path is not None else CONFIDENCE_OVERRIDE_TODAY_FILE
    if not override_path.exists():
        return None

    try:
        with open(override_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    confidence = payload.get("confidence_current")
    if confidence is None:
        return None

    return normalize_confidence(confidence)


def resolve_daily_confidence_gate(
    confidence_override: float | None,
    *,
    default_gate: float = 0.60,
    cautious_floor: float = 0.35,
) -> float:
    """Resolve o threshold efetivo do gate de confianca do dia.

    O P50-B ajusta a confidence diaria com base no WR do pregão anterior.
    Para nao ficar tao conservador quanto o gate fixo de 60%, usamos essa
    confidence como referencia do piso operacional, mas nunca abaixo de
    `cautious_floor` nem acima do gate padrao.
    """
    if confidence_override is None:
        return default_gate

    return max(cautious_floor, min(default_gate, confidence_override))


__all__ = [
    "CONFIDENCE_OVERRIDE_TODAY_FILE",
    "load_daily_confidence_override",
    "normalize_confidence",
    "resolve_daily_confidence_gate",
    "safe_float",
]
