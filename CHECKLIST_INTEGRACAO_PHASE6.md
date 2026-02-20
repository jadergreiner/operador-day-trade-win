---
title: Checklist Integração Phase 6
date: 2026-02-20
status: READY
last_updated: 2026-02-20T14:30:00Z
---

# ✅ CHECKLIST INTEGRAÇÃO PHASE 6

**Objetivo:** Garantir que todas as tarefas de integração sejam completadas
com qualidade antes de BETA 13/03.

---

## 📋 PRÉ-INTEGRAÇÃO (MON 27/02)

### Setup Environment

- [ ] Python 3.9+ instalado e verificado
  ```bash
  python --version  # 3.9+
  ```

- [ ] Virtual environment ativo
  ```bash
  python -m venv venv
  source venv/Scripts/activate  # Windows
  ```

- [ ] Dependencies instaladas
  ```bash
  pip install -r requirements.txt
  pip install fastapi uvicorn pytest pytest-asyncio  # Extras Phase 6
  ```

- [ ] Git status clean
  ```bash
  git status  # Nada uncommitted
  ```

### Code Review - Eng Sr

- [ ] Revisar `src/interfaces/websocket_server.py` (270 LOC)
  - [ ] ConnectionManager logic sound
  - [ ] Broadcast error handling OK
  - [ ] Health check endpoint present
  - [ ] Type hints 100%

- [ ] Revisar `src/interfaces/websocket_fila_integrador.py` (85 LOC)
  - [ ] Processo async worker OK
  - [ ] Error handling robust
  - [ ] Singleton pattern correct

- [ ] Revisar `tests/test_websocket_server.py` (180 LOC)
  - [ ] Test fixtures configured
  - [ ] Mocks usados corretamente
  - [ ] Coverage >80%

### Code Review - ML Expert

- [ ] Revisar `scripts/backtest_detector.py` (320 LOC)
  - [ ] Data loading logic OK
  - [ ] Detector integration correct
  - [ ] Metrics calculation accurate
  - [ ] Error handling comprehensive

- [ ] Revisar `src/infrastructure/config/alerta_config.py` (260 LOC)
  - [ ] Pydantic schemas valid
  - [ ] YAML loader functional
  - [ ] Env var resolution works
  - [ ] Type hints complete

---

## 🏗️ TASK-BY-TASK CHECKLIST

### INTEGRATION-ENG-001: BDI Integration

**Status:** ⏳ Ready to start

```
[ ] Find BDI processor file
    [ ] Search for processador_bdi.py OR similar
    [ ] If not found:
        [ ] Create new file: src/application/services/processador_bdi.py
        [ ] Start with skeleton class

[ ] Import detectors
    [ ] from application.services.detector_volatilidade import DetectorVolatilidade
    [ ] from application.services.detector_padroes_tecnico import DetectorPadroesTecnico
    [ ] from application.services.alerta_formatter import AlertaFormatter
    [ ] from infrastructure.providers.fila_alertas import FilaAlertas
    [ ] from infrastructure.config.alerta_config import get_config

[ ] Load config in __init__
    [ ] config = get_config()
    [ ] Setup detector params from config

[ ] Hook into vela loop
    [ ] After BDI analysis, call detectors
    [ ] Handle alerts returned
    [ ] Add to fila_alertas

[ ] Test locally
    [ ] python src/application/services/processador_bdi.py
    [ ] Verify no import errors
    [ ] Check alerts generated

[ ] Git commit
    [ ] git add -A
    [ ] git commit -m "feat: BDI integration com detectors"
    [ ] git push

Estimated Time: 3-4 hours
Success: Alerts generated in console
```

### INTEGRATION-ENG-002: WebSocket Server

**Status:** ✅ Code ready, testing next

