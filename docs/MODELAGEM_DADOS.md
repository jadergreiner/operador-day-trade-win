# Modelagem de Dados - Operador Day Trade WIN

**Data**: 03/03/2026
**Status**: ✅ COMPLETO
**Referência**: [ARCHITECTURE.md](ARCHITECTURE.md) | [DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md) | [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md)

---

## 📊 Database Configuration

**Banco Primário**: SQLite
**Localização**: `data/db/trading.db`
**Versão**: SQLite 3.x
**Encoding**: UTF-8
**Timezone**: America/Sao_Paulo (BRT -3)
**Backup**: Diário em `data/backups/`

---

## 🗂️ Schema DDL (Data Definition Language)

### Tabela 1: MARKET_DATA

```sql
CREATE TABLE market_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL,
    spread REAL NOT NULL DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(symbol, timestamp),
    CHECK(high >= open AND high >= close),
    CHECK(low <= open AND low <= close),
    CHECK(close >= 0.0),
    CHECK(volume >= 0)
);

CREATE INDEX idx_market_data_symbol_timestamp ON market_data(symbol, timestamp);
CREATE INDEX idx_market_data_timestamp_desc ON market_data(timestamp DESC);
```

**Campos**:
- `id`: PK, auto-increment
- `symbol`: Código do ativo (e.g., "WIN", "WDO")
- `timestamp`: Data/hora do candle (formato ISO 8601)
- `open/high/low/close`: Preços em REAL (almacener com 2 casas decimais)
- `volume`: Número de contratos (INTEGER)
- `spread`: Diferença bid-ask em pontos
- `created_at`: Timestamp quando inserido (auditoria)

**Constraints**:
- UNIQUE(symbol, timestamp): Um candle por símbolo por timestamp
- CHECK: Validações de integridade (high ≥ open, etc)

**Índices**:
- Por (symbol, timestamp): Queries por símbolo em período
- Por timestamp DESC: Últimos candles consultados rapidamente

---

### Tabela 2: FEATURES

```sql
CREATE TABLE features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_data_id INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    symbol TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    feature_value REAL NOT NULL,
    feature_group TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(market_data_id) REFERENCES market_data(id),
    UNIQUE(market_data_id, feature_name),
    CHECK(feature_value >= -999999 AND feature_value <= 999999)
);

CREATE INDEX idx_features_symbol_timestamp ON features(symbol, timestamp);
CREATE INDEX idx_features_market_data_id ON features(market_data_id);
CREATE INDEX idx_features_name ON features(feature_name);
```

**Campos**:
- `id`: PK
- `market_data_id`: FK para MARKET_DATA (cada feature vem de um candle)
- `timestamp`: Quando a feature foi calculada
- `symbol`: Código do ativo
- `feature_name`: Nome da feature (e.g., "rsi", "macd", "bollinger_upper")
- `feature_value`: Valor numérico da feature
- `feature_group`: Grupo da feature ("volatility", "momentum", "ma", "pattern", "lag", "correlation")

**Constraints**:
- UNIQUE(market_data_id, feature_name): Uma feature por tipo por candle
- FK market_data_id: Integridade referencial

**Índices**:
- Por (symbol, timestamp): Consultá-lo todas as features de um símbolo em período
- Por market_data_id: FK lookup
- Por feature_name: Queries por tipo de feature

---

### Tabela 3: PREDICTIONS

```sql
CREATE TABLE predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    model_name TEXT NOT NULL,
    prediction_type TEXT NOT NULL,
    predicted_value REAL NOT NULL,
    confidence_score REAL NOT NULL,
    actual_value REAL,
    direction TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,

    CHECK(confidence_score >= 0.0 AND confidence_score <= 1.0),
    CHECK(direction IN ('BUY', 'SELL', 'HOLD')),
    CHECK(status IN ('PENDING', 'VALIDADO', 'REJECTED', 'EXPIRED'))
);

CREATE INDEX idx_predictions_model_timestamp ON predictions(model_name, timestamp);
CREATE INDEX idx_predictions_direction ON predictions(direction);
CREATE INDEX idx_predictions_status ON predictions(status, timestamp);
```

