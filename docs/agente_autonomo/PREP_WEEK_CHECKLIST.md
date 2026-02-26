# 📋 PREP WEEK CHECKLIST (27-28/02/2026)

**Objetivo:** Cada persona valida seus pré-requisitos antes do kick-off de 01/03
**Timeline:** Terça (27/02) e Quarta (28/02)
**Checkpoint:** Até 28/02 EOD, tudo deve estar 100% validado

---

## 👤 CHECKLIST BY PERSONA

### 🔧 **DevOps Lead**

#### Azure Environment
- [ ] Subscription access testado (login com `az login`)
- [ ] Bicep CLI instalado (versão ≥ 0.13)
  ```bash
  az bicep version  # deve retornar versão
  ```
- [ ] Resource group naming validado: `operador-dt-staging`
- [ ] Azure region confirmado: `eastus`
  ```bash
  az account list --query "[].homeTenantId"
  ```

#### Local Environment
- [ ] PowerShell 7+ instalado (Windows) ou bash (Linux)
  ```powershell
  $PSVersionTable.PSVersion
  ```
- [ ] Git instalado e configurado
  ```bash
  git --version
  git config --global user.name  # deve retornar nome
  ```
- [ ] SSH key configurada para repo access
  ```bash
  ssh -T git@github.com  # deve retornar sucesso
  ```

#### Bicep Validation
- [ ] Arquivo copiado: `infrastructure/staging.bicep`
- [ ] Syntax validado localmente
  ```bash
  az bicep build --file infrastructure/staging.bicep
  # deve retornar sucesso sem erros
  ```
- [ ] Parâmetros revisados e documentados
- [ ] Deployment script preparado (PHASE4_FIRST_WEEK_ACTIONS.md)

#### Documentation Review
- [ ] PHASE4_STAGING_MASTERPLAN.md lido (2h)
- [ ] PHASE4_KICKOFF_MEETING.md lido (1h)
- [ ] PHASE4_FIRST_WEEK_ACTIONS.md lido (1.5h)
- [ ] GO_LIVE_CHECKLIST.md lido (30 min)
- [ ] Notes tomadas em `prep_notes_devops.txt`

#### Sign-Off
```
[ ] Assinado: DevOps está pronto
[ ] Data: _____/_____/2026
[ ] Contato de emergência: _______________
```

---

### 👨‍💻 **Eng Sr (Tech Lead)**

#### Git & Code
- [ ] Repository clonado/atualizado
  ```bash
  git clone <repo> # ou git pull origin main
  git branch --show-current  # deve ser 'main'
  ```
- [ ] Phase 3 code compreendido
  - [ ] OAuth implementation lido (15 min)
  - [ ] WebSocket server lido (15 min)
  - [ ] XGBoost integration lido (15 min)
- [ ] Deployment procedures compreendidas
- [ ] Connection strings documentadas
  - [ ] DATABASE_URL format conhecida
  - [ ] REDIS_URL format conhecida
  - [ ] JWT_SECRET generation procedure

#### Environment Setup
- [ ] Python 3.9+ instalado
  ```bash
  python --version  # retorna ≥ 3.9
  ```
- [ ] Docker instalado (se usar containers)
  ```bash
  docker --version
  ```
- [ ] Node.js 16+ instalado (si requerido)
  ```bash
  node --version  # retorna ≥ 16
  ```
- [ ] Requirements.txt validado
  ```bash
  pip install -r requirements.txt --dry-run
  # sem erros de dependências
  ```

#### Documentation Review
- [ ] PHASE4_STAGING_MASTERPLAN.md lido (2h)
- [ ] ARQUITETURA_MT5_v1.2.md ou arq relevante (1h)
- [ ] Deployment procedures documentadas
- [ ] Risk mitigation strategies compreendidas

#### Architecture Readiness
- [ ] Deployment runbook preparado (PHASE4_FIRST_WEEK_ACTIONS.md)
- [ ] Database migration scripts verificados
- [ ] Environment variables checklist preparado
- [ ] Health check endpoints verificados
- [ ] Logging strategy confirmada

#### Sign-Off
```
[ ] Assinado: Eng Sr está pronto
[ ] Data: _____/_____/2026
[ ] Contato de emergência: _______________
```

