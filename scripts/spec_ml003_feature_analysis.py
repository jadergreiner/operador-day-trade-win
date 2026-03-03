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

Padrão de Localização: Especificações técnicas devem estar em scripts/spec_*.py
Documentado em: docs/BACKLOG_UNIFICADO.md (P1-1: ML-003)
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

## 1. OVERVIEW - DELIVERABLES

- [ ] SHAP values analysis (top 10 features)
- [ ] Feature interaction plots
- [ ] Correlation matrix (24×24 heatmap)
- [ ] Drift detection rules (3 estratégias)
- [ ] Production monitoring config
- [ ] Detailed report (10-15 pages)

---

## 2. SHAP VALUES ANALYSIS

### Methodology
1. Train final model (from Sprint 1: scale_pos_weight=1.476)
2. Select 1000 random samples from training set
3. Calculate SHAP values using TreeSHAP (XGBoost native)
4. Summarize feature importance
5. Generate interaction plots

### Acceptance Criteria
- **AC-1:** SHAP values calculated for all 24 features
- **AC-2:** Top 10 features identified with contributions
- **AC-3:** Feature interactions documented
- **AC-4:** Bottom 5 features identified for potential pruning

---

## 3. FEATURE CORRELATION ANALYSIS

### Correlation Matrix
24×24 matrix showing Pearson correlation coefficients, P-values, and identify highly correlated pairs (r > 0.8)

### Acceptance Criteria
- **AC-5:** Correlation matrix heatmap generated
- **AC-6:** High correlation pairs (r > 0.8) identified
- **AC-7:** Recommendations for feature engineering documented

---

## 4. DRIFT DETECTION STRATEGY

### Rule 1: Mean Shift Detection
Alert if |mean_atual - mean_treino| > 1.5 * std_treino

### Rule 2: Distribution Change (KS Test)
Alert if KS statistic > 0.15

### Rule 3: Correlation Shift
Alert if correlation change > 0.20 for top 5 pairs

### Alert Severity
- GREEN (0 alerts): Normal
- YELLOW (1-2 alerts): Monitor
- ORANGE (3-5 alerts): Review within 48h
- RED (>5 alerts): STOP + retrain

### Acceptance Criteria
- **AC-8:** Drift detection rules defined
- **AC-9:** Alert thresholds calibrated
- **AC-10:** Monitoring dashboard mockup created

---

## 5. THRESHOLD SENSITIVITY ANALYSIS

### Sensitivity Curve
For thresholds [0.25, 0.27, 0.29, 0.30, 0.31, 0.33, 0.35]:
Compute F1, Win Rate, Expected P&L

### Acceptance Criteria
- **AC-11:** Sensitivity curve generated
- **AC-12:** Optimal threshold validated
- **AC-13:** Threshold adjustment rules documented

---

## 6. PRODUCTION MONITORING CONFIG

### Metrics to Monitor (Daily)
- Mean of each feature
- Std dev of each feature
- Min/Max values
- Win Rate (target: >= 59%)
- F1 Score
- Sharpe Ratio

### Acceptance Criteria
- **AC-14:** Monitoring rules defined
- **AC-15:** Alert thresholds set
- **AC-16:** Dashboard mockup with alerts

---

## 7. EXPLAINABILITY REPORT

### Sample Explanation (for traders)
Document trade decisions with feature contributions and confidence

### Acceptance Criteria
- **AC-17:** Sample explanations generated
- **AC-18:** Trader-friendly format created

---

## 8. SUCCESS CRITERIA (18 ACs)

All 18 acceptance criteria must be met for GATE 1 approval.

---

## 9. TIMELINE (5 days)

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
