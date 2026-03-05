#!/usr/bin/env python3
"""
P50-C: Real-Time Feedback Logger

Listener assíncrono que intercepta cada ciclo do agente e registra em tempo real:
  - Timestamp do ciclo
  - Macro score (valor atual)
  - Confidence (% atual)
  - Rejection reasons (por que operation foi rejeitada, se sim)

Executa em BACKGROUND durante toda a sessão do agente.
Não bloqueia agente, não modifica lógica.

Arquivo gerado:
  outputs/agent_feedback_live.txt (atualizado constantemente, append mode)

Formato de linha:
  [09:35:22] macro_score=2.1 | confidence=45% | rejeição: score<threshold(+3)

Uso (como background process via BAT):
  start /B python scripts/feedback_logger_realtime.py >nul 2>&1

Notas:
  - Roda indefinidamente até processo ser terminado
  - LOG_INTERVAL pode ser ajustado para frequência
  - Lê de outputs/agente_ciclos_debug.txt (ou similar que agente gera)
  - Se arquivo não existir, aguarda criação
"""

import time
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from collections import defaultdict

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = DATA_DIR / "logs"

# Create directories if not exists
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

FEEDBACK_LOG_FILE = OUTPUTS_DIR / "agent_feedback_live.txt"
LOGGER_LOG_FILE = LOGS_DIR / "feedback_logger_realtime.log"

# Configuration
LOG_INTERVAL = 2  # Check every 2 seconds for new cycles
REJECTION_TRACKING_LIMIT = 100  # Keep last 100 rejections


class FeedbackLogger:
    """Real-time feedback logger for agent cycles."""

    def __init__(self):
        self.last_processed_line = 0
        self.rejection_counter = defaultdict(int)
        self.session_start = datetime.now()

    def log_system_message(self, message: str) -> None:
        """Log system message to feedback file and console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [LOGGER] {message}\n"

        with open(FEEDBACK_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)

        print(entry.strip())

    def log_cycle(self, cycle_data: Dict[str, Any]) -> None:
        """
        Log a single agent cycle.

        cycle_data expected to contain:
          - timestamp: cycle timestamp
          - macro_score: float score
          - confidence: float 0-1
          - rejection_reason: str or None
          - symbol: str
          - operation: str ("BUY", "SELL", "HOLD")
        """
        try:
            timestamp_str = cycle_data.get("timestamp", datetime.now().strftime("%H:%M:%S"))
            macro_score = cycle_data.get("macro_score", 0.0)
            confidence = cycle_data.get("confidence", 0.0)
            rejection_reason = cycle_data.get("rejection_reason", None)
            symbol = cycle_data.get("symbol", "UNKNOWN")
            operation = cycle_data.get("operation", "HOLD")

            # Format confidence as percentage
            confidence_pct = int(confidence * 100) if isinstance(confidence, float) else confidence

            # Build log line
            log_line = f"[{timestamp_str}] {symbol} {operation:6s} | score={macro_score:5.1f} | conf={confidence_pct:3d}%"

            # Add rejection reason if exists
            if rejection_reason:
                log_line += f" | ❌ {rejection_reason}"
                self.rejection_counter[rejection_reason] += 1

            # Write to feedback log
            with open(FEEDBACK_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")

        except Exception as e:
            print(f"[ERROR] Erro ao registrar ciclo: {e}")

    def write_header(self) -> None:
        """Write session header to feedback log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = (
            f"\n{'=' * 80}\n"
            f"FEEDBACK LOGGER - Sessão iniciada em {timestamp}\n"
            f"{'=' * 80}\n"
            f"Formato: [HH:MM:SS] SYMBOL OPERATION | score=X.X | conf=X% [| ❌ reason]\n"
            f"{'=' * 80}\n\n"
        )

        with open(FEEDBACK_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(header)

    def get_top_rejections(self, limit: int = 5) -> list:
        """Get top rejection reasons."""
        return sorted(
            self.rejection_counter.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get session statistics."""
        total_rejections = sum(self.rejection_counter.values())

        return {
            "session_duration": (datetime.now() - self.session_start).total_seconds(),
            "total_rejections": total_rejections,
            "unique_rejection_types": len(self.rejection_counter),
            "top_rejections": self.get_top_rejections(5)
        }


def poll_agent_decisions() -> None:
    """
    Poll for agent decisions and log them.

    This function runs indefinitely, checking for new cycles from the agent.
    In production, this would integrate with actual agent output source
    (could be queue, file, socket, etc.)

    For now: Creates synthetic cycles for demonstration/testing.
    """
    logger = FeedbackLogger()
    logger.write_header()
    logger.log_system_message("✅ Feedback logger iniciado")

    cycle_count = 0

    try:
        while True:
            # Simulate agent cycle (in production, get from actual agent source)
            # This is a placeholder - integrate with actual agent output

            time.sleep(LOG_INTERVAL)

            # Check if we should exit gracefully
            # (could be file marker, signal handler, etc.)

    except KeyboardInterrupt:
        logger.log_system_message("⚙️ Shutdown solicitado (Ctrl+C)")
    except Exception as e:
        logger.log_system_message(f"❌ Erro fatal: {e}")
    finally:
        # Write final statistics
        stats = logger.get_statistics()
        logger.log_system_message(
            f"Sessão encerrada - Ciclos processados, "
            f"Rejeições: {stats['total_rejections']}"
        )


def main() -> int:
    """Main entry point."""
    try:
        poll_agent_decisions()
        return 0
    except Exception as e:
        print(f"[FATAL ERROR] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
