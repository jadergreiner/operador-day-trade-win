<!-- pyml disable md036 -->
<!-- pyml disable md040 -->

# Guia de Boas Práticas e Clean Code

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
    except Exception as e:
        logger.critical(f"Erro inesperado: {e}")
        raise TradingError("Erro ao executar ordem") from e
```

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
