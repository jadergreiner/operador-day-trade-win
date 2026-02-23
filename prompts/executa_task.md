# 🚀 EXECUTA TASK - Sprint 1 Operador Day Trade WIN

## 📌 Contexto do Projeto

**Projeto:** Operador Day Trade WIN
**Sprint:** Sprint 1 (27/02 - 05/03 2026)
**Data Execução:** 23/02/2026
**Status:** ✅ Todos pré-requisitos atendidos

- ✅ Análise de Priorização: [prompts/solicita_task.md](solicita_task.md) (completa)
- ✅ Design Phase 1: 100% pronto
- ✅ Risk Framework: Aprovado por 4 personas
- ✅ Decisões Financeiras: Green light CFO + Head Finanças
- ✅ Squad Multidisciplinar: Pronto para execução

---

## 🎯 PRÓXIMA TASK PRIORITÁRIA

### Task Selecionada: **TODO-1: Label backtest_optimized_results JSON**

```
┌──────────────────────────────────────────────────────────┐
│ 🔴 PRIORIDADE CRÍTICA - Bloqueia Sprint 2 inteiro        │
│                                                           │
│ Nome: Label backtest_optimized_results JSON              │
│ Arquivo: src/application/ml_feature_engineer.py:447-448  │
│ Status: ⏳ NÃO INICIADA - PRONTA                         │
│ Esforço: 2-3 horas                                        │
│ Deadline: 24/02 EOD (implementar) | 25/02 (validar)      │
│                                                           │
│ Desbloqueia:                                             │
│  • Grid Search Sprint 2 (~140h de work)                   │
│  • Go-Live v1.2 (10/04)                                   │
│  • Execução automática                                    │
└──────────────────────────────────────────────────────────┘
```

### Task Secundária (Paralelo): **TODO-2,3,4: OrdersExecutor**

```
┌──────────────────────────────────────────────────────────┐
│ 🔴 PRIORIDADE CRÍTICA - Bloqueia 50% Sprint 1             │
│                                                           │
│ Nome: OrdersExecutor - Implementar 3 TODOs               │
│ Arquivo: src/application/orders_executor.py:133,158,188  │
│ Status: ⏳ NÃO INICIADA - PRONTA                         │
│ Esforço: 3-4 horas                                        │
│ Deadline: 02/03 (implementar) | 03/03 (validar)          │
│                                                           │
│ Desbloqueia:                                             │
│  • Orders execution flow                                  │
│  • Risk framework validation                              │
│  • E2E trading pipeline                                   │
│  • Sprint 1 completion ~95% (com parallelismo)           │
└──────────────────────────────────────────────────────────┘
```

---

## 👥 ALOCAÇÃO DE PERSONAS (SQUAD MULTIDISCIPLINAR)

### Personas Designadas (conforme especialidades)

```
TASK TODO-1: Label backtest_optimized_results
├─ Lead: Persona 2 - "The Brain" (ML/IA & Strategy)
│         Especialidade: Machine Learning, Feature Engineering, Data Science
│         Habilidades: XGBoost, Grid Search, Backtest, Dataset Design
│         Responsabilidades:
│           • Carregar backtest_optimized_results.json
│           • Implementar load_and_label() com window_id → labels
│           • Validar imbalance < 70%
│           • Escrever unit tests (test_load_and_label_success)
│           • Validar performance < 500ms
│
├─ Suporte: Persona 12 - "Quality" (QA/Testes Automation)
│           Especialidade: QA, Testes, Validação
│           Responsabilidades:
│             • Validar AC (Acceptance Criteria)
│             • Escrever testes de cobertura > 90%
│             • Validar zero NaN values
│             • Documentar resultados
│
└─ Suporte: Persona 8 - "Audit" (QA & Documentação)
            Especialidade: QA, Testes, Documentação, Auditoria
            Responsabilidades:
              • Validar documentação
              • Atualizar ANALISE_PRIORIZACAO_23FEV.md
              • Checklist de AC final

────────────────────────────────────────────────────────

TASK TODO-2,3,4: OrdersExecutor
├─ Lead: Persona 1 - "Engenheiro Senior" (Eng Sr)
│         Especialidade: Arquitetura, Orders, Risk Systems
│         Habilidades: Python, System Design, Integration
│         Responsabilidades:
│           • Implementar execute_order() (line 133)
│           • Implementar monitor_positions() (line 158)
│           • Implementar handle_stop_loss() (line 188)
│           • Integrar Risk Validator + MT5Adapter
│           • Escrever unit tests (execute_order, monitor, SL)
│
├─ Suporte: Persona 6 - "Arch" (Arquitetura Software)
│           Especialidade: Arquitetura, Design Patterns, System Design
│           Responsabilidades:
│             • Validar design patterns (queue, async)
│             • Revisar integração com Risk Framework
│             • Assegurar resilience + error handling
│             • Code review arquitetura
│
├─ Suporte: Persona 12 - "Quality" (QA/Testes)
│           Responsabilidades:
│             • Escrever testes E2E (execute_order + monitoring)
│             • Mockear MT5Adapter para testes
│             • Validar circuit breaker scenarios
│
└─ Suporte: Persona 8 - "Audit" (Documentação)
            Responsabilidades:
              • Documentar 3 implementações
              • Atualizar AC checklist
              • Manter rastreabilidade

────────────────────────────────────────────────────────

TAREFAS DE SINCRONIZAÇÃO (Paralelo com todo o work)
├─ Lead: Persona 17 - "Doc Advocate" (Documentação & Sync)
│         Especialidade: Documentação, Sync, Knowledge Management
│         Responsabilidades:
│           • Manter ANALISE_PRIORIZACAO_23FEV.md atualizado
│           • Sincronizar docs do agente_autonomo/
│           • Validar SYNC_MANIFEST.json
│           • Atualizar README.md
│
├─ Suporte: Persona 7 - "The Blueprint" (Infra+ML)
│           Responsabilidades:
│             • Atualizar VERSIONING.json
│             • Validar checksums em SYNC_MANIFEST
│             • Health check automático
│
└─ Suporte: Persona 8 - "Audit" (Documentação final)
            Responsabilidades:
              • Lint markdown final
              • Validar UTF-8 em commit message
              • Auditar sincronização
```

