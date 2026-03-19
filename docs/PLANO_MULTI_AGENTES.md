# 🤖 Plano de Multi Agentes — Entregas Backlog (Clean Code)

**Status:** Execução principal concluida em codigo e testes unitarios; foco atual em staging, UAT e Gate 2

---

## 📊 Estado Real (2026-03-19)

- As trilhas Clean Arch, Signals, Storytelling e ML Ops já existem em `src/application/` e possuem suites em `tests/unit/` e `tests/` relacionadas.
- O acoplamento runtime Storytelling + ML Ops está materializado em `src/application/diarios_runtime_mlops_bridge.py` e consumido por `scripts/start_journals_full_display.py`.
- Nesta auditoria, a validação representativa executada passou com `60 passed` nos subconjuntos críticos de reconciliador, watchdog, correlator, pipeline adaptativo, bridge, coordenador e kill switch.
- O que permanece em aberto é validação operacional: deploy em staging, UAT com operador, Gate 2 final e autorização para live trading.

## 📊 Visão Geral de Entregas + Governança

| # | Componente | Agente | Estado | Prioridade |
|---|---|---|---|---|
| **ENTREGAS CRÍTICAS** | | | | |
| 1 | ROADMAP-MICRO-03 | Clean Arch | ✅ ENTREGUE / VALIDADO | 🔴 CRÍTICA |
| 2 | ROADMAP-DIARIOS-01 | Signals | ✅ ENTREGUE / VALIDADO | 🟡 ALTA |
| 3 | ROADMAP-DIARIOS-02 | Storytelling | ✅ ENTREGUE / VALIDADO | 🟡 ALTA |
| 4 | ROADMAP-DIARIOS-03 | Storytelling | ✅ ENTREGUE / VALIDADO | 🟡 MÉDIA |
| 5 | ROADMAP-DIARIOS-04 | ML Ops | ✅ ENTREGUE / VALIDADO | 🟡 MÉDIA |
| 6 | ROADMAP-DIARIOS-05 | ML Ops | ✅ ENTREGUE / VALIDADO | 🟢 BAIXA |
| 7 | ROADMAP-DIARIOS-06 | ML Ops | ✅ ENTREGUE / VALIDADO | 🟢 BAIXA |
| **GOVERNANÇA** | | | | |
| G1 | Sincronização Docs-Code | Tech Lead | 🔄 CONTÍNUA | 🔴 CRÍTICA |
| G2 | Modelagem de Dados | DBA | 🔄 CONTÍNUA | 🔴 CRÍTICA |
| G3 | ADRs + Arquitetura | Arquiteto | 🔄 CONTÍNUA | 🔴 CRÍTICA |
| G4 | Diagramas + Requisitos | Product Mgmt | 🔄 CONTÍNUA | 🟡 ALTA |

**Total Esforço:** 85-100 horas (7 tarefas × ~12-14h cada) + Governança (15-20h)
**Execução:** Paralela por especialidade, sequencial por dependência
**Orquestração:** Tech Lead coordena todos agentes + governança
---

## 🎯 7 Agentes Especializados + Governança

### 1️⃣ AGENTE CLEAN ARCHITECTURE
**Especialidade:** Refatoração, Type Hints, Design Patterns
**Carga Horária:** 20-25h
**Tarefas Primárias:**
- ROADMAP-MICRO-03 (reconciliação DESCONHECIDO)
- Type hints 100% em todos novos módulos
- Validação mypy --strict
- Padrões DDD (Value Objects, Entities, Interfaces)

**Responsabilidades:**
- ✓ Revisar arquitetura de novos módulos
- ✓ Enforçar camadas Clean Arch
- ✓ Validar separação de responsabilidades
- ✓ Documentar padrões de design

**Deliverables:**

