# 🎯 Análise de Priorização - Próxima Task (24/02/2026)

**Status:** ✅ Executado
**Data:** 2026-02-24 19:15 BRT
**Baseado em:** solicita_task.md framework
**Fontes:** ROADMAP.md, PLANO_DE_SPRINTS_MVP_NOW.md, ANALISE_PRIORIZACAO_24FEV.md, TAREFAS_INTEGRACAO_PHASE6.md

---

## 🎯 SEÇÃO 1: STATUS ATUAL

### Sprint Ativo & Contexto Geral

| Item | Status | Detalhes |
|------|--------|----------|
| **Sprint Ativo** | Sprint 2 (27/02-13/03) | Inteligência e Visibilidade |
| **Fase Atual** | Phase 1 Beta - Validation | 24/02-01/03 real trading |
| **% Conclusão Fases** | 100% (Fases 1-4) | ✅ Go-Live 24/02 executado |
| **% Conclusão Sprint 2** | 0% | 🔵 Não-iniciado (kickoff 27/02) |
| **Capital Deployed** | R$ 50.000 | Phase 1 Beta live trading |
| **Próximo Gateway** | 01/03 18:00 BRT | Phase 2 Go/No-Go (imovível) |

### Tarefas de Integração Phase 6 (Bloqueadores Atuais)

**Estado:** ⏳ QUEUED desde 20/02, devem iniciar 27/02

| ID | Tarefa | Owner | Status | Prioridade | ETA |
|----|--------|-------|--------|-----------|-----|
| ENG-001 | **BDI Integration** | Eng Sr | ⏳ PRONTA | 🔴 BLOCKER | 27-28/02 (3-4h) |
| ML-001 | **Backtesting Setup** | ML Expert | ⏳ PRONTA | 🔴 BLOCKER | 27-28/02 (2-3h) |
| ENG-002 | WebSocket Server | Eng Sr | ⏳ PRONTA | 🔴 CRÍTICA | 01-02/03 (2-3h) |
| ENG-003 | Email Configuration | Eng Sr | ⏳ PRONTA | 🟠 ALTA | 03-04/03 (1-2h) |
| ENG-004 | Staging Deployment | DevOps | ⏳ PRONTA | 🟠 ALTA | 05-06/03 (2-3h) |
| ML-002 | Backtest Validation | ML Expert | ⏳ PRONTA | 🔴 CRÍTICA | 28-01/03 (2-3h) |
| ML-003 | Performance Benchmarking | ML Expert | ⏳ PRONTA | 🟠 ALTA | 02-03/03 (2-3h) |
| ML-004 | Final Validation | ML Expert | ⏳ PRONTA | 🟠 ALTA | 04-05/03 (1-2h) |

### Backlog Sprint 2 (Após Phase 6)

**Must Have (Críticas - GATE 1 checkpoint 05/03):**

| ID | Tarefa | Owner | Estimativa | Status | Prioridade |
|----|--------|-------|-----------|--------|-----------|
| **S2-2** | **Calibrador ATR Dinâmico** | ML | 8h | ⏳ PENDING | 🔴 CRÍTICA |
| S2-3 | Confluência SMC (M1/M5) | Dev | 10h | ⏳ PENDING | 🔴 CRÍTICA |
| S2-4 | Integração Phicube (Mimas) | ML | 6h | ⏳ PENDING | 🔴 CRÍTICA |

**Should Have (05/03-13/03):**

| ID | Tarefa | Owner | Estimativa | Status |
|----|--------|-------|-----------|--------|
| S2-5 | Probabilidade T+60 | ML | 15h | ⏳ BACKLOG |
| S2-6 | Analytics de Intervenção | Doc | 6h | ⏳ BACKLOG |

### Phase 1 Validation Metrics (Real-Time Monitoring)

| Métrica | Target | Status | % Progresso |
|---------|--------|--------|------------|
| Win Rate | ≥60% | 📊 Monitorando | TBD (6h data) |
| Uptime | ≥99.5% | 📊 Monitorando | ~100% (6h) |
| Trader Confidence | 9+/10 | 📊 Monitorando | TBD (daily) |
| System Stability | 0 críticos | ✅ PASS | 100% |

