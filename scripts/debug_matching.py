#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('data/db/trading.db')
cursor = conn.cursor()

# Simular o que faz o script v3
cursor.execute("""
    SELECT DISTINCT e.id, e.episode_id
    FROM rl_episodes e
    INNER JOIN rl_rewards r ON e.episode_id = r.episode_id
    WHERE r.is_evaluated = 1
    ORDER BY e.episode_id
""")
episodes = cursor.fetchall()
print(f"Episodes loaded: {len(episodes)}")
print(f"First episode: {episodes[0] if episodes else 'NONE'}")

cursor.execute("""
    SELECT episode_id, reward_normalized, was_correct
    FROM rl_rewards
    WHERE is_evaluated = 1
""")
all_rewards = cursor.fetchall()
print(f"\nRewards loaded: {len(all_rewards)}")
print(f"First reward: {all_rewards[0] if all_rewards else 'NONE'}")

# Agrupar
rewards_by_episode = {}
for episode_id, reward_normalized, was_correct in all_rewards:
    if episode_id not in rewards_by_episode:
        rewards_by_episode[episode_id] = []
    rewards_by_episode[episode_id].append((reward_normalized, was_correct))

print(f"\nUnique episodes in rewards_by_episode: {len(rewards_by_episode)}")

# Simular loop
count = 0
for episode_id, _ in episodes[:5]:
    print(f"\nEpisode {episode_id}:")
    if episode_id in rewards_by_episode:
        print(f"  ✓ Found {len(rewards_by_episode[episode_id])} rewards")
        count += 1
    else:
        print(f"  ✗ NOT found")

print(f"\nMatches: {count} out of {min(5, len(episodes))}")

conn.close()
