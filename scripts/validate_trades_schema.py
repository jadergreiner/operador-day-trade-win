#!/usr/bin/env python3
"""
Validar schema da tabela trades no SQLite.
Útil para diagnosticar problemas como 'no such column'.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("data/db/trading.db")


def validate_trades_schema():
    """Validate that trades table exists and has required columns."""
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return False

    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='trades'"
        )
        if not cursor.fetchone():
            print("❌ Table 'trades' not found in database")
            conn.close()
            return False

        print("✅ Table 'trades' exists")

        # Get table schema
        cursor.execute("PRAGMA table_info(trades)")
        columns = cursor.fetchall()

        print(f"\n📋 Columns in 'trades' table ({len(columns)} total):")
        print("-" * 80)

        required_columns = {
            "id": "INTEGER",
            "trade_id": "TEXT",
            "symbol": "TEXT",
            "entry_time": "DATETIME",
            "exit_time": "DATETIME",
            "profit_loss": "NUMERIC",  # This is the correct column name!
            "status": "TEXT",
        }

        found_columns = {}
        for col in columns:
            col_id, col_name, col_type, notnull, dflt_value, pk = col
            status = "✅" if col_name in required_columns else "ℹ "
            print(f"  {status} {col_name:<20} {col_type}")
            found_columns[col_name] = col_type

        print("\n🔍 Validation Results:")
        print("-" * 80)

        all_ok = True
        for col_name, col_type in required_columns.items():
            if col_name in found_columns:
                print(f"  ✅ {col_name:<20} EXISTS")
            else:
                print(f"  ❌ {col_name:<20} MISSING!")
                all_ok = False

        # Check for data
        print("\n📊 Data Statistics:")
        print("-" * 80)
        cursor.execute(
            "SELECT COUNT(*) as total, COUNT(DISTINCT status) as statuses FROM trades"
        )
        total, statuses = cursor.fetchone()
        print(f"  Total trades:    {total}")
        print(f"  Unique statuses: {statuses}")

        if total > 0:
            cursor.execute(
                "SELECT DISTINCT status FROM trades ORDER BY status"
            )
            status_list = [row[0] for row in cursor.fetchall()]
            print(f"  Status values:   {', '.join(status_list)}")

        # Check profit_loss stats
        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN profit_loss IS NOT NULL THEN 1 END) as with_pnl,
                COUNT(CASE WHEN profit_loss > 0 THEN 1 END) as wins,
                COUNT(CASE WHEN profit_loss < 0 THEN 1 END) as losses,
                COUNT(CASE WHEN profit_loss = 0 THEN 1 END) as breakeven
            FROM trades
            """
        )
        total, with_pnl, wins, losses, breakeven = cursor.fetchone()
        print(f"\n  Profit/Loss Stats:")
        print(f"    With P&L data:   {with_pnl}/{total}")
        print(f"    Winning trades:  {wins}")
        print(f"    Losing trades:   {losses}")
        print(f"    Breakeven:       {breakeven}")

        conn.close()

        print("\n" + "=" * 80)
        if all_ok:
            print("✅ Schema validation PASSED - all required columns found!")
        else:
            print("❌ Schema validation FAILED - some columns missing!")
        print("=" * 80)

        return all_ok

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    validate_trades_schema()
