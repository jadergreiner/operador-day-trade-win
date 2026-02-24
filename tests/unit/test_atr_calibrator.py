"""
Testes Unitários para o Calibrador ATR Dinâmico.
Seguindo o padrão CASE-THEN-WHEN em Português.
"""

import pytest
from decimal import Decimal
from src.domain.services.atr_calibrator import ATRCalibrator


class TestCalibradorATR:
    """Suíte de testes para o Calibrador ATR."""

    def test_deve_calcular_trailing_stop_baseado_no_atr(self):
        # CASE: Dado um ATR de 100 pontos e um multiplicador de 2.0
        atr = Decimal("100")
        multiplicador = Decimal("2.0")
        calibrador = ATRCalibrator(multiplier=multiplicador)

        # WHEN: Quando calculamos o trailing stop
        resultado = calibrador.calculate_trailing_stop(atr)

        # THEN: Então o resultado deve ser 200 pontos
        assert resultado == Decimal("200")

    def test_deve_sugerir_volume_reduzido_para_volatilidade_alta(self):
        # CASE: Dado um ATR alto (ex: 300 pontos)
        atr = Decimal("300")
        calibrador = ATRCalibrator(high_volatility_threshold=Decimal("250"))

        # WHEN: Quando sugerimos o volume
        volume = calibrador.suggest_volume(atr, base_volume=2)

        # THEN: Então o volume deve ser reduzido para o mínimo (1)
        assert volume == 1

    def test_deve_manter_volume_base_para_volatilidade_normal(self):
        # CASE: Dado um ATR normal (ex: 100 pontos)
        atr = Decimal("100")
        calibrador = ATRCalibrator(high_volatility_threshold=Decimal("250"))

        # WHEN: Quando sugerimos o volume
        volume = calibrador.suggest_volume(atr, base_volume=2)

        # THEN: Então o volume deve ser mantido
        assert volume == 2

    def test_deve_garantir_valores_minimos_funcionais(self):
        # CASE: Dado um ATR muito baixo ou zero
        atr = Decimal("0")
        calibrador = ATRCalibrator(min_trailing_stop=Decimal("100"))

        # WHEN: Quando calculamos o trailing stop
        resultado = calibrador.calculate_trailing_stop(atr)

        # THEN: Então o resultado deve respeitar o mínimo configurado
        assert resultado == Decimal("100")
