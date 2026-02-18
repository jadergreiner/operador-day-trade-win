"""Treinamento do modelo LightGBM para trading WINFUT.

Pipeline completo: extração → feature engineering → target → treino → avaliação.
Suporta walk-forward validation, Optuna hyperparameter tuning e SHAP analysis.

Uso:
    python scripts/ml/train_lgbm_trading.py [--days 60] [--tune] [--mode classification]
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

warnings.filterwarnings("ignore", category=UserWarning)

# ── Imports do projeto ───────────────────────────────────────────────
from scripts.ml.extract_rl_dataset import build_unified_dataset
from src.application.services.ml.feature_engineering_v2 import (
    FeatureConfig,
    FeatureEngineer,
)
from src.application.services.ml.target_engineering import (
    TargetConfig,
    TargetEngineer,
)

# ── Paths ────────────────────────────────────────────────────────────
DB_PATH = ROOT_DIR / "data" / "db" / "trading.db"
MODEL_DIR = ROOT_DIR / "data" / "models" / "lgbm"
REPORT_DIR = ROOT_DIR / "data" / "ml" / "reports"

# ── Configuração do modelo ───────────────────────────────────────────

DEFAULT_LGBM_PARAMS = {
    "boosting_type": "gbdt",
    "num_leaves": 31,
    "max_depth": 5,
    "learning_rate": 0.05,
    "n_estimators": 500,
    "min_child_samples": 20,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "random_state": 42,
    "verbose": -1,
    "n_jobs": -1,
}

# Features que NÃO devem ser usadas como input (IDs, targets, metadata)
EXCLUDE_FEATURES = {
    "episode_id", "timestamp", "session_date", "source",
    "action", "reasoning", "created_at",
    "target_reward_composite", "target_class", "target_class_encoded",
    "target_direction", "target_profitable",
    "cf_reward_buy", "cf_reward_sell", "cf_reward_hold",
    # Rewards são target, não feature
    "reward_cont_5m", "reward_cont_15m", "reward_cont_30m",
    "reward_cont_60m", "reward_cont_120m",
    "reward_norm_5m", "reward_norm_15m", "reward_norm_30m",
    "reward_norm_60m", "reward_norm_120m",
    "was_correct_5m", "was_correct_15m", "was_correct_30m",
    "was_correct_60m", "was_correct_120m",
    "price_chg_pts_5m", "price_chg_pts_15m", "price_chg_pts_30m",
    "price_chg_pts_60m", "price_chg_pts_120m",
    "mfe_5m", "mfe_15m", "mfe_30m", "mfe_60m", "mfe_120m",
    "mae_5m", "mae_15m", "mae_30m", "mae_60m", "mae_120m",
    "vol_5m", "vol_15m", "vol_30m", "vol_60m", "vol_120m",
}

# ── Categóricas para LightGBM ───────────────────────────────────────
CATEGORICAL_FEATURES = [
    "micro_trend", "vwap_position", "smc_direction", "smc_equilibrium",
    "sentiment_intraday", "sentiment_momentum", "sentiment_volatility",
    "market_regime", "market_condition", "session_phase",
    "macro_bias", "fundamental_bias", "sentiment_bias", "technical_bias",
    "urgency", "risk_level", "recommended_approach",
    "setup_type", "setup_quality",
]


def _get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Seleciona colunas de features (exclui targets e metadata)."""
    return [
        c for c in df.columns
        if c not in EXCLUDE_FEATURES
        and not c.startswith("reward_")
        and not c.startswith("was_correct_")
        and not c.startswith("price_chg_pts_")
        and not c.startswith("mfe_")
        and not c.startswith("mae_")
        and not c.startswith("vol_")
        and not c.startswith("target_")
        and not c.startswith("cf_reward_")
    ]


