<!-- pyml disable md013 -->
<!-- pyml disable md031 -->
<!-- pyml disable md032 -->
<!-- pyml disable md040 -->

# 🚀 S2-5: Probabilidade T+60 — Plano Executivo da Squad

**Status:** 🟡 EM ANDAMENTO (Kickoff 27/02)
**Prioridade:** 🟠 ALTA (Prioridade 2 - SHOULD)
**Última Atualização:** 2026-02-24T23:00:00Z
**Sprint:** Sprint 2 (27/02 - 03/03)
**Documento de Governança:** [BOARD_MULTIDISCIPLINAR.json](BOARD_MULTIDISCIPLINAR.json)

---

## 📋 RESUMO EXECUTIVO (1 min read)

**Objetivo:** Implementar modelo de previsão direcional T+60 (próxima 1h) para
WIN, integrando XGBoost com 25 features M1 para adicionar confluência de curto
prazo aos sinais SMC existentes.

**Entrega Expected:** 03/03/2026 (5 dias de sprint paralela)
**Impacto:** +2-3% em win rate, -10% em false positives via confluência SMC+T+60
**Investment:** 24h equipe alocada (Squad 8 pessoas | Caminho crítico ~8h)

---

## 🎯 ACCEPTANCE CRITERIA (10 AC Obrigatórios)

Todos os 10 critérios devem estar ✅ para GATE 5 (Integração E2E):

| # | AC | Métrica | Target | Owner | Prioridade |
|---|----|---------| -------|-------|-----------|
| **1** | Modelo treinado + salvo | F1-score CV | ≥0.62 | ML Expert | 🔴 BLOCKER |
| **2** | Backtest validado | Taxa acertos | ≥60% | ML Expert | 🔴 BLOCKER |
| **3** | Latência inferência | P95 ms | <100ms | Arq. Sist. | 🔴 BLOCKER |
| **4** | File persistence OK | score_t60.json | Estrutura validada | Eng Sr | 🟡 CRÍTICO |
| **5** | Confluência SMC+T+60 | Logica operador | Verificada | Eng Sr | 🟡 CRÍTICO |
| **6** | Test coverage > 98% | Testes unitários | 4 suites PASS | QA Auto. | 🟡 CRÍTICO |
| **7** | Documentação 100% | Docstrings PT | 100% coverage | Head Docs | 🟢 ALTA |
| **8** | Lint Markdown PASS | Pymarkdown scan | Zero violations | Doc Advocate | 🟢 ALTA |
| **9** | SYNC_MANIFEST OK | Rastreamento | Entrada criada | Doc Advocate | 🟢 MÉDIA |
| **10** | AC Sign-off PO | Aprovação final | Product Owner | 🟢 MÉDIA |

---

## 👥 SQUAD MULTIDISCIPLINAR (8 pessoas, 24h total)

### Líderes de Domínio

| # | Personas | Especialidade | Horas | Caminho Crítico | Responsabilidades |
|---|----------|-------------|-------|----------------|------------------|
| **4** | ML Expert | Modelagem ML | 8h | ✅ SIM | Feature eng, treino, backtest |
| **3** | Eng Sr | Code integração | 4h | ✅ SIM | score_t60_inference + agente |
| **6** | Arq. Sist. | Performance | 2h | ⚠️ REVIEW | Design + latência validation |

### Suporte Especializado

| # | Personas | Especialidade | Horas | Papel | Responsabilidades |
|---|----------|-------------|-------|------|------------------|
| **11** | Data Engineer | QA dados | 2h | Validação | Dataset + backtest audit |
| **12** | QA Automation | Testes | 4h | Coverage | 4 test suites + E2E |
| **8** | Head Docs | Documentação | 2h | Padrões | Docstrings + lint |
| **14** | Product Owner | AC | 1h | Validação | Sign-off AC |
| **17** | Doc Advocate | Sync | 1h | Rastreamento | SYNC_MANIFEST + CHANGELOG |

**Total Alocação:** 24h paralelas = ~8h caminho crítico

---

## 📅 TIMELINE DETALHADA (5 dias)

### 🟢 DIA 1: 27/02 (14h - 23h) — ANÁLISE + DESIGN

```markdown
Atividades em PARALELO:

● ML Expert (2h): Analisar specs, desenhar feature engineering
● Data Engineer (1.5h): Validar histórico M1 (últimos 3 meses)
● Arq. Sist. (1h): Review design + latência estimada
● Head Docs (0.5h): Template docstring T60
● PO (0.5h): Confirmar AC

GATES DIÁRIOS:
  ✓ Especificação com 10 AC definidos
  ✓ Dataset validado ~40k velas
  ✓ Features listadas (25 features)
  ✓ Latência estimada <100ms

DELIVERABLES:
  - Design document (specs confirmadas)
  - AC list (10/10 assinados)
```

