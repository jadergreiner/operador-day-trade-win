"""Backtest do modelo WINFUT para todos os dias uteis de 2025."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
import sys
from typing import Optional

import joblib
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import get_config
from src.domain.enums.trading_enums import TimeFrame
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter


@dataclass
class DayResult:
    day: date
    rows: int
    accuracy: float
    day_direction: str
    day_hit: float
    source: str


def _date_range_2025() -> list[date]:
    start = date(2025, 1, 1)
    end = date(2025, 12, 31)
    days = []
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            days.append(cur)
        cur += timedelta(days=1)
    return days


def _load_m1_from_sqlite(
    db_path: Path,
    symbol: str,
    start_dt: datetime,
    end_dt: datetime,
) -> pd.DataFrame:
    import sqlite3

    query = (
        "SELECT timestamp, open, high, low, close, volume "
        "FROM market_data "
        "WHERE symbol = ? AND timeframe = 'M1' AND timestamp BETWEEN ? AND ? "
        "ORDER BY timestamp"
    )

    with sqlite3.connect(str(db_path)) as con:
        df = pd.read_sql(
            query,
            con,
            params=(
                symbol,
                start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            ),
            parse_dates=["timestamp"],
        )

    return df


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


def _load_m1_from_mt5(
    symbol: str,
    start_dt: datetime,
    end_dt: datetime,
) -> pd.DataFrame:
    config = get_config()
    adapter = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )

    adapter.connect()
    adapter.select_symbol(symbol)

    try:
        candles = adapter.get_candles_range(
            symbol=Symbol(symbol),
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

    return pd.DataFrame(rows)


def _compute_labels(
    df: pd.DataFrame,
    horizon_minutes: int,
    threshold: float,
) -> pd.Series:
    ts = df["timestamp"].to_numpy(dtype="datetime64[ns]")
    prices = df["close"].astype("float64").to_numpy()

    horizon = np.timedelta64(horizon_minutes, "m")
    future_idx = np.searchsorted(ts, ts + horizon)
    future_prices = np.full_like(prices, np.nan, dtype="float64")
    valid = future_idx < len(prices)
    future_prices[valid] = prices[future_idx[valid]]

    future_ret = (future_prices - prices) / prices

    def to_label(x: float) -> Optional[str]:
        if np.isnan(x):
            return None
        if x > threshold:
            return "BUY"
        if x < -threshold:
            return "SELL"
        return "HOLD"

    return pd.Series([to_label(x) for x in future_ret])


def _build_feature_rows(
    df: pd.DataFrame,
    numeric_cols: list[str],
    cat_cols: list[str],
) -> pd.DataFrame:
    df = df.copy()
    df["current_price"] = df["close"]
    open_price = df.iloc[0]["open"] if not df.empty else np.nan
    df["price_change_since_open"] = (df["current_price"] - open_price) / open_price
    df["price_change_last_10min"] = (
        (df["current_price"] - df["current_price"].shift(10))
        / df["current_price"].shift(10)
    )

    all_cols = numeric_cols + cat_cols
    features = pd.DataFrame(index=df.index)
    for col in all_cols:
        features[col] = np.nan

    for col in ["current_price", "price_change_since_open", "price_change_last_10min"]:
        if col in features.columns:
            features[col] = df[col]

    return features


def _day_direction(df: pd.DataFrame, threshold: float) -> tuple[str, float, float, float]:
    day_open = float(df.iloc[0]["open"])
    day_close = float(df.iloc[-1]["close"])
    day_return = (day_close - day_open) / day_open if day_open else 0.0
    if day_return > threshold:
        direction = "BUY"
    elif day_return < -threshold:
        direction = "SELL"
    else:
        direction = "HOLD"
    return direction, day_open, day_close, day_return


def _load_day_data(
    db_path: Path,
    symbol: str,
    start_dt: datetime,
    end_dt: datetime,
    allow_mt5: bool,
) -> tuple[pd.DataFrame, str]:
    df = _load_m1_from_sqlite(db_path, symbol, start_dt, end_dt)
    if not df.empty:
        return df, "SQLite"

    if not allow_mt5:
        return pd.DataFrame(), "None"

    try:
        df = _load_m1_from_mt5(symbol, start_dt, end_dt)
        if df.empty:
            return df, "MT5"
        rows = df.to_dict(orient="records")
        _insert_market_data(db_path, symbol, rows)
        return df, "MT5"
    except Exception:
        return pd.DataFrame(), "MT5"


def run_backtest_year(
    model_path: Path,
    db_path: Path,
    symbol: str,
    start_time: str,
    end_time: str,
    allow_mt5: bool,
) -> list[DayResult]:
    payload = joblib.load(model_path)
    pipeline = payload["pipeline"]
    numeric_cols = payload["numeric_cols"]
    cat_cols = payload["cat_cols"]
    label_classes = payload.get("label_classes", ["BUY", "HOLD", "SELL"])
    meta = payload.get("meta", {})
    horizon_minutes = int(meta.get("horizon_minutes", 30))
    threshold = float(meta.get("threshold", 0.0005))

    results: list[DayResult] = []

    for day in _date_range_2025():
        start_dt = datetime.combine(day, datetime.strptime(start_time, "%H:%M").time())
        end_dt = datetime.combine(day, datetime.strptime(end_time, "%H:%M").time())

        df, source = _load_day_data(db_path, symbol, start_dt, end_dt, allow_mt5)
        if df.empty:
            continue

        labels = _compute_labels(df, horizon_minutes, threshold)
        features = _build_feature_rows(df, numeric_cols, cat_cols)

        valid_mask = labels.notna()
        labels = labels[valid_mask]
        features = features.loc[valid_mask.index[valid_mask]]
        if labels.empty:
            continue

        raw_pred = pipeline.predict(features)
        if hasattr(raw_pred, "ndim") and raw_pred.ndim > 1:
            pred_idx = raw_pred.argmax(axis=1)
        else:
            pred_idx = raw_pred.astype(int)

        pred_labels = [label_classes[int(i)] for i in pred_idx]

        from sklearn.metrics import accuracy_score

        acc = accuracy_score(labels, pred_labels)
        day_direction, _, _, _ = _day_direction(df, threshold)
        day_hit = sum(1 for p in pred_labels if p == day_direction) / len(pred_labels)

        results.append(
            DayResult(
                day=day,
                rows=len(labels),
                accuracy=acc,
                day_direction=day_direction,
                day_hit=day_hit,
                source=source,
            )
        )

    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", default="data/models/winfut/winfut_model_latest.pkl")
    parser.add_argument("--db-path", default="data/db/trading.db")
    parser.add_argument("--symbol", default="WING26")
    parser.add_argument("--start", default="09:00")
    parser.add_argument("--end", default="17:30")
    parser.add_argument("--no-mt5", action="store_true")
    parser.add_argument("--output", default="data/export/winfut_backtest_2025.csv")
    args = parser.parse_args()

    results = run_backtest_year(
        model_path=Path(args.model_path),
        db_path=Path(args.db_path),
        symbol=args.symbol,
        start_time=args.start,
        end_time=args.end,
        allow_mt5=not args.no_mt5,
    )

    if not results:
        print("[ERRO] Nenhum dia com dados disponiveis em 2025.")
        return

    df = pd.DataFrame(
        [
            {
                "date": r.day.isoformat(),
                "rows": r.rows,
                "accuracy": r.accuracy,
                "day_direction": r.day_direction,
                "day_hit": r.day_hit,
                "source": r.source,
            }
            for r in results
        ]
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"Dias avaliados: {len(df)}")
    print(f"Acerto direcional medio: {df['accuracy'].mean():.3f}")
    print(f"Acerto vs direcao do dia medio: {df['day_hit'].mean():.3f}")
    print(f"CSV salvo em: {output_path}")


if __name__ == "__main__":
    main()
