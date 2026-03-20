#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL Training Scheduler - Executa treinamento automaticamente
Monitora degradação e reajusta modelo ao longo do tempo
"""
import sqlite3
import logging
import json
import uuid
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
import subprocess
import sys

from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock

# Scheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    print("❌ APScheduler não instalado. Execute:")
    print("   pip install apscheduler")
    sys.exit(1)

# ML
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, roc_auc_score, precision_score, recall_score

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/rl_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RLTrainingScheduler:
    """Executa treinamento RL automaticamente e monitora degradação"""

    def __init__(self, db_path='data/db/trading.db'):
        self.db_path = db_path
        self.scheduler = BackgroundScheduler()
        self.last_metrics = None

        # Criar logs dir
        Path('logs').mkdir(exist_ok=True)

        logger.info("=" * 60)
        logger.info("🤖 RL TRAINING SCHEDULER - INICIALIZADO")
        logger.info("=" * 60)

    def train_model(self):
        """Executa um ciclo de treinamento RL"""
        logger.info("\n🔄 INICIANDO NOVO CICLO DE TREINAMENTO...")

        try:
            with sqlite_write_lock(self.db_path):
                conn = sqlite3.connect(self.db_path)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                cursor = conn.cursor()

                # 1. Carregar episódios com rewards
                cursor.execute("""
                    SELECT DISTINCT e.id, e.episode_id
                    FROM rl_episodes e
                    INNER JOIN rl_rewards r ON e.episode_id = r.episode_id
                    WHERE r.is_evaluated = 1
                    ORDER BY e.episode_id DESC
                    LIMIT 2000
                """)
                episodes = cursor.fetchall()

                if len(episodes) < 100:
                    logger.warning(f"⚠️ Dados insuficientes: {len(episodes)} episódios")
                    conn.close()
                    return False

                logger.info(f"   Episódios carregados: {len(episodes)}")

                # 2. Carregar recompensas
                cursor.execute("""
                    SELECT episode_id, reward_normalized, was_correct
                    FROM rl_rewards
                    WHERE is_evaluated = 1
                    ORDER BY evaluated_at DESC
                """)
                all_rewards = cursor.fetchall()

                # Agregar por episódio
                rewards_by_episode = {}
                for episode_id, reward_normalized, was_correct in all_rewards:
                    if episode_id not in rewards_by_episode:
                        rewards_by_episode[episode_id] = []
                    rewards_by_episode[episode_id].append((reward_normalized, was_correct))

                wins = sum(1 for _, _, was_correct in all_rewards if was_correct == 1)
                logger.info(f"   Rewards: {len(all_rewards)} (Win: {wins}, {wins/len(all_rewards)*100:.1f}%)")

                # 3. Calcular features
                features_data = []
                y_data = []

                for episode_id_val, episode_uuid in episodes:
                    if episode_uuid not in rewards_by_episode:
                        continue

                    rewards_list = rewards_by_episode[episode_uuid]
                    if len(rewards_list) == 0:
                        continue

                    # Features
                    n_rewards = len(rewards_list)
                    reward_values = [r[0] for r in rewards_list]
                    is_correct_list = [r[1] for r in rewards_list]

                    win_rate = sum(is_correct_list) / n_rewards if n_rewards > 0 else 0
                    avg_reward = np.mean(reward_values)
                    max_reward = max(reward_values)
                    min_reward = min(reward_values)
                    reward_range = max_reward - min_reward

                    features = [n_rewards, win_rate, avg_reward, reward_range]
                    features_data.append(features)

                    # Label
                    label = 1 if win_rate >= 0.5 else 0
                    y_data.append(label)

                logger.info(f"   Features: {len(features_data)} episódios")

                if len(features_data) < 100:
                    logger.warning("❌ Dados insuficientes após filtragem")
                    conn.close()
                    return False

                # 4. Treinar modelo
                X = np.array(features_data)
                y = np.array(y_data)

                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.2, random_state=42, stratify=y
                )

                model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=8,
                    random_state=42,
                    n_jobs=-1
                )
                model.fit(X_train, y_train)

                # 5. Avaliação
                y_pred = model.predict(X_test)
                y_pred_proba = model.predict_proba(X_test)[:, 1]

                metrics = {
                    'f1': f1_score(y_test, y_pred),
                    'roc_auc': roc_auc_score(y_test, y_pred_proba),
                    'precision': precision_score(y_test, y_pred),
                    'recall': recall_score(y_test, y_pred),
                    'win_rate': sum(y_test == 1) / len(y_test),
                    'train_size': len(X_train),
                    'test_size': len(X_test),
                    'episodes_total': len(X)
                }

                logger.info(f"   F1: {metrics['f1']:.3f}")
                logger.info(f"   ROC-AUC: {metrics['roc_auc']:.3f}")
                logger.info(f"   Win Rate: {metrics['win_rate']:.3f}")

                # 6. Salvar métricas
                training_id = str(uuid.uuid4())
                now = datetime.now()

                feature_importance = {}
                if hasattr(model, 'feature_importances_'):
                    feature_names = ['n_rewards', 'win_rate', 'avg_reward', 'reward_range']
                    for name, imp in zip(feature_names, model.feature_importances_):
                        feature_importance[name] = float(imp)

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
                    'micro_tendencia_auto',
                    '4.0.0',
                    'RandomForest',
                    metrics['episodes_total'],
                    metrics['train_size'],
                    metrics['test_size'],
                    np.mean(reward_values) if 'reward_values' in locals() else 0,
                    metrics['win_rate'],
                    metrics['f1'],
                    json.dumps(feature_importance),
                    metrics['roc_auc'],
                    now,
                ))

                conn.commit()
                logger.info(f"   ✅ Métricas salvas! ID: {training_id}")

                # 7. Verificar degradação
                self._check_degradation(metrics)

                self.last_metrics = metrics
                conn.close()

                return True

        except Exception as e:
            logger.error(f"❌ Erro ao treinar: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _check_degradation(self, metrics):
        """Verifica se modelo degradou vs última métrica"""
        if self.last_metrics is None:
            logger.info("📍 Primeira execução - baseline estabelecido")
            return

        f1_current = metrics['f1']
        f1_last = self.last_metrics['f1']
        f1_drop = ((f1_last - f1_current) / f1_last * 100) if f1_last > 0 else 0

        if f1_drop > 10:  # Degradação > 10%
            logger.warning(f"⚠️ DEGRADAÇÃO DETECTADA: F1 caiu {f1_drop:.1f}%")
            self._alert_degradation(metrics)
        elif f1_drop > 5:
            logger.info(f"📊 Leve redução de {f1_drop:.1f}% - monitorando")
        else:
            logger.info(f"✅ Modelo estável (F1 drop: {f1_drop:.1f}%)")

    def _alert_degradation(self, metrics):
        """Alerta sobre degradação severa"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'alert_type': 'model_degradation',
            'last_f1': self.last_metrics['f1'] if self.last_metrics else None,
            'current_f1': metrics['f1'],
            'recommendation': 'Revisar dados recentes e janela de treinamento'
        }

        # Salvar em arquivo
        with open('logs/degradation_alerts.jsonl', 'a') as f:
            f.write(json.dumps(alert) + '\n')

        logger.warning(f"🚨 {alert['recommendation']}")

    def schedule_training(self,
                         time_of_day='22:00',    # Após fechamento do mercado
                         days_of_week='mon-fri'): # Dias úteis
        """Agenda treinamento diário"""

        try:
            # Trigger diário às 22:00 (final do dia)
            trigger = CronTrigger(
                hour=int(time_of_day.split(':')[0]),
                minute=int(time_of_day.split(':')[1]),
                day_of_week=days_of_week
            )

            self.scheduler.add_job(
                self.train_model,
                trigger=trigger,
                id='rl_daily_training',
                name='RL Daily Training',
                replace_existing=True
            )

            logger.info(f"✅ Treinamento agendado para {time_of_day} ({days_of_week})")

        except Exception as e:
            logger.error(f"❌ Erro ao agendar: {e}")
            return False

        return True

    def schedule_weekly_deep_training(self,
                                     day_of_week=4,      # Sexta-feira
                                     time_of_day='20:00'):
        """Agenda treinamento profundo semanal"""

        try:
            trigger = CronTrigger(
                day_of_week=day_of_week,
                hour=int(time_of_day.split(':')[0]),
                minute=int(time_of_day.split(':')[1])
            )

            self.scheduler.add_job(
                lambda: self._deep_training(),
                trigger=trigger,
                id='rl_weekly_deep',
                name='RL Weekly Deep Training',
                replace_existing=True
            )

            logger.info(f"✅ Deep training agendado para sexta-feira {time_of_day}")

        except Exception as e:
            logger.error(f"❌ Erro ao agendar deep training: {e}")
            return False

        return True

    def _deep_training(self):
        """Treinamento profundo com mais dados históricos"""
        logger.info("\n🔬 INICIANDO DEEP TRAINING SEMANAL...")

        try:
            with sqlite_write_lock(self.db_path):
                conn = sqlite3.connect(self.db_path)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=30000")
                cursor = conn.cursor()

                # Usar 100% dos dados (não limitar)
                cursor.execute("""
                    SELECT DISTINCT e.id, e.episode_id
                    FROM rl_episodes e
                    INNER JOIN rl_rewards r ON e.episode_id = r.episode_id
                    WHERE r.is_evaluated = 1
                    ORDER BY e.episode_id DESC
                """)
                episodes = cursor.fetchall()

                logger.info(f"   Episódios totais: {len(episodes)}")
                logger.info("   🔄 Retrainando com 100% dos dados...")

                # Mesmo processo mas com mais dados
                self._train_with_data(cursor, episodes, is_deep=True)

                conn.close()
                return True

        except Exception as e:
            logger.error(f"❌ Erro em deep training: {e}")
            return False

    def _train_with_data(self, cursor, episodes, is_deep=False):
        """Helper para treinar com dataset específico"""
        cursor.execute("""
            SELECT episode_id, reward_normalized, was_correct
            FROM rl_rewards
            WHERE is_evaluated = 1
        """)
        all_rewards = cursor.fetchall()

        rewards_by_episode = {}
        for episode_id, reward_normalized, was_correct in all_rewards:
            if episode_id not in rewards_by_episode:
                rewards_by_episode[episode_id] = []
            rewards_by_episode[episode_id].append((reward_normalized, was_correct))

        features_data = []
        y_data = []

        for episode_id_val, episode_uuid in episodes:
            if episode_uuid not in rewards_by_episode:
                continue

            rewards_list = rewards_by_episode[episode_uuid]
            if len(rewards_list) == 0:
                continue

            n_rewards = len(rewards_list)
            reward_values = [r[0] for r in rewards_list]
            is_correct_list = [r[1] for r in rewards_list]

            win_rate = sum(is_correct_list) / n_rewards if n_rewards > 0 else 0
            avg_reward = np.mean(reward_values)
            max_reward = max(reward_values)
            min_reward = min(reward_values)
            reward_range = max_reward - min_reward

            features = [n_rewards, win_rate, avg_reward, reward_range]
            features_data.append(features)

            label = 1 if win_rate >= 0.5 else 0
            y_data.append(label)

        X = np.array(features_data)
        y = np.array(y_data)

        # Deep training usa mais estimadores
        n_estimators = 200 if is_deep else 100
        max_depth = 10 if is_deep else 8

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.15, random_state=42, stratify=y
        )

        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]

        metrics = {
            'f1': f1_score(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
        }

        logger.info(f"   F1: {metrics['f1']:.3f}, ROC-AUC: {metrics['roc_auc']:.3f}")

    def start(self):
        """Inicia scheduler em background"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("🚀 SCHEDULER INICIADO")
            logger.info("=" * 60)
            return True
        return False

    def stop(self):
        """Para scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("⛔ SCHEDULER PARADO")
            return True
        return False

    def run_once(self):
        """Executa treinamento uma vez (útil para testes)"""
        logger.info("▶️ EXECUÇÃO ÚNICA")
        return self.train_model()

    def show_jobs(self):
        """Mostra jobs agendados"""
        jobs = self.scheduler.get_jobs()
        logger.info(f"\n📋 JOBS AGENDADOS ({len(jobs)}):")
        for job in jobs:
            logger.info(f"   - {job.name} (id={job.id})")
            logger.info(f"     Trigger: {job.trigger}")
        return jobs

def main():
    # Criar scheduler
    scheduler = RLTrainingScheduler()

    # Agendar treinamentos
    scheduler.schedule_training(time_of_day='22:00', days_of_week='mon-fri')
    scheduler.schedule_weekly_deep_training(day_of_week=4, time_of_day='20:00')

    # Mostrar jobs
    scheduler.show_jobs()

    # Iniciar
    scheduler.start()

    # Manter em background
    try:
        logger.info("\n✅ Sistema rodando em background...")
        logger.info("💡 Pressione CTRL+C para parar")
        logger.info("=" * 60 + "\n")

        while True:
            import time
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n⛔ Encerrando...")
        scheduler.stop()

if __name__ == '__main__':
    main()
