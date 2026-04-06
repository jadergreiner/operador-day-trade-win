"""Testes do health-check automatizado do gate de promocao."""

from __future__ import annotations

import json
from pathlib import Path

from src.application.scheduler_promotion_healthcheck import (
    evaluate_status_payload,
    load_status_payload_from_file,
    load_status_payload_from_latest_promotion_file,
)


def test_evaluate_status_payload_falha_quando_reprovado() -> None:
    payload = {
        "scheduler_symbol_promotion": {
            "status": "reprovado",
            "motivo": "acuracia insuficiente",
        }
    }
    result = evaluate_status_payload(payload)
    assert result.ok is False
    assert result.status == "reprovado"


def test_evaluate_status_payload_aprova_quando_aprovado() -> None:
    payload = {
        "scheduler_symbol_promotion": {
            "status": "aprovado",
            "motivo": "gate manual aprovado",
        }
    }
    result = evaluate_status_payload(payload)
    assert result.ok is True
    assert result.status == "aprovado"


def test_evaluate_status_payload_suporta_fail_on_custom() -> None:
    payload = {
        "scheduler_symbol_promotion": {
            "status": "sem_promocao",
            "motivo": "artefato ausente",
        }
    }
    result = evaluate_status_payload(payload, fail_on_statuses=("reprovado", "sem_promocao"))
    assert result.ok is False
    assert result.status == "sem_promocao"


def test_load_status_payload_from_file_ler_json(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    path.write_text(
        json.dumps({"scheduler_symbol_promotion": {"status": "aprovado"}}),
        encoding="utf-8",
    )
    payload = load_status_payload_from_file(path)
    assert payload["scheduler_symbol_promotion"]["status"] == "aprovado"


def test_load_status_payload_from_latest_promotion_file(tmp_path: Path) -> None:
    first = tmp_path / "scheduler_symbol_promotion_20260406_100000.json"
    second = tmp_path / "scheduler_symbol_promotion_20260406_120000.json"
    first.write_text(
        json.dumps({"scheduler_symbol_promotion": {"status": "aprovado"}}),
        encoding="utf-8",
    )
    second.write_text(
        json.dumps(
            {
                "scheduler_symbol_promotion": {
                    "status": "reprovado",
                    "aprovado": False,
                    "runtime_config_presente": True,
                    "motivo": "teste",
                }
            }
        ),
        encoding="utf-8",
    )
    payload = load_status_payload_from_latest_promotion_file(tmp_path)
    assert payload["scheduler_symbol_promotion"]["status"] == "reprovado"
