# 🤖 Plano de Multi Agentes — Entregas Backlog (Clean Code)

**Data:** 18/03/2026 | **Status:** Planejamento Executivo


---

## 📊 Visão Geral de Tarefas Pendentes

| # | Tarefa | Agente | Estado | Prioridade |
|---|--------|--------|--------|------------|
| 1 | ROADMAP-MICRO-03 | Clean Arch | ❌ PENDENTE | 🔴 CRÍTICA |
| 2 | ROADMAP-DIARIOS-01 | Signals | ❌ PENDENTE | 🟡 ALTA |
| 3 | ROADMAP-DIARIOS-02 | Storytelling | ❌ PENDENTE | 🟡 ALTA |
| 4 | ROADMAP-DIARIOS-03 | Learning | ❌ PENDENTE | 🟡 MÉDIA |
| 5 | ROADMAP-DIARIOS-04 | ML Ops | ❌ PENDENTE | 🟡 MÉDIA |
| 6 | ROADMAP-DIARIOS-05 | Guardian | ❌ PENDENTE | 🟢 BAIXA |
| 7 | ROADMAP-DIARIOS-06 | Adapty | ❌ PENDENTE | 🟢 BAIXA |

**Total Esforço:** 85-100 horas (7 tarefas × ~12-14h cada)
**Timeline:** 5-6 dias (ciclo 2 semanas recomendado)

---

## 🎯 4 Agentes Especializados

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

## 📋 Cronograma Paralelo (5-6 dias)

```
DIA 1 (Segundo-feira)
├─ 09:00-10:30: Kickoff + Planning (todos agentes)
├─ 10:30-17:30:
│  ├─ Clean Arch: ROADMAP-MICRO-03 Part 1 (Análise + Design)
│  ├─ Signals: ROADMAP-DIARIOS-01 Part 1 (Watchdog Design)
│  ├─ Storytelling: ROADMAP-DIARIOS-02 Part 1 (Schema + Persistence)
│  └─ ML Ops: ROADMAP-DIARIOS-04 Part 1 (Pipeline Design)
└─ 17:30-18:00: Daily Sync

DIA 2 (Terça-feira)
├─ 09:00-10:00: Sync de Bloqueadores
├─ 10:00-17:30:
│  ├─ Clean Arch: ROADMAP-MICRO-03 Part 2 (Implementação + Testes)
│  ├─ Signals: ROADMAP-DIARIOS-01 Part 2 (Implementação + Testes 22/22)
│  ├─ Storytelling: ROADMAP-DIARIOS-02 Part 2 (Correlação + Tests 20/20)
│  └─ ML Ops: ROADMAP-DIARIOS-04 Part 2 (Regime Adapter + Tests 18/18)
├─ 17:30-18:00: Code Review Paralelo
└─ 18:00-18:30: Integration Planning

DIA 3 (Quarta-feira)
├─ 09:00-10:00: Code Review Results
├─ 10:00-17:30:
│  ├─ Clean Arch: ROADMAP-MICRO-03 Finalização + Commits
│  ├─ Signals: Integração nos Diários
│  ├─ Storytelling: ROADMAP-DIARIOS-03 (Reflection Evolution + 16 testes)
│  └─ ML Ops: ROADMAP-DIARIOS-05 (Guardian Universal + 20 testes)
├─ 17:30-18:00: Integration Testing
└─ 18:00-18:30: Documentation Sync

DIA 4 (Quinta-feira)
├─ 09:00-10:00: Integration Issues Resolution
├─ 10:00-17:30:
│  ├─ Clean Arch: Code Review + Quality Gates
│  ├─ Signals: Finalização + Documentação
│  ├─ Storytelling: Exportador de Dataset (14 testes) + Action Channel (12 testes)
│  └─ ML Ops: Order Manager Learner (18 testes) + Finalização
├─ 17:30-18:00: Final Testing
└─ 18:00-18:30: Merge Planning

DIA 5 (Sexta-feira)
├─ 09:00-10:00: Pre-merge Review
├─ 10:00-15:00:
│  ├─ Todos: Final Commits + Squash
│  ├─ Todos: Documentation Polish
│  ├─ Todos: Type Hints Validation (mypy --strict)
│  └─ Todos: README + CHANGELOG Update
├─ 15:00-16:30: Integration Testing Completo
├─ 16:30-17:00: Gate 2 Preparation
└─ 17:00-18:00: Sprint Retrospective
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

### Fase 2 (Semana 4-5)
1. **Integração Completa** (Todos agentes)
   - Deploy em staging
   - UAT com operador
   - Performance benchmarks

2. **Gate 2 Final** (Clean Arch Lead)
   - Validação de reconciliação 100%
   - Zero resultados `DESCONHECIDO`
   - Live trading authorization

3. **Dashboard Unificado** (Signals Lead)
   - Real-time health display
   - Alertas estruturados
   - Metricas consolidadas

### Fase 3 (Semana 6+)
1. **Roadmap P3** (ML Ops Lead)
   - Multi-agent coordination
   - Advanced regime detection
   - Portfolio optimization

2. **Observabilidade Enterprise** (Signals Lead)
   - Prometheus metrics
   - Grafana dashboards
   - Alert routing

---

## 📞 Escalonamento & Bloqueadores

### Bloqueadores Conhecidos
- [ ] BUG-DIARIOS-04 (NameError motor_decisao) — **Resolver antes integração**
- [ ] BUG-DIARIOS-02 (eficiencia_pct) — **Resolver antes ML Ops**

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
- **Blockers:** Daily-standup @15:00 BRT para desbloquear
- **Integration:** Merge requests ao fim de cada dia
- **Quality:** Type hints enforçados por pre-commit hook
- **Knowledge:** Wikis / exemplos compartilhados em #shared-docs

---

**Documento Mantido por:** Equipe Multi-Agentes
**Última Atualização:** 18/03/2026
**Próxima Review:** 25/03/2026 (Kickoff Sprint 2)
