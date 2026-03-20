from __future__ import annotations

from pathlib import Path


def test_iniciar_diarios_bat_exibe_gate_diario_no_bootstrap() -> None:
    source = Path("INICIAR_DIARIOS.bat").read_text(encoding="utf-8")

    assert "Gate diario de confidence (bootstrap)" in source
    assert "confidence_override_today.json" in source