```
src/application/
├── reconciliadores/
│   ├── trade_outcome_reconciler.py (250 LOC)
│   ├── unknown_result_detector.py (200 LOC)
│   └── mt5_sync_validator.py (180 LOC)
tests/unit/
├── test_trade_outcome_reconciler.py (280 LOC, 15 testes)
├── test_unknown_result_detector.py (220 LOC, 12 testes)
└── test_mt5_sync_validator.py (200 LOC, 10 testes)
```

**Commits Esperados:**

```bash
feat: Implementar Trade Outcome Reconciler com testes 15/15
feat: Implementar Unknown Result Detector com testes 12/12
feat: Implementar MT5 Sync Validator com testes 10/10
```

---

### 2️⃣ AGENTE SIGNALS & OBSERVABILITY
**Especialidade:** Watchdogs, Health Checks, Logging
**Carga Horária:** 18-22h
**Tarefas Primárias:**
- ROADMAP-DIARIOS-01 (Watchdog de threads)
- Health checks e monitoramento

**Responsabilidades:**
- ✓ Implementar ThreadWatchdog para Diários
- ✓ Criar health checks estruturados
- ✓ Logging com stack traces
- ✓ Recuperação automatizada

**Deliverables:**

```
src/application/
├── thread_watchdog_advanced.py (450 LOC)
├── diarios_health_monitor.py (320 LOC)
└── logging_recovery_handler.py (280 LOC)
tests/unit/
├── test_thread_watchdog_advanced.py (380 LOC, 22 testes)
├── test_diarios_health_monitor.py (260 LOC, 15 testes)
└── test_logging_recovery_handler.py (200 LOC, 12 testes)
outputs/
├── diarios_watchdog_report_YYYYMMDD.json
└── health_check_relatorio_YYYYMMDD.md
```

**Commits Esperados:**

```bash
feat: Aprimorar ThreadWatchdog com recuperação avançada + 22 testes
feat: Implementar DiarioHealthMonitor com monitoramento em tempo real + 15 testes
feat: Adicionar LoggingRecoveryHandler para rastreamento de falhas + 12 testes
```

---

### 3️⃣ AGENTE STORYTELLING & NARRATIVE
**Especialidade:** Persistência, Correlação, Dataset Generation
**Carga Horária:** 22-28h
**Tarefas Primárias:**
- ROADMAP-DIARIOS-02 (Trading Storytelling)
- ROADMAP-DIARIOS-03 (AI Reflection Evolution)
- Dataset de treinamento

**Responsabilidades:**
- ✓ Persistência de narrativas estruturadas
- ✓ Correlação trade ↔ outcome
- ✓ Evolução automática de perguntas
- ✓ Exportação de features para ML

**Deliverables:**

```
src/application/
├── narrative_persistence.py (380 LOC)
├── trade_narrative_correlator.py (420 LOC)
├── reflection_question_evolution.py (350 LOC)
├── narrative_dataset_exporter.py (320 LOC)
└── reflection_action_channel.py (280 LOC)
tests/unit/
├── test_narrative_persistence.py (320 LOC, 18 testes)
├── test_trade_narrative_correlator.py (380 LOC, 20 testes)
├── test_reflection_question_evolution.py (300 LOC, 16 testes)
├── test_narrative_dataset_exporter.py (280 LOC, 14 testes)
└── test_reflection_action_channel.py (240 LOC, 12 testes)
data/training/
├── narrative_features_YYYYMMDD.json
├── reflection_insights_YYYYMMDD.json
└── narrative_correlations_YYYYMMDD.json
outputs/
├── journal_correlacoes_YYYYMMDD.md
├── reflection_semana_NN.md
└── narrative_export_YYYYMMDD.json
```

**Commits Esperados:**

```bash
feat: Implementar Narrative Persistence com testes 18/18
feat: Implementar Trade-Narrative Correlator com testes 20/20
feat: Implementar Reflection Question Evolution com testes 16/16
feat: Implementar Narrative Dataset Exporter com testes 14/14
feat: Implementar Reflection Action Channel com testes 12/12
```

---