**Campos**:
- `id`: PK
- `timestamp`: Quando a previsão foi feita
- `model_name`: Nome do modelo (e.g., "XGBoost v1.2", "LGBM", "Ensemble")
- `prediction_type`: Tipo ("classification", "regression", "volatility")
- `predicted_value`: Valor predito
- `confidence_score`: [0.0, 1.0] confiança da previsão
- `actual_value`: Valor real após a previsão (preenchido após validação)
- `direction`: Direção da previsão (BUY, SELL, HOLD)
- `status`: Estado da previsão (PENDING, VALIDADO, REJECTED, EXPIRED)
- `updated_at`: Quando status mudou

**Constraints**:
- confidence_score entre 0 e 1
- direction em enum list
- status em enum list

---

### Tabela 4: DECISIONS

```sql
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    decision_type TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    signals_used TEXT,
    risk_score REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    decision_reason TEXT,
    predictions_summary TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,

    CHECK(risk_score >= 0.0 AND risk_score <= 1.0),
    CHECK(decision_type IN ('BUY', 'SELL', 'HOLD')),
    CHECK(status IN ('PENDING', 'VALIDATING', 'APPROVED', 'REJECTED'))
);

CREATE INDEX idx_decisions_status ON decisions(status, timestamp);
CREATE INDEX idx_decisions_decision_type ON decisions(decision_type);
```

**Campos**:
- `id`: PK
- `timestamp`: Quando a decisão foi tomada
- `decision_type`: BUY, SELL, HOLD
- `reasoning`: Justificativa textual (e.g., "SMC confluence detected + ML confidence > 0.75")
- `signals_used`: Sinais combinados (JSON ou semicolon-separated)
- `risk_score`: Score de risco [0.0, 1.0] (quanto maior, mais risco)
- `status`: Estado da decisão
- `decision_reason`: Razão da rejeição (se rejeitada)
- `predictions_summary`: JSON com previsões que suportaram a decisão

---

### Tabela 5: TRADES

```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    broker_trade_id TEXT NOT NULL UNIQUE,
    decisions_id INTEGER NOT NULL,
    timestamp_entry DATETIME NOT NULL,
    timestamp_exit DATETIME,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL,
    stop_loss REAL NOT NULL,
    take_profit REAL NOT NULL,
    volume REAL NOT NULL,
    pnl REAL,
    pnl_percent REAL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    detector_spike REAL,
    ml_classifier_score REAL,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,

    FOREIGN KEY(decisions_id) REFERENCES decisions(id),
    CHECK(side IN ('BUY', 'SELL')),
    CHECK(status IN ('OPEN', 'CLOSED', 'CANCELLED')),
    CHECK(quantity > 0),
    CHECK(entry_price > 0),
    CHECK(pnl_percent >= -100 AND pnl_percent <= 10000)
);

CREATE INDEX idx_trades_symbol_timestamp ON trades(symbol, timestamp_entry);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_broker_id ON trades(broker_trade_id);
CREATE INDEX idx_trades_decisions_id ON trades(decisions_id);
```

**Campos**:
- `id`: PK
- `broker_trade_id`: Ticket único do MT5 (e.g., "12345678")
- `decisions_id`: FK para DECISIONS (qual decisão levou ao trade)
- `timestamp_entry`: Quando o trade foi executado
- `timestamp_exit`: Quando foi fechado
- `symbol`: Código do ativo (WIN, WDO, etc)
- `side`: BUY ou SELL
- `quantity`: Número de contratos
- `entry_price`: Preço de entrada
- `exit_price`: Preço de saída
- `stop_loss`: SL
- `take_profit`: TP
- `pnl`: Lucro/Prejuízo em reais
- `pnl_percent`: Lucro/Prejuízo em percentual
- `status`: OPEN, CLOSED, CANCELLED
- `detector_spike`: Valor do detector (e.g., 2.5σ)
- `ml_classifier_score`: Score do ML classifier
- `notes`: Anotações (detector info, motivo rejeição, etc)

**Constraints**:
- UNIQUE broker_trade_id: Não há duplicatas MT5
- FK decisions_id: Toda trade tem decisão
- CHECK side, status, quantity, pnl_percent: Validações

---

### Tabela 6: POSITIONS