```
[ ] Start uvicorn server
    [ ] cd src/interfaces
    [ ] python -m uvicorn websocket_server:app --host 0.0.0.0 --port 8765
    [ ] Verify: "Uvicorn running on http://0.0.0.0:8765"

[ ] Test health endpoint
    [ ] curl http://localhost:8765/health
    [ ] Expected: {"status": "ok", "active_connections": 0, ...}

[ ] Test metrics endpoint
    [ ] curl http://localhost:8765/metrics
    [ ] Expected: {"active_connections": 0, "status": "running"}

[ ] Test config endpoint
    [ ] curl http://localhost:8765/config
    [ ] Expected: {"version": "1.1.0", "features": {...}}

[ ] Test WebSocket connection (manual or tool)
    [ ] Use wscat or similar: wscat -c ws://localhost:8765/alertas
    [ ] Should connect successfully
    [ ] Should stay open (await messages)

[ ] Run unit tests
    [ ] pytest tests/test_websocket_server.py -v
    [ ] Expected: All tests pass (7+)

[ ] Run with BDI integration
    [ ] Start BDI processor separately
    [ ] Verify alerts flow to WebSocket
    [ ] Check client receives messages

[ ] Stress test
    [ ] Simulate 10 concurrent clients
    [ ] Send 100 alerts/sec for 30s
    [ ] Monitor: Memory, CPU, latency

[ ] Git commit integration
    [ ] git add -A
    [ ] git commit -m "feat: WebSocket server integrado com BDI"
    [ ] git push

Estimated Time: 2-3 hours
Success: Clients receive alerts <500ms
```

### INTEGRATION-ENG-003: Email Configuration

**Status:** Ready, can start in parallel

```
[ ] Setup development email
    [ ] Option A: Install MailHog (mock SMTP)
      [ ] Download MailHog binary
      [ ] Run: mailhog
      [ ] Access UI at http://localhost:1025
    [ ] OR Option B: Use existing SMTP server

[ ] Configure config/alertas.yaml
    [ ] Set email.smtp.host = "localhost" or prod SMTP
    [ ] Set email.smtp.port = 1025 or prod port
    [ ] Set email.smtp.user = "dev" or prod user
    [ ] Set email.recipients = ["operador@example.com"]

[ ] Test email delivery
    [ ] Trigger alert manually
    [ ] Check MailHog UI or email inbox
    [ ] Verify format (HTML bootstrap)

[ ] Test fallback path
    [ ] Disable WebSocket temporarily
    [ ] Trigger alert
    [ ] Verify email sent as fallback

[ ] Test retries
    [ ] Break SMTP connection
    [ ] Trigger alert
    [ ] Watch retries with exp. backoff (1s, 2s, 4s)

[ ] Production secrets
    [ ] Export env vars:
      [ ] export EMAIL_SMTP_PASSWORD="prod-password"
      [ ] export WEBSOCKET_TOKEN="prod-jwt"
    [ ] Verify config reads from env

[ ] Git commit
    [ ] git add -A
    [ ] git commit -m "feat: Email config com fallback"
    [ ] git push

Estimated Time: 1-2 hours
Success: Email delivers <8s with retry logic
```

### INTEGRATION-ML-001: Backtesting Setup

**Status:** ✅ Script ready, setup next

```
[ ] Install MT5 package
    [ ] pip install MetaTrader5
    [ ] OR: Use mock data (already in script)

[ ] Configure MT5 connection (if using real data)
    [ ] Launch MT5 terminal
    [ ] Enable DLL imports: Tools → Options → Experts → Allow DLL
    [ ] Get API credentials

[ ] Load 60-day historical data
    [ ] Run: python scripts/backtest_detector.py
    [ ] Expected output:
      [ ] "Carregados XXXX velas"
      [ ] "Processadas XXX/XXXX velas"
      [ ] Final report with metrics

[ ] Validate data loaded
    [ ] Check: First vela timestamp ~60 days ago
    [ ] Check: Last vela timestamp ~now
    [ ] Check: ~17,280 velas (60 days × 288 M5/day)

[ ] Check for import errors
    [ ] Run: python scripts/test_imports.py
    [ ] Expected: "Configuração carregada: ..."

[ ] Debug any import issues
    [ ] Check sys.path includes src/
    [ ] Verify alerta_config.py exists
    [ ] Check relative imports

[ ] Git commit
    [ ] git add -A  
    [ ] git commit -m "feat: Backtest setup com dados históricos"
    [ ] git push

Estimated Time: 2-3 hours
Success: 60-day data loaded, no errors
```

