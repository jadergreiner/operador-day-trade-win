"""Testes do health-check automatizado do gate de promocao."""

from __future__ import annotations

import json
from datetime import datetime
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


def test_evaluate_status_payload_tolera_sem_promocao_dentro_da_janela() -> None:
    payload = {
        "scheduler_symbol_promotion": {
            "status": "sem_promocao",
            "motivo": "aguardando promoção antes da abertura",
        }
    }
    result = evaluate_status_payload(
        payload,
        fail_on_statuses=("reprovado", "sem_promocao"),
        allow_sem_promocao_until="09:05",
        now=datetime(2026, 4, 7, 8, 55),
    )
    assert result.ok is True
    assert result.status == "sem_promocao"
    assert "09:05" in result.motivo


def test_evaluate_status_payload_reprova_sem_promocao_fora_da_janela() -> None:
    payload = {
        "scheduler_symbol_promotion": {
            "status": "sem_promocao",
            "motivo": "promoção ainda não realizada",
        }
    }
    result = evaluate_status_payload(
        payload,
        fail_on_statuses=("reprovado", "sem_promocao"),
        allow_sem_promocao_until="09:05",
        now=datetime(2026, 4, 7, 9, 6),
    )
    assert result.ok is False
    assert result.status == "sem_promocao"


def test_evaluate_status_payload_tolera_sem_promocao_em_conta_demo() -> None:
    payload = {
        "scheduler_symbol_promotion": {
            "status": "sem_promocao",
            "motivo": "sem promoção ativa no scheduler",
        }
    }
    result = evaluate_status_payload(
        payload,
        fail_on_statuses=("reprovado", "sem_promocao"),
        allow_sem_promocao_in_demo=True,
        now=datetime(2026, 4, 7, 11, 5),
    )
    assert result.ok is True
    assert result.status == "sem_promocao"
    assert "conta demo" in result.motivo.lower()


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
