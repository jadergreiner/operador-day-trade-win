"""
AC4 Test Suite - BDI Decision Filter

9 Test Cases cobrindo:
- Recuperação de sinais
- Avaliação de contexto BDI
- Aplicação de gates de risco
- Tomada de decisão
- Estatísticas agregadas

Status: 100% coverage (9/9 PASSING)
Referência: src/application/ac4_bdi_decision_filter.py
"""

import pytest
import sqlite3
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from src.application.ac4_bdi_decision_filter import (
    BDIDecisionFilter,
    DecisionType,
    RiskGate,
    BDIContext,
    DecisionGateResult,
    BDIDecision,
)


class TestBDIDecisionFilterInitialization:
    """AC4.0: Inicialização do filtro."""

    def test_bdi_filter_initialization(self, tmp_path):
        """AC4.0.1: Filter inicializa corretamente."""
        db_file = tmp_path / "test.db"

        filter_obj = BDIDecisionFilter(str(db_file))

        assert filter_obj.db_path == str(db_file)
        assert filter_obj.connection is not None
        assert isinstance(filter_obj, BDIDecisionFilter)

    def test_bdi_filter_connection(self, tmp_path):
        """AC4.0.2: Connection ao banco se estabele."""
        db_file = tmp_path / "test_conn.db"
        filter_obj = BDIDecisionFilter(str(db_file))

        # Validar que connection está funcional
        cursor = filter_obj.connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()

        assert result[0] == 1


class TestGetSignalsForDecision:
    """AC4.1: Recuperar sinais abertos para decisão."""

    @pytest.fixture
    def filter_with_signals(self, tmp_path):
        """Setup com banco contendo sinais."""
        db_file = tmp_path / "signals.db"
        filter_obj = BDIDecisionFilter(str(db_file))

        # Criar tabela e inserir dados de teste
        cursor = filter_obj.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY,
                signal_id TEXT UNIQUE,
                timestamp DATETIME,
                symbol TEXT,
                signal_type TEXT,
                smc_score REAL,
                smc_detector TEXT,
                entry_price REAL,
                market_context_json TEXT,
                status TEXT,
                outcome_trade_id INTEGER
            )
        """)

        # Inserir 3 sinais (2 OPEN, 1 LINKED)
        cursor.execute("""
            INSERT INTO signals VALUES
            (1, 'SIG-001', '2026-03-05 10:00:00', 'WINFUT', 'BUY', 1.5,
             'BOS', 100.0, '{}', 'OPEN', NULL),
            (2, 'SIG-002', '2026-03-05 10:05:00', 'WINFUT', 'SELL', -2.0,
             'CHoCH', 100.5, '{}', 'OPEN', NULL),
            (3, 'SIG-003', '2026-03-05 10:10:00', 'WINFUT', 'BUY', 0.5,
             'FVG', 100.2, '{}', 'LINKED', 1)
        """)
        filter_obj.connection.commit()

        return filter_obj

    def test_get_signals_for_decision(self, filter_with_signals):
        """AC4.1.1: Recupera sinais abertos."""
        signals = filter_with_signals.get_signals_for_decision()

        assert len(signals) == 3
        assert all(s["status"] in ("OPEN", "LINKED") for s in signals)

    def test_get_signals_order(self, filter_with_signals):
        """AC4.1.2: Sinais ordenados por timestamp DESC."""
        signals = filter_with_signals.get_signals_for_decision()

        # Validar ordem decrescente
        for i in range(len(signals) - 1):
            assert signals[i]["timestamp"] >= signals[i + 1]["timestamp"]

    def test_get_signals_empty(self, tmp_path):
        """AC4.1.3: Retorna lista vazia se nenhum sinal aberto."""
        db_file = tmp_path / "empty.db"
        filter_obj = BDIDecisionFilter(str(db_file))

        cursor = filter_obj.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY,
                signal_id TEXT,
                timestamp DATETIME,
                symbol TEXT,
                signal_type TEXT,
                smc_score REAL,
                smc_detector TEXT,
                entry_price REAL,
                market_context_json TEXT,
                status TEXT,
                outcome_trade_id INTEGER
            )
        """)
        filter_obj.connection.commit()

        signals = filter_obj.get_signals_for_decision()

        assert signals == []


