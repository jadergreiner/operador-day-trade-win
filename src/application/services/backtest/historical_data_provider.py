"""Provedor de dados historicos para backtest do MacroScore."""

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
import os

from src.application.services.macro_score.forex_handler import ForexScoreHandler
from src.application.services.macro_score.futures_resolver import (
    FuturesContractResolver,
)
from src.application.services.macro_score.item_registry import MacroScoreItemConfig
from src.domain.enums.macro_score_enums import AssetCategory, ScoringType
from src.domain.enums.trading_enums import TimeFrame
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import Candle, MT5Adapter
from src.infrastructure.database.schema import MarketDataModel, get_session
from decimal import Decimal
from src.domain.value_objects import Price

logger = logging.getLogger(__name__)

# Timeout em segundos para cada chamada MT5 de carregamento de dados
_MT5_CALL_TIMEOUT = 8


def _print_progress(current: int, total: int, symbol: str, status: str) -> None:
    """Imprime progresso de carregamento inline (sobreescreve a linha)."""
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = "#" * filled + "-" * (bar_len - filled)
    pct = (current / total * 100) if total > 0 else 0
    line = f"\r  [{bar}] {pct:5.1f}% ({current}/{total}) {symbol:<12} {status}"
    sys.stdout.write(line[:100].ljust(100))
    sys.stdout.flush()


