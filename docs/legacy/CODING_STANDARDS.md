<!-- pyml disable md036 -->
<!-- pyml disable md040 -->

# Guia de Boas Práticas e Clean Code

⭐ **CORE DO PRODUTO**: Todos os scripts importados/chamados por [INICIAR_DIARIOS.bat](../INICIAR_DIARIOS.bat) e [INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat](../INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat) DEVEM seguir 100% destes padrões.

## Princípios Fundamentais

### 1. SOLID Principles

**S - Single Responsibility Principle**

```python
# ❌ Ruim - classe faz muitas coisas
class TradeManager:
    def get_market_data(self): ...
    def analyze_data(self): ...
    def execute_trade(self): ...
    def log_to_database(self): ...

# ✅ Bom - responsabilidades separadas
class MarketDataProvider:
    def get_market_data(self): ...

class MarketAnalyzer:
    def analyze_data(self): ...

class TradeExecutor:
    def execute_trade(self): ...

class TradeRepository:
    def save_trade(self): ...
```

**O - Open/Closed Principle**

```python
# ✅ Aberto para extensão, fechado para modificação
from abc import ABC, abstractmethod

class TradingStrategy(ABC):
    @abstractmethod
    def should_enter(self, market_data) -> bool:
        pass

class ScalpingStrategy(TradingStrategy):
    def should_enter(self, market_data) -> bool:
        return market_data.rsi < 30

class SwingStrategy(TradingStrategy):
    def should_enter(self, market_data) -> bool:
        return market_data.macd_cross_up()
```

**L - Liskov Substitution Principle**

```python
# ✅ Subclasses podem substituir classes base sem quebrar
class Order:
    def execute(self) -> bool:
        return True

class MarketOrder(Order):
    def execute(self) -> bool:
        # Implementação específica mas mantém contrato
        return super().execute()
```

**I - Interface Segregation Principle**

```python
# ✅ Interfaces específicas ao invés de uma genérica
class IMarketDataReader(ABC):
    @abstractmethod
    def read_tick_data(self): ...

class IMarketDataWriter(ABC):
    @abstractmethod
    def write_tick_data(self): ...

# Cliente usa apenas o que precisa
class Analyzer:
    def __init__(self, reader: IMarketDataReader):
        self.reader = reader
```

**D - Dependency Inversion Principle**

```python
# ❌ Ruim - dependência de implementação concreta
class TradeEngine:
    def __init__(self):
        self.mt5 = MetaTrader5()  # Dependência concreta

# ✅ Bom - dependência de abstração
class TradeEngine:
    def __init__(self, broker: IBrokerAdapter):
        self.broker = broker  # Dependência abstrata
```

### 2. Clean Code Principles

#### Nomenclatura Clara e Significativa

```python
# ❌ Ruim
def calc(d, p):
    return d * p * 0.1

# ✅ Bom
def calculate_position_size(
    available_capital: Decimal,
    risk_percentage: Decimal
) -> Decimal:
    """Calcula o tamanho da posição baseado no capital e risco."""
    return available_capital * risk_percentage * Decimal('0.1')
```

#### Funções Pequenas e Focadas

```python
# ❌ Ruim - função faz muitas coisas
def process_trade(data):
    candle = get_candle(data)
    if candle.close > candle.open:
        rsi = calculate_rsi(data)
        if rsi < 30:
            entry_price = candle.close
            stop_loss = entry_price * 0.98
            take_profit = entry_price * 1.04
            send_order(entry_price, stop_loss, take_profit)
            log_trade()

# ✅ Bom - funções pequenas e focadas
def process_trade_signal(market_data: MarketData) -> TradeSignal:
    """Processa dados e retorna sinal de trade."""
    if not is_bullish_candle(market_data):
        return TradeSignal.HOLD

    if is_oversold(market_data):
        return TradeSignal.BUY

    return TradeSignal.HOLD

def execute_trade(signal: TradeSignal, market_data: MarketData) -> Trade:
    """Executa trade baseado no sinal."""
    if signal == TradeSignal.BUY:
        order_params = calculate_order_parameters(market_data)
        return send_order(order_params)
```

#### Comentários Apenas Quando Necessário

