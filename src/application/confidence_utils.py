"""Utilitarios para normalizacao e exibicao de confianca."""

from __future__ import annotations

from typing import Any


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


__all__ = ["normalize_confidence", "safe_float"]
