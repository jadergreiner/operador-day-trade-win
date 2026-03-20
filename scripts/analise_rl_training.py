#!/usr/bin/env python3
"""
Ativar treinamento RL real no Operador Quantico.

Este script demonstra como transformar os dados coletados em aprendizado.
"""

from pathlib import Path
import sqlite3
import json
from datetime import datetime, timedelta
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.infrastructure.database.db_paths import resolve_operational_db_path

DB_PATH = resolve_operational_db_path(ROOT_DIR, default_name="trading_rl_5000.db")

def analyze_rl_data():
    """Analisar dados RL e sugerir treinamento."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    print("\n" + "="*70)
    print("ANÁLISE DE DADOS RL E RECOMENDACÕES DE TREINAMENTO")
    print("="*70)

    # 1. Quantidade de dados
    cursor.execute("SELECT COUNT(*) FROM rl_episodes")
    episode_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM rl_rewards")
    reward_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT
            COUNT(*) as total_hold,
            SUM(CASE WHEN blocked_reason IS NOT NULL AND TRIM(blocked_reason) <> '' THEN 1 ELSE 0 END) as hold_bloqueado,
            SUM(CASE WHEN blocked_reason IS NULL OR TRIM(blocked_reason) = '' THEN 1 ELSE 0 END) as hold_genuino
        FROM rl_episodes
        WHERE action = 'HOLD'
    """)
    hold_total, hold_blocked, hold_genuine = cursor.fetchone()

    print(f"\n📊 VOLUME DE DADOS RL:")
    print(f"   Episódios: {episode_count:,} (MIN para treino: 100)")
    print(f"   Recompensas: {reward_count:,} (MIN para treino: 500)")
    print(f"   HOLD total: {hold_total:,} | bloqueado: {hold_blocked:,} | genuíno: {hold_genuine:,}")

    readiness = "✅ PRONTO" if episode_count >= 100 and reward_count >= 500 else "⚠️ INSUFICIENTE"
    print(f"   Status: {readiness}")

    # 2. Distribuição de recompensas
    cursor.execute("""
        SELECT
            COUNT(CASE WHEN reward_value > 0 THEN 1 END) as wins,
            COUNT(CASE WHEN reward_value < 0 THEN 1 END) as losses,
            COUNT(CASE WHEN reward_value = 0 THEN 1 END) as neutral
        FROM rl_rewards
    """)
    wins, losses, neutral = cursor.fetchone()
    total = wins + losses + neutral

    print(f"\n📈 DISTRIBUIÇÃO DE RECOMPENSAS:")
    print(f"   Positivas (Win): {wins:,} ({100*wins/total:.1f}%)")
    print(f"   Negativas (Loss): {losses:,} ({100*losses/total:.1f}%)")
    print(f"   Neutras: {neutral:,} ({100*neutral/total:.1f}%)")

    # 3. Últimas recompensas
    cursor.execute("""
        SELECT created_at, reward_value
        FROM rl_rewards
        ORDER BY created_at DESC
        LIMIT 5
    """)

    print(f"\n🔄 ÚLTIMAS 5 RECOMPENSAS:")
    for created_at, reward_value in cursor.fetchall():
        symbol = "✅" if reward_value > 0 else "❌" if reward_value < 0 else "⚪"
        print(f"   {symbol} {created_at}: {reward_value:+.2f}")

    # 4. Recomendações
    print(f"\n💡 RECOMENDAÇÕES PARA ATIVAR TREINAMENTO RL:")

    recommendations = [
        {
            "title": "1. Implementar Training Loop",
            "details": [
                "   └─ Criar script que lê dados de RL_EPISODES",
                "   └─ Treina modelo XGBoost/LightGBM incrementalmente",
                "   └─ Atualiza RL_TRAINING_METRICS a cada ciclo"
            ]
        },
        {
            "title": "2. Definir Estratégia de Recompensa",
            "details": [
                "   └─ reward = P&L (pontos ganhos/perdidos)",
                "   └─ reward = Sharpe Ratio do episódio",
                "   └─ reward = Win Rate target (ex: 60%)"
            ]
        },
        {
            "title": "3. Features para Features Engineered",
            "details": [
                "   └─ Usar dados de RL_INDICATOR_VALUES",
                "   └─ Extrair correlações de RL_CORRELATION_SCORES",
                "   └─ Criar matriz de features para XGBoost"
            ]
        },
        {
            "title": "4. Validação do Modelo",
            "details": [
                "   └─ Cross-validation: 5-fold sobre episódios",
                "   └─ Teste do modelo em dados novos (hold-out)",
                "   └─ Monitorar degradação (retraining a cada N dias)"
            ]
        }
    ]

    for rec in recommendations:
        print(f"\n   {rec['title']}")
        for detail in rec['details']:
            print(detail)

    # 5. Sugestão de comando
    print(f"\n⚡ PRÓXIMO PASSO (ATIVAR TREINAMENTO):")
    print(f"""
   python scripts/rl_training_loop.py \\
       --db data/db/trading.db \\
       --episodes 1370 \\
       --min-reward -100 \\
       --max-reward 500 \\
       --validation-split 0.2 \\
       --retrain-interval 24h
    """)

    conn.close()

    print("\n" + "="*70)
    print("CONCLUSÃO:")
    print("="*70)
    print("""
Os dados de RL existem e estão sendo coletados CORRETAMENTE.

PORÉM: Não há um loop de treinamento transformando esses dados
em aprendizado do modelo.

Para ativar treinamento real você precisa de:
1. ✅ Dados RL (JÁ EXISTE)
2. ❌ Training Loop (PRECISA IMPLEMENTAR)
3. ❌ Model Checkpointing (PRECISA IMPLEMENTAR)
4. ❌ Performance Metrics (PRECISA IMPLEMENTAR)
""")

if __name__ == "__main__":
    analyze_rl_data()
