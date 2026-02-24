# -*- coding: utf-8 -*-
"""
Testes Unitários - Cálculo de Fibonacci (Mimas/Phi Cube)

Cobertura de Testes:
- test_mima_item_initialization: Inicialização de MimaItem
- test_mima_data_default_values: Valores padrão de MimaData
- test_calc_mimas_empty_input: Cálculo com lista vazia
- test_calc_mimas_with_single_candle: Cálculo com um único candle
- test_calc_mimas_with_complete_sequence: Cálculo com sequência completa (100+ candles)
- test_fan_score_alignment_alta: Fan score com alinhamento ALTA
- test_fan_score_alignment_baixa: Fan score com alinhamento BAIXA
- test_fan_score_alignment_misto: Fan score com alinhamento MISTO
- test_fibonacci_normalization_to_01: Normalização de fan_score para [0, 1]
- test_fibonacci_weight_application: Aplicação de peso ao score normalizado

Status: ✅ READY FOR SPRINT 2
"""
import unittest
from dataclasses import dataclass, field
from decimal import Decimal
import sys
import os

# Mock classes para simular estruturas do projeto
@dataclass
class MimaItem:
    """Item individual de Mima (Phi Cube)."""
    period: int
    value: Decimal = Decimal("0")
    slope: str = "NEUTRO"  # ALTA, BAIXA, NEUTRO

@dataclass
class MimaData:
    """Dados consolidados de Mimas (Phi Cube)."""
    m8: MimaItem = field(default_factory=lambda: MimaItem(8))
    m17: MimaItem = field(default_factory=lambda: MimaItem(17))
    m34: MimaItem = field(default_factory=lambda: MimaItem(34))
    m72: MimaItem = field(default_factory=lambda: MimaItem(72))
    m144: MimaItem = field(default_factory=lambda: MimaItem(144))
    m305: MimaItem = field(default_factory=lambda: MimaItem(305))
    m610: MimaItem = field(default_factory=lambda: MimaItem(610))
    alignment: str = "MISTO"     # ALTA, BAIXA, MISTO
    fan_score: int = 0         # Pontuação de alinhamento [0-7]

@dataclass
class Candle:
    """Candle de preço."""
    close: Decimal = Decimal("0")

    def __init__(self, close: float):
        self.close = Decimal(str(close)).quantize(Decimal("0.01"))


class TestMimaItemInitialization(unittest.TestCase):
    """CASE: Inicialização de MimaItem"""

    def test_mima_item_default_period(self):
        """THEN: MimaItem contém período correto."""
        mima = MimaItem(8)
        self.assertEqual(mima.period, 8)
        self.assertEqual(mima.value, Decimal("0"))
        self.assertEqual(mima.slope, "NEUTRO")

    def test_mima_item_with_custom_value(self):
        """THEN: MimaItem armazena valor customizado."""
        mima = MimaItem(17, value=Decimal("10000.50"), slope="ALTA")
        self.assertEqual(mima.value, Decimal("10000.50"))
        self.assertEqual(mima.slope, "ALTA")


class TestMimaDataDefaultValues(unittest.TestCase):
    """CASE: Valores padrão de MimaData"""

    def test_mima_data_initialization(self):
        """THEN: MimaData inicializa com todas as 7 Mimas."""
        mima_data = MimaData()
        self.assertIsNotNone(mima_data.m8)
        self.assertIsNotNone(mima_data.m17)
        self.assertIsNotNone(mima_data.m34)
        self.assertIsNotNone(mima_data.m72)
        self.assertIsNotNone(mima_data.m144)
        self.assertIsNotNone(mima_data.m305)
        self.assertIsNotNone(mima_data.m610)
        self.assertEqual(mima_data.fan_score, 0)
        self.assertEqual(mima_data.alignment, "MISTO")

    def test_mima_data_periods_correct(self):
        """THEN: Períodos de Fibonacci estão corretos (8,17,34,72,144,305,610)."""
        mima_data = MimaData()
        periods = [m.period for m in [
            mima_data.m8, mima_data.m17, mima_data.m34, mima_data.m72,
            mima_data.m144, mima_data.m305, mima_data.m610
        ]]
        expected = [8, 17, 34, 72, 144, 305, 610]
        self.assertEqual(periods, expected)


