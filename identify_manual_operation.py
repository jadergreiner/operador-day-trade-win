#!/usr/bin/env python3
"""Identifica a operação aberta e seu encerramento manual."""

import sqlite3
from datetime import datetime
import json
from decimal import Decimal

DATABASE_PATH = "data/db/trading.db"

def analyze_manual_closure():
    """Analisa a operação aberta e seu encerramento manual."""
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # 1. Encontra o registro de encerramento manual mais recente
        cursor.execute("""
            SELECT id, trade_id, symbol, side, quantity, entry_price, entry_time, 
                   exit_price, exit_time, status, created_at 
            FROM trades 
            WHERE status = 'MANUAL_CLOSURE'
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        closure_record = cursor.fetchone()
        
        if not closure_record:
            print("❌ Nenhum registro de MANUAL_CLOSURE encontrado")
            return False
        
        closure_id = closure_record[0]
        closure_timestamp = closure_record[10]
        closure_symbol = closure_record[2]
        
        print("\n" + "="*70)
        print("🔍 ANÁLISE DE ENCERRAMENTO MANUAL WIN")
        print("="*70 + "\n")
        
        print("📋 REGISTRO DE ENCERRAMENTO:")
        print(f"  Trade ID: {closure_record[1]}")
        print(f"  Symbol: {closure_record[2]}")
        print(f"  Status: {closure_record[9]}")
        print(f"  Timestamp: {closure_record[10]}\n")
        
        # 2. Encontra operações abertas ANTES do encerramento
        cursor.execute("""
            SELECT id, trade_id, symbol, side, quantity, entry_price, entry_time, 
                   exit_price, exit_time, status, profit_loss, return_percentage, 
                   created_at, updated_at
            FROM trades 
            WHERE (status IN ('OPEN', 'ACTIVE', 'PENDING') 
                   OR (status = 'CLOSED' AND exit_time >= datetime('now', '-24 hours')))
            AND symbol = ?
            AND created_at < ?
            ORDER BY entry_time DESC
            LIMIT 5
        """, (closure_symbol, closure_timestamp))
        
        open_trades = cursor.fetchall()
        
        if open_trades:
            print("="*70)
            print(f"📊 OPERAÇÕES ABERTAS ANTES DO ENCERRAMENTO ({len(open_trades)} encontradas):")
            print("="*70 + "\n")
            
            for idx, trade in enumerate(open_trades, 1):
                (trade_id, tid, symbol, side, qty, entry_price, entry_time, 
                 exit_price, exit_time, status, profit_loss, return_pct, created_at, updated_at) = trade
                
                print(f"\n🎯 OPERAÇÃO #{idx}")
                print(f"  Trade ID: {tid}")
                print(f"  Symbol: {symbol}")
                print(f"  Side (Direção): {side}")
                print(f"  Quantidade: {qty}")
                print(f"  Preço de Entrada: {entry_price}")
                print(f"  Hora de Entrada: {entry_time}")
                
                if exit_price:
                    print(f"  Preço de Saída: {exit_price}")
                if exit_time:
                    print(f"  Hora de Saída: {exit_time}")
                
                print(f"  Status: {status}")
                
                if profit_loss is not None:
                    print(f"  Lucro/Prejuízo: R$ {profit_loss}")
                if return_pct is not None:
                    print(f"  Retorno %: {return_pct:.2f}%")
                    
                print(f"  Criado em: {created_at}")
                if updated_at and updated_at != created_at:
                    print(f"  Atualizado em: {updated_at}")
        else:
            print("⚠️ Nenhuma operação aberta encontrada nos registros recentes\n")
        
        # 3. Busca no journal log para mais contexto
        print("\n" + "="*70)
        print("📝 REGISTROS NO DIÁRIO (TRADING JOURNAL):")
        print("="*70 + "\n")
        
        cursor.execute("""
            SELECT entry_id, timestamp, symbol, headline, decision, confidence, 
                   detailed_narrative
            FROM trading_journal_logs 
            WHERE symbol = ? 
            AND timestamp >= datetime(?, '-2 hours')
            ORDER BY timestamp DESC
            LIMIT 3
        """, (closure_symbol, closure_timestamp))
        
        journal_records = cursor.fetchall()
        
        if journal_records:
            for idx, record in enumerate(journal_records, 1):
                (entry_id, ts, sym, headline, decision, conf, narrative) = record
                
                print(f"\n📖 ENTRADA #{idx}")
                print(f"  Entry ID: {entry_id}")
                print(f"  Timestamp: {ts}")
                print(f"  Headline: {headline}")
                print(f"  Decision: {decision}")
                print(f"  Confidence: {conf:.2%}" if conf else "  Confidence: N/A")
                
                if narrative and len(narrative) > 200:
                    print(f"  Narrativa: {narrative[:200]}...")
                elif narrative:
                    print(f"  Narrativa: {narrative}")
        else:
            print("ℹ️ Nenhum registro no diário encontrado")
        
        # 4. Resumo da operação correlacionada
        print("\n" + "="*70)
        print("🎯 RESUMO DA OPERAÇÃO ENCERRADA")
        print("="*70 + "\n")
        
        if open_trades:
            main_trade = open_trades[0]  # A mais recente
            (trade_id, tid, symbol, side, qty, entry_price, entry_time, 
             exit_price, exit_time, status, profit_loss, return_pct, created_at, updated_at) = main_trade
            
            print(f"✅ Operação Identificada:")
            print(f"  Trade ID: {tid}")
            print(f"  Ativo: {symbol}")
            print(f"  Operação: {side}")
            print(f"  Volume: {qty} contratos")
            print(f"  Entrada: {entry_price} às {entry_time}")
            print(f"  Encerramento Manual: {closure_timestamp}")
            
            time_diff = calculate_duration(entry_time, closure_timestamp)
            print(f"  Duração: {time_diff}")
            
            if profit_loss is not None:
                print(f"  Resultado: R$ {profit_loss:+.2f}")
            if return_pct is not None:
                print(f"  Retorno: {return_pct:+.2f}%")
        
        print("\n" + "="*70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if conn:
            conn.close()


def calculate_duration(entry_time, exit_time):
    """Calcula a duração da operação."""
    try:
        entry = datetime.fromisoformat(entry_time)
        exit_dt = datetime.fromisoformat(exit_time)
        
        duration = exit_dt - entry
        
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        seconds = int(duration.total_seconds() % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except:
        return "N/A"


def list_all_recent_trades():
    """Lista todos os trades recentes para referência."""
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        print("\n" + "="*70)
        print("📊 TODOS OS TRADES RECENTES (últimas 48 horas)")
        print("="*70 + "\n")
        
        cursor.execute("""
            SELECT trade_id, symbol, side, quantity, entry_price, entry_time, 
                   status, profit_loss, created_at
            FROM trades 
            WHERE created_at >= datetime('now', '-48 hours')
            ORDER BY created_at DESC
            LIMIT 20
        """)
        
        trades = cursor.fetchall()
        
        if trades:
            print(f"{'Trade ID':<35} {'Symbol':<8} {'Side':<6} {'Qty':<4} {'Entry Price':<12} {'Status':<15} {'PnL':<12}")
            print("-" * 120)
            
            for trade in trades:
                (tid, symbol, side, qty, entry_price, entry_time, status, pnl, created_at) = trade
                
                pnl_str = f"R${pnl:+.2f}" if pnl is not None else "N/A"
                
                print(f"{tid:<35} {symbol:<8} {side:<6} {qty:<4} {float(entry_price):<12.2f} {status:<15} {pnl_str:<12}")
        else:
            print("Nenhum trade encontrado")
            
        print()
        
    except Exception as e:
        print(f"❌ Erro ao listar trades: {e}")
        
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print("\n🔍 Identificando operação aberta e encerramento manual...\n")
    
    if analyze_manual_closure():
        list_all_recent_trades()
    else:
        print("❌ Falha na análise")
