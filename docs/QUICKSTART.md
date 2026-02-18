<!-- pyml disable md040 -->
<!-- pyml disable md032 -->

# Quantum Operator - Quick Start

## Como Usar o Operador Quântico

### 1. Modo Interativo (Recomendado)

Execute a interface CLI para interagir com o operador:

```bash
python -m src.interfaces.cli.quantum_operator_cli
```

Comandos disponíveis:
- `analyze WIN$N` - Analisa o mercado WIN e fornece decisão
- `analyze <SYMBOL>` - Analisa qualquer símbolo
- `status` - Mostra status da conexão MT5
- `help` - Mostra ajuda
- `exit` - Sai do programa

### 2. Uso Programático

```python
from config import get_config
from src.application.services.quantum_operator import QuantumOperatorEngine
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, TimeFrame
from decimal import Decimal

# Configurar
config = get_config()

# Conectar ao MT5
mt5 = MT5Adapter(
    login=config.mt5_login,
    password=config.mt5_password,
    server=config.mt5_server,
)
mt5.connect()

# Obter dados
symbol = Symbol("WIN$N")
candles = mt5.get_candles(symbol=symbol, timeframe=TimeFrame.M15, count=100)

# Analisar
operator = QuantumOperatorEngine()
decision = operator.analyze_and_decide(
    symbol=symbol,
    candles=candles,
    dollar_index=Decimal("104.5"),
    vix=Decimal("16.8"),
    selic=Decimal("10.75"),
    ipca=Decimal("4.5"),
    usd_brl=Decimal("5.85"),
    embi_spread=250,
)

# Ver decisão
print(decision.executive_summary)
print(f"Action: {decision.action}")
print(f"Confidence: {decision.confidence:.0%}")

if decision.recommended_entry:
    print(f"Entry: {decision.recommended_entry.entry_price}")
    print(f"Stop Loss: {decision.recommended_entry.stop_loss}")
    print(f"Take Profit: {decision.recommended_entry.take_profit}")
```

### 3. Exemplo Rápido

Execute o exemplo incluído:

```bash
python examples/quick_start.py
```

## O Que o Operador Faz

O **Operador Quântico** analisa 4 dimensões do mercado:

1. **Macroeconomia Mundial** 🌍
   - Apetite por risco global (Risk On/Off)
   - Impacto dos EUA (futuros, yields, dollar, VIX)
   - Efeito em mercados emergentes

2. **Fundamentos Brasil** 🇧🇷
   - Fluxo de capital estrangeiro
   - Risco-país (EMBI+)
   - SELIC, inflação, indicadores econômicos

3. **Sentimento de Mercado** 📊
   - Compradores vs Vendedores TODAY
   - Volatilidade intraday
   - Volume e momentum

4. **Análise Técnica** 📈
   - Setup de entrada (trend, reversal, range)
   - Stop loss e take profit
   - Indicadores (RSI, MACD, Bollinger, EMAs)

### Síntese Inteligente

O operador **sintetiza** todas as dimensões e:
- Calcula alinhamento entre as análises
- Avalia risco geral
- Identifica regime de mercado
- Gera decisão BUY/SELL/HOLD com confiança
- Fornece reasoning completo

## Decisão de Saída

O operador retorna:

```python
TradingDecision(
    action=TradeSignal.BUY,  # ou SELL, HOLD
    confidence=Decimal("0.85"),  # 0-1
    urgency="IMMEDIATE",  # IMMEDIATE, OPPORTUNISTIC, PATIENT, AVOID

    # Setup técnico
    recommended_entry=EntryPoint(...),

    # Análises
    macro_bias="BULLISH",
    fundamental_bias="BULLISH",
    sentiment_bias="BULLISH",
    technical_bias="BULLISH",

    # Métricas
    alignment_score=Decimal("1.0"),  # 100% aligned
    risk_level="LOW",

    # Reasoning
    primary_reason="...",
    supporting_factors=[...],
    warning_factors=[...],

    # Resumo executivo formatado
    executive_summary="..."
)
```

## Próximos Passos

1. Configure seu `.env` com credenciais MT5
2. Execute `python -m src.interfaces.cli.quantum_operator_cli`
3. Digite `analyze WIN$N`
4. Veja a decisão do Head Financeiro!

## Arquitetura

```
User Request
    ↓
Quantum Operator Engine
    ↓
┌───────────────────────────────────────┐
│  Macro → Fundamental → Sentiment      │
│     ↓         ↓           ↓           │
│  Technical Analysis                   │
│     ↓                                 │
│  Synthesis & Decision                 │
└───────────────────────────────────────┘
    ↓
Trading Decision (BUY/SELL/HOLD)
```

Todos componentes seguem Clean Architecture e SOLID principles!
