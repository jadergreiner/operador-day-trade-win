# 📋 GITHUB ISSUES - TODO RASTRACKTHROUGH (12 TODOs Mapeados)

**Data:** 23/02/2026 23:55 BRT
**Status:** ✅ TEMPLATES PREPARED
**Próxima Ação:** Criar issues no GitHub (24/02 morning)

---

## 🚀 TODO-1: Load Dataset + ML-Based Labeling

**GitHub Issue Title:**
```
[SPRINT-1] TODO-1: Load Dataset + ML-Based Labeling (ML-001) | 20h | BLOCKER
```

**Issue Template:**

```markdown
# 📊 [SPRINT-1] TODO-1: Load Dataset + ML-Based Labeling

## Description
Load backtest_optimized_results.json, apply ML-based labeling, extract 24 engineered features, and prepare training data for Grid Search (Sprint 2).

**Status:** NOT-STARTED
**Priority:** 🔴 CRITICAL (Blocker)
**Sprint:** Sprint 1 (27/02-05/03)
**Owner:** @ML-Expert
**ETA:** 2-3 days (27/02-28/02)
**Effort:** 20 hours

## Files Involved
- `src/application/ml_feature_engineer.py:447-448` (line TODO)
- `backtest_optimized_results.json` (input)
- `data/dataset_labeled.pkl` (output)

## Acceptance Criteria
1. [ ] Dataset loaded from backtest_optimized_results.json (1000+ samples)
2. [ ] ML-based labeling applied (consistency validated)
3. [ ] 24 features engineered from backtest data
4. [ ] Train/Val/Test split created (70/15/15)
5. [ ] Feature names saved in production format

## Tasks
- [ ] Load JSON file and parse backtest results
- [ ] Apply labeling algorithm (thresholds defined)
- [ ] Extract 24 features (volatilidade, momentum, patterns, etc)
- [ ] Create splits with stratification
- [ ] Run unit tests (7/7 must pass)
- [ ] Update ANALISE_PRIORIZACAO with progress
- [ ] Create backup of dataset

## Blockers
None - all prerequisites ready ✅

## Desbloqueia (Cascata)
- TODO-5: Grid search (Sprint 2)
- TODO-9: Pattern detector (v1.2)
- Gate 1: F1 score validation (05/03)

## Definition of Done
- [ ] AC 1-5 all PASS
- [ ] Unit tests 7/7 PASS
- [ ] Code review approved
- [ ] Zero TODOs/FIXMEs left
- [ ] ANALISE_PRIORIZACAO updated
- [ ] Commit pushed

## References
- [DESENVOLVIMENTO_DE_TASKS_PRIORIZADAS_SPRINT1.md](DESENVOLVIMENTO_DE_TASKS_PRIORIZADAS_SPRINT1.md)
- [EXECUTA_SOLICITA_TASK_23FEV_NOVA.md](EXECUTA_SOLICITA_TASK_23FEV_NOVA.md)
- [docs/CRITERIOS_DE_ACEITE_MVP.md](docs/CRITERIOS_DE_ACEITE_MVP.md)

## Label Suggestions
- `sprint-1`, `ml-training`, `blocker`, `data-loading`
```

---

## 🎯 TODO-2,3,4: Orders Executor Framework

**GitHub Issue Title:**
```
[SPRINT-1] TODO-2,3,4: Orders Executor Framework (ENG-002,003,004) | 25h | BLOCKER
```

**Issue Template:**

