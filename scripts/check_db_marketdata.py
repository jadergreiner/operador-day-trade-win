"""Verifica registros em data/db/trading.db para simbolos e datas.

Uso:
    python scripts/check_db_marketdata.py SYMBOL YYYY-MM-DD
Ex: python scripts/check_db_marketdata.py IBOV 2026-02-05
"""
import sys
import sqlite3
from datetime import datetime, timedelta

DB_PATH = 'data/db/trading.db'

def main():
    if len(sys.argv) < 3:
        print("Uso: scripts/check_db_marketdata.py SYMBOL YYYY-MM-DD [HH:MM|HH:MM-HH:MM]")
        return
    symbol = sys.argv[1]
    day = sys.argv[2]
    time_arg = sys.argv[3] if len(sys.argv) >= 4 else None
    try:
        date = datetime.fromisoformat(day).date()
    except Exception:
        print("Data invalida. Use YYYY-MM-DD")
        return

    # determine time window
    if time_arg:
        if '-' in time_arg:
            t0, t1 = time_arg.split('-', 1)
            start_dt = datetime.fromisoformat(f"{day}T{t0}")
            end_dt = datetime.fromisoformat(f"{day}T{t1}")
        else:
            # single time -> treat as start of M15 bar window
            t0 = time_arg
            start_dt = datetime.fromisoformat(f"{day}T{t0}")
            # end = start + 14 minutes 59 seconds
            end_dt = start_dt + timedelta(minutes=14, seconds=59)
        start = start_dt.strftime('%Y-%m-%d %H:%M:%S')
        end = end_dt.strftime('%Y-%m-%d %H:%M:%S')
    else:
        start = f"{date} 00:00:00"
        end = f"{date} 23:59:59"

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = ? AND timeframe = 'M15' AND timestamp BETWEEN ? AND ?
            ORDER BY timestamp
            """,
            (symbol, start, end),
        )
        rows = cur.fetchall()
        print(f"Found {len(rows)} M15 rows for {symbol} on {date}")
        for r in rows[:20]:
            print(r[0], r[1], r[2], r[3], r[4], r[5])
    except sqlite3.Error as e:
        print('DB error:', e)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
