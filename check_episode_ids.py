#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('data/db/trading.db')
cursor = conn.cursor()

# Ver alguns episodes
cursor.execute("SELECT id, episode_id FROM rl_episodes LIMIT 3")
episodes = cursor.fetchall()
print("=== RL_EPISODES ===")
for ep in episodes:
    print(f"  id={ep[0]}, episode_id={ep[1]}")

print("\n=== RL_REWARDS (amostra) ===")
cursor.execute("SELECT DISTINCT episode_id FROM rl_rewards LIMIT 3")
rewards_eps = cursor.fetchall()
for r in rewards_eps:
    print(f"  episode_id={r[0]}")

# Comparar types
print("\n=== Type Check ===")
cursor.execute("PRAGMA table_info(rl_episodes)")
for col in cursor.fetchall():
    if col[1] == 'episode_id':
        print(f"  RL_EPISODES.episode_id: {col[2]}")

cursor.execute("PRAGMA table_info(rl_rewards)")
for col in cursor.fetchall():
    if col[1] == 'episode_id':
        print(f"  RL_REWARDS.episode_id: {col[2]}")

conn.close()
