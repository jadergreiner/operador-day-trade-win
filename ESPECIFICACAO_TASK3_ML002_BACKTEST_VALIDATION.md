# 🚀 TASK #3: INTEGRATION-ML-002 - Backtest Validation Grid Search

**Executor:** ML Expert (ID 2) + Quality QA (ID 12)
**Data Criação:** 25/02/2026 (agora)
**Status:** ⏳ PRONTA PARA EXECUÇÃO
**Squad:** 3 personas + 2 on-call backup
**Deliverables:** Grid search results + 7 ACs + unit tests

---

## 🎯 EXECUTIVE SUMMARY

Esta task valida o modelo ML com **grid search de 8 thresholds** no dataset já carregado (TODO-1 ✅):

1. **Entrada:** `training_dataset.csv` (435 amostras × 26 features + label)
2. **Processo:** Grid search [threshold_sigma = 1.0 até 3.0 em steps 0.5]
3. **Saída:** `backtest_final_metrics.json` com F1 > 0.65 validado
4. **Go/No-Go:** Resultado define se escalamos capital em Phase 2

---

## ✅ ACCEPTANCE CRITERIA (7 - TASK #3)

| AC # | Critério | Descrição Técnica | Test |
|------|----------|-------------------|------|
| **1** | Grid Search Executado | Testar 8 thresholds consecutivamente | `test_grid_search_execution()` |
| **2** | Métricas Calculadas | F1, Precision, Recall, Win Rate para cada | `test_metrics_calculation()` |
| **3** | F1 > 0.65 Validado | Melhor threshold atinge F1 >= 0.65 | `test_f1_threshold_validation()` |
| **4** | Win Rate >= 60% | Backtest win rate confirmado 60%+ | `test_win_rate_validation()` |
| **5** | Threshold Ótimo Selecionado | Melhor threshold identificado e salvo | `test_optimal_threshold_selection()` |
| **6** | Relatório Gerado | backtest_final_metrics.json persistido | `test_report_generation()` |
| **7** | Unit Tests > 90% | 7 testes passando, coverage > 90% | `pytest --cov` |

---

## 🔍 ESPECIFICAÇÃO TÉCNICA DETALHADA

### Entrada: Dataset Carregado (TODO-1 ✅)

```
File: training_dataset.csv
Shape: (435 samples, 26 columns)
  - Cols 1-24: engineered features (volatility, momentum, MA, patterns, lags, correlation)
  - Col 25: label (0=SKIP, 1=BUY)
  - Col 26: window_id (traceability)

Distribuição Labels:
  - BUY: 54.9% (239 samples)
  - SKIP: 45.1% (196 samples)
  - Balance: 20-80% range ✅
```

### Grid Search Specification

```python
# Grid de 8 thresholds
thresholds = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]

# Para cada threshold:
for threshold in thresholds:
    # 1. Separar dados: train=70%, val=15%, test=15% (435*0.7=305, 65, 65)
    X_train, X_val, X_test = split_data(X, y, threshold)

    # 2. Treinar modelo (ou usar modelo base)
    # Se usar XGBoost: treinar em X_train/y_train
    # Se usar modelo base: usar modelo pré-treinado

    # 3. Avaliar em val set
    y_pred_val = model.predict(X_val)
    metrics_val = {
        'f1': f1_score(y_val, y_pred_val),
        'precision': precision_score(y_val, y_pred_val),
        'recall': recall_score(y_val, y_pred_val),
        'accuracy': accuracy_score(y_val, y_pred_val)
    }

    # 4. Backtest em test set (simular operações)
    trades = backtest_signal(y_test, y_pred_test, threshold)
    metrics_test = {
        'win_rate': calculate_win_rate(trades),
        'profit_factor': calculate_profit_factor(trades),
        'sharpe_ratio': calculate_sharpe(trades),
        'max_drawdown': calculate_max_drawdown(trades)
    }

    # 5. Salvar resultado
    results[threshold] = {
        'metrics_val': metrics_val,
        'metrics_test': metrics_test,
        'trades_count': len(trades),
        'timestamp': datetime.now()
    }

# Selecionar melhor threshold (maior F1 ou win_rate)
best_threshold = max(results, key=lambda t: results[t]['metrics_val']['f1'])
```

### Output: `backtest_final_metrics.json`

