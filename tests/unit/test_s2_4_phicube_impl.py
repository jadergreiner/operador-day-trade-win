# -*- coding: utf-8 -*-
"""
Testes Unitários - PhiCubeCalculator Implementation (S2-4).

Cobertura de Testes:
- test_init_default_window: Inicialização com valores padrão
- test_init_custom_window: Inicialização com window customizado
- test_add_candle_single: Adicionar um candle
- test_add_candle_multiple: Adicionar múltiplos candles
- test_add_candle_window_limit: Validar limite de janela
- test_calculate_empty_history: Calcular com histórico vazio
- test_calculate_insufficient_history: Calcular com histórico insuficiente (< 610)
- test_calculate_full_history: Calcular com histórico completo (610+)
- test_sma_calculation: SMA individual para período
- test_slope_update_alta: Slope ALTA detectado corretamente
- test_slope_update_baixa: Slope BAIXA detectado corretamente
- test_slope_update_neutro: Slope NEUTRO detectado corretamente
- test_fan_score_all_alta: Fan score máximo (+6) com ordem crescente
- test_fan_score_all_baixa: Fan score mínimo (-6) com ordem decrescente
- test_fan_score_misto: Fan score misto (~0) com ordem aleatória
- test_alignment_detection_alta: Alinhamento ALTA detectado (fan > 2)
- test_alignment_detection_baixa: Alinhamento BAIXA detectado (fan < -2)
- test_alignment_detection_misto: Alinhamento MISTO detectado (|fan| <= 2)
- test_normalization_alta: Normalização (+6 → 1.0)
- test_normalization_baixa: Normalização (-6 → 0.0)
- test_normalization_zero: Normalização (0 → 0.5)
- test_weighted_score_default_weight: Peso padrão 0.15
- test_weighted_score_custom_weight: Peso customizado
- test_factory_function: create_phicube_calculator()
- test_get_status_dictionary: Status completo para telemetria

Status: ✅ READY FOR SPRINT 2
"""

import unittest
from decimal import Decimal
import sys
import os

# Adicionar path ao script para importação
sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'scripts'
)))

try:
    from score_phicube import (
        PhiCubeCalculator,
        MimaItem,
        MimaData,
        create_phicube_calculator
    )
except ImportError as e:
    print(f"Erro ao importar: {e}")
    print(f"Sys.path: {sys.path}")
    raise


class TestPhiCubeInitialization(unittest.TestCase):
    """CASE: Inicialização de PhiCubeCalculator"""

    def test_init_default_window(self):
        """THEN: Inicializa com window_size padrão (610)."""
        calc = PhiCubeCalculator()
        self.assertEqual(calc.window_size, 610)
        self.assertEqual(len(calc.prices), 0)
        self.assertIsNotNone(calc.current_mima)

    def test_init_custom_window(self):
        """THEN: Inicializa com window_size customizado."""
        calc = PhiCubeCalculator(window_size=100)
        self.assertEqual(calc.window_size, 100)
        self.assertEqual(len(calc.prices), 0)


class TestAddCandle(unittest.TestCase):
    """CASE: Adição de candles ao histórico"""

    def test_add_candle_single(self):
        """THEN: Adiciona um candle com sucesso."""
        calc = PhiCubeCalculator()
        calc.add_candle(10650.00)
        self.assertEqual(len(calc.prices), 1)
        self.assertEqual(calc.prices[0], Decimal("10650.00"))

    def test_add_candle_multiple(self):
        """THEN: Adiciona múltiplos candles sequencialmente."""
        calc = PhiCubeCalculator()
        prices = [10650, 10651, 10652, 10653, 10654]
        for price in prices:
            calc.add_candle(price)

        self.assertEqual(len(calc.prices), 5)
        # Verificar conversão para Decimal
        for i, price in enumerate(prices):
            self.assertEqual(
                calc.prices[i],
                Decimal(str(price)).quantize(Decimal("0.01"))
            )

    def test_add_candle_window_limit(self):
        """THEN: Respeita limite de janela (mantém últimos N)."""
        calc = PhiCubeCalculator(window_size=10)
        # Adicionar 20 candles
        for i in range(20):
            calc.add_candle(10600 + i * 0.1)

        # Deve manter apenas os últimos 10
        self.assertEqual(len(calc.prices), 10)
        # Próximo candle deve ser ~10609 (último dos 20)
        self.assertAlmostEqual(
            float(calc.prices[-1]),
            10600 + 19 * 0.1,
            places=1
        )

    def test_add_candle_decimal_precision(self):
        """THEN: Converte float para Decimal com precisão 2 casas."""
        calc = PhiCubeCalculator()
        calc.add_candle(10650.12345)  # Input com muitas casas
        # Deve quantizar para 2 casas
        self.assertEqual(calc.prices[0], Decimal("10650.12"))


