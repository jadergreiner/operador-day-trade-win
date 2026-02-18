"""Backtest do modelo WINFUT usando M1 do dia informado."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, time
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
class BacktestResult:
    rows: int
    accuracy: float
    class_report: str


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
    # Base features from M1
    df = df.copy()
    df["current_price"] = df["close"]
    open_price = df.iloc[0]["open"] if not df.empty else np.nan
    df["price_change_since_open"] = (df["current_price"] - open_price) / open_price
    df["price_change_last_10min"] = (
        (df["current_price"] - df["current_price"].shift(10))
        / df["current_price"].shift(10)
    )

    # Ensure all expected columns exist
    all_cols = numeric_cols + cat_cols
    features = pd.DataFrame(index=df.index)
    for col in all_cols:
        features[col] = np.nan

    for col in ["current_price", "price_change_since_open", "price_change_last_10min"]:
        if col in features.columns:
            features[col] = df[col]

    return features


def run_backtest(
    model_path: Path,
    db_path: Path,
    symbol: str,
    date_str: str,
    start_time: str,
    end_time: str,
) -> BacktestResult:
    payload = joblib.load(model_path)
    pipeline = payload["pipeline"]
    numeric_cols = payload["numeric_cols"]
    cat_cols = payload["cat_cols"]
    label_classes = payload.get("label_classes", ["BUY", "HOLD", "SELL"])
    meta = payload.get("meta", {})
    horizon_minutes = int(meta.get("horizon_minutes", 30))
    threshold = float(meta.get("threshold", 0.0005))

    date = datetime.strptime(date_str, "%Y-%m-%d")
    start_dt = datetime.combine(date.date(), datetime.strptime(start_time, "%H:%M").time())
    end_dt = datetime.combine(date.date(), datetime.strptime(end_time, "%H:%M").time())

    if date.weekday() >= 5:
        print("[AVISO] A data informada e fim de semana; pode nao haver dados.")

    df = _load_m1_from_sqlite(db_path, symbol, start_dt, end_dt)
    source = "SQLite"

    if df.empty:
        print("[INFO] Sem dados M1 no SQLite, tentando MT5...")
        try:
            df = _load_m1_from_mt5(symbol, start_dt, end_dt)
            source = "MT5"
        except Exception as exc:
            print(f"[ERRO] Falha ao consultar MT5: {exc}")
            df = pd.DataFrame()

    if df.empty:
        raise RuntimeError("Nao ha dados M1 disponiveis para a data/horario.")

    print(f"Fonte de dados M1: {source} | Linhas: {len(df)}")

    day_open = float(df.iloc[0]["open"])
    day_close = float(df.iloc[-1]["close"])
    day_return = (day_close - day_open) / day_open if day_open else 0.0
    if day_return > threshold:
        day_direction = "BUY"
    elif day_return < -threshold:
        day_direction = "SELL"
    else:
        day_direction = "HOLD"

    labels = _compute_labels(df, horizon_minutes, threshold)
    features = _build_feature_rows(df, numeric_cols, cat_cols)

    valid_mask = labels.notna()
    labels = labels[valid_mask]
    features = features.loc[valid_mask.index[valid_mask]]

    raw_pred = pipeline.predict(features)
    if hasattr(raw_pred, "ndim") and raw_pred.ndim > 1:
        pred_idx = raw_pred.argmax(axis=1)
    else:
        pred_idx = raw_pred.astype(int)

    pred_labels = [label_classes[int(i)] for i in pred_idx]

    from sklearn.metrics import accuracy_score, classification_report

    acc = accuracy_score(labels, pred_labels)
    report = classification_report(labels, pred_labels, digits=3, zero_division=0)

    day_hit = sum(1 for p in pred_labels if p == day_direction) / len(pred_labels)

    print("\nABERTURA x FECHAMENTO")
    print(f"Abertura: {day_open:.2f} | Fechamento: {day_close:.2f}")
    print(f"Variacao: {day_return:.4%} | Direcao do dia: {day_direction}")
    print(f"Acerto do modelo vs direcao do dia: {day_hit:.3f}")

    return BacktestResult(rows=len(labels), accuracy=acc, class_report=report)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", default="data/models/winfut/winfut_model_latest.pkl")
    parser.add_argument("--db-path", default="data/db/trading.db")
    parser.add_argument("--symbol", default="WING26")
    parser.add_argument("--date", default="2026-02-08")
    parser.add_argument("--start", default="09:00")
    parser.add_argument("--end", default="17:30")
    args = parser.parse_args()

    result = run_backtest(
        model_path=Path(args.model_path),
        db_path=Path(args.db_path),
        symbol=args.symbol,
        date_str=args.date,
        start_time=args.start,
        end_time=args.end,
    )

    print("\nBACKTEST WINFUT")
    print(f"Linhas avaliadas: {result.rows}")
    print(f"Acerto direcional: {result.accuracy:.3f}")
    print("Relatorio por classe:")
    print(result.class_report)


if __name__ == "__main__":
    main()