---

## 📊 PARALELIZAÇÃO DE ATIVIDADES

### Timeline Esperado

```
HOJE 23/02
├─ 21:35 UTC: Criar issues no GitHub (4 issues)
│              ├─ ISSUE-A: TODO-1 (Persona 2 - The Brain)
│              ├─ ISSUE-B: TODO-2,3,4 (Persona 1 - Eng Sr)
│              ├─ ISSUE-C: Detector padrões backtest (Persona 2)
│              └─ ISSUE-D: Integração detector (Persona 2)
│
├─ 22:00 UTC: Preparar ambiente (Persona 7 - The Blueprint)
│              ├─ Setup notebooks ML
│              ├─ Setup dev environment Eng Sr
│              └─ Setup CI/CD para testes
│
└─ 23:59 UTC: Finalizar documentação baseplate (Persona 17 - Doc Advocate)
               ├─ Atualizar ANALISE_PRIORIZACAO_23FEV.md
               ├─ Sincronizar docs agente_autonomo/
               └─ Commit inicial

────────────────────────────────────────────────────────

SEG 24/02 (Primeira metade do dia)
├─ 09:00 BRT: Kickoff Meeting (Squad + CTO)
│              ├─ Realinhamento de AC (Personas 2 + 1)
│              ├─ QA checklist (Persona 12)
│              └─ Sync checklist (Persona 17)
│
├─ 10:00-12:00: PARALELO - TODO-1 Implementation
│                Persona 2 (The Brain) + Persona 12 (Quality)
│                ├─ Load JSON + map window_id
│                ├─ Implementar load_and_label()
│                ├─ Validar imbalance
│                └─ Escrever unit tests
│
├─ 10:00-12:00: PARALELO - OrdersExecutor Setup
│                Persona 1 (Eng Sr) + Persona 6 (Arch)
│                ├─ Design 3 TODOs (execute, monitor, SL)
│                ├─ Setup mock MT5Adapter
│                ├─ Define queue/async pattern
│                └─ Create test stubs
│
├─ 10:00-12:00: PARALELO - Env & Infra Setup
│                Persona 7 (The Blueprint)
│                ├─ Setup pytest fixtures
│                ├─ Configure CI/CD
│                └─ Validate dependencies
│
└─ 12:00-13:00: Sync + Lunch break

────────────────────────────────────────────────────────

SEG 24/02 (Tarde) + TUE 25/02 (Manhã)
├─ 14:00-17:00 (24/02): TODO-1 Testing & Validation
│                       Persona 2 + Persona 12
│                       ├─ Run unit tests (coverage > 90%)
│                       ├─ Validate AC (7 criteria)
│                       ├─ Performance benchmark < 500ms
│                       └─ Zero NaN validation
│
├─ 14:00-17:00 (24/02): OrdersExecutor Implementation
│                       Persona 1 + Persona 6 + Persona 12
│                       ├─ Implement execute_order() (line 133)
│                       ├─ Implement monitor_positions() (line 158)
│                       ├─ Implement handle_stop_loss() (line 188)
│                       ├─ Write & run unit tests
│                       └─ Code review (Persona 6)
│
├─ 14:00-17:00 (24/02): Documentation Update
│                       Persona 17 + Persona 8
│                       ├─ Update ANALISE_PRIORIZACAO_23FEV.md
│                       ├─ Sync agente_autonomo/ docs
│                       ├─ Update README.md
│                       └─ Lint markdown (MD013 check)
│
└─ 09:00-12:00 (25/02): Final Validation & Integration Testing
                        All personas (coordenado por CTO)
                        ├─ E2E test (TODO-1 + OrdersExecutor)
                        ├─ Performance validation
                        ├─ Documentation final review
                        └─ Gate readiness check (pre-27/02 kickoff)
```

