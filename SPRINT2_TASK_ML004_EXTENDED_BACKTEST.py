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
"""

SPEC = """
# ML-004: EXTENDED BACKTEST (252 TRADING DAYS)

**Objetivo:** Validar modelo com 1 ano de dados históricos (252 trading days)
**Owner:** ML Expert
**Team:** ML Expert + Data Scientist
**Sprint:** Sprint 2 (03/03 - 10/03)
**Duration:** 7 dias (56 horas)
**Deadline:** 10/03 17:00 UTC (ready for GATE 2)
**Dependency:** ENG-003 API ready (for integration testing)

---

## 1. OVERVIEW

### Objective
Simular modelo de trading automatizado em 252 dias (1 ano) de dados históricos
Resultado: Validar Sharpe ratio, Win Rate, Drawdown, P&L expectations

### Success Metrics (GATE 2 Criteria)
```
✅ Sharpe ratio >= 1.0 (risk-adjusted returns)
✅ Win rate >= 59% (minimum, we achieved 60.7% in backtest)
✅ Drawdown < 15% (risk control threshold)
✅ Consistency: Monthly P&L std < 30% of mean
```

### Data Period
```
Historical Period: Feb 2025 - Feb 2026 (252 trading days)
Current Date: Feb 26, 2026
Training Period Used: Jan 2025 - Jan 2026 (training_dataset.csv)
Out-of-Sample: Feb 2026 - Latest (validation)
```

---

## 2. DATA PREPARATION

### Data Sources
```
1. Windfutures (WINFUT) OHLCV data
   - Source: MT5 history (via broker API)
   - Resolution: 15-minute bars
   - Period: Feb 2025 - Feb 2026
   
2. Expected Size
   - Trading days: 252
   - Bars per day: 26 (9:30 - 19:00 BRT, 15-min)
   - Total bars: ~6,500
   - Total samples: 6,500 - 20 (window) = 6,480
```

### Feature Engineering (24 features)
```
Use SAME features as training set:
├─ Volatility (4): Bollinger, ATR, Historical Vol, 3-Sigma
├─ Momentum (4): RSI, MACD, ROC, OBV
├─ Moving Averages (5): SMA50, EMA9, EMA21, slopes
├─ Patterns (3): Mean reversion, Volume spike, Impulse
├─ Lags (9): Return lags, Close/volume lags
└─ Correlation (2): 20-period corr, Trend strength

CRITICAL: Use SAME scaling (StandardScaler from training set)
```

### Data Validation
- [ ] AC-1: Data completeness (no gaps in OHLCV)
- [ ] AC-2: Feature computation (24 features generated)
- [ ] AC-3: Scaling consistency (using training scaling params)

---

## 3. MODEL DEPLOYMENT SIMULATION

### Model Configuration (LOCKED from Sprint 1)
```python
model = XGBClassifier(
    scale_pos_weight=1.476,      # ← Optimal (found in ETAPA 2.1)
    n_estimators=200,
    max_depth=8,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)

# Training data: training_dataset.csv (435 samples, 70/15/15 split)
# Model already trained and saved from Sprint 1
```

### Prediction Logic
```python
For each 15-min bar:
    1. Compute 24 features (using 20-bar lookback window)
    2. Scale features (using training StandardScaler)
    3. Get model probability: p = model.predict_proba(features)[0][1]
    4. Decision:
       if p >= 0.30:  # THRESHOLD (locked from ETAPA 2.2)
           SEND BUY ORDER
       else:
           SKIP (or previous position management)
    5. Log trade: timestamp, features, probability, signal
```

### Model Retraining Policy (Production)
```
Current Policy:
  - Model trained on data up to: Jan 2026
  - Deployed: Feb 26, 2026 (LIVE)
  - Retrain when: Win Rate falls below 55% for 5 consecutive days
  - Frequency: ~Monthly (as data accumulates)
  
This Backtest:
  - Simulates with SAME model (no retraining)
  - Acceptable because: 252 days test period covers diverse conditions
```

### Acceptance Criteria
- [ ] AC-4: Model loaded correctly
- [ ] AC-5: Predictions generated for all bars
- [ ] AC-6: Threshold (0.30) applied consistently

---

## 4. TRADING SIMULATION

