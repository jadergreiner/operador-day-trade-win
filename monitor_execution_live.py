#!/usr/bin/env python
"""Monitorar status da execução automática em tempo real."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path("data/db/trading.db")


def monitor_execution():
    """Monitora status atual da execução."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        print("\n" + "=" * 100)
        print("📊 STATUS DE EXECUÇÃO - SISTEMA AUTOMÁTICO")
        print("=" * 100)
        print(f"\nHorário: {datetime.now().strftime('%d/02/2026 %H:%M:%S')}")

        # 1. Ordens recentes
        cursor.execute("""
            SELECT 
                id, trade_id, symbol, side, entry_price, entry_time,
                status, execution_method, stop_loss, take_profit, profit_loss
            FROM trades
            WHERE entry_time > datetime('now', '-3 hours')
            ORDER BY entry_time DESC
            LIMIT 10
        """)

        recent = cursor.fetchall()
        
        print("\n" + "-" * 100)
        print("📋 ÚLTIMAS ORDENS (ÚLTIMAS 3H)")
        print("-" * 100)

        if recent:
            for trade in recent:
                pid, tid, sym, side, entry, et, status, method, sl, tp, pnl = trade
                icon = "🤖" if method == "automated" else "👤"
                time_str = et.split("T")[1].split(".")[0] if et else "N/A"
                sl_str = f"{float(sl):.2f}" if sl else "NULL"
                tp_str = f"{float(tp):.2f}" if tp else "NULL"
                pnl_str = f"{float(pnl):+.2f}" if pnl else "-"
                
                print(f"{icon} {sym:10} {side:6} {time_str:10} SL:{sl_str:10} TP:{tp_str:10} P&L:{pnl_str:10}")
        else:
            print("❌ Nenhuma ordem criada ainda")

        # 2. Estatísticas gerais
        cursor.execute("""
            SELECT 
                execution_method,
                COUNT(*) as total,
                SUM(CASE WHEN status='CLOSED' THEN 1 ELSE 0 END) as fechadas,
                SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END) as abertas
            FROM trades
            GROUP BY execution_method
            ORDER BY execution_method
        """)

        stats = cursor.fetchall()
        
        print("\n" + "-" * 100)
        print("📊 ESTATÍSTICAS GERAIS")
        print("-" * 100)

        for method, total, closed, open_count in stats:
            icon = "👤" if method == "manual" else "🤖"
            print(f"{icon} {method:10} → Total: {total:3} | Fechadas: {closed:3} | Abertas: {open_count:3}")

        # 3. Data de última ordem
        cursor.execute("SELECT MAX(entry_time) FROM trades")
        last_time = cursor.fetchone()[0]
        if last_time:
            print(f"\n⏰ Última ordem: {last_time}")

        # 4. Status do banco
        print("\n" + "-" * 100)
        print("✅ STATUS DO SISTEMA")
        print("-" * 100)

        if recent:
            automated_recent = [t for t in recent if t[7] == "automated"]
            if automated_recent:
                print("✅ Sistema automático está GERANDO ordens")
                
                # Verificar se têm SL/TP
                with_sl_tp = [t for t in automated_recent if t[8] is not None and t[9] is not None]
                if with_sl_tp:
                    print(f"✅ Ordens automáticas com SL/TP: {len(with_sl_tp)}/{len(automated_recent)}")
                else:
                    print(f"⚠️ Ordens automáticas SEM SL/TP: {len(automated_recent)}")
            else:
                print("⏳ Aguardando primeira ordem automática...")
        else:
            print("⏳ Sistema iniciado - aguardando primeiras ordens...")

        conn.close()

    except Exception as e:
        print(f"❌ Erro ao monitorar: {e}")


if __name__ == "__main__":
    monitor_execution()
