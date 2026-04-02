# Emergency Rollback Procedure

**Situação:** Sistema em erro crítico, revert necessário
**Data:** 08/03/2026
**Responsável de Execução:** CTO / Eng Sr (com aprovação CFO)
**Janela SLA:** < 10 minutos

---

## Cenários de Rollback

### Cenário 1: Dados Corrompidos (CRÍTICO)

**Sintomas:**

- Database access denied
- Corrupt SQLite file
- Transação incompleta
- Data integrity check failed

**Se descoberto ANTES de go-live (08:00-15:00):**

```bash
# Step 1: Parar tudo (5 segundos)
taskkill /F /IM python.exe 2>/dev/null || killall python

# Step 2: Verificar backup (10 seg)
ls -la data/db/backups/ | head -5
# Esperado: backups recentes com timestamp

# Step 3: Restaurar do backup pré-launch (30 seg)
copy data\db\backups\trading_20260310_prelaunch.db data\db\trading.db /Y

# Step 4: Verificar integridade (20 seg)
sqlite3 data/db/trading.db "PRAGMA integrity_check;"
# Esperado: "ok"

# Step 5: Reiniciar sistema (30 seg)
python -m src.application.services.trading_orchestrator --test-db

# Step 6: Validar (20 seg)
python -c "
import sqlite3
conn = sqlite3.connect('data/db/trading.db')
cursor = conn.execute('SELECT COUNT(*) FROM sqlite_master WHERE type=\"table\";')
tables = cursor.fetchone()[0]
print(f'✅ Database restored: {tables} tables found')
"
```

**Decision Point:**
- ✅ **Se leitura OK:** Continue para go-live (reporte ao CTO)
- ❌ **Se Still Corrupt:** Goto Cenário 3 (Rollback Completo)

**Documentar:**

```bash
git log --oneline -5 > data/logs/rollback_backup_restore_20260310.log
echo "Rollback: Database restored from prelaunch backup" >> data/logs/rollback_backup_restore_20260310.log
```

---

### Cenário 2: Model Loading Failure (CRÍTICO)

**Sintomas:**
- "Error loading model: file not found"
- Model weights corrupted
- Feature schema mismatch
- Inference crashes

**Se descoberto ANTES de go-live:**

```bash
# Step 1: Identify last known good model (10 seg)
ls -la data/models/
# Look for: xgboost_v1.0.pkl.bak or xgboost_v0.9.pkl

# Step 2: Check backup exists
if [ ! -f "data/models/xgboost_v1.0.pkl.bak" ]; then
  echo "ERROR: No backup found. Goto Scenario 3"
  exit 1
fi

# Step 3: Restore from backup (5 seg)
copy data\models\xgboost_v1.0.pkl.bak data\models\xgboost_v1.0.pkl /Y

# Step 4: Test model loading (15 seg)
python -c "
from src.ml.backtest_server_xgboost import load_model
try:
  m = load_model('data/models/xgboost_v1.0.pkl')
  print('✅ Model loaded successfully')
except Exception as e:
  print(f'❌ Model still broken: {e}')
  exit(1)
"

# Step 5: Rerun backtest validation (30 seg)
python scripts/backtest_optimizado.py --test-only --skip-plot

# Step 6: Decision
# Expected: 14/14 tests PASS
# If yes: Model restored, continue
# If no: Goto Scenario 3
```

**Decision Point:**
- ✅ **Se 14/14 tests PASS:** Continue to go-live
- ❌ **Se tests FAIL:** Goto Cenário 3

---

### Cenário 3: Completo Rollback (MÁXIMA EMERGÊNCIA)

**Ativação:** Aprovação SIMULTÂNEA de CTO + CFO obrigatória
**Janela de Decisão:** < 5 minutos
**Consequência:** Adiamento de go-live para 11/03 ou 12/03

**Procedimento:**

```bash
# FASE 1: Parar tudo (2 min)
echo "INICIANDO ROLLBACK COMPLETO - $(date)" >> data/logs/EMERGENCY_ROLLBACK.log

# 1A: Kill all running processes
taskkill /F /IM python.exe 2>/dev/null
sleep 2

# 1B: Backup current state (para análise pós-incident)
mkdir -p data/emergency_backups/
copy data\db\trading.db data\emergency_backups\trading_BROKEN_$(date +%Y%m%d_%H%M%S).db

# 1C: Log the action
echo "Killed all Python processes and backed up broken DB" >> data/logs/EMERGENCY_ROLLBACK.log

# FASE 2: Restore to last stable (2 min)
echo "Restoring from last known good snapshot..." >> data/logs/EMERGENCY_ROLLBACK.log

# 2A: Find latest stable backup from BEFORE 08/03
ls -la data/db/backups/trading_20260307*.db | tail -1
# Expected: backup from 07/03 or earlier

# 2B: Restore it
copy data\db\backups\trading_20260307_stable.db data\db\trading.db /Y
echo "Database restored from 20260307 backup" >> data/logs/EMERGENCY_ROLLBACK.log

# 2C: Restore model from backup
copy data\models\xgboost_v0.8.pkl data\models\xgboost_v1.0.pkl /Y
echo "Model rolled back to v0.8" >> data/logs/EMERGENCY_ROLLBACK.log

# 2D: Clear all caches
rm -rf __pycache__/ data/cache/* config/__pycache__/
echo "Caches cleared" >> data/logs/EMERGENCY_ROLLBACK.log

# FASE 3: Validation (1 min)
echo "Running validation suite..." >> data/logs/EMERGENCY_ROLLBACK.log

# 3A: Test DB
sqlite3 data/db/trading.db "PRAGMA integrity_check;" | grep "ok"
if [ $? -eq 0 ]; then echo "✅ DB valid"; else echo "❌ DB still broken"; fi

# 3B: Test model
python -c "
from src.ml.backtest_server_xgboost import load_model
load_model('data/models/xgboost_v1.0.pkl')
print('✅ Model OK')
" || echo "❌ Model broken"

# 3C: Test basic imports
python -c "from src import *; print('✅ Imports OK')" || echo "❌ Import error"

# FASE 4: Decision Gate (1 min)
echo "Validation complete. Awaiting CTO decision..." >> data/logs/EMERGENCY_ROLLBACK.log

# Check all three tests passed
if [ "$db_ok" == "✅ DB valid" ] && [ "$model_ok" == "✅ Model OK" ] \
  && [ "$imports_ok" == "✅ Imports OK" ]; then
  echo "✅ ROLLBACK SUCCESSFUL" >> data/logs/EMERGENCY_ROLLBACK.log
  echo "System ready for retest" >> data/logs/EMERGENCY_ROLLBACK.log
else
  echo "❌ ROLLBACK INCOMPLETE" >> data/logs/EMERGENCY_ROLLBACK.log
  echo "Multiple systems still broken" >> data/logs/EMERGENCY_ROLLBACK.log
  echo "⚠️ MAJOR INCIDENT - Escalate to CIO" >> data/logs/EMERGENCY_ROLLBACK.log
  exit 1
fi
```