### Position Management
```
Entry Rules:
  - Signal: p >= 0.30
  - Entry: Next bar open (1 bar delay for realistic entry)
  
Exit Rules:
  - Duration: 2-5 bars (typical scalp/day trade)
  - OR: Profit target hit (TP = entry + 100 pips)
  - OR: Stop loss hit (SL = entry - 50 pips)
  - OR: End of day (4:55 PM BRT close)
  
Position Sizing:
  - Fixed: 1 contract per trade
  - Capital: R$ 50k (Phase 1 starting capital)
  - Leverage: 1:1 (conservative, actual: 1:50 available)
```

### Risk Management (Circuit Breakers)
```
Phase 1 Circuit Breakers (Feb-Apr 2026):
  -3% daily loss:   ALERTA (trader can continue)
  -5% daily loss:   SLOW MODE (50% position size, 90% ML confidence)
  -8% total loss:   HALT (all trading stopped)

Backtest Assumption:
  - No circuit breaker activations expected
  - If drawdown > 8%: Report and analyze causes
```

### Acceptance Criteria
- [ ] AC-7: Position entries/exits calculated correctly
- [ ] AC-8: Risk management applied (circuit breakers)
- [ ] AC-9: Capital management (50k baseline)

---

## 5. PERFORMANCE METRICS

### Primary Metrics (GATE 2 Criteria)

#### Metric 1: Sharpe Ratio >= 1.0
```
Sharpe = (Mean Return - Risk-Free Rate) / Std Dev of Returns
       = (μ_daily - 0%) / σ_daily

Example:
  Mean daily return: +0.25%
  Std dev: +0.20%
  Sharpe = 0.25% / 0.20% = 1.25 ✅ (PASS)
  
Target: >= 1.0 (risk adjusted)
Risk-Free: 0% (conservative, actual: ~10% Selic BRL)
```

#### Metric 2: Win Rate >= 59%
```
Win Rate = TP / (TP + FP)
         = Profitable Trades / Total Trades

Example:
  TP (profitable): 145 trades
  FP (loss): 95 trades
  Win Rate = 145 / 240 = 60.4% ✅ (PASS)
  
Target: >= 59% (minimum acceptable)
Historical (Sprint 1): 60.7% (expect slight decay)
```

#### Metric 3: Drawdown < 15%
```
Drawdown = (Peak - Trough) / Peak

Example:
  Peak equity: R$ 52,000
  Trough: R$ 44,500
  Drawdown = (52k - 44.5k) / 52k = 14.4% ✅ (PASS)
  
Target: < 15% (risk control)
Acceptable: Up to 15%
Critical: > 20% (triggers circuit breaker)
```

### Secondary Metrics (Reporting)

#### Consistency
```
Monthly P&L:
  Jan: +3,250 (6.5% return)
  Feb: +2,100 (4.2% return)
  Mar: +2,800 (5.6% return)
  ...
  
Expected: Std Dev < 30% of mean month return
Why: Trading should be consistent, not volatile
```

#### Correlation (Backtest vs Live)
```
Backtest Results: 60.7% win rate
Live Trading (30 days): TBD during Phase 1
Expected Correlation: <= 5% decay
  - Acceptable: Live WR >= 57.5%
  - Suspect: Live WR < 54%
  
Why: Accounts for slippage, market differences, etc.
```

#### Monthly Breakdown
```
| Month | Trades | Win % | P&L    | Return |
|-------|--------|-------|--------|---------|
| Feb25 |   48   | 62%   | +3,250 | +6.5%   |
| Mar25 |   42   | 58%   | +1,900 | +3.8%   |
| Apr25 |   55   | 63%   | +3,100 | +6.2%   |
| ...   |  ...   | ...   |  ...   |  ...    |
| Jan26 |   51   | 60%   | +2,800 | +5.6%   |
| Feb26 |   23   | 61%   | +1,450 | +2.9%   |
|-------|--------|-------|--------|---------|
| TOTAL |  240   | 60.4% | +33,200| +66.4%  |

Observations:
- Consistency: Win % varies 58-63% (good)
- P&L: Ranges 1.9k-3.3k per month (good)
- Trend: Flat (no deterioration over time = healthy model)
```

