#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SOLUCAO PERMANENTE - CLEANUP AUTOMATICO DE DADOS ANTIGOS
========================================================

Este script deve ser rodado como tarefa agendado (Task Scheduler ou Cron)
a cada 6-12 horas para prevenir acumulo de dados no banco.

Objetivo: Manter apenas dados dos ultimos N dias, limpando dados expirados.
"""

import sqlite3
from datetime import datetime, timedelta
import os

def cleanup_old_data(db_path, days_to_keep=7):
    """
    Remove registros antigos do banco de dados.
    
    Args:
        db_path: Caminho para o banco SQLite
        days_to_keep: Numero de dias de dados a manter (padrao: 7)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
        
        # Definir mapeamento de tabelas e coluna de data
        table_cleanup = {
            'rl_training_metrics': 'timestamp',
            'rl_correlation_scores': 'timestamp',
            'rl_episodes': 'created_at',
            'rl_rewards': 'timestamp',
            'rl_indicator_values': 'timestamp',
            'trading_journal_logs': 'created_at',
            'ai_reflection_logs': 'created_at',
            'system_health_logs': 'timestamp',
        }
        
        total_deleted = 0
        
        for table, date_col in table_cleanup.items():
            try:
                cursor.execute(f"DELETE FROM [{table}] WHERE {date_col} < ?", (cutoff_date,))
                deleted = cursor.rowcount
                total_deleted += deleted
                
                if deleted > 0:
                    print(f"  {table}: -{deleted} registros")
            except Exception as e:
                print(f"  {table}: ERRO - {e}")
        
        # VACUUM para recuperar espaco
        print("\n  Compactando banco com VACUUM...")
        conn.commit()
        cursor.close()
        conn.close()
        
        # Fazer VACUUM
        conn = sqlite3.connect(db_path)
        conn.execute("VACUUM")
        conn.close()
        
        size_mb = os.path.getsize(db_path) / (1024*1024)
        print(f"\n  Limpeza completa!")
        print(f"  Total deletado: {total_deleted:,} registros")
        print(f"  Tamanho banco: {size_mb:.2f} MB")
        
        return True
    except Exception as e:
        print(f"  ERRO: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("LIMPEZA AUTOMATICA DE DADOS ANTIGOS")
    print("=" * 70)
    
    db_path = r"data\db\trading.db"
    
    if os.path.exists(db_path):
        print(f"\n1. LIMPANDO DADOS (mantendo ultimos 7 dias)...")
        if cleanup_old_data(db_path, days_to_keep=7):
            print("\n[OK] Limpeza executada com sucesso!")
        else:
            print("\n[ERRO] Falha na limpeza!")
    else:
        print(f"[ERRO] Banco nao encontrado: {db_path}")
    
    print("=" * 70)
