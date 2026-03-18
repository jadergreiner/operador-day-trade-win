"""Application configuration using Pydantic."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MT5Config(BaseSettings):
    """ADR-016: Terminal fallback configuration with explicit validation.

    Responsável por:
    - Validar que we conectamos ao terminal correto (CLEAR, não FBS/XP/etc)
    - Permitir fallback determinístico para terminais alternativos se configurado
    - Registrar decisões de terminal em SQLite para auditoria 7-ano
    """

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    terminal_primary: str = Field(
        default="Clear Investimentos",
        description="Terminal primário esperado (sem fallback permitido)",
    )

    terminal_fallback_enabled: bool = Field(
        default=True,
        description="Habilitar fallback para terminais alternativos (ADR-016)",
    )

    terminal_fallback_list: list[str] = Field(
        default_factory=lambda: ["FBS", "XP Investimentos", "Zero", "IC Markets"],
        description="Lista de brokers aceitos como fallback (JSON array no .env)",
    )

    terminal_fallback_action: Literal["LOG_WARN_CONTINUE", "REJECT_ERROR"] = Field(
        default="LOG_WARN_CONTINUE",
        description="Ação ao detectar fallback: LOG_WARN_CONTINUE ou REJECT_ERROR",
    )

    @field_validator("terminal_primary")
    @classmethod
    def validate_terminal_primary(cls, v: str) -> str:
        """Terminal primário não pode ser vazio."""
        if not v or len(v.strip()) == 0:
            raise ValueError("terminal_primary não pode ser vazio")
        return v.strip()

    @field_validator("terminal_fallback_list", mode="before")
    @classmethod
    def validate_terminal_fallback_list(cls, v: str | list[str]) -> list[str]:
        """Parse terminal fallback list (pode ser JSON string ou já lista)."""
        if isinstance(v, str):
            try:
                # Tentar parsear JSON válido
                parsed = json.loads(v)
                if not isinstance(parsed, list) or len(parsed) == 0:
                    raise ValueError("terminal_fallback_list deve ser uma lista não-vazia")
                return parsed
            except json.JSONDecodeError as e:
                raise ValueError(f"terminal_fallback_list JSON inválido: {e}")
        elif isinstance(v, list):
            if len(v) == 0:
                raise ValueError("terminal_fallback_list não pode ser vazia")
            return v
        else:
            raise ValueError(f"terminal_fallback_list deve ser JSON array ou lista Python, recebido {type(v)}")

    def is_terminal_accepted(self, detected_terminal: str) -> bool:
        """Verificar se terminal detectado é aceito (primário ou fallback).

        Args:
            detected_terminal: Nome do terminal detectado (ex: "FBS MetaTrader 5")

        Returns:
            True se terminal é primário ou está em fallback_list (se habilitado)
            False se terminal não é aceito
        """
        if detected_terminal == self.terminal_primary:
            return True

        if self.terminal_fallback_enabled and detected_terminal in self.terminal_fallback_list:
            return True

        return False

    def should_log_fallback(self, detected_terminal: str) -> bool:
        """Verificar se deve log WARNING ao detectar fallback.

        Returns:
            True se foi detectado fallback (detected != primary) mas é aceito
        """
        return (
            detected_terminal != self.terminal_primary
            and self.is_terminal_accepted(detected_terminal)
        )


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
    mt5_terminal_path: Optional[str] = Field(
        default=None,
        description="(OPTIONAL) Exact path to terminal64.exe (S2-5 Terminal Isolation) — "
                    "If not set, MT5 will auto-detect the terminal. "
                    "Specify this to prevent accidental connection to different MT5 terminals (FBS, XP, etc)"
    )

    # ── ADR-016: Terminal Fallback Configuration ────────────────────────
    mt5_terminal_primary: str = Field(
        default="Clear Investimentos",
        description="Terminal primário esperado (ADR-016)",
    )

    mt5_terminal_fallback_enabled: bool = Field(
        default=True,
        description="Habilitar fallback para terminais alternativos (ADR-016)",
    )

    mt5_terminal_fallback_list: list[str] = Field(
        default_factory=lambda: ["FBS", "XP Investimentos", "Zero", "IC Markets"],
        description="Lista de brokers aceitos como fallback (ADR-016)",
    )

    mt5_terminal_fallback_action: Literal["LOG_WARN_CONTINUE", "REJECT_ERROR"] = Field(
        default="LOG_WARN_CONTINUE",
        description="Ação ao detectar fallback (ADR-016)",
    )
    # ────────────────────────────────────────────────────────────────────

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

    @field_validator("mt5_terminal_path")
    @classmethod
    def validate_mt5_terminal_path(cls, v: Optional[str]) -> Optional[str]:
        """Validate that MT5 terminal path points to Clear broker (isolamento de terminal).

        CRÍTICO: Previne acidentes com FBS, XP, Zero Markets ou outro broker.
        """
        if v is None:
            return None

        v_upper = v.upper()
        if "CLEAR" not in v_upper:
            raise ValueError(
                f"Terminal path deve apontar para CLEAR (não FBS/XP/Zero/outro).\n"
                f"Caminho fornecido: {v}\n"
                f"Esperado: algo como C:\\Program Files\\Clear Investimentos MT5 Terminal\\terminal64.exe"
            )

        return v

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
        _config = TradingConfig()  # type: ignore[call-arg]
        _config.ensure_directories()
    return _config


def reset_config() -> None:
    """Reset global configuration (useful for testing)."""
    global _config
    _config = None
