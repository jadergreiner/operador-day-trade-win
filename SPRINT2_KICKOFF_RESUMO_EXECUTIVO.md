# 🚀 SPRINT 2 - ATIVIDADES & PRIORIDADES

**Status:** ✅ **PRONTO PARA EXECUÇÃO**
**Squad:** 8 personas
**Objetivo:** Phase 2 Execution & Deployment (Capital escalation 50k → 100k)
**Format:** Organizado por **Prioridade** (P0 > P1), não por datas

---

## 📊 VISÃO GERAL

```
┌─────────────────────────────────────────────────┐
│        SPRINT 2: PHASE 2 EXECUTION               │
├─────────────────────────────────────────────────┤
│                                                 │
│  3 TASKS PARALELAS:                            │
│  ├─ P0-1: ENG-003 - MT5 REST API               │
│  ├─ P1-1: ML-003 - Feature Analysis            │
│  └─ P0-2: ML-004 - Extended Backtest           │
│           (bloqueado até ENG-003 pronto)       │
│                                                 │
│  GATES CRÍTICOS:                                │
│  ├─ GATE 1: ENG-003 + ML-003 completos         │
│  └─ GATE 2: ML-004 completo + UAT sign-off     │
│                                                 │
│  🚀 GO-LIVE: Quando tudo pronto                │
│     Capital: R$ 50k → R$ 100k (if GATE 2 GO)  │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 🎯 TAREFAS (3 Tasks P0)

### Task 1: ENG-003 - MT5 REST API Implementation
**Priority:** P0 (CRÍTICO)
**Lead:** Eng Sr (Backend)
**Squad:** 3 Backend Developers
**Status:** Ready for execution

**O que entregar:**
- FastAPI REST server com 5 endpoints core
- OAuth 2.0 authentication
- Async order queue (RabbitMQ)
- WebSocket real-time positions
- Error handling + retry logic
- 100% unit/integration/E2E tests
- Performance: P95 latency < 200ms

**Critérios de Sucesso (8 ACs):**
- AC-1: Authentication valida credenciais MT5
- AC-2: Token refresh sem re-auth
- AC-3: Orders enviados async (non-blocking)
- AC-4: Retry logic (3x exponential backoff)
- AC-5: Order status tracked real-time
- AC-6: Positions updated < 100ms (WebSocket)
- AC-7: Account balance updated 30s
- AC-8: Healthcheck inclui todas dependencies

---

### Task 2: ML-003 - Feature Importance Analysis
**Priority:** P1 (IMPORTANTE)
**Lead:** ML Expert
**Squad:** ML Expert + Data Scientist
**Status:** Ready for execution

**O que entregar:**
- SHAP values (top 10 features identified)
- Correlation matrix analysis (24×24)
- Drift detection rules (3 rules: mean shift, distribution, correlation)
- Threshold sensitivity analysis
- Production monitoring config
- Detailed reports (20+ pages)

**Critérios de Sucesso (18 ACs):**
- AC-1 through AC-18 covering:
  - Feature importance ranking
  - Correlation pairs (r > 0.8)
  - Drift alert rules
  - Monitoring thresholds
  - Explainability for traders

---

### Task 3: ML-004 - Extended Backtest (252 Trading Days)
**Priority:** P0 (CRÍTICO)
**Lead:** ML Expert
**Dependency:** Espera ENG-003 estar pronto
**Status:** Bloqueado até ENG-003 completo

**O que entregar:**
- 252-day historical backtest (1 year)
- Performance metrics (Sharpe, Win Rate, Drawdown)
- Monthly breakdown + consistency analysis
- Feature importance during trades
- Market regime analysis
- Detailed reports (20+ pages)

**Critérios de Sucesso (GATE 2 - 20 ACs):**
- **AC-10: Sharpe ratio >= 1.0** ✅
- **AC-11: Win rate >= 59%** ✅
- **AC-12: Drawdown < 15%** ✅
- AC-13 through AC-20: Consistency, reports, visualizations

---

## � SEQUÊNCIA DE EXECUÇÃO (SEM DATAS)

### Execução Paralela:
```
┌────────────────────────────────────────────┐
│ Track 1: ENG-003 (Infrastructure)          │
│ ├─ Design & architecture                  │
│ ├─ Authentication layer                   │
│ ├─ Order execution endpoints              │
│ ├─ Position tracking service              │
│ ├─ Error handling & retry logic           │
│ └─ Integration testing                    │
│    WHEN DONE: Unblocks ML-004             │
│                                           │
│ Track 2: ML-003 (Analytics)                │
│ ├─ SHAP values computation                │
│ ├─ Correlation analysis                   │
│ ├─ Drift detection rules                  │
│ ├─ Alert thresholds                       │
│ └─ Monitoring configuration               │
│    NO DEPENDENCIES                        │
│                                           │
│ Track 3: ML-004 (Validation)               │
│ ├─ Wait: ENG-003 complete                 │
│ ├─ Load 252-day data                       │
│ ├─ Run backtest simulation                │
│ ├─ Compute metrics (Sharpe, WR, DD)      │
│ └─ Generate reports                       │
│    GATE 2 DECISION POINT                  │
└────────────────────────────────────────────┘
```

---

## 🎯 GATES & DECISÕES CRÍTICAS

### 🟢 GATE 1: ENG-003 + ML-003 Complete

**Critérios de Go:**
- ✅ ENG-003: 8/8 AC passing
- ✅ ML-003: 18/18 AC passing
- ✅ Integration: API ↔ Model tested
- ✅ Performance: API P95 latency < 500ms
- ✅ Code review: 2+ reviewers approved

**Decision:**
- **GO:** Start ML-004 imediatamente
- **CONDITIONAL GO:** Minor fixes (1-2 AC), rework 1-2 dias
- **NO-GO:** Major issues, rework 3+ dias, retry GATE 1

---

### 🟢 GATE 2: ML-004 Complete + UAT Ready

**Critérios de Go (MUST ALL PASS):**
- ✅ Sharpe ratio >= 1.0
- ✅ Win rate >= 59%
- ✅ Max drawdown < 15%
- ✅ Monthly consistency < 30% std
- ✅ 20/20 AC passing
- ✅ Trader UAT sign-off
- ✅ All reports approved

**Decision (Capital Activation):**
- **GO:** Ativar R$ 100k Phase 2 capital
- **CONDITIONAL GO:** Sharpe >= 0.95 ou WR >= 58%, mais analysis
- **REWORK:** < 2 criteria met, return to dev
- **NO-GO:** Time expired ou < 1 criteria, delay Phase 2

---

## 👥 SQUAD ALLOCATION

| Role | Name | Hours | Tasks |
|------|------|-------|-------|
| **Eng Sr** | Senior Engineer | 48h | ENG-003 (design + lead) |
| **Dev 1** | Backend Dev | 40h | ENG-003 (Auth + Orders) |
| **Dev 2** | Backend Dev | 40h | ENG-003 (Positions + WS) |
| **Dev 3** | Backend Dev | 40h | ENG-003 (Queue + retry) |
| **ML Expert** | ML Lead | 48h | ML-003 + ML-004 |
| **Data Sci** | Data Scientist | 40h | ML-003 + ML-004 |
| **QA Lead** | Test Lead | 32h | Testing + validation |
| **Test Eng** | Test Engineer | 32h | Test automation |
| **DevOps** | DevOps Eng | 16h | Infrastructure |
| **Total** | 8 personas | 336h | (21 days × 16 h/day) |

---

## 📊 MÉTRICAS DE SUCESSO

### Sprint 2 Overall Goals
```
Code Delivery:
✅ 800 LOC API code
✅ 400 LOC ML analysis code
✅ 600 LOC test code
✅ Total: 1,800 LOC novo

