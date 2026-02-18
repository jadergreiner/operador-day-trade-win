"""Analisa episodios RL e rewards do dia 12/02/2026."""
import sqlite3

con = sqlite3.connect("data/db/trading.db")
cur = con.cursor()

print("=== EPISODIOS RL 12/02/2026 ===")
rows = cur.execute("""
    SELECT action, COUNT(*) as cnt,
           ROUND(AVG(macro_score_final),1),
           ROUND(AVG(micro_score),1),
           ROUND(AVG(overall_confidence),3),
           ROUND(MIN(win_price),0),
           ROUND(MAX(win_price),0),
           MIN(timestamp),
           MAX(timestamp)
    FROM rl_episodes
    WHERE DATE(timestamp) = '2026-02-12'
    GROUP BY action
    ORDER BY cnt DESC
""").fetchall()
for r in rows:
    ts_start = r[7][11:16] if r[7] else "?"
    ts_end = r[8][11:16] if r[8] else "?"
    macro = r[2] if r[2] is not None else 0
    micro = r[3] if r[3] is not None else 0
    conf = r[4] if r[4] is not None else 0
    pmin = r[5] if r[5] is not None else 0
    pmax = r[6] if r[6] is not None else 0
    print(f"  {r[0]:>5}: {r[1]:>3}x | macro={macro:>6} micro={micro:>5} conf={conf:.3f} | preco {pmin:.0f}-{pmax:.0f} | {ts_start}-{ts_end}")
total = sum(r[1] for r in rows)
print(f"  TOTAL: {total} episodios")

# Rewards de hoje
print()
print("=== REWARDS AVALIADOS 12/02 ===")
rows = cur.execute("""
    SELECT e.action, r.horizon_minutes,
           COUNT(*) as cnt,
           SUM(CASE WHEN r.was_correct=1 THEN 1 ELSE 0 END) as correct,
           ROUND(AVG(r.reward_continuous),3) as avg_reward,
           ROUND(AVG(r.price_change_points),1) as avg_chg_pts
    FROM rl_rewards r
    JOIN rl_episodes e ON r.episode_id = e.episode_id
    WHERE DATE(e.timestamp) = '2026-02-12'
      AND r.was_correct IS NOT NULL
    GROUP BY e.action, r.horizon_minutes
    ORDER BY e.action, r.horizon_minutes
""").fetchall()
header = f"  {'Acao':>5} | {'Horiz':>5} | {'Cnt':>4} | {'Corretos':>8} | {'WR%':>5} | {'Reward':>7} | {'ChgPts':>7}"
print(header)
print("  " + "-" * (len(header) - 2))
for r in rows:
    wr = (r[3] / r[2] * 100) if r[2] > 0 else 0
    print(f"  {r[0]:>5} | {r[1]:>5} | {r[2]:>4} | {r[3]:>8} | {wr:>5.1f} | {r[4]:>7.3f} | {r[5]:>7.1f}")

# Evolucao temporal: macro score e acao por hora
print()
print("=== EVOLUCAO POR HORA 12/02 ===")
rows = cur.execute("""
    SELECT SUBSTR(timestamp, 12, 2) as hora,
           COUNT(*) as cnt,
           SUM(CASE WHEN action='BUY' THEN 1 ELSE 0 END) as buys,
           SUM(CASE WHEN action='SELL' THEN 1 ELSE 0 END) as sells,
           SUM(CASE WHEN action='HOLD' THEN 1 ELSE 0 END) as holds,
           ROUND(AVG(macro_score_final),1) as avg_macro,
           ROUND(AVG(micro_score),1) as avg_micro,
           ROUND(AVG(overall_confidence),3) as avg_conf,
           ROUND(MIN(win_price),0) as low,
           ROUND(MAX(win_price),0) as high
    FROM rl_episodes
    WHERE DATE(timestamp) = '2026-02-12'
    GROUP BY SUBSTR(timestamp, 12, 2)
    ORDER BY hora
""").fetchall()
print(f"  {'Hora':>4} | {'Cnt':>3} | {'BUY':>3} {'SELL':>4} {'HOLD':>4} | {'Macro':>6} {'Micro':>6} {'Conf':>6} | {'Low':>7} {'High':>7}")
print("  " + "-" * 75)
for r in rows:
    vals = [v if v is not None else 0 for v in r]
    print(f"  {vals[0]:>4} | {vals[1]:>3} | {vals[2]:>3} {vals[3]:>4} {vals[4]:>4} | {vals[5]:>6} {vals[6]:>6} {vals[7]:>6.3f} | {vals[8]:>7.0f} {vals[9]:>7.0f}")

