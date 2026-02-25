<!-- pyml disable md013 -->
<!-- pyml disable md040 -->

# Arquitetura do Sistema - Operador Quantitativo WIN

## Visão Geral

Sistema de trading quantitativo para Mini Índice Brasileiro (WIN) com arquitetura em camadas, integrando análise de machine learning, decisão automatizada e execução via MetaTrader 5.

## Princípios Arquiteturais

1. **Separation of Concerns**: Cada camada tem responsabilidade única e bem definida
2. **Event-Driven Architecture**: Comunicação assíncrona entre módulos
3. **Domain-Driven Design**: Modelagem centrada no domínio financeiro
4. **SOLID Principles**: Código modular, extensível e testável
5. **Observability First**: Logging, métricas e auditoria em todas as camadas
6. **🔴 CRITICAL - Confirmation Closure Principle** ⭐ NEW
   - **Toda operação crítica DEVE ter ciclo fechado:**
     1. Request Layer (envio para MT5)
     2. Confirmation Layer (escuta e persiste resposta)
     3. Verification Layer (valida 1:1 mapping)
     4. Feedback Layer (notifica sistema de aprendizado)
   - **Sem qualquer uma dessas 4 camadas, o ciclo não está fechado**
   - ⚠️ **Status (24/02):** Camadas 1 implantada, 2-4 FALTANDO (veja P0-CAUSA_RAIZ_DADOS_DESAPARECIDOS.md)

## Arquitetura em Camadas

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                       │
│                   (Dashboard, Monitoring)                    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      DECISION LAYER                          │
│              (AI Head Financeiro - Decisor)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Risk Manager │  │ Portfolio Mgr│  │ Order Manager│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     ANALYSIS LAYER                           │
│           (Modelos de ML e Análise Técnica)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ML Models    │  │ Technical    │  │ Forecast     │      │
│  │ (Prediction) │  │ Indicators   │  │ Engine       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      DATA LAYER                              │
│          (Captura, Transformação e Persistência)             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ MT5 Adapter  │  │ Data Pipeline│  │ Repository   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ MetaTrader 5 │  │ SQLite DB    │  │ File System  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Componentes Principais

### 1. Data Layer (Camada de Dados)

**Responsabilidade**: Captura, transformação e persistência de dados de mercado em tempo real.

**Componentes**:
- **MT5Adapter**: Interface com MetaTrader 5 para captura de dados
- **DataPipeline**: Processamento, limpeza e normalização de dados
- **Repository Pattern**: Abstração de persistência
- **Cache Layer**: Redis/Memória para dados em tempo real

**Tecnologias**: MetaTrader5 Python API, SQLite, pandas

### 2. Analysis Layer (Camada de Análise)

**Responsabilidade**: Análise técnica, modelos preditivos e geração de sinais.

**Componentes**:
- **ML Models**:
  - Modelo de Classificação (Bull/Bear/Neutro)
  - Modelo de Regressão (Previsão de Preço)
  - Modelo de Volatilidade
  - Ensemble (combinação de modelos)
- **SMC Confluence Engine (S2-3)**: Motor de confluência de Smart Money Concepts
  entre M1 e M5. Identifica zonas de Supply/Demand e Support/Resistance baseadas
  em cálculo real de Swing High/Low para sinais de "Convicção Máxima".
- **Score T+60 (S2-5)**: Modelo de previsão direcional para 1h (T+60) usando
  XGBoost com 25 features M1. Adiciona confluência de curto prazo aos sinais SMC.
  Implementado em: `scripts/score_t60_builder.py`, `score_t60_train.py`,
  `score_t60_inference.py`, `score_t60_backtest.py`. Output: `~/.operador_score_t60.json`.
- **Technical Indicators**: RSI, MACD, Bollinger, Volume Profile
- **Forecast Engine**: Previsões de curto, médio prazo
- **Feature Engineering**: Criação de features para ML

**Tecnologias**: scikit-learn, XGBoost, LightGBM, TensorFlow/PyTorch, TA-Lib

