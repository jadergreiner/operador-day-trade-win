# Operador Quântico - Mini Índice WIN

**Head Financeiro do Maior Fundo de Investimentos da América Latina**

Sistema de trading quantitativo com análise multidimensional que sintetiza e relaciona Macro, Fundamentos, Sentimento e Análise Técnica para tomar decisões de classe mundial.

## 🎯 O Operador Quântico

Como **Head Financeiro**, o Operador Quântico analisa 4 dimensões fundamentais:

### 1. 🌍 Macroeconomia Mundial
O que está acontecendo no mundo AGORA que impacta minhas posições HOJE:
- Risk On/Risk Off global
- FED, Treasuries, Dollar Index, VIX
- Impacto em mercados emergentes

### 2. 🇧🇷 Análise Fundamentalista
Cenário Brasil no Mundo:
- Fluxo de capital estrangeiro (entrada/saída)
- Risco-país (EMBI+)
- SELIC, Inflação, indicadores econômicos
- Como investidores avaliam o Brasil

### 3. 📊 Sentimento de Mercado
Qual o cenário e probabilidade para HOJE:
- Compradores vs Vendedores dominando
- Volatilidade intraday
- Volume e momentum
- Probabilidade up/down/neutro

### 4. 📈 Análise Técnica
Os melhores pontos de entrada:
- **Tendências**: Surfando momentum forte
- **Reversões**: Extremos em suportes/resistências
- **Range**: Lateralização com operações curtas
- Indicadores: RSI, MACD, Bollinger, EMAs, ATR

## ✨ Síntese Inteligente

O Operador **sintetiza** todas as dimensões e gera:
- ✅ Decisão: BUY / SELL / HOLD
- 📊 Confiança: 0-100%
- 🎯 Setup de entrada com Stop Loss e Take Profit
- 📈 Risk/Reward calculado
- 💡 Reasoning completo e fundamentado
- ⚠️ Alertas e fatores de risco

## Instrucoes do Copilot

A comunicacao entre Agente e Humano deve ser sempre em Portugues.

## 🚀 Quick Start

```bash
# 1. Configure o ambiente
cp .env.example .env
# Edite .env com suas credenciais MT5

# 2. Instale dependências
pip install -r requirements.txt

# 3. Execute o Operador Quântico
python -m src.interfaces.cli.quantum_operator_cli

# 4. Analise o mercado
> analyze WIN$N
```

Veja [QUICKSTART.md](docs/QUICKSTART.md) para mais detalhes.

## 📊 Características Técnicas

- **Clean Architecture**: Separação perfeita entre domínio, aplicação e infraestrutura
- **SOLID Principles**: Código modular, extensível e testável
- **Domain-Driven Design**: Modelagem rica de domínio financeiro
- **Type Safety**: Type hints em 100% do código
- **MetaTrader 5**: Integração completa para dados em tempo real
- **Gestão de Risco**: Position sizing, stop loss dinâmico, drawdown control
- **🔔 Alertas Automáticos (v1.1)**: Detecção de padrões, entrega multicanal (Push/Email), deduplicação >95%, auditoria CVM

## 🔔 Sistema de Alertas Automáticos (US-004) ✅ IMPLEMENTADO

**Status: Implementação Completa - Pronto para Beta (13/03/2026)**

### Características:
- ✅ **Detecção de Volatilidade**: Z-score >2σ com confirmação em 2 velas (<30s P95)
- ✅ **Detecção de Padrões**: Engulfing, Divergência RSI, Breaks de Suporte/Resistência
- ✅ **Entrega Multicanal**: WebSocket PRIMARY (<500ms) + Email SMTP SECONDARY (2-8s com retry 3x)
- ✅ **Deduplicação**: >95% com hash SHA256 + TTL cache
- ✅ **Rate Limiting**: STRICT 1 alerta/padrão/minuto
- ✅ **Auditoria CVM**: SQLite append-only, 7 anos retenção, 3 tabelas normalizadas
- ✅ **Métricas**: Taxa captura ≥85%, False positive <10%, Throughput 100+/min
- ✅ **Testes**: 11 testes (8 unit + 3 integration) com >80% cobertura

### Documentação:
- [📋 Sumário de Implementação](IMPLEMENTACAO_US004_SUMARIO.md) - Visão completa do projeto
- [🔔 API de Alertas](docs/alertas/ALERTAS_API.md) - Protocolo WebSocket + RFC SMTP + exemplos Python/JS
- [📚 README de Alertas](docs/alertas/ALERTAS_README.md) - Quick start, troubleshooting, métricas
- [🧠 Especificação ML](docs/alertas/aquivostemp_DETECTION_ENGINE_SPEC.md) - Fórmulas, backtest (88% captura, 12% FP)

