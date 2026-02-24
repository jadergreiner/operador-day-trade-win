# ✅ S3-1 PREPARAÇÃO — Production Deployment de S2-6

**Status:** 🟢 EM EXECUÇÃO (Gate 2 GO - 24/02 17:45)
**Owner:** DevOps + Infra
**Timeline:** 24/02 → 28/02 (Preparação) | 03/03+ (Execução)
**Objetivo:** Preparar ambiente de produção para S2-6 Analytics

---

## 🎯 Quick Checklist (Preparação Paralela)

### [X] Pré-requisitos Validados
- ✅ Infrastructure layer pronto
- ✅ CI/CD pipeline funcionando
- ✅ Staging environment disponível

### [ ] Passo 1: Staging Environment Setup (24/02-25/02 — 4 horas)

**O que fazer:**

```bash
# Terminal 4: Setup de Staging
cd c:/repo/operador-day-trade-win

# 1. Provisionar servidor staging
terraform apply -target aws_instance.staging -auto-approve

# 2. Deploy da aplicação
docker build -t operador-day-trade:staging .
docker push <registry>/operador-day-trade:staging

# 3. Deploy da imagem
kubectl apply -f k8s/staging/deployment.yaml

# 4. Validar health
curl https://staging.operador-day-trade.local/health
```

**Checklist:**
- [ ] Servidor staging ativo
- [ ] Container image built e pushado
- [ ] Kubernetes deployment RUNNING
- [ ] Health check PASSING

---

### [ ] Passo 2: Database Replication (25/02-26/02 — 4 horas)

**O que fazer:**

```bash
# Terminal: Setup DB replication
# Production DB → Staging DB

# 1. Backup produção
mysqldump -u prod_user -p production_db > backup_latest.sql

# 2. Restore em staging
mysql -u staging_user -p staging_db < backup_latest.sql

# 3. Validar integridade
mysql -u staging_user -p staging_db -e "SELECT COUNT(*) FROM trader_interventions;"

# 4. Monitorar replicação
watch -n 2 'mysql -e "SHOW SLAVE STATUS\G" | grep Seconds_Behind_Master'
```

**Checklist:**
- [ ] Backup criado (data/backup_latest.sql)
- [ ] Restore validado
- [ ] Row count bate com produção
- [ ] Replicação ativa e sincronizada

---

### [ ] Passo 3: Monitoring & Logging (26/02-27/02 — 4 horas)

**O que fazer:**

```bash
# Setup de observabilidade para staging

# 1. Prometheus scrape config
cat >> prometheus.yml <<EOF
- job_name: 'staging-operador'
  static_configs:
    - targets: ['staging.operador-day-trade.local:9090']
  scrape_interval: 15s
EOF

# 2. Grafana dashboard
curl -X POST http://grafana:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @grafana/dashboards/staging-analytics.json

# 3. ELK logging
filebeat test config -e -c filebeat.staging.yml

# 4. Alerting
alertmanager --config.file=alertmanager.staging.yml
```

**Dashboard Esperado:**

```
┌─ Staging Analytics Dashboard ──────────────┐
│                                             │
│ API Latency (P95): _____ms   [TARGET: 200] │
│ Error Rate: _____%   [TARGET: <1%]         │
│ DB Connections: ___   [TARGET: <50]        │
│ Memory Usage: ____MB  [TARGET: <500]       │
│ Uptime: ____days      [TARGET: 100%]       │
│                                             │
└─────────────────────────────────────────────┘
```

**Checklist:**
- [ ] Prometheus scraping metrics
- [ ] Grafana dashboards ativo
- [ ] ELK pipeline funcionando
- [ ] Alertas configurados

---

### [ ] Passo 4: Load Testing (27/02-28/02 — 4 horas)

**O que fazer:**

```bash
# Terminal: Load testing com Apache JMeter
jmeter -n -t tests/performance/analytics_load_test.jmx \
  -l tests/performance/results.jtl \
  -Jremote_server=staging.operador-day-trade.local \
  -Jnum_threads=100 \
  -Jramp_time=60 \
  -Jduration=1800

# Esperado:
# - Throughput: 500+ req/s
# - P95 latency: <200ms
# - Error rate: <1%
```

**Load Test Plan:**

```
┌─ Scenarios ────────────────┐
│                            │
│ POST /intervention/log     │
│   - 50 req/s               │
│ GET /analytics/stats       │
│   - 150 req/s              │
│ GET /dashboard             │
│   - 100 req/s              │
│ UPDATE /intervention/{id}  │
│   - 100 req/s              │
│                            │
│ Total: 400+ concurrent     │
└────────────────────────────┘
```

**Checklist:**
- [ ] Load test executado
- [ ] Resultados salvos (results.jtl)
- [ ] Throughput ≥ 500 req/s
- [ ] P95 latency ≤ 200ms
- [ ] Error rate ≤ 1%

---

### [ ] Passo 5: Disaster Recovery (28/02 — 2 horas)

