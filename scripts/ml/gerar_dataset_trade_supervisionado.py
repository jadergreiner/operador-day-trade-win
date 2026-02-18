#!/usr/bin/env python3
"""Gera dataset diário consolidado (features por trade) para treino supervisionado.

Fontes:
- trades (tabela operacional consolidada)
- mt5_deals_raw / mt5_orders_raw (microestrutura real)
- trade_audit_reports (status de reconciliação)

Saídas:
- data/ml/daily/trade_features_YYYYMMDD.csv
- data/ml/daily/trade_features_YYYYMMDD.parquet (se engine disponível)
- data/ml/trade_supervised_dataset.csv (acumulado histórico)
- data/ml/trade_supervised_dataset.parquet (acumulado histórico, se possível)
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT_DIR / "data" / "db" / "trading.db"
DEFAULT_DAILY_DIR = ROOT_DIR / "data" / "ml" / "daily"
DEFAULT_MASTER_CSV = ROOT_DIR / "data" / "ml" / "trade_supervised_dataset.csv"
DEFAULT_MASTER_PARQUET = ROOT_DIR / "data" / "ml" / "trade_supervised_dataset.parquet"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera dataset diário supervisionado por trade.")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Data da sessão (YYYY-MM-DD).")
    parser.add_argument("--db-path", default=str(DEFAULT_DB), help="Caminho do SQLite.")
    parser.add_argument("--symbol-prefixes", default="WIN,WDO", help="Prefixos de símbolos separados por vírgula.")
    parser.add_argument("--daily-dir", default=str(DEFAULT_DAILY_DIR), help="Diretório de saída diária.")
    parser.add_argument("--master-csv", default=str(DEFAULT_MASTER_CSV), help="CSV acumulado de treino supervisionado.")
    parser.add_argument("--master-parquet", default=str(DEFAULT_MASTER_PARQUET), help="Parquet acumulado de treino supervisionado.")
    parser.add_argument("--no-append-master", action="store_true", help="Não atualizar dataset histórico acumulado.")
    return parser.parse_args()


def _load_table(conn: sqlite3.Connection, query: str, params: tuple | list | None = None) -> pd.DataFrame:
    params = params or ()
    return pd.read_sql_query(query, conn, params=params)


def _weighted_avg(values: pd.Series, weights: pd.Series) -> float | None:
    w = weights.fillna(0).astype(float)
    v = values.fillna(0).astype(float)
    denom = w.sum()
    if denom <= 0:
        return None
    return float((v * w).sum() / denom)


def _build_deals_features(df_deals: pd.DataFrame) -> pd.DataFrame:
    if df_deals.empty:
        return pd.DataFrame(columns=["position_id"])

    in_entries = {0, 2}   # DEAL_ENTRY_IN / INOUT
    out_entries = {1, 2, 3}  # DEAL_ENTRY_OUT / INOUT / OUT_BY

    rows: list[dict] = []
    for pos_id, grp in df_deals.groupby("position_id", dropna=False):
        g = grp.copy().sort_values("time_exec")

        g_in = g[g["deal_entry"].isin(in_entries)]
        g_out = g[g["deal_entry"].isin(out_entries)]

        volume_in = float(g_in["volume"].fillna(0).sum())
        volume_out = float(g_out["volume"].fillna(0).sum())
        volume_total = float(g["volume"].fillna(0).sum())

        avg_entry = _weighted_avg(g_in["price"], g_in["volume"]) if not g_in.empty else None
        avg_exit = _weighted_avg(g_out["price"], g_out["volume"]) if not g_out.empty else None

        profit_raw = float(g["profit"].fillna(0).sum())
        commission_raw = float(g["commission"].fillna(0).sum())
        fee_raw = float(g["fee"].fillna(0).sum())
        swap_raw = float(g["swap"].fillna(0).sum())
        pnl_net_raw = profit_raw - commission_raw - fee_raw - swap_raw

        first_exec = g["time_exec"].min()
        last_exec = g["time_exec"].max()

        rows.append(
            {
                "position_id": str(int(pos_id)) if pd.notna(pos_id) else "",
                "mt5_deals_count": int(len(g)),
                "mt5_entry_deals_count": int(len(g_in)),
                "mt5_exit_deals_count": int(len(g_out)),
                "mt5_volume_in": volume_in,
                "mt5_volume_out": volume_out,
                "mt5_volume_total": volume_total,
                "mt5_avg_entry_price": avg_entry,
                "mt5_avg_exit_price": avg_exit,
                "mt5_profit_raw": profit_raw,
                "mt5_commission_raw": commission_raw,
                "mt5_fee_raw": fee_raw,
                "mt5_swap_raw": swap_raw,
                "mt5_pnl_net_raw": pnl_net_raw,
                "mt5_first_exec": first_exec,
                "mt5_last_exec": last_exec,
            }
        )

    return pd.DataFrame(rows)


def _build_orders_features(df_orders: pd.DataFrame) -> pd.DataFrame:
    if df_orders.empty:
        return pd.DataFrame(columns=["position_id"])

    rows: list[dict] = []
    for pos_id, grp in df_orders.groupby("position_id", dropna=False):
        g = grp.copy().sort_values("time_setup")

        rows.append(
            {
                "position_id": str(int(pos_id)) if pd.notna(pos_id) else "",
                "mt5_orders_count": int(len(g)),
                "mt5_order_type_nunique": int(g["order_type"].nunique(dropna=True)),
                "mt5_order_reason_nunique": int(g["order_reason"].nunique(dropna=True)),
                "mt5_order_state_last": float(g["order_state"].dropna().iloc[-1]) if g["order_state"].notna().any() else np.nan,
                "mt5_price_open_mean": float(g["price_open"].fillna(0).mean()) if len(g) else np.nan,
                "mt5_price_current_last": float(g["price_current"].dropna().iloc[-1]) if g["price_current"].notna().any() else np.nan,
                "mt5_sl_mean": float(g["sl"].fillna(0).mean()) if len(g) else np.nan,
                "mt5_tp_mean": float(g["tp"].fillna(0).mean()) if len(g) else np.nan,
            }
        )

    return pd.DataFrame(rows)


def _derive_targets(df: pd.DataFrame) -> pd.DataFrame:
    pnl = df["profit_loss"].fillna(0).astype(float)
    df["target_pnl"] = pnl
    df["target_is_win"] = (pnl > 0).astype(int)
    df["target_is_loss"] = (pnl < 0).astype(int)
    df["target_class"] = np.where(pnl > 0, "WIN", np.where(pnl < 0, "LOSS", "BREAKEVEN"))

    rr = pd.to_numeric(df.get("risk_reward_ratio", np.nan), errors="coerce") if "risk_reward_ratio" in df.columns else np.nan
    if isinstance(rr, pd.Series):
        df["risk_reward_ratio"] = rr

    return df


def _safe_to_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def main() -> int:
    args = _parse_args()

    report_date = args.date
    try:
        datetime.strptime(report_date, "%Y-%m-%d")
    except ValueError:
        print("[ERRO] --date inválida. Use YYYY-MM-DD.")
        return 2

    prefixes = [p.strip().upper() for p in args.symbol_prefixes.split(",") if p.strip()]

    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"[ERRO] Banco não encontrado: {db_path}")
        return 1

    daily_dir = Path(args.daily_dir)
    daily_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        trades = _load_table(
            conn,
            """
            SELECT *
            FROM trades
            WHERE substr(entry_time,1,10)=?
            ORDER BY entry_time ASC
            """,
            (report_date,),
        )

        if trades.empty:
            print(f"[AVISO] Nenhum trade encontrado para {report_date}.")
            return 0

        trades = trades[trades["symbol"].astype(str).str.upper().str.startswith(tuple(prefixes))].copy()

        deals = _load_table(
            conn,
            """
            SELECT *
            FROM mt5_deals_raw
            WHERE session_date=?
            ORDER BY time_exec ASC
            """,
            (report_date,),
        )
        orders = _load_table(
            conn,
            """
            SELECT *
            FROM mt5_orders_raw
            WHERE session_date=?
            ORDER BY time_setup ASC
            """,
            (report_date,),
        )

        audit = _load_table(
            conn,
            """
            SELECT *
            FROM trade_audit_reports
            WHERE report_date=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (report_date,),
        )

        try:
            watchdog_events = _load_table(
                conn,
                """
                SELECT event_type, action_taken, status
                FROM hedge_watchdog_events
                WHERE session_date=?
                """,
                (report_date,),
            )
        except Exception:
            watchdog_events = pd.DataFrame(columns=["event_type", "action_taken", "status"])

    finally:
        conn.close()

    deals_features = _build_deals_features(deals)
    orders_features = _build_orders_features(orders)

    df = trades.copy()
    df["broker_trade_id"] = df["broker_trade_id"].astype(str)

    if not deals_features.empty:
        df = df.merge(
            deals_features,
            left_on="broker_trade_id",
            right_on="position_id",
            how="left",
        )
    if not orders_features.empty:
        df = df.merge(
            orders_features,
            left_on="broker_trade_id",
            right_on="position_id",
            how="left",
            suffixes=("", "_ord"),
        )

    df["entry_time"] = _safe_to_datetime(df["entry_time"])
    df["exit_time"] = _safe_to_datetime(df["exit_time"])
    df["mt5_first_exec"] = _safe_to_datetime(df.get("mt5_first_exec", pd.Series(dtype="datetime64[ns]")))
    df["mt5_last_exec"] = _safe_to_datetime(df.get("mt5_last_exec", pd.Series(dtype="datetime64[ns]")))

    df["session_date"] = report_date
    df["entry_hour"] = df["entry_time"].dt.hour
    df["entry_minute"] = df["entry_time"].dt.minute
    df["entry_weekday"] = df["entry_time"].dt.weekday
    df["holding_minutes"] = ((df["exit_time"] - df["entry_time"]).dt.total_seconds() / 60.0).fillna(0.0)
    df["is_closed"] = (df["status"].astype(str).str.upper() == "CLOSED").astype(int)

    df["entry_price"] = pd.to_numeric(df["entry_price"], errors="coerce")
    df["exit_price"] = pd.to_numeric(df["exit_price"], errors="coerce")
    df["profit_loss"] = pd.to_numeric(df["profit_loss"], errors="coerce")
    df["commission"] = pd.to_numeric(df["commission"], errors="coerce")

    sign = np.where(df["side"].astype(str).str.upper() == "BUY", 1.0, -1.0)
    df["price_diff"] = (df["exit_price"] - df["entry_price"]).fillna(0.0)
    df["points_result_signed"] = df["price_diff"] * sign
    df["abs_points_moved"] = df["price_diff"].abs()

    df["slippage_entry_points"] = pd.to_numeric(df.get("entry_price"), errors="coerce") - pd.to_numeric(df.get("mt5_avg_entry_price"), errors="coerce")
    df["slippage_exit_points"] = pd.to_numeric(df.get("exit_price"), errors="coerce") - pd.to_numeric(df.get("mt5_avg_exit_price"), errors="coerce")

    df = _derive_targets(df)

    if not audit.empty:
        a = audit.iloc[0]
        df["audit_status"] = str(a.get("status", ""))
        df["audit_pnl_diff"] = float(a.get("pnl_diff", 0.0) or 0.0)
        df["audit_missing_in_sqlite"] = int(a.get("missing_in_sqlite", 0) or 0)
        df["audit_extra_in_sqlite"] = int(a.get("extra_in_sqlite", 0) or 0)
    else:
        df["audit_status"] = ""
        df["audit_pnl_diff"] = np.nan
        df["audit_missing_in_sqlite"] = np.nan
        df["audit_extra_in_sqlite"] = np.nan

    # Features diárias do watchdog hedge
    if watchdog_events.empty:
        df["watchdog_events_day"] = 0
        df["watchdog_orphan_detected_day"] = 0
        df["watchdog_auto_close_day"] = 0
    else:
        ev = watchdog_events.copy()
        ev["event_type"] = ev["event_type"].astype(str)
        ev["action_taken"] = ev["action_taken"].astype(str)
        ev["status"] = ev["status"].astype(str)

        df["watchdog_events_day"] = int(len(ev))
        df["watchdog_orphan_detected_day"] = int((ev["event_type"] == "ORPHAN_DETECTED").sum())
        df["watchdog_auto_close_day"] = int(((ev["action_taken"] == "AUTO_CLOSE") & (ev["status"] == "SUCCESS")).sum())

    # Limpeza de colunas auxiliares de merge
    for c in ["position_id", "position_id_ord"]:
        if c in df.columns:
            df.drop(columns=[c], inplace=True)

    # Ordenação para consistência
    sort_cols = [c for c in ["entry_time", "trade_id"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)

    date_token = report_date.replace("-", "")
    daily_csv = daily_dir / f"trade_features_{date_token}.csv"
    daily_parquet = daily_dir / f"trade_features_{date_token}.parquet"

    df.to_csv(daily_csv, index=False, encoding="utf-8")

    parquet_daily_ok = True
    try:
        df.to_parquet(daily_parquet, index=False)
    except Exception as exc:
        parquet_daily_ok = False
        print(f"[AVISO] Não foi possível gravar Parquet diário: {exc}")

    if not args.no_append_master:
        master_csv = Path(args.master_csv)
        master_csv.parent.mkdir(parents=True, exist_ok=True)

        if master_csv.exists():
            old = pd.read_csv(master_csv)
            merged = pd.concat([old, df], ignore_index=True)
        else:
            merged = df.copy()

        merged = merged.drop_duplicates(subset=["trade_id", "session_date"], keep="last")
        merged = merged.sort_values(["session_date", "entry_time"], na_position="last").reset_index(drop=True)
        merged.to_csv(master_csv, index=False, encoding="utf-8")

        master_parquet = Path(args.master_parquet)
        try:
            merged.to_parquet(master_parquet, index=False)
        except Exception as exc:
            print(f"[AVISO] Não foi possível gravar Parquet acumulado: {exc}")

    print("=" * 90)
    print(f"DATASET SUPERVISIONADO GERADO | data={report_date} | linhas={len(df)} | colunas={len(df.columns)}")
    print("=" * 90)
    print(f"Daily CSV: {daily_csv}")
    if parquet_daily_ok:
        print(f"Daily Parquet: {daily_parquet}")
    if not args.no_append_master:
        print(f"Master CSV: {args.master_csv}")
        print(f"Master Parquet: {args.master_parquet}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
