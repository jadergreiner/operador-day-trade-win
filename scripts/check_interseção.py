#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('data/db/trading.db')
cursor = conn.cursor()

# Verificar interseção
print("=== Verificação de Interseção ===")

cursor.execute("SELECT COUNT(DISTINCT episode_id) FROM rl_episodes")
episodes_count = cursor.fetchone()[0]
print(f"Episodes únicos em RL_EPISODES: {episodes_count}")

cursor.execute("SELECT COUNT(DISTINCT episode_id) FROM rl_rewards WHERE is_evaluated = 1")
rewards_count = cursor.fetchone()[0]
print(f"Rewards únicos em RL_REWARDS (evaluated): {rewards_count}")

# Rewards que casam com episodes
cursor.execute("""
    SELECT COUNT(DISTINCT r.episode_id)
    FROM rl_rewards r
    INNER JOIN rl_episodes e ON r.episode_id = e.episode_id
    WHERE r.is_evaluated = 1
""")
matches = cursor.fetchone()[0]
print(f"Rewards com episode correspondente: {matches}")

# Se há problema, verificar diferenças
cursor.execute("""
    SELECT DISTINCT r.episode_id
    FROM rl_rewards r
    LEFT JOIN rl_episodes e ON r.episode_id = e.episode_id
    WHERE r.is_evaluated = 1 AND e.episode_id IS NULL
    LIMIT 5
""")
print(f"\nRewards sem episode correspondente (amostra):")
for row in cursor.fetchall():
    print(f"  {row[0]}")

conn.close()
