# 🚀 SPRINT 2 - ATIVIDADES POR PRIORIDADE

**Status:** ✅ Atividades Prontas
**Squad:** 8 personas
**Objetivo:** Phase 2 Execution & Deployment (Capital escalation 50k → 100k)

---

## 🎯 TAREFAS CRÍTICAS (P0 - BLOQUEADORES)

### P0-1: ENG-003 - MT5 REST API Implementation
**Lead:** Eng Sr (Backend)
**Squad:** 3 Backend Developers + Eng Sr (4 pessoas)
**Horas:** 160 dev hours total
**Priority:** P0 (CRÍTICO - bloqueia ML-004)

#### O Que Entregar:
- FastAPI REST server (async, high-performance)
- 14 REST endpoints (Auth, Orders, Positions, Account, Health)
- OAuth 2.0 authentication (MT5 token-based)
- RabbitMQ async queue (order processing)
- WebSocket real-time (position updates < 100ms)
- Redis cache (30s TTL for positions/account)
- PostgreSQL audit trail (all operations logged)
- Error handling + 3x exponential backoff retry logic
- 100% unit/integration/E2E test coverage
- Performance: P95 latency < 200ms (order), < 100ms (WebSocket)

#### Endpoints (14 total):
```
Authentication:
  POST   /auth/login              (OAuth 2.0)
  POST   /auth/refresh            (Token refresh)

Orders:
  POST   /orders/send             (Async queue)
  GET    /orders/{ticket}         (Status)
  GET    /orders/history          (All orders)
  PATCH  /orders/{ticket}/cancel  (Cancel)

Positions:
  GET    /positions               (All positions)
  PATCH  /positions/{ticket}      (Modify SL/TP)
  DELETE /positions/{ticket}      (Close)
  GET    /positions/{ticket}/pnl  (P&L)

Account:
  GET    /account                 (Balance, equity, margin)
  GET    /health                  (Dependencies health)
```

#### Acceptance Criteria (8):
- ✅ AC-1: Authentication valida credenciais MT5
- ✅ AC-2: Token refresh sem re-auth
- ✅ AC-3: Orders enviados async (non-blocking)
- ✅ AC-4: Retry logic (3x exponential backoff)
- ✅ AC-5: Order status tracked real-time
- ✅ AC-6: Positions updated < 100ms (WebSocket)
- ✅ AC-7: Account balance updated 30s
- ✅ AC-8: Healthcheck inclui todas dependencies

#### Tests Required:
- 20+ unit tests (Auth, Queue, Cache, Error handling)
- 10+ integration tests (API ↔ MT5 mock, E2E flows)
- 5+ performance tests (load, stress, failover)
- Code review: 2+ reviewers

#### Success Criteria:
- 🟢 8/8 AC passing
- 🟢 P95 latency < 500ms verified
- 🟢 All tests passing (35+ tests)
- 🟢 Code reviewed + approved

---

### P0-2: ML-004 - Extended Backtest (252 Trading Days)
**Lead:** ML Expert
**Squad:** ML Expert + Data Scientist (2 pessoas)
**Horas:** 88 dev hours total
**Priority:** P0 (CRÍTICO - go/no-go decision)
**Bloqueador:** Espera ENG-003 estar pronto

#### O Que Entregar:
- 252-day historical backtest (full year simulation)
- Performance metrics (Sharpe, Win Rate, Drawdown)
- Monthly P&L breakdown + consistency analysis
- Feature importance heatmap (during trading)
- Market regime analysis (3 regimes identified)
- Seasonal pattern analysis
- 20+ page detailed report
- Equity curve visualization
- Drawdown chart analysis

#### Data Used:
- 252 trading days (1 full year)
- Historical OHLCV data
- No data gaps, no holidays
- Feature engineering: 24 features (same as training)
- Model: XGBoost (scale_pos_weight=1.476 LOCKED)
- Threshold: 0.30 probability (LOCKED)

