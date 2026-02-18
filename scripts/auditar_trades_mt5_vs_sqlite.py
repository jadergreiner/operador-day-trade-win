#!/usr/bin/env python3
"""
Auditoria MT5 vs SQLite com persistência de dados brutos para aprendizado.

Objetivos:
1) Buscar ordens e deals reais no MT5 por data
2) Persistir ordens/deals brutos no SQLite (feature store operacional)
3) Reconciliar com tabela local `trades`
4) Gerar relatório JSON e registrar resumo em tabela de auditoria

Uso:
  python scripts/auditar_trades_mt5_vs_sqlite.py --date 2026-02-13
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import MetaTrader5 as mt5

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import get_config
from src.infrastructure.database.schema import create_database


@dataclass
class PositionSummary:
    position_id: int
    symbol: str
    side: str
    entry_time: str
    exit_time: str | None
    status: str
    volume: float
    entry_price: float
    exit_price: float | None
    realized_pnl: float
    deals_count: int


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audita operações reais MT5 vs SQLite.")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"), help="Data da auditoria (YYYY-MM-DD).")
    parser.add_argument("--symbol-prefixes", type=str, default="WIN,WDO", help="Prefixos de símbolos separados por vírgula.")
    parser.add_argument("--db-path", type=str, default=str(ROOT_DIR / "data" / "db" / "trading.db"), help="Caminho do SQLite.")
    return parser.parse_args()


def _connect_mt5() -> None:
    cfg = get_config()

    if not mt5.initialize():
        raise RuntimeError(f"Falha no initialize MT5: {mt5.last_error()}")

    ok = mt5.login(login=cfg.mt5_login, password=cfg.mt5_password, server=cfg.mt5_server)
    if not ok:
        err = mt5.last_error()
        mt5.shutdown()
        raise RuntimeError(f"Falha no login MT5: {err}")


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS mt5_orders_raw (
            order_ticket INTEGER PRIMARY KEY,
            position_id INTEGER,
            symbol TEXT NOT NULL,
            order_type INTEGER,
            order_state INTEGER,
            order_reason INTEGER,
            volume_initial REAL,
            volume_current REAL,
            price_open REAL,
            price_current REAL,
            sl REAL,
            tp REAL,
            time_setup TEXT,
            time_done TEXT,
            comment TEXT,
            external_id TEXT,
            session_date TEXT NOT NULL,
            synced_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS ix_mt5_orders_raw_session ON mt5_orders_raw(session_date, symbol);

        CREATE TABLE IF NOT EXISTS mt5_deals_raw (
            deal_ticket INTEGER PRIMARY KEY,
            order_ticket INTEGER,
            position_id INTEGER,
            symbol TEXT NOT NULL,
            deal_type INTEGER,
            deal_entry INTEGER,
            deal_reason INTEGER,
            volume REAL,
            price REAL,
            profit REAL,
            commission REAL,
            fee REAL,
            swap REAL,
            time_exec TEXT,
            comment TEXT,
            external_id TEXT,
            session_date TEXT NOT NULL,
            synced_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS ix_mt5_deals_raw_session ON mt5_deals_raw(session_date, symbol);

        CREATE TABLE IF NOT EXISTS trade_audit_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            mt5_orders_count INTEGER NOT NULL,
            mt5_deals_count INTEGER NOT NULL,
            mt5_positions_count INTEGER NOT NULL,
            sqlite_trades_count INTEGER NOT NULL,
            sqlite_closed_count INTEGER NOT NULL,
            sqlite_open_count INTEGER NOT NULL,
            mt5_realized_pnl REAL NOT NULL,
            sqlite_realized_pnl REAL NOT NULL,
            pnl_diff REAL NOT NULL,
            missing_in_sqlite INTEGER NOT NULL,
            extra_in_sqlite INTEGER NOT NULL,
            status TEXT NOT NULL,
            report_file TEXT,
            details_json TEXT
        );

        CREATE INDEX IF NOT EXISTS ix_trade_audit_reports_date ON trade_audit_reports(report_date, generated_at);
        """
    )
    conn.commit()


def _weighted_price(items: list) -> float | None:
    total_vol = sum(float(i.volume) for i in items)
    if total_vol <= 0:
        return None
    return sum(float(i.price) * float(i.volume) for i in items) / total_vol


