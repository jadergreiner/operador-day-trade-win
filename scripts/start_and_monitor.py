"""
Start and Monitor Trading - Inicia e monitora trading automatizado.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import subprocess
import time
from datetime import datetime


def main():
    """Start trading system and monitor."""

    print("=" * 80)
    print("INICIANDO TRADING AUTOMATIZADO")
    print("=" * 80)
    print()

    # Start trading process
    # Usar diretório de logs relativo ao projeto ao invés de hardcoded
    log_dir = project_root / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "trading_live.log"

    process = subprocess.Popen(
        [sys.executable, str(project_root / "scripts" / "run_automated_trading.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    print(f"[OK] Sistema iniciado (PID: {process.pid})")
    print()
    print("=" * 80)
    print("MONITORAMENTO EM TEMPO REAL")
    print("=" * 80)
    print()
    print("Pressione Ctrl+C para parar o sistema")
    print()
    print("-" * 80)

    try:
        # Monitor output in real-time
        for line in process.stdout:
            print(line.rstrip())

    except KeyboardInterrupt:
        print()
        print("-" * 80)
        print("PARANDO SISTEMA...")
        print("-" * 80)
        print()

        process.terminate()
        process.wait(timeout=10)

        print("[OK] Sistema parado")
        print()


if __name__ == "__main__":
    main()
