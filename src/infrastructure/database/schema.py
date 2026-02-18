"""Database schema using SQLAlchemy."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Integer,
    Numeric,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

Base = declarative_base()


class MarketDataModel(Base):
    """Table for storing market tick/candle data."""

    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    open = Column(Numeric(18, 6), nullable=False)
    high = Column(Numeric(18, 6), nullable=False)
    low = Column(Numeric(18, 6), nullable=False)
    close = Column(Numeric(18, 6), nullable=False)
    volume = Column(Integer, nullable=False)
    spread = Column(Numeric(10, 6), nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class FeatureModel(Base):
    """Table for storing calculated features and indicators."""

    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    feature_name = Column(String(100), nullable=False, index=True)
    feature_value = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class PredictionModel(Base):
    """Table for storing ML model predictions."""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    model_name = Column(String(100), nullable=False, index=True)
    prediction_type = Column(String(50), nullable=False)  # classification/regression
    predicted_value = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)  # Filled later for validation
    created_at = Column(DateTime, default=datetime.now)


class DecisionModel(Base):
    """Table for storing trading decisions."""

    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    decision_type = Column(String(20), nullable=False)  # BUY/SELL/HOLD
    reasoning = Column(String(1000), nullable=True)
    signals_used = Column(JSON, nullable=True)  # JSON array of signals
    risk_assessment = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    executed = Column(Integer, default=0)  # Boolean: 0=No, 1=Yes
    created_at = Column(DateTime, default=datetime.now)


class TradeModel(Base):
    """Table for storing executed trades."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(36), nullable=False, unique=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # BUY/SELL
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Numeric(18, 6), nullable=False)
    entry_time = Column(DateTime, nullable=False, index=True)
    exit_price = Column(Numeric(18, 6), nullable=True)
    exit_time = Column(DateTime, nullable=True)
    stop_loss = Column(Numeric(18, 6), nullable=True)
    take_profit = Column(Numeric(18, 6), nullable=True)
    status = Column(String(20), nullable=False, index=True)
    broker_trade_id = Column(String(100), nullable=True)
    commission = Column(Numeric(18, 6), default=Decimal("0"))
    profit_loss = Column(Numeric(18, 6), nullable=True)
    return_percentage = Column(Float, nullable=True)
    notes = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PerformanceModel(Base):
    """Table for storing portfolio performance snapshots."""

    __tablename__ = "performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    balance = Column(Numeric(18, 2), nullable=False)
    equity = Column(Numeric(18, 2), nullable=False)
    profit_loss = Column(Numeric(18, 2), nullable=False)
    drawdown = Column(Float, nullable=False)
    win_rate = Column(Float, nullable=True)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    sharpe_ratio = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class ModelMetadataModel(Base):
    """Table for storing ML model metadata and versions."""

    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(100), nullable=False, unique=True, index=True)
    model_type = Column(String(50), nullable=False)
    version = Column(String(20), nullable=False)
    trained_at = Column(DateTime, nullable=False)
    training_metrics = Column(JSON, nullable=True)
    hyperparameters = Column(JSON, nullable=True)
    file_path = Column(String(500), nullable=False)
    is_active = Column(Integer, default=1)  # Boolean: 0=No, 1=Yes
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class MacroScoreItemModel(Base):
    """Snapshot individual de cada item analisado pelo macro score."""

    __tablename__ = "macro_score_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    item_number = Column(Integer, nullable=False)
    symbol = Column(String(30), nullable=False, index=True)
    resolved_symbol = Column(String(30), nullable=True)
    category = Column(String(50), nullable=False)
    correlation = Column(String(10), nullable=False)
    opening_price = Column(Numeric(18, 6), nullable=True)
    current_price = Column(Numeric(18, 6), nullable=True)
    score = Column(Integer, nullable=False)
    weight = Column(Numeric(10, 4), nullable=False)
    weighted_score = Column(Numeric(10, 4), nullable=False)
    status = Column(String(20), nullable=False)
    detail = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class MacroScoreDecisionModel(Base):
    """Decisao final do sistema macro score."""

    __tablename__ = "macro_score_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), nullable=False, unique=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    total_items = Column(Integer, nullable=False)
    items_available = Column(Integer, nullable=False)
    items_unavailable = Column(Integer, nullable=False)
    score_bullish = Column(Numeric(10, 4), nullable=False)
    score_bearish = Column(Numeric(10, 4), nullable=False)
    score_neutral = Column(Integer, nullable=False)
    score_final = Column(Numeric(10, 4), nullable=False)
    signal = Column(String(10), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=True)
    win_price_at_decision = Column(Numeric(18, 2), nullable=True)
    summary = Column(String(2000), nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class MacroScoreFeedbackModel(Base):
    """Feedback de aprendizado por reforco do macro score."""

    __tablename__ = "macro_score_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), nullable=False, index=True)
    timestamp_decision = Column(DateTime, nullable=False)
    signal_at_decision = Column(String(10), nullable=False)
    score_at_decision = Column(Numeric(10, 4), nullable=False)
    win_price_at_decision = Column(Numeric(18, 2), nullable=False)
    evaluation_minutes = Column(Integer, nullable=False)
    win_price_at_evaluation = Column(Numeric(18, 2), nullable=True)
    actual_direction = Column(String(10), nullable=True)
    decision_correct = Column(Integer, nullable=True)
    price_change_points = Column(Numeric(10, 2), nullable=True)
    evaluated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class SimpleMacroScoreDecisionModel(Base):
    """Decisao do modelo simplificado (-1/0/+1) por rodada."""

    __tablename__ = "simple_macro_score_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    total_items = Column(Integer, nullable=False)
    items_available = Column(Integer, nullable=False)
    total_raw = Column(Integer, nullable=False)
    signal = Column(String(10), nullable=False)
    group_scores = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class SimpleMacroScoreItemModel(Base):
    """Itens individuais do modelo simplificado por rodada."""

    __tablename__ = "simple_macro_score_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(Integer, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    item_number = Column(Integer, nullable=False)
    symbol = Column(String(30), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    final_score = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class TradingJournalLogModel(Base):
    """Persistencia do diario de mercado."""

    __tablename__ = "trading_journal_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(String(30), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    headline = Column(String(200), nullable=False)
    market_feeling = Column(String(50), nullable=False)
    detailed_narrative = Column(String(5000), nullable=False)
    decision = Column(String(10), nullable=False)
    confidence = Column(Float, nullable=False)
    reasoning = Column(String(1000), nullable=True)
    macro_bias = Column(String(10), nullable=False)
    fundamental_bias = Column(String(10), nullable=False)
    sentiment_bias = Column(String(10), nullable=False)
    technical_bias = Column(String(10), nullable=False)
    alignment_score = Column(Float, nullable=False)
    market_regime = Column(String(20), nullable=False)
    key_observations = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class AIReflectionLogModel(Base):
    """Persistencia do diario da IA."""

    __tablename__ = "ai_reflection_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    current_price = Column(Numeric(18, 6), nullable=False)
    price_change_since_open = Column(Float, nullable=False)
    price_change_last_10min = Column(Float, nullable=False)
    my_decision = Column(String(10), nullable=False)
    my_confidence = Column(Float, nullable=False)
    my_alignment = Column(Float, nullable=False)
    honest_assessment = Column(String(1000), nullable=False)
    what_im_seeing = Column(String(1000), nullable=False)
    data_relevance = Column(String(500), nullable=False)
    am_i_useful = Column(String(500), nullable=False)
    what_would_work_better = Column(String(500), nullable=False)
    human_makes_sense = Column(Integer, nullable=False)
    human_feedback = Column(String(500), nullable=False)
    what_actually_moves_price = Column(String(500), nullable=False)
    my_data_correlation = Column(String(500), nullable=False)
    mood = Column(String(50), nullable=False)
    one_liner = Column(String(500), nullable=False)
    tags = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class SimpleScoreAlignmentModel(Base):
    """Alinhamento por ciclo entre preco e score simplificado."""

    __tablename__ = "simple_score_alignment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    price = Column(Numeric(18, 6), nullable=True)
    prev_price = Column(Numeric(18, 6), nullable=True)
    price_dir = Column(Integer, nullable=False)  # -1, 0, +1
    total_raw = Column(Integer, nullable=False)
    prev_total_raw = Column(Integer, nullable=True)
    score_dir = Column(Integer, nullable=False)  # -1, 0, +1
    group_raws = Column(JSON, nullable=True)
    group_dirs = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class SimpleScoreMatrixModel(Base):
    """Snapshot da matriz de alinhamento e pesos por grupo."""

    __tablename__ = "simple_score_matrices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    matrix = Column(JSON, nullable=False)
    group_weights = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


def create_database(db_path: str = "data/db/trading.db") -> None:
    """
    Create all database tables.

    Args:
        db_path: Path to SQLite database file
    """
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    print(f"Database created at: {db_path}")


def get_session(db_path: str = "data/db/trading.db") -> Session:
    """
    Get a database session.

    Args:
        db_path: Path to SQLite database file

    Returns:
        SQLAlchemy session
    """
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


if __name__ == "__main__":
    # Create database when run directly
    create_database()
