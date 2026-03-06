# 📊 Data Models - Operador Day Trade WIN

**Versão:** 1.0.4
**Data Criação:** 27/02/2026
**Última Atualização:** 03/03/2026 (AC4 + AC5 + AC6 Pipeline Complete)
**Responsável:** Data Engineer + Arquiteto de Sistemas
**Sincronização:** [ARCHITECTURE.md](ARCHITECTURE.md) | [MODELAGEM_DADOS.md](MODELAGEM_DADOS.md) | [DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md)
**Status:** ✅ Sincronizado com 5 documentos arquiteturais + AC1-AC6 Implementation

⭐ **CORE DO PRODUTO**: Os modelos aqui descritos são populados/utilizados por [INICIAR_DIARIOS.bat](../INICIAR_DIARIOS.bat) e [INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat](../INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat).

⭐ **AC6 ML FEEDBACK LOOP** (03/03/2026): MLFeedbackLoop implementado para learning complete com 21 testes + 100% coverage

---

## 🎯 Objetivo

Documentar os modelos de dados que suportam a operação do Operador Day Trade WIN,
especialmente a integração com decisões, persistência e auditoria de operações.

## 📚 Documentação Relacionada (Ler Junto)

| Documento | Propósito | Quando Ler |
|-----------|----------|-----------|
| **[MODELAGEM_DADOS.md](MODELAGEM_DADOS.md)** | Schema SQL completo (DDL) com 10 tabelas, indices e triggers | Quando implementar BD |
| **[DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md)** | Modelo ER visual com 10 entidades e relacionamentos | Quando entender fluxo de dados |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Visão arquitetural geral do sistema | Primeiro (contexto) |
| **[REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md)** | Regras que devem ser validadas nos dados | Quando definir validações |

**Fluxo de Leitura:**
1. ARCHITECTURE.md (contexto geral)
2. DIAGRAMA_DADOS.md (visão ER)
3. DATA_MODELS.md (descrição dos modelos - este arquivo)
4. MODELAGEM_DADOS.md (implementação SQL completa)
5. REGRAS_NEGOCIO.md (validações aplicáveis)

## 📋 PADRÕES DE CODIFICAÇÃO

Todas as operações com modelos de dados devem seguir [CODING_STANDARDS.md](CODING_STANDARDS.md):

**Para Schemas e Tabelas:**
- Naming conventions: snake_case (tabelas), CamelCase (classes)
- Type hints on all data access code (mypy --strict)
- Repository Pattern for database access (abstraction)
- Error handling with detailed logging
- Audit trails for all mutations (created_at, updated_at, deleted_at)

**Para Code Data Access:**
- Use type hints on queries and results
- Implement retry logic for transient failures
- Log all database operations (reads, writes, deletes)
- Validate data constraints in application layer
- Use repositories to abstract persistence

**Validação:** Code review + Schema review + Tests

---

## 📚 Padrão de Scripts - Localização Obrigatória

**Todos os scripts Python de análise, auditoria e utilidade devem estar em `scripts/`**

