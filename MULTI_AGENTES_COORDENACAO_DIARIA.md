# 📋 Multi Agentes — Matriz de Coordenação & Daily Checkpoints

**Objetivo:** Facilitar sincronização paralela evitando bloqueadores.

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

## 📅 Daily Checkpoint Framework

### Daily Sync @15:00 BRT (30 minutos)

#### Rodada 1: Status Reports (5 min)

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

#### Rodada 2: Bloqueadores (10 min)

**Todos:**
- Tem BUG que bloqueia integração?
- Precisa de código de outro agente?
- Está travado em mypy ou pytest?

#### Rodada 3: Cross-Review (10 min)

**Clean Arch → Signals:**
- Reconciler afeta threads?

**Signals → Storytelling:**
- Watchdog precisa de narrativa?

**Storytelling → ML Ops:**
- Dataset exporter pronto para retrain?

**ML Ops → Clean Arch:**
- Modelos afetam reconciliação?

#### Rodada 4: Plan Ahead (5 min)

- Próximos 4 horas: O que fazer?
- Merge candidates para fim do dia?
- PRs prontas para review?

---

## ✅ Daily Checkpoint Checklist

### By Agent (copy & paste daily)

```
## Clean Arch — DIA N

### Status
- [ ] reconciliador: N/250 LOC
- [ ] detector: N/200 LOC
- [ ] validator: N/180 LOC
- [ ] Testes: N/37 PASSING
- [ ] mypy: CLEAN / 0 ERRORS

### Bloqueadores
- Nenhum / [ ] Listar

### Próximas 4h
- [ ] Task principal

### PRs Abertas
- [ ] Link para PR (se houver)
```

---

## 🔄 Integração Sequencial

### Fase 1: Código Independente (DIA 1-2)

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

### Fase 2: Testes Unitários (DIA 2-3)

Todos agentes adicionam testes em paralelo.

```yaml
Total: 274 testes = 37 + 49 + 80 + 108

Target: 100% PASSING por DIA 3 noon
```

### Fase 3: Integrações Cruzadas (DIA 3-4)

Agentes conectam código em sequência.

```
DIA 3 afternoon:
  ├─ Clean Arch finaliza
  │  └─ Outputs: 3 modules + 37 tests
  │
  ├─ Signals integra no diary manager
  │  └─ Inputs: watchdog + recovery + health
  │
  └─ Storytelling integra no narrative loop
     └─ Outputs: datasets pronto para DIA 4

DIA 4:
  ├─ ML Ops integra retreinamento
  │  └─ Inputs: datasets de Storytelling
  │
  └─ Final integration tests
     └─ E2E: agentes conversando
```

### Fase 4: Finalização (DIA 5-6)

Commits, polishing, retrospective.

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

### 15-Minute Response SLA

Se código bloqueador é encontrado:

1. **Agente reporta** em daily sync
2. **Lead responde** em <15 min com sugestão
3. **Cross-review** em <30 min
4. **Merge blocker** resolvido ou escalado

---

## 📞 Communication Channels

### Instantaneous (Use for blockers)
- Slack #multi-agentes-realtime

### Scheduled (Use for updates)
- Daily 15:00 BRT sync call

### Async (Use for feedback)
- PR comments
- GitHub discussions

### Documentation
- This file (updated daily)
- docs/PLANO_MULTI_AGENTES.md (master plan)

---

## ✨ Daily Standup Template

**Use this in daily sync call (copy & paste):**

```
## [Agent Name] Update - DIA N

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

### ❓ Questions for Others
- Does Signals need narrative data?
- Can ML Ops start without reconciler?
- ...

### 🎯 Next 4 Hours
1. Feature implementation
2. Unit tests
3. Code review

### 📊 Metrics
- Total LOC written: YYY
- Tests passing: NN/NN
- mypy status: ✅ CLEAN / ❌ ERRORS
```

---

**Template Version:** 1.0 | **Last Update:** 18/03/2026

**Coordinator:** Multi-Agent Scrum Master

**Next Review:** Daily @15:00 BRT