#### GATE 2 Decision Criteria (MUST PASS):
```
Sharpe Ratio:       >= 1.0     (risk-adjusted returns)
Win Rate:           >= 59%     (probability of profit)
Max Drawdown:       < 15%      (risk control)
Consistency:        < 30% std  (monthly regularity)
```

#### Acceptance Criteria (20):
- ✅ AC-1 through AC-20 covering:
  - Data loading + validation
  - Features extracted correctly
  - Backtest logic verified
  - Metrics calculated properly
  - Reports generated
  - Visualizations complete
  - Peer reviewed
  - All gates passed

#### Success Criteria:
- 🟢 20/20 AC passing
- 🟢 Sharpe >= 1.0 ✅
- 🟢 Win Rate >= 59% ✅
- 🟢 Drawdown < 15% ✅
- 🟢 Reports approved

#### Capital Decision (If All Criteria Met):
```
GATE 2 APPROVED = Activate R$ 100k Phase 2 capital
GATE 2 REJECTED = Stay with R$ 50k Phase 1
```

---

## 🎯 TAREFAS IMPORTANTES (P1 - NÃO-BLOQUEADORES)

### P1-1: ML-003 - Feature Importance Analysis
**Lead:** ML Expert
**Squad:** ML Expert + Data Scientist (2 pessoas)
**Horas:** 88 dev hours total
**Priority:** P1 (IMPORTANTE - production monitoring)

#### O Que Entregar:
- SHAP values analysis (top 10 features ranked)
- 24×24 correlation matrix heatmap
- Drift detection rules (3 strategies):
  - Mean shift test (µ ± 2σ)
  - Kolmogorov-Smirnov test (p > 0.05)
  - Correlation shift (Δr > 0.1)
- Alert thresholds (Green/Yellow/Orange/Red levels)
- Threshold sensitivity analysis (±0.05)
- Production monitoring configuration
- Explainability for traders (decision trees, IF-THEN rules)
- 20+ page detailed report

#### Acceptance Criteria (18):
- ✅ AC-1 through AC-18 covering:
  - SHAP analysis complete
  - Correlation matrix generated
  - All 3 drift rules configured
  - Alert thresholds validated
  - Sensitivity analysis done
  - Monitoring config ready
  - Reports finalized
  - Peer reviewed

#### Success Criteria:
- 🟢 18/18 AC passing
- 🟢 SHAP top 10 features identified
- 🟢 Drift rules tested
- 🟢 Report approved

---

## 📋 TASK EXECUTION FLOW (SEQUÊNCIA LÓGICA)

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  PARALLEL TRACK 1: Infrastructure                      │
│  ├─ P0-1: ENG-003 - MT5 REST API                      │
│  │   ├─ Design & architecture                         │
│  │   ├─ Authentication layer                          │
│  │   ├─ Order execution endpoints                     │
│  │   ├─ Position tracking service                     │
│  │   ├─ Error handling & retry logic                 │
│  │   ├─ Integration testing                           │
│  │   └─ ✅ READY when: 8/8 AC passing                │
│  │                                                    │
│  └─ UNBLOCKS: P0-2 (ML-004 can start)               │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  PARALLEL TRACK 2: Analytics & Validation             │
│  ├─ P1-1: ML-003 - Feature Analysis                   │
│  │   ├─ SHAP values computation                       │
│  │   ├─ Correlation analysis                          │
│  │   ├─ Drift detection rules                         │
│  │   ├─ Alert thresholds                              │
│  │   ├─ Sensitivity analysis                          │
│  │   ├─ Monitoring configuration                      │
│  │   └─ ✅ READY when: 18/18 AC passing              │
│  │                                                    │
│  └─ PREREQUISITE: None (independent)                 │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  SEQUENTIAL TASK (After ENG-003 Ready):               │
│  └─ P0-2: ML-004 - Extended Backtest                 │
│    ├─ Wait for: ENG-003 complete                     │
│    ├─ Load 252-day data                               │
│    ├─ Run backtest simulation                         │
│    ├─ Compute metrics (Sharpe, WR, DD)              │
│    ├─ Generate reports & visualizations              │
│    ├─ Peer review                                     │
│    └─ ✅ READY when: 20/20 AC passing                │
│         AND Sharpe >= 1.0, WR >= 59%, DD < 15%     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 SQUAD ALLOCATION

