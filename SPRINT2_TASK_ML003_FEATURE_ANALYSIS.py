#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SPRINT 2 - ML-003: FEATURE IMPORTANCE ANALYSIS
===============================================

Especificação técnica para análise de importância de features
Identificação de features críticas para produção monitoring

Lead: ML Expert
Duration: 5 dias (26/02 - 02/03)
Priority: P1
"""

SPEC = """
# ML-003: FEATURE IMPORTANCE ANALYSIS

**Objetivo:** Identificar features críticas, correlações e drift detection
**Owner:** ML Expert (ML Lead)
**Team:** ML Expert + Data Scientist
**Sprint:** Sprint 2 (26/02 - 02/03)
**Duration:** 5 dias (40 horas)
**Deadline:** 02/03 17:00 UTC (ready for GATE 1)

---

## 1. OVERVIEW

### Deliverables
- [ ] SHAP values analysis (top 10 features)
- [ ] Feature interaction plots
- [ ] Correlation matrix (24×24 heatmap)
- [ ] Drift detection rules
- [ ] Production monitoring config
- [ ] Detailed report (10-15 pages)

### Why This Matters
- **Production Ops:** Which features to monitor for degradation?
- **Risk Management:** Feature drift = model drift = trading losses
- **Feature Engineering:** Which features can we drop/improve?
- **Explainability:** Why does model recommend BUY/SKIP?

---

## 2. SHAP VALUES ANALYSIS

### Methodology
```
1. Train final model (from Sprint 1: scale_pos_weight=1.476)
2. Select 1000 random samples from training set
3. Calculate SHAP values using TreeSHAP (XGBoost native)
4. Summarize feature importance
5. Generate interaction plots
```

### Expected Output
```python
{
  'feature_name': [...list of 24 feature names...],
  'shap_values': [...mean |SHAP| for each feature...],
  'top_10': [
    {'feature': 'VOLATILITY_BOLLINGER_HIGH_3_SMA_20',
     'mean_shap': 0.145,
     'contribution': '14.5%'},
    ...
  ],
  'bottom_5': [
    {'feature': 'LAG_CLOSE_5_DAYS',
     'mean_shap': 0.008,
     'contribution': '0.8%'}
  ]
}
```

### Key Insights to Extract
- Which features drive BUY predictions?
- Which features drive SKIP predictions?
- Feature interactions (feature X reinforces feature Y)
- Redundant features (high correlation, low SHAP)

### Acceptance Criteria
- **AC-1:** SHAP values calculated for all 24 features
- **AC-2:** Top 10 features identified with contributions
- **AC-3:** Feature interactions documented
- **AC-4:** Bottom 5 features identified for potential pruning

---

## 3. FEATURE CORRELATION ANALYSIS

### Correlation Matrix
```
24×24 matrix showing:
- Pearson correlation coefficients
- P-values (significance)
- Feature pairs with r > 0.8 (potential redundancy)
```

### Analysis Steps
1. Load training dataset (435 samples)
2. Calculate correlation matrix
3. Identify highly correlated pairs (r > 0.8)
4. Visualize heatmap
5. Assess impact on model

### Expected Findings
- Identify feature redundancy (e.g., two moving averages)
- Cross-feature interactions
- Multicollinearity issues

### Output
```
Correlation Pairs with |r| > 0.8:
1. MOMENTUM_RSI_14 ↔ MOMENTUM_MACD: r = 0.82
2. MA_SMA_50 ↔ MA_EMA_21: r = 0.79 (close to threshold)
3. VOLATILITY_BOLLINGER_HIGH_3 ↔ VOLATILITY_ATR_14: r = 0.75

Recommendation:
- No features need removal (all contribute different signals)
- Consider normalizing feature scales in future versions
```

### Acceptance Criteria
- **AC-5:** Correlation matrix heatmap generated
- **AC-6:** High correlation pairs (r > 0.8) identified
- **AC-7:** Recommendations for feature engineering documented

---

## 4. DRIFT DETECTION STRATEGY

### What is Feature Drift?
"Sudden changes in feature distributions compared to training data"
- Example: VOLATILITY suddenly increases 50% (market shock)
- Impact: Model expects historical patterns, fails on new patterns

