"""Promocao manual de calibracao por simbolo para runtime do scheduler."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class PromotionDecision:
    aprovado: bool
    motivo: str
    detalhes: dict[str, Any]


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_calibration_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Relatorio de calibracao invalido: raiz nao eh objeto.")
    return payload


def validate_promotion_gate(
    report: Mapping[str, Any],
    *,
    required_symbols: tuple[str, ...] = ("WIN", "WDO"),
    min_scenarios_per_symbol: int = 2,
    min_accuracy: float = 1.0,
) -> PromotionDecision:
    recs_raw = report.get("recomendacao_por_simbolo")
    if not isinstance(recs_raw, Mapping):
        return PromotionDecision(
            aprovado=False,
            motivo="campo recomendacao_por_simbolo ausente/invalid",
            detalhes={},
        )

    detalhes: dict[str, Any] = {"symbols": {}}
    for symbol in required_symbols:
        rec = recs_raw.get(symbol)
        if not isinstance(rec, Mapping):
            return PromotionDecision(
                aprovado=False,
                motivo=f"simbolo obrigatorio ausente no relatorio: {symbol}",
                detalhes=detalhes,
            )
        acertos = int(rec.get("acertos", 0))
        total = int(rec.get("total_cenarios", 0))
        accuracy = (acertos / total) if total > 0 else 0.0
        detalhes["symbols"][symbol] = {
            "acertos": acertos,
            "total_cenarios": total,
            "accuracy": round(accuracy, 4),
        }
        if total < min_scenarios_per_symbol:
            return PromotionDecision(
                aprovado=False,
                motivo=f"cobertura insuficiente para {symbol}: {total}<{min_scenarios_per_symbol}",
                detalhes=detalhes,
            )
        if accuracy < min_accuracy:
            return PromotionDecision(
                aprovado=False,
                motivo=f"acuracia insuficiente para {symbol}: {accuracy:.2%}<{min_accuracy:.2%}",
                detalhes=detalhes,
            )

    return PromotionDecision(
        aprovado=True,
        motivo="gate manual aprovado",
        detalhes=detalhes,
    )


def _extract_runtime_calibration(report: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    recs_raw = report.get("recomendacao_por_simbolo")
    if not isinstance(recs_raw, Mapping):
        raise ValueError("Campo recomendacao_por_simbolo ausente.")

    runtime_cfg: dict[str, dict[str, float]] = {}
    for symbol, rec in recs_raw.items():
        if not isinstance(symbol, str) or not isinstance(rec, Mapping):
            continue
        recommended = rec.get("calibracao_recomendada")
        if not isinstance(recommended, Mapping):
            continue
        parsed: dict[str, float] = {}
        for key in (
            "stress_score_trigger",
            "volatilidade_trigger",
            "loss_streak_divisor",
            "media_negativa_scale",
        ):
            value = _coerce_float(recommended.get(key))
            if value is not None:
                parsed[key] = value
        if len(parsed) == 4:
            runtime_cfg[symbol.upper()] = parsed
    if not runtime_cfg:
        raise ValueError("Nenhuma calibracao valida encontrada para promocao.")
    return runtime_cfg


def promote_runtime_calibration(
    *,
    report_path: Path,
    destination_path: Path,
    approver: str,
    min_scenarios_per_symbol: int = 2,
    min_accuracy: float = 1.0,
    dry_run: bool = False,
) -> dict[str, Any]:
    report = load_calibration_report(report_path)
    decision = validate_promotion_gate(
        report,
        min_scenarios_per_symbol=min_scenarios_per_symbol,
        min_accuracy=min_accuracy,
    )
    payload: dict[str, Any] = {
        "timestamp_promocao": datetime.now().isoformat(timespec="seconds"),
        "approver": approver,
        "source_report": str(report_path).replace("\\", "/"),
        "aprovado": decision.aprovado,
        "motivo": decision.motivo,
        "detalhes_gate": decision.detalhes,
        "destination_path": str(destination_path).replace("\\", "/"),
        "dry_run": dry_run,
    }
    if not decision.aprovado:
        return payload

    runtime_cfg = _extract_runtime_calibration(report)
    payload["runtime_calibration"] = runtime_cfg
    if not dry_run:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        destination_path.write_text(
            json.dumps(
                {
                    "metadata": {
                        "timestamp_promocao": payload["timestamp_promocao"],
                        "approver": approver,
                        "source_report": payload["source_report"],
                    },
                    "calibracao_por_simbolo": runtime_cfg,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return payload
