"""Adaptador MetaTrader 5 para Broker."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.domain.entities import Order
from src.domain.enums.trading_enums import OrderSide, TimeFrame
from src.domain.exceptions import BrokerConnectionError, OrderExecutionError
from src.domain.value_objects import Price, Symbol


@dataclass
class TickData:
    """Representa um tick do mercado."""

    symbol: Symbol
    bid: Price
    ask: Price
    last: Price
    volume: int
    timestamp: datetime


@dataclass
class Candle:
    """Representa um candlestick (vela)."""

    symbol: Symbol
    timeframe: TimeFrame
    open: Price
    high: Price
    low: Price
    close: Price
    volume: int
    timestamp: datetime


class IBrokerAdapter(ABC):
    """Interface para adaptadores de broker (abstracao para diferentes brokers)."""

    @abstractmethod
    def connect(self) -> bool:
        """Conecta ao broker."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Desconecta do broker."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Verifica se esta conectado ao broker."""
        pass

    @abstractmethod
    def get_current_tick(self, symbol: Symbol) -> TickData:
        """Obtem dados de tick atual para um simbolo."""
        pass

    @abstractmethod
    def get_candles(
        self,
        symbol: Symbol,
        timeframe: TimeFrame,
        count: int = 100,
        start_time: Optional[datetime] = None,
    ) -> list[Candle]:
        """Obtem dados historicos de candles."""
        pass

    @abstractmethod
    def send_order(self, order: Order) -> str:
        """
        Envia ordem ao broker.

        Retorna o ID da ordem no broker.
        """
        pass

    @abstractmethod
    def close_position(self, symbol: Symbol) -> bool:
        """Fecha todas as posicoes de um simbolo."""
        pass

    @abstractmethod
    def get_account_balance(self) -> Decimal:
        """Obtem o saldo atual da conta."""
        pass

    @abstractmethod
    def get_account_equity(self) -> Decimal:
        """Obtem o patrimonio atual da conta."""
        pass


class MT5Adapter(IBrokerAdapter):
    """
    Implementacao do adaptador MetaTrader 5.

    Fornece integracao com o terminal MT5.
    """

    def __init__(
        self,
        login: int,
        password: str,
        server: str,
        timeout: int = 60000,
    ):
        """
        Inicializa o adaptador MT5.

        Args:
            login: Login da conta MT5
            password: Senha da conta MT5
            server: Nome do servidor MT5
            timeout: Timeout de conexao em milissegundos
        """
        self.login = login
        self.password = password
        self.server = server
        self.timeout = timeout
        self._mt5 = None
        self._time_offset_seconds: Optional[int] = -3 * 3600

    def _normalize_timestamp(self, epoch_seconds: int) -> datetime:
        """Normaliza timestamps do MT5 para horario de Brasilia (UTC-3)."""
        ts = int(epoch_seconds)
        return datetime.utcfromtimestamp(ts + self._time_offset_seconds)

    def connect(self) -> bool:
        """Conecta ao MetaTrader 5."""
        try:
            import MetaTrader5 as mt5

            self._mt5 = mt5

            # Inicializa conexao com MT5
            if not mt5.initialize():
                raise BrokerConnectionError(
                    f"MT5 initialize failed: {mt5.last_error()}"
                )

            # Login na conta
            authorized = mt5.login(
                login=self.login,
                password=self.password,
                server=self.server,
                timeout=self.timeout,
            )

            if not authorized:
                raise BrokerConnectionError(
                    f"MT5 login failed: {mt5.last_error()}"
                )

            return True

        except ImportError:
            raise BrokerConnectionError(
                "MetaTrader5 package not installed. Install with: pip install MetaTrader5"
            )
        except Exception as e:
            raise BrokerConnectionError(f"Failed to connect to MT5: {e}")

    def disconnect(self) -> None:
        """Desconecta do MetaTrader 5."""
        if self._mt5:
            self._mt5.shutdown()

    def is_connected(self) -> bool:
        """Verifica se esta conectado ao MT5."""
        if not self._mt5:
            return False

        terminal_info = self._mt5.terminal_info()
        return terminal_info is not None and terminal_info.trade_allowed

    def get_current_tick(self, symbol: Symbol) -> TickData:
        """Obtem dados de tick atual para um simbolo."""
        self._ensure_connected()

        tick = self._mt5.symbol_info_tick(symbol.code)

        if tick is None:
            raise OrderExecutionError(
                f"Failed to get tick for {symbol}: {self._mt5.last_error()}"
            )

        return TickData(
            symbol=symbol,
            bid=Price(Decimal(str(tick.bid))),
            ask=Price(Decimal(str(tick.ask))),
            last=Price(Decimal(str(tick.last))),
            volume=tick.volume,
            timestamp=self._normalize_timestamp(tick.time),
        )

    def get_candles(
        self,
        symbol: Symbol,
        timeframe: TimeFrame,
        count: int = 100,
        start_time: Optional[datetime] = None,
    ) -> list[Candle]:
        """Obtem dados historicos de candles."""
        self._ensure_connected()

        # Mapeia timeframe para constante MT5
        timeframe_map = {
            TimeFrame.M1: self._mt5.TIMEFRAME_M1,
            TimeFrame.M5: self._mt5.TIMEFRAME_M5,
            TimeFrame.M15: self._mt5.TIMEFRAME_M15,
            TimeFrame.M30: self._mt5.TIMEFRAME_M30,
            TimeFrame.H1: self._mt5.TIMEFRAME_H1,
            TimeFrame.H4: self._mt5.TIMEFRAME_H4,
            TimeFrame.D1: self._mt5.TIMEFRAME_D1,
        }

        mt5_timeframe = timeframe_map.get(timeframe)
        if not mt5_timeframe:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        # Obtem as barras
        if start_time:
            rates = self._mt5.copy_rates_from(
                symbol.code, mt5_timeframe, start_time, count
            )
        else:
            rates = self._mt5.copy_rates_from_pos(
                symbol.code, mt5_timeframe, 0, count
            )

        if rates is None:
            raise OrderExecutionError(
                f"Failed to get candles for {symbol}: {self._mt5.last_error()}"
            )

        # Converte para objetos Candle
        candles = []
        for rate in rates:
            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                open=Price(Decimal(str(rate["open"]))),
                high=Price(Decimal(str(rate["high"]))),
                low=Price(Decimal(str(rate["low"]))),
                close=Price(Decimal(str(rate["close"]))),
                volume=int(rate["tick_volume"]),
                timestamp=self._normalize_timestamp(rate["time"]),
            )
            candles.append(candle)

        return candles

    def get_candles_range(
        self,
        symbol: Symbol,
        timeframe: TimeFrame,
        start_time: datetime,
        end_time: datetime,
    ) -> list[Candle]:
        """Obtem dados historicos de candles por intervalo de tempo."""
        self._ensure_connected()

        timeframe_map = {
            TimeFrame.M1: self._mt5.TIMEFRAME_M1,
            TimeFrame.M5: self._mt5.TIMEFRAME_M5,
            TimeFrame.M15: self._mt5.TIMEFRAME_M15,
            TimeFrame.M30: self._mt5.TIMEFRAME_M30,
            TimeFrame.H1: self._mt5.TIMEFRAME_H1,
            TimeFrame.H4: self._mt5.TIMEFRAME_H4,
            TimeFrame.D1: self._mt5.TIMEFRAME_D1,
        }

        mt5_timeframe = timeframe_map.get(timeframe)
        if not mt5_timeframe:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        rates = self._mt5.copy_rates_range(
            symbol.code, mt5_timeframe, start_time, end_time
        )
        if rates is None:
            return []

        candles = []
        for rate in rates:
            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                open=Price(Decimal(str(rate["open"]))),
                high=Price(Decimal(str(rate["high"]))),
                low=Price(Decimal(str(rate["low"]))),
                close=Price(Decimal(str(rate["close"]))),
                volume=int(rate["tick_volume"]),
                timestamp=self._normalize_timestamp(rate["time"]),
            )
            candles.append(candle)

        return candles

    @staticmethod
    def _round_to_tick(price: float, tick_size: float) -> float:
        """Arredonda preço para o múltiplo mais próximo do tick size.

        WIN mini-índice: tick_size = 5.0 (move de 5 em 5)
        Exemplo: 186481.25 → 186480.0, 185884.02 → 185885.0
        """
        if tick_size <= 0:
            return price
        return round(round(price / tick_size) * tick_size, 2)

    def _get_tick_size(self, symbol_code: str) -> float:
        """Obtém o tick size (variação mínima de preço) do símbolo."""
        info = self._mt5.symbol_info(symbol_code)
        if info and hasattr(info, 'trade_tick_size') and info.trade_tick_size > 0:
            return info.trade_tick_size
        # Fallback para WIN: tick = 5 pontos
        if 'WIN' in symbol_code.upper():
            return 5.0
        return 0.01

    def _resolve_tradable_symbol(self, symbol_code: str) -> str:
        """Resolve símbolo de cotação contínua para contrato negociável.

        WIN$N → contrato real atual (ex: WINJ26)
        Se já for negociável, retorna o mesmo.
        """
        info = self._mt5.symbol_info(symbol_code)
        if info is None:
            return symbol_code

        # Se o símbolo aceita ordens diretamente, usa ele
        if info.trade_mode == self._mt5.SYMBOL_TRADE_MODE_FULL:
            return symbol_code

        # Tenta resolver via path ou custom (WIN$N → contrato real)
        # MT5 expõe o campo 'path' ou 'basis' com o contrato real
        if hasattr(info, 'basis') and info.basis:
            basis_info = self._mt5.symbol_info(info.basis)
            if basis_info and basis_info.trade_mode == self._mt5.SYMBOL_TRADE_MODE_FULL:
                return info.basis

        # Fallback: busca contratos WIN ativos
        symbols = self._mt5.symbols_get(group="*WIN*")
        if symbols:
            for s in symbols:
                if (s.trade_mode == self._mt5.SYMBOL_TRADE_MODE_FULL
                        and s.name.startswith("WIN")
                        and not s.name.endswith("$N")):
                    return s.name

        return symbol_code

    def send_order(self, order: Order) -> str:
        """Envia ordem ao MT5."""
        self._ensure_connected()

        # Resolve símbolo negociável (WIN$N → WINJ26, etc.)
        tradable_symbol = self._resolve_tradable_symbol(order.symbol.code)

        # Mapeia lado da ordem para tipo de ordem MT5
        if order.side == OrderSide.BUY:
            order_type = self._mt5.ORDER_TYPE_BUY
        else:
            order_type = self._mt5.ORDER_TYPE_SELL

        # Obtem preco atual
        tick = self.get_current_tick(Symbol(tradable_symbol))
        price = tick.ask if order.side == OrderSide.BUY else tick.bid

        # Obtém tick size para arredondamento de preços
        tick_size = self._get_tick_size(tradable_symbol)

        # Prepara requisicao — ORDER_FILLING_RETURN para B3
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": tradable_symbol,
            "volume": float(order.quantity.value),
            "type": order_type,
            "price": self._round_to_tick(float(price.value), tick_size),
            "deviation": 10,
            "magic": 234000,
            "comment": f"MA{str(order.order_id)[:8]}",
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_RETURN,
        }

        # Em contas hedge, fechamento correto exige vínculo explícito da posição.
        if order.close_position_ticket is not None:
            request["position"] = int(order.close_position_ticket)

        # Adiciona SL/TP se fornecidos (arredondados ao tick size)
        if order.stop_loss:
            request["sl"] = self._round_to_tick(float(order.stop_loss.value), tick_size)
        if order.take_profit:
            request["tp"] = self._round_to_tick(float(order.take_profit.value), tick_size)

        # Envia ordem
        result = self._mt5.order_send(request)

        if result is None:
            last_err = self._mt5.last_error()
            raise OrderExecutionError(
                f"order_send retornou None. Símbolo: {tradable_symbol} | "
                f"Last error: {last_err} | Request: {request}"
            )

        if result.retcode != self._mt5.TRADE_RETCODE_DONE:
            raise OrderExecutionError(
                f"Order execution failed: {result.comment} (code: {result.retcode}) | "
                f"Símbolo: {tradable_symbol}"
            )

        return str(result.order)

    def resolve_open_position_ticket(
        self,
        symbol: Symbol,
        side: OrderSide,
    ) -> Optional[int]:
        """Resolve ticket da posição aberta mais recente para símbolo+lados.

        Útil para contas hedge, onde o fechamento deve referenciar `position`.
        """
        self._ensure_connected()

        tradable = self._resolve_tradable_symbol(symbol.code)
        positions = self._mt5.positions_get(symbol=tradable)
        if not positions:
            if tradable != symbol.code:
                positions = self._mt5.positions_get(symbol=symbol.code)
            if not positions:
                return None

        mt5_type = self._mt5.ORDER_TYPE_BUY if side == OrderSide.BUY else self._mt5.ORDER_TYPE_SELL
        candidates = [p for p in positions if int(getattr(p, "type", -1)) == mt5_type]
        if not candidates:
            return None

        # Prioriza posição mais recente desse lado
        candidates = sorted(candidates, key=lambda p: int(getattr(p, "time", 0) or 0), reverse=True)
        return int(candidates[0].ticket)

    def close_position(self, symbol: Symbol) -> bool:
        """Fecha todas as posicoes de um simbolo."""
        self._ensure_connected()

        # Tenta com símbolo original e também com o negociável
        tradable = self._resolve_tradable_symbol(symbol.code)
        positions = self._mt5.positions_get(symbol=tradable)

        if positions is None or len(positions) == 0:
            # Tenta com símbolo original caso seja diferente
            if tradable != symbol.code:
                positions = self._mt5.positions_get(symbol=symbol.code)
            if positions is None or len(positions) == 0:
                return True

        for position in positions:
            # Tipo de ordem oposta para fechar
            if position.type == self._mt5.ORDER_TYPE_BUY:
                order_type = self._mt5.ORDER_TYPE_SELL
            else:
                order_type = self._mt5.ORDER_TYPE_BUY

            request = {
                "action": self._mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,  # Usa símbolo da posição real
                "volume": position.volume,
                "type": order_type,
                "position": position.ticket,
                "deviation": 10,
                "magic": 234000,
                "comment": "Close position",
                "type_time": self._mt5.ORDER_TIME_GTC,
                "type_filling": self._mt5.ORDER_FILLING_RETURN,
            }

            result = self._mt5.order_send(request)

            if result is None:
                last_err = self._mt5.last_error()
                raise OrderExecutionError(
                    f"close_position: order_send retornou None. Last error: {last_err}"
                )

            if result.retcode != self._mt5.TRADE_RETCODE_DONE:
                raise OrderExecutionError(
                    f"Failed to close position: {result.comment} (code: {result.retcode})"
                )

        return True

    def get_positions(self, symbol: Optional[Symbol] = None) -> list:
        """Retorna posições abertas (todas ou por símbolo)."""
        self._ensure_connected()

        if symbol is None:
            positions = self._mt5.positions_get()
            return list(positions) if positions else []

        tradable = self._resolve_tradable_symbol(symbol.code)
        positions = self._mt5.positions_get(symbol=tradable)
        if not positions and tradable != symbol.code:
            positions = self._mt5.positions_get(symbol=symbol.code)
        return list(positions) if positions else []

    def close_position_by_ticket(self, position_ticket: int) -> bool:
        """Fecha uma posição específica pelo ticket (seguro para conta hedge)."""
        self._ensure_connected()

        positions = self._mt5.positions_get()
        if not positions:
            return False

        position = None
        for p in positions:
            if int(getattr(p, "ticket", 0) or 0) == int(position_ticket):
                position = p
                break

        if position is None:
            return False

        if int(position.type) == self._mt5.ORDER_TYPE_BUY:
            order_type = self._mt5.ORDER_TYPE_SELL
        else:
            order_type = self._mt5.ORDER_TYPE_BUY

        tick = self._mt5.symbol_info_tick(position.symbol)
        if tick is None:
            raise OrderExecutionError(
                f"close_position_by_ticket: sem tick para {position.symbol}"
            )

        tick_size = self._get_tick_size(position.symbol)
        close_price = tick.bid if order_type == self._mt5.ORDER_TYPE_SELL else tick.ask

        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": float(position.volume),
            "type": order_type,
            "position": int(position.ticket),
            "price": self._round_to_tick(float(close_price), tick_size),
            "deviation": 10,
            "magic": 234000,
            "comment": f"Watchdog close pos={position.ticket}",
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_RETURN,
        }

        result = self._mt5.order_send(request)
        if result is None:
            raise OrderExecutionError(
                f"close_position_by_ticket: order_send None | last_error={self._mt5.last_error()}"
            )

        if result.retcode != self._mt5.TRADE_RETCODE_DONE:
            raise OrderExecutionError(
                f"close_position_by_ticket falhou: {result.comment} (code: {result.retcode})"
            )

        return True

    def get_account_balance(self) -> Decimal:
        """Obtem o saldo atual da conta."""
        self._ensure_connected()

        account_info = self._mt5.account_info()
        if account_info is None:
            raise BrokerConnectionError("Failed to get account info")

        return Decimal(str(account_info.balance))

    def get_account_equity(self) -> Decimal:
        """Obtem o patrimonio atual da conta."""
        self._ensure_connected()

        account_info = self._mt5.account_info()
        if account_info is None:
            raise BrokerConnectionError("Failed to get account info")

        return Decimal(str(account_info.equity))

    def _ensure_connected(self) -> None:
        """Garante que estamos conectados ao MT5."""
        if not self.is_connected():
            raise BrokerConnectionError("Not connected to MT5")

    def get_available_symbols(self, prefix: str = "") -> list[str]:
        """Lista simbolos disponiveis no MT5, opcionalmente filtrados por prefixo."""
        self._ensure_connected()

        if prefix:
            symbols = self._mt5.symbols_get(prefix + "*")
        else:
            symbols = self._mt5.symbols_get()

        if symbols is None:
            return []

        return [s.name for s in symbols]

    def select_symbol(self, symbol_code: str) -> bool:
        """Habilita um simbolo no terminal MT5 para receber dados.

        Fallback: se symbol_select falhar (ex: 'Out of memory' com Market Watch
        cheio), verifica se o simbolo ja esta visivel via symbol_info.
        """
        self._ensure_connected()

        result = self._mt5.symbol_select(symbol_code, True)
        if result is True or result is None:
            return True

        # Fallback: simbolo pode ja estar habilitado/visivel
        info = self._mt5.symbol_info(symbol_code)
        return info is not None and info.visible

    def get_symbol_info_tick(self, symbol_code: str) -> Optional[TickData]:
        """Obtem tick de um simbolo por string (sem exigir Symbol VO)."""
        self._ensure_connected()

        tick = self._mt5.symbol_info_tick(symbol_code)
        if tick is None:
            return None

        return TickData(
            symbol=Symbol(symbol_code),
            bid=Price(Decimal(str(tick.bid))),
            ask=Price(Decimal(str(tick.ask))),
            last=Price(Decimal(str(tick.last))),
            volume=tick.volume,
            timestamp=self._normalize_timestamp(tick.time),
        )

    def get_daily_candle(self, symbol_code: str) -> Optional["Candle"]:
        """Obtem o candle diario atual para extrair preco de abertura do dia."""
        self._ensure_connected()

        rates = self._mt5.copy_rates_from_pos(
            symbol_code, self._mt5.TIMEFRAME_D1, 0, 1
        )

        if rates is None or len(rates) == 0:
            return None

        rate = rates[0]
        return Candle(
            symbol=Symbol(symbol_code),
            timeframe=TimeFrame.D1,
            open=Price(Decimal(str(rate["open"]))),
            high=Price(Decimal(str(rate["high"]))),
            low=Price(Decimal(str(rate["low"]))),
            close=Price(Decimal(str(rate["close"]))),
            volume=int(rate["tick_volume"]),
            timestamp=self._normalize_timestamp(rate["time"]),
        )
