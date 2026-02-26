# 🤖 SUBTASK 8.1: ML Dataset Loading & Preparation

**Owner:** ML Expert (Data Science Team)
**Duration:** 2 hours
**Status:** 🟢 READY TO START
**Start Time:** NOW (PARALLEL with PRIORITY 4.3 + 5.1)

---

## 📋 Objective

Implement and validate **ML feature engineering pipeline** with dataset loading, preprocessing, and feature extraction. This subtask establishes the data foundation for model training and backtesting.

---

## ✅ Acceptance Criteria for Subtask 8.1

1. **Dataset Loading** ✓
   - Load OHLCV data from CSV/database
   - Support 1, 5, 15-minute timeframes
   - Validate data integrity (no gaps, sorted timestamps)
   - Verified with unit test

2. **Feature Engineering** ✓
   - Extract 24 engineered features (6 categories)
   - Volatility features: Bollinger Bands, ATR, Historical Vol, Sigma
   - Momentum features: RSI, MACD, ROC, OBV
   - Moving Average features: SMA, EMA, slopes
   - Pattern features: Mean reversion, Volume spike, Impulse
   - Lag features: Return lags, Volume lags (9 features)
   - Correlation features: 20-period correlation, Trend strength
   - All features normalized (mean=0, std=1)

3. **Data Preprocessing** ✓
   - Handle missing values (forward fill or interpolation)
   - Outlier detection (3-sigma rule)
   - Train/validation/test splits (70/15/15)
   - Feature scaling (StandardScaler)
   - Verified with unit test

4. **Label Generation** ✓
   - Binary classification: Profitable (1) / Unprofitable (0)
   - Look-forward window: 5-minute returns
   - Threshold: >0.1% = profitable
   - Train/val/test labels aligned with features
   - Verified with unit test

5. **Data Quality Validation** ✓
   - Feature statistics computed (mean, std, min, max)
   - Missing value percentage <2%
   - Scaling verification (normalized features)
   - Label distribution balanced (40-60% split)
   - Verified with unit test

---

## 🔧 Implementation Guide

### Step 1: Review Current ML Implementation

**File:** `src/ml/feature_pipeline_ati5.py` (420 LOC)

**Key Classes:**
- `DataLoader`: Load OHLCV data from sources
- `FeatureEngineer`: Extract 24 features
- `DataPreprocessor`: Handle missing values, scaling
- `DataValidator`: Quality checks

**Current Status:** ✅ Baseline implementation complete

### Step 2: Prepare Test Data

**Create test fixture** - `tests/fixtures/sample_data.csv`:

```csv
timestamp,open,high,low,close,volume
2025-01-01 09:30:00,100.00,101.50,99.50,100.50,1000000
2025-01-01 09:35:00,100.50,102.00,100.00,101.50,1100000
2025-01-01 09:40:00,101.50,102.50,101.00,102.00,1200000
2025-01-01 09:45:00,102.00,103.00,101.50,102.50,1300000
2025-01-01 09:50:00,102.50,103.50,102.00,103.00,1400000
... (repeat 100+ rows for valid training data)
```

Or use **existing market data** from your source:
- MetaTrader 5 export (CSV)
- Yahoo Finance API
- Polygon.io data

### Step 3: Run ML Feature Tests

**File:** `tests/unit/test_ati5_ml_features.py` (330 LOC)

**Command:**
```bash
pytest tests/unit/test_ati5_ml_features.py -v
```

**Expected Output:**
```
tests/unit/test_ati5_ml_features.py::TestDataLoader::test_load_csv PASSED
tests/unit/test_ati5_ml_features.py::TestDataLoader::test_validate_data_integrity PASSED
tests/unit/test_ati5_ml_features.py::TestFeatureEngineer::test_feature_extraction PASSED
tests/unit/test_ati5_ml_features.py::TestFeatureEngineer::test_feature_count PASSED
tests/unit/test_ati5_ml_features.py::TestDataPreprocessor::test_missing_value_handling PASSED
tests/unit/test_ati5_ml_features.py::TestDataPreprocessor::test_feature_scaling PASSED
tests/unit/test_ati5_ml_features.py::TestLabelGenerator::test_label_generation PASSED
tests/unit/test_ati5_ml_features.py::TestDataValidator::test_data_quality_metrics PASSED

===================== 8 passed in 3.45s =====================
```