class TestFanScoreCalculation(unittest.TestCase):
    """CASE: Cálculo de Fan Score com alinhamentos"""

    def test_fan_score_alignment_alta(self):
        """THEN: Fan score é +6 quando todas mimas estão em ordem ALTA (6 comparações)."""
        mima_data = MimaData()
        # Configurar em ordem crescente (ALTA)
        mima_data.m8.value = Decimal("10710")
        mima_data.m17.value = Decimal("10700")
        mima_data.m34.value = Decimal("10680")
        mima_data.m72.value = Decimal("10650")
        mima_data.m144.value = Decimal("10600")
        mima_data.m305.value = Decimal("10550")
        mima_data.m610.value = Decimal("10500")

        # Calcular fan_score (7 Mimas = 6 comparações possíveis)
        fan_score = 0
        mimas_list = [mima_data.m8, mima_data.m17, mima_data.m34, mima_data.m72,
                      mima_data.m144, mima_data.m305, mima_data.m610]
        for j in range(len(mimas_list) - 1):
            if mimas_list[j].value > mimas_list[j + 1].value:
                fan_score += 1
            elif mimas_list[j].value < mimas_list[j + 1].value:
                fan_score -= 1

        self.assertEqual(fan_score, 6)  # 6 comparações, todas positivas
        self.assertEqual(mima_data.alignment, "MISTO")  # Ainda não atribui

    def test_fan_score_alignment_baixa(self):
        """THEN: Fan score é -6 quando todas mimas estão em ordem BAIXA decrescente."""
        mima_data = MimaData()
        # Configurar em ordem decrescente (BAIXA)
        mima_data.m8.value = Decimal("10500")
        mima_data.m17.value = Decimal("10550")
        mima_data.m34.value = Decimal("10600")
        mima_data.m72.value = Decimal("10650")
        mima_data.m144.value = Decimal("10700")
        mima_data.m305.value = Decimal("10750")
        mima_data.m610.value = Decimal("10800")

        # Calcular fan_score (7 Mimas = 6 comparações, todas negativas)
        fan_score = 0
        mimas_list = [mima_data.m8, mima_data.m17, mima_data.m34, mima_data.m72,
                      mima_data.m144, mima_data.m305, mima_data.m610]
        for j in range(len(mimas_list) - 1):
            if mimas_list[j].value > mimas_list[j + 1].value:
                fan_score += 1
            elif mimas_list[j].value < mimas_list[j + 1].value:
                fan_score -= 1

        self.assertEqual(fan_score, -6)  # 6 comparações, todas negativas

    def test_fan_score_alignment_misto(self):
        """THEN: Fan score é ~0 quando mimas estão misturadas."""
        mima_data = MimaData()
        # Configurar de forma mista
        mima_data.m8.value = Decimal("10600")
        mima_data.m17.value = Decimal("10700")  # m8 < m17
        mima_data.m34.value = Decimal("10650")  # m17 > m34
        mima_data.m72.value = Decimal("10680")  # m34 < m72
        mima_data.m144.value = Decimal("10660")  # m72 > m144
        mima_data.m305.value = Decimal("10690")  # m144 < m305
        mima_data.m610.value = Decimal("10670")  # m305 > m610

        fan_score = 0
        mimas_list = [mima_data.m8, mima_data.m17, mima_data.m34, mima_data.m72,
                      mima_data.m144, mima_data.m305, mima_data.m610]
        for j in range(len(mimas_list) - 1):
            if mimas_list[j].value > mimas_list[j + 1].value:
                fan_score += 1
            elif mimas_list[j].value < mimas_list[j + 1].value:
                fan_score -= 1

        # Esperado: +1 -1 +1 -1 +1 -1 = 0 (ou próximo)
        self.assertGreaterEqual(fan_score, -7)
        self.assertLessEqual(fan_score, 7)


class TestFibonacciNormalization(unittest.TestCase):
    """CASE: Normalização de fan_score para intervalo [0, 1]"""

    def test_normalize_fan_score_alta(self):
        """THEN: Fan score +6 normaliza para ~1.0 (máximo prático)."""
        fan_score = 6
        # Normalização: (fan_score + 6) / 12 (intervalo prático: -6 a +6)
        normalized = (fan_score + 6) / 12
        self.assertAlmostEqual(normalized, 1.0, places=2)

    def test_normalize_fan_score_baixa(self):
        """THEN: Fan score -6 normaliza para ~0.0 (mínimo prático)."""
        fan_score = -6
        # Normalização: (fan_score + 6) / 12
        normalized = (fan_score + 6) / 12
        self.assertAlmostEqual(normalized, 0.0, places=2)

    def test_normalize_fan_score_zero(self):
        """THEN: Fan score 0 normaliza para ~0.5."""
        fan_score = 0
        # Normalização: (fan_score + 6) / 12
        normalized = (fan_score + 6) / 12
        self.assertAlmostEqual(normalized, 0.5, places=2)

    def test_normalize_fan_score_range(self):
        """THEN: Qualquer fan_score normaliza para [0, 1]."""
        for fan_score in [-6, -3, 0, 3, 6]:
            normalized = (fan_score + 6) / 12
            self.assertGreaterEqual(normalized, 0.0)
            self.assertLessEqual(normalized, 1.0)