### 3. Decision Layer (Camada de Decisão)

**Responsabilidade**: Tomada de decisão inteligente baseada em análises e gestão de risco.

**Componentes**:
- **AI Head Financeiro**: Motor de decisão principal (LLM-augmented)
- **ATRCalibrator**: Calibrador dinâmico de volatilidade (S2-2). Ajusta Trailing Stop e Ticket Size baseado no ATR de 15 minutos.
- **Risk Manager**:
  - Stop Loss dinâmico
  - Position Sizing
  - Exposure Control
  - Drawdown Management
- **Portfolio Manager**: Gestão de capital e alocação
- **Order Manager**: Gestão de ordens e execução

**Tecnologias**: Python, Event-driven patterns

### 4. Execution Layer (Camada de Execução)

**Responsabilidade**: Execução de ordens no MetaTrader 5 e gestão de posições com
isolamento obrigatório de terminal.

**Componentes**:
- **MT5 Terminal Isolation (S2-5)**: Validação obrigatória de PID, account login
  e reconnect automático com retry [5s, 10s, 20s]. Implementado em:
  - `MT5Adapter._validate_terminal_isolation()`: Validação de isolamento
  - `MT5Adapter._save_session_fingerprint()`: Persistência de sessão
  - `MT5Adapter._ensure_connected_with_isolation()`: Validação antes de
    operações críticas
  - `MT5IsolationHealthCheck`: Monitor contínuo (a cada 30s) com alerta de
    desconexão
  - Status visual em `MONITOR_OPERADOR.bat`
- **MT5 REST Adapter**: Interface com MetaTrader 5 via REST Gateway
  (`src/infrastructure/providers/mt5_adapter.py`)
- **Risk Validator**: Chain of Responsibility para validar Capital, Correlação
  e Volatilidade (`src/application/risk_validator.py`)
- **Orders Executor**: Gerenciador do ciclo de vida da ordem e automação
  (`src/application/orders_executor.py`)
- **Order Executor**: Envio de ordens ao MT5
- **Position Manager**: Monitoramento de posições abertas
- **Trade Monitor**: Acompanhamento de trades em tempo real
- **Execution Logger**: Auditoria de execuções

**Tecnologias**: MetaTrader5 Python API, HTTP/REST, Pydantic

### 🔴 6. Confirmation & Feedback Layers (CAMADAS FALTANDO - P0 CRÍTICO)

**⚠️ STATUS 24/02: FALTANDO - Causando dados desaparecidos**

**Responsabilidade**: Confirmar execução em MT5, persistir trades, fechar loop de aprendizado.

**Componentes FALTANDO:**

#### **A. Confirmation Handler Layer** ❌ MISSING
- **O que faz:** Escuta resposta de MT5 após send_order()
- **Status:** SEM IMPLEMENTAÇÃO
- **Evidência:** 4 trades executados em MT5, 0 persistidos em SQLite
- **Impacto:** Audit trail incompleto, violação CVM/B3

```python
# FALTA IMPLEMENTAR:
class ExecutionConfirmationHandler:
    """Handle MT5 execution responses and persist trades"""
    async def on_order_execution(self, event: OrderExecutedEvent):
        # 1. Parse MT5 response (ticket, price, time, fee)  
        # 2. INSERT executed_trade (com decision_id linkage)
        # 3. UPDATE pending_order status
        # 4. Publish trade_outcome_event para RL
```

#### **B. Verification Layer** ❌ MISSING  
- **O que faz:** Valida 1:1 mapping entre MT5 executions ↔ Database records
- **Status:** SEM IMPLEMENTAÇÃO
- **Evidência:** Nenhum relatório de discrepâncias MT5 vs SQLite
- **Impacto:** Impossível detectar perdas de dados

```python
# FALTA IMPLEMENTAR:
class TradeSyncVerifier:
    """Verify 1:1 mapping MT5 executions ↔ Database records"""
    def validate(self) -> TradeSyncReport:
        # Compara trades em MT5 (history_deals)
        # com trades em SQLite (simulated_trades)
        # Output: Report de discrepâncias (MUST BE ZERO)
```

