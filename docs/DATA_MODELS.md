# 📊 Data Models - Operador Day Trade WIN

**Versão:** 1.0.1
**Data Criação:** 27/02/2026
**Última Atualização:** 03/03/2026
**Responsável:** Data Engineer + Arquiteto de Sistemas
**Sincronização:** [ARCHITECTURE.md](ARCHITECTURE.md) | [MODELAGEM_DADOS.md](MODELAGEM_DADOS.md) | [DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md)
**Status:** ✅ Sincronizado com 5 documentos arquiteturais

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

## 4️⃣ CAMADA 4: Decisions & Signals (Decisões e Sinais)

### 4.1 Tabela: `trading_signals` (Sinais Gerados)

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
