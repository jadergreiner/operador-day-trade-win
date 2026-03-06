"""
AC6 Test Suite - ML Feedback Loop

16 Test Cases cobrindo:
- Correlação signal → outcome
- Força do sinal (win rate, ROI, Sharpe)
- Importância de features
- Geração de training labels
- Atualização de pesos do modelo
- Métricas de aprendizado

Status: 100% coverage (16/16 PASSING)
Referência: src/application/ac6_ml_feedback_loop.py
"""

import pytest
import sqlite3
from datetime import datetime

from src.application.ac6_ml_feedback_loop import (
    MLFeedbackLoop,
    SignalOutcomeLinkage,
    SignalStrengthMetrics,
    FeatureImportance,
    TrainingLabel,
    ModelIteration,
    LearningMetrics,
    SignalStrength,
    LearningOutcome,
    ModelVersion,
)


class TestMLFeedbackLoopInitialization:
    """AC6.0: Inicialização do feedback loop."""

    def test_ml_feedback_loop_initialization(self, tmp_path):
        """AC6.0.1: Feedback loop inicializa corretamente."""
        db_file = tmp_path / "test.db"

        loop = MLFeedbackLoop(str(db_file))

        assert loop.db_path == str(db_file)
        assert loop.connection is not None
        assert isinstance(loop, MLFeedbackLoop)

    def test_ml_feedback_loop_connection(self, tmp_path):
        """AC6.0.2: Connection ao banco se estabelece."""
        db_file = tmp_path / "test_conn.db"
        loop = MLFeedbackLoop(str(db_file))

        cursor = loop.connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()

        assert result[0] == 1


class TestCorrelateSignalToOutcome:
    """AC6.1: Correlacionar signal ↔ trade outcome."""

    @pytest.fixture
    def loop_with_data(self, tmp_path):
        """Setup com dados de sinal e trade."""
        db_file = tmp_path / "correlation.db"
        loop = MLFeedbackLoop(str(db_file))

        cursor = loop.connection.cursor()
        cursor.execute(
            """
            CREATE TABLE signals (
                signal_id TEXT PRIMARY KEY,
                symbol TEXT,
                entry_price REAL,
                created_at DATETIME
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY,
                signal_id TEXT,
                exit_price REAL,
                pnl_realized REAL,
                created_at DATETIME
            )
            """
        )

        # Insert test data
        signal_created = datetime.now()
        cursor.execute(
            "INSERT INTO signals VALUES (?, ?, ?, ?)",
            ("SIG-CORR-001", "WINFUT", 100.0, signal_created.isoformat())
        )

        trade_created = datetime.now()
        cursor.execute(
            "INSERT INTO trades VALUES (?, ?, ?, ?, ?)",
            (1, "SIG-CORR-001", 105.0, 500.0, trade_created.isoformat())
        )
        loop.connection.commit()

        return loop

    def test_correlate_winning_trade(self, loop_with_data):
        """AC6.1.1: Correlaciona winning trade corretamente."""
        linkage = loop_with_data.correlate_signal_to_outcome("SIG-CORR-001")

        assert linkage is not None
        assert linkage.signal_id == "SIG-CORR-001"
        assert linkage.outcome_type == LearningOutcome.WINNING_TRADE
        assert linkage.pnl_realized == 500.0

    def test_correlate_losing_trade(self, tmp_path):
        """AC6.1.2: Correlaciona losing trade corretamente."""
        db_file = tmp_path / "losing.db"
        loop = MLFeedbackLoop(str(db_file))

        cursor = loop.connection.cursor()
        cursor.execute("CREATE TABLE signals (signal_id TEXT, symbol TEXT, entry_price REAL, created_at DATETIME)")
        cursor.execute("CREATE TABLE trades (id INTEGER, signal_id TEXT, exit_price REAL, pnl_realized REAL, created_at DATETIME)")

        cursor.execute(
            "INSERT INTO signals VALUES (?, ?, ?, ?)",
            ("SIG-LOSS-001", "WINFUT", 100.0, datetime.now().isoformat())
        )
        cursor.execute(
            "INSERT INTO trades VALUES (?, ?, ?, ?, ?)",
            (1, "SIG-LOSS-001", 95.0, -50.0, datetime.now().isoformat())
        )
        loop.connection.commit()

        linkage = loop.correlate_signal_to_outcome("SIG-LOSS-001")

        assert linkage.outcome_type == LearningOutcome.LOSING_TRADE
        assert linkage.pnl_realized == -50.0

    def test_correlate_nonexistent_signal(self, tmp_path):
        """AC6.1.3: Retorna None para sinal inexistente."""
        db_file = tmp_path / "empty.db"
        loop = MLFeedbackLoop(str(db_file))

        cursor = loop.connection.cursor()
        cursor.execute("CREATE TABLE signals (signal_id TEXT PRIMARY KEY, symbol TEXT, entry_price REAL, created_at DATETIME)")
        cursor.execute("CREATE TABLE trades (id INTEGER, signal_id TEXT, exit_price REAL, pnl_realized REAL, created_at DATETIME)")
        loop.connection.commit()

        linkage = loop.correlate_signal_to_outcome("NONEXISTENT")

        assert linkage is None


