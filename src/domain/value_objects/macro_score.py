"""Value Objects para o sistema de Macro Score."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Score:
    """Value Object - pontuacao individual de um item (-1, 0, +1)."""

    value: int

    def __post_init__(self) -> None:
        if self.value not in (-1, 0, 1):
            raise ValueError(f"Score deve ser -1, 0 ou +1, recebeu: {self.value}")

    def __str__(self) -> str:
        if self.value > 0:
            return "+1"
        return str(self.value)

    def __repr__(self) -> str:
        return f"Score({self.value})"


@dataclass(frozen=True)
class Weight:
    """Value Object - peso de um item (>= 0)."""

    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))
        if self.value < 0:
            raise ValueError(f"Weight deve ser >= 0, recebeu: {self.value}")

    def __str__(self) -> str:
        return f"{self.value:.2f}"

    def __repr__(self) -> str:
        return f"Weight({self.value})"


@dataclass(frozen=True)
class WeightedScore:
    """Value Object - score ponderado (score * peso)."""

    score: Score
    weight: Weight

    @property
    def contribution(self) -> Decimal:
        """Contribuicao ponderada deste item."""
        return Decimal(str(self.score.value)) * self.weight.value

    def __str__(self) -> str:
        return f"{self.contribution:+.2f}"

    def __repr__(self) -> str:
        return f"WeightedScore(score={self.score.value}, weight={self.weight.value}, contribution={self.contribution})"
