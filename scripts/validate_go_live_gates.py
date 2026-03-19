"""Orquestra BL-01, BL-07 e BL-08 para validacao pre-Go-Live."""

from __future__ import annotations

import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.application.release_gates import (
    GoLiveDecision,
    OperationalUATService,
    QualityGateService,
    StagingReadinessService,
)


def _persist_json(path: Path, payload: dict[str, object]) -> None:
    """Escreve um payload JSON com UTF-8 e indentacao legivel."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def executar_go_live_pipeline(
    *,
    base_dir: Path = BASE_DIR,
    output_dir: Path | None = None,
    staging_service: StagingReadinessService | None = None,
    quality_service: QualityGateService | None = None,
    uat_service: OperationalUATService | None = None,
) -> GoLiveDecision:
    """Executa os gates canonicos e persiste as evidencias locais."""
    release_dir = output_dir or (base_dir / "outputs" / "release_gates")
    staging = staging_service or StagingReadinessService(base_dir=base_dir)
    quality = quality_service or QualityGateService()

    staging_report = staging.executar()
    _persist_json(release_dir / "bl01_staging_readiness.json", staging_report.para_dict())

    quality_report = quality.executar()
    _persist_json(release_dir / "bl07_quality_gate.json", quality_report.para_dict())

    uat = uat_service or OperationalUATService(
        base_dir=base_dir,
        evidence_dir=release_dir,
    )
    uat_report = uat.executar()
    _persist_json(release_dir / "bl08_uat_operacional.json", uat_report.para_dict())

    decision = GoLiveDecision.from_gates(
        gates=(staging_report, quality_report, uat_report),
    )

    _persist_json(release_dir / "go_live_decision.json", decision.para_dict())

    return decision


def main() -> int:
    """Executa os gates canonicos e grava a decisao final."""
    decision = executar_go_live_pipeline(base_dir=BASE_DIR)

    for gate in decision.gates:
        status = "OK" if gate.aprovado else "FAIL"
        print(f"[{gate.nome.upper()}] {status}")
        for item in gate.resultados:
            item_status = "OK" if item.sucesso else "FAIL"
            print(f" - [{item_status}] {item.nome}: {item.mensagem}")

    print(f"[GO-LIVE] DECISAO: {decision.decisao}")
    print(f"[GO-LIVE] Artefato salvo: {BASE_DIR / 'outputs' / 'release_gates' / 'go_live_decision.json'}")
    return 0 if decision.aprovado else 1


if __name__ == "__main__":
    raise SystemExit(main())
