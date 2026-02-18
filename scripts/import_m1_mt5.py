"""Importa candles M1 do MT5 para o SQLite."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import get_config
from src.domain.enums.trading_enums import TimeFrame
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter


def _insert_market_data(db_path: Path, symbol: str, rows: list[dict]) -> int:
    import sqlite3

    if not rows:
        return 0

    with sqlite3.connect(str(db_path)) as con:
        cur = con.cursor()
        cur.execute(
            "DELETE FROM market_data WHERE symbol=? AND timeframe='M1' AND timestamp BETWEEN ? AND ?",
            (symbol, rows[0]["timestamp"], rows[-1]["timestamp"]),
        )
        cur.executemany(
            """
            INSERT INTO market_data
            (symbol, timestamp, timeframe, open, high, low, close, volume, spread, created_at)
            VALUES (?, ?, 'M1', ?, ?, ?, ?, ?, 0, datetime('now'))
            """,
            [
                (
                    symbol,
                    r["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                    r["open"],
                    r["high"],
                    r["low"],
                    r["close"],
                    r["volume"],
                )
                for r in rows
            ],
        )
        con.commit()

    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="WING26")
    parser.add_argument("--date", default="2026-02-08")
    parser.add_argument("--start", default="09:00")
    parser.add_argument("--end", default="17:30")
    parser.add_argument("--db-path", default="data/db/trading.db")
    args = parser.parse_args()

    date = datetime.strptime(args.date, "%Y-%m-%d")
    start_dt = datetime.combine(date.date(), datetime.strptime(args.start, "%H:%M").time())
    end_dt = datetime.combine(date.date(), datetime.strptime(args.end, "%H:%M").time())

    config = get_config()
    adapter = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    adapter.connect()
    adapter.select_symbol(args.symbol)

    try:
        candles = adapter.get_candles_range(
            symbol=Symbol(args.symbol),
            timeframe=TimeFrame.M1,
            start_time=start_dt,
            end_time=end_dt,
        )
    finally:
        adapter.disconnect()

    rows = []
    for c in candles:
        rows.append(
            {
                "timestamp": c.timestamp,
                "open": float(c.open.value),
                "high": float(c.high.value),
                "low": float(c.low.value),
                "close": float(c.close.value),
                "volume": c.volume,
            }
        )

    if not rows:
        print("[AVISO] Nenhum candle M1 retornado pelo MT5.")
        return

    inserted = _insert_market_data(Path(args.db_path), args.symbol, rows)
    print(f"[OK] Inseridos {inserted} candles M1 em {args.db_path}")


if __name__ == "__main__":
    main()