Documentation:
✅ API specification (OpenAPI/Swagger)
✅ Feature importance report (20 pages)
✅ Extended backtest report (20 pages)
✅ Monitoring config + rules

Quality:
✅ 100% unit test coverage
✅ 8/8 integration tests passing
✅ 5/5 E2E tests passing
✅ Load test: 100 req/sec sustained

Testing:
✅ Code review: 2+ reviewers
✅ Performance: P95 < 200ms (API)
✅ Reliability: 99.9% uptime
✅ Security: HTTPS + OAuth 2.0
```

### GATE 2 Decision Metrics
```
BACKTEST VALIDATION:
  Sharpe Ratio:       >= 1.0     (target: risk-adjusted returns)
  Win Rate:           >= 59%     (target: probability of profit)
  Max Drawdown:       < 15%      (target: risk control)
  Consistency:        < 30% std  (target: regularity)

EXPECTED PERFORMANCE:
  Daily Avg Return:   +0.25% - 0.35%
  Monthly P&L:        R$ 3,700 - 5,200
  Annual Return:      +60% - +88%
  Risk-Adjusted:      Sharpe 1.0+ (excellent)
```

---

## ⚠️ RISCOS & MITIGAÇÕES

| Risk | Impact | Mitigation |
|------|--------|-----------|
| MT5 API unstable | P0 | Mock server, retry logic, circuit breaker |
| Model overfitting | P0 | Out-of-sample validation, CV included |
| Data gaps (holidays) | P1 | Validate completeness, exclude holidays |
| Performance degradation | P1 | Load testing, monitoring alerts |
| Token expiry during trading | P2 | Auto-refresh, long-lived cache |

---

## 📚 DOCUMENTAÇÃO

Todos os arquivos de especificação estão prontos:

1. **SPRINT2_KICKOFF_DASHBOARD.py** (Executável)
   - Overview, timeline, gates, success criteria
   - Gera SPRINT2_DASHBOARD.json

2. **SPRINT2_TASK_ENG003_MT5_API.py** (Executável)
   - Especificação técnica completa (API spec)
   - 8 acceptance criteria
   - Timeline + risk mitigation

3. **SPRINT2_TASK_ML003_FEATURE_ANALYSIS.py** (Executável)
   - SHAP analysis, correlation, drift detection
   - 18 acceptance criteria
   - Monitoring config

4. **SPRINT2_TASK_ML004_EXTENDED_BACKTEST.py** (Executável)
   - 252-day backtest specification
   - GATE 2 decision criteria
   - 20 acceptance criteria

---

## ✅ PRÉ-FLIGHT CHECKLIST

**Antes de começar:**

- [x] Especificações técnicas finalizadas
- [x] Squad alocado (8 personas)
- [x] Documentação pronta
- [x] Git repository setup
- [x] Monitoring/logging setup
- [x] Staging environment ready
- [x] Historical data available (252 days)
- [x] Model saved from Sprint 1 (scale_pos_weight=1.476)
- [x] Risk framework documented
- [x] Trader briefing agendado

---

## 🎓 KEY INSIGHTS FROM SPRINT 1

**Aplicar em Sprint 2:**

1. **Model Tuning:** scale_pos_weight=1.476 é ótimo - NÃO MUDAR
2. **Threshold:** 0.30 é well-positioned - considerar sensitivity analysis
3. **Overfitting:** Gap de 28% é aceitável para finance - monitor via CV
4. **CV Stability:** std=0.0233 é excelente - expect similar in backtest
5. **Testing:** 7/7 tests passing = confiança alta no modelo

---

## 🚀 PRÓXIMOS PASSOS

### Para Começar Agora:

1. **Time Assembly**
   - Confirmar todas as 8 personas são
   - Briefar sobre atividades (not datas!)
   - Clarify AC criteria

2. **Environment Validation**
   - API repo setup
   - Dependencies installed
   - All services running (MT5 mock, RabbitMQ, Redis, PG)

3. **Development Starts**
   - ENG-003: API scaffold + auth
   - ML-003: Data loading + SHAP
   - First commits

### Checkpoints (When Ready, No Dates):

- **After ENG-003 done:** GATE 1 review
- **After ML-004 done:** GATE 2 review + capital decision
- **If GATE 2 GO:** Production deployment + Phase 2 activation

### Daily Ritual:

- [ ] Standup: 15:00 UTC (15 min)
- [ ] Blocker identification
- [ ] Progress update
- [ ] Next priorities

---

## 📞 CONTATOS & ESCALAÇÃO

| Role | Contact | Escalation |
|------|---------|-----------|
| **Sprint Lead** | Eng Sr | - |
| **Tech Lead (API)** | Eng Sr | CTO |
| **ML Lead** | ML Expert | Head Data |
| **QA Lead** | QA Lead | Test Manager |
| **Product Owner** | PO | CFO (capital approval) |

**Standups:** Daily 15:00 UTC
**Gates:** 05/03 & 10/03 17:00 UTC (formal reviews)
**Escalation:** Immediate if blockers detected

---

## 🎊 STATUS FINAL

**Sprint 2 está 100% pronto para execução**

- ✅ Especificações técnicas completas
- ✅ Squad alocado (8 personas)
- ✅ Gates bem definidos (GATE 1, GATE 2)
- ✅ Riscos mitigados
- ✅ Documentação síncrona
- ✅ Format: **Activity-First** (prioridades, não datas)

**Próximo step:** Kick off quando squad estiver ready.

---

*Format: Activity-First (No Dates, Priority-Based)*