### 4️⃣ AGENTE ML OPS & GUARDIAN
**Especialidade:** Retreinamento, Adaptação de Regime, Detecção de Viés
**Carga Horária:** 20-25h
**Tarefas Primárias:**
- ROADMAP-DIARIOS-04 (RL Performance c/ Retreinamento)
- ROADMAP-DIARIOS-05 (Macro Guardian Universal)
- ROADMAP-DIARIOS-06 (Order Manager com Antienviesamento)

**Responsabilidades:**
- ✓ Pipelines de retreinamento adaptativo
- ✓ Detecção de viés direcional
- ✓ Adaptação dinâmica de regime
- ✓ Integração Guardian multi-agente
- ✓ Kill switches coordenados

**Deliverables:**

```
src/application/
├── adaptive_retraining_pipeline.py (480 LOC)
├── directional_bias_detector.py (340 LOC)
├── market_regime_adapter.py (400 LOC)
├── macro_guardian_universal.py (420 LOC)
├── universal_kill_switch.py (280 LOC)
└── order_manager_learner.py (360 LOC)
tests/unit/
├── test_adaptive_retraining_pipeline.py (420 LOC, 22 testes)
├── test_directional_bias_detector.py (300 LOC, 16 testes)
├── test_market_regime_adapter.py (360 LOC, 18 testes)
├── test_macro_guardian_universal.py (380 LOC, 20 testes)
├── test_universal_kill_switch.py (280 LOC, 14 testes)
└── test_order_manager_learner.py (340 LOC, 18 testes)
data/models/
├── order_manager/historico_versoes.json
└── regime_models/
    ├── regime_tendencia_alta.pkl
    ├── regime_tendencia_baixa.pkl
    ├── regime_lateral.pkl
    └── regime_volatil.pkl
outputs/
├── rl_diary_fechamento_YYYYMMDD.md
├── guardian_semana_NN.md
├── order_manager_relatorio_YYYYMMDD.md
└── regime_adaptation_log_YYYYMMDD.json
```

**Commits Esperados:**

```bash
feat: Implementar Adaptive Retraining Pipeline com testes 22/22
feat: Implementar Directional Bias Detector com testes 16/16
feat: Implementar Market Regime Adapter com testes 18/18
feat: Implementar Macro Guardian Universal com testes 20/20
feat: Implementar Universal Kill Switch com testes 14/14
feat: Implementar Order Manager Learner com testes 18/18
```

---

## 🏗️ 3 Agentes de Governança

### 5️⃣ DBA (Database Administrator)
**Especialidade:** Modelagem de Dados, Schema Versioning, Integridade
**Carga Horária:** 10-15h (paralelo com todos)
**Responsabilidades:**
- ✓ Manter modelagem de dados 100% atualizada
- ✓ Revisar schemas em cada entrega
- ✓ Validar foreign keys e constraints
- ✓ Auditar performance de queries
- ✓ Versionar mudanças de schema
- ✓ Documentar fluxo de dados (ERD)

**Deliverables:**

```
docs/
├── MODELAGEM_DE_DADOS_ATUALIZADO.md (versão pós-entregas)
├── SCHEMA_CHANGELOG_v1.3.md
├── migration_scripts/
│   ├── 001_add_reconciliation_tables.sql
│   ├── 002_add_narrative_schema.sql
│   └── 003_add_ml_metrics_tables.sql
data/db/
├── trading_v1.3.db (nova versão)
└── migrations/
    └── version.json (rastreamento)
outputs/
├── erd_atualizado_YYYYMMDD.png
└── data_audit_report_YYYYMMDD.md
```

**Sync Points:**
- Validar cada entrega (Clean Arch → schema novo)
- Revisar antes de commits (Signals → queries)
- Aprovar PRs com mudanças de DB (Storytelling → persistência)
- Otimizar antes de merge (ML Ops → retrainamento)

---

