# -*- coding: utf-8 -*-
"""
Calculador de Phi Cube (Mimas) — Confluência Geométrica Fibonacci.

Implementa o indicador Phi Cube baseado em períodos Fibonacci (8, 17, 34, 72,
144, 305, 610) para detectar alinhamento geométrico nos preços. Functiona como
"confluência de terceira dimensão" junto com SMC (S2-3) e ATR (S2-2).

Módulo: score_phicube.py
Arquitetura: S2-4 Integração Phicube (Mimas)
Objetivo: +3-5% win rate via confluência geométrica
Timeline: Sprint 2 (26-27/02/2026)

Author: ML Expert Squad
Status: ✅ PRODUCTION-READY
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional, Tuple
import logging

# Configurar logging em português
logger = logging.getLogger(__name__)


@dataclass
class MimaItem:
    """
    Item individual de Mima (Moving Average Fibonacci).

    Atributos:
        period: Período Fibonacci (8, 17, 34, 72, 144, 305, 610)
        value: Valor atual da média móvel em Decimal
        slope: Direção da média ("ALTA", "BAIXA", "NEUTRO")
    """
    period: int
    value: Decimal = Decimal("0")
    slope: str = "NEUTRO"

    def __post_init__(self):
        """Validar após inicialização."""
        if self.period not in [8, 17, 34, 72, 144, 305, 610]:
            logger.warning(
                f"AVISO: Período {self.period} não é padrão Fibonacci."
            )
        if self.slope not in ["ALTA", "BAIXA", "NEUTRO"]:
            raise ValueError(
                f"slope inválido: {self.slope}. Use ALTA/BAIXA/NEUTRO."
            )

    def __repr__(self) -> str:
        """Representação legível."""
        return (
            f"M{self.period}({self.value:.2f}, {self.slope})"
        )


@dataclass
class MimaData:
    """
    Dados consolidados de Mimas (Phi Cube).

    Agregado de 7 Mimas calculadas + fan_score que representa o alinhamento
    geométrico. Fan score [-6, +6] é normalizado para [0, 1].

    Atributos:
        m8-m610: 7 MimaItems para períodos Fibonacci
        alignment: Alinhamento detectado ("ALTA", "BAIXA", "MISTO")
        fan_score: Pontuação bruta de alinhamento [-6, +6]
    """
    m8: MimaItem = field(default_factory=lambda: MimaItem(8))
    m17: MimaItem = field(default_factory=lambda: MimaItem(17))
    m34: MimaItem = field(default_factory=lambda: MimaItem(34))
    m72: MimaItem = field(default_factory=lambda: MimaItem(72))
    m144: MimaItem = field(default_factory=lambda: MimaItem(144))
    m305: MimaItem = field(default_factory=lambda: MimaItem(305))
    m610: MimaItem = field(default_factory=lambda: MimaItem(610))
    alignment: str = "MISTO"
    fan_score: int = 0

    def get_list(self) -> List[MimaItem]:
        """Retorna lista de 7 Mimas em ordem Fibonacci."""
        return [
            self.m8, self.m17, self.m34, self.m72,
            self.m144, self.m305, self.m610
        ]

    def get_normalized_score(self) -> float:
        """
        Normaliza fan_score para intervalo [0, 1].

        Fan score bruto: [-6, +6] (6 comparações entre 7 Mimas)
        Normalizado: (fan_score + 6) / 12 → [0.0, 1.0]
        """
        return max(0.0, min(1.0, (self.fan_score + 6) / 12))

    def get_weighted_score(self, weight: float = 0.15) -> float:
        """
        Aplicar peso ao score normalizado para integração ao micro_score.

        Padrão: weight=0.15 (15% de contribuição máxima ao micro_score).
        """
        normalized = self.get_normalized_score()
        return normalized * weight

    def __repr__(self) -> str:
        """Representação legível."""
        return (
            f"MimaData(align={self.alignment}, fan={self.fan_score}, "
            f"norm={self.get_normalized_score():.3f})"
        )


class PhiCubeCalculator:
    """
    Calculador de Phi Cube (Mimas) — Confluência Geométrica.

    Mantém janela de preços históricos e calcula 7 Mimas (moving averages
    Fibonacci). Fan score detecta alinhamento geométrico (+6=ALTA, -6=BAIXA).

    Exemplo de uso:
        calc = PhiCubeCalculator()
        for candle in stream:
            calc.add_candle(candle.close)
            mima_data = calc.calculate()
            confluencia = mima_data.get_weighted_score(weight=0.15)
    """

    # Períodos Fibonacci padrão (em número de candles M1)
    PERIODS: List[int] = [8, 17, 34, 72, 144, 305, 610]

    def __init__(self, window_size: int = 610):
        """
        Inicializar calculador de Phi Cube.

        Args:
            window_size: Tamanho máximo do histórico de preços (default: 610)
        """
        self.window_size = window_size
        self.prices: List[Decimal] = []
        self.current_mima: MimaData = MimaData()

        logger.info(
            f"PhiCubeCalculator inicializado (window={window_size})"
        )

    def add_candle(self, close: float) -> None:
        """
        Adicionar novo candle (M1) ao histórico.

        Args:
            close: Preço de fechamento como float
        """
        # Converter para Decimal para precisão
        close_decimal = Decimal(str(close)).quantize(Decimal("0.01"))
        self.prices.append(close_decimal)

        # Manter janela máxima
        if len(self.prices) > self.window_size:
            self.prices = self.prices[-self.window_size:]

    def _calculate_sma(self, period: int) -> Optional[Decimal]:
        """
        Calcular Simple Moving Average (SMA) para período Fibonacci.

        Args:
            period: Período em candles (8, 17, 34, 72, 144, 305, 610)

        Returns:
            SMA como Decimal, ou None se histórico insuficiente
        """
        if len(self.prices) < period:
            return None

        window = self.prices[-period:]
        sma = sum(window) / Decimal(len(window))
        return sma.quantize(Decimal("0.01"))

    def _update_slope(self, mima: MimaItem, previous_value: Optional[Decimal]) -> None:
        """
        Atualizar slope (ALTA/BAIXA/NEUTRO) da Mima.

        Args:
            mima: MimaItem a atualizar
            previous_value: Valor anterior da SMA (para comparação)
        """
        if previous_value is None:
            mima.slope = "NEUTRO"
            return

        if mima.value > previous_value:
            mima.slope = "ALTA"
        elif mima.value < previous_value:
            mima.slope = "BAIXA"
        else:
            mima.slope = "NEUTRO"

    def _calculate_fan_score(self) -> int:
        """
        Calcular fan_score (alinhamento geométrico).

        Compara cada Mima com a seguinte:
        - +1 se maior (ordem descrescente = tendência ALTA)
        - -1 se menor (ordem crescente = tendência BAIXA)
        - 0 se igual

        Intervalo final: [-6, +6] (6 comparações entre 7 Mimas)

        Returns:
            fan_score como int
        """
        fan_score = 0
        mimas_list = self.current_mima.get_list()

        for i in range(len(mimas_list) - 1):
            if mimas_list[i].value > mimas_list[i + 1].value:
                fan_score += 1
            elif mimas_list[i].value < mimas_list[i + 1].value:
                fan_score -= 1

        return fan_score

    def _determine_alignment(self) -> str:
        """
        Determinar alinhamento ALTA/BAIXA/MISTO baseado em fan_score.

        Returns:
            String: "ALTA" se fan_score > 2, "BAIXA" se < -2, else "MISTO"
        """
        if self.current_mima.fan_score > 2:
            return "ALTA"
        elif self.current_mima.fan_score < -2:
            return "BAIXA"
        else:
            return "MISTO"

    def calculate(self) -> MimaData:
        """
        Calcular Mimas e retornar MimaData atualizada.

        Processa histórico de preços, calcula 7 SMAs Fibonacci, determina
        alinhamento geométrico.

        Returns:
            MimaData com 7 Mimas atualizadas + fan_score + alignment
        """
        # Edge case: histórico vazio
        if not self.prices:
            logger.warning("Histórico vazio, retornando MimaData padrão")
            return MimaData()

        # Guardar valores anteriores para slope
        previous_values = {
            m.period: m.value for m in self.current_mima.get_list()
        }

        # Calcular SMA para cada período Fibonacci
        for mima_item in self.current_mima.get_list():
            sma = self._calculate_sma(mima_item.period)

            if sma is not None:
                # Atualizar valor e slope
                previous = previous_values.get(mima_item.period)
                mima_item.value = sma
                self._update_slope(mima_item, previous)
            else:
                # Histórico insuficiente para este período
                mima_item.value = Decimal("0")
                mima_item.slope = "NEUTRO"

        # Calcular fan_score e alinhamento
        self.current_mima.fan_score = self._calculate_fan_score()
        self.current_mima.alignment = self._determine_alignment()

        return self.current_mima

    def get_fan_score(self) -> int:
        """Retornar fan_score bruto atual [-6, +6]."""
        return self.current_mima.fan_score

    def get_normalized_score(self) -> float:
        """Retornar fan_score normalizado [0, 1]."""
        return self.current_mima.get_normalized_score()

    def get_weighted_score(self, weight: float = 0.15) -> float:
        """Retornar score ponderado para integração ao micro_score."""
        return self.current_mima.get_weighted_score(weight)

    def get_status(self) -> dict:
        """
        Retornar status completo para telemetria/logging.

        Returns:
            Dict com métricas atuais
        """
        return {
            "candles_loaded": len(self.prices),
            "alignment": self.current_mima.alignment,
            "fan_score": self.current_mima.fan_score,
            "normalized_score": self.get_normalized_score(),
            "weighted_score_015": self.get_weighted_score(0.15),
            "mimas": {
                m.period: {
                    "value": float(m.value),
                    "slope": m.slope
                }
                for m in self.current_mima.get_list()
            }
        }


def create_phicube_calculator() -> PhiCubeCalculator:
    """Factory function para criar novo calculador."""
    return PhiCubeCalculator()


if __name__ == "__main__":
    # Exemplo de uso
    logging.basicConfig(level=logging.INFO)

    calc = create_phicube_calculator()

    # Simular stream de 100 candles com preço crescente
    for i in range(100):
        close = 10600 + i * 0.5
        calc.add_candle(close)

    # Calcular após ter histórico suficiente
    result = calc.calculate()
    print(f"Status: {result}")
    print(f"Score normalizado: {calc.get_normalized_score():.3f}")
    print(f"Score ponderado (15%): {calc.get_weighted_score(0.15):.4f}")
    print(f"Telemetria: {calc.get_status()}")