### Monitoring Rules

#### Rule 1: Mean Shift Detection
```
For each feature:
  - Compute rolling 30-day mean
  - Compare to training mean
  - Alert if |mean_atual - mean_treino| > 1.5 * std_treino
```
**Threshold:** > 1.5σ deviation = ALERT

#### Rule 2: Distribution Change Detection
```
For each feature:
  - Compute Kolmogorov-Smirnov (KS) test
  - Live distribution vs training distribution
  - Alert if KS statistic > 0.15
```
**Threshold:** KS > 0.15 = ALERT

#### Rule 3: Correlation Shift
```
For top 5 feature pairs:
  - Compute rolling 30-day correlation
  - Compare to training correlation
  - Alert if |corr_atual - corr_treino| > 0.20
```
**Threshold:** > 0.20 change = ALERT

### Alert Severity
```
GREEN (0 alerts):    Normal operations
YELLOW (1-2 alerts): Monitor closely, consider retraining soon
ORANGE (3-5 alerts): Recommend model review within 48h
RED (>5 alerts):     STOP trading, immediate model retraining
```

### Acceptance Criteria
- **AC-8:** Drift detection rules defined and documented
- **AC-9:** Alert thresholds calibrated
- **AC-10:** Monitoring dashboard mockup created

---

## 5. THRESHOLD SENSITIVITY ANALYSIS

### Question
"How sensitive is model performance to our threshold choice (0.30)?"

### Methodology
```
For thresholds [0.25, 0.27, 0.29, 0.30, 0.31, 0.33, 0.35]:
  - Compute F1 score
  - Compute Win Rate
  - Compute expected P&L (0.30 → +R$ 1500/day estimate)
  - Document sensitivity curve
```

### Expected Output
```
Threshold │ F1    │ Win Rate │ P&L/day │ Risk
──────────┼───────┼──────────┼─────────┼──────
0.25      │ 0.724 │ 0.558    │ +1200   │ High
0.27      │ 0.716 │ 0.564    │ +1350   │ Medium
0.29      │ 0.712 │ 0.602    │ +1480   │ Medium
0.30      │ 0.705 │ 0.604    │ +1500   │ Balanced ← OPTIMAL
0.31      │ 0.698 │ 0.608    │ +1480   │ Medium
0.35      │ 0.680 │ 0.620    │ +1400   │ Conservative
```

### Insights
- Threshold 0.30 is well-positioned
- If F1 drops, lower threshold (0.27)
- If Win Rate drops, raise threshold (0.33)

### Acceptance Criteria
- **AC-11:** Sensitivity curve generated
- **AC-12:** Optimal threshold validated
- **AC-13:** Threshold adjustment rules documented

---

## 6. PRODUCTION MONITORING CONFIG

### Metrics to Monitor (Daily)
```
[Features]
  - Mean of each feature (to detect shift)
  - Std dev of each feature
  - Min/Max values
  
[Model Performance]
  - Win Rate (target: >= 59%)
  - F1 Score (actual trading)
  - Sharpe Ratio (actual returns)
  
[Trading Metrics]
  - Number of trades
  - Average trade duration
  - Drawdown (max)
  - Capital utilization
```

### Alert Rules (Dashboard)
```
1. Feature drift (KS > 0.15)
   ├─ Alert every 4 hours
   └─ Action: Review and consider retraining

2. Performance degradation (Win Rate < 55%)
   ├─ Critical alert (page on-call)
   └─ Action: Manual review + potential pause

3. Sharpe ratio decay (< 0.8 for 5 days avg)
   ├─ Warning alert
   └─ Action: Schedule retraining

4. Capital at risk (drawdown > 12%)
   ├─ Critical alert
   └─ Action: Activate circuit breaker (-5% slow mode)
```

### Acceptance Criteria
- **AC-14:** Monitoring rules defined
- **AC-15:** Alert thresholds set
- **AC-16:** Dashboard mockup with alerts

---

## 7. EXPLAINABILITY REPORT

