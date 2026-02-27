"""
S2-6: Analytics de Intervencao Manual

Modulo de analytics para:
- Dashboard em tempo real (signals, performance, risk)
- API de feedback do trader
- Logging de intervencoes manuais
- Relatorios de performance
"""

__version__ = "0.1.0"
__all__ = [
    "AnalyticsDashboard",
    "TraderFeedbackAPI",
    "ManualOverrideLogger",
    "AnalyticsConfig",
]

from .analytics_dashboard import AnalyticsDashboard
from .trader_feedback_api import TraderFeedbackAPI
from .manual_override_logger import ManualOverrideLogger
from .config import AnalyticsConfig
