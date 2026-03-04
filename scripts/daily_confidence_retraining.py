#!/usr/bin/env python3
"""
P50-B: Daily Confidence Retraining Loop

Executado diariamente (startup via INICIAR_DIARIOS.bat) para recalcular confidence
baseado em WIN RATE REAL do pregão anterior (não esperado/teórico).

Lógica:
  1. Carrega trades executados do pregão anterior (data/db/trading.db)
  2. Calcula WIN RATE real = (wins / total_trades)
  3. Ajusta confidence incrementalmente:
     - WIN RATE > 60%: confidence += 0.03 (boost positivo)
     - WIN RATE 50-60%: confidence sem mudança
     - WIN RATE < 50%: confidence -= 0.02 (caution/conservador)
  4. Aplica caps/floors:
     - Máximo: 0.65 (não deixar muito otimista)
     - Mínimo: 0.25 (nunca zero)
  5. Persiste novo valor em config/confidence_override_today.json

Impacto:
  - Feedback loop positivo: se trading foi bom, sistema fica mais confiante
  - Evita regressão: se trading foi fraco, sistema mantém cautela
  - Quebra ciclo negativo de pessimismo aprendido

Uso:
  python scripts/daily_confidence_retraining.py

Saída:
  - Console: Transição de confidence com WIN RATE
  - Arquivo: data/logs/daily_confidence_retraining.log
  - Config: config/confidence_override_today.json (novo valor persiste)
"""

import json
import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from decimal import Decimal
from typing import Optional, Tuple

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_DIR = DATA_DIR / "db"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = DATA_DIR / "logs"

# Create logs directory if not exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / "daily_confidence_retraining.log"
TRADING_DB_FILE = DB_DIR / "trading.db"
CONFIDENCE_CONFIG_FILE = CONFIG_DIR / "confidence_override_today.json"

# Constants for confidence adjustment
CONFIDENCE_BOOST_GOOD = Decimal("0.03")  # WR > 60%
CONFIDENCE_PENALTY_POOR = Decimal("0.02")  # WR < 50%
CONFIDENCE_MAX = Decimal("0.65")
CONFIDENCE_MIN = Decimal("0.25")


