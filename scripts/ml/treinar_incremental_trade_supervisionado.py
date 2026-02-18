#!/usr/bin/env python3
"""Treino incremental diário usando dataset consolidado por trade.

Fluxo:
1) Carrega dataset acumulado (data/ml/trade_supervised_dataset.csv)
2) Seleciona janela temporal até a data de referência
3) Treina incrementalmente apenas novos trades (partial_fit)
4) Salva estado do modelo para próxima sessão
5) Gera relatório em data/ml/reports
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.preprocessing import LabelEncoder

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT_DIR / "data" / "ml" / "trade_supervised_dataset.csv"
MODEL_DIR = ROOT_DIR / "data" / "models" / "trade_incremental"
REPORT_DIR = ROOT_DIR / "data" / "ml" / "reports"

# Colunas excluídas para evitar vazamento de alvo e metadata operacional
EXCLUDE_COLUMNS = {
    "id",
    "trade_id",
    "broker_trade_id",
    "notes",
    "created_at",
    "updated_at",
    "session_date",
    "entry_time",
    "exit_time",
    "mt5_first_exec",
    "mt5_last_exec",
    "target_pnl",
    "target_is_win",
    "target_is_loss",
    "target_class",
    "profit_loss",
    "return_percentage",
    "exit_price",
    "price_diff",
    "points_result_signed",
    "abs_points_moved",
    "audit_status",
    "audit_pnl_diff",
    "audit_missing_in_sqlite",
    "audit_extra_in_sqlite",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Treino incremental supervisionado por trade.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET), help="Dataset consolidado CSV.")
    parser.add_argument("--as-of-date", default=datetime.now().strftime("%Y-%m-%d"), help="Data de referência (YYYY-MM-DD).")
    parser.add_argument("--days-window", type=int, default=180, help="Janela de dias para treino ativo.")
    parser.add_argument("--min-rows", type=int, default=20, help="Mínimo de linhas para treinar.")
    parser.add_argument("--force-full-retrain", action="store_true", help="Ignora estado anterior e recomeça do zero.")
    return parser.parse_args()


def _safe_json_default(obj: Any) -> Any:
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    return str(obj)


def _load_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("Dataset vazio.")

    required = {"trade_id", "session_date", "target_class"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset sem colunas obrigatórias: {sorted(missing)}")

    df["session_date"] = pd.to_datetime(df["session_date"], errors="coerce")
    df = df.dropna(subset=["session_date", "trade_id", "target_class"]).copy()
    return df


def _select_window(df: pd.DataFrame, as_of_date: str, days_window: int) -> pd.DataFrame:
    ref = pd.to_datetime(as_of_date, errors="coerce")
    if pd.isna(ref):
        raise ValueError("--as-of-date inválida. Use YYYY-MM-DD.")

    start = ref - pd.Timedelta(days=max(1, days_window))
    mask = (df["session_date"] >= start) & (df["session_date"] <= ref)
    out = df.loc[mask].copy()

    if "entry_time" in out.columns:
        out["entry_time"] = pd.to_datetime(out["entry_time"], errors="coerce")
        out = out.sort_values(["session_date", "entry_time"], na_position="last")
    else:
        out = out.sort_values(["session_date", "trade_id"])

    return out.reset_index(drop=True)


def _feature_columns(df: pd.DataFrame) -> list[str]:
    cols: list[str] = []
    for col in df.columns:
        if col in EXCLUDE_COLUMNS:
            continue
        if col.startswith("target_"):
            continue
        if col.endswith("_raw"):
            continue
        cols.append(col)
    return cols


def _rows_to_dicts(df: pd.DataFrame, cols: list[str]) -> list[dict[str, Any]]:
    tmp = df[cols].copy()
    for col in cols:
        if pd.api.types.is_datetime64_any_dtype(tmp[col]):
            tmp[col] = tmp[col].fillna(pd.Timestamp("1970-01-01")).astype(str)
        elif pd.api.types.is_numeric_dtype(tmp[col]):
            tmp[col] = tmp[col].fillna(0.0).astype(float)
        else:
            tmp[col] = tmp[col].fillna("UNKNOWN").astype(str)
    return tmp.to_dict(orient="records")


def _make_trade_key(df: pd.DataFrame) -> pd.Series:
    return df["session_date"].dt.strftime("%Y-%m-%d") + "|" + df["trade_id"].astype(str)


def _new_state(feature_columns: list[str]) -> dict[str, Any]:
    model = SGDClassifier(
        loss="log_loss",
        alpha=1e-4,
        max_iter=1,
        learning_rate="optimal",
        random_state=42,
        class_weight=None,
        warm_start=True,
    )
    return {
        "vectorizer": DictVectorizer(sparse=True),
        "label_encoder": LabelEncoder(),
        "model": model,
        "feature_columns": feature_columns,
        "trained_trade_keys": set(),
        "trained_at": None,
        "n_updates": 0,
    }


def _evaluate_quick(model: SGDClassifier, X, y_true: np.ndarray) -> dict[str, float]:
    if len(y_true) == 0:
        return {"accuracy": 0.0, "f1_macro": 0.0}
    y_pred = model.predict(X)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }


def main() -> int:
    args = _parse_args()

    dataset_path = Path(args.dataset)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    state_path = MODEL_DIR / "trade_incremental_state_latest.pkl"
    model_snapshot = MODEL_DIR / f"trade_incremental_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"

    try:
        df = _load_dataset(dataset_path)
        df = _select_window(df, args.as_of_date, args.days_window)
    except Exception as exc:
        print(f"[ERRO] Falha ao carregar dataset: {exc}")
        return 1

    if len(df) < args.min_rows:
        print(f"[AVISO] Dados insuficientes para treino (linhas={len(df)} < min_rows={args.min_rows}).")
        return 0

    feature_cols = _feature_columns(df)
    if not feature_cols:
        print("[ERRO] Nenhuma feature disponível após filtros.")
        return 2

    if state_path.exists() and not args.force_full_retrain:
        state = joblib.load(state_path)
        vectorizer: DictVectorizer = state["vectorizer"]
        label_encoder: LabelEncoder = state["label_encoder"]
        model: SGDClassifier = state["model"]
        trained_trade_keys: set[str] = set(state.get("trained_trade_keys", set()))
        feature_columns_saved = state.get("feature_columns", [])

        # Se schema de features mudou, recria estado do zero para evitar inconsistência
        if list(feature_columns_saved) != list(feature_cols):
            state = _new_state(feature_cols)
            vectorizer = state["vectorizer"]
            label_encoder = state["label_encoder"]
            model = state["model"]
            trained_trade_keys = set()
            force_full = True
        else:
            force_full = False
    else:
        state = _new_state(feature_cols)
        vectorizer = state["vectorizer"]
        label_encoder = state["label_encoder"]
        model = state["model"]
        trained_trade_keys = set()
        force_full = True

    trade_keys = _make_trade_key(df)
    df = df.assign(_trade_key=trade_keys)

    if force_full or args.force_full_retrain:
        train_df = df.copy()
    else:
        train_df = df[~df["_trade_key"].isin(trained_trade_keys)].copy()

    if train_df.empty:
        print("[OK] Nenhum novo trade para treino incremental.")
        return 0

    X_dict = _rows_to_dicts(train_df, feature_cols)
    y_raw = train_df["target_class"].astype(str).values

    unique_classes = sorted(pd.Series(y_raw).dropna().unique().tolist())
    if len(unique_classes) < 2:
        # Bootstrap: persiste estado/schema mesmo sem diversidade de classes.
        vectorizer.fit(X_dict)
        label_encoder.fit(unique_classes)

        state_out = {
            "vectorizer": vectorizer,
            "label_encoder": label_encoder,
            "model": model,
            "feature_columns": feature_cols,
            "trained_trade_keys": trained_trade_keys,
            "trained_at": datetime.now().isoformat(),
            "n_updates": int(state.get("n_updates", 0)) + 1,
            "dataset_path": str(dataset_path),
            "as_of_date": args.as_of_date,
            "days_window": args.days_window,
            "bootstrap_only": True,
        }

        joblib.dump(state_out, state_path)
        joblib.dump(state_out, model_snapshot)

        report = {
            "generated_at": datetime.now().isoformat(),
            "as_of_date": args.as_of_date,
            "dataset_path": str(dataset_path),
            "rows_window": int(len(df)),
            "rows_incremental": int(len(train_df)),
            "feature_count": int(len(feature_cols)),
            "classes": [str(c) for c in unique_classes],
            "batch_metrics": {"accuracy": 0.0, "f1_macro": 0.0},
            "daily_metrics": {},
            "classification_report_daily": {},
            "trained_trade_keys_total": int(len(trained_trade_keys)),
            "state_latest": str(state_path),
            "state_snapshot": str(model_snapshot),
            "mode": "bootstrap_single_class",
        }

        report_path = REPORT_DIR / f"incremental_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=_safe_json_default)

        print(
            "[AVISO] Lote incremental com apenas 1 classe. "
            "Estado/schema atualizados em modo bootstrap; aguardando diversidade "
            "de classes (WIN/LOSS/BREAKEVEN) para treinar."
        )
        print(f"Estado latest: {state_path}")
        print(f"Snapshot: {model_snapshot}")
        print(f"Relatório: {report_path}")
        return 0

    if force_full or args.force_full_retrain or not trained_trade_keys:
        X = vectorizer.fit_transform(X_dict)
        y = label_encoder.fit_transform(y_raw)
        model.partial_fit(X, y, classes=np.arange(len(label_encoder.classes_)))
    else:
        X = vectorizer.transform(X_dict)
        y = label_encoder.transform(y_raw)
        model.partial_fit(X, y)

    # Métrica rápida no lote treinado
    metrics = _evaluate_quick(model, X, y)

    # Métrica de sanidade no recorte mais recente da data de referência
    ref_date = pd.to_datetime(args.as_of_date)
    eval_df = df[df["session_date"].dt.date == ref_date.date()].copy()
    daily_metrics: dict[str, float] = {}
    class_report: dict[str, Any] = {}

    if not eval_df.empty:
        X_eval = vectorizer.transform(_rows_to_dicts(eval_df, feature_cols))
        y_eval = label_encoder.transform(eval_df["target_class"].astype(str).values)
        daily_metrics = _evaluate_quick(model, X_eval, y_eval)

        y_pred_eval = model.predict(X_eval)
        class_report = classification_report(
            y_eval,
            y_pred_eval,
            output_dict=True,
            zero_division=0,
            target_names=[str(c) for c in label_encoder.classes_],
        )

    newly_trained_keys = set(train_df["_trade_key"].tolist())
    all_trained_keys = trained_trade_keys.union(newly_trained_keys)

    state_out = {
        "vectorizer": vectorizer,
        "label_encoder": label_encoder,
        "model": model,
        "feature_columns": feature_cols,
        "trained_trade_keys": all_trained_keys,
        "trained_at": datetime.now().isoformat(),
        "n_updates": int(state.get("n_updates", 0)) + 1,
        "dataset_path": str(dataset_path),
        "as_of_date": args.as_of_date,
        "days_window": args.days_window,
    }

    joblib.dump(state_out, state_path)
    joblib.dump(state_out, model_snapshot)

    report = {
        "generated_at": datetime.now().isoformat(),
        "as_of_date": args.as_of_date,
        "dataset_path": str(dataset_path),
        "rows_window": int(len(df)),
        "rows_incremental": int(len(train_df)),
        "feature_count": int(len(feature_cols)),
        "classes": [str(c) for c in label_encoder.classes_],
        "batch_metrics": metrics,
        "daily_metrics": daily_metrics,
        "classification_report_daily": class_report,
        "trained_trade_keys_total": int(len(all_trained_keys)),
        "state_latest": str(state_path),
        "state_snapshot": str(model_snapshot),
        "mode": "full_retrain" if (force_full or args.force_full_retrain) else "incremental_update",
    }

    report_path = REPORT_DIR / f"incremental_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=_safe_json_default)

    print("=" * 92)
    print(
        f"TREINO INCREMENTAL CONCLUÍDO | modo={report['mode']} | "
        f"rows_incremental={report['rows_incremental']} | features={report['feature_count']}"
    )
    print("=" * 92)
    print(f"Métricas lote: acc={metrics.get('accuracy', 0):.3f} | f1_macro={metrics.get('f1_macro', 0):.3f}")
    if daily_metrics:
        print(
            f"Métricas dia {args.as_of_date}: acc={daily_metrics.get('accuracy', 0):.3f} | "
            f"f1_macro={daily_metrics.get('f1_macro', 0):.3f}"
        )
    print(f"Estado latest: {state_path}")
    print(f"Snapshot: {model_snapshot}")
    print(f"Relatório: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
