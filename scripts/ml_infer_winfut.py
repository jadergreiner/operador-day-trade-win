"""Run inference for WINFUT day-trade model using latest logs."""

from __future__ import annotations

import sys
from pathlib import Path as _Path

ROOT_DIR = _Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import argparse
from pathlib import Path

import joblib

from src.application.services.ml.winfut_dataset import build_latest_features


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="data/db/trading.db")
    parser.add_argument("--jsonl-path", default="data/db/reflections/reflections_log.jsonl")
    parser.add_argument("--model-path", default="data/models/winfut/winfut_model_latest.pkl")
    parser.add_argument("--tolerance-minutes", type=int, default=5)
    args = parser.parse_args()

    model_path = Path(args.model_path)
    if not model_path.exists():
        print(f"[ERRO] Modelo nao encontrado: {model_path}")
        return

    payload = joblib.load(model_path)
    pipeline = payload["pipeline"]
    label_classes = payload.get("label_classes")

    latest = build_latest_features(
        db_path=Path(args.db_path),
        jsonl_path=Path(args.jsonl_path),
        include_jsonl=True,
        tolerance_minutes=args.tolerance_minutes,
    )

    if latest.empty:
        print("[ERRO] Nao ha dados recentes para inferencia.")
        return

    raw_pred = pipeline.predict(latest)
    if hasattr(raw_pred, "ndim") and raw_pred.ndim > 1:
        pred_idx = int(raw_pred.argmax(axis=1)[0])
    else:
        pred_idx = int(raw_pred[0])
    proba = pipeline.predict_proba(latest)[0]
    classes = pipeline.named_steps["model"].classes_

    if label_classes:
        pred = label_classes[pred_idx]
        proba_map = {label_classes[int(cls)]: float(p) for cls, p in zip(classes, proba)}
    else:
        pred = pred_idx
        proba_map = {str(cls): float(p) for cls, p in zip(classes, proba)}

    ts = latest["timestamp"].iloc[0]
    price = latest["current_price"].iloc[0]

    print("\nINFERENCIA WINFUT")
    print(f"Timestamp: {ts}")
    print(f"Preco: {price}")
    print(f"Sinal: {pred}")
    print("Probabilidades:")
    for cls, p in proba_map.items():
        print(f"  {cls}: {p:.3f}")


if __name__ == "__main__":
    main()
