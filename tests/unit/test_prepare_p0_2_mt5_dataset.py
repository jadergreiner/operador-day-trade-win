import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from scripts.prepare_p0_2_mt5_dataset import prepare_dataset


def _seed_market_data(db_path: Path, *, symbol: str, timeframe: str, rows: int = 300) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                timeframe TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                spread REAL
            )
            """
        )
        now = datetime(2026, 3, 11, 18, 0, 0)
        rows_data = []
        price = 100000.0
        for i in range(rows):
            ts = now - timedelta(minutes=5 * (rows - i))
            price = price + 4.0
            rows_data.append(
                (
                    symbol,
                    ts.strftime("%Y-%m-%d %H:%M:%S"),
                    timeframe,
                    price - 10.0,
                    price + 10.0,
                    price - 15.0,
                    price,
                    1000 + i,
                    0.0,
                )
            )
        conn.executemany(
            """
            INSERT INTO market_data
            (symbol, timestamp, timeframe, open, high, low, close, volume, spread)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows_data,
        )
        conn.commit()


def test_prepare_dataset_generates_training_csv_and_metadata(tmp_path):
    db_path = tmp_path / "trading.db"
    dataset_path = tmp_path / "training_dataset.csv"
    metadata_path = tmp_path / "training_dataset.metadata.json"

    _seed_market_data(db_path, symbol="WINJ26", timeframe="M5", rows=320)

    result = prepare_dataset(
        db_path=db_path,
        symbol="WINJ26",
        timeframe="M5",
        lookback_days=365,
        min_rows=100,
        dataset_path=dataset_path,
        metadata_path=metadata_path,
    )

    assert result.rows >= 100
    assert dataset_path.exists()
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["synthetic"] is False
    assert metadata["source_type"] == "mt5_export_real"
    assert metadata["rows"] == result.rows
