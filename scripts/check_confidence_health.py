#!/usr/bin/env python3
"""
P50-A: Detector de Pessimismo Crônico - Check Confidence Health

Detecta padrão pessimista onde confidence fica < 0.45 por 10+ ciclos consecutivos.
Se pessimismo detectado, retorna exit code 0 (sucesso) para trigger reset automático.
Se saudável, retorna exit code 1 (sem ação necessária).

Funcione em AMBAS opções (1 e 2) - roda ANTES da escolha de modo.

Uso:
  python scripts/check_confidence_health.py

Saída:
  - Console: Diagnóstico claro
  - Arquivo: data/logs/check_confidence_health.log
  - Exit Code: 0 (pessimismo detectado) | 1 (saudável)

Exemplo de Retorno:
  [09:35:22] ⚠️ PESSIMISMO DETECTADO
  Confidence: 0.34 (últimos 15 ciclos < 0.45)
  Auto-reset em ação...

  Exit code: 0 ✅
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from decimal import Decimal
from typing import Optional

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_DIR = DATA_DIR / "db"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = DATA_DIR / "logs"

# Create logs directory if not exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / "check_confidence_health.log"
SESSION_SUMMARY_FILE = DB_DIR / "last_session_summary.json"
PESSIMISM_CONFIG_FILE = CONFIG_DIR / "pessimism_mode.json"
CONFIDENCE_HISTORY_FILE = CONFIG_DIR / "confidence_history.json"


def log_message(message: str) -> None:
    """Log message to file and console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"

    print(formatted)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")


def load_confidence_history() -> list[float]:
    """Load 20-cycle confidence history from file or create new."""
    if CONFIDENCE_HISTORY_FILE.exists():
        try:
            with open(CONFIDENCE_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("history", [])
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_confidence_history(history: list[float]) -> None:
    """Save confidence history to file (keep last 20 cycles)."""
    history = history[-20:]  # Keep only last 20

    data = {
        "timestamp": datetime.now().isoformat(),
        "history": history,
        "count": len(history)
    }

    with open(CONFIDENCE_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_last_decision_confidence() -> Optional[float]:
    """Get confidence value from last decision in session summary."""
    if not SESSION_SUMMARY_FILE.exists():
        return None

    try:
        with open(SESSION_SUMMARY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

            # Get last decision
            decisions = data.get("decisions", [])
            if decisions:
                last_decision = decisions[-1]
                confidence = last_decision.get("confidence")

                if confidence is not None:
                    # Convert Decimal string or float
                    if isinstance(confidence, str):
                        return float(Decimal(confidence))
                    return float(confidence)
    except (json.JSONDecodeError, IOError, ValueError):
        pass

    return None


def detect_pessimism(history: list[float]) -> tuple[bool, int, float]:
    """
    Detect chronic pessimism pattern.

    Returns:
        (is_pessimism_detected, consecutive_low_count, avg_confidence)
    """
    if not history or len(history) < 5:
        return False, 0, 0.0

    # Count consecutive cycles with confidence < 0.45
    consecutive_low = 0
    for confidence in reversed(history):
        if confidence < 0.45:
            consecutive_low += 1
        else:
            break

    # Calculate average confidence
    avg_conf = sum(history) / len(history) if history else 0.0

    # Pessimism detected if:
    # - 10+ consecutive cycles with confidence < 0.45, OR
    # - 15+ total samples with average < 0.40
    is_pessimism = (
        consecutive_low >= 10 or
        (len(history) >= 15 and avg_conf < 0.40)
    )

    return is_pessimism, consecutive_low, avg_conf


def save_pessimism_config(detected: bool, confidence: float, consecutive_count: int) -> None:
    """Save pessimism detection state to config file."""
    data = {
        "timestamp": datetime.now().isoformat(),
        "pessimism_detected": detected,
        "last_confidence": confidence,
        "consecutive_low_cycles": consecutive_count,
        "threshold_reduced": detected,
        "threshold_up": 3 if detected else 4,
        "threshold_down": -3 if detected else -4
    }

    with open(PESSIMISM_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main() -> int:
    """
    Main health check logic.

    Returns:
        0 = Pessimism detected (trigger reset)
        1 = System healthy (no action)
        2 = Error/unable to determine
    """
    try:
        # Load current confidence from last decision
        current_conf = load_last_decision_confidence()

        if current_conf is None:
            log_message("⚠️ Sem histórico de decisões ainda (primeiro startup)")
            save_pessimism_config(False, 0.0, 0)
            return 1  # No pessimism (can't detect yet)

        # Load confidence history
        history = load_confidence_history()
        history.append(current_conf)

        # Detect pessimism
        is_pessimism, consecutive_low, avg_conf = detect_pessimism(history)

        # Save updated history
        save_confidence_history(history)

        # Save pessimism config
        save_pessimism_config(is_pessimism, current_conf, consecutive_low)

        # Log result
        if is_pessimism:
            log_message(
                f"🔴 PESSIMISMO DETECTADO\n"
                f"  Confidence atual: {current_conf:.2f} (limite: <0.45)\n"
                f"  Ciclos consecutivos baixos: {consecutive_low}\n"
                f"  Média histórica: {avg_conf:.2f}\n"
                f"  → Auto-reset ativado (thresholds reduzidos)"
            )
            return 0  # Pessimism detected - trigger reset
        else:
            log_message(
                f"✅ Sistema saudável\n"
                f"  Confidence: {current_conf:.2f} (OK)\n"
                f"  Média histórica: {avg_conf:.2f}\n"
                f"  → Nenhuma ação necessária"
            )
            return 1  # Healthy - no action needed

    except Exception as e:
        log_message(f"❌ ERRO ao verificar saúde: {e}")
        return 2  # Error


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
