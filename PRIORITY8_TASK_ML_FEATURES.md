# 🚀 PRIORITY 8: ATI-5 ML Feature Pipeline + Baseline Model

**Owner:** ML Expert + Data Scientist
**Assigned:** ML Expert to lead
**Status:** ACTIVE - IN EXECUTION
**Start Time:** 2026-02-27 00:00:00Z
**Estimated Duration:** 8-10 hours (parallel with PRIORITY 4+5)
**Target Completion:** When 8/8 AC tests passing + F1 > 0.65 + SHAP analysis complete

---

## 📋 TASK SHEET

### Subtask 8.1: Dataset Loading + Preprocessing
**Duration:** 2 hours
**Dependencies:** None

```python
# Location: src/ml/feature_pipeline_ati5.py
# Todo:
  [ ] Load backtest CSV dataset (1000+ samples)
  [ ] Validate shape + missing values
  [ ] Create labels: 1 (good trade) / 0 (bad trade)
  [ ] Time-based train/val/test split (70/15/15)
  [ ] Calculate dataset statistics (mean, std, skew)
  [ ] Save feature metadata (feature_names.pkl)
```

**Acceptance Criteria:**
- [ ] Dataset loaded without errors
- [ ] Missing values handled (<5%)
- [ ] Labels validated (class distribution checked)

**Test File:** tests/unit/test_ati5_ml_features.py
- [ ] test_dataset_loading()
- [ ] test_data_split_proportions()
- [ ] test_label_distribution()

---

### Subtask 8.2: Feature Engineering (24 Features)
**Duration:** 3 hours
**Dependencies:** 8.1 complete

```python
# Required Groups:
# Group 1: Volatility (4 features)
  [ ] Bollinger Bands (upper/lower/pct_b)
  [ ] ATR (Average True Range)
  [ ] Historical Volatility (20-period)
  [ ] 3-Sigma bands

# Group 2: Momentum (4 features)
  [ ] RSI (14-period)
  [ ] MACD (signal difference)
  [ ] Rate of Change (ROC)
  [ ] On Balance Volume (OBV)

# Group 3: Moving Averages (5 features)
  [ ] SMA 50
  [ ] EMA 9
  [ ] EMA 21
  [ ] Slope SMA 50
  [ ] Slope EMA 9

# Group 4: Patterns (3 features)
  [ ] Mean Reversion Score
  [ ] Volume Spike Detector
  [ ] Impulse Pattern

# Group 5: Lags (9 features)
  [ ] Return[1,2,3]
  [ ] Close/Volume[1,2,3]
  [ ] Close Change

# Group 6: Correlation (2 features)
  [ ] 20-period correlation
  [ ] Trend Strength (ADX)
```

**Acceptance Criteria:**
- [ ] AC-1: All 24 features extracted
- [ ] AC-2: No NaN values (forward fill allowed)
- [ ] AC-3: Feature names saved + persistent

**Tests:**
- [ ] test_bollinger_bands_calculation()
- [ ] test_rsi_values_range()
- [ ] test_all_24_features_created()
- [ ] test_feature_names_persistence()

---

### Subtask 8.3: Feature Scaling + Data Preparation
**Duration:** 1.5 hours
**Dependencies:** 8.2 complete

```python
# Required:
  [ ] StandardScaler fit on train set ONLY
  [ ] Transform train/val/test sets
  [ ] Save scaler object (scaler.pkl)
  [ ] Verify mean≈0, std≈1 for features
  [ ] Remove outliers (3-sigma rule for extreme values)
```

**Acceptance Criteria:**
- [ ] AC-4: StandardScaler applied correctly
- [ ] Feature distributions normalized
- [ ] Outliers handled (<1% loss)

**Tests:**
- [ ] test_standardscaler_fit()
- [ ] test_normalized_distribution()
- [ ] test_outlier_removal()

---

### Subtask 8.4: XGBoost Grid Search + Training
**Duration:** 2.5 hours
**Dependencies:** 8.3 complete

```python
# Grid Search Parameters (8 configurations):
Config 1: depth=3, lr=0.1, trees=100
Config 2: depth=4, lr=0.1, trees=100
Config 3: depth=5, lr=0.1, trees=100
Config 4: depth=3, lr=0.05, trees=150
Config 5: depth=4, lr=0.05, trees=150
Config 6: depth=5, lr=0.05, trees=200
Config 7: depth=6, lr=0.1, trees=150
Config 8: depth=3, lr=0.2, trees=100

# For each config:
  [ ] 5-fold cross-validation
  [ ] Track: F1, Precision, Recall, AUROC
  [ ] Select best config (highest F1)
  [ ] Train final model on train+val
```

