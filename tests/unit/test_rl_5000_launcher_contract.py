"""Contrato do launcher RL 5000 em modo de produção estrita."""

from __future__ import annotations

from pathlib import Path


def test_launcher_rl_5000_usa_wrapper_confirmacao_e_preflight() -> None:
    launcher = Path("INICIAR_AGENTE_RL_5000.bat").read_text(encoding="utf-8")

    assert "python scripts\\agente_com_supervision.py --sl-tp-mode dinamico" in launcher
    assert "Tem certeza? (S/N): " in launcher
    assert "VALIDAR GO LIVE (BL-01 + BL-07 + BL-08)" in launcher
    assert "python scripts\\system_health_monitor.py" in launcher
    assert "python scripts\\sync_mt5_trades_to_db.py --days-back 3" in launcher
    assert "ORIGINAL - SEM PROTECAO" not in launcher