### 🟡 DIA 2: 28/02 (08h - 20h) — FEATURE ENGINEERING + DATASET

```markdown
Atividades em PARALELO:

● ML Expert (3h):
  - Implementar score_t60_builder.py
  - Extrair 25 features de M1
  - Criar labels retroativos (T+60 strategy)
  - Validar distribuição labels

● Data Engineer (1.5h):
  - Auditar 5 amostras labels aleatórias
  - Verificar dados faltantes
  - Gerar estatísticas dataset

● QA (1.5h):
  - Escrever test_score_t60_dataset.py
  - Fixtures para amostra dados
  - Validar splits 70/15/15

GATES DIÁRIOS (GATE 2 — Fim dia):
  ✓ score_t60_builder.py implementado
  ✓ 40k velas com labels criados
  ✓ 25 features extraídas + normalizadas
  ✓ Dataset tests PASSING (3/3)

DELIVERABLES:
  - score_t60_builder.py (80 LOC)
  - test_score_t60_dataset.py (60 LOC)
  - Dataset arquivo (CSV/parquet)
```

### 🟠 DIA 3: 01/03 (08h - 20h) — TREINAMENTO + GRID SEARCH

```markdown
Atividades em PARALELO:

● ML Expert (2.5h):
  - Implementar score_t60_train.py
  - Setup 5-fold CV (time-aware)
  - Correr 32 configs random XGBoost
  - Selecionar top 10 + Bayesian Opt

● Eng Sr (1.5h):
  - Otimizar código treino (multiprocessing)
  - Paralelizar grid search
  - Monitor tempo/memória

● Arq. Sist. (1h):
  - Review performance top 10 models
  - Validar latência <100ms
  - Selecionar melhor trade-off

● QA (1.5h):
  - Escrever test_score_t60_train.py
  - Validar random seeds (repeatability)
  - Verificar CV sem leakage

GATES DIÁRIOS (GATE 3 — Fim dia):
  ✓ score_t60_v1.0.pkl salvo
  ✓ CV F1 ≥ 0.62 em val set
  ✓ Grid search 32 configs completado
  ✓ Feature importance extraído
  ✓ Train tests PASSING (3/3)

DELIVERABLES:
  - score_t60_train.py (120 LOC)
  - test_score_t60_train.py (80 LOC)
  - Modelo score_t60_v1.0.pkl (~2MB)
  - Grid search results log
```

### 🔵 DIA 4: 02/03 (08h - 20h) — BACKTEST + VALIDAÇÃO

```markdown
Atividades em PARALELO:

● ML Expert (2h):
  - Implementar score_t60_backtest.py
  - Rodar backtest últimos 10 dias
  - Calcular taxa de acertos
  - Gerar relatório

● Eng Sr (1.5h):
  - Implementar score_t60_inference.py
  - Load modelo + infer dados novo
  - Write score_t60.json format
  - Unit tests

● Data Engineer (0.5h):
  - Auditar backtest data
  - Validar datas histórico

● QA (1.5h):
  - Escrever test_score_t60_backtest.py
  - Validar formato JSON output
  - Coverage tests

GATES DIÁRIOS (GATE 4 — Fim dia):
  ✓ Backtest 10 dias completado
  ✓ Taxa de acerto ≥ 60%
  ✓ score_t60_inference.py implementado
  ✓ File persistence funcional
  ✓ Backtest tests PASSING (3/3)

DELIVERABLES:
  - score_t60_backtest.py (100 LOC)
  - score_t60_inference.py (40 LOC)
  - test_score_t60_backtest.py (70 LOC)
  - backtest_results.json
  - score_t60.json (example)
```

### 🟣 DIA 5: 03/03 (08h - 18h) — INTEGRAÇÃO E2E + FINALIZACAO