```python
# ❌ Ruim - comentário redundante
def calculate_rsi(prices, period=14):
    # Calcula o RSI
    gains = []
    losses = []
    # Loop pelos preços
    for i in range(1, len(prices)):
        # Calcula a diferença
        diff = prices[i] - prices[i-1]
        ...

# ✅ Bom - código auto-explicativo
def calculate_rsi(
    prices: List[Decimal],
    period: int = 14
) -> Decimal:
    """
    Calcula Relative Strength Index.

    RSI = 100 - (100 / (1 + RS))
    onde RS = média de ganhos / média de perdas
    """
    gains, losses = separate_gains_and_losses(prices)
    avg_gain = calculate_exponential_average(gains, period)
    avg_loss = calculate_exponential_average(losses, period)

    return calculate_rsi_from_averages(avg_gain, avg_loss)
```

### 3. Type Hints Obrigatórios

```python
from typing import List, Optional, Dict, Tuple
from decimal import Decimal
from datetime import datetime

# ✅ Sempre use type hints
def calculate_sharpe_ratio(
    returns: List[Decimal],
    risk_free_rate: Decimal = Decimal('0.0')
) -> Decimal:
    """Calcula Sharpe Ratio."""
    ...

class Trade:
    def __init__(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        price: Decimal,
        timestamp: datetime
    ) -> None:
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.price = price
        self.timestamp = timestamp
```

### 4. Domain-Driven Design

#### Value Objects

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Price:
    """Value Object para preço - imutável."""
    value: Decimal

    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Preço não pode ser negativo")

    def add(self, other: 'Price') -> 'Price':
        return Price(self.value + other.value)

@dataclass(frozen=True)
class Money:
    """Value Object para valores monetários."""
    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self):
        if self.currency != "BRL":
            raise ValueError("Apenas BRL suportado")
```

#### Entities

```python
from datetime import datetime
from typing import Optional

class Trade:
    """Entidade Trade com identidade única."""

    def __init__(
        self,
        trade_id: str,
        symbol: str,
        side: OrderSide,
        quantity: int,
        entry_price: Price,
        timestamp: datetime
    ):
        self.id = trade_id
        self.symbol = symbol
        self.side = side
        self.quantity = quantity
        self.entry_price = entry_price
        self.timestamp = timestamp
        self.exit_price: Optional[Price] = None
        self.status = TradeStatus.OPEN

    def close(self, exit_price: Price) -> None:
        """Fecha o trade."""
        if self.status != TradeStatus.OPEN:
            raise InvalidOperationError("Trade já está fechado")

        self.exit_price = exit_price
        self.status = TradeStatus.CLOSED

    def calculate_profit(self) -> Optional[Money]:
        """Calcula lucro/prejuízo."""
        if not self.exit_price:
            return None

        diff = self.exit_price.value - self.entry_price.value
        if self.side == OrderSide.SELL:
            diff = -diff

        profit = diff * self.quantity
        return Money(profit)
```

#### Aggregates

```python
class Portfolio:
    """Aggregate Root - gerencia trades e capital."""

    def __init__(self, initial_capital: Money):
        self._capital = initial_capital
        self._trades: List[Trade] = []
        self._open_positions: Dict[str, Trade] = {}

    def open_trade(self, trade: Trade) -> None:
        """Abre novo trade com validações de aggregate."""
        self._validate_sufficient_capital(trade)
        self._validate_risk_limits(trade)

        self._trades.append(trade)
        self._open_positions[trade.id] = trade

    def _validate_sufficient_capital(self, trade: Trade) -> None:
        required = trade.entry_price.value * trade.quantity
        if required > self._capital.amount:
            raise InsufficientCapitalError()

    @property
    def total_value(self) -> Money:
        """Valor total do portfolio."""
        ...
```

### 5. Repository Pattern

```python
from abc import ABC, abstractmethod
from typing import List, Optional

class ITradeRepository(ABC):
    """Interface do repositório de trades."""

    @abstractmethod
    def save(self, trade: Trade) -> None:
        """Persiste um trade."""
        pass

    @abstractmethod
    def find_by_id(self, trade_id: str) -> Optional[Trade]:
        """Busca trade por ID."""
        pass

    @abstractmethod
    def find_open_trades(self) -> List[Trade]:
        """Retorna todos trades abertos."""
        pass

