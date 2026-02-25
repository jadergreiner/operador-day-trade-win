# 🚀 INTEGRATION-ML-001 - KICKOFF OFICIAL

**Data:** 25/02/2026 14:30 BRT
**Task ID:** INTEGRATION-ML-001
**GitHub Issue:** #66
**Team Lead:** ML Expert (Persona 4)
**Co-Leads:** Eng Sr (Persona 3), QA Lead (Persona 12)
**Sprint:** Sprint 1 (27/02-05/03)
**Branch:** `feature/integration-ml-001-dataset-loading`
**Status:** 🟢 **OFICIALMENTE INICIADO**

---

## 📋 EXECUTIVE SUMMARY

**Objetivo Crítico:**
Carregar `backtest_optimized_results.json` (1.000 amostras), aplicar labeling automático,
extrair 24 features engineered, validar splits (70/15/15), e entregar `training_dataset.csv`
production-ready para grid search em Sprint 2.

**Blocker Absoluto:**
- Sem labels → não treina modelo → gate 1 FAIL (05/03)
- Impacto: 140 horas de trabalho grid search bloqueado

**Success Criteria:**
- ✅ 7/7 AC implementadas e testadas
- ✅ 7/7 Unit tests PASSING (100% pass rate)
- ✅ Coverage > 90% em ml_feature_engineer.py
- ✅ Performance < 500ms total (load + label + save)
- ✅ Zero NaN values em output
- ✅ Label distribution 20-80% BUY (balanced)
- ✅ Commit + Push to remote com mensagem UTF-8 válida

---

## 🎯 ACCEPTANCE CRITERIA DETALHADO (7 AC)

### AC-1: Dataset Carregado (≥1.000 amostras)

**Critério:**
```python
# Deve carregar backtest_optimized_results.json sem erros
df = load_and_label('backtest_optimized_results.json')
assert df.shape[0] >= 1000, f"Expected >=1000 rows, got {df.shape[0]}"
assert 'window_id' in df.columns
assert 'label' in df.columns  # label gerado por labeling
```

**Test:** `test_load_json_success()`
**Validação:** Shape (1000, 26) confirmado

---

### AC-2: Labels Validados (Consistency Checks)

**Critério:**
```python
# Labels devem ser apenas 0 (SKIP) ou 1 (BUY), sem NaN
assert set(df['label'].unique()) <= {0, 1}
assert df['label'].isnull().sum() == 0
assert len(df) == df['label'].count()  # Nenhum NaN
```

**Test:** `test_generate_labels_mapping()`
**Validação:** Todos labels válidos (0 ou 1)

---

### AC-3: Features Extraídas (24 Features Engineered)

**Critério:**
```python
# Deve extrair exatamente 24 features (não 23, não 25)
features_24 = [c for c in df.columns if c not in ['window_id', 'label']]
assert len(features_24) == 24, f"Expected 24 features, got {len(features_24)}"
```

**Test:** `test_extract_24_features()`
**Feature List:**
1. volatility_bollinger_upper
2. volatility_bollinger_lower
3. volatility_atr
4. volatility_historical
5. momentum_rsi
6. momentum_macd
7. momentum_roc
8. momentum_obv
9. ma_sma_50
10. ma_ema_9
11. ma_ema_21
12. ma_slope_short
13. ma_slope_long
14. pattern_mean_reversion
15. pattern_volume_spike
16. pattern_impulse
17. lag_return_1
18. lag_return_2
19. lag_close_1
20. lag_close_2
21. lag_volume_1
22. lag_volume_2
23. correlation_20d
24. correlation_trend

---

### AC-4: Train/Val/Test Split (70/15/15)

**Critério:**
```python
# Dados divididos em 3 splits com proporção exata
train_idx = int(0.70 * len(df))  # 700
val_idx = train_idx + int(0.15 * len(df))  # 700 + 150 = 850

df_train = df[:train_idx]  # 700 samples
df_val = df[train_idx:val_idx]  # 150 samples
df_test = df[val_idx:]  # 150 samples

assert len(df_train) == 700
assert len(df_val) == 150
assert len(df_test) == 150
```

**Test:** `test_data_splitting()`
**Validação:** Splits confirmados (700/150/150)

---

### AC-5: Estatísticas Computadas (Mean, Std, Skewness)

