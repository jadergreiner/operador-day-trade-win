"""
Quick Start - Inicia ambos os diarios AGORA.

Nao espera horario de mercado. Roda imediatamente.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import subprocess
import time
from datetime import datetime


def main():
    """Start both journals immediately."""

    print("=" * 80)
    print("INICIANDO DIARIOS AUTOMATICOS")
    print("=" * 80)
    print()
    print(f"Horario: {datetime.now().strftime('%H:%M:%S')}")
    print()

    # Start trading journal
    print("[1/2] Iniciando Diario de Trading Storytelling (15min)...")
    trading_process = subprocess.Popen(
        [sys.executable, str(project_root / "scripts" / "continuous_journal.py")],
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
    )
    print(f"      PID: {trading_process.pid}")
    print("      [OK] Rodando em janela separada")
    print()

    time.sleep(2)

    # Start AI reflection
    print("[2/2] Iniciando Diario de Reflexao da IA (10min)...")
    ai_process = subprocess.Popen(
        [sys.executable, str(project_root / "scripts" / "ai_reflection_continuous.py")],
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
    )
    print(f"      PID: {ai_process.pid}")
    print("      [OK] Rodando em janela separada")
    print()

    print("=" * 80)
    print("AMBOS OS DIARIOS ESTAO RODANDO!")
    print("=" * 80)
    print()
    print("Dois processos ativos:")
    print(f"  1. Trading Journal (PID {trading_process.pid}) - A cada 15min")
    print(f"  2. AI Reflection   (PID {ai_process.pid}) - A cada 10min")
    print()
    print("Cada diario esta em sua propria janela.")
    print("Feche as janelas ou use Ctrl+C para parar.")
    print()
    print("Pressione Enter para fechar este launcher...")

    input()

    print("Launcher encerrado. Os diarios continuam rodando.")


if __name__ == "__main__":
    main()