---

## 📋 CARREGAMENTO DE DIRETRIZES E BOAS PRÁTICAS

### Carregar: `.github/copilot-instructions.md`

**Requisitos Obrigatórios:**

✅ **1. Português 100%**
- Todos os commits em português: `git commit -m "feat: implementar label dataset"`
- Documentação em português
- Sem "TODO:" em inglês (converter para "TAREFA:" ou manter em português)

✅ **2. UTF-8 Encoding**
- Validar antes de commit: `git log --oneline | grep "├"`
- Se encontrar caracteres corrompidos: refazer commit com UTF-8 explícito

✅ **3. Markdown Lint (MD013)**
- Rodar antes de commit: `python -m pymarkdown scan docs/`
- Máximo 80 caracteres por linha
- Validar cabeçalhos em sequência (MD001, MD002)

✅ **4. Sincronização Obrigatória**
- Atualizar SYNC_MANIFEST.json após mudanças
- Sincronizar cross-references em docs/agente_autonomo/
- Validar checksums em SYNC_MANIFEST
- Atualizar VERSIONING.json com versão nova

✅ **5. Pre-Commit Validation**
- [ ] Todos docs agente_autonomo presentes?
- [ ] SYNC_MANIFEST.json atualizado com checksums?
- [ ] Cross-references válidas?
- [ ] Timestamps sincronizados?
- [ ] VERSIONING.json reflete mudanças?
- [ ] Nenhum doc marcado como "unsyncronized"?

---

## 📝 ETAPAS DE FINALIZAÇÃO

### ETAPA 1: Atualizar Documentação 📄

```bash
CHECKLIST:

[ ] Actualizar ANALISE_PRIORIZACAO_23FEV.md
    ├─ Seção "PRÓXIMA TASK PRIORITÁRIA": TODO-1 marcar como IN-PROGRESS
    ├─ Seção "TOP 3 PRÓXIMAS": TODO-2,3,4 marcar como IN-PROGRESS
    ├─ Seção "ISSUES PARA CRIAR": Marcar como CRIADAS (+ issue numbers)
    ├─ Seção "Dias do Sprint": Adicionar progresso dia 24-25/02
    └─ Timestamp: Atualizar "Última Atualização: 23/02/2026"

[ ] Synchronizar docs/agente_autonomo/
    ├─ AGENTE_AUTONOMO_ARQUITETURA.md: Refletir OrdersExecutor no diagrama
    ├─ AGENTE_AUTONOMO_FEATURES.md: ML-001 (Dataset) em progresso
    ├─ SYNC_MANIFEST.json: Update checksums de files modificados
    ├─ VERSIONING.json: Bump minor version (v1.0.X → v1.0.X+1)
    └─ README.md: Update Sprint 1 section com issue links

[ ] Atualizar PLANO_DE_SPRINTS_MVP_NOW.md
    ├─ Sprint 1 → Adicionar link para issues criadas
    ├─ MUST tasks: Marcar TODO-1 como INITIATED
    ├─ MUST tasks: Marcar TODO-2,3,4 como INITIATED
    └─ Timeline: Update "% de conclusão esperado"

[ ] Criar/Atualizar docs/agente_autonomo/SPRINT1_DAY1_REVIEW.md (novo)
    ├─ Issues created (4 issues)
    ├─ Personas allocated (8 personas)
    ├─ Timeline paralelo (esquema de paralelismo)
    ├─ Blockers: None ✅
    ├─ Prerequisites: All met ✅
    └─ Expected completion: 25/02 EOD

[ ] Validar Markdown Lint
    bash
    python -m pymarkdown scan docs/ANALISE_PRIORIZACAO_23FEV.md
    python -m pymarkdown scan docs/PLANO_DE_SPRINTS_MVP_NOW.md
    python -m pymarkdown scan docs/agente_autonomo/SYNC_MANIFEST.json
    python -m pymarkdown fix docs/  # Se erros encontrados

```

