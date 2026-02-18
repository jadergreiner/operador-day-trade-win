"""Enums de trading - define todos os tipos de enumeracao do sistema."""

from enum import Enum, auto


class OrderSide(str, Enum):
    """Lado da ordem - compra ou venda."""

    BUY = "BUY"
    SELL = "SELL"

    def __str__(self) -> str:
        return self.value


class OrderType(str, Enum):
    """Tipo de ordem."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

    def __str__(self) -> str:
        return self.value


class TradeStatus(str, Enum):
    """Status do trade."""

    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

    def __str__(self) -> str:
        return self.value


class TradeSignal(str, Enum):
    """Sinal de trading gerado pela análise."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

    def __str__(self) -> str:
        return self.value


class TimeFrame(str, Enum):
    """Timeframes suportados."""

    M1 = "M1"  # 1 minuto
    M5 = "M5"  # 5 minutos
    M15 = "M15"  # 15 minutos
    M30 = "M30"  # 30 minutos
    H1 = "H1"  # 1 hora
    H4 = "H4"  # 4 horas
    D1 = "D1"  # 1 dia

    def __str__(self) -> str:
        return self.value

    def to_minutes(self) -> int:
        """Converte timeframe para minutos."""
        mapping = {
            "M1": 1,
            "M5": 5,
            "M15": 15,
            "M30": 30,
            "H1": 60,
            "H4": 240,
            "D1": 1440,
        }
        return mapping[self.value]


class PositionStatus(str, Enum):
    """Status da posição."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PARTIAL = "PARTIAL"

    def __str__(self) -> str:
        return self.value


class RiskLevel(str, Enum):
    """Nível de risco da operação."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"

    def __str__(self) -> str:
        return self.value


class MarketCondition(str, Enum):
    """Condição de mercado identificada."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    UNKNOWN = "UNKNOWN"

    def __str__(self) -> str:
        return self.value


class ModelType(str, Enum):
    """Tipos de modelos de machine learning."""

    CLASSIFIER = "CLASSIFIER"
    REGRESSOR = "REGRESSOR"
    ENSEMBLE = "ENSEMBLE"
    DEEP_LEARNING = "DEEP_LEARNING"

    def __str__(self) -> str:
        return self.value


class DecisionReason(str, Enum):
    """Razão para a decisão de trading."""

    ML_PREDICTION = "ML_PREDICTION"
    TECHNICAL_INDICATOR = "TECHNICAL_INDICATOR"
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    MARKET_CONDITION = "MARKET_CONDITION"
    PORTFOLIO_REBALANCE = "PORTFOLIO_REBALANCE"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"

    def __str__(self) -> str:
        return self.value