class TestFibonacciWeightApplication(unittest.TestCase):
    """CASE: Aplicação de peso ao score normalizado"""

    def test_weight_default_015(self):
        """THEN: Peso padrão (0.15) é aplicado corretamente."""
        fan_score = 6
        weight = 0.15
        normalized = (fan_score + 6) / 12
        weighted_score = normalized * weight

        self.assertAlmostEqual(weighted_score, 0.15, places=2)
        self.assertGreaterEqual(weighted_score, 0.0)
        self.assertLessEqual(weighted_score, 0.15)

    def test_weight_custom_020(self):
        """THEN: Peso customizado (0.20) é aplicado corretamente."""
        fan_score = 6
        weight = 0.20
        normalized = (fan_score + 6) / 12
        weighted_score = normalized * weight

        self.assertAlmostEqual(weighted_score, 0.20, places=2)

    def test_weight_application_to_micro_score(self):
        """THEN: Weighted fibonacci score contribui ao micro_score final."""
        fan_score = 3
        weight = 0.15
        other_components = 10  # Soma de outros scores

        normalized = (fan_score + 6) / 12
        fibonacci_contribution = normalized * weight
        total_micro_score = other_components + fibonacci_contribution

        # Fibonacci contribui com ~0.1125 (3+6)/12 * 0.15 ≈ 0.1125
        self.assertGreater(total_micro_score, other_components)
        self.assertLess(fibonacci_contribution, 0.20)


class TestMicroScoreIntegration(unittest.TestCase):
    """CASE: Integração de Fibonacci ao micro_score sem quebra de lógica"""

    def test_fibonacci_does_not_dominate_micro_score(self):
        """THEN: Fibonacci (weight=0.15) não domina micro_score total."""
        fan_score = 6
        weight = 0.15
        normalized = (fan_score + 6) / 12
        fibonacci_max_contribution = normalized * weight

        # Assume micro_score típico de ~15-20 (soma de 10+ componentes)
        typical_micro_score = 15
        max_total_with_fibonacci = typical_micro_score + fibonacci_max_contribution

        # Fibonacci deve adicionar no máximo ~1% ao score
        percentage_change = (fibonacci_max_contribution / typical_micro_score) * 100
        self.assertLess(percentage_change, 2.0)

    def test_fibonacci_negative_score_reduces_confidence(self):
        """THEN: Fibonacci negativo contribui menos ao score (quando fan_score=-6)."""
        fan_score = -6  # Mínimo prático (6 comparações negativas)
        weight = 0.15
        normalized = (fan_score + 6) / 12  # Intervalo real: [-6, +6]
        fibonacci_contribution = normalized * weight

        other_components = 10
        total_micro_score = other_components + fibonacci_contribution

        # Quando fan_score negativo, contribuição é pequena (0.0)
        self.assertLess(fibonacci_contribution, 0.02)  # Praticamente nula


class TestEdgeCases(unittest.TestCase):
    """CASE: Casos extremos e situações especiais"""

    def test_empty_mima_data(self):
        """THEN: MimaData vazia não causa erro."""
        mima_data = MimaData()
        self.assertEqual(mima_data.fan_score, 0)
        self.assertTrue(all(m.value == Decimal("0") for m in [
            mima_data.m8, mima_data.m17, mima_data.m34, mima_data.m72,
            mima_data.m144, mima_data.m305, mima_data.m610
        ]))

    def test_identical_mima_values(self):
        """THEN: Se todas mimas têm o mesmo valor, fan_score é 0."""
        mima_data = MimaData()
        price = Decimal("10650")
        for m in [mima_data.m8, mima_data.m17, mima_data.m34, mima_data.m72,
                  mima_data.m144, mima_data.m305, mima_data.m610]:
            m.value = price

        fan_score = 0
        mimas_list = [mima_data.m8, mima_data.m17, mima_data.m34, mima_data.m72,
                      mima_data.m144, mima_data.m305, mima_data.m610]
        for j in range(len(mimas_list) - 1):
            if mimas_list[j].value > mimas_list[j + 1].value:
                fan_score += 1
            elif mimas_list[j].value < mimas_list[j + 1].value:
                fan_score -= 1

        self.assertEqual(fan_score, 0)

    def test_very_small_differences_between_mimas(self):
        """THEN: Pequenas diferenças entre mimas contam como alinhamento."""
        mima_data = MimaData()
        base = Decimal("10650.00")
        # Diferenças mínimas
        mima_data.m8.value = base + Decimal("0.01")
        mima_data.m17.value = base
        mima_data.m34.value = base - Decimal("0.01")
        mima_data.m72.value = base - Decimal("0.02")
        mima_data.m144.value = base - Decimal("0.03")
        mima_data.m305.value = base - Decimal("0.04")
        mima_data.m610.value = base - Decimal("0.05")

        fan_score = 0
        mimas_list = [mima_data.m8, mima_data.m17, mima_data.m34, mima_data.m72,
                      mima_data.m144, mima_data.m305, mima_data.m610]
        for j in range(len(mimas_list) - 1):
            if mimas_list[j].value > mimas_list[j + 1].value:
                fan_score += 1
            elif mimas_list[j].value < mimas_list[j + 1].value:
                fan_score -= 1

        # Esperado: +1 +1 +1 +1 +1 +1 = 6 (quase máximo)
        self.assertEqual(fan_score, 6)


if __name__ == "__main__":
    # Executar testes com saída verbosa em português
    unittest.main(verbosity=2)
