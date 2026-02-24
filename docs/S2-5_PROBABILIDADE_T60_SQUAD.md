<!-- pyml disable md013 -->
<!-- pyml disable md031 -->
<!-- pyml disable md032 -->
<!-- pyml disable md040 -->
<!-- pyml disable md022 -->

# 📊 S2-5: Plano de Execução Paralela — Squad Multidisciplinar

**Prioridade:** 🟠 ALTA (Prioridade 2 - SHOULD)
**Sprint:** Sprint 2 (PRÓXIMO — Estimado 27/02-01/03)
**Status:** 🟡 PRIORIZADO
**Última Atualização:** 2026-02-24T20:30:00Z

---

## 📋 RESUMO EXECUTIVO

**Objetivo:** Desenvolver modelo de previsão direcional T+60 (próxima 1h) para
WIN, adicionando confluência de curto prazo aos sinais SMC existentes.

**Entrega Esperada:** 03/03/2026 (5 dias de desenvolvimento paralelo)
**Impacto Esperado:** +2-3% em win rate, -10% em false positives
**Risco Mitigado:** Sinais SMC isolados sem contexto de curto prazo

---

## 🎯 SQUAD MULTIDISCIPLINAR ALOCADA

| # | Persona | Expertise | Alocação | Tarefas |
|---|---------|----------|----------|---------|
| **4** | ML Expert | Modelagem + Treino | **8h** | Feature Eng + Treino + Backtest |
| **3** | Eng Sr | Code + Integração | **4h** | Integração + file persistence |
| **6** | Arquiteto Sist. | Performance + Design | **2h** | Review design + latência |
| **11** | Data Engineer | Pipeline + QA | **2h** | Dataset validation |
| **12** | QA Automation | Testes + Coverage | **4h** | Test suite + CV validation |
| **8** | Head Docs & Stds | Documentação | **2h** | Docstrings + lint |
| **14** | Product Owner | AC Validation | **1h** | Sign-off de AC |
| **17** | Doc Advocate | Sync + tracking | **1h** | Atualizar SYNC_MANIFEST |

**Total:** 24h em paralelo (efetivamente ~8h de caminho crítico)

---

## 📅 TIMELINE PARALELA (5 dias)

### 🟢 Dia 1 (27/02 - 14h-23h): ANÁLISE + DESIGN

```
Paralelo:
├─ ML Expert (2h)
│  ├─ Analisar código bdi_detector.py (ver padrão existente)
│  ├─ Desenhar arquitetura feature engineering
│  └─ Listar features que faltam extrair
│
├─ Data Engineer (2h)
│  ├─ Validar dataset histórico M1 (últimos 3 meses)
│  ├─ Contar velas + gaps
│  └─ Preparar split 70/15/15
│
├─ Arquiteto (1h)
│  ├─ Revisar Design RF-1 (modelo arquitetura)
│  ├─ Estimular latência de inferência
│  └─ Validar persistência file path
│
├─ Head Docs (1h)
│  ├─ Preparar template docstring para Score_t60
│  └─ Validar convenções código
│
└─ Product Owner (30min)
   └─ Confirmar AC OK

===== RESULTADO ESPERADO: Design Document + AC confirmado =====
✅ Features especificadas (25 features)
✅ Label strategy definida
✅ Dataset validado
✅ Latência estimada <100ms
```

### 🟡 Dia 2 (28/02 - 08h-20h): FEATURE ENGINEERING + DATASET

```
Paralelo:
├─ ML Expert (3h)
│  ├─ Implementar score_t60_builder.py
│  ├─ Extrair 25 features de M1
│  ├─ Criar labels retroativos (RF-1 strategy)
│  └─ Validar distribuição labels (não desbalanceado)
│
├─ Data Engineer (1.5h)
│  ├─ Executar score_t60_builder.py
│  ├─ Auditar 5 amostras labels aleatórias
│  ├─ Verificar para dados faltantes
│  └─ Gerar estatísticas dataset
│
├─ QA (1.5h)
│  ├─ Escrever test_score_t60_dataset.py
│  ├─ Fixtures para amostra de dados
│  └─ Validar splits 70/15/15
│
└─ Head Docs (30min)
   └─ Documentar funcões ao vivo

===== RESULTADO ESPERADO: Dataset completo + testes estruturados =====
✅ ~40k velas com labels
✅ Nenhum dado faltante
✅ Testes dataset PASSING
```

### 🟠 Dia 3 (01/03 - 08h-20h): TREINAMENTO + GRID SEARCH

