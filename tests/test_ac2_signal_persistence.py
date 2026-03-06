"""
Testes para AC2: Signal Persistence (Persistência de Sinais)

Testes:
    1. test_ac2_insert_single_signal - Inserir um único sinal
    2. test_ac2_market_context_serialization - Serializar contexto de mercado
    3. test_ac2_insert_batch_signals - Inserir múltiplos sinais
    4. test_ac2_duplicate_rejection - Rejeitar sinais duplicados
    5. test_ac2_deserialize_market_context - Desserializar contexto
    6. test_ac2_persistence_integration - Integração AC1 → AC2

Status: ✅ AC2 IMPLEMENTATION READY
Date: 05/03/2026
"""

import pytest
import json
import sqlite3
from datetime import datetime
from uuid import uuid4

from src.application.signal_persistence import (
    Signal,
    SignalType,
    SMCDetector,
    SignalOutcomeType,
    MarketContext,
    SignalPersistence,
    SignalGenerator,
)


# ==========================================================================
# FIXTURES
# ==========================================================================


@pytest.fixture
def db_path(tmp_path):
    """Cria database temporário para testes."""
    return str(tmp_path / "test_signals.db")


@pytest.fixture
def persistence(db_path):
    """Cria instância de SignalPersistence com DB temporário."""
    return SignalPersistence(db_path=db_path)


@pytest.fixture
def market_context():
    """Contexto de mercado padrão para testes."""
    return MarketContext(
        rsi=65.5,
        atr=50.0,
        bb_upper=123.750,
        bb_lower=123.150,
        volume=450,
        spread=2.0,
        trend_direction="UP",
        last_close=123.450,
    )


@pytest.fixture
def sample_signal(market_context):
    """Sinal padrão para testes."""
    return Signal(
        signal_id="test-signal-001",
        timestamp=datetime(2026, 3, 5, 14, 24, 0, 12000),
        symbol="WIN",
        signal_type=SignalType.BUY,
        smc_score=1.5,
        smc_detector=SMCDetector.BOS,
        entry_price=123.600,
        candle_index=2845,
        market_context=market_context,
        created_at=datetime(2026, 3, 5, 14, 24, 0, 12000),
    )


# ==========================================================================
# TEST SUITE
# ==========================================================================