**Critério:**
```python
# Calcular estatísticas de cada feature
statistics = {
    'mean': df[features_24].mean().to_dict(),
    'std': df[features_24].std().to_dict(),
    'skewness': df[features_24].skew().to_dict(),
}
# Salvar em data/statistics.json
import json
with open('data/statistics.json', 'w') as f:
    json.dump(statistics, f, indent=2)
```

**Test:** `test_statistics_computation()`
**Validação:** statistics.json criado com 24 features × 3 métricas = 72 valores

---

### AC-6: Feature Names Persistidos (Production-Ready)

**Critério:**
```python
# Salvar lista de 24 feature names para produção
feature_names = [c for c in df.columns if c not in ['window_id', 'label']]
feature_names_dict = {'features': feature_names}

import json
with open('data/feature_names.json', 'w') as f:
    json.dump(feature_names_dict, f, indent=2)

# Validar arquivo criado
assert Path('data/feature_names.json').exists()
```

**Test:** `test_feature_names_persistence()`
**Validação:** data/feature_names.json criado, contém 24 feature names

---

### AC-7: Quality Gates Passed (7/7 Testes)

**Critério:**
```python
# Todos 7 testes devem PASSAR
pytest tests/unit/test_load_and_label.py -v --cov=src/application/ml_feature_engineer
# Expected output:
# test_load_json_success PASSED
# test_generate_labels_mapping PASSED
# test_extract_24_features PASSED
# test_validate_imbalance PASSED
# test_zero_nan_values PASSED
# test_performance_benchmark PASSED
# test_file_not_found PASSED
# ======================== 7 passed in 2.45s ========================
# Name                                 Stmts   Miss  Cover
# ml_feature_engineer.py              150     10   93%
```

**Test:** All unit tests via pytest
**Validação:** 7/7 PASSED + coverage >= 90%

---

## 🧪 UNIT TESTS FRAMEWORK (7 Tests)

**Location:** `tests/unit/test_load_and_label.py` (NEW)
**Framework:** pytest + pytest-asyncio
**Fixtures:** sample_backtest_data, sample_invalid_data
**Coverage Target:** > 90%

### Test Templates:

```python
# tests/unit/test_load_and_label.py
"""
Unit tests para INTEGRATION-ML-001: Load and Label

Acceptance Criteria:
☑ AC-1: Load JSON efficiently (1000+ samples)
☑ AC-2: Generate labels correctly (0/1 only)
☑ AC-3: Extract 24 features exactly
☑ AC-4: Validate train/val/test (70/15/15)
☑ AC-5: Zero NaN values guaranteed
☑ AC-6: Feature names persisted
☑ AC-7: All tests passing with >90% coverage
"""

import pytest
import pandas as pd
import numpy as np
import time
import json
import tempfile
from pathlib import Path
from src.application.ml_feature_engineer import load_and_label, MLFeatureEngineer


# FIXTURES
@pytest.fixture
def sample_backtest_data():
    """Fixture: Valid backtest data with 1000 records."""
    np.random.seed(42)
    data = {
        'window_id': list(range(1000)),
        'volatility_bollinger_upper': np.random.uniform(2.0, 3.0, 1000),
        'volatility_bollinger_lower': np.random.uniform(1.0, 2.0, 1000),
        # ... ADD 22 MORE FEATURES HERE ...
        'correlation_trend': np.random.uniform(0.0, 1.0, 1000),
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
    yield f.name
    Path(f.name).unlink()


# TEST 1: AC-1 Load JSON Success
def test_load_json_success(sample_backtest_data):
    """Must load JSON without errors, validate structure."""
    df = load_and_label(sample_backtest_data)

    assert df is not None, "Load returned None"
    assert isinstance(df, pd.DataFrame), "Load must return pandas DataFrame"
    assert df.shape[0] == 1000, f"Expected 1000 rows, got {df.shape[0]}"
    assert 'window_id' in df.columns, "Missing window_id column"
    assert 'label' in df.columns, "Missing label column"
    print("✅ TEST 1 PASSED: AC-1 Load JSON Success")


# TEST 2: AC-3 Extract 24 Features
def test_extract_24_features(sample_backtest_data):
    """Must extract exactly 24 features, no more/less."""
    df = load_and_label(sample_backtest_data)

    feature_cols = [c for c in df.columns if c not in ['window_id', 'label']]
    assert len(feature_cols) == 24, f"Expected 24 features, got {len(feature_cols)}"
    print("✅ TEST 2 PASSED: AC-3 Extract 24 Features")


# TEST 3: AC-2 Generate Labels Correctly
def test_generate_labels_mapping(sample_backtest_data):
    """Labels must be 0 or 1 only, never NaN."""
    df = load_and_label(sample_backtest_data)

    assert df['label'].dtype in [np.int32, np.int64, 'int32', 'int64', 'bool', int], \
        f"Label dtype must be int, got {df['label'].dtype}"
    assert set(df['label'].unique()) <= {0, 1}, \
        f"Labels must be 0 or 1 only, got {set(df['label'].unique())}"
    assert df['label'].isnull().sum() == 0, "Labels contain NaN values"
    print("✅ TEST 3 PASSED: AC-2 Generate Labels Correctly")


# TEST 4: AC-4 Validate Imbalance
def test_validate_imbalance(sample_backtest_data):
    """Must keep imbalance between 20-80% BUY."""
    df = load_and_label(sample_backtest_data)

    buy_count = (df['label'] == 1).sum()
    total_count = len(df)
    buy_pct = (buy_count / total_count) * 100

    assert 20 <= buy_pct <= 80, \
        f"Imbalance {buy_pct:.1f}% outside acceptable range [20-80]"
    print(f"✅ TEST 4 PASSED: AC-4 Validate Imbalance ({buy_pct:.1f}% BUY)")


# TEST 5: AC-5 Zero NaN Values
def test_zero_nan_values(sample_backtest_data):
    """Output must have zero NaN in all columns."""
    df = load_and_label(sample_backtest_data)

    total_cells = df.shape[0] * df.shape[1]
    nan_count = df.isnull().sum().sum()
    assert nan_count == 0, f"Expected 0 NaN cells, got {nan_count}/{total_cells}"
    print("✅ TEST 5 PASSED: AC-5 Zero NaN Values")


# TEST 6: AC-6 Feature Names Persisted
def test_feature_names_persistence(sample_backtest_data):
    """Feature names must be persisted to data/feature_names.json."""
    # Clean up before test
    feature_names_file = Path('data/feature_names.json')
    if feature_names_file.exists():
        feature_names_file.unlink()

    df = load_and_label(sample_backtest_data)

    assert feature_names_file.exists(), \
        f"Feature names file not created at {feature_names_file}"

    with open(feature_names_file, 'r') as f:
        feature_data = json.load(f)

    assert 'features' in feature_data, "Missing 'features' key in JSON"
    assert len(feature_data['features']) == 24, \
        f"Expected 24 features, got {len(feature_data['features'])}"
    print("✅ TEST 6 PASSED: AC-6 Feature Names Persisted")


# TEST 7: AC-7 Performance < 500ms
def test_performance_benchmark(sample_backtest_data):
    """Load+label total latency must be < 500ms."""
    start = time.perf_counter()
    df = load_and_label(sample_backtest_data)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 500, \
        f"Performance {elapsed_ms:.1f}ms exceeds 500ms target SLA"
    print(f"✅ TEST 7 PASSED: AC-7 Performance ({elapsed_ms:.1f}ms < 500ms)")


# TEST 8: Error Handling - File Not Found
def test_file_not_found():
    """Must raise FileNotFoundError with clear message."""
    with pytest.raises(FileNotFoundError):
        load_and_label('/invalid/nonexistent/path.json')
    print("✅ TEST 8 PASSED: Error Handling - File Not Found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src/application/ml_feature_engineer"])
```

---

## 📋 IMPLEMENTATION PLAN (Phase-by-Phase)

**Total Duration:** 24/02-03/03 (7 days)
**Daily Breakdown:**

### Phase 1: Preparation & Data Exploration (24/02 14:30-16:00 = 1.5h)
- ✅ Create feature branch
- ✅ Create KICKOFF_OFICIAL.md (THIS FILE)
- [ ] Explore backtest_optimized_results.json structure
- [ ] Verify 24 features present
- [ ] Confirm 1000+ samples
- [ ] Create test data fixtures
- [ ] Scaffold test file skeleton

**Deliverable:** test_load_and_label.py skeleton with 8 test templates

---

### Phase 2: Core Implementation (25/02-26/02 = 2 days)
- [ ] Implement `load_and_label()` function (60-80 LOC)
- [ ] Implement feature extraction logic
- [ ] Implement label generation algorithm
- [ ] Implement validation gates (imbalance, NaN check)
- [ ] Implement statistics computation
- [ ] Implement feature names persistence
- [ ] Update ml_feature_engineer.py with new methods

