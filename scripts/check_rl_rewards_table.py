#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('data/db/trading.db')
cursor = conn.cursor()

# Verificar estrutura de RL_REWARDS
cursor.execute("PRAGMA table_info(rl_rewards)")
columns = cursor.fetchall()

print("=== Estrutura da Tabela RL_REWARDS ===\n")
for col in columns:
    print(f"  {col[1]:30} {col[2]:15}")

# Ver alguns registros
cursor.execute("SELECT * FROM rl_rewards LIMIT 5")
rows = cursor.fetchall()
print(f"\nPrimeiros 5 registros:")
for row in rows:
    print(f"  {row}")

conn.close()