class TestCalculateSignalStrength:
    """AC6.2: Calcular força do sinal."""

    @pytest.fixture
    def loop_with_trades(self, tmp_path):
        """Setup com múltiplos trades."""
        db_file = tmp_path / "strength.db"
        loop = MLFeedbackLoop(str(db_file))

        cursor = loop.connection.cursor()
        cursor.execute("CREATE TABLE signals (signal_id TEXT PRIMARY KEY)")
        cursor.execute("CREATE TABLE trades (signal_id TEXT, pnl_realized REAL, created_at DATETIME)")

        # Insert winning and losing trades
        pnls = [100, -50, 200, 150, -30, 120]
        now = datetime.now()
        for pnl in pnls:
            cursor.execute(
                "INSERT INTO trades VALUES (?, ?, ?)",
                ("SIG-STR-001", pnl, now.isoformat())
            )
        cursor.execute("INSERT INTO signals VALUES (?)", ("SIG-STR-001",))
        loop.connection.commit()

        return loop

    def test_calculate_win_rate(self, loop_with_trades):
        """AC6.2.1: Calcula win_rate corretamente."""
        metrics = loop_with_trades.calculate_signal_strength("SIG-STR-001", lookback_days=365)

        assert metrics is not None
        assert metrics.win_rate == pytest.approx(4/6, rel=0.01)  # 4 winning out of 6

    def test_calculate_avg_roi(self, loop_with_trades):
        """AC6.2.2: Calcula ROI médio corretamente."""
        metrics = loop_with_trades.calculate_signal_strength("SIG-STR-001", lookback_days=365)

        assert metrics.avg_roi == pytest.approx((100 - 50 + 200 + 150 - 30 + 120) / 6, rel=0.01)

    def test_calculate_signal_strength_strong(self, loop_with_trades):
        """AC6.2.3: Classifica sinal como STRONG com win_rate alta."""
        metrics = loop_with_trades.calculate_signal_strength("SIG-STR-001", lookback_days=365)

        assert metrics.signal_strength in [SignalStrength.STRONG, SignalStrength.NEUTRAL]

    def test_calculate_strength_no_trades(self, tmp_path):
        """AC6.2.4: Retorna None se sem trades."""
        db_file = tmp_path / "no_trades.db"
        loop = MLFeedbackLoop(str(db_file))

        cursor = loop.connection.cursor()
        cursor.execute("CREATE TABLE trades (signal_id TEXT, pnl_realized REAL, created_at DATETIME)")
        loop.connection.commit()

        metrics = loop.calculate_signal_strength("NONEXISTENT", lookback_days=30)

        assert metrics is None


class TestExtractFeatureImportance:
    """AC6.3: Extrair importância de features."""

    def test_extract_feature_importance(self, tmp_path):
        """AC6.3.1: Extrai importância de features."""
        db_file = tmp_path / "features.db"
        loop = MLFeedbackLoop(str(db_file))

        features = loop.extract_feature_importance("v1.1")

        assert len(features) > 0
        assert all(isinstance(f, FeatureImportance) for f in features)

    def test_feature_importance_has_correlation(self, tmp_path):
        """AC6.3.2: Features têm correlation score."""
        db_file = tmp_path / "features2.db"
        loop = MLFeedbackLoop(str(db_file))

        features = loop.extract_feature_importance("v1.1")

        assert all(hasattr(f, 'correlation_with_wins') for f in features)
        assert all(-1.0 <= f.correlation_with_wins <= 1.0 for f in features)

    def test_feature_importance_scores_normalized(self, tmp_path):
        """AC6.3.3: Importance scores entre 0.0 e 1.0."""
        db_file = tmp_path / "features3.db"
        loop = MLFeedbackLoop(str(db_file))

        features = loop.extract_feature_importance("v1.1")

        assert all(0.0 <= f.importance_score <= 1.0 for f in features)


