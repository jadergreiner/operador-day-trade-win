"""MacroScoreEngine - Orquestrador principal do sistema macro score."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from src.application.services.macro_score.forex_handler import ForexScoreHandler
from src.application.services.macro_score.futures_resolver import (
    FuturesContractResolver,
)
from src.infrastructure.providers.forex_api_provider import ForexAPIProvider
from src.application.services.macro_score.item_registry import (
    MacroScoreItemConfig,
    get_item_registry,
)
from src.application.services.macro_score.technical_scorer import (
    TechnicalIndicatorScorer,
)
from src.domain.enums.macro_score_enums import (
    AssetCategory,
    CorrelationType,
    MacroSignal,
    ScoringType,
)
from src.domain.enums.trading_enums import TimeFrame
from src.domain.value_objects import Symbol
from src.domain.value_objects.macro_score import Score, Weight, WeightedScore
from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.infrastructure.database.schema import MarketDataModel, get_session
from src.infrastructure.repositories.macro_score_repository import (
    IMacroScoreRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class ItemScoreResult:
    """Resultado de pontuacao de um item individual."""

    item_number: int
    symbol: str
    name: str
    category: AssetCategory
    correlation: CorrelationType
    resolved_symbol: Optional[str]
    opening_price: Optional[Decimal]
    current_price: Optional[Decimal]
    raw_score: int  # Score antes de aplicar correlacao
    final_score: int  # Score apos aplicar correlacao (-1, 0, +1)
    weight: Decimal
    weighted_score: Decimal  # final_score * weight
    available: bool
    detail: str


@dataclass
class MacroScoreResult:
    """Resultado completo da analise macro score."""

    session_id: str
    timestamp: datetime
    items: list[ItemScoreResult]
    total_items: int
    items_available: int
    items_unavailable: int
    score_bullish: Decimal  # Soma dos scores positivos
    score_bearish: Decimal  # Soma dos scores negativos (absoluto)
    score_neutral: int  # Contagem de scores zero
    score_final: Decimal  # Soma total ponderada
    signal: MacroSignal
    confidence: Decimal
    win_price: Optional[Decimal]
    summary: str

    def get_trading_bias(self) -> str:
        """Retorna bias compativel com QuantumOperatorEngine."""
        if self.signal == MacroSignal.COMPRA:
            return "BULLISH"
        elif self.signal == MacroSignal.VENDA:
            return "BEARISH"
        return "NEUTRAL"


class MacroScoreEngine:
    """Engine principal do sistema macro score.

    Orquestra a analise de 85 itens de mercado para gerar um
    score unico de direcao para o WIN.

    Pipeline:
    1. Para cada item do registry:
       a. Resolver simbolo (futuros, forex)
       b. Buscar tick atual e preco de abertura
       c. Calcular score bruto (-1, 0, +1)
       d. Aplicar correlacao (direta/inversa)
       e. Ponderar pelo peso
    2. Agregar scores
    3. Gerar sinal (COMPRA/VENDA/NEUTRO)
    4. Persistir resultado
    """

    def __init__(
        self,
        mt5_adapter: MT5Adapter,
        repository: Optional[IMacroScoreRepository] = None,
        neutral_threshold: Decimal = Decimal("0"),
        stale_tick_seconds: int = 4 * 60 * 60,
    ) -> None:
        self._mt5 = mt5_adapter
        self._repository = repository
        self._neutral_threshold = neutral_threshold
        self._stale_tick_seconds = stale_tick_seconds

        # Sub-servicos
        self._futures_resolver = FuturesContractResolver(mt5_adapter)
        self._forex_handler = ForexScoreHandler(mt5_adapter)
        self._forex_api = ForexAPIProvider(cache_ttl_seconds=60)
        self._technical_scorer = TechnicalIndicatorScorer(mt5_adapter)

        # Cache
        self._last_result: Optional[MacroScoreResult] = None

        # Simbolos com historico intraday indisponivel
        self._live_only_symbols = {"CNY"}

    def analyze(self) -> MacroScoreResult:
        """Executa analise completa de todos os 85 itens.

        Returns:
            MacroScoreResult com score final e detalhamento.
        """
        session_id = str(uuid.uuid4())
        timestamp = datetime.now()
        registry = get_item_registry()

        logger.info(
            "Iniciando analise macro score - sessao %s - %d itens",
            session_id[:8],
            len(registry),
        )

        # Processar cada item
        item_results: list[ItemScoreResult] = []
        for item_config in registry:
            result = self._process_item(item_config)
            item_results.append(result)

        # Agregar resultados
        macro_result = self._aggregate_results(
            session_id=session_id,
            timestamp=timestamp,
            items=item_results,
        )

        self._last_result = macro_result

        # Persistir se repositorio disponivel
        if self._repository:
            self._persist_result(macro_result)

        logger.info(
            "Analise macro score concluida - Score: %s | Sinal: %s | "
            "Disponiveis: %d/%d | Confianca: %s",
            macro_result.score_final,
            macro_result.signal,
            macro_result.items_available,
            macro_result.total_items,
            macro_result.confidence,
        )

        return macro_result

    def get_trading_bias(self) -> str:
        """Retorna bias de trading compativel com QuantumOperatorEngine.

        Returns:
            'BULLISH', 'BEARISH' ou 'NEUTRAL'
        """
        if not self._last_result:
            return "NEUTRAL"
        return self._last_result.get_trading_bias()

    def _process_item(self, config: MacroScoreItemConfig) -> ItemScoreResult:
        """Processa um item individual do registry.

        Resolve simbolo, busca dados, e calcula score.
        """
        # Indicadores tecnicos tem pipeline diferente
        if config.scoring_type == ScoringType.TECHNICAL_INDICATOR:
            return self._process_technical_item(config)

        # Spread de curva (ex: DI curto vs DI longo)
        if config.scoring_type == ScoringType.SPREAD_CURVE:
            return self._process_spread_curve_item(config)

        # Indicadores de fluxo/microestrutura (book, tape, delta)
        if config.scoring_type == ScoringType.FLOW_INDICATOR:
            return self._process_flow_item(config)

        # Resolver simbolo
        resolved_symbol = self._resolve_symbol(config)

        # Forex fallback via API quando MT5 nao tem o par
        if resolved_symbol is None and config.category == AssetCategory.FOREX:
            return self._process_forex_via_api(config)

        if resolved_symbol is None:
            return self._unavailable_result(config, "Simbolo nao disponivel")

        # Buscar preco de abertura e preco atual
        opening_price, current_price, reason = self._get_prices(
            resolved_symbol, config
        )
        if opening_price is None or current_price is None:
            reason_text = reason or f"Dados indisponiveis para {resolved_symbol}"
            return self._unavailable_result(config, reason_text)

        # Calcular score bruto (price vs open)
        raw_score = self._calculate_price_vs_open_score(
            current_price, opening_price
        )

        # Aplicar correlacao
        final_score = self._apply_correlation(raw_score, config.correlation)

        # Calcular score ponderado
        weighted = WeightedScore(
            score=Score(final_score),
            weight=Weight(config.weight),
        )

        # Montar detalhe
        price_change = current_price - opening_price
        pct_change = (
            (price_change / opening_price * 100) if opening_price != 0 else Decimal("0")
        )
        detail = (
            f"Abertura: {opening_price} | Atual: {current_price} | "
            f"Var: {price_change:+} ({pct_change:+.2f}%) | "
            f"Correl: {config.correlation} | Score: {final_score:+d}"
        )

        return ItemScoreResult(
            item_number=config.number,
            symbol=config.symbol,
            name=config.name,
            category=config.category,
            correlation=config.correlation,
            resolved_symbol=resolved_symbol,
            opening_price=opening_price,
            current_price=current_price,
            raw_score=raw_score,
            final_score=final_score,
            weight=config.weight,
            weighted_score=weighted.contribution,
            available=True,
            detail=detail,
        )

    def _process_forex_via_api(
        self, config: MacroScoreItemConfig
    ) -> ItemScoreResult:
        """Processa item forex via AwesomeAPI quando MT5 não tem o par.

        Busca cotação XXX/USD da API e calcula score considerando
        a convenção do par (XXX_USD vs USD_XXX).
        """
        quote = self._forex_api.get_quote(config.symbol)
        if quote is None:
            return self._unavailable_result(
                config, f"Forex {config.symbol} indisponivel (MT5 e API)"
            )

        # Calcular score bruto usando o handler (respeita convenção)
        raw_score = self._forex_handler.calculate_raw_score(
            config.symbol, quote.bid, quote.opening
        )

        # Aplicar correlação
        final_score = self._apply_correlation(raw_score, config.correlation)

        weighted = WeightedScore(
            score=Score(final_score),
            weight=Weight(config.weight),
        )

        price_change = quote.bid - quote.opening
        detail = (
            f"API Forex | Abertura: {quote.opening} | Atual: {quote.bid} | "
            f"Var: {price_change:+} ({quote.pct_change:+}%) | "
            f"Correl: {config.correlation} | Score: {final_score:+d}"
        )

        return ItemScoreResult(
            item_number=config.number,
            symbol=config.symbol,
            name=config.name,
            category=config.category,
            correlation=config.correlation,
            resolved_symbol=f"API:{config.symbol}/USD",
            opening_price=quote.opening,
            current_price=quote.bid,
            raw_score=raw_score,
            final_score=final_score,
            weight=config.weight,
            weighted_score=weighted.contribution,
            available=True,
            detail=detail,
        )

    def _process_technical_item(
        self, config: MacroScoreItemConfig
    ) -> ItemScoreResult:
        """Processa um item de indicador tecnico (itens 78-85)."""
        indicator_type = (
            config.indicator_config.get("type", "unknown")
            if config.indicator_config
            else "unknown"
        )

        try:
            # Buscar candles do WIN para calculos
            candles = self._get_win_candles()
            if not candles or len(candles) < 30:
                return self._unavailable_result(
                    config, "Candles insuficientes para indicador"
                )

            # Calcular score do indicador
            raw_score = self._technical_scorer.score_indicator(
                indicator_type=indicator_type,
                candles=candles,
                config=config.indicator_config,
            )

            # Indicadores tecnicos tem correlacao DIRETA com o WIN
            # (o score ja reflete a direcao correta)
            final_score = raw_score

            weighted = WeightedScore(
                score=Score(final_score),
                weight=Weight(config.weight),
            )

            detail = f"Indicador: {indicator_type} | Score: {final_score:+d}"

            return ItemScoreResult(
                item_number=config.number,
                symbol=config.symbol,
                name=config.name,
                category=config.category,
                correlation=config.correlation,
                resolved_symbol="WIN$N",
                opening_price=None,
                current_price=None,
                raw_score=raw_score,
                final_score=final_score,
                weight=config.weight,
                weighted_score=weighted.contribution,
                available=True,
                detail=detail,
            )

        except Exception as e:
            logger.error(
                "Erro ao processar indicador tecnico %s: %s",
                config.symbol, e,
            )
            return self._unavailable_result(
                config, f"Erro no indicador: {e}"
            )

    def _process_spread_curve_item(
        self, config: MacroScoreItemConfig
    ) -> ItemScoreResult:
        """Processa item do tipo SPREAD_CURVE (ex: inclinacao curva DI).

        Compara dois vertices da curva para determinar se o spread esta
        abrindo (bearish WIN) ou fechando (bullish WIN).
        """
        ic = config.indicator_config or {}
        short_sym = ic.get("short_vertex", "DI1H")
        long_sym = ic.get("long_vertex", "DI1F29")

        try:
            # Resolver os dois vertices via FuturesContractResolver
            short_resolved = self._futures_resolver.resolve(short_sym)
            long_resolved = self._futures_resolver.resolve(long_sym)

            if not short_resolved or not long_resolved:
                return self._unavailable_result(
                    config, f"Vertices indisponiveis: {short_sym}/{long_sym}"
                )

            # Buscar precos de cada vertice
            short_open, short_current, _ = self._get_prices(short_resolved)
            long_open, long_current, _ = self._get_prices(long_resolved)

            if None in (short_open, short_current, long_open, long_current):
                return self._unavailable_result(
                    config, "Dados de vertices da curva indisponiveis"
                )

            # Spread = longo - curto (em pontos-base de taxa)
            spread_now = long_current - short_current
            spread_open = long_open - short_open

            # Variacao do spread: abertura = mais risco = bearish WIN
            spread_change = spread_now - spread_open

            # Threshold: variacao > 5bp = significativo
            threshold = Decimal("0.05")
            if spread_change > threshold:
                raw_score = -1  # Spread abrindo = bearish
            elif spread_change < -threshold:
                raw_score = 1   # Spread fechando = bullish
            else:
                raw_score = 0

            final_score = self._apply_correlation(raw_score, config.correlation)

            weighted = WeightedScore(
                score=Score(final_score),
                weight=Weight(config.weight),
            )

            detail = (
                f"Spread curva [{short_sym}/{long_sym}]: "
                f"Abertura={spread_open:.4f} | Atual={spread_now:.4f} | "
                f"Var={spread_change:+.4f} | Score={final_score:+d}"
            )

            return ItemScoreResult(
                item_number=config.number,
                symbol=config.symbol,
                name=config.name,
                category=config.category,
                correlation=config.correlation,
                resolved_symbol=f"{short_resolved}/{long_resolved}",
                opening_price=spread_open,
                current_price=spread_now,
                raw_score=raw_score,
                final_score=final_score,
                weight=config.weight,
                weighted_score=weighted.contribution,
                available=True,
                detail=detail,
            )

        except Exception as e:
            logger.error(
                "Erro ao processar spread de curva %s: %s",
                config.symbol, e,
            )
            return self._unavailable_result(
                config, f"Erro no spread: {e}"
            )

    def _process_flow_item(
        self, config: MacroScoreItemConfig
    ) -> ItemScoreResult:
        """Processa item do tipo FLOW_INDICATOR (microestrutura).

        Delega para TechnicalIndicatorScorer com candles do WIN.
        """
        indicator_type = (
            config.indicator_config.get("type", "unknown")
            if config.indicator_config
            else "unknown"
        )

        try:
            candles = self._get_win_candles()
            if not candles or len(candles) < 10:
                return self._unavailable_result(
                    config, "Candles insuficientes para indicador de fluxo"
                )

            raw_score = self._technical_scorer.score_indicator(
                indicator_type=indicator_type,
                candles=candles,
                config=config.indicator_config,
            )

            final_score = self._apply_correlation(raw_score, config.correlation)

            weighted = WeightedScore(
                score=Score(final_score),
                weight=Weight(config.weight),
            )

            detail = f"Flow: {indicator_type} | Score: {final_score:+d}"

            return ItemScoreResult(
                item_number=config.number,
                symbol=config.symbol,
                name=config.name,
                category=config.category,
                correlation=config.correlation,
                resolved_symbol="WIN$N",
                opening_price=None,
                current_price=None,
                raw_score=raw_score,
                final_score=final_score,
                weight=config.weight,
                weighted_score=weighted.contribution,
                available=True,
                detail=detail,
            )

        except Exception as e:
            logger.error(
                "Erro ao processar indicador de fluxo %s: %s",
                config.symbol, e,
            )
            return self._unavailable_result(
                config, f"Erro no fluxo: {e}"
            )

    def _resolve_symbol(self, config: MacroScoreItemConfig) -> Optional[str]:
        """Resolve o simbolo MT5 para um item."""
        try:
            # Futuros: resolver contrato vigente (inclui moedas B3)
            if config.is_futures:
                return self._futures_resolver.resolve(config.symbol)

            # Forex sem is_futures: converter codigo de moeda para par MT5
            if config.category == AssetCategory.FOREX:
                return self._forex_handler.resolve_forex_symbol(config.symbol)

            # Ativo normal: tentar obter tick mesmo se select_symbol falhar
            tick = self._mt5.get_symbol_info_tick(config.symbol)
            if tick is not None:
                return config.symbol

            # Se ainda nao houver tick, tenta habilitar e revalidar
            if self._mt5.select_symbol(config.symbol):
                tick = self._mt5.get_symbol_info_tick(config.symbol)
                if tick is not None:
                    return config.symbol


            return None

        except Exception as e:
            logger.warning(
                "Erro ao resolver simbolo %s: %s", config.symbol, e
            )
            return None

    def _get_prices(
        self,
        symbol: str,
        config: Optional[MacroScoreItemConfig] = None,
    ) -> tuple[Optional[Decimal], Optional[Decimal], Optional[str]]:
        """Obtem preco de abertura e preco atual."""
        try:
            daily = self._mt5.get_daily_candle(symbol)
            tick = self._mt5.get_symbol_info_tick(symbol)

            # Persistir candle atual (M1) para backtesting quando disponivel
            candle = self._get_current_m1_candle(symbol)
            if candle is not None:
                self._save_candle_to_db(symbol, candle)

            if tick is None:
                return None, None, "Tick indisponivel"

            now_brt = datetime.utcnow() + timedelta(hours=-3)
            tick_age = (now_brt - tick.timestamp).total_seconds()
            if tick_age > self._stale_tick_seconds:
                return None, None, f"Tick desatualizado ({int(tick_age)}s)"

            # Persistir o tick com timestamp de captura para backtesting
            self._save_tick_to_db(symbol, tick, timestamp_override=now_brt)

            if daily is None and config and config.symbol in self._live_only_symbols:
                db_symbol = config.symbol
                opening_price = self._get_open_from_db(db_symbol)
                current_price = self._get_latest_from_db(db_symbol)
                if opening_price is None:
                    opening_price = tick.last.value
                if current_price is None:
                    current_price = tick.last.value
                return opening_price, current_price, None

            if daily is None:
                opening_price = self._get_open_from_db(symbol)
                current_price = self._get_latest_from_db(symbol)
                if opening_price is None:
                    opening_price = tick.last.value
                if current_price is None:
                    current_price = tick.last.value
                return opening_price, current_price, None

            opening_price = self._get_open_from_db(symbol) or daily.open.value
            current_price = self._get_latest_from_db(symbol) or tick.last.value
            return opening_price, current_price, None

        except Exception as e:
            logger.warning(
                "Erro ao obter precos de %s: %s", symbol, e
            )
            return None, None, "Erro ao obter precos"

    def _save_tick_to_db(
        self,
        symbol: str,
        tick,
        timestamp_override: Optional[datetime] = None,
    ) -> None:
        """Persiste tick como candle M1 para uso futuro."""
        session = get_session()
        try:
            ts = timestamp_override or tick.timestamp
            exists = (
                session.query(MarketDataModel)
                .filter(MarketDataModel.symbol == symbol)
                .filter(MarketDataModel.timeframe == TimeFrame.M1.name)
                .filter(MarketDataModel.timestamp == ts)
                .first()
            )
            if exists:
                return

            last_price = tick.last.value
            spread = None
            if tick.ask and tick.bid:
                spread = tick.ask.value - tick.bid.value

            session.add(
                MarketDataModel(
                    symbol=symbol,
                    timestamp=ts,
                    timeframe=TimeFrame.M1.name,
                    open=last_price,
                    high=last_price,
                    low=last_price,
                    close=last_price,
                    volume=int(tick.volume),
                    spread=spread,
                )
            )
            session.commit()
        finally:
            session.close()

    def _save_candle_to_db(self, symbol: str, candle) -> None:
        """Persiste candle M1 para uso futuro."""
        session = get_session()
        try:
            exists = (
                session.query(MarketDataModel)
                .filter(MarketDataModel.symbol == symbol)
                .filter(MarketDataModel.timeframe == candle.timeframe.name)
                .filter(MarketDataModel.timestamp == candle.timestamp)
                .first()
            )
            if exists:
                return

            spread = None
            session.add(
                MarketDataModel(
                    symbol=symbol,
                    timestamp=candle.timestamp,
                    timeframe=candle.timeframe.name,
                    open=candle.open.value,
                    high=candle.high.value,
                    low=candle.low.value,
                    close=candle.close.value,
                    volume=int(candle.volume),
                    spread=spread,
                )
            )
            session.commit()
        finally:
            session.close()

    def _get_current_m1_candle(self, symbol: str):
        """Busca candle M1 atual para um simbolo."""
        try:
            candles = self._mt5.get_candles(
                symbol=Symbol(symbol),
                timeframe=TimeFrame.M1,
                count=1,
            )
            if not candles:
                return None
            return candles[-1]
        except Exception:
            return None

    def _get_open_from_db(self, symbol: str) -> Optional[Decimal]:
        """Retorna o primeiro preco do dia salvo no DB (M1)."""
        session = get_session()
        try:
            now = datetime.utcnow() + timedelta(hours=-3)
            row = (
                session.query(MarketDataModel)
                .filter(MarketDataModel.symbol == symbol)
                .filter(MarketDataModel.timeframe == TimeFrame.M1.name)
                .filter(MarketDataModel.timestamp >= datetime.combine(now.date(), datetime.min.time()))
                .filter(MarketDataModel.timestamp <= datetime.combine(now.date(), datetime.max.time()))
                .order_by(MarketDataModel.timestamp)
                .first()
            )
            if row:
                return Decimal(row.open)
            daily = (
                session.query(MarketDataModel)
                .filter(MarketDataModel.symbol == symbol)
                .filter(MarketDataModel.timeframe == TimeFrame.D1.name)
                .filter(MarketDataModel.timestamp >= datetime.combine(now.date(), datetime.min.time()))
                .filter(MarketDataModel.timestamp <= datetime.combine(now.date(), datetime.max.time()))
                .order_by(MarketDataModel.timestamp)
                .first()
            )
            if daily:
                return Decimal(daily.open)
            return None
        finally:
            session.close()

    def _get_latest_from_db(self, symbol: str) -> Optional[Decimal]:
        """Retorna o ultimo preco do dia salvo no DB (M1)."""
        session = get_session()
        try:
            now = datetime.utcnow() + timedelta(hours=-3)
            row = (
                session.query(MarketDataModel)
                .filter(MarketDataModel.symbol == symbol)
                .filter(MarketDataModel.timeframe == TimeFrame.M1.name)
                .filter(MarketDataModel.timestamp >= datetime.combine(now.date(), datetime.min.time()))
                .filter(MarketDataModel.timestamp <= datetime.combine(now.date(), datetime.max.time()))
                .order_by(MarketDataModel.timestamp.desc())
                .first()
            )
            if row:
                return Decimal(row.close)
            daily = (
                session.query(MarketDataModel)
                .filter(MarketDataModel.symbol == symbol)
                .filter(MarketDataModel.timeframe == TimeFrame.D1.name)
                .filter(MarketDataModel.timestamp >= datetime.combine(now.date(), datetime.min.time()))
                .filter(MarketDataModel.timestamp <= datetime.combine(now.date(), datetime.max.time()))
                .order_by(MarketDataModel.timestamp.desc())
                .first()
            )
            if daily:
                return Decimal(daily.close)
            return None
        finally:
            session.close()

    def _calculate_price_vs_open_score(
        self, current: Decimal, opening: Decimal
    ) -> int:
        """Calcula score baseado em preco atual vs abertura.

        Retorna score BRUTO (sem aplicar correlacao).
        +1 se subiu, -1 se caiu, 0 se igual.
        """
        if current > opening:
            return 1
        elif current < opening:
            return -1
        return 0

    def _apply_correlation(
        self, raw_score: int, correlation: CorrelationType
    ) -> int:
        """Aplica tipo de correlacao ao score bruto.

        - DIRETA: ativo subiu (+1) = bom para WIN (+1)
        - INVERSA: ativo subiu (+1) = ruim para WIN (-1)
        """
        if correlation == CorrelationType.INVERSA:
            return -raw_score
        return raw_score

    def _get_win_candles(self) -> list:
        """Obtem candles intraday do WIN para indicadores tecnicos."""
        try:
            from src.domain.enums.trading_enums import TimeFrame
            from src.domain.value_objects import Symbol

            symbol = Symbol("WIN$N")
            candles = self._mt5.get_candles(
                symbol=symbol,
                timeframe=TimeFrame.M5,
                count=200,
            )
            return candles
        except Exception as e:
            logger.error("Erro ao obter candles WIN: %s", e)
            return []

    def _unavailable_result(
        self, config: MacroScoreItemConfig, reason: str
    ) -> ItemScoreResult:
        """Cria resultado para item indisponivel (contribui 0)."""
        return ItemScoreResult(
            item_number=config.number,
            symbol=config.symbol,
            name=config.name,
            category=config.category,
            correlation=config.correlation,
            resolved_symbol=None,
            opening_price=None,
            current_price=None,
            raw_score=0,
            final_score=0,
            weight=config.weight,
            weighted_score=Decimal("0"),
            available=False,
            detail=reason,
        )

    def _aggregate_results(
        self,
        session_id: str,
        timestamp: datetime,
        items: list[ItemScoreResult],
    ) -> MacroScoreResult:
        """Agrega resultados individuais em score final."""
        available = [i for i in items if i.available]
        unavailable = [i for i in items if not i.available]

        # Somar scores ponderados
        score_final = sum(
            (i.weighted_score for i in items), Decimal("0")
        )

        # Contagens
        score_bullish = sum(
            (i.weighted_score for i in items if i.weighted_score > 0),
            Decimal("0"),
        )
        score_bearish = sum(
            (abs(i.weighted_score) for i in items if i.weighted_score < 0),
            Decimal("0"),
        )
        score_neutral = sum(1 for i in items if i.final_score == 0)

        # Determinar sinal
        signal = self._determine_signal(score_final)

        # Calcular confianca
        confidence = self._calculate_confidence(
            available=len(available),
            total=len(items),
            score_bullish=score_bullish,
            score_bearish=score_bearish,
            score_final=score_final,
        )

        # Obter preco atual do WIN
        win_price = self._get_win_price()

        # Gerar resumo
        summary = self._generate_summary(
            score_final=score_final,
            signal=signal,
            items_available=len(available),
            total_items=len(items),
            score_bullish=score_bullish,
            score_bearish=score_bearish,
            score_neutral=score_neutral,
        )

        return MacroScoreResult(
            session_id=session_id,
            timestamp=timestamp,
            items=items,
            total_items=len(items),
            items_available=len(available),
            items_unavailable=len(unavailable),
            score_bullish=score_bullish,
            score_bearish=score_bearish,
            score_neutral=score_neutral,
            score_final=score_final,
            signal=signal,
            confidence=confidence,
            win_price=win_price,
            summary=summary,
        )

    def _determine_signal(self, score_final: Decimal) -> MacroSignal:
        """Determina sinal com base no score final."""
        if score_final > self._neutral_threshold:
            return MacroSignal.COMPRA
        elif score_final < -self._neutral_threshold:
            return MacroSignal.VENDA
        return MacroSignal.NEUTRO

    def _calculate_confidence(
        self,
        available: int,
        total: int,
        score_bullish: Decimal,
        score_bearish: Decimal,
        score_final: Decimal = Decimal("0"),
    ) -> Decimal:
        """Calcula confianca da decisao.

        Fatores:
        - Cobertura: % de itens disponiveis (peso 0.25)
        - Unanimidade: quanto mais unilateral, mais confiante (peso 0.25)
        - Magnitude do score: quanto mais extremo, mais confiante (peso 0.50)

        FIX 12/02/2026: Adicionado score_magnitude como 3o fator.
        A formula anterior (0.4*cov + 0.6*unan) travava confianca em ~43%
        porque unanimidade nunca atinge valores altos com 104 itens diversos.
        Com magnitude, score -8 gera ~52%, score -15 gera ~65%.
        """
        if total == 0:
            return Decimal("0")

        # Cobertura (0 a 1)
        coverage = Decimal(str(available)) / Decimal(str(total))

        # Unanimidade (0 a 1)
        total_score = score_bullish + score_bearish
        if total_score == 0:
            unanimity = Decimal("0")
        else:
            unanimity = abs(score_bullish - score_bearish) / total_score

        # Magnitude do score (0 a 1): quanto mais extremo, mais confiante
        # Divisor 20 = score ponderado de ~20 representa convicção máxima
        score_magnitude = min(
            abs(score_final) / Decimal("20"),
            Decimal("1.0"),
        )

        # Confianca = media ponderada com 3 fatores
        confidence = (
            coverage * Decimal("0.25")
            + unanimity * Decimal("0.25")
            + score_magnitude * Decimal("0.50")
        )

        return min(confidence, Decimal("1.0"))

    def _get_win_price(self) -> Optional[Decimal]:
        """Obtem preco atual do WIN."""
        try:
            tick = self._mt5.get_symbol_info_tick("WIN$N")
            if tick:
                return tick.last.value
            return None
        except Exception:
            return None

    def _generate_summary(
        self,
        score_final: Decimal,
        signal: MacroSignal,
        items_available: int,
        total_items: int,
        score_bullish: Decimal,
        score_bearish: Decimal,
        score_neutral: int,
    ) -> str:
        """Gera resumo textual da analise."""
        signal_text = {
            MacroSignal.COMPRA: "COMPRA (Score Positivo)",
            MacroSignal.VENDA: "VENDA (Score Negativo)",
            MacroSignal.NEUTRO: "NEUTRO (Score Zero/Proximo)",
        }

        return (
            f"Macro Score: {score_final:+.2f} | Sinal: {signal_text[signal]} | "
            f"Itens: {items_available}/{total_items} | "
            f"Alta: +{score_bullish:.1f} | Baixa: -{score_bearish:.1f} | "
            f"Neutros: {score_neutral}"
        )

    def _persist_result(self, result: MacroScoreResult) -> None:
        """Persiste resultado no repositorio."""
        try:
            # Salvar items individuais
            items_data = [
                {
                    "timestamp": result.timestamp,
                    "item_number": item.item_number,
                    "symbol": item.symbol,
                    "resolved_symbol": item.resolved_symbol,
                    "category": str(item.category),
                    "correlation": str(item.correlation),
                    "opening_price": item.opening_price,
                    "current_price": item.current_price,
                    "score": item.final_score,
                    "weight": item.weight,
                    "weighted_score": item.weighted_score,
                    "status": "DISPONIVEL" if item.available else "INDISPONIVEL",
                    "detail": item.detail,
                }
                for item in result.items
            ]
            self._repository.save_item_scores(result.session_id, items_data)

            # Salvar decisao final
            decision_data = {
                "session_id": result.session_id,
                "timestamp": result.timestamp,
                "total_items": result.total_items,
                "items_available": result.items_available,
                "items_unavailable": result.items_unavailable,
                "score_bullish": result.score_bullish,
                "score_bearish": result.score_bearish,
                "score_neutral": result.score_neutral,
                "score_final": result.score_final,
                "signal": str(result.signal),
                "confidence": result.confidence,
                "win_price_at_decision": result.win_price,
                "summary": result.summary,
            }
            self._repository.save_decision(decision_data)

            # Criar registros de feedback pendentes (30min, 1h, 2h)
            for minutes in [30, 60, 120]:
                feedback_data = {
                    "session_id": result.session_id,
                    "timestamp_decision": result.timestamp,
                    "signal_at_decision": str(result.signal),
                    "score_at_decision": result.score_final,
                    "win_price_at_decision": result.win_price or Decimal("0"),
                    "evaluation_minutes": minutes,
                }
                self._repository.save_feedback(feedback_data)

            logger.info(
                "Resultado macro score persistido - sessao %s",
                result.session_id[:8],
            )

        except Exception as e:
            logger.error("Erro ao persistir macro score: %s", e)