```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trades_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    timestamp_open DATETIME NOT NULL,
    timestamp_close DATETIME,
    current_price REAL NOT NULL,
    pnl REAL NOT NULL,
    pnl_percent REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,

    FOREIGN KEY(trades_id) REFERENCES trades(id),
    CHECK(side IN ('BUY', 'SELL')),
    CHECK(status IN ('OPEN', 'CLOSED', 'PENDING')),
    UNIQUE(symbol, status)
);

CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_trades_id ON positions(trades_id);
```

**Campos**:
- `id`: PK
- `trades_id`: FK para TRADES
- `symbol`: Código do ativo
- `side`: BUY ou SELL
- `quantity`: Quantidade
- `entry_price`: Preço de entrada
- `timestamp_open`: Quando abriu
- `timestamp_close`: Quando fechou
- `current_price`: Preço atual (atualizado em tempo real)
- `pnl`: P&L não realizado
- `pnl_percent`: P&L %
- `status`: OPEN, CLOSED, PENDING

**Nota**: UNIQUE(symbol, status) garante que com uma posição OPEN por símbolo no máximo

---

### Tabela 7: PERFORMANCE

```sql
CREATE TABLE performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL UNIQUE,
    session_balance REAL NOT NULL,
    session_equity REAL NOT NULL,
    profit_loss REAL NOT NULL,
    profit_loss_percent REAL NOT NULL,
    drawdown REAL NOT NULL,
    drawdown_percent REAL NOT NULL,
    win_rate REAL NOT NULL,
    sharpe_ratio REAL NOT NULL,
    max_consecutive_wins INTEGER NOT NULL,
    total_trades INTEGER NOT NULL,
    total_wins INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    CHECK(win_rate >= 0.0 AND win_rate <= 100.0),
    CHECK(session_balance > 0),
    CHECK(total_trades >= 0)
);

CREATE INDEX idx_performance_timestamp ON performance(timestamp DESC);
```

**Campos**:
- `timestamp`: Hora do snapshot (UNIQUE por timestamp)
- `session_balance`: Saldo atual
- `session_equity`: Patrimônio (balance + open positions P&L)
- `profit_loss`: Lucro/Prejuízo em reais
- `profit_loss_percent`: LP em %
- `drawdown`: Máxima queda (em reais)
- `drawdown_percent`: Máxima queda em %
- `win_rate`: % de trades vencedores
- `sharpe_ratio`: Métrica de risco-retorno
- `max_consecutive_wins`: Maior sequência de ganhos
- `total_trades`: Total de trades no período
- `total_wins`: Total de trades vencedores

---

### Tabela 8: RL_EPISODES

```sql
CREATE TABLE rl_episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trades_id INTEGER,
    timestamp DATETIME NOT NULL,
    episode_number INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    state TEXT NOT NULL,
    action TEXT NOT NULL,
    reward REAL NOT NULL,
    next_state TEXT NOT NULL,
    done BOOLEAN NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(trades_id) REFERENCES trades(id),
    CHECK(done IN (0, 1))
);

CREATE INDEX idx_rl_episodes_symbol ON rl_episodes(symbol);
CREATE INDEX idx_rl_episodes_trades_id ON rl_episodes(trades_id);
```

**Campos**:
- `id`: PK
- `trades_id`: FK para TRADES (opcional, pode ter episodes fora de trades)
- `timestamp`: Quando o episode ocorreu
- `episode_number`: Número sequencial (para replay no RL)
- `symbol`: Código do ativo
- `state`: Estado codificado (JSON com features)
- `action`: Ação tomada (HOLD, BUY, SELL)
- `reward`: Reward do RL (obtido após próximo step)
- `next_state`: Estado seguinte
- `done`: Se episode terminou (1) ou continua (0)

---

### Tabela 9: RL_REWARDS

```sql
CREATE TABLE rl_rewards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rl_episodes_id INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    reward_value REAL NOT NULL,
    cumulative_reward REAL NOT NULL,
    reward_type TEXT NOT NULL,
    reasoning TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(rl_episodes_id) REFERENCES rl_episodes(id),
    CHECK(reward_type IN ('price_up', 'price_down', 'hold', 'penalty', 'terminal'))
);

CREATE INDEX idx_rl_rewards_episode_id ON rl_rewards(rl_episodes_id);
```

