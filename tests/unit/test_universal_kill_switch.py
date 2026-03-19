"""Testes unitarios para o universal kill switch."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from src.application.universal_kill_switch import (
    UniversalKillSwitch,
    UniversalKillSwitchResult,
)


@dataclass
class EventRecord:
    """Estrutura simples para testar suporte a objetos."""

    source: str
    severity: str
    score_impacto: float | None = None
    kill_switch_ativo: bool = False
    category: str = ""
    message: str = ""
    timestamp: str = "2026-03-18T12:00:00"


class TestUniversalKillSwitch:
    """Cobertura do consolidado universal de kill-switch."""

    def test_ativa_por_kill_switch_explicito(self) -> None:
        switch = UniversalKillSwitch()

        result = switch.evaluate(
            [
                {
                    "source": "macro_guardian",
                    "severity": "INFO",
                    "score_impacto": 0.10,
                    "kill_switch_ativo": True,
                    "category": "macro",
                    "message": "bloqueio direto",
                },
                {
                    "source": "risk_validator",
                    "severity": "WARNING",
                    "score_impacto": 0.40,
                    "kill_switch_ativo": False,
                    "category": "risk",
                    "message": "alerta",
                },
            ]
        )

        assert result.active is True
        assert result.severity == "WARNING"
        assert result.trigger_count == 1
        assert result.trigger_sources == ["macro_guardian"]
        assert "kill_switch_ativo=True" in result.reason
        assert "REVIEW_KILL_SWITCH_SOURCE" in result.actions

    def test_ativa_por_evento_critical(self) -> None:
        switch = UniversalKillSwitch()

        result = switch.evaluate(
            [
                {
                    "source": "service_a",
                    "severity": "WARNING",
                    "score_impacto": 0.20,
                    "kill_switch_ativo": False,
                },
                {
                    "source": "service_b",
                    "severity": "CRITICAL",
                    "score_impacto": 0.15,
                    "kill_switch_ativo": False,
                    "message": "falha critica",
                },
            ]
        )

        assert result.active is True
        assert result.severity == "CRITICAL"
        assert result.trigger_count == 1
        assert result.trigger_sources == ["service_b"]
        assert "CRITICAL" in result.reason
        assert "PAUSE_NEW_ENTRIES" in result.actions
        assert "NOTIFY_RISK_CHANNEL" in result.actions

    def test_ativa_por_media_score_impacto_com_objetos(self) -> None:
        switch = UniversalKillSwitch(score_threshold=0.75)

        result = switch.evaluate(
            [
                EventRecord(
                    source="feed_alpha",
                    severity="INFO",
                    score_impacto=0.80,
                    message="impacto alto",
                ),
                EventRecord(
                    source="feed_beta",
                    severity="WARNING",
                    score_impacto=0.90,
                    message="impacto alto",
                ),
            ]
        )

        assert result.active is True
        assert result.severity == "WARNING"
        assert result.trigger_count == 2
        assert result.trigger_sources == ["feed_alpha", "feed_beta"]
        assert result.score_impacto_medio == pytest.approx(0.85)
        assert "media score_impacto" in result.reason
        assert "REDUCE_EXPOSURE" in result.actions

    def test_permanece_inativo_quando_nenhuma_regra_dispara(self) -> None:
        switch = UniversalKillSwitch(score_threshold=0.75)

        result = switch.evaluate(
            [
                {
                    "source": "source_1",
                    "severity": "INFO",
                    "score_impacto": 0.30,
                    "kill_switch_ativo": False,
                },
                {
                    "source": "source_2",
                    "severity": "WARNING",
                    "score_impacto": 0.40,
                    "kill_switch_ativo": False,
                },
            ]
        )

        assert result.active is False
        assert result.severity == "INFO"
        assert result.trigger_count == 0
        assert result.trigger_sources == []
        assert result.actions == ["MONITOR"]
        assert result.score_impacto_medio == pytest.approx(0.35)
        assert "Nenhum gatilho" in result.reason

    def test_to_dict_e_serializacao_json(self) -> None:
        result = UniversalKillSwitchResult(
            active=True,
            reason="teste",
            severity="WARNING",
            trigger_count=2,
            trigger_sources=["a", "b"],
            score_impacto_medio=0.9,
            actions=["PAUSE_NEW_ENTRIES"],
            audit={"nested": {"value": 1}, "generated": True},
        )

        payload = result.to_dict()

        assert payload["active"] is True
        assert payload["reason"] == "teste"
        assert payload["generated_at"]
        assert isinstance(payload["generated_at"], str)
        assert json.loads(json.dumps(payload, ensure_ascii=False))["audit"]["nested"][
            "value"
        ] == 1

    def test_valida_severity_invalida_em_evento(self) -> None:
        switch = UniversalKillSwitch()

        with pytest.raises(ValueError, match="severity invalida"):
            switch.evaluate(
                [
                    {
                        "source": "bad_source",
                        "severity": "ALERT",
                        "score_impacto": 0.10,
                        "kill_switch_ativo": False,
                    }
                ]
            )

    def test_valida_score_invalido_no_construtor(self) -> None:
        with pytest.raises(ValueError, match="score_threshold deve ser numerico"):
            UniversalKillSwitch(score_threshold="alto")

    def test_valida_score_impacto_invalido_em_evento(self) -> None:
        switch = UniversalKillSwitch()

        with pytest.raises(ValueError, match="evento invalido"):
            switch.evaluate(
                [
                    {
                        "source": "bad_score",
                        "severity": "INFO",
                        "score_impacto": "nao_numero",
                        "kill_switch_ativo": False,
                    }
                ]
            )
