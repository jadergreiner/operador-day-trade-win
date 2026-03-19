# 🚀 PHASE 2 - Orquestração 3 Agentes Paralelos

**Kickoff:** Após AC5.10 complete
**Duração Estimada:** 6-8 semanas
**Coordenação:** Tech Lead + Daily Standups
**Branch:** feature/roadmap-diarios-phase2

---

## 🤖 3 Agentes Especializados

### 1️⃣ **Agente: Signals & Observability**
**Lead:** Eng Sr focused on watchdogs/health
**Módulos:** 3 (1.050+ LOC total)

```
ROADMAP-DIARIOS-01: Watchdog Advanced
├── thread_watchdog_advanced.py (350 LOC)
│   ├── ThreadWatchdog service (heartbeat monitoring)
│   ├── Deadlock detection (timeout + stalled threads)
│   ├── Recovery mechanisms (restart + escalation)
│   └── Health metrics (persisted)
├── diarios_health_monitor.py (350 LOC)
│   ├── HealthMonitor service (system state)
│   ├── Multi-component health (DB, threads, feeds)
│   ├── Health dashboard JSON + Markdown
│   └── Alert thresholds (configurable)
└── logging_recovery_handler.py (350 LOC)
    ├── LoggingRecoveryService (resilience)
    ├── Buffer + durability (in-process queue)
    ├── Rotation + cleanup (old logs)
    └── Integration with diarios

📊 Tests: 22 (unit) + 15 (integration) = 37 total
🎯 Target Coverage: ≥85%
⏱️ Estimated: 18-22 hours (4-5 days parallel)
✅ Acceptance: All 37 tests PASSED, mypy clean, <1% performance overhead
```

**Dependencies:**
- ✅ AC5.8 (TradeOutcome for thread management)
- ✅ AC5.9 (FeedbackValidator for health state)

---

### 2️⃣ **Agente: Storytelling & Narrative**
**Lead:** ML Expert focused on persistence + correlation
**Módulos:** 5 (1.750+ LOC total)

```
ROADMAP-DIARIOS-02: Trading Storytelling (Persistence)
├── narrative_persistence.py (350 LOC)
│   ├── NarrativePersistenceService
│   ├── Structured narrative storage (SQLite)
│   ├── ACID transactions + rollback
│   └── Narrative versioning + audit trail
└── trade_narrative_correlator.py (400 LOC)
    ├── TradeNarrativeCorrelator
    ├── Link trade outcomes → narrative events
    ├── Build narrative chains (causal)
    └── Export correlated dataset

📊 Tests: 18 + 20 = 38 total
🎯 Target Coverage: ≥85%
⏱️ Estimated: 20-24 hours (4-5 days)

ROADMAP-DIARIOS-03: AI Reflection Evolution
├── reflection_question_evolution.py (400 LOC)
│   ├── QuestionEvolutionEngine
│   ├── Generate adaptive reflective questions
│   ├── Learn from trader responses
│   └── Emergent question themes
├── narrative_dataset_exporter.py (300 LOC)
│   ├── NarrativeDatasetExporter
│   ├── Export structured dataset for training
│   ├── Feature engineering (narrative features)
│   └── Quality validation
└── reflection_action_channel.py (300 LOC)
    ├── ReflectionActionChannel
    ├── Link reflections → trading actions
    ├── Measure impact on performance
    └── Feedback loop closure

📊 Tests: 16 + 14 + 12 = 42 total
🎯 Total for DIARIOS-02+03: 80 tests, ≥85% coverage
⏱️ Estimated: 22-28 hours (5-6 days parallel with DIARIOS-01)

**Depends on:**
- ✅ AC5.8 + AC5.9 (narrative context)
- ⏳ AC5.10 (feedback → narrative triggers)
```

---

### 3️⃣ **Agente: ML Ops & Guardian**
**Lead:** ML Expert focused on retraining + coordination
**Modules:** 6 (2.100+ LOC total)

```
ROADMAP-DIARIOS-04: RL Retraining Scheduler
├── rl_retrain_scheduler.py (400 LOC)
│   ├── RLRetrainScheduler service
│   ├── Episode batching (N episodes → retrain trigger)
│   ├── Performance degradation detection
│   ├── Schedule + execute retrain jobs
│   └── Model versioning (save best, fallback)
└── rl_episode_quality_scorer.py (350 LOC)
    ├── EpisodeQualityScorer
    ├── Score each RL episode (confidence, PnL, etc.)
    ├── Aggregate quality metrics
    └── Feed back to scheduler

📊 Tests: 20 + 18 = 38 total

ROADMAP-DIARIOS-05: Guardian Universal (AI Coordination)
├── guardian_agent_coordinator.py (450 LOC)
│   ├── GuardianAgentCoordinator (central orchestrator)
│   ├── Manage 4 RL agents (isolation + coordination)
│   ├── Prevent conflicts (orders, positions)
│   ├── Collective decision making (voting)
│   └── Shared resource allocation
└── multi_agent_conflict_resolver.py (350 LOC)
    ├── ConflictResolver
    ├── Detect potential conflicts
    ├── Apply resolution strategies
    └── Log + audit all decisions

📊 Tests: 22 + 16 = 38 total

ROADMAP-DIARIOS-06: Order Manager Learner
├── order_manager_learner.py (400 LOC)
│   ├── OrderManagerLearner (meta-learner)
│   ├── Learn order execution patterns
│   ├── Adapt SL/TP based on history
│   ├── Slippage prediction
│   └── Fill rate optimization
└── execution_pattern_analyzer.py (300 LOC)
    ├── ExecutionPatternAnalyzer
    ├── Analyze historical executions
    ├── Detect edge cases + learn
    └── Update execution strategies

📊 Tests: 20 + 18 = 38 total
🎯 Total for DIARIOS-04+05+06: 114 tests, ≥85% coverage
⏱️ Estimated: 20-25 hours (4-5 days parallel)

**Depends on:**
- ✅ AC5.8 + AC5.9 + AC5.10 (full feedback loop)
- 🤝 Coordination with Agentes 1+2
```

