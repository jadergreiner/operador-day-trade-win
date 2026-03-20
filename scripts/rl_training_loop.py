#!/usr/bin/env python3
"""
RL Training Loop - Ativar Aprendizado Real do Operador Quantico.

Transforma episódios RL coletados em conhecimento trainando modelos incrementais.

Uso:
    python scripts/rl_training_loop.py
    python scripts/rl_training_loop.py --cycles 10
    python scripts/rl_training_loop.py --retrain-days 1
"""

import logging
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import argparse

from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    f1_score, roc_auc_score, precision_score, recall_score
)

HAS_XGBOOST = False

# Setup
ROOT_DIR = Path(__file__).parent.parent
DB_PATH = ROOT_DIR / "data" / "db" / "trading.db"
LOG_DIR = ROOT_DIR / "logs" / "rl_training"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"rl_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RLTrainingPipeline:
    """Pipeline para treinar modelo RL a partir de episódios coletados."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None
        self.scaler = StandardScaler()
        self.model = None

    def connect(self):
        """Conectar ao banco."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        try:
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA busy_timeout=30000")
        except sqlite3.Error:
            pass
        logger.info(f"Conectado a {self.db_path}")

    def close(self):
        """Desconectar."""
        if self.conn:
            self.conn.close()

    def load_episode_data(self) -> pd.DataFrame:
        """Carregar dados de episódios RL do banco."""
        query = """
        SELECT
            e.episode_id,
            e.created_at,
            COUNT(r.id) as n_rewards,
            AVG(r.reward_normalized) as avg_reward,
            MAX(r.reward_normalized) as max_reward,
            MIN(r.reward_normalized) as min_reward,
            SUM(CASE WHEN r.reward_normalized > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN r.reward_normalized < 0 THEN 1 ELSE 0 END) as losses
        FROM rl_episodes e
        LEFT JOIN rl_rewards r ON e.episode_id = r.episode_id
        GROUP BY e.episode_id
        """

        df = pd.read_sql_query(query, self.conn)
        logger.info(f"Carregados {len(df)} episódios")
        return df

    def load_indicators(self, episode_ids: List[str]) -> pd.DataFrame:
        """Carregar valores de indicadores para episódios."""
        placeholders = ','.join(['?' for _ in episode_ids])
        query = f"""
        SELECT
            episode_id,
            indicator_name,
            indicator_value,
            timestamp_capture
        FROM rl_indicator_values
        WHERE episode_id IN ({placeholders})
        """

        df = pd.read_sql_query(query, self.conn, params=episode_ids)
        logger.info(f"Carregados {len(df)} registros de indicadores")
        return df

    def load_correlations(self, episode_ids: List[str]) -> pd.DataFrame:
        """Carregar scores de correlação."""
        placeholders = ','.join(['?' for _ in episode_ids])
        query = f"""
        SELECT
            episode_id,
            correlation_pair,
            correlation_coefficient,
            significance_score
        FROM rl_correlation_scores
        WHERE episode_id IN ({placeholders})
        """

        df = pd.read_sql_query(query, self.conn, params=episode_ids)
        logger.info(f"Carregados {len(df)} registros de correlação")
        return df

    def engineer_features(self, episodes_df: pd.DataFrame,
                         indicators_df: pd.DataFrame,
                         correlations_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Engenharia de features a partir dos dados RL."""

        features = episodes_df.copy()

        # Feature 1: Momentum de recompensas
        features['reward_momentum'] = features['avg_reward']
        features['win_loss_ratio'] = features['wins'] / (features['losses'] + 1)
        features['volatility_reward'] = features['max_reward'] - features['min_reward']

        # Feature 2: Agregados de indicadores por episódio
        if len(indicators_df) > 0:
            ind_agg = indicators_df.groupby('episode_id').agg({
                'indicator_value': ['mean', 'std', 'min', 'max']
            }).reset_index()
            ind_agg.columns = ['episode_id', 'ind_mean', 'ind_std', 'ind_min', 'ind_max']
            features = features.merge(ind_agg, on='episode_id', how='left')

        # Feature 3: Agregados de correlação
        if len(correlations_df) > 0:
            corr_agg = correlations_df.groupby('episode_id').agg({
                'correlation_coefficient': ['mean', 'std'],
                'significance_score': 'mean'
            }).reset_index()
            corr_agg.columns = ['episode_id', 'corr_mean', 'corr_std', 'sig_mean']
            features = features.merge(corr_agg, on='episode_id', how='left')

        # Preenchimento de NaNs
        features = features.fillna(0)

        # Target: Episódio foi positivo?
        y = (features['avg_reward'] > 0).astype(int)

        logger.info(f"Engineered {features.shape[1]} features para {features.shape[0]} amostras")
        logger.info(f"Distribuição do target: {y.value_counts().to_dict()}")

        return features, y

    def train_model(self, X: pd.DataFrame, y: pd.Series) -> Dict:
        """Treinar modelo de classificação."""

        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        logger.info(f"Train: {X_train.shape[0]}, Test: {X_test.shape[0]}")

        # Selecionar features numéricas
        numeric_cols = X_train.select_dtypes(include=[np.number]).columns.tolist()
        numeric_cols = [c for c in numeric_cols if c != 'episode_id' and not c.startswith('created')]

        X_train_numeric = X_train[numeric_cols]
        X_test_numeric = X_test[numeric_cols]

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train_numeric)
        X_test_scaled = self.scaler.transform(X_test_numeric)

        # Treinar modelo
        logger.info("Treinando modelo...")

        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_train_scaled, y_train)

        # Avaliar
        y_pred = self.model.predict(X_test_scaled)
        y_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]

        metrics = {
            'f1': f1_score(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'train_size': len(X_train),
            'test_size': len(X_test),
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"Métricas: F1={metrics['f1']:.3f}, ROC-AUC={metrics['roc_auc']:.3f}, "
                   f"Precision={metrics['precision']:.3f}, Recall={metrics['recall']:.3f}")

        return metrics

    def save_training_metrics(self, metrics: Dict):
        """Salvar métricas de treinamento no banco."""
        with sqlite_write_lock(self.db_path):
            cursor = self.conn.cursor()

            cursor.execute("""
                INSERT INTO rl_training_metrics
                (f1_score, roc_auc, precision, recall, train_samples,
                 test_samples, model_type, training_timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics['f1'],
                metrics['roc_auc'],
                metrics['precision'],
                metrics['recall'],
                metrics['train_size'],
                metrics['test_size'],
                'RandomForest',
                metrics['timestamp'],
                datetime.now().isoformat()
            ))

            self.conn.commit()
        logger.info("Métricas salvas no RL_TRAINING_METRICS")

    def run(self):
        """Executar pipeline completo."""
        try:
            logger.info("=" * 80)
            logger.info("INICIANDO RL TRAINING LOOP")
            logger.info("=" * 80)

            # 1. Carregar dados
            logger.info("\n1️⃣ Carregando dados de episódios...")
            episodes_df = self.load_episode_data()

            if len(episodes_df) < 10:
                logger.warning(f"Apenas {len(episodes_df)} episódios. Mínimo: 10")
                return False

            # 2. Carregar indicadores
            logger.info("\n2️⃣ Carregando indicadores...")
            episode_ids = episodes_df['episode_id'].tolist()
            indicators_df = self.load_indicators(episode_ids)

            # 3. Carregar correlações
            logger.info("\n3️⃣ Carregando correlações...")
            correlations_df = self.load_correlations(episode_ids)

            # 4. Engenharia de features
            logger.info("\n4️⃣ Engineered features...")
            X, y = self.engineer_features(episodes_df, indicators_df, correlations_df)

            # 5. Treinar modelo
            logger.info("\n5️⃣ Treinando modelo...")
            metrics = self.train_model(X, y)

            # 6. Salvar métricas
            logger.info("\n6️⃣ Salvando métricas...")
            self.save_training_metrics(metrics)

            logger.info("\n" + "=" * 80)
            logger.info("✅ RL TRAINING LOOP CONCLUÍDO COM SUCESSO")
            logger.info("=" * 80 + "\n")

            return True

        except Exception as e:
            logger.error(f"Erro no training loop: {e}", exc_info=True)
            return False


def main():
    parser = argparse.ArgumentParser(description='RL Training Loop para Operador Quantico')
    parser.add_argument('--cycles', type=int, default=1, help='Número de ciclos de treinamento')
    parser.add_argument('--retrain-days', type=int, default=1, help='Dias entre retreinos')
    args = parser.parse_args()

    logger.info(f"Iniciando com cycles={args.cycles}, retrain_days={args.retrain_days}")

    pipeline = RLTrainingPipeline(DB_PATH)
    pipeline.connect()

    success = pipeline.run()

    pipeline.close()

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