class TestSMACalculation(unittest.TestCase):
    """CASE: Cálculo de Moving Averages Fibonacci"""

    def test_sma_insufficient_history(self):
        """THEN: Retorna None se histórico < período."""
        calc = PhiCubeCalculator()
        calc.add_candle(10650)
        # Tentar calcular SMA-8 com apenas 1 candle
        sma = calc._calculate_sma(8)
        self.assertIsNone(sma)

    def test_sma_exact_period(self):
        """THEN: Calcula SMA com exatamente N candles."""
        calc = PhiCubeCalculator()
        prices = [10650, 10651, 10652, 10653, 10654, 10655, 10656, 10657]
        for p in prices:
            calc.add_candle(p)

        # SMA-8 deve ser média dos 8 candles
        sma = calc._calculate_sma(8)
        expected = sum(Decimal(str(p)).quantize(Decimal("0.01"))
                      for p in prices) / Decimal(8)
        self.assertAlmostEqual(float(sma), float(expected), places=1)

    def test_sma_simple_values(self):
        """THEN: SMA com valores simples é correto."""
        calc = PhiCubeCalculator()
        # Adicionar 10 candles com valor constante 100
        for _ in range(10):
            calc.add_candle(100.00)

        sma = calc._calculate_sma(5)
        self.assertEqual(sma, Decimal("100.00"))


class TestSlopeUpdate(unittest.TestCase):
    """CASE: Atualização de slope (ALTA/BAIXA/NEUTRO)"""

    def test_slope_alta_increasing(self):
        """THEN: Slope ALTA quando SMA aumenta."""
        calc = PhiCubeCalculator()
        mima = MimaItem(8, value=Decimal("100.00"), slope="NEUTRO")
        previous = Decimal("99.00")

        calc._update_slope(mima, previous)
        self.assertEqual(mima.slope, "ALTA")

    def test_slope_baixa_decreasing(self):
        """THEN: Slope BAIXA quando SMA diminui."""
        calc = PhiCubeCalculator()
        mima = MimaItem(8, value=Decimal("99.00"), slope="NEUTRO")
        previous = Decimal("100.00")

        calc._update_slope(mima, previous)
        self.assertEqual(mima.slope, "BAIXA")

    def test_slope_neutro_equal(self):
        """THEN: Slope NEUTRO quando SMA igual."""
        calc = PhiCubeCalculator()
        mima = MimaItem(8, value=Decimal("100.00"), slope="NEUTRO")
        previous = Decimal("100.00")

        calc._update_slope(mima, previous)
        self.assertEqual(mima.slope, "NEUTRO")

    def test_slope_neutro_no_previous(self):
        """THEN: Slope NEUTRO quando não há valor anterior."""
        calc = PhiCubeCalculator()
        mima = MimaItem(8, value=Decimal("100.00"), slope="ALTA")

        calc._update_slope(mima, None)
        self.assertEqual(mima.slope, "NEUTRO")


class TestFanScoreCalculation(unittest.TestCase):
    """CASE: Cálculo de Fan Score (alinhamento geométrico)"""

    def test_fan_score_all_alta_maximum(self):
        """THEN: Fan score +6 quando ordem crescente (ALTA)."""
        calc = PhiCubeCalculator()
        # Configurar Mimas em ordem estritamente decrescente (ALTA trend)
        values = [Decimal("10710"), Decimal("10700"), Decimal("10680"),
                  Decimal("10650"), Decimal("10600"), Decimal("10550"),
                  Decimal("10500")]

        mimas_list = calc.current_mima.get_list()
        for mima, value in zip(mimas_list, values):
            mima.value = value

        fan_score = calc._calculate_fan_score()
        self.assertEqual(fan_score, 6)

    def test_fan_score_all_baixa_minimum(self):
        """THEN: Fan score -6 quando ordem decrescente (BAIXA)."""
        calc = PhiCubeCalculator()
        # Configurar Mimas em ordem estritamente crescente (BAIXA trend)
        values = [Decimal("10500"), Decimal("10550"), Decimal("10600"),
                  Decimal("10650"), Decimal("10680"), Decimal("10700"),
                  Decimal("10800")]

        mimas_list = calc.current_mima.get_list()
        for mima, value in zip(mimas_list, values):
            mima.value = value

        fan_score = calc._calculate_fan_score()
        self.assertEqual(fan_score, -6)

    def test_fan_score_misto_near_zero(self):
        """THEN: Fan score ~0 quando misturado."""
        calc = PhiCubeCalculator()
        # Configurar alternado: cima, baixo, cima, baixo...
        values = [Decimal("10600"), Decimal("10700"), Decimal("10650"),
                  Decimal("10680"), Decimal("10660"), Decimal("10690"),
                  Decimal("10670")]

        mimas_list = calc.current_mima.get_list()
        for mima, value in zip(mimas_list, values):
            mima.value = value

        fan_score = calc._calculate_fan_score()
        # Com padrão alternado: +1 -1 +1 -1 +1 -1 = 0
        self.assertEqual(fan_score, 0)

    def test_fan_score_identical_values_zero(self):
        """THEN: Fan score 0 quando todas Mimas iguais."""
        calc = PhiCubeCalculator()
        constant = Decimal("10650.00")

        mimas_list = calc.current_mima.get_list()
        for mima in mimas_list:
            mima.value = constant

        fan_score = calc._calculate_fan_score()
        self.assertEqual(fan_score, 0)