---

## 📅 Timeline (Gantt-style)

```
Week 1 (20-24 Mar):
  Mon 20:  AC5.10 complete ✅ → Phase 2 kickoff
  Tue-Sat: 3 Agentes parallel setup
           ├─ Agente 1: Test stubs (DIARIOS-01)
           ├─ Agente 2: Test stubs (DIARIOS-02/03)
           └─ Agente 3: Test stubs (DIARIOS-04/05/06)

Week 2-3 (27 Mar - 07 Apr):
  Mon 27:  Daily standups start (15:00 BRT)
  Tue+:    Implementation phase (RED → GREEN)
           Parallel: Test failures → implementation
           Integration: Partial feature handoffs

Week 4 (10 Apr):
  ├─ GATE 1: All 250+ tests PASSED
  ├─ Performance validation
  ├─ Type safety (mypy clean)
  └─ Code review + merge

Week 5 (17 Apr):
  ├─ Integration testing (all 3 agentes)
  ├─ Staging deployment
  └─ UAT ready

Week 6 (20 Apr):
  └─ 🚀 PRODUCTION GO-LIVE
```

---

## 🎯 Success Criteria (Phase 2)

✅ **Code:**
- 250+ tests PASSED (37+80+114)
- Coverage ≥85% (all 3 agentes)
- mypy --strict: 0 errors
- All docstrings 100% português

✅ **Integration:**
- 4 RL agents coordinated (Guardian)
- Storytelling fully persistent
- Watchdogs < 1% overhead
- Feedback loop closed (AC5.8→AC5.9→AC5.10→Phase2)

✅ **Operability:**
- 4 new BAT launchers (1 per agente type)
- Dashboard updated (health, narratives, RL metrics)
- On-call runbook prepared
- Monitoring alerts configured

✅ **Business:**
- Win rate maintained ≥65%
- Return to capital ≥300%
- Operational overhead < 5% fees

---

## 📊 Resource Allocation

| Agente | Lead | Hours/Week | Parallelism | Total |
|--------|------|-----------|------------|-------|
| Signals (1) | Eng Sr | 4-5h | 100% | 18-22h |
| Storytelling (2) | ML Expert | 5-6h | 100% | 22-28h |
| ML Ops (3) | ML Expert | 4-5h | 100% | 20-25h |
| **Tech Lead (Coord)** | **Tech Lead** | **8-10h/week** | **100%** | **40h** |

**Total: 100-110 hours Phase 2 work (6-8 weeks with 3 parallel teams)**

---

## 🔄 Daily Coordination (15:00 BRT)

**Standup Format:**
1. **Agente 1:** Watchdog status + blockers
2. **Agente 2:** Narrative progress + dependencies
3. **Agente 3:** ML Ops + Guardian updates
4. **Tech Lead:** Sync status + integration points
5. **Breakout:** 1:1s if needed

**Escalation Path:**
- Issue → Agente lead (15 min)
- Blocker → Tech Lead (1h max)
- Architecture → CTO review (async)

---

## 📋 Pre-Requisites for 20/03 Kickoff

- [x] AC5.10 COMPLETE (code + tests)
- [ ] Phase 2 infra scaffolding (this document)
- [ ] Test stubs for all 3 agentes (250+ tests)
- [ ] Fixtures prepared (AC5.8+AC5.9+AC5.10 data)
- [ ] CI/CD updated (new test paths)
- [ ] Monitoring prep (new metrics)
- [ ] On-call scheduling (3 agentes rotation)

---

## 🚀 Kickoff Agenda (20/03 09:00 BRT)

1. **Welcome + alignment** (10 min)
   - Recap AC5.10 completion
   - Phase 2 strategic goals
   - Commitment + risks

2. **Technical walkthrough** (20 min)
   - Module structure overview
   - Dependency graph (3 agentes)
   - Integration points

3. **Day 1 tasks assignment** (10 min)
   - Agente 1: start test stubs
   - Agente 2: start test stubs
   - Agente 3: start test stubs
   - Tech Lead: CI/CD + monitoring

4. **Q&A + breakout** (10 min)

---

**Status:** 🟢 **INFRASTRUCTURE READY**
**Next:** Create test stubs (by 20/03 morning) → Start implementation
