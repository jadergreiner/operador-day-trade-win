# 📋 Multi Agentes — Matriz de Coordenação & Checkpoints

**Objetivo:** Facilitar execução paralela com validação de dependências e
evitar bloqueadores entre agentes.

---

## 🟢 Checkpoint Real — 2026-03-18

### Execucao Paralela Concluida (Signals / ROADMAP-DIARIOS-01)

**Status geral:** Em progresso com base funcional entregue

**Entregas implementadas:**
- `src/application/thread_watchdog_advanced.py`
- `src/application/diarios_health_monitor.py`
- `src/application/logging_recovery_handler.py`
- `tests/unit/test_thread_watchdog_advanced.py`
- `tests/unit/test_diarios_health_monitor.py`
- `tests/unit/test_logging_recovery_handler.py`

**Validacao executada:**
- `pytest -q tests/unit/test_thread_watchdog_advanced.py tests/unit/test_diarios_health_monitor.py tests/unit/test_logging_recovery_handler.py`
- Resultado: `27 passed`

**Resumo de cobertura funcional desta rodada:**
- Watchdog avancado com reinicio automatico, heartbeat e health report
- Monitor de saude com severidade por thread e export markdown
- Handler de logging/recuperacao com relatorio JSON/markdown e status por componente

**Bloqueadores desta rodada:**
- Nenhum bloqueador funcional para seguir com Signals

---

## 🟢 Checkpoint Real — 2026-03-18 (Rodada 2)

### Execucao Paralela Concluida (Clean Arch + Storytelling + ML Ops)

**Status geral:** Rodada concluida com integracao validada

**Entregas por trilha:**
- Clean Arch (hardening reconciliadores)
  - `src/application/reconciliadores/trade_outcome_reconciler.py`
  - `src/application/reconciliadores/unknown_result_detector.py`
  - `src/application/reconciliadores/mt5_sync_validator.py`
  - `tests/unit/reconciliadores/*`
- Storytelling (bootstrap ROADMAP-DIARIOS-02)
  - `src/application/narrative_persistence.py`
  - `tests/unit/test_narrative_persistence.py`
- ML Ops (bootstrap ROADMAP-DIARIOS-04)
  - `src/application/directional_bias_detector.py`
  - `tests/unit/test_directional_bias_detector.py`

**Validacao integrada executada:**
- `pytest -q tests/unit/reconciliadores tests/unit/test_thread_watchdog_advanced.py tests/unit/test_diarios_health_monitor.py tests/unit/test_logging_recovery_handler.py tests/unit/test_narrative_persistence.py tests/unit/test_directional_bias_detector.py`
- Resultado: `80 passed`

**Resumo operacional desta rodada:**
- Reconciliacao endurecida para edge cases sem quebra de API
- Persistencia narrativa inicial pronta para integracoes seguintes
- Detector de vies direcional pronto para acoplamento em pipeline de ML

**Bloqueadores desta rodada:**
- Nenhum bloqueador tecnico para avancar para correlator e pipeline adaptativo

---

## 🟢 Checkpoint Real — 2026-03-18 (Rodada 3)

### Execucao Paralela Concluida (ML Ops / ROADMAP-DIARIOS-04)

**Status geral:** Pipeline adaptativo inicial entregue e validado

**Entregas implementadas:**
- `src/application/adaptive_retraining_pipeline.py`
- `tests/unit/test_adaptive_retraining_pipeline.py`

**Validacao executada:**
- `pytest -q tests/unit/test_adaptive_retraining_pipeline.py`
- Resultado: `14 passed`

**Resumo operacional desta rodada:**
- Avaliacao de gatilho por performance, drift e vies
- Planejamento de retreino com prioridade e janela off-peak
- Suporte a metricas planas e aninhadas para encaixe com outros modulos

**Bloqueadores desta rodada:**
- Nenhum bloqueador tecnico para seguir para o restante do roadmap ML Ops

---

## 🟢 Checkpoint Real — 2026-03-18 (Storytelling A)

### Execucao Paralela Concluida (Trade Narrative Correlator)

**Status geral:** Entrega concluida e validada

**Entregas implementadas:**
- `src/application/trade_narrative_correlator.py`
- `tests/unit/test_trade_narrative_correlator.py`

**Validacao executada:**
- `pytest -q tests/unit/test_narrative_persistence.py tests/unit/test_trade_narrative_correlator.py`
- Resultado: `24 passed`

**Resumo funcional desta rodada:**
- Match prioritario por `trade_id`
- Fallback temporal simples com janela configuravel
- Saida serializavel para correlacao e features

**Bloqueadores desta rodada:**
- Nenhum bloqueador para seguir com Storytelling B

---

## 🟢 Checkpoint Real — 2026-03-18 (Rodada 4)

### Execucao Paralela Concluida (Storytelling B + Guardian + DIARIOS-06)

**Status geral:** Rodada concluida com pacote multiagente integrado