def _build_position_summaries(deals: list) -> list[PositionSummary]:
    deal_entry_in = getattr(mt5, "DEAL_ENTRY_IN", 0)
    deal_entry_out = getattr(mt5, "DEAL_ENTRY_OUT", 1)
    deal_entry_inout = getattr(mt5, "DEAL_ENTRY_INOUT", 2)
    deal_entry_out_by = getattr(mt5, "DEAL_ENTRY_OUT_BY", 3)
    deal_type_buy = getattr(mt5, "DEAL_TYPE_BUY", 0)

    grouped: dict[int, list] = defaultdict(list)
    for d in deals:
        pid = int(getattr(d, "position_id", 0) or 0)
        key = pid if pid != 0 else int(d.order)
        grouped[key].append(d)

    summaries: list[PositionSummary] = []
    for pid, group in grouped.items():
        group = sorted(group, key=lambda d: int(d.time))

        in_deals = [d for d in group if int(d.entry) in (deal_entry_in, deal_entry_inout)]
        out_deals = [d for d in group if int(d.entry) in (deal_entry_out, deal_entry_out_by, deal_entry_inout)]
        if not in_deals:
            continue

        first_in = in_deals[0]
        side = "BUY" if int(first_in.type) == deal_type_buy else "SELL"

        in_vol = sum(float(d.volume) for d in in_deals)
        out_vol = sum(float(d.volume) for d in out_deals)

        closed = out_vol >= (in_vol - 1e-9) and len(out_deals) > 0
        status = "CLOSED" if closed else "OPEN"

        entry_price = _weighted_price(in_deals) or float(first_in.price)
        exit_price = _weighted_price(out_deals) if out_deals else None

        realized_pnl = sum(float(getattr(d, "profit", 0.0) or 0.0) for d in group)
        realized_pnl -= sum(float(getattr(d, "commission", 0.0) or 0.0) for d in group)
        realized_pnl -= sum(float(getattr(d, "fee", 0.0) or 0.0) for d in group)
        realized_pnl -= sum(float(getattr(d, "swap", 0.0) or 0.0) for d in group)

        summaries.append(
            PositionSummary(
                position_id=int(pid),
                symbol=str(first_in.symbol),
                side=side,
                entry_time=datetime.fromtimestamp(int(first_in.time)).isoformat(),
                exit_time=datetime.fromtimestamp(int(out_deals[-1].time)).isoformat() if out_deals else None,
                status=status,
                volume=in_vol,
                entry_price=float(entry_price),
                exit_price=float(exit_price) if exit_price is not None else None,
                realized_pnl=float(realized_pnl),
                deals_count=len(group),
            )
        )

    return summaries


def _persist_raw(conn: sqlite3.Connection, report_date: str, orders: list, deals: list) -> None:
    synced_at = datetime.now().isoformat()

    for o in orders:
        conn.execute(
            """
            INSERT INTO mt5_orders_raw (
                order_ticket, position_id, symbol,
                order_type, order_state, order_reason,
                volume_initial, volume_current,
                price_open, price_current, sl, tp,
                time_setup, time_done,
                comment, external_id, session_date, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(order_ticket) DO UPDATE SET
                position_id=excluded.position_id,
                symbol=excluded.symbol,
                order_type=excluded.order_type,
                order_state=excluded.order_state,
                order_reason=excluded.order_reason,
                volume_initial=excluded.volume_initial,
                volume_current=excluded.volume_current,
                price_open=excluded.price_open,
                price_current=excluded.price_current,
                sl=excluded.sl,
                tp=excluded.tp,
                time_setup=excluded.time_setup,
                time_done=excluded.time_done,
                comment=excluded.comment,
                external_id=excluded.external_id,
                session_date=excluded.session_date,
                synced_at=excluded.synced_at
            """,
            (
                int(o.ticket),
                int(getattr(o, "position_id", 0) or 0),
                str(o.symbol),
                int(o.type),
                int(o.state),
                int(getattr(o, "reason", 0) or 0),
                float(getattr(o, "volume_initial", 0.0) or 0.0),
                float(getattr(o, "volume_current", 0.0) or 0.0),
                float(getattr(o, "price_open", 0.0) or 0.0),
                float(getattr(o, "price_current", 0.0) or 0.0),
                float(getattr(o, "sl", 0.0) or 0.0),
                float(getattr(o, "tp", 0.0) or 0.0),
                datetime.fromtimestamp(int(getattr(o, "time_setup", 0) or 0)).isoformat() if int(getattr(o, "time_setup", 0) or 0) > 0 else None,
                datetime.fromtimestamp(int(getattr(o, "time_done", 0) or 0)).isoformat() if int(getattr(o, "time_done", 0) or 0) > 0 else None,
                str(getattr(o, "comment", "") or ""),
                str(getattr(o, "external_id", "") or ""),
                report_date,
                synced_at,
            ),
        )

    for d in deals:
        conn.execute(
            """
            INSERT INTO mt5_deals_raw (
                deal_ticket, order_ticket, position_id, symbol,
                deal_type, deal_entry, deal_reason,
                volume, price, profit, commission, fee, swap,
                time_exec, comment, external_id,
                session_date, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(deal_ticket) DO UPDATE SET
                order_ticket=excluded.order_ticket,
                position_id=excluded.position_id,
                symbol=excluded.symbol,
                deal_type=excluded.deal_type,
                deal_entry=excluded.deal_entry,
                deal_reason=excluded.deal_reason,
                volume=excluded.volume,
                price=excluded.price,
                profit=excluded.profit,
                commission=excluded.commission,
                fee=excluded.fee,
                swap=excluded.swap,
                time_exec=excluded.time_exec,
                comment=excluded.comment,
                external_id=excluded.external_id,
                session_date=excluded.session_date,
                synced_at=excluded.synced_at
            """,
            (
                int(d.ticket),
                int(getattr(d, "order", 0) or 0),
                int(getattr(d, "position_id", 0) or 0),
                str(d.symbol),
                int(getattr(d, "type", 0) or 0),
                int(getattr(d, "entry", 0) or 0),
                int(getattr(d, "reason", 0) or 0),
                float(getattr(d, "volume", 0.0) or 0.0),
                float(getattr(d, "price", 0.0) or 0.0),
                float(getattr(d, "profit", 0.0) or 0.0),
                float(getattr(d, "commission", 0.0) or 0.0),
                float(getattr(d, "fee", 0.0) or 0.0),
                float(getattr(d, "swap", 0.0) or 0.0),
                datetime.fromtimestamp(int(d.time)).isoformat(),
                str(getattr(d, "comment", "") or ""),
                str(getattr(d, "external_id", "") or ""),
                report_date,
                synced_at,
            ),
        )

    conn.commit()