**Decision Point:** 01/03 18:00 BRT — Se todos metrics GREEN → Phase 2 GO (2x capital R$ 100k)

---

## 🎯 SEÇÃO 2: DEPENDÊNCIAS CRÍTICAS

### Mapa de Bloqueadores Detalhado

```
┌─────────────────────────────────────────────────────────────┐
│                   BLOCKER ABSOLUTO 1                       │
│           INTEGRATION-ENG-001: BDI Integration             │
│              (3-4 horas - 27-28/02)                        │
│                    Eng Sr OWNER                            │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────────────────┐
        │            │                        │
        ▼            ▼                        ▼
   ENG-002      ENG-003              S2-3 + S2-4
 WebSocket      Email Config       SMC + Phicube
 (2-3h)         (1-2h)             (16h total)
   ├─ Deps      ├─ Deps                 ├─ Deps
   └─ ENG-001   └─ ENG-001             └─ ENG-001


┌─────────────────────────────────────────────────────────────┐
│                   BLOCKER ABSOLUTO 2                       │
│         INTEGRATION-ML-001: Backtesting Setup              │
│              (2-3 horas - 27-28/02)                        │
│                   ML Expert OWNER                          │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼──────────────┐
        │            │              │
        ▼            ▼              ▼
   ML-002        ML-003          ML-004
  Validation   Benchmarking    Final Valid.
  (2-3h)        (2-3h)          (1-2h)
  ├─ Deps       ├─ Deps         ├─ Deps
  └─ML-001      └─ ML-002       └─ ML-003
       
   Gate Criteria:       Performance Req:     Pre-Gate 1:
   ├─ Capture ≥85%      ├─ P95 <30s          ├─ pytest
   ├─ FP ≤10%           ├─ Mem <50MB         ├─ mypy
   └─ WinRate ≥60%      └─ Throughput >100   └─ Coverage 98%
```

### Caminho Crítico (Critical Path Analysis)

**Path A (Eng Sr - Sequential):**

```
ENG-001 (3-4h)
    ↓
ENG-002 (2-3h)  [Depende de ENG-001]
    ↓
ENG-003 (1-2h)  [Parallelizável com ENG-002]
    ↓
ENG-004 (2-3h)  [Após ENG-001, ENG-002, ENG-003]
─────────────────────────
Total: 8-12h sequencial
Timeline: 27/02 10:00 → 28/02 17:00
Criticality: 🔴 BLOCKER ABSOLUTO
```

**Path B (ML Expert - Sequential):**

```
ML-001 (2-3h)
    ↓
ML-002 (2-3h)  [Depende de ML-001]
    ↓
ML-003 (2-3h)  [Depende de ML-002]
    ↓
ML-004 (1-2h)  [Depende de ML-003]
─────────────────────────
Total: 7-11h sequencial
Timeline: 27/02 10:30 → 28/02 17:00
Criticality: 🔴 BLOCKER ABSOLUTO
```

**Parallelization:** Path A e Path B podem rodar **simultaneamente** (Eng Sr + ML Expert)
- **Dia 27/02:** Kickoff 09:00 → Path A + Path B começam 10:00
- **Dia 28/02 EOD:** Ambos paths devem estar ✅ COMPLETOS
- **Dia 01/03:** Sprint 2 tasks (S2-2, S2-3, S2-4) podem iniciar

### Personas Críticas Bloqueadas/Aguardando

| Persona | Aguardando | Bloqueador | Impacto |
|---------|-----------|-----------|--------|
| **Eng Sr** | GO para BDI-001 | (nenhum) | SE NÃO: atrasa 8-12h |
| **ML Expert** | GO para ML-001 | (nenhum) | SE NÃO: atrasa 7-11h |
| **QA Lead** | Completo ENG/ML | ENG-001 + ML-001 | Testes paralelos desde 28/02 EOD |
| **DevOps** | Completo todos | ENG-004 | Staging deploy apenas após ENG-004 ✅ |
| **Doc Advocate** | Tasks finalizadas | Todos ENG/ML | Docs sincroniza ao fim de cada Path |