### Arquitetura:
```
MetaTrader 5 (candles)
       ↓
┌─────────────────────────────────────────┐
│ Detection Engine (asyncio)              │
│ • DetectorVolatilidade (z-score)        │
│ • DetectorPadroesTecnico (patterns)     │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ FilaAlertas (Queue + Dedup + Rate Limit)│
│ • asyncio.Queue, SHA256 hash, TTL Cache │
│ • >95% deduplication                    │
│ • STRICT rate limiting (1/min/padrão)   │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ AlertaDeliveryManager (Multi-Channel)   │
│ • WebSocket (PRIMARY <500ms)            │
│ • Email SMTP (SECONDARY 2-8s + retry)   │
│ • SMS (TERTIARY v1.2)                   │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│ AuditoriaAlertas (CVM Compliant)        │
│ • SQLite append-only                    │
│ • 3 tabelas: alertas, entrega, ações    │
│ • 7 anos retenção                       │
└─────────────────────────────────────────┘
```

### Gateway de Beta:
- [ ] Code review aprovado (2 reviewers)
- [ ] 11/11 testes passando
- [ ] Backtesting ≥85% captura, ≥60% win rate
- [ ] Latência P95 <30s confirmada
- [ ] Lint 0 erros (Python + Markdown)
- [ ] Documentação 100% com exemplos
- [ ] Integração com BDI processor completa
- [ ] Ambiente preparado (WebSocket + Email)

**Timeline:** 13/03/2026 GO-LIVE com capital R$ 50k (Phase 1 BETA)

[📖 Veja o sumário completo de implementação →](IMPLEMENTACAO_US004_SUMARIO.md)

## Estrutura do Projeto

```
operador-day-trade-win/
├── src/
│   ├── domain/              # Entidades e regras de negócio
│   │   ├── entities/        # Trade, Portfolio, Order
│   │   ├── value_objects/   # Price, Money, Position
│   │   ├── enums/           # OrderSide, TradeStatus, Signal
│   │   └── exceptions/      # Exceções de domínio
│   ├── application/         # Casos de uso e serviços
│   │   ├── services/        # Risk Manager, Portfolio Manager
│   │   └── use_cases/       # ExecuteTrade, AnalyzeMarket
│   ├── infrastructure/      # Implementações técnicas
│   │   ├── adapters/        # MT5Adapter, ModelAdapter
│   │   ├── repositories/    # SQLite repositories
│   │   └── database/        # Schema e migrations
│   └── interfaces/          # Pontos de entrada
│       └── cli/             # Interface CLI
├── tests/
│   ├── unit/               # Testes unitários
│   └── integration/        # Testes de integração
├── config/                 # Arquivos de configuração
├── data/                   # Dados, DB e modelos
├── docs/                   # Documentação
└── notebooks/              # Jupyter notebooks para análise
```

## Requisitos

- Python 3.11+
- MetaTrader 5
- SQLite

## Instalação

```bash
# Clone o repositório
git clone <repository-url>
cd operador-day-trade-win

# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instale dependências
pip install -r requirements.txt

# Configure variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais
```

## Configuração

Edite o arquivo `.env`:

```env
# MetaTrader 5
MT5_LOGIN=seu_login
MT5_PASSWORD=sua_senha
MT5_SERVER=seu_servidor

# Trading
TRADING_SYMBOL=WIN$N
MAX_POSITIONS=2
RISK_PER_TRADE=0.02

# Database
DB_PATH=data/db/trading.db
```

## 💻 Uso

### Modo Interativo (Recomendado)

```bash
python -m src.interfaces.cli.quantum_operator_cli
```

Comandos:
- `analyze WIN$N` - Analisa mercado e gera decisão
- `status` - Status da conexão MT5
- `help` - Ajuda
- `exit` - Sair

### Uso Programático

```python
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.domain.value_objects import Symbol

# Inicializar operador
operator = QuantumOperatorEngine()

# Analisar e decidir
decision = operator.analyze_and_decide(
    symbol=Symbol("WIN$N"),
    candles=candles_from_mt5,
    dollar_index=...,
    vix=...,
    selic=...,
    # ... outros parâmetros
)

# Ver decisão
print(decision.executive_summary)
print(f"Action: {decision.action}")  # BUY/SELL/HOLD
print(f"Confidence: {decision.confidence:.0%}")
print(f"Setup: {decision.recommended_entry}")
```

