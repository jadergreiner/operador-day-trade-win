___
title: Tarefas de Integração - Phase 6
date: 2026-02-20
autor: Agentes Autônomos (Eng Sr + ML Expert)
status: INITIATED
target: Beta 13/03 (15 dias)
---

# 🔧 TAREFAS DE INTEGRAÇÃO - PHASE 6

**Status:** ⏳ **JUST KICKED OFF** (Seg 27/02)

**Objetivo:** Integrar completo delivery de alertas (Detectors → Fila → WebSocket
→ Clientes) + Validação de Backtesting ante de BETA.

---

## 📋 ASSIGNATION PARALELA

### Eng Sr (Senior Software Engineer) - 4 Tarefas

```
INTEGRATION-ENG-001: BDI Integration [⏳ NEXT]
 └─ Status: Ready to start
 └─ Duration: 3-4 hours
 └─ Blocker: None
 └─ Resource: src/application/services/ + config

INTEGRATION-ENG-002: WebSocket Server [✅ CREATED]
 └─ Status: Code ready (src/interfaces/websocket_server.py)
 └─ Duration: 2-3 hours (start day 2-3)
 └─ Blocker: BDI integration complete
 └─ Dependencies: FastAPI, uvicorn, asyncio

INTEGRATION-ENG-003: Email Configuration [⏳ NEXT]
 └─ Status: Ready to start (parallel)
 └─ Duration: 1-2 hours
 └─ Blocker: None
 └─ Resource: config/alertas.yaml (template ready)

INTEGRATION-ENG-004: Staging Deployment [⏳ FINAL]
 └─ Status: Queued (day 6-7)
 └─ Duration: 2-3 hours
 └─ Blocker: All Eng Sr tasks complete
 └─ Resource: Staging server + credentials
```

### ML Expert (Machine Learning Specialist) - 4 Tarefas

```
INTEGRATION-ML-001: Backtesting Setup [✅ CREATED]
 └─ Status: Script ready (scripts/backtest_detector.py)
 └─ Duration: 2-3 hours (start Monday)
 └─ Blocker: None
 └─ Resource: MT5 historical data (60 dias)

INTEGRATION-ML-002: Backtesting Validation [⏳ NEXT]
 └─ Status: Ready to run (day 2)
 └─ Duration: 2-3 hours
 └─ Blocker: Backtesting setup complete
 └─ Gate Criteria:
     • Capture rate ≥ 85%
     • False positives ≤ 10%
     • Win rate ≥ 60%

INTEGRATION-ML-003: Performance Benchmarking [⏳ NEXT]
 └─ Status: Ready to run (day 4-5)
 └─ Duration: 2-3 hours
 └─ Blocker: Backtest PASS
 └─ Metrics:
     • Latency P95 < 30s
     • Memory < 50MB
     • Throughput > 100 alerts/min

INTEGRATION-ML-004: Final Validation [⏳ FINAL]
 └─ Status: Queued (day 6-7)
 └─ Duration: 1-2 hours
 └─ Blocker: All ML tasks complete
 └─ Checks: pytest, mypy, coverage
```

---

## 🚀 TIMELINE PARALELA (27 FEB - 13 MAR)

