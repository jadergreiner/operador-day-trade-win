"""Integracao do launcher real ate a auditoria do contexto de abertura."""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import sys
import types
from pathlib import Path


def test_launcher_main_gera_auditoria_e_injeta_contexto(
    tmp_path: Path,
    monkeypatch,
) -> None:
    fake_agent = types.ModuleType("agente_micro_tendencia_winfut")
    execution_state = {"ran": False}

    def _fake_main() -> None:
        execution_state["ran"] = True

    fake_agent.main = _fake_main  # type: ignore[attr-defined]
    fake_s2_6 = types.ModuleType("agente_micro_tendencia_s2_6_integrated")
    fake_s2_6.initialize_s2_6_adapter = lambda _url: object()  # type: ignore[attr-defined]
    fake_data_loader = types.ModuleType("src.application.data_loader")
    fake_data_loader.load_and_label = lambda *_args, **_kwargs: None  # type: ignore[attr-defined]

    launcher_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "launch_agent_with_ml_v1_2_3.py"
    )

    monkeypatch.setitem(sys.modules, "agente_micro_tendencia_winfut", fake_agent)
    monkeypatch.setitem(
        sys.modules,
        "agente_micro_tendencia_s2_6_integrated",
        fake_s2_6,
    )
    monkeypatch.setitem(
        sys.modules,
        "src.application.data_loader",
        fake_data_loader,
    )

    spec = importlib.util.spec_from_file_location(
        "launcher_ml_integration_test",
        launcher_path,
    )
    launcher = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(launcher)

    db_dir = tmp_path / "data" / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    context_dir = tmp_path / "analysis"
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

    monkeypatch.setenv("OPENING_CONTEXT_DIR", str(context_dir))
    monkeypatch.setattr(launcher, "root_dir", tmp_path)
    monkeypatch.setattr(launcher, "AGENT_AVAILABLE", True)
    monkeypatch.setattr(launcher, "agente_module", fake_agent)
    monkeypatch.setattr(launcher, "start_api_server_subprocess", lambda: None)
    monkeypatch.setattr(launcher, "start_ati1_ws_subprocess", lambda: None)
    monkeypatch.setattr(launcher, "start_execution_monitor_subprocess", lambda: None)
    monkeypatch.setattr(
        launcher,
        "setup_integrations",
        lambda: {
            "terminal_isolation": False,
            "s2_6": True,
            "ml": False,
            "p0_1_api": False,
            "agent": True,
        },
    )
    monkeypatch.setattr(sys, "argv", ["launch_agent_with_ml_v1_2_3.py", "--auto-trade"])

    launcher.main()

    assert execution_state["ran"] is True
    assert hasattr(fake_agent, "PROMPT_ABERTURA_AGENTES")
    assert hasattr(fake_agent, "OPENING_CONTEXT_POLICY")
    assert hasattr(fake_agent, "OPENING_CONTEXT_FEATURES")

    conn = sqlite3.connect(str(db_dir / "trading.db"))
    try:
        row = conn.execute(
            """
            SELECT agent_name, source, prompt_abertura_agentes
            FROM opening_context_audit
            WHERE agent_name = 'micro_tendencia_launcher'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] == "micro_tendencia_launcher"
    assert row[1] == "launch_agent_with_ml_v1_2_3"
    assert "PETR4 + VALE3 + DOL comportado" in row[2]
