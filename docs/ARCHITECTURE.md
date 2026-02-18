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
- **Technical Indicators**: RSI, MACD, Bollinger, Volume Profile
- **Forecast Engine**: Previsões de curto, médio prazo
- **Feature Engineering**: Criação de features para ML

**Tecnologias**: scikit-learn, XGBoost, LightGBM, TensorFlow/PyTorch, TA-Lib

### 3. Decision Layer (Camada de Decisão)

**Responsabilidade**: Tomada de decisão inteligente baseada em análises e gestão de risco.

**Componentes**:
- **AI Head Financeiro**: Motor de decisão principal (LLM-augmented)
- **Risk Manager**:
  - Stop Loss dinâmico
  - Position Sizing
  - Exposure Control
  - Drawdown Management
- **Portfolio Manager**: Gestão de capital e alocação
- **Order Manager**: Gestão de ordens e execução

**Tecnologias**: Python, Event-driven patterns

### 4. Execution Layer (Camada de Execução)

**Responsabilidade**: Execução de ordens no MetaTrader 5 e gestão de posições.

**Componentes**:
- **Order Executor**: Envio de ordens ao MT5
- **Position Manager**: Monitoramento de posições abertas
- **Trade Monitor**: Acompanhamento de trades em tempo real
- **Execution Logger**: Auditoria de execuções

**Tecnologias**: MetaTrader5 Python API

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

1. **Unit Tests**: 80%+ coverage
2. **Integration Tests**: Teste de integração com MT5
3. **Backtesting**: Validação histórica de estratégias
4. **Paper Trading**: Simulação em tempo real
5. **Performance Tests**: Latência < 100ms

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
