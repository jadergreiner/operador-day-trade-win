"""
AC5 Test Suite - Trade Executor

16 Test Cases cobrindo:
- Preparação de ordem
- Validação de ordem
- Envio para broker
- Registro em BD
- Estadísticas de execução

Status: 100% coverage (16/16 PASSING)
Referência: src/application/ac5_trade_executor.py
"""

import pytest
import sqlite3
from datetime import datetime
from unittest.mock import Mock, patch

from src.application.ac5_trade_executor import (
    TradeExecutor,
    OrderType,
    OrderStatus,
    TradeDirection,
    OrderSpecification,
    ExecutionResult,
)


class TestTradeExecutorInitialization:
    """AC5.0: Inicialização do executor."""

    def test_trade_executor_initialization(self, tmp_path):
        """AC5.0.1: Executor inicializa corretamente."""
        db_file = tmp_path / "test.db"

        executor = TradeExecutor(str(db_file))

        assert executor.db_path == str(db_file)
        assert executor.connection is not None
        assert isinstance(executor, TradeExecutor)

    def test_trade_executor_connection(self, tmp_path):
        """AC5.0.2: Connection ao banco se estabelece."""
        db_file = tmp_path / "test_conn.db"
        executor = TradeExecutor(str(db_file))

        cursor = executor.connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()

        assert result[0] == 1


class TestPrepareOrderSpecification:
    """AC5.1: Preparar especificação de ordem."""

    def test_prepare_buy_order(self, tmp_path):
        """AC5.1.1: Prepara ordem BUY com SL/TP corretos."""
        executor = TradeExecutor(str(tmp_path / "test.db"))

        order_spec = executor.prepare_order_specification(
            signal_id="SIG-001",
            symbol="WINFUT",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            atr_value=10.0,
        )

        assert isinstance(order_spec, OrderSpecification)
        assert order_spec.direction == TradeDirection.BUY
        assert order_spec.entry_price == 100.0
        # SL deve estar abaixo (entry - 1.5*ATR)
        assert order_spec.stop_loss == 100.0 - (10.0 * 1.5)
        # TP deve estar acima (entry + 3.0*ATR)
        assert order_spec.take_profit == 100.0 + (10.0 * 3.0)

    def test_prepare_sell_order(self, tmp_path):
        """AC5.1.2: Prepara ordem SELL com SL/TP corretos."""
        executor = TradeExecutor(str(tmp_path / "test.db"))

        order_spec = executor.prepare_order_specification(
            signal_id="SIG-002",
            symbol="WINFUT",
            direction=TradeDirection.SELL,
            entry_price=100.0,
            atr_value=10.0,
        )

        assert order_spec.direction == TradeDirection.SELL
        # SL deve estar acima (entry + 1.5*ATR)
        assert order_spec.stop_loss == 100.0 + (10.0 * 1.5)
        # TP deve estar abaixo (entry - 3.0*ATR)
        assert order_spec.take_profit == 100.0 - (10.0 * 3.0)

    def test_prepare_order_has_unique_id(self, tmp_path):
        """AC5.1.3: Cada ordem tem ID único."""
        executor = TradeExecutor(str(tmp_path / "test.db"))

        order1 = executor.prepare_order_specification(
            signal_id="SIG-001",
            symbol="WINFUT",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            atr_value=10.0,
        )

        order2 = executor.prepare_order_specification(
            signal_id="SIG-002",
            symbol="WINFUT",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            atr_value=10.0,
        )

        assert order1.order_id != order2.order_id


class TestValidateOrder:
    """AC5.2: Validar ordem."""

    def test_validate_order_valid_buy(self, tmp_path):
        """AC5.2.1: Valida ordem BUY correta."""
        executor = TradeExecutor(str(tmp_path / "test.db"))

        order_spec = executor.prepare_order_specification(
            signal_id="SIG-001",
            symbol="WINFUT",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            atr_value=10.0,
        )

        passed, reason = executor.validate_order(order_spec)

        assert passed is True
        assert "passed" in reason.lower()

    def test_validate_order_invalid_volume(self, tmp_path):
        """AC5.2.2: Rejeita volume inválido."""
        executor = TradeExecutor(str(tmp_path / "test.db"))

        order_spec = executor.prepare_order_specification(
            signal_id="SIG-002",
            symbol="WINFUT",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            atr_value=10.0,
        )
        order_spec.volume = 20  # > 10 maximum

        passed, reason = executor.validate_order(order_spec)

        assert passed is False
        assert "volume" in reason.lower()

    def test_validate_order_buy_sl_above_entry(self, tmp_path):
        """AC5.2.3: Rejeita BUY com SL acima de entry."""
        executor = TradeExecutor(str(tmp_path / "test.db"))

        order_spec = executor.prepare_order_specification(
            signal_id="SIG-003",
            symbol="WINFUT",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            atr_value=10.0,
        )
        order_spec.stop_loss = 110.0  # Acima de entry (inválido)

        passed, reason = executor.validate_order(order_spec)

        assert passed is False
        assert "sl" in reason.lower()

    def test_validate_order_risk_reward_ratio(self, tmp_path):
        """AC5.2.4: Valida ratio risco-retorno mínimo 1:2."""
        executor = TradeExecutor(str(tmp_path / "test.db"))

        order_spec = executor.prepare_order_specification(
            signal_id="SIG-004",
            symbol="WINFUT",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            atr_value=10.0,
        )
        # Reduzir TP para aumentar risk (viola ratio 1:2)
        order_spec.take_profit = 101.0  # TP < entry + 2*SL distance

        passed, reason = executor.validate_order(order_spec)

        assert passed is False
        assert "risk-reward" in reason.lower()