def _prepare_data(
    df: pd.DataFrame,
    feature_cols: list[str],
    target_col: str,
    mode: str,
) -> tuple[pd.DataFrame, pd.Series]:
    """Prepara X e y para treinamento."""
    X = df[feature_cols].copy()
    y = df[target_col].copy()

    # Converter categóricas para LightGBM
    for col in X.columns:
        if X[col].dtype.name == "category" or col in CATEGORICAL_FEATURES:
            X[col] = X[col].astype("category")

    # Object → float (colunas que deveriam ser numéricas mas vieram como object)
    for col in X.columns:
        if X[col].dtype == object and col not in CATEGORICAL_FEATURES:
            X[col] = pd.to_numeric(X[col], errors="coerce")

    # Booleanos → int
    for col in X.columns:
        if X[col].dtype == bool:
            X[col] = X[col].astype(int)

    # Remover linhas com target NaN
    mask = y.notna()
    X = X[mask]
    y = y[mask]

    return X, y


def _walk_forward_split(
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = 5,
    gap: int = 30,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Gera splits walk-forward com gap (purging).

    gap = número de amostras entre treino e validação para evitar leakage.
    """
    n = len(X)
    splits = []

    # Cada fold usa uma porção crescente para treino
    test_size = n // (n_splits + 1)

    for i in range(n_splits):
        train_end = test_size * (i + 2) - gap
        test_start = test_size * (i + 2)
        test_end = min(test_start + test_size, n)

        if train_end <= 0 or test_start >= n:
            continue

        train_idx = np.arange(0, train_end)
        test_idx = np.arange(test_start, test_end)

        if len(train_idx) < 50 or len(test_idx) < 10:
            continue

        splits.append((train_idx, test_idx))

    return splits


def train_classification(
    X: pd.DataFrame,
    y: pd.Series,
    params: dict | None = None,
    n_splits: int = 5,
    gap: int = 30,
) -> dict[str, Any]:
    """Treina modelo de classificação com walk-forward validation."""
    import lightgbm as lgb
    from sklearn.metrics import (
        accuracy_score,
        balanced_accuracy_score,
        classification_report,
        f1_score,
    )

    lgb_params = {**DEFAULT_LGBM_PARAMS}
    lgb_params["objective"] = "multiclass"
    lgb_params["num_class"] = int(y.nunique())
    lgb_params["metric"] = "multi_logloss"
    if params:
        lgb_params.update(params)

    splits = _walk_forward_split(X, y, n_splits=n_splits, gap=gap)
    if not splits:
        print("⚠ Dados insuficientes para walk-forward. Treinando com split simples.")
        split_point = int(len(X) * 0.8)
        splits = [(np.arange(split_point), np.arange(split_point, len(X)))]

    fold_results = []
    best_model = None
    best_score = -1

    for fold_idx, (train_idx, test_idx) in enumerate(splits, 1):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        if y_train.nunique() < 2:
            print(f"  Fold {fold_idx}: ignorado (classes insuficientes no treino)")
            continue

        model = lgb.LGBMClassifier(**lgb_params)

        # Identificar features categóricas
        cat_features = [c for c in X_train.columns if X_train[c].dtype.name == "category"]

        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)],
            categorical_feature=cat_features if cat_features else "auto",
        )

        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        bal_acc = balanced_accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)

        fold_results.append({
            "fold": fold_idx,
            "train_size": len(train_idx),
            "test_size": len(test_idx),
            "accuracy": acc,
            "balanced_accuracy": bal_acc,
            "f1_macro": f1,
        })

        print(f"  Fold {fold_idx}: acc={acc:.3f} bal_acc={bal_acc:.3f} f1={f1:.3f} "
              f"(train={len(train_idx)}, test={len(test_idx)})")

        if f1 > best_score:
            best_score = f1
            best_model = model

    if not fold_results:
        print("⚠ Nenhum fold executado com sucesso!")
        return {}

    # Treinar modelo final com todos os dados
    print("\n  Treinando modelo final com todos os dados...")
    final_model = lgb.LGBMClassifier(**lgb_params)
    cat_features = [c for c in X.columns if X[c].dtype.name == "category"]
    final_model.fit(
        X, y,
        categorical_feature=cat_features if cat_features else "auto",
    )

    # Report do último fold
    if best_model:
        y_pred_final = best_model.predict(X.iloc[splits[-1][1]])
        y_test_final = y.iloc[splits[-1][1]]
        report = classification_report(
            y_test_final, y_pred_final, output_dict=True, zero_division=0
        )
    else:
        report = {}

    # Resumo
    results_df = pd.DataFrame(fold_results)
    avg_metrics = {
        "accuracy_mean": results_df["accuracy"].mean(),
        "accuracy_std": results_df["accuracy"].std(),
        "balanced_accuracy_mean": results_df["balanced_accuracy"].mean(),
        "f1_macro_mean": results_df["f1_macro"].mean(),
        "f1_macro_std": results_df["f1_macro"].std(),
        "n_folds": len(fold_results),
    }

    print(f"\n  Média walk-forward: acc={avg_metrics['accuracy_mean']:.3f}±{avg_metrics['accuracy_std']:.3f}, "
          f"f1={avg_metrics['f1_macro_mean']:.3f}±{avg_metrics['f1_macro_std']:.3f}")

    return {
        "model": final_model,
        "best_fold_model": best_model,
        "fold_results": fold_results,
        "avg_metrics": avg_metrics,
        "classification_report": report,
        "feature_names": list(X.columns),
        "categorical_features": cat_features,
        "params": lgb_params,
    }


def train_regression(
    X: pd.DataFrame,
    y: pd.Series,
    params: dict | None = None,
    n_splits: int = 5,
    gap: int = 30,
) -> dict[str, Any]:
    """Treina modelo de regressão (prediz reward contínuo)."""
    import lightgbm as lgb
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    lgb_params = {**DEFAULT_LGBM_PARAMS}
    lgb_params["objective"] = "regression"
    lgb_params["metric"] = "mae"
    if params:
        lgb_params.update(params)

    splits = _walk_forward_split(X, y, n_splits=n_splits, gap=gap)
    if not splits:
        split_point = int(len(X) * 0.8)
        splits = [(np.arange(split_point), np.arange(split_point, len(X)))]

    fold_results = []
    best_model = None
    best_mae = float("inf")

    for fold_idx, (train_idx, test_idx) in enumerate(splits, 1):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        model = lgb.LGBMRegressor(**lgb_params)
        cat_features = [c for c in X_train.columns if X_train[c].dtype.name == "category"]

        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)],
            categorical_feature=cat_features if cat_features else "auto",
        )

        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred) if len(y_test) > 1 else 0.0

        # Acurácia direcional (se o sinal concorda)
        dir_acc = np.mean(np.sign(y_pred) == np.sign(y_test)) if len(y_test) > 0 else 0.0

        fold_results.append({
            "fold": fold_idx,
            "train_size": len(train_idx),
            "test_size": len(test_idx),
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "directional_accuracy": dir_acc,
        })

        print(f"  Fold {fold_idx}: MAE={mae:.4f} RMSE={rmse:.4f} R²={r2:.4f} "
              f"dir_acc={dir_acc:.3f} (train={len(train_idx)}, test={len(test_idx)})")

        if mae < best_mae:
            best_mae = mae
            best_model = model

    # Modelo final
    print("\n  Treinando modelo final...")
    final_model = lgb.LGBMRegressor(**lgb_params)
    cat_features = [c for c in X.columns if X[c].dtype.name == "category"]
    final_model.fit(X, y, categorical_feature=cat_features if cat_features else "auto")

    results_df = pd.DataFrame(fold_results)
    avg_metrics = {
        "mae_mean": results_df["mae"].mean(),
        "mae_std": results_df["mae"].std(),
        "rmse_mean": results_df["rmse"].mean(),
        "r2_mean": results_df["r2"].mean(),
        "directional_accuracy_mean": results_df["directional_accuracy"].mean(),
        "n_folds": len(fold_results),
    }

    print(f"\n  Média walk-forward: MAE={avg_metrics['mae_mean']:.4f}±{avg_metrics['mae_std']:.4f}, "
          f"dir_acc={avg_metrics['directional_accuracy_mean']:.3f}")

    return {
        "model": final_model,
        "best_fold_model": best_model,
        "fold_results": fold_results,
        "avg_metrics": avg_metrics,
        "feature_names": list(X.columns),
        "categorical_features": cat_features,
        "params": lgb_params,
    }


def analyze_feature_importance(
    model: Any,
    feature_names: list[str],
    top_n: int = 30,
) -> pd.DataFrame:
    """Analisa importância das features via gain e split."""
    imp_gain = model.feature_importances_
    imp_split = model.booster_.feature_importance(importance_type="split")

    imp_df = pd.DataFrame({
        "feature": feature_names[:len(imp_gain)],
        "importance_gain": imp_gain,
        "importance_split": imp_split[:len(imp_gain)] if len(imp_split) >= len(imp_gain) else np.zeros(len(imp_gain)),
    })
    imp_df = imp_df.sort_values("importance_gain", ascending=False)

    print(f"\nTop-{top_n} features por importância (gain):")
    for _, row in imp_df.head(top_n).iterrows():
        bar = "█" * int(row["importance_gain"] / imp_df["importance_gain"].max() * 30)
        print(f"  {row['feature']:50s} gain={row['importance_gain']:8.1f} {bar}")

    return imp_df


def compute_shap_analysis(
    model: Any,
    X: pd.DataFrame,
    max_samples: int = 500,
) -> dict:
    """Calcula SHAP values para interpretabilidade."""
    try:
        import shap
    except ImportError:
        print("⚠ SHAP não instalado. Instale com: pip install shap")
        return {}

    # Subsample para performance
    if len(X) > max_samples:
        X_sample = X.sample(max_samples, random_state=42)
    else:
        X_sample = X

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    # Feature importance média via SHAP
    if isinstance(shap_values, list):
        # Multi-class: média das classes
        mean_shap = np.mean([np.abs(sv).mean(axis=0) for sv in shap_values], axis=0)
    else:
        mean_shap = np.abs(shap_values).mean(axis=0)

    shap_imp = pd.DataFrame({
        "feature": X_sample.columns,
        "shap_importance": mean_shap,
    }).sort_values("shap_importance", ascending=False)

    print(f"\nTop-20 features por SHAP value:")
    for _, row in shap_imp.head(20).iterrows():
        bar = "█" * int(row["shap_importance"] / shap_imp["shap_importance"].max() * 30)
        print(f"  {row['feature']:50s} SHAP={row['shap_importance']:.4f} {bar}")

    return {
        "shap_importance": shap_imp,
        "explainer": explainer,
    }


def save_model_artifacts(
    result: dict,
    mode: str,
    model_dir: Path = MODEL_DIR,
    report_dir: Path = REPORT_DIR,
) -> Path:
    """Salva modelo, metadata e reports."""
    model_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Modelo
    model_path = model_dir / f"lgbm_{mode}_{timestamp}.pkl"
    joblib.dump(result["model"], model_path)

    # Symlink para latest
    latest_path = model_dir / f"lgbm_{mode}_latest.pkl"
    if latest_path.exists():
        latest_path.unlink()
    try:
        latest_path.symlink_to(model_path.name)
    except (OSError, NotImplementedError):
        # Windows pode falhar com symlinks; copiar o modelo
        joblib.dump(result["model"], latest_path)

    # Metadata
    metadata = {
        "timestamp": timestamp,
        "mode": mode,
        "model_path": str(model_path),
        "params": result.get("params", {}),
        "avg_metrics": result.get("avg_metrics", {}),
        "fold_results": result.get("fold_results", []),
        "feature_names": result.get("feature_names", []),
        "categorical_features": result.get("categorical_features", []),
        "n_features": len(result.get("feature_names", [])),
    }

    # Converter numpy types para JSON
    def _convert(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    metadata_path = report_dir / f"training_report_{timestamp}.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, default=_convert)

    # Feature importance
    if "feature_importance" in result:
        imp_path = report_dir / f"feature_importance_{timestamp}.csv"
        result["feature_importance"].to_csv(imp_path, index=False)

    print(f"\n✓ Modelo salvo em: {model_path}")
    print(f"  Latest: {latest_path}")
    print(f"  Report: {metadata_path}")

    return model_path


def run_tuning(
    X: pd.DataFrame,
    y: pd.Series,
    mode: str = "classification",
    n_trials: int = 50,
) -> dict:
    """Hyperparameter tuning com Optuna."""
    try:
        import optuna
    except ImportError:
        print("⚠ Optuna não instalado. Usando parâmetros default.")
        return DEFAULT_LGBM_PARAMS

    import lightgbm as lgb

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial):
        params = {
            "num_leaves": trial.suggest_int("num_leaves", 15, 63),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "n_estimators": trial.suggest_int("n_estimators", 100, 800),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
        }

        splits = _walk_forward_split(X, y, n_splits=3, gap=20)
        if not splits:
            return 0.0

        scores = []
        for train_idx, test_idx in splits:
            X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
            y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]

            cat_features = [c for c in X_tr.columns if X_tr[c].dtype.name == "category"]

            if mode == "classification":
                full_params = {**DEFAULT_LGBM_PARAMS, **params,
                               "objective": "multiclass",
                               "num_class": int(y.nunique()),
                               "metric": "multi_logloss"}
                model = lgb.LGBMClassifier(**full_params)
                model.fit(X_tr, y_tr,
                          eval_set=[(X_te, y_te)],
                          callbacks=[lgb.early_stopping(30, verbose=False),
                                     lgb.log_evaluation(0)],
                          categorical_feature=cat_features if cat_features else "auto")
                from sklearn.metrics import f1_score
                y_pred = model.predict(X_te)
                scores.append(f1_score(y_te, y_pred, average="macro", zero_division=0))
            else:
                full_params = {**DEFAULT_LGBM_PARAMS, **params,
                               "objective": "regression", "metric": "mae"}
                model = lgb.LGBMRegressor(**full_params)
                model.fit(X_tr, y_tr,
                          eval_set=[(X_te, y_te)],
                          callbacks=[lgb.early_stopping(30, verbose=False),
                                     lgb.log_evaluation(0)],
                          categorical_feature=cat_features if cat_features else "auto")
                y_pred = model.predict(X_te)
                scores.append(np.mean(np.sign(y_pred) == np.sign(y_te)))

        return np.mean(scores)

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    print(f"\n  Melhor trial: {study.best_value:.4f}")
    print(f"  Parâmetros: {study.best_params}")

    return {**DEFAULT_LGBM_PARAMS, **study.best_params}


def main():
    parser = argparse.ArgumentParser(description="Treinar modelo LightGBM para trading")
    parser.add_argument("--days", type=int, default=None, help="Últimos N dias de dados")
    parser.add_argument("--horizon", type=int, default=30, help="Horizonte do reward (min)")
    parser.add_argument("--mode", choices=["classification", "regression"], default="classification")
    parser.add_argument("--tune", action="store_true", help="Usar Optuna para tuning")
    parser.add_argument("--tune-trials", type=int, default=50, help="Número de trials Optuna")
    parser.add_argument("--splits", type=int, default=5, help="Número de folds walk-forward")
    parser.add_argument("--gap", type=int, default=30, help="Gap de purging entre folds")
    parser.add_argument("--shap", action="store_true", help="Calcular SHAP analysis")
    parser.add_argument("--db", type=str, default=str(DB_PATH))
    args = parser.parse_args()

    print("=" * 60)
    print(f"ML Training Pipeline — {args.mode.upper()}")
    print(f"Horizonte: {args.horizon}min | Folds: {args.splits} | Gap: {args.gap}")
    print("=" * 60)

    # 1. Extração
    print("\n📊 Etapa 1: Extração do dataset...")
    raw_dataset = build_unified_dataset(
        db_path=Path(args.db),
        days=args.days,
        horizon=args.horizon,
    )

    if raw_dataset.empty or len(raw_dataset) < 50:
        print(f"\n⚠ Dataset muito pequeno ({len(raw_dataset)} amostras). Mínimo: 50.")
        print("  Aguarde mais dias de coleta de dados RL.")
        return

    # 2. Feature Engineering
    print("\n🔧 Etapa 2: Feature Engineering...")
    fe = FeatureEngineer()
    dataset = fe.transform(raw_dataset)
    print(fe.report(dataset))

    # 3. Target Engineering
    print("\n🎯 Etapa 3: Target Engineering...")
    te = TargetEngineer(TargetConfig(primary_horizon=args.horizon))
    dataset = te.build_targets(dataset)

    # 4. Preparar X e y
    print("\n📐 Etapa 4: Preparação de features...")
    feature_cols = _get_feature_columns(dataset)
    print(f"  Features selecionadas: {len(feature_cols)}")

    if args.mode == "classification":
        target_col = "target_class_encoded"
    else:
        target_col = "target_reward_composite"

    X, y = _prepare_data(dataset, feature_cols, target_col, args.mode)
    print(f"  Dataset final: {X.shape[0]} amostras × {X.shape[1]} features")

    if len(X) < 50:
        print(f"\n⚠ Amostras insuficientes após limpeza ({len(X)}). Mínimo: 50.")
        return

    # 5. Tuning (opcional)
    best_params = None
    if args.tune:
        print("\n⚙️ Etapa 5: Hyperparameter Tuning (Optuna)...")
        best_params = run_tuning(X, y, mode=args.mode, n_trials=args.tune_trials)

    # 6. Treinamento
    print(f"\n🚀 Etapa {'6' if args.tune else '5'}: Treinamento walk-forward...")
    if args.mode == "classification":
        result = train_classification(X, y, params=best_params, n_splits=args.splits, gap=args.gap)
    else:
        result = train_regression(X, y, params=best_params, n_splits=args.splits, gap=args.gap)

    if not result:
        print("\n⚠ Treinamento falhou!")
        return

    # 7. Feature importance
    print("\n📊 Feature Importance...")
    imp_df = analyze_feature_importance(result["model"], result["feature_names"])
    result["feature_importance"] = imp_df

    # 8. SHAP (opcional)
    if args.shap:
        print("\n🔍 SHAP Analysis...")
        shap_result = compute_shap_analysis(result["model"], X)
        if shap_result:
            result["shap_importance"] = shap_result.get("shap_importance")

    # 9. Salvar
    print("\n💾 Salvando modelo...")
    model_path = save_model_artifacts(result, mode=args.mode)

    # 10. Resumo
    print("\n" + "=" * 60)
    print("RESUMO DO TREINAMENTO")
    print("=" * 60)
    metrics = result["avg_metrics"]
    if args.mode == "classification":
        print(f"  Acurácia: {metrics.get('accuracy_mean', 0):.3f} ± {metrics.get('accuracy_std', 0):.3f}")
        print(f"  F1-macro: {metrics.get('f1_macro_mean', 0):.3f} ± {metrics.get('f1_macro_std', 0):.3f}")
        print(f"  Bal. Acc: {metrics.get('balanced_accuracy_mean', 0):.3f}")
    else:
        print(f"  MAE:      {metrics.get('mae_mean', 0):.4f} ± {metrics.get('mae_std', 0):.4f}")
        print(f"  R²:       {metrics.get('r2_mean', 0):.4f}")
        print(f"  Dir. Acc: {metrics.get('directional_accuracy_mean', 0):.3f}")
    print(f"  Features: {len(result['feature_names'])}")
    print(f"  Amostras: {len(X)}")
    print(f"  Folds:    {metrics.get('n_folds', 0)}")
    print(f"  Modelo:   {model_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
