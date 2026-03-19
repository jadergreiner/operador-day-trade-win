"""Adapter para classificar o regime de mercado a partir de metricas tecnicas.

O componente aceita entradas em formato `dict` ou objeto com atributos e
consolida a leitura de:
- trend_strength
- volatility
- directional_bias
- adx
- atr_percent
- range_compression

A saida e uma recomendacao serializavel com regime, confianca e ajustes de
risco/posicao para consumo por outras camadas da aplicacao.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _coerce_float(value: Any, field_name: str) -> float:
    try:
        coerced = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} deve ser numerico") from exc

    if coerced != coerced:
        raise ValueError(f"{field_name} nao pode ser NaN")
    return coerced


def _get_value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _scale_percent_like(value: float) -> float:
    """Converte fracao ou percentual em escala percentual comparavel."""
    if abs(value) <= 1.0:
        return value * 100.0
    return value


class MarketRegime(str, Enum):
    """Regimes de mercado suportados pelo adapter."""

    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"


@dataclass(frozen=True)
class MarketRegimeRecommendation:
    """Resultado estruturado da classificacao de regime de mercado."""

    regime: MarketRegime
    confidence: float
    risk_multiplier: float
    position_size_multiplier: float
    reasons: list[str]
    signals: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Converte a recomendacao para um dict serializavel."""
        return {
            "regime": self.regime.value,
            "confidence": self.confidence,
            "risk_multiplier": self.risk_multiplier,
            "position_size_multiplier": self.position_size_multiplier,
            "reasons": list(self.reasons),
            "signals": dict(self.signals),
        }

    para_dict = to_dict