#### **C. RL Feedback Closure Layer** ❌ MISSING
- **O que faz:** Envia resultados reais de trades ao RL system
- **Status:** SEM IMPLEMENTAÇÃO  
- **Evidência:** RL aprendendo com 239 simulações, 0 outcomes reais
- **Impacto:** Machine learning sem aprendizado de verdade

```python
# FALTA IMPLEMENTAR:
class RLTradeOutcomeReceiver:
    """Close the learning loop: trade outcome → RL update"""
    async def on_trade_closed(self, event: TradeClosedEvent):
        # Calcula realized_pnl
        # UPDATE rl_rewards com outcome REAL
        # RL system aprende com verdade, não simulação
```

**🚨 AÇÃO IMEDIATA (P0):**
- Ver [P0-CAUSA_RAIZ_DADOS_DESAPARECIDOS.md](../P0-CAUSA_RAIZ_DADOS_DESAPARECIDOS.md) para design completo
- Implementar 3 componentes (4-6 horas)
- Validar com E2E test
- Deploy hoje ou 25/02

**Tecnologias**: asyncio, Event Bus, Repository Pattern, Type Safety

### 5. Trade Persistence Layer (Confirmation Closure) ✅ IMPLEMENTED (Phase 2-3)

**Status:** ✅ COMPLETE - TASK-CRÍTICA-0 Resolution  
**Implementation Date:** 2026-02-24 → 2026-02-25  
**Validation:** 9/9 E2E Tests Passing

**Responsabilidade**: Garantir que 100% das ordens executadas em MT5 sejam persistidas em SQLite com retry logic, audit trail e zero data loss.

**Componentes Implementados:**

