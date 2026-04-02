"""Adaptador MetaTrader 5 para Broker."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional
import json
import logging
import os
import re
import time
from pathlib import Path

from src.domain.entities import Order
from src.domain.enums.trading_enums import OrderSide, TimeFrame
from src.domain.exceptions import BrokerConnectionError, OrderExecutionError
from src.domain.value_objects import Price, Symbol

logger = logging.getLogger(__name__)


AGENT_LABELS_BY_MAGIC: dict[int, str] = {
    234500: "RL 5000",
    234600: "RL Direto",
    234700: "Micro Tend",
    234800: "Diarios",
}


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

    @abstractmethod
    def get_time_offset_hours(self) -> int:
        """Retorna o offset de fuso horario detectado (horas)."""
        pass


class MT5Adapter(IBrokerAdapter):
    """
    Implementacao do adaptador MetaTrader 5.

    Fornece integracao com o terminal MT5 com suporte a isolamento de
    terminal (S2-5: MT5 Terminal Isolation & Reconnect).
    """

    def __init__(
        self,
        login: int,
        password: str,
        server: str,
        timeout: int = 60000,
        terminal_exe_path: Optional[str] = None,
    ):
        """
        Inicializa o adaptador MT5.

        Args:
            login: Login da conta MT5
            password: Senha da conta MT5
            server: Nome do servidor MT5
            timeout: Timeout de conexao em milissegundos
            terminal_exe_path: Caminho do executável do terminal64.exe
                (se None, usa o primeiro encontrado)

        Exemplo:
            adapter = MT5Adapter(
                login=1000346516,
                password="senha",
                server="Clear MT5 - Live",
                terminal_exe_path="C:\\Program Files\\Clear Investimentos MT5\\terminal64.exe"
            )
        """
        self.login = login
        self.password = password
        self.server = server
        self.timeout = timeout
        self.terminal_exe_path = terminal_exe_path
        self._mt5: Any = None
        self._time_offset_seconds: Optional[int] = -3 * 3600
        self._session_fingerprint: Optional[dict] = None
        self._trading_halted: bool = False

    @staticmethod
    def _normalizar_caminho_terminal(caminho: Optional[str]) -> str:
        """Normaliza caminhos para comparação segura e tolerante a variações."""
        if not caminho:
            return ""
        return str(Path(caminho)).replace("\\", "/").lower().strip()

    def _terminal_corresponde_ao_esperado(self, expected_path: str, actual_path: str) -> bool:
        """Compara paths do terminal com tolerância a variações de instalação."""
        expected_norm = self._normalizar_caminho_terminal(expected_path)
        actual_norm = self._normalizar_caminho_terminal(actual_path)

        if not expected_norm or not actual_norm:
            return False

        if expected_norm == actual_norm:
            return True

        expected_name = Path(expected_norm).name
        actual_name = Path(actual_norm).name
        if expected_name and expected_name != actual_name:
            return False

        expected_parent = Path(expected_norm).parent.as_posix()
        actual_parent = Path(actual_norm).parent.as_posix()
        if expected_parent and expected_parent in actual_parent:
            return True
        if actual_parent and actual_parent in expected_parent:
            return True

        generic_tokens = {
            "c:",
            "program",
            "files",
            "programfiles",
            "program files",
            "program files (x86)",
            "mt5",
            "terminal64.exe",
            "metatrader",
            "metaquotes",
        }

        def _tokens(text: str) -> set[str]:
            tokens = {
                token.strip()
                for token in text.replace("/", " ").replace("\\", " ").split()
                if token.strip()
            }
            return {token for token in tokens if token not in generic_tokens}

        expected_tokens = _tokens(expected_parent)
        actual_tokens = _tokens(actual_parent)
        return len(expected_tokens.intersection(actual_tokens)) > 0

    def _normalize_timestamp(self, epoch_seconds: int) -> datetime:
        """Normaliza timestamps do MT5 para horario de Brasilia (UTC-3)."""
        ts = int(epoch_seconds)
        offset = self._time_offset_seconds or 0
        return datetime.utcfromtimestamp(ts + offset)

    @staticmethod
    def _build_order_comment(order: Order) -> str:
        """Monta comentario curto e legivel para o ticket no MT5."""
        agent_name = AGENT_LABELS_BY_MAGIC.get(order.magic_number, "Agente")
        order_prefix = str(order.order_id)[:8]
        comment = f"{agent_name}_EA{order.magic_number}_MA{order_prefix}"
        # Alguns servidores MT5 rejeitam separadores como "|" e caracteres especiais.
        safe_comment = re.sub(r"[^A-Za-z0-9_\-]", "", comment)
        return safe_comment[:31]

    def _get_mt5_terminal_pid(self) -> Optional[int]:
        """
        Encontra o PID do processo terminal64.exe em execução.

        Se terminal_exe_path foi especificado, valida que corresponde.
        Caso contrário, usa o primeiro encontrado.

        Returns:
            PID do processo, ou None se não encontrado.
        """
        try:
            import psutil

            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if 'terminal64.exe' not in proc.info['name'].lower():
                        continue

                    exe_path = proc.info['exe']
                    if not exe_path:
                        continue

                    # Se terminal_exe_path foi especificado, VALIDA MATCH (proteção contra FBS/XP/outro)
                    if self.terminal_exe_path:
                        if not self._terminal_corresponde_ao_esperado(
                            self.terminal_exe_path,
                            exe_path,
                        ):
                            logger.debug(
                                "Terminal mismatch: expected %s, got %s",
                                self.terminal_exe_path,
                                exe_path,
                            )
                            continue

                    return int(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except ImportError:
            logger.warning(
                "psutil not installed. Terminal isolation validation disabled. "
                "Install with: pip install psutil"
            )
            return None

        return None

    def _save_session_fingerprint(self) -> bool:
        """
        Salva fingerprint da sessão MT5 após conexão bem-sucedida.

        Fingerprint inclui: PID, exe_path, account_login, server, timestamp

        Returns:
            True se salvo com sucesso, False caso contrário.
        """
        try:
            pid = self._get_mt5_terminal_pid()
            if not pid:
                logger.warning("Could not find terminal64.exe PID for fingerprint")
                return False

            self._session_fingerprint = {
                "pid": pid,
                "exe_path": self.terminal_exe_path or "[auto-detected]",
                "account_login": self.login,
                "server": self.server,
                "timestamp": datetime.now().isoformat(),
            }

            # Persistir em arquivo
            home = os.path.expanduser("~")
            session_file = os.path.join(home, ".mt5_operator_session.json")

            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(self._session_fingerprint, f, indent=2)

            logger.info(
                f"MT5 session fingerprint saved: PID={pid}, Login={self.login}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save session fingerprint: {e}")
            return False

    def _validate_terminal_isolation(self) -> bool:
        """
        Valida isolamento de terminal e conta.

        Verifica:
        1. PID do terminal64.exe ainda está em execução
        2. Account login atual corresponde ao esperado

        Raises:
            BrokerConnectionError se isolamento foi violado

        Returns:
            True se isolamento válido, False caso contrário.
        """
        if not self._session_fingerprint:
            logger.debug("No session fingerprint set, skipping isolation check")
            return True

        try:
            import psutil

            # 1. Valida PID
            pid = self._session_fingerprint.get("pid")
            if pid and not psutil.pid_exists(pid):
                logger.error(
                    f"Terminal isolation violation: PID {pid} no longer exists. "
                    "Terminal may have crashed."
                )
                return False

            # 2. Valida account login
            if not self._mt5:
                logger.warning("MT5 module not initialized")
                return False

            account_info = self._mt5.account_info()
            if not account_info:
                logger.warning("Could not get account info for isolation validation")
                return False

            if account_info.login != self.login:
                logger.error(
                    f"Terminal isolation violation: Expected login {self.login}, "
                    f"but MT5 is logged in as {account_info.login}"
                )
                return False

            logger.debug("Terminal isolation validation passed")
            return True

        except ImportError:
            logger.warning("psutil not available for terminal isolation check")
            return True
        except Exception as e:
            logger.error(f"Error during isolation validation: {e}")
            return False

    def _ensure_connected_with_isolation(self) -> None:
        """
        Garante que estamos conectados ao MT5 E que isolamento é válido.

        Raises:
            BrokerConnectionError se não conectado ou isolamento violado.
        """
        if not self.is_connected():
            raise BrokerConnectionError("Not connected to MT5")

        if self._trading_halted:
            raise BrokerConnectionError(
                "Trading halted due to previous isolation violation. "
                "Manual intervention required."
            )

        if not self._validate_terminal_isolation():
            self._trading_halted = True
            raise BrokerConnectionError(
                "Terminal isolation validation failed. "
                "Trading halted as safety measure."
            )

    def is_trading_halted(self) -> bool:
        """
        Verifica se o sistema está em estado HALT.

        Um sistema em HALT não executa ordens até que o isolamento
        seja restaurado manualmente.

        Returns:
            True se em HALT, False caso contrário.
        """
        return self._trading_halted

    def connect(self) -> bool:
        """
        Conecta ao MetaTrader 5 com retry automático e validação de isolamento.

        Implementa retry com exponential backoff: [5s, 10s, 20s]

        Returns:
            True se conexão bem-sucedida, False caso contrário.
        """
        return self._connect_with_retry(max_retries=3, backoff_seconds=[5, 10, 20])

    def _connect_with_retry(
        self,
        max_retries: int = 3,
        backoff_seconds: Optional[list] = None,
    ) -> bool:
        """
        Conecta ao MT5 com retry automático.

        Args:
            max_retries: Número máximo de tentativas
            backoff_seconds: Lista de segundos para aguardar entre tentativas

        Returns:
            True se conectado, False se todos os retries falharem.
        """
        if backoff_seconds is None:
            backoff_seconds = [5, 10, 20]

        for attempt in range(max_retries):
            try:
                if self._connect_single():
                    logger.info("MT5 connection established successfully")
                    return True

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = backoff_seconds[attempt]
                    logger.warning(
                        f"MT5 connection attempt {attempt + 1}/{max_retries} "
                        f"failed. Retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"MT5 connection failed after {max_retries} attempts: {e}"
                    )
                    self._trading_halted = True
                    raise BrokerConnectionError(
                        f"Failed to connect to MT5 after {max_retries} attempts"
                    )

        return False

    def _connect_single(self) -> bool:
        """
        Tenta uma única conexão ao MT5 (sem retry).

        Returns:
            True se bem-sucedido, False caso contrário.

        Raises:
            BrokerConnectionError se ocorrer erro

        """
        try:
            import MetaTrader5 as mt5
            import os

            self._mt5 = mt5

            # S2-5: Validar que terminal_exe_path é válido ANTES de usar
            # Se válido, usa o path específico. Se não, deixa MT5 auto-detectar
            terminal_path_valid = None
            if self.terminal_exe_path and isinstance(self.terminal_exe_path, str):
                if os.path.isfile(self.terminal_exe_path):
                    terminal_path_valid = self.terminal_exe_path
                else:
                    raise BrokerConnectionError(
                        f"Terminal executable not found: {self.terminal_exe_path}\n"
                        f"Verifique o MT5_TERMINAL_PATH em .env ou que o terminal está instalado"
                    )

            # Inicializa conexão ao MT5
            # If terminal path is valid, use it. Otherwise let MT5 auto-detect ✅
            if terminal_path_valid:
                if not mt5.initialize(path=terminal_path_valid):
                    raise BrokerConnectionError(
                        f"MT5 initialize failed: {mt5.last_error()}"
                    )
            else:
                # Path is None/empty - let MT5 auto-detect the terminal
                if not mt5.initialize():
                    raise BrokerConnectionError(
                        f"MT5 initialize failed (auto-detect): {mt5.last_error()}"
                    )

            # Login na conta
            authorized = mt5.login(
                login=self.login,
                password=self.password,
                server=self.server,
                timeout=self.timeout,
            )

            if authorized:
                # Sincronizacao Dinamica de Timezone (GAP-02 / Oportunidade 7)
                try:
                    # Tenta capturar o server time de um simbolo ativo para
                    # calcular o offset real
                    tick = mt5.symbol_info_tick("WIN$N") or mt5.symbol_info_tick(
                        "WDO$N"
                    )
                    if tick:
                        server_time_secs = tick.time
                        local_time_secs = int(datetime.utcnow().timestamp())
                        # Alvo: UTC-3 (Brasilia)
                        target_brt_secs = local_time_secs - (3 * 3600)
                        auto_offset = target_brt_secs - server_time_secs
                        # Arredonda para horas cheias para evitar jitter de rede
                        self._time_offset_seconds = round(auto_offset / 3600) * 3600
                except Exception:
                    pass

            if not authorized:
                raise BrokerConnectionError(
                    f"MT5 login failed: {mt5.last_error()}"
                )

            # Salva fingerprint após conexão bem-sucedida (S2-5)
            self._save_session_fingerprint()
            self._trading_halted = False

            return True

        except ImportError:
            raise BrokerConnectionError(
                "MetaTrader5 package not installed. "
                "Install with: pip install MetaTrader5"
            )
        except BrokerConnectionError:
            raise
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
            return float(info.trade_tick_size)
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
                return str(info.basis)

        # Fallback: busca contratos WIN ativos
        symbols = self._mt5.symbols_get(group="*WIN*")
        if symbols:
            for s in symbols:
                if (s.trade_mode == self._mt5.SYMBOL_TRADE_MODE_FULL
                        and s.name.startswith("WIN")
                        and not s.name.endswith("$N")):
                    return str(s.name)

        return symbol_code

    def send_order(self, order: Order) -> str:
        """Envia ordem ao MT5."""
        # Valida isolamento antes de operação crítica (S2-5)
        self._ensure_connected_with_isolation()

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
            "magic": order.magic_number,
            "comment": self._build_order_comment(order),
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

        # Coleta info do simbolo para diagnostico
        symbol_info = self._mt5.symbol_info(tradable_symbol)
        symbol_diag = {}
        if symbol_info is not None:
            symbol_diag = {
                "trade_mode": getattr(symbol_info, "trade_mode", "?"),
                "session_open": getattr(symbol_info, "session_open", "?"),
                "session_close": getattr(symbol_info, "session_close", "?"),
                "volume_min": getattr(symbol_info, "volume_min", "?"),
                "volume_max": getattr(symbol_info, "volume_max", "?"),
                "bid": getattr(symbol_info, "bid", "?"),
                "ask": getattr(symbol_info, "ask", "?"),
                "spread": getattr(symbol_info, "spread", "?"),
            }

        # Envia ordem
        logger.debug(
            "[send_order] Enviando request ao MT5 | simbolo=%s | request=%s | symbol_diag=%s",
            tradable_symbol,
            request,
            symbol_diag,
        )
        result = self._mt5.order_send(request)

        if result is None:
            last_err = self._mt5.last_error()
            logger.error(
                "[send_order] order_send retornou None | simbolo=%s | last_error=%s"
                " | request=%s | symbol_diag=%s",
                tradable_symbol,
                last_err,
                request,
                symbol_diag,
            )
            raise OrderExecutionError(
                f"order_send retornou None. Símbolo: {tradable_symbol} | "
                f"Last error: {last_err} | Request: {request}"
            )

        if result.retcode != self._mt5.TRADE_RETCODE_DONE:
            logger.error(
                "[send_order] Ordem rejeitada | retcode=%s | comment=%s"
                " | simbolo=%s | request=%s | symbol_diag=%s | result=%s",
                result.retcode,
                result.comment,
                tradable_symbol,
                request,
                symbol_diag,
                result,
            )
            raise OrderExecutionError(
                f"Order execution failed: {result.comment} (code: {result.retcode}) | "
                f"Símbolo: {tradable_symbol} | Request: {request} | "
                f"Symbol diag: {symbol_diag}"
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

    def obter_preco_saida_por_ticket(
        self,
        position_ticket: int,
        symbol: Optional[Symbol] = None,
        side: Optional[OrderSide] = None,
        lookback_days: int = 7,
    ) -> Optional[float]:
        """Obtém o preço real de saída de um ticket pela história do MT5.

        Prioridade:
        1. Deal de fechamento na history_deals_get()
        2. Tick atual da posição ainda visível no terminal
        3. Tick atual do símbolo, como fallback seguro
        """
        self._ensure_connected()

        ticket_int = int(position_ticket)

        # 1) Se a posição ainda existir no terminal, usar preço atual mais seguro
        try:
            positions = self._mt5.positions_get()
            if positions:
                for position in positions:
                    pos_ticket = int(getattr(position, "ticket", 0) or 0)
                    if pos_ticket != ticket_int:
                        continue

                    pos_symbol = str(getattr(position, "symbol", "") or "")
                    tick = self._mt5.symbol_info_tick(pos_symbol)
                    if tick is not None:
                        if int(getattr(position, "type", -1)) == self._mt5.ORDER_TYPE_BUY:
                            return float(getattr(tick, "bid", 0.0) or 0.0)
                        return float(getattr(tick, "ask", 0.0) or 0.0)

                    price_current = getattr(position, "price_current", None)
                    if price_current is not None:
                        return float(price_current)
        except Exception as e:
            logger.debug("Failed to resolve live position price for ticket %s: %s", ticket_int, e)

        # 2) Histórico de deals para obter o preço real de fechamento
        try:
            if hasattr(self._mt5, "history_deals_get"):
                end_dt = datetime.utcnow()
                start_dt = end_dt - timedelta(days=max(1, int(lookback_days)))
                deals = self._mt5.history_deals_get(start_dt, end_dt)
                if deals:
                    candidatos = []
                    for deal in deals:
                        deal_ticket = int(
                            getattr(deal, "position_id", 0)
                            or getattr(deal, "position", 0)
                            or 0
                        )
                        if deal_ticket != ticket_int:
                            continue

                        entry = getattr(deal, "entry", None)
                        entry_text = str(entry).upper() if entry is not None else ""
                        if entry_text and ("OUT" not in entry_text and "CLOSE" not in entry_text):
                            continue

                        candidatos.append(deal)

                    if candidatos:
                        candidatos.sort(
                            key=lambda deal: int(getattr(deal, "time", 0) or 0),
                            reverse=True,
                        )
                        preco = getattr(candidatos[0], "price", None)
                        if preco is not None:
                            return float(preco)
        except Exception as e:
            logger.debug("Failed to resolve history price for ticket %s: %s", ticket_int, e)

        # 3) Fallback por símbolo para evitar retorno vazio quando a história
        # ainda não está disponível no terminal.
        try:
            if symbol is not None:
                tick = self._mt5.symbol_info_tick(symbol.code)
                if tick is not None:
                    if side == OrderSide.BUY:
                        return float(getattr(tick, "bid", 0.0) or 0.0)
                    if side == OrderSide.SELL:
                        return float(getattr(tick, "ask", 0.0) or 0.0)
                    return float(
                        getattr(tick, "last", 0.0)
                        or getattr(tick, "bid", 0.0)
                        or getattr(tick, "ask", 0.0)
                        or 0.0
                    )
        except Exception as e:
            logger.debug("Failed to resolve fallback symbol price for ticket %s: %s", ticket_int, e)

        return None

    def obter_pnl_fechado(
        self,
        ticket: int,
        magic_number: int,
        lookback_days: int = 7,
    ) -> Optional[float]:
        """Obtém o profit de um deal fechado pelo ticket e magic_number.

        Retorna o campo ``profit`` do deal cujo ``position_id`` bate com
        ``ticket`` e cujo ``magic`` bate com ``magic_number``.
        Retorna ``None`` quando nao encontrado ou em caso de excecao.

        Args:
            ticket: ID da posicao a localizar no historico de deals.
            magic_number: Numero magico do agente — usado para filtrar
                deals e garantir isolamento entre agentes.
            lookback_days: Janela de busca retroativa em dias.
        """
        self._ensure_connected()

        ticket_int = int(ticket)
        try:
            if not hasattr(self._mt5, "history_deals_get"):
                return None

            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(days=max(1, int(lookback_days)))
            deals = self._mt5.history_deals_get(start_dt, end_dt)
            if not deals:
                return None

            for deal in deals:
                deal_position_id = int(
                    getattr(deal, "position_id", 0)
                    or getattr(deal, "position", 0)
                    or 0
                )
                if deal_position_id != ticket_int:
                    continue

                deal_magic = int(getattr(deal, "magic", 0) or 0)
                if deal_magic != int(magic_number):
                    continue

                profit = getattr(deal, "profit", None)
                if profit is None:
                    return None
                return float(profit)

        except Exception as e:
            logger.debug(
                "obter_pnl_fechado: excecao ao buscar ticket=%s magic=%s: %s",
                ticket_int,
                magic_number,
                e,
            )

        return None

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

        tradable_symbol = self._resolve_tradable_symbol(str(position.symbol))

        if int(position.type) == self._mt5.ORDER_TYPE_BUY:
            order_type = self._mt5.ORDER_TYPE_SELL
        else:
            order_type = self._mt5.ORDER_TYPE_BUY

        tick = self._mt5.symbol_info_tick(tradable_symbol)
        if tick is None and tradable_symbol != position.symbol:
            tick = self._mt5.symbol_info_tick(position.symbol)
        if tick is None:
            raise OrderExecutionError(
                f"close_position_by_ticket: sem tick para {position.symbol}"
            )

        tick_size = self._get_tick_size(tradable_symbol)
        close_price = tick.bid if order_type == self._mt5.ORDER_TYPE_SELL else tick.ask

        base_request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": tradable_symbol,
            "volume": float(position.volume),
            "type": order_type,
            "position": int(position.ticket),
            "price": self._round_to_tick(float(close_price), tick_size),
            "deviation": 10,
            "magic": 234000,
            "comment": f"Watchdog close pos={position.ticket}",
        }

        filling_options = [
            getattr(self._mt5, "ORDER_FILLING_RETURN", None),
            getattr(self._mt5, "ORDER_FILLING_IOC", None),
            getattr(self._mt5, "ORDER_FILLING_FOK", None),
        ]
        filling_options = [f for f in filling_options if f is not None]

        request_variants = []
        for filling in filling_options:
            request_variants.append(
                {
                    **base_request,
                    "type_time": self._mt5.ORDER_TIME_GTC,
                    "type_filling": filling,
                }
            )
            request_variants.append(
                {
                    **base_request,
                    "type_filling": filling,
                }
            )

        last_error: Optional[str] = None
        for request in request_variants:
            result = self._mt5.order_send(request)
            if result is None:
                last_error = f"order_send None | last_error={self._mt5.last_error()}"
                continue
            if result.retcode == self._mt5.TRADE_RETCODE_DONE:
                return True
            last_error = f"{result.comment} (code: {result.retcode})"

        raise OrderExecutionError(
            f"close_position_by_ticket falhou: {last_error} | symbol={tradable_symbol} | ticket={position_ticket}"
        )

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

    def get_time_offset_hours(self) -> int:
        """Retorna o offset de fuso horario detectado (horas)."""
        return int(self._time_offset_seconds / 3600) if self._time_offset_seconds is not None else -3

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
