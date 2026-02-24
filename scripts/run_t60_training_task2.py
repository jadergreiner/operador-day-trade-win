"""
run_t60_training_task2.py — Execução de Task 2: XGBoost Grid Search

Script que executa o treinamento XGBoost com grid search de 32 configs
para validar pipeline de Tarefa 2 (S2-5).

Uso:
    python scripts/run_t60_training_task2.py

Output:
    - models/score_t60_v1.0_BEST.pkl (melhor modelo)
    - models/grid_search_results.json (resultados grid search)
"""

import json
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, List
import pickle
import time

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


def generate_synthetic_dataset(n_samples: int = 1000) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Gera dataset sintético para teste de stream (demo).

    Em produção, usaríamos dados reais de velas M1.
    """
    logger.info(f"Gerando dataset sintético com {n_samples} amostras...")

    np.random.seed(42)
    n_features = 25

    # Gerar features
    X = np.random.randn(n_samples, n_features)

    # Criar labels parcialmente separáveis
    y = np.random.binomial(1, p=0.5, size=n_samples)

    # Adicionar sinal pequeno
    X[y == 1, :5] += 0.3

    feature_names = [f"feat_{i}" for i in range(n_features)]
    df = pd.DataFrame(X, columns=feature_names)
    df["label_t60"] = y

    logger.info(f"✅ Dataset gerado: shape={df.shape}, labels: {(y==0).sum()} BEAR, {(y==1).sum()} BULL")

    return df, df["label_t60"].values


def create_grid_configs(n_configs: int = 32) -> List[Dict[str, Any]]:
    """Cria grid de hyperparâmetros XGBoost."""
    logger.info(f"Criando {n_configs} configs de grid search...")

    np.random.seed(42)

    max_depths = [4, 5, 6, 7, 8]
    learning_rates = [0.05, 0.1, 0.15, 0.2]
    n_estimators_list = [50, 100, 150, 200]
    subsamples = [0.7, 0.8, 0.9]
    colsamples = [0.7, 0.8, 0.9]

    configs = []
    for i in range(n_configs):
        config = {
            "config_id": i + 1,
            "max_depth": int(np.random.choice(max_depths)),
            "learning_rate": float(np.random.choice(learning_rates)),
            "n_estimators": int(np.random.choice(n_estimators_list)),
            "subsample": float(np.random.choice(subsamples)),
            "colsample_bytree": float(np.random.choice(colsamples)),
            "base_score": 0.5,
            "random_state": 42,
            "verbosity": 0,
            "n_jobs": -1
        }
        configs.append(config)

    logger.info(f"✅ {len(configs)} configs criadas")
    return configs


def train_and_evaluate(
    X_train: np.ndarray,
    X_val: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_val: np.ndarray,
    y_test: np.ndarray,
    configs: List[Dict[str, Any]]
) -> Tuple[Dict[str, Any], xgb.XGBClassifier]:
    """
    Executa grid search com 5-fold CV.

    Returns:
        (best_config, best_model)
    """
    logger.info(f"Iniciando grid search com {len(configs)} configs...")

    results = []
    best_f1 = 0
    best_model = None
    best_config_dict = None
    cv = TimeSeriesSplit(n_splits=5)

    start_time = time.time()

    for i, config in enumerate(configs):
        config_id = config.pop("config_id")

        # Treinar com config
        try:
            # Cross-validation scores
            cv_f1_scores = []
            for train_idx, test_idx in cv.split(X_train):
                X_cv_train = X_train[train_idx]
                X_cv_test = X_train[test_idx]
                y_cv_train = y_train[train_idx]
                y_cv_test = y_train[test_idx]

                model = xgb.XGBClassifier(**config)
                model.fit(X_cv_train, y_cv_train)
                y_pred = model.predict(X_cv_test)
                cv_f1 = f1_score(y_cv_test, y_pred, zero_division=0)
                cv_f1_scores.append(cv_f1)

            cv_f1_mean = np.mean(cv_f1_scores)
            cv_f1_std = np.std(cv_f1_scores)

            # Treinar no set completo de treino
            model = xgb.XGBClassifier(**config)
            model.fit(X_train, y_train)

            # Avaliar em validação
            y_val_pred = model.predict(X_val)
            y_val_proba = model.predict_proba(X_val)[:, 1]

            f1 = f1_score(y_val, y_val_pred, zero_division=0)
            precision = precision_score(y_val, y_val_pred, zero_division=0)
            recall = recall_score(y_val, y_val_pred, zero_division=0)
            auc = roc_auc_score(y_val, y_val_proba) if len(np.unique(y_val)) > 1 else 0.5

            result = {
                "config_id": config_id,
                "params": config,
                "cv_f1_mean": float(cv_f1_mean),
                "cv_f1_std": float(cv_f1_std),
                "val_f1": float(f1),
                "val_precision": float(precision),
                "val_recall": float(recall),
                "val_auc": float(auc),
                "status": "SUCCESS"
            }

            results.append(result)

            # Atualizar melhor modelo
            if f1 > best_f1:
                best_f1 = f1
                best_model = model
                best_config_dict = config.copy()
                best_config_dict["config_id"] = config_id

            logger.info(
                f"  Config {config_id:2d}/{len(configs)}: "
                f"F1={f1:.3f} (CV: {cv_f1_mean:.3f}±{cv_f1_std:.3f})"
            )

        except Exception as e:
            logger.warning(f"  Config {config_id:2d}/{len(configs)}: ERRO - {str(e)[:50]}")
            results.append({
                "config_id": config_id,
                "params": config,
                "status": "FAILED",
                "error": str(e)[:100]
            })

    elapsed = time.time() - start_time
    logger.info(f"\n✅ Grid search completo em {elapsed:.1f}s")
    logger.info(f"   Melhor F1: {best_f1:.3f} (config_id={best_config_dict['config_id']})")

    return {
        "best_config": best_config_dict,
        "best_f1": best_f1,
        "all_results": results,
        "elapsed_seconds": elapsed
    }, best_model


def evaluate_on_test_set(
    model: xgb.XGBClassifier,
    X_test: np.ndarray,
    y_test: np.ndarray
) -> Dict[str, float]:
    """Avalia modelo no test set."""
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    metrics = {
        "test_f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "test_precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "test_recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "test_auc": float(roc_auc_score(y_test, y_proba) if len(np.unique(y_test)) > 1 else 0.5),
    }

    return metrics


def main():
    """Função principal."""
    logger.info("=" * 70)
    logger.info("S2-5 TASK 2: XGBoost Grid Search para Score T+60")
    logger.info("=" * 70)

    # Setup
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    # Gerar dataset
    df, labels = generate_synthetic_dataset(n_samples=1000)

    feature_cols = [col for col in df.columns if col != "label_t60"]
    X = df[feature_cols].values
    y = labels

    # Split treino/val/teste (70/15/15)
    n = len(X)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    X_train = X[:train_end]
    X_val = X[train_end:val_end]
    X_test = X[val_end:]

    y_train = y[:train_end]
    y_val = y[train_end:val_end]
    y_test = y[val_end:]

    logger.info(f"Data split: train={len(X_train)}, val={len(X_val)}, test={len(X_test)}")

    # Normalizar
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    # Grid search configs
    configs = create_grid_configs(n_configs=32)

    # Treinar
    grid_results, best_model = train_and_evaluate(
        X_train_scaled, X_val_scaled, X_test_scaled,
        y_train, y_val, y_test,
        configs
    )

    # Avaliar em test set
    test_metrics = evaluate_on_test_set(best_model, X_test_scaled, y_test)
    grid_results["test_metrics"] = test_metrics

    logger.info(f"\nTest Set Metrics:")
    logger.info(f"  F1:        {test_metrics['test_f1']:.3f}")
    logger.info(f"  Precision: {test_metrics['test_precision']:.3f}")
    logger.info(f"  Recall:    {test_metrics['test_recall']:.3f}")
    logger.info(f"  AUC:       {test_metrics['test_auc']:.3f}")

    # Salvar melhor modelo
    model_path = models_dir / "score_t60_v1.0_BEST.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(best_model, f)
    logger.info(f"\n✅ Modelo salvo em {model_path}")

    # Salvar resultados grid search
    results_path = models_dir / "grid_search_results.json"
    with open(results_path, "w") as f:
        json.dump(grid_results, f, indent=2, default=str)
    logger.info(f"✅ Resultados grid search salvos em {results_path}")

    # Validar gates
    logger.info(f"\n" + "=" * 70)
    logger.info("GATE 1 VALIDATION (05/03):")
    logger.info(f"  F1 >= 0.62?            {test_metrics['test_f1']:.3f} >= 0.62 → {'✅ PASS' if test_metrics['test_f1'] >= 0.62 else '❌ FAIL'}")
    logger.info(f"  Precision >= 0.60?     {test_metrics['test_precision']:.3f} >= 0.60 → {'✅ PASS' if test_metrics['test_precision'] >= 0.60 else '❌ FAIL'}")
    logger.info(f"  Recall >= 0.62?        {test_metrics['test_recall']:.3f} >= 0.62 → {'✅ PASS' if test_metrics['test_recall'] >= 0.62 else '❌ FAIL'}")
    logger.info(f"  AUC >= 0.70?           {test_metrics['test_auc']:.3f} >= 0.70 → {'✅ PASS' if test_metrics['test_auc'] >= 0.70 else '❌ FAIL'}")
    logger.info(f"=" * 70)

    logger.info("\n🚀 Task 2 XGBoost Training COMPLETA!")
    logger.info(f"   Próximo: Task 4 (Real-time Inference)")


if __name__ == "__main__":
    main()
