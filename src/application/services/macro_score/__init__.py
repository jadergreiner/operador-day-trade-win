"""Macro Score Engine - Sistema de pontuacao macro para WIN."""

from src.application.services.macro_score.engine import (
    ItemScoreResult,
    MacroScoreEngine,
    MacroScoreResult,
)
from src.application.services.macro_score.forex_handler import ForexScoreHandler
from src.application.services.macro_score.futures_resolver import (
    FuturesContractResolver,
)
from src.application.services.macro_score.item_registry import (
    MacroScoreItemConfig,
    get_item_registry,
)
from src.application.services.macro_score.technical_scorer import (
    TechnicalIndicatorScorer,
)

__all__ = [
    "MacroScoreEngine",
    "MacroScoreResult",
    "ItemScoreResult",
    "MacroScoreItemConfig",
    "get_item_registry",
    "FuturesContractResolver",
    "ForexScoreHandler",
    "TechnicalIndicatorScorer",
]
