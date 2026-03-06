"""
Teste de AC1: Geração de Sinal M5 com Detecção SMC

Acceptance Criteria 1 (Camada 1):
    ✓ M5 detecta SMC (BOS/CHoCH/FVG) a cada fechamento de candle
    ✓ Produz sinal COMPRA ou VENDA com score [-3, +3]
    ✓ Sinal gerado INDEPENDENTE de qualquer decisão de entrada
    ✓ Mínimo: 2.880 candles (10 dias) para validação estatística

Status: IMPLEMENTAÇÃO v1.0 (05/03/2026)
Referência: docs/prompts/OPERATIVE_BRIEF_BACKTEST_V1_2.md (AC1)
"""

import pytest
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import sys
from pathlib import Path

# Adicionar src/ ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from application.signal_persistence import (
    SignalGenerator,
    SignalType,
    SMCDetector,
    MarketContext,
    Signal,
)


class TestAC1SignalGenerationM5:
    """Test suite para AC1: Geração de Sinal M5"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup para cada teste."""
        self.generator = SignalGenerator(
            logger=logging.getLogger("test_ac1")
        )
        self.symbol = "WIN"
        self.timeframe = "M5"

    # ========================================================================
    # AC1 - Critério 1: M5 detecta SMC (BOS/CHoCH/FVG)
    # ========================================================================

    def test_ac1_detect_bos_bullish(self):
        """
        ✓ AC1.1: Detectar Break of Structure (BOS) Bullish

        Critério: Quando close > high anterior → BOS Bullish → sinal BUY
        """
        # Arrange: Criar candle M5 com BOS bullish
        candles = {
            "open": 123400.0,
            "high": 123450.0,
            "low": 123350.0,
            "close": 123500.0,  # > prev_high (123450) = BOS
            "volume": 100,
            "prev_high": 123450.0,
            "prev_low": 123300.0,
        }
        current_price = 123500.0

        # Act: Detectar sinal
        signal = self.generator.detect_smc(
            candles_m5=candles,
            symbol=self.symbol,
            current_price=current_price,
            candle_index=0,
        )

        # Assert: Validar sinal gerado
        assert signal is not None, "Sinal BOS bullish não foi detectado"
        assert signal.signal_type == SignalType.BUY, "Sinal deveria ser BUY"
        assert signal.smc_detector == SMCDetector.BOS, "Detector deveria ser BOS"
        assert (
            -3.0 <= signal.smc_score <= 3.0
        ), f"Score fora do range [-3, +3]: {signal.smc_score}"
        assert signal.smc_score > 0, "Score BOS bullish deveria ser positivo"

    def test_ac1_detect_bos_bearish(self):
        """
        ✓ AC1.1: Detectar Break of Structure (BOS) Bearish

        Critério: Quando close < low anterior → BOS Bearish → sinal SELL
        """
        # Arrange: Criar candle M5 com BOS bearish
        candles = {
            "open": 123400.0,
            "high": 123450.0,
            "low": 123200.0,  # < prev_low (123300) = BOS
            "close": 123250.0,
            "volume": 100,
            "prev_high": 123450.0,
            "prev_low": 123300.0,
        }
        current_price = 123250.0

        # Act: Detectar sinal
        signal = self.generator.detect_smc(
            candles_m5=candles,
            symbol=self.symbol,
            current_price=current_price,
            candle_index=0,
        )

        # Assert: Validar sinal gerado
        assert signal is not None, "Sinal BOS bearish não foi detectado"
        assert signal.signal_type == SignalType.SELL, "Sinal deveria ser SELL"
        assert signal.smc_detector == SMCDetector.BOS, "Detector deveria ser BOS"
        assert (
            -3.0 <= signal.smc_score <= 3.0
        ), f"Score fora do range [-3, +3]: {signal.smc_score}"
        assert signal.smc_score < 0, "Score BOS bearish deveria ser negativo"

    # ========================================================================
    # AC1 - Critério 2: Score [-3, +3]
    # ========================================================================

    def test_ac1_score_in_valid_range(self):
        """
        ✓ AC1.2: Score produzido está no range [-3, +3]

        Critério: Qualquer sinal gerado deve ter score entre -3 e +3
        """
        # Arrange: Criar múltiplos candles
        test_cases = [
            {
                "name": "Strong bullish BOS",
                "candles": {
                    "open": 123400.0,
                    "high": 123450.0,
                    "low": 123350.0,
                    "close": 123550.0,  # Strong break
                    "volume": 500,
                    "prev_high": 123450.0,
                    "prev_low": 123300.0,
                },
                "expected_type": SignalType.BUY,
            },
            {
                "name": "Moderate bearish BOS",
                "candles": {
                    "open": 123400.0,
                    "high": 123450.0,
                    "low": 123200.0,  # Moderate break
                    "close": 123250.0,
                    "volume": 200,
                    "prev_high": 123450.0,
                    "prev_low": 123300.0,
                },
                "expected_type": SignalType.SELL,
            },
        ]

        for test_case in test_cases:
            # Act: Detectar sinal
            signal = self.generator.detect_smc(
                candles_m5=test_case["candles"],
                symbol=self.symbol,
                current_price=test_case["candles"]["close"],
            )

            # Assert: Score deve estar em [-3, +3]
            if signal:
                assert (
                    -3.0 <= signal.smc_score <= 3.0
                ), f"Score {signal.smc_score} fora do range para {test_case['name']}"
                assert (
                    signal.signal_type == test_case["expected_type"]
                ), f"Tipo incorreto para {test_case['name']}"

    # ========================================================================
    # AC1 - Critério 3: INDEPENDENTE de decisão de entrada
    # ========================================================================

    def test_ac1_signal_independent_from_decision(self):
        """
        ✓ AC1.3: Sinal gerado INDEPENDENTE de qualquer decisão

        Critério: Uma vez gerado, sinal existe sem depender de decisão
        Camada 1 (sinal) ≠ Camada 2 (decisão de ENTRAR/FICAR_DE_FORA)
        """
        # Arrange: Criar candle M5
        candles = {
            "open": 123400.0,
            "high": 123450.0,
            "low": 123350.0,
            "close": 123500.0,
            "volume": 100,
            "prev_high": 123450.0,
            "prev_low": 123300.0,
        }
        current_price = 123500.0

        # Act: Gerar sinal (SEM nenhuma informação de decisão)
        signal = self.generator.detect_smc(
            candles_m5=candles,
            symbol=self.symbol,
            current_price=current_price,
        )

        # Assert: Sinal deve ser gerado e não ter campos de Camada 2
        assert signal is not None, "Sinal não foi gerado"
        assert hasattr(signal, "signal_type"), "Sinal deve ter signal_type"
        assert hasattr(signal, "smc_score"), "Sinal deve ter smc_score"

        # Verificar que decision fields NÃO estão preenchidos
        # (esses são campos de Camada 2, não Camada 1)
        assert (
            not hasattr(signal, "decision_type")
            or signal.decision_type is None
        ), "Sinal Camada 1 NÃO deve ter decision_type"

        # Verificar que signal_id é ÚNICO (pronto para persistência)
        assert signal.signal_id is not None, "Signal deve ter UUID único"
        assert len(signal.signal_id) > 0, "Signal_id não pode ser vazio"

    # ========================================================================
    # AC1 - Critério 4: Validação de volume mínimo (2.880 candles = 10 dias)
    # ========================================================================

    def test_ac1_minimum_candles_validation(self):
        """
        ✓ AC1.4: Validação de volume mínimo (2.880 candles para 10 dias)

        Critério: Dataset deve ter mínimo 2.880 candles M5 para validação
        Cálculo: 10 dias × 288 M5/dia = 2.880 candles
        """
        MIN_CANDLES = 2880  # 10 dias de M5
        CANDLES_PER_DAY = 288  # 24h × 60 min / 5 min

        # Arrange: Gerar número adequado de candles
        def generate_candles_dataset(num_days: int) -> List[Dict]:
            """Gera dataset synthetic de candles M5."""
            candles_list = []
            base_price = 123000.0
            current_time = datetime.now() - timedelta(days=num_days)

            for day in range(num_days):
                for candle_idx in range(CANDLES_PER_DAY):
                    # Preço varia aleatoriamente
                    price_change = (
                        50.0 if candle_idx % 10 == 0 else -10.0
                    )  # Simula movimento
                    base_price += price_change

                    candle = {
                        "timestamp": current_time.isoformat(),
                        "open": base_price - 10.0,
                        "high": base_price + 5.0,
                        "low": base_price - 15.0,
                        "close": base_price,
                        "volume": 100 + candle_idx % 50,
                        "prev_high": base_price - 5.0,  # Variação para BOS
                        "prev_low": base_price - 25.0,
                    }
                    candles_list.append(candle)
                    current_time += timedelta(minutes=5)

            return candles_list

        # Act: Gerar dataset de 10 dias
        dataset_10days = generate_candles_dataset(num_days=10)
        signals_generated = []

        for candle in dataset_10days:
            signal = self.generator.detect_smc(
                candles_m5={
                    "close": candle["close"],
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "volume": candle["volume"],
                    "prev_high": candle["prev_high"],
                    "prev_low": candle["prev_low"],
                },
                symbol=self.symbol,
                current_price=candle["close"],
            )
            if signal:
                signals_generated.append(signal)

        # Assert: Validações
        assert (
            len(dataset_10days) == MIN_CANDLES
        ), f"Dataset deve ter exatamente {MIN_CANDLES} candles"
        assert (
            len(signals_generated) > 0
        ), "Deve gerar pelo menos alguns sinais"
        assert (
            len(signals_generated) <= len(dataset_10days)
        ), "Número de sinais deve ser ≤ total de candles"

    # ========================================================================
    # AC1 - Propriedades do Signal (Camada 1)
    # ========================================================================

    def test_ac1_signal_properties_complete(self):
        """
        ✓ AC1.5: Signal gerado tem TODAS as propriedades de Camada 1

        Propriedades obrigatórias:
            - signal_id: UUID único
            - timestamp: momento do sinal
            - symbol: ativo (WIN, WDO, etc)
            - signal_type: BUY ou SELL
            - smc_score: [-3, +3]
            - smc_detector: BOS, CHoCH, FVG
            - entry_price: preço de entrada
            - market_context: indicadores capturados (RSI, ATR, etc)
        """
        # Arrange: Criar market_context completo
        market_context = MarketContext(
            rsi=65.5,
            atr=50.0,
            bb_upper=123500.0,
            bb_lower=123200.0,
            volume=500,
            spread=2.0,
            trend_direction="UP",
            last_close=123400.0,
        )

        candles = {
            "open": 123400.0,
            "high": 123450.0,
            "low": 123350.0,
            "close": 123500.0,
            "volume": 100,
            "prev_high": 123450.0,
            "prev_low": 123300.0,
        }
        current_price = 123500.0

        # Act: Gerar sinal com contexto
        signal = self.generator.detect_smc(
            candles_m5=candles,
            symbol=self.symbol,
            current_price=current_price,
            market_context=market_context,
            candle_index=42,
        )

        # Assert: Validar ALL propriedades obrigatórias
        assert signal is not None, "Signal não foi gerado"

        # Propriedades obrigatórias de Camada 1
        assert signal.signal_id is not None, "signal_id obrigatório"
        assert len(signal.signal_id) > 0, "signal_id não pode ser vazio"
        assert signal.timestamp is not None, "timestamp obrigatório"
        assert isinstance(signal.timestamp, datetime), "timestamp deve ser datetime"
        assert signal.symbol == self.symbol, "symbol deve ser preservado"
        assert signal.signal_type in [
            SignalType.BUY,
            SignalType.SELL,
        ], "signal_type deve ser BUY ou SELL"
        assert -3.0 <= signal.smc_score <= 3.0, "smc_score deve estar em [-3, +3]"
        assert signal.smc_detector in [
            SMCDetector.BOS,
            SMCDetector.CHOCH,
            SMCDetector.FVG,
        ], "smc_detector deve ser BOS/CHoCH/FVG"
        assert signal.entry_price == current_price, "entry_price deve ser current_price"
        assert signal.candle_index == 42, "candle_index deve ser preservado"

        # Contexto de mercado capturado
        assert signal.market_context is not None, "market_context obrigatório"
        assert signal.market_context.rsi == 65.5, "RSI deve ser preservado"
        assert signal.market_context.atr == 50.0, "ATR deve ser preservado"
        assert signal.market_context.trend_direction == "UP", "trend deveria ser UP"

    def test_ac1_signals_are_unique(self):
        """
        ✓ AC1.6: Cada signal gerado tem UUID **único**

        Critério: Mesmo que 2 sinais sejam idênticos (preço/tipo),
        cada um deve ter signal_id único para auditoria.
        """
        # Arrange: Mesmo candle M5, rodado 3 vezes
        candles = {
            "open": 123400.0,
            "high": 123450.0,
            "low": 123350.0,
            "close": 123500.0,
            "volume": 100,
            "prev_high": 123450.0,
            "prev_low": 123300.0,
        }
        current_price = 123500.0

        # Act: Gerar 3 sinais idênticos
        signals = []
        for i in range(3):
            signal = self.generator.detect_smc(
                candles_m5=candles,
                symbol=self.symbol,
                current_price=current_price,
            )
            if signal:
                signals.append(signal)

        # Assert: signal_ids devem ser TODOS diferentes
        assert (
            len(signals) == 3
        ), "Deveriam ser gerados 3 sinais"
        signal_ids = [s.signal_id for s in signals]
        assert len(set(signal_ids)) == 3, "Todos signal_ids devem ser únicos"

    # ========================================================================
    # AC1 - Rejeição de sinais fracos
    # ========================================================================

    def test_ac1_rejects_weak_signals(self):
        """
        ✓ AC1.7: Rejeita sinais com score < |1.0| (muito fracas)

        Critério: Apenas sinais com |score| >= 1.0 são válidos
        """
        # Arrange: Candle com movimento fraco (não deve gerar sinal)
        weak_candles = {
            "open": 123400.0,
            "high": 123450.0,
            "low": 123350.0,
            "close": 123405.0,  # Movimento muito pequeno
            "volume": 10,  # Baixo volume
            "prev_high": 123450.0,
            "prev_low": 123300.0,
        }
        current_price = 123405.0

        # Act: Tentar detectar sinal fraco
        signal = self.generator.detect_smc(
            candles_m5=weak_candles,
            symbol=self.symbol,
            current_price=current_price,
        )

        # Assert: Sinal fraco NÃO deveria ser gerado
        # (porque score seria < |1.0|)
        assert signal is None, "Sinais fraco não deveria ser gerado"


