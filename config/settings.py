"""Application configuration using Pydantic."""

from decimal import Decimal
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingConfig(BaseSettings):
    """Trading system configuration."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # MetaTrader 5 Configuration
    mt5_login: int = Field(..., description="MT5 account login")
    mt5_password: str = Field(..., description="MT5 account password")
    mt5_server: str = Field(..., description="MT5 server name")

    # Trading Parameters
    trading_symbol: str = Field(
        default="WIN$N",
        description="Symbol to trade",
    )
    max_positions: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum open positions",
    )
    risk_per_trade: Decimal = Field(
        default=Decimal("0.02"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Risk percentage per trade (0-1)",
    )
    max_drawdown: Decimal = Field(
        default=Decimal("0.15"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Maximum drawdown before pause (0-1)",
    )
    min_risk_reward: Decimal = Field(
        default=Decimal("2.0"),
        ge=Decimal("1"),
        description="Minimum risk/reward ratio",
    )

    # Database Configuration
    db_path: str = Field(
        default="data/db/trading.db",
        description="SQLite database path",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    log_path: str = Field(
        default="data/logs/",
        description="Log files directory",
    )

    # Machine Learning Configuration
    model_path: str = Field(
        default="data/models/",
        description="ML models directory",
    )
    retrain_interval: int = Field(
        default=7,
        ge=1,
        description="Model retraining interval in days",
    )

    # Macro Score Configuration
    macro_score_enabled: bool = Field(
        default=True,
        description="Habilita sistema macro score",
    )
    macro_score_neutral_threshold: Decimal = Field(
        default=Decimal("0"),
        ge=Decimal("0"),
        description="Threshold para sinal NEUTRO (score entre -threshold e +threshold)",
    )
    macro_score_confidence_min: Decimal = Field(
        default=Decimal("0.3"),
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Confianca minima para considerar sinal valido",
    )
    macro_score_candles_count: int = Field(
        default=200,
        ge=50,
        description="Quantidade de candles para indicadores tecnicos",
    )
    macro_score_indicator_timeframe: str = Field(
        default="M5",
        description="Timeframe para indicadores tecnicos (M1, M5, M15)",
    )

    # Application Configuration
    env: str = Field(
        default="development",
        description="Environment (development, production)",
    )
    debug: bool = Field(
        default=False,
        description="Debug mode",
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v_upper

    @field_validator("env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        """Validate environment."""
        valid_envs = ["development", "production"]
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v_lower

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        Path(self.log_path).mkdir(parents=True, exist_ok=True)
        Path(self.model_path).mkdir(parents=True, exist_ok=True)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.env == "development"


# Global config instance
_config: TradingConfig | None = None


def get_config() -> TradingConfig:
    """
    Get or create global configuration instance.

    Returns:
        TradingConfig instance
    """
    global _config
    if _config is None:
        _config = TradingConfig()
        _config.ensure_directories()
    return _config


def reset_config() -> None:
    """Reset global configuration (useful for testing)."""
    global _config
    _config = None
