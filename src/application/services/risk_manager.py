"""Servico de gerenciamento de risco."""

from decimal import Decimal
from typing import Optional

from src.domain.entities import Portfolio, Trade
from src.domain.enums.trading_enums import RiskLevel
from src.domain.exceptions import RiskLimitExceededError
from src.domain.value_objects import Money, Percentage, Price, Quantity


class RiskManager:
    """
    Servico para gerenciamento de risco de trading.

    Implementa regras e validacoes de gerenciamento de risco.
    """

    def __init__(
        self,
        max_risk_per_trade: Percentage,
        max_drawdown: Percentage,
        min_risk_reward: Decimal,
    ):
        """
        Inicializa o gerenciador de risco.

        Args:
            max_risk_per_trade: Percentual maximo de risco por trade
            max_drawdown: Drawdown maximo permitido
            min_risk_reward: Relacao risco/retorno minima
        """
        self.max_risk_per_trade = max_risk_per_trade
        self.max_drawdown = max_drawdown
        self.min_risk_reward = min_risk_reward

    def calculate_position_size(
        self,
        capital: Money,
        entry_price: Price,
        stop_loss: Price,
    ) -> Quantity:
        """
        Calcula tamanho da posicao baseado em parametros de risco.

        Usa dimensionamento fracional fixo.

        Args:
            capital: Capital disponivel
            entry_price: Preco de entrada
            stop_loss: Preco de stop loss

        Returns:
            Tamanho de posicao recomendado
        """
        # Calcula risco por contrato
        risk_per_contract = abs(entry_price.value - stop_loss.value)

        # Calcula valor maximo de risco
        max_risk_amount = self.max_risk_per_trade.of(capital)

        # Calcula tamanho da posicao
        position_size = int(max_risk_amount.amount / risk_per_contract)

        # Minimo 1 contrato
        return Quantity(max(1, position_size))

    def validate_trade_risk(
        self,
        trade: Trade,
        portfolio: Portfolio,
    ) -> None:
        """
        Valida se o trade atende aos requisitos de risco.

        Args:
            trade: Trade a ser validado
            portfolio: Portfolio atual

        Raises:
            RiskLimitExceededError: Se os limites de risco forem excedidos
        """
        # Verifica se o stop loss esta definido
        if not trade.stop_loss:
            raise RiskLimitExceededError("Stop loss is required for all trades")

        # Calcula valor do risco
        risk_per_contract = abs(
            trade.entry_price.value - trade.stop_loss.value
        )
        total_risk = risk_per_contract * trade.quantity.value
        max_allowed_risk = self.max_risk_per_trade.of(portfolio.current_capital)

        if total_risk > max_allowed_risk.amount:
            raise RiskLimitExceededError(
                f"Trade risk ({total_risk}) exceeds maximum allowed "
                f"risk ({max_allowed_risk.amount})"
            )

        # Verifica relacao risco/retorno se o take profit estiver definido
        if trade.take_profit:
            risk = abs(trade.entry_price.value - trade.stop_loss.value)
            reward = abs(trade.take_profit.value - trade.entry_price.value)
            risk_reward_ratio = reward / risk

            if risk_reward_ratio < self.min_risk_reward:
                raise RiskLimitExceededError(
                    f"Risk/reward ratio ({risk_reward_ratio:.2f}) is below "
                    f"minimum ({self.min_risk_reward})"
                )

    def validate_portfolio_risk(self, portfolio: Portfolio) -> None:
        """
        Valida niveis de risco do portfolio.

        Args:
            portfolio: Portfolio a ser validado

        Raises:
            RiskLimitExceededError: Se o risco do portfolio exceder os limites
        """
        # Verifica drawdown
        current_drawdown = portfolio.calculate_max_drawdown()

        if current_drawdown.value > self.max_drawdown.value:
            raise RiskLimitExceededError(
                f"Portfolio drawdown ({current_drawdown}) exceeds "
                f"maximum allowed ({self.max_drawdown}). Trading paused."
            )

    def assess_risk_level(
        self,
        trade: Trade,
        portfolio: Portfolio,
    ) -> RiskLevel:
        """
        Avalia nivel de risco de um trade.

        Args:
            trade: Trade a ser avaliado
            portfolio: Portfolio atual

        Returns:
            Nivel de risco avaliado
        """
        if not trade.stop_loss:
            return RiskLevel.EXTREME

        # Calcula percentual de risco
        risk_per_contract = abs(
            trade.entry_price.value - trade.stop_loss.value
        )
        total_risk = risk_per_contract * trade.quantity.value
        risk_percentage = total_risk / portfolio.current_capital.amount

        # Classifica nivel de risco
        if risk_percentage < Decimal("0.01"):
            return RiskLevel.LOW
        elif risk_percentage < Decimal("0.02"):
            return RiskLevel.MEDIUM
        elif risk_percentage < Decimal("0.03"):
            return RiskLevel.HIGH
        else:
            return RiskLevel.EXTREME

    def calculate_stop_loss(
        self,
        entry_price: Price,
        atr: Decimal,
        multiplier: Decimal = Decimal("2"),
    ) -> Price:
        """
        Calcula stop loss baseado no ATR (Average True Range).

        Args:
            entry_price: Preco de entrada
            atr: Valor atual do ATR
            multiplier: Multiplicador do ATR para distancia do stop

        Returns:
            Preco de stop loss calculado
        """
        stop_distance = atr * multiplier
        # Assumindo posicao comprada - ajustar para vendida
        stop_loss = entry_price.value - stop_distance
        return Price(max(Decimal("0"), stop_loss))

    def calculate_take_profit(
        self,
        entry_price: Price,
        stop_loss: Price,
        risk_reward_ratio: Optional[Decimal] = None,
    ) -> Price:
        """
        Calcula take profit baseado na relacao risco/retorno.

        Args:
            entry_price: Preco de entrada
            stop_loss: Preco de stop loss
            risk_reward_ratio: Relacao R:R desejada (usa padrao se None)

        Returns:
            Preco de take profit calculado
        """
        ratio = risk_reward_ratio or self.min_risk_reward

        risk = abs(entry_price.value - stop_loss.value)
        reward = risk * ratio

        # Assumindo posicao comprada
        take_profit = entry_price.value + reward
        return Price(take_profit)
