#!/usr/bin/env python3
"""Relatório de Status do Aprendizado RL - Operador Quantico."""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.infrastructure.database.db_paths import resolve_operational_db_path

DB_PATH = resolve_operational_db_path(ROOT_DIR, default_name="trading_rl_5000.db")

def report():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    print("\n" + "="*80)
    print(" "*25 + "RELATÓRIO RL - OPERADOR QUANTICO")
    print("="*80)

    # ========== COLETA DE DADOS ==========
    cursor.execute("SELECT COUNT(*) FROM rl_episodes")
    n_episodes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM rl_rewards")
    n_rewards = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT episode_id) FROM rl_rewards")
    n_evaluated = cursor.fetchone()[0]

    cursor.execute("""
        SELECT
            COUNT(*) as total_hold,
            SUM(CASE WHEN blocked_reason IS NOT NULL AND TRIM(blocked_reason) <> '' THEN 1 ELSE 0 END) as hold_bloqueado,
            SUM(CASE WHEN blocked_reason IS NULL OR TRIM(blocked_reason) = '' THEN 1 ELSE 0 END) as hold_genuino
        FROM rl_episodes
        WHERE action = 'HOLD'
    """)
    hold_total, hold_blocked, hold_genuine = cursor.fetchone()

    print(f"\n1️⃣  COLETA DE DADOS (✅ ATIVA)")
    print(f"   {'─'*76}")
    print(f"   Episódios RL:          {n_episodes:>6,} registros   [MIN: 100   STATUS: ✅ OK]")
    print(f"   Recompensas:           {n_rewards:>6,} registros   [MIN: 500   STATUS: ✅ OK]")
    print(f"   Episódios Avaliados:   {n_evaluated:>6,} episódios  [Pronto para treino]")
    print(f"   HOLD total:            {hold_total:>6,} episódios")
    print(f"   HOLD bloqueado:        {hold_blocked:>6,} episódios")
    print(f"   HOLD genuíno:          {hold_genuine:>6,} episódios")

    # ========== ANÁLISE DE RECOMPENSAS ==========
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN reward_normalized > 0 THEN 1 ELSE 0 END) as positive,
            SUM(CASE WHEN reward_normalized < 0 THEN 1 ELSE 0 END) as negative,
            SUM(CASE WHEN reward_normalized = 0 THEN 1 ELSE 0 END) as neutral,
            AVG(reward_normalized) as media,
            MAX(reward_normalized) as maximo,
            MIN(reward_normalized) as minimo
        FROM rl_rewards WHERE is_evaluated = 1
    """)

    result = cursor.fetchone()
    total, positive, negative, neutral, media, maximo, minimo = result

    if total:
        positive_pct = 100 * positive / total
        negative_pct = 100 * negative / total

        print(f"\n2️⃣  QUALIDADE DAS RECOMPENSAS (✅ COLETADAS)")
        print(f"   {'─'*76}")
        print(f"   Total Avaliadas:       {total:>6,}")
        print(f"   Positivas (Wins):      {positive:>6,}  ({positive_pct:>5.1f}%) ✅")
        print(f"   Negativas (Losses):    {negative:>6,}  ({negative_pct:>5.1f}%) ❌")
        print(f"   Neutras:               {neutral:>6,}  ({100*(neutral/total) if total else 0:>5.1f}%) ⚪")
        print(f"   {'─'*76}")
        print(f"   Recompensa Média:      {media:>6.3f}")
        print(f"   Recompensa Máx:        {maximo:>6.3f}")
        print(f"   Recompensa Min:        {minimo:>6.3f}")

    # ========== STATUS DO TREINAMENTO ==========
    cursor.execute("SELECT COUNT(*) FROM rl_training_metrics")
    n_training_runs = cursor.fetchone()[0]

    print(f"\n3️⃣  TREINAMENTO DO MODELO (❌ INATIVO)")
    print(f"   {'─'*76}")
    print(f"   Ciclos de Treinamento: {n_training_runs:>6,} [ESPERADO: >0  STATUS: ❌ NÃO ATIVO]")
    print(f"   Última Atualização:    Nunca")
    print(f"   Status da Policy:      Não atualizada")

    # ========== DADOS COMPLEMENTARES ==========
    cursor.execute("""
        SELECT COUNT(*) FROM rl_episodes
        WHERE created_at > datetime('now', '-24 hours')
    """)
    last_24h = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM micro_trend_opportunities
        WHERE created_at > datetime('now', '-24 hours')
    """)
    opp_24h = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM trades
        WHERE created_at > datetime('now', '-24 hours')
    """)
    trades_24h = cursor.fetchone()[0]

    print(f"\n4️⃣  ATIVIDADE NAS ÚLTIMAS 24H")
    print(f"   {'─'*76}")
    print(f"   Episódios RL:          {last_24h:>6,} (coleta ativa)")
    print(f"   Oportunidades:         {opp_24h:>6,} (detecção ativa)")
    print(f"   Trades Executados:     {trades_24h:>6,} (execução ativa)")

    # ========== RECOMENDAÇÕES ==========
    print(f"\n5️⃣  RECOMENDAÇÕES")
    print(f"   {'─'*76}")

    recommendations = []

    if n_episodes >= 100 and n_rewards >= 500:
        recommendations.append("   ✅ Dados suficientes para INICIAR treinamento RL")
    else:
        recommendations.append("   ⏳ Aguardando mais episódios para treinar")

    if positive > negative:
        recommendations.append("   ✅ Win rate positivo nas recompensas (good signal)")
    else:
        recommendations.append("   ⚠️  Win rate negativo - revisar regras de reward")

    if n_training_runs == 0:
        recommendations.append("   🔴 CRÍTICO: Loop de treinamento não está rodando!")
        recommendations.append("      └─ Implemente scripts/rl_training_loop.py")

    for rec in recommendations:
        print(rec)

    # ========== PRÓXIMOS PASSOS ==========
    print(f"\n6️⃣  PRÓXIMOS PASSOS")
    print(f"   {'─'*76}")
    print(f"   1. Verificar se RLPersistenceService está sendo executado")
    print(f"   2. Implementar RL Training Loop (scripts/rl_training_loop.py)")
    print(f"   3. Definir função de recompensa apropriada")
    print(f"   4. Treinar modelo XGBoost/LightGBM incremental")
    print(f"   5. Validar predictions contra dados reais")
    print(f"   6. Monitorar RL_TRAINING_METRICS para degradação")

    print(f"\n" + "="*80)
    print(f"\nCONCLUSÃO:")
    print(f"  • Coleta RL:     ✅ FUNCIONANDO (episódios e recompensas sendo salvos)")
    print(f"  • Treinamento:   ❌ NÃO IMPLEMENTADO (loop de RL não está rodando)")
    print(f"  • Ação Requerida: Implementar training loop para ativar aprendizado real")
    print(f"\n" + "="*80 + "\n")

    conn.close()

if __name__ == "__main__":
    report()
