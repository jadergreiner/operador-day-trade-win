"""Testes unitarios para o macro guardian universal."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.application.macro_guardian_universal_log import (
    persist_macro_guardian_events,
)
from src.application.universal_kill_switch import UniversalKillSwitch


def _make_event(
    *,
    timestamp: datetime,
    severity: str,
    tipo_evento: str,
    descricao: str,
    score_impacto: float,
    kill_switch_ativo: bool = False,
    source: str = "macro_scenario_guardian",
) -> dict[str, object]:
    """Cria um evento canonico para persistencia no log do guardian."""
    return {
        "timestamp": timestamp.isoformat(timespec="seconds"),
        "severity": severity,
        "tipo_evento": tipo_evento,
        "descricao": descricao,
        "score_impacto": score_impacto,
        "kill_switch_ativo": kill_switch_ativo,
        "source": source,
        "action": "MONITOR",
    }


def _create_guardian(db_path: Path):
    """Importa o modulo alvo dentro do teste para manter o contrato explicito."""
    from src.application.macro_guardian_universal import MacroGuardianUniversal

    return MacroGuardianUniversal(
        db_path=db_path,
        operational_context_dir=db_path.parent / "analysis_vazio",
    )


class TestMacroGuardianUniversal:
    """Cobertura do snapshot macro universal e export de features."""

    def test_snapshot_sem_eventos_retorna_estado_neutro(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "guardian.db"
            guardian = _create_guardian(db_path)

            snapshot = guardian.build_snapshot()
            features = guardian.export_features(snapshot)

            assert snapshot.total_eventos == 0
            assert snapshot.alertas_ativos == 0
            assert snapshot.kill_switch_ativo is False
            assert snapshot.kill_switch_reason == ""
            assert snapshot.regime_macro == "ESTAVEL"
            assert snapshot.score_guardian == pytest.approx(0.0)
            assert snapshot.to_feature_dict() == features
            assert features["score_guardian"] == pytest.approx(0.0)
            assert features["alertas_ativos"] == 0
            assert features["kill_switch_ativo"] is False
            assert features["regime_macro"] == "ESTAVEL"

    def test_snapshot_com_eventos_persistidos_em_sqlite_temporal(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "guardian.db"
            now = datetime.utcnow()
            persist_macro_guardian_events(
                db_path,
                [
                    _make_event(
                        timestamp=now - timedelta(minutes=12),
                        severity="INFO",
                        tipo_evento="NORMALIZACAO",
                        descricao="cenario estavel",
                        score_impacto=12.0,
                    ),
                    _make_event(
                        timestamp=now - timedelta(minutes=6),
                        severity="WARNING",
                        tipo_evento="VOLATILIDADE",
                        descricao="alerta moderado",
                        score_impacto=48.0,
                    ),
                    _make_event(
                        timestamp=now - timedelta(minutes=1),
                        severity="CRITICAL",
                        tipo_evento="DOLAR_AGRESSAO",
                        descricao="risco extremo",
                        score_impacto=92.0,
                        kill_switch_ativo=True,
                    ),
                ],
            )

            guardian = _create_guardian(db_path)
            snapshot = guardian.build_snapshot(lookback_minutes=30)

            assert snapshot.total_eventos == 3
            assert snapshot.alertas_ativos == 2
            assert snapshot.kill_switch_ativo is True
            assert snapshot.regime_macro == "CRITICO"
            assert snapshot.score_guardian == pytest.approx((12.0 + 48.0 + 92.0) / 3.0)
            assert "CRITICAL" in snapshot.kill_switch_reason
            assert "kill_switch_ativo=True" in snapshot.kill_switch_reason or "kill_switch" in snapshot.kill_switch_reason.lower()

            payload = snapshot.to_dict()
            assert payload["total_eventos"] == 3
            assert payload["kill_switch_ativo"] is True
            assert json.dumps(payload, ensure_ascii=False)

    def test_integracao_com_universal_kill_switch_por_evento_critical(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "guardian.db"
            now = datetime.utcnow()
            persist_macro_guardian_events(
                db_path,
                [
                    _make_event(
                        timestamp=now - timedelta(minutes=3),
                        severity="WARNING",
                        tipo_evento="ALERTA",
                        descricao="alerta leve",
                        score_impacto=20.0,
                    ),
                    _make_event(
                        timestamp=now - timedelta(minutes=1),
                        severity="CRITICAL",
                        tipo_evento="KILL_SWITCH",
                        descricao="bloqueio imediato",
                        score_impacto=99.0,
                    ),
                ],
            )

            guardian = _create_guardian(db_path)
            snapshot = guardian.build_snapshot()

            expected = UniversalKillSwitch().evaluate(snapshot.recent_events)

            assert snapshot.kill_switch_ativo is True
            assert expected.active is True
            assert expected.severity == "CRITICAL"
            assert "CRITICAL" in snapshot.kill_switch_reason
            assert "PAUSE_NEW_ENTRIES" in expected.actions

    def test_integracao_com_universal_kill_switch_por_flag_explicita(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "guardian.db"
            now = datetime.utcnow()
            persist_macro_guardian_events(
                db_path,
                [
                    _make_event(
                        timestamp=now - timedelta(minutes=2),
                        severity="INFO",
                        tipo_evento="NORMAL",
                        descricao="operacao em observacao",
                        score_impacto=14.0,
                    ),
                    _make_event(
                        timestamp=now - timedelta(minutes=1),
                        severity="WARNING",
                        tipo_evento="FLAG_ESPECIAL",
                        descricao="risco operacional",
                        score_impacto=33.0,
                        kill_switch_ativo=True,
                    ),
                ],
            )

            guardian = _create_guardian(db_path)
            snapshot = guardian.build_snapshot()

            assert snapshot.kill_switch_ativo is True
            assert "kill_switch_ativo=True" in snapshot.kill_switch_reason
            assert snapshot.regime_macro == "CRITICO"

    def test_export_features_for_agents_contains_core_fields_and_is_serializable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "guardian.db"
            now = datetime.utcnow()
            persist_macro_guardian_events(
                db_path,
                [
                    _make_event(
                        timestamp=now - timedelta(minutes=4),
                        severity="INFO",
                        tipo_evento="CALMA",
                        descricao="mercado neutro",
                        score_impacto=5.0,
                    ),
                    _make_event(
                        timestamp=now - timedelta(minutes=1),
                        severity="WARNING",
                        tipo_evento="ATENCAO",
                        descricao="alerta moderado",
                        score_impacto=25.0,
                    ),
                ],
            )

            guardian = _create_guardian(db_path)
            snapshot = guardian.build_snapshot()
            features = guardian.export_features(snapshot)

            assert features["score_guardian"] == pytest.approx(snapshot.score_guardian)
            assert features["alertas_ativos"] == snapshot.alertas_ativos
            assert features["regime_macro"] == snapshot.regime_macro
            assert features["kill_switch_ativo"] == snapshot.kill_switch_ativo
            assert features["kill_switch_reason"] == snapshot.kill_switch_reason
            assert json.loads(json.dumps(features, ensure_ascii=False))["score_guardian"] == pytest.approx(
                snapshot.score_guardian
            )

    def test_carrega_contexto_operacional_bdi_e_gera_prompt_curto(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "guardian.db"
            context_dir = Path(tmpdir) / "analysis"
            context_dir.mkdir(parents=True, exist_ok=True)
            context_file = context_dir / "BDI_CONTEXTO_AGENTES_20260319.json"
            context_file.write_text(
                json.dumps(
                    {
                        "report_date": "2026-03-19",
                        "market_state": {
                            "regime_macro": "CAUTELOSO",
                            "intraday_bias": "NEUTRO_LEVEMENTE_BAIXISTA",
                        },
                        "watchlist": ["PETR4", "VALE3", "DOL"],
                        "rates_fx": {
                            "fx_reference_band": [5.21, 5.22],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            from src.application.macro_guardian_universal import MacroGuardianUniversal

            guardian = MacroGuardianUniversal(
                db_path=db_path,
                operational_context_dir=context_dir,
            )

            snapshot = guardian.build_snapshot()
            features = guardian.export_features(snapshot)

            assert snapshot.regime_macro == "CAUTELOSO"
            assert snapshot.vies_intraday == "NEUTRO_LEVEMENTE_BAIXISTA"
            assert snapshot.watchlist == ["PETR4", "VALE3", "DOL"]
            assert "PETR4 + VALE3 + DOL comportado" in snapshot.prompt_abertura_agentes
            assert "Monitorar EWZ e IBOV" in snapshot.prompt_abertura_agentes
            assert features["prompt_abertura_agentes"] == snapshot.prompt_abertura_agentes
            assert features["opening_prompt"] == snapshot.prompt_abertura_agentes
            assert snapshot.metadata["operational_context_loaded"] is True