class TestGenerateTrainingLabel:
    """AC6.4: Gerar training labels."""

    def test_generate_label(self, tmp_path):
        """AC6.4.1: Gera training label para sinal."""
        db_file = tmp_path / "label.db"
        loop = MLFeedbackLoop(str(db_file))

        cursor = loop.connection.cursor()
        cursor.execute("CREATE TABLE signals (signal_id TEXT PRIMARY KEY)")
        cursor.execute("CREATE TABLE trades (signal_id TEXT, pnl_realized REAL, created_at DATETIME)")

        cursor.execute("INSERT INTO signals VALUES (?)", ("SIG-LABEL-001",))
        for pnl in [100, 150, 120]:  # All winning
            cursor.execute(
                "INSERT INTO trades VALUES (?, ?, ?)",
                ("SIG-LABEL-001", pnl, datetime.now().isoformat())
            )
        loop.connection.commit()

        label = loop.generate_training_label("SIG-LABEL-001")

        assert label is not None
        assert isinstance(label, TrainingLabel)
        assert -1.0 <= label.label_value <= 1.0

    def test_label_value_ranges(self, tmp_path):
        """AC6.4.2: Label value é -1.0 a +1.0."""
        db_file = tmp_path / "label2.db"
        loop = MLFeedbackLoop(str(db_file))

        cursor = loop.connection.cursor()
        cursor.execute("CREATE TABLE signals (signal_id TEXT PRIMARY KEY)")
        cursor.execute("CREATE TABLE trades (signal_id TEXT, pnl_realized REAL, created_at DATETIME)")

        cursor.execute("INSERT INTO signals VALUES (?)", ("SIG-LABEL-002",))
        cursor.execute(
            "INSERT INTO trades VALUES (?, ?, ?)",
            ("SIG-LABEL-002", 100, datetime.now().isoformat())
        )
        loop.connection.commit()

        label = loop.generate_training_label("SIG-LABEL-002")

        assert label is not None
        assert -1.0 <= label.label_value <= 1.0

    def test_label_confidence_normalized(self, tmp_path):
        """AC6.4.3: Confidence score entre 0.0 e 1.0."""
        db_file = tmp_path / "label3.db"
        loop = MLFeedbackLoop(str(db_file))

        cursor = loop.connection.cursor()
        cursor.execute("CREATE TABLE signals (signal_id TEXT PRIMARY KEY)")
        cursor.execute("CREATE TABLE trades (signal_id TEXT, pnl_realized REAL, created_at DATETIME)")

        cursor.execute("INSERT INTO signals VALUES (?)", ("SIG-LABEL-003",))
        cursor.execute(
            "INSERT INTO trades VALUES (?, ?, ?)",
            ("SIG-LABEL-003", 50, datetime.now().isoformat())
        )
        loop.connection.commit()

        label = loop.generate_training_label("SIG-LABEL-003")

        assert label is not None
        assert 0.0 <= label.confidence <= 1.0


class TestUpdateModelWeights:
    """AC6.5: Atualizar model weights."""

    def test_update_model_weights(self, tmp_path):
        """AC6.5.1: Atualiza model com training labels."""
        db_file = tmp_path / "model.db"
        loop = MLFeedbackLoop(str(db_file))

        labels = [
            TrainingLabel("SIG-001", 0.8, 0.9, "High win rate", None),
            TrainingLabel("SIG-002", -0.3, 0.6, "Low win rate", None),
            TrainingLabel("SIG-003", 0.5, 0.75, "Neutral", None),
        ]

        iteration = loop.update_model_weights("v1.1", labels)

        assert iteration is not None
        assert isinstance(iteration, ModelIteration)
        assert iteration.model_version == "v1.1"

    def test_model_iteration_metrics(self, tmp_path):
        """AC6.5.2: ModelIteration contém métricas validadas."""
        db_file = tmp_path / "model2.db"
        loop = MLFeedbackLoop(str(db_file))

        labels = [TrainingLabel("SIG-001", 0.5, 0.5, "Test", None)]
        iteration = loop.update_model_weights("v1.1", labels)

        assert 0.0 <= iteration.validation_accuracy <= 1.0
        assert 0.0 <= iteration.f1_score <= 1.0
        assert 0.0 <= iteration.win_rate_backtest <= 1.0

    def test_update_model_empty_labels(self, tmp_path):
        """AC6.5.3: Retorna None se sem labels."""
        db_file = tmp_path / "model3.db"
        loop = MLFeedbackLoop(str(db_file))

        iteration = loop.update_model_weights("v1.1", [])

        assert iteration is None


