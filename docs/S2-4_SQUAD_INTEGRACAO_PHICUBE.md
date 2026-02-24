# 📋 S2-4: Integração Phicube (Mimas) — Squad Multidisciplinar

**ID da Tarefa**: S2-4  
**Título**: Integração Phicube (Mimas)  
**Prioridade**: 🟢 **PRIORIZADO SPRINT 2**  
**Status**: 🟡 **EM ANDAMENTO** (iniciado 24/02/2026)  
**Owner Principal**: [ML Expert](BOARD_MULTIDISCIPLINAR.json)  

---

## 🎯 Objetivo Executivo

Ativar o cálculo de alinhamento de leque das Sequências de Fibonacci (Mimas) — **8, 17, 34,
72, 144, 305, 610** — e integrá-lo ao `micro_score`. O código de cálculo já existe, mas **não
é contabilizado na decisão** de execução. Resultado esperado: **aumento de confiança no sinal
através de confluência técnica geométrica**.

---

## 📊 Squad Multidisciplinar (11 membros)

| ID | Nome | Rol | Sprint | Responsabilidade |
|:---|:---|:---|:---:|:---|
| **2** | Coordenadora de Governança | Gov | S2-4 | Rastreamento de status, sincronização docs, gates |
| **3** | Eng Sr | Tech | S2-4 | Integração no `micro_score`, refatoração do motor de decisão |
| **4** | ML Expert | ML | S2-4 | Validação do cálculo Fibonacci, otimização de pesos |
| **6** | Arquiteto de Sistemas | Arch | S2-4 | Desenho da camada de análise, padrões de integração |
| **7** | Infra DevOps | DevOps | S2-4 | CI/CD, testes automáticos, deployment |
| **8** | Head de Documentação & Standards | Doc | S2-4 | Documentação técnica, padrões de código |
| **9** | Operações | Ops | S2-4 | Validação em ambiente de staging/produção |
| **11** | Data Engineer | Data | S2-4 | Pipeline de dados para Fibonacci, backtesting |
| **12** | QA Automation | QA | S2-4 | Testes unitários (98%+ cobertura), integração E2E |
| **13** | Trader Líder | Trading | S2-4 | Validação de sinais, confirmação empírica |
| **14** | Product Owner | PO | S2-4 | Aceitação de critérios, priorização |

---

## 📌 Contextualização Técnica

### O que existe hoje?

O código de cálculo de Fibonacci (Phi Cube) **já está implementado** em algum lugar do projeto.
As Mimas são sequências de suporte/resistance baseadas em proporções áureas:

```
Fibonacci Sequence: 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610...
Phi Cube (Mimas): 8, 17, 34, 72, 144, 305, 610
```

Essas proporções são usadas em análise técnica para identificar **zonas de confluência
geométrica** onde o preço tende a reagir (suporte/resistance).

### O que falta?

**Integração ao `micro_score`**: O cálculo existe, mas não contribui para a decisão final de
execução de ordem. Precisa ser:

1. ✅ Normalizado (0-1)
2. ✅ Ponderado em conjunto com outros sinais
3. ✅ Testado contra dados históricos (backtest Fibonacci)
4. ✅ Documentado e rastreável

### Impacto Esperado

- **Aumento de Confiança**: Confluência técnica adicional
- **Redução de Falsos Positivos**: Filtro geométrico
- **Aumento de Taxa de Acerto**: Espera-se +3-5% de melhoria em win rate

---

## 🔄 Subtasks Paralelas (8 Tasks)

### BLOCKER TASKS (Dependências Críticas - Execute em Série)