class HistoricalDataProvider:
    """Carrega e fornece dados historicos para backtest barra-a-barra.

    Pre-carrega todos os dados necessarios para uma data especifica:
    1. Candle D1 de cada simbolo (preco de abertura do dia)
    2. Barras M15 de cada simbolo (precos intraday)
    3. Barras M5 do WIN$N (para indicadores tecnicos)

    A cada step do backtest, fornece o close do M15 como "preco atual".
    """

    def __init__(self, mt5_adapter: MT5Adapter, date: datetime) -> None:
        self._mt5 = mt5_adapter
        self._date = date

        # Dados pre-carregados
        self._daily_opens: dict[str, Decimal] = {}
        self._daily_closes: dict[str, Decimal] = {}
        self._m15_bars: dict[str, list[Candle]] = {}
        self._win_m15: list[Candle] = []
        self._win_m5: list[Candle] = []

        # Mapeamento simbolo registry -> simbolo resolvido MT5
        self._resolved_symbols: dict[str, Optional[str]] = {}

        # Sub-servicos para resolucao
        self._futures_resolver = FuturesContractResolver(mt5_adapter)
        self._forex_handler = ForexScoreHandler(mt5_adapter)

        # Overrides conhecidos para simbolos com baixa disponibilidade historica
        self._symbol_overrides = {
            "BRI": "BRIM11",
            "EUR": "EURO11",
            "SJC": "SJCK26",
        }

        # Simbolos que devem usar apenas dados do DB (evita travamento no MT5)
        self._db_only_symbols = {"CNY", "TRY", "ZAR", "CLP", "HSI"}

        # Estatisticas de carregamento
        self.symbols_loaded: int = 0
        self.symbols_failed: int = 0
        self.load_errors: list[str] = []
        # carregar blacklist (simbolos problemáticos que travam MT5)
        self._blacklist = self._load_blacklist()

    def _load_blacklist(self) -> set:
        """Carrega lista de simbolos a serem ignorados a partir de data/bad_symbols.txt"""
        path = os.path.join(os.getcwd(), 'data', 'bad_symbols.txt')
        if not os.path.exists(path):
            return set()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                items = {line.strip() for line in f if line.strip() and not line.strip().startswith('#')}
            return items
        except Exception:
            return set()

    def is_registry_symbol_blacklisted(self, registry_symbol: str) -> bool:
        """Verifica se um simbolo do registry foi mapeado para um simbolo bloqueado."""
        resolved = self._resolved_symbols.get(registry_symbol)
        if resolved is None:
            return False
        return resolved in self._blacklist

    def load_all(self, registry: list[MacroScoreItemConfig]) -> None:
        """Pre-carrega todos os dados historicos para a data.

        Args:
            registry: Lista de itens do macro score.
        """
        # Inicio do dia para buscar barras
        day_start = self._date.replace(hour=9, minute=0, second=0, microsecond=0)

        # Coletar simbolos unicos a resolver
        symbols_to_load: dict[str, MacroScoreItemConfig] = {}
        for item in registry:
            if item.scoring_type == ScoringType.TECHNICAL_INDICATOR:
                continue
            symbols_to_load[item.symbol] = item

        total = len(symbols_to_load)
        logger.info(
            "Carregando dados historicos para %s - %d simbolos",
            self._date.strftime("%d/%m/%Y"),
            total,
        )

        # Resolver e carregar cada simbolo (com progresso)
        for idx, (symbol_key, item) in enumerate(symbols_to_load.items(), 1):
            _print_progress(idx, total, symbol_key, "resolvendo...")

            # Evitar travamento no MT5: usar DB direto quando houver dados locais
            m15_db = self._load_m15_from_db(symbol_key, day_start)
            if m15_db:
                self._resolved_symbols[symbol_key] = symbol_key
                self._m15_bars[symbol_key] = m15_db
                daily_open = self._load_daily_open_from_db(symbol_key, self._date)
                if daily_open is None and symbol_key not in self._db_only_symbols:
                    resolved_contract = None
                    try:
                        resolved_contract = self._resolve_symbol(item)
                    except Exception:
                        resolved_contract = None
                    if resolved_contract and resolved_contract != symbol_key:
                        daily_open = self._load_daily_open_from_db(
                            resolved_contract, self._date
                        )
                        if daily_open is None:
                            daily_open = self._load_daily_open_safe(
                                resolved_contract
                            )
                    else:
                        daily_open = self._load_daily_open_safe(symbol_key)
                if daily_open is not None:
                    self._daily_opens[symbol_key] = daily_open
                if symbol_key not in self._db_only_symbols:
                    try:
                        resolved_contract = self._resolve_symbol(item)
                    except Exception:
                        resolved_contract = None
                    target_symbol = resolved_contract or symbol_key
                    if len(m15_db) < 20:
                        day_start_ts = self._date.replace(hour=9, minute=0, second=0, microsecond=0)
                        day_end_ts = self._date.replace(hour=18, minute=15, second=0, microsecond=0)
                        mt5_bars = self._load_m15_range_safe(target_symbol, day_start_ts, day_end_ts)
                        if mt5_bars:
                            try:
                                self._save_candles_to_db(target_symbol, TimeFrame.M15, mt5_bars)
                            except Exception:
                                pass
                            # Atualizar em memoria para evitar quedas no meio do dia
                            if target_symbol == symbol_key:
                                self._m15_bars[symbol_key] = mt5_bars
                            else:
                                self._m15_bars[symbol_key] = mt5_bars
                    prev_date = self._date - timedelta(days=1)
                    prev_db = self._load_m15_from_db_for_date(target_symbol, prev_date)
                    if len(prev_db) < 20:
                        prev_start = prev_date.replace(hour=9, minute=0, second=0, microsecond=0)
                        prev_end = prev_date.replace(hour=18, minute=15, second=0, microsecond=0)
                        mt5_prev = self._load_m15_range_safe(target_symbol, prev_start, prev_end)
                        if mt5_prev:
                            try:
                                self._save_candles_to_db(target_symbol, TimeFrame.M15, mt5_prev)
                            except Exception:
                                pass
                self.symbols_loaded += 1
                _print_progress(idx, total, symbol_key, f"DB ({len(m15_db)} barras)")
                continue

            daily_candle_db = self._load_daily_candle_from_db(symbol_key, self._date)
            if daily_candle_db is not None:
                daily_open, daily_close = daily_candle_db
                self._resolved_symbols[symbol_key] = symbol_key
                self._daily_opens[symbol_key] = daily_open
                self._daily_closes[symbol_key] = daily_close
                self.symbols_loaded += 1
                _print_progress(idx, total, symbol_key, "DB D1")
                continue

            if symbol_key in self._db_only_symbols:
                self._resolved_symbols[symbol_key] = symbol_key
                self.symbols_failed += 1
                self.load_errors.append(
                    f"{symbol_key}: sem dados no DB (db-only)"
                )
                _print_progress(idx, total, symbol_key, "DB vazio")
                continue

            # Verificar conexao antes de qualquer chamada MT5
            self._ensure_mt5_connected()

            try:
                resolved = self._resolve_symbol(item)
            except Exception as e:
                resolved = None
                logger.debug("Excecao ao resolver %s: %s", symbol_key, e)

            self._resolved_symbols[symbol_key] = resolved

            if resolved is None:
                self.symbols_failed += 1
                self.load_errors.append(f"{symbol_key}: simbolo nao resolvido")
                _print_progress(idx, total, symbol_key, "FALHOU")
                continue

            # Se o simbolo estiver na blacklist, tentar usar D1 do DB antes de pular
            if resolved in self._blacklist:
                daily_candle = self._load_daily_candle_from_db(resolved, self._date)
                if daily_candle is None and symbol_key != resolved:
                    daily_candle = self._load_daily_candle_from_db(
                        symbol_key, self._date
                    )
                if daily_candle is not None:
                    daily_open, daily_close = daily_candle
                    self._daily_opens[resolved] = daily_open
                    self._daily_closes[resolved] = daily_close
                    self.symbols_loaded += 1
                    _print_progress(idx, total, symbol_key, "DB D1")
                    continue
                self.symbols_failed += 1
                self.load_errors.append(
                    f"{symbol_key} ({resolved}): simbolo bloqueado (blacklist)"
                )
                _print_progress(idx, total, symbol_key, "BLOQUEADO")
                continue

            _print_progress(idx, total, symbol_key, f"-> {resolved}")

            # Garantir M15 do dia e do dia anterior no DB
            if symbol_key not in self._db_only_symbols:
                current_db = self._load_m15_from_db_for_date(resolved, self._date)
                if len(current_db) < 20:
                    day_start_ts = self._date.replace(hour=9, minute=0, second=0, microsecond=0)
                    day_end_ts = self._date.replace(hour=18, minute=15, second=0, microsecond=0)
                    mt5_bars = self._load_m15_range_safe(resolved, day_start_ts, day_end_ts)
                    if mt5_bars:
                        try:
                            self._save_candles_to_db(resolved, TimeFrame.M15, mt5_bars)
                        except Exception:
                            pass
                prev_date = self._date - timedelta(days=1)
                prev_db = self._load_m15_from_db_for_date(resolved, prev_date)
                if len(prev_db) < 20:
                    prev_start = prev_date.replace(hour=9, minute=0, second=0, microsecond=0)
                    prev_end = prev_date.replace(hour=18, minute=15, second=0, microsecond=0)
                    mt5_prev = self._load_m15_range_safe(resolved, prev_start, prev_end)
                    if mt5_prev:
                        try:
                            self._save_candles_to_db(resolved, TimeFrame.M15, mt5_prev)
                        except Exception:
                            pass

            # Tentar carregar M15 do DB antes de chamar MT5
            m15_bars = self._load_m15_from_db(resolved, day_start)
            if m15_bars:
                self._m15_bars[resolved] = m15_bars
                # try to load daily open from DB
                daily_open = self._load_daily_open_from_db(resolved, self._date)
                if daily_open is None:
                    daily_open = self._load_daily_open_safe(resolved)
                if daily_open is not None:
                    self._daily_opens[resolved] = daily_open
                self.symbols_loaded += 1
                _print_progress(idx, total, symbol_key, f"DB ({len(m15_bars)} barras)")
                continue

            # Fallback: usar candle D1 do DB quando nao houver M15
            daily_candle = self._load_daily_candle_from_db(resolved, self._date)
            if daily_candle is None and symbol_key != resolved:
                daily_candle = self._load_daily_candle_from_db(
                    symbol_key, self._date
                )
            if daily_candle is not None:
                daily_open, daily_close = daily_candle
                self._daily_opens[resolved] = daily_open
                self._daily_closes[resolved] = daily_close
                self.symbols_loaded += 1
                _print_progress(idx, total, symbol_key, "DB D1")
                continue

            # Carregar D1 (abertura do dia) - com timeout
            daily_open = self._load_daily_open_safe(resolved)
            if daily_open is not None:
                self._daily_opens[resolved] = daily_open

            # Carregar M15 da data - com timeout
            m15_bars = self._load_m15_bars_safe(resolved, day_start)
            if m15_bars:
                self._m15_bars[resolved] = m15_bars
                # Persistir no DB para reuso
                try:
                    self._save_candles_to_db(resolved, TimeFrame.M15, m15_bars)
                except Exception:
                    pass
                self.symbols_loaded += 1
                _print_progress(
                    idx, total, symbol_key, f"OK ({len(m15_bars)} barras)"
                )
            else:
                self.symbols_failed += 1
                self.load_errors.append(
                    f"{symbol_key} ({resolved}): sem barras M15"
                )
                _print_progress(idx, total, symbol_key, "sem M15")

        # Finalizar linha de progresso
        print()

        # Carregar barras do WIN$N
        print("  Carregando barras WIN$N (M15 + M5)...", end="", flush=True)
        self._ensure_mt5_connected()
        self._load_win_bars(day_start)
        print(f" OK ({len(self._win_m15)} M15, {len(self._win_m5)} M5)")

        logger.info(
            "Dados carregados: %d OK, %d falhas, %d barras WIN M15, %d barras WIN M5",
            self.symbols_loaded,
            self.symbols_failed,
            len(self._win_m15),
            len(self._win_m5),
        )

    # ====================================
    # Chamadas MT5 com timeout
    # ====================================

    def _call_with_timeout(self, fn, timeout: int = _MT5_CALL_TIMEOUT):
        """Executa uma funcao com timeout usando thread.

        Se a chamada MT5 travar (ex: copy_rates_from em contrato sem dados),
        retorna None apos o timeout e reconecta ao MT5.

        IMPORTANTE: Nao usar 'with' no ThreadPoolExecutor, pois o __exit__
        chama shutdown(wait=True) que bloqueia se a thread estiver presa.
        """
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(fn)
        try:
            result = future.result(timeout=timeout)
            executor.shutdown(wait=False)
            return result
        except FuturesTimeout:
            # Nao esperar a thread presa - liberar imediatamente
            executor.shutdown(wait=False)
            logger.warning("Timeout na chamada MT5 (>%ds)", timeout)
            self._reconnect_mt5()
            return None
        except Exception as e:
            executor.shutdown(wait=False)
            logger.debug("Erro na chamada MT5: %s", e)
            return None

    def _ensure_mt5_connected(self) -> None:
        """Verifica se MT5 esta conectado. Reconecta se necessario."""
        try:
            if not self._mt5.is_connected():
                self._reconnect_mt5()
        except Exception:
            self._reconnect_mt5()

    def _reconnect_mt5(self) -> None:
        """Tenta reconectar ao MT5."""
        try:
            logger.info("Reconectando ao MT5...")
            self._mt5.disconnect()
            self._mt5.connect()
            logger.info("Reconexao bem-sucedida")
        except Exception as e:
            logger.error("Falha ao reconectar MT5: %s", e)

    def _load_daily_open_safe(self, resolved_symbol: str) -> Optional[Decimal]:
        """Carrega preco de abertura D1 com timeout."""
        def _load():
            candles = self._mt5.get_candles(
                symbol=Symbol(resolved_symbol),
                timeframe=TimeFrame.D1,
                count=1,
                start_time=self._date.replace(hour=0, minute=0, second=0),
            )
            if candles:
                return candles[0].open.value
            return None

        try:
            return self._call_with_timeout(_load)
        except Exception as e:
            logger.debug("Erro ao carregar D1 de %s: %s", resolved_symbol, e)
            return None

    # ====================================
    # Persistencia em DB
    # ====================================

    def _save_candles_to_db(self, symbol: str, timeframe: TimeFrame, candles: list[Candle]) -> None:
        """Salva candles no banco (market_data)."""
        session = get_session()
        try:
            for c in candles:
                # evitar duplicados por timestamp/symbol/timeframe
                exists = (
                    session.query(MarketDataModel)
                    .filter(MarketDataModel.symbol == symbol)
                    .filter(MarketDataModel.timeframe == timeframe.name)
                    .filter(MarketDataModel.timestamp == c.timestamp)
                    .first()
                )
                if exists:
                    continue

                mdl = MarketDataModel(
                    symbol=symbol,
                    timestamp=c.timestamp,
                    timeframe=timeframe.name,
                    open=c.open.value,
                    high=c.high.value,
                    low=c.low.value,
                    close=c.close.value,
                    volume=c.volume,
                )
                session.add(mdl)
            session.commit()
        finally:
            session.close()

    def _load_m15_from_db(self, symbol: str, day_start: datetime) -> list[Candle]:
        """Carrega candles M15 do DB para a data alvo se existirem."""
        return self._load_m15_from_db_for_date(symbol, self._date)

    def _load_m15_from_db_for_date(self, symbol: str, date: datetime) -> list[Candle]:
        """Carrega candles M15 do DB para uma data especifica."""
        session = get_session()
        try:
            day = date.date()
            rows = (
                session.query(MarketDataModel)
                .filter(MarketDataModel.symbol == symbol)
                .filter(MarketDataModel.timeframe == TimeFrame.M15.name)
                .filter(MarketDataModel.timestamp >= datetime.combine(day, datetime.min.time()))
                .filter(MarketDataModel.timestamp <= datetime.combine(day, datetime.max.time()))
                .order_by(MarketDataModel.timestamp)
                .all()
            )
            candles: list[Candle] = []
            for r in rows:
                candles.append(
                    Candle(
                        symbol=Symbol(symbol),
                        timeframe=TimeFrame.M15,
                        open=Price(Decimal(r.open)),
                        high=Price(Decimal(r.high)),
                        low=Price(Decimal(r.low)),
                        close=Price(Decimal(r.close)),
                        volume=int(r.volume),
                        timestamp=r.timestamp,
                    )
                )
            return candles
        finally:
            session.close()

    def _load_m5_from_db(self, symbol: str, start: datetime, end: datetime) -> list[Candle]:
        """Carrega candles M5 do DB em um intervalo informado."""
        session = get_session()
        try:
            rows = (
                session.query(MarketDataModel)
                .filter(MarketDataModel.symbol == symbol)
                .filter(MarketDataModel.timeframe == TimeFrame.M5.name)
                .filter(MarketDataModel.timestamp >= start)
                .filter(MarketDataModel.timestamp <= end)
                .order_by(MarketDataModel.timestamp)
                .all()
            )
            candles: list[Candle] = []
            for r in rows:
                candles.append(
                    Candle(
                        symbol=Symbol(symbol),
                        timeframe=TimeFrame.M5,
                        open=Price(Decimal(r.open)),
                        high=Price(Decimal(r.high)),
                        low=Price(Decimal(r.low)),
                        close=Price(Decimal(r.close)),
                        volume=int(r.volume),
                        timestamp=r.timestamp,
                    )
                )
            return candles
        finally:
            session.close()

    def _load_daily_open_from_db(self, symbol: str, date: datetime) -> Optional[Decimal]:
        session = get_session()
        try:
            day = date.date()
            row = (
                session.query(MarketDataModel)
                .filter(MarketDataModel.symbol == symbol)
                .filter(MarketDataModel.timeframe == TimeFrame.D1.name)
                .filter(MarketDataModel.timestamp >= datetime.combine(day, datetime.min.time()))
                .filter(MarketDataModel.timestamp <= datetime.combine(day, datetime.max.time()))
                .order_by(MarketDataModel.timestamp)
                .first()
            )
            if row:
                return Decimal(row.open)
            return None
        finally:
            session.close()

    def _load_daily_candle_from_db(
        self, symbol: str, date: datetime
    ) -> Optional[tuple[Decimal, Decimal]]:
        session = get_session()
        try:
            day = date.date()
            row = (
                session.query(MarketDataModel)
                .filter(MarketDataModel.symbol == symbol)
                .filter(MarketDataModel.timeframe == TimeFrame.D1.name)
                .filter(MarketDataModel.timestamp >= datetime.combine(day, datetime.min.time()))
                .filter(MarketDataModel.timestamp <= datetime.combine(day, datetime.max.time()))
                .order_by(MarketDataModel.timestamp)
                .first()
            )
            if row:
                return (Decimal(row.open), Decimal(row.close))
            return None
        finally:
            session.close()

    def _load_m15_bars_safe(
        self, resolved_symbol: str, day_start: datetime
    ) -> list[Candle]:
        """Carrega barras M15 da data com timeout."""
        target_date = self._date.date()

        def _load():
            candles = self._mt5.get_candles(
                symbol=Symbol(resolved_symbol),
                timeframe=TimeFrame.M15,
                count=100,
                start_time=day_start,
            )
            if not candles:
                return []
            return [c for c in candles if c.timestamp.date() == target_date]

        try:
            result = self._call_with_timeout(_load)
            return result if result else []
        except Exception as e:
            logger.debug("Erro ao carregar M15 de %s: %s", resolved_symbol, e)
            return []

    def _load_m15_range_safe(
        self, resolved_symbol: str, start_time: datetime, end_time: datetime
    ) -> list[Candle]:
        """Carrega barras M15 em um intervalo com timeout."""
        def _load():
            candles = self._mt5.get_candles_range(
                symbol=Symbol(resolved_symbol),
                timeframe=TimeFrame.M15,
                start_time=start_time,
                end_time=end_time,
            )
            return candles or []

        try:
            result = self._call_with_timeout(_load)
            return result if result else []
        except Exception as e:
            logger.debug("Erro ao carregar M15 range de %s: %s", resolved_symbol, e)
            return []

    # ====================================
    # Resolucao de simbolos
    # ====================================

    def _resolve_symbol(self, config: MacroScoreItemConfig) -> Optional[str]:
        """Resolve o simbolo MT5 para um item do registry."""
        try:
            override = self._symbol_overrides.get(config.symbol)
            if override:
                if self._mt5.select_symbol(override):
                    tick = self._mt5.get_symbol_info_tick(override)
                    if tick is not None:
                        return override

            if config.is_futures:
                return self._futures_resolver.resolve(config.symbol)

            if config.category == AssetCategory.FOREX:
                return self._forex_handler.resolve_forex_symbol(config.symbol)

            # Ativo normal
            if self._mt5.select_symbol(config.symbol):
                return config.symbol

            return None
        except Exception as e:
            logger.warning("Erro ao resolver %s: %s", config.symbol, e)
            return None

    # ====================================
    # Carregamento WIN$N
    # ====================================

    def _resolve_win_symbol(self) -> Optional[str]:
        """Resolve simbolo WIN com fallback entre alternativas disponiveis."""
        candidates = [
            "WIN$N",
            "WIN$D",
            "WIN$",
            "WIN@N",
            "WIN@",
            "WING26",
        ]

        for symbol in candidates:
            try:
                if self._mt5.select_symbol(symbol):
                    tick = self._mt5.get_symbol_info_tick(symbol)
                    if tick is not None:
                        return symbol
            except Exception:
                continue

        # fallback: tentar qualquer simbolo com prefixo WIN
        try:
            for symbol in self._mt5.get_available_symbols("WIN"):
                if self._mt5.select_symbol(symbol):
                    tick = self._mt5.get_symbol_info_tick(symbol)
                    if tick is not None:
                        return symbol
        except Exception:
            return None

        return None

    def _load_win_bars(self, day_start: datetime) -> None:
        """Carrega barras M15 e M5 do WIN$N para a data."""
        win_symbol_code = self._resolve_win_symbol()
        if not win_symbol_code:
            return

        win_symbol = Symbol(win_symbol_code)
        target_date = self._date.date()

        # Intervalo B3 (horario Brasilia). Ajuste se necessario via fuso do broker.
        b3_start = self._date.replace(hour=9, minute=0, second=0, microsecond=0)
        b3_end = self._date.replace(hour=18, minute=15, second=0, microsecond=0)

        # M15 do WIN
        def _load_m15():
            candles = self._mt5.get_candles_range(
                symbol=win_symbol,
                timeframe=TimeFrame.M15,
                start_time=b3_start,
                end_time=b3_end,
            )
            if candles:
                return [c for c in candles if c.timestamp.date() == target_date]
            return []

        result = self._call_with_timeout(_load_m15)
        if result:
            self._win_m15 = result

        self._ensure_mt5_connected()

        # M5 do WIN (para indicadores tecnicos)
        m5_start = b3_start - timedelta(days=2)

        def _load_m5():
            candles = self._mt5.get_candles_range(
                symbol=win_symbol,
                timeframe=TimeFrame.M5,
                start_time=m5_start,
                end_time=b3_end,
            )
            if candles:
                return candles
            return []

        result = self._call_with_timeout(_load_m5)
        if result:
            self._win_m5 = result

        # Persistir M5 do WIN no DB para reuso futuro
        if self._win_m5:
            try:
                self._save_candles_to_db(win_symbol_code, TimeFrame.M5, self._win_m5)
            except Exception:
                pass

        # Pre-carregar M5 anteriores para ter historico suficiente nos indicadores
        if len(self._win_m5) < 30:
            prev_day_start = self._date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
            prev_day_end = prev_day_start.replace(hour=23, minute=59, second=59)
            prev_db = self._load_m5_from_db(win_symbol_code, prev_day_start, prev_day_end)
            if prev_db:
                merged = prev_db + self._win_m5
                self._win_m5 = merged[-200:]

        if len(self._win_m5) < 30:
            prev_start = b3_start - timedelta(hours=6)
            prev_end = b3_start

            def _load_prev_m5():
                candles = self._mt5.get_candles_range(
                    symbol=win_symbol,
                    timeframe=TimeFrame.M5,
                    start_time=prev_start,
                    end_time=prev_end,
                )
                if candles:
                    return [c for c in candles if c.timestamp < b3_start]
                return []

            prev_result = self._call_with_timeout(_load_prev_m5)
            if not prev_result:
                wide_start = b3_start - timedelta(days=2)

                def _load_prev_window_m5():
                    candles = self._mt5.get_candles_range(
                        symbol=win_symbol,
                        timeframe=TimeFrame.M5,
                        start_time=wide_start,
                        end_time=b3_start,
                    )
                    if candles:
                        return [c for c in candles if c.timestamp < b3_start]
                    return []

                prev_result = self._call_with_timeout(_load_prev_window_m5)

            if prev_result:
                # Mantem ordem cronologica e limita a 200 candles
                merged = prev_result + self._win_m5
                self._win_m5 = merged[-200:]

    # ====================================
    # Acesso a dados carregados
    # ====================================

    def get_resolved_symbol(self, registry_symbol: str) -> Optional[str]:
        """Retorna o simbolo MT5 resolvido para um simbolo do registry."""
        return self._resolved_symbols.get(registry_symbol)

    def get_daily_open(self, resolved_symbol: str) -> Optional[Decimal]:
        """Retorna preco de abertura D1 de um simbolo."""
        return self._daily_opens.get(resolved_symbol)

    def get_price_at_bar(
        self, resolved_symbol: str, bar_index: int
    ) -> Optional[Decimal]:
        """Retorna close do M15 no indice dado para um simbolo.

        Args:
            resolved_symbol: Simbolo MT5 resolvido
            bar_index: Indice da barra M15 (0-based)

        Returns:
            Preco de fechamento (close) da barra ou None.
        """
        bars = self._m15_bars.get(resolved_symbol)
        if not bars or bar_index >= len(bars):
            return self._daily_closes.get(resolved_symbol)
        return bars[bar_index].close.value

    def get_win_bars(self) -> list[Candle]:
        """Retorna todas as barras M15 do WIN$N da data."""
        return self._win_m15

    def get_win_m5_candles_up_to(self, up_to_time: datetime) -> list[Candle]:
        """Retorna ate 200 candles M5 do WIN ate o momento dado.

        Usado para calcular indicadores tecnicos no contexto historico.

        Args:
            up_to_time: Limite temporal (inclusive)

        Returns:
            Lista de candles M5 anteriores ao momento, max 200.
        """
        filtered = [c for c in self._win_m5 if c.timestamp <= up_to_time]
        return filtered[-200:]

    def get_total_win_bars(self) -> int:
        """Retorna quantidade total de barras M15 do WIN."""
        return len(self._win_m15)

    def get_symbols_with_data_at_bar(self, bar_index: int) -> int:
        """Conta quantos simbolos tem dados no indice de barra dado."""
        count = 0
        for bars in self._m15_bars.values():
            if bar_index < len(bars):
                count += 1
        # Contar simbolos com fallback D1
        count += len(self._daily_closes)
        return count