---

### 🧠 **ML Expert**

#### Model Verification
- [ ] XGBoost models localizados no repositório
  ```bash
  ls -la models/  # listar arquivos .pkl ou .joblib
  ```
- [ ] Versão de cada modelo documentada
  - [ ] Modelo principal versão ____
  - [ ] Fallback modelo versão ____
  - [ ] Feature set versão ____
- [ ] Model size verificado (< 100MB ideal)
- [ ] Dependencies verificadas (sklearn, xgboost versions)

#### Feature Engineering
- [ ] Feature list completa (24 features)
  ```python
  # verificar que todas features carregam
  import joblib
  model = joblib.load('models/model.pkl')
  print(model.get_booster().get_score())  # deve listar features
  ```
- [ ] Feature scaling documentado (StandardScaler)
- [ ] Feature names persistidas em arquivo
- [ ] Example inference testado localmente

#### Inference Pipeline
- [ ] Prediction pipeline testado
  ```bash
  python scripts/test_inference.py
  # deve retornar prediction sem erros
  ```
- [ ] Batch prediction capacidade verificada (50+ samples)
- [ ] Latency testada (target: <100ms per prediction)
- [ ] Error handling documentado

#### Documentation Review
- [ ] ML_FEATURE_ENGINEERING_v1.2.md lido (1.5h)
- [ ] Backtest results compreendidos
- [ ] Grid search outcomes analisados
- [ ] Model performance metrics documentados

#### Sign-Off
```
[ ] Assinado: ML Expert está pronto
[ ] Data: _____/_____/2026
[ ] Contato de emergência: _______________
```

---

### 🧪 **QA Lead**

#### Load Testing Setup
- [ ] Locust instalado
  ```bash
  pip install locust
  locust --version  # retorna versão
  ```
- [ ] Arquivo `locustfile.py` revisado
- [ ] 3 cenários entendidos:
  - [ ] Scenario 1: 100 users
  - [ ] Scenario 2: 200 users
  - [ ] Scenario 3: 500 users
- [ ] Locust testado localmente (sem conectar servidor real)
  ```bash
  locust -f locustfile.py --headless --users 10 --run-time 60s
  ```

#### UAT Environment
- [ ] pytest instalado
  ```bash
  pip install pytest
  pytest --version
  ```
- [ ] UAT test suite (`uat_test_cases.py`) revisada
- [ ] 12 test cases compreendidos
  - [ ] 6 Trader tests
  - [ ] 3 CIO tests
  - [ ] 3 CFO tests
- [ ] Test data sets preparados
- [ ] Mock/fixture data documentada

#### Monitoring Dashboard
- [ ] Dashboard tool selecionado (CloudWatch, AppInsights, etc)
- [ ] Dashboards pré-criados (se possível)
- [ ] Alert rules documentadas
- [ ] Notification channels configuradas
  - [ ] Email alerts
  - [ ] Slack notifications
  - [ ] SMS (critical only)

#### CI/CD Validation
- [ ] GitHub Actions workflow visitado
- [ ] 63+ tests executados localmente com sucesso
  ```bash
  python -m pytest tests/  -v
  # todos tests devem passar
  ```
- [ ] Test report gerado
- [ ] Coverage metrics verificados (target: ≥85%)

#### Documentation Review
- [ ] PHASE4_KICKOFF_MEETING.md lido (1h)
- [ ] PHASE4_FIRST_WEEK_ACTIONS.md lido (2h)
- [ ] GO_LIVE_CHECKLIST.md lido (1h)
- [ ] UAT procedures documentadas
- [ ] Test execution timeline compreendida

#### Sign-Off
```
[ ] Assinado: QA Lead está pronto
[ ] Data: _____/_____/2026
[ ] Contato de emergência: _______________
```

---

### 🔗 **Integration Eng**

#### E2E Testing Framework
- [ ] End-to-end test suite visitada
- [ ] Integration test cases revisados
- [ ] Test execution order documentado
- [ ] Expected durações estimadas

#### Component Integration
- [ ] OAuth + WebSocket integration compreendida
- [ ] API + Database integration validada
- [ ] ML model + prediction service integration compreendida
- [ ] Monitoring + alerting integration documentada

