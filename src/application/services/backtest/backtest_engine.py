"""Engine de backtest que replica o MacroScoreEngine com dados historicos."""

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.application.services.backtest.historical_data_provider import (
    HistoricalDataProvider,
)
from src.application.services.macro_score.engine import (
    ItemScoreResult,
    MacroScoreResult,
)
from src.application.services.macro_score.forex_handler import ForexScoreHandler
from src.application.services.macro_score.item_registry import MacroScoreItemConfig
from src.application.services.macro_score.technical_scorer import (
    TechnicalIndicatorScorer,
)
from src.domain.enums.macro_score_enums import (
    AssetCategory,
    CorrelationType,
    MacroSignal,
    ScoringType,
)
from src.domain.value_objects.macro_score import Score, Weight, WeightedScore

logger = logging.getLogger(__name__)


class BacktestMacroScoreEngine:
    """Engine de backtest que replica o calculo do MacroScoreEngine.

    Usa dados pre-carregados do HistoricalDataProvider em vez de
    buscar dados ao vivo do MT5.

    Para cada barra M15, calcula:
    1. Score de cada item (price vs open D1, com dados historicos)
    2. Score de indicadores tecnicos (com candles M5 ate aquele momento)
    3. Agregacao e sinal final
    """

    def __init__(
        self,
        data_provider: HistoricalDataProvider,
        registry: list[MacroScoreItemConfig],
        technical_scorer: TechnicalIndicatorScorer,
        forex_handler: ForexScoreHandler,
        neutral_threshold: Decimal = Decimal("0"),
    ) -> None:
        self._data = data_provider
        self._registry = registry
        self._technical_scorer = technical_scorer
        self._forex_handler = forex_handler
        self._neutral_threshold = neutral_threshold

    def score_at_bar(self, bar_index: int) -> MacroScoreResult:
        """Calcula MacroScore completo para uma barra M15 especifica.

        Args:
            bar_index: Indice da barra M15 (0-based)

        Returns:
            MacroScoreResult com score final e detalhamento por item.
        """
        session_id = str(uuid.uuid4())
        win_bars = self._data.get_win_bars()
        timestamp = (
            win_bars[bar_index].timestamp
            if bar_index < len(win_bars)
            else datetime.now()
        )

        item_results: list[ItemScoreResult] = []

        for config in self._registry:
            if config.scoring_type == ScoringType.TECHNICAL_INDICATOR:
                result = self._process_technical_item(config, timestamp)
            else:
                result = self._process_price_item(config, bar_index)
            item_results.append(result)

        return self._aggregate_results(
            session_id=session_id,
            timestamp=timestamp,
            items=item_results,
            bar_index=bar_index,
        )

    def _process_price_item(
        self, config: MacroScoreItemConfig, bar_index: int
    ) -> ItemScoreResult:
        """Processa um item de preco vs abertura com dados historicos."""
        resolved = self._data.get_resolved_symbol(config.symbol)
        if resolved is None:
            return self._unavailable_result(config, "Simbolo nao resolvido")

        opening_price = self._data.get_daily_open(resolved)
        current_price = self._data.get_price_at_bar(resolved, bar_index)

        if opening_price is None or current_price is None:
            return self._unavailable_result(
                config, f"Dados indisponiveis para {resolved}"
            )

        # Score bruto: preco atual vs abertura
        if config.category == AssetCategory.FOREX:
            # Quando o simbolo resolvido e o proprio codigo (DB local, ex: CNY/BRL),
            # nao aplica convencao USD/XXX para evitar inverter o sinal.
            if resolved == config.symbol:
                raw_score = self._calculate_price_vs_open_score(
                    current_price, opening_price
                )
            else:
                raw_score = self._forex_handler.calculate_raw_score(
                    config.symbol, current_price, opening_price
                )
        else:
            raw_score = self._calculate_price_vs_open_score(
                current_price, opening_price
            )

        # Aplicar correlacao
        final_score = self._apply_correlation(raw_score, config.correlation)

        # Score ponderado
        weighted = WeightedScore(
            score=Score(final_score),
            weight=Weight(config.weight),
        )

        # Detalhe
        price_change = current_price - opening_price
        pct_change = (
            (price_change / opening_price * 100)
            if opening_price != 0
            else Decimal("0")
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
            resolved_symbol=resolved,
            opening_price=opening_price,
            current_price=current_price,
            raw_score=raw_score,
            final_score=final_score,
            weight=config.weight,
            weighted_score=weighted.contribution,
            available=True,
            detail=detail,
        )

    def _process_technical_item(
        self, config: MacroScoreItemConfig, bar_timestamp: datetime
    ) -> ItemScoreResult:
        """Processa um item de indicador tecnico com candles historicos."""
        indicator_type = (
            config.indicator_config.get("type", "unknown")
            if config.indicator_config
            else "unknown"
        )

        try:
            # Obter candles M5 do WIN ate o momento da barra
            candles = self._data.get_win_m5_candles_up_to(bar_timestamp)
            if not candles or len(candles) < 30:
                return self._unavailable_result(
                    config, "Candles insuficientes para indicador"
                )

            raw_score = self._technical_scorer.score_indicator(
                indicator_type=indicator_type,
                candles=candles,
                config=config.indicator_config,
            )

            # Indicadores tecnicos tem correlacao DIRETA com o WIN
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

    def _calculate_price_vs_open_score(
        self, current: Decimal, opening: Decimal
    ) -> int:
        """Calcula score baseado em preco atual vs abertura."""
        if current > opening:
            return 1
        elif current < opening:
            return -1
        return 0

    def _apply_correlation(
        self, raw_score: int, correlation: CorrelationType
    ) -> int:
        """Aplica tipo de correlacao ao score bruto."""
        if correlation == CorrelationType.INVERSA:
            return -raw_score
        return raw_score

    def _unavailable_result(
        self, config: MacroScoreItemConfig, reason: str
    ) -> ItemScoreResult:
        """Cria resultado para item indisponivel."""
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
        bar_index: int,
    ) -> MacroScoreResult:
        """Agrega resultados individuais em score final."""
        available = [i for i in items if i.available]
        unavailable = [i for i in items if not i.available]

        score_final = sum(
            (i.weighted_score for i in items), Decimal("0")
        )

        score_bullish = sum(
            (i.weighted_score for i in items if i.weighted_score > 0),
            Decimal("0"),
        )
        score_bearish = sum(
            (abs(i.weighted_score) for i in items if i.weighted_score < 0),
            Decimal("0"),
        )
        score_neutral = sum(1 for i in items if i.final_score == 0)

        # Sinal
        if score_final > self._neutral_threshold:
            signal = MacroSignal.COMPRA
        elif score_final < -self._neutral_threshold:
            signal = MacroSignal.VENDA
        else:
            signal = MacroSignal.NEUTRO

        # Confianca
        confidence = self._calculate_confidence(
            available=len(available),
            total=len(items),
            score_bullish=score_bullish,
            score_bearish=score_bearish,
        )

        # Preco WIN na barra
        win_bars = self._data.get_win_bars()
        win_price = (
            win_bars[bar_index].close.value
            if bar_index < len(win_bars)
            else None
        )

        # Resumo
        signal_text = {
            MacroSignal.COMPRA: "COMPRA (Score Positivo)",
            MacroSignal.VENDA: "VENDA (Score Negativo)",
            MacroSignal.NEUTRO: "NEUTRO (Score Zero/Proximo)",
        }
        summary = (
            f"Macro Score: {score_final:+.2f} | Sinal: {signal_text[signal]} | "
            f"Itens: {len(available)}/{len(items)} | "
            f"Alta: +{score_bullish:.1f} | Baixa: -{score_bearish:.1f} | "
            f"Neutros: {score_neutral}"
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

    def _calculate_confidence(
        self,
        available: int,
        total: int,
        score_bullish: Decimal,
        score_bearish: Decimal,
    ) -> Decimal:
        """Calcula confianca da decisao (replica logica da engine principal)."""
        if total == 0:
            return Decimal("0")

        coverage = Decimal(str(available)) / Decimal(str(total))

        total_score = score_bullish + score_bearish
        if total_score == 0:
            unanimity = Decimal("0")
        else:
            unanimity = abs(score_bullish - score_bearish) / total_score

        confidence = coverage * Decimal("0.4") + unanimity * Decimal("0.6")
        return min(confidence, Decimal("1.0"))
