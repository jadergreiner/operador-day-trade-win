# 📋 Multi Agentes — Matriz de Coordenação & Checkpoints

**Objetivo:** Facilitar execução paralela com validação de dependências e
evitar bloqueadores entre agentes.

---

## 🔗 Matriz de Dependências

```
┌─────────────────────────────────────────────────────┐
│  ROADMAP-MICRO-03 (Clean Arch)                      │
│  Trade Outcome Reconciler                           │
│  Dependency: ZERO (independente)                    │
└─────────────────┬───────────────────────────────────┘
                  │
                  ├──────────────────────────┐
                  │                          │
┌─────────────────▼──────────┐  ┌───────────▼──────────┐
│  ROADMAP-DIARIOS-01        │  │  ROADMAP-DIARIOS-02  │
│  Signals (Watchdog)        │  │  Storytelling        │
│  Dependency: ZERO          │  │  Dependency: ZERO    │
└────────────────────────────┘  └──────────────────────┘
                  │                          │
                  └──────────┬───────────────┘
                             │
                  ┌──────────▼──────────┐
                  │ ROADMAP-DIARIOS-03  │
                  │ AI Reflection Eval  │
                  │ Dep: ROADMAP-02 ✓   │
                  └────────────────────┘
                             │
      ┌──────────────────────┼──────────────────┐
      │                      │                  │
┌─────▼─────┐  ┌────────────▼────────┐  ┌────▼──────┐
│ DIARIOS-04│  │  DIARIOS-05 (Guard) │  │ DIARIOS-06│
│ Retrain   │  │ Universal Guardian  │  │ Order Mgr │
│ Dep: 03✓  │  │ Dep: 01, 02, 03✓   │  │ Dep: 04✓  │
└───────────┘  └─────────────────────┘  └───────────┘
```

### Legenda
- ✓ = Dependência satisfeita
- → = Ordem de implementação
- 🔴 = Bloqueador crítico
- 🟡 = Pode rodar em paralelo

---

## ✅ Checkpoint Framework

### Sync de Status (Periódico)

#### Rodada 1: Status Reports

**Clean Arch Lead:**
- [ ] 250/250 LOC reconciler completado?
- [ ] 15 testes passando?
- [ ] mypy --strict clean?

**Signals Lead:**
- [ ] 450/450 LOC watchdog completado?
- [ ] 22 testes passando?
- [ ] Health reports gerados?

**Storytelling Lead:**
- [ ] 1.750/1750 LOC narrativa completado?
- [ ] 80 testes passando?
- [ ] Datasets exportados?

**ML Ops Lead:**
- [ ] 2.280/2280 LOC ML completado?
- [ ] 108 testes passando?
- [ ] Modelos versionados?

#### Rodada 2: Bloqueadores

**Todos:**
- Tem BUG que bloqueia integração?
- Precisa de código de outro agente?
- Está travado em mypy ou pytest?

#### Rodada 3: Cross-Review

**Clean Arch → Signals:**
- Reconciler afeta threads?

**Signals → Storytelling:**
- Watchdog precisa de narrativa?

**Storytelling → ML Ops:**
- Dataset exporter pronto para retrain?

**ML Ops → Clean Arch:**
- Modelos afetam reconciliação?

#### Rodada 4: Próximos Passos

- Próxima tarefa: O que fazer?
- Merge candidates preparadas?
- PRs prontas para review?

---

## 📊 Checkpoint Checklist

### Por Agente (usar a cada checkpoint)

```
## Clean Arch — Checkpoint N

### Status
- [ ] reconciliador: N/250 LOC
- [ ] detector: N/200 LOC
- [ ] validator: N/180 LOC
- [ ] Testes: N/37 PASSING
- [ ] mypy: CLEAN / 0 ERRORS

### Bloqueadores
- Nenhum / [ ] Listar

### Próximo Mileston
- [ ] Task principal

### PRs Abertas
- [ ] Link para PR (se houver)
```

---

## 🔄 Integração Sequencial

### Fase 1: Desenvolvimento Independente

Todos agentes desenvolvem em paralelo sem dependências.

```yaml
Clean Arch:
  - reconciliador.py (250 LOC)
  - detector.py (200 LOC)
  - validator.py (180 LOC)

Signals:
  - watchdog.py (450 LOC)
  - health_monitor.py (320 LOC)
  - recovery_handler.py (280 LOC)

Storytelling:
  - narrative_persistence.py (380 LOC)
  - correlator.py (420 LOC)
  - exporter.py (320 LOC)

ML Ops:
  - retraining_pipeline.py (480 LOC)
  - bias_detector.py (340 LOC)
  - regime_adapter.py (400 LOC)
```

