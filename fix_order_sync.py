#!/usr/bin/env python3
"""Corrige os registros das ordens 2276191196 e 2276191635 no banco de dados."""

import sqlite3
from datetime import datetime

DATABASE_PATH = "data/db/trading.db"

def fix_order_records():
    """Corrige os registros das ordens fechadas."""

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        print("\n" + "="*100)
        print("🔧 CORRIGINDO REGISTROS DE ORDENS FECHADAS")
        print("="*100 + "\n")

        # Ordem 2 - 2276191196
        print("📝 CORRIGINDO ORDEM #2 (2276191196):")
        print("-" * 100)

        cursor.execute("""
            UPDATE trades
            SET
                status = 'CLOSED',
                exit_price = 194130,
                exit_time = '2026-02-26T18:21:23',
                profit_loss = 28.00,
                return_percentage = 0.01,
                updated_at = ?
            WHERE broker_trade_id = '2276191196'
        """, (datetime.now().isoformat(),))

        rows_updated_2 = cursor.rowcount

        print(f"  ✅ Linhas atualizadas: {rows_updated_2}")
        print(f"  Status: CLOSED")
        print(f"  Preço Saída: R$ 194.130,00")
        print(f"  Hora Saída: 2026-02-26T18:21:23")
        print(f"  P&L: +R$ 28,00")
        print(f"  Retorno: +0,01%")

        # Ordem 3 - 2276191635
        print(f"\n📝 CORRIGINDO ORDEM #3 (2276191635):")
        print("-" * 100)

        cursor.execute("""
            UPDATE trades
            SET
                status = 'CLOSED',
                exit_price = 194130,
                exit_time = '2026-02-26T18:21:24',
                profit_loss = 46.00,
                return_percentage = 0.02,
                updated_at = ?
            WHERE broker_trade_id = '2276191635'
        """, (datetime.now().isoformat(),))

        rows_updated_3 = cursor.rowcount

        print(f"  ✅ Linhas atualizadas: {rows_updated_3}")
        print(f"  Status: CLOSED")
        print(f"  Preço Saída: R$ 194.130,00")
        print(f"  Hora Saída: 2026-02-26T18:21:24")
        print(f"  P&L: +R$ 46,00")
        print(f"  Retorno: +0,02%")

        # Commit das mudanças
        conn.commit()

        print(f"\n\n{'='*100}")
        print("✅ SINCRONIZAÇÃO CONCLUÍDA")
        print(f"{'='*100}\n")

        print(f"Total de Ordens Corrigidas: {rows_updated_2 + rows_updated_3}")
        print(f"Total P&L Recuperado: +R$ {28.00 + 46.00:,.2f}")

        # Verificação
        print(f"\n{'='*100}")
        print("🔍 VERIFICANDO CORREÇÕES")
        print(f"{'='*100}\n")

        cursor.execute("""
            SELECT broker_trade_id, status, profit_loss, exit_price, exit_time
            FROM trades
            WHERE broker_trade_id IN ('2276191196', '2276191635')
            ORDER BY broker_trade_id
        """)

        verified = cursor.fetchall()

        for broker_id, status, pnl, exit_price, exit_time in verified:
            print(f"✅ Ordem {broker_id}:")
            print(f"   Status: {status}")
            print(f"   P&L: R$ {float(pnl):+,.2f}" if pnl else "   P&L: N/A")
            print(f"   Saída: R$ {float(exit_price):,.2f}" if exit_price else "   Saída: N/A")
            print(f"   Hora: {exit_time}")
            print()

        print(f"{'='*100}\n")

        return True

    except Exception as e:
        print(f"❌ Erro ao corrigir registros: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print("\n🔧 Iniciando correção de registros desincronizados...\n")
    fix_order_records()