#### **Task-001: DATA_ENGINEER** — Descobrir, Extrair e Documentar Fibonacci
- **Owner**: Data Engineer (#11)
- **Duração Estimada**: 4h
- **AC (Acceptance Criteria)**:
  1. Arquivo(s) contendo lógica Fibonacci identificado(s)
  2. Sequências validadas (8, 17, 34, 72, 144, 305, 610)
  3. Função `calcular_mimas(price, timeframe)` documentada
  4. Dataset histórico com Fibonacci processado (1.000+ candles)
  5. `test_fibonacci_calculation.py` com 5+ cenários

**Artefatos Esperados**:
  - `src/analysis/fibonacci_calculator.py` (referência ou novo)
  - `tests/unit/test_fibonacci.py`
  - `docs/S2-4_FIBONACCI_SPEC.md`

#### **Task-002: ARCH** — Desenhar Integração no `micro_score`
- **Owner**: Arquiteto de Sistemas (#6)
- **Depende de**: Task-001
- **Duração Estimada**: 3h
- **AC**:
  1. Diagrama de fluxo: Fibonacci → Normalizar → Peso → micro_score
  2. Interface proposta: `score_fibonacci: ScoreFibonacci`
  3. Padrão de integração definido (Chain of Responsibility vs Strategy)
  4. Documento de design: `S2-4_DESIGN_INTEGRACAO.md`
  5. Revisão técnica aprovada (Eng Sr + ML Expert)

**Artefatos Esperados**:
  - `docs/S2-4_DESIGN_INTEGRACAO.md` (250+ linhas)
  - Diagrama UML/Mermaid do fluxo
  - Proposta de refatoração

---

### IMPLEMENTATION TASKS (Execução em Paralelo)

#### **Task-003: ENG_SR** — Integrar Fibonacci ao `micro_score`
- **Owner**: Eng Sr (#3)
- **Depende de**: Task-001, Task-002
- **Duração Estimada**: 6h
- **AC**:
  1. `MicroScore.score_fibonacci` adicionado
  2. Normalização (0-1) implementada
  3. Peso do Fibonacci configurável (default: 0.15)
  4. Código 100% type-hinted (mypy --strict OK)
  5. Clean Code (sem comentários obvios, nomes semânticos)
  6. Integração completa no `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`

**Artefatos Esperados**:
  - Modificação em `src/application/micro_score.py`
  - `src/models/score_fibonacci.py` (novo componente)
  - Integração no `agente_autonomo/` (se aplicável)

#### **Task-004: ML_EXPERT** — Validar e Otimizar Pesos Fibonacci
- **Owner**: ML Expert (#4)
- **Depende de**: Task-001
- **Duração Estimada**: 5h
- **AC**:
  1. Backtest Fibonacci isolado (min 50 trades)
  2. Matriz de correlação: Fibonacci vs SMC vs ATR vs RSI
  3. Otimização de peso via grid search (4-6 configurações)
  4. Win rate esperado: baseline +3-5%
  5. `backtest_fibonacci_results.json` gerado
  6. Relatório: `S2-4_ML_VALIDATION.md`

**Artefatos Esperados**:
  - `scripts/backtest_fibonacci.py`
  - `backtest_fibonacci_results.json`
  - `docs/S2-4_ML_VALIDATION.md`

#### **Task-005: QA_AUTOMATION** — Testes Unitários (98% cobertura)
- **Owner**: QA Lead (#12)
- **Duração Estimada**: 6h
- **AC**:
  1. `test_fibonacci_calculation.py` — 8 casos (CASE-THEN-WHEN)
  2. `test_micro_score_fibonacci_integration.py` — 6 casos
  3. `test_fibonacci_normalization.py` — 5 casos
  4. Coverage: 98%+ de `score_fibonacci.py`
  5. Todos os testes PASSING (verbose output em Português)
  6. Mocks de MT5 criados

**Artefatos Esperados**:
  - `tests/unit/test_fibonacci_*.py` (3 arquivos)
  - Coverage report (HTML)

#### **Task-006: DATA_ENGINEER** — Backtesting & Validação de Pesos
- **Owner**: Data Engineer (#11)
- **Depende de**: Task-003, Task-004
- **Duração Estimada**: 4h
- **AC**:
  1. Histórico de 6 meses processado (WIN, WDOTEST, WINFUT)
  2. Fibonacci ativado em 4 cenários de peso (0.1, 0.15, 0.2, 0.25)
  3. Comparativo: com vs sem Fibonacci
  4. TTM (Time to Confidence) calculado
  5. Recomendação de peso final (com IC 95%)

**Artefatos Esperados**:
  - `scripts/backtest_fibonacci_scenarios.py`
  - `backtest_scenarios_results.json`
  - Dataframe comparativo (CSV)

#### **Task-007: OPS** — Staging & Validação de Ambiente
- **Owner**: Operações (#9)
- **Depende de**: Task-003, Task-005
- **Duração Estimada**: 3h
- **AC**:
  1. Deployment em staging concluído
  2. MONITOR_OPERADOR.bat executa sem erros
  3. Health checks passam (connection, latency P95 <500ms)
  4. Fibonacci score visível em logs (`FIBONACCI_SCORE=0.87`)
  5. Relatório de readiness: `S2-4_STAGING_VALIDATION.md`

**Artefatos Esperados**:
  - Confirmação de deploy em staging
  - Health check log
  - Validação em MONITOR_LOGS.bat

#### **Task-008: TRADER_LÍDER** — Validação Empírica de Sinais
- **Owner**: Trader Líder (#13)
- **Depende de**: Task-007
- **Duração Estimada**: 2h (observação em staging)
- **AC**:
  1. 10+ sinais documentados (entrada/saída com Fibonacci score)
  2. Confirmação visual: "Fibonacci alinhado com visuais de gráfico"
  3. Feedback qualitativo: "Aumentou confiança?" (Sim/Não/Parcial)
  4. Recomendação: Go/No-Go para produção
  5. Sign-off: `S2-4_TRADER_VALIDATION.md`

**Artefatos Esperados**:
  - Logs de sinais com Fibonacci score
  - Feedback qualitativo documentado

---

### DOCUMENTATION & SYNC TASKS (Paralelo com Implementation)

#### **Task-009: DOC_ADVOCATE** — Documentação Técnica & Padrões
- **Owner**: Head de Documentação (#8)
- **Duração Estimada**: 4h
- **AC**:
  1. `docs/S2-4_GUIA_IMPLEMENTACAO.md` (500+ linhas)
  2. Docstrings 100% em Python
  3. Exemplos de uso (copy-paste ready)
  4. Padrão de erro tratado (invalid price, timezone issues)
  5. Lint: pymarkdown OK, mypy --strict OK

#### **Task-010: GOV_COORD** — Rastreamento & Sincronização
- **Owner**: Coordenadora de Governança (#2)
- **Duração Estimada**: 2h (contínuo)
- **AC**:
  1. STATUS_ENTREGAS.md atualizado (Status: EM ANDAMENTO)
  2. ROADMAP.md referencia S2-4 com progresso
  3. SYNC_MANIFEST.json atualizado
  4. Commits rastreados e sincronizados
  5. Daily standup: Progresso comunicado ao time

---

## 🔗 Dependências & Timeline

```
Task-001 (Data Engineer) [4h]
  │
  ├─→ Task-002 (Arch) [3h] ─→ Task-003 (ENG_SR) [6h] ┐
  │                           │                       │
  │                           └─→ Task-005 (QA) [6h] │
  │                                                   ├─→ Task-007 (OPS) [3h] ─→ Task-008 (Trader) [2h]
  │                           │                       │
  └─→ Task-004 (ML Expert) [5h] ─→ Task-006 (Data) [4h] ┘
      (paralelo com Eng Sr)

Task-009 (Doc) [4h] ─┐
Task-010 (Gov) [2h] ─┼─→ EXECUTION + SYNC (contínuo)
```

**Timeline Total Estimado**: 8-10h (caminho crítico)  
**Data Target**: 26-27/02/2026

---

## ✅ Critérios de Conclusão

- [ ] 8 subtasks com AC 100% atendidos
- [ ] 98%+ cobertura de testes (unittest)
- [ ] Fibonacci integrado e normalizado no micro_score
- [ ] Backtest validado (+3-5% win rate esperado)
- [ ] Staging validado + Trader sign-off
- [ ] Documentação completa (Português, lint OK)
- [ ] Commit & Push com mensagem clara
- [ ] INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat testado (funcional)
- [ ] STATUS_ENTREGAS.md atualizado (Status: ✅ CONCLUÍDO)

---

## 🎯 Próximas Ações

1. **Kick-off da Squad**: Alinhamento com todos os membros
2. **Task-001 Iniciada**: Data Engineer descobre arquivos Fibonacci
3. **Daily Standup**: 15:00 BRT (todos os dias)
4. **Gate de Qualidade**: 26/02 17:00 (revisão antes de merge)

---

## 📚 Referências

- [STATUS_ENTREGAS.md](STATUS_ENTREGAS.md) — Rastreamento oficial
- [ROADMAP.md](ROADMAP.md) — Visão estratégica
- [ARCHITECTURE.md](ARCHITECTURE.md) — Desenho técnico
- [BOARD_MULTIDISCIPLINAR.json](BOARD_MULTIDISCIPLINAR.json) — Squad
