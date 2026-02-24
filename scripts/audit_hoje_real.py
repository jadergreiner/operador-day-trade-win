import sqlite3
import os
from datetime import datetime

def audit_rl_today():
    db_path = os.path.join("data", "db", "trading.db")
    if not os.path.exists(db_path):
        print(f"Banco não encontrado em: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"--- AUDITORIA DE REINFORCEMENT LEARNING (RL) - {datetime.now().strftime('%Y-%m-%d')} ---")

    # 1. Verificar registros em RL_EPISODES hoje
    try:
        cursor.execute("SELECT count(*) FROM rl_episodes WHERE timestamp LIKE '2026-02-23%'")
        episodes_today = cursor.fetchone()[0]
        print(f"Novos Episódios RL hoje: {episodes_today}")
    except Exception as e:
        print(f"Erro em rl_episodes: {e}")

    # 2. Verificar registros em RL_REWARDS hoje
    try:
        cursor.execute("SELECT count(*) FROM rl_rewards WHERE timestamp LIKE '2026-02-23%'")
        rewards_today = cursor.fetchone()[0]
        print(f"Novas Recompensas RL hoje: {rewards_today}")
    except Exception as e:
        print(f"Erro em rl_rewards: {e}")

    # 3. Verificar RL_TRAINING_METRICS hoje
    try:
        cursor.execute("SELECT * FROM rl_training_metrics WHERE timestamp LIKE '2026-02-23%'")
        metrics = cursor.fetchall()
        print(f"Métricas de Treinamento RL hoje: {len(metrics)}")
        for m in metrics:
            print(f"Métrica: {m}")
    except Exception as e:
        print(f"Erro em rl_training_metrics: {e}")

    # 4. Total acumulado para contexto do Board
    print("\nStatus Acumulado (Total Histórico):")
    for table in ["rl_episodes", "rl_rewards", "rl_training_metrics"]:
        cursor.execute(f"SELECT count(*) FROM {table}")
        print(f"- {table}: {cursor.fetchone()[0]} registros")

    conn.close()

if __name__ == "__main__":
    audit_rl_today()
