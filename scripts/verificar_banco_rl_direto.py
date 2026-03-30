#!/usr/bin/env python3
"""
Script para verificar estrutura do banco trading_rl_direto.db
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "trading_rl_direto.db"

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

# Listar tabelas
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tabelas = cursor.fetchall()
print("Tabelas:", tabelas)

# Ver estrutura da tabela trades se existir
if ('trades',) in tabelas:
    cursor.execute('PRAGMA table_info(trades)')
    colunas = cursor.fetchall()
    print("Colunas da tabela trades:")
    for col in colunas:
        print(f"  {col}")

    # Ver algumas linhas de exemplo
    cursor.execute('SELECT * FROM trades LIMIT 5')
    linhas = cursor.fetchall()
    print("Primeiras 5 linhas da tabela trades:")
    for linha in linhas:
        print(f"  {linha}")

conn.close()