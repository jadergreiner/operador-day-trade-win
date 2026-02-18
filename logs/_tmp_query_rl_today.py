import sqlite3

conn = sqlite3.connect('data/db/trading.db')
cur = conn.cursor()

today = '2026-02-13'

cur.execute("PRAGMA table_info(rl_episodes)")
rl_ep_cols = [r[1] for r in cur.fetchall()]
print('[RL_EP_COLS]', rl_ep_cols)

if 'timestamp' in rl_ep_cols:
    cur.execute('SELECT COUNT(*) FROM rl_episodes WHERE date(timestamp)=?', (today,))
    print('[RL_EP_TODAY]', cur.fetchone()[0])

cur.execute("PRAGMA table_info(rl_rewards)")
rl_rw_cols = [r[1] for r in cur.fetchall()]
print('[RL_RW_COLS]', rl_rw_cols)

if 'created_at' in rl_rw_cols:
    cur.execute('SELECT COUNT(*) FROM rl_rewards WHERE date(created_at)=?', (today,))
    print('[RL_REWARDS_TODAY_CREATED_AT]', cur.fetchone()[0])
elif 'timestamp' in rl_rw_cols:
    cur.execute('SELECT COUNT(*) FROM rl_rewards WHERE date(timestamp)=?', (today,))
    print('[RL_REWARDS_TODAY_TIMESTAMP]', cur.fetchone()[0])

conn.close()
