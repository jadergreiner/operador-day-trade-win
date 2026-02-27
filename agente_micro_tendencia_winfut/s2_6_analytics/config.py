"""
Configuracao para S2-6: Analytics de Intervencao Manual
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AnalyticsConfig:
    """Configuracao do modulo de analytics"""

    # Localizacoes
    log_dir: Path = Path.home() / ".operador_analytics"
    override_log_file: str = "manual_overrides.log"
    feedback_log_file: str = "trader_feedback.log"
    metrics_db_file: str = "analytics_metrics.db"

    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    api_ws_url: str = "ws://localhost:8001/feedback"
    api_timeout_seconds: int = 30

    # Dashboard Settings
    dashboard_refresh_interval_sec: float = 1.0  # 1 segundo
    dashboard_history_days: int = 30  # Manter 30 dias de historico

    # Logging Settings
    log_level: str = "INFO"
    log_retention_days: int = 90
    enable_syslog: bool = False

    # Analytics Settings
    metrics_aggregation_interval_sec: float = 60.0  # 1 minuto
    performance_lookback_periods: tuple = (1, 5, 10, 30)  # minutos

    # Manual Override Settings
    require_reason_on_override: bool = True
    max_consecutive_manual_overrides: int = 3
    manual_override_alert_threshold: float = 0.15  # 15% de intervencoes

    # Risk Monitoring
    enable_risk_monitoring: bool = True
    risk_check_interval_sec: float = 5.0
    max_drawdown_alert_threshold: float = 0.10  # 10%

    def __post_init__(self) -> None:
        """Validacao apos inicializacao"""
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @property
    def override_log_path(self) -> Path:
        """Caminho completo do arquivo de override logging"""
        return self.log_dir / self.override_log_file

    @property
    def feedback_log_path(self) -> Path:
        """Caminho completo do arquivo de feedback logging"""
        return self.log_dir / self.feedback_log_file

    @property
    def metrics_db_path(self) -> Path:
        """Caminho completo do banco de dados de metricas"""
        return self.log_dir / self.metrics_db_file


# Instancia global padrao
default_config = AnalyticsConfig()