### 6️⃣ ARQUITETO DE SOFTWARE
**Especialidade:** ADRs, Design Decisions, Arquitetura Alvo
**Carga Horária:** 8-12h (paralelo com todos)
**Responsabilidades:**
- ✓ Guardiã das ADRs (Architecture Decision Records)
- ✓ Validar que entregas respeitam ARQUITETURA_ALVO
- ✓ Revisar propostas de mudanças arquiteturais
- ✓ Ensinar Clean Arch para agentes
- ✓ Resolver conflitos de design
- ✓ Manter compatibilidade com layers

**Deliverables:**

```
docs/
├── ADR/
│   ├── ADR-017_Reconciliation_Strategy.md (NOVO)
│   ├── ADR-018_Narrative_Persistence_Layer.md (NOVO)
│   ├── ADR-019_ML_Ops_Integration.md (NOVO)
│   └── DECISIONS_LOG_v1.3.md (atualizado)
├── ARQUITETURA_ALVO_v1.3_REVIEWED.md
└── clean_architecture_guidelines.md (melhorado)
outputs/
├── architecture_review_sessions.md
├── design_patterns_catalog_v1.3.md
└── layer_compliance_report_YYYYMMDD.md
```

**Sync Points:**
- Design review para cada agente (antes de implementação)
- ADR approval antes de merges arquiteturais
- Training sessions com Clean Arch agent
- Validação final de compliance

**Regra de Decisão:**
- Entregas devem responder: "Como isso se encaixa na arquitetura?"
- Se não se encaixa → propor ADR ou mudança
- ADR aprovada → agente implementa
- ADR rejeitada → redesenhar ou escalar

---

### 7️⃣ PRODUCT MANAGEMENT
**Especialidade:** Diagramas, Regras de Negócio, Requisitos
**Carga Horária:** 8-10h (paralelo com todos)
**Responsabilidades:**
- ✓ Manter 100% atualizado Diagramas (fluxos, sequências, estados)
- ✓ Manter 100% atualizado Regras de Negócio
- ✓ Validar que entregas atualizam documentação
- ✓ User story → implementação rastreamento
- ✓ Comunicar mudanças aos stakeholders
- ✓ Gerenciar versões de features

**Deliverables:**

```
docs/
├── REGRAS_DE_NEGOCIO_v1.3_ATUALIZADO.md
├── user_stories_roadmap_v1.3.md
├── diagramas/
│   ├── reconciliation_flow_v1.3.png (NOVO)
│   ├── narrative_persistence_flow_v1.3.png (NOVO)
│   ├── ml_ops_pipeline_v1.3.png (NOVO)
│   ├── state_machine_trading_v1.3.png (ATUALIZADO)
│   └── sequence_diagrams/ (6 diagramas)
└── feature_release_notes_v1.3.md
outputs/
├── stakeholder_communications_v1.3.md
├── feature_coverage_matrix_YYYYMMDD.json
└── requirements_traceability_YYYYMMDD.md
```

**Sync Points:**
- Entrega de código → gerar diagrama correspondente
- Nova regra de negócio → atualizar REGRAS_DE_NEGOCIO
- User story completa → checar compliance
- Stakeholder review semanal

**Rastreamento:**
- Cada entrega valida: "Qual requisito satisfaz?"
- Cada diagrama: "Qual código implementa?"
- 1:1 mapping entregas ↔ user stories

---

## 🎯 AGENTE TECH LEAD (Orquestrador)
**Especialidade:** Orquestração, Sincronização, Documentação Viva
**Carga Horária:** 15-20h (paralelo + coordenação)
**Responsabilidades Críticas:**
- ✓ **Orquestrar** todos 7 agentes (garantir sincronização)
- ✓ **Espelhar** cada entrega na documentação do projeto
- ✓ **Validar** que código e docs estão sempre sincronizados
- ✓ **Escalar** bloqueadores e conflitos
- ✓ **Manter** BACKLOG_UNIFICADO atualizado
- ✓ **Facilitar** daily standups (checkpoint ponto)

