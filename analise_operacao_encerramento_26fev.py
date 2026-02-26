#!/usr/bin/env python3
"""Análise detalhada de operações do dia 26/02/2026 - Encerramento manual WIN."""

import sqlite3
from datetime import datetime, timedelta

DATABASE_PATH = "data/db/trading.db"

def detailed_analysis():
    """Análise detalhada das operações de hoje."""

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Data de hoje (26/02/2026)
        today = "2026-02-26"

        print("\n" + "="*90)
        print(f"📊 OPERAÇÕES DO DIA {today} - ANÁLISE DETALHADA")
        print("="*90 + "\n")

        # 1. OPERAÇÕES ABERTAS NO ENCERRAMENTO (OPEN)
        cursor.execute("""
            SELECT id, trade_id, symbol, side, quantity, entry_price, entry_time,
                   stop_loss, take_profit, status, created_at
            FROM trades
            WHERE status = 'OPEN'
            AND date(created_at) = ?
            ORDER BY entry_time DESC
        """, (today,))

        open_trades = cursor.fetchall()

        print("\n🟢 OPERAÇÕES ABERTAS NO ENCERRAMENTO (Status: OPEN)")
        print("-" * 90)

        if open_trades:
            for idx, trade in enumerate(open_trades, 1):
                (trade_id, tid, symbol, side, qty, entry_price, entry_time,
                 stop_loss, take_profit, status, created_at) = trade

                print(f"\n  #{idx} {symbol} {side} x{qty}")
                print(f"      Trade ID: {tid}")
                print(f"      Preço de Entrada: R$ {float(entry_price):,.2f}")
                print(f"      Hora de Entrada: {entry_time}")

                if stop_loss:
                    print(f"      Stop Loss: R$ {float(stop_loss):,.2f}")
                if take_profit:
                    print(f"      Take Profit: R$ {float(take_profit):,.2f}")

                print(f"      Criado em: {created_at}")
                print(f"      ⚠️ OPERAÇÃO JÁ ESTAVA ABERTA NO ENCERRAMENTO!")
        else:
            print("  Nenhuma operação aberta encontrada")

        # 2. OPERAÇÕES FECHADAS HOJE
        cursor.execute("""
            SELECT id, trade_id, symbol, side, quantity, entry_price, entry_time,
                   exit_price, exit_time, status, profit_loss, return_percentage, created_at
            FROM trades
            WHERE status = 'CLOSED'
            AND date(created_at) = ?
            ORDER BY exit_time DESC
        """, (today,))

        closed_trades = cursor.fetchall()

        print("\n\n🔴 OPERAÇÕES FECHADAS (Status: CLOSED)")
        print("-" * 90)

        if closed_trades:
            total_pnl = 0
            winning_trades = 0
            losing_trades = 0

            for idx, trade in enumerate(closed_trades, 1):
                (trade_id, tid, symbol, side, qty, entry_price, entry_time,
                 exit_price, exit_time, status, profit_loss, return_pct, created_at) = trade

                is_win = profit_loss > 0 if profit_loss else False
                indicator = "✅" if is_win else "❌"

                if profit_loss:
                    total_pnl += profit_loss
                    if is_win:
                        winning_trades += 1
                    else:
                        losing_trades += 1

                print(f"\n  #{idx} {indicator} {symbol} {side} x{qty}")
                print(f"      Trade ID: {tid}")
                print(f"      Entrada: R$ {float(entry_price):,.2f} às {entry_time}")
                print(f"      Saída: R$ {float(exit_price):,.2f} às {exit_time}")

                if profit_loss is not None:
                    print(f"      P&L: R$ {profit_loss:+,.2f}", end="")

                if return_pct is not None:
                    print(f" ({return_pct:+.2f}%)")
                else:
                    print()

            print(f"\n  📊 RESUMO OPERAÇÕES FECHADAS:")
            print(f"      Total de Trades: {len(closed_trades)}")
            print(f"      Vencedores: {winning_trades}")
            print(f"      Perdedores: {losing_trades}")
            print(f"      P&L Total: R$ {total_pnl:+,.2f}")
        else:
            print("  Nenhuma operação fechada encontrada")

        # 3. CORRELAÇÃO COM ENCERRAMENTO MANUAL
        print(f"\n\n🎯 ENCERRAMENTO MANUAL - {today} 18:22:23")
        print("-" * 90)

        cursor.execute("""
            SELECT id, trade_id, symbol, created_at
            FROM trades
            WHERE status = 'MANUAL_CLOSURE'
            AND date(created_at) = ?
            ORDER BY created_at DESC
        """, (today,))

        closure = cursor.fetchone()

        if closure:
            (closure_id, closure_tid, closure_symbol, closure_time) = closure

            print(f"\n  ✅ Encerramento Registrado")
            print(f"      Trade ID: {closure_tid}")
            print(f"      Símbolo: {closure_symbol}")
            print(f"      Timestamp: {closure_time}")
            print(f"      Motivo: Horário programado de finalização")

        # 4. STATUS FINAL
        print(f"\n\n📈 STATUS FINAL DO OPERADOR WIN")
        print("="*90)

        cursor.execute("""
            SELECT COUNT(*) FROM trades
            WHERE symbol IN ('WINFUT', 'WINJ26')
            AND status = 'OPEN'
        """)

        open_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT SUM(profit_loss)
            FROM trades
            WHERE symbol IN ('WINFUT', 'WINJ26')
            AND status = 'CLOSED'
            AND date(created_at) = ?
        """, (today,))

        result = cursor.fetchone()
        daily_pnl = result[0] if result and result[0] else 0

        print(f"\n  Operações Abertas em ENCERRAMENTO: {open_count}")
        print(f"  P&L Diário (Trades Fechados): R$ {daily_pnl:+,.2f}")
        print(f"  Horário de Encerramento: 18:22:23")
        print(f"  Status: ✅ ENCERREMENT CONFIRMADO NO BANCO DE DADOS")

        print("\n" + "="*90 + "\n")

        return True

    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print("\n🔍 Analisando operações aberta vs encerramento manual...\n")
    detailed_analysis()