**Campos**:
- `id`: PK
- `rl_episodes_id`: FK para RL_EPISODES
- `timestamp`: Quando o reward foi calculado
- `reward_value`: Valor do reward (pode ser negativo para penalties)
- `cumulative_reward`: Soma de rewards até este ponto
- `reward_type`: Tipo de reward
- `reasoning`: Explicação

---

### Tabela 10: AUDIT_LOG

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    action TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    user TEXT NOT NULL DEFAULT 'SYSTEM',
    ip_address TEXT,
    trades_id INTEGER,
    decisions_id INTEGER,
    positions_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    CHECK(action IN ('INSERT', 'UPDATE', 'DELETE', 'APPROVE', 'REJECT')),
    CHECK(entity_type IN ('TRADE', 'DECISION', 'POSITION', 'PREDICTION', 'ORDER'))
);

CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_trades_id ON audit_log(trades_id);
```

**Campos**:
- `id`: PK
- `timestamp`: Quando a mudança ocorreu
- `entity_type`: Tipo de entidade modificada
- `entity_id`: ID da entidade
- `action`: INSERT, UPDATE, DELETE, APPROVE, REJECT
- `old_value`: Valor anterior (JSON se objeto)
- `new_value`: Novo valor (JSON se objeto)
- `user`: Usuário que fez a mudança
- `ip_address`: IP de origem (para web requests)
- Foreign keys para rastrear mudanças específicas

---

## 🔄 Views Úteis (Lógica Reutilizável)

```sql
-- View: Trades recentes com decision info
CREATE VIEW v_trades_with_decisions AS
SELECT
    t.id,
    t.broker_trade_id,
    t.timestamp_entry,
    t.symbol,
    t.side,
    t.entry_price,
    t.pnl,
    t.pnl_percent,
    t.status,
    d.decision_type,
    d.risk_score,
    d.reasoning
FROM trades t
LEFT JOIN decisions d ON t.decisions_id = d.id
WHERE t.timestamp_entry > datetime('now', '-1 day');

-- View: P&L diário agregado
CREATE VIEW v_daily_pnl AS
SELECT
    date(timestamp_entry) as trade_date,
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(SUM(pnl), 2) as daily_pnl,
    ROUND(AVG(pnl_percent), 2) as avg_pnl_percent
FROM trades
WHERE status = 'CLOSED'
GROUP BY date(timestamp_entry);

-- View: Open positions com P&L
CREATE VIEW v_open_positions AS
SELECT
    p.id,
    p.symbol,
    p.side,
    p.quantity,
    p.entry_price,
    p.current_price,
    ROUND(p.pnl, 2) as pnl,
    ROUND(p.pnl_percent, 2) as pnl_percent,
    (p.current_price - p.entry_price) * p.quantity as exposure
FROM positions
WHERE status = 'OPEN'
ORDER BY p.symbol;
```

---

## 📝 Triggers (Automação)

```sql
-- Trigger: Atualizar updated_at em trades
CREATE TRIGGER tr_trades_updated_at
AFTER UPDATE ON trades
FOR EACH ROW
BEGIN
    UPDATE trades SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Trigger: Log em audit_log quando trade é criada
CREATE TRIGGER tr_audit_trade_insert
AFTER INSERT ON trades
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (timestamp, entity_type, entity_id, action, new_value, user)
    VALUES (CURRENT_TIMESTAMP, 'TRADE', NEW.id, 'INSERT', json_object('broker_id', NEW.broker_trade_id), 'SYSTEM');
END;

-- Trigger: Validar que SL < entry < TP
CREATE TRIGGER tr_validate_sl_tp
BEFORE INSERT ON trades
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Invalid SL/TP: SL must be < entry < TP for long positions')
    WHERE NEW.side = 'BUY' AND (NEW.stop_loss >= NEW.entry_price OR NEW.entry_price >= NEW.take_profit);
END;
```

---

## 🔗 Documentos Relacionados

- [DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md) - ER diagram visual
- [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md) - Regras que governam os dados
- [ARCHITECTURE.md](ARCHITECTURE.md) - Arquitetura geral

---

**ÚLTIMA ATUALIZAÇÃO:** 03/03/2026 | **STATUS**: ✅ COMPLETO