### Sample Explanation (for traders)
```
Trade Decision: SELL WINFUT @ 123456

Model Reasoning:
├─ VOLATILITY_BOLLINGER_HIGH_3: +18% contribution (HIGH VOLATILITY)
├─ MOMENTUM_RSI_14: +12% contribution (OVERBOUGHT - RSI > 70)
├─ MOMENTUM_OBV: +10% contribution (Volume decline)
├─ MA_SMA_50_slope: -8% contribution (Downtrend)
└─ [Other features]: +48% contribution (ensemble effect)

Confidence: 72% (threshold: 0.30)
Model Statistics: 60.7% win rate (historic)
Risk: -1500 PYR (if wrong)
```

### Acceptance Criteria
- **AC-17:** Sample explanations generated
- **AC-18:** Trader-friendly format created

---

## 8. DELIVERABLES

### Code (est. 400 LOC)
```python
# analysis/shap_analysis.py (150 LOC)
def compute_shap_values(model, X_sample):
    # TreeSHAP for XGBoost
    # Generate interaction plots
    # Return top-10 features

# analysis/correlation_analysis.py (100 LOC)
def analyze_correlations(X_train):
    # Compute correlation matrix
    # Identify high-correlation pairs
    # Visualize heatmap

# monitoring/drift_detection.py (150 LOC)
def detect_drift(X_live, X_reference):
    # Mean shift detection
    # KS test for distribution
    # Correlation shift detection
```

### Documentation
```
1. SHAP_VALUES_ANALYSIS.md (10 pages)
   ├─ Top 10 features with contributions
   ├─ Feature interactions
   ├─ Visualization: bar plot + interaction plot
   └─ Trader implications

2. CORRELATION_ANALYSIS.md (5 pages)
   ├─ Heatmap visualization
   ├─ High-correlation pairs
   ├─ Redundancy assessment
   └─ Feature engineering recommendations

3. DRIFT_DETECTION_RULES.md (8 pages)
   ├─ Alert definitions
   ├─ Threshold calibration
   ├─ Monitoring dashboard mockup
   └─ Response procedures

4. THRESHOLD_SENSITIVITY.md (4 pages)
   ├─ Sensitivity curve
   ├─ P&L impact analysis
   ├─ Risk assessment
   └─ Threshold adjustment rules
```

---

## 9. SUCCESS CRITERIA

| AC | Criterion | Verification |
|----|-----------|--------------|
| AC-1 | SHAP values for all 24 features | Report: feature importance table |
| AC-2 | Top 10 features identified | Report: ranked contributions |
| AC-3 | Feature interactions documented | Report: interaction plots generated |
| AC-4 | Bottom 5 features identified | Report: lowest SHAP values listed |
| AC-5 | Correlation matrix heatmap | Report: 24×24 visualization |
| AC-6 | High correlation pairs found | Report: pairs with r > 0.8 |
| AC-7 | Feature engineering recommendations | Report: action items list |
| AC-8 | Drift detection rules defined | Monitoring: 3 drift rules coded |
| AC-9 | Alert thresholds calibrated | Config: thresholds documented |
| AC-10 | Dashboard mockup/draft | Design: Grafana dashboard JSON |
| AC-11 | Sensitivity curve generated | Report: threshold sensitivity plot |
| AC-12 | Optimal threshold validated | Report: threshold=0.30 confirmed |
| AC-13 | Threshold adjustment rules | Rules: decision tree documented |
| AC-14 | Monitoring rules defined | Config: alert rules defined |
| AC-15 | Alert thresholds set | Config: all thresholds documented |
| AC-16 | Dashboard mockup with alerts | Design: alert visualization |
| AC-17 | Sample explanations generated | Report: 3-5 example trades |
| AC-18 | Trader-friendly format | Report: non-technical summary |

---

## 10. TIMELINE (5 days)

| Day | Task | Owner | Status |
|-----|------|-------|--------|
| 26/02 | Kickoff + data prep | ML Expert | - |
| 27/02 | SHAP analysis | Data Scientist | - |
| 28/02 | Correlation + Drift rules | ML Expert | - |
| 01/03 | Threshold sensitivity | Both | - |
| 02/03 | Report + dashboard | ML Expert | 🎯 GATE 1 |

---

**Owner:** ML Expert
**Due:** 02/03 17:00 UTC (GATE 1)
**Status:** Not started (ready for kickoff 26/02)
"""

if __name__ == '__main__':
    print(SPEC)