### Dependências de Decisão Executiva (GATES)

| Gate | Data | Ator | Métrica | Status | Impacto |
|------|------|------|--------|--------|--------|
| **Phase 1 Decision** | 01/03 18:00 | CTO/CEO | Win Rate ≥60% | 📊 MONITORING | Go/No-Go Phase 2 |
| **Gate 1 Learnings** | 05/03 17:00 | Eng Sr + ML | ENG-001 + ML-001 ✅ | ⏳ AGUARDANDO | Autoriza Sprint 2 Main |
| **Beta Launch** | 13/03 | Trader | E2E tests PASS | ⏳ DEPENDENT | v1.1 release decision |

---

## 🎯 SEÇÃO 3: RISCO OPERACIONAL

### Tarefas Atrasadas & Timeline

| Task | Original ETA | Atual | Dias Perdidos | Razão |
|------|-------------|--------|--------------|-------|
| ENG-001 | 27/02 | 27/02 | 0 dias | No atraso - pronto |
| ML-001 | 27/02 | 27/02 | 0 dias | No atraso - pronto |
| Sprint 2 | 27/02 | 27/02 | 0 dias | On schedule |
| Phase 2 Decision | **01/03** | **01/03** | 0 dias | ⚠️ NÃO PODE ATRASAR |

**Status:** Nenhuma tarefa atrasada tecnicamente. Todas 8 Integration tasks estão QUEUED desde 20/02, prontas para iniciar 27/02 conforme planejado.

### SLAs em Risco - Matriz de Criticidade

| SLA | Timeline | Dias Restantes | Status | Criticidade | Ação |
|-----|----------|----------------|--------|------------|------|
| **Phase 1 Decision** | 01/03 18:00 | **5 dias úteis** | 🟠 MÉDIO | 🔴 CRÍTICA | Monitorar Win Rate daily |
| **Gate 1 Checkpoint** | 05/03 17:00 | **9 dias úteis** | 🟢 BAIXO | 🟠 ALTA | Completa ENG-001 + ML-001 |
| **Beta v1.1 Launch** | 13/03 | **17 dias** | 🟢 BAIXO | 🟢 MÉDIA | E2E tests após Gate 1 |
| **Go-Live v1.2** | 10/04 | **45 dias** | 🟢 BAIXO | 🟢 BAIXA | Parallel Sprint 2/3/4 |

### Fatores de Risco Alto/Médio/Baixo

**🔴 RISCO ALTO:**
1. **Phase 1 Validation Decision (01/03 18:00 - IMOVÍVEL)**
   - Se Win Rate <60% → Phase 2 atrasa 7+ dias
   - Impacto: Perda de momentum, possível replanejamento capital
   - Mitigação: Daily monitoring, trader on-call 24/7
  
2. **BDI Integration Blocker (27-28/02)**
   - Se ENG-001 atrasar >4h → cascata para ENG-002, ENG-003, ENG-004
   - Impacto: 10-15h atraso até staging deploy
   - Mitigação: Sprint planning 26/02 (pré-validação), escalation protocol

3. **Backtesting Validation Gates (28/02-01/03)**
   - Se ML-002 falhar (Capture <85%, FP >10%, WinRate <60%)
   - Impacto: Retraining necessário antes Phase 2 decision
   - Mitigação: Grid search testado localmente (pre-sprint), fallback v1.1 detector

**🟠 RISCO MÉDIO:**
4. **Eng Sr + ML Expert Disponibilidade (27/02-05/03)**
- Se um deles indisponível: O outro continua, mas parallelism perde
- Impacto: +2-3 dias até Gate 1
- Mitigação: Backup personas (Arch Engineer como substitute)

