# DEPLOYMENT RUNBOOK — Profit Protection v2

**Data Criação:** 02/04/2026
**Versão:** 1.0
**Status:** Ready for Production

---

## 📋 1. PRÉ-DEPLOY CHECKLIST

Executar ANTES de qualquer deploy em produção:

```bash
□ MT5 Terminal conectado e autenticado
□ Todas as posições rastreadas e visíveis
□ Backup de config feito: config/profit_protection.yaml.backup_<timestamp>
□ Backup de DB feito: data/db/trading.db.backup_<timestamp>
□ Branch: claude/youthful-mcclintock validado localmente
□ Testes: 32/32 profit_protection tests passando
□ Staging validation: AC-V1 PASSOU (zero MT5 side effects)
□ Logs configurados: data/logs/ com rotation policy
□ Alertas: Telegram/Email configurados para emergência
□ Team notificado: Trader, CIO, CFO informados
```

### Emergency Contacts

| Role | Contact | Purpose |
|------|---------|---------|
| Trader | ... | Halt ordens, manual override |
| CIO | ... | Technical decision, rollback approval |
| CFO | ... | Capital reallocation if needed |

---

## 🚀 2. DEPLOY PROCEDURE (Production)

### Passo 1: Backup Completo

```bash
# Backup configs
cp config/profit_protection.yaml \
   config/profit_protection.yaml.backup_$(date +%Y%m%d_%H%M%S)

# Backup database
cp data/db/trading.db \
   data/db/trading.db.backup_$(date +%Y%m%d_%H%M%S)

# Stash local changes
git stash
```

### Passo 2: Deploy Code

```bash
# Pull latest from main
git fetch origin main
git checkout main -- src/application/profit_protection_engine.py
git checkout main -- scripts/agente_rl_direto_independente.py
git checkout main -- scripts/agente_com_supervision.py

# Ou checkout entire branch para main (quando pronto)
# git checkout main
# git merge claude/youthful-mcclintock
# git push origin main
```

### Passo 3: Validar & Restart

```bash
# Validar sintaxe
python -m py_compile scripts/agente_rl_direto_independente.py
python -m py_compile scripts/agente_com_supervision.py

# Parar agentes antigos
pkill -f agente_rl_direto_independente.py
pkill -f agente_com_supervision.py
sleep 5

# Restart com nova versão
python scripts/agente_rl_direto_independente.py > logs/rl_direto_$(date +%Y%m%d).log 2>&1 &
python scripts/agente_com_supervision.py > logs/rl_5000_$(date +%Y%m%d).log 2>&1 &

# Verificar logs por erros
sleep 10
tail -50 logs/rl_direto_*.log | grep -i "error\|exception\|traceback"
tail -50 logs/rl_5000_*.log | grep -i "error\|exception\|traceback"
```

### Passo 4: Post-Deploy Validation

```bash
# Verificar processamento
□ RL 5000 agente rodando? (check PID)
  ps aux | grep agente_com_supervision.py | grep -v grep

□ RL Direto agente rodando? (check PID)
  ps aux | grep agente_rl_direto_independente.py | grep -v grep

□ Proteção ativa? (check logs)
  grep -i "processar_protecao" logs/rl_direto_*.log | tail -5
  grep -i "processar_protecao" logs/rl_5000_*.log | tail -5

□ Posições abertas?
  grep -i "posicao.*aberta" logs/rl_direto_*.log | tail -3

□ Nenhum erro crítico?
  grep -i "exception\|traceback" logs/*.log | wc -l
  # Esperado: 0 linhas
```

### Passo 5: Monitor (24/7 First 72h)

```bash
# Setup monitoring alerts
watch -n 60 'tail -20 logs/rl_direto_$(date +%Y%m%d).log'
watch -n 60 'tail -20 logs/rl_5000_$(date +%Y%m%d).log'

# Key metrics to watch
□ Win rate >= 62% (benchmark) vs degradation
□ False positives <= 10% (AC requirement)
□ Break-even activations: monitor frequency
□ Performance latency: P95 < 500ms
□ Memory usage: stable, < 500MB
□ Drawdown: watch for exceeding -5% circuit breaker

# If metric degrades:
→ Trigger ROLLBACK immediately
→ Notify stakeholders
→ Collect evidence for post-mortem
```

---

## 🔄 3. ROLLBACK PROCEDURE (Emergency)

### Quando Ativar Rollback

```
Trigger ROLLBACK se QUALQUER dos seguintes ocorrer:

□ Crash do agente (app não inicia)
□ Win rate cai abaixo 55% (>5% degradation)
□ MT5 side effects detectados (ordens abertas sem autorização)
□ Memory leak (uso cresce monotonicamente)
□ Latência P95 > 1000ms (2x target)
□ Qualquer exception não capturada nos logs
```

### Rollback Steps

**Passo 1: Decisão & Notificação**

```bash
# Notificar stakeholders IMEDIATAMENTE
echo "ROLLBACK TRIGGERED at $(date)" | mail cio@company.com

# Document reason
echo "ROLLBACK REASON: <specific metric degradation>" \
  > data/logs/rollback_reason_$(date +%Y%m%d_%H%M%S).txt
```