```json
{
  "grid_search_results": {
    "1.0": { "f1": 0.62, "win_rate": 58.5%, ... },
    "1.5": { "f1": 0.64, "win_rate": 61.2%, ... },
    "2.0": { "f1": 0.68, "win_rate": 63.9%, ... },
    "2.5": { "f1": 0.67, "win_rate": 62.1%, ... },
    ...
  },
  "optimal_threshold": 2.0,
  "optimal_metrics": {
    "f1": 0.68,
    "precision": 0.70,
    "recall": 0.66,
    "win_rate": 63.9,
    "profit_factor": 1.85,
    "sharpe_ratio": 1.42,
    "max_drawdown": -12.5
  },
  "decision": "GO",
  "reason": "F1=0.68 (target 0.65) + win_rate=63.9% (target 60%)",
  "timestamp": "2026-02-25T23:55:00Z"
}
```

---

## 🧪 UNIT TEST TEMPLATES (7 - TASK #3)

```python
# File: tests/unit/test_task3_ml002_backtest_validation.py

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from src.application.ml_classifier import BacktestValidator

@pytest.fixture
def training_data():
    """Load training_dataset.csv for validation."""
    df = pd.read_csv('training_dataset.csv')
    X = df.drop(['window_id', 'label'], axis=1).values
    y = df['label'].values
    return X, y

# TEST 1: Grid Search Execution
def test_grid_search_execution(training_data):
    """Should execute grid search for all 8 thresholds."""
    X, y = training_data
    validator = BacktestValidator(X, y)

    results = validator.grid_search(thresholds=[1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5])

    assert len(results) == 8
    assert all(t in results for t in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5])

# TEST 2: Metrics Calculation
def test_metrics_calculation(training_data):
    """Should calculate F1, Precision, Recall, Win Rate."""
    X, y = training_data
    validator = BacktestValidator(X, y)

    metrics = validator.calculate_metrics(y_true=y, y_pred=y)

    assert 'f1' in metrics
    assert 'precision' in metrics
    assert 'recall' in metrics
    assert 'win_rate' in metrics
    assert 0 <= metrics['f1'] <= 1

# TEST 3: F1 > 0.65 Validation
def test_f1_threshold_validation(training_data):
    """Should have at least one threshold with F1 >= 0.65."""
    X, y = training_data
    validator = BacktestValidator(X, y)

    results = validator.grid_search(thresholds=[1.0, 1.5, 2.0, 2.5, 3.0])

    max_f1 = max(r['f1'] for r in results.values())
    assert max_f1 >= 0.65, f"Max F1={max_f1} < 0.65 target"

# TEST 4: Win Rate >= 60% Validation
def test_win_rate_validation(training_data):
    """Should have at least one threshold with win_rate >= 60%."""
    X, y = training_data
    validator = BacktestValidator(X, y)

    results = validator.grid_search(thresholds=[1.0, 1.5, 2.0, 2.5, 3.0])

    max_wr = max(r.get('win_rate', 0) for r in results.values())
    assert max_wr >= 0.60, f"Max win_rate={max_wr} < 0.60 target"

# TEST 5: Optimal Threshold Selection
def test_optimal_threshold_selection(training_data):
    """Should select best threshold by F1."""
    X, y = training_data
    validator = BacktestValidator(X, y)

    results = validator.grid_search(thresholds=[1.0, 1.5, 2.0, 2.5, 3.0])
    optimal = validator.select_optimal_threshold(results)

    assert optimal in [1.0, 1.5, 2.0, 2.5, 3.0]
    assert results[optimal]['f1'] == max(r['f1'] for r in results.values())

# TEST 6: Report Generation
def test_report_generation(training_data, tmp_path):
    """Should generate backtest_final_metrics.json."""
    X, y = training_data
    validator = BacktestValidator(X, y)

    results = validator.grid_search(thresholds=[1.0, 1.5, 2.0])
    report_path = tmp_path / "backtest_final_metrics.json"

    validator.save_report(results, str(report_path))

    assert report_path.exists()
    import json
    with open(report_path) as f:
        report = json.load(f)
    assert 'grid_search_results' in report
    assert 'optimal_threshold' in report

# TEST 7: Coverage >90%
def test_full_pipeline(training_data):
    """Full pipeline integration test."""
    X, y = training_data
    validator = BacktestValidator(X, y)

    # Run full grid search
    results = validator.grid_search(thresholds=[1.0, 1.5, 2.0, 2.5, 3.0])
    optimal = validator.select_optimal_threshold(results)

    # Verify structure
    assert len(results) == 5
    assert isinstance(optimal, float)
    assert all('f1' in r for r in results.values())
```

---

## 📋 IMPLEMENTATION STEPS (Passo-a-Passo)

### Step 1: Preparar Dados (15 min)

