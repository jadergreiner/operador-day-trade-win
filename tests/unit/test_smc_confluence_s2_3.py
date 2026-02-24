"""
Unit Tests para S2-3: Confluência SMC (M1/M5)

Testar a lógica de confluência entre timeframes curtos para sinais de convicção máxima.

REGRAS:
- CASE-THEN-WHEN (Dado/Quando/Então)
- Verboso em Português
- Clean Code
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from scripts.agente_micro_tendencia_winfut import (
    _calc_smc_multi_tf,
    _calc_atr_map,
    SMCTimeframeData,
    SMCMultiTF,
    Candle
)

class TestSMCConfluence:
    """Test suite para Confluência SMC M1/M5 - S2-3"""

    # ==================== TEST S2-3: CONFLUENCE ALIGNMENT ====================

    def test_smc_confluence_m1_m5_bullish(self):
        """
        CASE: M1 e M5 ambos com bias BULLISH e em DISCOUNT (Zona de Compra)
        WHEN: _calc_smc_multi_tf é chamado com candles de M1 e M5
        THEN: Deve retornar confluência 'ALTA' com score máximo (5)
        """
        with patch("scripts.agente_micro_tendencia_winfut._detect_smc_for_timeframe") as mock_detect:
            def side_effect(candles, tf):
                data = SMCTimeframeData(timeframe=tf)
                if tf in ["M1", "M5"]:
                    data.bias = "BULLISH"
                    data.equilibrium = "DISCOUNT"
                    data.direction = "ALTA"
                return data
            mock_detect.side_effect = side_effect

            # Passando listas vazias pois o mock intercepta
            result = _calc_smc_multi_tf([], [], [], [])

            assert result.confluence_m1_m5 == "ALTA", "Deveria ser ALTA quando alinhado Bullish"
            assert result.confluence_score == 5, "Score deveria ser 5 para confluência perfeita"

    def test_smc_confluence_m1_m5_bearish(self):
        """
        CASE: M1 e M5 ambos com bias BEARISH e em PREMIUM (Zona de Venda)
        WHEN: _calc_smc_multi_tf é chamado
        THEN: Deve retornar confluência 'BAIXA' com score máximo (5)
        """
        with patch("scripts.agente_micro_tendencia_winfut._detect_smc_for_timeframe") as mock_detect:
            def side_effect(candles, tf):
                data = SMCTimeframeData(timeframe=tf)
                if tf in ["M1", "M5"]:
                    data.bias = "BEARISH"
                    data.equilibrium = "PREMIUM"
                    data.direction = "BAIXA"
                return data
            mock_detect.side_effect = side_effect

            result = _calc_smc_multi_tf([], [], [], [])

            assert result.confluence_m1_m5 == "BAIXA", "Deveria ser BAIXA quando alinhado Bearish"
            assert result.confluence_score == 5, "Score deveria ser 5 para confluência perfeita"

    def test_smc_confluence_m1_m5_desalinhado(self):
        """
        CASE: M1 BULLISH e M5 BEARISH (Divergência de timeframes)
        WHEN: _calc_smc_multi_tf é chamado
        THEN: Deve retornar confluência 'NEUTRO' com score 0
        """
        with patch("scripts.agente_micro_tendencia_winfut._detect_smc_for_timeframe") as mock_detect:
            def side_effect(candles, tf):
                data = SMCTimeframeData(timeframe=tf)
                if tf == "M1":
                    data.bias = "BULLISH"
                elif tf == "M5":
                    data.bias = "BEARISH"
                return data
            mock_detect.side_effect = side_effect

            result = _calc_smc_multi_tf([], [], [], [])

            assert result.confluence_m1_m5 == "NEUTRO"
            assert result.confluence_score == 0

    # ==================== TEST S2-3: ATR MAP (VOLATILITY WEB) ====================

    def test_atr_map_calculo_basico(self):
        """
        CASE: Preço 130000 e ATR 200
        WHEN: _calc_atr_map é chamado com multiplicadores padrão
        THEN: Deve retornar os níveis de 1.0x, 1.5x, 2.0x e 3.0x corretos
        """
        price = Decimal("130000")
        atr = Decimal("200")

        result = _calc_atr_map(price, atr, multipliers=[1.0, 2.0])

        # 130000 + 200 = 130200
        # 130000 + 400 = 130400
        assert result["up_1.0x"] == Decimal("130200")
        assert result["up_2.0x"] == Decimal("130400")
        assert result["down_1.0x"] == Decimal("129800")
        assert result["down_2.0x"] == Decimal("129600")

    def test_atr_map_arredondamento_tick_size(self):
        """
        CASE: Preço e ATR que resultam em valores quebrados
        WHEN: _calc_atr_map é chamado
        THEN: Deve arredondar todos os níveis para o tick_size do WIN (5 pts)
        """
        price = Decimal("130000")
        # ATR 201 -> m=1x -> 130201 -> deve virar 130200
        atr = Decimal("201")

        result = _calc_atr_map(price, atr, multipliers=[1.0])
        assert result["up_1.0x"] == Decimal("130200")

        # ATR 203 -> m=1x -> 130203 -> deve virar 130205
        atr2 = Decimal("203")
        result2 = _calc_atr_map(price, atr2, multipliers=[1.0])
        assert result2["up_1.0x"] == Decimal("130205")
