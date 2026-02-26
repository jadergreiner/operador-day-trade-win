# 🚀 SPRINT 2 - TAREFAS PRIORITIZADAS (SEM DATAS)

**Status:** ✅ Pronto para execução  
**Squad:** 8 personas  
**Formato:** Organizado por Prioridade & Atividades  

---

## 📋 TAREFAS (Ordem de Execução)

### 🔴 P0-1: ENG-003 - MT5 REST API (BLOQUEADOR)

**Lead:** Eng Sr  
**Squad:** 3 Backend Devs (4 total)  
**Horas:** 160 dev hours  
**Status:** Ready to start

**Deliverables:**
- 14 REST endpoints (Auth, Orders, Positions)
- OAuth 2.0 authentication
- RabbitMQ async queue + retry (3x exponential backoff)
- WebSocket (< 100ms real-time)
- Redis cache + PostgreSQL audit trail
- 100% test coverage (unit + integration + E2E)
- Performance: P95 < 200ms

**AC (8):** Authentication, Token refresh, Async orders, Retry logic, Order tracking, WebSocket latency, Account updates, Health checks

**Success Criteria:**
- ✅ 8/8 AC passing
- ✅ P95 latency < 500ms
- ✅ 35+ tests passing
- ✅ Code reviewed (2+ reviewers)

**Unblocks:** ML-004 can start when this is done

---

### 🟡 P1-1: ML-003 - Feature Analysis (INDEPENDENT)

**Lead:** ML Expert  
**Squad:** ML Expert + Data Scientist (2 total)  
**Horas:** 88 dev hours  
**Status:** Ready to start (no dependencies)

**Deliverables:**
- SHAP values (top 10 features ranked)
- 24×24 correlation matrix heatmap
- Drift detection rules (3 rules):
  - Mean shift test (µ ± 2σ)
  - KS test (p > 0.05)
  - Correlation shift (Δr > 0.1)
- Alert thresholds (Green/Yellow/Orange/Red)
- Threshold sensitivity analysis (±0.05)
- Production monitoring config
- 20+ page report + visualizations

**AC (18):** SHAP analysis, Correlation matrix, Drift rules, Alert config, Sensitivity analysis, Monitoring setup, Reports complete

**Success Criteria:**
- ✅ 18/18 AC passing
- ✅ All drift rules tested
- ✅ Monitoring config ready
- ✅ Reports approved

**Dependencies:** None

---

### 🔴 P0-2: ML-004 - Extended Backtest (SEQUENTIAL)

**Lead:** ML Expert  
**Squad:** ML Expert + Data Scientist  
**Horas:** 88 dev hours  
**Status:** Blocked (waits for ENG-003)

**Starts When:** ENG-003 is complete

**Deliverables:**
- 252-day historical backtest (full year)
- Performance metrics:
  - Sharpe ratio calculation
  - Win rate (TP / (TP+FP))
  - Max drawdown analysis
  - Monthly consistency
- Feature importance during trades
- Market regime analysis
- 20+ page report + equity curve + drawdown chart

**AC (20):** Data validation, Feature extraction, Backtest logic, Metrics calculation, Reports generation, Visualizations, Peer review

**GATE 2 Criteria (Must ALL Pass):**
- ✅ Sharpe >= 1.0
- ✅ Win rate >= 59%
- ✅ Drawdown < 15%
- ✅ Consistency: Std(monthly) < 30% mean

**Capital Decision:**
- If ALL criteria PASS: Activate R$ 100k Phase 2
- If ANY criterion FAILS: Stay with R$ 50k Phase 1

---

## 📊 EXECUTION MODEL

```
PARALLEL EXECUTION:
┌─────────────────────┬──────────────────┐
│  ENG-003            │  ML-003          │
│  (Infrastructure)   │  (Analytics)     │
│  ✅ Ready           │  ✅ Ready        │
│  When done          │  When done       │
│  → Unblocks ML-004  │  → Independent   │
└─────────────────────┴──────────────────┘
                  ↓
        ┌─────────────────────┐
        │  ML-004             │
        │  (Validation)       │
        │  ⏳ Blocked         │
        │  When ENG-003 done  │
        │  → GATE 2 Decision  │
        └─────────────────────┘
```

