"""Testes unitarios do MacroScoreEngine."""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from src.domain.enums.macro_score_enums import (
    AssetCategory,
    CorrelationType,
    MacroSignal,
    ScoringType,
)
from src.domain.value_objects.macro_score import Score, Weight, WeightedScore
from src.application.services.macro_score.engine import (
    MacroScoreEngine,
    ItemScoreResult,
    MacroScoreResult,
)
from src.application.services.macro_score.item_registry import (
    MacroScoreItemConfig,
    get_item_registry,
)


class TestScore:
    """Testes do Value Object Score."""

    def test_score_positivo(self):
        s = Score(1)
        assert s.value == 1
        assert str(s) == "+1"

    def test_score_negativo(self):
        s = Score(-1)
        assert s.value == -1
        assert str(s) == "-1"

    def test_score_neutro(self):
        s = Score(0)
        assert s.value == 0
        assert str(s) == "0"

    def test_score_invalido(self):
        with pytest.raises(ValueError):
            Score(2)

    def test_score_invalido_negativo(self):
        with pytest.raises(ValueError):
            Score(-2)

    def test_score_frozen(self):
        s = Score(1)
        with pytest.raises(AttributeError):
            s.value = 0


class TestWeight:
    """Testes do Value Object Weight."""

    def test_weight_padrao(self):
        w = Weight(Decimal("1.0"))
        assert w.value == Decimal("1.0")

    def test_weight_zero(self):
        w = Weight(Decimal("0"))
        assert w.value == Decimal("0")

    def test_weight_negativo_invalido(self):
        with pytest.raises(ValueError):
            Weight(Decimal("-1"))

    def test_weight_converte_float(self):
        w = Weight(1.5)
        assert isinstance(w.value, Decimal)


class TestWeightedScore:
    """Testes do Value Object WeightedScore."""

    def test_contribuicao_positiva(self):
        ws = WeightedScore(Score(1), Weight(Decimal("1.0")))
        assert ws.contribution == Decimal("1.0")

    def test_contribuicao_negativa(self):
        ws = WeightedScore(Score(-1), Weight(Decimal("1.0")))
        assert ws.contribution == Decimal("-1.0")

    def test_contribuicao_neutra(self):
        ws = WeightedScore(Score(0), Weight(Decimal("1.0")))
        assert ws.contribution == Decimal("0")

    def test_contribuicao_com_peso(self):
        ws = WeightedScore(Score(1), Weight(Decimal("2.5")))
        assert ws.contribution == Decimal("2.5")

    def test_contribuicao_peso_zero(self):
        ws = WeightedScore(Score(1), Weight(Decimal("0")))
        assert ws.contribution == Decimal("0")


class TestItemRegistry:
    """Testes do registro de itens."""

    def test_total_85_itens(self):
        items = get_item_registry()
        assert len(items) == 85

    def test_numeracao_sequencial(self):
        items = get_item_registry()
        numbers = [i.number for i in items]
        assert numbers == list(range(1, 86))

    def test_simbolos_unicos(self):
        items = get_item_registry()
        symbols = [i.symbol for i in items]
        assert len(symbols) == len(set(symbols))

    def test_peso_inicial_1(self):
        items = get_item_registry()
        for item in items:
            assert item.weight == Decimal("1.0")

    def test_categorias_corretas(self):
        items = get_item_registry()
        categories = set(i.category for i in items)
        assert AssetCategory.INDICES_BRASIL in categories
        assert AssetCategory.ACOES_BRASIL in categories
        assert AssetCategory.FOREX in categories
        assert AssetCategory.COMMODITIES in categories
        assert AssetCategory.INDICADORES_TECNICOS in categories

    def test_bova11_correlacao_direta(self):
        items = get_item_registry()
        bova11 = next(i for i in items if i.symbol == "BOVA11")
        assert bova11.correlation == CorrelationType.DIRETA

    def test_wdo_correlacao_inversa(self):
        items = get_item_registry()
        wdo = next(i for i in items if i.symbol == "WDO")
        assert wdo.correlation == CorrelationType.INVERSA
        assert wdo.is_futures is True

    def test_gldg_ouro_inversa_futuro(self):
        items = get_item_registry()
        gldg = next(i for i in items if i.symbol == "GLDG")
        assert gldg.correlation == CorrelationType.INVERSA
        assert gldg.is_futures is True

    def test_indicadores_tecnicos_config(self):
        items = get_item_registry()
        tech_items = [
            i for i in items
            if i.scoring_type == ScoringType.TECHNICAL_INDICATOR
        ]
        assert len(tech_items) == 8
        for item in tech_items:
            assert item.indicator_config is not None
            assert "type" in item.indicator_config

    def test_forex_is_futures(self):
        """Moedas forex devem ser resolvidas como futuros B3."""
        items = get_item_registry()
        eur = next(i for i in items if i.symbol == "EUR")
        jpy = next(i for i in items if i.symbol == "JPY")
        assert eur.is_futures is True
        assert jpy.is_futures is True
        assert eur.category == AssetCategory.FOREX
        assert jpy.category == AssetCategory.FOREX