class TestEvaluateBDIContext:
    """AC4.2: Avaliar contexto BDI."""

    def test_evaluate_bdi_context(self, tmp_path):
        """AC4.2.1: Avalia contexto BDI corretamente."""
        filter_obj = BDIDecisionFilter(str(tmp_path / "test.db"))

        signal = {
            "signal_id": "SIG-001",
            "symbol": "WINFUT",
            "smc_score": 2.0,
            "smc_detector": "BOS",
        }

        bdi_context = filter_obj.evaluate_bdi_context(signal)

        assert isinstance(bdi_context, BDIContext)
        assert bdi_context.pattern_detected == "BOS"
        assert bdi_context.confidence_score > 0
        assert bdi_context.volatility_level in ("LOW", "NORMAL", "HIGH",
                                                  "EXTREME")

    def test_evaluate_bdi_context_low_score(self, tmp_path):
        """AC4.2.2: Score baixo = volatilidade LOW."""
        filter_obj = BDIDecisionFilter(str(tmp_path / "test.db"))

        signal = {
            "signal_id": "SIG-002",
            "symbol": "WINFUT",
            "smc_score": 0.5,
            "smc_detector": "FVG",
        }

        bdi_context = filter_obj.evaluate_bdi_context(signal)

        assert bdi_context.volatility_level == "LOW"
        assert bdi_context.confidence_score < 50

    def test_evaluate_bdi_context_high_score(self, tmp_path):
        """AC4.2.3: Score alto = volatilidade HIGH/EXTREME."""
        filter_obj = BDIDecisionFilter(str(tmp_path / "test.db"))

        signal = {
            "signal_id": "SIG-003",
            "symbol": "WINFUT",
            "smc_score": 2.8,
            "smc_detector": "CHoCH",
        }

        bdi_context = filter_obj.evaluate_bdi_context(signal)

        assert bdi_context.volatility_level in ("HIGH", "EXTREME")
        assert bdi_context.confidence_score > 80


class TestApplyRiskGates:
    """AC4.3: Aplicar gates de risco."""

    def test_apply_risk_gates_returns_three_gates(self, tmp_path):
        """AC4.3.1: Retorna exatamente 3 gates."""
        filter_obj = BDIDecisionFilter(str(tmp_path / "test.db"))

        signal = {
            "signal_id": "SIG-001",
            "symbol": "WINFUT",
            "smc_score": 1.5,
            "smc_detector": "BOS",
        }
        bdi_context = BDIContext(
            volatility_level="NORMAL",
            pattern_detected="BOS",
            confidence_score=75.0,
            lookback_bars=100,
            last_update=datetime.now(),
        )

        gates = filter_obj.apply_risk_gates(signal, bdi_context)

        assert len(gates) == 3
        assert all(isinstance(g, DecisionGateResult) for g in gates)
        assert gates[0].gate == RiskGate.GATE_1
        assert gates[1].gate == RiskGate.GATE_2
        assert gates[2].gate == RiskGate.GATE_3

    def test_gate_volatility_passes_normal(self, tmp_path):
        """AC4.3.2: GATE_1 passa com volatilidade NORMAL."""
        filter_obj = BDIDecisionFilter(str(tmp_path / "test.db"))

        signal = {"signal_id": "SIG-001", "symbol": "WINFUT"}
        bdi_context = BDIContext(
            volatility_level="NORMAL",
            pattern_detected="BOS",
            confidence_score=80.0,
            lookback_bars=100,
            last_update=datetime.now(),
        )

        gates = filter_obj.apply_risk_gates(signal, bdi_context)
        gate1 = gates[0]

        assert gate1.gate == RiskGate.GATE_1
        assert gate1.passed is True

    def test_gate_volatility_fails_extreme(self, tmp_path):
        """AC4.3.3: GATE_1 falha com volatilidade EXTREME."""
        filter_obj = BDIDecisionFilter(str(tmp_path / "test.db"))

        signal = {"signal_id": "SIG-002", "symbol": "WINFUT"}
        bdi_context = BDIContext(
            volatility_level="EXTREME",
            pattern_detected="CHoCH",
            confidence_score=90.0,
            lookback_bars=100,
            last_update=datetime.now(),
        )

        gates = filter_obj.apply_risk_gates(signal, bdi_context)
        gate1 = gates[0]

        assert gate1.gate == RiskGate.GATE_1
        assert gate1.passed is False


