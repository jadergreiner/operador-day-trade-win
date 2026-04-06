"""Testes para promocao manual da calibracao do scheduler runtime."""

from __future__ import annotations

import json
from pathlib import Path

from src.application.rl_scheduler_calibration_promotion import (
    promote_runtime_calibration,
    validate_promotion_gate,
)


def _sample_report() -> dict[str, object]:
    return {
        "recomendacao_por_simbolo": {
            "WIN": {
                "calibracao_recomendada": {
                    "stress_score_trigger": 0.7,
                    "volatilidade_trigger": 75.0,
                    "loss_streak_divisor": 4.0,
                    "media_negativa_scale": 2.0,
                },
                "acertos": 2,
                "total_cenarios": 2,
            },
            "WDO": {
                "calibracao_recomendada": {
                    "stress_score_trigger": 0.6,
                    "volatilidade_trigger": 60.0,
                    "loss_streak_divisor": 3.0,
                    "media_negativa_scale": 2.5,
                },
                "acertos": 2,
                "total_cenarios": 2,
            },
        }
    }


def test_validate_promotion_gate_aprova_relatorio_valido() -> None:
    decision = validate_promotion_gate(_sample_report())
    assert decision.aprovado is True


def test_validate_promotion_gate_reprova_acuracia_baixa() -> None:
    report = _sample_report()
    report["recomendacao_por_simbolo"]["WDO"]["acertos"] = 1  # type: ignore[index]
    decision = validate_promotion_gate(report, min_accuracy=1.0)
    assert decision.aprovado is False


def test_promote_runtime_calibration_escreve_arquivo_destino(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(_sample_report()), encoding="utf-8")
    destination = tmp_path / "runtime.json"
    result = promote_runtime_calibration(
        report_path=report_path,
        destination_path=destination,
        approver="qa_manual",
    )
    assert result["aprovado"] is True
    assert destination.exists()
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["calibracao_por_simbolo"]["WIN"]["stress_score_trigger"] == 0.7


def test_promote_runtime_calibration_dry_run_nao_escreve(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(_sample_report()), encoding="utf-8")
    destination = tmp_path / "runtime.json"
    result = promote_runtime_calibration(
        report_path=report_path,
        destination_path=destination,
        approver="qa_manual",
        dry_run=True,
    )
    assert result["aprovado"] is True
    assert destination.exists() is False