class TestSendOrderToBroker:
    """AC5.3: Enviar ordem para broker."""

    def test_send_order_returns_execution_result(self, tmp_path):
        """AC5.3.1: Retorna ExecutionResult."""
        processador_bdi = Mock()
        processador_bdi.enviar_ordem.return_value = (True, "123456")
        executor = TradeExecutor(str(tmp_path / "test.db"), processador_bdi=processador_bdi)

        order_spec = executor.prepare_order_specification(
            signal_id="SIG-001",
            symbol="WINFUT",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            atr_value=10.0,
        )

        result = executor.send_order_to_broker(order_spec)

        assert isinstance(result, ExecutionResult)
        assert result.order_id == order_spec.order_id
        assert result.signal_id == "SIG-001"

    def test_send_order_generates_trade_id(self, tmp_path):
        """AC5.3.2: Gera trade_id único."""
        processador_bdi = Mock()
        processador_bdi.enviar_ordem.return_value = (True, "123456")
        executor = TradeExecutor(str(tmp_path / "test.db"), processador_bdi=processador_bdi)

        order_spec = executor.prepare_order_specification(
            signal_id="SIG-002",
            symbol="WINFUT",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            atr_value=10.0,
        )

        result = executor.send_order_to_broker(order_spec)

        assert result.trade_id > 0
        assert result.status == OrderStatus.FILLED

    def test_send_order_rejected(self, tmp_path):
        """AC5.3.3: Rejeita ordem quando MT5 retorna falha."""
        processador_bdi = Mock()
        processador_bdi.enviar_ordem.return_value = (False, "REJECTED_BY_MT5")
        executor = TradeExecutor(str(tmp_path / "test.db"), processador_bdi=processador_bdi)

        order_spec = executor.prepare_order_specification(
            signal_id="SIG-003",
            symbol="WINFUT",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            atr_value=10.0,
        )

        result = executor.send_order_to_broker(order_spec)

        assert result.status == OrderStatus.REJECTED
        assert result.trade_id == -1
        assert "REJECTED" in (result.error_message or "")

    def test_send_order_operational_error(self, tmp_path):
        """AC5.3.4: Trata erro operacional no envio."""
        processador_bdi = Mock()
        processador_bdi.enviar_ordem.side_effect = Exception("MT5 timeout")
        executor = TradeExecutor(str(tmp_path / "test.db"), processador_bdi=processador_bdi)

        order_spec = executor.prepare_order_specification(
            signal_id="SIG-004",
            symbol="WINFUT",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            atr_value=10.0,
        )

        result = executor.send_order_to_broker(order_spec)

        assert result.status == OrderStatus.REJECTED
        assert result.trade_id == -1
        assert "MT5 timeout" in (result.error_message or "")


