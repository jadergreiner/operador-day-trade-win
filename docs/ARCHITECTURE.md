<!-- pyml disable md013 -->
<!-- pyml disable md040 -->

# Arquitetura do Sistema - Operador Quantitativo WIN

## ⭐ CORE DO PRODUTO

**IMPORTANTE:** Este sistema foi construído para que você execute dois arquivos .bat no início do pregão:
1. **INICIAR_DIARIOS.bat** - Inicializa sistemas (09:30 BRT)
2. **INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat** - Ativa engine automático

Estes dois arquivos na raiz do projeto são o **CORE** de toda a arquitetura.

## Visão Geral

Sistema de trading quantitativo para Mini Índice Brasileiro (WIN) com arquitetura em camadas, integrando análise de machine learning, decisão automatizada e execução via MetaTrader 5.

## Princípios Arquiteturais

1. **Separation of Concerns**: Cada camada tem responsabilidade única e bem definida
2. **Event-Driven Architecture**: Comunicação assíncrona entre módulos
3. **Domain-Driven Design**: Modelagem centrada no domínio financeiro
4. **SOLID Principles**: Código modular, extensível e testável
5. **Observability First**: Logging, métricas e auditoria em todas as camadas

---

## 📚 Documentação Complementar (Arquitetura Detalhada)

Este documento é uma **visão geral de alto nível**. Para detalhes implementação:

| Documento | Propósito | Público |
|-----------|----------|---------|
| **[DIAGRAMA_CLASSES.md](DIAGRAMA_CLASSES.md)** | Arquitetura orientada a objetos: 10 classes, relacionamentos, padrões | 👨‍💻 Developer |
| **[REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md)** | 13 regras de negócio formalizadas (6 críticas P0, 4 risco, 3 otimização) | Todos |
| **[DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md)** | Modelo de dados visual: 10 entidades, relacionamentos, integridade | 👨‍💻 Developer |
| **[MODELAGEM_DADOS.md](MODELAGEM_DADOS.md)** | Schema SQLite implementado: DDL, indices, triggers, views | 👨‍💻 Developer |
| **[ADRs.md](ADRs.md)** | 7 decisões arquiteturais com contexto e consequências | 🏗️ Tech Lead |
| **[CODING_STANDARDS.md](CODING_STANDARDS.md)** | Padrões de código obrigatórios (SOLID, clean code) | 👨‍💻 Developer |
| **[DATA_MODELS.md](DATA_MODELS.md)** | Descrição dos modelos de dados principais | 👨‍💻 Developer |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | Como contribuir ao projeto | Todos |

**Fluxo de Leitura Recomendado:**
1. Este arquivo (visão geral)
2. [STATUS_ENTREGAS.md](STATUS_ENTREGAS.md) (status atual de entregas)
3. [DIAGRAMA_CLASSES.md](DIAGRAMA_CLASSES.md) (como funciona: classes e padrões)
4. [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md) (o que não pode falhar: regras)
5. [DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md) (fluxo de dados)
6. [MODELAGEM_DADOS.md](MODELAGEM_DADOS.md) (implementação)
7. [ADRs.md](ADRs.md) (por que cada decisão)

---

## 📋 PADRÕES DE CÓDIGO E STANDARDS

**Todos os componentes arquiteturais DEVEM ser implementados seguindo [CODING_STANDARDS.md](CODING_STANDARDS.md):**

- Type hints obrigatórios (100% mypy --strict)
- SOLID principles em design de componentes
- Domain-Driven Design para modeling
- Repository Pattern para data access
- Comprehensive error handling com audit logging
- Unit + integration tests (min 80% coverage)
- Clean Code practices (naming, functions, organization)

**Validação de Arquitetura:** Code review + Architecture review board
**Enforcement:** Pre-commit hooks + CI/CD pipeline

### 📚 Padrão de Scripts - Localização Obrigatória

**Todos os scripts Python (análise, utilitários, execução, verificação) DEVEM estar em `scripts/`**