**Entregas implementadas:**
- Storytelling B
  - `src/application/reflection_action_channel.py`
  - `tests/unit/test_reflection_action_channel.py`
- Guardian Universal (coordenacao)
  - `src/application/multi_agent_conflict_resolver.py`
  - `src/application/guardian_agent_coordinator.py`
  - `tests/unit/test_multi_agent_conflict_resolver.py`
  - `tests/unit/test_guardian_agent_coordinator.py`
- ML Ops / DIARIOS-06
  - `src/application/rl_episode_quality_scorer.py`
  - `src/application/execution_pattern_analyzer.py`
  - `src/application/order_manager_learner.py`
  - `tests/unit/test_rl_episode_quality_scorer.py`
  - `tests/unit/test_execution_pattern_analyzer.py`
  - `tests/unit/test_order_manager_learner.py`

**Validacao integrada executada:**
- `python -m pytest tests/unit/test_reflection_action_channel.py tests/unit/test_multi_agent_conflict_resolver.py tests/unit/test_guardian_agent_coordinator.py tests/unit/test_rl_episode_quality_scorer.py tests/unit/test_execution_pattern_analyzer.py tests/unit/test_order_manager_learner.py -q`
- Resultado: `31 passed`

**Resumo funcional desta rodada:**
- Canal de reflexao-acao com deduplicacao, vinculo temporal e sumario de impacto
- Resolucao de conflitos BUY/SELL entre agentes com trilha de auditoria
- Coordenador Guardian para decisao consolidada (executar, ajustar ou bloquear)
- Scoring de qualidade por episodio RL e agregacao por lote
- Analise de padroes de execucao (slippage, fill rate, latencia, falhas)
- Learner para recomendar ajustes operacionais (modo conservador/agressivo)

**Bloqueadores desta rodada:**
- Nenhum bloqueador tecnico para iniciar acoplamento em runtime no fluxo DIARIOS-06

---

## 🟢 Checkpoint Real — 2026-03-19 (Rodada 5)

### Execucao Paralela Concluida (Guardian Universal Log / DIARIOS-05 bootstrap)

**Status geral:** Canal universal do Guardian iniciado com persistencia multi-nivel

**Entregas implementadas:**
- Guardian Universal Log
  - `src/application/macro_guardian_universal_log.py`
  - `tests/unit/test_macro_guardian_universal_log.py`
- Integracao Macro Scenario Guardian
  - `src/application/services/macro_scenario_guardian.py`
  - `tests/unit/test_macro_scenario_guardian_persistence.py`

**Validacao integrada executada:**
- `python -m pytest -q tests/unit/test_macro_guardian_universal_log.py tests/unit/test_macro_scenario_guardian_persistence.py tests/unit/test_diario_order_manager.py`
- Resultado: `50 passed`

**Resumo funcional desta rodada:**
- Tabela `macro_guardian_log` criada com schema para INFO/WARNING/CRITICAL
- Persistencia universal de eventos macro com payload estruturado e `kill_switch_ativo`
- Consulta de eventos recentes por severidade para consumo cross-agent
- Snapshot heuristico para leitura operacional (`kill_switch_ativo`, `score_impacto_medio`, `alertas_ativos`, `regime_macro`)
- `run_guardian_check` com persistencia opcional por ciclo no canal universal

**Bloqueadores desta rodada:**
- Nenhum bloqueador tecnico para ampliar consumo do Guardian nos demais agentes

---

## 🟢 Checkpoint Real — 2026-03-19 (Rodada 6)

### Execucao Paralela Concluida (ML Ops / DIARIOS-05-06 complementar)

**Status geral:** Rodada concluida com novos modulos de adaptacao de regime e kill switch universal

**Entregas implementadas:**
- Adaptacao de regime de mercado
  - `src/application/market_regime_adapter.py`
  - `tests/unit/test_market_regime_adapter.py`
- Kill switch universal
  - `src/application/universal_kill_switch.py`
  - `tests/unit/test_universal_kill_switch.py`

**Validacao integrada executada:**
- `python -m pytest -q tests/unit/test_market_regime_adapter.py tests/unit/test_universal_kill_switch.py tests/unit/test_guardian_agent_coordinator.py tests/unit/test_macro_guardian_universal_log.py tests/unit/test_macro_scenario_guardian_persistence.py tests/unit/test_diario_order_manager.py`
- Resultado: `71 passed`

**Resumo funcional desta rodada:**
- Classificacao de regime com 4 estados operacionais (`TRENDING_UP`, `TRENDING_DOWN`, `RANGING`, `HIGH_VOLATILITY`)
- Recomendacao serializavel de risco e tamanho de posicao por regime
- Consolidacao universal de gatilhos de risco por `kill_switch_ativo`, severidade `CRITICAL` e media de `score_impacto`
- Saida auditavel para consumo por coordenadores Guardian e pipelines de decisao

**Bloqueadores desta rodada:**
- Nenhum bloqueador tecnico para seguir para acoplamento runtime no fluxo de diarios

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
