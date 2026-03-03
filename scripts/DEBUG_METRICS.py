"""
DEBUG: Investigar problema com métricas zeradas no grid_search
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_score, recall_score, confusion_matrix

# Load dataset
df = pd.read_csv('training_dataset.csv')
X = df.drop(['window_id', 'label'], axis=1).values
y = df['label'].values

print(f"Dataset: {X.shape[0]} × {X.shape[1]}")
print(f"Labels: {(y==1).sum()} BUY, {(y==0).sum()} SKIP")

# Split
X_temp, X_test, y_temp, y_test = train_test_split(
    X, y, test_size=0.15, random_state=42, stratify=y
)
X_train, X_val, y_train, y_val = train_test_split(
    X_temp, y_temp, test_size=15/85, random_state=42, stratify=y_temp
)

print(f"\nTrain: {X_train.shape[0]} | Val: {X_val.shape[0]} | Test: {X_test.shape[0]}")
print(f"Train labels: {(y_train==1).sum()} BUY, {(y_train==0).sum()} SKIP")

# Train
model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)

# Predict
y_val_proba = model.predict_proba(X_val)[:, 1]
y_test_proba = model.predict_proba(X_test)[:, 1]

print(f"\nProbability ranges (val):")
print(f"  Min: {y_val_proba.min():.4f}")
print(f"  Max: {y_val_proba.max():.4f}")
print(f"  Mean: {y_val_proba.mean():.4f}")
print(f"  Median: {np.median(y_val_proba):.4f}")

print(f"\nProbability ranges (test):")
print(f"  Min: {y_test_proba.min():.4f}")
print(f"  Max: {y_test_proba.max():.4f}")
print(f"  Mean: {y_test_proba.mean():.4f}")
print(f"  Median: {np.median(y_test_proba):.4f}")

# Test threshold 0.5 (padrão)
print(f"\nTest com threshold 0.5:")
y_val_pred = (y_val_proba >= 0.5).astype(int)
y_test_pred = (y_test_proba >= 0.5).astype(int)

print(f"Val pred: {(y_val_pred==1).sum()} positivas (de {len(y_val_pred)})")
print(f"Test pred: {(y_test_pred==1).sum()} positivas (de {len(y_test_pred)})")

f1 = f1_score(y_val, y_val_pred, zero_division=0)
print(f"F1 (val): {f1:.4f}")

tn, fp, fn, tp = confusion_matrix(y_test, y_test_pred).ravel()
print(f"Confusion matrix (test): TP={tp}, FP={fp}, FN={fn}, TN={tn}")

# Test various thresholds
print(f"\nTest various thresholds:")
for t in [0.5, 0.3, 0.2, 0.1, 0.05]:
    y_pred = (y_test_proba >= t).astype(int)
    n_pos = (y_pred==1).sum()
    if n_pos > 0:
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        win_rate = tp / (tp + fp) if (tp + fp) > 0 else 0
        print(f"  t={t:.2f}: {n_pos} pred | TP={tp}, FP={fp}, WIN_RATE={win_rate:.4f}")