1. **Phase 2 Capital Approval (contingente 01/03)**
   - Mesmo se Phase 1 GO, Head Finanças precisa ✅ aprovação
   - Impacto: Delay ~3-5 dias se análise financeira estender
   - Mitigação: Financial brief preparado 28/02

**🟢 RISCO BAIXO:**
6. Infraestrutura Azure (staging deploy) - redundância testada ✅
7. Marketplace/data provider integração - v1.1 já rodando ✅
8. MT5 connection stability - heartbeat verificado ✅ daily

### Personas Críticas com Deadlines

| Persona | Task | Deadline | % Progresso | Status |
|---------|------|----------|------------|--------|
| **Eng Sr** | ENG-001, 002, 003, 004 | 06/03 23:59 | 0% | ⏳ WAIT GO |
| **ML Expert** | ML-001, 002, 003, 004 | 06/03 23:59 | 0% | ⏳ WAIT GO |
| **QA Lead** | E2E + integration tests | 12/03 23:59 | 0% | ⏳ BLOCKED |
| **DevOps** | Staging deploy | 06/03 23:59 | 0% | ⏳ BLOCKED |
| **Product Owner** | Gate 1 acceptance | 05/03 17:00 | 0% | ⏳ BLOCKED |

---

## 🎯 SEÇÃO 4: TODOs NÃO RASTREADOS

### TODOs Encontrados via grep (#TODO comments)

**Total:** 30 TODOs identificados no código-fonte via `grep "#\s*(TODO|FIXME|XXX):"`

#### Grupo A: TODOs de Implementação Crítica (8)

| Arquivo | Linha | TODO | Prioridade | Issue | Owner | Estimativa |
|---------|-------|------|-----------|-------|-------|-----------|
| `src/application/ml_feature_engineer.py` | 473 | Validate file exists (raise FileNotFoundError) | 🔴 CRÍTICA | [CRIAR] | ML | 0.5h |
| `src/application/ml_feature_engineer.py` | 474 | Load JSON from backtest_optimized_results.json | 🔴 CRÍTICA | [CRIAR] | ML | 1h |
| `src/application/ml_feature_engineer.py` | 478 | Extract features as numpy array X | 🔴 CRÍTICA | [CRIAR] | ML | 2h |
| `src/application/ml_feature_engineer.py` | 479 | Extract labels as numpy array y | 🔴 CRÍTICA | [CRIAR] | ML | 1h |
| `src/application/ml_feature_engineer.py` | 488 | Calculate positive_ratio = sum(y) / len(y) | 🔴 CRÍTICA | [CRIAR] | ML | 0.5h |
| `src/application/orders_executor.py` | 133 | Implementar após Risk Validator pronto | 🟠 ALTA | [CRIAR] | Eng Sr | 3h |
| `src/application/orders_executor.py` | 158 | Implementar após MT5Adapter pronto | 🟠 ALTA | [CRIAR] | Eng Sr | 2h |
| `src/application/services/processador_bdi.py` | 81 | Detector de padrões técnicos (após ML-002) | 🟠 ALTA | [CRIAR] | ML | 4h |

#### Grupo B: TODOs de Validação & Testes (15)