```
SEMANA 1 (27 FEB - 01 MAR)
├─ MON 27/02:
│  ├─ Eng Sr:  🎯 BDI INTEGRATION START
│  │           └─ Locate processador_bdi.py
│  │           └─ Hook detectors into loop
│  │           └─ Load config (CONFIG-READY ✅)
│  └─ ML:      🎯 BACKTEST SETUP START
│              └─ Review backtest_detector.py (CREATED ✅)
│              └─ Setup MT5 data connection
│              └─ Configure environment
│
├─ TUE 28/02:
│  ├─ Eng Sr:  ⚙️ BDI Integration (cont'd)
│  │           └─ Test alerts generated
│  │           └─ Implement websocket_fila_integrador (CREATED ✅)
│  └─ ML:      ⚙️ Backtesting Setup (cont'd)
│              └─ Load 60-day data
│              └─ Initial test run
│
├─ WED 01/03:
│  ├─ Eng Sr:  ✅ BDI Integration DONE
│  │           🎯 WebSocket Server START
│  │           └─ Review websocket_server.py (CREATED ✅)
│  │           └─ Start uvicorn server
│  │           └─ Test /health endpoint
│  └─ ML:      ✅ Backtesting Setup DONE
│              🎯 BACKTEST VALIDATION START
│              └─ Run detector on historical data
│              └─ Check gate criteria
│              └─ Analyze results

SEMANA 2 (03 MAR - 06 MAR)
├─ MON-TUE 03-04/03:
│  ├─ Eng Sr:  ⚙️ WebSocket Server (cont'd)
│  │           └─ Multi-client broadcast tests
│  │           └─ Connection manager tests
│  └─ ML:      ⚙️ Backtest Analysis (cont'd)
│
├─ WED 05/03:
│  ├─ Eng Sr:  ✅ WebSocket DONE
│  │           🎯 EMAIL CONFIG START
│  │           └─ Setup SMTP (dev: MailHog)
│  │           └─ Config loader integration
│  └─ ML:      ✅ Backtest Validation DONE
│              🎯 PERFORMANCE BENCH START
│              └─ Profile latency
│              └─ Memory profiling
│              └─ Throughput tests
│
├─ THU-FRI 06-07/03:
│  ├─ Eng Sr:  ✅ EMAIL CONFIG DONE
│  │           🎯 STAGING DEPLOY START
│  │           └─ Code review all components
│  │           └─ Validate imports
│  │           └─ Dry-run deployment
│  └─ ML:      ✅ PERFORMANCE BENCH DONE
│              🎯 FINAL VALIDATION START
│              └─ pytest all tests
│              └─ mypy type checking
│              └─ Coverage analysis

SEMANA 3 (10 MAR - 13 MAR)
├─ MON 10/03:
│  ├─ Eng Sr:  ✅ STAGING DEPLOY DONE
│  │           📋 Integration Testing START
│  └─ ML:      ✅ FINAL VALIDATION DONE
│              📋 Metrics Summary START
│
├─ TUE 11/03:
│  ├─ Both:    🔍 Final Validation Sprint
│  │           └─ E2E testing on staging
│  │           └─ CFO metrics review
│  │           └─ Team sign-off
│
├─ WED 12/03:
│  ├─ Both:    🎯 Go-Live Preparation
│  │           └─ Production deployment prep
│  │           └─ Runbook finalized
│  │           └─ Rollback plan ready
│
└─ THU 13/03:
   └─ 🚀 BETA LAUNCH - ALL SYSTEMS GO
      ├─ Production deployment
      ├─ Client notifications
      ├─ Real-time monitoring
      └─ Success metrics tracking
```

---

## 📦 DELIVERABLES CRIADOS (Phase 6 Kickoff)

### ✅ Eng Sr Deliverables (Just Created)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `src/interfaces/websocket_server.py` | 270 | FastAPI WebSocket server, broadcast, health | ✅ Created |
| `src/interfaces/websocket_fila_integrador.py` | 85 | Fila → WebSocket middleware | ✅ Created |
| `tests/test_websocket_server.py` | 180 | Unit + integration tests | ✅ Created |

**Total Eng Sr (Phase 6-New):** 535 LOC

### ✅ ML Expert Deliverables (Just Created)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `scripts/backtest_detector.py` | 320 | Historical data backtest script | ✅ Created |
| `scripts/test_imports.py` | 15 | Import validation helper | ✅ Created |

**Total ML Expert (Phase 6-New):** 335 LOC

### ✅ Existing Code (Phase 4 - Available for Integration)

| Component | Files | Status | Used By |
|-----------|-------|--------|---------|
| Detectors | 2 files | ✅ Ready | BDI integration |
| Config System | 1 file | ✅ JUST CREATED | All services |
| Delivery | 1 file | ✅ Ready | Fila → WebSocket |
| Fila | 1 file | ✅ Ready | Alerts processing |
| Audit | 1 file | ✅ Ready | Logging |
| Tests | 2 files | ✅ Ready | Validation |

---

## 🎯 IMMEDIATE ACTIONS (MON 27/02)

### Eng Sr TODO:

