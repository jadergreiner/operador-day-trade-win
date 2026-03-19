"""Politica operacional baseada no contexto estruturado da abertura."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

DEFAULT_HEAVYWEIGHTS = ("PETR4", "VALE3")
BUY_ACTIONS = {"BUY", "COMPRAR"}
SELL_ACTIONS = {"SELL", "VENDER"}
NEUTRAL_ACTIONS = {"", "AGUARDAR", "HOLD", "NEUTRO", "NONE"}


def _safe_text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "sim", "ativo", "on"}:
            return True
        if normalized in {"0", "false", "no", "nao", "off"}:
            return False
    return default


def _safe_float(value: Any, default: float | None = None) -> float | None:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return []


def normalize_action(action: Any) -> str:
    """Normaliza a acao textual para BUY, SELL ou NEUTRO."""
    normalized = _safe_text(action).upper()
    if normalized in BUY_ACTIONS:
        return "BUY"
    if normalized in SELL_ACTIONS:
        return "SELL"
    if normalized in NEUTRAL_ACTIONS:
        return "NEUTRO"
    return normalized


def _extract_features(source: Any) -> dict[str, Any]:
    if source is None:
        return {}
    if isinstance(source, Mapping):
        return dict(source)
    features = getattr(source, "features", None)
    if isinstance(features, Mapping):
        return dict(features)
    to_dict = getattr(source, "to_dict", None)
    if callable(to_dict):
        try:
            payload = to_dict()
        except Exception:
            payload = {}
        if isinstance(payload, Mapping):
            return dict(payload)
    return {}


def _nested_get(mapping: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, Mapping):
            return default
        current = current.get(key)
    return current if current is not None else default


@dataclass(slots=True)
class OpeningContextPolicy:
    """Snapshot normalizado das flags operacionais da abertura."""

    regime_macro: str = ""
    vies_intraday: str = ""
    watchlist: list[str] = field(default_factory=list)
    heavyweights: list[str] = field(default_factory=list)
    kill_switch_ativo: bool = False
    kill_switch_reason: str = ""
    prompt_abertura_agentes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime_macro": self.regime_macro,
            "vies_intraday": self.vies_intraday,
            "watchlist": list(self.watchlist),
            "heavyweights": list(self.heavyweights),
            "kill_switch_ativo": self.kill_switch_ativo,
            "kill_switch_reason": self.kill_switch_reason,
            "prompt_abertura_agentes": self.prompt_abertura_agentes,
        }


@dataclass(slots=True)
class OpeningContextGateResult:
    """Resultado da avaliacao do contexto de abertura para uma acao."""

    allow_entry: bool
    normalized_action: str
    policy: OpeningContextPolicy
    reasons: list[str] = field(default_factory=list)
    required_confirmations: list[str] = field(default_factory=list)
    confidence_used: float | None = None
    alignment_used: float | None = None
    live_market_confirmation: dict[str, Any] = field(default_factory=dict)

    @property
    def summary(self) -> str:
        if self.allow_entry:
            if self.reasons:
                return ", ".join(self.reasons)
            return "contexto_abertura_sem_restricoes"
        if self.reasons:
            return ", ".join(self.reasons)
        return "contexto_abertura_bloqueado"

    def to_context_payload(self) -> dict[str, Any]:
        payload = self.policy.to_dict()
        payload.update(
            {
                "acao_normalizada": self.normalized_action,
                "contexto_abertura_liberado": self.allow_entry,
                "contexto_abertura_motivos": list(self.reasons),
                "required_confirmations": list(self.required_confirmations),
                "live_market_confirmation": _safe_mapping(
                    self.live_market_confirmation
                ),
            }
        )
        if self.confidence_used is not None:
            payload["confidence_used"] = self.confidence_used
        if self.alignment_used is not None:
            payload["alignment_used"] = self.alignment_used
        return payload


def normalize_opening_context(source: Any) -> OpeningContextPolicy:
    """Extrai um contrato simples a partir do runtime/features/context."""
    features = _extract_features(source)
    operational_context = _safe_mapping(features.get("contexto_operacional"))
    watchlist = [
        _safe_text(item).upper()
        for item in (
            _safe_list(features.get("watchlist"))
            or _safe_list(operational_context.get("watchlist"))
        )
        if _safe_text(item)
    ]
    heavyweights = [ticker for ticker in DEFAULT_HEAVYWEIGHTS if ticker in watchlist]
    if not heavyweights:
        heavyweights = list(DEFAULT_HEAVYWEIGHTS)

    regime_macro = _safe_text(
        features.get("regime_macro")
        or _nested_get(operational_context, "market_state", "regime_macro", default="")
    )
    vies_intraday = _safe_text(
        features.get("vies_intraday")
        or features.get("intraday_bias")
        or _nested_get(operational_context, "market_state", "intraday_bias", default="")
    )
    kill_switch_reason = _safe_text(
        features.get("kill_switch_reason") or features.get("reason")
    )

    return OpeningContextPolicy(
        regime_macro=regime_macro,
        vies_intraday=vies_intraday,
        watchlist=watchlist,
        heavyweights=heavyweights,
        kill_switch_ativo=_safe_bool(
            features.get("kill_switch_ativo", features.get("active_kill_switch"))
        ),
        kill_switch_reason=kill_switch_reason,
        prompt_abertura_agentes=_safe_text(features.get("prompt_abertura_agentes")),
    )


def evaluate_opening_context_gate(
    action: Any,
    context: Any,
    *,
    confidence: float | None = None,
    alignment: float | None = None,
    market_confirmation: Any | None = None,
) -> OpeningContextGateResult:
    """Aplica as flags estruturadas do contexto de abertura sobre uma acao."""
    normalized_action = normalize_action(action)
    policy = normalize_opening_context(context)
    allow_entry = normalized_action in {"BUY", "SELL"}
    reasons: list[str] = []
    required_confirmations: list[str] = []
    confidence_used = _safe_float(confidence)
    alignment_used = _safe_float(alignment)
    vies_upper = policy.vies_intraday.upper()
    live_market_confirmation = _safe_mapping(market_confirmation)

    if normalized_action == "NEUTRO":
        return OpeningContextGateResult(
            allow_entry=True,
            normalized_action=normalized_action,
            policy=policy,
            reasons=["acao_neutra_sem_bloqueio"],
            confidence_used=confidence_used,
            alignment_used=alignment_used,
            live_market_confirmation=live_market_confirmation,
        )

    if policy.kill_switch_ativo:
        reasons.append("kill_switch_abertura_ativo")
        if policy.kill_switch_reason:
            reasons.append(policy.kill_switch_reason)
        allow_entry = False

    if normalized_action == "BUY":
        required_confirmations = list(policy.heavyweights)
        for symbol_name in ("DOL", "IBOV", "EWZ"):
            if symbol_name not in required_confirmations:
                required_confirmations.append(symbol_name)
        if "BAIXISTA" in vies_upper:
            reasons.append("vies_intraday_baixista")
            if confidence_used is None or confidence_used < 0.72:
                reasons.append("compra_sem_confirmacao_contextual")
                allow_entry = False
            if alignment_used is not None and alignment_used < 0.65:
                reasons.append("compra_sem_alinhamento_suficiente")
                allow_entry = False
        elif "ALTISTA" in vies_upper:
            reasons.append("compra_alinhada_ao_vies")
        elif policy.watchlist:
            reasons.append("compra_monitorando_watchlist")

        if live_market_confirmation:
            if live_market_confirmation.get("buy_confirmed") is True:
                reasons.append("compra_confirmada_live")
            else:
                reasons.append("compra_sem_confirmacao_live")
                allow_entry = False
            if live_market_confirmation.get("monitors_positive"):
                reasons.append(
                    "monitores_favoraveis:"
                    + ",".join(
                        str(item)
                        for item in live_market_confirmation.get(
                            "monitors_positive", []
                        )
                    )
                )
            if live_market_confirmation.get("monitors_negative"):
                reasons.append(
                    "monitores_contrarios:"
                    + ",".join(
                        str(item)
                        for item in live_market_confirmation.get(
                            "monitors_negative", []
                        )
                    )
                )

    elif normalized_action == "SELL":
        required_confirmations = ["DOL", "IBOV", "EWZ"]
        if "BAIXISTA" in vies_upper:
            reasons.append("venda_alinhada_ao_vies")
        elif "ALTISTA" in vies_upper:
            reasons.append("vies_intraday_altista")
            if confidence_used is None or confidence_used < 0.72:
                reasons.append("venda_sem_confirmacao_contextual")
                allow_entry = False
            if alignment_used is not None and alignment_used < 0.65:
                reasons.append("venda_sem_alinhamento_suficiente")
                allow_entry = False
        elif policy.watchlist:
            reasons.append("venda_monitorando_watchlist")

        if live_market_confirmation:
            if live_market_confirmation.get("sell_quality_confirmed") is True:
                reasons.append("venda_confirmada_live")
            elif "BAIXISTA" in vies_upper:
                reasons.append("venda_sem_confirmacao_live")
                allow_entry = False
            if live_market_confirmation.get("monitors_positive"):
                reasons.append(
                    "monitores_favoraveis:"
                    + ",".join(
                        str(item)
                        for item in live_market_confirmation.get(
                            "monitors_positive", []
                        )
                    )
                )
            if live_market_confirmation.get("monitors_negative"):
                reasons.append(
                    "monitores_contrarios:"
                    + ",".join(
                        str(item)
                        for item in live_market_confirmation.get(
                            "monitors_negative", []
                        )
                    )
                )

    if allow_entry and not reasons:
        reasons.append("contexto_abertura_neutro")

    return OpeningContextGateResult(
        allow_entry=allow_entry,
        normalized_action=normalized_action,
        policy=policy,
        reasons=reasons,
        required_confirmations=required_confirmations,
        confidence_used=confidence_used,
        alignment_used=alignment_used,
        live_market_confirmation=live_market_confirmation,
    )


__all__ = [
    "OpeningContextGateResult",
    "OpeningContextPolicy",
    "evaluate_opening_context_gate",
    "normalize_action",
    "normalize_opening_context",
]