**Depois do Rollback Completo:**

1. **Immediate Actions (0-5 min):**
   - [ ] Notify all stakeholders (Slack, Teams, Email)
   - [ ] Mark incident in central log
   - [ ] CTO + CFO call for post-mortem
   - [ ] Stop all trading activity (HALT)

2. **Investigation (5-30 min):**
   - [ ] Pull emergency backup: `data/emergency_backups/`
   - [ ] Analyze root cause
   - [ ] Review git commits since last stable
   - [ ] Check system logs

3. **Next Steps (after investigation):**
   - [ ] Fix root cause
   - [ ] Rerun full test suite
   - [ ] Schedule retest (likely 09/03 morning)
   - [ ] Get new approval from all 4 gatekeepers
   - [ ] Reschedule go-live (11/03 or later)

4. **Communication Template:**

```text
Subject: INCIDENT REPORT - Emergency Rollback 10/03 14:30

SUMMARY:
- Time: 10/03 14:30 BRT
- System: Trading engine (production)
- Status: ROLLED BACK to 07/03 stable snapshot
- Impact: Go-live POSTPONED to 11/03

ROOT CAUSE: [To be determined in post-mortem]

ACTIONS TAKEN:
- Stopped all trading activity
- Restored database from 07/03
- Validated all systems passing
- Escalated to CIO

NEXT STEPS:
- Post-mortem meeting: 10/03 16:00
- Root cause analysis: 10/03 16:00-17:30
- Retest plan: 09/03 morning
- New approval gate: 10/03 18:00
```

---

## Partial Rollback Scenarios

### Rollback Only Database (Keep Model)

```bash
# If model is OK but database is corrupted:
copy data\db\backups\trading_clean.db data\db\trading.db /Y
python -c "
import sqlite3
conn = sqlite3.connect('data/db/trading.db')
print('✅ DB restored')
"
```

### Rollback Only Model (Keep Database)

```bash
# If database is OK but model is broken:
copy data\models\xgboost_v0.9.pkl data\models\xgboost_v1.0.pkl /Y
python scripts/backtest_optimizado.py --test-only
```

### Rollback Only Code (Fresh Install)

```bash
# If code is broken but data/model OK:
git checkout HEAD~1 src/  # Revert last commit
python -m pip install -r requirements.txt
python -c "from src import *; print('✅ Code OK')"
```

---

## Prevention Measures (Implemented)

✅ **Automated Backups:**
- Daily backup: 09:00 BRT
- Pre-launch backup: 08/03 12:00
- Backup verification: Automático

✅ **Testing Before Deploy:**
- Unit tests: 14/14 PASS required
- Load test: P95 <500ms required
- Model test: F1 >0.65 required
- Integration: E2E test required

✅ **Database Integrity:**
- PRAGMA integrity_check at startup
- Transaction logging enabled
- Write-ahead logging (WAL) enabled
- Vacuum scheduled weekly

✅ **Model Versioning:**
- Backup before update (filename.bak)
- Version tracking in VERSIONING.json
- Feature schema validation on load

---

## Critical Contacts (Escalation Order)

1. **CTO/Eng Sr** (FIRST - < 2 min) - Technical decision
2. **CFO/Finance** (Parallel - < 2 min) - Financial impact
3. **CIO** (If > 30 min rollback time) - Major incident
4. **CEO** (If capital at risk) - Executive notification

---

## Post-Rollback Checklist

Before attempting re-launch:

- [ ] Root cause identified and documented
- [ ] Fix verified in test environment
- [ ] All 14 tests passing again
- [ ] New backtest showing same metrics
- [ ] CTO sign-off: "Code is safe"
- [ ] CFO sign-off: "Capital protected"
- [ ] Trader confirmed: "Dashboard working"
- [ ] New go-live date scheduled
- [ ] Incident report filed

---

Document: ROLLBACK_PROCEDURE.md
Created: 08/03/2026 16:25 BRT
Status: ✅ READY FOR EMERGENCY USE

**Last Review:** 08/03 16:25
**Next Review Required:** 10/03 after go-live (if any incident)