**O que fazer:**

```bash
# Testar cenários de falha

# 1. Database failover
# Simular queda de DB primária
sudo systemctl stop mysql
# Validar que staging failover com sucesso

# 2. Service restart
kubectl delete pod deployment/staging-operador-xxx
# Validar que novo pod inicia automaticamente

# 3. Configuration rollback
# Se nova versão falhar:
kubectl rollout undo deployment/staging-operador

# Documentar procedimentos
curl -X POST http://docs/api/disaster-recovery \
  -d '{"scenario": "db_failover", "recovery_time_seconds": 45, "status": "PASSED"}'
```

**Checklist:**
- [ ] DB failover simulado e PASSED
- [ ] Service restart automático OK
- [ ] Rollback testado
- [ ] Documentação criada

---

## 📋 Production Deployment Schedule (03/03+)

### Pré-flight Checklist (02/03 - CTO Review)

```
DEPLOYMENT READINESS CHECKLIST
═══════════════════════════════

[ ] Code review: All changes approved
[ ] Tests: 100% PASSING on staging
[ ] Monitoring: Alerts configured
[ ] Runbook: Deployment procedure documented
[ ] Rollback: Plan documented and tested
[ ] Backup: Latest backup available
[ ] Sign-off: CTO + Head Finanças approved
```

### Deployment Steps (03/03 14:00-16:00)

```bash
# 1. Blue-Green setup
# Produção (Blue) rodando
# Deployment (Green) pronto

# 2. Health check
curl https://operador-day-trade.local/health

# 3. Gradual traffic shift
# 10% → 25% → 50% → 100%

# 4. Monitoring intensivo
# À cada etapa, validar:
#   - Error rate ≤ 1%
#   - Latency P95 ≤ 200ms
#   - No data loss

# 5. Finalização
# Se tudo OK: commit a mudança
# Se problema: instant rollback
```

### Rollback Procedure (Se necessário)

```bash
# Instant rollback se algo der errado
kubectl rollout undo deployment/prod-operador

# Validar:
curl https://operador-day-trade.local/health

# Notificar stakeholders
# Investigar erro
# Replan para próximo dia
```

---

## 📊 Dependency Graph

```
S2-4 (Fibonacci)────┐
                    ├─→ S2-5 Integration Testing
S2-6 (Analytics)────┤
                    └─→ S3-1 Production Deploy (03/03+)
```

**Sequência:**
1. ✅ S2-4 completa (25/02 06:00)
2. ✅ S2-6 completa (25/02 07:00)
3. 🔄 S2-5 integration tests (25/02-02/03)
4. 🟡 S3-1 deploy (03/03 14:00)

---

## 📊 Timeline Esperada

| Fase | Datas | Status | Owner |
|------|-------|--------|-------|
| 1. Staging Setup | 24/02-25/02 | 🟠 PENDING | DevOps |
| 2. DB Replication | 25/02-26/02 | 🟠 PENDING | DBA |
| 3. Monitoring | 26/02-27/02 | 🟠 PENDING | Infra |
| 4. Load Testing | 27/02-28/02 | 🟠 PENDING | QA |
| 5. DR Testing | 28/02 | 🟠 PENDING | DevOps |
| 6. Pre-flight | 02/03 | 🟠 PENDING | CTO |
| 7. Production Deploy | 03/03 14:00 | 🟠 PENDING | DevOps |

**Duração Total Prep:** 6 dias (24/02-02/03)
**Duração Deploy:** 2 horas (03/03 14:00-16:00)

---

## ✅ Success Criteria

- ✅ Staging 100% réplica de produção
- ✅ Load test PASSED (500+ req/s)
- ✅ Disaster recovery testado
- ✅ Rollback procedure documentado
- ✅ Team treinado em deployment
- ✅ CTO pre-flight sign-off recebido

---

## 🚨 Go/No-Go Decision (02/03 16:00)

**Critérios GO:**
- [ ] Todos testes PASSING (98%+)
- [ ] Load test P95 < 200ms
- [ ] Staging uptime > 99.5%
- [ ] Zero critical bugs
- [ ] CTO approved

**Critérios NO-GO (Defer):**
- [ ] Algum teste falhando
- [ ] Load test P95 > 250ms
- [ ] Staging downtime > 0.5%
- [ ] Bugs críticos abertos
- [ ] CTO expressed concerns

**Default:** GO (a menos que algum NO-GO critério se aplique)

---

## ✅ Próximas Ações

1. Confirmar disponibilidade DevOps (24/02 18:00)
2. Iniciar Passo 1 (Staging setup)
3. Paralelizar com S2-4 e S2-6
4. Daily standup de preparação (09:00, 15:00)

**Status:** 🔄 EM EXECUÇÃO (Preparação)

---

> Documento criado em 24/02 17:45 como parte de Gate 2 GO Approval
> Deployment efetivo: 03/03/2026 14:00 BRT
