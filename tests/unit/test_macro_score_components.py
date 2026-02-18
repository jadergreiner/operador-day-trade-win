"""Testes unitarios dos componentes do macro score."""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from src.application.services.macro_score.forex_handler import (
    ForexScoreHandler,
    FOREX_PAIR_MAP,
)
from src.application.services.macro_score.technical_scorer import (
    TechnicalIndicatorScorer,
)
from src.infrastructure.adapters.mt5_adapter import Candle
from src.domain.enums.macro_score_enums import ForexConvention
from src.domain.enums.trading_enums import TimeFrame
from src.domain.value_objects import Price, Symbol


def _make_candle(
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: int = 1000,
) -> Candle:
    """Helper para criar candle de teste."""
    from datetime import datetime
    return Candle(
        symbol=Symbol("TEST"),
        timeframe=TimeFrame.M5,
        open=Price(Decimal(str(open_price))),
        high=Price(Decimal(str(high_price))),
        low=Price(Decimal(str(low_price))),
        close=Price(Decimal(str(close_price))),
        volume=volume,
        timestamp=datetime.now(),
    )


def _make_candles_trending_up(count: int = 50) -> list[Candle]:
    """Cria serie de candles em tendencia de alta."""
    candles = []
    base = 100.0
    for i in range(count):
        o = base + i * 0.5
        c = o + 0.3
        h = c + 0.1
        l = o - 0.1
        candles.append(_make_candle(o, h, l, c, volume=1000 + i * 10))
    return candles


def _make_candles_trending_down(count: int = 50) -> list[Candle]:
    """Cria serie de candles em tendencia de baixa."""
    candles = []
    base = 150.0
    for i in range(count):
        o = base - i * 0.5
        c = o - 0.3
        h = o + 0.1
        l = c - 0.1
        candles.append(_make_candle(o, h, l, c, volume=1000 + i * 10))
    return candles


def _make_candles_sideways(count: int = 50) -> list[Candle]:
    """Cria serie de candles lateral."""
    candles = []
    base = 100.0
    for i in range(count):
        offset = 0.2 if i % 2 == 0 else -0.2
        o = base + offset
        c = base - offset
        h = max(o, c) + 0.1
        l = min(o, c) - 0.1
        candles.append(_make_candle(o, h, l, c, volume=1000))
    return candles


class TestForexScoreHandler:
    """Testes do ForexScoreHandler."""

    def setup_method(self):
        self.mt5_mock = MagicMock()
        self.handler = ForexScoreHandler(self.mt5_mock)

    def test_mapeamento_12_moedas(self):
        """Deve ter 12 moedas mapeadas."""
        assert len(FOREX_PAIR_MAP) == 12

    def test_eur_xxx_usd(self):
        """EUR deve usar convencao XXX_USD (EURUSD)."""
        symbol = self.handler.get_mt5_symbol("EUR")
        convention = self.handler.get_convention("EUR")
        assert symbol == "EURUSD"
        assert convention == ForexConvention.XXX_USD

    def test_jpy_usd_xxx(self):
        """JPY deve usar convencao USD_XXX (USDJPY)."""
        symbol = self.handler.get_mt5_symbol("JPY")
        convention = self.handler.get_convention("JPY")
        assert symbol == "USDJPY"
        assert convention == ForexConvention.USD_XXX

    def test_moeda_desconhecida(self):
        """Moeda nao mapeada retorna None."""
        assert self.handler.get_mt5_symbol("XYZ") is None
        assert self.handler.get_convention("XYZ") is None

    # --- Testes de score XXX_USD ---

    def test_eurusd_subiu_moeda_forte(self):
        """EURUSD subiu = EUR forte = score +1."""
        score = self.handler.calculate_raw_score(
            "EUR", Decimal("1.1000"), Decimal("1.0900")
        )
        assert score == 1

    def test_eurusd_caiu_moeda_fraca(self):
        """EURUSD caiu = EUR fraco = score -1."""
        score = self.handler.calculate_raw_score(
            "EUR", Decimal("1.0800"), Decimal("1.0900")
        )
        assert score == -1

    def test_eurusd_igual_neutro(self):
        """EURUSD igual = neutro = score 0."""
        score = self.handler.calculate_raw_score(
            "EUR", Decimal("1.0900"), Decimal("1.0900")
        )
        assert score == 0

    # --- Testes de score USD_XXX (inversao) ---

    def test_usdjpy_subiu_moeda_fraca(self):
        """USDJPY subiu = USD forte = JPY FRACO = score -1."""
        score = self.handler.calculate_raw_score(
            "JPY", Decimal("155.00"), Decimal("154.00")
        )
        assert score == -1

    def test_usdjpy_caiu_moeda_forte(self):
        """USDJPY caiu = USD fraco = JPY FORTE = score +1."""
        score = self.handler.calculate_raw_score(
            "JPY", Decimal("153.00"), Decimal("154.00")
        )
        assert score == 1

    def test_usdcad_subiu_moeda_fraca(self):
        """USDCAD subiu = USD forte = CAD FRACO = score -1."""
        score = self.handler.calculate_raw_score(
            "CAD", Decimal("1.3600"), Decimal("1.3500")
        )
        assert score == -1

    def test_usdcad_caiu_moeda_forte(self):
        """USDCAD caiu = USD fraco = CAD FORTE = score +1."""
        score = self.handler.calculate_raw_score(
            "CAD", Decimal("1.3400"), Decimal("1.3500")
        )
        assert score == 1

    # --- Todas as moedas ---

    def test_gbp_xxx_usd(self):
        assert self.handler.get_convention("GBP") == ForexConvention.XXX_USD

    def test_aud_xxx_usd(self):
        assert self.handler.get_convention("AUD") == ForexConvention.XXX_USD

    def test_nzd_xxx_usd(self):
        assert self.handler.get_convention("NZD") == ForexConvention.XXX_USD

    def test_chf_usd_xxx(self):
        assert self.handler.get_convention("CHF") == ForexConvention.USD_XXX

    def test_mxn_usd_xxx(self):
        assert self.handler.get_convention("MXN") == ForexConvention.USD_XXX

    def test_zar_usd_xxx(self):
        assert self.handler.get_convention("ZAR") == ForexConvention.USD_XXX

    def test_try_usd_xxx(self):
        assert self.handler.get_convention("TRY") == ForexConvention.USD_XXX

    def test_cny_usd_xxx(self):
        assert self.handler.get_convention("CNY") == ForexConvention.USD_XXX

    def test_clp_usd_xxx(self):
        assert self.handler.get_convention("CLP") == ForexConvention.USD_XXX


