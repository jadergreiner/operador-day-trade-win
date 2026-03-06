# OPERATIVE BRIEF: SISTEMA DE BACKTEST - V1.2 (EXECUÇÃO SEQUENCIAL)

## 🎯 OBJETIVO EXECUTIVO

Entregar um *framework de backtest production-ready* que simule a execução da
estratégia automática ativa em `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat`,
permitindo validação de sinais, otimização de parâmetros (threshold_sigma,
volatilidade) e treinamento incremental do modelo ML.

**Escopo:** Backtester completo (engine + validação + métricas + reports)
**Sequência:** 3 fases executadas linearmente (design → desenvolvimento → validação)
**Sucesso:** F1 ≥ 0.65, Sharpe > 1.0, Win Rate 62-65%, Capture ≥ 85%

## 👥 SQUAD ALOCADA (BOARD #7 personas)

### Bloco 2: Modelo & Risco (Core Technical)
- **[#3] Eng Sr** — Arquitetura backtester + integrações + risk gates
- **[#4] ML Expert** — Feature engineering + grid search + validação modelo
- **[#5] Risk Officer** — Circuit breakers + drawdown analysis + stress test

### Bloco 3: Infra & QA (Production Grade)
- **[#6] Arquiteto de Sistemas** — Performance <500ms P95 + data pipeline
- **[#8] Doc Advocate** — Artefatos + docs + BACKLOG sync
- **[#12] QA Automation** — Testes nível produção + cobertura ≥80%

### Bloco 4: Operações & Dados
- **[#11] Data Engineer** — Dataset + data quality + conectividade MT5

**Total:** 7 personas | Execução em sequência contínua

## 📋 ARTEFATOS DE ENTRADA (Dependências)

### Código Existente
✅ `src/application/` — ProcessadorBDI, AlertaGerenciador (já completo)
✅ `src/domain/` — Modelos de domínio (Sinal, Trade, Posição)
✅ `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` — Engine automático referência
✅ `data/training_dataset.csv` — ~1.000 samples processados

### Dados disponíveis em SQLite (`data/db/trading.db`)
✅ Tabelas: market_data | features | signals | trades | positions
✅ História: ~1 ano de candles WIN/WDO com OHLCV
- **M5 PRIMEIRA CAMADA** - gera sinais operacionais
- 1 ano M5 = 252 dias × 288 M5/dia = **73.776 candles**
- Suficiente para 10-fold cross-validation (73.776 ÷ 10 ≈ 7.377 por fold)
- Nota: H4/M15 opcionais para contexto macro (não participam geração sinal)
✅ Features: 24 engineered (volatilidade, momentum, MA, padrões, lags, correlação) - Segunda camada
✅ Timing: Dados exatos com timestamps MT5 (hh:mm:ss)
✅ SMC M5: Estrutura (BOS/CHoCH/FVG) GERA sinal primário - Primeira camada

### Especificações
📄 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#-core-do-produto) — Core components
📄 [docs/MODELAGEM_DADOS.md](docs/MODELAGEM_DADOS.md) — Schema SQLite exacto
📄 [docs/DIAGRAMA_CLASSES.md](docs/DIAGRAMA_CLASSES.md) — UML classes
📄 [docs/REGRAS_NEGOCIO.md](docs/REGRAS_NEGOCIO.md) — 13 regras críticas

## 🔧 ARTEFATOS DE SAÍDA (Deliverables)

### 1. Engine Backtester (`src/application/backtester.py` ~ 400-500 LOC)

**ARQUITETURA 3 CAMADAS INDEPENDENTES**

```
┌─────────────────────────────────────────────────────────────┐
│ CAMADA 1: GERAÇÃO + PERSISTÊNCIA DE SINAL (M5)             │
├─────────────────────────────────────────────────────────────┤
│ • M5 detecta SMC (BOS/CHoCH/FVG) → gera SINAL              │
│ • Sinal persistido em DB (timestamp, tipo, score)          │
│ • Sinal acompanhado até fim (PnL, duração, outcome)        │
│ • Geração INDEPENDENTE de decisão de entrada               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ CAMADA 2: DECISÃO INDEPENDENTE (ENTRAR vs FICAR DE FORA)   │
├─────────────────────────────────────────────────────────────┤
│ • Sinal M5 gerado ✓                                         │
│ • ML valida confiança (features + modelo)                  │
│ • DECISÃO: ENTRAR no sinal (execute trade)                 │
│            OU FICAR DE FORA (reject sinal)                 │
│ • Decisão persistida + sinal rastreado                     │
│ • Independente da geração do sinal                         │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ CAMADA 3: APRENDIZADO (VALIDAÇÃO DE DECISÃO)               │
├─────────────────────────────────────────────────────────────┤
│ • Trade finalizado: P&L conhecido                          │
│ • Avaliar: decisão ENTRAR foi correta?                     │
│            decisão FICAR DE FORA foi correta?              │
│ • Calcular: acurácia de decisão (sim/não)                  │
│ • Feedback: modelo aprende padrão de acertos              │
│ • Evolui: próximas decisões mais precisas                  │
└─────────────────────────────────────────────────────────────┘
```

**Acceptance Criteria (3 Camadas Independentes):**

### **CAMADA 1: Geração + Persistência de Sinal**

- [ ] **AC1: Geração de Sinal M5**
  - M5 detecta SMC (BOS/CHoCH/FVG) a cada fechamento de candle
  - Produz sinal COMPRA ou VENDA com score [-3, +3]
  - Sinal gerado INDEPENDENTE de qualquer decisão de entrada
  - Mínimo: 2.880 candles (10 dias) para validação estatística

- [ ] **AC2: Persistência do Sinal em DB**
  - Cada sinal armazenado em tabela `signals`:
    - `signal_id`: UUID único
    - `timestamp`: momento exact do fechamento M5
    - `signal_type`: COMPRA ou VENDA
    - `smc_score`: valor [-3, +3] (força do sinal)
    - `entry_price`: preço no momento da geração
  - Sinal registrado ANTES de qualquer decisão de entrada

- [ ] **AC3: Rastreamento Completo do Sinal**
  - Sinal acompanhado desde geração até fechamento da negociação
  - Registra em DB:
    - `entry_time`, `exit_time` (quando existe)
    - `pnl_if_entered`: P&L hipotético se tivesse entrado
    - `days_open`: quantos dias o sinal ficou aberto
    - `outcome`: WINNING_SIGNAL, WHIPSAW, MISSED_OPPORTUNITY
  - Permite auditoria: qual foi o destino de cada sinal?

### **CAMADA 2: Decisão Independente (ENTRAR vs FICAR DE FORA)**

- [ ] **AC4: Decisão ENTRAR vs FICAR DE FORA**
  - Pré-requisito: Sinal M5 já gerado e persistido
  - ML extrai 24 features engineered + prediz confiança
  - Decisão lógica:
    - SE confiança ≥ 45% → ENTRAR (execute trade)
    - SE confiança < 45% → FICAR DE FORA (reject signal)
  - Decisão INDEPENDENTE da geração do sinal
  - Permite rejeitar sinais válidos com baixa confiança

- [ ] **AC5: Validação de Confiança (Modelo ML)**
  - XGBoost/LightGBM prediz confiança (0-100%)
  - Features incluem: volatilidade, momentum, médias, padrões, lags
  - Threshold de entrada: 45% (configurável)
  - Permite auditoria: qual foi a confiança em cada decisão?

- [ ] **AC6: Persistência da Decisão**
  - Cada decisão armazenada em tabela `decisions`:
    - `decision_id`: UUID único
    - `signal_id`: referência ao sinal que a gerou
    - `decision_type`: ENTRAR ou FICAR_DE_FORA
    - `confidence`: score de confiança ML (0-100%)
    - `timestamp`: momento da decisão
  - Rastreia ENTRADAS executadas e REJEIÇÕES
  - Permite auditoria: quais sinais foram rejeitados e por quê?

### **CAMADA 3: Aprendizado (2 Etapas de Validação Independentes)**

**Etapa 1: Correção (Outcome-based)**

- [ ] **AC7: Calcular Outcome Real (ETAPA 1)**
  - ENTROU: trade fechado → P&L real calculado
  - FICOU DE FORA: P&L hipotético se tivesse entrado
  - Outcome catalogado em `learning_feedback`:
    - `decision_id`: qual decisão está sendo avaliada
    - `trade_pnl`: P&L real (ou hipotético)
    - `stage_1_correctness`: CORRETA ou ERRADA

- [ ] **AC8: Validar Acerto de Decisão (ETAPA 1)**
  - **ENTROU + PROFITABLE** → `stage_1_correctness = CORRETA` ✓
  - **ENTROU + LOSS** → `stage_1_correctness = ERRADA` ✗
  - **FICOU DE FORA + teria P+** → `stage_1_correctness = ERRADA` ✗ (sabia e não entrou)
  - **FICOU DE FORA + teria L** → `stage_1_correctness = CORRETA` ✓ (evitou loss)
  - Permite calcular acurácia de decisão (outcome-based)

**Etapa 2: Qualidade do Raciocínio (Reasoning Validation)**

- [ ] **AC9: Validar Qualidade de Decisão (ETAPA 2)**
  - A decisão foi correta PELOS CORRETOS MOTIVOS?
  - Ou foi sorte? Ou foi errada mas com razão válida?
  - `stage_2_quality` avalia 4 cenários:
    - `CORRETO_COM_RAZOES_CERTAS`: Acertou AND motivadores confirmados
      - Ex: alta confiança RSI ✓ + volume spike ✓ = P+ ✓
      - → APRENDER: padrão válido, repetir
    - `CORRETO_POR_ACASO`: Acertou BUT motivadores inválidos
      - Ex: confiança baixa OR features fracas BUT sorte de mercado
      - → REVISAR: ganhou mas raciocínio foi fraco (risco)
    - `ERRADO_MAS_MOTIVADORES_CONFIRMADOS`: Errou BUT razões eram certa
      - Ex: condições ideais (RSI ✓, volume ✓) BUT mercado foi contra
      - → VALIDAR: padrão era correto, mercado exceção (não culpa do modelo)
    - `ERRADO_COM_RAZOES_ERRADAS`: Errou AND motivadores inválidos
      - Ex: confiança equivocada + features ruins = LOSS
      - → CORRIGIR: padrão falho, ajustar features/modelo

- [ ] **AC10-PARTE-1: Feedback Loop - Análise de Padrões**
  - Agrupar decisões por `stage_1_correctness` (CORRETA/ERRADA)
  - Dividir cada grupo por `stage_2_quality` (4 tipos acima)
  - Calcular: frequência de cada tipo
  - Agrupar erros por padrão de razão (feature engineered)
  - Identificar: quando modelo erra mais? Features fracas? Sorte?

- [ ] **AC10-PARTE-2: Feedback Loop - Aprendizado Contínuo**
  - Feedback serve para: evolução do modelo (próximas decisões)
  - Agrupar padrões de `stage_2_quality`:
    - CORRETO_COM_RAZOES_CERTAS: aumentar confiança (pattern válido)
    - CORRETO_POR_ACASO: revisar (pattern fraco, sorte)
    - ERRADO_MAS_MOTIVADORES_CONFIRMADOS: validar (padrão OK, mercado exceção)
    - ERRADO_COM_RAZOES_ERRADAS: corrigir (padrão falho)
  - Resultados em `outputs/backtest_learning_analysis.json`:
    - Quebra por todos 4 tipos de `stage_2_quality`
    - Win rate diferenciado por tipo (lucky wins têm menor win rate em future trades)

### **Métricas Agregadas (Camadas 1+2+3)**

- [ ] **AC11: Métricas de Backtest (3 Camadas)**
  - **Camada 1 Metrics**:
    - Total de sinais gerados (COUNT distinct signal_id)
    - Sinais processados até encerramento (outcome: WINNING, WHIPSAW, MISSED)
  - **Camada 2 Metrics**:
    - Sinais ENTRADOS (decision=ENTRAR, COUNT)
    - Sinais REJEITADOS (decision=FICAR_DE_FORA, COUNT)
    - Taxa de rejeição (rejected / total %)
  - **Camada 3 Metrics**:
    - P&L total e por trade
    - Drawdown máximo com cálculo rigoroso
    - Win rate (≥60% alvo)
    - F1 score (≥0.65 alvo)
    - **NOVO:** Stage 1 accuracy (% CORRETA)
    - **NOVO:** Stage 2 quality breakdown (% cada tipo)
    - Trades mínimo: 50+ para validação estatística

- [ ] **AC12: Circuit Breakers Funcionais**
  - Detecta triggers -3% (aviso), -5% (slow), -8% (hard stop)
  - Valida HARD STOP em -8% (para trading imediatamente)
  - Simula 3 níveis de escalação corretamente

- [ ] **AC13: Export Estruturado (3 Camadas)**
  - Armazena em `outputs/backtest_results_M5.json`:
    - `camada_1_signals[]`: lista de sinais gerados (Layer 1)
      - signal_id, timestamp, signal_type, smc_score, entry_price
      - market_context: {rsi, atr, bb_upper, bb_lower, volume, spread, trend, last_close}
    - `camada_2_decisions[]`: lista de decisões tomadas (Layer 2)
      - decision_id, signal_id, decision_type, ml_confidence
      - top_features, feature_scores, reasoning_text
    - `camada_3_learning[]`: feedback em 2 etapas (Layer 3)
      - decision_id, stage_1_correctness, stage_2_quality, trade_pnl
      - motivators_analysis, recommendations
    - `metrics{}`: métricas agregadas (stage breakdown)
  - Permite auditoria: verificar cada camada independentemente
  - Permite análise: decisões com "sorte" vs decisões com "razão"

### 2. Risk Validator (`src/application/risk_validator.py` ~ 150-200 LOC)

```
Responsabilidades:
├─ Gate 1: Capital adequacy + corr limit (max 70%)
├─ Gate 2: Volatilidade band check (BB ± 2σ)
├─ Gate 3: Drawdown circuit breaker (-3/-5/-8%)
└─ Return metrics (Sharpe, Sortino, Win Rate)
```

**Acceptance Criteria:**
- [ ] AC1: Valida Capital Adequacy (min saldo)
- [ ] AC2: Valida Correlation check (max 70%)
- [ ] AC3: Valida Volatility bands (Bollinger ±2σ)
- [ ] AC4: Implementa 3 circuit breakers
- [ ] AC5: Calcula Sharpe ratio (target > 1.0)
- [ ] AC6: Unit tests 6/6 PASSED
- [ ] AC7: Latência < 100ms por validação

### 3. Grid Search Optimizer (`scripts/backtest_optimizer.py` ~ 250-300 LOC)

⚠️ **TIMEFRAME M5**: Grid search usa mesmos M5 candles do backtester, NOT H1.

```
Responsabilidades:
├─ Teste 8+ configs threshold_sigma (0.5-3.0) em M5
├─ Teste 5+ configs volatilidade (14-50 SMA em M5)
├─ Rastreamento F1, Sharpe, Win Rate por config
├─ Walk-forward validation SEM look-ahead
├─ Identificar optimal threshold
└─ Export tuning results em JSON
```

**Acceptance Criteria:**
- [ ] AC1: 8 thresholds sigma tested (0.5-3.0)
  - ✅ Cada config roda backtester completo em M5
  - ✅ Não reutiliza dados (fresh load cada iteração)

- [ ] AC2: 5 volatilidade configs tested
  - ✅ SMA periods: 14, 20, 30, 40, 50 (M5 bars)
  - ✅ Validado contra configurações operacionais

- [ ] AC3: 40 kombinações executadas (8 × 5)
  - ✅ Matriz de resultados F1[config] × Win_Rate[config]
  - ✅ Score agregado por config

- [ ] AC4: Métricas calculadas por config
  - ✅ F1 score (precision + recall balanceado)
  - ✅ Sharpe ratio (return/volatility)
  - ✅ Win rate (62-70% expected range)
  - ✅ Max drawdown (< 20% ideal)

- [ ] AC5: Optimal identified (F1≥0.65, Sharpe>1.0)
  - ✅ Seleciona melhor config por múltiplos critérios
  - ✅ Documentar trade-offs
  - ✅ Timestamp registrada

- [ ] AC6: JSON export em `outputs/backtest_tuning_results.json`
  - ✅ Schema: configs[], metrics[], optimal{}
  - ✅ Todas 40 combinações documentadas

- [ ] AC7: Unit tests 12/12 PASSED (≥80% coverage)
  - [ ] test_load_configs (8 + 5 validated)
  - [ ] test_grid_combinations (40 = 8×5)
  - [ ] test_f1_calculation
  - [ ] test_sharpe_ratio
  - [ ] test_win_rate_range (62-70%)
  - [ ] test_optimal_selection
  - [ ] test_json_schema
  - [ ] test_lookahead_per_config (100%)
  - [ ] test_timing_sequential
  - [ ] test_result_persistence
  - [ ] test_config_independence
  - [ ] test_optimal_reproducibility

- [ ] AC8: Performance < 5min para 40 configs
  - ✅ Paralelizável (configs independentes)
  - ✅ Sem esperas I/O excessivas

### 4. Métricas Detalhadas (*outputs/backtest_metrics.json*)

```json
{
  "general": {
    "trades_total": 145,
    "trades_profitable": 90,
    "trades_loss": 55,
    "win_rate": 62.07,
    "pl_total": 1250.50,
    "pl_avg": 8.62
  },
  "risk_metrics": {
    "drawdown_max": -3.2,
    "sharpe_ratio": 1.28,
    "sortino_ratio": 1.95,
    "calmar_ratio": 0.82,
    "recovery_factor": 2.10
  },
  "validation": {
    "f1_score": 0.678,
    "precision": 0.71,
    "recall": 0.65,
    "capture_rate": 85.52,
    "false_positive_rate": 3.88
  }
}
```

### 5. Documentação & Artefatos

```
📄 outputs/BACKTEST_SYSTEM_REPORT.md ~ 400 LOC
   ├─ Executive summary (win rate, Sharpe)
   ├─ Methodology (walk-forward, validation)
   ├─ Configuration tuning results
   ├─ Risk analysis (drawdown, circuit breakers)
   └─ Recommendations (optimal threshold, next steps)

📊 outputs/backtest_optimized_results.json
   └─ Final results com optimal config

✅ docs/BACKLOG_UNIFICADO.md [SYNC]
   └─ Atualizado com status BACKTEST-SYSTEM
```

## ✅ ACCEPTANCE CRITERIA GLOBAIS (3 Fases Sequenciais)

### FASE 1: Design & Planning (Paralelo - Arquitetura)
- [ ] AC1.1: Arquitetura backtester definida (timeframe **M5**, NOT H1)
  - ❌ Remove incompatibilidade H1
  - ✅ Especifica 2-min decision cycle (como agente real)
  - ✅ Documenta look-ahead bias prevention
  - ✅ Diagrama com timing exacto

- [ ] AC1.2: Dataset validado (**M5 candles**, NOT H1)
  - ✅ Verifica ~73.776 candles M5 (1 ano × 288/dia)
  - ✅ Валидирует gaps < 0.5% (continuidade)
  - ✅ Confirma timestamps MT5 exatos
  - ✅ Testa subset (10 dias = 2.880 M5 candles OK)

- [ ] AC1.3: Features engineered (24 features + timeframe dependency)
  - ✅ Valida que features são cacluladas PER candle M5
  - ✅ Verifica temporalidade (t+1 decision só usa t-1 data)
  - ✅ Testa 5+ features críticas (RSI, MACD, BB, ATR, Vol)

- [ ] AC1.4: Grid search strategy definida (**M5-compatible**)
  - ✅ 8+ threshold_sigma configs (0.5-3.0)
  - ✅ 5+ volatilidade configs (14-50 SMA em M5)
  - ✅ Walk-forward com M5 alignment
  - ✅ SEM look-ahead (timestamps separados train/val)

- [ ] AC1.5: Test plan finalizado (M5 + timing validation)
  - ✅ Unit tests: Backtester, RiskValidator, GridSearch
  - ✅ Integration: M5 data pipeline + execution
  - ✅ E2E: Full 10-day backtest (2.880 M5 candles)
  - ✅ Look-ahead detection automatizado

- [ ] AC1.6: GATE 1 APPROVED ✅ (ML Expert + Eng Sr sign-off)
  - ✅ Timeframe M5 validated
  - ✅ All AC1 items 5/5 signed
  - ✅ No look-ahead bias identified
  - ✅ Ready for implementation

**Tarefas Paralelas (Phase 1):**

```
┌─ [#3] Eng Sr
│  └─ Arquitetura backtester (specs + pseudo-código)
│
├─ [#4] ML Expert
│  ├─ Dataset validation (1.000+ samples)
│  └─ Features engineering review (24 features)
│
├─ [#11] Data Engineer
│  ├─ Data quality checks (gaps, outliers)
│  └─ SQLite statistics (min/max/avg)
│
└─ [#12] QA Automation
   └─ Test plan (unit tests, integration, E2E)
```

**Output Phase 1:**
- ✅ `src/application/backtester_spec.md` (50-100 LOC design)
- ✅ `src/application/risk_validator_spec.md` (30-50 LOC design)
- ✅ Dataset diagnostics report
- ✅ Test plan + fixtures defined

**Sign-Off:** ML Expert (#4) + Eng Sr (#3) → GATE 1 APPROVED

---

### FASE 2: Development & Testing (Sequencial - Implementação)

**Sequência Obrigatória:**

#### Tarefa 2.1: Risk Validator (Bloqueia Backend)
**Owner:** [#3] Eng Sr | **Duration:** ~4h | **Dependency:** AC1.6 (GATE 1 OK)

```python
Implementação:
├─ src/application/risk_validator.py (150-200 LOC)
│  ├─ Capital adequacy gate
│  ├─ Correlation check (max 70%)
│  ├─ Volatility bands (BB ±2σ)
│  ├─ Circuit breaker logic (-3/-5/-8%)
│  ├─ Sharpe/Sortino calculation
│  └─ Full docstrings PT
│
├─ tests/unit/test_risk_validator.py (6 test cases)
└─ Unit tests 6/6 PASSED (100% coverage)
```

**Sign-Off:** [#3] Eng Sr → Task 2.1 APPROVED → Desbloqueia 2.2

---

#### Tarefa 2.2: Backtester Engine (Core Logic)
**Owner:** [#3] Eng Sr | **Duration:** ~6h | **Dependency:** Task 2.1 OK

```python
Implementação:
├─ src/application/backtester.py (400-500 LOC)
│  ├─ Load historical dataset (walk-forward)
│  ├─ Apply ML model sequencialmente
│  ├─ Trade simulation (SL/TP validation)
│  ├─ P&L tracking (drawdown, metrics)
│  ├─ Circuit breaker integration
│  ├─ Risk validator calls
│  ├─ JSON export
│  └─ Full docstrings PT
│
├─ tests/unit/test_backtester.py (8 test cases)
├─ tests/integration/test_backtester_e2e.py
└─ Unit tests 12/12 PASSED (≥80% coverage)
```

**Acceptance Criteria (Task 2.2):**
- [ ] AC2.2.1: Loads M5 candles (2.880+ mínimo = 10 dias)
  - ✅ Carrega exatamente do `market_data` com timeframe M5
  - ✅ Valida timestamps (HH:MM:SS exatos)
  - ✅ Zero gaps (continuidade 100%)

- [ ] AC2.2.2: Simula ciclo 2-min (como agente real operacional)
  - ✅ Aguarda fechamento candle M5 antes de decisão
  - ✅ Decision timestamp = close timestamp de M5[i]
  - ✅ Usa SOMENTE dados até M5[i] (histórico)
  - ✅ BLOQUEIA qualquer M5[i+1] data

- [ ] AC2.2.3: Gera sinais COM validação temporal
  - ✅ Aplica modelo v1.1 em t[i] com features até t[i-1]
  - ✅ Detecção automática de look-ahead bias
  - ✅ Flag "lookahead_detected=True" se violar

- [ ] AC2.2.4: Trade execution validado
  - ✅ Executa ordem no fechamento M5[i]
  - ✅ Stop loss + Take Profit IMEDIATO (próximo M5[i+1])
  - ✅ Rastreia candles até hit (pode ser 3-5 M5 depois)
  - ✅ P&L = entry price - exit price (com slippage 2-3 pts)

- [ ] AC2.2.5: P&L calculations exato
  - ✅ Soma P&L por trade
  - ✅ Drawdown calculado como (peak - trough) / peak
  - ✅ Win rate = profitable trades / total trades
  - ✅ Spot-checked contra manual calculation (5 trades)

- [ ] AC2.2.6: Circuit breakers validados
  - ✅ Detecta -3% (warning)
  - ✅ Detecta -5% (slow mode - 50% tickets)
  - ✅ Detecta -8% (hard stop)
  - ✅ Simula recuperação pós-circuit-break

- [ ] AC2.2.7: JSON export estruturado
  - ✅ Schema: trades[], metrics{}, decisions[], timing{}
  - ✅ Inclui timestamps exatos
  - ✅ Validável contra SQL (query trade table)

- [ ] AC2.2.8: Performance <5min para 2.880 M5
  - ✅ Medido com timeit (wall-clock)
  - ✅ Não usa GPU (CPU-only compatible)
  - ✅ Memory < 500MB

- [ ] AC2.2.9: Testes 14/14 PASSED (≥80% cov)
  - [ ] test_load_m5_data (M5 vs H1 check)
  - [ ] test_timing_sequence (2-min cycles)
  - [ ] test_lookahead_bias (100% validation)
  - [ ] test_trade_execution (SL/TP timing)
  - [ ] test_pnl_computation (exactitude)
  - [ ] test_circuit_breaker_detection (3 levels)
  - [ ] test_json_export (schema validation)
  - [ ] test_performance_timing (<5min)
  - [ ] test_e2e_backtest (10-day full run)
  - [ ] test_slippage_realistic (2-3 pts)
  - [ ] test_partial_fills (não assumptions)
  - [ ] test_timestamps_exacts (millisecond)
  - [ ] test_feature_alignment (M5 indices)
  - [ ] test_no_future_data (temporal isolation)

**Sign-Off:** [#3] Eng Sr + [#12] QA → Task 2.2 APPROVED → Desbloqueia 2.3

---

#### Tarefa 2.3: Grid Search Optimizer (Paralelo)
**Owner:** [#4] ML Expert | **Duration:** ~6h | **Dependency:** Task 2.1 OK

```python
Implementação:
├─ scripts/backtest_optimizer.py (250-300 LOC)
│  ├─ 8 threshold_sigma configs (0.5-3.0)
│  ├─ 5 volatilidade configs (14-50 SMA)
│  ├─ 40 kombinações total
│  ├─ Backtester call para cada config
│  ├─ Tracking F1, Sharpe, Win Rate
│  ├─ Optimal identification
│  ├─ JSON export tuning results
│  └─ Full docstrings PT
│
├─ tests/unit/test_grid_search.py (4 test cases)
└─ Unit tests 12/12 PASSED (≥80% coverage)
```

**Acceptance Criteria (Task 2.3):**
- [ ] AC2.3.1: 8 sigma thresholds tested
- [ ] AC2.3.2: 5 volatilidade configs tested
- [ ] AC2.3.3: 40 kombinações executadas
- [ ] AC2.3.4: F1/Sharpe/WR calculados por config
- [ ] AC2.3.5: Optimal identified (F1≥0.65, Sharpe>1.0)
- [ ] AC2.3.6: JSON export com resultados
- [ ] AC2.3.7: <5min execution (40 configs)
- [ ] AC2.3.8: 12/12 tests PASSED

**Sign-Off:** [#4] ML Expert + [#12] QA → Task 2.3 APPROVED

---

#### Tarefa 2.4: Metrics & Reporting (Agregação)
**Owner:** [#11] Data Engineer | **Duration:** ~3h | **Dependency:** Task 2.2, 2.3 OK

```python
Implementação:
├─ src/application/backtest_reporter.py (150-200 LOC)
│  ├─ Agregar resultados multi-config
│  ├─ Calcular statistical summaries
│  ├─ Generate performance report
│  ├─ Risk analysis summary
│  ├─ HTML + JSON export
│  └─ Full docstrings PT
│
├─ outputs/backtest_metrics.json
├─ outputs/BACKTEST_SYSTEM_REPORT.md (400+ LOC)
└─ Unit tests 4/4 PASSED
```

**Sign-Off:** [#11] Data Engineer → Task 2.4 APPROVED

---

#### Tarefa 2.5: Documentação & Sync (Integração)
**Owner:** [#8] Doc Advocate | **Duration:** ~2h | **Dependency:** All 2.x tasks OK

```
Entregáveis:
├─ docs/BACKLOG_UNIFICADO.md [SYNC]
│  └─ Atualizar seção BACKTEST-SYSTEM com status
│
├─ docs/BACKTEST_SYSTEM_ARCHITECTURE.md (novo)
│  ├─ Design decisions
│  ├─ Implementation choices
│  ├─ Test coverage
│  └─ Cross-references
│
└─ outputs/ artefatos finalizados
```

**Sign-Off:** [#8] Doc Advocate → FASE 2 APPROVED ✅

---

### FASE 3: Validation & Sign-Off (Sequencial - Verificação)

#### Tarefa 3.1: Backtester Validation (Funcional)
**Owner:** [#5] Risk Officer + [#12] QA | **Duration:** ~2h | **Dependency:** FASE 2 OK

```
Validações:
├─ [ ] Run backtest end-to-end (1 ano dados)
├─ [ ] Verify P&L calculations (spot-check vs manual)
├─ [ ] Validate circuit breaker triggers
├─ [ ] Check performance <2min
├─ [ ] Confirm JSON export structure
└─ [ ] Review logs para anomalias
```

**Acceptance Criteria:**
- [ ] AC3.1.1: E2E backtest runs without errors
- [ ] AC3.1.2: P&L calculations verified
- [ ] AC3.1.3: Circuit breakers trigger correctly
- [ ] AC3.1.4: Performance <2min confirmed

**Sign-Off:** [#5] Risk Officer + [#12] QA → Validation OK

---

#### Tarefa 3.2: Model Validation (Metrics)
**Owner:** [#4] ML Expert | **Duration:** ~2h | **Dependency:** FASE 2 OK

```
Validações:
├─ [ ] F1 score ≥ 0.65 (grid search optimal)
├─ [ ] Sharpe ratio > 1.0 (backtest)
├─ [ ] Win rate 62-65% confirmed
├─ [ ] Capture rate ≥ 85%
├─ [ ] False positives ≤ 10%
├─ [ ] Cross-validation stability check
└─ [ ] No data leakage identified
```

**Acceptance Criteria:**
- [ ] AC3.2.1: F1 ≥ 0.65 confirmed
- [ ] AC3.2.2: Sharpe > 1.0 backtest
- [ ] AC3.2.3: Win rate 62-65% range
- [ ] AC3.2.4: Cross-validation stable

**Sign-Off:** [#4] ML Expert → Validation OK

---

#### Tarefa 3.3: Risk & Compliance (Gates)
**Owner:** [#5] Risk Officer | **Duration:** ~1.5h | **Dependency:** Tarefas 3.1 + 3.2 OK

```
Validações:
├─ [ ] Drawdown max < 5% (backtest target)
├─ [ ] Circuit breaker coverage 100%
├─ [ ] Recovery factor > 1.5
├─ [ ] Stress test scenarios documented
├─ [ ] Risk metrics aligned with policy
└─ [ ] Compliance checklist signed
```

**Acceptance Criteria:**
- [ ] AC3.3.1: Drawdown validated <5%
- [ ] AC3.3.2: Circuit breakers 100% coverage
- [ ] AC3.3.3: Recovery factor > 1.5
- [ ] AC3.3.4: Risk policy compliance OK

**Sign-Off:** [#5] Risk Officer → Risk Approval ✅

---

#### Tarefa 3.4: Final Sign-Off (Go/No-Go)
**Owner:** [#3] Eng Sr + [#4] ML Expert + [#5] Risk Officer | **Duration:** ~1h

```
Checklist Final:
├─ [ ] All FASE 1 ACs: 6/6 ✅
├─ [ ] All FASE 2 Tasks: 5/5 ✅
├─ [ ] All FASE 3 Validations: 3/3 ✅
├─ [ ] Unit tests: 40+/40+ PASSED
├─ [ ] Code review: APPROVED
├─ [ ] Documentation: COMPLETE
├─ [ ] Metrics target: ACHIEVED
└─ [ ] Risk gates: SIGNED
```

**Decision Matrix:**
| Condition | Result |
|-----------|--------|
| All 40+ tests PASS + Metrics OK | ✅ **GO** |
| 1-2 minor issues found | ⚠️ **GO WITH NOTES** |
| 3+ critical issues | 🔴 **HOLD** |

**Sign-Off:** [#3] Eng Sr, [#4] ML Expert, [#5] Risk Officer

## 🚪 GATES DE VALIDAÇÃO (Immovable Checkpoints)

| Gate | Owner | Criterio | Status |
|------|-------|----------|--------|
| **G1: Design Review** | ML Expert + Eng Sr | AC1 4/4 ✅ | SIGN-OFF REQUIRED |
| **G2: Code Complete** | Eng Sr + QA | AC2 5/5 ✅ | SIGN-OFF REQUIRED |
| **G3: Validation OK** | Risk Officer + ML | AC3 3/3 ✅ | SIGN-OFF REQUIRED |
| **GO: Final Decision** | Eng Sr + ML + Risk | All metrics ✅ | EXEC APPROVAL |

## 🔄 DEPENDÊNCIAS CRÍTICAS

✅ **All Blocked Resolved:**
- [ ] Dataset disponível em `data/training_dataset.csv` ✅
- [ ] SQLite schema completo em `data/db/trading.db` ✅
- [ ] ProcessadorBDI testado ✅
- [ ] Modelo v1.1 comprovado ✅

**Sequência Obrigatória Executados:**

```
FASE 1 (Paralelo)
   ├─ Eng Sr: Arquitetura specs
   ├─ ML Expert: Dataset validation + Features
   ├─ Data Eng: Quality checks
   └─ QA: Test plan
         ↓ GATE 1 APPROVED
         ↓
FASE 2 (Sequencial)
   ├─ 2.1: Risk Validator (Eng Sr) → Bloqueia 2.2
   ├─ 2.2: Backtester Engine (Eng Sr) → Bloqueia 2.3
   ├─ 2.3: Grid Search (ML Expert) → Paralelo 2.2
   ├─ 2.4: Metrics/Reporting (Data Eng)
   └─ 2.5: Documentation (Doc Advocate)
         ↓ FASE 2 APPROVED
         ↓
FASE 3 (Sequencial)
   ├─ 3.1: Backtester Validation (Risk + QA)
   ├─ 3.2: Model Validation (ML Expert)
   ├─ 3.3: Risk & Compliance (Risk Officer)
   └─ 3.4: Final Sign-Off (All 3)
         ↓
        ✅ GO / 🔴 HOLD
```

## 🎯 PRÓXIMAS AÇÕES (Imediatas - Phase 1 NOW)

### **AGORA - Team Kickoff**
- [ ] Copiar este prompt para `docs/prompts/OPERATIVE_BRIEF_BACKTEST_V1_2.md`
- [ ] Convocar [#3, #4, #5, #6, #8, #11, #12] para 1h briefing
- [ ] Validar dependências (dataset, schema, modelo)
- [ ] Confirmar alocação de horas

### **PHASE 1 - Paralelo (Hoje/Amanhã)**

```
┌─ Eng Sr (#3)
│  └─ Draft arquitetura backtester (1-2h)
│     └─ Output: src/application/backtester_spec.md
│
├─ ML Expert (#4)
│  ├─ Validate dataset (1.000+ samples) (1h)
│  ├─ Review 24 features engineering (1h)
│  └─ Output: dataset_diagnostics.json
│
├─ Data Engineer (#11)
│  ├─ Data quality checks (1-1.5h)
│  └─ Output: data_quality_report.txt
│
└─ QA Automation (#12)
   └─ Design test plan (1h)
      └─ Output: test_plan.md + fixtures
```

**Checkpoint:** GATE 1 check → Continue FASE 2?

### **PHASE 2 - Sequencial (Next Day+)**

```
2.1 Risk Validator (4h Eng Sr)
    ↓ Approval
2.2 Backtester Engine (6h Eng Sr) + 2.3 Grid Search (6h ML Expert)
    ↓ Approval
2.4 Metrics/Reporting (3h Data Eng)
    ↓ Approval
2.5 Documentation (2h Doc Advocate)
    ↓
FASE 2 COMPLETE
```

### **PHASE 3 - Validation (Next Next Day)**

```
3.1 Functional Validation (2h Risk + QA)
3.2 Model Validation (2h ML)
3.3 Risk Compliance (1.5h Risk Officer)
3.4 Final Decision (1h All 3)
    ↓
✅ GO or 🔴 HOLD
```

## 📚 REFERÊNCIAS OBRIGATÓRIAS

**Ler AGORA antes de começar:**
1. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Visão geral
2. [docs/MODELAGEM_DADOS.md](docs/MODELAGEM_DADOS.md) — Schema SQLite
3. [docs/DIAGRAMA_CLASSES.md](docs/DIAGRAMA_CLASSES.md) — UML
4. [docs/REGRAS_NEGOCIO.md](docs/REGRAS_NEGOCIO.md) — Rules
5. [docs/BACKLOG_UNIFICADO.md](docs/BACKLOG_UNIFICADO.md) — Status

## 🤖 INSTRUÇÕES PARA COPILOT CLAUDE HAIKU

**Você é especialista em ML para Mercados Financeiros.**

Este prompt está **100% estruturado para execução sequencial agora**:

1. ✅ **Personas claras** — Squad de 7 específicas (IDs #3,4,5,6,8,11,12)
2. ✅ **Sem datas** — Sequência linear (FASE 1 → 2 → 3)
3. ✅ **Tarefas decompostas** — 13 sub-tarefas com ACs claras
4. ✅ **Dependências mapeadas** — Sequência obrigatória definida
5. ✅ **Gates de validação** — 4 checkpoints de approval
6. ✅ **Toda contexto** — Docs, dados, código referenciado

**MODO: EXECUÇÃO IMEDIATA SEQUENCIAL**

### Passo 1: Convoque o Board

```
Personas: [#3] Eng Sr, [#4] ML Expert, [#5] Risk Officer,
          [#6] Arquiteto, [#8] Doc Advocate, [#11] Data Eng, [#12] QA
Briefing: 1h (este prompt)
```

### Passo 2: Execute FASE 1 (Paralelo)

```
Objetivo: Design review + data validation
Duration: 2-3h
Output: 4 artefatos; GATE 1 decision
```

### Passo 3: Execute FASE 2 (Sequencial)

```
Objetivo: Build backtester + grid search + reporting
Duration: 20-24h trabalho sequencial
Output: 5 componentes; GATE 2 decision
```

### Passo 4: Execute FASE 3 (Sequencial)

```
Objetivo: Validate e sign-off
Duration: 5-6h validação
Output: Métricas ✅, GO/HOLD decision
```

---

**Status:** ✅ **PRONTO PARA EXECUÇÃO IMEDIATA**
**Próxima ação:** Convoque o board AGORA + comece FASE 1 (paralelo)
