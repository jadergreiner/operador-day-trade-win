"""
Data Models para S2-6: Analytics de Intervencao Manual
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class InterventionType(Enum):
    """Tipos de intervencao manual"""
    SIGNAL_APPROVAL = "signal_approval"  # Trader aprovou sinal
    SIGNAL_REJECTION = "signal_rejection"  # Trader rejeitou sinal
    MANUAL_ENTRY = "manual_entry"  # Trader abriu posicao manual
    MANUAL_EXIT = "manual_exit"  # Trader fechou posicao manual
    PARAMETER_OVERRIDE = "parameter_override"  # Alteracao de parametros
    SYSTEM_PAUSE = "system_pause"  # Pausou o sistema
    SYSTEM_RESUME = "system_resume"  # Retomou o sistema


class SignalStatus(Enum):
    """Status de um sinal"""
    GENERATED = "generated"  # Sinal gerado
    PENDING_APPROVAL = "pending_approval"  # Aguardando aprovacao
    APPROVED = "approved"  # Aprovado pelo trader
    REJECTED = "rejected"  # Rejeitado pelo trader
    EXECUTED = "executed"  # Executado
    CANCELLED = "cancelled"  # Cancelado


@dataclass
class Signal:
    """Estrutura de sinal de trading"""
    signal_id: str
    timestamp: datetime
    timeframe: str  # M1, M5, etc
    direction: str  # BULLISH, BEARISH
    confidence_score: float  # 0.0-1.0 (S2-5 T+60 probability)
    smc_confluence_score: float  # 0.0-5.0 (S2-3 SMC confluence)
    entry_price: float
    stop_loss: float
    take_profit: float
    reward_risk_ratio: float

    status: SignalStatus = SignalStatus.GENERATED
    approved_by: Optional[str] = None
    approval_timestamp: Optional[datetime] = None
    execution_price: Optional[float] = None
    execution_timestamp: Optional[datetime] = None
    pnl_points: Optional[float] = None
    pnl_percentage: Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validacao apos inicializacao"""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(
                f"confidence_score deve estar entre 0.0 e 1.0: "
                f"{self.confidence_score}"
            )
        if not 0.0 <= self.smc_confluence_score <= 5.0:
            raise ValueError(
                f"smc_confluence_score deve estar entre 0.0 e 5.0: "
                f"{self.smc_confluence_score}"
            )
        if self.stop_loss >= self.entry_price and self.direction == "BULLISH":
            raise ValueError(
                f"stop_loss deve ser menor que entry_price para BULLISH: "
                f"SL={self.stop_loss}, Entry={self.entry_price}"
            )
        if self.take_profit <= self.entry_price and self.direction == "BULLISH":
            raise ValueError(
                f"take_profit deve ser maior que entry_price para BULLISH: "
                f"TP={self.take_profit}, Entry={self.entry_price}"
            )


@dataclass
class ManualOverride:
    """Estrutura de intervencao manual"""
    override_id: str
    timestamp: datetime
    intervention_type: InterventionType
    trader_id: str
    reason: str  # Por que fez a intervencao?

    signal_id: Optional[str] = None  # Se relacionado a um sinal
    previous_value: Optional[Any] = None  # Valor anterior (se override de param)
    new_value: Optional[Any] = None  # Novo valor

    result_impact: Optional[str] = None  # Impacto da decisao
    pnl_impact: Optional[float] = None  # P&L gerado pela intervencao

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TraderFeedback:
    """Estrutura de feedback do trader"""
    feedback_id: str
    timestamp: datetime
    trader_id: str
    signal_id: str

    feedback_type: str  # "signal_quality", "risk_level", "system_suggestion", etc
    rating: int  # 1-5 (1=very bad, 5=excellent)
    comment: str

    suggestions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Metricas de performance agregadas"""
    period_start: datetime
    period_end: datetime

    total_signals: int = 0
    approved_signals: int = 0
    rejected_signals: int = 0
    executed_signals: int = 0

    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl_points: float = 0.0
    total_pnl_brl: float = 0.0

    win_rate: float = 0.0
    avg_profit_per_trade: float = 0.0
    avg_loss_per_trade: float = 0.0
    profit_factor: float = 0.0

    manual_interventions: int = 0
    intervention_success_rate: float = 0.0

    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0

    metadata: Dict[str, Any] = field(default_factory=dict)
