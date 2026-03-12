"""
Prepara dataset real para P0-2 a partir da tabela market_data (origem MT5).

Gera:
- data/training_dataset.csv
- data/training_dataset.metadata.json

Contrato de saída:
- índice temporal ordenado crescente
- 24 features + close + label (0/1)
- metadata auditável com synthetic=false e hash SHA-256
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd


@dataclass
class PrepareResult:
    dataset_path: Path
    metadata_path: Path
    rows: int
    date_start: str
    date_end: str
    symbol: str
    timeframe: str
    lookback_days_requested: int
    lookback_days_actual: int


def _load_market_data(
    db_path: Path,
    symbol: str,
    timeframe: str,
    lookback_days: int,
) -> pd.DataFrame:
    if not db_path.exists():
        raise FileNotFoundError(f"Banco não encontrado: {db_path}")

    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            """
            SELECT MAX(timestamp)
            FROM market_data
            WHERE symbol = ? AND timeframe = ?
            """,
            (symbol, timeframe),
        ).fetchone()

        if not row or row[0] is None:
            raise ValueError(
                f"Sem dados em market_data para symbol={symbol} timeframe={timeframe}"
            )

        end_ts = pd.Timestamp(row[0])
        start_ts = end_ts - timedelta(days=lookback_days)

        df = pd.read_sql_query(
            """
            SELECT timestamp, open, high, low, close, volume
            FROM market_data
            WHERE symbol = ? AND timeframe = ?
              AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            conn,
            params=(symbol, timeframe, start_ts.strftime("%Y-%m-%d %H:%M:%S"), row[0]),
            parse_dates=["timestamp"],
        )

    if df.empty:
        raise ValueError(
            f"Consulta retornou 0 linhas para symbol={symbol} timeframe={timeframe}"
        )

    df = df.drop_duplicates(subset=["timestamp"]).set_index("timestamp").sort_index()
    return df


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    return 100 - (100 / (1 + rs))


def _rolling_corr_with_time(values: pd.Series, window: int = 20) -> pd.Series:
    def _corr(chunk: pd.Series) -> float:
        idx = np.arange(len(chunk), dtype=float)
        if len(chunk) < 2:
            return 0.0
        return float(np.corrcoef(idx, chunk.to_numpy(dtype=float))[0, 1])

    return values.rolling(window).apply(_corr, raw=False)


