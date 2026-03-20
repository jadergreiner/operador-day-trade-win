from __future__ import annotations

from pathlib import Path


def test_main_banner_exibe_gate_diario() -> None:
    source = Path("scripts/start_journals_full_display.py").read_text(encoding="utf-8")

    assert "print(f\"Gate diario de confidence: {_current_daily_confidence_gate():.0%}\")" in source
    assert "print(\"Iniciando 5 diários em paralelo...\")" in source