```
Paralelo:
├─ ML Expert (2.5h)
│  ├─ Implementar score_t60_train.py
│  ├─ Setup 5-fold CV (time-aware)
│  ├─ Correr 32x random XGBoost configs
│  └─ Selecionar top 10 + Bayesian Opt
│
├─ Eng Sr (1.5h)
│  ├─ Otimizar código de treino (multiprocessing)
│  ├─ Paralelizar grid search
│  └─ Monitorar tempo/memória
│
├─ Arquiteto (1h)
│  ├─ Review perfo dos 10 best models
│  ├─ Validar latência <100ms
│  └─ Selecionar melhor trade-off
│
├─ QA (1.5h)
│  ├─ Escrever test_score_t60_train.py
│  ├─ Validar random seeds (repeatability)
│  └─ Verificar CV sem leakage
│
└─ Head Docs (30min)
   └─ Documentar grid search results

===== RESULTADO ESPERADO: Modelo treinado + documentado =====
✅ Score_t60_v1.0.pkl (melhor modelo)
✅ Grid search log (32 configs)
✅ CV scores (F1 ≥ 0.62 esperado)
✅ Feature importance plot
```

### 🔵 Dia 4 (02/03 - 08h-20h): BACKTEST + VALIDAÇÃO

```
Paralelo:
├─ ML Expert (2h)
│  ├─ Implementar score_t60_backtest.py
│  ├─ Rodar backtest nos últimos 10 dias
│  ├─ Calcular taxa de acerto (target: 60%+)
│  └─ Gerar relatório de hits/misses
│
├─ Data Engineer (1h)
│  ├─ Validar velas de backtest (não overlap treino)
│  ├─ Auditar 10 predictions manualmente
│  └─ Verificar correlação com realidade
│
├─ QA (2h)
│  ├─ Escrever test_score_t60_backtest.py
│  ├─ Testar edge cases (gaps, holidays)
│  ├─ Validar JSON output format
│  └─ Coverage >98%
│
├─ Eng Sr (1h)
│  ├─ Implementar score_t60_inference.py
│  ├─ Setup file persistence (~/.operador_score_t60.json)
│  └─ Testes de leitura/escrita
│
└─ Head Docs (30min)
   └─ Finalizar docstrings

===== RESULTADO ESPERADO: Modelo validado + pronto para produção =====
✅ Taxa de acerto ≥ 60% em backtest
✅ Arquivo .json funcional
✅ Todos testes PASSING (8/8)
✅ Coverage >98%
```

### 🟢 Dia 5 (03/03 - 08h-18h): INTEGRAÇÃO E2E + DOCUMENTAÇÃO

```
Paralelo:
├─ Eng Sr (1h)
│  ├─ Integrar score_t60_inference.py no loop agente
│  ├─ Testar leitura score_t60.json no bat
│  └─ Validar fluxo confluência (SMC + T+60)
│
├─ Arquiteto (30min)
│  ├─ Code review final
│  ├─ Validar latência total <100ms
│  └─ Sign-off performance
│
├─ QA (30min)
│  ├─ Testes E2E integração
│  ├─ Regression tests
│  └─ Coverage final check
│
├─ Head Docs (1h)
│  ├─ Lint Markdown (pymarkdown scan)
│  ├─ Finalizar comentários
│  └─ Atualizar ARCHITECTURE.md
│
├─ Doc Advocate (30min)
│  ├─ Atualizar SYNC_MANIFEST.json
│  ├─ Registrar checksums
│  └─ Criar entrada em CHANGELOG.md
│
└─ Product Owner (30min)
   └─ Final sign-off AC (10/10 ✅)

===== RESULTADO ESPERADO: PRONTO PARA PRODUÇÃO =====
✅ Integração E2E funcionando
✅ Confluência SMC+T+60 operacional
✅ Documentação 100% sincronizada
✅ Lint passed
✅ Commit pronto para push
```

---

## 📊 DISTRIBUIÇÃO DE TAREFAS DETALHADAS

### 🔴 BLOCKERS (Caminho Crítico)

```
┌─→ ML Expert (Dia 2-3)
│   ├─ score_t60_builder.py (Dia 2)
│   ├─ score_t60_train.py (Dia 3)
│   ├─ score_t60_backtest.py (Dia 4)
│   └─ Modelo treinado + validado
│
└─→ Eng Sr (Dia 4-5)
    ├─ score_t60_inference.py (Dia 4)
    └─ Integração no agente (Dia 5)
```

### 🟡 PARALELOS (Podem rodar independente)

