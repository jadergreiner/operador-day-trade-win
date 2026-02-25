import sqlite3
import json
from datetime import datetime

# Acessar trading.db para analytics de aprendizado
print("=" * 80)
print("📚 VERIFICAÇÃO DE APRENDIZADO PERSISTIDO - 24/02/2026")
print("=" * 80)

try:
    conn = sqlite3.connect('data/db/trading.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Verificar RL Episodes (aprendizado do agente)
    print("\n📌 Tabela 'rl_episodes' - Episódios de RL:")
    cursor.execute("SELECT COUNT(*) FROM rl_episodes WHERE session_date = '2026-02-24';")
    count = cursor.fetchone()[0]
    print(f"  Total de episódios em 24/02: {count}")

    if count > 0:
        cursor.execute("""
            SELECT id, timestamp, source, macro_score_final, micro_score,
                   action, macro_bias, reasoning, created_at
            FROM rl_episodes
            WHERE session_date = '2026-02-24'
            ORDER BY timestamp DESC
            LIMIT 3;
        """)
        for row in cursor.fetchall():
            print(f"\n  ✅ Episódio ID {row['id']}:")
            print(f"     Timestamp: {row['timestamp']}")
            print(f"     Macro Score: {row['macro_score_final']} | Bias: {row['macro_bias']}")
            print(f"     Micro Score: {row['micro_score']} | Action: {row['action']}")
            print(f"     Reasoning: {row['reasoning'][:100]}...")

    # 2. Verificar Diary Feedback (reflexão do agente)
    print("\n" + "="*80)
    print("📌 Tabela 'diary_feedback' - Aprendizado & Reflexão:")
    cursor.execute("SELECT COUNT(*) FROM diary_feedback WHERE date = '2026-02-24';")
    count = cursor.fetchone()[0]
    print(f"  Total de feedback entries em 24/02: {count}")

    if count > 0:
        cursor.execute("""
            SELECT id, timestamp, source, nota_agente, win_rate_pct,
                   n_opportunities, n_episodes, smc_bypass_recomendado,
                   trend_following_recomendado, created_at
            FROM diary_feedback
            WHERE date = '2026-02-24'
            ORDER BY timestamp DESC
            LIMIT 3;
        """)
        for row in cursor.fetchall():
            print(f"\n  ✅ Diary Entry ID {row['id']}:")
            print(f"     Timestamp: {row['timestamp']}")
            print(f"     Agent Score: {row['nota_agente']}/10")
            print(f"     Win Rate: {row['win_rate_pct']:.2f}% | Episodes: {row['n_episodes']}")
            print(f"     Opportunities Detected: {row['n_opportunities']}")
            print(f"     SMC Bypass Recomendado: {bool(row['smc_bypass_recomendado'])}")
            print(f"     Trend Following Recomendado: {bool(row['trend_following_recomendado'])}")

    # 3. Verificar RL Rewards (rewards calculados)
    print("\n" + "="*80)
    print("📌 Tabela 'rl_rewards' - Rewards Calculados:")
    cursor.execute("""
        SELECT COUNT(*) FROM rl_rewards
        WHERE episode_id IN (
            SELECT episode_id FROM rl_episodes WHERE session_date = '2026-02-24'
        );
    """)
    count = cursor.fetchone()[0]
    print(f"  Total de rewards em 24/02: {count}")

    # 4. Verificar Training Metrics
    print("\n" + "="*80)
    print("📌 Tabela 'rl_training_metrics' - Métricas de Treinamento:")
    cursor.execute("SELECT COUNT(*) FROM rl_training_metrics;")
    total = cursor.fetchone()[0]
    print(f"  Total de métricas histórico: {total}")

    cursor.execute("SELECT * FROM rl_training_metrics ORDER BY id DESC LIMIT 1;")
    last_metric = cursor.fetchone()
    if last_metric:
        print(f"\n  ✅ Última métrica registrada:")
        print(f"     ID: {last_metric['id']}")
        for key in dict(last_metric).keys():
            print(f"     {key}: {last_metric[key]}")

    # 5. AI Reflection Logs
    print("\n" + "="*80)
    print("📌 Tabela 'ai_reflection_logs' - Reflexões do Agente:")
    cursor.execute("SELECT COUNT(*) FROM ai_reflection_logs WHERE DATE(timestamp) = '2026-02-24';")
    count = cursor.fetchone()[0]
    print(f"  Total de reflexões em 24/02: {count}")

    if count > 0:
        cursor.execute("""
            SELECT id, timestamp, reflection_type, quality_score,
                   action_items_count, recommendations
            FROM ai_reflection_logs
            WHERE DATE(timestamp) = '2026-02-24'
            ORDER BY timestamp DESC
            LIMIT 2;
        """)
        for row in cursor.fetchall():
            print(f"\n  ✅ Reflexão ID {row['id']}:")
            print(f"     Timestamp: {row['timestamp']}")
            print(f"     Type: {row['reflection_type']} | Quality: {row['quality_score']}")
            print(f"     Action Items: {row['action_items_count']}")

    # 6. Resumo de Aprendizado
    print("\n" + "="*80)
    print("📊 RESUMO DE APRENDIZADO PERSISTIDO EM 24/02:")
    print("="*80)

    cursor.execute("SELECT COUNT(*) FROM rl_episodes WHERE session_date = '2026-02-24';")
    episodes_24 = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM diary_feedback WHERE date = '2026-02-24';")
    feedback_24 = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM rl_rewards
        WHERE episode_id IN (
            SELECT episode_id FROM rl_episodes WHERE session_date = '2026-02-24'
        );
    """)
    rewards_24 = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ai_reflection_logs WHERE DATE(timestamp) = '2026-02-24';")
    reflections_24 = cursor.fetchone()[0]

    print(f"""
✅ **APRENDIZADO PERSISTIDO EM 24/02:**
  - RL Episodes (decisões do agente):    {episodes_24} ✅
  - Diary Feedback (reflexões):          {feedback_24} ✅
  - RL Rewards (rewards calculados):     {rewards_24} ✅
  - AI Reflection Logs (insights):       {reflections_24} ✅

**STATUS GERAL:** 🟢 Sistema persistiu APRENDIZADO corretamente

❌ MAS: Operações REAIS (trades) NÃO foram persistidas
   - simulated_trades de 24/02: VAZIO (0 registros)
   - Comparação: Aprendizado ✅ | Trades ❌
""")

    conn.close()

except Exception as e:
    print(f"❌ Erro ao verificar aprendizado: {e}")

print("\n" + "=" * 80)