### Exemplo Rápido

```bash
python examples/quick_start.py
```

## 📚 Documentação

- [🚀 Quick Start](docs/QUICKSTART.md) - Comece aqui!
- [📔 Diários Automatizados](docs/DIARIOS_AUTOMATICOS.md) - **NOVO!** Sistema inteligente de journaling
- [🏗️ Arquitetura](docs/ARCHITECTURE.md) - Arquitetura completa do sistema
- [📋 Desenho de Solução](docs/SOLUTION_DESIGN.md) - Visão executiva da solução
- [✨ Padrões de Código](docs/CODING_STANDARDS.md) - Clean Code e SOLID
- [🤝 Guia de Contribuição](docs/CONTRIBUTING.md) - Como contribuir

### ✅ Lint da Documentação (Markdown)

```bash
# Verificar lint dos docs
python -m pymarkdown scan docs

# Aplicar correções automáticas (quando suportado)
python -m pymarkdown fix docs/**/*.md
```

### 🚦 Gate Automático de Promoção de Modelo (OOT)

```bash
# Usa o relatório OOT rolling mais recente em logs/
python scripts/ml/promotion_gate.py

# Exemplo explícito (regra: 2 dias consecutivos)
python scripts/ml/promotion_gate.py --report logs/oot_rolling_3cuts_20260213_185128.json --candidate novo_20260213 --baseline baseline_20260212 --required-consecutive-days 2
```

## 🤖 Agente Autônomo (Sistema de Governança)

O Operador Quântico inclui um **Agente Autônomo** totalmente documentado com sistema de governança de sincronização obrigatória.

### Documentação do Agente Autônomo:

- [🏗️ Arquitetura](docs/agente_autonomo/AGENTE_AUTONOMO_ARQUITETURA.md) - Componentes e fluxo de dados
- [✨ Características](docs/agente_autonomo/AGENTE_AUTONOMO_FEATURES.md) - Feature matrix por versão
- [📋 Histórias de Usuário](docs/agente_autonomo/AGENTE_AUTONOMO_HISTORIAS.md) - Personas e user stories
- [🚀 Roadmap](docs/agente_autonomo/AGENTE_AUTONOMO_ROADMAP.md) - Timeline Q1-Q4 2026
- [📊 Backlog](docs/agente_autonomo/AGENTE_AUTONOMO_BACKLOG.md) - Sprint tracking e progresso
- [📝 Release Notes](docs/agente_autonomo/AGENTE_AUTONOMO_RELEASE.md) - Versões e suporte
- [📈 AutoTrader Matrix](docs/agente_autonomo/AUTOTRADER_MATRIX.md) - Matriz de estratégias (Timeframe × Ativo × Estratégia)
- [🧠 Estratégia ML](docs/agente_autonomo/AGENTE_AUTONOMO_RL.md) - Deep Q-Learning para padrões de trading
- [❓ FAQ + Lições](docs/agente_autonomo/AGENTE_AUTONOMO_FAQ_LICOES_APRENDIDAS.md) - Perguntas frequentes e aprendizados
- [📈 Changelog](docs/agente_autonomo/AGENTE_AUTONOMO_CHANGELOG.md) - Histórico de mudanças

### Sistema de Sincronização Obrigatória:

O Agente implementa um sistema rigoroso de **sincronização automática** de documentação:

- [📋 Manifest de Sincronização](docs/agente_autonomo/SYNC_MANIFEST.json) - Regras e validação automática
- [📦 Versionamento](docs/agente_autonomo/VERSIONING.json) - Rastreamento de componentes e releases
- [📊 Status Tracker](docs/agente_autonomo/AGENTE_AUTONOMO_TRACKER.md) - Dashboard de progresso em tempo real

**Validação Pre-Commit:**
```bash
# O sistema valida automaticamente antes de qualquer commit:
# ✓ Todos os documentos presentes?
# ✓ Checksums sincronizados?
# ✓ Cross-references válidas?
# ✓ Timestamps alinhados?
# ✓ Nenhum documento desincronizado?
```

## 📔 Sistema de Diários Automatizados

O Operador Quântico inclui um sistema revolucionário de **dois diários automatizados**:

