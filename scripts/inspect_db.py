#!/usr/bin/env python3
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "db" / "trading.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables:")
for t in tables:
    print(f"  - {t[0]}")

# Inspect trades table
print("\nTrades table schema:")
cursor.execute("PRAGMA table_info(mt5_orders)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col[1]} ({col[2]})")

conn.close()