```markdown
Atividades em PARALELO:

● Eng Sr (1h):
  - Integração score_t60.json no agente
  - Logica confluência SMC+T+60
  - Testar fluxo completo

● QA (1h):
  - Escrever test_score_t60_e2e.py
  - E2E flow validation
  - Latência medida

● Head Docs (0.5h):
  - Lint Markdown (pymarkdown scan)
  - Finalizar comentários
  - Atualizar ARCHITECTURE.md

● Doc Advocate (0.5h):
  - Atualizar SYNC_MANIFEST.json
  - Registrar checksums
  - Criar entrada CHANGELOG.md

● Arq. Sist. (0.5h):
  - Code review + latência final
  - Design sign-off

● PO (0.5h):
  - Final sign-off AC (10/10 ✅)

GATES DIÁRIOS (GATE 5 — Fim 18h):
  ✓ Integração E2E funcionando
  ✓ Confluência SMC+T+60 operacional
  ✓ Latência total <100ms medida
  ✓ Lint markdown PASSED
  ✓ SYNC_MANIFEST atualizado
  ✓ Todos 10 AC assinados

DELIVERABLES:
  - test_score_t60_e2e.py (50 LOC)
  - Agente atualizado com confluência
  - Documentação 100% sincronizada
  - CHANGELOG entry
  - Commit pronto para push
```

---

## 📊 ESTRUTURA DE ARQUIVOS

### Python Scripts (340 LOC + Testes 300 LOC)

```
scripts/
├─ score_t60_builder.py (447 LOC total, EXISTENTE) ✅
├─ score_t60_train.py (553 LOC total, EXISTENTE) ✅
├─ score_t60_backtest.py (349 LOC total, EXISTENTE) ✅
└─ score_t60_inference.py (392 LOC total, EXISTENTE) ✅

Total: 1.741 LOC (existente, pronto para completação)
```

### Test Suite (300+ LOC)

```
tests/
├─ test_score_t60_dataset.py (60 LOC, NOVO)
├─ test_score_t60_train.py (80 LOC, NOVO)
├─ test_score_t60_backtest.py (70 LOC, NOVO)
├─ test_score_t60_e2e.py (50 LOC, NOVO)
└─ conftest.py (fixtures compartilhadas)

Total: 300+ LOC (coverage >98%)
```

### Models + Artifacts

```
models/
├─ score_t60_v1.0.pkl (~2MB, GERADO DIA 3)
├─ score_t60_features_meta.json (~1KB)
├─ t60_dataset.parquet (GERADO DIA 2)
└─ grid_search_log.json (GERADO DIA 3)
```

### Documentação (EXISTENTE + ATUALIZADA)

```
docs/
├─ S2-5_PROBABILIDADE_T60_ESPECIFICACAO.md (267 LOC) ✅
├─ S2-5_PROBABILIDADE_T60_SQUAD.md (529 LOC) ✅
├─ S2-5_EQUIPE_EXECUTIVO_PLANO.md ← ESTE DOCUMENTO
├─ ARCHITECTURE.md (atualizar Analysis Layer)
├─ SYNC_MANIFEST.json (nova entrada S2-5)
└─ CHANGELOG.md (nova seção)
```

---

## 🧪 TESTES UNITÁRIOS OBRIGATÓRIOS

### Coverage Target: >98%

```python
# test_score_t60_dataset.py (3 testes)
● test_dataset_loading_completo
● test_label_validity_sem_dados_faltantes
● test_features_extraction_25_features

# test_score_t60_train.py (3 testes)
● test_cv_5fold_sem_leakage
● test_grid_search_32_configs_parallel
● test_model_pickle_persistence

# test_score_t60_backtest.py (3 testes)
● test_backtest_ultimos_10_dias
● test_accuracy_taxa_acertos_60_percent
● test_json_output_format_compliance

# test_score_t60_e2e.py (1 teste)
● test_agente_integration_score_t60_confluencia_smc
```

**Execução:**

```bash
pytest tests/test_score_t60*.py -v \
  --cov=scripts/score_t60* \
  --cov-report=html \
  --cov-report=term

# Expected: 10 PASSED | Coverage: >98%
```

---

## ✅ CHECKLIST DE GATES (5 gates + Final)

### GATE 1: Design Review (27/02 22h)

```
☐ Especificação com 10 AC definidos
☐ Dataset validado para ~40k velas
☐ Features listadas (25 features)
☐ Latência estimada <100ms
☐ Todos signs confirmaram AC
☐ Decision: GO / NO-GO ← Assinatura PO + ML lead
```

### GATE 2: Dataset + Features (28/02 20h)

```
☐ score_t60_builder.py implementado
☐ 40k velas com labels criados
☐ 25 features extraídas + normalizadas
☐ Dataset tests PASSING (3/3)
☐ Nenhum dado faltante validado
☐ Decision: GO / NO-GO ← Assinatura Data Eng + ML lead
```

