"""Valida BL-07: gate de qualidade para release."""

from __future__ import annotations

import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.application.release_gates import QualityGateService


def main() -> int:
    """Executa gate de qualidade e persiste evidencia em JSON."""
    servico = QualityGateService()
    relatorio = servico.executar()

    print("[BL-07] QUALITY GATE")
    for item in relatorio.resultados:
        status = "OK" if item.sucesso else "FAIL"
        print(f" - [{status}] {item.nome}: {item.mensagem}")

    pasta_relatorios = BASE_DIR / "outputs" / "release_gates"
    pasta_relatorios.mkdir(parents=True, exist_ok=True)
    destino = pasta_relatorios / "bl07_quality_gate.json"
    destino.write_text(
        json.dumps(relatorio.para_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[BL-07] Evidencia salva: {destino}")
    return 0 if relatorio.aprovado else 1


if __name__ == "__main__":
    raise SystemExit(main())
