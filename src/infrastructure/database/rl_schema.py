"""Schema colunar para Aprendizagem por Reforço (RL).

Modelo de dados otimizado para persistir TODOS os scores, cotações e
correlações a cada ciclo de análise, permitindo treinar e aprimorar
o sistema por Reinforcement Learning.

Estrutura:
    Tabelas de Dimensão (referência):
        - dim_correlation_items: Cadastro dos 85 itens correlacionados
        - dim_technical_indicators: Definição dos indicadores técnicos

    Tabelas Fato (dados de alta frequência):
        - rl_episodes: Episódio central — um registro por ciclo de decisão
        - rl_correlation_scores: Score e cotação de cada item por episódio
        - rl_indicator_values: Valor de cada indicador técnico por episódio
        - rl_analysis_biases: Viéses de cada análise por episódio
        - rl_rewards: Recompensa multi-horizonte (5m, 15m, 30m, 60m, 120m)

Filosofia:
    - Episódio = par (estado, ação)
    - Estado = vetor de scores + cotações + indicadores
    - Ação = decisão tomada (BUY/SELL/HOLD)
    - Recompensa = variação de preço após a decisão em múltiplos horizontes
    - Para RL: S(t) → A(t) → R(t+1)
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from src.infrastructure.database.schema import Base


# ============================================================
# TABELAS DE DIMENSÃO (Lookup / Referência)
# ============================================================


class DimCorrelationItemModel(Base):
    """Cadastro mestre dos itens de correlação monitorados.

    Tabela de referência com os 85 itens do macro score.
    Cada item tem um símbolo, categoria, tipo de correlação
    com o WIN e peso no cálculo.
    """

    __tablename__ = "dim_correlation_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_number = Column(Integer, nullable=False, unique=True, index=True)
    symbol = Column(String(30), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, index=True)
    correlation_type = Column(String(10), nullable=False)  # DIRETA / INVERSA
    weight = Column(Numeric(10, 4), nullable=False, default=Decimal("1.0"))
    is_futures = Column(Integer, default=0)  # 0=Não, 1=Sim
    scoring_type = Column(String(30), nullable=False)  # PRICE_VS_OPEN / TECHNICAL_INDICATOR
    indicator_config = Column(JSON, nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DimTechnicalIndicatorModel(Base):
    """Definição dos indicadores técnicos monitorados.

    Referência para indicadores como RSI, MACD, Bollinger Bands,
    VWAP, ADX, Stochastic, etc. com seus parâmetros padrão.
    """

    __tablename__ = "dim_technical_indicators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    indicator_code = Column(String(30), nullable=False, unique=True, index=True)
    indicator_name = Column(String(100), nullable=False)
    indicator_group = Column(String(50), nullable=False)  # MOMENTUM, TREND, VOLUME, VOLATILITY
    default_params = Column(JSON, nullable=True)  # {"period": 14, "overbought": 70, ...}
    value_type = Column(String(20), nullable=False)  # NUMERIC, SCORE, ENUM
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now)


# ============================================================
# TABELAS FATO (Dados de Treinamento - Alta Frequência)
# ============================================================


class RLEpisodeModel(Base):
    """Episódio central de decisão — um registro por ciclo.

    Armazena o estado agregado do mercado no momento da decisão,
    a ação tomada e metadados do ciclo. É a tabela master que
    conecta correlações, indicadores e recompensas.

    Campos de estado resumido (para queries rápidas sem JOIN):
        - win_price: preço do WIN no momento
        - macro_score_final: score macro agregado
        - micro_score: score micro (se micro agente ativo)
        - alignment_score: alinhamento geral das análises
        - confidence: confiança da decisão

    Campos de ação:
        - action: BUY, SELL, HOLD
        - urgency: IMMEDIATE, OPPORTUNISTIC, PATIENT, AVOID

    Campos de contexto:
        - source: QUANTUM (análise completa) ou MICRO_AGENT (micro tendência)
        - market_regime: TRENDING, RANGING, VOLATILE, UNCERTAIN
    """

    __tablename__ = "rl_episodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    episode_id = Column(String(36), nullable=False, unique=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    source = Column(String(20), nullable=False, index=True)  # QUANTUM / MICRO_AGENT

    # ---- ESTADO: Preços de referência ----
    win_price = Column(Numeric(18, 2), nullable=True)
    win_open_price = Column(Numeric(18, 2), nullable=True)
    win_high_of_day = Column(Numeric(18, 2), nullable=True)
    win_low_of_day = Column(Numeric(18, 2), nullable=True)
    win_price_change_pct = Column(Float, nullable=True)

    # ---- ESTADO: Scores agregados ----
    macro_score_final = Column(Numeric(10, 4), nullable=True)
    macro_score_bullish = Column(Numeric(10, 4), nullable=True)
    macro_score_bearish = Column(Numeric(10, 4), nullable=True)
    macro_score_neutral = Column(Integer, nullable=True)
    macro_items_available = Column(Integer, nullable=True)
    macro_confidence = Column(Float, nullable=True)

    micro_score = Column(Integer, nullable=True)
    micro_trend = Column(String(20), nullable=True)  # CONTINUACAO / REVERSAO / CONSOLIDACAO

    # ---- ESTADO: Alinhamento e confiança ----
    alignment_score = Column(Float, nullable=True)
    overall_confidence = Column(Float, nullable=True)

    # ---- ESTADO: VWAP ----
    vwap_value = Column(Numeric(18, 6), nullable=True)
    vwap_upper_1sigma = Column(Numeric(18, 6), nullable=True)
    vwap_lower_1sigma = Column(Numeric(18, 6), nullable=True)
    vwap_upper_2sigma = Column(Numeric(18, 6), nullable=True)
    vwap_lower_2sigma = Column(Numeric(18, 6), nullable=True)
    vwap_position = Column(String(20), nullable=True)  # ABOVE_2S, ABOVE_1S, AT_VWAP, BELOW_1S, BELOW_2S

    # ---- ESTADO: Pivots ----
    pivot_pp = Column(Numeric(18, 6), nullable=True)
    pivot_r1 = Column(Numeric(18, 6), nullable=True)
    pivot_r2 = Column(Numeric(18, 6), nullable=True)
    pivot_r3 = Column(Numeric(18, 6), nullable=True)
    pivot_s1 = Column(Numeric(18, 6), nullable=True)
    pivot_s2 = Column(Numeric(18, 6), nullable=True)
    pivot_s3 = Column(Numeric(18, 6), nullable=True)

    # ---- ESTADO: Smart Money Concepts ----
    smc_direction = Column(String(20), nullable=True)
    smc_bos_score = Column(Integer, nullable=True)
    smc_equilibrium = Column(String(20), nullable=True)  # DISCOUNT / PREMIUM / EQUILIBRIUM
    smc_equilibrium_score = Column(Integer, nullable=True)
    smc_fvg_score = Column(Integer, nullable=True)

    # ---- ESTADO: Volume ----
    volume_today = Column(Integer, nullable=True)
    volume_avg = Column(Integer, nullable=True)
    volume_variance_pct = Column(Float, nullable=True)
    volume_score = Column(Integer, nullable=True)
    obv_score = Column(Integer, nullable=True)

    # ---- ESTADO: Sentimento ----
    sentiment_intraday = Column(String(30), nullable=True)
    sentiment_momentum = Column(String(20), nullable=True)
    sentiment_volatility = Column(String(10), nullable=True)
    probability_up = Column(Float, nullable=True)
    probability_down = Column(Float, nullable=True)
    probability_neutral = Column(Float, nullable=True)
    recommended_approach = Column(String(30), nullable=True)

    # ---- ESTADO: Regime de mercado ----
    market_regime = Column(String(20), nullable=True)
    market_condition = Column(String(20), nullable=True)
    session_phase = Column(String(20), nullable=True)

    # ---- ESTADO: Candle Patterns ----
    candle_pattern_score = Column(Integer, nullable=True)
    candle_pattern_detail = Column(String(200), nullable=True)

    # ---- AÇÃO: Decisão tomada ----
    action = Column(String(10), nullable=False, index=True)  # BUY / SELL / HOLD
    urgency = Column(String(20), nullable=True)
    risk_level = Column(String(20), nullable=True)

    # ---- AÇÃO: Setup (se houver) ----
    entry_price = Column(Numeric(18, 6), nullable=True)
    stop_loss = Column(Numeric(18, 6), nullable=True)
    take_profit = Column(Numeric(18, 6), nullable=True)
    risk_reward_ratio = Column(Float, nullable=True)
    setup_type = Column(String(20), nullable=True)
    setup_quality = Column(String(20), nullable=True)

    # ---- BIASES (facilitam queries rápidas) ----
    macro_bias = Column(String(10), nullable=True)
    fundamental_bias = Column(String(10), nullable=True)
    sentiment_bias = Column(String(10), nullable=True)
    technical_bias = Column(String(10), nullable=True)

    # ---- Metadados ----
    reasoning = Column(Text, nullable=True)
    session_date = Column(String(10), nullable=True, index=True)  # YYYY-MM-DD
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("ix_rl_episodes_date_action", "session_date", "action"),
        Index("ix_rl_episodes_source_ts", "source", "timestamp"),
    )


class RLCorrelationScoreModel(Base):
    """Score e cotação de cada item de correlação por episódio.

    Tabela de fato colunar: uma linha por item por episódio.
    Exemplo: episódio X tem 85 linhas (uma para cada item do macro score).

    Para RL: estes dados compõem o vetor de estado.
    O modelo aprende quais combinações de scores/preços levam a boas decisões.
    """

    __tablename__ = "rl_correlation_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    episode_id = Column(String(36), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)

    # ---- Identificação do item ----
    item_number = Column(Integer, nullable=False, index=True)
    symbol = Column(String(30), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    correlation_type = Column(String(10), nullable=False)  # DIRETA / INVERSA

    # ---- Cotações ----
    opening_price = Column(Numeric(18, 6), nullable=True)
    current_price = Column(Numeric(18, 6), nullable=True)
    price_change_pct = Column(Float, nullable=True)  # Variação % do dia

    # ---- Scores ----
    raw_score = Column(Integer, nullable=False)  # -1, 0, +1 (antes da correlação)
    final_score = Column(Integer, nullable=False)  # -1, 0, +1 (após aplicar correlação)
    weight = Column(Numeric(10, 4), nullable=False)
    weighted_score = Column(Numeric(10, 4), nullable=False)

    # ---- Status ----
    is_available = Column(Integer, nullable=False, default=1)  # 0=sem dados, 1=disponível
    resolved_symbol = Column(String(30), nullable=True)  # Símbolo efetivo (futuros)
    detail = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("ix_rl_corr_episode_item", "episode_id", "item_number"),
        Index("ix_rl_corr_category_ts", "category", "timestamp"),
        Index("ix_rl_corr_symbol_ts", "symbol", "timestamp"),
    )


class RLIndicatorValueModel(Base):
    """Valor de cada indicador técnico por episódio.

    Tabela de fato colunar: uma linha por indicador por episódio.
    Armazena tanto o valor numérico quanto o score derivado.

    Indicadores incluem:
        - RSI, Stochastic, MACD (momentum)
        - ADX, EMA9, SMA20, SMA50 (tendência)
        - Bollinger Bands (volatilidade)
        - VWAP, Volume, OBV (volume/fluxo)
        - ATR (risco)
    """

    __tablename__ = "rl_indicator_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    episode_id = Column(String(36), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)

    # ---- Identificação ----
    indicator_code = Column(String(30), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)  # M1, M5, M15, H1, D1

    # ---- Valores ----
    value = Column(Float, nullable=True)  # Valor numérico principal
    value_secondary = Column(Float, nullable=True)  # Segundo valor (ex: MACD signal)
    value_tertiary = Column(Float, nullable=True)  # Terceiro (ex: MACD histogram)
    score = Column(Integer, nullable=True)  # Score derivado: -1, 0, +1

    # ---- Contexto ----
    signal = Column(String(20), nullable=True)  # OVERBOUGHT, OVERSOLD, BULLISH, BEARISH, NEUTRAL
    detail = Column(String(200), nullable=True)

    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("ix_rl_ind_episode_code", "episode_id", "indicator_code"),
        Index("ix_rl_ind_code_tf_ts", "indicator_code", "timeframe", "timestamp"),
    )


class RLRewardModel(Base):
    """Recompensa multi-horizonte para cada episódio.

    Após cada decisão, o sistema captura o preço do WIN em múltiplos
    horizontes de tempo para calcular a recompensa real.

    Para RL:
        - reward_points: variação em pontos (positivo = movimento na direção da ação)
        - reward_pct: variação percentual
        - was_correct: 1 se a ação estava alinhada com o movimento real

    Horizonte múltiplo permite ao RL aprender em diferentes timeframes:
        - 5min: scalping
        - 15min: day trade rápido
        - 30min: day trade médio
        - 60min: day trade longo
        - 120min: swing intraday
    """

    __tablename__ = "rl_rewards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    episode_id = Column(String(36), nullable=False, index=True)
    timestamp_decision = Column(DateTime, nullable=False)

    # ---- Preços ----
    win_price_at_decision = Column(Numeric(18, 2), nullable=False)
    action_at_decision = Column(String(10), nullable=False)  # BUY / SELL / HOLD

    # ---- Horizonte de avaliação ----
    horizon_minutes = Column(Integer, nullable=False, index=True)  # 5, 15, 30, 60, 120
    evaluated_at = Column(DateTime, nullable=True)
    win_price_at_evaluation = Column(Numeric(18, 2), nullable=True)

    # ---- Recompensa calculada ----
    price_change_points = Column(Numeric(10, 2), nullable=True)  # Em pontos WIN
    price_change_pct = Column(Float, nullable=True)  # Variação %
    reward_direction = Column(String(10), nullable=True)  # UP / DOWN / FLAT
    was_correct = Column(Integer, nullable=True)  # 0/1 — ação alinhada com direção real?

    # ---- Reward para RL ----
    # reward normalizado: +1 (acertou forte), 0 (neutro), -1 (errou forte)
    reward_normalized = Column(Float, nullable=True)
    # reward contínuo: pontos × sinal da ação (positivo=bom, negativo=ruim)
    reward_continuous = Column(Float, nullable=True)

    # ---- Contexto do mercado no horizonte ----
    max_favorable_points = Column(Numeric(10, 2), nullable=True)  # MFE
    max_adverse_points = Column(Numeric(10, 2), nullable=True)  # MAE
    volatility_in_horizon = Column(Float, nullable=True)  # ATR do período

    # ---- Status ----
    is_evaluated = Column(Integer, default=0)  # 0=pendente, 1=avaliado
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint("episode_id", "horizon_minutes", name="uq_rl_reward_episode_horizon"),
        Index("ix_rl_reward_pending", "is_evaluated", "horizon_minutes"),
        Index("ix_rl_reward_ts_horizon", "timestamp_decision", "horizon_minutes"),
    )


class RLTrainingMetricsModel(Base):
    """Métricas de treinamento e evolução do modelo RL.

    Registra a performance do modelo a cada ciclo de treinamento,
    permitindo acompanhar a evolução e detectar degradação.
    """

    __tablename__ = "rl_training_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    training_id = Column(String(36), nullable=False, unique=True, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)

    # ---- Modelo ----
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(20), nullable=False)
    algorithm = Column(String(50), nullable=False)  # DQN, PPO, A2C, SAC, etc.

    # ---- Dataset ----
    episodes_total = Column(Integer, nullable=False)
    episodes_train = Column(Integer, nullable=False)
    episodes_validation = Column(Integer, nullable=False)
    date_range_start = Column(DateTime, nullable=True)
    date_range_end = Column(DateTime, nullable=True)

    # ---- Performance ----
    avg_reward = Column(Float, nullable=True)
    cumulative_reward = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)  # % decisões corretas
    profit_factor = Column(Float, nullable=True)  # soma_ganhos / soma_perdas
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)

    # ---- Detalhes por ação ----
    buy_accuracy = Column(Float, nullable=True)
    sell_accuracy = Column(Float, nullable=True)
    hold_accuracy = Column(Float, nullable=True)

    # ---- Hiperparâmetros ----
    hyperparameters = Column(JSON, nullable=True)
    feature_importance = Column(JSON, nullable=True)

    # ---- Validação ----
    validation_reward = Column(Float, nullable=True)
    overfitting_ratio = Column(Float, nullable=True)  # train_reward / val_reward

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


# ============================================================
# VIEW / QUERY HELPERS
# ============================================================


def create_rl_tables(engine) -> None:
    """Cria todas as tabelas do modelo RL.

    Chamado pela migration ou diretamente para inicialização.
    """
    tables = [
        DimCorrelationItemModel.__table__,
        DimTechnicalIndicatorModel.__table__,
        RLEpisodeModel.__table__,
        RLCorrelationScoreModel.__table__,
        RLIndicatorValueModel.__table__,
        RLRewardModel.__table__,
        RLTrainingMetricsModel.__table__,
    ]
    Base.metadata.create_all(engine, tables=tables)