### INTEGRATION-ML-002: Backtesting Validation

**Status:** Ready to run

```
[ ] Run detector on historical data
    [ ] python scripts/backtest_detector.py
    [ ] Watch console output for progress

[ ] Analyze results
    [ ] Check metrics:
      [ ] Taxa captura ≥ 85% ✓
      [ ] Taxa FP ≤ 10% ✓
      [ ] Win rate ≥ 60% ✓

[ ] If PASS (all 3 gates):
    [ ] ✅ Status = PASS
    [ ] Proceed to Performance Benchmarking
    [ ] Document pass in report

[ ] If FAIL (any gate):
    [ ] ❌ Status = FAIL
    [ ] Debug detector parameters
    [ ] Adjust config:
      [ ] Increase window (reduce noise) OR
      [ ] Lower threshold_sigma (increase sensitivity) OR
      [ ] Change confirmacao_velas
    [ ] Re-run backtest
    [ ] Iterate until PASS

[ ] Document issues & fixes
    [ ] If failure: Note adjustment made
    [ ] Save iteration result

[ ] Check result JSON
    [ ] cat backtest_results.json
    [ ] Verify all metrics present
    [ ] Share with CFO for approval

[ ] Git commit results
    [ ] git add backtest_results.json
    [ ] git commit -m "feat: Backtest validation PASS [gates met]"
    [ ] git push

Estimated Time: 2-3 hours
Success: All 3 gates PASS, report saved
```

### INTEGRATION-ML-003: Performance Benchmarking

**Status:** Ready after backtest PASS

```
[ ] Profile latency
    [ ] Install: pip install cProfile pstats
    [ ] Create profiler script
    [ ] Run: python -m cProfile -o profile_latency.prof script.py
    [ ] Analyze: pstats profile_latency.prof
    [ ] Check: P95 < 30s, P99 < 60s

[ ] Profile memory
    [ ] Install: pip install tracemalloc
    [ ] Add to script:
      [ ] import tracemalloc
      [ ] tracemalloc.start()
      [ ] ... run detector ...
      [ ] current, peak = tracemalloc.get_traced_memory()
      [ ] print(f"Memory: {peak / 1024 / 1024:.1f} MB")
    [ ] Target: < 50MB peak

[ ] Measure throughput
    [ ] Count alerts/minute over 5 min run
    [ ] Calculate: alerts_per_minute
    [ ] Target: > 100 alerts/min

[ ] CPU profiling
    [ ] Monitor: top or Process Explorer while running
    [ ] Target: < 10% average CPU

[ ] Latency distribution
    [ ] Collect 1000+ latency samples
    [ ] Create histogram
    [ ] Calculate: P50, P95, P99
    [ ] Export: performance_metrics.json

[ ] Load test
    [ ] Simulate 10 concurrent clients
    [ ] Send 100 alerts for 2 minutes
    [ ] Monitor: Memory, CPU, latency stability
    [ ] Expected: No degradation

[ ] Document findings
    [ ] Create performance_report.md
    [ ] Include: Metrics, graphs, recommendations

[ ] Git commit benchmarks
    [ ] git add performance_metrics.json
    [ ] git add performance_report.md
    [ ] git commit -m "feat: Performance benchmarks [all targets met]"
    [ ] git push

Estimated Time: 2-3 hours
Success: All performance targets met
```

