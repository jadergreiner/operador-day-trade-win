from datetime import datetime
from pathlib import Path
import sqlite3

from src.application.services.win_data_ingestion import (
    ingest_from_csv_export,
    ingest_win_history_auto,
)


def _create_market_data_table(db_path: Path) -> None:
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


def test_ingest_from_csv_export_parses_and_inserts(tmp_path: Path):
    db_path = tmp_path / "trading.db"
    export_dir = tmp_path / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    _create_market_data_table(db_path)

    csv_file = export_dir / "WINJ26_mock.csv"
    csv_file.write_text(
        "Data;Hora;Abertura;Máximo;Mínimo;Fechamento;Volume\n"
        "05/02/26;09:00:00;183.100,0;183.150,0;183.050,0;183.120,0;1000\n"
        "05/02/26;09:05:00;183.120,0;183.200,0;183.110,0;183.180,0;1200\n",
        encoding="utf-8",
    )

    stats = ingest_from_csv_export(
        db_path=str(db_path),
        export_dir=str(export_dir),
        start_dt=datetime(2026, 2, 1),
        end_dt=datetime(2026, 2, 28, 23, 59, 59),
        timeframe="M5",
    )

    assert stats.rows_loaded == 2
    assert stats.rows_inserted == 2
    assert stats.symbols_processed == 1
    assert stats.errors == []

    with sqlite3.connect(str(db_path)) as conn:
        count = conn.execute("SELECT COUNT(*) FROM market_data").fetchone()[0]
    assert count == 2


def test_ingest_deduplicates_existing_rows(tmp_path: Path):
    db_path = tmp_path / "trading.db"
    export_dir = tmp_path / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    _create_market_data_table(db_path)

    csv_file = export_dir / "WING26_mock.csv"
    csv_file.write_text(
        "Data;Hora;Abertura;Máximo;Mínimo;Fechamento;Volume\n"
        "05/02/26;09:00:00;183.100,0;183.150,0;183.050,0;183.120,0;1000\n",
        encoding="utf-8",
    )

    first = ingest_from_csv_export(
        db_path=str(db_path),
        export_dir=str(export_dir),
        start_dt=datetime(2026, 2, 1),
        end_dt=datetime(2026, 2, 28, 23, 59, 59),
        timeframe="M5",
    )
    second = ingest_win_history_auto(
        db_path=str(db_path),
        start_dt=datetime(2026, 2, 1),
        end_dt=datetime(2026, 2, 28, 23, 59, 59),
        timeframe="M5",
        source="csv",
        export_dir=str(export_dir),
    )

    assert first.rows_inserted == 1
    assert second.rows_inserted == 0
    assert second.rows_skipped_existing == 1

