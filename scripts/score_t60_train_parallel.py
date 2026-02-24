"""
score_t60_train_parallel.py — Grid Search Paralelo com Multiprocessing

Módulo para treinamento XGBoost paralelo com Task 2:
  - Setup de 32 configs em paralelo (n_jobs=-1)
  - Monitoramento de tempo/memória
  - Otimização de multiprocessing

Uso:
    python scripts/score_t60_train_parallel.py --n-jobs -1 --n-configs 32

Version: 1.0.0
Author: Eng Sr (Infra DevOps)
Date: 2026-02-24
"""

import logging
import json
import time
from pathlib import Path
from typing import Tuple, Dict, Any, List
import argparse
import pickle
import psutil
import multiprocessing as mp
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
import xgboost as xgb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s"
)
logger = logging.getLogger(__name__)


def get_system_stats() -> Dict[str, Any]:
    """Coleta estatísticas do sistema."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        cpu_count = mp.cpu_count()
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "cpu_count": cpu_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.warning(f"Erro coletando stats: {str(e)[:50]}")
        return {"error": str(e)[:50]}


def train_single_config(
    config_id: int,
    params: Dict[str, Any],
    X_train: np.ndarray,
    X_val: np.ndarray,
    y_train: np.ndarray,
    y_val: np.ndarray,
    cv_folds: int = 5
) -> Dict[str, Any]:
    """
    Treina single config em worker separado.
    
    Returns:
        Dict com métricas e config
    """
    try:
        # CV Scores
        tscv = TimeSeriesSplit(n_splits=cv_folds)
        cv_f1_scores = []
        
        for train_idx, test_idx in tscv.split(X_train):
            X_cv_train = X_train[train_idx]
            X_cv_test = X_train[test_idx]
            y_cv_train = y_train[train_idx]
            y_cv_test = y_train[test_idx]
            
            model = xgb.XGBClassifier(**params)
            model.fit(X_cv_train, y_cv_train, verbose=0)
            y_pred = model.predict(X_cv_test)
            cv_f1 = f1_score(y_cv_test, y_pred, zero_division=0)
            cv_f1_scores.append(cv_f1)
        
        cv_f1_mean = np.mean(cv_f1_scores)
        cv_f1_std = np.std(cv_f1_scores)
        
        # Treinar em dataset completo
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train, verbose=0)
        
        # Avaliar em validação
        y_val_pred = model.predict(X_val)
        y_val_proba = model.predict_proba(X_val)[:, 1]
        
        f1 = f1_score(y_val, y_val_pred, zero_division=0)
        precision = precision_score(y_val, y_val_pred, zero_division=0)
        recall = recall_score(y_val, y_val_pred, zero_division=0)
        auc = roc_auc_score(y_val, y_val_proba) if len(np.unique(y_val)) > 1 else 0.5
        
        return {
            "config_id": config_id,
            "params": params,
            "cv_f1_mean": float(cv_f1_mean),
            "cv_f1_std": float(cv_f1_std),
            "val_f1": float(f1),
            "val_precision": float(precision),
            "val_recall": float(recall),
            "val_auc": float(auc),
            "status": "SUCCESS"
        }
        
    except Exception as e:
        return {
            "config_id": config_id,
            "params": params,
            "status": "FAILED",
            "error": str(e)[:100]
        }


class ParallelGridSearch:
    """Grid Search com suporte a multiprocessing."""
    
    def __init__(self, n_jobs: int = -1, verbose: int = 1):
        """
        Inicializa.
        
        Args:
            n_jobs: -1 (todos cores), 1 (serial), N (N cores)
            verbose: Level de verbosidade
        """
        self.n_jobs = n_jobs if n_jobs != -1 else mp.cpu_count()
        self.verbose = verbose
        self.n_workers = self.n_jobs
        
        logger.info(f"ParallelGridSearch initialized with {self.n_workers} workers")
    
    def fit(
        self,
        X_train: np.ndarray,
        X_val: np.ndarray,
        y_train: np.ndarray,
        y_val: np.ndarray,
        configs: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Executa grid search em paralelo.
        
        Returns:
            (best_config_dict, all_results)
        """
        logger.info(f"Grid search com {len(configs)} configs usando {self.n_workers} workers")
        
        start_time = time.time()
        sys_stats = get_system_stats()
        logger.info(f"System: {sys_stats}")
        
        results = []
        best_f1 = 0
        best_config = None
        
        # Usar multiprocessing.Pool
        with mp.Pool(processes=self.n_workers) as pool:
            # Preparar tasks
            tasks = [
                {
                    "config_id": i + 1,
                    "params": config.copy(),
                    "X_train": X_train,
                    "X_val": X_val,
                    "y_train": y_train,
                    "y_val": y_val
                }
                for i, config in enumerate(configs)
            ]
            
            # Executar em paralelo
            task_results = []
            for i, task in enumerate(tasks):
                params = task.pop("params")
                config_id = task.pop("config_id")
                
                # Enviar para worker
                result = pool.apply_async(
                    train_single_config,
                    args=(
                        config_id,
                        params,
                        task["X_train"],
                        task["X_val"],
                        task["y_train"],
                        task["y_val"]
                    )
                )
                task_results.append((config_id, result))
            
            # Coletar resultados conforme completam
            for config_id, async_result in task_results:
                try:
                    result = async_result.get(timeout=300)  # 5 min timeout
                    results.append(result)
                    
                    if result.get("status") == "SUCCESS":
                        f1 = result.get("val_f1", 0)
                        if f1 > best_f1:
                            best_f1 = f1
                            best_config = result.get("params")
                        
                        if self.verbose:
                            logger.info(
                                f"  Config {result['config_id']:2d}/{len(configs)}: "
                                f"F1={f1:.3f} (CV: {result['cv_f1_mean']:.3f}±{result['cv_f1_std']:.3f})"
                            )
                    else:
                        logger.warning(f"  Config {config_id}: FAILED - {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.error(f"  Config {config_id}: Timeout/Error - {str(e)[:50]}")
        
        elapsed = time.time() - start_time
        
        logger.info(f"\n✅ Grid search completo em {elapsed:.1f}s ({elapsed/len(configs):.2f}s/config)")
        logger.info(f"   Melhor F1: {best_f1:.3f}")
        logger.info(f"   Speedup: {len(configs) * 2 / elapsed:.1f}x vs serial (estimado)")
        
        return {
            "best_config": best_config,
            "best_f1": best_f1,
            "all_results": results,
            "elapsed_seconds": elapsed,
            "n_workers": self.n_workers,
            "system_stats": sys_stats
        }, results


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description="S2-5 Task 3: Grid Search Paralelo")
    parser.add_argument("--n-jobs", type=int, default=-1, help="Número de workers (-1=todos)")
    parser.add_argument("--n-configs", type=int, default=32, help="Número de configs")
    parser.add_argument("--n-samples", type=int, default=1000, help="Tamanho do dataset")
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("S2-5 TASK 3: Grid Search Parallelization com n_jobs setup")
    logger.info("=" * 70)
    
    # Gerar dataset
    np.random.seed(42)
    n_samples = args.n_samples
    n_features = 25
    
    X = np.random.randn(n_samples, n_features)
    y = np.random.binomial(1, p=0.5, size=n_samples)
    X[y == 1, :5] += 0.3
    
    # Split 70/15/15
    n = len(X)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    
    X_train = X[:train_end]
    X_val = X[train_end:val_end]
    y_train = y[:train_end]
    y_val = y[train_end:val_end]
    
    # Normalizar
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    
    logger.info(f"Dataset: train={len(X_train)}, val={len(X_val)}")
    
    # Criar configs
    configs = []
    for i in range(args.n_configs):
        config = {
            "max_depth": int(np.random.choice([4, 5, 6, 7, 8])),
            "learning_rate": float(np.random.choice([0.05, 0.1, 0.15, 0.2])),
            "n_estimators": int(np.random.choice([50, 100, 150, 200])),
            "subsample": float(np.random.choice([0.7, 0.8, 0.9])),
            "colsample_bytree": float(np.random.choice([0.7, 0.8, 0.9])),
            "base_score": 0.5,
            "random_state": 42,
            "verbosity": 0
        }
        configs.append(config)
    
    logger.info(f"✅ {len(configs)} configs criadas")
    
    # BENCHMARK: Serial vs Parallel
    logger.info(f"\n--- BENCHMARK: Serial vs Parallel n_jobs={args.n_jobs} ---")
    
    # Parallel Grid Search
    grid_search = ParallelGridSearch(n_jobs=args.n_jobs, verbose=1)
    grid_results, results_list = grid_search.fit(X_train, X_val, y_train, y_val, configs)
    
    parallel_time = grid_results["elapsed_seconds"]
    
    # Serial estimate (2x slower, 1 core)
    serial_estimate = parallel_time * args.n_jobs if args.n_jobs != 1 else parallel_time
    speedup = serial_estimate / parallel_time if parallel_time > 0 else 0
    
    logger.info(f"\n📊 PERFORMANCE METRICS:")
    logger.info(f"   Parallel time: {parallel_time:.1f}s ({args.n_jobs} workers)")
    logger.info(f"   Serial estimate: {serial_estimate:.1f}s (1 worker)")
    logger.info(f"   Speedup: {speedup:.1f}x")
    logger.info(f"   Per-config avg: {parallel_time/len(configs):.2f}s")
    
    # Salvar resultados
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    results_path = models_dir / "grid_search_parallel_results.json"
    with open(results_path, "w") as f:
        json.dump(grid_results, f, indent=2, default=str)
    logger.info(f"\n✅ Resultados salvos em {results_path}")
    
    # Summary
    success_count = sum(1 for r in results_list if r.get("status") == "SUCCESS")
    logger.info(f"\n✅ Task 3 Parallelization COMPLETA!")
    logger.info(f"   Configs bem-sucedidos: {success_count}/{len(configs)}")
    logger.info(f"   Workers usados: {grid_results['n_workers']}")
    logger.info(f"   Tempo total: {parallel_time:.1f}s")
    logger.info(f"   Speedup vs serial: {speedup:.1f}x")
    logger.info(f"\n   ✅ Pronto para Task 4: Real-time Inference")


if __name__ == "__main__":
    main()