### Fase 2: Testes Unitários

Todos agentes concluem testes em paralelo.

```yaml
Total: 274 testes = 37 + 49 + 80 + 108

Target: 100% PASSING por DIA 3 noon
```

### Fase 3: Integrações Cruzadas

Agentes conectam código respeitando dependências.

```
Milestone 1 (Clean Arch finaliza):
  ├─ Outputs: 3 modules + 37 tests
  ├─ Signals integra no diary manager (paralelo)
  └─ Storytelling aguarda para Part 2

Milestone 2 (Storytelling pronto):
  ├─ Inputs: datasets de Storytelling
  ├─ ML Ops integra retreinamento
  └─ Final integration tests (E2E)
```

### Fase 4: Finalização

Commits estruturados, polish da documentação, validação final.

---

## 🎯 Merge Strategy

### Branch Per Agent

```bash
# Clean Arch
git checkout -b feature/roadmap-micro-03-reconciler

# Signals
git checkout -b feature/roadmap-diarios-01-watchdog

# Storytelling
git checkout -b feature/roadmap-diarios-02-storytelling

# ML Ops
git checkout -b feature/roadmap-diarios-04-mlops
```

### Merge Order (DIA 5)

1. **Clean Arch** (no dependencies) → `main`
2. **Signals** (no deps) → `main`
3. **Storytelling** (depends on 02 OK) → `main`
4. **ML Ops** (depends on storytelling OK) → `main`

### PR Template

```markdown
## [Agent Name] - ROADMAP-XXXXX

### Summary
Brief description

### Metrics
- [ ] Type hints: 100%
- [ ] Tests: N/N PASSING
- [ ] Cobertura: ≥85%
- [ ] mypy --strict: CLEAN

### Reviewers
- [ ] Cross-agent reviewer

### Merge Criteria
- [x] Tests passing
- [x] Code review approved
- [x] No blockers
```

---

## 📊 Real-Time Progress Board

### Atualize durante daily sync:

| Agent | Task | Status | LOC | Tests | Ready? |
|-------|------|--------|-----|-------|--------|
| Clean | Recon | ██████ | 250 | 15/15 | ✅ |
| Clean | Detect | ░░░░░░ | 50 | 5/12 | ⏳ |
| Signals | Watch | ░░░░░░ | 0 | 0/22 | ⏳ |
| Story | Narr | ░░░░░░ | 0 | 0/18 | ⏳ |
| ML | Retrain | ░░░░░░ | 0 | 0/22 | ⏳ |

---

## 🚨 Bloqueador Escalation

### Red Flag Conditions

| Trigger | Action | Owner |
|---------|--------|-------|
| pytest FAIL | Debug + pair session | Agente + Lead |
| mypy ERROR | Review types + fix | Clean Arch + Agente |
| DB corruption | Rollback + fix schema | ML Ops |
| MT5 failed | Skip MT5 tests locally | Agente |

### SLA de Resposta

Se código bloqueador é encontrado:

1. **Agente reporta** em checkpoint
2. **Lead responde** rapidamente com sugestão
3. **Cross-review** implementado
4. **Merge blocker** resolvido ou escalado

---

## 📞 Communication Channels

### Instantaneous (para bloqueadores)
- Comunicação direta com lead

### Checkpoint (para updates)
- Validação periódica de status

### Async (para feedback)
- PR comments
- GitHub discussions

### Documentation
- This file (updated daily)
- docs/PLANO_MULTI_AGENTES.md (master plan)

---

## ✨ Status Update Template

**Use neste checkpoint (copiar & colar):**

```
## [Agent Name] Update - Checkpoint N

### ✅ Completed Since Last Sync
- Feature X: Y LOC
- Tests: N PASSING
- ...

### ⏳ In Progress Now
- Feature Z: Design/Coding/Testing phase
- ETA: Y hours

### 🚨 Blockers / Issues
- [ ] NONE
- [ ] Issue 1: [Description + ETA to resolve]

### ❓ Dependencies / Questions
- Does Signals need narrative data?
- Can ML Ops start without reconciler?
- ...

### 🎯 Próximas Tasks
1. Feature implementation
2. Unit tests
3. Code review

### 📊 Metrics
- Total LOC written: YYY
- Tests passing: NN/NN
- mypy status: ✅ CLEAN / ❌ ERRORS
```

---

**Template Version:** 1.0 | **Status:** Ativo

**Coordinator:** Multi-Agent Lead

**Checkpoint:** Periódico conforme progresso
