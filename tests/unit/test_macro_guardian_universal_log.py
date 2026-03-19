"""Testes unitários para macro_guardian_universal_log."""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.application.macro_guardian_universal_log import (
    ensure_macro_guardian_log_table,
    fetch_latest_guardian_snapshot,
    fetch_recent_macro_guardian_events,
    persist_macro_guardian_events,
)


class TestMacroGuardianUniversalLog:
    """Cobertura da API universal do Guardian macro."""

    def test_ensure_macro_guardian_log_table_cria_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "guardian.db"

            ensure_macro_guardian_log_table(db_path)

            conn = sqlite3.connect(db_path)
            try:
                rows = conn.execute(
                    "PRAGMA table_info(macro_guardian_log)"
                ).fetchall()
            finally:
                conn.close()

            colunas = [row[1] for row in rows]
            assert colunas == [
                "id",
                "timestamp",
                "severity",
                "tipo_evento",
                "descricao",
                "valor_atual",
                "valor_anterior",
                "score_impacto",
                "action",
                "source",
                "kill_switch_ativo",
                "payload_json",
            ]

    def test_persist_macro_guardian_events_multi_nivel(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "guardian.db"
            base_ts = datetime(2026, 3, 18, 12, 0, 0)
            events = [
                {
                    "timestamp": base_ts.isoformat(),
                    "severity": "INFO",
                    "tipo_evento": "SCENARIO_OK",
                    "descricao": "cenário estável",
                    "valor_atual": 10.5,
                    "valor_anterior": 10.1,
                    "score_impacto": 1.0,
                    "action": "MONITOR",
                    "kill_switch_ativo": False,
                },
                {
                    "timestamp": (base_ts + timedelta(minutes=1)).isoformat(),
                    "severity": "WARNING",
                    "tipo_evento": "DIVERGENCIA",
                    "descricao": "divergência moderada",
                    "valor_atual": 8.4,
                    "valor_anterior": 9.0,
                    "score_impacto": -4.0,
                    "action": "REDUCE_EXPOSURE",
                    "kill_switch_ativo": False,
                },
                {
                    "timestamp": (base_ts + timedelta(minutes=2)).isoformat(),
                    "severity": "CRITICAL",
                    "tipo_evento": "KILL_SWITCH",
                    "descricao": "risco extremo",
                    "valor_atual": 7.2,
                    "valor_anterior": 9.8,
                    "score_impacto": -9.5,
                    "action": "PAUSE_TRADING",
                    "kill_switch_ativo": True,
                },
            ]

            inserted = persist_macro_guardian_events(db_path, events)

            assert inserted == 3

            conn = sqlite3.connect(db_path)
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM macro_guardian_log"
                ).fetchone()[0]
            finally:
                conn.close()

            assert count == 3

    def test_fetch_recent_macro_guardian_events_filtra_severidade(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "guardian.db"
            now = datetime(2026, 3, 18, 12, 0, 0)
            persist_macro_guardian_events(
                db_path,
                [
                    {
                        "timestamp": now.isoformat(),
                        "severity": "INFO",
                        "tipo_evento": "INFO_EVENT",
                        "descricao": "info",
                        "score_impacto": 0.5,
                    },
                    {
                        "timestamp": (now + timedelta(minutes=1)).isoformat(),
                        "severity": "WARNING",
                        "tipo_evento": "WARN_EVENT",
                        "descricao": "warning",
                        "score_impacto": -2.0,
                    },
                    {
                        "timestamp": (now + timedelta(minutes=2)).isoformat(),
                        "severity": "CRITICAL",
                        "tipo_evento": "CRIT_EVENT",
                        "descricao": "critical",
                        "score_impacto": -8.0,
                    },
                ],
            )

            filtered = fetch_recent_macro_guardian_events(
                db_path,
                limit=10,
                severities=["WARNING", "CRITICAL"],
            )

            assert len(filtered) == 2
            assert [event["severity"] for event in filtered] == [
                "CRITICAL",
                "WARNING",
            ]
            assert all("payload_json" in event for event in filtered)

    def test_fetch_latest_guardian_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "guardian.db"
            now = datetime.utcnow()
            old_ts = (now - timedelta(minutes=90)).isoformat(timespec="seconds")
            recent_ts_1 = (now - timedelta(minutes=10)).isoformat(timespec="seconds")
            recent_ts_2 = (now - timedelta(minutes=5)).isoformat(timespec="seconds")
            recent_ts_3 = now.isoformat(timespec="seconds")

            persist_macro_guardian_events(
                db_path,
                [
                    {
                        "timestamp": old_ts,
                        "severity": "CRITICAL",
                        "tipo_evento": "OLD_EVENT",
                        "descricao": "fora da janela",
                        "score_impacto": -20.0,
                        "kill_switch_ativo": True,
                    },
                    {
                        "timestamp": recent_ts_1,
                        "severity": "INFO",
                        "tipo_evento": "RECENT_INFO",
                        "descricao": "ok",
                        "score_impacto": 2.0,
                        "kill_switch_ativo": False,
                    },
                    {
                        "timestamp": recent_ts_2,
                        "severity": "WARNING",
                        "tipo_evento": "RECENT_WARN",
                        "descricao": "alerta",
                        "score_impacto": -4.0,
                        "kill_switch_ativo": False,
                    },
                    {
                        "timestamp": recent_ts_3,
                        "severity": "CRITICAL",
                        "tipo_evento": "RECENT_CRIT",
                        "descricao": "falha grave",
                        "score_impacto": -6.0,
                        "kill_switch_ativo": True,
                    },
                ],
            )

            snapshot = fetch_latest_guardian_snapshot(db_path, lookback_minutes=30)

            assert snapshot["total_eventos"] == 3
            assert snapshot["kill_switch_ativo"] is True
            assert snapshot["alertas_ativos"] == 2
            assert snapshot["regime_macro"] == "CRITICO"
            assert snapshot["score_impacto_medio"] == pytest.approx(-8.0 / 3.0)
