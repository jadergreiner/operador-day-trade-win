# 🎯 PRÓXIMAS TAREFAS (EM ORDEM DE PRIORIDADE)

**Documento:** PROXIMAS_TAREFAS_PRIORIDADE.md  
**Status:** ✅ Atualizado - Sem datas fictícias  
**Operador:** INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat  
**Responsável:** Coordenadora de Governança + Board Multidisciplinar

---

## 📊 P0 - CRÍTICAS (BLOQUEADORES)

### 1. Team Kick-off & Confirmação de Squads
**Objetivo:** Alinhar 11 personas com timeline e expectativas

- [ ] Confirmação de 11 personas designadas presentes
- [ ] Review détalhado dos 12 passos squad_multi.md
- [ ] Confirmação timeline e checkpoints imóveis
- [ ] Q&A e clarificações de dúvidas
- [ ] Document attendance + sign-off

**Responsável:** Coordenadora de Governança  
**Equipe:** Board Multidisciplinar (11 personas)

---

### 2. Environment Setup (SQUAD 1 Lead)
**Objetivo:** Preparar infraestrutura para desenvolvimento

- [ ] Docker setup (RabbitMQ, PostgreSQL, Redis)
- [ ] Python venv creation + dependencies instaladas
- [ ] CI/CD pipeline configuration (GitHub Actions)
- [ ] TDD test fixtures preparados e testados
- [ ] Git branches criadas (feature/ATI-1 a ATI-10)
- [ ] Verify all developers can access development environment

**Responsável:** Infra DevOps  
**Equipe:** SQUAD 1 (Eng Sr, 3x Dev-Backend)

---

### 3. Design Reviews (SQUAD 1 + SQUAD 2)
**Objetivo:** Validar arquitetura antes de desenvolvimento

**SQUAD 1 Design Review:**
- [ ] API specifications ATI-1 (Dashboard) finalizadas
- [ ] API specifications ATI-2 (OAuth) finalizadas
- [ ] Queue topology ATI-3 (RabbitMQ) aprovado
- [ ] WebSocket architecture ATI-4 finalizadas
- [ ] DB schema (PostgreSQL) definitivo aprovado
- [ ] Infrastructure diagrams reviewed

**SQUAD 2 Design Review:**
- [ ] Feature engineering plan ATI-5 (SHAP) aprovado
- [ ] SHAP methodology specifications finalizadas
- [ ] Drift detection rules ATI-6 specifications finalizadas
- [ ] ML pipeline architecture approved
- [ ] Monitoring setup specifications finalizadas

**Responsável:** Arquiteto de Sistemas + Eng Sr + ML Expert  
**Approval:** Eng Sr + ML Expert + Product Owner

---

### 4. Development Environment Validation
**Objetivo:** Garantir todos podem começar a desenvolver

- [ ] All developers can clone repository
- [ ] All dependencies installed (requirements.txt OK)
- [ ] Docker containers running (RabbitMQ, PostgreSQL, Redis)
- [ ] Database migrations executed
- [ ] First Hello World test passing
- [ ] CI/CD pipeline green (first commit)

**Responsável:** Infra DevOps + Eng Sr  
**Definition of Done:** All checks green on main branch

---

### 5. TDD Test Implementation Begins
**Objetivo:** Preparar framework de testes antes de código

**SQUAD 1 - Test Fixtures:**
- [ ] Test database setup (PostgreSQL test instance)
- [ ] File fixtures ATI-1 (Dashboard)
- [ ] File fixtures ATI-2 (OAuth)
- [ ] File fixtures ATI-3 (Queue)
- [ ] File fixtures ATI-4 (WebSocket)
- [ ] File fixtures ATI-8 (Retry)
- [ ] File fixtures ATI-9 (Position)
- [ ] Mock definitions for MT5 API

**SQUAD 2 - Test Fixtures:**
- [ ] Dataset fixtures ATI-5 (SHAP)
- [ ] Dataset fixtures ATI-6 (Drift)
- [ ] ML model mocks
- [ ] Backtest data fixtures

**Responsável:** QA Manager + Test Automation Engineer  
**Target:** 98% code coverage (global target)

---

## 📈 P1 - ALTAS (MUST-HAVE)

### 6. Feature Development (Parallel)
**Objetivo:** Implementar 10 features conforme especificação

**SQUAD 1 - Backend Features (In Parallel):**
- [ ] ATI-1: Dashboard de Ordens (8 AC)
- [ ] ATI-2: OAuth 2.0 API (8 AC)
- [ ] ATI-3: RabbitMQ Queue (8 AC)
- [ ] ATI-4: WebSocket Real-time (8 AC)
- [ ] ATI-8: Retry Logic 3x (8 AC)
- [ ] ATI-9: Position Monitor SL/TP (8 AC)

**SQUAD 2 - ML Features (In Parallel):**
- [ ] ATI-5: SHAP + Features (8 AC)
- [ ] ATI-6: Drift Detection + Alerts (8 AC)

