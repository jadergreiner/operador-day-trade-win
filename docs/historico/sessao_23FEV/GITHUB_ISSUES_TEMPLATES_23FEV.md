# 🐙 GitHub Issues - Criar com gh cli

**Status:** 4 issues prontas para criar HOJE (23/02)
**Comando:** Use `gh issue create` com os templates abaixo
**Documentação:** https://cli.github.com/manual/gh_issue_create

---

## ISSUE-1: [SPRINT-1] Label backtest_optimized_results ⚠️ BLOCKER

**Tipo:** Bug + Task (código quebrado)
**Prioridade:** 🔴 CRÍTICO (bloqueia ML training)
**Sprint:** Sprint 1 (27/02-05/03)
**Persona:** ML Expert
**Esforço:** 2-3 horas

### Comando gh cli

```bash
gh issue create \
  --title "[SPRINT-1] Label backtest_optimized_results JSON (ml_feature_engineer.py:447-448)" \
  --body "# Background

Arquivo TODO encontrado: \`src/application/ml_feature_engineer.py:447-448\`

\`\`\`python
# TODO: Implementar após ter backtest_optimized_results.json
logger.info('TODO: Implementar load_and_label com backtest results')
\`\`\`

## Problem

Grid search do modelo XGBoost depende de **labeled dataset** (win/loss por opportunity).

Artifact já existe: \`backtest_optimized_results.json\`

A função \`load_and_label()\` precisa:
1. Carregar \`backtest_optimized_results.json\`
2. Map cada \`window_id\` → label (\`1\` para win, \`0\` para loss)
3. Retornar dataset pronto para modelo

## Acceptance Criteria

- [x] Arquivo JSON carregado sem erros
- [x] 17.280 oportunidades processadas
- [x] Labels ~1.374 (windows com rewards)
- [x] Imbalance < 70% (30%+ positivos)
- [x] Performance < 500ms
- [x] Unit test: \`test_load_and_label_success\`
- [x] No NaN values

## Implementation Notes

- Use \`window_id\` como join key
- Considerar imbalance: pode treinar com class_weight auto
- Testar performance em 17.280 rows

## Impact

Desbloqueia:
- Grid search ML training (20+ horas de work)
- Sprint 2 execution (6/03 start)
- Go-Live v1.2 (10/04)" \
  --label "high-priority,sprint-1,blocker,bug,backend" \
  --assignee "@ml-expert"
```