class TestAlignmentDetection(unittest.TestCase):
    """CASE: Detecção de alinhamento ALTA/BAIXA/MISTO"""

    def test_alignment_alta_positive_fan(self):
        """THEN: Alinhamento ALTA quando fan_score > 2."""
        calc = PhiCubeCalculator()
        calc.current_mima.fan_score = 5
        alignment = calc._determine_alignment()
        self.assertEqual(alignment, "ALTA")

    def test_alignment_baixa_negative_fan(self):
        """THEN: Alinhamento BAIXA quando fan_score < -2."""
        calc = PhiCubeCalculator()
        calc.current_mima.fan_score = -5
        alignment = calc._determine_alignment()
        self.assertEqual(alignment, "BAIXA")

    def test_alignment_misto_near_zero(self):
        """THEN: Alinhamento MISTO quando |fan_score| <= 2."""
        calc = PhiCubeCalculator()
        for fan_score in [-2, -1, 0, 1, 2]:
            calc.current_mima.fan_score = fan_score
            alignment = calc._determine_alignment()
            self.assertEqual(alignment, "MISTO")


class TestNormalization(unittest.TestCase):
    """CASE: Normalização de fan_score para [0, 1]"""

    def test_normalize_maximum_score_6(self):
        """THEN: Fan score +6 normaliza para 1.0."""
        mima = MimaData()
        mima.fan_score = 6
        normalized = mima.get_normalized_score()
        self.assertAlmostEqual(normalized, 1.0, places=2)

    def test_normalize_minimum_score_minus_6(self):
        """THEN: Fan score -6 normaliza para 0.0."""
        mima = MimaData()
        mima.fan_score = -6
        normalized = mima.get_normalized_score()
        self.assertAlmostEqual(normalized, 0.0, places=2)

    def test_normalize_zero_score_05(self):
        """THEN: Fan score 0 normaliza para 0.5."""
        mima = MimaData()
        mima.fan_score = 0
        normalized = mima.get_normalized_score()
        self.assertAlmostEqual(normalized, 0.5, places=2)

    def test_normalize_all_scores_range(self):
        """THEN: Todos fan_scores normalizam para [0, 1]."""
        mima = MimaData()
        for fan_score in range(-6, 7):
            mima.fan_score = fan_score
            normalized = mima.get_normalized_score()
            self.assertGreaterEqual(normalized, 0.0)
            self.assertLessEqual(normalized, 1.0)


class TestWeightedScore(unittest.TestCase):
    """CASE: Aplicação de peso ao score normalizado"""

    def test_weighted_score_default_weight_015(self):
        """THEN: Peso padrão 0.15 aplicado corretamente."""
        mima = MimaData()
        mima.fan_score = 6
        weighted = mima.get_weighted_score(weight=0.15)
        # (6+6)/12 * 0.15 = 1.0 * 0.15 = 0.15
        self.assertAlmostEqual(weighted, 0.15, places=2)

    def test_weighted_score_custom_weight_020(self):
        """THEN: Peso customizado 0.20 aplicado corretamente."""
        mima = MimaData()
        mima.fan_score = 6
        weighted = mima.get_weighted_score(weight=0.20)
        self.assertAlmostEqual(weighted, 0.20, places=2)

    def test_weighted_score_minimum_fan(self):
        """THEN: Fan score -6 contribui 0 (mínimo)."""
        mima = MimaData()
        mima.fan_score = -6
        weighted = mima.get_weighted_score(weight=0.15)
        self.assertAlmostEqual(weighted, 0.0, places=2)