#### Performance Testing
- [ ] Performance targets confirmados:
  - [ ] P95 latency < 500ms (500 users)
  - [ ] Memory usage < 100MB per pod
  - [ ] CPU utilization < 80%
- [ ] Profiling tools instalados (if needed)
- [ ] Baseline performance compreendida

#### Documentation Review
- [ ] PHASE4_FIRST_WEEK_ACTIONS.md lido (2h)
- [ ] PHASE4_STAGING_MASTERPLAN.md lido (2h)
- [ ] Integration test procedures compreendidas
- [ ] Executive summary da arquitetura lido

#### Sign-Off
```
[ ] Assinado: Integration Eng está pronto
[ ] Data: _____/_____/2026
[ ] Contato de emergência: _______________
```

---

### 📝 **Tech Writer**

#### Documentation Review
- [ ] Todos 5 docs de kick-off lidos (6h total)
  - [ ] PHASE4_KICKOFF_MEETING.md (1h)
  - [ ] PHASE4_FIRST_WEEK_ACTIONS.md (2h)
  - [ ] PHASE4_STAGING_MASTERPLAN.md (2h)
  - [ ] GO_LIVE_CHECKLIST.md (1h)
- [ ] Markdown lint validado (MD013 etc)
- [ ] Links verificados (cross-references)
- [ ] Português validado (sem encoding issues)

#### Runbooks & Procedures
- [ ] Emergency procedures documentadas
- [ ] Escalation procedures documentadas
- [ ] Contingency procedures documentadas
- [ ] Rollback procedures documentadas

#### Communication Templates
- [ ] Email template para status updates preparado
- [ ] Slack message templates preparados
- [ ] Report template para EOD reports preparado
- [ ] Gate decision template preparado

#### Sign-Off
```
[ ] Assinado: Tech Writer está pronto
[ ] Data: _____/_____/2026
[ ] Contato de emergência: _______________
```

---

### 👔 **Trader (Business Owner)**

#### Business Requirements
- [ ] Phase 4 objectives compreendidos
  - [ ] O que é "signal accuracy"?
  - [ ] Qual é o benchmark de win rate?
  - [ ] Como o sistema será validado?
- [ ] Success criteria compreendidos
- [ ] Risk framework compreendido
- [ ] Override procedures compreendidas

#### UAT Preparation
- [ ] Trader acceptance test cases revisados (6 tests)
- [ ] Test data sets preparados
- [ ] Expected outcomes documentados
- [ ] Failure scenarios compreendidos

#### Communication
- [ ] Slack channels confirmados
  - [ ] #phase4-deployment
  - [ ] #phase4-testing
  - [ ] #phase4-blockers
- [ ] Daily standup time confirmado (15:00 BRT)
- [ ] Emergency contact established

#### Sign-Off
```
[ ] Assinado: Trader está pronto
[ ] Data: _____/_____/2026
[ ] Contato de emergência: _______________
```

---

### 🔐 **CIO (Security Lead)**

#### Security Review
- [ ] Security framework compreendido
  - [ ] Authentication (OAuth JWT)
  - [ ] Encryption (TLS/HTTPS)
  - [ ] Authorization (role-based)
- [ ] Network security revisado (NSG rules)
- [ ] Key vault configuration revisada
- [ ] Audit logging requirements compreendidos

#### UAT Security Tests
- [ ] 3 security test cases revisados
- [ ] Test execution procedures compreendidas
- [ ] Expected outcomes documentados
- [ ] Failure scenarios conhecidos

#### Timeline
- [ ] Horário disponível para 07/03 UAT (confirmado)
- [ ] Contingency time bloqueado (se needed)
- [ ] Emergency escalation path definido

#### Sign-Off
```
[ ] Assinado: CIO está pronto
[ ] Data: _____/_____/2026
[ ] Contato de emergência: _______________
```

---

### 💰 **CFO (Finance Lead)**

#### Financial Framework
- [ ] Capital allocation compreendida
  - [ ] Phase 4 cost: R$ 27.5k
  - [ ] Go-live capital: R$ 50k
  - [ ] ROI target: 300% em 90 dias