```
Data Engineer:
├─ Validar dataset (Dia 1-2)
└─ Auditar backtest (Dia 4)

QA Automation:
├─ Test fixtures (Dia 2)
├─ CV validation (Dia 3)
├─ Backtest tests (Dia 4)
└─ E2E tests (Dia 5)

Documentation:
├─ Docstring template (Dia 1)
├─ Inline comments (Dias 2-4)
├─ Lint + finalize (Dia 5)
└─ SYNC_MANIFEST update (Dia 5)
```

---

## ✅ CHECKLIST DE GATES

### GATE 1: Design Review (Fim Dia 1, 27/02 22h)

- [ ] Especificação com 10 AC definidos
- [ ] Dataset validado para ~40k velas
- [ ] Features listadas (25 features)
- [ ] Latência estimada <100ms
- [ ] Todos signs confirmaram AC

**Decision:** GO / NO-GO para implementação

### GATE 2: Dataset + Features (Fim Dia 2, 28/02 20h)

- [ ] score_t60_builder.py implementado
- [ ] 40k velas com labels criados
- [ ] 25 features extraídas + normalizadas
- [ ] Dataset tests PASSING (3/3)
- [ ] Nenhum dado faltante validado

**Decision:** GO / NO-GO para treino

### GATE 3: Modelo Treinado (Fim Dia 3, 01/03 20h)

- [ ] Score_t60_v1.0.pkl existe + salvo
- [ ] CV F1 ≥ 0.62 em val set
- [ ] Grid search 32 configs completado
- [ ] Feature importance extraído
- [ ] Train tests PASSING (3/3)

**Decision:** GO / NO-GO para backtest

### GATE 4: Backtest Validado (Fim Dia 4, 02/03 20h)

- [ ] Backtest em últimos 10 dias completado
- [ ] Taxa de acerto ≥ 60%
- [ ] score_t60_inference.py implementado
- [ ] File persistence funcional
- [ ] Backtest tests PASSING (3/3)

**Decision:** GO / NO-GO para integração E2E

### GATE 5: Integração E2E + Docs (Fim Dia 5, 03/03 18h)

- [ ] score_t60.json lido no loop agente
- [ ] Confluência SMC+T+60 testada
- [ ] Latência total <100ms medida
- [ ] Lint markdown passed
- [ ] SYNC_MANIFEST atualizado
- [ ] Todos 10 AC assinados

**Decision:** READY FOR PRODUCTION ✅

---

## 📝 TAREFAS POR PESSOA

### ML Expert (8h total)
**Responsável:** Modelagem + Treino + Validação

**Dia 2 (28/02):**
```python
- score_t60_builder.py (3h)
  ├─ Ler dataset histórico M1
  ├─ Extrair 25 features
  ├─ Criar labels T+60
  └─ Salvar parquet/CSV
```

**Dia 3 (01/03):**
```python
- score_t60_train.py (2.5h)
  ├─ Setup 5-fold CV
  ├─ Rodar 32 configs (paralelo)
  ├─ Grid search best 10
  └─ Salvar score_t60_v1.0.pkl
```

**Dia 4 (02/03):**
```python
- score_t60_backtest.py (2.5h)
  ├─ Backtest últimos 10 dias
  ├─ Calcular taxa acerto
  ├─ Gerar relatório
  └─ Salvar backtest_results.json
```

### Eng Sr (4h total)
**Responsável:** Código + Integração

**Dia 3 (01/03):**
```python
- Otimizar score_t60_train.py (1.5h)
  ├─ Paralelizar grid search
  ├─ Monitor memória
  └─ Log tempo/recursos
```

**Dia 4 (02/03):**
```python
- score_t60_inference.py (1.5h)
  ├─ Load modelo .pkl
  ├─ Infer em novo dado
  ├─ Write score_t60.json
  └─ Unit tests
```

**Dia 5 (03/03):**
```python
- Integração agente (1h)
  ├─ Ler score_t60.json no loop
  ├─ Confluência SMC+T+60
  ├─ Testar lógica
  └─ Validar fluxo
```

### Arquiteto de Sistemas (2h total)
**Responsável:** Performance + Design

- Dia 1 (27/02): Design review (1h)
- Dia 3 (01/03): Perf validation top 10 models (0.5h)
- Dia 5 (03/03): Code review + latência final (0.5h)

### Data Engineer (2h total)
**Responsável:** Dataset Validation

- Dia 1 (27/02): Validar histórico (1h)
- Dia 2 (28/02): Auditar builders output (0.5h)
- Dia 4 (02/03): Verificar backtest data (0.5h)

### QA Automation (4h total)
**Responsável:** Testes + Coverage

