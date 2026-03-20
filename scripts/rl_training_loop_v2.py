#!/usr/bin/env python3
"""
RL Training Loop v2 - Simples e Funcional.

Transforma dados RL em aprendizado.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
import logging

from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "trading.db"


def main():
    """Executar treinamento simples."""

    logger.info("=" * 80)
    logger.info("RL TRAINING LOOP v2 - INICIANDO")
    logger.info("=" * 80)

    try:
        with sqlite_write_lock(DB_PATH):
            # 1. Conectar ao banco
            logger.info("\n1️⃣ Conectando ao banco...")
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            cursor = conn.cursor()

            # 2. Carregar episódios
            logger.info("\n2️⃣ Carregando episódios...")
            cursor.execute("""
                SELECT COUNT(*) FROM rl_episodes
            """)
            n_episodes = cursor.fetchone()[0]
            logger.info(f"   Total de episódios: {n_episodes}")

            if n_episodes < 10:
                logger.error(f"   ❌ Insuficiente! Mínimo: 10")
                conn.close()
                return False

            # 3. Carregar recompensas
            logger.info("\n3️⃣ Carregando recompensas...")
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN reward_normalized > 0 THEN 1 ELSE 0 END) as wins,
                    AVG(reward_normalized) as avg_reward
                FROM rl_rewards WHERE is_evaluated = 1
            """)
            total, wins, avg_reward = cursor.fetchone()
            logger.info(f"   Total: {total}")
            logger.info(f"   Wins: {wins}")
            logger.info(f"   Avg Reward: {avg_reward:.3f}")

            # 4. Engenharia simples de features
            logger.info("\n4️⃣ Calculando features...")

            # Feature 1: Win rate por episódio
            cursor.execute("""
                SELECT
                    episode_id,
                    COUNT(*) as n_rewards,
                    SUM(CASE WHEN reward_normalized > 0 THEN 1 ELSE 0 END) as wins,
                    AVG(reward_normalized) as avg_reward,
                    MAX(reward_normalized) as max_reward,
                    MIN(reward_normalized) as min_reward
                FROM rl_rewards
                GROUP BY episode_id
            """)

            features = []
            for row in cursor.fetchall():
                episode_id, n_r, wins, avg_r, max_r, min_r = row

                # Pular episódios sem dados
                if avg_r is None or max_r is None or min_r is None:
                    continue

                feature_tuple = {
                    'episode_id': episode_id,
                    'n_rewards': n_r,
                    'win_rate': wins / n_r if n_r > 0 else 0,
                    'avg_reward': avg_r,
                    'reward_range': max_r - min_r,
                    'target': 1 if avg_r > 0 else 0  # Target: episódio foi positivo
                }
                features.append(feature_tuple)

            logger.info(f"   Engenhariadas features para {len(features)} episódios")

            # 5. Estatísticas simples
            positive = sum(1 for f in features if f['target'] == 1)
            negative = len(features) - positive

            logger.info(f"   Episódios positivos: {positive} ({100*positive/len(features):.1f}%)")
            logger.info(f"   Episódios negativos: {negative} ({100*negative/len(features):.1f}%)")

            # 6. Treinar modelo simples (usando numpy/sklearn)
            logger.info("\n5️⃣ Treinando modelo...")

            try:
                import numpy as np
                from sklearn.ensemble import RandomForestClassifier
                from sklearn.model_selection import train_test_split
                from sklearn.metrics import f1_score, roc_auc_score, precision_score, recall_score

                # Preparar dados
                X = np.array([
                    [f['n_rewards'], f['win_rate'], f['avg_reward'], f['reward_range']]
                    for f in features
                ])
                y = np.array([f['target'] for f in features])

                # Split
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42, stratify=y
                )

                logger.info(f"   Train: {len(X_train)}, Test: {len(X_test)}")

                # Treinar
                model = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
                model.fit(X_train, y_train)

                # Avaliar
                y_pred = model.predict(X_test)
                y_pred_proba = model.predict_proba(X_test)[:, 1]

                f1 = f1_score(y_test, y_pred)
                roc_auc = roc_auc_score(y_test, y_pred_proba)
                precision = precision_score(y_test, y_pred)
                recall = recall_score(y_test, y_pred)

                logger.info(f"   F1: {f1:.3f}")
                logger.info(f"   ROC-AUC: {roc_auc:.3f}")
                logger.info(f"   Precision: {precision:.3f}")
                logger.info(f"   Recall: {recall:.3f}")

                # 7. Salvar métricas no banco
                logger.info("\n6️⃣ Salvando métricas...")

                cursor.execute("""
                    INSERT INTO rl_training_metrics
                    (f1_score, roc_auc, precision, recall, train_samples, test_samples,
                     model_type, training_timestamp, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f1, roc_auc, precision, recall,
                    len(X_train), len(X_test),
                    'RandomForest',
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

                conn.commit()
                logger.info(f"   ✅ Métricas salvas!")

            except Exception as e:
                logger.error(f"   ❌ Erro ao treinar: {e}")
                import traceback
                traceback.print_exc()
                conn.close()
                return False

            conn.close()

    except Exception as e:
        logger.error(f"   ❌ Erro inesperado no loop v2: {e}")
        import traceback
        traceback.print_exc()
        return False

    logger.info("\n" + "="*80)
    logger.info("✅ TREINAMENTO CONCLUÍDO COM SUCESSO")
    logger.info("="*80)
    logger.info(f"""
Conhecimento gerado:
  - Modelo: RandomForest
  - F1: {f1:.3f}
  - ROC-AUC: {roc_auc:.3f}
  - Dados: {len(features)} episódios
  - Amostras: {len(X_train)} treino, {len(X_test)} teste

Próximo ciclo em 24h...
    """)

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