#### A. SendToMT5Command ✅ (Execute Phase)
- **Arquivo:** [src/application/orders_executor.py](../src/application/orders_executor.py#L206-315)
- **Responsabilidade:** Envia ordem a MT5 e persiste resultado
- **Fluxo:**
  1. Recebe ExecutionOrder da fila
  2. Chama MT5Adapter.send_order() → Obtém ticket
  3. Atualiza ExecutionOrder com ticket + execution_time
  4. Converte para Trade entity via to_trade()
  5. Persiste em BD com retry logic (3x exponential backoff)
  6. Atualiza audit log

**Implementação:**
```python
class SendToMT5Command(OrderExecutionCommand):
    async def execute(self, order: ExecutionOrder) -> bool:
        # 1. ENVIAR AO MT5
        ticket = self.mt5_adapter.send_order(order_entity)
        
        # 2. CONVERTER PARA TRADE
        trade = order.to_trade(ticket)
        
        # 3. PERSISTIR COM RETRY (3x exponential backoff: 0.5s, 1s, 2s)
        persisted = await self._persist_with_retry(
            trade, order, max_retries=3
        )
        
        # 4. AUDIT LOG & RETURN
        if persisted:
            order.add_audit(OrderState.EXECUTED, "Trade persistido")
            return True
        else:
            order.add_audit(OrderState.REJECTED, "Persistência falhou")
            return False
```

#### B. ExecutionOrder.to_trade() ✅ (Converter Phase)
- **Arquivo:** [src/application/orders_executor.py](../src/application/orders_executor.py#L113-145)
- **Responsabilidade:** Mapeia ExecutionOrder (application) → Trade (domain)
- **Mapeamento:**
  - symbol: str → Symbol(str)
  - order_type: "BUY"/"SELL" → OrderSide enum
  - volume: float → Quantity(int) - convert to int
  - entry_price: float → Price(Decimal)
  - stop_loss/take_profit: float → Price(Decimal)
  - status → TradeStatus.OPEN
  - notes preserva detector_spike + ml_classifier_score

**Implementação:**
```python
def to_trade(self, mt5_ticket: str) -> Trade:
    return Trade(
        symbol=Symbol(self.symbol),
        side=OrderSide.BUY if self.order_type.upper() == "BUY" else OrderSide.SELL,
        quantity=Quantity(int(self.volume)),  # Convert to int
        entry_price=Price(Decimal(str(self.entry_price))),
        broker_trade_id=mt5_ticket,
        status=TradeStatus.OPEN,
        notes=f"Detector={self.detector_spike:.2f}σ, ML={self.ml_classifier_score:.2%}"
    )
```

#### C. Retry Logic with Exponential Backoff ✅
- **Implementação:** [orders_executor.py:291-310](../src/application/orders_executor.py#L291-310)
- **Estratégia:** Max 3 tentativas, aguards 0.5s → 1s → 2s
- **Tratamento de Erros:**
  - Transient failures (network) → retry
  - Database locks → retry
  - Permanent failures → REJECTED status
  - All retries exhausted → log + DLQ

**Fórmula:**
```
delay_ms = 500 * (2 ^ (attempt - 1))
Tentativa 1: 500ms
Tentativa 2: 1000ms
Tentativa 3: 2000ms
```

#### D. Audit Trail Logging ✅
- **Implementação:** [orders_executor.py:60-72](../src/application/orders_executor.py#L60-72)
- **Estados Rastreáveis:**
  ```
  ENQUEUED → VALIDATED → SENT_TO_MT5 → ACCEPTED_BY_MT5 → EXECUTED (ou REJECTED)
  ```
- **Metadata Capturada:** timestamp, ticket, execution_time, trade_id, retry_count, error_msg

**CVM/B3 Compliance:**
- ✅ Quando ordem foi enviada
- ✅ Quando foi confirmada em MT5
- ✅ Quando foi persistida em DB
- ✅ Qualquer erro no processo
- ✅ Número de retries realizados

### Test Coverage ✅ (Phase 3 Validation)

**Arquivo:** [tests/test_send_to_mt5_command_e2e.py](../tests/test_send_to_mt5_command_e2e.py)

**9 E2E Tests:**
- ✅ Happy path: MT5 send → BD persist (2 tests)
- ✅ Retry logic: Fail → retry → success (2 tests)
- ✅ Converter: ExecutionOrder → Trade mapping (2 tests)
- ✅ E2E integration: Full pipeline (2 tests)
- ✅ Reconciliation: 4 real trades from 24/02 (1 test)

**Result:** 9/9 PASSED (100%)

### Next Steps: Verification & RL Feedback Layers ⏳

**Phase 4-A (Verification Layer)** - TBD:
- Implementar TradeSyncVerifier
- Comparar trades MT5 vs SQLite
- Daily reconciliation job

**Phase 4-B (RL Feedback Closure)** - TBD:
- TradeClosedEvent → RL system
- PnL feedback para aprendizado
- Historical outcome tracking

**Referência Completa:** [docs/PERSISTENCE_GUARANTEE_PROTOCOL.md](../docs/PERSISTENCE_GUARANTEE_PROTOCOL.md)

**Tecnologias**: asyncio, Retry Pattern, SQLite ACID, Type Hints, Clean Architecture

### 6. Monitoring & Health Checks Layer (Camada de Monitoramento)

**Responsabilidade**: Garantir integridade operacional 24/7, latência e sincronia.

**Componentes**:
- **SystemHealthMonitor**: Script de monitoramento contínuo (`scripts/system_health_monitor.py`)
- **Latency Tracker**: Medição P95 de latência de execução (<500ms)
- **Governance Gate**: Verificador de sincronismo de documentação e status de entrega
- **Heartbeat Engine**: Sincronização e validação de conexão MT5 em tempo real

**Tecnologias**: Python, Psutil, SQLite (logs de saúde)

### 6. Performance & Scalability Layer

**Responsabilidade**: Garantir execução em tempo real com baixa latência (~500ms).

**Métricas (SLA)**:
- **Latência Interna (T1)**: < 100ms (Cálculo de features e score).
- **Latência de Decisão (T2)**: < 100ms (Regras de risco e diretivas).
- **Latência de Execução (T3)**: < 300ms (Envio para MT5 via REST).
- **P95 E2E**: < 500ms acumulado.

**Estratégias de Otimização**:
- **Imports Estáticos**: Proibição de imports dentro do loop principal.
- **Connection Reuse**: Mantém conexões MT5 e SQLite ativas para evitar handshake overhead.
- **Async I/O**: Persistência de logs e auditoria em threads separadas ou otimizadas.
- **Lazy Loading/Caching**: Dados macros não críticos cacheados por tempo definido.

## Fluxo de Execução Automática (Phase 7 - Sprint 1)

```
1. Detector (Spike) → Geração de sinal bruto
2. SMC Confluence (S2-3) → Validação M1/M5 zonas de liquidez
3. ML Classifier → Score de confiança (F1 > 0.65)
4. OrdersExecutor → Enfileiramento (ENQUEUED)
5. RiskValidator (Gate 1: Capital) → Saldo suficiente?
6. RiskValidator (Gate 2: Correlação) → < 70%?
7. RiskValidator (Gate 3: Volatilidade) → < 3-Sigma?
8. MT5Adapter.send_order() → VALIDAR ISOLAMENTO (S2-5)
   ├─ _ensure_connected_with_isolation()
   │  ├─ _validate_terminal_isolation() (PID, account_login)
   │  └─ is_trading_halted() check
   └─ Se passou: Envio via REST para MT5
9. PositionMonitor → Acompanhamento do trade
```

## S2-5: MT5 Terminal Isolation & Reconnect

**Objetivo**: Garantir que o operador conecte sempre à conta e terminal
corretos, com retry automático após desconexão.

### Mecanismos de Proteção

1. **Validação de Fingerprint**:
   - PID do `terminal64.exe` em execução
   - Account login corrente vs esperado
   - Server name match
   - Persistido em `~/.mt5_operator_session.json`

2. **Retry Automático com Exponential Backoff**:
   - Tentativa 1: aguardar 5s
   - Tentativa 2: aguardar 10s
   - Tentativa 3: aguardar 20s
   - Se falhar: Sistema entra em **HALT TRADING** (seguro falha)

3. **Health Check Contínuo** (30s interval):
   - `MT5IsolationHealthCheck.check_health()`
   - Detecta desconexões automáticas
   - Dispara reconnect
   - Monitora número de reconexões

4. **Validação em Operações Críticas**:
   - `_ensure_connected_with_isolation()` antes de `send_order()`
   - Rejeita ordem se isolamento violado
   - Levanta `BrokerConnectionError`

### Fluxo de Desconexão & Reconnect

```
┌─ Desconexão Detectada
│
├─ Tentativa 1 (aguardar 5s)
│  ├─ ✅ Sucesso? → Restaurar fingerprint → Retomar operação
│  └─ ❌ Falha → Tentativa 2
│
├─ Tentativa 2 (aguardar 10s)
│  ├─ ✅ Sucesso? → Restaurar fingerprint → Retomar operação
│  └─ ❌ Falha → Tentativa 3
│
├─ Tentativa 3 (aguardar 20s)
│  ├─ ✅ Sucesso? → Restaurar fingerprint → Retomar operação
│  └─ ❌ Falha → HALT TRADING + Log crítico + Alerta em MONITOR
│
└─ HALT OPERACIONAL
   ├─ _trading_halted = True
   ├─ Nenhuma nova ordem enviada
   ├─ Posições abertas mantidas
   └─ Aguardar intervenção manual do trader
```

## Fluxo de Dados

```
1. MT5 → DataLayer: Tick/Candle data em tempo real
2. DataLayer → AnalysisLayer: Dados processados e features
3. AnalysisLayer → DecisionLayer: Sinais, previsões e métricas
4. DecisionLayer → ExecutionLayer: Decisões de trade (Buy/Sell/Hold)
5. ExecutionLayer → MT5: Ordens de execução
6. MT5 → ExecutionLayer: Confirmação e status
7. Todas camadas → Database: Persistência para auditoria e backtesting
```

## Persistência de Dados

### SQLite Schema

```sql
-- Tabela de dados de mercado
market_data (
  id, symbol, timestamp, open, high, low, close, volume, spread
)

-- Tabela de features e indicadores
features (
  id, timestamp, symbol, feature_name, feature_value
)

-- Tabela de previsões
predictions (
  id, timestamp, model_name, prediction_type, predicted_value, confidence, actual_value
)

-- Tabela de decisões
decisions (
  id, timestamp, decision_type, reasoning, signals_used, risk_assessment
)

-- Tabela de trades
trades (
  id, timestamp, symbol, type, price, volume, stop_loss, take_profit, status
)

-- Tabela de performance
performance (
  id, timestamp, balance, equity, profit_loss, drawdown, win_rate, sharpe_ratio
)
```

## Gestão de Risco

1. **Position Sizing**: Kelly Criterion adaptado ou Fixed Fractional
2. **Stop Loss**: ATR-based ou Machine Learning predicted
3. **Max Drawdown**: Limite de 15% com pause automático
4. **Exposure Control**: Máximo 2 posições simultâneas
5. **Risk/Reward**: Mínimo 1:2

## Padrões de Projeto

1. **Repository Pattern**: Abstração de acesso a dados
2. **Strategy Pattern**: Diferentes estratégias de trading
3. **Observer Pattern**: Notificação de eventos de mercado
4. **Factory Pattern**: Criação de modelos e indicadores
5. **Singleton Pattern**: Configurações e conexões
6. **Command Pattern**: Execução de ordens

## Qualidade e Testes

### 1. Testes End-to-End (E2E) e QA Automation

**Objetivo**: Validar o fluxo completo do sistema, desde a captura de sinal até a execução da ordem e encerramento da posição no MetaTrader 5 em ambiente de teste/demonstração.

**Componentes**:
- **E2E Automation Suite**: Scripts especializados para automação de testes completos.
- **MT5 Mock/Paper**: Ambiente MetaTrader 5 em conta Demo ou simulador para execução segura.
- **Data Integrity Checker**: Validação de ponta a ponta da persistência no SQLite e MT5.
- **Performance Stress Tests**: Validação de latência P95 < 500ms durante fluxos intensos de mercado.

**Fluxo de Teste E2E**:
1. Injeção de cenário sintético (Tick Fake ou Candle Histórico).
2. Verificação de processamento pelas camadas Analysis e Decision.
3. Validação de envio de ordem para o MT5 Demo.
4. Confirmação de execução no Position Monitor.
5. Verificação de logs de auditoria e P&L virtual.

### 2. Unit Tests
- 80%+ coverage
- Foco em regras de negócio e lógica de cálculo de risco.

### 3. Integration Tests
- Teste de integração com MT5.
- Teste de fluxo de dados DataLayer → DecisionLayer.

### 4. Backtesting
- Validação histórica de estratégias.
- Capture rate >= 85%, FP <= 10%, Win Rate >= 60%.

### 5. Paper Trading
- Simulação em tempo real antes de produção real-money.

### 6. Performance Tests
- Latência < 100ms em componentes internos.
- Latência < 500ms P95 E2E.

## Segurança

1. **Credenciais**: Variáveis de ambiente (.env)
2. **API Keys**: Encriptadas
3. **Logs**: Sem exposição de dados sensíveis
4. **Auditoria**: Todos trades e decisões registrados

## Monitoramento

1. **Métricas de Negócio**: P&L, Win Rate, Sharpe, Drawdown
2. **Métricas Técnicas**: Latência, uptime, error rate
3. **Alertas**: Drawdown excessivo, erros críticos, anomalias
4. **Dashboard**: Visualização em tempo real

## Escalabilidade

- **Fase 1**: Single-threaded, local, 1 símbolo (WIN)
- **Fase 2**: Multi-threaded, múltiplos símbolos
- **Fase 3**: Microserviços, cloud, múltiplos brokers