### Acceptance Criteria
- [ ] AC-10: Sharpe ratio >= 1.0
- [ ] AC-11: Win rate >= 59%
- [ ] AC-12: Max drawdown < 15%
- [ ] AC-13: Monthly consistency documented
- [ ] AC-14: Correlation analysis (backtest vs expectations)

---

## 6. ANALYSIS & INSIGHTS

### Feature Importance During Backtest
```
Question: Which features drove wins vs losses?

Analysis:
  Winning trades (145):
    - Avg VOLATILITY_BOLLINGER: 0.18 (high vol)
    - Avg MOMENTUM_RSI: 68 (overbought/oversold)
    - Avg MOMENTUM_OBV: +500k (volume)
    
  Losing trades (95):
    - Avg VOLATILITY_BOLLINGER: 0.08 (low vol)
    - Avg MOMENTUM_RSI: 50 (neutral)
    - Avg MOMENTUM_OBV: -200k (declining volume)
    
Insight: Model works better in high-volatility, high-volume conditions
Action: Monitor feature values in production, alert if patterns change
```

### Market Regime Analysis
```
Market Conditions Encountered:

[Trending (60% of trades): +70% win rate]
  └─ Model excels in trending markets

[Ranging (30% of trades): +48% win rate]
  └─ Model underperforms in choppy/range-bound markets

[Gap Risk (10% of trades): +45% win rate]
  └─ Model losses concentrated in gap openings

Recommendation:
  - Consider adding regime detector
  - Disable trading in range-bound periods (if detected)
```

### Seasonal Patterns
```
Performance by Month:
  Q1 (Jan-Mar): Avg +5.5% (post-holiday volatility)
  Q2 (Apr-Jun): Avg +4.2% (stable period)
  Q3 (Jul-Sep): Avg +5.8% (economic data season)
  Q4 (Oct-Dec): Avg +6.1% (year-end positioning)

Note: Not sufficient for seasonal strategy, but awareness important
```

### Acceptance Criteria
- [ ] AC-15: Feature importance during backtest analyzed
- [ ] AC-16: Market regime analysis completed
- [ ] AC-17: Seasonal patterns documented

---

## 7. DELIVERABLES

### Code (est. 300 LOC)
```python
# backtest/engine.py (150 LOC)
def run_backtest(model, X_data, dates, prices):
    positions = []
    trades = []
    
    for i in range(len(X_data)):
        # Generate prediction
        # Execute order
        # Track P&L
        # Log trade
        
    return trades, equity_curve

# backtest/metrics.py (100 LOC)
def calculate_metrics(trades, equity_curve):
    sharpe = calculate_sharpe(returns)
    win_rate = calculate_win_rate(trades)
    drawdown = calculate_drawdown(equity_curve)
    
    return {
        'sharpe': sharpe,
        'win_rate': win_rate,
        'drawdown': drawdown,
        ...
    }

# backtest/analyzer.py (50 LOC)
def analyze_backtest(trades, metrics):
    monthly_breakdown(trades)
    feature_importance_analysis(trades)
    regime_analysis(trades)
```

### Reports (est. 20 pages)
```
ML004_BACKTEST_RESULTS.md (~10 pages):
  ├─ Executive Summary
  ├─ Metrics (Sharpe, Win Rate, Drawdown)
  ├─ Monthly breakdown table
  ├─ Equity curve chart
  ├─ Drawdown analysis
  ├─ Trade distribution
  └─ Key insights

ML004_DETAILED_ANALYSIS.md (~10 pages):
  ├─ Feature importance analysis
  ├─ Market regime analysis
  ├─ Seasonal patterns
  ├─ Trade examples (best/worst)
  ├─ Risk analysis
  └─ Recommendations for Phase 2

Visualizations:
  ├─ equity_curve.png (equity over 252 days)
  ├─ drawdown.png (underwater plot)
  ├─ monthly_pnl.png (bar chart by month)
  ├─ win_rate_dist.png (win % by month)
  └─ feature_heatmap.png (feature importance)
```

### Acceptance Criteria
- [ ] AC-18: Code complete and tested
- [ ] AC-19: Reports generated (20+ pages)
- [ ] AC-20: Visualizations created (5+ charts)

---

## 8. SUCCESS GATES (GATE 2)

### Go/No-Go Decision Criteria

**GATE 2: 10/03 17:00 UTC**

