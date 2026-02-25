# 📋 DAILY STANDUP TEMPLATE - Sprint 1 (27/02 - 05/03)

**Event:** Daily Standup  
**Time:** 15:00 BRT (15 minutes)  
**Frequency:** Monday-Friday during Sprint 1  
**Channel:** Slack #sprint-1-standup (async) + Zoom (optional sync)  
**Attendees:** All team leads + Product Owner  

---

## 📝 STANDUP REPORT TEMPLATE

### **Date: [Day, DD/MM]**

#### 👨‍💻 **Eng Sr Team (WebSocket + Risk Framework)**

**Yesterday's Accomplishments:**
- [ ] WebSocket skeleton: X% complete
- [ ] Risk validator gate 1: X% complete
- [ ] Test coverage: X% (target >85%)
- [ ] Code review status: [Done/Pending]

**Today's Plan:**
- [ ] [Task 1] - Expected: [Time/LOC]
- [ ] [Task 2] - Expected: [Time/LOC]
- [ ] [Task 3] - Expected: [Time/LOC]

**Blockers/Risks:**
- [ ] None identified
- [ ] [If any] Technical: [Description] → Mitigation: [Plan]
- [ ] [If any] Resource: [Description] → Escalate to: [Person]

**Code Quality Metrics:**
- Type hints: X% (target 100%)
- Test coverage: X% (target >90%)
- Lint errors: X (target 0)
- PR reviews pending: X

**Questions/Support Needed:**
- [Any question?]

---

#### 🧠 **ML Expert Team (Feature Engineering + Backtest)**

**Yesterday's Accomplishments:**
- [ ] Feature engineering: [Features count] validated
- [ ] Dataset quality: [Checks completed]
- [ ] Backtest setup: X% complete
- [ ] Grid search: [Configs tested]

**Today's Plan:**
- [ ] [Task 1] - Expected: [Metric/Results]
- [ ] [Task 2] - Expected: [Metric/Results]
- [ ] [Task 3] - Expected: [Metric/Results]

**Blockers/Risks:**
- [ ] None identified
- [ ] [If any] Model: [Description] → Mitigation: [Plan]
- [ ] [If any] Data: [Description] → Escalate to: [Person]

**ML Metrics:**
- Feature correlation: [Stats]
- Label distribution: BUY: X%, SKIP: Y%
- Dataset quality: [NaN %], [Outliers %]
- CV fold variance: X (target <0.05)

**Questions/Support Needed:**
- [Any question?]

---

#### 🧪 **QA Lead (Testing Coordination)**

**Yesterday's Accomplishments:**
- [ ] Test cases written: X (target 100%)
- [ ] Test execution: X/X passed (target 100%)
- [ ] Coverage analysis: X% (target >90%)
- [ ] Regression tests: [Status]

**Today's Plan:**
- [ ] Execute tests: [Module/Coverage]
- [ ] Coverage analysis: [Target %]
- [ ] Fix failing tests: [Count]

**Blockers/Risks:**
- [ ] None identified
- [ ] [If any] Test infra: [Description] → Support: [Team]

**Test Metrics:**
- Pass rate: X% (target 100%)
- Coverage: X% (target >90%)
- Average execution: Xs (target <10s)
- Critical defects: X (target 0)

**Questions/Support Needed:**
- [Any question?]

---

#### 📊 **Product Owner (Gate Status)**

**AC Completion Summary:**
- ML-001 (Dataset): 7/7 ✅ Complete
- ENG-002 (WebSocket): X/10 (target 10/10 by 01/03)
- ENG-003 (Risk): X/5 (target 5/5 by 02/03)
- ENG-004 (Orders): X/5 (target 5/5 by 03/03)
- ML-002 (Backtest): X/7 (target 7/7 by 02/03)
- ML-003 (Features): X/8 (target 8/8 by 28/02)

**Total AC Progress: X/42** (target 42/42 by 05/03)

**Gate 1 Readiness (05/03 17:00):**
- [] All 42 AC completed
- [] All tests passing (≥95% P95)
- [] Coverage >90% across all modules
- [] Performance SLA met (<500ms P95)
- [] Manual testing approved

**Risk Status:**
- 🟢 Green: All on track
- 🟡 Yellow: [If any] Item → Plan: [Mitigation]
- 🔴 Red: [If any] Item → Action: [Escalation]

**Decisions Needed:**
- [ ] Any scope change requests?
- [ ] Any resource reallocation?
- [ ] Any timeline adjustment?

---

## 🎯 EXAMPLE - DAY 1 (27/02)

### **Date: Monday, 27/02/2026**

#### 👨‍💻 **Eng Sr Team**

**Yesterday's Accomplishments:**
- Kickoff meeting completed
- WebSocket skeleton started: 30% complete (100 LOC skeleton)
- Risk validator design reviewed and approved
- [INTEGRATION-ML-001 already merged to main]

**Today's Plan:**
- Complete WebSocket routing handlers: 4h (100 LOC)
- Implement ConnectionManager: ~2h (70 LOC)
- Write unit test stubs: ~1h (10 test methods)

**Blockers/Risks:**
- None identified
- Dependencies: FastAPI environment ready ✅

**Code Quality Metrics:**
- Type hints: 100% (with skeleton code)
- Test coverage: 0% (tests not yet written)
- Lint errors: 0 (code clean)
- PR reviews pending: 1 (design review)