- Dia 2 (28/02): test_score_t60_dataset.py (1h)
- Dia 3 (01/03): test_score_t60_train.py (1h)
- Dia 4 (02/03): test_score_t60_backtest.py (1h)
- Dia 5 (03/03): test_score_t60_e2e.py (1h)

### Head Docs & Standards (2h total)
**Responsável:** Documentação + Lint

- Dia 1 (27/02): Docstring template (0.5h)
- Dias 2-4: Inline comments (1h paralelo)
- Dia 5 (03/03): Lint + finalize (0.5h)

### Product Owner (1h total)
- Dia 1 (27/02): Confirm AC (0.5h)
- Dia 5 (03/03): Final sign-off (0.5h)

### Doc Advocate (1h total)
- Dia 5 (03/03): SYNC_MANIFEST + CHANGELOG (1h)

---

## 📦 DELIVERABLES

### Arquivos Python (.py)
```
scripts/
├─ score_t60_builder.py (~80 LOC)
├─ score_t60_train.py (~120 LOC)
├─ score_t60_backtest.py (~100 LOC)
└─ score_t60_inference.py (~40 LOC)

Total: ~340 LOC (clean, well-commented)
```

### Arquivos de Testes
```
tests/
├─ test_score_t60_dataset.py (~60 LOC)
├─ test_score_t60_train.py (~80 LOC)
├─ test_score_t60_backtest.py (~70 LOC)
├─ test_score_t60_e2e.py (~50 LOC)
└─ conftest.py (fixtures)

Total: ~300 LOC (coverage >98%)
```

### Modelos
```
models/
├─ score_t60_v1.0.pkl (~2MB)
└─ score_t60_features_meta.json (~1KB)
```

### Documentação
```
docs/
├─ S2-5_PROBABILIDADE_T60_ESPECIFICACAO.md (atual)
├─ S2-5_PROBABILIDADE_T60_SQUAD.md ← Este arquivo
├─ ARCHITECTURE.md ← Atualizar seção Analysis Layer
├─ SYNC_MANIFEST.json ← Nova entrada
└─ CHANGELOG.md ← Nova seção
```

---

## 🧪 TESTE MANUAL FINAL

Antes de fazer commit:

```bash
# 1. Rodar pytest suite
pytest tests/test_score_t60*.py -v --cov=scripts/score_t60*.py

# 2. Simular integração no .bat
python scripts/score_t60_inference.py

# 3. Verificar arquivo JSON
cat ~/.operador_score_t60.json

# 4. Lint markdown
pymarkdown scan docs/S2-5_*.md

# 5. Lint Python
pylint scripts/score_t60*.py
black scripts/score_t60*.py --check

# 6. Rodear INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat (teste seco)
./INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat --dry-run
```

---

## 📋 TEMPLATE DE COMMIT

```bash
git add scripts/score_t60* tests/test_score_t60* models/* docs/S2-5*

git commit -m "feat: S2-5 Probabilidade T+60 - Previsão direcional 1h

- Implementar score_t60 com XGBoost (F1=0.63+)
- 25 features M1 + labels retroativos T+60
- Backtest validado: 62% acertos (últimos 10d)
- Integração no operador com confluência SMC+T+60
- 4 test suites (dataset, train, backtest, e2e)
- Coverage >98% | Lint passed | Docs sincronizados

Closes #S2-5"

git push origin main
```

---

## 📊 MÉTRICAS DE SUCESSO

| Métrica | Target | Atual | Status |
|---------|--------|-------|--------|
| CV F1-score | ≥0.62 | — | ⏳ TBD |
| Backtest Acertos | ≥60% | — | ⏳ TBD |
| Latência Inferência | <100ms | — | ⏳ TBD |
| Test Coverage | >98% | — | ⏳ TBD |
| AC Cumprimento | 10/10 | — | ⏳ TBD |

---

## 🔗 DOCUMENTOS RELACIONADOS

- [S2-5_PROBABILIDADE_T60_ESPECIFICACAO.md](S2-5_PROBABILIDADE_T60_ESPECIFICACAO.md)
- [ARCHITECTURE.md](ARCHITECTURE.md) → Analysis Layer
- [STATUS_ENTREGAS.md](STATUS_ENTREGAS.md)
- [BOARD_MULTIDISCIPLINAR.json](BOARD_MULTIDISCIPLINAR.json)

---

> **Protocolo:** [SYNC] Documento rastreado em SYNC_MANIFEST.json
> **Revisão:** 1.0.0 | **Data:** 2026-02-24 | **Status:** 🟡 PRIORIZADO
