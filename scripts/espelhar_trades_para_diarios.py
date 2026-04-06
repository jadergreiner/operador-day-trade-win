"""Espelha trades CLOSED do dia do DB fonte para trading_diarios.db.

Uso:
    python scripts/espelhar_trades_para_diarios.py --src <fonte.db> --dst <destino.db>
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Espelha trades CLOSED do dia para trading_diarios.db"
    )
    parser.add_argument("--src", required=True, help="Caminho do banco fonte (RL direto)")
    parser.add_argument("--dst", required=True, help="Caminho do banco destino (diarios)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    src_path = Path(args.src).resolve()
    dst_path = Path(args.dst).resolve()

    if not src_path.exists():
        print(f"[ERRO] Banco fonte nao encontrado: {src_path}")
        return 1

    if not dst_path.exists():
        print(f"[ERRO] Banco destino nao encontrado: {dst_path}")
        return 1

    today = datetime.now().date().isoformat()

    query_select = """
        SELECT
            trade_id, symbol, side, quantity, entry_price, entry_time, exit_price,
            exit_time, stop_loss, take_profit, status, broker_trade_id, commission,
            profit_loss, return_percentage, notes, created_at, updated_at, execution_method
        FROM trades
        WHERE DATE(entry_time) = ? AND status = 'CLOSED'
    """
    query_exists = "SELECT id FROM trades WHERE trade_id = ?"
    query_insert = """
        INSERT INTO trades (
            trade_id, symbol, side, quantity, entry_price, entry_time, exit_price,
            exit_time, stop_loss, take_profit, status, broker_trade_id, commission,
            profit_loss, return_percentage, notes, created_at, updated_at, execution_method
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """

    inserted = 0
    with sqlite3.connect(src_path) as src, sqlite3.connect(dst_path) as dst:
        src_cur = src.cursor()
        dst_cur = dst.cursor()
        src_cur.execute(query_select, (today,))
        rows = src_cur.fetchall()

        for row in rows:
            dst_cur.execute(query_exists, (row[0],))
            if dst_cur.fetchone():
                continue
            dst_cur.execute(query_insert, row)
            inserted += 1

        dst.commit()

    print(f"[OK] {inserted} trades espelhados para trading_diarios.db ({today})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except sqlite3.Error as exc:
        print(f"[ERRO] Falha SQLite no espelhamento: {exc}")
        raise SystemExit(1) from exc
    except Exception as exc:  # noqa: BLE001
        print(f"[ERRO] Falha inesperada no espelhamento: {exc}")
        raise SystemExit(1) from exc
