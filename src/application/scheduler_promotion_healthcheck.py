"""Health-check automatizado do gate de promocao do scheduler."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class HealthCheckResult:
    ok: bool
    status: str
    motivo: str
    source: str


def _normalize_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    return status if status else "sem_promocao"


def _extract_promotion_block(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    block = payload.get("scheduler_symbol_promotion")
    if isinstance(block, Mapping):
        return block
    return {}


def evaluate_status_payload(
    payload: Mapping[str, Any],
    *,
    fail_on_statuses: tuple[str, ...] = ("reprovado",),
) -> HealthCheckResult:
    block = _extract_promotion_block(payload)
    status = _normalize_status(block.get("status"))
    motivo = str(block.get("motivo", "")).strip()
    should_fail = status in set(s.lower() for s in fail_on_statuses)
    return HealthCheckResult(
        ok=not should_fail,
        status=status,
        motivo=motivo,
        source="payload",
    )


def load_status_payload_from_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Arquivo de status invalido: raiz nao eh objeto.")
    return payload


def load_status_payload_from_url(url: str, timeout_seconds: float = 3.0) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Falha ao consultar URL de status: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("Resposta do endpoint de status invalida: raiz nao eh objeto.")
    return payload


def load_status_payload_from_latest_promotion_file(outputs_dir: Path) -> dict[str, Any]:
    files = sorted(outputs_dir.glob("scheduler_symbol_promotion_*.json"))
    if not files:
        raise FileNotFoundError("Nenhum arquivo scheduler_symbol_promotion_*.json encontrado.")
    latest = files[-1]
    payload = load_status_payload_from_file(latest)
    block = _extract_promotion_block(payload)
    if block:
        return {
            "scheduler_symbol_promotion": {
                "status": _normalize_status(block.get("status")),
                "aprovado": bool(block.get("aprovado", False)),
                "runtime_config_presente": bool(
                    block.get("runtime_config_presente", False)
                ),
                "motivo": str(block.get("motivo", "")).strip(),
            }
        }
    return payload