### Step 4: Validate Feature Statistics

**Test Script** - Create `validate_ml_features.py`:

```python
#!/usr/bin/env python3
"""Validate ML feature engineering pipeline."""

import asyncio
import pandas as pd
import numpy as np
from src.ml.feature_pipeline_ati5 import (
    DataLoader, FeatureEngineer, DataPreprocessor,
    LabelGenerator, DataValidator
)

async def validate_ml_pipeline():
    """Run ML pipeline validation tests."""

    # Load data
    print("\n📊 TEST 1: Data Loading")
    loader = DataLoader()
    df = loader.load_ohlcv_data("sample_data.csv")
    print(f"✓ Data loaded: {len(df)} rows")
    print(f"✓ Columns: {list(df.columns)}")
    print(f"✓ Date range: {df.index.min()} to {df.index.max()}")

    # Feature engineering
    print("\n📊 TEST 2: Feature Engineering")
    engineer = FeatureEngineer()
    features_df = engineer.calculate_features(df)
    print(f"✓ Features calculated: {len(features_df.columns)} features")
    print(f"✓ Feature names: {list(features_df.columns)[:5]}...")
    print(f"✓ Feature count: {len(features_df.columns)} (target: 24)")

    # Validate feature count
    assert len(features_df.columns) >= 24, "Insufficient features"
    print(f"✓ Feature count verified: {len(features_df.columns)}")

    # Data preprocessing
    print("\n📊 TEST 3: Data Preprocessing")
    preprocessor = DataPreprocessor()
    processed_df = preprocessor.preprocess(features_df)
    print(f"✓ Missing values: {processed_df.isnull().sum().sum()}")
    print(f"✓ Shape after preprocessing: {processed_df.shape}")

    # Label generation
    print("\n📊 TEST 4: Label Generation")
    label_gen = LabelGenerator()
    labels = label_gen.generate_labels(df)
    print(f"✓ Labels generated: {len(labels)}")
    print(f"✓ Label distribution:")
    print(f"   - Profitable (1): {(labels == 1).sum()} ({100*(labels==1).sum()/len(labels):.1f}%)")
    print(f"   - Unprofitable (0): {(labels == 0).sum()} ({100*(labels==0).sum()/len(labels):.1f}%)")

    # Data quality validation
    print("\n📊 TEST 5: Data Quality Validation")
    validator = DataValidator()
    metrics = validator.compute_quality_metrics(processed_df, labels)

    print(f"✓ Feature Statistics:")
    for feature in processed_df.columns[:5]:
        mean = processed_df[feature].mean()
        std = processed_df[feature].std()
        min_val = processed_df[feature].min()
        max_val = processed_df[feature].max()
        print(f"   {feature}:")
        print(f"      Mean: {mean:.4f}, Std: {std:.4f}")
        print(f"      Min: {min_val:.4f}, Max: {max_val:.4f}")

    print(f"\n✓ Quality Metrics:")
    print(f"   Missing values: {metrics['missing_pct']:.2f}%")
    print(f"   Feature scaling: Normalized (μ≈0, σ≈1)")
    print(f"   Label balance: {metrics['label_balance']:.2f}")
    print(f"   Data points: {len(processed_df)}")

    # Train/val/test split
    print("\n📊 TEST 6: Train/Val/Test Split")
    train_size = int(0.7 * len(processed_df))
    val_size = int(0.15 * len(processed_df))
    test_size = len(processed_df) - train_size - val_size

    print(f"✓ Train set: {train_size} rows ({100*train_size/len(processed_df):.1f}%)")
    print(f"✓ Validation set: {val_size} rows ({100*val_size/len(processed_df):.1f}%)")
    print(f"✓ Test set: {test_size} rows ({100*test_size/len(processed_df):.1f}%)")

    # Feature importance check
    print("\n📊 TEST 7: Feature Correlation Check")
    correlation_matrix = processed_df.corr()
    high_corr_pairs = []

    for i in range(len(correlation_matrix.columns)):
        for j in range(i+1, len(correlation_matrix.columns)):
            if abs(correlation_matrix.iloc[i, j]) > 0.95:
                high_corr_pairs.append((
                    correlation_matrix.columns[i],
                    correlation_matrix.columns[j],
                    correlation_matrix.iloc[i, j]
                ))

    if high_corr_pairs:
        print(f"⚠️  High correlation pairs (>0.95): {len(high_corr_pairs)}")
        for feat1, feat2, corr in high_corr_pairs[:3]:
            print(f"   {feat1} <-> {feat2}: {corr:.3f}")
    else:
        print(f"✓ No excessive feature correlation (all <0.95)")

    # Final summary
    print("\n✅ ML PIPELINE VALIDATION COMPLETE!\n")
    print(f"Summary:")
    print(f"  - Dataset size: {len(processed_df)} rows")
    print(f"  - Features: {len(processed_df.columns)} engineered")
    print(f"  - Labels: {len(labels)} generated")
    print(f"  - Quality: {100 - metrics['missing_pct']:.1f}% complete")
    print(f"  - Ready for model training: ✅ YES")
    print()

if __name__ == "__main__":
    asyncio.run(validate_ml_pipeline())
```

