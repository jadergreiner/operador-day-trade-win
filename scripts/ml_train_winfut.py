"""Train a WINFUT day-trade model using available logs."""

from __future__ import annotations

import sys
from pathlib import Path as _Path

ROOT_DIR = _Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import argparse
from pathlib import Path
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.base import clone
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from src.application.services.ml.winfut_dataset import build_dataset


def _split_columns(df: pd.DataFrame) -> Tuple[list[str], list[str]]:
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = [c for c in df.columns if c not in numeric_cols]
    return numeric_cols, cat_cols


def _make_model() -> XGBClassifier:
    return XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        tree_method="hist",
        random_state=42,
    )


def _build_pipeline(numeric_cols: list[str], cat_cols: list[str]) -> Pipeline:
    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    cat_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, numeric_cols),
            ("cat", cat_pipe, cat_cols),
        ]
    )

    model = _make_model()

    return Pipeline(steps=[("preprocessor", preprocessor), ("model", model)])


def _evaluate_walk_forward(
    X: pd.DataFrame,
    y: pd.Series,
    pipeline: Pipeline,
    n_splits: int,
) -> None:
    tscv = TimeSeriesSplit(n_splits=n_splits)

    scores = []
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X), start=1):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        if pd.Series(y_train).nunique() < 2:
            print(f"Fold {fold}: ignorado (apenas 1 classe no treino)")
            continue

        fold_pipeline = clone(pipeline)
        fold_pipeline.fit(X_train, y_train)
        preds = fold_pipeline.predict(X_val)
        if hasattr(preds, "ndim") and preds.ndim > 1:
            preds = preds.argmax(axis=1)

        acc = accuracy_score(y_val, preds)
        f1 = f1_score(y_val, preds, average="macro")
        bal = balanced_accuracy_score(y_val, preds)
        scores.append((acc, f1, bal))

        print(f"Fold {fold}: acc={acc:.3f} f1_macro={f1:.3f} bal_acc={bal:.3f}")

    if scores:
        arr = np.array(scores)
        print(
            "Media (walk-forward): "
            f"acc={arr[:,0].mean():.3f} f1_macro={arr[:,1].mean():.3f} "
            f"bal_acc={arr[:,2].mean():.3f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="data/db/trading.db")
    parser.add_argument("--jsonl-path", default="data/db/reflections/reflections_log.jsonl")
    parser.add_argument("--horizon-minutes", type=int, default=30)
    parser.add_argument("--threshold", type=float, default=0.0005)
    parser.add_argument("--tolerance-minutes", type=int, default=5)
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--model-dir", default="data/models/winfut")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    jsonl_path = Path(args.jsonl_path)

    X, y, meta = build_dataset(
        db_path=db_path,
        jsonl_path=jsonl_path,
        include_jsonl=True,
        tolerance_minutes=args.tolerance_minutes,
        horizon_minutes=args.horizon_minutes,
        threshold=args.threshold,
        symbol="WING26",
    )

    if X.empty:
        print("[ERRO] Nao ha dados suficientes para treino.")
        return

    # Evitar Leakage: Remover timestamp e colunas de target escondidas
    X = X.drop(columns=["timestamp", "current_price", "future_return"], errors="ignore")

    print("Dataset:")
    print(f"  Linhas totais (features): {meta.rows_total}")
    print(f"  Linhas rotuladas: {meta.rows_labeled}")
    print(f"  Periodo: {meta.start} -> {meta.end}")
    print(f"  Horizonte: {meta.horizon_minutes} min | Threshold: {meta.threshold}")
    print("Distribuicao de classes:")
    print(y.value_counts(normalize=True).round(3).to_string())

    label_encoder = LabelEncoder()
    y_encoded = pd.Series(label_encoder.fit_transform(y), index=y.index)

    numeric_cols, cat_cols = _split_columns(X)
    pipeline = _build_pipeline(numeric_cols, cat_cols)

    print("\nValidacao walk-forward:")
    _evaluate_walk_forward(X, y_encoded, pipeline, n_splits=args.splits)

    print("\nTreinando modelo final...")
    pipeline.fit(X, y_encoded)

    preds = pipeline.predict(X)
    if hasattr(preds, "ndim") and preds.ndim > 1:
        preds = preds.argmax(axis=1)
    pred_labels = label_encoder.inverse_transform(preds)
    print("\nMetrica no treino (para sanity check):")
    print(f"Accuracy: {accuracy_score(y, pred_labels):.3f}")
    print(f"F1 macro: {f1_score(y, pred_labels, average='macro'):.3f}")
    print("Relatorio:")
    print(classification_report(y, pred_labels, digits=3))
    print("Matriz de confusao:")
    print(confusion_matrix(y, pred_labels, labels=label_encoder.classes_))

    model_dir = Path(args.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    ts = pd.Timestamp.utcnow().strftime("%Y%m%d_%H%M%S")
    model_path = model_dir / f"winfut_model_{ts}.pkl"
    latest_path = model_dir / "winfut_model_latest.pkl"

    payload = {
        "pipeline": pipeline,
        "numeric_cols": numeric_cols,
        "cat_cols": cat_cols,
        "meta": meta.__dict__,
        "label_classes": label_encoder.classes_.tolist(),
    }
    joblib.dump(payload, model_path)
    joblib.dump(payload, latest_path)

    print(f"\nModelo salvo em: {model_path}")
    print(f"Modelo latest: {latest_path}")


if __name__ == "__main__":
    main()