Ver [CODING_STANDARDS.md - Scripts](CODING_STANDARDS.md#11-scripts---padrão-de-localização-obrigatório-) para estrutura completa.

**Exemplos de scripts relacionados a data models:**
- `scripts/analise_sqlite.py` - Auditoria banco trading.db
- `scripts/verify_schema_integrity.py` - Validação de schemas
- `scripts/extract_data_export.py` - Exportação de dados
- `scripts/check_data_consistency.py` - Verificação de consistência

---

## 1️⃣ CAMADA 1: Market Data (Dados de Mercado)

### 1.1 Tabela: `market_candles` (Dados OHLCV)

**Propósito:** Armazenar candles (velas) de mercado em múltiplos timeframes.

**SQL Schema:**

```sql
CREATE TABLE market_candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL UNIQUE,
    symbol VARCHAR(10) NOT NULL,  -- "WINFUT"
    timeframe VARCHAR(5) NOT NULL,  -- "M1", "M5", "H1"
    open DECIMAL(10, 5) NOT NULL,
    high DECIMAL(10, 5) NOT NULL,
    low DECIMAL(10, 5) NOT NULL,
    close DECIMAL(10, 5) NOT NULL,
    volume BIGINT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (timestamp, symbol, timeframe),
    INDEX idx_timestamp_symbol (timestamp, symbol),
    INDEX idx_timeframe (timeframe)
);
```

**Exemplos de Registro:**

| timestamp | symbol | timeframe | open | high | low | close | volume |
|-----------|--------|-----------|------|------|-----|-------|--------|
| 2026-02-27 14:30:00 | WINFUT | M1 | 124230 | 124305 | 124210 | 124290 | 1250 |
| 2026-02-27 14:31:00 | WINFUT | M1 | 124290 | 124350 | 124270 | 124330 | 980 |
| 2026-02-27 14:35:00 | WINFUT | M5 | 124230 | 124350 | 124210 | 124330 | 5010 |

---

## 2️⃣ CAMADA 2: Technical Indicators (Indicadores Técnicos)

### 2.1 Tabela: `atr_historical` (ATR Dinâmico - S2-2)

**Propósito:** Armazenar cálculos históricos de ATR para análise de volatilidade
e calibração dinâmica de trailing stop e volume.

**SQL Schema:**

```sql
CREATE TABLE atr_historical (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    symbol VARCHAR(10) NOT NULL,  -- "WINFUT"
    timeframe VARCHAR(5) NOT NULL,  -- "M1", "M5"
    atr_period INTEGER NOT NULL DEFAULT 14,  -- Standard ATR period
    atr_value DECIMAL(10, 5) NOT NULL,  -- ATR raw value
    atr_zscore DECIMAL(5, 3) NOT NULL,  -- (atr - mean) / std
    atr_percentile_rank DECIMAL(5, 2) NOT NULL,  -- Percentile 0-100
    volatility_state VARCHAR(20) NOT NULL,  -- LOW, NORMAL, HIGH, EXTREME
    volatility_state_id INTEGER NOT NULL,  -- 1=LOW, 2=NORMAL, 3=HIGH, 4=EXTREME
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (timestamp, symbol, timeframe),
    INDEX idx_timestamp_volatility (timestamp, volatility_state),
    INDEX idx_symbol_timeframe (symbol, timeframe)
);
```

**Volatility States:**

| State | ID | Range (ATR Points) | Description |
|-------|----|--------------------|-------------|
| LOW | 1 | < 50 | Volatilidade baixa, até para day trade |
| NORMAL | 2 | 50-150 | Volatilidade padrão, operação ótima |
| HIGH | 3 | 150-300 | Volatilidade elevada, reduzir volume |
| EXTREME | 4 | > 300 | Volatilidade extrema, mínimo volume |

**Exemplos de Registro:**

| timestamp | symbol | timeframe | atr_value | atr_zscore | volatility_state |
|-----------|--------|-----------|-----------|-----------|------------------|
| 2026-02-27 14:30:00 | WINFUT | M1 | 125.50 | 0.35 | NORMAL |
| 2026-02-27 14:31:00 | WINFUT | M1 | 128.20 | 0.62 | NORMAL |
| 2026-02-27 15:00:00 | WINFUT | M1 | 280.75 | 2.15 | HIGH |
| 2026-02-27 15:05:00 | WINFUT | M1 | 380.90 | 3.05 | EXTREME |

---

### 2.2 Tabela: `technical_indicators` (Outros Indicadores)

**Propósito:** Armazenar outros indicadores técnicos (RSI, MACD, Bollinger, etc.)
para análise multi-indicador.

**SQL Schema:**

```sql
CREATE TABLE technical_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    timeframe VARCHAR(5) NOT NULL,
    -- Momentum
    rsi_14 DECIMAL(5, 2),  -- RSI 14 períodos
    macd DECIMAL(10, 5),  -- MACD line
    macd_signal DECIMAL(10, 5),  -- MACD signal
    macd_histogram DECIMAL(10, 5),  -- MACD histogram
    -- Volatility
    bb_upper DECIMAL(10, 5),  -- Bollinger Upper
    bb_middle DECIMAL(10, 5),  -- Bollinger Middle
    bb_lower DECIMAL(10, 5),  -- Bollinger Lower
    bb_pct_b DECIMAL(5, 2),  -- Bollinger %B
    -- Moving Averages
    sma_20 DECIMAL(10, 5),
    sma_50 DECIMAL(10, 5),
    ema_9 DECIMAL(10, 5),
    ema_21 DECIMAL(10, 5),
    -- Volume
    volume_ma_20 BIGINT,  -- Volume moving average 20
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (timestamp, symbol, timeframe),
    INDEX idx_timestamp_symbol (timestamp, symbol)
);
```

---

## 3️⃣ CAMADA 3: ML Features (Features de Machine Learning)

### 3.1 Tabela: `ml_features` (Features Engineeradas)

**Propósito:** Armazenar 24+ features engineeradas para treinamento e inferência
de modelos preditivos.

**SQL Schema:**

```sql
CREATE TABLE ml_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    -- Target Features (output)
    label INTEGER,  -- 0: SKIP, 1: BUY
    label_confidence DECIMAL(5, 2),  -- 0-100 confidence %
    -- Volatility Features (6)
    atr_15m DECIMAL(10, 5) NOT NULL,  -- ATR 15 min
    bb_range DECIMAL(10, 5) NOT NULL,  -- Upper - Lower
    bb_pct_b DECIMAL(5, 2) NOT NULL,  -- Bollinger %B
    hist_volatility DECIMAL(5, 3) NOT NULL,  -- 20-period HV
    volatility_zscore DECIMAL(5, 3) NOT NULL,  -- (vol - mean) / std
    volatility_regime_id INTEGER NOT NULL,  -- 1-4
    -- Momentum Features (4)
    rsi_14 DECIMAL(5, 2) NOT NULL,
    macd DECIMAL(10, 5) NOT NULL,
    macd_histogram DECIMAL(10, 5) NOT NULL,
    roc_10 DECIMAL(7, 4) NOT NULL,  -- Rate of Change 10
    -- Moving Average Features (5)
    close_sma_20_ratio DECIMAL(5, 3) NOT NULL,  -- close / sma20
    ema_9_21_diff DECIMAL(10, 5) NOT NULL,  -- ema9 - ema21
    sma_50_slope DECIMAL(7, 4) NOT NULL,  -- Inclinação SMA50
    price_above_bb_upper BOOLEAN NOT NULL,
    price_below_bb_lower BOOLEAN NOT NULL,
    -- Price Action Features (3)
    high_low_ratio DECIMAL(5, 3) NOT NULL,  -- high / low
    close_open_ratio DECIMAL(5, 3) NOT NULL,  -- close / open
    body_wick_ratio DECIMAL(5, 3) NOT NULL,  -- body / wick
    -- Lag Features (9) - últimas 3 velas
    lag1_close_change DECIMAL(7, 4) NOT NULL,
    lag1_volume_ma_20_ratio DECIMAL(5, 3) NOT NULL,
    lag2_rsi DECIMAL(5, 2) NOT NULL,
    lag3_macd DECIMAL(10, 5) NOT NULL,
    -- Correlation Features (2)
    corr_20_h1_m1 DECIMAL(5, 3) NOT NULL,  -- Correlação H1 vs M1
    trend_strength DECIMAL(5, 3) NOT NULL,  -- ADX-style
    -- Additional
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (timestamp, symbol),
    INDEX idx_timestamp_label (timestamp, label),
    INDEX idx_symbol (symbol)
);
```

---

## 4️⃣ CAMADA 4: Decisions & Signals (Decisões e Sinais) + AC3 Signal Tracking

### Arquitetura AC1→AC2→AC3 (Signal Lifecycle)

**AC1 (SignalGenerator):** Gera sinais com contexto de mercado
↓
**AC2 (SignalPersistence):** Persiste em `signals` table com outcome fields
↓
**AC3 (SignalTracker):** Rastreia ciclo de vida até outcome final (05/03/2026) ✅ IMPLEMENTED

### 4.1 Tabela: `signals` (AC1→AC2→AC3 Signal Lifecycle)

**Propósito:** Persistência + rastreamento completo de sinais desde geração até outcome final.

```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT UNIQUE NOT NULL,
    timestamp DATETIME NOT NULL,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    smc_score REAL NOT NULL,
    smc_detector TEXT NOT NULL,
    entry_price REAL NOT NULL,
    candle_index INTEGER,
    market_context_json TEXT,
    -- AC3: Signal Lifecycle Fields
    status TEXT DEFAULT 'OPEN',
    outcome_trade_id INTEGER,
    outcome_pnl REAL,
    outcome_days_open REAL,
    outcome_type TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME,

    FOREIGN KEY(outcome_trade_id) REFERENCES trades(id),
    CHECK(signal_type IN ('BUY', 'SELL')),
    CHECK(status IN ('OPEN', 'LINKED', 'CLOSED', 'WHIPSAW', 'MISSED')),
    CHECK(outcome_type IN ('WINNING_SIGNAL', 'LOSING_SIGNAL', 'BREAKEVEN_SIGNAL',
                           'WHIPSAW_SIGNAL', 'MISSED_SIGNAL', 'PARTIAL_SIGNAL', 'OPEN')),
    CHECK(smc_score >= -3.0 AND smc_score <= 3.0),
    UNIQUE(timestamp, symbol, signal_type)
);

CREATE INDEX idx_signals_timestamp ON signals(timestamp DESC);
CREATE INDEX idx_signals_symbol_timestamp ON signals(symbol, timestamp);
CREATE INDEX idx_signals_outcome_type ON signals(outcome_type);
CREATE INDEX idx_signals_status ON signals(status);
```

**AC3 Operations (SignalTracker):**
- `link_signal_to_trade()` - Vincula sinal a trade executada
- `update_signal_status()` - Atualiza status (OPEN→LINKED→CLOSED)
- `sync_from_db()` - Sincroniza com banco de dados
- `audit_signal_flow()` - Valida cadeia AC1→AC2→AC3
- `detect_orphaned()` - Identifica sinais sem persistência
- `get_tracking_stats()` - Estatísticas em tempo real

### 4.2 Tabela: `trading_signals` (Sinais Gerados)

**Propósito:** Registrar sinais gerados pelos modelos ML com confiança e
parâmetros técnicos.

**SQL Schema:**

```sql
CREATE TABLE trading_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,  -- "BUY", "SKIP", "NEUTRAL"
    ml_confidence DECIMAL(5, 2) NOT NULL,  -- 0-100%
    model_version VARCHAR(10) NOT NULL,  -- "v1.0", "v1.1", etc
    -- Confluence
    smc_m5_direction INTEGER,  -- 1: UP, -1: DOWN, 0: NEUTRAL
    smc_m1_direction INTEGER,
    smc_confluence_score DECIMAL(5, 2),  -- 0-100 if both agree
    atr_volatility_state VARCHAR(20),  -- LOW/NORMAL/HIGH/EXTREME
    score_t60_probability DECIMAL(5, 2),  -- T+60 direction prob
    -- Raw Features (snapshot for audit)
    features_json JSON,  -- Full feature vector as snapshot
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp_signal (timestamp, signal_type),
    INDEX idx_confidence (ml_confidence DESC)
);
```

---

### AC4: BDI Decision Filter (Decision Outcomes)

**AC4 (BDIDecisionFilter):** Avalia contexto BDI + aplica 3 gates de risco
↓
**AC5 (TradeExecutor):** Executa trades em MT5 (NEW - 03/03/2026) ✅ IMPLEMENTED

#### 4.3 Tabela: `bdi_decisions` (AC4 Decision Engine)

**Propósito:** Registrar decisões de AC4 com confiança e justificativa dos gates.

```sql
CREATE TABLE bdi_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT UNIQUE NOT NULL,
    signal_id TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    volatility_score REAL NOT NULL,
    macro_score REAL NOT NULL,
    drawdown_score REAL NOT NULL,
    decision_type TEXT NOT NULL,  -- EXECUTE, REJECT, HOLD
    confidence REAL NOT NULL,  -- 0.0-1.0
    gate1_passed BOOLEAN NOT NULL,  -- Volatilidade ≥ 75%
    gate2_passed BOOLEAN NOT NULL,  -- Macro ≥ 80%
    gate3_passed BOOLEAN NOT NULL,  -- Drawdown ≥ 85%
    justification TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(signal_id) REFERENCES signals(signal_id),
    CHECK(decision_type IN ('EXECUTE', 'REJECT', 'HOLD', 'CANCEL')),
    CHECK(confidence >= 0.0 AND confidence <= 1.0),
    INDEX idx_signal_decision (signal_id, timestamp),
    INDEX idx_decision_type (decision_type)
);
```

**AC4 Operations:**
- `get_signals_for_decision()` - Recupera sinais status OPEN/LINKED
- `evaluate_bdi_context()` - Análise volatilidade/padrões BDI
- `apply_risk_gates()` - Valida 3 gates (volatilidade, macro, drawdown)
- `make_decision()` - EXECUTE/REJECT com justificativa
- `get_decision_stats()` - Métricas agregadas (total, executed, rejected, avg_confidence)

---

### AC5: Trade Executor (Order Execution)

**AC5 (TradeExecutor):** Executa trades baseadas em AC4 EXECUTE decisions
↓
**Próximas Iterações:** Trade monitoring, ML feedback loop

#### 4.4 Tabela: `trades` (AC5 Trade Execution)

**Propósito:** Registrar trades executadas com especificação completa de SL/TP e
outcomes. Linkado a signals via outcome_trade_id.

```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT UNIQUE NOT NULL,
    signal_id TEXT NOT NULL,
    trade_id INTEGER UNIQUE NOT NULL,
    entry_price DECIMAL(10, 5) NOT NULL,
    stop_loss DECIMAL(10, 5) NOT NULL,
    take_profit DECIMAL(10, 5) NOT NULL,
    volume INTEGER NOT NULL,
    direction TEXT NOT NULL,  -- BUY, SELL
    order_type TEXT NOT NULL,  -- MARKET, LIMIT, STOP_MARKET
    status TEXT NOT NULL,  -- PENDING, SENT, FILLED, PARTIAL, CANCELLED, REJECTED
    execution_price DECIMAL(10, 5),
    execution_time DATETIME,
    exit_price DECIMAL(10, 5),
    exit_time DATETIME,
    pnl_realized DECIMAL(10, 5),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(signal_id) REFERENCES signals(signal_id),
    CHECK(direction IN ('BUY', 'SELL')),
    CHECK(order_type IN ('MARKET', 'LIMIT', 'STOP_MARKET')),
    CHECK(status IN ('PENDING', 'SENT', 'FILLED', 'PARTIAL', 'CANCELLED', 'REJECTED')),
    CHECK(volume >= 1 AND volume <= 10),
    INDEX idx_signal_trade (signal_id, trade_id),
    INDEX idx_status (status),
    INDEX idx_execution_time (execution_time)
);
```

**AC5 Operations:**
- `prepare_order_specification()` - Calcula SL = ATR*1.5, TP = ATR*3.0
- `validate_order()` - Checks volume (1-10), SL/TP positioning, risk-reward ≥1:2
- `send_order_to_broker()` - Envia para MT5 via ProcessadorBDI.enviar_ordem()
- `register_execution()` - Registra trade em BD, links signal_id → trade_id
- `execute_trade()` - Pipeline completo (prepare→validate→send→register)
- `get_execution_stats()` - Métricas (total_trades, open, closed, avg_pnl)

**Order Specification Details:**
- **SL/TP Calculation:** Baseado em ATR
  - BUY: SL = entry - 1.5×ATR, TP = entry + 3.0×ATR
  - SELL: SL = entry + 1.5×ATR, TP = entry - 3.0×ATR
- **Volume:** 1-10 (scaled position sizing)
- **Risk-Reward Ratio:** TP distance ≥ 2× SL distance (enforced validation)

---

### AC6: ML Feedback Loop (Learning Tables)

**AC6 (MLFeedbackLoop):** Correlaciona outcomes com sinais para retraining
↓
**Próximas Iterações:** Online learning, drift detection

#### 4.5 Tabela: `ml_feedback` (AC6 Signal Learning)

**Propósito:** Registrar linkage signal → outcome com signal strength metrics.

```sql
CREATE TABLE ml_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT NOT NULL,
    trade_id INTEGER,
    win_rate REAL,  -- % de trades winning
    avg_roi REAL,  -- ROI médio em %
    sharpe_ratio REAL,  -- Risco-adjusted return
    signal_strength TEXT,  -- VERY_WEAK, WEAK, NEUTRAL, STRONG, VERY_STRONG
    label_value REAL,  -- -1.0 (STRONG_SELL) to +1.0 (STRONG_BUY)
    label_confidence REAL,  -- 0.0-1.0
    feature_importance_json TEXT,  -- JSON com importance scores
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(signal_id) REFERENCES signals(signal_id),
    FOREIGN KEY(trade_id) REFERENCES trades(id),
    CHECK(signal_strength IN ('VERY_WEAK', 'WEAK', 'NEUTRAL', 'STRONG', 'VERY_STRONG')),
    CHECK(label_value >= -1.0 AND label_value <= 1.0),
    INDEX idx_signal_feedback (signal_id),
    INDEX idx_label_value (label_value DESC)
);
```

#### 4.6 Tabela: `model_iterations` (AC6 Model Versioning)

**Propósito:** Rastrear versões de modelo treinado com performance metrics.

```sql
CREATE TABLE model_iterations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_version TEXT UNIQUE NOT NULL,  -- v1.0, v1.1, v2.0, etc
    training_dataset_size INTEGER,  -- Número de samples usado
    validation_accuracy REAL,  -- 0.0-1.0
    f1_score REAL,  -- 0.0-1.0
    win_rate_backtest REAL,  -- % win rate em backtest
    sharpe_ratio REAL,  -- Risco-adjusted return
    is_production_ready BOOLEAN,
    released_at DATETIME,
    metrics_json TEXT,  -- Additional metrics as JSON
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    CHECK(validation_accuracy >= 0.0 AND validation_accuracy <= 1.0),
    CHECK(f1_score >= 0.0 AND f1_score <= 1.0),
    INDEX idx_model_version (model_version),
    INDEX idx_is_production (is_production_ready)
);
```

**AC6 Operations:**
- `correlate_signal_to_outcome()` - Link signal → trade outcome
- `calculate_signal_strength()` - Metrics: win_rate, ROI, Sharpe, drawdown
- `extract_feature_importance()` - Feature importance for model explanation
- `generate_training_label()` - Convert winning signals to labels
- `update_model_weights()` - Fine-tune model with feedback
- `get_learning_metrics()` - Aggregate KPIs for monitoring

---

## 5️⃣ CAMADA 5: Execution & Auditoria (Execução e Auditoria)

### 5.1 Tabela: `decision_audit_atr` (Auditoria ATR - S2-2)

**Propósito:** Registrar cada decisão incluindo parâmetros ATR usados para
ajuste de trailing stop e volume.

**SQL Schema:**

```sql
CREATE TABLE decision_audit_atr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    signal_id INTEGER NOT NULL FK REFERENCES trading_signals(id),
    -- ATR Parameters Used
    atr_raw_value DECIMAL(10, 5) NOT NULL,  -- ATR calculado naquele momento
    atr_zscore DECIMAL(5, 3) NOT NULL,
    volatility_state VARCHAR(20) NOT NULL,  -- LOW/NORMAL/HIGH/EXTREME
    -- Calibrator Outputs
    trailing_stop_calculated DECIMAL(10, 5) NOT NULL,  -- ATR * multiplier
    volume_suggested INTEGER NOT NULL,  -- 1-10 contratos
    trailing_stop_min DECIMAL(10, 5) NOT NULL,  -- min imposto pelo calibrador
    trailing_stop_max DECIMAL(10, 5) NOT NULL,  -- max imposto pelo calibrador
    -- Decision
    decision_made VARCHAR(20) NOT NULL,  -- "EXECUTE", "REJECT", "HOLD"
    decision_reason VARCHAR(200),  -- Motivo se rejected
    -- Execution Status
    executed BOOLEAN DEFAULT FALSE,
    execution_timestamp DATETIME,  -- quando foi executado
    actual_trailing_stop DECIMAL(10, 5),  -- o que foi realmente usado em MT5
    actual_volume INTEGER,  -- o que foi realmente enviado
    mt5_order_id INTEGER,  -- referência do lado MT5
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_signal_id (signal_id),
    INDEX idx_timestamp_executed (timestamp, executed)
);
```

**Exemplos:**

| timestamp | atr_value | trailing_stop_calc | volume_sug | decision | executed | mt5_order_id |
|-----------|-----------|-------------------|-----------|----------|----------|-------------|
| 2026-02-27 14:30:15 | 125.50 | 251.00 | 2 | EXECUTE | TRUE | 1048576 |
| 2026-02-27 14:35:30 | 280.75 | 400.00 | 1 | EXECUTE | TRUE | 1048577 |
| 2026-02-27 15:00:00 | 380.90 | 400.00 | 1 | REJECT | FALSE | NULL |

---

### 5.2 Tabela: `mt5_orders` (Ordens Executadas)

**Propósito:** Espelho de todas as ordens enviadas ao MT5 e seus resultados.

**SQL Schema:**

```sql
CREATE TABLE mt5_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mt5_order_id INTEGER UNIQUE NOT NULL,  -- Ticket MT5
    decision_audit_id INTEGER FK REFERENCES decision_audit_atr(id),
    -- Order Details
    timestamp_sent DATETIME NOT NULL,
    symbol VARCHAR(10) NOT NULL,  -- "WINFUT"
    order_type VARCHAR(20) NOT NULL,  -- "BUY", "SELL"
    volume INTEGER NOT NULL,  -- Qty de contratos
    entry_price DECIMAL(10, 5),  -- Preço de entrada (market order = NULL aqui)
    stop_loss DECIMAL(10, 5) NOT NULL,  -- Stop configurado
    take_profit DECIMAL(10, 5) NOT NULL,  -- TP configurado
    trailing_stop DECIMAL(10, 5),  -- Trailing configurado (ATR-based)
    -- Status
    status VARCHAR(20) NOT NULL,  -- "PENDING", "OPEN", "CLOSED", "ERROR"
    error_message VARCHAR(200),
    timestamp_filled DATETIME,
    filled_price DECIMAL(10, 5),  -- Preço real de preenchimento
    timestamp_closed DATETIME,
    close_price DECIMAL(10, 5),  -- Preço de fechamento
    profit_loss DECIMAL(10, 2),  -- P&L em pontos
    profit_loss_percent DECIMAL(5, 2),  -- P&L %
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_mt5_id (mt5_order_id),
    INDEX idx_timestamp_status (timestamp_sent, status)
);
```

---

### 5.3 Tabela: `operation_audit` (Auditoria Completa de Operações)

**Propósito:** Registro completo de cada operação para compliance (CVM/B3).

**SQL Schema:**

```sql
CREATE TABLE operation_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Rastreabilidade
    operation_id UUID UNIQUE NOT NULL,  -- UUID único
    timestamp_decision DATETIME NOT NULL,  -- Quando decidimos
    timestamp_execution DATETIME,  -- Quando executamos
    -- Referências
    signal_id INTEGER FK REFERENCES trading_signals(id),
    decision_audit_id INTEGER FK REFERENCES decision_audit_atr(id),
    mt5_order_id INTEGER FK REFERENCES mt5_orders(mt5_order_id),
    -- Details (snapshot)
    symbol VARCHAR(10) NOT NULL,
    account_balance DECIMAL(15, 2),  -- Balanço antes da op
    risk_percent DECIMAL(5, 2),  -- % de risco calculado
    -- Compliance
    trader_approval_required BOOLEAN DEFAULT FALSE,
    trader_approval_timestamp DATETIME,
    trader_override_active BOOLEAN DEFAULT FALSE,
    circuit_breaker_state VARCHAR(20),  -- "GREEN", "YELLOW", "RED", "HALT"
    -- Result
    final_status VARCHAR(20) NOT NULL,  -- "SUCCESS", "REJECTED", "ERROR"
    error_code VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_operation_id (operation_id),
    INDEX idx_timestamp (timestamp_decision)
);
```

---

## 📊 Relacionamentos (ER Diagram)

```
┌─────────────────────┐
│  market_candles     │
│ (M1, M5 data)       │
└──────────┬──────────┘
           │
           ├──→ ┌────────────────────────┐
           │    │  atr_historical (S2-2) │
           │    │ (ATR + Vol State)      │
           │    └────────┬───────────────┘
           │             │
           ├──→ ┌────────────────────────┐
           │    │technical_indicators    │
           │    │(RSI, MACD, etc)        │
           │    └────────┬───────────────┘
           │             │
           ├──→ ┌────────────────────────┐
           │    │    ml_features         │
           │    │  (24+ engineered)      │
           │    └────────┬───────────────┘
           │             │
           └─────────────┼────────────────┐
                         │                 │
              ┌──────────▼──────────┐     │
              │ trading_signals     │     │
              │ (ML predictions)    │     │
              └─────────┬───────────┘     │
                        │                 │
              ┌─────────▼────────────────┐│
              │ decision_audit_atr (S2-2)││
              │ (Trailing Stop, Vol)     ││
              └──┬────────────────────────┘│
                 │                         │
        ┌────────▼──────────┐   ┌─────────▼────────┐
        │  mt5_orders       │   │operation_audit   │
        │(Executed orders)  │   │(Compliance CVM)  │
        └───────────────────┘   └──────────────────┘
```

---

## 🔄 Fluxo de Dados

1. **Captura:** MT5 → `market_candles` (M1, M5)
2. **Cálculo:** `market_candles` → `atr_historical` + `technical_indicators`
3. **Features:** `atr_historical` + `technical_indicators` → `ml_features`
4. **Previsão:** `ml_features` → `trading_signals` (via ML model)
5. **Decisão:** `trading_signals` + `atr_historical` → `decision_audit_atr` (ATR calibration)
6. **Execução:** `decision_audit_atr` → `mt5_orders` (via MT5 API)
7. **Auditoria:** Todos → `operation_audit` (compliance trail)

---

## 🎯 Integrações Obrigatórias

| Documento | Sincronização |
|-----------|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Especifica camadas; DATA_MODELS implementa |
| [SQUAD_S2-2_ATR_DINAMICO.md](SQUAD_S2-2_ATR_DINAMICO.md) | Task 2.1 cria este documento |
| [STATUS_ENTREGAS.md](STATUS_ENTREGAS.md) | Referencia S2-2, seção "Decision Audit" |
| [ROADMAP.md](ROADMAP.md) | Oportunidade 19 (ATR) mapeia para esta estrutura |

---

## 🔐 Constraints & Índices Críticos

```sql
-- FOREIGN KEYS
ALTER TABLE decision_audit_atr ADD CONSTRAINT fk_signal_id
  FOREIGN KEY (signal_id) REFERENCES trading_signals(id);

ALTER TABLE mt5_orders ADD CONSTRAINT fk_decision_audit
  FOREIGN KEY (decision_audit_id) REFERENCES decision_audit_atr(id);

ALTER TABLE operation_audit ADD CONSTRAINT fk_audit_atr
  FOREIGN KEY (decision_audit_id) REFERENCES decision_audit_atr(id);

-- ÍNDICES DE PERFORMANCE
CREATE INDEX idx_atr_timestamp_volatility
  ON atr_historical(timestamp, volatility_state);

CREATE INDEX idx_decision_audit_executed
  ON decision_audit_atr(timestamp, executed);

CREATE INDEX idx_mt5_orders_status
  ON mt5_orders(timestamp_sent, status);

CREATE INDEX idx_operation_audit_timestamp
  ON operation_audit(timestamp_decision, final_status);
```

---

## 📝 Notas de Implementação

1. **Timestamps:** Sempre DATETIME com UTC timezone para consistência
2. **Decimals:** DECIMAL(10,5) para preços/ATR, DECIMAL(5,2) para percentuais
3. **UUIDs:** `operation_id` deve ser UUID para rastreabilidade global
4. **JSON Fields:** `features_json` armazena snapshot completo de features para auditoria
5. **Performance:** Todos os índices são critical para queries de tempo real
6. **Backup:** `operation_audit` é a tabela master para compliance

---

**Última Atualização:** 03/03/2026 (Sincronização com MODELAGEM_DADOS.md, DIAGRAMA_DADOS.md, REGRAS_NEGOCIO.md)
**Próximo Review:** Após implementação em P35 (06/03)

---

## P50: Data Models Pessimism Detection & Auto-Recovery

### Modelo: ConfidenceScore

**Propósito:** Representar valor de confiança e tendências associadas

```python
@dataclass
class ConfidenceScore:
    """Score de confiança do sistema com histórico de tendências"""

    value: float  # 0.0 to 1.0
    timestamp: datetime
    cycle_number: int
    win_rate_recent: float  # 0.0 to 1.0
    predictions_count: int
    correct_predictions: int

    @property
    def is_pessimistic(self) -> bool:
        """Retorna True se confiança está abaixo do threshold crítico (0.45)"""
        return self.value < 0.45

    @property
    def trend(self) -> str:
        """Tendência: 'declining', 'stable', 'improving'"""
        # Calculado comparando com ciclos anteriores
        pass
```

### Modelo: PessimismDetectionResult

**Propósito:** Resultado da análise de detecção de pessimismo

```python
@dataclass
class PessimismDetectionResult:
    """Resultado da detecção de pessimismo do sistema"""

    pessimism_detected: bool
    confidence_current: float
    confidence_threshold: float
    consecutive_low_cycles: int
    trigger_action: str  # 'none', 'alert', 'reset', 'retrain'
    adjustment_reason: str
    reset_strategy: str  # 'gradual', 'aggressive', 'conservative'
    affected_thresholds: Dict[str, float]  # Original vs adjusted

    @property
    def severity(self) -> str:
        """Severidade: 'low', 'medium', 'high', 'critical'"""
        if self.consecutive_low_cycles < 5:
            return 'low'
        elif self.consecutive_low_cycles < 10:
            return 'medium'
        elif self.consecutive_low_cycles < 15:
            return 'high'
        else:
            return 'critical'
```

### Modelo: FeedbackEvent

**Propósito:** Evento de feedback para retraining e logging

```python
@dataclass
class FeedbackEvent:
    """Evento de feedback do sistema (correto/incorreto) com contexto"""

    event_id: str  # UUID
    timestamp: datetime
    cycle_number: int
    prediction_id: str  # Referência à predição
    actual_outcome: bool  # True = correto, False = incorreto
    confidence_when_predicted: float
    market_type: str  # 'normal', 'volatile', 'trending'
    volatility_level: str  # 'low', 'standard', 'high'

    features_snapshot: Dict[str, float]  # Features usadas na predição
    feedback_trigger: str  # 'realtime', 'end_of_day', 'manual'

    @property
    def contribution_to_learning(self) -> float:
        """Peso deste feedback para retraining (0.0-1.0)"""
        # Eventos em mercado volatível > eventos em mercado normal
        # Eventos recentes > eventos antigos
        pass
```

### Modelo: RetrainingMetrics

**Propósito:** Métricas calculadas para decisão de retraining

```python
@dataclass
class RetrainingMetrics:
    """Métricas para decisão de retraining automático"""

    window_size: int  # Últimos N ciclos (default: 20)
    win_rate: float  # Taxa de acerto (0.0-1.0)
    f1_score: float  # F1 score do período (0.0-1.0)
    confidence_degradation: float  # -0.15 = degradou 15%
    prediction_consistency: float  # Variância em threshold
    drift_detected: bool  # Se houve mudança no mercado

    recommendation: str  # 'none', 'alert', 'retrain', 'retrain_forced'

    @property
    def should_retrain(self) -> bool:
        """Retorna True se métricas indicam necessidade de retraining"""
        return (
            self.win_rate < 0.60 or
            self.f1_score < 0.65 or
            self.confidence_degradation < -0.10 or
            self.drift_detected
        )
```

**Mapeamento para Banco de Dados:**
- `ConfidenceScore` → `CONFIDENCE_HEALTH` (SQLite: data/db/trading.db)
- `PessimismDetectionResult` → `PESSIMISM_MODE` (JSON: config/pessimism_mode.json)
- `FeedbackEvent` → `FEEDBACK_LOGS` (potencial futura tabela)
- `RetrainingMetrics` → `CONFIDENCE_HISTORY` (JSON: config/confidence_history.json)

---

## 🔗 Referências Cruzadas

### Relacionamento com Outros Documentos

- **MODELAGEM_DADOS.md**: Contém DDL SQL completo para todas as tabelas descritas aqui
- **DIAGRAMA_DADOS.md**: Contém ER diagram visual mostrando relacionamentos entre entidades
- **ARCHITECTURE.md**: Contém contexto geral de como dados fluem no sistema
- **REGRAS_NEGOCIO.md**: Contém validações que devem ser aplicadas aos dados
- **DIAGRAMA_CLASSES.md**: Contém classes que acessam esses modelos

### Tipos de Teste Relacionados

Para validar integridade dos data models:
1. **Unit Tests**: Validar constraints em código (ver CODING_STANDARDS.md)
2. **Integration Tests**: Validar relacionamentos entre tabelas (FK constraints)
3. **Schema Tests**: Validar DDL contra MODELAGEM_DADOS.md
4. **Data Quality Tests**: Validar regras em REGRAS_NEGOCIO.md

Ver [CONTRIBUTING.md](CONTRIBUTING.md) para padrão de testes.