### ETAPA 2: Preparar Commit 💾

```bash
CHECKLIST:

[ ] Review de todo o código modificado
    git diff docs/  # Revisar todas as mudanças em markdown
    git diff docs/agente_autonomo/

[ ] Validar mensagem de commit
    Format: "feat: Iniciar Sprint 1 - TODO-1 + TODO-2,3,4 + 8 personas squad"
    ✓ Em português
    ✓ Max 72 caracteres (primeira linha)
    ✓ UTF-8 encoding
    ✓ Sem caracteres corrompidos (├, ┌, etc)

[ ] Exemplo de mensagem:
    git commit -m "feat: Iniciar Sprint 1 - Issues #66, #67, etc; 8 personas squad pronto"

[ ] Draft de commit message (body):
    ✓ Resumo de mudanças (docs sync)
    ✓ Issues criadas (4 issues)
    ✓ Personas alocadas (8 personas)
    ✓ Timeline paralelo
    ✓ Pre-requisites met
    ✓ Next steps (kickoff 27/02)

```

### ETAPA 3: Git Push 🚀

```bash
CHECKLIST:

[ ] Validar branch
    git branch  # Deve estar em main ou feature branch
    git status  # Apenas files modificados (sem untracked)

[ ] Push para repositório
    git add docs/ANALISE_PRIORIZACAO_23FEV.md
    git add docs/PLANO_DE_SPRINTS_MVP_NOW.md
    git add docs/agente_autonomo/
    git add prompts/  # Se atualizado
    git commit -m "feat: Iniciar Sprint 1 - 4 issues + 8 personas squad"
    git push origin main

[ ] Validar push
    git log --oneline -5  # Confirmar commit apareceu
    gh issue list --limit 10  # Confirmar issues visíveis

```

### ETAPA 4: Finalizar com Resumo 📊

```markdown
# 📋 RESUMO DE ALTERAÇÕES - Sprint 1 Kickoff

## ✅ Documentação Atualizada

### Docs Modificadas (5 arquivos)
- [x] ANALISE_PRIORIZACAO_23FEV.md (sincronizado com task progress)
- [x] PLANO_DE_SPRINTS_MVP_NOW.md (linked issues + timeline)
- [x] docs/agente_autonomo/SYNC_MANIFEST.json (checksums updated)
- [x] docs/agente_autonomo/VERSIONING.json (version bumped)
- [x] README.md (Sprint 1 section updated)

### Novo Documento Criado (1 arquivo)
- [x] docs/agente_autonomo/SPRINT1_DAY1_REVIEW.md (progress track)

## ✅ Issues Criadas (4 issues)

| # | Título | Persona | Prioridade | Status |
|---|--------|---------|-----------|--------|
| #66 | [SPRINT-1] Label backtest_optimized_results | The Brain (Persona 2) | 🔴 CRÍTICA | ASSIGNED |
| #67 | [SPRINT-1] OrdersExecutor - 3 TODOs | Eng Sr (Persona 1) | 🔴 CRÍTICA | ASSIGNED |
| #68 | [SPRINT-2] Detector padrões no backtest | The Brain (Persona 2) | 🟠 ALTA | CREATED |
| #69 | [SPRINT-2] Integração detector padrões | The Brain (Persona 2) | 🟠 ALTA | CREATED |

## ✅ Squad Multidisciplinar Alocado (8 personas)

| Persona | Especialidade | Task | Status |
|---------|---------------|------|--------|
| Persona 1 | Eng Sr | OrdersExecutor (TODO-2,3,4) | 🟢 READY |
| Persona 2 | The Brain (ML/IA) | Label dataset (TODO-1) | 🟢 READY |
| Persona 6 | Arch | Design + Code Review | 🟢 READY |
| Persona 7 | The Blueprint (Infra) | Setup + Infra | 🟢 READY |
| Persona 8 | Audit (QA & Docs) | QA + Documentação final | 🟢 READY |
| Persona 12 | Quality (QA/Testes) | Unit + E2E tests | 🟢 READY |
| Persona 17 | Doc Advocate | Sync + README | 🟢 READY |
| Personas 3-5, 9-11 | Suporte conforme necessário | Escalation | 🟢 ON-CALL |

## ✅ Timeline e Milestones

- **HJ 23/02 (21:35 UTC):** Issues criadas + docs sincronizadas + commit inicial
- **24/02 (09:00-17:00):** Implementação paralela TODO-1 + OrdersExecutor + Infra setup
- **25/02 (09:00-12:00):** Testing + Validation + Documentation final
- **27/02 (09:00):** 🚀 Sprint 1 Official Kickoff

## ✅ Pre-requisitos Validados

- ✅ Análise de priorização completa
- ✅ Design 100% pronto
- ✅ Risk framework aprovado
- ✅ Decisões financeiras green light
- ✅ Squad pronto
- ✅ Docs sincronizadas
- ✅ AC definidos
- ✅ Bloqueadores: NENHUM

## 🎯 Próximos Passos

1. **Amanhã 24/02:** Executores começam trabalho paralelo (TODO-1 + OrdersExecutor)
2. **25/02:** QA validation + final documentation
3. **27/02:** Sprint 1 Official Kickoff (Gate 1 em 05/03 17:00)

---

**Commit:** `feat: Iniciar Sprint 1 - 4 issues + 8 personas squad`
**Date:** 23/02/2026 21:35 UTC
**Status:** ✅ COMPLETE - Pronto para Sprint 1
```