def _build_features(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    volume = df["volume"].astype(float)

    ret_1 = close.pct_change(1)
    ret_2 = close.pct_change(2)

    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    sma50 = close.rolling(50).mean()
    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr14 = tr.rolling(14).mean()

    obv = (np.sign(ret_1.fillna(0.0)) * volume).cumsum()
    vol_ma20 = volume.rolling(20).mean()
    future_ret_1 = close.shift(-1) / close - 1.0

    result = pd.DataFrame(index=df.index)
    result["close"] = close
    result["volatility_bollinger_upper"] = sma20 + 2 * std20
    result["volatility_bollinger_lower"] = sma20 - 2 * std20
    result["volatility_atr"] = atr14
    result["volatility_historical"] = ret_1.rolling(20).std()
    result["momentum_rsi"] = _rsi(close, 14)
    result["momentum_macd"] = ema12 - ema26
    result["momentum_roc"] = close.pct_change(10)
    result["momentum_obv"] = obv
    result["ma_sma_50"] = sma50
    result["ma_ema_9"] = ema9
    result["ma_ema_21"] = ema21
    result["ma_slope_short"] = ema9.diff(3)
    result["ma_slope_long"] = sma50.diff(10)
    result["pattern_mean_reversion"] = (close - sma20) / (std20 + 1e-9)
    result["pattern_volume_spike"] = volume / (vol_ma20 + 1e-9)
    result["pattern_impulse"] = ret_1.abs() / ((atr14 / close.replace(0, np.nan)) + 1e-9)
    result["lag_return_1"] = ret_1.shift(1)
    result["lag_return_2"] = ret_2.shift(1)
    result["lag_close_1"] = close.shift(1)
    result["lag_close_2"] = close.shift(2)
    result["lag_volume_1"] = volume.shift(1)
    result["lag_volume_2"] = volume.shift(2)
    result["correlation_20d"] = close.rolling(20).corr(volume)
    result["correlation_trend"] = _rolling_corr_with_time(close, 20)
    result["label"] = (future_ret_1 > 0).astype(int)

    result = result.replace([np.inf, -np.inf], np.nan).dropna()
    result.index = pd.to_datetime(result.index)
    result = result.sort_index()
    return result


def _write_metadata(
    dataset_path: Path,
    metadata_path: Path,
    *,
    symbol: str,
    timeframe: str,
    lookback_days_requested: int,
    lookback_days_actual: int,
) -> None:
    digest = sha256(dataset_path.read_bytes()).hexdigest()
    dataset_df = pd.read_csv(dataset_path, index_col=0, parse_dates=True)

    metadata = {
        "source": "market_data.sqlite",
        "source_type": "mt5_export_real",
        "symbol": symbol,
        "timeframe": timeframe,
        "rows": int(len(dataset_df)),
        "date_start": dataset_df.index.min().isoformat(),
        "date_end": dataset_df.index.max().isoformat(),
        "sha256": digest,
        "synthetic": False,
        "prepared_at": datetime.utcnow().isoformat() + "Z",
        "lookback_days_requested": lookback_days_requested,
        "lookback_days_actual": lookback_days_actual,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def prepare_dataset(
    *,
    db_path: Path,
    symbol: str,
    timeframe: str,
    lookback_days: int,
    min_rows: int,
    dataset_path: Path,
    metadata_path: Path,
) -> PrepareResult:
    raw = _load_market_data(
        db_path=db_path,
        symbol=symbol,
        timeframe=timeframe,
        lookback_days=lookback_days,
    )
    dataset = _build_features(raw)

    if len(dataset) < min_rows:
        raise ValueError(
            f"Dataset insuficiente para backtest: rows={len(dataset)} < min_rows={min_rows}"
        )

    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(dataset_path)

    lookback_days_actual = int((dataset.index.max() - dataset.index.min()).days)
    _write_metadata(
        dataset_path,
        metadata_path,
        symbol=symbol,
        timeframe=timeframe,
        lookback_days_requested=lookback_days,
        lookback_days_actual=lookback_days_actual,
    )

    return PrepareResult(
        dataset_path=dataset_path,
        metadata_path=metadata_path,
        rows=len(dataset),
        date_start=dataset.index.min().isoformat(),
        date_end=dataset.index.max().isoformat(),
        symbol=symbol,
        timeframe=timeframe,
        lookback_days_requested=lookback_days,
        lookback_days_actual=lookback_days_actual,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepara training_dataset real para P0-2")
    parser.add_argument("--db-path", default="data/db/trading.db")
    parser.add_argument("--symbol", default="WINJ26")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--lookback-days", type=int, default=365)
    parser.add_argument("--min-rows", type=int, default=1000)
    parser.add_argument("--dataset-path", default="data/training_dataset.csv")
    parser.add_argument("--metadata-path", default="data/training_dataset.metadata.json")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = prepare_dataset(
        db_path=Path(args.db_path),
        symbol=args.symbol,
        timeframe=args.timeframe,
        lookback_days=args.lookback_days,
        min_rows=args.min_rows,
        dataset_path=Path(args.dataset_path),
        metadata_path=Path(args.metadata_path),
    )

    print(
        "[OK] Dataset real preparado: "
        f"rows={result.rows} symbol={result.symbol} timeframe={result.timeframe} "
        f"range={result.date_start}..{result.date_end} "
        f"lookback_requested={result.lookback_days_requested}d "
        f"lookback_actual={result.lookback_days_actual}d"
    )
    print(f"[OK] Dataset: {result.dataset_path}")
    print(f"[OK] Metadata: {result.metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
