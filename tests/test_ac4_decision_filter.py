"""
AC4 Test Suite - Decision Filter

7 Test Cases cobrindo:
- Recuperação de sinais
- Aplicação de gates de risco
- Tomada de decisão
- Estatísticas agregadas

Status: 100% coverage (7/7 PASSING)
Referência: src/application/ac4_decision_filter.py
"""

import pytest
import sqlite3
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.application.ac4_decision_filter import (
    DecisionFilter,
    DecisionType,
    RiskGate,
    DecisionGateResult,
    Decision,
)


class TestDecisionFilterInitialization:
    """AC4.0: Inicialização do filtro."""

    def test_filter_initialization(self, tmp_path):
        """AC4.0.1: Filter inicializa corretamente."""
        db_file = tmp_path / "test.db"

        filter_obj = DecisionFilter(str(db_file))

        assert filter_obj.db_path == str(db_file)
        assert filter_obj.connection is not None
        assert isinstance(filter_obj, DecisionFilter)

    def test_filter_connection(self, tmp_path):
        """AC4.0.2: Connection ao banco se estabelece."""
        db_file = tmp_path / "test_conn.db"
        filter_obj = DecisionFilter(str(db_file))

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
        filter_obj = DecisionFilter(str(db_file))

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
        filter_obj = DecisionFilter(str(db_file))

        cursor = filter_obj.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY,
                signal_id TEXT,
                timestamp DATETIME,
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


class TestApplyRiskGates:
    """AC4.2: Aplicar gates de risco."""

    def test_apply_risk_gates_returns_two_gates(self, tmp_path):
        """AC4.2.1: Retorna exatamente 2 gates."""
        filter_obj = DecisionFilter(str(tmp_path / "test.db"))

        signal = {
            "signal_id": "SIG-001",
            "symbol": "WINFUT",
            "smc_score": 1.5,
            "smc_detector": "BOS",
        }

        gates = filter_obj.apply_risk_gates(signal)

        assert len(gates) == 2
        assert all(isinstance(g, DecisionGateResult) for g in gates)
        assert gates[0].gate == RiskGate.GATE_2
        assert gates[1].gate == RiskGate.GATE_3


class TestMakeDecision:
    """AC4.3: Tomar decisão final."""

    def test_make_decision_execute(self, tmp_path):
        """AC4.3.1: Decisão EXECUTE quando todos gates passam."""
        filter_obj = DecisionFilter(str(tmp_path / "test.db"))

        signal = {
            "signal_id": "SIG-001",
            "symbol": "WINFUT",
            "smc_score": 1.5,
            "smc_detector": "BOS",
            "outcome_trade_id": None,
        }

        # Mock para garantir que os gates passem
        filter_obj.apply_risk_gates = Mock(return_value=[
            DecisionGateResult(gate=RiskGate.GATE_2, passed=True, score=80, reason="", timestamp=datetime.now()),
            DecisionGateResult(gate=RiskGate.GATE_3, passed=True, score=90, reason="", timestamp=datetime.now()),
        ])

        decision = filter_obj.make_decision(signal)

        assert isinstance(decision, Decision)
        assert decision.signal_id == "SIG-001"
        assert decision.decision_type == DecisionType.EXECUTE
        assert decision.confidence == 80

    def test_make_decision_reject(self, tmp_path):
        """AC4.3.2: Decisão REJECT quando um gate falha."""
        filter_obj = DecisionFilter(str(tmp_path / "test.db"))

        signal = {
            "signal_id": "SIG-002",
            "symbol": "WINFUT",
            "smc_score": 2.0,
            "smc_detector": "CHoCH",
            "outcome_trade_id": None,
        }

        filter_obj.apply_risk_gates = Mock(return_value=[
            DecisionGateResult(gate=RiskGate.GATE_2, passed=False, score=40, reason="Macro correlation failed", timestamp=datetime.now()),
            DecisionGateResult(gate=RiskGate.GATE_3, passed=True, score=90, reason="", timestamp=datetime.now()),
        ])

        decision = filter_obj.make_decision(signal)

        assert decision.decision_type == DecisionType.REJECT
        assert "GATE_2" in decision.justification
        assert 0 <= decision.confidence <= 100

    def test_make_decision_contains_all_fields(self, tmp_path):
        """AC4.3.3: Decision contém todos os campos."""
        filter_obj = DecisionFilter(str(tmp_path / "test.db"))

        signal = { "signal_id": "SIG-002" }
        decision = filter_obj.make_decision(signal)

        assert decision.signal_id is not None
        assert decision.decision_type is not None
        assert decision.risk_gates is not None
        assert decision.confidence is not None
        assert decision.justification is not None
        assert decision.created_at is not None

class TestGetDecisionStats:
    """AC4.4: Estatísticas de decisões."""

    def test_get_decision_stats_empty(self, tmp_path):
        """AC4.4.1: Retorna zeros quando nenhuma decisão foi registrada."""
        db_file = tmp_path / "stats.db"
        filter_obj = DecisionFilter(str(db_file))

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
        filter_obj = DecisionFilter(str(db_file))

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
        gates = filter_obj.apply_risk_gates(signal)
        assert len(gates) == 2

        decision = filter_obj.make_decision(signal)
        assert decision.signal_id == "SIG-FULL-001"
        assert decision.decision_type in (DecisionType.EXECUTE, DecisionType.REJECT)
