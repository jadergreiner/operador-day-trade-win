#!/usr/bin/env python3
"""Verificar dados persistidos no SQLite."""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "db" / "trading.db"

if not DB_PATH.exists():
    print(f"Banco nao encontrado: {DB_PATH}")
    sys.exit(1)

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

print("\n" + "="*60)
print("ANALISE DO BANCO DE DADOS - trading.db")
print("="*60 + "\n")

# Ver todas as tabelas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print(f"Total de tabelas: {len(tables)}\n")

for table_tuple in tables:
    table_name = table_tuple[0]

    # Contar registros
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]

    # Listar colunas
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    print(f"📊 {table_name.upper()}")
    print(f"   Registros: {count}")
    print(f"   Colunas: {len(columns)}")

    if count > 0:
        # Mostrar amostra de dados
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
        row = cursor.fetchone()
        print(f"   Exemplo: {row[:3]}..." if len(str(row)) > 50 else f"   Exemplo: {row}")

    print()

# Procurar por tabelas RL
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%rl%'")
rl_tables = cursor.fetchall()

if rl_tables:
    print("\n⚡ TABELAS DE RL ENCONTRADAS:")
    for rl_table in rl_tables:
        print(f"   - {rl_table[0]}")
else:
    print("\n❌ NENHUMA TABELA RL ENCONTRADA")

conn.close()

print("\n" + "="*60)
print("CONCLUSAO:")
print("="*60)
print("""
O banco trading.db contem dados persistidos dos ciclos de trading.
Para aprendizado RL real, seria necessario:

1. Tabelas RL (episodes, rewards, transitions)
2. Modelo RL sendo treinado periodicamente
3. Policy updates baseadas nas recompensas
4. Historico de performance do modelo

Verifique se os modulos de RL estao implementados:
  - src/application/services/rl_persistence_service.py
  - src/infrastructure/repositories/rl_repository.py
  - src/infrastructure/database/rl_schema.py
""")
