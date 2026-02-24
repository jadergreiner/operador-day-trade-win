"""
Módulo: FibonacciCalculator
Descrição: Utilitário para normalização e aplicação de peso do Fibonacci Fan Score
ao micro_score de probabilidade de trade.

Fan Score [-6, +6] → Normalized [0.0, 1.0] → Contribution [0.0, 0.15]

Autor: Arquiteto de Sistemas + Eng Sr
Data: 24/02/2026
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class FibonacciConfig:
    """
    Configuração do Fibonacci Calculator.

    Attributes:
        weight: Peso da contribuição Fibonacci no micro_score (default: 0.15)
        min_fan_score: Valor mínimo do fan_score bruto (default: -6)
        max_fan_score: Valor máximo do fan_score bruto (default: +6)
        mima_lengths: Tupla com os períodos Fibonacci para MIMA (8, 17, 34, 72, 144, 305, 610)
    """
    weight: float = 0.15  # Peso na composição do micro_score
    min_fan_score: int = -6  # Mínimo
    max_fan_score: int = 6  # Máximo
    mima_lengths: Tuple[int, ...] = (8, 17, 34, 72, 144, 305, 610)


class FibonacciCalculator:
    """
    Calculadora de normalização e contribuição do Fibonacci Fan Score.

    Transforma scores brutos [-6, +6] em contribuições ponderadas [0.0, 0.15]
    ao micro_score do sistema de trading.

    O Fan Score é calculado a partir de 7 MIMA (Moving Average exponencial)
    em períodos Fibonacci (8, 17, 34, 72, 144, 305, 610). Comparando pares
    consecutivos de MIMAs (7-1=6 comparações), obtemos um score que varia
    de -6 (todas descendentes) até +6 (todas ascendentes).

    Example:
        >>> calc = FibonacciCalculator(weight=0.15)
        >>> normalized = calc.normalize_fan_score(6)  # Score ALTA máxima
        >>> assert normalized == 1.0

        >>> calc = FibonacciCalculator(weight=0.20)
        >>> contribution = calc.calculate_weighted_contribution(0)  # Score MISTO
        >>> assert contribution == 0.10  # (0+6)/12 * 0.20 = 0.10
    """

    def __init__(self, config: Optional[FibonacciConfig] = None):
        """
        Inicializa o FibonacciCalculator com configuração.

        Args:
            config: FibonacciConfig com parâmetros. Se None, usa defaults.
        """
        self.config = config or FibonacciConfig()
        self._validate_config()

    def _validate_config(self) -> None:
        """
        Valida a configuração.

        Raises:
            ValueError: Se parâmetros estão inconsistentes.
        """
        if not (0.0 <= self.config.weight <= 1.0):
            raise ValueError(
                f"weight deve estar em [0.0, 1.0], got {self.config.weight}"
            )

        if self.config.min_fan_score >= self.config.max_fan_score:
            raise ValueError(
                f"min_fan_score ({self.config.min_fan_score}) deve ser < "
                f"max_fan_score ({self.config.max_fan_score})"
            )

        if len(self.config.mima_lengths) != 7:
            raise ValueError(
                f"mima_lengths deve ter exatamente 7 períodos, "
                f"got {len(self.config.mima_lengths)}"
            )

    def normalize_fan_score(self, fan_score: int) -> float:
        """
        Normaliza fan_score de [-6, +6] para [0.0, 1.0].

        A normalização é linear:
        normalized = (fan_score - min_fan_score) / (max_fan_score - min_fan_score)

        Exemplos:
        - fan_score = -6 (BAIXA máxima) → 0.0
        - fan_score = 0 (MISTO neutro) → 0.5
        - fan_score = +6 (ALTA máxima) → 1.0

        Args:
            fan_score: Valor bruto do fan_score [-6, +6]

        Returns:
            Valor normalizado no intervalo [0.0, 1.0]

        Raises:
            ValueError: Se fan_score está fora do intervalo válido.
        """
        if not (self.config.min_fan_score <= fan_score <= self.config.max_fan_score):
            raise ValueError(
                f"fan_score {fan_score} está fora do intervalo permitido "
                f"[{self.config.min_fan_score}, {self.config.max_fan_score}]"
            )

        score_range = (
            self.config.max_fan_score - self.config.min_fan_score
        )
        normalized = (
            (fan_score - self.config.min_fan_score) / score_range
        )

        # Garantir clamping em [0.0, 1.0] (proteção contra erros de ponto flutuante)
        return max(0.0, min(1.0, normalized))

    def calculate_weighted_contribution(self, fan_score: int) -> float:
        """
        Calcula a contribuição ponderada do fan_score ao micro_score.

        Contribuição = normalized_score * weight

        Exemplos (com weight=0.15 default):
        - fan_score = +6 (ALTA) → contribution = 1.0 * 0.15 = 0.15
        - fan_score = 0 (MISTO) → contribution = 0.5 * 0.15 = 0.075
        - fan_score = -6 (BAIXA) → contribution = 0.0 * 0.15 = 0.00

        Args:
            fan_score: Valor bruto do fan_score [-6, +6]

        Returns:
            Contribuição ponderada no intervalo [0.0, self.config.weight]

        Raises:
            ValueError: Se fan_score está fora do intervalo válido.
        """
        normalized = self.normalize_fan_score(fan_score)
        contribution = normalized * self.config.weight
        return contribution

    def get_config(self) -> Dict:
        """
        Retorna a configuração atual como dicionário.

        Returns:
            Dicionário com os parâmetros da configuração.
        """
        return {
            "weight": self.config.weight,
            "min_fan_score": self.config.min_fan_score,
            "max_fan_score": self.config.max_fan_score,
            "mima_lengths": list(self.config.mima_lengths),
        }

    def get_fan_score_interpretation(self, fan_score: int) -> Dict:
        """
        Retorna uma interpretação qualitativa do fan_score.

        Args:
            fan_score: Valor bruto do fan_score [-6, +6]

        Returns:
            Dicionário com:
            - alignment: 'ALTA', 'BAIXA', ou 'MISTO'
            - strength: 'fraco', 'moderado', ou 'forte'
            - normalized: valor normalizado [0.0, 1.0]
            - contribution: valor da contribuição ao micro_score
        """
        normalized = self.normalize_fan_score(fan_score)
        contribution = self.calculate_weighted_contribution(fan_score)

        if fan_score > 0:
            alignment = "ALTA"
        elif fan_score < 0:
            alignment = "BAIXA"
        else:
            alignment = "MISTO"

        # Classificar força
        abs_score = abs(fan_score)
        if abs_score <= 2:
            strength = "fraco"
        elif abs_score <= 4:
            strength = "moderado"
        else:
            strength = "forte"

        return {
            "alignment": alignment,
            "strength": strength,
            "fan_score": fan_score,
            "normalized": normalized,
            "contribution": contribution,
            "weight": self.config.weight,
        }

    def apply_to_micro_score(
        self, base_micro_score: float, fan_score: int
    ) -> float:
        """
        Aplica a contribuição Fibonacci a um micro_score base.

        micro_score_final = base_micro_score + fibonacci_contribution
        O resultado é clamped em [0.0, 1.0]

        Args:
            base_micro_score: Score base antes da contribuição Fibonacci [0.0, 1.0]
            fan_score: Fan score bruto [-6, +6]

        Returns:
            Micro score final com contribuição Fibonacci [0.0, 1.0]

        Raises:
            ValueError: Se base_micro_score não está em [0.0, 1.0] ou
                       fan_score está fora do intervalo válido.
        """
        if not (0.0 <= base_micro_score <= 1.0):
            raise ValueError(
                f"base_micro_score {base_micro_score} deve estar em [0.0, 1.0]"
            )

        fibonacci_contribution = self.calculate_weighted_contribution(fan_score)
        micro_score_final = base_micro_score + fibonacci_contribution

        # Clamp em [0.0, 1.0]
        return max(0.0, min(1.0, micro_score_final))


# Instance global padrão
_default_calculator = None


def get_default_calculator(weight: float = 0.15) -> FibonacciCalculator:
    """
    Retorna ou cria a instância padrão do FibonacciCalculator.

    Args:
        weight: Peso para nova instância se não existir (default: 0.15)

    Returns:
        FibonacciCalculator inicializado.
    """
    global _default_calculator
    if _default_calculator is None:
        config = FibonacciConfig(weight=weight)
        _default_calculator = FibonacciCalculator(config)
    return _default_calculator


if __name__ == "__main__":
    # Exemplos de uso
    calc = FibonacciCalculator()

    print("=" * 60)
    print("FibonacciCalculator - Exemplos de Uso")
    print("=" * 60)

    print("\n1. Normalização de Fan Scores:")
    for score in [-6, -3, 0, 3, 6]:
        normalized = calc.normalize_fan_score(score)
        print(f"   fan_score={score:+2d} → normalized={normalized:.3f}")

    print("\n2. Contribuições ao Micro Score (weight=0.15):")
    for score in [-6, -3, 0, 3, 6]:
        contribution = calc.calculate_weighted_contribution(score)
        print(f"   fan_score={score:+2d} → contribution={contribution:.4f}")

    print("\n3. Interpretações Qualitativas:")
    for score in [-6, -2, 0, 2, 6]:
        interp = calc.get_fan_score_interpretation(score)
        print(f"   fan_score={score:+2d}:")
        print(f"      Alignment: {interp['alignment']}")
        print(f"      Strength: {interp['strength']}")
        print(f"      Contribution: {interp['contribution']:.4f}")

    print("\n4. Aplicação ao Micro Score:")
    base_scores = [0.4, 0.5, 0.6]
    fan_scores = [-6, 0, 6]
    for base in base_scores:
        print(f"   base_micro_score={base:.1f}:")
        for fan in fan_scores:
            final = calc.apply_to_micro_score(base, fan)
            print(f"      fan_score={fan:+2d} → final={final:.4f}")

    print("\n5. Configuração:")
    config = calc.get_config()
    print(f"   {config}")

    print("\n" + "=" * 60)
    print("Status: FibonacciCalculator pronto para integração ✅")
    print("=" * 60)