- [ ] Budget approval status confirmado
- [ ] Payment terms e procedures documentados

#### UAT Financial Tests
- [ ] 3 financial test cases revisados
- [ ] P&L validation procedures compreendidas
- [ ] Expected financial metrics documentados
- [ ] Risk threshold rules compreendidas

#### Capital Authorization
- [ ] Bank details confirmadas
- [ ] Transfer procedures documentadas
- [ ] Timeline para 08/03 confirmado
- [ ] Contingency (if approval delayed) compreendida

#### Sign-Off
```
[ ] Assinado: CFO está pronto
[ ] Data: _____/_____/2026
[ ] Contato de emergência: _______________
```

---

## 📞 **COMMUNICATION CHECKLIST (Everyone)**

### Slack Channels
- [ ] Membro de `#phase4-deployment`
- [ ] Membro de `#phase4-testing`
- [ ] Membro de `#phase4-blockers`
- [ ] Membro de `#operador-phase4`
- [ ] Clicou em "pin" no announcement channel

### Calendar Blocks
- [ ] 01/03 09:00-10:00: Kick-off Meeting (blocked)
- [ ] 02-05/03: Daily standups 15:00 (recurring)
- [ ] 06-09/03: UAT period (relevant people only)
- [ ] 10/03 09:00-18:00: Go-live day (intensive)

### Contact Information
- [ ] Nome completo confirmado: _______________
- [ ] Slack handle confirmado: @____________
- [ ] Email confirmado: _________________
- [ ] Telefone (if needed): _________________
- [ ] Timezone confirmado: _________________

### Documentation
- [ ] Todos 5 kick-off docs foram lidos
- [ ] Notes pessoais tomadas em arquivo txt
- [ ] Questions documentadas (para perguntar em 01/03)
- [ ] Dependências pessoais comunicadas (se há)

---

## 🎯 **OVERALL VALIDATION CHECKLIST**

### By 27/02 EOD
- [ ] 80% das tarefas completas
- [ ] Nenhum blocker identificado
- [ ] Questões documentadas (para kick-off)

### By 28/02 EOD (Final)
- [ ] 100% das tarefas completas
- [ ] Zero blockers não-resolvidos
- [ ] Todos documentos lidos
- [ ] Preparação psicológica completa
- [ ] **PRONTO PARA KICK-OFF em 01/03**

---

## ✅ **FINAL TEAM SIGN-OFF**

Abaixo, cada persona confirma que completou sua checklist:

| Persona | Completo | Data | Assinatura |
|---------|----------|------|-----------|
| **DevOps Lead** | [ ] | _____/_____/ | ____________ |
| **Eng Sr** | [ ] | _____/_____/ | ____________ |
| **ML Expert** | [ ] | _____/_____/ | ____________ |
| **QA Lead** | [ ] | _____/_____/ | ____________ |
| **Integration Eng** | [ ] | _____/_____/ | ____________ |
| **Tech Writer** | [ ] | _____/_____/ | ____________ |
| **Trader** | [ ] | _____/_____/ | ____________ |
| **CIO** | [ ] | _____/_____/ | ____________ |
| **CFO** | [ ] | _____/_____/ | ____________ |

---

## 📌 **PRÓXIMOS PASSOS**

### Immediately (27-28/02)
1. Download this checklist
2. Complete your persona section
3. Document any blockers in `#phase4-blockers` Slack channel
4. Sign-off below by 28/02 23:59 BRT

### On 01/03
1. Arrive 10 min early para kick-off meeting (08:50)
2. Have laptop pronto com todas ferramentas
3. Estar 100% focado (phones on silent)
4. Trazer notes pessoais para discussão

### If Blocker Found
```
Se encontrar qualquer blocker durante prep week:
1. Post em #phase4-blockers
2. Tag relevante persona (ex: @devops-lead)
3. Response time target: <2h
4. Se não resolvido: escalate para @eng-sr ou @cto
```

---

*Documento criado: 26/02/2026*
*Última atualização: 26/02/2026 23:55 BRT*
*Status: Ready for team distribution*
*Gate: 28/02 EOD - Team 100% ready confirmation*
