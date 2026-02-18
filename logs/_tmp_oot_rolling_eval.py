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
BASELINE_MODEL = ROOT / 'data' / 'models' / 'lgbm' / 'lgbm_classification_20260212_184547.pkl'
NEW_MODEL = ROOT / 'data' / 'models' / 'lgbm' / 'lgbm_classification_20260213_183729.pkl'


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


def trading_metrics_day(model, day_df: pd.DataFrame) -> dict:
    model_features = list(getattr(model, 'feature_names_', None) or getattr(model, 'feature_name_', None) or [])
    if not model_features:
        model_features = bt_feature_cols(day_df)
    model_features = [c for c in model_features if c != 'date']

    bt = BacktestSimulation(BacktestConfig(min_confidence=0.55, max_trades_per_day=8))
    metrics = bt.run(day_df.copy(), model, model_features, mode='classification', target_horizon=30)

    keep = [
        'n_trades', 'win_rate', 'total_net_pnl_pts', 'profit_factor',
        'max_drawdown_pts', 'sharpe_ratio', 'buy_trades', 'sell_trades'
    ]
    return {k: metrics.get(k) for k in keep}


def train_oot_model(train_df: pd.DataFrame, feat_cols: list[str]):
    X_train = prep_X_for_model(train_df[feat_cols], feat_cols)
    y_train = train_df['target_class_encoded'].copy()
    mask = y_train.notna()
    X_train = X_train[mask]
    y_train = y_train[mask]

    if len(y_train) < 50 or y_train.nunique() < 2:
        return None, {'train_samples': int(len(y_train)), 'classes': int(y_train.nunique()) if len(y_train) else 0}

    params = {
        'boosting_type': 'gbdt', 'num_leaves': 31, 'max_depth': 5,
        'learning_rate': 0.05, 'n_estimators': 500,
        'min_child_samples': 20, 'subsample': 0.8, 'colsample_bytree': 0.8,
        'reg_alpha': 0.1, 'reg_lambda': 1.0,
        'objective': 'multiclass', 'num_class': int(y_train.nunique()),
        'metric': 'multi_logloss', 'random_state': 42, 'verbose': -1, 'n_jobs': -1,
    }

    model = lgb.LGBMClassifier(**params)
    cat = [c for c in X_train.columns if X_train[c].dtype.name == 'category']
    model.fit(X_train, y_train, categorical_feature=cat if cat else 'auto')
    return model, {'train_samples': int(len(y_train)), 'classes': int(y_train.nunique())}


def safe_mean(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    return float(np.mean(vals))


def main():
    print('[ROLLING] extraindo dataset base...')
    raw = build_unified_dataset(db_path=DB_PATH, days=180, horizon=30)
    fe = FeatureEngineer()
    df = fe.transform(raw)
    te = TargetEngineer(TargetConfig(primary_horizon=30))
    df = te.build_targets(df)
    df = df.sort_values('timestamp').reset_index(drop=True)
    df['date'] = df['timestamp'].dt.date.astype(str)

    unique_dates = sorted(df['date'].unique())
    if len(unique_dates) < 4:
        raise RuntimeError(f'Poucas datas para rolling robusto: {unique_dates}')

    test_dates = unique_dates[-3:]  # D-2, D-1, D0
    print(f"[ROLLING] cortes={test_dates}")

    feat_cols = [c for c in bt_feature_cols(df) if c != 'date']

    static_models = {}
    if BASELINE_MODEL.exists():
        static_models['baseline_20260212'] = joblib.load(BASELINE_MODEL)
    if NEW_MODEL.exists():
        static_models['novo_20260213'] = joblib.load(NEW_MODEL)

    results = {
        'generated_at': datetime.now().isoformat(),
        'test_dates': test_dates,
        'train_window_rule': 'train: date < test_date',
        'models_evaluated': ['oot_train_until_prevday'] + list(static_models.keys()),
        'cuts': [],
    }

    aggregate = {}

    for d in test_dates:
        print(f"\n[CORTE] test_date={d}")
        train_df = df[df['date'] < d].copy()
        test_df = df[df['date'] == d].copy()

        for c in feat_cols:
            if c not in train_df.columns:
                train_df[c] = np.nan
            if c not in test_df.columns:
                test_df[c] = np.nan

        oot_model, oot_meta = train_oot_model(train_df, feat_cols)

        candidates = dict(static_models)
        if oot_model is not None:
            candidates = {'oot_train_until_prevday': oot_model, **candidates}

        cut_entry = {
            'test_date': d,
            'train_rows': int(len(train_df)),
            'test_rows': int(len(test_df)),
            'oot_train_meta': oot_meta,
            'models': {},
            'ranking_by_pnl': [],
        }

        ranking_rows = []
        for name, model in candidates.items():
            cm = class_metrics(model, test_df)
            tm = trading_metrics_day(model, test_df)
            cut_entry['models'][name] = {'classification': cm, 'trading': tm}
            ranking_rows.append((name, tm.get('total_net_pnl_pts', -1e9), cm.get('f1_macro', -1e9)))

            agg = aggregate.setdefault(name, {'acc': [], 'bal_acc': [], 'f1': [], 'pnl': [], 'wr': [], 'trades': [], 'wins_top_pnl': 0, 'cuts': 0})
            agg['acc'].append(cm.get('accuracy'))
            agg['bal_acc'].append(cm.get('balanced_accuracy'))
            agg['f1'].append(cm.get('f1_macro'))
            agg['pnl'].append(tm.get('total_net_pnl_pts'))
            agg['wr'].append(tm.get('win_rate'))
            agg['trades'].append(tm.get('n_trades'))
            agg['cuts'] += 1

            print(f"  - {name}: f1={cm.get('f1_macro'):.3f} pnl={tm.get('total_net_pnl_pts'):.1f} trades={tm.get('n_trades')} wr={tm.get('win_rate'):.3f}")

        ranking_rows.sort(key=lambda x: (x[1], x[2]), reverse=True)
        cut_entry['ranking_by_pnl'] = [r[0] for r in ranking_rows]
        if ranking_rows:
            aggregate[ranking_rows[0][0]]['wins_top_pnl'] += 1

        print(f"  ranking: {cut_entry['ranking_by_pnl']}")
        results['cuts'].append(cut_entry)

    summary = {}
    for name, agg in aggregate.items():
        summary[name] = {
            'cuts': agg['cuts'],
            'avg_accuracy': safe_mean(agg['acc']),
            'avg_balanced_accuracy': safe_mean(agg['bal_acc']),
            'avg_f1_macro': safe_mean(agg['f1']),
            'sum_net_pnl_pts': float(np.nansum(np.array(agg['pnl'], dtype=float))) if agg['pnl'] else 0.0,
            'avg_net_pnl_pts': safe_mean(agg['pnl']),
            'avg_win_rate': safe_mean(agg['wr']),
            'avg_trades': safe_mean(agg['trades']),
            'top_pnl_wins': agg['wins_top_pnl'],
        }

    overall_ranking = sorted(
        summary.items(),
        key=lambda kv: (
            kv[1]['top_pnl_wins'],
            kv[1]['sum_net_pnl_pts'],
            kv[1]['avg_f1_macro'] if kv[1]['avg_f1_macro'] is not None else -1e9,
        ),
        reverse=True,
    )

    results['aggregate_summary'] = summary
    results['overall_ranking'] = [r[0] for r in overall_ranking]

    out = ROOT / 'logs' / f"oot_rolling_3cuts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"\n[OVERALL_RANK] {results['overall_ranking']}")
    print(f"[OK] relatório salvo em {out}")


if __name__ == '__main__':
    main()