**SQUAD 3 - Validation (Blocked - GATE 1 Dependent):**
- [ ] ATI-7: Backtest 252 dias (20 AC) - Blocked
- [ ] ATI-10: Gate 2 Decision Framework (10 AC) - Blocked

**Responsável:** Eng Sr (SQUAD 1) + ML Expert (SQUAD 2)  
**Definition of Done:** Feature coding complete, unit tests green

---

### 7. Code Reviews & Quality Gates
**Objetivo:** Validar qualidade antes de merge

- [ ] 2+ reviewers approval required per feature
- [ ] 100% type hints validated (mypy --strict)
- [ ] 98% code coverage target validated
- [ ] Lint checks passed (pycodestyle + pylint)
- [ ] No code duplication >3%
- [ ] Clean Code principles validated
- [ ] Commit messages follow pattern (sem acentos)

**Responsável:** Arquiteto de Sistemas + Eng Sr (SQUAD 1) / ML Expert (SQUAD 2)  
**Tools:** GitHub PR reviews, pre-commit hooks

---

### 8. Integration Testing
**Objetivo:** Validar features funcionam juntas

- [ ] ATI-1 ↔ ATI-2: Dashboard + OAuth login
- [ ] ATI-2 ↔ ATI-3: OAuth + RabbitMQ queue auth
- [ ] ATI-3 ↔ ATI-8: Queue + Retry mechanism
- [ ] ATI-1 ↔ ATI-4: Dashboard + WebSocket updates
- [ ] ATI-4 ↔ ATI-9: WebSocket + Position changes
- [ ] Performance tests: P95 latency <500ms
- [ ] Reliability tests: Queue zero message loss

**Responsável:** QA Manager + Integration Engineer  
**Test Coverage:** End-to-end flows

---

### 9. Daily Standups (Recurring)
**Objetivo:** Manter alinhamento e resolver blockers quick

- [ ] SQUAD 1 status (10min) - Blockers + progress
- [ ] SQUAD 2 status (10min) - Blockers + progress
- [ ] SQUAD 3 status (5min) - Blocked, waiting GATE 1
- [ ] Risk discussion (5min) - New risks + escalation
- [ ] Action items recorded + assigned

**Responsável:** Coordenadora de Governança (Facilitadora)  
**Frequência:** Diária, horário fixo  
**Format:** Async update + weekly sync optional

---

### 10. Weekly Documentation Sync
**Objetivo:** Manter documentação sincronizada com realidade

- [ ] STATUS_ENTREGAS.md AC count progress updated
- [ ] CHANGELOG.md version bump (if needed)
- [ ] SYNC_MANIFEST.json checksums recalculated
- [ ] README.md timeline visual updated
- [ ] Git commit message follows pattern
- [ ] UTF-8 encoding validated
- [ ] Cross-references verified working

**Responsável:** Doc Advocate  
**Frequência:** Semanal, Terça 18:00 (fuso horário)  
**Output:** Formal documentation record

---

## 🔧 P2 - MÉDIAS (NICE-TO-HAVE)

### 11. Operador Integration (Phased)
**Objetivo:** Integrar features ao operador INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat

**Phase 1 - After ATI-2:**
- [ ] INICIAR.BAT importa módulo OAuth
- [ ] Operador requer login antes de start
- [ ] Tokens persisted em Redis

**Phase 2 - After ATI-1 + ATI-4:**
- [ ] INICIAR.BAT inicia dashboard server (port 8001)
- [ ] WebSocket listener active (port 8002)
- [ ] Dashboard accessible via browser localhost:8001

**Phase 3 - After ATI-3:**
- [ ] INICIAR.BAT inicia RabbitMQ consumer (background)
- [ ] Order queue monitored for new orders

**Phase 4 - After ATI-5 + ATI-6:**
- [ ] INICIAR.BAT carrega SHAP model
- [ ] Drift detector ativo (hourly checks)
- [ ] Alerts integrados ao dashboard

**Phase 5 - After GATE 1:**
- [ ] INICIAR.BAT runs GATE 1 validation check
- [ ] All 8 features must be green before startup

**Phase 6 - After TRACK 3:**
- [ ] INICIAR.BAT integra backtest scores
- [ ] Capital activation status displayed

**Responsável:** Dev-Backend Lead + Operações  
**Validation:** Operator remains functional end-to-end

---

### 12. Lint & Code Quality (Continuous)
**Objetivo:** Manter code quality standards

**Python Lint:**
- [ ] pycodestyle (PEP 8 compliance)
- [ ] pylint (code quality)
- [ ] mypy --strict (type checking)

**Markdown Lint:**
- [ ] pymarkdown (max 80 chars per line)
- [ ] No broken links in documentation