```markdown
# 🚀 [SPRINT-1] TODO-2,3,4: Orders Executor Framework

## Description
Implement Orders Executor with 3 complementary components:
- TODO-2: MT5 connection + order sending
- TODO-3: Position tracking + state machine
- TODO-4: SL/TP monitoring loop

**Status:** NOT-STARTED
**Priority:** 🔴 CRITICAL (Blocker)
**Sprint:** Sprint 1 (27/02-05/03)
**Owner:** @Eng-Sr
**ETA:** 4 days (27/02-02/03)
**Effort:** 25 hours (combined)

## Files Involved
- `src/application/orders_executor.py:133` (TODO-2)
- `src/application/orders_executor.py:158` (TODO-3)
- `src/application/orders_executor.py:188` (TODO-4)
- `src/domain/services/mt5_adapter.py` (dependency)

## Acceptance Criteria
1. [ ] MT5 connection established + authenticated
2. [ ] Orders sent successfully (async queue)
3. [ ] Positions tracked in real-time (state machine)
4. [ ] Retry mechanism (3x exponential backoff)
5. [ ] Error recovery + circuit breakers
6. [ ] Audit logging complete (CVM compliance)
7. [ ] Risk validators integrated (3 gates passing)
8. [ ] Message queue stable (no loss)
9. [ ] Performance P95 < 500ms
10. [ ] All integration tests 10/10 passing

## Sub-Tasks

### TODO-2: MT5 Connection + Order Sending
- [ ] Implement MT5Adapter.connect()
- [ ] Authenticate with broker credentials
- [ ] Create async order queue processor
- [ ] Test order placement (mock + real)
- [ ] Error handling + logging

### TODO-3: Position Tracking
- [ ] Implement state machine (10 states)
- [ ] Track open positions in real-time
- [ ] Calculate P&L per position
- [ ] Monitor entry/exit conditions
- [ ] Update dashboard via WebSocket

### TODO-4: SL/TP Monitoring
- [ ] Monitor SL levels (per position)
- [ ] Monitor TP levels (per position)
- [ ] Execute close order on trigger
- [ ] Log execution + audit trail
- [ ] Update P&L calculations

## Tests Required
- test_mt5_connection (auth + heartbeat)
- test_order_execution (queue processing)
- test_position_tracking (state machine)
- test_retry_mechanism (exponential backoff)
- test_error_recovery (circuit breaker)
- test_audit_logging (CVM format)
- test_risk_validators (all 3 gates)
- test_message_queue (throughput + loss)
- test_performance (P95 latency)
- test_e2e_integration (full flow)

## Blockers
None - design ready, dependencies met ✅

## Desbloqueia (Cascata)
- Staging Deployment (50% of precondition)
- Integration E2E tests (04/03+)
- Gate 2: Integration validation (12/03)
- Beta launch (13/03)

## Definition of Done
- [ ] AC 1-10 all PASS
- [ ] Unit tests 10/10 PASS
- [ ] Integration tests 8/8 PASS
- [ ] Code review approved by CTO
- [ ] Performance benchmarks collected
- [ ] Zero blocking bugs
- [ ] ANALISE_PRIORIZACAO updated
- [ ] Commit pushed

## References
- [DESENVOLVIMENTO_DE_TASKS_PRIORIZADAS_SPRINT1.md](DESENVOLVIMENTO_DE_TASKS_PRIORIZADAS_SPRINT1.md)
- [ARQUITETURA_INTEGRACAO_PHASE6.md](ARQUITETURA_INTEGRACAO_PHASE6.md)
- [RISK_FRAMEWORK_v1.2.md](docs/agente_autonomo/RISK_FRAMEWORK_v1.2.md)

## Label Suggestions
- `sprint-1`, `trading-execution`, `blocker`, `mt5-api`
```

---

## 🔄 TODO-5: Grid Search Parallelization

**GitHub Issue Title:**
```
[SPRINT-2] TODO-5: Grid Search Parallelization (ML-003) | 2h | OPTIMIZATION
```

**Issue Template:**

```markdown
# ⚡ [SPRINT-2] TODO-5: Grid Search Parallelization

## Description
Optimize grid search using joblib.Parallel to reduce execution time from 30+ minutes to 5-10 minutes (3x speedup).

**Status:** NOT-STARTED
**Priority:** 🟡 ALTA (Optimization)
**Sprint:** Sprint 2 (06/03-12/03)
**Owner:** @ML-Expert
**ETA:** 1-2 days (07/03-08/03)
**Effort:** 2 hours

## File
- `src/application/ml_classifier.py:452`

## Acceptance Criteria
1. [ ] Grid search parallelized (joblib.Parallel)
2. [ ] Execution time reduced 3x (30min → 10min)
3. [ ] Results identical to sequential version
4. [ ] Memory efficient (n_jobs=-1 or -2)
5. [ ] Unit tests passing (comparison test)

## Definition of Done
- [ ] AC 1-5 all PASS
- [ ] Code review approved
- [ ] Performance benchmark documented
- [ ] Commit pushed

## References
- [EXECUTA_SOLICITA_TASK_23FEV_NOVA.md](EXECUTA_SOLICITA_TASK_23FEV_NOVA.md)

## Label Suggestions
- `sprint-2`, `ml-optimization`, `performance`
```

---

## 🔧 TODO-7: Backtest Detector Integration

**GitHub Issue Title:**
```
[SPRINT-1] TODO-7: Backtest Detector Integration (ENG-005) | 1.5h | HIGH
```

**Issue Template:**

```markdown
# 🎯 [SPRINT-1] TODO-7: Backtest Detector Integration

## Description
Fix detector_padroes call in backtest pipeline to ensure correct pattern recognition flow.

**Status:** NOT-STARTED
**Priority:** 🟡 ALTA (Accuracy)
**Sprint:** Sprint 1 (02/03)
**Owner:** @Eng-Sr
**ETA:** 1.5 hours
**Effort:** Trivial

## File
- `scripts/backtest_detector.py:145`

## Acceptance Criteria
1. [ ] detector_padroes called correctly
2. [ ] Pattern recognition enabled
3. [ ] Backtest accuracy validated
4. [ ] Unit test passing
5. [ ] Results match expected metrics

## Definition of Done
- [ ] AC 1-5 all PASS
- [ ] Code review approved
- [ ] Commit pushed

## References
- [EXECUTA_SOLICITA_TASK_23FEV_NOVA.md](EXECUTA_SOLICITA_TASK_23FEV_NOVA.md)

## Label Suggestions
- `sprint-1`, `backtest`, `detector`
```

