"""Dataset builder for WINFUT day trade model."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class DatasetMeta:
    symbol: str
    horizon_minutes: int
    threshold: float
    rows_total: int
    rows_labeled: int
    start: Optional[pd.Timestamp]
    end: Optional[pd.Timestamp]


def _read_sqlite_table(db_path: Path, query: str) -> pd.DataFrame:
    import sqlite3

    with sqlite3.connect(str(db_path)) as con:
        return pd.read_sql(query, con, parse_dates=["timestamp"])


def load_sqlite_tables(db_path: Path) -> dict[str, pd.DataFrame]:
    """Load core tables from SQLite."""
    tables = {
        "reflections": _read_sqlite_table(
            db_path,
            "SELECT timestamp, current_price, price_change_since_open, "
            "price_change_last_10min, my_decision, my_confidence, my_alignment, "
            "human_makes_sense, my_data_correlation, mood "
            "FROM ai_reflection_logs",
        ),
        "journals": _read_sqlite_table(
            db_path,
            "SELECT timestamp, decision, confidence, market_feeling, "
            "macro_bias, fundamental_bias, sentiment_bias, technical_bias, "
            "alignment_score, market_regime "
            "FROM trading_journal_logs",
        ),
        "macro": _read_sqlite_table(
            db_path,
            "SELECT timestamp, total_items, items_available, total_raw, signal "
            "FROM simple_macro_score_decisions",
        ),
        "alignment": _read_sqlite_table(
            db_path,
            "SELECT timestamp, price_dir, score_dir, total_raw "
            "FROM simple_score_alignment",
        ),
    }

    return tables


def load_jsonl_reflections(jsonl_path: Path) -> pd.DataFrame:
    """Load reflections from JSONL as a fallback or complement."""
    if not jsonl_path.exists():
        return pd.DataFrame()

    rows: list[dict] = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            rows.append(
                {
                    "timestamp": rec.get("timestamp"),
                    "current_price": rec.get("current_price"),
                    "price_change_since_open": rec.get("price_change_since_open"),
                    "price_change_last_10min": rec.get("price_change_last_10min"),
                    "my_decision": rec.get("my_decision"),
                    "my_confidence": rec.get("my_confidence"),
                    "my_alignment": rec.get("my_alignment"),
                    "human_makes_sense": rec.get("human_makes_sense"),
                    "my_data_correlation": rec.get("my_data_correlation"),
                    "mood": rec.get("mood"),
                }
            )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df


def _normalize_reflections(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["human_makes_sense"] = df["human_makes_sense"].astype("float64")
    return df


def _merge_asof(
    base: pd.DataFrame,
    other: pd.DataFrame,
    tolerance_minutes: int,
    suffix: str,
) -> pd.DataFrame:
    if other.empty:
        return base

    other = other.sort_values("timestamp")
    return pd.merge_asof(
        base,
        other,
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta(minutes=tolerance_minutes),
        suffixes=("", suffix),
    )


def build_feature_frame(
    reflections: pd.DataFrame,
    journals: pd.DataFrame,
    macro: pd.DataFrame,
    alignment: pd.DataFrame,
    tolerance_minutes: int = 5,
) -> pd.DataFrame:
    """Join reflections with other logs using timestamp proximity."""
    if reflections.empty:
        return pd.DataFrame()

    df = reflections.sort_values("timestamp")
    df = _merge_asof(df, journals, tolerance_minutes, "_journal")
    df = _merge_asof(df, macro, tolerance_minutes, "_macro")
    df = _merge_asof(df, alignment, tolerance_minutes, "_align")

    return df


def _compute_future_return(
    timestamps: np.ndarray,
    prices: np.ndarray,
    horizon_minutes: int,
) -> np.ndarray:
    horizon = np.timedelta64(horizon_minutes, "m")
    future_idx = np.searchsorted(timestamps, timestamps + horizon)
    future_prices = np.full_like(prices, np.nan, dtype="float64")
    valid = future_idx < len(prices)
    future_prices[valid] = prices[future_idx[valid]]

    return (future_prices - prices) / prices


def add_labels(
    df: pd.DataFrame,
    horizon_minutes: int,
    threshold: float,
) -> pd.DataFrame:
    """Add BUY/SELL/HOLD labels based on future return."""
    if df.empty:
        return df

    df = df.copy()
    ts = df["timestamp"].to_numpy(dtype="datetime64[ns]")
    prices = df["current_price"].astype("float64").to_numpy()

    future_ret = _compute_future_return(ts, prices, horizon_minutes)
    df["future_return"] = future_ret

    def to_label(x: float) -> Optional[str]:
        if np.isnan(x):
            return None
        if x > threshold:
            return "BUY"
        if x < -threshold:
            return "SELL"
        return "HOLD"

    df["label"] = [to_label(x) for x in future_ret]

    return df


def build_dataset(
    db_path: Path,
    jsonl_path: Path,
    include_jsonl: bool = True,
    tolerance_minutes: int = 5,
    horizon_minutes: int = 30,
    threshold: float = 0.0005,
    symbol: str = "WING26",
) -> tuple[pd.DataFrame, pd.Series, DatasetMeta]:
    tables = load_sqlite_tables(db_path)
    reflections = _normalize_reflections(tables["reflections"])

    if include_jsonl:
        jsonl_df = _normalize_reflections(load_jsonl_reflections(jsonl_path))
        if not jsonl_df.empty:
            reflections = (
                pd.concat([reflections, jsonl_df], ignore_index=True)
                .drop_duplicates(subset=["timestamp"])
                .sort_values("timestamp")
            )

    feature_df = build_feature_frame(
        reflections,
        tables["journals"],
        tables["macro"],
        tables["alignment"],
        tolerance_minutes=tolerance_minutes,
    )

    labeled = add_labels(feature_df, horizon_minutes, threshold)
    labeled = labeled.dropna(subset=["label"]).reset_index(drop=True)

    start = labeled["timestamp"].min() if not labeled.empty else None
    end = labeled["timestamp"].max() if not labeled.empty else None

    meta = DatasetMeta(
        symbol=symbol,
        horizon_minutes=horizon_minutes,
        threshold=threshold,
        rows_total=len(feature_df),
        rows_labeled=len(labeled),
        start=start,
        end=end,
    )

    y = labeled.pop("label")
    return labeled, y, meta


def build_latest_features(
    db_path: Path,
    jsonl_path: Path,
    include_jsonl: bool = True,
    tolerance_minutes: int = 5,
) -> pd.DataFrame:
    tables = load_sqlite_tables(db_path)
    reflections = _normalize_reflections(tables["reflections"])

    if include_jsonl:
        jsonl_df = _normalize_reflections(load_jsonl_reflections(jsonl_path))
        if not jsonl_df.empty:
            reflections = (
                pd.concat([reflections, jsonl_df], ignore_index=True)
                .drop_duplicates(subset=["timestamp"])
                .sort_values("timestamp")
            )

    feature_df = build_feature_frame(
        reflections,
        tables["journals"],
        tables["macro"],
        tables["alignment"],
        tolerance_minutes=tolerance_minutes,
    )

    if feature_df.empty:
        return feature_df

    return feature_df.tail(1)