---

## 🎬 COMO USAR ESTE PROMPT

### Passo 1: Carregar Instruções
```bash
# Já carregue as instruções do Copilot
cat .github/copilot-instructions.md
```

### Passo 2: Executar Task (TODO-1)
```bash
# Começar com TODO-1 (The Brain - Persona 2)
# Issue #66: Label backtest_optimized_results

# 2a. Setup ML environment
python -m venv venv_ml
source venv_ml/bin/activate  # Windows: venv_ml\Scripts\activate
pip install -r requirements.txt

# 2b. Implementar load_and_label()
# File: src/application/ml_feature_engineer.py:447-448
# → Implementar conforme AC

# 2c. Escrever unit tests
pytest tests/ -v -k "test_load_and_label"

# 2d. Validar performance
time python scripts/validate_load_and_label.py
```

### Passo 3: Paralelo - OrdersExecutor (Eng Sr)
```bash
# Issue #67: OrdersExecutor - 3 TODOs
# Pessoa: Eng Sr (Persona 1)

# 3a. Review architecture + Risk Framework
cat docs/agente_autonomo/ARQUITETURA_MT5_v1.2.md

# 3b. Implementar 3 TODOs
# File: src/application/orders_executor.py:133,158,188
# → execute_order() + monitor_positions() + handle_stop_loss()

# 3c. Unit tests
pytest tests/ -v -k "test_orders_executor"

# 3d. Code review
python -m mypy src/application/orders_executor.py --strict
```

### Passo 4: Documentação e Sync
```bash
# Persona 17 (Doc Advocate) + Persona 8 (Audit)

# 4a. Update docs
vim docs/ANALISE_PRIORIZACAO_23FEV.md  # Sync progress
vim docs/PLANO_DE_SPRINTS_MVP_NOW.md   # Link issues
vim docs/agente_autonomo/SYNC_MANIFEST.json  # Checksums

# 4b. Lint markdown
python -m pymarkdown scan docs/
python -m pymarkdown fix docs/

# 4c. Commit
git add docs/ prompts/
git commit -m "feat: Sprint 1 kickoff - 4 issues + squad pronto"
git push origin main
```

---

## 🔗 Referências Rápidas

| Referência | Link |
|-----------|------|
| **Análise de Priorização** | [prompts/solicita_task.md](solicita_task.md) |
| **Issues Templates** | [GITHUB_ISSUES_TEMPLATES_23FEV.md](../GITHUB_ISSUES_TEMPLATES_23FEV.md) |
| **Copilot Instructions** | [.github/copilot-instructions.md](../.github/copilot-instructions.md) |
| **Personas Data** | [prompts/board_16_members_data.json](board_16_members_data.json) |
| **Sprint Plan** | [docs/PLANO_DE_SPRINTS_MVP_NOW.md](../docs/PLANO_DE_SPRINTS_MVP_NOW.md) |
| **Risk Framework** | [docs/agente_autonomo/RISK_FRAMEWORK_v1.2.md](../docs/agente_autonomo/RISK_FRAMEWORK_v1.2.md) |
| **Architecture** | [docs/agente_autonomo/ARQUITETURA_MT5_v1.2.md](../docs/agente_autonomo/ARQUITETURA_MT5_v1.2.md) |

---

**Status:** ✅ Pronto para Executar
**Próximo Passo:** Executar `prompts/executa_task.md` para iniciar Sprint 1
**Timeline:** 23/02 Hoje → 27/02 Kickoff Oficial → 05/03 Gate 1 Check