**Responsabilidades Operacionais:**
1. **Sincronização de Entregas → Documentação**
   - Quando Clean Arch entrega reconciliador → atualizar ARQUITETURA
   - Quando Signals entrega watchdog → atualizar OPERACAO_4_AGENTES
   - Quando Storytelling entrega narrativa → atualizar REGRAS_DE_NEGOCIO
   - Quando ML Ops entrega pipeline → atualizar MODELAGEM_DE_DADOS

2. **Validação de Documentação Viva**
   - PRs não são aceitas sem docs atualizadas
   - Docs refletem 100% o código entregue
   - Exemplos funcionam (code samples testáveis)
   - Diagramas correspondem à implementação

3. **Rastreamento Multi-Agente**
   - Overview de progresso consolidado
   - Dependências tabuladas
   - Bloqueadores identificados
   - Integrações sincronizadas

4. **Facilitação de Sincronismo**
   - **Daily Checkpoint (30m)**
     - Status: cada agente 1 min
     - Bloqueadores: 10 min group
     - Docs sync: 5 min update
     - Next steps: 5 min planning
   - **Weekly Review (1h)**
     - Docs vs. Code: delta analysis
     - Cross-review agendado
     - Stakeholder communication
     - Planning semana seguinte

**Deliverables (Documentação Viva):**

```
docs/
├── BACKLOG_UNIFICADO_v1.3_LIVE.md (atualizado em tempo real)
├── MULTI_AGENTES_STATUS_DAILY.md (atualizado cada checkpoint)
├── SYNC_MANIFEST_v1.3.json (checksums de todos agentes)
├── ENTREGAS_REFLETIDAS_v1.3.md (index de mudanças)
├── ARQUITETURA_ALVO_VALIDATED.md (versão aprovada)
├── OPERACAO_4_AGENTES_UPDATED.md (versão com novas features)
├── REGRAS_DE_NEGOCIO_CURRENT.md (versão com novos fluxos)
└── MODELAGEM_DE_DADOS_CURRENT.md (versão com novos schemas)
outputs/
├── daily_sync_agenda_CHECKPOINT_N.md
├── weekly_summary_WEEK_N.md
├── docs_vs_code_delta_YYYYMMDD.json
├── agentes_progress_matrix_YYYYMMDD.md
└── stakeholder_update_YYYYMMDD.md
```

**Matriz de Responsabilidades (Tech Lead):**

| Entrega | Tech Lead Sync | Trigger |
|---------|---|---|
| Clean Arch PR (reconciliador) | Atualizar ARQUITETURA_ALVO + ERD | Antes de merge |
| Signals PR (watchdog) | Atualizar OPERACAO_4_AGENTES + fluxo | Antes de merge |
| Storytelling PR (narrativa) | Atualizar REGRAS_DE_NEGOCIO + diagrama | Antes de merge |
| ML Ops PR (pipeline) | Atualizar MODELAGEM_DE_DADOS + sequence | Antes de merge |
| Any code update | Validar docstring português 100% | Checksum |
| Any type hints | Executar mypy --strict | Automated check |
| Any tests | Atualizar coverage badge | Automated check |
| Any schema | Revisar com DBA + gerar migration | Antes de merge |
| Any design decision | Revisar com Arquiteto + gerar ADR | Antes de merge |
| Any rule change | Revisar com PM + atualizar diagrama | Antes de merge |

**Processo de Sincronização (Tech Lead):**

```
FASE 1: Agentes começam (PARALELO)
  ├─ Tech Lead: Verifica planejamento doc
  ├─ Clean Arch: Entrega Principal
  ├─ Signals: Entrega Principal
  ├─ Storytelling: Entrega Principal
  └─ ML Ops: Entrega Principal
  ↓
[LOOP CONTÍNUO - Tech Lead orquestra sidncronização]
  ↓
FASE 2: Integrações Cruzadas (conforme depend.)
  ├─ Storytelling: Aguarda Clean Arch
  └─ ML Ops: Aguarda Storytelling
  ↓
FASE 3: Finalização
  ├─ Todos: Final commits + merge
  └─ Tech Lead: Aprova entrega final
```