| Arquivo | Linha | TODO | Prioridade | Issue | Owner | Estimativa |
|---------|-------|------|-----------|-------|-------|-----------|
| `src/application/ml_feature_engineer.py` | 480 | Create metadata dict | 🟠 ALTA | [CRIAR] | ML | 1h |
| `src/application/ml_feature_engineer.py` | 483 | Extract window_id mappings from JSON | 🟠 ALTA | [CRIAR] | ML | 1h |
| `src/application/ml_feature_engineer.py` | 488 | Assert 0.3 <= positive_ratio <= 0.7 | 🟠 ALTA | [CRIAR] | ML | 0.5h |
| `src/application/ml_feature_engineer.py` | 493 | Assert np.isnan(X).sum() == 0 | 🔴 CRÍTICA | [CRIAR] | ML | 0.5h |
| `src/application/ml_feature_engineer.py` | 498 | Use timer decorator + assert execution_time < 500ms | 🟠 ALTA | [CRIAR] | ML | 1h |
| `src/application/ml_feature_engineer.py` | 502-506 | Create tests/unit/test_load_and_label.py (4 tests) | 🔴 CRÍTICA | [CRIAR] | QA | 3h |
| `src/application/ml_feature_engineer.py` | 550-552 | Count positive/negative samples + ratio | 🟠 ALTA | [CRIAR] | ML | 1h |
| `src/application/orders_executor.py` | 188 | Implementar loop de monitoramento | 🟠 ALTA | [CRIAR] | Eng Sr | 2h |
| `src/domain/entities/portfolio.py` | 110 | Adicionar cálculo lucro/prejuízo nao realizado | 🟢 BAIXA | [CRIAR] | Dev | 2h |
| `src/application/ml_classifier.py` | 452 | Implementar grid search em paralelo | 🟠 ALTA | [CRIAR] | ML | 4h |

#### Grupo C: TODOs de Otimização (7)

_Restantes não-críticos listados para referência futura._

### Mapeamento de TODOs para Issues GitHub

**Status:** 23 TODOs mapeados, preparados para issue creation.

**Recomendação:**
- **Críticos (8):** Converter em Issues HOJE (24/02) → Target Sprint 2
- **Altos (9):** Converter em Issues HOJE → Target Sprint 2 + Phase 6
- **Médios (5):** Backlog para Phase 3+
- **Baixos (8):** Não-bloqueadores, roadmap futura

**Template Issue (usar GITHUB_ISSUES_TEMPLATES_23FEV.md):**

```markdown
Issue Title: [TODO-ML-001] Implement load_and_label() - JSON file loading

Persona: ML Expert
Prioridade: 🔴 CRÍTICA
Esforço: 5.5 horas (8 sub-tasks)
Bloqueador: SIM - Bloqueia INTEGRATION-ML-001 (Backtesting)
Área: Machine Learning / Feature Engineering
Sprint: Sprint 2 Phase 6
Deadline: 28/02 17:00

### Substasks:
- [ ] Validate file exists + raise FileNotFoundError
- [ ] Load JSON from backtest_optimized_results.json
- [ ] Extract features as numpy array X
- [ ] Extract labels as numpy array y
- [ ] Create metadata dict + window_id mappings
- [ ] Calculate positive_ratio + assert 0.3-0.7 balance
- [ ] Validate no NaN values (np.isnan)
- [ ] Assert execution_time < 500ms (timer decorator)

### Acceptance Criteria:
1. AC-1: Function load_and_label(file_path) returns (X, y, metadata)
2. AC-2: All 4 unit tests passing (test_load_and_label_*.py)
3. AC-3: Docstring + type hints 100%
4. AC-4: Coverage >= 95%
```

---

## 🚀 SAÍDA ESPERADA

### 1. PRÓXIMA TASK PRIORITÁRIA

