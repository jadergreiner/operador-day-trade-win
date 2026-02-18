"""
Live Monitor - Monitora sistema de trading em tempo real.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
from datetime import datetime


def monitor_output_file(file_path: str):
    """Monitor output file for new lines."""

    print("=" * 80)
    print("MONITOR DE TRADING AUTOMATIZADO")
    print("=" * 80)
    print()
    print("Monitorando sistema em tempo real...")
    print("Pressione Ctrl+C para parar")
    print()
    print("-" * 80)

    last_position = 0

    try:
        while True:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_position)
                    new_lines = f.readlines()
                    last_position = f.tell()

                    if new_lines:
                        for line in new_lines:
                            print(line.rstrip())

            except FileNotFoundError:
                pass

            time.sleep(1)

    except KeyboardInterrupt:
        print()
        print("-" * 80)
        print("Monitor interrompido")
        print()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        monitor_output_file(sys.argv[1])
    else:
        print("Uso: python live_monitor.py <caminho_do_arquivo>")
