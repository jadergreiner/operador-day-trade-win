"""Entidade Portfolio - raiz agregada para gerenciamento de capital e trades."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from src.domain.entities.trade import Position, Trade
from src.domain.enums.trading_enums import OrderSide
from src.domain.exceptions import InsufficientCapitalError, InvalidOperationError
from src.domain.value_objects import Money, Percentage, Symbol


@dataclass
class Portfolio:
    """
    Raiz Agregada - gerencia trades, posicoes e capital.

    Aplica regras de negocio e invariantes relacionados a operacoes.
    """

    initial_capital: Money
    portfolio_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.now)
    _current_capital: Money = field(init=False)
    _positions: dict[str, Position] = field(default_factory=dict)
    _trade_history: list[Trade] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Inicializa o estado do portfolio."""
        self._current_capital = self.initial_capital

    @property
    def current_capital(self) -> Money:
        """Obtem capital atual."""
        return self._current_capital

    @property
    def positions(self) -> list[Position]:
        """Obtem todas as posicoes."""
        return list(self._positions.values())

    @property
    def open_positions(self) -> list[Position]:
        """Obtem apenas posicoes abertas."""
        return [p for p in self._positions.values() if p.is_open()]

    @property
    def trade_history(self) -> list[Trade]:
        """Obtem historico completo de trades."""
        return self._trade_history.copy()

    def open_trade(
        self,
        trade: Trade,
        risk_percentage: Percentage,
        max_positions: int = 2,
    ) -> None:
        """
        Abre um novo trade com validacao.

        Args:
            trade: Trade a ser aberto
            risk_percentage: Risco maximo por trade
            max_positions: Numero maximo de posicoes abertas

        Raises:
            InsufficientCapitalError: Se nao houver capital suficiente
            InvalidOperationError: Se os limites de risco forem excedidos
        """
        self._validate_max_positions(max_positions)
        self._validate_sufficient_capital(trade, risk_percentage)

        # Adiciona ao historico de trades
        self._trade_history.append(trade)

        # Adiciona a posicao existente ou cria nova
        position_key = f"{trade.symbol.code}_{trade.side.value}"

        if position_key in self._positions:
            self._positions[position_key].add_trade(trade)
        else:
            position = Position(symbol=trade.symbol, side=trade.side)
            position.add_trade(trade)
            self._positions[position_key] = position

    def close_trade(self, trade: Trade, exit_price) -> None:
        """Fecha um trade e atualiza o capital."""
        if trade not in self._trade_history:
            raise InvalidOperationError("Trade not found in portfolio")

        trade.close(exit_price)

        # Atualiza o capital com base no lucro/prejuizo
        pl = trade.calculate_profit_loss()
        if pl:
            self._current_capital = self._current_capital.add(pl)

        # Verifica se a posicao deve ser removida
        self._cleanup_closed_positions()

    def calculate_total_value(self) -> Money:
        """
        Calcula o valor total do portfolio (capital + lucro/prejuizo nao realizado).

        Isso requer precos de mercado atuais para posicoes abertas.
        Por enquanto, retorna o capital atual.
        """
        # TODO: Adicionar calculo de lucro/prejuizo nao realizado quando dados de mercado estiverem disponiveis
        return self._current_capital

    def calculate_total_return(self) -> Percentage:
        """Calcula o retorno total em percentual."""
        current_value = self.calculate_total_value()
        return_value = (
            current_value.amount - self.initial_capital.amount
        ) / self.initial_capital.amount
        return Percentage(return_value)

    def calculate_win_rate(self) -> Optional[Decimal]:
        """Calcula a taxa de acerto a partir dos trades fechados."""
        closed_trades = [t for t in self._trade_history if not t.is_open()]

        if not closed_trades:
            return None

        winning_trades = sum(
            1 for t in closed_trades if t.is_profitable() is True
        )
        return Decimal(winning_trades) / Decimal(len(closed_trades))

    def calculate_average_profit(self) -> Optional[Money]:
        """Calcula o lucro medio dos trades vencedores."""
        winning_trades = [
            t
            for t in self._trade_history
            if not t.is_open() and t.is_profitable() is True
        ]

        if not winning_trades:
            return None

        total_profit = sum(
            t.calculate_profit_loss().amount  # type: ignore
            for t in winning_trades
        )
        avg = total_profit / len(winning_trades)
        return Money(avg)

    def calculate_average_loss(self) -> Optional[Money]:
        """Calcula o prejuizo medio dos trades perdedores."""
        losing_trades = [
            t
            for t in self._trade_history
            if not t.is_open() and t.is_profitable() is False
        ]

        if not losing_trades:
            return None

        total_loss = sum(
            t.calculate_profit_loss().amount  # type: ignore
            for t in losing_trades
        )
        avg = total_loss / len(losing_trades)
        return Money(avg)

    def calculate_max_drawdown(self) -> Percentage:
        """
        Calcula o drawdown maximo em percentual.

        Esta e uma versao simplificada. Uma implementacao completa
        rastrearia o valor do portfolio ao longo do tempo.
        """
        # Simplificado: compara atual com inicial
        if self._current_capital.amount >= self.initial_capital.amount:
            return Percentage(Decimal("0"))

        drawdown = (
            self.initial_capital.amount - self._current_capital.amount
        ) / self.initial_capital.amount
        return Percentage(drawdown)

    def _validate_max_positions(self, max_positions: int) -> None:
        """Valida que o limite maximo de posicoes nao foi excedido."""
        if len(self.open_positions) >= max_positions:
            raise InvalidOperationError(
                f"Maximum positions ({max_positions}) already open"
            )

    def _validate_sufficient_capital(
        self, trade: Trade, risk_percentage: Percentage
    ) -> None:
        """Valida que ha capital suficiente para o trade."""
        required_capital = trade.entry_price.value * trade.quantity.value

        # Verifica se ha capital suficiente
        if required_capital > self._current_capital.amount:
            raise InsufficientCapitalError(
                f"Insufficient capital. Required: {required_capital}, "
                f"Available: {self._current_capital.amount}"
            )

        # Verifica se o risco esta dentro dos limites
        if trade.stop_loss:
            potential_loss = abs(
                trade.entry_price.value - trade.stop_loss.value
            ) * trade.quantity.value

            max_risk = risk_percentage.of(self._current_capital)

            if potential_loss > max_risk.amount:
                raise InvalidOperationError(
                    f"Trade risk ({potential_loss}) exceeds maximum "
                    f"allowed risk ({max_risk.amount})"
                )

    def _cleanup_closed_positions(self) -> None:
        """Remove posicoes que nao possuem trades abertos."""
        to_remove = [
            key for key, pos in self._positions.items() if not pos.is_open()
        ]

        for key in to_remove:
            del self._positions[key]

    def __eq__(self, other: object) -> bool:
        """Portfolios sao iguais se possuem o mesmo portfolio_id."""
        if not isinstance(other, Portfolio):
            return False
        return self.portfolio_id == other.portfolio_id

    def __hash__(self) -> int:
        """Hash baseado no portfolio_id."""
        return hash(self.portfolio_id)