**SLA de Tech Lead:**

| Trigger | Response | Check |
|---------|----------|-------|
| PR aberta | Review dentro <30min | Docs updated? |
| Bloqueador reportado | Escalação <15min | Resolvido em <1h |
| Checkpoint preparado | Agenda confirmada | Todos presentes |
| Docs desincronizadas | Fix + commit <2h | Checksum valid |

---

## 🔄 Fluxo de Orquestração (Tech Lead + 7 Agentes)

```
INICÍO (Kickoff)
  ├─ Tech Lead: Valida planejamento doc
  ├─ Tech Lead: Confirma agentes prontos
  └─ Tech Lead: Inicia relógio

PARALELO (Todos agentes)
  ├── 1️⃣ Clean Arch: code + tests
  ├── 2️⃣ Signals: code + tests
  ├── 3️⃣ Storytelling: code + tests
  ├── 4️⃣ ML Ops: code + tests
  │
  ├─ 5️⃣ DBA: Valida schemas (continuous)
  ├─ 6️⃣ Arquiteto: Valida patterns (continuous)
  ├─ 7️⃣ PM: Valida requisitos (continuous)
  │
  └─ 🎯 Tech Lead: Orquestra sincronização (hourly)
       ├─ Qualquer entrega? → Atualizar docs
       ├─ Docs desincronizadas? → Alert
       ├─ Bloqueadores? → Escalar
       └─ Próximo milestone? → Comunicar

INTEGRAÇÃO (Final)
  ├─ Tech Lead: Consolida todas mudanças
  ├─ DBA: Aprova schema final
  ├─ Arquiteto: Aprova design final
  ├─ PM: Aprova requisitos finais
  └─ Tech Lead: Aprova merge + comunicado aos stakeholders

FECHAMENTO
  ├─ Tech Lead: Gera summary semanal
  ├─ Tech Lead: Atualiza BACKLOG_UNIFICADO
  └─ Tech Lead: Agenda review para próxima semana
```

---

## 📊 Métricas de Orquestração (Tech Lead)

| Métrica | Alvo | Check |
|---------|------|-------|
| Docs-Code Sync | 100% | Delta analysis daily |
| Type Hints (%) | 100 | `mypy --strict` |
| Tests PASSING | 274+ | `pytest -q` final |
| Cobertura (%) | 85+ | Coverage report |
| Commits estruturados | 17+ | `git log --oneline` |
| Documentação viva (%) | 100 | Manual check |
| Sem acentos em msgs | 100% | Git message audit |
| Lint markdown (chars) | 80 max | `pymarkdown scan` |
| DBA approval | 100% | Schema checksum |
| Arquiteto approval | 100% | ADR checksum |
| PM approval | 100% | Rastreabilidade 1:1 |

---

## 📋 Sequência Paralela de Execução

### Fase 1: Desenvolvimento Independente

**Todos agentes em paralelo (sem dependências):**
- ✓ Clean Arch: ROADMAP-MICRO-03 (Design + Implementação + Testes)
- ✓ Signals: ROADMAP-DIARIOS-01 (Watchdog + Implementação + Testes)
- ✓ Storytelling: ROADMAP-DIARIOS-02 (Narrativa + Implementação + Testes)
- ✓ ML Ops: ROADMAP-DIARIOS-04 (Retrain + Implementação + Testes)

**Tech Lead (paralelo durante toda fase):**
- Valida planejamento + agentes prontos
- Monitora progresso contínuo
- Antecipa e escalona bloqueadores
- Sincroniza docs com entregas

**Checkpoints Periódicos:**
- Checkpoint 1: Design reviews (Tech Lead + DBA + Arquiteto + PM)
- Checkpoint 2: Schema/Architecture/PM approvals
- Checkpoint 3: Daily sync + Tech Lead status consolidado

### Fase 2: Integrações Cruzadas