```bash
# 1. Locate BDI processor
find . -name "*bdi*.py" -o -name "*processador*.py"

# 2. Review config system (READY)
cat src/infrastructure/config/alerta_config.py

# 3. Start BDI integration
# - Import detectors
# - Import config
# - Hook into vela processing

# 4. Test imports
python scripts/test_imports.py

# 5. Git push first work
git add -A
git commit -m "feat: WebSocket server + fila integrador + backtest setup"
```

### ML Expert TODO:

```bash
# 1. Review backtest script (CREATED)
cat scripts/backtest_detector.py

# 2. Validate imports
python scripts/test_imports.py

# 3. Setup MT5 connection
# - Install MetaTrader5 package
# - Configure credentials
# - Test data fetch

# 4. Initial backtest run
python scripts/backtest_detector.py

# 5. Analyze results vs gate criteria
```

---

## 🔐 CONFIGURATION REFERENCE

### Config Files Location:
- Template: `config/alertas.yaml`
- Loader: `src/infrastructure/config/alerta_config.py`
- Usage: `from infrastructure.config import get_config`

### Example Usage:
```python
from infrastructure.config import get_config

config = get_config()
print(config.detection.volatilidade.threshold_sigma)  # 2.0
print(config.delivery.websocket.url)  # ws://localhost:8765
```

### Environment Variables:
```bash
# Configurar antes de rodar
export ALERTAS_CONFIG_PATH="config/alertas.yaml"
export EMAIL_SMTP_PASSWORD="seu-password"
export WEBSOCKET_TOKEN="jwt-token-prod"
```

---

## ✅ SUCCESS CRITERIA

### Phase 6 Integration Complete When:

**Eng Sr Tasks:**
- [ ] BDI processor integration done (alerts generating)
- [ ] WebSocket server running on port 8765
- [ ] Email configuration validated (dev + prod)
- [ ] Staging deployment successful
- [ ] All 14 system tests passing

**ML Expert Tasks:**
- [ ] Backtesting script running without errors
- [ ] Gate criteria validation complete (≥85% capture)
- [ ] Performance benchmarking done (P95 <30s)
- [ ] Final validation (pytest, mypy, coverage)
- [ ] Metrics summary ready for CFO

**Combined:**
- [ ] E2E test: Detection → Fila → WebSocket → Client ✅
- [ ] Latency validation: Alert delivery <500ms (WS), <8s (Email)
- [ ] Audit logging: All events registered (CVM compliant)
- [ ] Team confidence level >90%
- [ ] CFO sign-off for BETA 13/03

---

## 📞 ESCALATION / BLOCKERS

| Item | Owner | Escalate If | Action |
|------|-------|-------------|--------|
| BDI location unknown | Eng Sr | Not found after 1h | Search codebase or create |
| Mt5 data unavailable | ML | Error fetching data | Use mock data + iterate |
| WebSocket perf issues | Eng Sr | Latency >2s | Profile + optimize |
| Backtest fails gate | ML | Capture <85% | Adjust detector params |

---

## 📊 METRICS TRACKING

**Daily Standup Checklist:**

```
Date: ___/___
Eng Sr Status: [ ] On track [ ] Delayed [ ] Blocked
ML Status:     [ ] On track [ ] Delayed [ ] Blocked

Eng Sr Tasks:
  - BDI Integration:        □ 0%  □ 25%  □ 50%  □ 75%  □ 100%
  - WebSocket Server:       □ 0%  □ 25%  □ 50%  □ 75%  □ 100%
  - Email Config:           □ 0%  □ 25%  □ 50%  □ 75%  □ 100%
  - Staging Deployment:     □ 0%  □ 25%  □ 50%  □ 75%  □ 100%

ML Expert Tasks:
  - Backtest Setup:         □ 0%  □ 25%  □ 50%  □ 75%  □ 100%
  - Backtest Validation:    □ 0%  □ 25%  □ 50%  □ 75%  □ 100%
  - Performance Bench:      □ 0%  □ 25%  □ 50%  □ 75%  □ 100%
  - Final Validation:       □ 0%  □ 25%  □ 50%  □ 75%  □ 100%

Blockers: _________________
Next Actions: _________________
```

---

**Próximos Passos:** BOTH START MONDAY (27/02) 🚀

