"""Value Objects module."""

from src.domain.value_objects.financial import (
    Money,
    Percentage,
    Price,
    Quantity,
    Symbol,
)
from src.domain.value_objects.macro_score import Score, Weight, WeightedScore
from src.domain.value_objects.risco_externo import (
    ConfiguracaoCooldown,
    ConfiguracaoGanhoDiario,
    ConfiguracaoHorario,
    ConfiguracaoSLMaximo,
    EventoCalendario,
    ResultadoGateRisco,
)

__all__ = [
    "Price",
    "Money",
    "Quantity",
    "Percentage",
    "Symbol",
    "Score",
    "Weight",
    "WeightedScore",
    "ConfiguracaoCooldown",
    "ConfiguracaoSLMaximo",
    "ConfiguracaoHorario",
    "ConfiguracaoGanhoDiario",
    "EventoCalendario",
    "ResultadoGateRisco",
]