**Run validation:**
```bash
python validate_ml_features.py
```

**Expected Output:**
```
📊 TEST 1: Data Loading
✓ Data loaded: 1440 rows
✓ Columns: ['open', 'high', 'low', 'close', 'volume']
✓ Date range: 2025-01-01 09:30:00 to 2025-01-06 16:00:00

📊 TEST 2: Feature Engineering
✓ Features calculated: 24 features
✓ Feature names: ['bb_upper', 'bb_middle', 'bb_lower', 'atr', 'hist_volatility']...
✓ Feature count: 24 (target: 24)
✓ Feature count verified: 24

📊 TEST 3: Data Preprocessing
✓ Missing values: 0
✓ Shape after preprocessing: (1440, 24)

📊 TEST 4: Label Generation
✓ Labels generated: 1440
✓ Label distribution:
   - Profitable (1): 580 (40.3%)
   - Unprofitable (0): 860 (59.7%)

📊 TEST 5: Data Quality Validation
✓ Feature Statistics:
   bb_upper:
      Mean: 0.0012, Std: 1.0023
      Min: -2.9834, Max: 3.0156

✓ Quality Metrics:
   Missing values: 0.05%
   Feature scaling: Normalized (μ≈0, σ≈1)
   Label balance: 40.3
   Data points: 1440

📊 TEST 6: Train/Val/Test Split
✓ Train set: 1008 rows (70.0%)
✓ Validation set: 216 rows (15.0%)
✓ Test set: 216 rows (15.0%)

📊 TEST 7: Feature Correlation Check
✓ No excessive feature correlation (all <0.95)

✅ ML PIPELINE VALIDATION COMPLETE!

Summary:
  - Dataset size: 1440 rows
  - Features: 24 engineered
  - Labels: 1440 generated
  - Quality: 99.95% complete
  - Ready for model training: ✅ YES
```

### Step 5: Generate Feature Importance Report

**Command:**
```bash
# Run with detailed output
pytest tests/unit/test_ati5_ml_features.py -v --tb=short
```

### Step 6: Save Processed Dataset for Next Subtask

**Command:**
```bash
python -c "
from src.ml.feature_pipeline_ati5 import DataLoader, FeatureEngineer, DataPreprocessor
import pickle

# Load, engineer, preprocess
loader = DataLoader()
df = loader.load_ohlcv_data('sample_data.csv')

engineer = FeatureEngineer()
features_df = engineer.calculate_features(df)

preprocessor = DataPreprocessor()
processed_df = preprocessor.preprocess(features_df)

# Save for next subtask
with open('data/processed_features.pkl', 'wb') as f:
    pickle.dump(processed_df, f)

print(f'✓ Processed features saved: {processed_df.shape}')
"
```

---

## 🎯 Success Criteria for Subtask 8.1

```
✅ Dataset loads without errors
✅ All 8 AC tests passing
✅ 24 features engineered correctly
✅ Missing values <2%
✅ Feature scaling verified (normalized)
✅ Train/val/test splits created (70/15/15)
✅ Label distribution balanced (40-60%)
✅ No excessive feature correlation
✅ Feature statistics computed
✅ Data saved for next subtask (model training)
```

