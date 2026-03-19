"""
ROADMAP-DIARIOS-04: Detector de vies direcional.

Responsabilidades:
- Analisar sequencias de sinais ou trades buy/sell.
- Medir concentracao direcional e desequilibrio entre lados.
- Classificar a intensidade do vies por limiares configuraveis.
- Expor relatorios JSON-friendly para consumo por outros modulos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


class BiasLevel(str, Enum):
    """Nivel de vies direcional observado na sequencia analisada."""

    BAIXO = "baixo"
    MODERADO = "moderado"
    ALTO = "alto"


@dataclass(frozen=True)
class DirectionalBiasReport:
    """Relatorio consolidado de vies direcional."""

    total_signals: int
    buy_count: int
    sell_count: int
    dominant_side: str
    dominant_count: int
    directional_concentration_pct: float
    directional_imbalance_pct: float
    bias_level: BiasLevel
    moderate_threshold_pct: float
    high_threshold_pct: float
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """Converte o relatorio para uma estrutura serializavel."""
        return {
            "total_signals": self.total_signals,
            "buy_count": self.buy_count,
            "sell_count": self.sell_count,
            "dominant_side": self.dominant_side,
            "dominant_count": self.dominant_count,
            "directional_concentration_pct": self.directional_concentration_pct,
            "directional_imbalance_pct": self.directional_imbalance_pct,
            "bias_level": self.bias_level.value,
            "moderate_threshold_pct": self.moderate_threshold_pct,
            "high_threshold_pct": self.high_threshold_pct,
            "timestamp": self.timestamp.isoformat(),
        }


class DirectionalBiasDetector:
    """
    Detector de vies direcional baseado em sequencias de sinais/trades.

    O detector aceita entradas como strings ou mapeamentos com chaves
    comuns do dominio, por exemplo: `side`, `direction`, `action`,
    `signal` e `type`.
    """

    _BUY_VALUES = {"buy", "long", "bullish", "call", "up"}
    _SELL_VALUES = {"sell", "short", "bearish", "put", "down"}
    _DEFAULT_MODERATE_THRESHOLD = 60.0
    _DEFAULT_HIGH_THRESHOLD = 75.0

    def __init__(
        self,
        moderate_threshold_pct: float = _DEFAULT_MODERATE_THRESHOLD,
        high_threshold_pct: float = _DEFAULT_HIGH_THRESHOLD,
    ) -> None:
        self._validate_thresholds(moderate_threshold_pct, high_threshold_pct)
        self._moderate_threshold_pct = moderate_threshold_pct
        self._high_threshold_pct = high_threshold_pct

    def detect_bias(
        self,
        signals: Iterable[str | Mapping[str, Any]],
    ) -> DirectionalBiasReport:
        """Analisa uma sequencia de sinais e retorna um relatorio."""
        normalized_signals = [self._normalize_signal(signal) for signal in signals]
        buy_count = sum(1 for side in normalized_signals if side == "buy")
        sell_count = sum(1 for side in normalized_signals if side == "sell")
        total_signals = len(normalized_signals)

        dominant_side, dominant_count = self._resolve_dominant_side(
            buy_count,
            sell_count,
        )
        concentration_pct = self._calculate_concentration_pct(
            dominant_count,
            total_signals,
        )
        imbalance_pct = self._calculate_imbalance_pct(
            buy_count,
            sell_count,
            total_signals,
        )
        bias_level = self._classify_bias_level(concentration_pct, total_signals)

        return DirectionalBiasReport(
            total_signals=total_signals,
            buy_count=buy_count,
            sell_count=sell_count,
            dominant_side=dominant_side,
            dominant_count=dominant_count,
            directional_concentration_pct=concentration_pct,
            directional_imbalance_pct=imbalance_pct,
            bias_level=bias_level,
            moderate_threshold_pct=self._moderate_threshold_pct,
            high_threshold_pct=self._high_threshold_pct,
            timestamp=datetime.now(),
        )

    def detectar_vies_direcional(
        self,
        sinais: Iterable[str | Mapping[str, Any]],
    ) -> DirectionalBiasReport:
        """Alias em portugues para analise de vies direcional."""
        return self.detect_bias(sinais)

    def analyze_signals(
        self,
        signals: Iterable[str | Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Retorna o relatorio em formato dict para integrações simples."""
        return self.detect_bias(signals).to_dict()

    def build_report(
        self,
        signals: Iterable[str | Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Alias para `analyze_signals` com nome semantico de relatorio."""
        return self.analyze_signals(signals)

    def _normalize_signal(self, signal: str | Mapping[str, Any]) -> str:
        if isinstance(signal, str):
            return self._normalize_side_value(signal)

        for key in ("side", "direction", "signal", "action", "type"):
            if key in signal:
                return self._normalize_side_value(signal[key])

        raise ValueError("Sinal sem campo direcional reconhecivel.")

    def _normalize_side_value(self, value: Any) -> str:
        if value is None:
            raise ValueError("Sinal direcional vazio.")

        normalized = str(value).strip().lower()
        if normalized in self._BUY_VALUES:
            return "buy"
        if normalized in self._SELL_VALUES:
            return "sell"

        raise ValueError(f"Valor direcional invalido: {value!r}")

    def _resolve_dominant_side(self, buy_count: int, sell_count: int) -> tuple[str, int]:
        if buy_count == 0 and sell_count == 0:
            return "neutral", 0
        if buy_count == sell_count:
            return "neutral", buy_count
        if buy_count > sell_count:
            return "buy", buy_count
        return "sell", sell_count

    def _calculate_concentration_pct(
        self,
        dominant_count: int,
        total_signals: int,
    ) -> float:
        if total_signals <= 0:
            return 0.0
        return round((dominant_count / total_signals) * 100.0, 4)

    def _calculate_imbalance_pct(
        self,
        buy_count: int,
        sell_count: int,
        total_signals: int,
    ) -> float:
        if total_signals <= 0:
            return 0.0
        return round((abs(buy_count - sell_count) / total_signals) * 100.0, 4)

    def _classify_bias_level(
        self,
        concentration_pct: float,
        total_signals: int,
    ) -> BiasLevel:
        if total_signals <= 0:
            return BiasLevel.BAIXO
        if concentration_pct >= self._high_threshold_pct:
            return BiasLevel.ALTO
        if concentration_pct >= self._moderate_threshold_pct:
            return BiasLevel.MODERADO
        return BiasLevel.BAIXO

    def _validate_thresholds(
        self,
        moderate_threshold_pct: float,
        high_threshold_pct: float,
    ) -> None:
        if moderate_threshold_pct < 0 or high_threshold_pct < 0:
            raise ValueError("Limiar nao pode ser negativo.")
        if moderate_threshold_pct > high_threshold_pct:
            raise ValueError("Limiar moderado nao pode exceder o limiar alto.")
        if high_threshold_pct > 100:
            raise ValueError("Limiar alto nao pode exceder 100.")
