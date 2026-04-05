"""Entidade Portfolio - raiz agregada para gerenciamento de capital e trades."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from src.domain.entities.trade import Position, Trade
from src.domain.enums.trading_enums import OrderSide
from src.domain.exceptions import InsufficientCapitalError, InvalidOperationError
from src.domain.value_objects import Money, Percentage, Price, Symbol

logger = logging.getLogger(__name__)


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

    def close_trade(self, trade: Trade, exit_price: Price) -> None:
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

    def calculate_unrealized_pnl(
        self,
        current_prices: dict[str, Price],
    ) -> Money:
        """
        Calcula o P&L nao realizado de todas as posicoes abertas.

        Para cada posicao aberta, busca o preco atual pelo simbolo.
        Posicoes sem preco disponivel sao ignoradas com aviso em log.

        Args:
            current_prices: Mapa de simbolo -> preco atual (ex: {"WIN$N": Price(...)})

        Returns:
            Money com o P&L nao realizado total (pode ser negativo)
        """
        total_unrealized = Decimal("0")

        for position in self.open_positions:
            symbol_code = position.symbol.code
            current_price = current_prices.get(symbol_code)

            if current_price is None:
                logger.warning(
                    "pnl_nao_realizado | simbolo=%s | preco_atual=indisponivel"
                    " | posicao ignorada",
                    symbol_code,
                )
                continue

            pl = position.calculate_unrealized_pl(current_price)
            total_unrealized += pl.amount

            logger.info(
                "pnl_nao_realizado | simbolo=%s | preco_atual=%.2f"
                " | pl_nao_realizado=%.2f",
                symbol_code,
                float(current_price.value),
                float(pl.amount),
            )

        return Money(total_unrealized)

    def calculate_total_value(
        self,
        current_prices: Optional[dict[str, Price]] = None,
    ) -> Money:
        """
        Calcula o valor total do portfolio (capital realizado + P&L nao realizado).

        Quando ``current_prices`` e fornecido, soma o P&L nao realizado das
        posicoes abertas ao capital atual.  Sem precos, retorna apenas o
        capital realizado (comportamento anterior, retrocompativel).

        Args:
            current_prices: Mapa de simbolo -> preco atual obtido do MT5.
                            Exemplo: {"WIN$N": Price(Decimal("128500"))}

        Returns:
            Money representando o valor total do portfolio
        """
        if not current_prices:
            return self._current_capital

        unrealized = self.calculate_unrealized_pnl(current_prices)

        total = self._current_capital.amount + unrealized.amount

        logger.info(
            "portfolio_total_value | capital_realizado=%.2f"
            " | pnl_nao_realizado=%.2f | total=%.2f",
            float(self._current_capital.amount),
            float(unrealized.amount),
            float(total),
        )

        return Money(total)

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
        return Money(Decimal(str(avg)))

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
        return Money(Decimal(str(avg)))

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