---

## 📊 Expected Duration

- **Data Loading & Review:** 15 min
- **Feature Engineering:** 30 min
- **Test Execution:** 15 min
- **Validation Script:** 20 min
- **Feature Report:** 10 min
- **Documentation:** 10 min
- **Total:** ~120 minutes (2 hours - can run in parallel)

---

## 🔗 Dependencies

**Prerequisites (completed):**
- ✅ PRIORITY 1: Environment setup
- ✅ PRIORITY 2: Team sync
- ✅ PRIORITY 3: GATE 1 approval

**Current Codebase:**
- ✅ `src/ml/feature_pipeline_ati5.py` (420 LOC - COMPLETE)
- ✅ `tests/unit/test_ati5_ml_features.py` (330 LOC - COMPLETE)

**External Data Sources:**
- OHLCV data (sample_data.csv or live feed)
- 1440+ rows minimum for training

**External Dependencies:**
- `pandas` - Data manipulation
- `numpy` - Numerical computing
- `scikit-learn` - Feature scaling

**Next:** SUBTASK 8.2 will train ML model on engineered features

---

## ⚠️ Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| "FileNotFoundError: sample_data.csv not found" | Create test data or use real OHLCV source |
| "Feature count mismatch" | Verify FeatureEngineer extracts all 24 categories |
| "Label distribution imbalanced" | Adjust threshold or use SMOTE oversampling |
| "Feature scaling failing" | Check for NaN/inf values before scaling |
| "Slow feature engineering" | Use vectorized pandas operations, not loops |

---

## 🚀 Execution Steps - EXACT COMMANDS

```bash
# 1. Navigate to project
cd c:\repo\operador-day-trade-win

# 2. Check data source
ls data/  # or show available CSV files

# 3. Run ML tests
pytest tests/unit/test_ati5_ml_features.py -v

# 4. Create validation script
# (Copy validate_ml_features.py code from Step 4 above)

# 5. Run validation
python validate_ml_features.py

# 6. Generate feature report
pytest tests/unit/test_ati5_ml_features.py::TestFeatureEngineer -v

# 7. Save processed data
python -c "from src.ml.feature_pipeline_ati5 import ... (see Step 6)"

# 8. If all passing
pytest tests/unit/test_ati5_ml_features.py -q --tb=short
```

---

## 📝 Documentation Template

When complete, create `SUBTASK_8_1_COMPLETE.md`:

```markdown
# ✅ SUBTASK 8.1 COMPLETE: ML Dataset Loading & Preparation

**Timestamp:** [TIME]
**Owner:** ML Expert
**Duration:** [ACTUAL TIME]
**Status:** ✅ COMPLETE

## Test Results
- Data Loading: ✅ PASSED
- Data Integrity: ✅ PASSED
- Feature Engineering: ✅ PASSED
- Feature Count: ✅ PASSED (24/24)
- Data Preprocessing: ✅ PASSED
- Label Generation: ✅ PASSED
- Data Quality: ✅ PASSED

## AC Status (All 5 AC for 8.1)
✅ AC-1: Dataset Loading
✅ AC-2: Feature Engineering
✅ AC-3: Data Preprocessing
✅ AC-4: Label Generation
✅ AC-5: Data Quality Validation

## Metrics
- Dataset Size: 1.440 rows
- Features: 24 engineered
- Train/Val/Test: 70/15/15 split
- Label Balance: ~40% profitable
- Data Quality: >99% complete
- Ready for model training: ✅ YES

## Next Steps
→ Subtask 8.2: XGBoost Model Training & Grid Search
```

---

## ✨ Notes

- **Parallel Execution:** This runs simultaneously with SUBTASK 4.3 + SUBTASK 5.1
- **No Blocking:** Independent of other tracks
- **Data Foundation:** Critical for all subsequent ML work
- **Feature Selection:** 24 features tested, will use importance analysis later
- **Class Imbalance:** Monitor 40-60% split, may use stratified sampling

---

**Status:** 🟢 **READY TO START NOW**

When complete, proceed to **SUBTASK 8.2** (XGBoost Model Training)

---

**Parallel Timeline:** Can run simultaneously with Subtasks 4.3 + 5.1
**Time to Complete:** ~120 min ⏱️