def _load_sqlite_trades(conn: sqlite3.Connection, report_date: str, prefixes: list[str]) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT * FROM trades
        WHERE substr(entry_time,1,10)=?
        ORDER BY entry_time ASC
        """,
        (report_date,),
    )
    rows = cur.fetchall()

    return [r for r in rows if any(str(r["symbol"]).upper().startswith(px) for px in prefixes)]


def _build_report(report_date: str, mt5_orders: list, mt5_deals: list, mt5_positions: list[PositionSummary], sqlite_trades: list[sqlite3.Row]) -> dict:
    mt5_realized_pnl = round(sum(p.realized_pnl for p in mt5_positions if p.status == "CLOSED"), 2)

    sqlite_closed = [r for r in sqlite_trades if str(r["status"]).upper() == "CLOSED"]
    sqlite_open = [r for r in sqlite_trades if str(r["status"]).upper() != "CLOSED"]

    sqlite_realized_pnl = round(sum(float(r["profit_loss"] or 0.0) for r in sqlite_closed), 2)

    mt5_by_pid = {str(p.position_id): p for p in mt5_positions}
    sqlite_by_pid = {str(r["broker_trade_id"]): r for r in sqlite_trades if r["broker_trade_id"]}

    missing_in_sqlite = sorted([pid for pid in mt5_by_pid.keys() if pid not in sqlite_by_pid])
    extra_in_sqlite = sorted([pid for pid in sqlite_by_pid.keys() if pid not in mt5_by_pid])

    pnl_diffs = []
    for pid, p in mt5_by_pid.items():
        row = sqlite_by_pid.get(pid)
        if not row:
            continue
        db_pnl = float(row["profit_loss"] or 0.0)
        diff = round(p.realized_pnl - db_pnl, 2)
        if abs(diff) > 0.01:
            pnl_diffs.append(
                {
                    "broker_trade_id": pid,
                    "mt5_pnl": round(p.realized_pnl, 2),
                    "sqlite_pnl": round(db_pnl, 2),
                    "diff": diff,
                }
            )

    pnl_diff_total = round(mt5_realized_pnl - sqlite_realized_pnl, 2)

    status = "OK"
    if missing_in_sqlite or extra_in_sqlite or abs(pnl_diff_total) > 0.01 or pnl_diffs:
        status = "DIVERGENTE"

    return {
        "report_date": report_date,
        "generated_at": datetime.now().isoformat(),
        "counts": {
            "mt5_orders": len(mt5_orders),
            "mt5_deals": len(mt5_deals),
            "mt5_positions": len(mt5_positions),
            "sqlite_trades": len(sqlite_trades),
            "sqlite_closed": len(sqlite_closed),
            "sqlite_open": len(sqlite_open),
        },
        "pnl": {
            "mt5_realized": mt5_realized_pnl,
            "sqlite_realized": sqlite_realized_pnl,
            "diff": pnl_diff_total,
        },
        "reconciliation": {
            "missing_in_sqlite": missing_in_sqlite,
            "extra_in_sqlite": extra_in_sqlite,
            "pnl_diffs_by_trade": pnl_diffs,
        },
        "positions": [p.__dict__ for p in mt5_positions],
        "status": status,
    }


def _persist_report(conn: sqlite3.Connection, report: dict, report_file: Path) -> None:
    conn.execute(
        """
        INSERT INTO trade_audit_reports (
            report_date, generated_at,
            mt5_orders_count, mt5_deals_count, mt5_positions_count,
            sqlite_trades_count, sqlite_closed_count, sqlite_open_count,
            mt5_realized_pnl, sqlite_realized_pnl, pnl_diff,
            missing_in_sqlite, extra_in_sqlite,
            status, report_file, details_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report["report_date"],
            report["generated_at"],
            int(report["counts"]["mt5_orders"]),
            int(report["counts"]["mt5_deals"]),
            int(report["counts"]["mt5_positions"]),
            int(report["counts"]["sqlite_trades"]),
            int(report["counts"]["sqlite_closed"]),
            int(report["counts"]["sqlite_open"]),
            float(report["pnl"]["mt5_realized"]),
            float(report["pnl"]["sqlite_realized"]),
            float(report["pnl"]["diff"]),
            int(len(report["reconciliation"]["missing_in_sqlite"])),
            int(len(report["reconciliation"]["extra_in_sqlite"])),
            report["status"],
            str(report_file),
            json.dumps(report, ensure_ascii=False),
        ),
    )
    conn.commit()


