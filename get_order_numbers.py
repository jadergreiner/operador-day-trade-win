#!/usr/bin/env python3
"""Extrai o número de ordens das operações abertas no encerramento manual."""

import sqlite3

DATABASE_PATH = "data/db/trading.db"

def get_order_numbers():
    """Obtém o número de ordens das operações."""
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        print("\n" + "="*80)
        print("🔢 NÚMEROS DE ORDENS - OPERAÇÕES ABERTAS NO ENCERRAMENTO 26/02")
        print("="*80 + "\n")
        
        # Operações ABERTAS (OPEN)
        cursor.execute("""
            SELECT id, trade_id, broker_trade_id, symbol, side, quantity, 
                   entry_price, entry_time, status
            FROM trades 
            WHERE status = 'OPEN'
            AND symbol IN ('WINFUT', 'WINJ26')
            ORDER BY entry_time DESC
        """)
        
        open_trades = cursor.fetchall()
        
        print("📍 OPERAÇÕES EM ABERTO:")
        print("-" * 80)
        
        if open_trades:
            for idx, trade in enumerate(open_trades, 1):
                (db_id, trade_id, broker_id, symbol, side, qty, 
                 entry_price, entry_time, status) = trade
                
                print(f"\nOperação #{idx}")
                print(f"  📦 ID Interno (DB):    {db_id}")
                print(f"  🔑 Trade ID:           {trade_id}")
                print(f"  🏦 Broker Order ID:    {broker_id if broker_id else '(Não registrado)'}")
                print(f"  📊 Símbolo:            {symbol}")
                print(f"  📈 Tipo:               {side}")
                print(f"  📋 Quantidade:         {qty}")
                print(f"  💹 Preço Entrada:      R$ {float(entry_price):,.2f}")
                print(f"  ⏰ Hora Entrada:       {entry_time}")
                print(f"  🔴 Status:             {status}")
        else:
            print("  Nenhuma operação aberta encontrada")
        
        # Operações FECHADAS (para comparação)
        cursor.execute("""
            SELECT id, trade_id, broker_trade_id, symbol, side, quantity, 
                   entry_price, exit_price, entry_time, exit_time, status,
                   profit_loss
            FROM trades 
            WHERE status = 'CLOSED'
            AND symbol IN ('WINFUT', 'WINJ26')
            AND date(created_at) >= '2026-02-24'
            ORDER BY exit_time DESC
            LIMIT 5
        """)
        
        closed_trades = cursor.fetchall()
        
        print(f"\n\n✅ OPERAÇÕES FECHADAS (Últimas 5 - Ref):")
        print("-" * 80)
        
        if closed_trades:
            for idx, trade in enumerate(closed_trades, 1):
                (db_id, trade_id, broker_id, symbol, side, qty, 
                 entry_price, exit_price, entry_time, exit_time, status, pnl) = trade
                
                print(f"\nOperação #{idx}")
                print(f"  📦 ID Interno (DB):    {db_id}")
                print(f"  🔑 Trade ID:           {trade_id}")
                print(f"  🏦 Broker Order ID:    {broker_id if broker_id else '(Não registrado)'}")
                print(f"  📊 Símbolo:            {symbol}")
                print(f"  📈 Tipo:               {side}")
                print(f"  📋 Quantidade:         {qty}")
                print(f"  💹 Entrada/Saída:      R$ {float(entry_price):,.2f} → R$ {float(exit_price):,.2f}")
                print(f"  ⏰ Duração:            {entry_time} até {exit_time}")
                print(f"  P&L:                   R$ {float(pnl):+,.2f}" if pnl else "  P&L:                   Não calculado")
        else:
            print("  Nenhuma operação fechada encontrada")
        
        print("\n" + "="*80)
        
        # Resumo importante
        print("\n⚠️ IMPORTANTE:")
        print("-" * 80)
        print("\nOs IDs encontrados:")
        print("  • ID Interno (DB): Identificador único do banco de dados")
        print("  • Trade ID: UUID único de cada transação")
        print("  • Broker Order ID: Número da ordem no broker (pode estar vazio)")
        print("\nPara operações em ABERTO, o Broker Order ID pode não estar")
        print("preenchido se a execução não foi confirmada no broker.")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    get_order_numbers()
