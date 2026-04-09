#!/usr/bin/env python3
"""Valida que o launcher está vinculado ao terminal da Clear configurado."""

from __future__ import annotations

import sys
from pathlib import Path

import MetaTrader5 as mt5

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import get_config
from src.infrastructure.terminal_isolation_enforcer import (
    TerminalIsolationViolation,
    initialize_enforcer,
)


def _caminho_equivalente(esperado_exe: str, runtime_path: str) -> bool:
    esperado_dir = Path(esperado_exe).expanduser().resolve().parent
    runtime_dir = Path(runtime_path).expanduser().resolve()
    esperado_norm = str(esperado_dir).replace("\\", "/").lower()
    runtime_norm = str(runtime_dir).replace("\\", "/").lower()
    return esperado_norm == runtime_norm or esperado_norm in runtime_norm or runtime_norm in esperado_norm


def main() -> int:
    config = get_config()
    terminal_path = (config.mt5_terminal_path or "").strip()

    if not terminal_path:
        print("[ERRO] MT5_TERMINAL_PATH nao configurado.")
        return 2

    try:
        enforcer = initialize_enforcer(terminal_path)
        enforcer.validate_before_operation("launcher_preflight")
        status = enforcer.get_isolation_status()

        if not mt5.initialize(path=terminal_path):
            print(f"[ERRO] Falha ao inicializar terminal Clear: {mt5.last_error()}")
            return 2

        info = mt5.terminal_info()
        runtime_path = str(getattr(info, "path", "") or "")
        runtime_name = str(getattr(info, "name", "") or "")
        runtime_company = str(getattr(info, "company", "") or "")
        mt5.shutdown()

        if not runtime_path or not _caminho_equivalente(terminal_path, runtime_path):
            print(
                "[ERRO] O MetaTrader5 nao vinculou ao terminal da Clear esperado. "
                f"Runtime={runtime_path or '[vazio]'}"
            )
            return 2

        identidade = f"{runtime_name} | {runtime_company} | {runtime_path}"
        if "clear" not in identidade.lower():
            print(
                "[ERRO] O terminal ativo nao aparenta ser o da Clear. "
                f"Identidade={identidade}"
            )
            return 2

        print(
            f"[OK] Terminal Clear validado | clear_pids={status['clear_pids']} | "
            f"runtime={runtime_path}"
        )
        if status.get("dangerous_terminals_detected"):
            print(
                "[INFO] Outros terminais MT5 permanecem permitidos: "
                f"{status['dangerous_terminals_detected']}"
            )
        return 0
    except TerminalIsolationViolation as exc:
        print(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