### INTEGRATION-ENG-004: Staging Deployment

**Status:** Ready after other Eng Sr tasks

```
[ ] Code review all components
    [ ] Review BDI integration code
    [ ] Review WebSocket server code
    [ ] Review config system code
    [ ] Look for potential issues

[ ] Static analysis
    [ ] Run: mypy src/ --strict
    [ ] Expected: 0 errors
    [ ] Run: pylint src/ --disable=all
    [ ] Look for critical issues only

[ ] Unit test validation
    [ ] Run: pytest tests/test_alertas_unit.py -v
    [ ] Expected: 8/8 pass ✓

[ ] Integration test validation
    [ ] Run: pytest tests/test_alertas_integration.py -v
    [ ] Expected: 3/3 pass ✓

[ ] WebSocket test validation
    [ ] Run: pytest tests/test_websocket_server.py -v
    [ ] Expected: 7+/7+ pass ✓

[ ] Deploy to staging
    [ ] Copy code to staging server
    [ ] Configure staging env vars
    [ ] Install dependencies: pip install -r requirements.txt
    [ ] Start services:
      [ ] BDI processor
      [ ] WebSocket server (port 8765)
      [ ] Database connection

[ ] Sanity checks
    [ ] curl http://staging:8765/health → 200 OK
    [ ] Test WebSocket connection → Connected
    [ ] Send test alert → Received in client

[ ] E2E test on staging
    [ ] Connect operator client
    [ ] Trigger alert from BDI
    [ ] Verify:
      [ ] Alert generated
      [ ] Queued properly
      [ ] Delivered to client <500ms
      [ ] Logged in audit DB

[ ] Rollback test
    [ ] Break one component (e.g., database)
    [ ] Verify system degrades gracefully
    [ ] Email fallback works
    [ ] No data loss

[ ] Performance on staging
    [ ] Run: backtest_detector.py on staging
    [ ] Check metrics match pre-staging baseline

[ ] Git commit staging
    [ ] git add -A
    [ ] git commit -m "feat: Staging deployment ready for UAT"
    [ ] git push

Estimated Time: 2-3 hours
Success: All tests pass, E2E flow works
```

### INTEGRATION-ML-004: Final Validation

**Status:** Ready after backtest + performance

```
[ ] Run all unit tests
    [ ] pytest tests/ -v --tb=short
    [ ] Expected: 11/11 tests pass ✓
    [ ] If any fail: Debug + fix

[ ] Type checking
    [ ] Run: mypy src/ --strict
    [ ] Expected: 0 type errors
    [ ] If errors: Fix type hints

[ ] Coverage analysis
    [ ] Run: pytest tests/ --cov=src --cov-report=html
    [ ] Check: coverage > 80%
    [ ] If < 80%: Add more tests

[ ] Lint check (Python)
    [ ] Run: pylint src/ --disable=all --enable=E,F
    [ ] Expected: 0 critical errors
    [ ] If errors: Fix & re-run

[ ] Doc validation
    [ ] Check: All functions have docstrings
    [ ] Check: Docstrings are Portuguese
    [ ] Check: Examples present where needed

[ ] Manual E2E flow
    [ ] Start all services
    [ ] Connect client
    [ ] Generate alert manually
    [ ] Trace through system:
      [ ] Detector triggers ✓
      [ ] Alert queued ✓
      [ ] WebSocket sent ✓
      [ ] Client received ✓
      [ ] Audit logged ✓

[ ] Backward compatibility
    [ ] Old clients still work? ✓
    [ ] Old config format compatible? ✓

[ ] Security review
    [ ] No hardcoded secrets? ✓
    [ ] Env vars used for sensitive data? ✓
    [ ] WebSocket token validation present? ✓
    [ ] Input sanitization done? ✓

[ ] Create final report
    [ ] Summary: All gates PASS
    [ ] Metrics: Performance targets met
    [ ] Tests: 100% passing
    [ ] Type safety: 100% coverage
    [ ] Ready for production

[ ] Team sign-off
    [ ] Eng Sr approves code
    [ ] ML Expert approves algorithms
    [ ] DevOps approves deployment
    [ ] PO approves features
    [ ] CFO approves launch

[ ] Git commit final
    [ ] git add -A
    [ ] git commit -m "feat: Final validation complete - ready for BETA 13/03"
    [ ] git push
    [ ] git tag -a v1.1.0-beta -m "Beta release - 13 March 2026"
    [ ] git push origin v1.1.0-beta

Estimated Time: 1-2 hours
Success: All validations pass, team signed off
```

