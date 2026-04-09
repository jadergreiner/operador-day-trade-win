"""Health-check automatizado do gate de promocao do scheduler."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
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


def _parse_horario_hhmm(valor: str) -> tuple[int, int]:
    """Converte `HH:MM` em `(hora, minuto)` com validação simples."""
    texto = str(valor or "").strip()
    try:
        hora_txt, minuto_txt = texto.split(":", maxsplit=1)
        hora = int(hora_txt)
        minuto = int(minuto_txt)
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            f"Horário inválido para tolerância operacional: {valor!r}. Use HH:MM."
        ) from exc

    if not (0 <= hora <= 23 and 0 <= minuto <= 59):
        raise ValueError(
            f"Horário inválido para tolerância operacional: {valor!r}. Use HH:MM."
        )
    return hora, minuto


def evaluate_status_payload(
    payload: Mapping[str, Any],
    *,
    fail_on_statuses: tuple[str, ...] = ("reprovado",),
    allow_sem_promocao_until: str | None = None,
    allow_sem_promocao_in_demo: bool = False,
    now: datetime | None = None,
) -> HealthCheckResult:
    block = _extract_promotion_block(payload)
    status = _normalize_status(block.get("status"))
    motivo = str(block.get("motivo", "")).strip()
    fail_on = {s.lower() for s in fail_on_statuses}

    tolerado = False
    if status == "sem_promocao" and "sem_promocao" in fail_on:
        if allow_sem_promocao_in_demo:
            tolerado = True
            complemento = "sem_promocao tolerado em conta demo"
            motivo = f"{motivo} | {complemento}" if motivo else complemento
        elif allow_sem_promocao_until:
            hora, minuto = _parse_horario_hhmm(allow_sem_promocao_until)
            referencia = now or datetime.now()
            limite = referencia.replace(
                hour=hora,
                minute=minuto,
                second=0,
                microsecond=0,
            )
            tolerado = referencia <= limite
            if tolerado:
                complemento = (
                    f"sem_promocao tolerado até {limite.strftime('%H:%M')} "
                    f"na janela mínima operacional"
                )
                motivo = f"{motivo} | {complemento}" if motivo else complemento

    should_fail = status in fail_on and not tolerado
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
