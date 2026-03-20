"""Ingestão de histórico WIN para `market_data` (SQLite).

Suporta duas fontes:
- MT5 direto (MetaTrader5)
- CSV export local (`data/export` por padrão)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import os
import re
import sqlite3
from typing import Any, Optional
import csv

from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock


WIN_CONTRACT_RE = re.compile(r"^WIN[A-Z]\d{2}$", re.IGNORECASE)


@dataclass
class IngestionStats:
    source: str
    timeframe: str
    start_date: str
    end_date: str
    symbols_processed: int
    rows_loaded: int
    rows_inserted: int
    rows_skipped_existing: int
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "timeframe": self.timeframe,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "symbols_processed": self.symbols_processed,
            "rows_loaded": self.rows_loaded,
            "rows_inserted": self.rows_inserted,
            "rows_skipped_existing": self.rows_skipped_existing,
            "errors": self.errors,
        }


def _load_mt5_credentials() -> tuple[Optional[int], Optional[str], Optional[str]]:
    login = os.environ.get("MT5_LOGIN")
    password = os.environ.get("MT5_PASSWORD")
    server = os.environ.get("MT5_SERVER")
    if login and password and server:
        return int(login), password, server

    env_path = Path(".env")
    if not env_path.exists():
        return None, None, None

    with env_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("MT5_LOGIN="):
                login = line.split("=", 1)[1].strip()
            elif line.startswith("MT5_PASSWORD="):
                password = line.split("=", 1)[1].strip()
            elif line.startswith("MT5_SERVER="):
                server = line.split("=", 1)[1].strip()
    if login and password and server:
        return int(login), password, server
    return None, None, None


def _ensure_market_data_table(db_path: str) -> None:
    with sqlite_write_lock(db_path):
        with sqlite3.connect(db_path) as conn:
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


def _insert_market_rows(
    db_path: str,
    symbol: str,
    timeframe: str,
    rows: list[dict[str, Any]],
) -> tuple[int, int]:
    """Insere apenas timestamps inexistentes para símbolo/timeframe."""
    if not rows:
        return 0, 0

    ts_min = rows[0]["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    ts_max = rows[-1]["timestamp"].strftime("%Y-%m-%d %H:%M:%S")

    with sqlite_write_lock(db_path):
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT timestamp FROM market_data
                WHERE symbol=? AND timeframe=? AND timestamp BETWEEN ? AND ?
                """,
                (symbol, timeframe, ts_min, ts_max),
            )
            existing = {row[0] for row in cur.fetchall()}

            to_insert = []
            skipped = 0
            for row in rows:
                ts = row["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                if ts in existing:
                    skipped += 1
                    continue
                to_insert.append(
                    (
                        symbol,
                        ts,
                        timeframe,
                        float(row["open"]),
                        float(row["high"]),
                        float(row["low"]),
                        float(row["close"]),
                        int(row.get("volume", 0)),
                        0.0,
                    )
                )

            if to_insert:
                cur.executemany(
                    """
                    INSERT INTO market_data
                    (symbol, timestamp, timeframe, open, high, low, close, volume, spread, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    to_insert,
                )
            conn.commit()
    return len(to_insert), skipped


def _parse_num(value: Any) -> float:
    text = str(value or "0").strip()
    if not text:
        return 0.0
    # Suporta padrão BR com vírgula decimal e ponto de milhar.
    text = text.replace(".", "").replace(",", ".")
    return float(text)


def _parse_csv_export(path: Path, start_dt: datetime, end_dt: datetime) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            date_raw = (r.get("Data") or r.get("Date") or "").strip()
            time_raw = (r.get("Hora") or r.get("Time") or "").strip()
            if not date_raw or not time_raw:
                continue
            day, month, year = date_raw.split("/")
            if len(year) == 2:
                year = f"20{year}"
            ts = datetime.strptime(f"{day}/{month}/{year} {time_raw}", "%d/%m/%Y %H:%M:%S")
            if ts < start_dt or ts > end_dt:
                continue

            open_v = _parse_num(r.get("Abertura") or r.get("Open"))
            high_v = _parse_num(r.get("Máximo") or r.get("M�ximo") or r.get("Max"))
            low_v = _parse_num(r.get("Mínimo") or r.get("M�nimo") or r.get("Min"))
            close_v = _parse_num(r.get("Fechamento") or r.get("Close"))
            vol_raw = r.get("Volume") or r.get("Vol") or 0
            volume = int(_parse_num(vol_raw))
            rows.append(
                {
                    "timestamp": ts,
                    "open": open_v,
                    "high": high_v,
                    "low": low_v,
                    "close": close_v,
                    "volume": volume,
                }
            )
    rows.sort(key=lambda x: x["timestamp"])
    return rows


def _discover_csv_win_symbols(export_dir: str) -> dict[str, Path]:
    base = Path(export_dir)
    if not base.exists():
        return {}
    out: dict[str, Path] = {}
    for file in base.iterdir():
        if not file.is_file():
            continue
        symbol = file.name.split("_")[0].upper()
        if WIN_CONTRACT_RE.match(symbol):
            out[symbol] = file
    return out


def ingest_from_csv_export(
    db_path: str,
    export_dir: str,
    start_dt: datetime,
    end_dt: datetime,
    timeframe: str = "M5",
) -> IngestionStats:
    _ensure_market_data_table(db_path)
    symbols = _discover_csv_win_symbols(export_dir)
    errors: list[str] = []
    rows_loaded = 0
    rows_inserted = 0
    rows_skipped = 0

    for symbol, path in symbols.items():
        try:
            rows = _parse_csv_export(path, start_dt, end_dt)
            rows_loaded += len(rows)
            ins, skp = _insert_market_rows(db_path, symbol, timeframe, rows)
            rows_inserted += ins
            rows_skipped += skp
        except Exception as exc:  # pragma: no cover
            errors.append(f"{symbol}: {exc}")

    return IngestionStats(
        source="csv",
        timeframe=timeframe,
        start_date=start_dt.date().isoformat(),
        end_date=end_dt.date().isoformat(),
        symbols_processed=len(symbols),
        rows_loaded=rows_loaded,
        rows_inserted=rows_inserted,
        rows_skipped_existing=rows_skipped,
        errors=errors,
    )


def ingest_from_mt5(
    db_path: str,
    start_dt: datetime,
    end_dt: datetime,
    timeframe: str = "M5",
) -> IngestionStats:
    _ensure_market_data_table(db_path)
    errors: list[str] = []
    rows_loaded = 0
    rows_inserted = 0
    rows_skipped = 0

    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception as exc:
        return IngestionStats(
            source="mt5",
            timeframe=timeframe,
            start_date=start_dt.date().isoformat(),
            end_date=end_dt.date().isoformat(),
            symbols_processed=0,
            rows_loaded=0,
            rows_inserted=0,
            rows_skipped_existing=0,
            errors=[f"MetaTrader5 indisponível: {exc}"],
        )

    terminal_path = os.environ.get("MT5_TERMINAL_PATH")
    if terminal_path:
        if not os.path.isfile(terminal_path):
            return IngestionStats(
                source="mt5",
                timeframe=timeframe,
                start_date=start_dt.date().isoformat(),
                end_date=end_dt.date().isoformat(),
                symbols_processed=0,
                rows_loaded=0,
                rows_inserted=0,
                rows_skipped_existing=0,
                errors=[f"MT5_TERMINAL_PATH invalido: {terminal_path}"],
            )
        if not mt5.initialize(path=terminal_path):
            return IngestionStats(
                source="mt5",
                timeframe=timeframe,
                start_date=start_dt.date().isoformat(),
                end_date=end_dt.date().isoformat(),
                symbols_processed=0,
                rows_loaded=0,
                rows_inserted=0,
                rows_skipped_existing=0,
                errors=[f"mt5.initialize falhou: {mt5.last_error()}"],
            )
    else:
        if not mt5.initialize():
            return IngestionStats(
                source="mt5",
                timeframe=timeframe,
                start_date=start_dt.date().isoformat(),
                end_date=end_dt.date().isoformat(),
                symbols_processed=0,
                rows_loaded=0,
                rows_inserted=0,
                rows_skipped_existing=0,
                errors=[f"mt5.initialize falhou: {mt5.last_error()}"],
            )

    login, password, server = _load_mt5_credentials()
    if login and password and server:
        ok = mt5.login(login=login, password=password, server=server)
        if not ok:
            errors.append(f"mt5.login falhou: {mt5.last_error()}")

    try:
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
        }
        mt5_tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_M5)

        symbols_info = mt5.symbols_get(group="WIN*") or []
        symbols = sorted(
            {
                s.name.upper()
                for s in symbols_info
                if WIN_CONTRACT_RE.match(s.name.upper())
            }
        )

        for symbol in symbols:
            try:
                mt5.symbol_select(symbol, True)
                rates = mt5.copy_rates_range(symbol, mt5_tf, start_dt, end_dt)
                if rates is None or len(rates) == 0:
                    continue
                parsed = []
                for rate in rates:
                    parsed.append(
                        {
                            "timestamp": datetime.fromtimestamp(int(rate["time"])),
                            "open": float(rate["open"]),
                            "high": float(rate["high"]),
                            "low": float(rate["low"]),
                            "close": float(rate["close"]),
                            "volume": int(rate["tick_volume"]),
                        }
                    )
                rows_loaded += len(parsed)
                ins, skp = _insert_market_rows(db_path, symbol, timeframe.upper(), parsed)
                rows_inserted += ins
                rows_skipped += skp
            except Exception as exc:  # pragma: no cover
                errors.append(f"{symbol}: {exc}")
    finally:
        mt5.shutdown()

    return IngestionStats(
        source="mt5",
        timeframe=timeframe.upper(),
        start_date=start_dt.date().isoformat(),
        end_date=end_dt.date().isoformat(),
        symbols_processed=len(locals().get("symbols", [])),
        rows_loaded=rows_loaded,
        rows_inserted=rows_inserted,
        rows_skipped_existing=rows_skipped,
        errors=errors,
    )


def ingest_win_history_auto(
    db_path: str,
    start_dt: datetime,
    end_dt: datetime,
    timeframe: str = "M5",
    source: str = "auto",
    export_dir: str = "data/export",
) -> IngestionStats:
    src = source.lower().strip()
    if src not in {"auto", "mt5", "csv"}:
        raise ValueError(f"Fonte de ingestão inválida: {source}")

    if src in {"auto", "mt5"}:
        mt5_stats = ingest_from_mt5(
            db_path=db_path,
            start_dt=start_dt,
            end_dt=end_dt,
            timeframe=timeframe,
        )
        if src == "mt5":
            return mt5_stats
        if mt5_stats.rows_inserted > 0:
            return mt5_stats
        # fallback para CSV no modo auto
        csv_stats = ingest_from_csv_export(
            db_path=db_path,
            export_dir=export_dir,
            start_dt=start_dt,
            end_dt=end_dt,
            timeframe=timeframe,
        )
        csv_stats.errors = mt5_stats.errors + csv_stats.errors
        return csv_stats

    return ingest_from_csv_export(
        db_path=db_path,
        export_dir=export_dir,
        start_dt=start_dt,
        end_dt=end_dt,
        timeframe=timeframe,
    )
