"""Check automatizado do gate de promocao do scheduler para operacao/CI.

Exemplos:
    python scripts/check_scheduler_promotion_gate.py
    python scripts/check_scheduler_promotion_gate.py --status-file outputs/status_snapshot.json
    python scripts/check_scheduler_promotion_gate.py --fail-on reprovado,sem_promocao
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

from src.application.scheduler_promotion_healthcheck import (  # noqa: E402
    evaluate_status_payload,
    load_status_payload_from_file,
    load_status_payload_from_latest_promotion_file,
    load_status_payload_from_url,
)


def _parse_fail_on(raw: str) -> tuple[str, ...]:
    parts = [item.strip().lower() for item in raw.split(",")]
    cleaned = tuple(item for item in parts if item)
    return cleaned or ("reprovado",)


def _ler_variavel_env_local(chave: str) -> str:
    """Lê uma variável do ambiente atual ou do arquivo `.env` do projeto."""
    valor = os.getenv(chave, "").strip()
    if valor:
        return valor

    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return ""

    for linha in env_path.read_text(encoding="utf-8").splitlines():
        texto = linha.strip()
        if not texto or texto.startswith("#") or "=" not in texto:
            continue
        nome, conteudo = texto.split("=", 1)
        if nome.strip() == chave:
            return conteudo.strip()
    return ""


def _conta_demo_ativa() -> bool:
    """Detecta se a operação atual está apontando para servidor demo."""
    candidatos = (
        _ler_variavel_env_local("MT5_SERVER"),
        _ler_variavel_env_local("MT5_WINFUT_SERVER"),
    )
    return any("demo" in valor.strip().lower() for valor in candidatos if valor)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status-url", default="http://localhost:8765/status")
    parser.add_argument("--status-file", default="")
    parser.add_argument("--fallback-latest-promotion", action="store_true")
    parser.add_argument("--outputs-dir", default="outputs")
    parser.add_argument("--timeout-seconds", type=float, default=3.0)
    parser.add_argument("--fail-on", default="reprovado")
    parser.add_argument(
        "--allow-sem-promocao-until",
        default=os.getenv("PROMOTION_GATE_ALLOW_SEM_PROMOCAO_UNTIL", ""),
        help="Horário HH:MM em que `sem_promocao` ainda é tolerado (ex.: pre-open).",
    )
    parser.add_argument("--json-output", action="store_true")
    args = parser.parse_args()

    fail_on = _parse_fail_on(args.fail_on)
    if args.status_file:
        payload = load_status_payload_from_file(Path(args.status_file))
        source = f"file:{args.status_file}"
    else:
        try:
            payload = load_status_payload_from_url(args.status_url, args.timeout_seconds)
            source = f"url:{args.status_url}"
        except Exception:
            if not args.fallback_latest_promotion:
                raise
            payload = load_status_payload_from_latest_promotion_file(Path(args.outputs_dir))
            source = f"fallback-file:{args.outputs_dir}"

    conta_demo_ativa = _conta_demo_ativa()
    result = evaluate_status_payload(
        payload,
        fail_on_statuses=fail_on,
        allow_sem_promocao_until=(args.allow_sem_promocao_until or None),
        allow_sem_promocao_in_demo=conta_demo_ativa,
    )
    output = {
        "ok": result.ok,
        "status": result.status,
        "motivo": result.motivo,
        "source": source,
        "fail_on": list(fail_on),
        "allow_sem_promocao_until": args.allow_sem_promocao_until or None,
        "allow_sem_promocao_in_demo": conta_demo_ativa,
    }
    if args.json_output:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(
            f"[PROMO-GATE-CHECK] ok={output['ok']} status={output['status']} "
            f"source={source} motivo={output['motivo'] or '-'}"
        )
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