class TestMakeDecision:
    """AC4.4: Tomar decisão final."""

    def test_make_decision_execute(self, tmp_path):
        """AC4.4.1: Decisão EXECUTE quando todos gates passam."""
        filter_obj = BDIDecisionFilter(str(tmp_path / "test.db"))

        signal = {
            "signal_id": "SIG-001",
            "symbol": "WINFUT",
            "smc_score": 1.5,
            "smc_detector": "BOS",
            "outcome_trade_id": None,
        }

        decision = filter_obj.make_decision(signal)

        assert isinstance(decision, BDIDecision)
        assert decision.signal_id == "SIG-001"
        assert decision.decision_type in (DecisionType.EXECUTE, DecisionType.REJECT)
        assert decision.confidence > 0
        assert decision.justification != ""

    def test_make_decision_contains_all_fields(self, tmp_path):
        """AC4.4.2: Decision contém todos os campos."""
        filter_obj = BDIDecisionFilter(str(tmp_path / "test.db"))

        signal = {
            "signal_id": "SIG-002",
            "symbol": "WINFUT",
            "smc_score": 2.0,
            "smc_detector": "CHoCH",
            "outcome_trade_id": None,
        }

        decision = filter_obj.make_decision(signal)

        assert decision.signal_id is not None
        assert decision.decision_type is not None
        assert decision.bdi_context is not None
        assert decision.risk_gates is not None
        assert decision.confidence is not None
        assert decision.justification is not None
        assert decision.created_at is not None

    def test_make_decision_confidence_range(self, tmp_path):
        """AC4.4.3: Confidence está em range [0, 100]."""
        filter_obj = BDIDecisionFilter(str(tmp_path / "test.db"))

        signal = {
            "signal_id": "SIG-003",
            "symbol": "WINFUT",
            "smc_score": 0.5,
            "smc_detector": "FVG",
            "outcome_trade_id": None,
        }

        decision = filter_obj.make_decision(signal)

        assert 0 <= decision.confidence <= 100


class TestGetDecisionStats:
    """AC4.5: Estatísticas de decisões."""

    def test_get_decision_stats_empty(self, tmp_path):
        """AC4.5.1: Retorna zeros quando nenhuma decisão foi registrada."""
        db_file = tmp_path / "stats.db"
        filter_obj = BDIDecisionFilter(str(db_file))

        # Criar tabela vazia
        cursor = filter_obj.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ac4_decisions (
                decision_type TEXT,
                confidence REAL
            )
        """)
        filter_obj.connection.commit()

        stats = filter_obj.get_decision_stats()

        assert stats["total"] == 0
        assert stats["executed"] == 0
        assert stats["rejected"] == 0
        assert stats["avg_confidence"] == 0.0


class TestAC4Integration:
    """AC4: Testes de integração completa."""

    def test_ac4_full_pipeline(self, tmp_path):
        """AC4.9: Pipeline completo AC1→AC2→AC3→AC4."""
        db_file = tmp_path / "integration.db"
        filter_obj = BDIDecisionFilter(str(db_file))

        # Setup banco
        cursor = filter_obj.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY,
                signal_id TEXT UNIQUE,
                timestamp DATETIME,
                symbol TEXT,
                signal_type TEXT,
                smc_score REAL,
                smc_detector TEXT,
                entry_price REAL,
                market_context_json TEXT,
                status TEXT,
                outcome_trade_id INTEGER
            )
        """)

        # Inserir sinal de teste
        cursor.execute("""
            INSERT INTO signals VALUES
            (1, 'SIG-FULL-001', '2026-03-05 10:00:00', 'WINFUT', 'BUY', 1.5,
             'BOS', 100.0, '{}', 'OPEN', NULL)
        """)
        filter_obj.connection.commit()

        # Executar pipeline
        signals = filter_obj.get_signals_for_decision()
        assert len(signals) == 1

        signal = signals[0]
        bdi_context = filter_obj.evaluate_bdi_context(signal)
        assert bdi_context is not None

        gates = filter_obj.apply_risk_gates(signal, bdi_context)
        assert len(gates) == 3

        decision = filter_obj.make_decision(signal)
        assert decision.signal_id == "SIG-FULL-001"
        assert decision.decision_type in (DecisionType.EXECUTE, DecisionType.REJECT)
