#!/usr/bin/env python3
"""Wrapper de compatibilidade para aplicar lições do BDI 12/02 no pregão 13/02."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
GENERIC_SCRIPT = ROOT_DIR / "scripts" / "aplicar_licoes_bdi.py"


def main() -> int:
    cmd = [
        sys.executable,
        str(GENERIC_SCRIPT),
        "--bdi-date",
        "20260212",
        "--target-date",
        "2026-02-13",
    ]

    return subprocess.run(cmd, cwd=str(ROOT_DIR), check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