class SqliteTradeRepository(ITradeRepository):
    """Implementação concreta usando SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def save(self, trade: Trade) -> None:
        # Implementação específica SQLite
        ...

    def find_by_id(self, trade_id: str) -> Optional[Trade]:
        # Implementação específica SQLite
        ...
```

### 6. Error Handling

```python
# ✅ Exceções customizadas
class TradingError(Exception):
    """Erro base para trading."""
    pass

class InsufficientCapitalError(TradingError):
    """Capital insuficiente para trade."""
    pass

class InvalidOrderError(TradingError):
    """Ordem inválida."""
    pass

class BrokerConnectionError(TradingError):
    """Erro de conexão com broker."""
    pass

class TerminalIsolationViolation(TradingError):
    """Violação de isolamento de terminal (broker diferente de Clear)."""
    pass

# ✅ Tratamento específico
def execute_order(order: Order) -> Trade:
    try:
        validate_order(order)
        return send_to_broker(order)
    except BrokerConnectionError as e:
        logger.error(f"Falha ao conectar broker: {e}")
        raise
    except InvalidOrderError as e:
        logger.warning(f"Ordem inválida: {e}")
        raise
    except TerminalIsolationViolation as e:
        logger.critical(f"❌ BLOQUEADO: {e}")
        sys.exit(1)  # HARD STOP - não continua
    except Exception as e:
        logger.critical(f"Erro inesperado: {e}")
        raise TradingError("Erro ao executar ordem") from e
```

### 6.5. Terminal Isolation Validation Pattern ✅ NOVO

**OBRIGATÓRIO:** Todo código que envia ordens DEVE validar isolamento de terminal ANTES.

```python
# ✅ Padrão obrigatório para execução segura
from src.infrastructure.terminal_isolation_enforcer import TerminalIsolationEnforcer

def execute_critical_operation(operation_name: str) -> None:
    """Valida isolamento antes de operação crítica."""
    enforcer = TerminalIsolationEnforcer(
        expected_terminal_path=settings.mt5_terminal_path
    )

    # ANTES de qualquer ação irreversível
    try:
        enforcer.validate_critical_operation(f"{operation_name}:entry")
    except TerminalIsolationViolation as e:
        logger.critical(f"❌ BLOQUEADO: {e}")
        raise  # Rejeita operação

    # Agora é SEGURO prosseguir
    logger.info(f"✅ Isolamento validado para {operation_name}")

# ✅ Uso em execute_entry()
def execute_entry(signal: SignalData) -> None:
    execute_critical_operation("execute_entry:send_order")

    # Após validação, é seguro enviar ordem
    order = create_order(signal)
    send_to_mt5(order)

# ✅ Uso em main loop (vigilância contínua)
def main_trading_loop():
    enforcer = TerminalIsolationEnforcer(
        expected_terminal_path=settings.mt5_terminal_path
    )

    while True:
        # Validação contínua
        enforcer.validate_continuous()  # KILL SWITCH se terminal muda

        # Resto da lógica
        signal = analyzer.analyze_market()
        if signal.should_trade:
            execute_entry(signal)
```

**Status de Compliance:**
- ✅ Obrigatório em todos os métodos que enviam ordens (execute_entry, etc)
- ✅ Documentado em [ARCHITECTURE.md § 4.5](ARCHITECTURE.md#45-terminal-isolation-enforcer-s2-6)
- ✅ Exemplos completos em [src/infrastructure/terminal_isolation_enforcer.py](../src/infrastructure/terminal_isolation_enforcer.py)
- ✅ Validações implementadas em [scripts/audit_terminal_isolation.py](../scripts/audit_terminal_isolation.py)

### 7. Logging e Observabilidade

```python
import logging
from typing import Any, Dict

# ✅ Structured logging
logger = logging.getLogger(__name__)

def execute_trade(signal: TradeSignal, market_data: MarketData) -> Trade:
    logger.info(
        "Executando trade",
        extra={
            "signal": signal.value,
            "symbol": market_data.symbol,
            "price": float(market_data.close),
            "timestamp": market_data.timestamp.isoformat()
        }
    )

    try:
        trade = create_and_send_order(signal, market_data)

        logger.info(
            "Trade executado com sucesso",
            extra={
                "trade_id": trade.id,
                "entry_price": float(trade.entry_price.value)
            }
        )

        return trade

    except TradingError as e:
        logger.error(
            "Falha ao executar trade",
            extra={
                "error": str(e),
                "signal": signal.value
            },
            exc_info=True
        )
        raise
```

### 8. Testing Best Practices

```python
import pytest
from decimal import Decimal
from datetime import datetime

# ✅ Testes claros e focados
class TestTradeExecution:
    """Suite de testes para execução de trades."""

    def test_should_execute_buy_order_when_signal_is_buy(self):
        # Arrange
        signal = TradeSignal.BUY
        market_data = create_market_data(price=Decimal('100.0'))
        executor = TradeExecutor(MockBroker())

        # Act
        trade = executor.execute(signal, market_data)

        # Assert
        assert trade.side == OrderSide.BUY
        assert trade.entry_price.value == Decimal('100.0')

    def test_should_raise_error_when_insufficient_capital(self):
        # Arrange
        portfolio = Portfolio(initial_capital=Money(Decimal('100.0')))
        large_trade = create_trade(required_capital=Decimal('200.0'))

        # Act & Assert
        with pytest.raises(InsufficientCapitalError):
            portfolio.open_trade(large_trade)
```

### 9. Configuration Management

```python
from pydantic import BaseSettings, Field
from typing import Optional

# ✅ Configuração tipada e validada
class TradingConfig(BaseSettings):
    """Configurações do sistema de trading."""

    # MT5 Configuration
    mt5_login: int = Field(..., env='MT5_LOGIN')
    mt5_password: str = Field(..., env='MT5_PASSWORD')
    mt5_server: str = Field(..., env='MT5_SERVER')

    # Trading Parameters
    symbol: str = Field(default='WIN$N', env='TRADING_SYMBOL')
    max_positions: int = Field(default=2, ge=1, le=5)
    risk_per_trade: Decimal = Field(default=Decimal('0.02'), ge=0, le=1)

    # Database
    db_path: str = Field(default='data/trading.db', env='DB_PATH')

    # Logging
    log_level: str = Field(default='INFO', env='LOG_LEVEL')

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'

# Uso
config = TradingConfig()
```

### 10. Code Organization

```
src/
├── domain/              # Entidades, Value Objects, Aggregates
│   ├── entities/
│   ├── value_objects/
│   └── exceptions/
├── application/         # Use Cases e Services
│   ├── services/
│   └── use_cases/
├── infrastructure/      # Implementações concretas
│   ├── repositories/
│   ├── adapters/
│   └── external/
└── interfaces/          # Controllers, APIs
    └── cli/
```

### 11. Scripts - Padrão de Localização Obrigatório ⭐

**TODOS os scripts Python (análise, utilitários, execução) DEVEM estar em `scripts/`**

```
scripts/
├── analise_*.py          # Scripts de análise (consultoria/diagnóstico)
├── analyze_*.py          # Scripts de análise detalhada
├── run_*.py              # Scripts de execução (main entry points)
├── launch_*.py           # Scripts de inicialização de agentes
├── check_*.py            # Scripts de verificação/validação
├── cleanup_*.py          # Scripts de limpeza de dados/logs
├── verify_*.py           # Scripts de auditoria/verificação
├── extract_*.py          # Scripts de extração de dados
├── sync_*.py             # Scripts de sincronização
├── monitor_*.py          # Scripts de monitoramento
└── README.md             # Documentação dos scripts disponíveis
```

**Benefícios:**
- ✅ Evita poluição da raiz do projeto
- ✅ Fácil localização de scripts (CI/CD escaneia `scripts/`)
- ✅ Padrão consistente com Single Responsibility Principle
- ✅ Clareza de propósito (nome começa com ação clara)
- ✅ Organização por categoria (analise, run, check, etc)

**Convenção de Naming:**
- Sempre use **snake_case** (ex: `analise_rl_training.py`)
- Comece com **verbo/ação** (analise, run, check, verify, cleanup)
- Inclua **contexto** (rl, sqlite, critical_failure)
- NUNCA coloque scripts na raiz (exceto se temporário com justificativa em PR)

## 📚 Exemplos de Implementação Real

### AC1: SignalGenerator (06/03/2026) ✅ EXEMPLARY IMPLEMENTATION

**Localização:** `src/domain/signal_generator.py` (449 LOC)

Este módulo exemplifica as melhores práticas descritas acima:

**Padrões Implementados:**
- ✅ **SOLID**:
  - Single Responsibility: Cada método detecta um padrão SMC específico
  - Open/Closed: Fácil adicionar novos detectores sem modificar classe base
  - Liskov: Signal e Candle são value objects que substituem dados brutos
  - Interface Segregation: Métodos específicos (detect_bos, detect_choch, detect_fvg)
  - Dependency Inversion: Aceita MarketContext como parâmetro (não hardcoded)

- ✅ **Type Hints:** 100% coverage (mypy --strict OK)
- ✅ **Docstrings:** Completas com exemplos e parâmetros
- ✅ **Domain-Driven Design:** Signal é value object imutável (dataclass frozen=True)
- ✅ **Error Handling:** Validação de confluence com logging
- ✅ **Testing:** 6/6 integration tests PASSED (AC1→AC6 pipeline validation)

**Estrutura das Classes:**
```python
@dataclass(frozen=True)
class Signal:
    signal_id: str           # UUID para rastreamento
    timestamp: datetime
    symbol: str
    signal_type: str         # BUY, SELL, HOLD
    smc_score: float         # [-3, +3] range
    smc_detector: str        # BOS, CHoCH, FVG, IMPULSE
    entry_price: float
    candle_index: int
    market_context: MarketContext

@dataclass(frozen=True)
class MarketContext:
    rsi: float
    atr: float
    bb_upper: float
    bb_lower: float
    volume: int
    spread: float
    trend_direction: str
    last_close: float
```

**Métodos Exemplo:**
```python
def generate_signal(
    self,
    symbol: str,
    signal_type: str,
    smc_score: float,
    smc_detector: str,
    entry_price: float,
    candle_index: int,
    market_context: MarketContext
) -> Signal:
    """
    AC1.4: Generates signal with full market context.

    Returns Signal dataclass with UUID and timestamp.
    """
    return Signal(
        signal_id=f"SIG-{uuid4().hex[:8].upper()}",
        timestamp=datetime.now(tz=timezone.utc),
        symbol=symbol,
        signal_type=signal_type,
        smc_score=smc_score,
        smc_detector=smc_detector,
        entry_price=entry_price,
        candle_index=candle_index,
        market_context=market_context
    )
```

**Como Usar como Referência:**
1. Quando implementar novos detectores, siga estrutura AC1
2. Use AC1 como template para novos Value Objects
3. Aplique padrão de type hints em AC1 a todo novo código
4. Referencie commit 29a9353 para arquitetura padrão

**Métricas de Qualidade:**
- LOC: 449 (production ready)
- Type Coverage: 100%
- Test Coverage: 6/6 scenarios PASSED
- Mypy Checklist: ✅ Clean (strict mode)
- Docstring Coverage: 100%

## Code Review Checklist


- [ ] Código segue princípios SOLID
- [ ] Funções têm responsabilidade única
- [ ] Type hints em todas funções e métodos
- [ ] Nomenclatura clara e significativa
- [ ] Tratamento de erros adequado
- [ ] Logging estruturado implementado
- [ ] Testes unitários escritos (>80% coverage)
- [ ] Documentação (docstrings) presente
- [ ] Sem código comentado (remover)
- [ ] Sem magic numbers (usar constantes)
- [ ] Configurações em variáveis de ambiente
- [ ] Validação de dados de entrada
---

## 🔗 Referências Arquiteturais

### Documentos Relacionados (Integridade Referencial)

Quando implementar código, consulte também:

| Documento | Quando Consultar |
|-----------|------------------|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Entender contexto geral (estrutura de camadas) |
| **[DIAGRAMA_CLASSES.md](DIAGRAMA_CLASSES.md)** | Implementar novas classes ou padrões |
| **[REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md)** | Validar código contra 13 regras (6 críticas) |
| **[DIAGRAMA_DADOS.md](DIAGRAMA_DADOS.md)** | Ao trabalhar com modelos de dados |
| **[MODELAGEM_DADOS.md](MODELAGEM_DADOS.md)** | Implementar persistência em SQLite |
| **[ADRS.md](ADRS.md)** | Entender por quê cada decisão arquitetural |
| **[DATA_MODELS.md](DATA_MODELS.md)** | Descrição das entidades de dados |
| **[CONTRIBUTING.md](CONTRIBUTING.md)** | Processo de contribuição completo |

### Pre-Commit Validation

Antes de fazer commit, validar:

1. **Type Checking** (OBRIGATÓRIO):
   ```bash
   mypy src/ --strict
   ```

2. **Code Format** (OBRIGATÓRIO):
   ```bash
   black src/ --check
   isort src/ --check
   ```

3. **SOLID Compliance** (MANUAL):
   Verificar contra princípios em seção "SOLID Principles" acima

4. **REGRAS_NEGOCIO Compliance** (MANUAL):
   Validar contra [REGRAS_NEGOCIO.md](REGRAS_NEGOCIO.md)

5. **Test Coverage** (OBRIGATÓRIO):
   ```bash
   pytest --cov=src --cov-report=term-missing
   ```
   Mínimo 80% coverage

