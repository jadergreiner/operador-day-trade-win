#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SPRINT 2 - ML-004: EXTENDED BACKTEST (252 TRADING DAYS)
========================================================

Especificação técnica para teste estendido do modelo (1 ano completo)
Validação de performance sustentável do modelo em produção

Lead: ML Expert
Duration: 7 dias (03/03 - 10/03)
Priority: P0 (Bloqueador)

Padrão de Localização: Especificações técnicas devem estar em scripts/spec_*.py
Documentado em: docs/BACKLOG_UNIFICADO.md (P0-2: ML-004)
"""

SPEC = """
# ML-004: EXTENDED BACKTEST (252 TRADING DAYS)

**Objetivo:** Validar modelo com 1 ano de dados históricos (252 trading days)
**Owner:** ML Expert
**Team:** ML Expert + Data Scientist
**Sprint:** Sprint 2 (03/03 - 10/03)
**Duration:** 7 dias (56 horas)
**Deadline:** 10/03 17:00 UTC (ready for GATE 2 decision)
**Dependency:** ENG-003 API ready (for integration testing)

---

## 1. OVERVIEW

### Objective
Simular modelo com 1 ano de dados históricos (252 trading days)
Resultado: Validar Sharpe ratio, Win Rate, Drawdown, P&L expectations

### Success Metrics (GATE 2 Criteria - MUST ALL PASS)
✅ Sharpe ratio >= 1.0 (risk-adjusted returns)
✅ Win rate >= 59% (minimum acceptable)
✅ Drawdown < 15% (risk control threshold)
✅ Consistency: Monthly P&L std < 30% of mean

---

## 2. DATA PREPARATION

### Data Sources
1. Windfutures (WINFUT) OHLCV data
2. Period: Feb 2025 - Feb 2026 (252 trading days)
3. Resolution: 15-minute bars
4. Expected samples: ~6,480

### Feature Engineering (24 features)
Use SAME features as training set:
- Volatility (4)
- Momentum (4)
- Moving Averages (5)
- Patterns (3)
- Lags (9)
- Correlation (2)

**CRITICAL:** Use SAME scaling (StandardScaler from training set)

### Acceptance Criteria
- **AC-1:** Data completeness (no gaps)
- **AC-2:** 24 features generated
- **AC-3:** Scaling consistency validated

---

## 3. MODEL DEPLOYMENT SIMULATION

### Model Configuration (LOCKED from Sprint 1)
```python
XGBClassifier(
    scale_pos_weight=1.476,
    n_estimators=200,
    max_depth=8,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)
```

### Prediction Logic
For each 15-min bar:
1. Compute 24 features (20-bar lookback)
2. Scale features (training StandardScaler)
3. Get probability: p = model.predict_proba(features)[0][1]
4. Decision: if p >= 0.30 → BUY, else SKIP
5. Log trade

### Acceptance Criteria
- **AC-4:** Model loaded correctly
- **AC-5:** Predictions generated for all bars
- **AC-6:** Threshold (0.30) applied consistently

---

## 4. TRADING SIMULATION

### Position Management
- Entry: when p >= 0.30 (next bar open)
- Exit: TP (100 pips) or SL (50 pips) or EOD
- Size: 1 contract per trade
- Capital: R$ 50k (Phase 1)

### Risk Management (Circuit Breakers)
- -3%: ALERTA (trader continues)
- -5%: SLOW MODE (50% position size)
- -8%: HALT (all trading stopped)

### Acceptance Criteria
- **AC-7:** Position entries/exits correct
- **AC-8:** Risk management applied
- **AC-9:** Capital management (50k baseline)

---

## 5. PERFORMANCE METRICS

### Primary (GATE 2 Criteria)

#### Sharpe Ratio >= 1.0
Sharpe = Mean Daily Return / Std Dev of Returns
Target: >= 1.0 (risk-adjusted)

#### Win Rate >= 59%
Win Rate = Profitable Trades / Total Trades
Target: >= 59%

#### Drawdown < 15%
Drawdown = (Peak - Trough) / Peak
Target: < 15%

#### Consistency
Monthly P&L std < 30% of mean
Why: Trading should be consistent

### Acceptance Criteria
- **AC-10:** Sharpe ratio >= 1.0
- **AC-11:** Win rate >= 59%
- **AC-12:** Max drawdown < 15%
- **AC-13:** Monthly consistency documented
- **AC-14:** Correlation analysis completed

---

## 6. ANALYSIS & INSIGHTS

### Feature Importance During Backtest
Which features drove wins vs losses?

### Market Regime Analysis
Performance in Trending vs Ranging vs Gap conditions

### Seasonal Patterns
Performance by quarter/month

### Acceptance Criteria
- **AC-15:** Feature importance analyzed
- **AC-16:** Market regime analysis completed
- **AC-17:** Seasonal patterns documented

---

## 7. DELIVERABLES

### Code (est. 300 LOC)
- backtest/engine.py (150 LOC)
- backtest/metrics.py (100 LOC)
- backtest/analyzer.py (50 LOC)

### Reports (est. 20 pages)
- ML004_BACKTEST_RESULTS.md (~10 pages)
- ML004_DETAILED_ANALYSIS.md (~10 pages)

### Visualizations (5+ charts)
- equity_curve.png
- drawdown.png
- monthly_pnl.png
- win_rate_dist.png
- feature_heatmap.png

### Acceptance Criteria
- **AC-18:** Code complete and tested
- **AC-19:** Reports generated (20+ pages)
- **AC-20:** Visualizations created (5+ charts)

---

## 8. GATE 2 DECISION (10/03)

### Go/No-Go Criteria

```
IF Sharpe >= 1.0 AND Win Rate >= 59% AND Drawdown < 15%:
    Decision: 🟢 GO (Proceed with R$ 100k capital activation)
ELSE:
    Decision: 🔴 NO-GO (Return to design/retraining)
```

### Timeline (7 days)

| Day | Task | Owner | Status |
|-----|------|-------|--------|
| 03/03 | Kickoff + data load | ML Expert | - |
| 04/03 | Feature engineering | Data Scientist | - |
| 05/03 | Backtest engine + runs | ML Expert | - |
| 06/03 | Metrics + analysis | Both | - |
| 07/03 | Report generation | ML Expert | - |
| 08/03 | Peer review + fixes | Data Scientist | - |
| 09/03 | Final polish | ML Expert | - |
| 10/03 | GATE 2 Review | All | 🎯 DECISION |

---

## 9. SUCCESS CRITERIA (20 ACs)

All 20 acceptance criteria must be met for GATE 2 approval.

---

**Owner:** ML Expert
**Due:** 10/03 17:00 UTC (GATE 2 Decision)
**Status:** Not started (depends on ENG-003 ready)

🎯 **GATE 2 Decision:** GO/NO-GO for Phase 2 Capital Activation (R$ 100k)
"""

if __name__ == '__main__':
    print(SPEC)
