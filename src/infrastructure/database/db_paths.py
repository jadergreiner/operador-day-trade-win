"""Helpers para resolver o SQLite operacional correto por contexto."""

from __future__ import annotations

import os
from pathlib import Path


_DB_ENV_PRIORITY = (
    "DIARIOS_DB_PATH",
    "RL_DIRETO_DB_PATH",
    "RL5000_DB_PATH",
    "MICRO_TENDENCIA_DB_PATH",
    "TRADING_DB_PATH",
    "DB_PATH",
)


def resolve_operational_db_path(
    base_dir: str | Path | None = None,
    default_name: str = "trading.db",
) -> Path:
    """Resolve o banco SQLite operacional a partir do ambiente.

    Prioridade:
    1. Variáveis específicas do launcher
    2. DB_PATH genérico
    3. default_name relativo a base_dir
    """
    for env_name in _DB_ENV_PRIORITY:
        override = os.getenv(env_name, "").strip()
        if override:
            path = Path(override).expanduser()
            return path if path.is_absolute() else (Path(base_dir or ".") / path)

    root = Path(base_dir or ".")
    return root / "data" / "db" / default_name