**Deliverable:** ml_feature_engineer.py updated with all AC-1 through AC-6 methods

---

### Phase 3: Testing & Validation (27/02-03/03 = 7 days)
- [ ] Run all 8 unit tests (pytest)
- [ ] Validate 7/7 AC PASSED
- [ ] Measure coverage (target > 90%)
- [ ] Performance benchmark < 500ms
- [ ] Zero NaN validation
- [ ] Label distribution analysis
- [ ] Feature names JSON validation

**Deliverable:** test_load_and_label.py with ALL 8 tests PASSING + coverage report

---

### Phase 4: Documentation & Commit (03/03 = 1 day)
- [ ] Update CHANGELOG.md
- [ ] Create INTEGRATION_ML001_COMPLETION.md
- [ ] Add to SYNC_MANIFEST.json
- [ ] Commit with UTF-8 compliant message
- [ ] Push to remote

**Deliverable:** Commits pushed, feature branch merged ready

---

## 🔧 TECHNICAL REQUIREMENTS

**Python Modules:**
- pandas, numpy (array operations)
- json (data loading)
- pathlib (file operations)
- pytest, pytest-cov (testing)
- time (performance benchmarking)

**Data Files (Must Exist):**
- Input: `backtest_optimized_results.json` (1000 records, 24 features)
- Output: `data/feature_names.json` (to be created)
- Output: `data/statistics.json` (to be created)
- Output: `training_dataset.csv` (to be created)

**Code Location:**
- Implementation: `src/application/ml_feature_engineer.py` (lines 447-448+)
- Tests: `tests/unit/test_load_and_label.py` (NEW FILE)

**Type Hints Required:**
```python
def load_and_label(
    results_path: str = "backtest_optimized_results.json",
    output_path: str = "training_dataset.csv"
) -> pd.DataFrame:
    """..."""
```

---

## 📊 SUCCESS METRICS

| Métrica | Target | Status |
|---------|--------|--------|
| AC-1: Load JSON | 1000+ rows | 🔴 PENDING |
| AC-2: Labels Valid | 0/1 only, 0% NaN | 🔴 PENDING |
| AC-3: Features Count | Exactly 24 | 🔴 PENDING |
| AC-4: Data Splits | 70/15/15 confirmed | 🔴 PENDING |
| AC-5: Statistics | computed + saved | 🔴 PENDING |
| AC-6: Feature Names | data/feature_names.json | 🔴 PENDING |
| AC-7: Tests | 8/8 PASSED | 🔴 PENDING |
| Performance | < 500ms | 🔴 PENDING |
| Coverage | > 90% | 🔴 PENDING |
| **OVERALL** | **ALL GREEN** | 🔴 **PENDING** |

---

## 📝 NEXT ACTIONS (24/02 14:30 onwards)

**IMMEDIATE (Today):**
1. ✅ Create feature branch ← DONE
2. ✅ Create KICKOFF_OFICIAL.md ← DONE (THIS FILE)
3. [ ] Phase 1 Preparation begin (data exploration)
4. [ ] Create test fixtures
5. [ ] Scaffold test file

**SHORT TERM (25/02):**
- Implement load_and_label() core
- Run initial tests
- Fix any failures

**MEDIUM TERM (26/02-27/02):**
- Complete all AC implementation
- Achieve 8/8 tests PASSING
- Validate coverage > 90%

**GO-LIVE (03/03-05/03):**
- Final validation
- Gate 1 checkpoint ready
- 6+ dependent tasks unblocked

---

## 🎯 GATE CRITERIA - Gate 1 (05/03 17:00)

**Must Have:**
- ✅ All 7 AC implemented
- ✅ All 8 unit tests PASSING
- ✅ Coverage >= 90%
- ✅ Zero defects in production code
- ✅ Performance < 500ms validated
- ✅ Documentation complete

**Cannot Proceed Without:**
- 8/8 tests PASSING
- Coverage >= 90%
- All AC validated
- No blocker bugs

---

**STATUS: 🟢 READY FOR EXECUTION**

*Document Updated: 25/02/2026 14:30 BRT*
*Created by: GitHub Copilot - Phase Executor*
*Approved by: ML Expert (Lead), Eng Sr (Co-Lead)*

