"""Entidades de dominio - objetos com identidade."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from src.domain.enums.trading_enums import OrderSide, OrderType, TradeStatus
from src.domain.exceptions import InvalidOperationError
from src.domain.value_objects import Money, Price, Quantity, Symbol


@dataclass
class Order:
    """
    Entidade representando uma ordem de trading.

    Possui identidade (order_id) e ciclo de vida.
    """

    symbol: Symbol
    side: OrderSide
    quantity: Quantity
    order_type: OrderType
    price: Optional[Price] = None
    stop_loss: Optional[Price] = None
    take_profit: Optional[Price] = None
    close_position_ticket: Optional[int] = None
    order_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
    broker_order_id: Optional[str] = None

    def __post_init__(self) -> None:
        """Valida ordem apos inicializacao."""
        if self.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            if not self.price:
                raise InvalidOperationError(
                    f"Price required for {self.order_type} orders"
                )

    def set_broker_order_id(self, broker_order_id: str) -> None:
        """Define o ID da ordem na corretora apos envio."""
        self.broker_order_id = broker_order_id

    def __eq__(self, other: object) -> bool:
        """Ordens sao iguais se possuem o mesmo order_id."""
        if not isinstance(other, Order):
            return False
        return self.order_id == other.order_id

    def __hash__(self) -> int:
        """Hash baseado no order_id."""
        return hash(self.order_id)


@dataclass
class Trade:
    """
    Entidade representando um trade concluido ou em andamento.

    Possui identidade (trade_id) e ciclo de vida da abertura ao fechamento.
    """

    symbol: Symbol
    side: OrderSide
    quantity: Quantity
    entry_price: Price
    entry_time: datetime
    trade_id: UUID = field(default_factory=uuid4)
    exit_price: Optional[Price] = None
    exit_time: Optional[datetime] = None
    stop_loss: Optional[Price] = None
    take_profit: Optional[Price] = None
    status: TradeStatus = TradeStatus.OPEN
    broker_trade_id: Optional[str] = None
    commission: Money = field(default_factory=lambda: Money(Decimal("0")))
    notes: str = ""

    def close(
        self, exit_price: Price, exit_time: Optional[datetime] = None
    ) -> None:
        """Fecha o trade."""
        if self.status != TradeStatus.OPEN:
            raise InvalidOperationError(
                f"Cannot close trade with status {self.status}"
            )

        self.exit_price = exit_price
        self.exit_time = exit_time or datetime.now()
        self.status = TradeStatus.CLOSED

    def cancel(self) -> None:
        """Cancela o trade."""
        if self.status == TradeStatus.CLOSED:
            raise InvalidOperationError("Cannot cancel closed trade")

        self.status = TradeStatus.CANCELLED

    def calculate_profit_loss(self) -> Optional[Money]:
        """
        Calcula lucro ou prejuizo do trade.

        Retorna None se o trade nao estiver fechado.
        """
        if not self.exit_price or self.status != TradeStatus.CLOSED:
            return None

        # Calcula diferenca de preco
        price_diff = self.exit_price.value - self.entry_price.value

        # Ajusta pelo lado da operacao (SELL significa lucro quando o preco cai)
        if self.side == OrderSide.SELL:
            price_diff = -price_diff

        # Calcula P&L
        gross_pl = price_diff * self.quantity.value
        net_pl = gross_pl - self.commission.amount

        return Money(net_pl)

    def calculate_return_percentage(self) -> Optional[Decimal]:
        """Calcula percentual de retorno baseado no preco de entrada."""
        if not self.exit_price or self.status != TradeStatus.CLOSED:
            return None

        price_diff = self.exit_price.value - self.entry_price.value
        if self.side == OrderSide.SELL:
            price_diff = -price_diff

        return (price_diff / self.entry_price.value) * 100

    def is_open(self) -> bool:
        """Verifica se o trade esta aberto."""
        return self.status == TradeStatus.OPEN

    def is_profitable(self) -> Optional[bool]:
        """Verifica se o trade esta lucrativo. Retorna None se nao estiver fechado."""
        pl = self.calculate_profit_loss()
        if pl is None:
            return None
        return pl.is_positive()

    def __eq__(self, other: object) -> bool:
        """Trades sao iguais se possuem o mesmo trade_id."""
        if not isinstance(other, Trade):
            return False
        return self.trade_id == other.trade_id

    def __hash__(self) -> int:
        """Hash baseado no trade_id."""
        return hash(self.trade_id)


@dataclass
class Position:
    """
    Entidade representando uma posicao aberta (agregacao de trades).

    Uma posicao pode consistir em multiplos trades na mesma direcao.
    """

    symbol: Symbol
    side: OrderSide
    position_id: UUID = field(default_factory=uuid4)
    trades: list[Trade] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def add_trade(self, trade: Trade) -> None:
        """Adiciona um trade a posicao."""
        if trade.symbol != self.symbol:
            raise InvalidOperationError(
                f"Trade symbol {trade.symbol} doesn't match position symbol {self.symbol}"
            )

        if trade.side != self.side:
            raise InvalidOperationError(
                f"Trade side {trade.side} doesn't match position side {self.side}"
            )

        self.trades.append(trade)

    def total_quantity(self) -> Quantity:
        """Calcula quantidade total de todos os trades."""
        total = sum(trade.quantity.value for trade in self.trades if trade.is_open())
        return Quantity(total) if total > 0 else Quantity(1)

    def average_entry_price(self) -> Price:
        """Calcula preco medio ponderado de entrada."""
        open_trades = [t for t in self.trades if t.is_open()]

        if not open_trades:
            raise InvalidOperationError("No open trades in position")

        total_value = sum(
            trade.entry_price.value * trade.quantity.value for trade in open_trades
        )
        total_quantity = sum(trade.quantity.value for trade in open_trades)

        return Price(total_value / total_quantity)

    def calculate_unrealized_pl(self, current_price: Price) -> Money:
        """Calcula P&L nao realizado baseado no preco atual."""
        open_trades = [t for t in self.trades if t.is_open()]

        total_pl = Decimal("0")
        for trade in open_trades:
            price_diff = current_price.value - trade.entry_price.value
            if trade.side == OrderSide.SELL:
                price_diff = -price_diff

            pl = price_diff * trade.quantity.value
            total_pl += pl

        return Money(total_pl)

    def close_position(self, exit_price: Price) -> None:
        """Fecha todos os trades abertos na posicao."""
        exit_time = datetime.now()
        for trade in self.trades:
            if trade.is_open():
                trade.close(exit_price, exit_time)

    def is_open(self) -> bool:
        """Verifica se a posicao possui algum trade aberto."""
        return any(trade.is_open() for trade in self.trades)

    def __eq__(self, other: object) -> bool:
        """Posicoes sao iguais se possuem o mesmo position_id."""
        if not isinstance(other, Position):
            return False
        return self.position_id == other.position_id

    def __hash__(self) -> int:
        """Hash baseado no position_id."""
        return hash(self.position_id)
