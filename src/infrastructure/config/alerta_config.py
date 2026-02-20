"""
Configuração de Alertas Automáticos - Schema Validation & Loading

Validação com Pydantic + support para environment variables.
"""

import os
from typing import Optional
from pathlib import Path
from pydantic import BaseModel, Field, validator
import yaml
import logging

logger = logging.getLogger(__name__)


# DetectionConfig
class DetectionVolatilityConfig(BaseModel):
    """Configuração para detecção de volatilidade."""
    habilitado: bool = True
    window: int = Field(default=20, description="Janela de cálculo (períodos)")
    threshold_sigma: float = Field(default=2.0, description="Threshold z-score")
    confirmacao_velas: int = Field(default=2, description="Velas para confirmação")
    latencia_target_ms: int = Field(default=30000, description="Target latência P95")

    class Config:
        extra = "allow"


class DetectionPadroesConfig(BaseModel):
    """Configuração para detecção de padrões técnicos."""
    habilitado: bool = True
    engulfing_enabled: bool = True
    rsi_divergencia_enabled: bool = True
    break_suporte_enabled: bool = True
    break_resistencia_enabled: bool = True

    class Config:
        extra = "allow"


class DetectionConfig(BaseModel):
    """Configuração completa da detecção."""
    volatilidade: DetectionVolatilityConfig = Field(default_factory=DetectionVolatilityConfig)
    padroes: DetectionPadroesConfig = Field(default_factory=DetectionPadroesConfig)


# DeliveryConfig
class WebSocketConfig(BaseModel):
    """Configuração WebSocket."""
    url: str = Field(default="ws://localhost:8765/alertas")
    timeout_ms: int = Field(default=500)
    retry_enabled: bool = False
    token_env: Optional[str] = Field(default="WEBSOCKET_TOKEN")

    class Config:
        extra = "allow"


class EmailConfig(BaseModel):
    """Configuração Email SMTP."""
    smtp_host: str = Field(default="localhost")
    smtp_port: int = Field(default=1025)
    smtp_user_env: Optional[str] = Field(default="SMTP_USER")
    smtp_password_env: Optional[str] = Field(default="SMTP_PASSWORD")
    use_tls: bool = False
    retry_enabled: bool = True
    max_retries: int = 3
    recipients: list = Field(default_factory=lambda: ["operador@fund.local"])

    class Config:
        extra = "allow"


class SMSConfig(BaseModel):
    """Configuração SMS (v1.2 future)."""
    habilitado: bool = False
    provedor: str = Field(default="twilio")
    max_retries: int = 2

    class Config:
        extra = "allow"


class DeliveryConfig(BaseModel):
    """Configuração completa de delivery."""
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    sms: SMSConfig = Field(default_factory=SMSConfig)


# FilaConfig
class FilaConfig(BaseModel):
    """Configuração da fila de alertas."""
    tamanho_maximo: int = Field(default=100)
    rate_limit_segundos: int = Field(default=60)
    dedup_ttl_segundos: int = Field(default=120)
    max_simultaneos: int = Field(default=3)

    class Config:
        extra = "allow"


# AuditoriaConfig
class AuditoriaConfig(BaseModel):
    """Configuração de auditoria."""
    database_path: str = Field(default="data/db/alertas_audit.db")
    retencao_dias: int = Field(default=2555)  # 7 anos
    backup_enabled: bool = True
    backup_path: Optional[str] = None

    class Config:
        extra = "allow"


# LoggingConfig
class LoggingConfig(BaseModel):
    """Configuração de logging."""
    nivel: str = Field(default="INFO")
    arquivo: Optional[str] = None
    rotacao: str = Field(default="daily")
    backup_count: int = 7

    class Config:
        extra = "allow"


# Main Config
class AlertaConfig(BaseModel):
    """Configuração completa de alertas automáticos."""
    habilitado: bool = True
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    delivery: DeliveryConfig = Field(default_factory=DeliveryConfig)
    fila: FilaConfig = Field(default_factory=FilaConfig)
    auditoria: AuditoriaConfig = Field(default_factory=AuditoriaConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @validator("detection", pre=True)
    def parse_detection(cls, v):
        if isinstance(v, dict):
            v.setdefault("volatilidade", {})
            v.setdefault("padroes", {})
        return v

    class Config:
        extra = "allow"

    def get_env_var(self, env_var_name: Optional[str]) -> Optional[str]:
        """Resolve environment variable."""
        if not env_var_name:
            return None
        return os.getenv(env_var_name)


def load_config(config_path: str = "config/alertas.yaml") -> AlertaConfig:
    """
    Carrega configuração de arquivo YAML com validação Pydantic.

    Args:
        config_path: Caminho para arquivo config/alertas.yaml

    Returns:
        AlertaConfig validada

    Raises:
        FileNotFoundError: Se arquivo não existe
        ValueError: Se YAML inválido
    """
    config_file = Path(config_path)

    if not config_file.exists():
        logger.warning(f"Config file não encontrado: {config_path}")
        logger.info("Usando configuração padrão (defaults)")
        return AlertaConfig()

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        logger.info(f"Carregada configuração: {config_path}")
        return AlertaConfig(**yaml_data)

    except yaml.YAMLError as e:
        raise ValueError(f"YAML inválido em {config_path}: {e}")
    except Exception as e:
        raise ValueError(f"Erro ao carregar configuração: {e}")


# Singleton pattern para config global
_config_instance: Optional[AlertaConfig] = None


def get_config() -> AlertaConfig:
    """Retorna instância global de configuração (lazy-loaded)."""
    global _config_instance
    if _config_instance is None:
        _config_instance = load_config()
    return _config_instance


def reset_config() -> None:
    """Reseta singleton (útil para testes)."""
    global _config_instance
    _config_instance = None