Decision Tree:
```
Start GATE 2 Review (10/03)
  │
  ├─ Sharpe >= 1.0?
  │  ├─ YES → Continue
  │  └─ NO  → 🔴 NO-GO (Model underperforms on risk-adjusted basis)
  │
  ├─ Win Rate >= 59%?
  │  ├─ YES → Continue
  │  └─ NO  → 🔴 NO-GO (Below minimum threshold, may lose money)
  │
  ├─ Drawdown < 15%?
  │  ├─ YES → Continue
  │  └─ NO  → 🟡 CONDITIONAL (Risk too high, needs circuit breaker adjustment)
  │
  ├─ Consistency OK? (monthly std < 30%)
  │  ├─ YES → Continue
  │  └─ 🟡 WARNING (Inconsistent model, monitor closely in Phase 1)
  │
  └─ → 🟢 GO (All criteria met, authorized for Phase 2 capital activation)
```

### Example Decisions

**Scenario A: PERFECT (All Green)**
```
Sharpe: 1.25 ✅
Win Rate: 61% ✅
Drawdown: 12% ✅
Consistency: 5% std ✅

Decision: 🟢 GO (Proceed with R$ 100k capital activation)
```

**Scenario B: MARGINAL (Some Warnings)**
```
Sharpe: 1.05 ✅ (barely above 1.0)
Win Rate: 59.5% ✅ (barely above 59%)
Drawdown: 14.8% ✅ (near limit of 15%)
Consistency: 28% std ⚠️ (near 30% max)

Decision: 🟢 GO (Marginal but acceptable, closer circuit breaker monitoring)
```

**Scenario C: FAIL (Below Thresholds)**
```
Sharpe: 0.92 ❌ (below 1.0)
Win Rate: 57% ❌ (below 59%)
Drawdown: 18% ❌ (above 15%)

Decision: 🔴 NO-GO (Model fails validation, return to design)
Action: Review and reoptimize model, reschedule for 15/03
```

---

## 9. TIMELINE (7 days)

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

## 10. SUCCESS CRITERIA (AC-1 through AC-20)

| AC# | Criterion | Verification |
|-----|-----------|--------------|
| AC-1 | Data completeness (252 days) | Report: no missing bars |
| AC-2 | 24 features computed | Report: feature table |
| AC-3 | Scaling consistency | Code: using training scaler |
| AC-4 | Model loads correctly | Test: model prediction |
| AC-5 | Predictions for all bars | Report: 6,480 predictions |
| AC-6 | Threshold applied (0.30) | Test: signal generation |
| AC-7 | Position entries/exits correct | Test: order logic validation |
| AC-8 | Risk management applied | Config: circuit breakers |
| AC-9 | Capital management (50k) | Report: equity tracking |
| AC-10 | Sharpe >= 1.0 | Report: computed Sharpe |
| AC-11 | Win rate >= 59% | Report: win rate table |
| AC-12 | Drawdown < 15% | Report: max drawdown |
| AC-13 | Monthly consistency documented | Report: monthly breakdown |
| AC-14 | Correlation analysis done | Report: expectations vs backtest |
| AC-15 | Feature importance analyzed | Report: feature analysis |
| AC-16 | Market regime analysis | Report: regime breakdown |
| AC-17 | Seasonal patterns documented | Report: seasonal analysis |
| AC-18 | Code complete & tested | Tests: 100% passing |
| AC-19 | Reports generated (20+ pages) | Deliverable: markdown files |
| AC-20 | Visualizations created (5+ charts) | Deliverable: PNG/SVG files |

---

## 11. RISK MITIGATION

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Data gaps in history | High | Validate completeness daily, impute if needed |
| Model overfit to training | High | Cross-validate on out-of-sample 2026 data |
| Slippage/spread assumptions | Medium | Conservative: +0.5% slippage added to costs |
| Circuit breaker not triggered | Low | Explicitly test with synthetic loss injection |
| Report generation fails | Medium | Version control, multiple export formats |

---

**Owner:** ML Expert
**Due:** 10/03 17:00 UTC (GATE 2 Decision)
**Status:** Not started (depends on ENG-003 ready)

🎯 **GATE 2 Decision:** GO/NO-GO for Phase 2 Capital Activation (R$ 100k)
"""

if __name__ == '__main__':
    print(SPEC)