class MarketRegimeAdapter:
    """Classifica o regime de mercado a partir de metricas tecnicas simples."""

    _TREND_STRENGTH_THRESHOLD = 55.0
    _ADX_TREND_THRESHOLD = 22.0
    _ADX_STRONG_THRESHOLD = 28.0
    _VOLATILITY_HIGH_THRESHOLD = 70.0
    _ATR_HIGH_THRESHOLD = 4.0
    _RANGE_COMPRESSION_THRESHOLD = 60.0
    _LOW_TREND_THRESHOLD = 25.0
    _LOW_ADX_THRESHOLD = 18.0

    def recommend(self, metrics: Any = None) -> MarketRegimeRecommendation:
        """Gera recomendacao de regime para um conjunto de metricas."""
        extracted = self._extract_metrics(metrics)
        if not extracted or extracted.get("recognized_metrics", 0) == 0:
            return self._fallback_recommendation()

        recognized_metrics = extracted["recognized_metrics"]
        trend_strength = extracted.get("trend_strength")
        volatility = extracted.get("volatility")
        directional_bias = extracted.get("directional_bias")
        adx = extracted.get("adx")
        atr_percent = extracted.get("atr_percent")
        range_compression = extracted.get("range_compression")

        volatility_score = self._build_volatility_score(volatility, atr_percent)
        trend_up_score = self._build_trend_score(
            trend_strength=trend_strength,
            directional_bias=directional_bias,
            adx=adx,
            range_compression=range_compression,
            volatility=volatility,
            direction="up",
        )
        trend_down_score = self._build_trend_score(
            trend_strength=trend_strength,
            directional_bias=directional_bias,
            adx=adx,
            range_compression=range_compression,
            volatility=volatility,
            direction="down",
        )
        range_score = self._build_range_score(
            trend_strength=trend_strength,
            volatility=volatility,
            adx=adx,
            range_compression=range_compression,
        )

        regime = self._classify_regime(
            trend_up_score=trend_up_score,
            trend_down_score=trend_down_score,
            range_score=range_score,
            volatility_score=volatility_score,
            trend_strength=trend_strength,
            directional_bias=directional_bias,
            adx=adx,
            volatility=volatility,
            atr_percent=atr_percent,
            range_compression=range_compression,
        )
        confidence = self._calculate_confidence(
            regime=regime,
            recognized_metrics=recognized_metrics,
            trend_up_score=trend_up_score,
            trend_down_score=trend_down_score,
            range_score=range_score,
            volatility_score=volatility_score,
            trend_strength=trend_strength,
            directional_bias=directional_bias,
            adx=adx,
            volatility=volatility,
            atr_percent=atr_percent,
            range_compression=range_compression,
        )
        risk_multiplier, position_size_multiplier, reasons = self._build_adjustments(
            regime=regime,
            confidence=confidence,
            trend_strength=trend_strength,
            directional_bias=directional_bias,
            adx=adx,
            volatility=volatility,
            atr_percent=atr_percent,
            range_compression=range_compression,
            trend_up_score=trend_up_score,
            trend_down_score=trend_down_score,
            range_score=range_score,
            volatility_score=volatility_score,
        )

        signals = {
            "recognized_metrics": float(recognized_metrics),
            "trend_strength": trend_strength,
            "volatility": volatility,
            "directional_bias": directional_bias,
            "adx": adx,
            "atr_percent": atr_percent,
            "range_compression": range_compression,
            "trend_up_score": round(trend_up_score, 4),
            "trend_down_score": round(trend_down_score, 4),
            "range_score": round(range_score, 4),
            "volatility_score": round(volatility_score, 4),
        }

        return MarketRegimeRecommendation(
            regime=regime,
            confidence=round(confidence, 4),
            risk_multiplier=round(risk_multiplier, 4),
            position_size_multiplier=round(position_size_multiplier, 4),
            reasons=reasons,
            signals=signals,
        )

    def analyze(self, metrics: Any = None) -> MarketRegimeRecommendation:
        """Alias em ingles para `recommend`."""
        return self.recommend(metrics)

    def classify(self, metrics: Any = None) -> MarketRegimeRecommendation:
        """Alias semantico para classificacao de regime de mercado."""
        return self.recommend(metrics)

    def _extract_metrics(self, source: Any) -> dict[str, Any]:
        if source is None:
            return {}

        raw_values: dict[str, Any] = {}
        recognized_metrics = 0

        for field_name in (
            "trend_strength",
            "volatility",
            "directional_bias",
            "adx",
            "atr_percent",
            "range_compression",
        ):
            raw_value = _get_value(source, field_name, None)
            if raw_value is None:
                continue

            coerced = _coerce_float(raw_value, field_name)
            if field_name in {"volatility", "adx", "atr_percent", "range_compression"}:
                if coerced < 0:
                    raise ValueError(f"{field_name} nao pode ser negativo")

            if field_name in {"trend_strength", "directional_bias"}:
                value = _scale_percent_like(coerced)
            else:
                value = coerced

            raw_values[field_name] = value
            recognized_metrics += 1

        raw_values["recognized_metrics"] = recognized_metrics
        return raw_values

    def _fallback_recommendation(self) -> MarketRegimeRecommendation:
        return MarketRegimeRecommendation(
            regime=MarketRegime.RANGING,
            confidence=0.15,
            risk_multiplier=1.0,
            position_size_multiplier=1.0,
            reasons=["Entrada insuficiente para classificar regime com confianca."],
            signals={
                "recognized_metrics": 0.0,
                "trend_strength": None,
                "volatility": None,
                "directional_bias": None,
                "adx": None,
                "atr_percent": None,
                "range_compression": None,
                "trend_up_score": 0.0,
                "trend_down_score": 0.0,
                "range_score": 0.0,
                "volatility_score": 0.0,
            },
        )

    def _build_volatility_score(
        self,
        volatility: float | None,
        atr_percent: float | None,
    ) -> float:
        components: list[float] = []
        if volatility is not None:
            components.append(_clamp(volatility, 0.0, 100.0))
        if atr_percent is not None:
            components.append(_clamp(_scale_percent_like(atr_percent), 0.0, 100.0))

        if not components:
            return 0.0
        return sum(components) / len(components)

    def _build_trend_score(
        self,
        *,
        trend_strength: float | None,
        directional_bias: float | None,
        adx: float | None,
        range_compression: float | None,
        volatility: float | None,
        direction: str,
    ) -> float:
        orientation = 1.0 if direction == "up" else -1.0
        score = 0.0

        if trend_strength is not None:
            score += max(0.0, orientation * trend_strength)
        if directional_bias is not None:
            score += max(0.0, orientation * directional_bias)
        if adx is not None:
            score += max(0.0, adx - self._ADX_TREND_THRESHOLD) * 0.75
        if range_compression is not None:
            score += max(0.0, 50.0 - range_compression) * 0.25
        if volatility is not None:
            score += max(0.0, 55.0 - volatility) * 0.10

        return score

    def _build_range_score(
        self,
        *,
        trend_strength: float | None,
        volatility: float | None,
        adx: float | None,
        range_compression: float | None,
    ) -> float:
        score = 0.0
        if range_compression is not None:
            score += range_compression
        if trend_strength is not None:
            score += max(0.0, 40.0 - abs(trend_strength)) * 0.7
        if volatility is not None:
            score += max(0.0, 55.0 - volatility) * 0.35
        if adx is not None:
            score += max(0.0, 28.0 - adx) * 0.65
        return score

    def _classify_regime(
        self,
        *,
        trend_up_score: float,
        trend_down_score: float,
        range_score: float,
        volatility_score: float,
        trend_strength: float | None,
        directional_bias: float | None,
        adx: float | None,
        volatility: float | None,
        atr_percent: float | None,
        range_compression: float | None,
    ) -> MarketRegime:
        strong_volatility = volatility_score >= self._VOLATILITY_HIGH_THRESHOLD
        atr_extreme = atr_percent is not None and atr_percent >= self._ATR_HIGH_THRESHOLD
        volatility_is_dominant = strong_volatility or atr_extreme

        if volatility_is_dominant:
            trend_best = max(trend_up_score, trend_down_score)
            if trend_best < range_score * 0.75:
                return MarketRegime.HIGH_VOLATILITY

        up_qualifies = self._is_trend_direction(
            trend_score=trend_up_score,
            trend_strength=trend_strength,
            directional_bias=directional_bias,
            adx=adx,
            direction="up",
        )
        down_qualifies = self._is_trend_direction(
            trend_score=trend_down_score,
            trend_strength=trend_strength,
            directional_bias=directional_bias,
            adx=adx,
            direction="down",
        )

        if up_qualifies and (not down_qualifies or trend_up_score >= trend_down_score):
            return MarketRegime.TRENDING_UP
        if down_qualifies and (not up_qualifies or trend_down_score > trend_up_score):
            return MarketRegime.TRENDING_DOWN

        if self._is_ranging(
            trend_strength=trend_strength,
            volatility=volatility,
            adx=adx,
            range_compression=range_compression,
            range_score=range_score,
        ):
            return MarketRegime.RANGING

        if trend_up_score >= trend_down_score and trend_up_score >= range_score:
            return MarketRegime.TRENDING_UP
        if trend_down_score > trend_up_score and trend_down_score >= range_score:
            return MarketRegime.TRENDING_DOWN
        if volatility_is_dominant:
            return MarketRegime.HIGH_VOLATILITY
        return MarketRegime.RANGING

    def _is_trend_direction(
        self,
        *,
        trend_score: float,
        trend_strength: float | None,
        directional_bias: float | None,
        adx: float | None,
        direction: str,
    ) -> bool:
        if trend_score <= 0:
            return False

        orientation = 1.0 if direction == "up" else -1.0
        trend_component = 0.0 if trend_strength is None else orientation * trend_strength
        bias_component = 0.0 if directional_bias is None else orientation * directional_bias

        if trend_component <= 0 and bias_component <= 0:
            return False

        aligned = trend_component > 0 or bias_component > 0
        strong_trend = (
            (trend_strength is not None and orientation * trend_strength >= self._TREND_STRENGTH_THRESHOLD)
            or (directional_bias is not None and orientation * directional_bias >= 35.0)
        )
        adx_support = adx is not None and adx >= self._ADX_TREND_THRESHOLD
        return aligned and (strong_trend or adx_support)

    def _is_ranging(
        self,
        *,
        trend_strength: float | None,
        volatility: float | None,
        adx: float | None,
        range_compression: float | None,
        range_score: float,
    ) -> bool:
        compression_support = range_compression is not None and range_compression >= self._RANGE_COMPRESSION_THRESHOLD
        weak_trend = trend_strength is None or abs(trend_strength) <= self._LOW_TREND_THRESHOLD
        weak_adx = adx is None or adx <= self._LOW_ADX_THRESHOLD
        controlled_volatility = volatility is None or volatility <= 65.0
        return compression_support or (weak_trend and weak_adx and controlled_volatility and range_score > 0)

    def _calculate_confidence(
        self,
        *,
        regime: MarketRegime,
        recognized_metrics: int,
        trend_up_score: float,
        trend_down_score: float,
        range_score: float,
        volatility_score: float,
        trend_strength: float | None,
        directional_bias: float | None,
        adx: float | None,
        volatility: float | None,
        atr_percent: float | None,
        range_compression: float | None,
    ) -> float:
        coverage = _clamp(recognized_metrics / 6.0, 0.0, 1.0)
        if regime == MarketRegime.HIGH_VOLATILITY:
            support = _clamp(volatility_score / 100.0, 0.0, 1.0)
            atr_support = 0.0 if atr_percent is None else _clamp(atr_percent / 6.0, 0.0, 1.0)
            confidence = 0.35 + 0.4 * support + 0.15 * atr_support + 0.1 * coverage
            if volatility is not None and volatility >= self._VOLATILITY_HIGH_THRESHOLD:
                confidence += 0.05
            return _clamp(confidence, 0.0, 1.0)

        if regime == MarketRegime.TRENDING_UP:
            return self._trend_confidence(
                trend_score=trend_up_score,
                trend_strength=trend_strength,
                directional_bias=directional_bias,
                adx=adx,
                volatility_score=volatility_score,
                coverage=coverage,
                direction="up",
            )

        if regime == MarketRegime.TRENDING_DOWN:
            return self._trend_confidence(
                trend_score=trend_down_score,
                trend_strength=trend_strength,
                directional_bias=directional_bias,
                adx=adx,
                volatility_score=volatility_score,
                coverage=coverage,
                direction="down",
            )

        compression = 0.0 if range_compression is None else _clamp(range_compression / 100.0, 0.0, 1.0)
        weak_trend = 0.0 if trend_strength is None else _clamp((40.0 - abs(trend_strength)) / 40.0, 0.0, 1.0)
        weak_adx = 0.0 if adx is None else _clamp((28.0 - adx) / 28.0, 0.0, 1.0)
        low_vol = 0.0 if volatility is None else _clamp((60.0 - volatility) / 60.0, 0.0, 1.0)
        confidence = 0.30 + 0.35 * compression + 0.15 * weak_trend + 0.10 * weak_adx + 0.10 * low_vol + 0.10 * coverage
        if regime == MarketRegime.RANGING and range_score > 0:
            confidence += 0.05
        return _clamp(confidence, 0.0, 1.0)

    def _trend_confidence(
        self,
        *,
        trend_score: float,
        trend_strength: float | None,
        directional_bias: float | None,
        adx: float | None,
        volatility_score: float,
        coverage: float,
        direction: str,
    ) -> float:
        orientation = 1.0 if direction == "up" else -1.0
        trend_component = 0.0 if trend_strength is None else max(0.0, orientation * trend_strength) / 100.0
        bias_component = 0.0 if directional_bias is None else max(0.0, orientation * directional_bias) / 100.0
        adx_component = 0.0 if adx is None else _clamp((adx - self._ADX_TREND_THRESHOLD) / 30.0, 0.0, 1.0)
        balance_penalty = 0.0
        if trend_strength is not None and directional_bias is not None:
            same_side = (trend_strength >= 0 and directional_bias >= 0) or (
                trend_strength <= 0 and directional_bias <= 0
            )
            if orientation > 0:
                same_side = trend_strength >= 0 and directional_bias >= 0
            else:
                same_side = trend_strength <= 0 and directional_bias <= 0
            balance_penalty = 0.1 if same_side else 0.0

        volatility_penalty = _clamp(volatility_score / 200.0, 0.0, 0.25)
        confidence = 0.32 + 0.30 * trend_component + 0.22 * bias_component + 0.16 * adx_component + 0.10 * coverage
        confidence += balance_penalty
        confidence -= volatility_penalty
        return _clamp(confidence, 0.0, 1.0)

    def _build_adjustments(
        self,
        *,
        regime: MarketRegime,
        confidence: float,
        trend_strength: float | None,
        directional_bias: float | None,
        adx: float | None,
        volatility: float | None,
        atr_percent: float | None,
        range_compression: float | None,
        trend_up_score: float,
        trend_down_score: float,
        range_score: float,
        volatility_score: float,
    ) -> tuple[float, float, list[str]]:
        reasons: list[str] = []

        if regime == MarketRegime.HIGH_VOLATILITY:
            vol_part = _clamp(volatility_score / 100.0, 0.0, 1.0)
            atr_part = 0.0 if atr_percent is None else _clamp(atr_percent / 6.0, 0.0, 1.0)
            risk_multiplier = _clamp(1.20 + 0.55 * vol_part + 0.10 * atr_part, 1.0, 1.85)
            position_size_multiplier = _clamp(0.85 - 0.35 * confidence, 0.40, 0.85)
            reasons.append("Volatilidade elevada indica ajuste conservador de risco.")
            if volatility is not None:
                reasons.append(f"Volatilidade observada em {volatility:.2f}.")
            if atr_percent is not None:
                reasons.append(f"ATR percentual em {atr_percent:.2f}.")
            return risk_multiplier, position_size_multiplier, reasons

        if regime == MarketRegime.TRENDING_UP:
            trend_part = 0.0 if trend_strength is None else _clamp(trend_strength / 100.0, 0.0, 1.0)
            bias_part = 0.0 if directional_bias is None else _clamp(directional_bias / 100.0, 0.0, 1.0)
            adx_part = 0.0 if adx is None else _clamp(adx / 50.0, 0.0, 1.0)
            risk_multiplier = _clamp(0.92 + 0.12 * (1.0 - confidence) - 0.05 * adx_part, 0.78, 1.08)
            position_size_multiplier = _clamp(1.00 + 0.30 * confidence + 0.10 * trend_part + 0.05 * bias_part, 1.00, 1.35)
            reasons.append("Tendencia de alta favorece posicao compradora.")
            if trend_strength is not None:
                reasons.append(f"Trend strength positivo em {trend_strength:.2f}.")
            if directional_bias is not None:
                reasons.append(f"Directional bias alinhado em {directional_bias:.2f}.")
            if adx is not None:
                reasons.append(f"ADX sustentando tendencia em {adx:.2f}.")
            return risk_multiplier, position_size_multiplier, reasons

        if regime == MarketRegime.TRENDING_DOWN:
            trend_part = 0.0 if trend_strength is None else _clamp(abs(trend_strength) / 100.0, 0.0, 1.0)
            bias_part = 0.0 if directional_bias is None else _clamp(abs(directional_bias) / 100.0, 0.0, 1.0)
            adx_part = 0.0 if adx is None else _clamp(adx / 50.0, 0.0, 1.0)
            risk_multiplier = _clamp(0.92 + 0.12 * (1.0 - confidence) - 0.05 * adx_part, 0.78, 1.08)
            position_size_multiplier = _clamp(1.00 + 0.30 * confidence + 0.10 * trend_part + 0.05 * bias_part, 1.00, 1.35)
            reasons.append("Tendencia de baixa favorece posicao vendedora.")
            if trend_strength is not None:
                reasons.append(f"Trend strength negativo em {trend_strength:.2f}.")
            if directional_bias is not None:
                reasons.append(f"Directional bias alinhado em {directional_bias:.2f}.")
            if adx is not None:
                reasons.append(f"ADX sustentando tendencia em {adx:.2f}.")
            return risk_multiplier, position_size_multiplier, reasons

        compression = 0.0 if range_compression is None else _clamp(range_compression / 100.0, 0.0, 1.0)
        risk_multiplier = _clamp(0.82 - 0.08 * confidence - 0.05 * compression, 0.65, 0.95)
        position_size_multiplier = _clamp(0.68 + 0.18 * confidence - 0.05 * compression, 0.50, 0.95)
        reasons.append("Mercado lateral pede metas e stops mais contidos.")
        if range_compression is not None:
            reasons.append(f"Range compression em {range_compression:.2f}.")
        if adx is not None:
            reasons.append(f"ADX baixo em {adx:.2f}.")
        if volatility is not None:
            reasons.append(f"Volatilidade controlada em {volatility:.2f}.")
        return risk_multiplier, position_size_multiplier, reasons

__all__ = [
    "MarketRegime",
    "MarketRegimeAdapter",
    "MarketRegimeRecommendation",
]