# ============================================================================
# TESTES DE INTEGRAÇÃO (AC1 + Persistência)
# ============================================================================


class TestAC1Integration:
    """Testes de integração: AC1 + persistência em DB"""

    @pytest.fixture
    def setup(self):
        """Setup para testes de integração."""
        self.generator = SignalGenerator(
            logger=logging.getLogger("test_ac1_integration")
        )
        self.symbol = "WIN"

    def test_ac1_signal_ready_for_persistence(self, setup):
        """
        ✓ AC1.8: Signal gerado pronto para persistência

        Critério: Signal object tem todos campos necessários
        para INSERT em tabela `signals` (BD)
        """
        # Arrange
        candles = {
            "open": 123400.0,
            "high": 123450.0,
            "low": 123350.0,
            "close": 123500.0,
            "volume": 100,
            "prev_high": 123450.0,
            "prev_low": 123300.0,
        }

        # Act: Gerar sinal
        signal = self.generator.detect_smc(
            candles_m5=candles,
            symbol=self.symbol,
            current_price=123500.0,
        )

        # Assert: Verificar que sinal tem todos campos para DB
        assert signal is not None
        assert signal.signal_id is not None, "signal_id obrigatório para DB"
        assert signal.timestamp is not None, "timestamp obrigatório"
        assert signal.symbol is not None, "symbol obrigatório"
        assert signal.signal_type is not None, "signal_type obrigatório"
        assert (
            signal.smc_score is not None
        ), "smc_score obrigatório"
        assert signal.smc_detector is not None, "smc_detector obrigatório"
        assert signal.entry_price is not None, "entry_price obrigatório"


if __name__ == "__main__":
    # Executar testes: pytest tests/test_camada1_ac1_signal_generation.py -v
    pytest.main([__file__, "-v", "--tb=short"])