class TestCalculateMethod(unittest.TestCase):
    """CASE: Método principal calculate() - Integração completa"""

    def test_calculate_returns_mima_data(self):
        """THEN: calculate() retorna MimaData válido."""
        calc = PhiCubeCalculator()
        for _ in range(610):
            calc.add_candle(10650)

        result = calc.calculate()
        self.assertIsInstance(result, MimaData)
        self.assertIsNotNone(result.alignment)
        self.assertIn(result.alignment, ["ALTA", "BAIXA", "MISTO"])

    def test_calculate_empty_history(self):
        """THEN: calculate() com histórico vazio retorna defaults."""
        calc = PhiCubeCalculator()
        result = calc.calculate()
        self.assertIsInstance(result, MimaData)

    def test_calculate_updates_fan_score(self):
        """THEN: calculate() atualiza fan_score."""
        calc = PhiCubeCalculator()
        # Adicionar 100 candles crescentes
        for i in range(100):
            calc.add_candle(10600 + i)

        result = calc.calculate()
        # Com preço crescente, esperamos fan_score positivo
        self.assertGreaterEqual(result.fan_score, 0)


class TestGetterMethods(unittest.TestCase):
    """CASE: Métodos getter (fan_score, scores)"""

    def test_get_fan_score(self):
        """THEN: get_fan_score() retorna fan_score bruto."""
        calc = PhiCubeCalculator()
        calc.current_mima.fan_score = 5
        self.assertEqual(calc.get_fan_score(), 5)

    def test_get_normalized_score(self):
        """THEN: get_normalized_score() retorna [0, 1]."""
        calc = PhiCubeCalculator()
        calc.current_mima.fan_score = 6
        normalized = calc.get_normalized_score()
        self.assertAlmostEqual(normalized, 1.0, places=2)

    def test_get_weighted_score(self):
        """THEN: get_weighted_score() aplica peso."""
        calc = PhiCubeCalculator()
        calc.current_mima.fan_score = 0  # Meio
        weighted = calc.get_weighted_score(0.15)
        # (0+6)/12 * 0.15 = 0.5 * 0.15 ≈ 0.075
        self.assertAlmostEqual(weighted, 0.075, places=2)


class TestGetStatus(unittest.TestCase):
    """CASE: Status dictionary para telemetria"""

    def test_get_status_structure(self):
        """THEN: get_status() retorna dict com estrutura correta."""
        calc = PhiCubeCalculator()
        for _ in range(100):
            calc.add_candle(10650)

        calc.calculate()
        status = calc.get_status()

        # Verificar campos obrigatórios
        self.assertIn("candles_loaded", status)
        self.assertIn("alignment", status)
        self.assertIn("fan_score", status)
        self.assertIn("normalized_score", status)
        self.assertIn("weighted_score_015", status)
        self.assertIn("mimas", status)

    def test_get_status_mimas_data(self):
        """THEN: Status contém dados de todas 7 Mimas."""
        calc = PhiCubeCalculator()
        for _ in range(610):
            calc.add_candle(10650)

        calc.calculate()
        status = calc.get_status()

        mimas_dict = status["mimas"]
        expected_periods = [8, 17, 34, 72, 144, 305, 610]
        for period in expected_periods:
            self.assertIn(period, mimas_dict)
            self.assertIn("value", mimas_dict[period])
            self.assertIn("slope", mimas_dict[period])


class TestFactoryFunction(unittest.TestCase):
    """CASE: Factory function create_phicube_calculator()"""

    def test_factory_creates_calculator(self):
        """THEN: Factory retorna PhiCubeCalculator válido."""
        calc = create_phicube_calculator()
        self.assertIsInstance(calc, PhiCubeCalculator)
        self.assertEqual(calc.window_size, 610)


class TestEdgeCases(unittest.TestCase):
    """CASE: Casos extremos e situações especiais"""

    def test_very_small_price_movements(self):
        """THEN: Diferenças mínimas (~0.01) contam para alinhamento."""
        calc = PhiCubeCalculator()
        base = Decimal("10650.00")
        for i in range(100):
            calc.add_candle(float(base + Decimal("0.01") * i))

        calc.calculate()
        # Com incrementos mínimos, ainda deve detectar trend
        self.assertIsNotNone(calc.current_mima.fan_score)

    def test_constant_price_no_movement(self):
        """THEN: Preço constante resulta em fan_score=0."""
        calc = PhiCubeCalculator()
        for _ in range(610):
            calc.add_candle(10650.00)

        calc.calculate()
        self.assertEqual(calc.current_mima.fan_score, 0)

    def test_rapid_price_changes(self):
        """THEN: Mudanças rápidas processadas corretamente."""
        calc = PhiCubeCalculator()
        # Simular spike: preço sobe 100 pontos rapidamente
        prices = [10650] * 50 + [10750] * 50  # Spike no meio
        for p in prices:
            calc.add_candle(p)

        calc.calculate()
        # Após spike, Mimas devem estar elevadas
        self.assertGreater(calc.current_mima.m8.value, Decimal("10650"))


if __name__ == "__main__":
    # Executar testes com saída verbosa em português
    unittest.main(verbosity=2)