**Passo 2: Stop Current Version**

```bash
# Kill agentes em produção
pkill -f agente_rl_direto_independente.py
pkill -f agente_com_supervision.py
sleep 5

# Verify killed
ps aux | grep agente_ | grep -v grep
# Expected: empty output
```

**Passo 3: Restore Backups**

```bash
# Restore config
cp config/profit_protection.yaml.backup_LATEST \
   config/profit_protection.yaml
echo "Config restored"

# Restore database (OPTIONAL - only if data corrupted)
# cp data/db/trading.db.backup_LATEST \
#    data/db/trading.db
# echo "Database restored"
```

**Passo 4: Checkout Old Version**

```bash
# Git rollback to previous release tag
git fetch origin main
git checkout v1.0.0 -- src/application/profit_protection_engine.py
git checkout v1.0.0 -- scripts/agente_rl_direto_independente.py
git checkout v1.0.0 -- scripts/agente_com_supervision.py

# Ou completely revert if needed
# git revert --no-edit HEAD
# git push origin main
```

**Passo 5: Restart Old Version**

```bash
# Validar sintaxe versão antiga
python -m py_compile scripts/agente_rl_direto_independente.py
python -m py_compile scripts/agente_com_supervision.py

# Restart com versão prévia (SEM proteção v2)
python scripts/agente_rl_direto_independente.py \
  > logs/rl_direto_v1_rollback_$(date +%Y%m%d).log 2>&1 &

python scripts/agente_com_supervision.py \
  > logs/rl_5000_v1_rollback_$(date +%Y%m%d).log 2>&1 &

# Verificar start
sleep 10
ps aux | grep agente_ | grep -v grep
```

**Passo 6: Post-Rollback Validation**

```bash
# Verificar operação
□ Ambos agentes rodando?
  ps aux | grep agente_ | grep -v grep | wc -l
  # Esperado: 2 linhas

□ Posições continuam abertas?
  grep -i "posicao.*aberta" logs/rl_direto_v1_rollback*.log | tail -3

□ Ordens sendo executadas?
  grep -i "executor\|ordem.*enviada" logs/*.log | tail -5

□ Nenhum erro?
  grep -i "exception\|traceback" logs/rl_*_v1_rollback*.log | wc -l
  # Esperado: 0

□ Versão confirmada ao invés de v2?
  python -c "from src.application.profit_protection_engine import ProfitProtectionEngine; print('v2 still present!')" 2>&1 | grep -i "error"
  # Esperado: ImportError (profit_protection_engine não existe em v1)
```

### Post-Rollback Steps

```bash
# 1. Notify stakeholders with status
echo "ROLLBACK COMPLETE - Back to v1.0.0. Trading normal." \
  | mail cio@company.com

# 2. Create incident report
cat > data/logs/incident_report_$(date +%Y%m%d_%H%M%S).md << 'EOF'
# Rollback Incident Report

**Timestamp:** $(date)
**Trigger:** [specify which metric/error]
**Duration:** [minutes from detection to full recovery]
**Data Loss:** [none/trades affected/positions closed]
**Actions Taken:** [list steps executed]
**Next Steps:** [investigation plan]
EOF

# 3. Archive logs for investigation
mkdir -p data/logs/incidents/rollback_$(date +%Y%m%d_%H%M%S)
cp logs/*.log data/logs/incidents/rollback_*/

# 4. Schedule post-mortem
echo "Scheduling 24h post-mortem for incident analysis"
echo "Post-Mortem: $(date -d '+1 day') 10:00 BRT \n..." | mail team@company.com

# 5. Version pinning
echo "v1.0.0-stable" > .version
git commit -m "docs: Rollback to v1.0.0 - Production incident"
git push origin main
```

---

## ✅ 4. ROLLBACK VALIDATION CHECKLIST

Após rollback, validar TODAS as caixas antes de considerar "estável":

```
□ Aplicação rodando (uptime > 1h)
□ Trading continuando normalmente
□ Win rate estável (não degradado)
□ Sem crashes logs
□ Operador confirmou: operação normal
□ CFO confirmou: capital allocation segura
□ CIO confirmou: nenhum dados corrompidos
□ Incident created para post-mortem
```

---

## 📊 5. VERSION HISTORY

| Versão | Data | Status | Notas |
|--------|------|--------|-------|
| v1.0.0 | 15/03/2026 | Stable (Current) | RL Direto sem Profit Protection |
| v2.0.0 | 04/04/2026 | Production | RL Direto + Proteção Periódica |

**Rollback Path:** v2.0.0 → v1.0.0 (always available)

---

## 🔗 REFERÊNCIAS

- ADR-018: `docs/ARQUITETURA_ALVO.md#adr-018`
- Feature Spec: Notebook `notebooks/release_management_profit_protection_v2.ipynb`
- Test Evidence: `tests/unit/test_rl_direto_profit_protection_integration.py`
- Staging Results: `outputs/profit_protection_staging/validation_report.md`

**Última atualização:** 02/04/2026 18:00 BRT
**Próxima revisão:** Post-deploy (72h)
