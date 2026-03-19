"""Orquestra BL-01 e BL-07 para validacao pre-Go-Live."""

from __future__ import annotations

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.application.release_gates import QualityGateService, StagingReadinessService


def main() -> int:
    """Executa staging readiness e quality gate em sequencia."""
    staging = StagingReadinessService(base_dir=BASE_DIR).executar()
    if not staging.aprovado:
        print("[GO-LIVE] BL-01 reprovado. Corrija staging antes de continuar.")
        return 1

    quality = QualityGateService().executar()
    if not quality.aprovado:
        print("[GO-LIVE] BL-07 reprovado. Corrija qualidade antes de continuar.")
        return 1

    print("[GO-LIVE] BL-01 + BL-07 aprovados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