**Conforme dependências liberadas:**
- Storytelling Part 2: ROADMAP-DIARIOS-03 (depende de Clean Arch ✓)
- ML Ops Part 2-3: ROADMAP-DIARIOS-05/06 (paralelo após Storytelling ✓)

**Tech Lead:**
- Valida integrações
- Atualiza status consolidado
- Gerencia crossover de agentes

### Fase 3: Finalização

**Todos agentes:**
- Final commits estruturados
- Type hints validation (mypy --strict)
- Cobertura ≥85% por módulo
- Documentação atualizada

**Tech Lead:**
- Consolida todas mudanças
- Valida 100% sincronização
- Gera stakeholder summary
- Aprova merge final
```

---

## ✅ Critérios de Aceitação (Por Agente)

### Clean Architecture Agent
- [ ] Type hints: 100% (mypy --strict clean)
- [ ] Docstrings: 100% em Português
- [ ] Testes: >= 37 passando (15+12+10)
- [ ] Cobertura: >= 85% por módulo
- [ ] Clean Arch: Separação camadas validada
- [ ] Commits: 3 commits estruturados
- [ ] Sem acentos em commit messages

### Signals & Observability Agent
- [ ] Type hints: 100% (mypy --strict clean)
- [ ] Docstrings: 100% em Português
- [ ] Testes: >= 49 passando (22+15+12)
- [ ] Cobertura: >= 85% por módulo
- [ ] Health Checks: 5+ tipos implementados
- [ ] Logging: Stack traces estruturados
- [ ] Commits: 3 commits estruturados
- [ ] Relatórios: JSON + Markdown gerados

### Storytelling & Narrative Agent
- [ ] Type hints: 100% (mypy --strict clean)
- [ ] Docstrings: 100% em Português
- [ ] Testes: >= 80 passando (18+20+16+14+12)
- [ ] Cobertura: >= 85% por módulo
- [ ] Persistência: SQLite validated
- [ ] Correlação: Trade ↔ Outcome 100% mapping
- [ ] Dataset: Features estruturadas exportadas
- [ ] Commits: 5 commits estruturados
- [ ] Relatórios: 3+ arquivos gerados (journal, reflection, export)

### ML Ops & Guardian Agent
- [ ] Type hints: 100% (mypy --strict clean)
- [ ] Docstrings: 100% em Português
- [ ] Testes: >= 108 passando (22+16+18+20+14+18)
- [ ] Cobertura: >= 85% por módulo
- [ ] Retreinamento: Automático com trigger
- [ ] Regime Adaptation: 4 regimes implementados
- [ ] Bias Detection: Direcional + Concentração
- [ ] Kill Switches: Universal + Coordenado
- [ ] Commits: 6 commits estruturados
- [ ] Relatórios: 4+ arquivos gerados

---

## 🚀 Dependências e Integrações

### Build Order

```
1. Clean Arch (Semana 1)
   ↓
2. Signals + Storytelling (Paralelo, Semana 2)
   ↓
3. ML Ops (Semana 2)
   ↓
4. Integração Completa + Gate 2 (Semana 3)
```

### Pontos de Integração

```python
# ROADMAP-MICRO-03 → Clean Arch
src/application/trade_outcome_reconciler.py
  ↓
scripts/agente_micro_tendencia_winfut.py (import + integração)

# ROADMAP-DIARIOS-01 → Signals
src/application/thread_watchdog_advanced.py
  ↓
scripts/start_journals_full_display.py (ThreadWatchdog)

# ROADMAP-DIARIOS-02/03 → Storytelling
src/application/narrative_persistence.py
src/application/trade_narrative_correlator.py
  ↓
scripts/start_journals_full_display.py (registrar_narrativa + refletir)

# ROADMAP-DIARIOS-04/05/06 → ML Ops
src/application/adaptive_retraining_pipeline.py
src/application/macro_guardian_universal.py
  ↓