| Role | Hours | Focus | Tasks |
|------|-------|-------|-------|
| **Eng Sr** | 48h | API design + lead | ENG-003 |
| **Dev-1** | 40h | Auth + Orders | ENG-003 |
| **Dev-2** | 40h | Positions + WS | ENG-003 |
| **Dev-3** | 40h | Queue + retry | ENG-003 |
| **ML Expert** | 48h | SHAP + Backtest | ML-003 + ML-004 |
| **Data Sci** | 40h | Data prep | ML-003 + ML-004 |
| **QA Lead** | 32h | Test strategy | All tasks |
| **Test Eng** | 32h | Automation | All tasks |
| **Total** | 320h | - | - |

---

## 🎯 SUCCESS CRITERIA SUMMARY

### ENG-003 (P0-1) - PASS/FAIL
```
MUST HAVE:
  ✅ 8/8 AC passing
  ✅ P95 latency < 500ms
  ✅ All 35+ tests passing
  ✅ Code reviewed (2+ reviewers)
  ✅ Type hints: 100%
  ✅ Docstrings: 100%

NICE-TO-HAVE:
  - Load test: 100 concurrent users
  - Stress test: 500 req/sec
```

### ML-003 (P1-1) - PASS/FAIL
```
MUST HAVE:
  ✅ 18/18 AC passing
  ✅ SHAP top 10 features
  ✅ Drift rules configured
  ✅ Monitoring config ready
  ✅ 20+ page report

NICE-TO-HAVE:
  - Historical drift analysis (past 6 months)
  - Model explainability for traders
```

### ML-004 (P0-2) - GO/NO-GO DECISION
```
GATE 2 CRITERIA (ALL MUST PASS):
  ✅ Sharpe >= 1.0
  ✅ Win Rate >= 59%
  ✅ Drawdown < 15%
  ✅ Consistency: Std(monthly) < 30% of mean
  ✅ 20/20 AC passing
  ✅ All reports approved

IF ALL PASS:
  → Activate R$ 100k Phase 2 capital

IF ANY FAIL:
  → Stay with R$ 50k Phase 1 (analyze, rework, retry)
```

---

## ⚠️ CRITICAL DEPENDENCIES

### Must Complete FIRST (No Negotiation):
1. **ENG-003** must be done before ML-004 can be integrated
2. **ML-003** is independent (can start anytime)
3. **ML-004** requires ENG-003 done (for integration testing)

### Blocking Scenarios:
```
If ENG-003 FAILS:
  → ML-004 integration testing blocked
  → NO GO-LIVE possible

If ML-004 FAILS gate criteria:
  → NO capital escalation to R$ 100k
  → Stay with Phase 1 (R$ 50k)
  → Analyze backtest + iterate
```

---

## 📞 ESCALATION POINTS

| Scenario | Action | Owner |
|----------|--------|-------|
| **ENG-003 has blockers** | Tech Lead + CTO | Eng Sr |
| **ML-003/004 metrics off** | Analysis + rerun | ML Expert |
| **Gate criteria not met** | Go/No-Go decision | Product Owner + CFO |
| **Capital go-live delayed** | Communication to board | CFO |

---

## ✅ READY TO START

All tasks are **FULLY SPECIFIED** and **READY FOR EXECUTION**.

Next step: **Team standup** to confirm squad allocation and begin work.

---

*Generated: 26/02/2026*
*Format: Activity-First (No Dates, Priority-Based)*
