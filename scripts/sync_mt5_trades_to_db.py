#!/usr/bin/env python3
"""
Sincroniza operações reais do MetaTrader 5 para a tabela local `trades`.

Uso:
  python scripts/sync_mt5_trades_to_db.py --days-back 3
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
import uuid
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
class SyncTrade:
    trade_id: str
    symbol: str
    side: str
    quantity: int
    entry_price: float
    entry_time: datetime
    exit_price: float | None
    exit_time: datetime | None
    status: str
    broker_trade_id: str
    commission: float
    profit_loss: float | None
    return_percentage: float | None
    notes: str


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sincroniza trades reais do MT5 para SQLite local.")
    parser.add_argument("--days-back", type=int, default=3, help="Janela de dias para buscar histórico no MT5.")
    parser.add_argument(
        "--symbol-prefixes",
        type=str,
        default="WIN,WDO",
        help="Prefixos de símbolo separados por vírgula para sincronizar.",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=str(ROOT_DIR / "data" / "db" / "trading.db"),
        help="Caminho do SQLite local.",
    )
    return parser.parse_args()


def _connect_mt5() -> tuple[bool, str]:
    cfg = get_config()

    if not mt5.initialize():
        return False, f"Falha no initialize: {mt5.last_error()}"

    ok = mt5.login(login=cfg.mt5_login, password=cfg.mt5_password, server=cfg.mt5_server)
    if not ok:
        err = mt5.last_error()
        mt5.shutdown()
        return False, f"Falha no login MT5: {err}"

    return True, "OK"


def _weighted_price(deals: list) -> float | None:
    vol = sum(float(d.volume) for d in deals)
    if vol <= 0:
        return None
    return sum(float(d.price) * float(d.volume) for d in deals) / vol


def _build_sync_trade(position_id: int, deals: list, account_login: int) -> SyncTrade | None:
    if not deals:
        return None

    deals = sorted(deals, key=lambda d: int(d.time))

    deal_entry_in = getattr(mt5, "DEAL_ENTRY_IN", 0)
    deal_entry_out = getattr(mt5, "DEAL_ENTRY_OUT", 1)
    deal_entry_inout = getattr(mt5, "DEAL_ENTRY_INOUT", 2)
    deal_entry_out_by = getattr(mt5, "DEAL_ENTRY_OUT_BY", 3)

    in_deals = [d for d in deals if int(d.entry) in (deal_entry_in, deal_entry_inout)]
    out_deals = [d for d in deals if int(d.entry) in (deal_entry_out, deal_entry_out_by, deal_entry_inout)]

    if not in_deals:
        return None

    first_in = in_deals[0]

    deal_type_buy = getattr(mt5, "DEAL_TYPE_BUY", 0)
    side = "BUY" if int(first_in.type) == deal_type_buy else "SELL"

    in_vol = sum(float(d.volume) for d in in_deals)
    out_vol = sum(float(d.volume) for d in out_deals)

    entry_price = _weighted_price(in_deals) or float(first_in.price)
    entry_time = datetime.fromtimestamp(int(first_in.time))

    exit_price = _weighted_price(out_deals) if out_deals else None
    exit_time = datetime.fromtimestamp(int(out_deals[-1].time)) if out_deals else None

    closed = out_vol >= (in_vol - 1e-9) and len(out_deals) > 0
    status = "CLOSED" if closed else "OPEN"

    commission = sum(float(getattr(d, "commission", 0.0) or 0.0) for d in deals)
    fee = sum(float(getattr(d, "fee", 0.0) or 0.0) for d in deals)
    swap = sum(float(getattr(d, "swap", 0.0) or 0.0) for d in deals)
    profit = sum(float(getattr(d, "profit", 0.0) or 0.0) for d in deals)

    total_costs = commission + fee + swap
    profit_loss = profit - total_costs

    return_pct = None
    if closed and entry_price:
        if side == "BUY":
            return_pct = ((float(exit_price) - entry_price) / entry_price) * 100 if exit_price is not None else None
        else:
            return_pct = ((entry_price - float(exit_price)) / entry_price) * 100 if exit_price is not None else None

    trade_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_DNS,
            f"mt5:{account_login}:{position_id}:{first_in.symbol}:{int(first_in.ticket)}",
        )
    )

    notes = (
        f"sync_mt5 position_id={position_id}; "
        f"deals={[int(d.ticket) for d in deals]}; "
        f"orders={[int(d.order) for d in deals]}"
    )

    return SyncTrade(
        trade_id=trade_id,
        symbol=str(first_in.symbol),
        side=side,
        quantity=max(1, int(round(in_vol))),
        entry_price=float(entry_price),
        entry_time=entry_time,
        exit_price=float(exit_price) if exit_price is not None else None,
        exit_time=exit_time,
        status=status,
        broker_trade_id=str(position_id),
        commission=float(total_costs),
        profit_loss=float(profit_loss),
        return_percentage=float(return_pct) if return_pct is not None else None,
        notes=notes,
    )


def _upsert_trade(conn: sqlite3.Connection, trade: SyncTrade) -> tuple[str, int]:
    row = conn.execute(
        "SELECT id, status FROM trades WHERE trade_id = ?",
        (trade.trade_id,),
    ).fetchone()

    if row is None:
        conn.execute(
            """
            INSERT INTO trades (
                trade_id, symbol, side, quantity,
                entry_price, entry_time,
                exit_price, exit_time,
                stop_loss, take_profit,
                status, broker_trade_id,
                commission, profit_loss, return_percentage,
                notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                trade.trade_id,
                trade.symbol,
                trade.side,
                trade.quantity,
                trade.entry_price,
                trade.entry_time.isoformat(),
                trade.exit_price,
                trade.exit_time.isoformat() if trade.exit_time else None,
                trade.status,
                trade.broker_trade_id,
                trade.commission,
                trade.profit_loss,
                trade.return_percentage,
                trade.notes,
            ),
        )
        return "inserted", 1

    existing_id = int(row[0])
    existing_status = str(row[1])

    if existing_status == "CLOSED" and trade.status == "CLOSED":
        return "unchanged", existing_id

    conn.execute(
        """
        UPDATE trades
        SET symbol = ?, side = ?, quantity = ?,
            entry_price = ?, entry_time = ?,
            exit_price = ?, exit_time = ?,
            status = ?, broker_trade_id = ?,
            commission = ?, profit_loss = ?, return_percentage = ?,
            notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            trade.symbol,
            trade.side,
            trade.quantity,
            trade.entry_price,
            trade.entry_time.isoformat(),
            trade.exit_price,
            trade.exit_time.isoformat() if trade.exit_time else None,
            trade.status,
            trade.broker_trade_id,
            trade.commission,
            trade.profit_loss,
            trade.return_percentage,
            trade.notes,
            existing_id,
        ),
    )
    return "updated", existing_id


def main() -> int:
    args = _parse_args()

    db_path = Path(args.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    create_database(str(db_path))

    ok, msg = _connect_mt5()
    if not ok:
        print(f"[ERRO] {msg}")
        return 1

    account = mt5.account_info()
    account_login = int(account.login) if account else 0

    now = datetime.now()
    start = now - timedelta(days=max(1, args.days_back))

    deals = mt5.history_deals_get(start, now)
    if deals is None:
        err = mt5.last_error()
        mt5.shutdown()
        print(f"[ERRO] history_deals_get falhou: {err}")
        return 2

    prefixes = [p.strip().upper() for p in args.symbol_prefixes.split(",") if p.strip()]
    deals = [d for d in deals if any(str(d.symbol).upper().startswith(px) for px in prefixes)]

    grouped = defaultdict(list)
    for d in deals:
        position_id = int(getattr(d, "position_id", 0) or 0)
        key = position_id if position_id != 0 else int(d.order)
        grouped[key].append(d)

    sync_trades: list[SyncTrade] = []
    for key, group in grouped.items():
        t = _build_sync_trade(key, group, account_login)
        if t is not None:
            sync_trades.append(t)

    inserted = 0
    updated = 0
    unchanged = 0

    conn = sqlite3.connect(str(db_path))
    try:
        for t in sync_trades:
            result, _ = _upsert_trade(conn, t)
            if result == "inserted":
                inserted += 1
            elif result == "updated":
                updated += 1
            else:
                unchanged += 1
        conn.commit()
    finally:
        conn.close()
        mt5.shutdown()

    print(
        f"[OK] Sync MT5 concluído | deals_filtrados={len(deals)} | "
        f"trades_mapeados={len(sync_trades)} | inserted={inserted} | updated={updated} | unchanged={unchanged}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
