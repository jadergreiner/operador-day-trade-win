#!/usr/bin/env python3
"""Valida as ordens do terminal MT5 contra o banco de dados."""

import sqlite3
from datetime import datetime, timedelta

DATABASE_PATH = "data/db/trading.db"

def validate_orders():
    """Valida as 3 ordens contra o banco de dados."""
    
    # Dados do terminal MT5
    terminal_orders = [
        {
            "date": "2026.02.26",
            "time": "13:17:37",
            "order_id": 2276170194,
            "symbol": "WINJ26",
            "type": "buy",
            "volume": 1,
            "entry_price": 193625,
            "close_time": "13:17:43",
            "close_price": 193615,
            "pnl": -2.00,
            "status": "CLOSED"
        },
        {
            "date": "2026.02.26",
            "time": "17:02:12",
            "order_id": 2276191196,
            "symbol": "WINJ26",
            "type": "sell",
            "volume": 1,
            "entry_price": 194270,
            "sl": 194555,
            "tp": 193245,
            "close_time": "18:21:23",
            "close_price": 194130,
            "pnl": 28.00,
            "status": "CLOSED"
        },
        {
            "date": "2026.02.26",
            "time": "17:08:47",
            "order_id": 2276191635,
            "symbol": "WINJ26",
            "type": "sell",
            "volume": 1,
            "entry_price": 194360,
            "sl": 194645,
            "tp": 193245,
            "close_time": "18:21:24",
            "close_price": 194130,
            "pnl": 46.00,
            "status": "CLOSED"
        }
    ]
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        print("\n" + "="*100)
        print("🔍 VALIDAÇÃO CRUZADA: TERMINAL MT5 vs BANCO DE DADOS")
        print("="*100 + "\n")
        
        all_match = True
        
        for idx, terminal_order in enumerate(terminal_orders, 1):
            print(f"\n{'='*100}")
            print(f"📋 ORDEM #{idx} - BROKER ID: {terminal_order['order_id']}")
            print(f"{'='*100}")
            
            # Busca a ordem no BD
            cursor.execute("""
                SELECT id, trade_id, symbol, side, quantity, entry_price, exit_price,
                       entry_time, exit_time, status, profit_loss, stop_loss, take_profit,
                       broker_trade_id, created_at, updated_at
                FROM trades 
                WHERE broker_trade_id = ?
            """, (str(terminal_order['order_id']),))
            
            db_record = cursor.fetchone()
            
            print(f"\n📍 TERMINAL MT5:")
            print(f"  Data/Hora Abertura:  {terminal_order['date']} {terminal_order['time']}")
            print(f"  Símbolo:             {terminal_order['symbol']}")
            print(f"  Tipo:                {terminal_order['type'].upper()}")
            print(f"  Volume:              {terminal_order['volume']}")
            print(f"  Preço Entrada:       {terminal_order['entry_price']}")
            
            if 'sl' in terminal_order:
                print(f"  Stop Loss:           {terminal_order['sl']}")
            if 'tp' in terminal_order:
                print(f"  Take Profit:         {terminal_order['tp']}")
                
            print(f"  Data/Hora Fechamento:{terminal_order['close_time']}")
            print(f"  Preço Fechamento:    {terminal_order['close_price']}")
            print(f"  P&L:                 {terminal_order['pnl']:+.2f}")
            print(f"  Status:              {terminal_order['status'].upper()} ✅")
            
            if db_record:
                (db_id, trade_id, symbol, side, qty, entry_price, exit_price,
                 entry_time, exit_time, status, pnl, sl, tp, broker_id, created_at, updated_at) = db_record
                
                print(f"\n💾 BANCO DE DADOS:")
                print(f"  ID Interno:          {db_id}")
                print(f"  Trade ID:            {trade_id}")
                print(f"  Símbolo:             {symbol}")
                print(f"  Tipo:                {side}")
                print(f"  Volume:              {qty}")
                print(f"  Preço Entrada:       R$ {float(entry_price):,.2f}")
                
                if exit_price:
                    print(f"  Preço Saída:         R$ {float(exit_price):,.2f}")
                
                print(f"  Hora Entrada:        {entry_time}")
                
                if exit_time:
                    print(f"  Hora Saída:          {exit_time}")
                
                if sl:
                    print(f"  Stop Loss:           R$ {float(sl):,.2f}")
                if tp:
                    print(f"  Take Profit:         R$ {float(tp):,.2f}")
                    
                print(f"  P&L:                 R$ {float(pnl):+,.2f}" if pnl else "  P&L:                 N/A")
                print(f"  Status:              {status}")
                print(f"  Criado:              {created_at}")
                print(f"  Atualizado:          {updated_at}")
                
                # Validação
                print(f"\n✅ VALIDAÇÃO:")
                
                matches = []
                mismatches = []
                
                # Symbol
                if symbol.upper() == terminal_order['symbol'].upper():
                    matches.append(f"✅ Símbolo: {symbol}")
                else:
                    mismatches.append(f"❌ Símbolo: Terminal={terminal_order['symbol']}, DB={symbol}")
                
                # Type
                side_map = {"buy": "BUY", "sell": "SELL"}
                if side == side_map.get(terminal_order['type'].lower()):
                    matches.append(f"✅ Tipo: {side}")
                else:
                    mismatches.append(f"❌ Tipo: Terminal={terminal_order['type']}, DB={side}")
                
                # Volume
                if qty == terminal_order['volume']:
                    matches.append(f"✅ Volume: {qty}")
                else:
                    mismatches.append(f"❌ Volume: Terminal={terminal_order['volume']}, DB={qty}")
                
                # Entry Price (com tolerância para conversão)
                if abs(float(entry_price) - terminal_order['entry_price']) < 1:
                    matches.append(f"✅ Preço Entrada: {float(entry_price):,.2f}")
                else:
                    mismatches.append(f"❌ Preço Entrada: Terminal={terminal_order['entry_price']}, DB={float(entry_price)}")
                
                # Status
                if status == terminal_order['status'].upper():
                    matches.append(f"✅ Status: {status}")
                else:
                    mismatches.append(f"❌ Status: Terminal={terminal_order['status'].upper()}, DB={status}")
                
                # P&L (com tolerância de 1 ponto)
                if pnl and abs(float(pnl) - terminal_order['pnl']) < 1:
                    matches.append(f"✅ P&L: {float(pnl):+,.2f}")
                else:
                    pnl_val = float(pnl) if pnl else None
                    mismatches.append(f"⚠️ P&L: Terminal={terminal_order['pnl']:+.2f}, DB={pnl_val}")
                
                for match in matches:
                    print(f"  {match}")
                
                if mismatches:
                    print(f"\n  ⚠️ DISCREPÂNCIAS:")
                    for mismatch in mismatches:
                        print(f"  {mismatch}")
                    all_match = False
                
            else:
                print(f"\n❌ BANCO DE DADOS: ORDEM NÃO ENCONTRADA!")
                print(f"   ⚠️ O banco de dados não contém registro para broker_trade_id = {terminal_order['order_id']}")
                all_match = False
        
        # Resumo final
        print(f"\n\n{'='*100}")
        print("📊 RESUMO DE VALIDAÇÃO")
        print(f"{'='*100}\n")
        
        print(f"Total de Ordens Validadas: 3")
        print(f"Ordens Encontradas no BD:  {sum(1 for _ in terminal_orders if cursor.execute('SELECT 1 FROM trades WHERE broker_trade_id = ?', (str(_['order_id']),)).fetchone())}")
        
        if all_match:
            print(f"\n✅ TODAS AS ORDENS VALIDADAS COM SUCESSO!")
        else:
            print(f"\n⚠️ EXISTEM DISCREPÂNCIAS - VERIFICAR DETALHES ACIMA")
        
        print(f"\n{'='*100}\n")
        
        return all_match
        
    except Exception as e:
        print(f"❌ Erro na validação: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print("\n🔍 Iniciando validação cruzada das ordens...\n")
    validate_orders()