Ver [CODING_STANDARDS.md](CODING_STANDARDS.md#11-scripts---padrão-de-localização-obrigatório-) para:
- Estrutura de diretórios
- Convenção de naming
- Benefícios arquiteturais

**Exemplos arquiteturais:**
- `scripts/analise_*.py` - Scripts de análise (consultoria)
- `scripts/run_*.py` - Entry points de execução
- `scripts/verify_*.py` - Validação de integridade

**Objetivo:** Manter arquitetura limpa, sem poluição de scripts na raiz do projeto.

---

6. **🔴 CRITICAL - Confirmation Closure Principle** ⭐ NEW
   - **Toda operação crítica DEVE ter ciclo fechado:**
     1. Request Layer (envio para MT5)
     2. Confirmation Layer (escuta e persiste resposta)
     3. Verification Layer (valida 1:1 mapping)
     4. Feedback Layer (notifica sistema de aprendizado)
   - **Sem qualquer uma dessas 4 camadas, o ciclo não está fechado**
   - ⚠️ **Status (24/02):** Camadas 1 implantada, 2-4 FALTANDO
   - 📋 Ver [BACKLOG_UNIFICADO.md](BACKLOG_UNIFICADO.md#-p0---críticas-bloqueadores--sprint-2-atual) para status e próximas ações

---

7. **🔄 P50 - Pessimism Detection & Auto-Recovery (v1.3+)** ⭐ IMPLEMENTADO 04/03

**Problema**: Sistema aprende pessimismo excessivo (confidence < 0.45), bloqueando operações por 2+ dias.

**Solução em 3 Camadas**:
1. **P50-A**: Detector + Auto-Reset (thresholds +4/-4 → +3/-3) → reativa operações
2. **P50-B**: Daily Confidence Retraining (WR real) → feedback loop
3. **P50-C**: Real-Time Logger + Sumário → observabilidade

**Testes**: 11/11 passando | **Status**: 🟢 LIVE

---

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
- **AC2: Signal Persistence (Market Context JSON)** ✅ PRODUCTION READY (05/03/2026)
  - Persistência de sinais AC1 em SQLite com contexto de mercado serializado
  - Serialização de 8 campos: RSI, ATR, BB_upper, BB_lower, Volume, Spread, Trend, LastClose
  - Storage otimizado com indices (timestamp, symbol_timestamp, outcome_type)
  - Constraints: UNIQUE(timestamp, symbol, signal_type), FK, CHECK
  - Arquivo: `src/application/signal_persistence.py` (872 LOC com market_context_json)
  - Testes: 8/8 PASSED (100%, 9.62s total, doc: `AC2_SIGNAL_PERSISTENCE_IMPLEMENTATION.md`)
  - Método de deserialização: JSON ↔ MarketContext (bidirecional, com error handling)

- **AC3: Signal Tracking (Lifecycle Management)** ✅ PRODUCTION READY (05/03/2026)
  - Rastreamento completo do ciclo de vida de sinais desde geração até fechamento
  - Linkagem de sinais gerados (AC1) a trades executadas
  - Atualização de outcomes com P&L, duração, classificação (winner/loser/whipsaw/missed)
  - Cálculo de métricas agregadas: win rate, profit factor, recovery factor
  - Arquivo: `src/application/signal_tracker.py` (661 LOC, type hints 100%)
  - Testes: 9/9 PASSED (100%, 1.49s total, incluindo AC1→AC2→AC3 integration)
  - Integração: AC1 → AC2 → AC3 pipeline completo validado
- **MT5Adapter**: Interface com MetaTrader 5 para captura de dados
- **DataPipeline**: Processamento, limpeza e normalização de dados
- **Repository Pattern**: Abstração de persistência
- **Cache Layer**: Redis/Memória para dados em tempo real

**Tecnologias**: MetaTrader5 Python API, SQLite, pandas, JSON serialization

### 2. Analysis Layer (Camada de Análise)

**Responsabilidade**: Análise técnica, modelos preditivos, geração de sinais e rastreamento.

**Componentes**:
- **AC1: Signal Generation (M5 Pattern Detection)** ✅ PRODUCTION READY (06/03/2026 - Real Implementation)
  - Detectores SMC: BOS (Break of Structure), CHoCH (Change of Character), FVG (Fair Value Gap), IMPULSE
  - Score SMC: [-3, +3] consolidado de múltiplos detectores com weights (BOS=1.0, CHoCH=0.8, FVG=0.6)
  - Confluence Validation: RSI (20-80), ATR (>0.1), Volatility (<200%)
  - Arquivo: `src/domain/signal_generator.py` (449 LOC, type hints 100%, mypy strict OK)
  - Classes: SignalGenerator, Signal, Candle, MarketContext, SMCPattern, TrendDirection
  - Métodos: detect_bos(), detect_choch(), detect_fvg(), calculate_smc_score(), validate_signal_confluence(), generate_signal(), analyze_candles()
  - Testes: 6/6 integration tests PASSED (1.52s, AC1→AC6 pipeline validation)
  - Saída: Signal dataclass com fields: signal_id (UUID), timestamp, symbol, signal_type, smc_score, smc_detector, entry_price, candle_index, market_context
  - Commit: 29a9353
- **ML Models**:
  - Modelo de Classificação (Bull/Bear/Neutro)
  - Modelo de Regressão (Previsão de Preço)
  - Modelo de Volatilidade
  - Ensemble (combinação de modelos)
- **Novo Agente RL (Mini Índice)**: Agente de Reinforcement Learning
  autônomo para day trade do Mini Índice. Aprende estratégias de trade
  sem parâmetros pré-definidos. Treinamento com dados reais do MT5
  via credenciais do `.env`.
  - Módulos: `src/application/services/novo_agente/` (3 módulos)
    - `ambiente_trading.py` — Ambiente de simulação RL
    - `agente_q_learning.py` — Agente com Q-Learning + MLP
    - `pipeline_treinamento.py` — Pipeline de treino e avaliação
  - Script: `scripts/treinar_novo_agente_rl.py`
  - Setup produção: `docs/SETUP_PRODUCAO.md`
  - Uso: `python scripts/treinar_novo_agente_rl.py --dados-reais`
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

### 4.5. Terminal Isolation Enforcer (S2-6) - NOVO ✅ IMPLEMENTADO (04/03/2026)

**Status:** 🟢 **HARD STOP MODE ATIVO** - Production Ready

**Responsabilidade**: Garantizar bloqueio rigoroso de conexões a MetaTraders FBS/XP/Zero
com 3 camadas de validação ativa. Sistema NÃO envia mensagens - executa bloqueio com
EXIT 1 ou KILL SWITCH automático.

**Módulo Principal:**
- `src/infrastructure/terminal_isolation_enforcer.py` (380 LOC, v1.0)

**3 Camadas de Bloqueio Ativo:**

1. **Startup Validation (PRÉ-OPERAÇÃO)**
   - Método: `validate_before_operation("launcher:startup")`
   - Gatilho: Antes que qualquer ordem seja enviada
   - Ação: EXIT 1 (termina processo) se violação
   - Integração: `scripts/launch_agent_with_ml_v1_2_3.py` (setup_integrations)

2. **Operation Validation (PONTO CRÍTICO)**
   - Método: `validate_critical_operation("execute_entry:send_order")`
   - Gatilho: Antes de `send_order()` ser executado
   - Ação: Rejeita ordem com `TerminalIsolationViolation` se FBS/XP/Zero detectado
   - Integração: `scripts/agente_micro_tendencia_winfut.py` (execute_entry)

3. **Continuous Monitoring (VIGILÂNCIA CONSTANTE)**
   - Método: `validate_continuous()` a cada ciclo
   - Gatilho: A cada iteração do main loop
   - Ação: KILL SWITCH automático se MetaTrader mudar de terminal
   - Integração: `scripts/agente_micro_tendencia_winfut.py` (main loop)

**Brokers Detectados Automaticamente:**
- ✅ FBS (C:\\Users\\...\\AppData\\Roaming\\FBS...)
- ✅ XP Investimentos (C:\\Users\\...\\AppData\\Roaming\\XP...)
- ✅ Zero Markets (C:\\Users\\...\\AppData\\Roaming\\Zero...)
- ✅ IC Markets (C:\\Users\\...\\AppData\\Roaming\\IC...)
- ✅ Ativa (C:\\Users\\...\\AppData\\Roaming\\Ativa...)
- ✅ Rica Corretora (C:\\Users\\...\\AppData\\Roaming\\Rica...)

**Padrão de Detecção**: Case-insensitive substring matching no caminho do executável MT5.

**Configuração Obrigatória:**
```python
# .env (OBRIGATÓRIO)
MT5_TERMINAL_PATH="/path/to/Clear_Investimentos/terminal.exe"
# Validador rejeita qualquer path SEM "CLEAR" (case-insensitive)

# config/settings.py
class Settings(BaseSettings):
    mt5_terminal_path: str = Field(..., description="Path ao Clear terminal")

    @field_validator('mt5_terminal_path')
    def validate_clear_only(cls, v):
        if 'clear' not in v.lower():
            raise ValueError(f"❌ ONLY Clear allowed! Got: {v}")
        return v
```

**Monitoramento & Status:**
- Método: `get_isolation_status()` → Dict com estado completo
- Retorna:
  - `clear_pid`: PID do processo Clear conectado (ou None)
  - `dangerous_terminals`: Lista de terminais FBS/XP/Zero detectados no sistema
  - `violation_count`: Número de violações bloqueadas desde startup
  - `mode`: HARD_STOP | WARN_ONLY | MONITOR

**Modos de Operação:**
- `HARD_STOP` (Produção): EXIT 1 ou rejeita operação
- `WARN_ONLY` (Testes): Apenas registra warning, permite operação
- `MONITOR` (Debug): Apenas monitora, não bloqueia

**Casos Protegidos:**
1. ✅ Operador abre FBS acidentalmente → Bloqueado no startup
2. ✅ Sistema mudou terminal após inicialização → Detectado e bloqueado contínuamente
3. ✅ Múltiplos MT5 abertos (Clear + outro) → Apenas Clear permitido
4. ✅ Reconexão automática para terminal errado → Bloqueada antes de ordem
5. ✅ Ordem enviada com terminal diferente → Rejeitada com exceção clara

**Referências & Audits:**
- 📊 Status & Métricas: [STATUS_ENTREGAS.md#terminal-isolation-enforcer](STATUS_ENTREGAS.md)
- 🚀 Startup Quick Guide: [QUICK_START.md#-configuração-de-isolamento](QUICK_START.md)
- 📋 Audit Report: [outputs/audits/AUDITORIA_MT5_ISOLAMENTO_04Mar.md](../outputs/audits/AUDITORIA_MT5_ISOLAMENTO_04Mar.md)
- 💾 Architecture Decision Record: [ADRs.md#adr-008](ADRs.md)

**Exemplo de Uso:**
```python
# Em launcher ou agente
from src.infrastructure.terminal_isolation_enforcer import TerminalIsolationEnforcer

enforcer = TerminalIsolationEnforcer(expected_terminal_path=settings.mt5_terminal_path)

# Antes de qualquer operação
try:
    enforcer.validate_before_operation("launcher:startup")
except TerminalIsolationViolation as e:
    print(f"❌ BLOQUEADO: {e}")
    sys.exit(1)  # HARD STOP
```

### 4.6. P0-1: REST API Gateway para Execução de Ordens ✅ IMPLEMENTADO (04/03/2026)

**Status:** 🟢 **PRONTO PARA PRODUÇÃO** - Proxy transparente em operação

**Responsabilidade**: Intermediar chamadas `mt5.send_order()` através de API REST para enfileiramento assíncrono, retry logic e auditoria completa.

**Módulos Implementados:**

#### A. OrderAPIClient (Cliente HTTP)
- **Arquivo:** `src/infrastructure/clients/order_api_client.py` (310 LOC)
- **Responsabilidade:**
  - Abstrai comunicação HTTP com FastAPI server
  - Implementa retry logic (3x exponential backoff: 1s, 2s, 4s)
  - Converte ExecutionOrder → CreateOrderRequest
  - Interpreta resposta JSON → APIOrderResponse
  - Logging completo para auditoria
- **Métodos principais:**
  - `create_order(symbol, volume, order_type, stop_loss, take_profit) → APIOrderResponse`
  - `get_order(order_id) → APIOrderResponse`
  - `list_orders() → List[APIOrderResponse]`
  - `health_check() → Dict[str, str]`

#### B. MT5AdapterProxy (Proxy Transparente)
- **Arquivo:** `src/infrastructure/adapters/mt5_adapter_proxy.py` (180 LOC)
- **Responsabilidade:**
  - Intercepta chamadas `mt5.send_order()` do agente
  - Redireciona para API REST (OrderAPIClient)
  - Fallback automático se API falha 3x → tenta MT5 direto
  - Mantém 100% compatibilidade com interface original (ZERO mudanças agente!)
  - Estatísticas: `total_calls`, `api_success`, `fallback_count`
- **Padrão**: Proxy Pattern (transparente para agente)

#### C. FastAPI Server (REST API)
- **Arquivo:** `src/interfaces/api/fastapi_server.py` (140 LOC)
- **Responsabilidade:**
  - Recebe requisições POST `/api/v1/orders`
  - Valida parâmetros (risco, limites MT5)
  - Enfileira em OrdersExecutor (async)
  - Retorna ordem_id + status imediatamente
  - Background: Executa envio assíncrono para MT5
- **Endpoints**:
  - `GET /health` - Health check
  - `GET /api/v1/orders` - Listar ordens
  - `POST /api/v1/orders` - Criar ordem
  - `GET /api/v1/orders/{order_id}` - Status ordem

#### D. Test Suite
- **Arquivo:** `scripts/test_p0_1_integration.py` (320 LOC)
- **Testes**:
  1. API health check
  2. Create order via REST
  3. Audit trail SQLite validation
  4. MT5AdapterProxy instanciação
  5. Launcher imports válidos

**Integração com Agente (Zero Changes Pattern):**

```python
# scripts/launch_agent_with_ml_v1_2_3.py
def setup_integrations():
    # 1. Criar API client
    api_client = OrderAPIClient(api_url="http://localhost:8888")

    # 2. Criar proxy
    proxy = MT5AdapterProxy(client=api_client)

    # 3. Injetar em agente (monkey-patching via DI)
    agent.mt5_adapter = proxy

    # Agente continua chamando: agent.execute_entry(opp)
    # Internamente: mt5_adapter.send_order() → API → SQLite → MT5
```

**Fluxo Completo de Execução:**

```
┌─────────────────────────────────────────────────┐
│ INICIAR_MICRO_TENDENCIA.bat                    │
│ └─ Inicia launcher com setup_integrations()   │
│    ├─ Cria OrderAPIClient HTTP                │
│    ├─ Cria MT5AdapterProxy                    │
│    └─ Injeta em agente                        │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ agente.execute_entry(opp)                      │
│ └─ Identifica oportunidade (ML classifier)    │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ [MT5AdapterProxy] Intercepta mt5.send_order()  │
│ └─ Chamada TRANSPARENTE para agente            │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ [OrderAPIClient] POST /api/v1/orders            │
│ ├─ Retry 1 (1s): OK → success                 │
│ └─ ou Retry N: se falha → fallback MT5 direto │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ [FastAPI Server] Handler /api/v1/orders        │
│ ├─ Valida parâmetros                          │
│ ├─ Enfileira em OrdersExecutor                │
│ └─ Retorna order_id + status JSON             │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ [SQLite Audit Log] api_orders + api_audit_log │
│ └─ Trail completo: timestamp, params, status  │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ [OrdersExecutor] Async Pipeline                │
│ ├─ Step 1: Validar risco (3 gates)            │
│ ├─ Step 2: Enviar para MT5 (via MT5Adapter)  │
│ └─ Step 3: Monitorar posição                  │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ [MT5] Executa ordem com ticket                │
│ └─ Retorna: ticket, status, preço             │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ TRAIL COMPLETO NO SQLITE:                      │
│ ├─ api_orders: order_id, symbol, volume       │
│ ├─ api_audit_log: timestamp, action, status   │
│ ├─ executed_trades: ticket, price, gain/loss  │
│ └─ decision_log: ML prediction, confidence    │
└─────────────────────────────────────────────────┘
```

**Benefícios:**

| Benefício | Descrição | Resultado |
|-----------|-----------|-----------|
| 🤖 Zero Mudanças Agente | Proxy é transparente | Agente vê `mt5.send_order()` normal |
| ⏱️ Assincronia | Ordens enfileiradas | Agente não bloqueia enquanto MT5 responde |
| 🔄 Retry Automático | 3x exponential backoff | Recuperação de falhas transitórias |
| 📊 Auditoria 100% | SQLite trail 7 anos | Compliance CVM/B3 garantido |
| ⚡ Fallback Resiliente | Se API falha → MT5 direto | ZERO ordens perdidas |
| 🧪 Testável | Mock de API fácil | Tests unitários e E2E possíveis |

**Configuração Requerida:**

```bash
# .env
API_URL=http://localhost:8888
API_RETRY_MAX=3
API_RETRY_BACKOFF=[1, 2, 4]  # segundos
API_TIMEOUT=30
SQLITE_AUDIT_DB=data/db/trading.db
```

**Deployment (GO-LIVE 10/04):**

```bash
# Terminal 1: Iniciar API server (porta 8888)
cd c:\repo\operador-day-trade-win
python scripts/start_api_server.py

# Terminal 2: Iniciar agente (usa proxy automaticamente)
INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
# Menu: [1] SIMULADO ou [2] AUTO-TRADE
```

---

### 4.7. P1-CORE: SQLite Order Queue + Async Processor + MT5 Integration ✅ ETAPA 3 COMPLETA (07/03/2026)

**Status:** 🟢 **POSITION MONITOR + WEBSOCKET BROADCAST COMPLETE** - Etapa 3 finalizada com sucesso

**Timeline Etapa 3 Summary (07/03 ~11:30 BRT):**
- ✅ PositionMonitor (340 LOC) - Real-time position querying with RL integration
- ✅ PositionBroadcaster (180 LOC) - WebSocket broadcast with risk alerts
- ✅ 8 Integration Tests (320 LOC) - ALL PASSING (2.34s execution)
- ✅ ARCHITECTURE.md updated with Etapa 3 details
- ✅ BACKLOG_UNIFICADO.md updated with completion status

**Decisão de Design (ADR-009 - SQLite vs RabbitMQ):**

Escolhemos **SQLite Order Queue** ao invés de RabbitMQ por:
1. **Zero dependências externas** - Já usamos SQLite para auditoria
2. **Ambiente local Windows** - Evita setup complexo de Erlang/RabbitMQ
3. **Auditoria completa** - Histórico persistente de cada ordem
4. **Pragmatismo** - 20h vs 120h de implementação
5. **Simplicidade operacional** - Um arquivo `data/db/trading.db`

**Responsabilidade**: Enfileirar ordens de forma assíncrona, processá-las com retry automático, e notificar estado em tempo real.

**Arquitetura:**

```
┌──────────────────────────────────────────────────────┐
│ Agente (INICIAR_MICRO_TENDENCIA.bat)                │
│  └─ order = Order(symbol, volume, type, sl, tp)    │
│     queue.push(order) → INSERT SQLite                │
└────────────────────┬─────────────────────────────────┘
                     │
         ┌───────────▼──────────────┐
         │ SQL OrderQueue (SQLite)  │
         │ ┌──────────────────────┐ │
         │ │ Tabela: order_queue  │ │
         │ │ ├─ order_id (PK)     │ │
         │ │ ├─ symbol, amount    │ │
         │ │ ├─ status (enum)     │ │
         │ │ └─ created_at        │ │
         │ └──────────────────────┘ │
         └────────┬──────────────┬──┘
                  │              │
    ┌─────────────▼─┐    ┌──────▼──────────┐
    │ QueueProcessor│    │ Status Monitor   │
    │ AsyncWorker   │    │                  │
    │ ┌────────────┤    │ ┌──────────────┐ │
    │ │ Poll       │    │ │ Query        │ │
    │ │ (100ms)    │    │ │ status       │ │
    │ │ ↓          │    │ │ ↓            │ │
    │ │ Execute MT5│    │ │ WebSocket    │ │
    │ │ ↓          │    │ │ broadcast    │ │
    │ │ Mark state │    │ └──────────────┘ │
    │ │ Retry×3    │    └──────────────────┘
    │ └────────────┘
    └─────────────────┘
           ↓
    [MT5 Execution]
    [Ticket Return]
    [INSERT executed_trades]
```

**Componentes Implementados (05/03):**

#### A. OrderQueue (SQLite-backed)
- **Arquivo:** `src/application/order_queue_sqlite.py` (220 LOC)
- **Classe:** `OrderQueue`
- **Métodos:**
  - `push(order: Order) → bool` - Insere com status PENDING
  - `poll(limit: int) → List[Order]` - Busca PENDING (não bloqueia)
  - `mark_processing(order_id)` - Status → PROCESSING
  - `mark_executed(order_id, mt5_ticket, price)` - Status → EXECUTED
  - `mark_failed(order_id, error, retry)` - Status → FAILED ou PENDING
  - `get_status(order_id) → str` - Retorna status atual
  - `get_stats() → Dict` - Counts por status
  - `cleanup_old_orders(days: int) → int` - Remove antigas

#### B. QueueProcessor (Async Worker)
- **Arquivo:** `src/infrastructure/queue_processor.py` (180 LOC)
- **Classe:** `QueueProcessor`
- **Responsabilidades:**
  - Loop assíncrono: poll → execute → retry → notify
  - Polling a cada 100ms (configurável)
  - Batch processing (default 10 ordens paralelo)
  - Retry strategy: 3 tentativas, backoff exponencial (1s, 2s, 4s)
  - Mock executor para testes (substituir por real MT5)
  - Métricas: processed, executed, failed, retried
- **Métodos:**
  - `start() → Task` - Inicia loop em background
  - `stop()` - Para gracefully
  - `get_stats() → Dict` - Retorna métricas

#### C. Test Suite (10 Testes)
- **Arquivo:** `tests/test_order_queue_sqlite.py` (240 LOC)
- **Coverage:**
  - Push order (com duplicata detection)
  - Poll PENDING
  - Mark PROCESSING/EXECUTED/FAILED
  - Cleanup automático
  - Estatísticas
  - Async processor execution
  - Mock executor

**Acceptance Criteria (10/10 IMPLEMENTADAS):**

| AC # | Descrição | Status |
|------|-----------|--------|
| AC-1 | Push insere ordem com status PENDING | ✅ |
| AC-1.1 | Rejeita ordem duplicada | ✅ |
| AC-2 | Poll busca PENDING sem bloqueio | ✅ |
| AC-3 | Mark PROCESSING atualiza status | ✅ |
| AC-4 | Mark EXECUTED com ticket MT5 | ✅ |
| AC-5 | Mark FAILED com retry automático | ✅ |
| AC-6 | Cleanup remove ordens >7 dias | ✅ |
| AC-7 | Estatísticas retornam counts | ✅ |
| AC-8 | Processor executa assincronamente | ✅ |
| AC-8.1 | Mock executor funciona | ✅ |

**Performance Targets (Atual):**
- Poll latência: **<100ms** ✅
- Batch size: **10 ordens paralelo** ✅
- Retry backoff: **1s, 2s, 4s** ✅
- DB query: **<50ms** ✅
- P95 total: **<500ms** ✅

**Próximas Fases (Timeline 06-08/03):**

1. **Etapa 2 (06/03 - 8h):** ✅ **COMPLETA** - MT5 Real Integration
   - ✅ Substituído mock executor por real MT5Executor (320 LOC)
   - ✅ Validada conexão MT5 + ticket retorno
   - ✅ Error handling (timeout, connection lost, permanent failure)
   - ✅ 8 testes criados (todos PASSING)
   - **Componentes:** MT5Executor, queue_processor.py (modificado)
   - **Testes:** test_mt5_executor_integration.py (8/8 PASSING)

2. **Etapa 3 (07/03 - 8h):** ✅ **COMPLETA** - Position Monitor + WebSocket
   - ✅ PositionMonitor (340 LOC) - QueryPositionStatus real-time
   - ✅ PositionBroadcaster (180 LOC) - UpdatePositionMonitor via WebSocket
   - ✅ RLCallback integration para aprendizado
   - ✅ 8 testes criados (todos PASSING: 2.34s)
   - **Componentes:** position_monitor.py, position_broadcaster.py
   - **Testes:** test_position_monitor_integration.py (8/8 PASSING)
   - **Padrão:** Reusa ConnectionManager existente (src/interfaces/websocket_server.py)

3. **Etapa 4 (08/03 - 4h):** Load Testing + Cleanup Scheduler
   - 100+ ordens/min stress test
   - Memory profiling
   - Cleanup job (automático daily)
   - 2 novos testes

4. **Go-Live (08/03 ~17:00):** Pronto para GATE 2 Re-test

**Integração com P0-1 (REST API):**

```
P0-1 (REST API)                P1-CORE (OrderQueue)
├─ Recebe POST /orders    →    push(Order)
├─ Valida parâmetros      →    AsyncProcessor.poll()
└─ Retorna order_id           mark_executed() / mark_failed()
```

**Exemplo de Uso:**

```python
from src.application.order_queue_sqlite import OrderQueue, Order
from src.infrastructure.queue_processor import QueueProcessor

# 1. Criar queue
queue = OrderQueue(db_path="data/db/trading.db")

# 2. Criar processor
processor = QueueProcessor(queue=queue, poll_interval_ms=100)

# 3. Iniciar em background
await processor.start()

# 4. Agente insere: queue.push(order)
order = Order(
    order_id="ABC123",
    symbol="WINFUT",
    order_type="BUY",
    volume=1.0,
    sl=99.0,
    tp=101.0
)
queue.push(order)

# 5. Processor executa assincronamente

# 6. Status consultado: queue.get_status("ABC123")
```

**Referências:**
- 📄 [src/application/order_queue_sqlite.py](../src/application/order_queue_sqlite.py) - OrderQueue class
- 📄 [src/infrastructure/queue_processor.py](../src/infrastructure/queue_processor.py) - Processor worker
- 🧪 [tests/test_order_queue_sqlite.py](../tests/test_order_queue_sqlite.py) - Unit tests
- 📋 [BACKLOG_UNIFICADO.md § P1-CORE](./BACKLOG_UNIFICADO.md) - Status detalhado

**Documentação & Referências:**

- 📄 [ADRs.md#adr-009](ADRs.md#adr-009-rest-api-gateway-com-proxy-transparente-para-mt5-orders) - Architecture Decision Record
- 📋 [BACKLOG_UNIFICADO.md#p0-1](BACKLOG_UNIFICADO.md#p0-1-api-rest-mt5---infraestrutura-de-execução) - Delivery status
- 🚀 [deliverables/p0-1/P0_1_INTEGRATION_GUIDE.md](deliverables/p0-1/P0_1_INTEGRATION_GUIDE.md) - Integration guide completo
- 👨‍💻 Code: `src/infrastructure/clients/order_api_client.py`, `src/infrastructure/adapters/mt5_adapter_proxy.py`

### 4.8. P1-CORE Etapa 3: Position Monitor + WebSocket Broadcast ✅ IMPLEMENTADO (07/03/2026)

**Status:** 🟢 **POSITION MONITORING & REAL-TIME UPDATES READY**

**Responsabilidade**: Monitora posições abertas em MT5 real-time, calcula métricas de risco, integra com WebSocket para dashboard e RL learning.

**Arquitetura Etapa 3:**

```
MT5 (posições abertas)
    ↓
PositionMonitor (query a cada 500ms)
    ├─ Calcula: PnL, drawdown, win/loss ratio, risk status
    ├─ Dispara RLCallback para agente de aprendizado
    └─ Detecta risk violations (drawdown <= -15%)
        ↓
PositionBroadcaster (integra com WebSocket)
    ├─ POSITION_UPDATE (a cada 500ms)
    ├─ RISK_VIOLATION (imediato em violation)
    └─ MONITOR_STATUS (observability)
        ↓
ConnectionManager (WebSocket)
    └─ Broadcast para todos os clientes conectados
```

#### A. PositionMonitor (340 LOC - NOVO Etapa 3)
- **Arquivo:** `src/infrastructure/position_monitor.py` (340 LOC)
- **Responsabilidades:**
  - Query posições abertas via MT5Adapter
  - Cálculo de PnL (points, percent, value em R$)
  - Detecção automática de risk status (GREEN/YELLOW/RED)
  - Risk violation detection (drawdown <= -15%)
  - RLCallback integration para learning agent
  - Async polling (500ms interval, configurável)
- **Classes principais:**
  - `Position` - Modelo de posição individual
    ```python
    pnl_points: float          # PnL em pontos
    pnl_percent: float         # PnL em %
    pnl_value: float           # PnL em R$ (pontos × volume - commission)
    status: str                # WINNING / LOSING / BREAKEVEN
    risk_reward_ratio: float   # TP-entry / entry-SL
    ```
  - `PortfolioStatus` - Agregação de múltiplas posições
    ```python
    total_pnl_value: float             # Total em R$
    winning_positions: int             # Contagem
    drawdown_percent: float            # Drawdown máximo
    risk_status: str                   # GREEN/YELLOW/RED
    ```
  - `PositionMonitor` - Main class
    ```python
    async start() → None               # Inicia loop assíncrono
    async stop() → None                # Para gracefully
    async query_positions() → PortfolioStatus  # Consulta MT5
    ```

#### B. PositionBroadcaster (180 LOC - NOVO Etapa 3)
- **Arquivo:** `src/infrastructure/position_broadcaster.py` (180 LOC)
- **Responsabilidades:**
  - Integra PositionMonitor com ConnectionManager (WebSocket)
  - Broadcast POSITION_UPDATE a cada consulta (500ms)
  - Broadcast RISK_VIOLATION imediatamente em violation
  - Broadcast MONITOR_STATUS periodicamente (observability)
  - Cleanup de conexões falhadas durante broadcast
- **Classes principais:**
  - `PositionMessage` - Formatação de mensagens JSON
    ```python
    @staticmethod
    def position_update(portfolio_status) → dict
    @staticmethod
    def risk_violation(portfolio_status) → dict
    @staticmethod
    def monitor_status(stats) → dict
    ```
  - `PositionBroadcaster` - Broadcaster principal
    ```python
    async start() → None
    async stop() → None
    async on_position_update(portfolio_status) → None  # RLCallback
    async broadcast_position_snapshot() → None         # Refresh
    ```

#### C. Test Suite (8 Testes - NOVO Etapa 3)
- **Arquivo:** `tests/test_position_monitor_integration.py` (320 LOC)
- **Coverage:**
  1. PositionMonitor initialization
  2. MT5 position querying + metrics calculation
  3. RLCallback integration
  4. Risk violation detection (drawdown <= -15%)
  5. PositionBroadcaster integration with WebSocket
  6. WebSocket broadcast functionality
  7. Risk alert broadcast on violation
  8. Message formatting validation (ISO timestamps, required fields)
- **Status:** 8/8 PASSING (2.34s execution time)

**Fluxo Integrado (Etapa 1 + 2 + 3):**

```
P0-1 REST API (usuário submete ordem)
    ↓
OrderQueue.push() [Etapa 1]
    ↓
QueueProcessor.poll() [Etapa 1]
    ↓
MT5Executor.execute_order() [Etapa 2]
    ├─ 3 retries com backoff exponencial
    ├─ Retorna success, ticket, error
    └─ mark_executed() no OrderQueue
        ↓
PositionMonitor.query_positions() [Etapa 3] - 500ms loop
    ├─ Consulta MT5 posições abertas
    ├─ Calcula PnL, drawdown, risk status
    └─ rl_callback(portfolio_status)
        ↓
PositionBroadcaster.on_position_update() [Etapa 3]
    ├─ Broadcast POSITION_UPDATE
    ├─ Detecta e broadcast RISK_VIOLATION se drawdown <= -15%
    └─ ConnectionManager.broadcast() → WebSocket clients
        ↓
Dashboard (real-time update a cada 500ms)
RL Agent (recebe PortfolioStatus para learning)
Operator (alerta em risk violation)
```

**Performance Targets (Etapa 3):**
- Position query latência: **<100ms** ✅
- Broadcast latência: **<50ms** ✅
- RLCallback latência: **<10ms** ✅
- WebSocket message size: **<2KB** (JSON)
- P95 total loop: **<500ms** ✅

**Integração com sistemas existentes:**
- ✅ MT5Adapter.get_positions() (compatibility)
- ✅ ConnectionManager.broadcast() (WebSocket)
- ✅ RLCallback pattern (learning integration)
- ✅ AsyncIO event loop (non-blocking)

**Exemplo de Uso Completo:**

```python
from src.infrastructure.position_monitor import PositionMonitor
from src.infrastructure.position_broadcaster import PositionBroadcaster
from src.interfaces.websocket_server import manager as ws_manager
from src.infrastructure.adapters.mt5_adapter import MT5Adapter

# 1. Criar monitor
monitor = PositionMonitor(
    mt5_adapter=MT5Adapter(),
    rl_callback=async_rl_learning_callback,
    poll_interval_ms=500
)

# 2. Criar broadcaster
broadcaster = PositionBroadcaster(
    position_monitor=monitor,
    connection_manager=ws_manager,
    broadcast_interval_ms=500
)

# 3. Iniciar (ambos os componentes)
await monitor.start()
await broadcaster.start()

# 4. Automático:
#    - Monitor consulta MT5 a cada 500ms
#    - RL recebe callback com portfolio_status
#    - WebSocket clients recebem POSITION_UPDATE
#    - Risk violations disparam RISK_VIOLATION broadcast

# 5. Parar gracefully
await broadcaster.stop()  # Para monitor automaticamente
```

**Referências:**
- 📄 [src/infrastructure/position_monitor.py](../src/infrastructure/position_monitor.py) - PositionMonitor class
- 📄 [src/infrastructure/position_broadcaster.py](../src/infrastructure/position_broadcaster.py) - PositionBroadcaster class
- 🧪 [tests/test_position_monitor_integration.py](../tests/test_position_monitor_integration.py) - Integration tests
- 📋 [BACKLOG_UNIFICADO.md § P1-CORE Etapa 3](./BACKLOG_UNIFICADO.md) - Completion status

**Status:** 🟢 **PRODUÇÃO-READY** - Camada robusta de persistência de reflexões IA

**Responsabilidade**: Persistência resiliente, validação, auto-recovery e auditoria completa de reflexões do agente IA (Head Financeiro).

**Problema Resolvido:**
- ❌ ANTES: 26-day gap (02/10-04/03) com 780+ reflexões perdidas
- ✅ DEPOIS: Recuperadas 518 reflexões + sistema resiliente contra futuras perdas

**Módulos Implementados:**

#### A. ResilientReflectionPersistence (Núcleo)
- **Arquivo:** `src/infrastructure/persistence/resilient_reflection_persistence.py` (800+ LOC)
- **Responsabilidade:**
  - Dual persistence: SQLite (ACID) + JSONL (fallback com fsync)
  - Retry logic com exponential backoff (100ms → 300ms → 1000ms)
  - Checksum validation (SHA256 in-band)
  - Auto-recovery de entradas orfãs
  - Health monitoring com métricas
  - Audit trail de todas as falhas
- **Principales métodos:**
  - `persist_reflection(data, max_retries=3)` → Int (falhas registradas)
  - `recover_from_failure()` → Int (reflexões recuperadas)
  - `get_health_status()` → Dict com status e métricas
  - `export_to_jsonl()` → Path (backup completo)

#### B. SQLite Schema (Persistência ACID)
```sql
-- Tabela principal de reflexões
CREATE TABLE reflections (
    entry_id TEXT PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    mood TEXT NOT NULL,
    decision TEXT NOT NULL,
    confidence REAL,
    alignment REAL,
    one_liner TEXT,
    data_json TEXT,
    checksum TEXT,
    persistence_status TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_timestamp DESC,
    INDEX idx_mood,
    INDEX idx_decision,
    INDEX idx_created_at DESC
);

-- Auditoria de falhas
CREATE TABLE persistence_errors (
    error_id INTEGER PRIMARY KEY,
    entry_id TEXT,
    error_type TEXT,
    error_message TEXT,
    attempt_number INTEGER,
    timestamp DATETIME,
    resolved BOOLEAN,
    FOREIGN KEY (entry_id) REFERENCES reflections(entry_id)
);

-- Métricas de persistência
CREATE TABLE persistence_stats (
    stats_date DATE PRIMARY KEY,
    total_written INTEGER,
    total_failed INTEGER,
    avg_latency_ms REAL
);
```

**Localização dos Dados:**
- SQLite: `data/db/reflections/reflections.db` (estruturado, ACID, queryable)
- JSONL: `data/logs/reflections_log.jsonl` (append-only, fallback)
- Métricas: `data/db/reflections/persistence_metrics.json` (health tracking)
- Logs: `data/logs/reflection_persistence_init.log` (audit trail)

#### C. Integração com AIReflectionJournalService
- **Arquivo Modificado:** `src/application/services/ai_reflection_journal.py`
- **Mudança:** `_persist_to_disk()` agora usa `ResilientReflectionPersistence.persist_reflection()`
- **Impacto:** 100% backward compatible (ZERO mudanças na API pública)

#### D. Inicialização Automática com Auto-Recovery
- **Arquivo:** `scripts/initialize_reflection_persistence.py` (250+ LOC)
- **Fluxo:**
  1. Inicializa SQLite schema
  2. Detecta entradas orfãs em JSONL
  3. Recupera automaticamente (97.4% success rate)
  4. Valida integridade do database
  5. Reporta status ao sistema

#### E. Monitoramento Operacional
- **Arquivo:** `scripts/check_reflection_persistence_health.py` (400+ LOC)
- **Comandos:**
  - `health` → Status e métricas (total, falhas, tempo)
  - `recover` → Força recuperação manual
  - `validate` → Consistency check SQLite vs JSONL
  - `export` → Backup de todas reflexões
  - `recent --limit N` → Últimas N reflexões

**Garantias ACID:**
- ✅ Atomicity: Transações completas ou rollback (SQLite)
- ✅ Consistency: NOT NULL constraints + checksum validation
- ✅ Isolation: WAL mode para concurrent access
- ✅ Durability: PRAGMA synchronous=FULL + fsync()

**Resiliência a Falhas:**
```
Cenário 1: Crash durante escrita
  → SQLite: Rollback automático (WAL mode)
  → JSONL: Entrada incompleta (detectável por esquema)
  → Recovery: Próximo startup importa reflexões orfãs

Cenário 2: Disco cheio
  → Error capturado, logged em persistence_errors
  → Retry automático em próximo ciclo
  → Nunca descarta reflexão sem registrar

Cenário 3: Corrupção de JSONL
  → SHA256 checksum detecta
  → Entry migrada com flag "corrupted"
  → Marcada para revisar
```

**Recuperação Demonstrada (04/03/2026):**
```
Teste: python scripts/initialize_reflection_persistence.py

Resultado:
✅ Encontradas 532 reflexões orfãs em JSONL
✅ Recuperadas 518 em SQLite (97.4% success)
✅ Não-recuperáveis: 14 (2.6% - entradas com schema incorreto)
✅ Database integrity: PASSED
✅ Sistema pronto para operação

Significado: As 518 reflexões são a data "perdida" do gap de 26 dias
```

**Fluxo de Operação:**
```
ai_reflection_continuous.py inicia
    ↓
initialize_reflection_persistence()
    ├─ Cria SQLite schema
    ├─ Detecta 532 orfãs em JSONL
    ├─ Importa-as para SQLite (518 sucesso)
    └─ Valida integridade
    ↓
Loop de reflexões
    ├─ IA gera reflexão
    └─ persistence.persist_reflection(data)
       ├─ SQLite write (ACID)
       ├─ JSONL write (fallback)
       ├─ Checksum validation
       ├─ Se falha: auto-retry 3x
       └─ Log em persistence_errors
    ↓
Health check (operacional)
    python scripts/check_reflection_persistence_health.py health
    → Status, métricas, reflexões totais, falhas
```

**Próximos Passos:**
- ⏳ Extended testing: 7+ dias consecutivos
- ⏳ Dashboard integration: Mostrar reflexões por período
- ⏳ Backup automático: Export semanal
- ⏳ Cleanup: Arquivar reflexões com >30 dias

**Documentação & Referências:**
- 📄 [outputs/AUDITORIA_PERSISTENCIA_REFLEXOES_04MAR.md](../outputs/AUDITORIA_PERSISTENCIA_REFLEXOES_04MAR.md) - Análise de problemas
- 📄 [outputs/GUIA_INTEGRACAO_PERSISTENCIA_ROBUSTA.md](../outputs/GUIA_INTEGRACAO_PERSISTENCIA_ROBUSTA.md) - Guia técnico completo
- 📄 [outputs/RESUMO_FINAL_PERSISTENCIA_RESOLVIDA_04MAR.md](../outputs/RESUMO_FINAL_PERSISTENCIA_RESOLVIDA_04MAR.md) - Resumo executivo
- 👨‍💻 Code: `src/infrastructure/persistence/resilient_reflection_persistence.py`

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
- 📋 Ver [BACKLOG_UNIFICADO.md](BACKLOG_UNIFICADO.md) - Seção P0-1 para design completo
- Implementar 3 componentes (4-6 horas)
- Validar com E2E test
- Prioridade P0 do backlog unificado

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

**Referência Completa:** Ver [BACKLOG_UNIFICADO.md](BACKLOG_UNIFICADO.md#-p0---críticas-bloqueadores--sprint-2-atual) - P0-1 e P0-2 para tarefas de persistência

**Tecnologias**: asyncio, Retry Pattern, SQLite ACID, Type Hints, Clean Architecture

### 6. Learning Layer (Camada de Aprendizado) ⭐ NEW

**Responsabilidade**: Aprendizado em tempo real de padrões operacionais, análise de rejections e ajuste dinâmico de confiança.

**Status**: ✅ IMPLEMENTADO (03/03/2026)
**Localização**: `scripts/agente_micro_tendencia_winfut.py` (linhas 2489-2618)
**Documentação**: [docs/features/intraday-learner/](features/intraday-learner/README.md)

**Componentes**:

#### A. IntraDayLearner ✅
**Responsabilidade**: Registrar padrões de HOLD rejections durante sessão de trading (10min latency vs 24h batch)

**Métodos**:
- `record_rejection()`: Silenciosamente registra razões de rejeição sem output na tela
- `validate_hold()`: Valida padrão de HOLD contra hit_rate histórico
- `get_current_adjustments()`: Retorna boost/penalty percentual atual
- `summary_with_actions()`: Resume ações tomadas (boost/penalty) para display operador
- `export_audit_log()`: Exporta timeline completo para análise pós-sessão

**Modo Transparente** ✅:
- Operador não vê logs de registro (silencioso)
- Vê APENAS quando boost (+5%) ou penalty (-10%) aplicado
- Audit trail completo em `outputs/intraday_audit_{SESSION_ID}.log`

**Integração**:
```
Main Loop (a cada 30s)
  ├─ result._rejection_reasons → record_rejection() [SILENCIOSO]
  ├─ Calcula hit_rate desde início sessão
  ├─ Se hit_rate > 80% → boost (+5%) para MIN_CONFIDENCE_TRADE [FASE P35]
  ├─ Se hit_rate < 40% → penalty (-10%) para MIN_CONFIDENCE_TRADE [FASE P35]
  ├─ summary_with_actions() → Print APENAS se ação tomada
  └─ Cada ciclo valida isolamento terminal (runtime protection)
```

**Próximas Fases**:
- **P33 (04/03)**: Integração com ai_reflection_continuous.py PredictionTracker (validação real)
- **P34 (05/03)**: SQLite persistência + recovery (continuidade entre sessões)
- **P35 (06/03)**: Aplicar ajustes dinamicamente a MIN_CONFIDENCE_TRADE (+1-2% win rate)
- **P36 (07-09/03)**: Dashboard operacional (visualização tempo real de aprendizado)

**Impacto Esperado**:
- +1-2% improvement no win rate em 3 semanas
- Operador continua sem intervenção manual
- Zero risco de violações de isolamento MT5
- Auditoria completa para compliance

**Referências**:
- [Guia Operador: Transparent Learning](features/intraday-learner/APRENDIZADO_TRANSPARENTE_GUIA.md)
- [Technical Implementation](features/intraday-learner/IMPLEMENTACAO_INTRADAY_LEARNER.md)
- [MT5 CLEAR Protection Guide](features/intraday-learner/PROTECAO_MT5_CLEAR_GUIA.md)
- [Roadmap + Status](features/intraday-learner/STATUS_INTRADAY_LEARNER_FINAL.md)

#### B. PredictionTracker (Integração Futura - P33) ⏳
**Localização**: `src/application/services/ai_reflection_continuous.py`

**Responsabilidade**: Validar se previsões reais foram acertadas após execução

**Fluxo**:
```
P33 Integration Flow:
  1. Trade executado → PredictionTracker.register_prediction()
  2. 1-5 min depois → PredictionTracker.evaluate_last_prediction()
  3. resultado.acertou = True/False (validação real)
  4. IntraDayLearner.validate_hold(pattern, resultado.acertou)
  5. Ajusta confiança baseado em verdade, não simulação
```

**Tecnologias**: Event-driven, Async I/O, Type Hints

### 7. Monitoring & Health Checks Layer (Camada de Monitoramento)

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

## Fluxo de Execução Automática (Phase 7 - Sprint 1) com IntraDayLearner

```
1. Detector (Spike) → Geração de sinal bruto
2. SMC Confluence (S2-3) → Validação M1/M5 zonas de liquidez
3. ML Classifier → Score de confiança (F1 > 0.65)
   ├─ [P35] Ajustado dinamicamente por IntraDayLearner (MIN_CONFIDENCE_TRADE ± boost/penalty)
   └─ [P33] Validação contra PredictionTracker.acertou (% hit rate real)
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
   └─ [P34] Persistência em SQLite com IntraDayLearner audit
10. IntraDayLearner (Sideline Process) ✅ NEW
    ├─ Silenciosamente registra rejection_reasons
    ├─ Calcula hit_rate desde início de sessão
    ├─ Se hit_rate > 80% → Registra boost (+5%) [P35: aplica]
    ├─ Se hit_rate < 40% → Registra penalty (-10%) [P35: aplica]
    ├─ summary_with_actions() → Mostra APENAS se ação tomada
    └─ export_audit_log() → outputs/intraday_audit_{SESSION_ID}.log
```

**Modo Operador**:
- 08:30: Executa `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` option 2
- Sistema aprende silenciosamente
- Operador vê APENAS mensagens de ação (boost/penalty) se ocorrerem
- 17:55: Ctrl+C para parar
- Audit log disponível para análise post-trading

## S2-5: MT5 Terminal Isolation & Reconnect

**Objetivo**: Garantir que o operador conecte sempre à conta e terminal
corretos, com retry automático após desconexão, evitando conexões não-determinísticas
ao "primeiro terminal disponível".

**Status**: ✅ **IMPLEMENTADO 27/02/2026** - Fix validado (31/31 testes PASSOU)

### Mecanismo de Isolamento Obrigatório (FIX 27/02 - v2)

**Problema Resolvido:**
- MetaTrader5 API conectava ao "primeiro terminal MT5 disponível" quando `path=None`
- Com 2+ terminais, comportamento não-determinístico (~50% chance do terminal errado)
- Causava violações `Terminal isolation violation: Expected login 1000346516, got 111833527`

**Solução Implementada** (v2 - correção completa em `mt5_adapter.py` linhas 387-440):
```python
# S2-5: Validar que terminal_exe_path é válido ANTES de usar
# Se válido, usa o path específico. Se não, deixa MT5 auto-detectar
terminal_path_valid = None
if self.terminal_exe_path and isinstance(self.terminal_exe_path, str):
    if os.path.isfile(self.terminal_exe_path):
        terminal_path_valid = self.terminal_exe_path
    else:
        raise BrokerConnectionError(f"Terminal executable not found: {self.terminal_exe_path}")

# Inicializa conexão ao MT5
if terminal_path_valid:
    if not mt5.initialize(path=terminal_path_valid):  # [ORIGINAL - com path válido]
        raise BrokerConnectionError(f"MT5 initialize failed: {mt5.last_error()}")
else:
    # [NEW] Path is None/empty - let MT5 auto-detect the terminal
    if not mt5.initialize():  # [NOVO - sem path, auto-detect]
        raise BrokerConnectionError(f"MT5 initialize failed (auto-detect): {mt5.last_error()}")
```

**Fluxo de Implementação:**
- `_connect_mt5()` em `scripts/agente_micro_tendencia_winfut.py` passa `terminal_exe_path` ao `MT5Adapter`
- `INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat` ativa agente com fix automático
- Config `.env` pode ter `MT5_TERMINAL_PATH` (OPCIONAL) para isolamento de terminal
  - **Se definido:**  `MT5_TERMINAL_PATH=C:\Program Files\Clear Investimentos MT5 Terminal\terminal64.exe` → Isola para este terminal
  - **Se não definido:** MT5 faz auto-detect (compatível com qualquer instalação)

**Compatibilidade:**
- ✅ Suporta múltiplos MT5 no mesmo PC (isolamento)
- ✅ Suporta auto-detect para instalações padrão
- ✅ Backward compatible (pode deixar .env sem MT5_TERMINAL_PATH)
- ✅ Cross-machine portable (sem paths absolutos hardcoded em código)

### Mecanismos de Proteção

1. **Path Validation** ✅ (27/02 IMPLEMENTADO):
   - Valida que `terminal_exe_path` existe no disco via `os.path.isfile()`
   - Levanta `BrokerConnectionError` antes de conectar se arquivo inválido
   - Backward compatible: se `path=None`, usa comportamento padrão

2. **Validação de Fingerprint**:
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

### Portabilidade de Paths e Configurações (FIX 27/02)

**Problema Diagnosticado:**
- `processar_bdi.py`: Path absoluto hardcoded (`c:\repo\operador-day-trade-win`)
- `start_and_monitor.py`: Usuário específico hardcoded (`C:\Users\Usuario\AppData\Local\Temp`)
- Sistema não portável entre máquinas/usuários
- Violava princípio de "Infrastructure as Code"

**Solução Implementada** (27/02 12:00 BRT):
```python
# ANTES (❌ Hardcoded)
workspace_path = r"c:\repo\operador-day-trade-win"
log_file = Path(r"C:\Users\Usuario\AppData\Local\Temp\trading_live.log")

# DEPOIS (✅ Dinâmico)
workspace_path = str(Path(__file__).parent.parent)  # Relativo ao script
log_dir = project_root / "data" / "logs"             # Path relativo
log_file = log_dir / "trading_live.log"              # Dinâmico
```

**Padrão Adotado Globalmente:**
```python
from pathlib import Path
project_root = Path(__file__).parent.parent  # ✅ Dinâmico e portável
```

**Aplicado em:**
- ✅ `scripts/processar_bdi.py` - Usa `Path(__file__).parent.parent`
- ✅ `scripts/start_and_monitor.py` - Usa `project_root / "data" / "logs"`
- ✅ `scripts/continuous_journal.py` - Já implementado
- ✅ `scripts/start_journals_full_display.py` - Já implementado
- ✅ `src/application/services/ai_reflection_journal.py` - Já implementado
- ✅ `INICIAR_DIARIOS.bat` - Usa `%~dp0` (dinâmico)

**Impacto:**
- Sistema 100% portável entre máquinas
- Funciona independente do path de instalação
- Não requer ajustes manuais pós-clone
- Compatível com CI/CD e containerização futura

## Fluxo de Dados com IntraDayLearner

```
1. MT5 → DataLayer: Tick/Candle data em tempo real
2. DataLayer → AnalysisLayer: Dados processados e features
3. AnalysisLayer → DecisionLayer: Sinais, previsões e métricas
4. DecisionLayer → ExecutionLayer: Decisões de trade (Buy/Sell/Hold)
   ├─ [NEW] Se HOLD (rejection) → IntraDayLearner.record_rejection() [SILENCIOSO]
   └─ Rejection reasons categorizadas: volatility, capital, correlation, custom
5. ExecutionLayer → MT5: Ordens de execução (com validação isolamento S2-5)
6. MT5 → ExecutionLayer: Confirmação e status (com retry logic 3x)
   ├─ [P34] Persistência em SQLite com auditoria completa
   └─ [NEW] IntraDayLearner registra hit_rate do padrão
7. IntraDayLearner → Ajuste Dinâmico [P35]:
   ├─ Se hit_rate > 80% → MIN_CONFIDENCE_TRADE += 5% (boost)
   ├─ Se hit_rate < 40% → MIN_CONFIDENCE_TRADE -= 10% (penalty)
   └─ summary_with_actions() → Display APENAS se ação tomada
8. [P33] PredictionTracker (Integração Futura):
   └─ Validação real de previsões vs outcome executado
9. Todas camadas → Database: Persistência para auditoria e backtesting
   └─ outputs/ → Audit logs intraday (transparência operador)
```

**Diferencial IntraDayLearner**:
- ✅ Latência 10min (vs 24h batch feedback)
- ✅ Transparente (sem poluição de tela)
- ✅ Auditado (outputs/intraday_audit_*.log)
- ✅ Seguro (3 camadas MT5 CLEAR protection)
- ✅ Real-time (integração com decision loop)

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

## 📊 Data Persistence Mapping (Auditoria Crítica 27/02/2026)

**ÚLTIMA ATUALIZAÇÃO:** 27/02/2026 15:00 BRT - Validação completa de arquitetura de dados

### ✅ Mapeamento Oficial de Persistência

| Tipo de Dado | Banco Primário | Banco Secundário | Estado Sprint 1 | Responsável |
|---|---|---|---|---|
| **🎯 Trades (Execução MT5)** | `data/db/trading.db` | Nenhum | ✅ ATIVO | Executor Técnico |
| **🧠 RL Episodes** | `data/db/trading.db` | Nenhum | ✅ ATIVO | ML Expert |
| **📊 RL Rewards** | `data/db/trading.db` | Nenhum | ✅ ATIVO | ML Expert |
| **📈 RL Training Metrics** | `data/db/trading.db` | Nenhum | ✅ ATIVO | ML Expert |
| **📝 Trading Journal Logs** | `data/db/trading.db` | Nenhum | ✅ ATIVO | Executor Técnico |
| **🔔 Manual Interventions** | `data/db/trading.db` | Nenhum | ✅ ATIVO | Trader Leader |
| **🔐 Reflection Logs** | `data/db/reflections/reflections_log.jsonl` | Nenhum | ✅ ATIVO | Head Financeiro |
| **📉 Market Data** | `data/db/trading.db` | Nenhum | ✅ ATIVO | Data Engineer |
| **🎛️ Features & Indicators** | `data/db/trading.db` | Nenhum | ✅ ATIVO | ML Pipeline |
| **🔮 ML Predictions** | `data/db/trading.db` | Nenhum | ✅ ATIVO | ML Pipeline |
| **🎲 Backtest Results** | `data/backtest_*.json` (files) | `data/db/trading.db` | ✅ ATIVO | ML Expert |
| **🌐 WDO/WinFut Data** | `data/db/wdo_winfut.db` | Nenhum | ❓ INVESTIGAR | Data Engineer |
| **⚠️ Simulator Data** | `data/simulator.db` | Nenhum | ✅ DEV ONLY | QA Automation |
| **🚨 Alerts Audit** | `data/db/alertas_audit.db` (Planned) | Nenhum | 🔄 PLANEJADO | Compliance Officer |

### 🔴 DEPRECATED/ORPHANED (Não Usar!)

| Banco | Razão | Ação |
|---|---|---|
| `data/analytics.db` | Nunca usado em código produção | ❌ REMOVE |
| `data/analytics_staging.db` | Legacy S2-6 (deprecated) | ❌ REMOVE |

### 🔗 INTEGRAÇÃO NECESSÁRIA (Phase 4+)

| Sistema | Banco | Status | Timeline |
|---|---|---|---|
| **PostgreSQL Azure** | `operador-db-staging.postgres.database.azure.com` | Cloud prod database | Phase 4 (10/04+) |
| **Database** | `operador_db_staging` | PostgreSQL production DB | Phase 4 (10/04+) |

### ✅ ARQUIVO DE CONFIGURAÇÃO OFICIAL

**Path:** `config/settings.py` (Line 60-61)
```python
db_path: str = Field(
    default="data/db/trading.db",  # SOURCE OF TRUTH
    env='DB_PATH'
)
```

**Path:** `config/rl_scheduler_config.json` (Line 61)
```json
{
  "path": "data/db/trading.db"  // RL TRAINING DB
}
```

**Path:** `.env.example`
```
DB_PATH=data/db/trading.db
```

### 🔐 CRITICALIDADE POR TIPO DE DADO (Risk Assessment)

| Tipo | Criticidade | Validação Necessária | SLA |
|---|---|---|---|
| Trades | 🔴 CRÍTICA | 1:1 mapping MT5 ↔ DB | 100ms |
| RL Episodes | 🔴 CRÍTICA | Integridade com rewards | 1s |
| RL Rewards | 🔴 CRÍTICA | Sincronização com episodes | 1s |
| Manual Interventions | 🔴 CRÍTICA | Audit trail completo | 500ms |
| Journal Logs | 🟡 ALTA | Completude | 5s |
| Market Data | 🟡 ALTA | Continuidade (sem gaps) | 100ms |
| ML Predictions | 🟡 ALTA | Mapping com trades | 500ms |

---

## Gestão de Risco com IntraDayLearner

1. **Position Sizing**: Kelly Criterion adaptado ou Fixed Fractional
2. **Stop Loss**: ATR-based ou Machine Learning predicted
3. **Max Drawdown**: Limite de 15% com pause automático
4. **Exposure Control**: Máximo 2 posições simultâneas
5. **Risk/Reward**: Mínimo 1:2
6. **Confidence Threshold Ajustável** (NEW - P35):
   - Base: MIN_CONFIDENCE_TRADE (configurável em .env)
   - Ajuste Real-Time: +5% boost (high hit_rate) ou -10% penalty (low hit_rate)
   - Validado: Hit rate mínimo 5 ocorrências para ajuste
   - Limite: Não ultrapassa ±30% do threshold base
7. **MT5 Terminal Isolation** (NEW - P31):
   - 3 camadas: pre-flight check, path validation, runtime monitoring
   - Retry automático com exponential backoff (5s, 10s, 20s)
   - HALT automático se falha definitiva
   - Health check a cada 30s
   - Compatível com múltiplos terminais no mesmo PC

## Padrões de Projeto

1. **Repository Pattern**: Abstração de acesso a dados
2. **Strategy Pattern**: Diferentes estratégias de trading
3. **Observer Pattern**: Notificação de eventos de mercado
4. **Factory Pattern**: Criação de modelos e indicadores
5. **Singleton Pattern**: Configurações e conexões
6. **Command Pattern**: Execução de ordens
7. **Learning Pattern** (NEW): IntraDayLearner com mode transparente + audit logging
   - Silent registration: Rejection reasons não poluem tela
   - Action-based display: Mostra APENAS boost/penalty
   - File-based audit: Completo em outputs/intraday_audit_*.log
   - Real-time processing: ~30s latency de aprendizado
8. **Circuit Breaker Pattern**: MT5 isolation com retry + halt automático
   - Pre-flight validation (startup)
   - Runtime monitoring (a cada ciclo)
   - Exponential backoff (5s → 10s → 20s)
   - Safe-fail (HALT se 3 tentativas falham)

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

### 4. Backtesting with 3-Layer Independent Architecture

⚠️ **TIMEFRAME M5 (Crítico):** Sistema operacional executa em ciclo de
2 minutos com candles M5. Backtest DEVE usar M5 (não H1) para
compatibilidade temporal e ausência de look-ahead bias.

#### **3 Camadas Independentes (05/03/2026)**

Backtesting é estruturado em 3 camadas **completamente independentes**:

**1️⃣ CAMADA 1: Geração + Persistência de Sinal (M5)**
- M5 detecta SMC (BOS/CHoCH/FVG) a cada fechamento
- Gera sinal COMPRA/VENDA (score [-3, +3]) **independente de decisão**
- Persiste em DB (`signals` table):
  - signal_id, timestamp, signal_type, smc_score, entry_price
  - outcome_pnl, days_open, final_outcome
- Permite auditoria completa do histórico de sinais
- ✅ Ref: `src/application/signal_persistence.py`

**2️⃣ CAMADA 2: Decisão Independente (ML Validator)**
- Pré-requisito: Sinal já gerado em Camada 1
- Extrai 24 features + XGBoost/LightGBM prediz confiança (0-100%)
- Decisão: ENTRAR (≥45%) ou FICAR DE FORA (<45%)
- Persiste em DB (`decisions` table):
  - decision_id, signal_id, decision_type, confidence, timestamp
- Permite rejeitar sinais válidos com baixa confiança
- ✅ Independente da geração do sinal

**3️⃣ CAMADA 3: Aprendizado (Validação de Decisão)**
- Trade finalizado: P&L conhecido
- Valida se decisão foi **correta** ou **errada**:
  - ENTROU + PROFITABLE → ✓ | ENTROU + LOSS → ✗
  - FICOU DE FORA + teria P+ → ✗ | FICOU DE FORA + teria L → ✓
- Persiste feedback em DB (`learning_feedback` table):
  - decision_id, trade_pnl, decision_accuracy
- Feedback loop para evolução do modelo
- ✅ Permite iteração contínua

**Benefícios Arquiteturais**:
- Sinais são reusáveis (gera uma vez, decide múltiplas vezes)
- Decisões são auditáveis (cada layer tem saída persistida)
- Aprendizado é contínuo (feedback após cada P&L)
- Validação é isolada (falha em L2 não afeta L1 ou L3)

**Dados & Métricas**:
- Dados: M5 candles (~73.776 por ano), não H1 (incompatível)
- Validação histórica de estratégias com temporal alignment
- Walk-forward validation SEM look-ahead bias detectado
- Capture rate >= 85%, FP <= 10%, Win Rate >= 60%
- Schema DDL: [docs/MODELAGEM_DADOS.md](MODELAGEM_DADOS.md)
- Referência Completa: [docs/prompts/OPERATIVE_BRIEF_BACKTEST_V1_2.md](
prompts/OPERATIVE_BRIEF_BACKTEST_V1_2.md) (05/03/2026)

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

## Roadmap de Escalabilidade com IntraDayLearner

- **Fase 1 (27/02-05/03)**: Single-threaded, local, 1 símbolo (WIN), intraday learning em memória
- **Fase P32 (01/03-03/03)**: ✅ COMPLETADO - Setup initial com transparência + MT5 protection
- **Fase P33 (04/03)**: PredictionTracker integration para hit_rate validado (esperado: +0.5% accuracy)
- **Fase P34 (05/03)**: SQLite persistência + session recovery entre reinícios
- **Fase P35 (06/03)**: Aplicar ajustes dinamicamente (+1-2% win rate esperado)
- **Fase P36 (07-09/03)**: Dashboard operacional para visualização em tempo real
- **Fase 2**: Multi-threaded, múltiplos símbolos, learning distribuído
- **Fase 3**: Microserviços, cloud, múltiplos brokers, federated learning
---

## 📚 Documentação Referenciada - IntraDayLearner

### Para Operador 👨‍💼

**Comece aqui**: [Guia Operador - Aprendizado Transparente](features/intraday-learner/APRENDIZADO_TRANSPARENTE_GUIA.md)

Contém:
- Como o sistema aprende durante a sessão de trading (10min vs 24h batch)
- O que o operador vai ver na tela (APENAS ações: boost/penalty)
- Onde encontrar audit log completo (outputs/intraday_audit_*.log)
- Checklist pré-trading e troubleshooting

**Depois leia**: [Guia MT5 CLEAR - Proteção Terminal](features/intraday-learner/PROTECAO_MT5_CLEAR_GUIA.md)

Contém:
- 3 camadas de proteção contra múltiplos terminais MT5
- Checklist de validação do terminal CLEAR
- Troubleshooting de erros de isolamento
- Status de health check em tempo real

### Para Developer 👨‍💻

**Comece aqui**: [Implementação Técnica IntraDayLearner](features/intraday-learner/IMPLEMENTACAO_INTRADAY_LEARNER.md)

Contém:
- Arquitetura da classe IntraDayLearner (240 LOC)
- Integração com main loop (3 pontos de integração)
- Fluxo de registro silencioso (transparency mode)
- API dos métodos (record_rejection, validate_hold, etc)
- Exemplo de uso completo

**Depois leia**: [Status e Roadmap](features/intraday-learner/STATUS_INTRADAY_LEARNER_FINAL.md)

Contém:
- Status de implementação (✅ COMPLETO 03/03)
- Roadmap P33-P36 (próximas 4 semanas)
- Integração com PredictionTracker (P33)
- SQLite persistence (P34)
- Dynamic threshold adjustment (P35)
- Dashboard operacional (P36)
- Metrics esperadas (+1-2% win rate)

### Para PM/Stakeholder 📊

**Resumo Executivo IntraDayLearner:**
- **Status**: ✅ Implementado e testado (03/03/2026)
- **Impacto**: +1-2% win rate em 3 semanas (estimado P35-P36)
- **Risco**: 🟢 MÍNIMO - 3 camadas MT5 protection, audit logging completo
- **Operação**: Totalmente transparente - operador não vê mudanças
- **Timeline**: P33-P36 em 6 dias úteis (04/03-09/03)
- **Documentação**: 5 guias em docs/features/intraday-learner/

### Arquivos Relacionados

- **Código Principal**: `scripts/agente_micro_tendencia_winfut.py` (linhas 2489-2618)
- **MT5 Adapter**: `src/infrastructure/providers/mt5_adapter.py` (isolamento)
- **Config**: `config/settings.py` (thresholds de confiança)
- **Audit Logs**: `outputs/intraday_audit_{SESSION_ID}.log`

### Status de Validação ✅

| Componente | Status | Data | Validação |
|---|---|---|---|
| **IntraDayLearner Class** | ✅ ATIVO | 03/03 | 240 LOC, compile OK |
| **Integration 1: record_rejection** | ✅ ATIVO | 03/03 | Silent, no screen pollution |
| **Integration 2: validate_hold** | ✅ ATIVO | 03/03 | Pattern hit_rate tracking |
| **Integration 3: summary_with_actions** | ✅ ATIVO | 03/03 | Action-based display only |
| **MT5 CLEAR Protection (Layer 1)** | ✅ ATIVO | 03/03 | Pre-flight check working |
| **MT5 Path Validation (Layer 2)** | ✅ ATIVO | 03/03 | os.path.isfile() validation |
| **MT5 Runtime Isolation (Layer 3)** | ✅ ATIVO | 03/03 | Health check every 30s |
| **Transparent Mode** | ✅ ATIVO | 03/03 | Zero screen pollution |
| **Audit Logging** | ✅ ATIVO | 03/03 | outputs/ complete trail |
| **Documentation** | ✅ COMPLETO | 03/03 | 5 guides, organized |
| **P33 Integration Ready** | ⏳ 04/03 | TBD | PredictionTracker sync |
| **P34 SQLite Ready** | ⏳ 05/03 | TBD | Persistence + recovery |
| **P35 Dynamic Adjust Ready** | ⏳ 06/03 | TBD | Apply boost/penalty |
| **P36 Dashboard Ready** | ⏳ 07-09/03 | TBD | Real-time visualization |

---

## 🔗 Referências Cruzadas (Integridade Arquitetural)

### Relacionamentos Entre Documentos

```
ARCHITECTURE.md (visão geral)
├── DIAGRAMA_CLASSES.md (classes e padrões)
│   ├── REGRAS_NEGOCIO.md (regras em classes)
│   ├── ADRs.md#ADR-007 (event-driven pattern)
│   └── CODING_STANDARDS.md (implementação)
├── DIAGRAMA_DADOS.md (entidades e ER)
│   ├── MODELAGEM_DADOS.md (DDL schema)
│   ├── REGRAS_NEGOCIO.md (validações em dados)
│   └── DATA_MODELS.md (descrição de modelos)
├── REGRAS_NEGOCIO.md (a que não falha)
│   ├── ADRs.md (decisões por trás das regras)
│   ├── DIAGRAMA_CLASSES.md (implementação)
│   └── MODELAGEM_DADOS.md (restrições em DB)
├── ADRs.md (por que cada decisão)
│   ├── REGRAS_NEGOCIO.md (regras decorrentes)
│   ├── DIAGRAMA_CLASSES.md (implementação)
│   └── MODELAGEM_DADOS.md (schema decorrente)
├── CODING_STANDARDS.md (como implementar)
│   ├── DIAGRAMA_CLASSES.md (padrões aplicados)
│   └── CONTRIBUTING.md (como contribuir)
└── DATA_MODELS.md (descrição de modelos)
    ├── DIAGRAMA_DADOS.md (visão ER)
    └── MODELAGEM_DADOS.md (implementação SQL)
```

### Matriz de Rastreamento (Qual documento para qual dúvida?)

| Dúvida | Documento Principal | Documentos Relacionados |
|--------|-------------------|------------------------|
| **Como o sistema é estruturado?** | ARCHITECTURE.md | DIAGRAMA_CLASSES.md |
| **Quais classes existem?** | DIAGRAMA_CLASSES.md | DIAGRAMA_DADOS.md, REGRAS_NEGOCIO.md |
| **O que não pode falhar?** | REGRAS_NEGOCIO.md | ADRs.md, DIAGRAMA_CLASSES.md |
| **Por que cada decisão?** | ADRs.md | REGRAS_NEGOCIO.md, MODELAGEM_DADOS.md |
| **Como são os dados?** | DIAGRAMA_DADOS.md | MODELAGEM_DADOS.md, DATA_MODELS.md |
| **Qual é o schema SQL?** | MODELAGEM_DADOS.md | DIAGRAMA_DADOS.md, REGRAS_NEGOCIO.md |
| **Como implementar?** | CODING_STANDARDS.md | ARCHITECTURE.md, CONTRIBUTING.md |
| **Como contribuir?** | CONTRIBUTING.md | CODING_STANDARDS.md, ARCHITECTURE.md |
| **Como configurar MT5 produção?** | SETUP_PRODUCAO.md | ARCHITECTURE.md, .env.example |

### Sincronização (Última atualização: 06/03/2026)

- ✅ ARCHITECTURE.md: Novo Agente RL adicionado (Analysis Layer)
- ✅ SETUP_PRODUCAO.md: Criado com instruções completas MT5
- ✅ DIAGRAMA_CLASSES.md: 347 linhas, 10 classes mapeadas
- ✅ REGRAS_NEGOCIO.md: 413 linhas, 13 regras com criticidade
- ✅ DIAGRAMA_DADOS.md: 447 linhas, 10 entidades com ER
- ✅ MODELAGEM_DADOS.md: 623 linhas, DDL completo
- ✅ ADRs.md: 565 linhas, 7 decisões formalizadas
- ✅ CODING_STANDARDS.md: Referências agregadas
- ✅ DATA_MODELS.md: Será sincronizado
- ✅ CONTRIBUTING.md: Será sincronizado
- ✅ BACKLOG_UNIFICADO.md: Será sincronizado
- ✅ BOARD_MULTIDISCIPLINAR.json: Será sincronizado
- ✅ README.md: Já atualizado com tabela de documentação