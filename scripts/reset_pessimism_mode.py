#!/usr/bin/env python3
"""
P50-A: Auto-Reset Pessimism Mode

Reduz thresholds quando pessimismo é detectado por check_confidence_health.py.

Mudança de Thresholds:
  - Normal: buy_threshold = +4, sell_threshold = -4
  - Pessimismo: buy_threshold = +3, sell_threshold = -3
  
Esta redução permite que operações com scores menos extremos sejam geradas.

Impacto no Agente:
  - Operações que eram rejeitadas agora passam
  - Ex: macro_score=2.5 não passava em +4, passa em +3
  - Sistema volta a gerar sinais (~15-20/dia esperado)

Uso:
  python scripts/reset_pessimism_mode.py

Saída:
  - Console: Confirmação de reset
  - Arquivo: data/logs/reset_pessimism_mode.log
  - Config: config/pessimism_mode.json (persiste estado)

Fluxo de Integração:
  INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
    ├─ check_confidence_health.py (exit 0 = pessimismo detectado)
    └─ reset_pessimism_mode.py (auto-call se exit 0)
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = DATA_DIR / "logs"

# Create logs directory if not exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / "reset_pessimism_mode.log"
PESSIMISM_CONFIG_FILE = CONFIG_DIR / "pessimism_mode.json"


def log_message(message: str, level: str = "INFO") -> None:
    """Log message to file and console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [{level}] {message}"
    
    print(formatted)
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")


def load_pessimism_config() -> dict:
    """Load current pessimism configuration."""
    if PESSIMISM_CONFIG_FILE.exists():
        try:
            with open(PESSIMISM_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    return {
        "timestamp": datetime.now().isoformat(),
        "pessimism_detected": False,
        "last_confidence": 0.0,
        "consecutive_low_cycles": 0,
        "threshold_reduced": False,
        "threshold_up": 4,
        "threshold_down": -4
    }


def reset_thresholds() -> dict:
    """
    Reset thresholds when pessimism detected.
    
    Returns:
        Updated config with reduced thresholds
    """
    config = load_pessimism_config()
    
    # Apply reset: thresholds reduced by 1
    previous_up = config.get("threshold_up", 4)
    previous_down = config.get("threshold_down", -4)
    
    config.update({
        "timestamp": datetime.now().isoformat(),
        "threshold_reduced": True,
        "threshold_up": max(2, previous_up - 1),  # 4 → 3, floor at 2
        "threshold_down": min(-2, previous_down + 1),  # -4 → -3, ceil at -2
        "reset_reason": "Pessimismo detectado - auto-reset em ação",
        "reset_timestamp": datetime.now().isoformat()
    })
    
    return config


def save_pessimism_config(config: dict) -> bool:
    """Save updated config to file."""
    try:
        with open(PESSIMISM_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        log_message(f"Erro salvando config: {e}", level="ERROR")
        return False


def main() -> int:
    """
    Reset pessimism mode and update thresholds.
    
    Returns:
        0 = Success
        1 = Failure
    """
    try:
        # Load current config
        old_config = load_pessimism_config()
        old_up = old_config.get("threshold_up", 4)
        old_down = old_config.get("threshold_down", -4)
        
        # Reset thresholds
        new_config = reset_thresholds()
        new_up = new_config.get("threshold_up", 3)
        new_down = new_config.get("threshold_down", -3)
        
        # Save updated config
        if not save_pessimism_config(new_config):
            log_message("Falha ao persistir configuração", level="ERROR")
            return 1
        
        # Log success
        log_message(
            f"✅ PESSIMISMO RESET EXECUTADO\n"
            f"  Thresholds ajustados:\n"
            f"    BUY:  {old_up:+.0f} → {new_up:+.0f}\n"
            f"    SELL: {old_down:+.0f} → {new_down:+.0f}\n"
            f"  → Operações voltam a ser geradas\n"
            f"  → Expect ~15-20 sinais/dia",
            level="SUCCESS"
        )
        
        # Console output for operator
        print()
        print("=" * 60)
        print("🟢 P50-A: PESSIMISMO RESET - OPERAÇÕES REATIVADAS")
        print("=" * 60)
        print(f"Thresholds: {old_up:+.0f}/{old_down:+.0f} → {new_up:+.0f}/{new_down:+.0f}")
        print(f"Status: Pronto para opção 1 ou 2")
        print("=" * 60)
        print()
        
        return 0
    
    except Exception as e:
        log_message(f"Erro durante reset: {e}", level="ERROR")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
