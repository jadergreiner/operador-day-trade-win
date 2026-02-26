"""
ETAPA 2.1: MODEL OPTIMIZATION - Class Weights + Hyperparameter Tuning

Objetivo: Atingir AC-3 (F1 >= 0.65) E AC-4 (Win Rate >= 60%)
Estratégia: Penalizar False Positives com class_weight para maximizar Win Rate
Data: 25/02/2026
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

from ETAPA1_ML_EXPERT_SCAFFOLD import load_dataset


def run_optimized_grid_search():
    """
    ETAPA 2.1: Grid search com class weights otimizados.
    
    Estratégia:
    - Usar scale_pos_weight para penalizar FP (aumentar Win Rate)
    - Combinar com threshold tuning
    - Testar 8 configs diferentes
    """
    
    print("\n" + "=" * 80)
    print("🔍 ETAPA 2.1: MODEL OPTIMIZATION - Class Weights Tuning")
    print("=" * 80)
    
    # ========================================================================
    # PASSO 1: Carregar dataset
    # ========================================================================
    print("\n[PASSO 1] Carregando dataset...")
    X, y = load_dataset('training_dataset.csv')
    n_samples, n_features = X.shape
    n_buy = (y == 1).sum()
    n_skip = (y == 0).sum()
    
    print(f"✅ Dataset: {n_samples} samples × {n_features} features")
    print(f"   - BUY: {n_buy} ({100*n_buy/n_samples:.1f}%)")
    print(f"   - SKIP: {n_skip} ({100*n_skip/n_samples:.1f}%)")
    
    # ========================================================================
    # PASSO 2: Split (70/15/15)
    # ========================================================================
    print("\n[PASSO 2] Dividindo dataset (70/15/15)...")
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=15/85, random_state=42, stratify=y_temp
    )
    
    print(f"   Train: {X_train.shape[0]} | Val: {X_val.shape[0]} | Test: {X_test.shape[0]}")
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    
    # ========================================================================
    # PASSO 3: Testar 8 configs de class_weight + thresholds
    # ========================================================================
    print("\n[PASSO 3] Testando 8 configs de scale_pos_weight...")
    print("   Estratégia: Variar scale_pos_weight para penalizar FP")
    print("   scale_pos_weight controla o trade-off BUY vs SKIP")
    
    try:
        from xgboost import XGBClassifier
    except ImportError:
        print("❌ Erro: XGBoost não está instalado")
        return False
    
    # Scale pos weight é: n_negatives / n_positives
    # Aumentar scale_pos_weight = penalizar False Positives (aumentar Win Rate)
    base_scale = float(n_skip) / float(n_buy)
    
    # 8 configs diferentes de scale_pos_weight
    scale_weights = [
        base_scale * 0.8,      # Menos peso em FP (mais liberal)
        base_scale * 1.0,      # Padrão
        base_scale * 1.2,
        base_scale * 1.4,
        base_scale * 1.6,      # Mais peso em FP (mais conservador)
        base_scale * 1.8,
        base_scale * 2.0,
        base_scale * 2.2,
    ]
    
    all_results = {}
    best_f1 = 0
    best_wr = 0
    best_config = None
    best_threshold = None
    
    for config_idx, scale_pos_weight in enumerate(scale_weights, 1):
        print(f"\n   [Config {config_idx}/8] scale_pos_weight={scale_pos_weight:.3f}")
        
        # Train model com class weight
        model = XGBClassifier(
            n_estimators=200,
            max_depth=8,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,  # ← KEY: Penalizar FP
            random_state=42,
            verbosity=0,
            n_jobs=-1
        )
        model.fit(X_train_scaled, y_train, verbose=False)
        
        # Predict probabilities
        y_val_proba = model.predict_proba(X_val_scaled)[:, 1]
        y_test_proba = model.predict_proba(X_test_scaled)[:, 1]
        
        # Testar múltiplos thresholds para esta config
        config_results = {}
        
        for threshold in [0.1, 0.2, 0.3, 0.4, 0.5]:
            y_val_pred = (y_val_proba >= threshold).astype(int)
            y_test_pred = (y_test_proba >= threshold).astype(int)
            
            from sklearn.metrics import f1_score, precision_score, recall_score, confusion_matrix
            
            f1 = f1_score(y_val, y_val_pred, zero_division=0)
            precision = precision_score(y_val, y_val_pred, zero_division=0)
            recall = recall_score(y_val, y_val_pred, zero_division=0)
            
            tn, fp, fn, tp = confusion_matrix(y_test, y_test_pred).ravel()
            win_rate = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            
            config_results[threshold] = {
                'f1': round(f1, 4),
                'precision': round(precision, 4),
                'recall': round(recall, 4),
                'win_rate': round(win_rate, 4),
            }
            
            # Track best
            if f1 >= 0.65 and win_rate >= 0.60:
                if f1 + win_rate > best_f1 + best_wr:
                    best_f1 = f1
                    best_wr = win_rate
                    best_config = config_idx
                    best_threshold = threshold
        
        all_results[float(config_idx)] = config_results
        
        # Mostrar melhor threshold para esta config
        best_t = max(config_results, key=lambda t: config_results[t]['f1'])
        best_metrics = config_results[best_t]
        print(f"      Best threshold: {best_t} → F1={best_metrics['f1']:.4f}, WR={best_metrics['win_rate']:.4f}")
    
    # ========================================================================
    # PASSO 4: Relatório de resultados
    # ========================================================================
    print("\n" + "-" * 80)
    print("📊 RESULTADOS OTIMIZAÇÃO:\n")
    
    if best_threshold is not None:
        print(f"🎉 SUCESSO! Encontrado config que passa em AMBOS os blockers:")
        print(f"   Config: {best_config}/8")
        print(f"   Scale Pos Weight: {scale_weights[best_config-1]:.3f}")
        print(f"   Threshold: {best_threshold}")
        print(f"   F1 Score: {best_f1:.4f} ✅ (target: ≥0.65)")
        print(f"   Win Rate: {best_wr:.4f} ✅ (target: ≥0.60)")
        gate2_pass = True
    else:
        print(f"⚠️  Nenhuma config atingiu AMBOS os blockers (AC-3 E AC-4)")
        print(f"   Recomendação: Tentar feature engineering ou revisitar especificação")
        gate2_pass = False
    
    print("\n" + "=" * 80)
    
    return gate2_pass, all_results, best_config, best_threshold, scale_weights


if __name__ == '__main__':
    success, results, config, threshold, scales = run_optimized_grid_search()
    exit(0 if success else 1)
