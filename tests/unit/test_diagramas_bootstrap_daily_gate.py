from __future__ import annotations

from pathlib import Path


def test_diagramas_documenta_bootstrap_diario_de_confidence() -> None:
    source = Path("docs/DIAGRAMAS.md").read_text(encoding="utf-8")

    assert "Bootstrap Diario de Confidence" in source
    assert "prints daily_confidence_gate" in source
    assert "INICIAR_AGENTE_RL_5000.bat" in source