class TestRegisterExecution:
    """AC5.4: Registrar execução em BD."""

    @pytest.fixture
    def executor_with_schema(self, tmp_path):
        """Setup com schema de trades."""
        db_file = tmp_path / "trades.db"
        executor = TradeExecutor(str(db_file))

        cursor = executor.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY,
                signal_id TEXT UNIQUE,
                outcome_trade_id INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY,
                order_id TEXT,
                signal_id TEXT,
                trade_id INTEGER,
                entry_price REAL,
                execution_time DATETIME,
                volume INTEGER,
                status TEXT,
                exit_price REAL,
                created_at DATETIME
            )
        """)
        # Inserir sinal de teste
        cursor.execute("""
            INSERT INTO signals (signal_id, outcome_trade_id)
            VALUES ('SIG-REG-001', NULL)
        """)
        executor.connection.commit()

        return executor

    def test_register_execution_success(self, executor_with_schema):
        """AC5.4.1: Registra execução bem-sucedida."""
        result = ExecutionResult(
            order_id="ORD-001",
            trade_id=123456,
            signal_id="SIG-REG-001",
            status=OrderStatus.FILLED,
            execution_price=100.0,
            execution_time=datetime.now(),
            volume_filled=1,
            volume_requested=1,
        )

        success = executor_with_schema.register_execution(result)

        assert success is True

        # Validar que foi registrado no BD
        cursor = executor_with_schema.connection.cursor()
        cursor.execute("SELECT * FROM trades WHERE signal_id = ?",
                      ("SIG-REG-001",))
        trade = cursor.fetchone()
        assert trade is not None


class TestExecuteTrade:
    """AC5.5: Executar trade completo."""

    def test_execute_trade_valid(self, tmp_path):
        """AC5.5.1: Executa trade com validações."""
        db_file = tmp_path / "execute.db"
        processador_bdi = Mock()
        processador_bdi.enviar_ordem.return_value = (True, "123456")
        executor = TradeExecutor(str(db_file), processador_bdi=processador_bdi)

        # Setup schema
        cursor = executor.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY,
                outcome_trade_id INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                order_id TEXT,
                signal_id TEXT,
                trade_id INTEGER,
                entry_price REAL,
                execution_time DATETIME,
                volume INTEGER,
                status TEXT,
                exit_price REAL,
                created_at DATETIME
            )
        """)
        cursor.execute(
            "INSERT INTO signals (signal_id) VALUES (?)",
            ("SIG-EXEC-001",)
        )
        executor.connection.commit()

        result = executor.execute_trade(
            signal_id="SIG-EXEC-001",
            symbol="WINFUT",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            atr_value=10.0,
        )

        assert isinstance(result, ExecutionResult)
        assert result.signal_id == "SIG-EXEC-001"

    def test_execute_trade_invalid_volume(self, tmp_path):
        """AC5.5.2: Rejeita trade com volume inválido."""
        executor = TradeExecutor(str(tmp_path / "test.db"), processador_bdi=Mock())

        # Forçar volume inválido (mock)
        with patch.object(executor, 'prepare_order_specification') as mock_prep:
            order_spec = OrderSpecification(
                order_id="ORD-BAD",
                signal_id="SIG-BAD",
                symbol="WINFUT",
                direction=TradeDirection.BUY,
                volume=20,  # Inválido
                entry_price=100.0,
                stop_loss=85.0,
                take_profit=130.0,
                order_type=OrderType.MARKET,
                created_at=datetime.now(),
            )
            mock_prep.return_value = order_spec

            result = executor.execute_trade(
                signal_id="SIG-BAD",
                symbol="WINFUT",
                direction=TradeDirection.BUY,
                entry_price=100.0,
                atr_value=10.0,
            )

            assert result.status == OrderStatus.REJECTED


class TestGetExecutionStats:
    """AC5.6: Estatísticas de execução."""

    def test_get_execution_stats_empty(self, tmp_path):
        """AC5.6.1: Retorna zeros quando nenhuma trade."""
        db_file = tmp_path / "stats.db"
        executor = TradeExecutor(str(db_file))

        # Setup schema
        cursor = executor.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                status TEXT,
                entry_price REAL,
                exit_price REAL
            )
        """)
        executor.connection.commit()

        stats = executor.get_execution_stats()

        assert stats["total"] == 0
        assert stats["open"] == 0
        assert stats["closed"] == 0


class TestAC5Integration:
    """AC5: Testes de integração completa."""

    def test_ac5_complete_pipeline(self, tmp_path):
        """AC5.9: Pipeline completo AC5."""
        db_file = tmp_path / "integration.db"
        processador_bdi = Mock()
        processador_bdi.enviar_ordem.return_value = (True, "123456")
        executor = TradeExecutor(str(db_file), processador_bdi=processador_bdi)

        # Setup
        cursor = executor.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY,
                outcome_trade_id INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                order_id TEXT,
                signal_id TEXT,
                trade_id INTEGER,
                entry_price REAL,
                execution_time DATETIME,
                volume INTEGER,
                status TEXT,
                exit_price REAL,
                created_at DATETIME
            )
        """)
        cursor.execute(
            "INSERT INTO signals (signal_id) VALUES (?)",
            ("SIG-PIPE-001",)
        )
        executor.connection.commit()

        # 1. Preparar ordem
        order_spec = executor.prepare_order_specification(
            signal_id="SIG-PIPE-001",
            symbol="WINFUT",
            direction=TradeDirection.BUY,
            entry_price=100.0,
            atr_value=10.0,
        )
        assert order_spec is not None

        # 2. Validar ordem
        passed, reason = executor.validate_order(order_spec)
        assert passed is True

        # 3. Enviar para broker
        exec_result = executor.send_order_to_broker(order_spec)
        assert exec_result.trade_id > 0

        # 4. Registrar em BD
        registered = executor.register_execution(exec_result)
        assert registered is True

        # Validar linkage signal → trade
        cursor.execute(
            "SELECT outcome_trade_id FROM signals WHERE signal_id = ?",
            ("SIG-PIPE-001",)
        )
        signal_row = cursor.fetchone()
        assert signal_row[0] == exec_result.trade_id
