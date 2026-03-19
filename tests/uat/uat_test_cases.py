#!/usr/bin/env python3
"""Runner de BL-08 para validar evidencias operacionais do produto atual.

O runner nao simula mercados antigos, datas historicas vencidas ou mocks
enganosos.
Ele apenas consolida evidencias locais do runtime WIN/WIN$N e dos 4 agentes
operacionais, gerando saida JSON serializavel em `outputs/release_gates/`.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.application.release_gates import OperationalUATService


def _persist_json(path: Path, payload: dict[str, object]) -> None:
    """Salva um payload JSON com UTF-8 e indentacao legivel."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def executar_uat_operacional(
    *,
    base_dir: Path = BASE_DIR,
    evidence_dir: Path | None = None,
) -> dict[str, object]:
    """Executa o BL-08 com evidencias locais e retorna o payload serializavel."""
    servico = OperationalUATService(base_dir=base_dir, evidence_dir=evidence_dir)
    relatorio = servico.executar()
    payload = relatorio.para_dict()
    pasta_relatorios = evidence_dir or (base_dir / "outputs" / "release_gates")
    _persist_json(pasta_relatorios / "bl08_uat_operacional.json", payload)
    return payload


def main() -> int:
    """Executa o BL-08 e imprime o resumo operacional."""
    payload = executar_uat_operacional()

    print("[BL-08] UAT OPERACIONAL")
    for item in payload["resultados"]:
        status = "OK" if item["sucesso"] else "FAIL"
        print(f" - [{status}] {item['nome']}: {item['mensagem']}")

    destino = BASE_DIR / "outputs" / "release_gates" / "bl08_uat_operacional.json"
    print(f"[BL-08] Evidencia salva: {destino}")
    return 0 if payload["aprovado"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
