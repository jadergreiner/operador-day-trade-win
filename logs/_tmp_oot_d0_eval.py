import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score

from scripts.ml.extract_rl_dataset import build_unified_dataset
from scripts.ml.backtest_simulation import BacktestConfig, BacktestSimulation, _get_feature_columns as bt_feature_cols
from src.application.services.ml.feature_engineering_v2 import FeatureEngineer, FeatureConfig
from src.application.services.ml.target_engineering import TargetEngineer, TargetConfig

DB_PATH = ROOT / 'data' / 'db' / 'trading.db'
MODELS = {
    'baseline_20260212': ROOT / 'data' / 'models' / 'lgbm' / 'lgbm_classification_20260212_184547.pkl',
    'novo_20260213': ROOT / 'data' / 'models' / 'lgbm' / 'lgbm_classification_20260213_183729.pkl',
}

def prep_X_for_model(df: pd.DataFrame, model_features: list[str]) -> pd.DataFrame:
    X = df.copy()
    for mf in model_features:
        if mf not in X.columns:
            X[mf] = np.nan
    X = X[model_features].copy()

    cat = set(FeatureConfig().categorical_features)
    for c in X.columns:
        if c in cat:
            X[c] = X[c].astype('category')
        elif X[c].dtype == object:
            X[c] = pd.to_numeric(X[c], errors='coerce')
        elif X[c].dtype == bool:
            X[c] = X[c].astype(int)
    return X

def class_metrics(model, df_eval: pd.DataFrame) -> dict:
    y_true = df_eval['target_class_encoded'].copy()
    model_features = list(getattr(model, 'feature_names_', None) or getattr(model, 'feature_name_', None) or [])
    if not model_features:
        model_features = bt_feature_cols(df_eval)
    model_features = [c for c in model_features if c != 'date']
    X_eval = prep_X_for_model(df_eval, model_features)

    mask = y_true.notna()
    X_eval = X_eval[mask]
    y_true = y_true[mask]

    y_pred = model.predict(X_eval)
    return {
        'n_samples': int(len(y_true)),
        'accuracy': float(accuracy_score(y_true, y_pred)),
        'balanced_accuracy': float(balanced_accuracy_score(y_true, y_pred)),
        'f1_macro': float(f1_score(y_true, y_pred, average='macro', zero_division=0)),
    }

def run_backtest_day(model, df_eval: pd.DataFrame) -> dict:
    model_features = list(getattr(model, 'feature_names_', None) or getattr(model, 'feature_name_', None) or [])
    if not model_features:
        model_features = bt_feature_cols(df_eval)
    model_features = [c for c in model_features if c != 'date']

    bt = BacktestSimulation(BacktestConfig(min_confidence=0.55, max_trades_per_day=8))
    m = bt.run(df_eval.copy(), model, model_features, mode='classification', target_horizon=30)
    keep = ['n_trades','win_rate','total_net_pnl_pts','profit_factor','max_drawdown_pts','sharpe_ratio','buy_trades','sell_trades']
    return {k: m.get(k) for k in keep}

def main():
    raw = build_unified_dataset(db_path=DB_PATH, days=180, horizon=30)
    fe = FeatureEngineer()
    df = fe.transform(raw)
    te = TargetEngineer(TargetConfig(primary_horizon=30))
    df = te.build_targets(df)
    df = df.sort_values('timestamp').reset_index(drop=True)
    df['date'] = df['timestamp'].dt.date.astype(str)

    d0 = df['date'].max()
    train_df = df[df['date'] < d0].copy()
    test_df = df[df['date'] == d0].copy()

    print(f"[OOT] D0={d0} | train_rows={len(train_df)} | test_rows={len(test_df)}")

    feat_cols = [c for c in bt_feature_cols(df) if c != 'date']
    for c in feat_cols:
        if c not in train_df.columns:
            train_df[c] = np.nan
        if c not in test_df.columns:
            test_df[c] = np.nan

    X_train = prep_X_for_model(train_df[feat_cols], feat_cols)
    y_train = train_df['target_class_encoded'].copy()
    mask = y_train.notna()
    X_train = X_train[mask]
    y_train = y_train[mask]

    params = {
        'boosting_type': 'gbdt', 'num_leaves': 31, 'max_depth': 5,
        'learning_rate': 0.05, 'n_estimators': 500,
        'min_child_samples': 20, 'subsample': 0.8, 'colsample_bytree': 0.8,
        'reg_alpha': 0.1, 'reg_lambda': 1.0,
        'objective': 'multiclass', 'num_class': int(y_train.nunique()),
        'metric': 'multi_logloss', 'random_state': 42, 'verbose': -1, 'n_jobs': -1,
    }
    oot_model = lgb.LGBMClassifier(**params)
    cat = [c for c in X_train.columns if X_train[c].dtype.name == 'category']
    oot_model.fit(X_train, y_train, categorical_feature=cat if cat else 'auto')

    results = {
        'generated_at': datetime.now().isoformat(),
        'd0': d0,
        'train_rows': int(len(train_df)),
        'test_rows': int(len(test_df)),
        'models': {}
    }

    candidates = {'oot_train_to_d_minus_1': oot_model}
    for name, path in MODELS.items():
        if path.exists():
            candidates[name] = joblib.load(path)

    for name, model in candidates.items():
        print(f"\n[MODEL] {name}")
        cm = class_metrics(model, test_df)
        bt = run_backtest_day(model, test_df)
        results['models'][name] = {'classification': cm, 'trading_d0': bt}
        print(f"  cls: acc={cm['accuracy']:.3f} bal_acc={cm['balanced_accuracy']:.3f} f1={cm['f1_macro']:.3f} n={cm['n_samples']}")
        print(f"  bt : trades={bt['n_trades']} wr={bt['win_rate']:.3f} pnl={bt['total_net_pnl_pts']:.1f} dd={bt['max_drawdown_pts']:.1f} pf={bt['profit_factor']:.2f}")

    rank = sorted(
        results['models'].items(),
        key=lambda kv: (
            kv[1]['trading_d0'].get('total_net_pnl_pts', -1e9),
            kv[1]['classification'].get('f1_macro', -1e9),
        ),
        reverse=True,
    )
    results['ranking'] = [r[0] for r in rank]

    out = ROOT / 'logs' / f"oot_d0_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"\n[RANK] {results['ranking']}")
    print(f"[OK] relatório salvo em {out}")

if __name__ == '__main__':
    main()
