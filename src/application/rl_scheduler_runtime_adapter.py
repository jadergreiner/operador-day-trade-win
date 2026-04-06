"""Adaptador de runtime para alimentar RLScheduler com dados dos agentes RL."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Iterable, Mapping

_CALIBRACAO_POR_SIMBOLO: dict[str, dict[str, float]] = {
    # WIN tipicamente aceita maior variância intraday antes de classificar estresse.
    "WIN": {
        "stress_score_trigger": 0.70,
        "volatilidade_trigger": 75.0,
        "loss_streak_divisor": 4.0,
        "media_negativa_scale": 2.0,
    },
    # WDO costuma virar regime com menos trades; mais sensível no gatilho.
    "WDO": {
        "stress_score_trigger": 0.60,
        "volatilidade_trigger": 60.0,
        "loss_streak_divisor": 3.0,
        "media_negativa_scale": 2.5,
    },
    "DEFAULT": {
        "stress_score_trigger": 0.70,
        "volatilidade_trigger": 75.0,
        "loss_streak_divisor": 4.0,
        "media_negativa_scale": 2.0,
    },
}

_RUNTIME_CALIBRATION_CACHE: dict[str, Any] = {
    "path": None,
    "mtime": None,
    "data": {},
}


def _coerce_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalizar_simbolo(simbolo: str | None) -> str:
    if not simbolo:
        return "DEFAULT"
    upper = simbolo.upper()
    if "WIN" in upper:
        return "WIN"
    if "WDO" in upper:
        return "WDO"
    return "DEFAULT"


def obter_calibracao_simbolo(simbolo: str | None) -> dict[str, float]:
    base = dict(_CALIBRACAO_POR_SIMBOLO[_normalizar_simbolo(simbolo)])
    runtime = _get_runtime_calibration_for_symbol(simbolo)
    base.update(runtime)
    return base


def _runtime_calibration_path() -> Path:
    raw = (
        os.getenv("RL_SCHEDULER_SYMBOL_CALIBRATION_PATH", "").strip()
        or "data/scheduler/symbol_calibration_runtime.json"
    )
    return Path(raw)


def _read_runtime_calibration_file(path: Path) -> dict[str, dict[str, float]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, Mapping):
        return {}
    raw_cfg = payload.get("calibracao_por_simbolo")
    if not isinstance(raw_cfg, Mapping):
        return {}
    parsed_cfg: dict[str, dict[str, float]] = {}
    for symbol, cfg in raw_cfg.items():
        if not isinstance(symbol, str) or not isinstance(cfg, Mapping):
            continue
        parsed: dict[str, float] = {}
        for key in (
            "stress_score_trigger",
            "volatilidade_trigger",
            "loss_streak_divisor",
            "media_negativa_scale",
        ):
            value = _coerce_float(cfg.get(key))
            if value is not None:
                parsed[key] = value
        if len(parsed) == 4:
            parsed_cfg[symbol.upper()] = parsed
    return parsed_cfg


def _load_runtime_calibration() -> dict[str, dict[str, float]]:
    path = _runtime_calibration_path()
    cache_path = _RUNTIME_CALIBRATION_CACHE.get("path")
    cache_mtime = _RUNTIME_CALIBRATION_CACHE.get("mtime")
    mtime = path.stat().st_mtime if path.exists() else None
    if cache_path == str(path) and cache_mtime == mtime:
        data = _RUNTIME_CALIBRATION_CACHE.get("data")
        if isinstance(data, dict):
            return data
    data = _read_runtime_calibration_file(path)
    _RUNTIME_CALIBRATION_CACHE["path"] = str(path)
    _RUNTIME_CALIBRATION_CACHE["mtime"] = mtime
    _RUNTIME_CALIBRATION_CACHE["data"] = data
    return data


def _get_runtime_calibration_for_symbol(simbolo: str | None) -> dict[str, float]:
    normalized = _normalizar_simbolo(simbolo)
    data = _load_runtime_calibration()
    cfg = data.get(normalized)
    if isinstance(cfg, dict):
        return dict(cfg)
    return {}


def _resolver_calibracao(
    simbolo: str | None,
    calibracao_override: Mapping[str, Any] | None = None,
) -> dict[str, float]:
    calibracao = obter_calibracao_simbolo(simbolo)
    if calibracao_override is None:
        return calibracao
    for key in (
        "stress_score_trigger",
        "volatilidade_trigger",
        "loss_streak_divisor",
        "media_negativa_scale",
    ):
        parsed = _coerce_float(calibracao_override.get(key))
        if parsed is not None:
            calibracao[key] = parsed
    return calibracao


def extrair_pnls(trades_fechados: Iterable[Mapping[str, Any]]) -> list[float]:
    """Extrai PnLs normalizados a partir do payload de trades fechados."""
    pnls: list[float] = []
    for trade in trades_fechados:
        if not isinstance(trade, Mapping):
            continue
        for key in ("pnl", "pnl_pct", "profit_loss", "resultado_final_pct"):
            parsed = _coerce_float(trade.get(key))
            if parsed is not None:
                pnls.append(parsed)
                break
    return pnls


def calcular_metricas_para_scheduler(
    trades_fechados: Iterable[Mapping[str, Any]],
) -> dict[str, float]:
    """Calcula métricas compactas para detecção de degradação no scheduler."""
    pnls = extrair_pnls(trades_fechados)
    if not pnls:
        return {"win_rate": 0.0, "sharpe": 0.0, "f1": 0.0}

    total = len(pnls)
    wins = sum(1 for value in pnls if value > 0.0)
    win_rate = (wins / total) * 100.0
    mean = sum(pnls) / total
    variance = sum((value - mean) ** 2 for value in pnls) / total
    std = math.sqrt(variance)
    sharpe = mean / std if std > 1e-9 else 0.0
    f1_proxy = wins / total

    return {
        "win_rate": float(win_rate),
        "sharpe": float(sharpe),
        "f1": float(f1_proxy),
    }


def construir_contexto_operacional_para_scheduler(
    trades_fechados: Iterable[Mapping[str, Any]],
    *,
    simbolo: str | None = None,
    calibracao_override: Mapping[str, Any] | None = None,
) -> dict[str, float | str]:
    """Deriva contexto operacional (regime/estresse/vol) da sessão recente."""
    pnls = extrair_pnls(trades_fechados)
    calibracao = _resolver_calibracao(simbolo, calibracao_override)
    if not pnls:
        return {
            "regime_mercado": "estavel",
            "stress_score": 0.0,
            "volatilidade": 0.0,
            "simbolo_contexto": _normalizar_simbolo(simbolo),
        }

    losses_streak = 0
    max_losses_streak = 0
    for value in pnls:
        if value < 0.0:
            losses_streak += 1
            if losses_streak > max_losses_streak:
                max_losses_streak = losses_streak
        else:
            losses_streak = 0

    mean = sum(pnls) / len(pnls)
    variance = sum((value - mean) ** 2 for value in pnls) / len(pnls)
    vol = math.sqrt(variance) * 100.0
    win_rate = (sum(1 for value in pnls if value > 0.0) / len(pnls)) * 100.0

    stress_score = min(
        1.0,
        max(
            max_losses_streak / calibracao["loss_streak_divisor"],
            0.0
            if mean >= 0
            else min(1.0, abs(mean) * calibracao["media_negativa_scale"]),
            0.0 if win_rate >= 50.0 else (50.0 - win_rate) / 50.0,
        ),
    )
    regime = (
        "stress_high_vol"
        if (
            stress_score >= calibracao["stress_score_trigger"]
            or vol >= calibracao["volatilidade_trigger"]
        )
        else "estavel"
    )

    return {
        "regime_mercado": regime,
        "stress_score": float(stress_score),
        "volatilidade": float(vol),
        "simbolo_contexto": _normalizar_simbolo(simbolo),
    }
