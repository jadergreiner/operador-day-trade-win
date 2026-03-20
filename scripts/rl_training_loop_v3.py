#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL Training Loop v3 - Sincroniza com coluna real da RL_TRAINING_METRICS
"""
import sqlite3
import logging
import json
import uuid
from datetime import datetime
from pathlib import Path
import sys
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, roc_auc_score, precision_score, recall_score

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("\n" + "=" * 55)
    logger.info("RL TRAINING LOOP v3 - COM ESTRUTURA CORRETA")
    logger.info("=" * 55 + "\n")

    try:
        with sqlite_write_lock(ROOT_DIR / 'data' / 'db' / 'trading.db'):
            # 1️⃣ Conectar ao banco
            logger.info("1️⃣ Conectando ao banco...")
            conn = sqlite3.connect(str(ROOT_DIR / 'data' / 'db' / 'trading.db'))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            cursor = conn.cursor()

            # 2️⃣ Carregar episódios (que têm rewards)
            logger.info("2️⃣ Carregando episódios com rewards...")
            cursor.execute("""
                SELECT DISTINCT e.id, e.episode_id
                FROM rl_episodes e
                INNER JOIN rl_rewards r ON e.episode_id = r.episode_id
                WHERE r.is_evaluated = 1
                ORDER BY e.episode_id
            """)
            episodes = cursor.fetchall()
            logger.info(f"   Total de episódios com rewards: {len(episodes)}")

            if len(episodes) == 0:
                logger.error("   ❌ Nenhum episódio encontrado!")
                conn.close()
                return False

            # 3️⃣ Carregar recompensas
            logger.info("3️⃣ Carregando recompensas...")
            cursor.execute("""
                SELECT episode_id, reward_normalized, was_correct
                FROM rl_rewards
                WHERE is_evaluated = 1
            """)
            all_rewards = cursor.fetchall()
            logger.info(f"   Total: {len(all_rewards)}")

            # Contar wins
            wins = sum(1 for _, _, was_correct in all_rewards if was_correct == 1)
            logger.info(f"   Wins: {wins}")
            logger.info(f"   Losses: {len(all_rewards) - wins}")
            logger.info(f"   Win Rate: {wins / len(all_rewards) * 100:.1f}%")

            # Agrupar recompensas por episódio
            rewards_by_episode = {}
            for episode_id, reward_normalized, was_correct in all_rewards:
                if episode_id not in rewards_by_episode:
                    rewards_by_episode[episode_id] = []
                rewards_by_episode[episode_id].append((reward_normalized, was_correct))

            # 4️⃣ Calcular features apenas de episódios com dados
            logger.info("4️⃣ Calculando features...")
            features_data = []
            y_data = []

            for episode_id_val, episode_uuid in episodes:
                if episode_uuid not in rewards_by_episode:
                    continue  # Skip episódios sem rewards

                rewards_list = rewards_by_episode[episode_uuid]

                if len(rewards_list) == 0:
                    continue

                # Extrair features
                n_rewards = len(rewards_list)
                reward_values = [r[0] for r in rewards_list]
                is_correct_list = [r[1] for r in rewards_list]

                win_rate = sum(is_correct_list) / n_rewards if n_rewards > 0 else 0
                avg_reward = np.mean(reward_values) if len(reward_values) > 0 else 0
                max_reward = max(reward_values) if len(reward_values) > 0 else 0
                min_reward = min(reward_values) if len(reward_values) > 0 else 0
                reward_range = max_reward - min_reward if max_reward is not None and min_reward is not None else 0

                features = [n_rewards, win_rate, avg_reward, reward_range]
                features_data.append(features)

                # Label: positivo se +50% dos rewards foram wins
                label = 1 if win_rate >= 0.5 else 0
                y_data.append(label)

            logger.info(f"   Engenhariadas features para {len(features_data)} episódios")
            logger.info(f"   Episódios positivos: {sum(y_data)} ({sum(y_data)/len(y_data)*100:.1f}%)")
            logger.info(f"   Episódios negativos: {len(y_data) - sum(y_data)} ({(len(y_data)-sum(y_data))/len(y_data)*100:.1f}%)")

            if len(features_data) < 10:
                logger.error("   ❌ Dados insuficientes para treinar!")
                conn.close()
                return False

            # 5️⃣ Treinar modelo
            logger.info("5️⃣ Treinando modelo...")
            X = np.array(features_data)
            y = np.array(y_data)

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            model = RandomForestClassifier(
                n_estimators=50,
                max_depth=5,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_train, y_train)

            # Avaliação
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test)[:, 1]

            f1 = f1_score(y_test, y_pred)
            roc_auc = roc_auc_score(y_test, y_pred_proba)
            precision = precision_score(y_test, y_pred)
            recall = recall_score(y_test, y_pred)

            logger.info(f"   Train: {len(X_train)}, Test: {len(X_test)}")
            logger.info(f"   F1: {f1:.3f}")
            logger.info(f"   ROC-AUC: {roc_auc:.3f}")
            logger.info(f"   Precision: {precision:.3f}")
            logger.info(f"   Recall: {recall:.3f}")

            # 6️⃣ Salvar métricas com estrutura correta
            logger.info("6️⃣ Salvando métricas...")

            training_id = str(uuid.uuid4())
            now = datetime.now()

            # Feature importance
            feature_importance = {}
            if hasattr(model, 'feature_importances_'):
                feature_names = ['n_rewards', 'win_rate', 'avg_reward', 'reward_range']
                for name, imp in zip(feature_names, model.feature_importances_):
                    feature_importance[name] = float(imp)

            # Win rate do teste
            test_win_rate = sum(y_test == 1) / len(y_test) if len(y_test) > 0 else 0

            try:
                cursor.execute("""
                    INSERT INTO rl_training_metrics
                    (training_id, timestamp, model_name, model_version, algorithm,
                     episodes_total, episodes_train, episodes_validation,
                     avg_reward, win_rate, buy_accuracy,
                     feature_importance, validation_reward, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    training_id,
                    now,
                    'micro_tendencia_v3',
                    '3.0.0',
                    'RandomForest',
                    len(X),
                    len(X_train),
                    len(X_test),
                    np.mean(reward_values) if 'reward_values' in locals() else 0,
                    test_win_rate,
                    f1,
                    json.dumps(feature_importance),
                    roc_auc,
                    now,
                ))
                conn.commit()
                logger.info(f"   ✅ Métricas salvas com sucesso!")
                logger.info(f"   Training ID: {training_id}\n")

            except Exception as e:
                logger.error(f"   ❌ Erro ao salvar: {e}")
                conn.close()
                return False

            # 📊 Resumo
            logger.info("📊 RESUMO DO TREINAMENTO:")
            logger.info(f"   Episodes: {len(X_train)} (train) + {len(X_test)} (test) = {len(X)} (total)")
            logger.info(f"   F1: {f1:.3f}")
            logger.info(f"   ROC-AUC: {roc_auc:.3f}")
            logger.info(f"   Precision: {precision:.3f}")
            logger.info(f"   Recall: {recall:.3f}")
            logger.info(f"   Win Rate (test): {test_win_rate:.3f}")
            logger.info(f"\n🚀 Modelo treinado e pronto para produção!\n")

            conn.close()
            return True

    except Exception as e:
        logger.error(f"   ❌ Erro inesperado no loop v3: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