**Commit Standards:**
- [ ] No accents in commit messages
- [ ] Pattern: "feat: ...", "fix: ...", "docs: ..."
- [ ] UTF-8 encoding on all files

**Responsável:** QA Manager  
**Frequency:** Per feature completion, weekly audit

---

### 13. Risk Management & Escalation
**Objetivo:** Gerenciar riscos proativamente

- [ ] Weekly risk assessment (Thursday)
- [ ] Blocker resolution <24h (escalate if needed)
- [ ] Risk log updated in STATUS_ENTREGAS.md
- [ ] Risk mitigation plans assigned
- [ ] Escalation path clear (Coordenadora → Eng Sr/ML Expert → CEO)

**Responsável:** Coordenadora de Governança  
**Frequency:** Semanal, Thursday status

---

### 14. Weekly Commits & Push (Recurring)
**Objetivo:** Manter histórico Git atualizado

- [ ] Feature commits: Per AC completion
- [ ] Pattern: "feat: ATI-# (X/X AC passed)"
- [ ] Documentation commits: Weekly
- [ ] All files UTF-8 encoded
- [ ] SSH key working (GitHub authentication)
- [ ] Commits pushed to origin/main

**Responsável:** Coordenadora de Governança (coordena)  
**Frequency:** Weekly, every Friday 18:00 BRT  
**Audit:** Git log reviewed + CHANGELOG maintained

---

## 🎯 CHECKPOINTS CRÍTICOS (IMÓVEIS)

### ✅ GATE 1 - AC Validation Checkpoint

**Bloqueador:** TRACK 3 não inicia até GATE 1 = GO

**Validação Obrigatória:**
- [ ] TRACK 1: 6 ATI × 8 AC = 48/48 AC PASSED
- [ ] TRACK 2: 2 ATI × 8 AC = 16/16 AC PASSED
- [ ] Total: 64/64 AC across all features
- [ ] Unit tests: 64+ running, ≥98% coverage
- [ ] Code reviews: 2+ approvals per feature
- [ ] Documentation: STATUS_ENTREGAS, CHANGELOG, SYNC_MANIFEST sincronizadas
- [ ] Operador: INICIAR.BAT com todas 8 features operacionais
- [ ] Performance: WebSocket P95 <100ms, Queue zero loss

**Decision Committee:** Eng Sr + ML Expert + Product Owner + CFO

**Result:**
- GO → TRACK 3 inicia (ATI-7, ATI-10)
- NO-GO → 3-day refactor cycle, retry GATE 1

---

### ✅ GATE 2 - Capital Activation Checkpoint

**Bloqueador:** Capital decision R$ 50k vs R$ 100k

**Validação Obrigatória:**
- [ ] Backtest 252 dias executado sem erros
- [ ] Sharpe Ratio ≥ 1.0 ✅
- [ ] Win Rate ≥ 59% ✅
- [ ] Drawdown ≤ 15% ✅
- [ ] Consistency ≤ 30% ✅
- [ ] ATI-7: 20/20 AC PASSED
- [ ] ATI-10: 10/10 AC PASSED
- [ ] Unit tests: 24+, ≥98% coverage
- [ ] Code reviews: 2+ approvals per feature
- [ ] CFO: Formal approval signed

**Decision Committee:** ML Expert + CFO + Trader Líder + CEO

**Result:**
- ALL PASS → R$ 100k capital ativado 🚀 (Phase 2 starts)
- ANY FAIL → R$ 50k continued, 3-week refactor, retry GATE 2

---

## 📋 CHECKLIST FINAL

### Before GATE 1:
- [ ] All 118 AC specifications reviewed
- [ ] All 64+ unit tests implemented
- [ ] All documentation synchronized
- [ ] All code merged to main branch
- [ ] Zero blockers ready for GATE 1
- [ ] Team energy + morale high
- [ ] Stakeholder alignment confirmed

### Before GATE 2:
- [ ] Backtest 252 days completed
- [ ] All 4 metrics validated
- [ ] Capital allocation risk reviewed
- [ ] Phase 2 timeline ready
- [ ] Monitoring infrastructure live
- [ ] CFO sign-off obtained

---

## 📊 STATUS SUMMARY

| Item | Status | Next Step |
|------|--------|-----------|
| 10 Features Spec | ✅ COMPLETE | Development starts |
| Squads Mobilized | ✅ COMPLETE | Team kick-off |
| Environment Ready | ⏳ IN PROGRESS | Setup validation |
| Design Reviews | ⏳ IN PROGRESS | Code development |
| Development | ⏳ IN PROGRESS | Testing |
| GATE 1 | ⏳ PENDING | Validation checkpoint |
| GATE 2 | ⏳ PENDING | Capital decision |

---

**Última Atualização:** d4fd4aa  
**Responsável:** Coordenadora de Governança  
**Próxima Review:** Após cada checkpoint

---

🚀 **Pronto para começar. Bem-vindo ao Sprint 2 Paralelo!**