**Acceptance Criteria:**
- [ ] AC-5: Grid search completed (8 configs)
- [ ] AC-6: Best config selected (F1 > 0.65)
- [ ] AC-7: Final model trained

**Tests:**
- [ ] test_grid_search_execution()
- [ ] test_cross_validation_folds()
- [ ] test_model_f1_score()
- [ ] test_best_config_selection()

---

### Subtask 8.5: SHAP Analysis + Model Interpretation
**Duration:** 1 hour
**Dependencies:** 8.4 complete

```python
# Required:
  [ ] SHAP explainer (TreeExplainer for XGBoost)
  [ ] Calculate SHAP values for val set
  [ ] Feature importance ranking
  [ ] Save SHAP plot + feature importance plot
  [ ] Document top 5 most important features
```

**Acceptance Criteria:**
- [ ] AC-8: SHAP values calculated + plots saved
- [ ] Feature importance ranked
- [ ] Train backtest validation results saved

**Tests:**
- [ ] test_shap_output()
- [ ] test_feature_importance_ranking()

---

## 🎯 SUCCESS CRITERIA (All 8 AC)

```
✅ AC-1: All 24 features extracted
✅ AC-2: No NaN values (forward filled)
✅ AC-3: Feature names saved + persistent
✅ AC-4: StandardScaler applied correctly
✅ AC-5: Grid search completed (8 configs)
✅ AC-6: Best config selected (F1 > 0.65)
✅ AC-7: Final model trained
✅ AC-8: SHAP analysis complete

MUST HAVE:
✅ 8/8 AC tests PASSING
✅ F1 score > 0.65 on validation set
✅ Model AUROC > 0.70
✅ All 24 features documented
✅ 300-400 LOC production code
✅ 150+ LOC test code
✅ SHAP plots + feature importance saved
```

---

## 📊 DELIVERABLES

**Code Files:**
- [ ] `src/ml/feature_pipeline_ati5.py` (300-400 LOC)
- [ ] `tests/unit/test_ati5_ml_features.py` (150+ LOC)

**Data Files:**
- [ ] `data/feature_importance.json` (24 features ranked)
- [ ] `models/xgboost_best_model.pkl` (trained model)
- [ ] `models/scaler.pkl` (StandardScaler)
- [ ] `data/feature_names.pkl` (serialized feature list)

**SHAP Analysis:**
- [ ] `plots/shap_summary_plot.png`
- [ ] `plots/shap_dependence.png`
- [ ] `reports/ML_ANALYSIS_REPORT.md` (findings)

**PR When Done:**
- [ ] All 8 AC tests PASSING
- [ ] F1 > 0.65 verified
- [ ] SHAP analysis documented
- [ ] Ready to merge to feature/ATI-5-ml-features

---

## ⏱️ EXECUTION TIMELINE

```
00:00 - 02:00  → Subtask 8.1 (Dataset + preprocessing)
02:00 - 05:00  → Subtask 8.2 (Feature engineering - 24 features)
05:00 - 06:30  → Subtask 8.3 (Feature scaling)
06:30 - 09:00  → Subtask 8.4 (XGBoost grid search + training)
09:00 - 10:00  → Subtask 8.5 (SHAP analysis)

Total: ~10 hours
```

---

## 📞 BLOCKERS / QUESTIONS

If you get stuck:
- Q: "Feature engineering taking too long?"
  → Use pre-built functions (talib, pandas_ta) if available
- Q: "Grid search consuming too much memory?"
  → Use partial_fit() or reduce cv folds to 3
- Q: "F1 score not reaching 0.65?"
  → Review feature quality, try feature selection
- Q: "SHAP analysis slow?"
  → Use sample_explainer() on 1000 samples

**Escalate to ML Expert Lead if:** Blocker > 45 min

---

## ✅ NEXT STEP

**Type when complete:**
```
"PRIORITY 8 DONE: ML pipeline ready + 8/8 AC tests passing + F1 > 0.65 + SHAP analysis complete"
```

Then: Ready for PRIORITY 9 (Drift Detection) - which depends on this

---

**Status:** 🟢 **ACTIVE**
**Owner:** ML Expert + Data Scientist
**Next Review:** After Subtask 8.2 (5h 00m)
