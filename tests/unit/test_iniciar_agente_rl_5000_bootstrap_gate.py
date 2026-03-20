from __future__ import annotations

from pathlib import Path


def test_iniciar_agente_rl_5000_exibe_gate_diario_no_bootstrap() -> None:
    source = Path("INICIAR_AGENTE_RL_5000.bat").read_text(encoding="utf-8")

    assert "Gate diario de confidence" in source
    assert ":show_daily_gate" in source
    assert "confidence_override_today.json" in source