```
Nome: INTEGRATION-ENG-001: BDI Integration
Sprint: Sprint 2 (27/02-13/03)
Status: ⏳ PRONTA PARA INICIAR (nenhum bloqueador)
Razão: 🔴 BLOCKER ABSOLUTO
        ├─ Desbloqueia 3 Eng Sr tasks (ENG-002, ENG-003, ENG-004)
        ├─ Desbloqueia 2 Sprint 2 features (S2-3 SMC, S2-4 Phicube)
        └─ Impacto cascata: 6 downstream tasks dependem

Persona: 👨‍💻 Eng Sr (Senior Software Engineer)
Issue #: [CRIAR NOVA] #70 (referência post-execution)
         └─ Title: "[ENG-001] BDI Integration - Phase 6"
         └─ AC: 7 acceptance criteria (já especificados)
         └─ Docs: TASK_SPEC_BDI_INTEGRATION_16.md

Bloqueadores: NENHUM (pronto para iniciar)

Desbloqueia: 
  1. INTEGRATION-ENG-002 (WebSocket Server) - 2-3h
  2. INTEGRATION-ENG-003 (Email Configuration) - 1-2h
  3. INTEGRATION-ENG-004 (Staging Deployment) - 2-3h
  4. S2-3 SMC Confluência (10h)
  5. S2-4 Phicube Integration (6h)
  6. QA E2E Tests (paralelo)
  
  Impacto Total: 24-30 horas desbloqueia de trabalho stream

ETA: 3-4 horas de execução
     Timeline: 27/02 10:00 → 28/02 14:00 (com almoço 12:30-13:00)
     
Criticalidade: 🔴 BLOCKER ABSOLUTO
  └─ Se atrasa >4h → cascata 10-15h em downstream
  └─ SLA: DEVE completar até 28/02 EOD (antes Gate 1)
  └─ Trigger de escalation: Se >3h sem update (standup 15:00)

Dependências Técnicas:
  ├─ Pre-requisite: processador_bdi.py em src/application/services/
  └─ Test Fixtures: 10+ velas histórico (já disponível)

Recursos Necessários:
  ├─ 1 Eng Sr dedicado 100% (27-28/02 10:00-17:00)
  ├─ 1 QA para code review (paralelo)
  ├─ PT spec: TASK_SPEC_BDI_INTEGRATION_16.md (já pronto)
  └─ Environment: Local dev (MT5 mock funcional)
```

### 2. TOP 3 PRÓXIMAS (após prioritária)

```
═══════════════════════════════════════════════════════════════

TASK [2]: INTEGRATION-ML-001: Backtesting Setup
───────────────────────────────────────────────────────────────
Razão: 🔴 BLOCKER ABSOLUTO (parallel path)
       ├─ Desbloqueia ML-002, ML-003, ML-004
       ├─ Parallelizável com ENG-001 (não há dependency)
       ├─ Gate Criteria: Capture ≥85%, FP ≤10%, WinRate ≥60%
       └─ Crítico para Phase 1 Validation Decision (01/03)

Status: ⏳ PRONTA PARA INICIAR
        └─ Owner: ML Expert
        └─ ETA: 2-3 horas (27-28/02)
        └─ Issue #: [CRIAR NOVA] #71

Persona: 🧠 ML Expert (Machine Learning Specialist)

═══════════════════════════════════════════════════════════════

TASK [3]: INTEGRATION-ENG-002: WebSocket Server
───────────────────────────────────────────────────────────────
Razão: 🔴 CRÍTICA (high value for delivery chain)
       ├─ Depende: INTEGRATION-ENG-001 (BDI)
       ├─ Desbloqueia: ENG-003, ENG-004 parallelism
       ├─ Código já pronto em src/interfaces/websocket_server.py
       └─ Timeline: Pode iniciar 01/03 morning (após ENG-001)

Status: ⏳ QUEUED (aguardando ENG-001 ✅)
        └─ Owner: Eng Sr
        └─ ETA: 2-3 horas
        └─ Issue #: [CRIAR NOVA] #68 (já referenciado)

Persona: 👨‍💻 Eng Sr

═══════════════════════════════════════════════════════════════

TASK [4]: S2-2: Calibrador ATR Dinâmico
───────────────────────────────────────────────────────────────
Razão: 🔴 CRÍTICA (MUST backlog)
       ├─ Gate 1 Dependency (05/03 deadline)
       ├─ Ativa 8 horas de desenvolvimento ML
       ├─ Integração com sistema de gestão de risco Phase 1
       └─ Baseline: v1.1 static ATR, upgrade para dynamic

Status: ⏳ PENDING (aguardando Phase 6 completo)
        └─ Owner: ML Expert
        └─ ETA: 8 horas
        └─ Issue #: [CRIAR NOVA] #XX

Persona: 🧠 ML Expert

═══════════════════════════════════════════════════════════════
```

### 3. CRONOGRAMA CRÍTICO (27/02 - 05/03)

