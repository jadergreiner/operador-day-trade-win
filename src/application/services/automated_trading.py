"""
Automated Trading Engine - Executa operacoes automaticamente no MT5.

Sistema completo de trading automatizado:
- Analisa mercado usando Quantum Operator
- Executa ordens automaticamente no MT5
- Gerencia posicoes abertas
- Implementa stop loss e take profit
- Gestao de risco rigorosa
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.domain.entities.trade import Order
from src.domain.enums.trading_enums import OrderSide, OrderType, TradeSignal
from src.domain.value_objects import Symbol, Price, Quantity


@dataclass
class TradingPosition:
    """Posicao aberta no mercado."""

    ticket: str
    symbol: Symbol
    side: OrderSide
    entry_price: Price
    quantity: Quantity
    stop_loss: Price
    take_profit: Price
    opened_at: datetime
    unrealized_pnl: Decimal = Decimal("0")


@dataclass
class TradingResult:
    """Resultado de uma operacao."""

    ticket: str
    symbol: Symbol
    side: OrderSide
    entry_price: Price
    exit_price: Price
    quantity: Quantity
    pnl: Decimal
    pnl_percent: Decimal
    duration_seconds: int
    exit_reason: str  # "STOP_LOSS", "TAKE_PROFIT", "TRAILING_STOP", "MANUAL"


class AutomatedTradingEngine:
    """
    Engine de trading automatizado.

    Responsabilidades:
    - Analisar mercado continuamente
    - Decidir quando entrar/sair
    - Executar ordens no MT5
    - Gerenciar posicoes abertas
    - Ajustar stops dinamicamente
    - Calcular position sizing
    """

    def __init__(
        self,
        mt5_adapter,
        quantum_operator,
        max_positions: int = 1,
        risk_per_trade: Decimal = Decimal("0.02"),  # 2% por trade
        min_confidence: Decimal = Decimal("0.70"),  # 70% confianca minima
        min_alignment: Decimal = Decimal("0.75"),  # 75% alinhamento minimo
        use_trailing_stop: bool = True,
        trailing_distance_percent: Decimal = Decimal("0.5"),  # 0.5% trailing
    ):
        self.mt5 = mt5_adapter
        self.operator = quantum_operator
        self.max_positions = max_positions
        self.risk_per_trade = risk_per_trade
        self.min_confidence = min_confidence
        self.min_alignment = min_alignment
        self.use_trailing_stop = use_trailing_stop
        self.trailing_distance_percent = trailing_distance_percent

        self.open_positions: list[TradingPosition] = []
        self.closed_trades: list[TradingResult] = []

    def can_open_position(self) -> bool:
        """Check if we can open a new position."""
        return len(self.open_positions) < self.max_positions

    def should_enter_trade(
        self,
        signal: TradeSignal,
        confidence: Decimal,
        alignment: Decimal,
    ) -> bool:
        """
        Decide if we should enter a trade.

        Criteria:
        - Signal is BUY or SELL (not HOLD)
        - Confidence >= min_confidence
        - Alignment >= min_alignment
        - We have room for more positions
        """

        if signal == TradeSignal.HOLD:
            return False

        if confidence < self.min_confidence:
            return False

        if alignment < self.min_alignment:
            return False

        if not self.can_open_position():
            return False

        return True

    def calculate_position_size(
        self,
        symbol: Symbol,
        entry_price: Price,
        stop_loss: Price,
        account_balance: Decimal,
    ) -> int:
        """
        Calculate position size based on risk management.

        Uses fixed risk per trade (e.g., 2% of account).

        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            account_balance: Current account balance

        Returns:
            Number of contracts to trade
        """

        # Calculate risk amount in currency
        risk_amount = account_balance * self.risk_per_trade

        # Calculate risk per contract
        risk_per_contract = abs(entry_price.value - stop_loss.value)

        if risk_per_contract == 0:
            return 1  # Minimum 1 contract

        # Calculate number of contracts
        contracts = int(risk_amount / risk_per_contract)

        # Always at least 1 contract, but limited
        return max(1, min(contracts, 10))  # Max 10 contracts per trade

    def execute_entry(
        self,
        symbol: Symbol,
        signal: TradeSignal,
        entry_price: Price,
        stop_loss: Price,
        take_profit: Price,
        quantity: Quantity,
    ) -> Optional[str]:
        """
        Execute entry order in MT5.

        Args:
            symbol: Trading symbol
            signal: BUY or SELL
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            quantity: Number of contracts

        Returns:
            Ticket number if successful, None otherwise
        """

        side = OrderSide.BUY if signal == TradeSignal.BUY else OrderSide.SELL

        order = Order(
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        try:
            ticket = self.mt5.send_order(order)

            if ticket:
                # Save position
                position = TradingPosition(
                    ticket=ticket,
                    symbol=symbol,
                    side=side,
                    entry_price=entry_price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    opened_at=datetime.now(),
                )

                self.open_positions.append(position)

                return ticket

        except Exception as e:
            print(f"[ERRO] Falha ao executar ordem: {e}")

        return None

    def execute_exit(
        self,
        position: TradingPosition,
        exit_price: Price,
        exit_reason: str,
    ) -> bool:
        """
        Execute exit order (close position).

        Args:
            position: Position to close
            exit_price: Exit price
            exit_reason: Reason for exit

        Returns:
            True if successful
        """

        # Close order is opposite side
        close_side = OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY

        order = Order(
            symbol=position.symbol,
            side=close_side,
            order_type=OrderType.MARKET,
            quantity=position.quantity,
            price=exit_price,
        )

        try:
            ticket = self.mt5.send_order(order)

            if ticket:
                # Calculate PnL
                if position.side == OrderSide.BUY:
                    pnl = (exit_price.value - position.entry_price.value) * position.quantity.value
                else:
                    pnl = (position.entry_price.value - exit_price.value) * position.quantity.value

                pnl_percent = (pnl / position.entry_price.value) * 100

                duration = (datetime.now() - position.opened_at).total_seconds()

                # Save result
                result = TradingResult(
                    ticket=position.ticket,
                    symbol=position.symbol,
                    side=position.side,
                    entry_price=position.entry_price,
                    exit_price=exit_price,
                    quantity=position.quantity,
                    pnl=pnl,
                    pnl_percent=pnl_percent,
                    duration_seconds=int(duration),
                    exit_reason=exit_reason,
                )

                self.closed_trades.append(result)

                # Remove from open positions
                self.open_positions.remove(position)

                return True

        except Exception as e:
            print(f"[ERRO] Falha ao fechar posicao: {e}")

        return False

    def update_position_pnl(self, position: TradingPosition, current_price: Price):
        """Update unrealized PnL for open position."""

        if position.side == OrderSide.BUY:
            pnl = (current_price.value - position.entry_price.value) * position.quantity.value
        else:
            pnl = (position.entry_price.value - current_price.value) * position.quantity.value

        position.unrealized_pnl = pnl

    def check_stop_loss_hit(
        self,
        position: TradingPosition,
        current_price: Price,
    ) -> bool:
        """Check if stop loss was hit."""

        if position.side == OrderSide.BUY:
            return current_price.value <= position.stop_loss.value
        else:
            return current_price.value >= position.stop_loss.value

    def check_take_profit_hit(
        self,
        position: TradingPosition,
        current_price: Price,
    ) -> bool:
        """Check if take profit was hit."""

        if position.side == OrderSide.BUY:
            return current_price.value >= position.take_profit.value
        else:
            return current_price.value <= position.take_profit.value

    def update_trailing_stop(
        self,
        position: TradingPosition,
        current_price: Price,
    ):
        """Update trailing stop loss."""

        if not self.use_trailing_stop:
            return

        trailing_distance = current_price.value * (self.trailing_distance_percent / 100)

        if position.side == OrderSide.BUY:
            # For long, move stop up if price moves up
            new_stop = current_price.value - trailing_distance

            if new_stop > position.stop_loss.value:
                position.stop_loss = Price(Decimal(str(new_stop)))

        else:
            # For short, move stop down if price moves down
            new_stop = current_price.value + trailing_distance

            if new_stop < position.stop_loss.value:
                position.stop_loss = Price(Decimal(str(new_stop)))

    def manage_open_positions(self, current_price: Price):
        """
        Manage all open positions.

        - Update PnL
        - Check stops
        - Update trailing stops
        - Execute exits if needed
        """

        positions_to_close = []

        for position in self.open_positions:
            # Update PnL
            self.update_position_pnl(position, current_price)

            # Check stop loss
            if self.check_stop_loss_hit(position, current_price):
                positions_to_close.append((position, "STOP_LOSS"))
                continue

            # Check take profit
            if self.check_take_profit_hit(position, current_price):
                positions_to_close.append((position, "TAKE_PROFIT"))
                continue

            # Update trailing stop
            self.update_trailing_stop(position, current_price)

        # Execute exits
        for position, reason in positions_to_close:
            self.execute_exit(position, current_price, reason)

    def get_daily_pnl(self) -> Decimal:
        """Get total PnL for the day."""

        # Closed trades PnL
        closed_pnl = sum(t.pnl for t in self.closed_trades)

        # Open positions unrealized PnL
        open_pnl = sum(p.unrealized_pnl for p in self.open_positions)

        return closed_pnl + open_pnl

    def get_win_rate(self) -> Decimal:
        """Calculate win rate from closed trades."""

        if not self.closed_trades:
            return Decimal("0")

        winners = sum(1 for t in self.closed_trades if t.pnl > 0)
        return Decimal(str(winners)) / Decimal(str(len(self.closed_trades))) * 100

    def get_statistics(self, mt5_positions=None) -> dict:
        """Get trading statistics including MT5 external positions."""

        closed_total = len(self.closed_trades)
        winners = sum(1 for t in self.closed_trades if t.pnl > 0)
        losers = sum(1 for t in self.closed_trades if t.pnl < 0)

        total_pnl = sum(t.pnl for t in self.closed_trades)
        win_rate = (winners / closed_total * 100) if closed_total > 0 else 0

        avg_win = (
            sum(t.pnl for t in self.closed_trades if t.pnl > 0) / winners
            if winners > 0 else 0
        )

        avg_loss = (
            sum(t.pnl for t in self.closed_trades if t.pnl < 0) / losers
            if losers > 0 else 0
        )

        # Contabilizacao de posicoes abertas (Engine + MT5 Externo)
        open_count = len(self.open_positions)
        if mt5_positions:
            # Conta tickets unicos que ja nao estao na engine
            engine_tickets = {p.ticket for p in self.open_positions}
            mt5_count = sum(1 for p in mt5_positions if str(p.ticket) not in engine_tickets)
            open_count += mt5_count

        return {
            "total_trades": closed_total,
            "winners": winners,
            "losers": losers,
            "win_rate": win_rate,
            "total_pnl": float(total_pnl),
            "avg_win": float(avg_win),
            "avg_loss": float(avg_loss),
            "open_positions": open_count,
        }