**Execution Rules:**
1. ENG-003 and ML-003 run simultaneously (no dependencies)
2. ML-004 waits for ENG-003 to complete
3. All tasks must pass their AC criteria
4. GATE reviews happen when tasks complete (not on fixed schedule)

---

## 👥 SQUAD ALLOCATION

| Role | Hours | Tasks |
|------|-------|-------|
| Eng Sr | 48h | ENG-003 design + lead |
| Dev-1 | 40h | ENG-003 Auth + Orders |
| Dev-2 | 40h | ENG-003 Positions + WS |
| Dev-3 | 40h | ENG-003 Queue + retry |
| ML Expert | 48h | ML-003 + ML-004 |
| Data Scientist | 40h | ML-003 + ML-004 |
| QA Lead | 32h | Test strategy |
| Test Engineer | 32h | Test automation |
| **Total** | **320h** | — |

---

## 🎯 GATES & DECISIONS

### GATE 1: ENG-003 + ML-003 Complete

**Go Criteria:**
- ENG-003: 8/8 AC done
- ML-003: 18/18 AC done
- Code review: 2+ reviewers
- Tests: All passing

**Decision:**
- ✅ GO: Start ML-004 immediately
- ⚠️ CONDITIONAL: Minor fixes, retry in 1-2 days
- ❌ NO-GO: Major issues, rework 3+ days

---

### GATE 2: ML-004 Complete + UAT Ready

**Go Criteria (ALL must pass):**
- Sharpe >= 1.0 ✅
- Win rate >= 59% ✅
- Drawdown < 15% ✅
- Consistency < 30% ✅
- 20/20 AC done
- Trader UAT sign-off

**Decision (Capital Activation):**
- ✅ GO: Activate R$ 100k Phase 2
- ⚠️ CONDITIONAL: Sharpe 0.95+ or WR 58%+, more analysis
- ❌ NO-GO: < 2 criteria met, return to dev
- ❌ DELAY: Major issues, revisit later

---

## ⚠️ CRITICAL PATH

```
Critical Path = ENG-003 → ML-004
  (ML-003 is parallel, not critical path)

Longest duration = ENG-003 (160h) + ML-004 (88h) = 248h
Parallel potential = ML-003 (88h) runs alongside ENG-003

If ENG-003 delays → ML-004 delays (blocker)
If ML-003 delays → No impact (independent)
If ML-004 delays → No impact (not blocking anything)
```

---

## ✅ SUCCESS CRITERIA SUMMARY

**MUST HAVE (All Tasks):**
- ✅ All AC criteria passing
- ✅ Code reviewed (2+ reviewers)
- ✅ 100% type hints
- ✅ Comprehensive tests (80%+ coverage)
- ✅ Documentation complete

**GATE 1 (ENG-003 + ML-003):**
- ✅ 8/8 + 18/18 AC passing
- ✅ API P95 latency < 500ms
- ✅ Code review approved
- ✅ Integration tested

**GATE 2 (ML-004 + Capital):**
- ✅ Sharpe >= 1.0
- ✅ Win rate >= 59%
- ✅ Drawdown < 15%
- ✅ Consistency validated
- ✅ Trader UAT approved

---

## 🚀 NEXT STEPS

### Immediate (When You're Ready):
1. ✅ Confirm squad availability
2. ✅ Setup environment (API repo, DB, queues)
3. ✅ Begin development

### When ENG-003 Done:
- GATE 1 review
- If GO: Start ML-004
- If NO-GO: Rework

### When ML-004 Done:
- GATE 2 review + metrics validation
- If GO: Capital activation
- If NO-GO: Analyze + iterate

### Daily Routine:
- Standup: 15:00 UTC (15 min)
- Progress update
- Blocker identification
- Next day planning

---

## 📞 ESCALATION

| Issue | Owner | Escalate To |
|-------|-------|-------------|
| ENG-003 blocker | Eng Sr | CTO |
| ML metrics off | ML Expert | Head Data |
| Gate criteria fail | PO | CFO + Board |
| Capital decision | CFO | Board |

---

## 🎊 PRONTO!

**Tudo está especificado, testável e pronto.**

Próximo step: Team standup + começar quando squad tiver ready.

---

*Formato: Activity-First (Prioridades, sem datas)*  
*Gerado: 26/02/2026*
