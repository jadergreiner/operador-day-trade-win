#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RL Health Monitor - Acompanha saúde e degradação do modelo
"""
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RLHealthMonitor:
    """Monitora saúde do modelo RL"""

    def __init__(self, db_path='data/db/trading.db'):
        self.db_path = db_path

    def get_metrics_history(self, days=7):
        """Retorna histórico de métricas dos últimos N dias"""
        conn = sqlite3.connect(self.db_path)

        query = """
            SELECT
                training_id,
                timestamp,
                model_version,
                buy_accuracy,
                validation_reward,
                win_rate,
                episodes_total,
                created_at
            FROM rl_training_metrics
            WHERE created_at >= datetime('now', '-' || ? || ' days')
            ORDER BY created_at DESC
        """

        try:
            df = pd.read_sql_query(
                query,
                conn,
                params=(days,),
                parse_dates=['created_at']
            )
            conn.close()
            return df
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            return None

    def detect_degradation(self, threshold_drop=0.10):
        """Detecta degradação significativa"""
        history = self.get_metrics_history(days=30)

        if history is None or len(history) < 2:
            return None, "Dados insuficientes"

        # Pegar últimas duas métricas (buy_accuracy = F1 score)
        latest = history.iloc[0]['buy_accuracy']
        previous = history.iloc[1]['buy_accuracy']

        drop = (previous - latest) / previous if previous > 0 else 0

        if drop > threshold_drop:
            return 'DEGRADATION', f"F1 caiu {drop*100:.1f}%"
        elif drop > threshold_drop / 2:
            return 'WARNING', f"F1 caiu {drop*100:.1f}% (monitorar)"
        else:
            return 'HEALTHY', "Modelo estável"

    def get_model_info(self):
        """Retorna info do modelo mais recente"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                training_id,
                model_version,
                algorithm,
                episodes_total,
                episodes_train,
                episodes_validation,
                buy_accuracy as f1,
                created_at
            FROM rl_training_metrics
            ORDER BY created_at DESC
            LIMIT 1
        """)

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'training_id': row[0],
            'model_version': row[1],
            'algorithm': row[2],
            'episodes_total': row[3],
            'episodes_train': row[4],
            'episodes_validation': row[5],
            'f1_score': row[6],
            'trained_at': row[7]
        }

    def print_health_report(self):
        """Imprime relatório de saúde"""
        print("\n" + "=" * 70)
        print("📊 RL MODEL HEALTH REPORT")
        print("=" * 70)

        # Info do modelo
        model_info = self.get_model_info()
        if model_info:
            print(f"\n✅ MODELO ATUAL:")
            print(f"   Version: {model_info['model_version']}")
            print(f"   Algorithm: {model_info['algorithm']}")
            print(f"   F1 Score: {model_info['f1_score']:.3f}")
            print(f"   Episodes: {model_info['episodes_train']} train / {model_info['episodes_validation']} validation = {model_info['episodes_total']} total")
            print(f"   Trained: {model_info['trained_at']}")
        else:
            print("\n❌ NENHUM MODELO ENCONTRADO")
            print("=" * 70)
            return

        # Histórico
        history = self.get_metrics_history(days=7)
        if history is not None and len(history) > 0:
            print(f"\n📈 HISTÓRICO (últimos 7 dias):")
            print(f"   Total de treinos: {len(history)}")
            print(f"   F1 Min: {history['buy_accuracy'].min():.3f}")
            print(f"   F1 Max: {history['buy_accuracy'].max():.3f}")
            print(f"   F1 Média: {history['buy_accuracy'].mean():.3f}")

        # Degradation
        status, msg = self.detect_degradation()
        print(f"\n🔍 STATUS:")
        if status == 'DEGRADATION':
            print(f"   🚨 {msg}")
        elif status == 'WARNING':
            print(f"   ⚠️ {msg}")
        else:
            print(f"   ✅ {msg}")

        print("\n" + "=" * 70 + "\n")

def main():
    monitor = RLHealthMonitor()
    monitor.print_health_report()

if __name__ == '__main__':
    main()