```
27/02 (segunda)
├─ 09:00-10:00: SPRINT2_OFFICIAL_KICKOFF (agenda em SPRINT2_OFFICIAL_KICKOFF_27FEV.md)
├─ 10:00-14:00: ENG-001 Phase 1-3 (Setup + Implementation + Tests)
├─ 10:30-13:00: ML-001 execução paralela
├─ 12:30-13:00: ALMOÇO
├─ 13:00-14:00: ENG-001 Phase 4 + Code review
├─ 14:00-15:00: ML-001 Phase 2-3 (Validation)
├─ 15:00-15:15: 🔴 DAILY STANDUP #1 (DAILY_STANDUP_CONFIG_SPRINT2.md)
│                  Done vs Plan vs Blockers
├─ 15:15-17:00: Buffer + contingency (if blockers emergen)
└─ 17:00 EOD: Status lock-in (commit + push)

28/02 (terça)
├─ 09:00-10:00: ENG-002 setup
├─ 10:00-12:30: ENG-002 implementation
├─ 10:30-13:00: ML-002 backtest validation grid
├─ 12:30-13:00: ALMOÇO
├─ 13:00-14:00: ENG-002 unit tests
├─ 14:00-15:00: ML-002 capture/FP/WinRate analysis
├─ 15:00-15:15: 🔴 DAILY STANDUP #2
├─ 15:15-17:00: ENG-003 + contingency
└─ 17:00 EOD: ✅ ENG-001, ENG-002, ML-001, ML-002 MUST COMPLETE (or escalate)

01/03-05/03 (wed-sun)
├─ ENG-003, ENG-004, ML-003, ML-004 (remaining Phase 6)
├─ Parallel: S2-2 (Calibrador ATR) design/implementation
├─ Daily standups 15:00 BRT
└─ 05/03 17:00: 🎯 GATE 1 CHECKPOINT (Feature validation)

01/03 18:00 (HARD DEADLINE)
└─ Phase 1 Decision: Win Rate ≥60% → Phase 2 GO (R$ 100k)
```

---

## ⚠️ RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|--------|-----------|
| ENG-001 atrasa >4h | 10% | 🔴 CRÍTICO | Pre-sprint validation 26/02, Eng Sr dedicated 100% |
| ML-002 gates falham | 15% | 🔴 CRÍTICO | Fallback v1.1 detector, grid search batched |
| Phase 1 Win Rate <60% | 20% | 🔴 CRÍTICO | Daily monitoring, trader on-call, market analysis |
| Eng Sr indisponível | 5% | 🟠 MÉDIO | Arch Eng substitui, pre-documented code |
| Infrastructure issues | 5% | 🟠 MÉDIO | Azure HA testada, staging fallback pronto |

---

## 📋 PRÓXIMOS PASSOS IMEDIATOS

**Hoje (24/02 19:30-20:00):**
1. ✅ Enviar confirmação aos personas: Eng Sr + ML Expert → "Pronto para 27/02?"
2. ✅ Distribuir documentos: TASK_SPEC_BDI_INTEGRATION_16.md, TASK_SPEC_BACKTEST_SETUP_17.md
3. ✅ Preparar 2 calendário bloqueios (27-28/02 10:00-17:00, 28/02-05/03 15:00 standups)

**Amanhã (25/02):**
1. Preparar ambiente: processador_bdi.py code review
2. ML Expert: Mount Jupyter + backtest_optimized_results.json validation
3. QA: Test fixtures prontas para unit tests

**26/02 (Pre-sprint):**
1. Final validações de code + dependencies
2. Alinhamento final riscos + mitigações
3. Confirmar personas 100% disponíveis

**27/02 09:00 – 🚀 SPRINT 2 OFFICIAL KICKOFF**

---

**Documento:** PRIORIDADE_PROXIMA_TASK_24FEV.md  
**Versão:** 1.0.0  
**Estado:** ✅ COMPLETO  
**Sincronização:** ROADMAP.md, ANALISE_PRIORIZACAO_24FEV.md, TAREFAS_INTEGRACAO_PHASE6.md
