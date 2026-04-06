"""Contrato do launcher RL Direto em modo de produção estrita."""

from __future__ import annotations

from pathlib import Path


def test_launcher_rl_direto_usa_preflight_e_gate_promocao() -> None:
    launcher = Path("INICIAR_AGENTE_RL_DIRETO.bat").read_text(encoding="utf-8")

    assert "python scripts\\agente_rl_direto_independente.py --mode dinamico" in launcher
    assert "Tem certeza? (S/N): " in launcher
    assert "python scripts\\system_health_monitor.py" in launcher
    assert (
        "python scripts\\check_scheduler_promotion_gate.py --fallback-latest-promotion --fail-on reprovado"
        in launcher
    )
    assert "python scripts\\sync_mt5_trades_to_db.py --db \"%RL_DIRETO_DB_PATH%\" --days-back 3 --lock-timeout 0" in launcher