def main() -> int:
    args = _parse_args()
    report_date = args.date

    try:
        day_start = datetime.strptime(report_date, "%Y-%m-%d")
    except ValueError:
        print("[ERRO] --date inválida. Use YYYY-MM-DD.")
        return 2

    day_end = day_start + timedelta(days=1) - timedelta(seconds=1)

    db_path = Path(args.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    create_database(str(db_path))

    prefixes = [p.strip().upper() for p in args.symbol_prefixes.split(",") if p.strip()]

    try:
        _connect_mt5()

        orders = mt5.history_orders_get(day_start, day_end)
        if orders is None:
            raise RuntimeError(f"history_orders_get falhou: {mt5.last_error()}")

        deals = mt5.history_deals_get(day_start, day_end)
        if deals is None:
            raise RuntimeError(f"history_deals_get falhou: {mt5.last_error()}")

        orders_f = [o for o in orders if any(str(o.symbol).upper().startswith(px) for px in prefixes)]
        deals_f = [d for d in deals if any(str(d.symbol).upper().startswith(px) for px in prefixes)]
        positions = _build_position_summaries(deals_f)

        conn = sqlite3.connect(str(db_path))
        try:
            _ensure_tables(conn)
            _persist_raw(conn, report_date, orders_f, deals_f)
            sqlite_trades = _load_sqlite_trades(conn, report_date, prefixes)

            report = _build_report(report_date, orders_f, deals_f, positions, sqlite_trades)

            out_dir = ROOT_DIR / "data" / "auditoria"
            out_dir.mkdir(parents=True, exist_ok=True)
            report_file = out_dir / f"trade_audit_{report_date.replace('-', '')}_{datetime.now().strftime('%H%M%S')}.json"
            report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

            _persist_report(conn, report, report_file)
        finally:
            conn.close()

    except Exception as exc:
        print(f"[ERRO] Auditoria falhou: {exc}")
        return 1
    finally:
        mt5.shutdown()

    print("=" * 84)
    print(f"AUDITORIA MT5 x SQLITE | data={report_date} | status={report['status']}")
    print("=" * 84)
    print(
        "MT5: orders={mt5o} deals={mt5d} positions={mt5p} | SQLite: trades={dbt} closed={dbc} open={dbo}".format(
            mt5o=report["counts"]["mt5_orders"],
            mt5d=report["counts"]["mt5_deals"],
            mt5p=report["counts"]["mt5_positions"],
            dbt=report["counts"]["sqlite_trades"],
            dbc=report["counts"]["sqlite_closed"],
            dbo=report["counts"]["sqlite_open"],
        )
    )
    print(
        f"PnL realizado MT5={report['pnl']['mt5_realized']:.2f} | SQLite={report['pnl']['sqlite_realized']:.2f} | diff={report['pnl']['diff']:.2f}"
    )
    print(
        f"Faltando no SQLite={len(report['reconciliation']['missing_in_sqlite'])} | Extras no SQLite={len(report['reconciliation']['extra_in_sqlite'])}"
    )
    print(f"Relatório: {report_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
