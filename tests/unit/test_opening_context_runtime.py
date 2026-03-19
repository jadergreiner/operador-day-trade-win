"""Testes unitarios para runtime e auditoria do contexto de abertura."""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from src.application.opening_context_audit import persist_opening_context_audit
from src.application.opening_context_runtime import initialize_opening_context_runtime


def test_persist_opening_context_audit_grava_registro() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "trading.db")

        row_id = persist_opening_context_audit(
            db_path,
            agent_name="micro_tendencia",
            source="test",
            session_id="sessao_1",
            mode="SIMULATED",
            prompt_abertura_agentes="Comprar so com confirmacao.",
            macro_context={
                "regime_macro": "CAUTELOSO",
                "vies_intraday": "NEUTRO_LEVEMENTE_BAIXISTA",
                "watchlist": ["PETR4", "VALE3"],
            },
        )

        assert row_id > 0

        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                """
                SELECT agent_name, mode, regime_macro, vies_intraday,
                       prompt_abertura_agentes
                FROM opening_context_audit
                WHERE id = ?
                """,
                (row_id,),
            ).fetchone()
        finally:
            conn.close()

        assert row == (
            "micro_tendencia",
            "SIMULATED",
            "CAUTELOSO",
            "NEUTRO_LEVEMENTE_BAIXISTA",
            "Comprar so com confirmacao.",
        )


def test_initialize_opening_context_runtime_carrega_prompt_e_audita() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_root = Path(tmpdir)
        db_path = temp_root / "trading.db"
        context_dir = temp_root / "analysis"
        context_dir.mkdir(parents=True, exist_ok=True)
        context_dir.joinpath("BDI_CONTEXTO_AGENTES_20260319.json").write_text(
            json.dumps(
                {
                    "report_date": "2026-03-19",
                    "market_state": {
                        "regime_macro": "CAUTELOSO",
                        "intraday_bias": "NEUTRO_LEVEMENTE_BAIXISTA",
                    },
                    "watchlist": ["PETR4", "VALE3", "DOL"],
                    "rates_fx": {"fx_reference_band": [5.21, 5.22]},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        printed: list[str] = []
        runtime = initialize_opening_context_runtime(
            db_path=str(db_path),
            agent_name="rl_5000",
            source="test_runtime",
            session_id="agente_1",
            mode="DINAMICO",
            printer=printed.append,
            operational_context_dir=context_dir,
        )

        assert runtime.features["regime_macro"] == "CAUTELOSO"
        assert runtime.features["vies_intraday"] == "NEUTRO_LEVEMENTE_BAIXISTA"
        assert runtime.policy.watchlist == ["PETR4", "VALE3", "DOL"]
        assert runtime.policy.heavyweights == ["PETR4", "VALE3"]
        assert "PETR4 + VALE3 + DOL comportado" in runtime.prompt_abertura_agentes
        assert "Monitorar EWZ e IBOV" in runtime.prompt_abertura_agentes
        assert any("Prompt agentes:" in line for line in printed)

        conn = sqlite3.connect(str(db_path))
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM opening_context_audit WHERE agent_name = 'rl_5000'"
            ).fetchone()[0]
        finally:
            conn.close()

        assert count == 1