---

## 💾 TODO-6: P&L Tracker Completion

**GitHub Issue Title:**
```
[POST-LAUNCH] TODO-6: P&L Tracker Completion | 2h | MEDIUM
```

**Issue Template:**

```markdown
# 📊 [POST-LAUNCH] TODO-6: P&L Tracker Completion

## Description
Add P&L computation for unrealized gains/losses per position when market data is available.

**Status:** DEFERRED
**Priority:** 🟢 MÉDIA (Nice-to-have)
**Sprint:** Post-launch (after 10/04)
**Owner:** TBD
**Effort:** 2 hours

## File
- `src/domain/entities/portfolio.py:110`

## Acceptance Criteria
1. [ ] P&L calculation implemented
2. [ ] Unrealized G/L computed per position
3. [ ] Dashboard updated
4. [ ] Unit tests passing

## Definition of Done
- [ ] AC 1-4 all PASS
- [ ] Code review approved
- [ ] Commit pushed

## Label Suggestions
- `post-launch`, `portfolio`, `nice-to-have`
```

---

## 📝 TODO-8,9,10-12: Technical Debt

**GitHub Issue Title:**
```
[TECHNICAL-DEBT] TODO-8,9,10-12: Code Quality + Testing | 1-2h each | LOW
```

**Issue Template:**

```markdown
# 🧹 [TECHNICAL-DEBT] TODO-8,9,10-12: Code Quality

## Description
Various technical debt items for post-launch refactoring:
- TODO-8: WebSocket test coverage (test_websocket_server.py:159)
- TODO-9: Pattern detector deferred (processador_bdi.py:81)
- TODO-10-12: Various refactors (scripts, services)

**Status:** DEFERRED
**Priority:** 🟢 BAIXA (Code quality)
**Sprint:** Post-launch (Sprints 3-4)
**Owner:** Team rotation
**Effort:** 1-2 hours each

## Acceptance Criteria
- [ ] Each TODO converted to focused issue
- [ ] Test coverage improved
- [ ] Code quality improved

## Definition of Done
- [ ] AC all PASS
- [ ] Code review approved
- [ ] Commit pushed

## Label Suggestions
- `technical-debt`, `code-quality`, `post-launch`
```

---

## 🎬 PRÓXIMAS AÇÕES (24/02 MORNING)

```
1. Criar todos os 8 GitHub Issues (templates acima)
   └─ TODO-1 (BLOCKER) = Issue #XX
   └─ TODO-2,3,4 (BLOCKER) = Issue #XX
   └─ TODO-5 (Sprint 2) = Issue #XX
   └─ TODO-7 (Sprint 1) = Issue #XX
   └─ TODO-6 (Post-launch) = Issue #XX
   └─ TODO-8,9,10-12 (Debt) = Issue #XX

2. Link issues em documentação
   └─ EXECUTA_SOLICITA_TASK_23FEV_NOVA.md (seção 4)
   └─ ANALISE_PRIORIZACAO_23FEV.md (seção 4)

3. Assign personas
   └─ ML Expert: TODO-1, TODO-5
   └─ Eng Sr: TODO-2,3,4, TODO-7
   └─ QA Lead: TODO-8,9,10-12

4. Add labels
   └─ `sprint-1`, `sprint-2`, `blocker`, `ml`, `trading`, etc

5. Create GitHub Project board (if not exists)
   └─ Columns: Backlog, Ready, In Progress, Review, Done
   └─ Link all TODOs
```

---

## 📊 GITHUB ISSUES SUMMARY

| Issue # | TODO | Title | Priority | Sprint | Owner | ETA | Status |
|---------|------|-------|----------|--------|-------|-----|--------|
| TBD | 1 | Load Dataset + ML Labeling | 🔴 Blocker | 1 | ML Expert | 2d | Not-started |
| TBD | 2,3,4 | Orders Executor Framework | 🔴 Blocker | 1 | Eng Sr | 4d | Not-started |
| TBD | 5 | Grid Search Parallelization | 🟡 Alta | 2 | ML Expert | 1d | Not-started |
| TBD | 7 | Backtest Detector Integration | 🟡 Alta | 1 | Eng Sr | 1.5h | Not-started |
| TBD | 6 | P&L Tracker Completion | 🟢 Média | Post | TBD | 2h | Deferred |
| TBD | 8-12 | Technical Debt | 🟢 Baixa | Post | Team | 1-2h | Deferred |

---

**Versão:** 1.0
**Data:** 23/02/2026 23:55 BRT
**Status:** ✅ TEMPLATES READY - CRIAR ISSUES EM 24/02