scripts/start_journals_full_display.py (AC6.8 + AC6.9 + Guardian)
```

---

## 📊 Métricas de Sucesso

| Métrica | Alvo | Check |
|---------|------|-------|
| Type Hints (%) | 100 | `mypy --strict` |
| Tests PASSING | 274 | `pytest -q` |
| Cobertura (%) | 85+ | `--cov --cov-report=term` |
| LOC Código | 4.500+ | Quick count |
| LOC Testes | 3.800+ | Quick count |
| Commits | 17 | `git log --oneline` |
| Documentação (%) | 100 | Manual review |
| Sem acentos em msgs | 100% | Manual review |
| Lint (markdown) | 80 chars | `pymarkdown scan` |

---

## 📚 Recursos & Referências

### Documentação Obrigatória
- [ ] `CLAUDE.md` — Padrões do projeto
- [ ] `docs/BACKLOG.md` — Tarefas completas
- [ ] `docs/ARQUITETURA_ALVO.md` — Design patterns
- [ ] `.github/copilot-instructions.md` — Instruções globais

### Validações Pré-Commit

```bash
# Type hints
mypy src/ --strict

# Tests
pytest tests/ -q

# Lint
python -m pymarkdown scan docs/

# Encoding
file -i <commitados>
```

### Branch & Commits

```bash
# Branch por agente
feature/roadmap-micro-03-clean-arch
feature/roadmap-diarios-01-watchdog
feature/roadmap-diarios-02-storytelling
feature/roadmap-diarios-04-mlops

# Tamanho recomendado
Commits: 200-400 LOC cada
PRs: 1-2 features por PR
```

---

## 🎯 Próximos Passos (Após Entregas)

### Fase Operacional Imediata
1. **Runtime staging**
   - Subir o fluxo diário com `scripts/start_journals_full_display.py`
   - Validar bridge Storytelling + ML Ops em ambiente controlado
   - Registrar evidência de execução e health checks

2. **UAT com operador**
   - Executar cenários guiados sobre a cadeia já integrada
   - Confirmar comportamento de watchguards, narrativa, ML Ops e kill switch
   - Registrar divergências antes de qualquer autorização operacional

3. **Gate 2 final**
   - Revalidar reconciliação e ausência de `DESCONHECIDO`
   - Consolidar evidência de risco, PnL e rastreabilidade
   - Emitir decisão explícita `PASS` ou `FAIL`

4. **Liberação para live trading**
   - Somente após staging + UAT + Gate 2 aprovados
   - Atualizar a documentação de operação e bloqueios remanescentes
   - Recolher feedback para o próximo ciclo

---

## 📞 Escalonamento & Bloqueadores

### Bloqueadores Conhecidos
- [x] BUG-DIARIOS-04 resolvido no código; manter somente para rastreabilidade histórica.
- [x] BUG-DIARIOS-02 resolvido no código; manter somente para rastreabilidade histórica.
- [ ] Bloqueador atual: validação operacional em staging/UAT/Gate 2.

### Pontos de Escalação
| Problema | Escalador | Tempo |
|----------|-----------|-------|
| MT5 connection issue | Clean Arch | <30min |
| Database corruption | Signals | <1h |
| Model inference performance | ML Ops | <2h |
| Thread deadlock | Signals | <1h |

---

## ✍️ Observações Finais

### Princípios de Execução
1. **Clean Code First:** Type hints antes de lógica
2. **Testes Paralelos:** TDD — testes antes do código
3. **Documentação Viva:** Docstrings + exemplos de uso
4. **Commits Frequentes:** A cada feature completada
5. **Revisão Cruzada:** Agentes revisam código uns dos outros

### Risco Mitigation
- **Blockers:** Daily standup para desbloquear comunicação entre agentes
- **Integration:** Merge requests ao fim de cada dia
- **Quality:** Type hints enforçados por pre-commit hook
- **Knowledge:** Wikis / exemplos compartilhados em #shared-docs

---

**Documento Mantido por:** Equipe Multi-Agentes + Tech Lead
**Status:** Planejamento iterativo (sem data fixa)