### Ou manualmente no GitHub:
1. Ir em [Issues → New Issue](https://github.com/seu-user/operador-day-trade-win/issues/new)
2. Copiar título e descrição acima
3. Add labels: `high-priority,sprint-1,blocker`
4. Assign para ML Expert

---

## ISSUE-2: [SPRINT-1] OrdersExecutor implementation (3 TODOs)

**Tipo:** Feature task
**Prioridade:** 🔴 CRÍTICO (bloqueia Sprint 1)
**Sprint:** Sprint 1 (28/02-02/03)
**Persona:** Eng Sr
**Esforço:** 3-4 horas

### Comando gh cli

```bash
gh issue create \
  --title "[SPRINT-1] OrdersExecutor - Implement 3 TODOs (orders_executor.py)" \
  --body "# Background

Arquivo: \`src/application/orders_executor.py\`

Três TODOs encontrados (lines 133, 158, 188):

1. **Line 133:** Implementar \`execute_order()\` após Risk Validator pronto
2. **Line 158:** Implementar \`monitor_positions()\` após MT5Adapter pronto
3. **Line 188:** Implementar \`handle_stop_loss()\` loop de monitoramento

## Problem

OrdersExecutor é o coração da execução automática v1.2.
Atualmente schemático → precisa lógica completa.

## Acceptance Criteria

### execute_order()

- [x] Assinar risk validator output (Gate 1-3)
- [x] Se Gate 3 PASS → enviar order MT5
- [x] Se qualquer gate FAIL → log alert, skip
- [x] Retry logic: 3x com exponential backoff (1s, 2s, 4s)
- [x] Order tracking → RL_EPISODES table
- [x] Unit test: \`test_execute_order_success\`
- [x] Unit test: \`test_execute_order_gate_blocked\`

### monitor_positions()

- [x] Query MT5Adapter a cada 10s
- [x] Track P&L realizado + unrealizado
- [x] Detectar SL hit → log + trigger escalation
- [x] Desduplicar redundant positions
- [x] Unit test: \`test_monitor_positions\` (mock MT5)

### handle_stop_loss()

- [x] If P&L unrealizado < -3% → log ALERT
- [x] If P&L < -5% → slow mode (50% capital, 90% ML filter)
- [x] If P&L < -8% → HALT all orders
- [x] Unit test: circuit breaker scenarios
- [x] Escalation chain: Trader → CIO → CFO

## Implementation Notes

- Use queue.Queue para async processing
- Timeout 5s max (trading latency critical)
- Mock MT5Adapter para testes
- Logging a \`logs/orders_executor.log\`

## Impact

Desbloqueia:
- 50% do Sprint 1 (Eng Sr roadmap)
- E2E trading flow
- Risk framework validation
- Phase 6 integration" \
  --label "high-priority,sprint-1,feature,backend" \
  --assignee "@eng-sr"
```

---

## ISSUE-3: [SPRINT-2] Parallelize grid search (ml_classifier.py)

**Tipo:** Optimization task
**Prioridade:** 🟡 MÉDIO
**Sprint:** Sprint 2 (6/03-12/03)
**Persona:** ML Expert
**Esforço:** 1-2 horas

### Comando gh cli

```bash
gh issue create \
  --title "[SPRINT-2] Optimize XGBoost grid search - Parallel joblib (ml_classifier.py:452)" \
  --body "# Background

Arquivo TODO: \`src/application/ml_classifier.py:452\`

Grid search atual leva **30-40 minutos** com 8 configs.

## Problem

Configurações testáveis:
- 8 hyperparameter combos (n_estimators, max_depth, learning_rate)
- Cada combo: 5-fold cross-validation
- Total: 40 training rounds sequenciais

**Bottleneck:** CPU sequencial

## Solution: joblib.Parallel

Usar \`joblib.Parallel(n_jobs=-1)\` → utiliza todos os cores

Expected speedup: **3-5x** (30min → 7-10min)

## Acceptance Criteria

- [x] Use joblib.Parallel na GridSearchCV
- [x] n_jobs=-1 (auto cores)
- [x] fixed random_state (reproducibility)
- [x] Performance: < 10 minutos
- [x] Validate: F1 score same ±0.01
- [x] No data leakage in parallelization
- [x] Unit test: \`test_grid_search_parallel\`
- [x] Benchmark: before/after timing

## Implementation Notes

- XGBoost tree_method='approx' safe for parallel
- Set random_state=42 on all splits
- Log timing to \`logs/grid_search_bench.log\`

## Impact

- Sprint 2 gains 20-30 min/day (efficient iteration)
- Enables daily retraining cycles (v1.2)" \
  --label "medium-priority,sprint-2,optimization" \
  --assignee "@ml-expert"
```

---

## ISSUE-4: [POST-LAUNCH] P&L unrealized calculation

**Tipo:** Feature task
**Prioridade:** 🟡 MÉDIO
**Sprint:** Post Go-Live (~Sprint 2+)
**Persona:** Eng Sr
**Esforço:** 2-3 horas

### Comando gh cli

```bash
gh issue create \
  --title "[POST-LAUNCH] Add P&L unrealized calculation (portfolio.py:110)" \
  --body "# Background

Arquivo TODO: \`src/domain/entities/portfolio.py:110\`

\`\`\`python
# TODO: Adicionar calculo de lucro/prejuizo nao realizado
# quando dados de mercado estiverem disponiveis
\`\`\`

## Problem

Trader precisa ver P&L unrealizado em tempo real → avaliar se fecha posição.

Portfolio.py atualmente calcula apenas P&L **realizado** (closed trades).

## Solution

Integrar preços live do MT5 Adapter:
- Cada posição aberta tem entry_price
- MT5 fornece current_price a cada tick
- P&L unrealizado = (current_price - entry_price) × qty

## Acceptance Criteria

- [x] MT5Adapter.get_current_prices() chamado
- [x] Portfolio.unrealized_pnl property calculado
- [x] Dashboard refresh < 5 segundos
- [x] Precisão: ±1 pip (0.0001)
- [x] Cache prices (avoid excessive API calls)
- [x] Unit test: \`test_unrealized_pnl_calculation\`
- [x] Integration test: mock MT5 live prices

## Implementation Notes

- Cache com TTL 2s (reduz API load)
- Use MT5 bid price (mais conservador)
- Log anomalias (ex: negative qty)
- Dashboard: show realized + unrealized + total

## Timing

- Post Go-Live (não é crítico para Phase 1)
- Include em Sprint 2+ (medium priority)
- Trader pediu em UAT (06/03) → nice-to-have

## Impact

- Trader dashboard completeness +1 métrica
- Risk management improvement
- Support for dynamic exit decisions" \
  --label "medium-priority,post-launch,feature,backend" \
  --assignee "@eng-sr"
```

---

## 📋 CHECKLIST: Criar Issues (Hoje 23/02)

```bash
# Terminal Windows PowerShell:

# 1. Verificar gh cli instalado
which gh
gh --version

# 2. Autenticar (se necessário)
gh auth login

# 3. Criar Issue-1 (BLOCKER)
gh issue create \
  --title "[SPRINT-1] Label backtest_optimized_results JSON (ml_feature_engineer.py:447-448)" \
  --body "..." \
  --label "high-priority,sprint-1,blocker,bug,backend"

# 4. Criar Issue-2 (OrdersExecutor)
gh issue create \
  --title "[SPRINT-1] OrdersExecutor - Implement 3 TODOs (orders_executor.py)" \
  --body "..." \
  --label "high-priority,sprint-1,feature,backend"

# 5. Criar Issue-3 (Parallelization)
gh issue create \
  --title "[SPRINT-2] Optimize XGBoost grid search - Parallel joblib (ml_classifier.py:452)" \
  --body "..." \
  --label "medium-priority,sprint-2,optimization"

# 6. Criar Issue-4 (P&L)
gh issue create \
  --title "[POST-LAUNCH] Add P&L unrealized calculation (portfolio.py:110)" \
  --body "..." \
  --label "medium-priority,post-launch,feature,backend"

# 7. Verificar issues criadas
gh issue list --label "sprint-1,sprint-2"
```

---

## 🔗 Alternative: Criar via Web UI

Se preferir interface visual:

1. Go: https://github.com/operador-day-trade-win/issues
2. Click: **New Issue**
3. Copiar título e descrição do template acima
4. Add labels
5. Assign a pessoa
6. Click: **Submit new issue**

**Tempo estimado:** 5 minutos por issue (20 min total)

---

## 📊 Summary: Issues Criadas

| ID | Título | Sprint | Status | Esforço |
|----|--------|--------|--------|---------|
| #TBD-1 | Label backtest JSON | 1 | 🔴 BLOCKER | 2-3h |
| #TBD-2 | OrdersExecutor 3x | 1 | 🟠 HIGH | 3-4h |
| #TBD-3 | Grid search parallel | 2 | 🟡 MED | 1-2h |
| #TBD-4 | P&L unrealized | Post | 🟡 MED | 2-3h |

Total esforço: **8-12 horas** de desenvolvimento
Distribuição: Sprint 1 (5-7h) + Sprint 2 (1-2h) + Post-Launch (2-3h)

---

**Criado:** 23/02/2026 16:47 BRT
**Próxima ação:** Execute `gh issue create` commands acima HOJE
**Checklist:** [x] Sprint 1  [ ] Sprint 2  [ ] Post-Launch

