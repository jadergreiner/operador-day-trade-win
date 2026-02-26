"""Machine Learning module para WINFUT.

Componentes:
- winfut_dataset: Dataset builder (consume RL tables)
- winfut_feature_engineer: Feature engineering (Tier-1, Tier-2)
- winfut_model_trainer: XGBoost training (walk-forward validation)
- lgbm_agent_integrator: LightGBM integration no agente (26/02/2026)
"""

# Imports tolerantes a falhas - só carrega o que existe
try:
    from src.application.services.ml.winfut_feature_engineer import WinFutFeatureEngineer
except ImportError:
    WinFutFeatureEngineer = None

try:
    from src.application.services.ml.winfut_model_trainer import WinFutModelTrainer
except ImportError:
    WinFutModelTrainer = None

try:
    from src.application.services.ml.lgbm_agent_integrator import LGBMAgentIntegrator
except ImportError:
    LGBMAgentIntegrator = None

__all__ = [
    "WinFutFeatureEngineer",
    "WinFutModelTrainer",
    "LGBMAgentIntegrator",
]
