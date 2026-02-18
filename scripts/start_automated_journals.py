"""
Sistema Automatizado de Diarios - Inicia ambos os diarios automaticamente.

Gerencia:
1. Diario de Trading (15min) - Narrativa do mercado
2. Diario de Reflexao da IA (10min) - Auto-critica sincera

Roda automaticamente durante o horario de mercado.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import subprocess
import time
from datetime import datetime, time as dt_time
from typing import Optional


class AutomatedJournalManager:
    """Gerenciador automatizado dos diarios."""

    def __init__(self, market_open: dt_time, market_close: dt_time):
        self.market_open = market_open
        self.market_close = market_close
        self.trading_journal_process: Optional[subprocess.Popen] = None
        self.ai_reflection_process: Optional[subprocess.Popen] = None

    def is_market_open(self) -> bool:
        """Check if market is currently open."""
        now = datetime.now().time()
        return self.market_open <= now <= self.market_close

    def start_trading_journal(self):
        """Start trading storytelling journal."""
        print("[INICIANDO] Diario de Trading Storytelling (15min)...")

        self.trading_journal_process = subprocess.Popen(
            [sys.executable, str(project_root / "scripts" / "continuous_journal.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
        )

        print(f"[OK] Trading Journal iniciado - PID: {self.trading_journal_process.pid}")

    def start_ai_reflection(self):
        """Start AI reflection journal."""
        print("[INICIANDO] Diario de Reflexao da IA (10min)...")

        self.ai_reflection_process = subprocess.Popen(
            [sys.executable, str(project_root / "scripts" / "ai_reflection_continuous.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
        )

        print(f"[OK] AI Reflection iniciado - PID: {self.ai_reflection_process.pid}")

    def stop_all(self):
        """Stop all journal processes."""
        print("\n[PARANDO] Todos os diarios...")

        if self.trading_journal_process:
            self.trading_journal_process.terminate()
            print("[OK] Trading Journal parado")

        if self.ai_reflection_process:
            self.ai_reflection_process.terminate()
            print("[OK] AI Reflection parado")

    def check_processes(self) -> tuple[bool, bool]:
        """Check if processes are still running."""
        trading_alive = (
            self.trading_journal_process is not None
            and self.trading_journal_process.poll() is None
        )
        ai_alive = (
            self.ai_reflection_process is not None
            and self.ai_reflection_process.poll() is None
        )
        return trading_alive, ai_alive

    def run_automated(self):
        """Run journals automatically during market hours."""
        print("=" * 80)
        print("SISTEMA AUTOMATIZADO DE DIARIOS")
        print("=" * 80)
        print()
        print(f"Horario de Mercado: {self.market_open.strftime('%H:%M')} - {self.market_close.strftime('%H:%M')}")
        print()
        print("Diarios:")
        print("  1. Trading Storytelling - A cada 15 minutos")
        print("  2. Reflexao da IA - A cada 10 minutos")
        print()
        print("Pressione Ctrl+C para parar")
        print()

        try:
            # Wait for market to open
            while not self.is_market_open():
                now = datetime.now()
                print(f"[{now.strftime('%H:%M:%S')}] Aguardando abertura do mercado...")
                time.sleep(60)  # Check every minute

            # Start both journals
            print()
            print("=" * 80)
            print("MERCADO ABERTO - INICIANDO DIARIOS")
            print("=" * 80)
            print()

            self.start_trading_journal()
            time.sleep(2)  # Small delay between starts
            self.start_ai_reflection()

            print()
            print("[OK] Ambos os diarios estao rodando!")
            print()
            print("Monitorando processos...")
            print()

            # Monitor processes
            last_check = datetime.now()

            while self.is_market_open():
                time.sleep(30)  # Check every 30 seconds

                trading_alive, ai_alive = self.check_processes()

                now = datetime.now()

                # Restart if crashed
                if not trading_alive:
                    print(f"[{now.strftime('%H:%M:%S')}] [AVISO] Trading Journal parou. Reiniciando...")
                    self.start_trading_journal()

                if not ai_alive:
                    print(f"[{now.strftime('%H:%M:%S')}] [AVISO] AI Reflection parou. Reiniciando...")
                    self.start_ai_reflection()

                # Status update every 5 minutes
                if (now - last_check).seconds >= 300:
                    print(f"[{now.strftime('%H:%M:%S')}] Status: Trading={'ATIVO' if trading_alive else 'INATIVO'} | IA={'ATIVO' if ai_alive else 'INATIVO'}")
                    last_check = now

            # Market closed
            print()
            print("=" * 80)
            print("MERCADO FECHADO - PARANDO DIARIOS")
            print("=" * 80)
            print()

            self.stop_all()

            print()
            print("Sistema encerrado. Ate amanha!")
            print()

        except KeyboardInterrupt:
            print()
            print("=" * 80)
            print("INTERROMPIDO PELO USUARIO")
            print("=" * 80)
            print()
            self.stop_all()
            print()


def main():
    """Main entry point."""

    # Brazilian market hours: 09:00 - 17:30 (Brasilia time)
    market_open = dt_time(9, 0)
    market_close = dt_time(17, 30)

    manager = AutomatedJournalManager(market_open, market_close)
    manager.run_automated()


if __name__ == "__main__":
    main()