**Questions/Support Needed:**
- Can QA finalize test plan by EOD 27/02?

---

#### 🧠 **ML Expert Team**

**Yesterday's Accomplishments:**
- Dataset loading COMPLETE (INTEGRATION-ML-001 merged)
- Feature list validated: 24 features ready
- Data quality checks completed: 0 NaN cells, balanced labels
- Grid search configuration prepared (8 configs to test)

**Today's Plan:**
- Finalize feature engineering: ~2h (verify all 24 features)
- Create feature correlation matrix: ~1h
- Prepare dataset for backtest: ~1h (preprocessing)
- Start grid search setup: ~2h (XGBoost config)

**Blockers/Risks:**
- None identified
- Dependencies: Dataset ready ✅, compute resources ready ✅

**ML Metrics:**
- Features validated: 24/24 ✅
- Label distribution: BUY 54.9%, SKIP 45.1% (balanced)
- Zero NaN cells: 0/11,310 ✅
- Data split: 70/15/15 verified ✅

**Questions/Support Needed:**
- Will backtest results be ready by 02/03 EOD?

---

#### 🧪 **QA Lead**

**Yesterday's Accomplishments:**
- Test strategy documented
- Test framework (pytest) configured
- Test environment ready: git, Python venv, dependencies

**Today's Plan:**
- Write test cases for ENG-002: ~2h (10 test stubs)
- Setup coverage tracking: ~1h
- Create regression test plan: ~1h

**Blockers/Risks:**
- None identified

**Test Metrics:**
- Pass rate: 100% on ML-001 (inherited)
- Coverage: Ready to track (baseline: 0% for new code)
- Execution: Pytest environment: 0.2s avg per test
- Critical defects: 0 (inherited from ML-001)

**Questions/Support Needed:**
- When will first ENG-002 code be ready for testing?

---

#### 📊 **Product Owner**

**AC Completion Summary:**
- ML-001 (Dataset): 7/7 ✅ Complete (merged to main)
- ENG-002 (WebSocket): 0/10 (started today, ~30% design)
- ENG-003 (Risk): 0/5 (design ready, starts 28/02)
- ENG-004 (Orders): 0/5 (design ready, starts 02/03)
- ML-002 (Backtest): 0/7 (starts 01/03)
- ML-003 (Features): 0/8 (started today, in-progress)

**Total AC Progress: 7/42 (16.7%)**
- Expected by EOD 27/02: ~8/42 (19%)
- Timeline to 05/03: On track ✅

**Gate 1 Readiness (05/03 17:00):**
- On track (all teams started, no blockers identified)
- Risk level: 🟢 Green

**Risk Status:**
- 🟢 Green: All teams mobilized, parallel execution started
- Timeline: 27/02-05/03 sprint on schedule

**Decisions Needed:**
- None at Day 1 kickoff (all approved in pre-sprint)

---

## 📝 FOR YOUR TEAM LEAD

**How to Use This Template:**

1. **Copy this section** at 14:45 on standup day
2. **Fill in your section** (copy relevant template above)
3. **Post to Slack** #sprint-1-standup by 15:00 BRT
4. **If blockers:** Tag relevant person for discussion
5. **Async sync:** Team leads review all posts within 30 min
6. **Zoom call (optional):** Only if >2 blockers need real-time discussion

---

## 🎯 STANDUP SUCCESS CRITERIA

Each standup should have:
- ✅ Specific accomplishments (not "made progress")
- ✅ Concrete plan for next day (with effort estimate)
- ✅ Clear blocker identification (if any)
- ✅ Metrics visibility (test %, coverage %, etc)
- ✅ Resource requests (if support needed)

**Time Limit:** 15 minutes = ~2 min per team

---

## 📊 AGGREGATED STANDUP STATUS

**Facilitator (PO)** combines all team reports at end of standup for:

**Overall Sprint Status:**
```
Day X Summary (DD/MM/YYYY):

AC Progress:      Y/42 (X%)  [green/yellow/red based on X%]
Test Pass Rate:   Y%         [must be ≥95%]
Code Coverage:    Y%         [must reach 90% by 05/03]
Performance P95:  Yms        [must be <500ms by 05/03]
Blocker Count:    Y          [must be ≤1 to stay green]

Go/No-Go Status:  [GREEN/YELLOW/RED based on all above]
Risk Level:       [LOW/MEDIUM/HIGH]
Actions Required: [List if any]

Tomorrow's Focus: [Top 3 priorities]
```

---

## 🚨 ESCALATION TRIGGERS

**Auto-escalate if any of these occur:**

| Trigger | Escalate To | Timeline |
|---------|-------------|----------|
| Test pass rate <95% for >1 day | QA Lead | +4h |
| Coverage drops below 85% | Eng Sr / ML Expert | +4h |
| Performance >500ms P95 | Eng Sr | +2h |
| >2 blockers on same team | Team Lead → PO | +1h |
| AC completion behind >10% | PO → Head Delivery | +2h |
| Critical defect found | QA → CTO | Immediate |
| Member sick/unavailable | Team Lead → Manager | Immediate |

---

**Sprint 1 Daily Standup Protocol:** ✅ **READY**  
**First Standup:** 27/02/2026 @ 15:00 BRT  
**Duration:** 15 minutes  
**Format:** Async (Slack) + Optional Sync (Zoom)  

Use template above for consistency across all 9 standups (27/02-05/03).

