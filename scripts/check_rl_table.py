#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('data/db/trading.db')
cursor = conn.cursor()

# Verificar estrutura da tabela
cursor.execute("PRAGMA table_info(rl_training_metrics)")
columns = cursor.fetchall()

print("=== Estrutura da Tabela RL_TRAINING_METRICS ===\n")
for col in columns:
    print(f"  {col[1]:30} {col[2]:15}")

# Verificar quantos registros existem
cursor.execute("SELECT COUNT(*) FROM rl_training_metrics")
count = cursor.fetchone()[0]
print(f"\nTotal de registros: {count}")

# Ver alguns registros
if count > 0:
    cursor.execute("SELECT * FROM rl_training_metrics LIMIT 3")
    print("\nPrimeiros registros:")
    for row in cursor.fetchall():
        print(f"  {row}")

conn.close()
