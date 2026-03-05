#!/usr/bin/env python3
"""
FIX #1: Migrar schema do banco de dados.

Adiciona/valida colunas necessárias na tabela trades:
- pnl (already exists but may be named profit_loss)
- profit_loss (already exists)
- wl_status (win/loss indicator)

Execução:
  python scripts/fix_database_schema.py
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DB_DIR = PROJECT_ROOT / "data" / "db"
DB_FILE = DB_DIR / "trading.db"


def log_msg(msg: str, level="INFO"):
    """Log with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def check_table_columns(cursor, table_name: str) -> list:
    """Get all columns in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return [col[1] for col in columns]


def migrate_trades_table():
    """Migrate trades table schema."""
    if not DB_FILE.exists():
        log_msg(f"❌ Database not found: {DB_FILE}", "ERROR")
        return False

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Check current columns
        columns = check_table_columns(cursor, "trades")
        log_msg(f"✓ Current columns in trades: {columns}")

        # FIX 1: Add 'pnl' column if not exists
        if "pnl" not in columns:
            log_msg("⚠️ Column 'pnl' not found, adding...")
            cursor.execute("""
                ALTER TABLE trades
                ADD COLUMN pnl REAL DEFAULT 0.0
            """)
            log_msg("✓ Column 'pnl' added")
        else:
            log_msg("✓ Column 'pnl' already exists")

        # FIX 2: Add 'profit_loss' if not exists
        if "profit_loss" not in columns:
            log_msg("⚠️ Column 'profit_loss' not found, adding...")
            cursor.execute("""
                ALTER TABLE trades
                ADD COLUMN profit_loss REAL DEFAULT 0.0
            """)
            log_msg("✓ Column 'profit_loss' added")
        else:
            log_msg("✓ Column 'profit_loss' already exists")

        # FIX 3: Add 'wl_status' if not exists
        if "wl_status" not in columns:
            log_msg("⚠️ Column 'wl_status' not found, adding...")
            cursor.execute("""
                ALTER TABLE trades
                ADD COLUMN wl_status TEXT DEFAULT 'NEUTRAL'
            """)
            # Populate wl_status based on profit_loss
            cursor.execute("""
                UPDATE trades
                SET wl_status = CASE
                    WHEN profit_loss > 0 THEN 'WIN'
                    WHEN profit_loss < 0 THEN 'LOSS'
                    ELSE 'NEUTRAL'
                END
                WHERE wl_status = 'NEUTRAL'
            """)
            log_msg("✓ Column 'wl_status' added and populated")
        else:
            log_msg("✓ Column 'wl_status' already exists")

        # FIX 4: Ensure pnl and profit_loss are synchronized
        log_msg("⚠️ Synchronizing pnl ↔ profit_loss...")
        cursor.execute("""
            UPDATE trades
            SET pnl = profit_loss
            WHERE pnl IS NULL OR pnl = 0.0
        """)
        log_msg("✓ pnl synchronized with profit_loss")

        conn.commit()
        conn.close()

        log_msg("✅ Database migration complete!", "SUCCESS")
        return True

    except sqlite3.Error as e:
        log_msg(f"❌ Database error: {e}", "ERROR")
        return False
    except Exception as e:
        log_msg(f"❌ Unexpected error: {e}", "ERROR")
        return False


def validate_trades_query():
    """Validate that retraining query works."""
    if not DB_FILE.exists():
        return False

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Test the query that daily_confidence_retraining uses
        test_query = """
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as wins
        FROM trades
        WHERE DATE(entry_time) = DATE('now')
            AND status = 'CLOSED'
        """

        cursor.execute(test_query)
        result = cursor.fetchone()
        conn.close()

        log_msg(f"✓ Query validation successful: total={result[0]}, wins={result[1]}")
        return True

    except sqlite3.Error as e:
        log_msg(f"❌ Query validation failed: {e}", "ERROR")
        return False


if __name__ == "__main__":
    log_msg("=" * 70)
    log_msg("DATABASE SCHEMA MIGRATION - FIX #1", "INFO")
    log_msg("=" * 70)

    success = migrate_trades_table()

    if success:
        validate_trades_query()
        log_msg("=" * 70)
        log_msg("✅ DATABASE MIGRATION COMPLETE", "SUCCESS")
        log_msg("=" * 70)
        print("\nNext steps:")
        print("  1. Restart daily_confidence_retraining.py")
        print("  2. Verify: python scripts/daily_confidence_retraining.py")
        sys.exit(0)
    else:
        log_msg("=" * 70)
        log_msg("❌ MIGRATION FAILED", "ERROR")
        log_msg("=" * 70)
        sys.exit(1)
