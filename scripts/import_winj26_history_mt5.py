"""Importa histórico completo de WINJ26 do MT5 para market_data."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import os
import sqlite3
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _load_env_value(key: str) -> str | None:
    env_val = os.environ.get(key)
    if env_val:
        return env_val

    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return None
    with env_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return None


def load_mt5_credentials() -> tuple[int | None, str | None, str | None]:
    login = os.environ.get("MT5_LOGIN")
    password = os.environ.get("MT5_PASSWORD")
    server = os.environ.get("MT5_SERVER")
    if login and password and server:
        return int(login), password, server

    login = _load_env_value("MT5_LOGIN")
    password = _load_env_value("MT5_PASSWORD")
    server = _load_env_value("MT5_SERVER")

    if login and password and server:
        return int(login), password, server
    return None, None, None


def resolve_timeframe(mt5: object, timeframe: str) -> int:
    tf = timeframe.upper()
    mapping = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
    }
    if tf not in mapping:
        raise ValueError(f"Timeframe não suportado: {timeframe}")
    return mapping[tf]


def ensure_market_data_table(db_path: Path) -> None:
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                timeframe TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                spread REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def import_history(symbol: str, timeframe: str, db_path: Path, chunk_size: int) -> None:
    try:
        import MetaTrader5 as mt5
    except Exception as exc:
        raise RuntimeError(f"MetaTrader5 indisponível: {exc}") from exc

    terminal_path = _load_env_value("MT5_TERMINAL_PATH")
    if terminal_path:
        initialized = mt5.initialize(path=terminal_path)
    else:
        initialized = mt5.initialize()

    if not initialized:
        raise RuntimeError(f"mt5.initialize falhou: {mt5.last_error()}")

    login, password, server = load_mt5_credentials()
    if login and password and server:
        ok = mt5.login(login=login, password=password, server=server)
        if not ok:
            mt5.shutdown()
            raise RuntimeError(f"mt5.login falhou: {mt5.last_error()}")

    selected = mt5.symbol_select(symbol, True)
    if not selected:
        # Alguns terminais retornam False mesmo com symbol_info válido.
        if mt5.symbol_info(symbol) is None:
            mt5.shutdown()
            raise RuntimeError(f"symbol_select falhou para {symbol}: {mt5.last_error()}")

    tf = resolve_timeframe(mt5, timeframe)

    all_rows: list[tuple] = []
    pos = 0
    while True:
        rates = mt5.copy_rates_from_pos(symbol, tf, pos, chunk_size)
        if rates is None or len(rates) == 0:
            break
        for r in rates:
            ts = datetime.fromtimestamp(int(r["time"])).strftime("%Y-%m-%d %H:%M:%S")
            all_rows.append(
                (
                    symbol,
                    ts,
                    timeframe.upper(),
                    float(r["open"]),
                    float(r["high"]),
                    float(r["low"]),
                    float(r["close"]),
                    int(r["tick_volume"]),
                    0.0,
                )
            )
        pos += len(rates)
        if len(rates) < chunk_size:
            break

    mt5.shutdown()

    if not all_rows:
        raise RuntimeError("Nenhum candle retornado para o símbolo/timeframe solicitado.")

    # Ordena crescente por timestamp para persistência estável
    all_rows.sort(key=lambda x: x[1])

    ensure_market_data_table(db_path)
    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM market_data WHERE symbol=? AND timeframe=?",
            (symbol, timeframe.upper()),
        )
        cur.executemany(
            """
            INSERT INTO market_data
            (symbol, timestamp, timeframe, open, high, low, close, volume, spread, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            all_rows,
        )
        conn.commit()

    print(
        f"[OK] Importação concluída: {symbol} {timeframe.upper()} | "
        f"candles={len(all_rows)} | início={all_rows[0][1]} | fim={all_rows[-1][1]} | db={db_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="WINJ26")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--db-path", default="data/db/trading.db")
    parser.add_argument("--chunk-size", type=int, default=50000)
    args = parser.parse_args()

    import_history(
        symbol=args.symbol,
        timeframe=args.timeframe,
        db_path=Path(args.db_path),
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