class TestTechnicalIndicatorScorer:
    """Testes do TechnicalIndicatorScorer."""

    def setup_method(self):
        self.mt5_mock = MagicMock()
        self.scorer = TechnicalIndicatorScorer(self.mt5_mock)

    # --- Volume ---

    def test_volume_acima_media_preco_subindo(self):
        """Volume alto + preco subindo = +1."""
        candles = _make_candles_trending_up(30)
        # Aumentar volume do ultimo candle
        last = candles[-1]
        candles[-1] = _make_candle(
            float(last.open.value),
            float(last.high.value),
            float(last.low.value),
            float(last.close.value),
            volume=50000,
        )
        score = self.scorer.score_volume(candles)
        assert score == 1

    def test_volume_acima_media_preco_caindo(self):
        """Volume alto + preco caindo = -1."""
        candles = _make_candles_trending_down(30)
        last = candles[-1]
        candles[-1] = _make_candle(
            float(last.open.value),
            float(last.high.value),
            float(last.low.value),
            float(last.close.value),
            volume=50000,
        )
        score = self.scorer.score_volume(candles)
        assert score == -1

    def test_volume_dados_insuficientes(self):
        """Dados insuficientes retorna 0."""
        candles = _make_candles_sideways(5)
        score = self.scorer.score_volume(candles)
        assert score == 0

    # --- RSI ---

    def test_rsi_sobrevendido(self):
        """RSI < 30 (sobrevendido) = +1."""
        # Criar candles com queda forte para RSI baixo
        candles = _make_candles_trending_down(50)
        score = self.scorer.score_rsi(candles)
        assert score == 1

    def test_rsi_sobrecomprado(self):
        """RSI > 70 (sobrecomprado) = -1."""
        # Criar candles com alta forte para RSI alto
        candles = _make_candles_trending_up(50)
        score = self.scorer.score_rsi(candles)
        assert score == -1

    # --- Estocastico ---

    def test_stochastic_sobrevendido(self):
        """Estocastico < 20 = +1."""
        candles = _make_candles_trending_down(30)
        score = self.scorer.score_stochastic(candles)
        assert score == 1

    def test_stochastic_sobrecomprado(self):
        """Estocastico > 80 = -1."""
        candles = _make_candles_trending_up(30)
        score = self.scorer.score_stochastic(candles)
        assert score == -1

    # --- VWAP ---

    def test_vwap_preco_acima(self):
        """Preco acima do VWAP = +1."""
        candles = _make_candles_trending_up(30)
        score = self.scorer.score_vwap(candles)
        assert score == 1

    def test_vwap_preco_abaixo(self):
        """Preco abaixo do VWAP = -1."""
        candles = _make_candles_trending_down(30)
        score = self.scorer.score_vwap(candles)
        assert score == -1

    # --- score_indicator dispatch ---

    def test_score_indicator_dispatch_rsi(self):
        """score_indicator deve despachar corretamente para RSI."""
        candles = _make_candles_trending_up(50)
        score = self.scorer.score_indicator("rsi", candles, {"period": 14})
        assert score in (-1, 0, 1)

    def test_score_indicator_tipo_desconhecido(self):
        """Tipo desconhecido retorna 0."""
        candles = _make_candles_sideways(30)
        score = self.scorer.score_indicator("inexistente", candles)
        assert score == 0

    def test_score_indicator_candles_vazios(self):
        """Candles insuficientes retorna 0."""
        score = self.scorer.score_indicator("rsi", [])
        assert score == 0

    # --- OBV ---

    def test_obv_acumulacao(self):
        """OBV subindo (acumulacao) em tendencia de alta = +1."""
        candles = _make_candles_trending_up(50)
        score = self.scorer.score_obv(candles)
        assert score == 1

    def test_obv_distribuicao(self):
        """OBV caindo (distribuicao) em tendencia de baixa = -1."""
        candles = _make_candles_trending_down(50)
        score = self.scorer.score_obv(candles)
        assert score == -1

    # --- Agressao ---

    def test_agressao_compradora(self):
        """Predominancia compradora = +1."""
        candles = _make_candles_trending_up(20)
        score = self.scorer.score_aggression(candles)
        assert score == 1

    def test_agressao_vendedora(self):
        """Predominancia vendedora = -1."""
        candles = _make_candles_trending_down(20)
        score = self.scorer.score_aggression(candles)
        assert score == -1

    # --- MACD ---

    def test_macd_dados_insuficientes(self):
        """MACD sem dados suficientes = 0."""
        candles = _make_candles_sideways(10)
        score = self.scorer.score_macd(candles)
        assert score == 0
