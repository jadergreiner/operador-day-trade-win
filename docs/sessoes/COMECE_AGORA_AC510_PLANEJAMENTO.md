# 🎯 AC5.10 ML/RL Feedback Integration - Planejamento Executivo

**Objetivo:** Finalizador Phase 1 - integrar AC5.8 + AC5.9 com ML/RL feedback loop
**Estimativa:** 4-5 horas
**Checkpoint Target:** 100% Phase 1 completion
**Status:** ⏳ PLANEJAMENTO

---

## 📋 Contexto

### Dependências Resolvidas ✅

- **AC5.8 (Trade Outcome Reconciler):** ✅ COMPLETE (15/15 testes)
  - Fornece: `TradeOutcome` entities, reconciliation status
  - Output: SQLite persistence

- **AC5.9 (Feedback Validator):** ✅ COMPLETE (15/15 testes)
  - Fornece: `FeedbackValidationResult` com correlation + health scores
  - Output: JSON + Markdown reports

### AC5.10 Função Crítica

**Ponte entre Execução (AC5.8+AC5.9) ← → Aprendizado (ML/RL)**

```
┌──────────────────┐
│   AC5.8 Outcome  │ (trade reconciliation)
│  +              │
│   AC5.9 Feedback │ (validation health)
└───────┬──────────┘
        │
        ▼
┌──────────────────────────────────────────┐
│   AC5.10 Integration Service  🔄         │
│  1. Validate correlation                 │
│  2. Route to ML pipeline (≥80% quality)  │
│  3. Route to RL trainer (degradation OK) │
│  4. Persist metrics + logs               │
│  5. Generate integration report          │
└───────┬──────────────────────────────────┘
        │
        ├─→ ML Pipeline (retraining trigger)
        ├─→ RL Scheduler (new episodes)
        └─→ Metrics DB (feedback loop health)
```

---

## 🎯 Requirements AC5.10 (10 Acceptance Criteria)

| AC | Requirement | Tipo | Prioridade |
|----|-------------|------|-----------|
| **AC5.10.1** | Consume FeedbackValidationResult from AC5.9 | Code | P0 |
| **AC5.10.2** | Consume TradeOutcome records from AC5.8 | Code | P0 |
| **AC5.10.3** | Coordinate ML pipeline trigger (when feedback quality ≥80%) | Logic | P0 |
| **AC5.10.4** | Coordinate RL training trigger (when performance degrades >5%) | Logic | P0 |
| **AC5.10.5** | Persist feedback loop metrics to SQLite | Persistence | P1 |
| **AC5.10.6** | Generate integration report (JSON + Markdown) | Report | P1 |
| **AC5.10.7** | Handle errors with retry + fallback | Resilience | P1 |
| **AC5.10.8** | Feedback routing latency <1s (P95) | Performance | P2 |
| **AC5.10.9** | Detailed logging per feedback batch | Observability | P2 |
| **AC5.10.10** | Idempotent processing (no duplicate training triggers) | Safety | P2 |

---

## 📂 Estrutura de Entrega

### Arquivos a Criar

```
src/application/
├── ml_rl_feedback_integration.py       ← Main service (350-400 LOC)
│   ├── FeedbackIntegrationService
│   ├── PipelineRoutingDecision
│   ├── IntegrationMetrics (dataclass)
│   └── Helper functions

tests/
├── test_ac5_10_ml_rl_integration.py    ← Tests (300-350 LOC)
│   ├── TestFeedbackIntegration (10 tests)
│   └── TestIntegrationMetrics
```

### Dependências Externas

- `src.application.trade_outcome_reconciler` (AC5.8)
- `src.application.feedback_validator` (AC5.9)
- `sqlite3` (SQLite persistence)
- Mocked: ML pipeline, RL scheduler (stubs)

---

## 🧪 Test Plan (10 Tests)

| Test | AC Ref | Tipo | Objective |
|------|--------|------|-----------|
| test_consume_trade_outcomes | AC5.10.2 | Unit | Parse TradeOutcome correctly |
| test_consume_feedback_validation | AC5.10.1 | Unit | Parse FeedbackValidationResult correctly |
| test_route_to_ml_pipeline_quality_ok | AC5.10.3 | Unit | Trigger ML when correlation ≥80% |
| test_route_to_rl_trainer_degradation | AC5.10.4 | Unit | Trigger RL when perf < threshold |
| test_skip_training_quality_low | AC5.10.3 | Unit | Don't trigger ML when feedback <80% |
| test_persist_metrics_to_sqlite | AC5.10.5 | Integration | Metrics saved correctly |
| test_generate_integration_report | AC5.10.6 | Unit | JSON + Markdown formats correct |
| test_error_handling_retry | AC5.10.7 | Unit | Retry on transient errors |
| test_idempotency_duplicate_feedback | AC5.10.10 | Unit | No duplicate training triggers |
| test_performance_feedback_routing | AC5.10.8 | Performance | Latency <1s (benchmark) |

---

## 📈 Implementation Timeline (4-5 hours)

### Phase 1: Setup (30 min)
- [ ] Create test file with 10 test stubs
- [ ] Create fixtures for AC5.8 + AC5.9 data
- [ ] Add pytest markers

### Phase 2: RED Phase (30 min)
- [ ] Run tests → expect import errors
- [ ] Verify all 10 tests in RED state

### Phase 3: GREEN Phase (2-2.5 hours)
- [ ] Implement FeedbackIntegrationService class
- [ ] Implement routing logic (ML + RL)
- [ ] Implement persistence layer
- [ ] Implement report generation
- [ ] Run tests → fix failures iteratively

### Phase 4: REFACTOR + Validation (1-1.5 hours)
- [ ] Add docstrings + type hints
- [ ] Run mypy --strict (expect 0 errors)
- [ ] Calculate coverage (target ≥85%)
- [ ] Code review + cleanup

### Phase 5: Integration + Commit (30 min)
- [ ] Git add + commit
- [ ] Update BACKLOG with completion
- [ ] Document for Phase 2 teams

---

## ✅ Success Criteria

- ✅ 10/10 tests PASSED
- ✅ Coverage ≥85%
- ✅ mypy --strict: 0 errors
- ✅ Integration with AC5.8 + AC5.9 validated
- ✅ metrics persisted to SQLite
- ✅ Reports generated (JSON + Markdown)
- ✅ Performance <1s verified
- ✅ 1-2 commits with clear messages
- ✅ Documentation complete

---

## 🔄 Parallelism with Phase 2

**While AC5.10 implementation ongoing:**

- Phase 2 infra teams can prepare module scaffolding
- Agente 1 (Signals) prepares ROADMAP-DIARIOS-01 stubs
- Agente 2 (Storytelling) prepares ROADMAP-DIARIOS-02/03 stubs
- Agente 3 (ML Ops) prepares ROADMAP-DIARIOS-04/05/06 stubs
- Tech Lead: Orquestração + CI/CD prep

**Target:** AC5.10 COMPLETE by 20/03 EOD
**Phase 2 START:** 20/03 morning (infrastructure ready)

---

## 📝 Notes

- AC5.10 is **last module of Phase 1** (integration finalizer)
- Not complex logic, mostly orchestration + routing
- Heavy reuse of AC5.8 + AC5.9 patterns (TDD, fixtures, etc.)
- Small technical debt: ML/RL stubs needed for mocking
- Strategic: clears path for 4 parallel Phase 2 agentes

---

**Status:** 🟢 **READY FOR IMPLEMENTATION**
**Next:** Create test stubs tomorrow morning + execute TDD cycle