class TestAC2SignalPersistence:
    """Testes da Camada 1 - AC2: Signal Persistence"""

    def test_ac2_insert_single_signal(self, persistence, sample_signal):
        """AC2-T1: Inserir um único sinal com contexto de mercado"""

        # Verificar que sinal está com contexto
        assert sample_signal.market_context is not None
        assert sample_signal.market_context.rsi == 65.5

        # Executar insert
        result = persistence.insert(sample_signal)

        # Verificar resultado
        assert result is True, "Insert deve retornar True"

        # Consultar DB para confirmar persistência
        conn = sqlite3.connect(persistence.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM signals WHERE signal_id = ?", (sample_signal.signal_id,))
        row = cursor.fetchone()
        conn.close()

        # Validações
        assert row is not None, "Sinal deve existir no database"
        assert row["symbol"] == "WIN"
        assert row["signal_type"] == "BUY"
        assert row["smc_score"] == 1.5
        assert row["smc_detector"] == "BOS"
        assert row["outcome_type"] == "OPEN"  # Status inicial

        # Verificar market_context_json foi salvo
        assert row["market_context_json"] is not None
        context = json.loads(row["market_context_json"])
        assert context["rsi"] == 65.5
        assert context["atr"] == 50.0
        assert context["volume"] == 450
        assert context["trend_direction"] == "UP"
        assert len(context) == 8  # Todos os 8 campos

    def test_ac2_market_context_serialization(self, persistence, market_context):
        """AC2-T2: Serializar MarketContext para JSON"""

        # Serializar
        json_str = persistence._serialize_market_context(market_context)

        # Verificar é string JSON válida
        assert isinstance(json_str, str)
        data = json.loads(json_str)

        # Validar todos os 8 campos
        assert data["rsi"] == 65.5
        assert data["atr"] == 50.0
        assert data["bb_upper"] == 123.750
        assert data["bb_lower"] == 123.150
        assert data["volume"] == 450
        assert data["spread"] == 2.0
        assert data["trend_direction"] == "UP"
        assert data["last_close"] == 123.450
        assert len(data) == 8

    def test_ac2_market_context_none(self, persistence):
        """AC2-T2b: Serializar MarketContext None"""

        # Serializar None
        json_str = persistence._serialize_market_context(None)

        # Deve retornar JSON vazio
        assert json_str == "{}"
        assert json.loads(json_str) == {}

    def test_ac2_deserialize_market_context(self, persistence):
        """AC2-T5: Desserializar JSON para MarketContext"""

        # JSON de exemplo
        json_str = json.dumps(
            {
                "rsi": 65.5,
                "atr": 50.0,
                "bb_upper": 123.750,
                "bb_lower": 123.150,
                "volume": 450,
                "spread": 2.0,
                "trend_direction": "UP",
                "last_close": 123.450,
            }
        )

        # Desserializar
        context = persistence._deserialize_market_context(json_str)

        # Validar
        assert context is not None
        assert context.rsi == 65.5
        assert context.atr == 50.0
        assert context.volume == 450
        assert context.trend_direction == "UP"

    def test_ac2_duplicate_rejection(self, persistence, sample_signal):
        """AC2-T4: Rejeitar sinais com signal_id duplicado"""

        # Inserir primeira vez - deve suceder
        result1 = persistence.insert(sample_signal)
        assert result1 is True

        # Inserir novamente - deve falhar (UNIQUE constraint)
        result2 = persistence.insert(sample_signal)
        assert result2 is False, "Segundo insert deve retornar False (duplicado)"

        # Verificar que apenas UM sinal está no DB
        conn = sqlite3.connect(persistence.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM signals WHERE signal_id = ?", (sample_signal.signal_id,))
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1, "Apenas um sinal deve estar no database"

    def test_ac2_insert_batch_signals(self, persistence, market_context):
        """AC2-T3: Inserir múltiplos sinais em batch"""

        signals = []
        for i in range(3):
            signal = Signal(
                signal_id=f"batch-signal-{i}",
                timestamp=datetime(2026, 3, 5, 14, 24 + i, i),
                symbol="WIN",
                signal_type=SignalType.BUY if i % 2 == 0 else SignalType.SELL,
                smc_score=1.5 + i * 0.5,
                smc_detector=SMCDetector.BOS,
                entry_price=123.6 + i,
                candle_index=2845 + i,
                market_context=market_context,
                created_at=datetime(2026, 3, 5, 14, 24 + i, i),
            )
            signals.append(signal)

        # Inserir todos
        for signal in signals:
            result = persistence.insert(signal)
            assert result is True, f"Todos os sinais devem ser inseridos"

        # Verificar no DB
        conn = sqlite3.connect(persistence.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM signals")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 3, "Todos os 3 sinais devem estar no database"

    def test_ac2_persistence_integration_with_generator(self, persistence, db_path):
        """AC2-T6: Integração AC1 (gerador) → AC2 (persistência)"""

        # Criar um signal via SignalGenerator (AC1)
        generator = SignalGenerator()

        # Simular M5 candle
        candles = {
            "open": 123450.0,
            "high": 123650.0,
            "low": 123250.0,
            "close": 123600.0,
            "volume": 450,
            "prev_high": 123450.0,
            "prev_low": 123200.0,
        }

        market_context = MarketContext(
            rsi=65.5,
            atr=50.0,
            bb_upper=123.750,
            bb_lower=123.150,
            volume=450,
            spread=2.0,
            trend_direction="UP",
            last_close=123.450,
        )

        # AC1: Gerar sinal
        signal = generator.detect_smc(
            candles_m5=candles,
            symbol="WIN",
            current_price=123600.0,
            market_context=market_context,
            candle_index=2845,
        )

        # Verificar sinal foi gerado
        assert signal is not None, "AC1 deve gerar sinal válido"
        assert signal.market_context is not None

        # AC2: Persistir sinal
        result = persistence.insert(signal)
        assert result is True, "AC2 deve persistir sinal com sucesso"

        # Verificar no DB
        retrieved_signal = persistence.get_signal(signal.signal_id)
        assert retrieved_signal is not None, "Sinal deve ser recuperável do DB"
        assert retrieved_signal.signal_id == signal.signal_id
        assert retrieved_signal.market_context is not None
        assert retrieved_signal.market_context.rsi == 65.5

    def test_ac2_get_signals_by_symbol(self, persistence, market_context):
        """AC2: Recuperar sinais por símbolo"""

        # Inserir 5 sinais (3 WIN, 2 WDO)
        for i in range(3):
            signal = Signal(
                signal_id=f"win-{i}",
                timestamp=datetime(2026, 3, 5, 14, 24, i),
                symbol="WIN",
                signal_type=SignalType.BUY,
                smc_score=1.5,
                smc_detector=SMCDetector.BOS,
                entry_price=123.6,
                candle_index=2845,
                market_context=market_context,
                created_at=datetime(2026, 3, 5, 14, 24, i),
            )
            persistence.insert(signal)

        for i in range(2):
            signal = Signal(
                signal_id=f"wdo-{i}",
                timestamp=datetime(2026, 3, 5, 14, 25, i),
                symbol="WDO",
                signal_type=SignalType.SELL,
                smc_score=-1.5,
                smc_detector=SMCDetector.CHOCH,
                entry_price=69000.0,
                candle_index=2846,
                market_context=market_context,
                created_at=datetime(2026, 3, 5, 14, 25, i),
            )
            persistence.insert(signal)

        # Recuperar sinais WIN
        win_signals = persistence.get_signals_by_symbol("WIN", limit=10)
        assert len(win_signals) == 3, "Deve retornar 3 sinais WIN"
        assert all(s.symbol == "WIN" for s in win_signals)
        assert all(s.market_context is not None for s in win_signals)

        # Recuperar sinais WDO
        wdo_signals = persistence.get_signals_by_symbol("WDO", limit=10)
        assert len(wdo_signals) == 2, "Deve retornar 2 sinais WDO"
        assert all(s.symbol == "WDO" for s in wdo_signals)


# ==========================================================================
# TEST EXECUTION
# ==========================================================================

if __name__ == "__main__":
    # Executar com: pytest tests/test_ac2_signal_persistence.py -v
    pytest.main([__file__, "-v"])