class TestMacroScoreEngineCorrelation:
    """Testes de correlacao direta e inversa."""

    def setup_method(self):
        """Setup com MT5 mockado."""
        self.mt5_mock = MagicMock()
        self.engine = MacroScoreEngine(
            mt5_adapter=self.mt5_mock,
            repository=None,
        )

    def test_price_vs_open_subiu(self):
        score = self.engine._calculate_price_vs_open_score(
            Decimal("130000"), Decimal("129000")
        )
        assert score == 1

    def test_price_vs_open_caiu(self):
        score = self.engine._calculate_price_vs_open_score(
            Decimal("128000"), Decimal("129000")
        )
        assert score == -1

    def test_price_vs_open_igual(self):
        score = self.engine._calculate_price_vs_open_score(
            Decimal("129000"), Decimal("129000")
        )
        assert score == 0

    def test_correlacao_direta_subiu(self):
        """Ativo subiu + correlacao direta = +1 para WIN."""
        result = self.engine._apply_correlation(1, CorrelationType.DIRETA)
        assert result == 1

    def test_correlacao_direta_caiu(self):
        """Ativo caiu + correlacao direta = -1 para WIN."""
        result = self.engine._apply_correlation(-1, CorrelationType.DIRETA)
        assert result == -1

    def test_correlacao_inversa_subiu(self):
        """Ativo subiu + correlacao inversa = -1 para WIN."""
        result = self.engine._apply_correlation(1, CorrelationType.INVERSA)
        assert result == -1

    def test_correlacao_inversa_caiu(self):
        """Ativo caiu + correlacao inversa = +1 para WIN."""
        result = self.engine._apply_correlation(-1, CorrelationType.INVERSA)
        assert result == 1

    def test_correlacao_neutro(self):
        """Score 0 permanece 0 independente da correlacao."""
        assert self.engine._apply_correlation(0, CorrelationType.DIRETA) == 0
        assert self.engine._apply_correlation(0, CorrelationType.INVERSA) == 0


class TestMacroScoreEngineSignal:
    """Testes de determinacao de sinal."""

    def setup_method(self):
        self.mt5_mock = MagicMock()
        self.engine = MacroScoreEngine(
            mt5_adapter=self.mt5_mock,
            repository=None,
        )

    def test_signal_compra(self):
        """Score positivo = COMPRA."""
        signal = self.engine._determine_signal(Decimal("5"))
        assert signal == MacroSignal.COMPRA

    def test_signal_venda(self):
        """Score negativo = VENDA."""
        signal = self.engine._determine_signal(Decimal("-3"))
        assert signal == MacroSignal.VENDA

    def test_signal_neutro(self):
        """Score zero = NEUTRO."""
        signal = self.engine._determine_signal(Decimal("0"))
        assert signal == MacroSignal.NEUTRO

    def test_signal_neutro_com_threshold(self):
        """Score dentro do threshold = NEUTRO."""
        engine = MacroScoreEngine(
            mt5_adapter=self.mt5_mock,
            repository=None,
            neutral_threshold=Decimal("3"),
        )
        assert engine._determine_signal(Decimal("2")) == MacroSignal.NEUTRO
        assert engine._determine_signal(Decimal("-2")) == MacroSignal.NEUTRO
        assert engine._determine_signal(Decimal("4")) == MacroSignal.COMPRA
        assert engine._determine_signal(Decimal("-4")) == MacroSignal.VENDA

    def test_trading_bias_bullish(self):
        """get_trading_bias retorna BULLISH para COMPRA."""
        result = MagicMock(spec=MacroScoreResult)
        result.get_trading_bias.return_value = "BULLISH"
        self.engine._last_result = result
        assert self.engine.get_trading_bias() == "BULLISH"

    def test_trading_bias_sem_resultado(self):
        """get_trading_bias retorna NEUTRAL sem analise."""
        assert self.engine.get_trading_bias() == "NEUTRAL"


class TestMacroScoreEngineResilience:
    """Testes de resiliencia - itens indisponiveis."""

    def setup_method(self):
        self.mt5_mock = MagicMock()
        self.engine = MacroScoreEngine(
            mt5_adapter=self.mt5_mock,
            repository=None,
        )

    def test_item_indisponivel_contribui_zero(self):
        """Item indisponivel deve contribuir 0 ao score final."""
        config = MacroScoreItemConfig(
            number=99,
            symbol="TESTE",
            name="Teste",
            category=AssetCategory.INDICES_BRASIL,
            correlation=CorrelationType.DIRETA,
            weight=Decimal("1.0"),
            is_futures=False,
            forex_convention=None,
            scoring_type=ScoringType.PRICE_VS_OPEN,
            indicator_config=None,
        )
        result = self.engine._unavailable_result(config, "Nao disponivel")
        assert result.final_score == 0
        assert result.weighted_score == Decimal("0")
        assert result.available is False

    def test_confianca_zero_sem_itens(self):
        """Confianca deve ser 0 sem itens."""
        confidence = self.engine._calculate_confidence(
            available=0, total=0,
            score_bullish=Decimal("0"),
            score_bearish=Decimal("0"),
        )
        assert confidence == Decimal("0")

    def test_confianca_alta_cobertura_total(self):
        """Cobertura total com unanimidade maxima = alta confianca."""
        confidence = self.engine._calculate_confidence(
            available=85, total=85,
            score_bullish=Decimal("50"),
            score_bearish=Decimal("0"),
        )
        assert confidence == Decimal("1.0")

    def test_confianca_media_cobertura_parcial(self):
        """Cobertura parcial reduz confianca."""
        confidence = self.engine._calculate_confidence(
            available=40, total=85,
            score_bullish=Decimal("30"),
            score_bearish=Decimal("10"),
        )
        assert Decimal("0") < confidence < Decimal("1")
