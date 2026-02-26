#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3
import os
from datetime import datetime, timedelta

print("=" * 70)
print("LIMPEZA DE DADOS ANTIGOS DO BANCO")
print("=" * 70)

db_path = r"data\db\trading.db"
days_to_keep = 7  # Manter apenas dados dos ultimos 7 dias

print(f"\n1. CONECTANDO AO BANCO: {db_path}")
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Descobrir Data limite
    cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
    print(f"   Data limite (manter apos): {cutoff_date}")
    
    # Listar tabelas com coluna de data
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    total_deleted = 0
    
    print(f"\n2. ANALISANDO TABELAS ({len(tables)})")
    
    # Tabelas comuns que tem timestamp/date
    date_columns = {
        'rl_training_metrics': 'timestamp',
        'rl_correlation_scores': 'timestamp',
        'rl_episodes': 'created_at',
        'rl_rewards': 'timestamp',
        'rl_indicator_values': 'timestamp',
        'trading_journal_logs': 'created_at',
        'ai_reflection_logs': 'created_at',
        'system_health_logs': 'timestamp',
        'mt5_deals_raw': 'time',
        'mt5_orders_raw': 'time',
        'simulated_trades': 'entry_time'
    }
    
    print(f"\n3. DELETANDO REGISTROS COM DATA < {cutoff_date}")
    
    for table, date_col in date_columns.items():
        if table in tables:
            try:
                # Contar registros antes
                cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
                count_before = cursor.fetchone()[0]
                
                if count_before > 0:
                    # Tentar deletar com a coluna de data
                    cursor.execute(f"DELETE FROM [{table}] WHERE {date_col} < ?", (cutoff_date,))
                    deleted = cursor.rowcount
                    
                    if deleted > 0:
                        print(f"   {table:35s}: -{deleted:6d} registros ({count_before} -> {count_before-deleted})")
                        total_deleted += deleted
            except Exception as e:
                print(f"   {table:35s}: [ERRO] {str(e)[:30]}")
    
    # VACUUM para recuperar espaço
    print(f"\n4. COMPACTANDO BANCO (VACUUM)...")
    size_before = os.path.getsize(db_path) / (1024*1024)
    conn.commit()
    cursor.close()
    conn.close()
    
    # Reabrir para fazer VACUUM
    conn = sqlite3.connect(db_path)
    conn.execute("VACUUM")
    conn.close()
    
    size_after = os.path.getsize(db_path) / (1024*1024)
    
    print(f"   Tamanho ANTES: {size_before:.2f} MB")
    print(f"   Tamanho DEPOIS: {size_after:.2f} MB")
    print(f"   Espaco recuperado: {size_before - size_after:.2f} MB")
    
    print(f"\n5. RESUMO")
    print(f"   Total registros deletados: {total_deleted:,}")
    print(f"   Banco compactado: {size_after:.2f} MB")
    
except Exception as e:
    print(f"   ERRO: {e}")

print("\n" + "=" * 70)
