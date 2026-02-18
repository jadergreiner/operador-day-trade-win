"""Verifica status do banco de dados RL."""
import sqlite3

con = sqlite3.connect("data/db/trading.db")
cur = con.cursor()

# Tabelas RL
tables = [t[0] for t in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'rl_%'"
).fetchall()]
print("=== Tabelas RL ===")
for t in tables:
    print(f"  {t}")

# Contagem de episódios
try:
    cnt = cur.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM rl_episodes").fetchone()
    print(f"\nrl_episodes: {cnt[0]} registros | {cnt[1]} -> {cnt[2]}")
except Exception as e:
    print(f"sem rl_episodes: {e}")

# Contagem de rewards
try:
    cnt = cur.execute("SELECT COUNT(*) FROM rl_rewards").fetchone()
    print(f"rl_rewards: {cnt[0]} registros")
except Exception as e:
    print(f"sem rl_rewards: {e}")

# Micro trend decisions
try:
    cnt = cur.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM micro_trend_decisions").fetchone()
    print(f"\nmicro_trend_decisions: {cnt[0]} registros | {cnt[1]} -> {cnt[2]}")
except Exception as e:
    print(f"sem micro_trend_decisions: {e}")

# Correlation scores
try:
    cnt = cur.execute("SELECT COUNT(*) FROM rl_correlation_scores").fetchone()
    print(f"rl_correlation_scores: {cnt[0]} registros")
except Exception as e:
    print(f"sem rl_correlation_scores: {e}")

# Indicator values
try:
    cnt = cur.execute("SELECT COUNT(*) FROM rl_indicator_values").fetchone()
    print(f"rl_indicator_values: {cnt[0]} registros")
except Exception as e:
    print(f"sem rl_indicator_values: {e}")

# Dataset size
try:
    cnt = cur.execute("SELECT COUNT(DISTINCT session_date), COUNT(*) FROM rl_episodes").fetchone()
    print(f"\nDias unicos: {cnt[0]} | Total episodios: {cnt[1]}")
except:
    pass

# Ações do agente por dia
try:
    rows = cur.execute("""
        SELECT DATE(timestamp), action, COUNT(*)
        FROM rl_episodes
        GROUP BY DATE(timestamp), action
        ORDER BY DATE(timestamp) DESC, action
        LIMIT 20
    """).fetchall()
    print("\n=== Acoes por dia (ultimos) ===")
    for r in rows:
        print(f"  {r[0]} | {r[1]:>6} | {r[2]} episodios")
except Exception as e:
    print(f"Erro: {e}")

con.close()
