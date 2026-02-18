"""Implementacao do repositorio de trades."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.domain.entities import Trade
from src.domain.enums.trading_enums import OrderSide, TradeStatus
from src.domain.value_objects import Money, Price, Quantity, Symbol
from src.infrastructure.database.schema import TradeModel


class ITradeRepository(ABC):
    """Interface do repositorio de trades."""

    @abstractmethod
    def save(self, trade: Trade) -> None:
        """Persiste um trade."""
        pass

    @abstractmethod
    def find_by_id(self, trade_id: UUID) -> Optional[Trade]:
        """Busca trade por ID."""
        pass

    @abstractmethod
    def find_open_trades(self, symbol: Optional[Symbol] = None) -> list[Trade]:
        """Busca todos os trades abertos, opcionalmente filtrados por simbolo."""
        pass

    @abstractmethod
    def find_all(self, limit: int = 100) -> list[Trade]:
        """Busca todos os trades com limite."""
        pass

    @abstractmethod
    def update(self, trade: Trade) -> None:
        """Atualiza trade existente."""
        pass


class SqliteTradeRepository(ITradeRepository):
    """Implementacao SQLite do repositorio de trades."""

    def __init__(self, session: Session):
        """
        Inicializa o repositorio com a sessao do banco de dados.

        Args:
            session: Sessao do SQLAlchemy
        """
        self.session = session

    def save(self, trade: Trade) -> None:
        """Persiste um trade no banco de dados."""
        trade_model = self._to_model(trade)
        self.session.add(trade_model)
        self.session.commit()

    def find_by_id(self, trade_id: UUID) -> Optional[Trade]:
        """Busca trade por ID."""
        model = (
            self.session.query(TradeModel)
            .filter(TradeModel.trade_id == str(trade_id))
            .first()
        )

        if not model:
            return None

        return self._to_entity(model)

    def find_open_trades(self, symbol: Optional[Symbol] = None) -> list[Trade]:
        """Busca todos os trades abertos."""
        query = self.session.query(TradeModel).filter(
            TradeModel.status == TradeStatus.OPEN.value
        )

        if symbol:
            query = query.filter(TradeModel.symbol == symbol.code)

        models = query.all()
        return [self._to_entity(m) for m in models]

    def find_all(self, limit: int = 100) -> list[Trade]:
        """Busca todos os trades com limite."""
        models = (
            self.session.query(TradeModel)
            .order_by(TradeModel.entry_time.desc())
            .limit(limit)
            .all()
        )

        return [self._to_entity(m) for m in models]

    def update(self, trade: Trade) -> None:
        """Atualiza trade existente."""
        model = (
            self.session.query(TradeModel)
            .filter(TradeModel.trade_id == str(trade.trade_id))
            .first()
        )

        if not model:
            raise ValueError(f"Trade not found: {trade.trade_id}")

        # Atualiza campos
        model.exit_price = (
            trade.exit_price.value if trade.exit_price else None
        )
        model.exit_time = trade.exit_time
        model.status = trade.status.value
        model.commission = trade.commission.amount

        # Calcula P&L se fechado
        if trade.status == TradeStatus.CLOSED:
            pl = trade.calculate_profit_loss()
            if pl:
                model.profit_loss = pl.amount

            return_pct = trade.calculate_return_percentage()
            if return_pct:
                model.return_percentage = float(return_pct)

        self.session.commit()

    def _to_model(self, trade: Trade) -> TradeModel:
        """Converte entidade de dominio para modelo de banco de dados."""
        return TradeModel(
            trade_id=str(trade.trade_id),
            symbol=trade.symbol.code,
            side=trade.side.value,
            quantity=trade.quantity.value,
            entry_price=trade.entry_price.value,
            entry_time=trade.entry_time,
            exit_price=trade.exit_price.value if trade.exit_price else None,
            exit_time=trade.exit_time,
            stop_loss=trade.stop_loss.value if trade.stop_loss else None,
            take_profit=(
                trade.take_profit.value if trade.take_profit else None
            ),
            status=trade.status.value,
            broker_trade_id=trade.broker_trade_id,
            commission=trade.commission.amount,
            notes=trade.notes,
        )

    def _to_entity(self, model: TradeModel) -> Trade:
        """Converte modelo de banco de dados para entidade de dominio."""
        return Trade(
            trade_id=UUID(model.trade_id),
            symbol=Symbol(model.symbol),
            side=OrderSide(model.side),
            quantity=Quantity(model.quantity),
            entry_price=Price(model.entry_price),
            entry_time=model.entry_time,
            exit_price=Price(model.exit_price) if model.exit_price else None,
            exit_time=model.exit_time,
            stop_loss=Price(model.stop_loss) if model.stop_loss else None,
            take_profit=(
                Price(model.take_profit) if model.take_profit else None
            ),
            status=TradeStatus(model.status),
            broker_trade_id=model.broker_trade_id,
            commission=Money(model.commission),
            notes=model.notes or "",
        )
