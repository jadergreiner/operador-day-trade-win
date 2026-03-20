"""Contexto decisorio com score continuo e hard guards estruturais."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _safe_text(value: Any, default: str = "") -> str:
    text = str(value).strip() if value is not None else ""
    return text if text else default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        coerced = float(value)
    except (TypeError, ValueError):
        return default
    if coerced != coerced:  # NaN
        return default
    return coerced


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        coerced = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(0, coerced)


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "sim", "on", "ativo"}:
            return True
        if normalized in {"0", "false", "no", "nao", "off", "inativo"}:
            return False
    return default


def _safe_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return []


def _normalize_confidence(value: Any, default: float = 0.0) -> float:
    """Normaliza confidence para a faixa 0-1."""
    confidence = _safe_float(value, default)
    if confidence < 0:
        return 0.0
    if confidence > 1.0 and confidence <= 100.0:
        confidence /= 100.0
    return _clamp(confidence, 0.0, 1.0)


def _normalize_signed_score(value: Any, default: float = 0.0) -> float:
    """Normaliza score para a faixa -1 a 1."""
    score = _safe_float(value, default)
    if abs(score) > 1.0 and abs(score) <= 100.0:
        score /= 100.0
    return _clamp(score, -1.0, 1.0)


def _normalize_action(value: Any) -> str:
    """Normaliza a acao para BUY, SELL ou NEUTRO."""
    action = _safe_text(value, "NEUTRO").upper()
    if action in {"", "NONE", "NEUTRO", "HOLD", "AGUARDAR", "AGUARDA"}:
        return "NEUTRO"
    if action in {"BUY", "COMPRA", "COMPRAR", "LONG"}:
        return "BUY"
    if action in {"SELL", "VENDA", "VENDER", "SHORT"}:
        return "SELL"
    return action


def _normalize_diario_direction(value: Any) -> str:
    """Normaliza a direcao diaria para ALTISTA, BAIXISTA ou NEUTRO."""
    direction = _safe_text(value, "NEUTRO").upper()
    if direction in {"", "NONE", "NEUTRO", "HOLD", "AGUARDAR", "AGUARDA"}:
        return "NEUTRO"
    if direction in {"ALTISTA", "ALTA", "BULL", "BULLISH", "UP"}:
        return "ALTISTA"
    if direction in {"BAIXISTA", "BAIXA", "BEAR", "BEARISH", "DOWN"}:
        return "BAIXISTA"
    if "ALT" in direction or "ALTA" in direction:
        return "ALTISTA"
    if "BAIX" in direction or "BEAR" in direction or "SHORT" in direction:
        return "BAIXISTA"
    return direction


def _infer_diario_alignment(action: str, diario_direction: str) -> float:
    """Infere alinhamento direcional simples entre acao e diario."""
    if action not in {"BUY", "SELL"}:
        return 0.0
    if diario_direction == "NEUTRO":
        return 0.0
    if action == "BUY":
        return 1.0 if diario_direction == "ALTISTA" else -1.0 if diario_direction == "BAIXISTA" else 0.0
    return 1.0 if diario_direction == "BAIXISTA" else -1.0 if diario_direction == "ALTISTA" else 0.0


def _risk_reward_signal(risk_reward: float) -> float:
    """Converte risk/reward em sinal continuo [-1, 1]."""
    return _clamp(risk_reward - 1.0, -1.0, 1.0)


def _adx_signal(adx: float) -> float:
    """Classifica ADX em um sinal simples de tendencia."""
    if adx <= 0.0:
        return 0.0
    if adx < 12.0:
        return -0.20
    if adx < 18.0:
        return -0.05
    if adx < 25.0:
        return 0.08
    if adx < 40.0:
        return 0.15
    return 0.10


def _append_reason(reason_codes: list[str], code: str) -> None:
    if code and code not in reason_codes:
        reason_codes.append(code)


def _update_flag(feature_flags: dict[str, Any], key: str, value: Any) -> None:
    feature_flags[key] = value


@dataclass(slots=True)
class DecisionContext:
    """Snapshot normalizado do contexto decisorio."""

    # Compatibilidade legada (scripts de runtime)
    raw_confidence: float = 0.0
    adjusted_confidence: float | None = None
    context_penalty: float = 0.0
    penalty: float = 0.0
    opening_context: Any = None
    normalized_context: Any = None
    market_confirmation: dict[str, Any] = field(default_factory=dict)
    diario_payload: dict[str, Any] = field(default_factory=dict)
    volatility: float | None = None

    module_name: str = ""
    action: str = "NEUTRO"
    model_confidence: float = 0.0
    macro_score: float = 0.0
    diario_direction: str = "NEUTRO"
    diario_confidence: float = 0.0
    diario_alignment: float = 0.0
    diario_hold_flag: bool = False
    diario_neutral_flag: bool = True
    micro_invalidated_count: int = 0
    micro_contra_indicado_count: int = 0
    micro_furou_count: int = 0
    risk_reward: float = 0.0
    adx: float = 0.0
    atr: float = 0.0
    reason_codes: list[str] = field(default_factory=list)
    feature_flags: dict[str, Any] = field(default_factory=dict)
    context_score: float = 0.0
    confidence_penalty: float = 0.0
    trade_size_factor: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """Retorna o contexto em formato serializavel."""
        return asdict(self)

    para_dict = to_dict


def build_context_features(**kwargs: Any) -> DecisionContext:
    """Constrói um contexto decisorio com defaults seguros."""
    module_name = _safe_text(kwargs.get("module_name"), "")
    action = _normalize_action(kwargs.get("action"))
    raw_confidence = _normalize_confidence(
        kwargs.get("raw_confidence", kwargs.get("model_confidence"))
    )
    model_confidence = _normalize_confidence(
        kwargs.get("model_confidence", raw_confidence)
    )
    macro_score = _normalize_signed_score(kwargs.get("macro_score"))
    diario_direction = _normalize_diario_direction(kwargs.get("diario_direction"))
    diario_confidence = _normalize_confidence(kwargs.get("diario_confidence"))
    diario_alignment = kwargs.get("diario_alignment")
    if diario_alignment is None:
        diario_alignment = _infer_diario_alignment(action, diario_direction)
    diario_alignment = _normalize_signed_score(diario_alignment)

    diario_hold_flag = _safe_bool(kwargs.get("diario_hold_flag"), False)
    diario_neutral_flag = _safe_bool(kwargs.get("diario_neutral_flag"), diario_direction == "NEUTRO")

    micro_invalidated_count = _safe_int(kwargs.get("micro_invalidated_count"))
    micro_contra_indicado_count = _safe_int(kwargs.get("micro_contra_indicado_count"))
    micro_furou_count = _safe_int(kwargs.get("micro_furou_count"))
    risk_reward = max(0.0, _safe_float(kwargs.get("risk_reward"), 0.0))
    adx = max(0.0, _safe_float(kwargs.get("adx"), 0.0))
    atr = max(0.0, _safe_float(kwargs.get("atr"), 0.0))

    reason_codes = [str(item).strip() for item in _safe_list(kwargs.get("reason_codes")) if str(item).strip()]
    feature_flags = _safe_mapping(kwargs.get("feature_flags"))

    context_score = _clamp(_safe_float(kwargs.get("context_score"), 0.0), -1.0, 1.0)
    confidence_penalty = _clamp(_safe_float(kwargs.get("confidence_penalty"), 0.0), 0.0, 1.0)
    trade_size_factor = _clamp(_safe_float(kwargs.get("trade_size_factor"), 1.0), 0.0, 2.0)

    return DecisionContext(
        raw_confidence=raw_confidence,
        adjusted_confidence=kwargs.get("adjusted_confidence"),
        context_penalty=confidence_penalty,
        penalty=confidence_penalty,
        opening_context=kwargs.get("opening_context"),
        normalized_context=kwargs.get("normalized_context"),
        market_confirmation=_safe_mapping(kwargs.get("market_confirmation")),
        diario_payload=_safe_mapping(kwargs.get("diario_payload")),
        volatility=kwargs.get("volatility"),
        module_name=module_name,
        action=action,
        model_confidence=model_confidence,
        macro_score=macro_score,
        diario_direction=diario_direction,
        diario_confidence=diario_confidence,
        diario_alignment=diario_alignment,
        diario_hold_flag=diario_hold_flag,
        diario_neutral_flag=diario_neutral_flag,
        micro_invalidated_count=micro_invalidated_count,
        micro_contra_indicado_count=micro_contra_indicado_count,
        micro_furou_count=micro_furou_count,
        risk_reward=risk_reward,
        adx=adx,
        atr=atr,
        reason_codes=reason_codes,
        feature_flags=feature_flags,
        context_score=context_score,
        confidence_penalty=confidence_penalty,
        trade_size_factor=trade_size_factor,
    )


def compute_context_score(ctx: DecisionContext) -> DecisionContext:
    """Calcula score continuo em [-1, 1] e atualiza sinais derivados."""
    reason_codes = ctx.reason_codes
    feature_flags = ctx.feature_flags

    action = _normalize_action(ctx.action)
    diario_direction = _normalize_diario_direction(ctx.diario_direction)
    model_confidence = _normalize_confidence(ctx.model_confidence)
    macro_score = _normalize_signed_score(ctx.macro_score)
    diario_confidence = _normalize_confidence(ctx.diario_confidence)
    diario_alignment = _normalize_signed_score(ctx.diario_alignment)
    risk_reward_signal = _risk_reward_signal(max(0.0, ctx.risk_reward))
    adx_signal = _adx_signal(max(0.0, ctx.adx))
    atr_valid = ctx.atr > 0.0

    micro_invalidated = min(ctx.micro_invalidated_count, 3)
    micro_contra_indicado = min(ctx.micro_contra_indicado_count, 3)
    micro_furou = min(ctx.micro_furou_count, 3)
    micro_pressure_total = micro_invalidated + micro_contra_indicado + micro_furou

    score = 0.0

    model_signal = (model_confidence - 0.5) * 0.45
    score += model_signal
    _update_flag(feature_flags, "model_confidence_signal", model_signal)
    if model_confidence >= 0.7:
        _append_reason(reason_codes, "modelo_confianca_alta")
        _update_flag(feature_flags, "modelo_confianca_alta", True)
    elif model_confidence <= 0.4:
        _append_reason(reason_codes, "modelo_confianca_baixa")
        _update_flag(feature_flags, "modelo_confianca_baixa", True)
    else:
        _update_flag(feature_flags, "modelo_confianca_neutra", True)

    macro_signal = macro_score * 0.20
    score += macro_signal
    _update_flag(feature_flags, "macro_score_normalizado", macro_score)
    _update_flag(feature_flags, "macro_score_signal", macro_signal)
    if macro_score >= 0.15:
        _append_reason(reason_codes, "macro_favoravel")
        _update_flag(feature_flags, "macro_favoravel", True)
    elif macro_score <= -0.15:
        _append_reason(reason_codes, "macro_desfavoravel")
        _update_flag(feature_flags, "macro_desfavoravel", True)

    diario_signal = diario_alignment * (0.20 + diario_confidence * 0.20)
    score += diario_signal
    _update_flag(feature_flags, "diario_alignment", diario_alignment)
    _update_flag(feature_flags, "diario_alignment_signal", diario_signal)
    _update_flag(feature_flags, "diario_direction", diario_direction)
    _update_flag(feature_flags, "diario_confidence", diario_confidence)
    if ctx.diario_hold_flag:
        score -= 0.35
        _append_reason(reason_codes, "diario_hold_ativo")
        _update_flag(feature_flags, "diario_hold_ativo", True)
    elif diario_direction == "NEUTRO" or ctx.diario_neutral_flag:
        score -= 0.05
        _append_reason(reason_codes, "diario_neutro")
        _update_flag(feature_flags, "diario_neutro", True)
    elif diario_alignment > 0:
        _append_reason(reason_codes, "diario_alinhado")
        _update_flag(feature_flags, "diario_alinhado", True)
    elif diario_alignment < 0:
        _append_reason(reason_codes, "diario_contrario")
        _update_flag(feature_flags, "diario_contrario", True)

    rr_signal = risk_reward_signal * 0.30
    score += rr_signal
    _update_flag(feature_flags, "risk_reward_signal", risk_reward_signal)
    if risk_reward_signal >= 0.2:
        _append_reason(reason_codes, "risk_reward_favoravel")
        _update_flag(feature_flags, "risk_reward_favoravel", True)
    elif risk_reward_signal <= -0.2:
        _append_reason(reason_codes, "risk_reward_desfavoravel")
        _update_flag(feature_flags, "risk_reward_desfavoravel", True)
    else:
        _update_flag(feature_flags, "risk_reward_neutro", True)

    score += adx_signal
    _update_flag(feature_flags, "adx_signal", adx_signal)
    if adx_signal >= 0.10:
        _append_reason(reason_codes, "adx_trend_forte")
        _update_flag(feature_flags, "adx_trend_forte", True)
    elif adx_signal < 0.0:
        _append_reason(reason_codes, "adx_fraco")
        _update_flag(feature_flags, "adx_fraco", True)
    else:
        _update_flag(feature_flags, "adx_neutro", True)

    if atr_valid:
        score += 0.02
        _append_reason(reason_codes, "atr_valido")
        _update_flag(feature_flags, "atr_valido", True)
    else:
        score -= 0.08
        _append_reason(reason_codes, "atr_invalido")
        _update_flag(feature_flags, "atr_invalido", True)

    if micro_invalidated:
        penalty = micro_invalidated * 0.06
        score -= penalty
        _append_reason(reason_codes, "micro_invalidados_presentes")
        _update_flag(feature_flags, "micro_invalidated_count", ctx.micro_invalidated_count)
        _update_flag(feature_flags, "micro_invalidated_penalty", penalty)

    if micro_contra_indicado:
        penalty = micro_contra_indicado * 0.10
        score -= penalty
        _append_reason(reason_codes, "micro_contra_indicados_presentes")
        _update_flag(feature_flags, "micro_contra_indicado_count", ctx.micro_contra_indicado_count)
        _update_flag(feature_flags, "micro_contra_indicado_penalty", penalty)

    if micro_furou:
        penalty = micro_furou * 0.12
        score -= penalty
        _append_reason(reason_codes, "micro_furou_presente")
        _update_flag(feature_flags, "micro_furou_count", ctx.micro_furou_count)
        _update_flag(feature_flags, "micro_furou_penalty", penalty)

    if action in {"BUY", "SELL"}:
        _update_flag(feature_flags, "action_normalizada", action)
        _update_flag(feature_flags, "acao_operacional", True)
    else:
        _update_flag(feature_flags, "acao_operacional", False)

    _update_flag(feature_flags, "micro_pressao_total", micro_pressure_total)
    _update_flag(feature_flags, "atr", ctx.atr)
    _update_flag(feature_flags, "adx", ctx.adx)
    _update_flag(feature_flags, "risk_reward", ctx.risk_reward)

    score = _clamp(score, -1.0, 1.0)
    ctx.context_score = score
    ctx.trade_size_factor = _clamp(1.0 + score * 0.5, 0.25, 1.20)
    ctx.context_penalty = _clamp(1.0 - score, 0.0, 1.0)
    ctx.penalty = ctx.context_penalty
    _update_flag(feature_flags, "context_score", score)
    _update_flag(feature_flags, "trade_size_factor", ctx.trade_size_factor)
    _update_flag(feature_flags, "context_penalty", ctx.context_penalty)
    _update_flag(feature_flags, "diario_direction_alinhado", diario_alignment > 0.0)
    _update_flag(feature_flags, "diario_direction_contrario", diario_alignment < 0.0)

    return ctx


def apply_context_to_confidence(*args: Any, **kwargs: Any) -> float:
    """Aplica penalidade de contexto sobre a confidence do modelo."""
    ctx: DecisionContext
    base_confidence: float | None = None

    if len(args) == 1 and isinstance(args[0], DecisionContext):
        ctx = args[0]
    elif len(args) == 2:
        if isinstance(args[0], DecisionContext):
            ctx = args[0]
            base_confidence = _normalize_confidence(args[1], ctx.model_confidence)
        else:
            base_confidence = _normalize_confidence(args[0])
            ctx = args[1]
    elif "context" in kwargs:
        ctx = kwargs["context"]
        if "confidence" in kwargs:
            base_confidence = _normalize_confidence(kwargs["confidence"])
    elif "ctx" in kwargs:
        ctx = kwargs["ctx"]
        if "confidence" in kwargs:
            base_confidence = _normalize_confidence(kwargs["confidence"])
    else:
        raise TypeError("apply_context_to_confidence requer contexto decisorio.")

    if not isinstance(ctx, DecisionContext):
        raise TypeError("contexto invalido para apply_context_to_confidence")

    if base_confidence is None:
        base_confidence = _normalize_confidence(
            ctx.model_confidence if ctx.model_confidence else ctx.raw_confidence
        )

    context_score = _clamp(_safe_float(ctx.context_score, 0.0), -1.0, 1.0)

    penalty = 0.0
    if context_score < 0.0:
        penalty += abs(context_score) * 0.45
    if ctx.diario_hold_flag:
        penalty += 0.15
    elif ctx.diario_neutral_flag:
        penalty += 0.05
    if ctx.micro_invalidated_count > 0:
        penalty += min(ctx.micro_invalidated_count, 3) * 0.03
    if ctx.micro_contra_indicado_count > 0:
        penalty += min(ctx.micro_contra_indicado_count, 3) * 0.04
    if ctx.micro_furou_count > 0:
        penalty += min(ctx.micro_furou_count, 3) * 0.05

    penalty = _clamp(penalty, 0.0, 0.75)
    adjusted_confidence = _clamp(base_confidence - penalty, 0.0, 1.0)

    ctx.raw_confidence = base_confidence
    ctx.model_confidence = base_confidence
    ctx.adjusted_confidence = adjusted_confidence
    ctx.confidence_penalty = penalty
    ctx.context_penalty = penalty
    ctx.penalty = penalty
    _update_flag(ctx.feature_flags, "confidence_penalty", penalty)
    _update_flag(ctx.feature_flags, "confidence_adjusted", adjusted_confidence)

    return adjusted_confidence


def build_decision_context(**kwargs: Any) -> DecisionContext:
    """Alias retrocompativel para runtimes que chamam build_decision_context."""
    return build_context_features(**kwargs)


def serialize_decision_context(ctx: DecisionContext) -> dict[str, Any]:
    """Converte o contexto em um dict serializavel."""
    return asdict(ctx)


def evaluate_hard_guards(
    *,
    mt5_connected: Any = None,
    market_data_ok: Any = None,
    rr_possible: Any = None,
    daily_limit_ok: Any = None,
    cooldown_ok: Any = None,
    **kwargs: Any,
) -> tuple[bool, str | None]:
    """Avalia apenas guardas estruturais essenciais."""
    aliases = kwargs
    checks = [
        ("mt5_connected", mt5_connected if mt5_connected is not None else aliases.get("mt5_connected")),
        ("market_data_ok", market_data_ok if market_data_ok is not None else aliases.get("market_data_ok")),
        ("rr_possible", rr_possible if rr_possible is not None else aliases.get("rr_possible")),
        ("daily_limit_ok", daily_limit_ok if daily_limit_ok is not None else aliases.get("daily_limit_ok")),
        ("cooldown_ok", cooldown_ok if cooldown_ok is not None else aliases.get("cooldown_ok")),
    ]

    for guard_name, guard_value in checks:
        if not _safe_bool(guard_value, False):
            return False, guard_name
    return True, None


__all__ = [
    "DecisionContext",
    "apply_context_to_confidence",
    "build_decision_context",
    "build_context_features",
    "compute_context_score",
    "evaluate_hard_guards",
    "serialize_decision_context",
]