### GATE 3: Modelo Treinado (01/03 20h)

```
☐ Score_t60_v1.0.pkl existe + salvo
☐ CV F1 ≥ 0.62 em val set
☐ Grid search 32 configs completado
☐ Feature importance extraído
☐ Train tests PASSING (3/3)
☐ Decision: GO / NO-GO ← Assinatura ML lead + Arq. Sist.
```

### GATE 4: Backtest Validado (02/03 20h)

```
☐ Backtest em últimos 10 dias completado
☐ Taxa de acerto ≥ 60%
☐ score_t60_inference.py implementado
☐ File persistence funcional
☐ Backtest tests PASSING (3/3)
☐ Decision: GO / NO-GO ← Assinatura ML lead + Eng Sr
```

### GATE 5: Integração E2E + Docs (03/03 18h)

```
☐ score_t60.json lido no loop agente
☐ Confluência SMC+T+60 testada
☐ Latência total <100ms medida
☐ Lint markdown PASSED
☐ SYNC_MANIFEST atualizado
☐ Todos 10 AC assinados
☐ Decision: READY FOR PRODUCTION ← Assinatura PO
```

---

## 📋 COMMIT FINAL (DIA 5, APÓS GATE 5)

```bash
git add scripts/score_t60* \
        tests/test_score_t60* \
        models/score_t60* \
        docs/S2-5*

git commit -m "feat: S2-5 Probabilidade T+60 - Previsão direcional 1h

- Implementar score_t60 com XGBoost (F1≥0.63)
- 25 features M1 + labels retroativos T+60
- Backtest validado: ≥60% acertos (últimos 10d)
- Integração no operador com confluência SMC+T+60
- 4 test suites (dataset, train, backtest, e2e)
- Coverage >98% | Lint ✅ | Docs sincronizados

Acceptance Criteria: 10/10 ✅
Test Gates: 5/5 PASSED ✅
Ready for Production: YES ✅

Closes #S2-5"

git push origin main
```

---

## 🔗 DOCUMENTOS RASTREADOS

- [Status de Entregas](STATUS_ENTREGAS.md) — Marcado como "EM ANDAMENTO"
- [Roadmap](ROADMAP.md) — Sprint 2 (27/02-03/03) com timeline
- [Board Multidisciplinar](BOARD_MULTIDISCIPLINAR.json) — Squad S2-5 registrada
- [Especificação Técnica](S2-5_PROBABILIDADE_T60_ESPECIFICACAO.md) — RF-1 a RF-4
- [Plano Squad Paralela](S2-5_PROBABILIDADE_T60_SQUAD.md) — Cronograma detalhado
- [Arquitetura](ARCHITECTURE.md) — Analysis Layer (será atualizado)
- [Sync Manifest](docs/SYNC_MANIFEST.json) — Será criado entry nova

---

## 📊 MÉTRICAS DE SUCESSO

| Métrica | Target | Status | Owner |
|---------|--------|--------|-------|
| CV F1-score | ≥0.62 | ⏳ TBD | ML Expert |
| Backtest Acertos | ≥60% | ⏳ TBD | ML Expert |
| Latência Inferência | <100ms | ⏳ TBD | Arq. Sist. |
| Test Coverage | >98% | ⏳ TBD | QA Automation |
| AC Cumprimento | 10/10 | ⏳ TBD | Product Owner |
| Lint Markdown | PASS | ⏳ TBD | Doc Advocate |
| SYNC OK | ✅ | ⏳ TBD | Doc Advocate |

---

## 🚀 PRÓXIMOS PASSOS

### Imediato (26/02 - Antes do Kickoff)

- [ ] Confirmar alocação de 8 personas (BOARD validado)
- [ ] Revisar specs com ML Expert + Eng Sr
- [ ] Alocar ambientes/máquinas para grid search paralelo
- [ ] Preparar datasets históricos (últimos 3 meses M1)

### Dia 1 (27/02 14h)

- [ ] Kickoff Squad com todos 8 membros
- [ ] Revisar este documento + AC
- [ ] Setup ambientes de desenvolvimento
- [ ] Começar análise de features (ML Expert)

### Dias 2-5

- [ ] Executar conforme timeline detalhada acima
- [ ] Gates diários às 20h (sinal para próximo dia)
- [ ] Daily standups 15:00 BRT

---

> **Protocolo:** [SYNC] Documento rastreado em SYNC_MANIFEST.json
> **Versão:** 1.0.0 | **Data:** 2026-02-24 | **Status:** 🟡 PRIORIZADO
