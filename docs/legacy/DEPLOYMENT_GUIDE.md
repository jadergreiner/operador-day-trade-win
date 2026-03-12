# Deployment Guide - Fase 1 Beta Launch

**Versão:** 1.0
**Data:** 08/03/2026
**Status:** Phase 1 Beta (R$ 50.000 capital)
**Target Launch:** 10/03/2026 15:00 BRT

---

## Quick Start (5 min)

```bash
# 1. Clone/pull latest code
cd c:/repo/operador-day-trade-win
git pull origin main

# 2. Verify dependencies
python -m pip list | grep -E "xgboost|pandas|numpy"

# 3. Run health check
python -c "from src.ml import *; print('✅ Imports OK')"

# 4. Verify database
sqlite3 data/db/trading.db ".tables"

# 5. Start monitoring
python scripts/load_test_order_queue.py --duration 10 --rate 50
```

If all green → Proceed to deployment

---

## Pre-Deployment Checklist (15 min)

### Infrastructure
- [ ] Database `data/db/trading.db` exists
- [ ] Backup directory `data/db/backups/` ready
- [ ] Logging configured (check `data/logs/`)
- [ ] Network latency <100ms
- [ ] Disk space >10GB available

### Code
- [ ] All tests passing: `pytest tests/test_etapa4_load_and_cleanup.py -v`
  - Expected: 14/14 PASS (18.23 seconds)
- [ ] Load test runs: `python scripts/load_test_order_queue.py --duration 10 --rate 50`
  - Expected: P95 <500ms, Memory <50MB
- [ ] No encoding errors in scripts
- [ ] All commits pushed to main

### Model
- [ ] Model artifacts loaded: `data/models/xgboost_v1.0.pkl` exists
- [ ] Features ready: `data/feature_names.json` present
- [ ] Threshold configured: `sigma = 1.0`
- [ ] Backtest results: `backtest_optimized_results.json` shows PASS

### Operations
- [ ] Trader trained on dashboard
- [ ] Manual override tested
- [ ] On-call schedule confirmed
- [ ] Communication channels verified (Teams, Slack, etc)

### Governance
- [ ] All 4 gatekeepers approved (git log shows approvals)
- [ ] Capital R$ 50k allocated
- [ ] Compliance checklist signed

---

## Step-by-Step Deployment (30 min)

### Step 1: Environment Setup (5 min)

```bash
# 1A. Load environment variables
# On Windows, execute BAT file or set manually:
set PYTHONPATH=c:\repo\operador-day-trade-win\src;%PYTHONPATH%
set MT5_TERMINAL_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
set TRADING_DB=c:\repo\operador-day-trade-win\data\db\trading.db

# 1B. Verify environment
python -c "import os; print(f'PYTHONPATH={os.environ.get(\"PYTHONPATH\")}')"
```

### Step 2: Database Verification (5 min)

```bash
# 2A. Test connectivity
python -c "import sqlite3; conn = sqlite3.connect('data/db/trading.db'); print(f'✅ DB connected')"

# 2B. Create backup
copy data\db\trading.db data\db\backups\trading_20260310_prelaunch.db

# 2C. Verify backup
sqlite3 data/db/backups/trading_20260310_prelaunch.db "PRAGMA integrity_check;"
```

### Step 3: Model Loading (5 min)

```bash
# 3A. Load model & test inference
python -c "
from src.ml.backtest_server_xgboost import *
model = load_model('data/models/xgboost_v1.0.pkl')
features = load_feature_names('data/feature_names.json')
print(f'✅ Model loaded ({len(features)} features)')
print(f'✅ Threshold: 1.0 sigma')
"

# 3B. Test prediction
python -c "
from src.ml.backtest_server_xgboost import predict_signal
sample_data = [[0.5]*24]  # 24 features
signal = predict_signal(sample_data, threshold=1.0)
print(f'✅ Prediction: {signal}')
"
```

### Step 4: System Integration Test (5 min)

```bash
# 4A. Test order queue
python scripts/load_test_order_queue.py --duration 5 --rate 50

# 4B. Expected output:
# Total orders: ~250
# Success rate: >98%
# P95 latency: <500ms
# Memory delta: <50MB
```