# Bias e sentimento hoje
print()
print("=== BIAS E REGIME DE MERCADO 12/02 ===")
rows = cur.execute("""
    SELECT macro_bias, market_regime, market_condition,
           COUNT(*) as cnt,
           ROUND(AVG(macro_score_final),1) as avg_macro,
           ROUND(AVG(overall_confidence),3) as avg_conf
    FROM rl_episodes
    WHERE DATE(timestamp) = '2026-02-12'
    GROUP BY macro_bias, market_regime, market_condition
    ORDER BY cnt DESC
    LIMIT 10
""").fetchall()
for r in rows:
    conf = r[5] if r[5] is not None else 0
    macro = r[4] if r[4] is not None else 0
    print(f"  bias={r[0]} regime={r[1]} cond={r[2]} | {r[3]}x | macro={macro} conf={conf:.3f}")

# Melhores e piores rewards hoje
print()
print("=== TOP 5 MELHORES REWARDS 12/02 ===")
rows = cur.execute("""
    SELECT e.timestamp, e.action, e.win_price,
           r.horizon_minutes, r.price_change_points, r.reward_continuous, r.was_correct,
           e.macro_score_final, e.micro_score
    FROM rl_rewards r
    JOIN rl_episodes e ON r.episode_id = e.episode_id
    WHERE DATE(e.timestamp) = '2026-02-12'
      AND r.was_correct IS NOT NULL
    ORDER BY r.reward_continuous DESC
    LIMIT 5
""").fetchall()
for r in rows:
    ts = r[0][11:16] if r[0] else "?"
    correct = "V" if r[6] else "X"
    print(f"  {ts} {r[1]:>4} @ {r[2]:.0f} | {r[3]}min | chg={r[4]:+.0f}pts | reward={r[5]:+.3f} [{correct}] | macro={r[7]} micro={r[8]}")

print()
print("=== TOP 5 PIORES REWARDS 12/02 ===")
rows = cur.execute("""
    SELECT e.timestamp, e.action, e.win_price,
           r.horizon_minutes, r.price_change_points, r.reward_continuous, r.was_correct,
           e.macro_score_final, e.micro_score
    FROM rl_rewards r
    JOIN rl_episodes e ON r.episode_id = e.episode_id
    WHERE DATE(e.timestamp) = '2026-02-12'
      AND r.was_correct IS NOT NULL
    ORDER BY r.reward_continuous ASC
    LIMIT 5
""").fetchall()
for r in rows:
    ts = r[0][11:16] if r[0] else "?"
    correct = "V" if r[6] else "X"
    print(f"  {ts} {r[1]:>4} @ {r[2]:.0f} | {r[3]}min | chg={r[4]:+.0f}pts | reward={r[5]:+.3f} [{correct}] | macro={r[7]} micro={r[8]}")

# SMC info
print()
print("=== SMC DIRECTION HOJE ===")
rows = cur.execute("""
    SELECT smc_direction, smc_equilibrium, COUNT(*),
           ROUND(AVG(macro_score_final),1),
           SUM(CASE WHEN action='BUY' THEN 1 ELSE 0 END),
           SUM(CASE WHEN action='SELL' THEN 1 ELSE 0 END)
    FROM rl_episodes
    WHERE DATE(timestamp) = '2026-02-12'
    GROUP BY smc_direction, smc_equilibrium
    ORDER BY COUNT(*) DESC
""").fetchall()
for r in rows:
    print(f"  SMC {r[0]} | {r[1]} | {r[2]}x | macro_avg={r[3]} | BUY:{r[4]} SELL:{r[5]}")

con.close()