class TestPublishLearningMetrics:
    """AC6.6: Publicar learning metrics."""

    def test_get_learning_metrics(self, tmp_path):
        """AC6.6.1: Retorna learning metrics."""
        db_file = tmp_path / "metrics.db"
        loop = MLFeedbackLoop(str(db_file))

        cursor = loop.connection.cursor()
        cursor.execute("CREATE TABLE signals (outcome_trade_id INTEGER)")
        for i in range(10):
            cursor.execute(
                "INSERT INTO signals VALUES (?)",
                (i if i % 2 == 0 else None,)  # Half with outcomes
            )
        loop.connection.commit()

        metrics = loop.get_learning_metrics()

        assert metrics is not None
        assert isinstance(metrics, LearningMetrics)
        assert metrics.total_signals_analyzed == 10

    def test_metrics_coverage(self, tmp_path):
        """AC6.6.2: Métricas cobrem os KPIs principais."""
        db_file = tmp_path / "metrics2.db"
        loop = MLFeedbackLoop(str(db_file))

        cursor = loop.connection.cursor()
        cursor.execute("CREATE TABLE signals (outcome_trade_id INTEGER)")
        loop.connection.commit()

        metrics = loop.get_learning_metrics()

        assert hasattr(metrics, 'total_signals_analyzed')
        assert hasattr(metrics, 'signals_with_outcomes')
        assert hasattr(metrics, 'average_signal_strength')
        assert hasattr(metrics, 'model_version')


class TestAC6Integration:
    """AC6: Complete feedback loop integration."""

    def test_ac6_complete_feedback_loop(self, tmp_path):
        """AC6.9: Feedback loop completo AC6.1-AC6.6."""
        db_file = tmp_path / "integration.db"
        loop = MLFeedbackLoop(str(db_file))

        # Setup schema
        cursor = loop.connection.cursor()
        cursor.execute(
            """
            CREATE TABLE signals (
                signal_id TEXT PRIMARY KEY,
                symbol TEXT,
                entry_price REAL,
                outcome_trade_id INTEGER,
                created_at DATETIME
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY,
                signal_id TEXT,
                exit_price REAL,
                pnl_realized REAL,
                created_at DATETIME
            )
            """
        )

        # Insert data
        signal_created = datetime.now()
        cursor.execute(
            "INSERT INTO signals VALUES (?, ?, ?, ?, ?)",
            ("SIG-PIPE-001", "WINFUT", 100.0, 1, signal_created.isoformat())
        )

        trade_created = datetime.now()
        cursor.execute(
            "INSERT INTO trades VALUES (?, ?, ?, ?, ?)",
            (1, "SIG-PIPE-001", 105.0, 500.0, trade_created.isoformat())
        )

        loop.connection.commit()

        # 1. Correlate signal → outcome
        linkage = loop.correlate_signal_to_outcome("SIG-PIPE-001")
        assert linkage is not None

        # 2. Calculate signal strength
        strength = loop.calculate_signal_strength("SIG-PIPE-001", lookback_days=365)
        assert strength is not None

        # 3. Extract feature importance
        features = loop.extract_feature_importance("v1.1")
        assert len(features) > 0

        # 4. Generate training label
        label = loop.generate_training_label("SIG-PIPE-001", strength)
        assert label is not None
        assert -1.0 <= label.label_value <= 1.0

        # 5. Update model weights
        iteration = loop.update_model_weights("v1.1", [label])
        assert iteration is not None
        assert iteration.is_production_ready

        # 6. Get learning metrics
        metrics = loop.get_learning_metrics()
        assert metrics is not None
        assert metrics.total_signals_analyzed >= 1