---

## 🎯 GATES & APPROVALS

### Technical Gates

- [ ] **BDI Integration:** Alerts generating in production frequency
- [ ] **WebSocket Server:** Clients receive messages <500ms consistently
- [ ] **Backtesting:** All 3 criteria pass (Capture ≥85%, FP ≤10%, Win ≥60%)
- [ ] **Performance:** All targets met (Latency P95 <30s, Memory <50MB)
- [ ] **Tests:** 100% passing (18+ tests)
- [ ] **Type Safety:** 100% type hints, mypy passes strict mode

### Business Gates

- [ ] **CFO Approval:** Financial metrics reviewed, budget approved
- [ ] **PO Sign-off:** Features match US-004 requirements
- [ ] **Compliance:** Audit logging CVM-compliant
- [ ] **Security:** All sensitive data in env vars, no hardcodes

### Deployment Gates

- [ ] **Staging:** All E2E tests pass
- [ ] **DevOps:** Infrastructure ready (WS port 8765, SSL configured)
- [ ] **Ops Team:** Monitoring + alerts configured
- [ ] **Backup Plan:** Rollback procedure documented

---

## 📊 DAILY PROGRESS TRACKER

Use this table daily (27/02 - 12/03):

```
DATE       | ENG SR STATUS | ML STATUS | BLOCKERS | NEXT ACTIONS
-----------|---------------|-----------|----------|------------------
27/02 (Mon)| BDI: 0%       | Setup: 0% | None     | Both start
28/02 (Tue)| BDI: 50%      | Setup: 80%| None     | Continue
01/03 (Wed)| BDI: ✅ DONE  | Val: 50%  | None     | WS server
02/03 (Thu)| WS: 50%       | Val: 100% | Params?  | Debug backtest
03/03 (Fri)| WS: 100%      | Perf: 50%| None     | Email config
04/03 (Sat)| Email: 50%    | Perf: 100%| None    | Staging prep
05/03 (Sun)| Email: ✅     | Final: 30%| None    | Final validation
06/03 (Mon)| Deploy: 50%   | Final: 70%| Any?    | Staging E2E
07/03 (Tue)| Deploy: ✅    | Final: ✅ | None     | Go-live prep
08-12/03   | Integration tests / UAT / Metrics tracking
13/03 (Thu)| 🚀 BETA LAUNCH - ALL SYSTEMS GO
```

---

## ✅ EOF CHECKLIST (Day Before BETA)

**Before deploying to production on 13/03:**

- [ ] All 18+ tests passing
- [ ] No TypeErrors or warning)
- [ ] No merge conflicts
- [ ] No uncommitted changes
- [ ] All secrets in env vars (nothing hardcoded)
- [ ] Audit logs enabled and verified
- [ ] Backups tested & working
- [ ] Rollback plan documented
- [ ] Team briefed on launch plan
- [ ] Monitoring dashboards configured
- [ ] On-call support ready
- [ ] Customer comms drafted
- [ ] CFO final approval obtained
- [ ] Launch checklist complete

---

**Target Completion:** ✅ Wednesday 12/03 (Day before BETA)

**Launch:** 🚀 Thursday 13/03 (BETA PRODUCTION)