def log_message(message: str, level: str = "INFO") -> None:
    """Log message to file and console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] [{level}] {message}"
    
    print(formatted)
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")


def load_current_confidence() -> Decimal:
    """Load current confidence from config or default."""
    if CONFIDENCE_CONFIG_FILE.exists():
        try:
            with open(CONFIDENCE_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                conf_val = data.get("confidence_current")
                if conf_val is not None:
                    return Decimal(str(conf_val))
        except (json.JSONDecodeError, IOError, ValueError):
            pass
    
    # Default: neutral confidence
    return Decimal("0.50")


def calculate_previous_day_win_rate() -> Optional[Tuple[float, int, int]]:
    """
    Calculate actual WIN RATE from previous trading day.
    
    Returns:
        (win_rate, wins_count, total_count) or None if no trades
    """
    if not TRADING_DB_FILE.exists():
        return None
    
    try:
        conn = sqlite3.connect(TRADING_DB_FILE)
        cursor = conn.cursor()
        
        # Get yesterday's date (trading might have ended already)
        yesterday = datetime.now().date() - timedelta(days=1)
        yesterday_str = yesterday.strftime("%Y-%m-%d")
        
        # Query trades from yesterday
        # Assuming table has: execution_date (or similar), pnl, status columns
        query = """
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
        FROM trades
        WHERE DATE(execution_date) = ?
            AND status IN ('CLOSED', 'COMPLETED')
        """
        
        cursor.execute(query, (yesterday_str,))
        result = cursor.fetchone()
        conn.close()
        
        if not result or result[0] == 0:
            return None  # No trades yesterday
        
        total_trades = result[0]
        wins = result[1] or 0
        win_rate = wins / total_trades if total_trades > 0 else 0.0
        
        return (win_rate, wins, total_trades)
    
    except (sqlite3.Error, Exception) as e:
        log_message(f"Erro ao consultar trades: {e}", level="ERROR")
        return None


def adjust_confidence(current: Decimal, win_rate: float) -> Decimal:
    """
    Adjust confidence based on win rate.
    
    Rules:
      - WR > 60%: +0.03 boost
      - 50% <= WR <= 60%: no change
      - WR < 50%: -0.02 penalty
    
    Applies caps: [0.25, 0.65]
    """
    new_confidence = current
    adjustment_reason = ""
    
    if win_rate > 0.60:
        new_confidence = current + CONFIDENCE_BOOST_GOOD
        adjustment_reason = f"Boost positivo: WR={win_rate:.1%} > 60%"
    elif win_rate < 0.50:
        new_confidence = current - CONFIDENCE_PENALTY_POOR
        adjustment_reason = f"Penalty conservador: WR={win_rate:.1%} < 50%"
    else:
        adjustment_reason = f"Sem mudança: WR={win_rate:.1%} (50-60%)"
    
    # Apply caps
    new_confidence = max(CONFIDENCE_MIN, min(CONFIDENCE_MAX, new_confidence))
    
    return new_confidence, adjustment_reason


def save_confidence_config(confidence: Decimal, win_rate: float, trades_count: int) -> bool:
    """Save updated confidence to config file."""
    try:
        config = {
            "timestamp": datetime.now().isoformat(),
            "confidence_current": float(confidence),
            "confidence_previous": float(load_current_confidence()),
            "win_rate_last_trading_day": win_rate,
            "trades_count_yesterday": trades_count,
            "retraining_date": datetime.now().date().isoformat(),
            "source": "p50_daily_retraining"
        }
        
        with open(CONFIDENCE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return True
    except IOError as e:
        log_message(f"Erro salvando config: {e}", level="ERROR")
        return False


def main() -> int:
    """
    Main retraining logic.
    
    Returns:
        0 = Success
        1 = No trades to retrain from (still success, just no action)
        2 = Error
    """
    try:
        log_message("Iniciando daily confidence retraining...")
        
        # Load current confidence
        current_conf = load_current_confidence()
        log_message(f"Confidence atual: {float(current_conf):.2f}")
        
        # Get previous day's win rate
        result = calculate_previous_day_win_rate()
        
        if result is None:
            log_message("Sem trades no pregão anterior para retraining", level="WARN")
            return 1  # Not an error, just no action needed
        
        win_rate, wins, total = result
        log_message(
            f"Pregão anterior:\n"
            f"  WIN RATE: {win_rate:.1%} ({wins}/{total} trades)\n",
            level="INFO"
        )
        
        # Adjust confidence
        new_conf, reason = adjust_confidence(current_conf, win_rate)
        
        log_message(
            f"Ajuste de confidence:\n"
            f"  {reason}\n"
            f"  {float(current_conf):.2f} → {float(new_conf):.2f}"
            f" ({new_conf - current_conf:+.2f})",
            level="INFO"
        )
        
        # Save updated config
        if not save_confidence_config(new_conf, win_rate, total):
            log_message("Falha ao persistir configuração", level="ERROR")
            return 2
        
        # Console output
        print()
        print("=" * 60)
        print("🔄 P50-B: DAILY CONFIDENCE RETRAINING")
        print("=" * 60)
        print(f"WIN RATE (anterior): {win_rate:.1%}")
        print(f"Confidence: {float(current_conf):.2f} → {float(new_conf):.2f}")
        print(f"Trades: {total} | Ganhos: {wins}")
        print("=" * 60)
        print()
        
        log_message("Daily retraining concluído com sucesso", level="SUCCESS")
        return 0
    
    except Exception as e:
        log_message(f"Erro durante retraining: {e}", level="ERROR")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
