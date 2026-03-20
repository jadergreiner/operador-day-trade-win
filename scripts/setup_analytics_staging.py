#!/usr/bin/env python
"""Passo 1.2: Database Setup para staging"""

import sqlite3
from pathlib import Path

from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock

db_path = 'data/analytics_staging.db'

# 1. Criar database
Path(db_path).parent.mkdir(parents=True, exist_ok=True)
with sqlite_write_lock(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    cursor = conn.cursor()

    # 2. Criar tabela trader_interventions
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trader_interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        symbol TEXT NOT NULL,
        action TEXT NOT NULL,
        trader_decision TEXT,
        p_and_l REAL,
        result TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 3. Criar índices
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON trader_interventions(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON trader_interventions(symbol)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_action ON trader_interventions(action)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_result ON trader_interventions(result)')

    conn.commit()

    # 4. Validar
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f'✅ Database: {db_path}')
    print(f'✅ Tabela criada: {tables}')

    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indices = cursor.fetchall()
    print(f'✅ Índices criados: {len(indices)} indices')

    conn.close()
    print("✅ PASSO 1.2 OK: Database Setup completo")