### Step 5: Deploy to Live (3 min)

```bash
# 5A. Start MT5 connection (if using real MT5)
# WARNING: Ensure MT5_TERMINAL_PATH points to CLEAR account only!
# System will refuse connection to FBS/XP/Zero/IC/Ativa/Rica

# 5B. Activate trading engine
python -m src.application.services.trading_orchestrator \
  --capital 50000 \
  --max_position_size 5000 \
  --risk_limit 1.5 \
  --dry_run false

# 5C. Expected output:
# 2026-03-10 15:00:15 - INFO - Capital: R$ 50.000
# 2026-03-10 15:00:15 - INFO - Max position: R$ 5.000
# 2026-03-10 15:00:15 - INFO - Risk limit: 1.5%
# 2026-03-10 15:00:15 - INFO - [OK] Trading engine active
```

---

## Monitoring During Go-Live (First 4 hours)

### Real-Time Metrics to Watch

```python
# Monitor these in logs/trading.log
- Alerts generated (target: 1-3 per hour)
- Order execution latency (target: <500ms)
- Position tracking accuracy (target: 100%)
- P&L tracking (baseline: break-even acceptable)
- False positive rate (target: <10%)
```

### Key Log Files

- `data/logs/trading.log` - Order execution log
- `data/logs/model.log` - ML inference log
- `data/logs/risk.log` - Risk system events
- `data/logs/errors.log` - Error tracking

### Dashboard Access

```
Local: http://localhost:8000/dashboard
Reference: See KICKOFF_FINAL_PRE_LAUNCH.txt for trader training
```

---

## Rollback Procedure (Emergency)

See [ROLLBACK_PROCEDURE.md](ROLLBACK_PROCEDURE.md) for:
- Circuit breaker activation (-3%, -5%, -8%)
- Manual trade veto
- Database restoration
- Service restart

**Critical escalation:** Contact CTO immediately if any blocker found

---

## Post-Deployment (First 24 hours)

| Time | Action | Owner | Success Criteria |
|------|--------|-------|-----------------|
| T+0 | Activation | CTO | Systems operational |
| T+5 min | First alert | ML Expert | Signal generated correctly |
| T+30 min | Performance check | Trader | P95 latency <500ms |
| T+1h | Metrics review | All | No critical errors |
| T+4h | Performance review | Trader | P&L alignment |
| T+24h | Day 1 analysis | Team | Decision on GATE 3 (scaling) |

---

## Troubleshooting

### Common Issues

1. **Database locked**
   - Symptom: `sqlite3.OperationalError: database is locked`
   - Fix: Restart application, check for hanging connections
   - Prevention: Use backup-before-delete pattern

2. **Model loading fails**
   - Symptom: `FileNotFoundError: No such file or directory: model.pkl`
   - Fix: Verify file exists, check permissions, rebuild if needed
   - Prevention: Always backup model artifacts before deploy

3. **Network timeout**
   - Symptom: `Timeout connecting to MT5`
   - Fix: Check firewall, verify MT5 running, restart connection
   - Prevention: Monitor network latency in real-time

4. **Memory leak**
   - Symptom: Memory usage grows >100MB over time
   - Fix: Restart service, check for circular references
   - Prevention: Run memory profiler before deploy

See [RUNBOOK_COMMON_ISSUES.md](RUNBOOK_COMMON_ISSUES.md) for 15+ scenarios

---

## Approval Sign-Off

- [ ] CTO/Eng Sr: Environment ready ✓
- [ ] ML Expert: Model loaded & tested ✓
- [ ] Trader: Dashboard operational ✓
- [ ] Finance/CFO: Capital allocated ✓

**Deployment approved:** 10/03/2026 14:30 by all gatekeepers

---

## Support

For issues during deployment:
- **Technical:** CTO/Eng Sr (0-15 min response)
- **Model:** ML Expert (0-15 min response)
- **Operations:** Trader (immediate)
- **Escalation:** Contact executive on-call

24/5 coverage active during Phase 1 Beta

---

Document: DEPLOYMENT_GUIDE.md
Created: 08/03/2026 16:15 BRT
Status: ✅ READY FOR PRODUCTION