### 1. 📰 Diário de Trading Storytelling (15 minutos)
Narrativa jornalística do mercado:
- Manchetes tipo Bloomberg/InfoMoney
- Sentimento emocional (PANIC, GREEDY, FEARFUL, CALM)
- Decisões operacionais fundamentadas
- Tags para aprendizagem de máquina

### 2. 🤔 Diário de Reflexão da IA (10 minutos)
**Auto-crítica sincera e humorada**:
- "Estou sendo útil ou só gerando ruído?"
- "Meus dados realmente movem o preço?"
- "O humano está ajudando ou atrapalhando?"
- Sugestões do que funcionaria melhor

**Iniciar diários automaticamente:**
```bash
# Opção 1: Duplo clique
INICIAR_DIARIOS.bat

# Opção 2: Python
python scripts/quick_start_journals.py
```

Os diários fornecem dados ricos para **aprendizagem por reforço** no final do dia.

[📖 Documentação completa dos diários](docs/DIARIOS_AUTOMATICOS.md)

## 🤖 Sistema de Trading Automatizado

⚠️ **NOVO:Execução automática de operações no MetaTrader 5**

O Operador Quântico agora pode **operar automaticamente** no mercado:

### Características:
- ✅ Análise contínua do mercado (30 segundos)
- ✅ Execução automática de ordens no MT5
- ✅ Stop Loss e Take Profit automáticos
- ✅ Trailing Stop dinâmico (0.5%)
- ✅ Gestão de risco rigorosa (2% por trade)
- ✅ Apenas trades com alta confiança (≥75%)
- ✅ Apenas trades com alto alinhamento (≥75%)
- ✅ 1 contrato por vez (configurável)

### Iniciar Trading Automatizado:
```bash
# ⚠️ AVISO: Executa ordens REAIS com dinheiro REAL
# SEMPRE teste em conta DEMO primeiro!

INICIAR_TRADING_AUTOMATICO.bat
```

### Segurança e Controle:
- Confirmação obrigatória antes de iniciar
- Máximo de 1 posição aberta por vez
- Stop loss sempre definido
- Estatísticas em tempo real
- Fechamento automático ao parar sistema

[📖 Documentação completa do Trading Automatizado](docs/TRADING_AUTOMATIZADO.md)

**IMPORTANTE: Trading automatizado envolve riscos. Teste extensivamente em conta DEMO antes de usar com dinheiro real.**

## 🎓 Como Funciona

```
Usuario solicita análise
       ↓
Quantum Operator Engine
       ↓
┌──────────────────────────────────────┐
│ 1. Macro Analysis      (Global)      │
│ 2. Fundamental Analysis (Brasil)     │
│ 3. Sentiment Analysis   (Intraday)   │
│ 4. Technical Analysis   (Entry)      │
└──────────────────────────────────────┘
       ↓
Síntese Multidimensional
       ↓
Decisão BUY/SELL/HOLD
+ Setup completo
+ Reasoning
+ Risk Assessment
```

## 🎯 Exemplo de Decisão

```
╔══════════════════════════════════════════════════════════════╗
║  OPERADOR QUÂNTICO - DECISÃO DO HEAD FINANCEIRO              ║
╚══════════════════════════════════════════════════════════════╝

🎯 DECISÃO: COMPRA RECOMENDADA
📊 CONFIANÇA: 85%
🎚️ ALINHAMENTO: 100%
⚠️ RISCO: LOW

💡 RAZÃO PRINCIPAL:
Forte alinhamento entre Macro, Fundamentos, Sentimento, Técnica
favorecendo BUY

📊 ANÁLISE MULTIDIMENSIONAL:
   🌍 Macro:        BULLISH ✅
   🇧🇷 Fundamentos:  BULLISH ✅
   📈 Sentimento:   BULLISH ✅
   📊 Técnica:      BULLISH ✅

🎯 SETUP RECOMENDADO:
   Tipo:         TREND
   Sinal:        BUY
   Entrada:      R$ 127,450.00
   Stop Loss:    R$ 127,000.00
   Take Profit:  R$ 128,350.00
   R/R Ratio:    2.0
   Qualidade:    GOOD
   Confiança:    75%
   Razão:        Pullback to EMA21 in uptrend
```

## Testes

```bash
# Executar todos os testes
pytest

# Testes com coverage
pytest --cov=src --cov-report=html

# Testes específicos
pytest tests/unit/domain/
```

## Segurança

- Nunca commite credenciais
- Use variáveis de ambiente
- Mantenha o `.env` no `.gitignore`

## Licença

Uso pessoal apenas.