```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# Carregar dados
df = pd.read_csv('training_dataset.csv')

# Separar features e labels
X = df.drop(['window_id', 'label'], axis=1).values.astype(np.float32)
y = df['label'].values.astype(np.int32)

print(f"✅ Data loaded: X shape={X.shape}, y shape={y.shape}")
print(f"   Label distribution: {(y==1).sum()} BUY, {(y==0).sum()} SKIP")

#Split data
X_train, X_rest, y_train, y_rest = train_test_split(X, y, test_size=0.30, random_state=42)
X_val, X_test, y_val, y_test = train_test_split(X_rest, y_rest, test_size=0.5, random_state=42)

print(f"✅ Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")
```

### Step 2: Implementar Grid Search (120 min)

```python
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score
from xgboost import XGBClassifier
import json
from datetime import datetime

class BacktestValidator:
    def __init__(self, X, y):
        self.X = X
        self.y = y

    def grid_search(self, thresholds=[1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]):
        results = {}

        for threshold in thresholds:
            print(f"Testing threshold {threshold}...")

            # Train model with this threshold
            model = XGBClassifier(max_depth=5, learning_rate=0.1, n_estimators=100)

            X_train, X_val, y_train, y_val = train_test_split(
                self.X, self.y, test_size=0.30, random_state=42
            )
            X_val2, X_test, y_val2, y_test = train_test_split(
                X_val, y_val, test_size=0.5, random_state=42
            )

            model.fit(X_train, y_train)

            # Evaluate
            y_pred_val = model.predict(X_val2)
            y_pred_test = model.predict(X_test)

            metrics_val = {
                'f1': float(f1_score(y_val2, y_pred_val)),
                'precision': float(precision_score(y_val2, y_pred_val)),
                'recall': float(recall_score(y_val2, y_pred_val)),
                'accuracy': float(accuracy_score(y_val2, y_pred_val))
            }

            metrics_test = {
                'f1': float(f1_score(y_test, y_pred_test)),
                'win_rate': float((y_pred_test == y_test).sum() / len(y_test))
            }

            results[threshold] = {
                'metrics_val': metrics_val,
                'metrics_test': metrics_test
            }

        return results

    def select_optimal_threshold(self, results):
        return max(results.keys(), key=lambda t: results[t]['metrics_val']['f1'])

    def save_report(self, results, output_path='backtest_final_metrics.json'):
        optimal_threshold = self.select_optimal_threshold(results)

        report = {
            'grid_search_results': results,
            'optimal_threshold': optimal_threshold,
            'optimal_metrics': results[optimal_threshold],
            'timestamp': datetime.now().isoformat()
        }

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"✅ Report saved to {output_path}")
```

### Step 3: Run & Validate (30 min)

```bash
# Execute grid search
python -c "
import pandas as pd
from src.application.ml_classifier import BacktestValidator

df = pd.read_csv('training_dataset.csv')
X = df.drop(['window_id', 'label'], axis=1).values
y = df['label'].values

validator = BacktestValidator(X, y)
results = validator.grid_search()
validator.save_report(results)

# Display results
import json
with open('backtest_final_metrics.json') as f:
    report = json.load(f)

optimal = report['optimal_threshold']
f1 = report['optimal_metrics']['metrics_val']['f1']
wr = report['optimal_metrics']['metrics_test']['win_rate']

print(f'✅ Optimal threshold: {optimal}')
print(f'   F1 Score: {f1:.4f} (target: >=0.65)')
print(f'   Win Rate: {wr:.1%} (target: >=60%)')
print(f'   Decision: GO' if f1 >= 0.65 and wr >= 0.60 else '   Decision: NO-GO')
"

# Execute testes
python -m pytest tests/unit/test_task3_ml002_backtest_validation.py -v --cov
```

---

## 📊 Success Criteria (Validação Final)

```
✅ AC-1: Grid search com 8 thresholds executado
✅ AC-2: Métricas calculadas (F1, Precision, Recall, Win Rate)
✅ AC-3: F1 >= 0.65 validado ← CRÍTICO
✅ AC-4: Win Rate >= 60% comprovado ← CRÍTICO
✅ AC-5: Threshold ótimo identificado
✅ AC-6: backtest_final_metrics.json persistido
✅ AC-7: Unit tests >90% coverage

Phase 2 Decision: GO ou NO-GO baseado em AC-3 + AC-4
```

---

**Responsável:** ML Expert (ID 2)
**QA:** Quality (ID 12)
**Timeline:** ~2-3 horas
**Status:** ⏳ PRONTA PARA COMEÇAR
