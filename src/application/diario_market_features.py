"""Canal intraday do Diario: snapshot auditavel + soft features para agentes."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from src.application.opening_context_policy import (
    normalize_action,
    normalize_opening_context,
)

TABLE_NAME = "diario_market_features"
DEFAULT_STALE_AFTER_SECONDS = 90
DEFAULT_LATEST_JSON_PATH = (
    Path("outputs") / "analysis" / "diario_market_features_latest.json"
)

_POSITIVE_CONFIRMATION = "CONFIRMANDO_COMPRA"
_NEGATIVE_CONFIRMATION = "CONFIRMANDO_VENDA"
_MIXED_CONFIRMATION = "MISTO"
_NEUTRAL_CONFIRMATION = "NEUTRO"
_UNAVAILABLE_CONFIRMATION = "INDISPONIVEL"


def _safe_text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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


def _safe_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _safe_list(value: Any) -> list[Any]:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return []


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


def _extract_operational_context(source: Any) -> dict[str, Any]:
    features = _extract_features(source)
    operational = _safe_mapping(features.get("contexto_operacional"))
    if operational:
        return operational
    if isinstance(source, Mapping):
        return _safe_mapping(source.get("contexto_operacional"))
    return {}


def _extract_price_value(value: Any) -> float:
    if hasattr(value, "value"):
        return _safe_float(getattr(value, "value"))
    return _safe_float(value)


def _extract_candle_prices(
    candles: list[Any],
) -> tuple[list[float], list[float], list[float], list[float]]:
    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    for candle in candles or []:
        opens.append(_extract_price_value(getattr(candle, "open", 0.0)))
        highs.append(_extract_price_value(getattr(candle, "high", 0.0)))
        lows.append(_extract_price_value(getattr(candle, "low", 0.0)))
        closes.append(_extract_price_value(getattr(candle, "close", 0.0)))
    return opens, highs, lows, closes


def _ensure_parent(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _get_connection(db_path: str | Path) -> sqlite3.Connection:
    _ensure_parent(db_path)
    conn = sqlite3.connect(str(db_path), timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _parse_timestamp(timestamp: Any) -> datetime | None:
    text = _safe_text(timestamp)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _round4(value: float) -> float:
    return round(float(value), 4)


def _serialize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _normalize_confirmation_from_snapshot(snapshot: Any) -> str:
    payload = _safe_mapping(snapshot)
    if not payload:
        return _UNAVAILABLE_CONFIRMATION
    available = _safe_bool(payload.get("available"), True)
    if not available:
        return _UNAVAILABLE_CONFIRMATION
    delta_pct = _safe_float(payload.get("delta_pct"))
    if delta_pct >= 0.10:
        return _POSITIVE_CONFIRMATION
    if delta_pct <= -0.10:
        return _NEGATIVE_CONFIRMATION
    return _NEUTRAL_CONFIRMATION


def _group_confirmation(snapshots: list[Any]) -> str:
    confirmations = [
        _normalize_confirmation_from_snapshot(snapshot)
        for snapshot in snapshots
        if _safe_mapping(snapshot)
    ]
    confirmations = [
        item for item in confirmations if item != _UNAVAILABLE_CONFIRMATION
    ]
    if not confirmations:
        return _UNAVAILABLE_CONFIRMATION
    if all(item == _POSITIVE_CONFIRMATION for item in confirmations):
        return _POSITIVE_CONFIRMATION
    if all(item == _NEGATIVE_CONFIRMATION for item in confirmations):
        return _NEGATIVE_CONFIRMATION
    if (
        _POSITIVE_CONFIRMATION in confirmations
        and _NEGATIVE_CONFIRMATION in confirmations
    ):
        return _MIXED_CONFIRMATION
    return _NEUTRAL_CONFIRMATION


@dataclass(slots=True)
class DiarioMarketFeaturesSnapshot:
    """Contrato canonico do snapshot intraday do Diario."""

    timestamp: str
    session_id: str
    symbol: str
    direction_hint: str = "NEUTRO"
    confidence: float = 0.0
    macro_regime: str = ""
    vies_intraday: str = ""
    reversal_score: float = 0.0
    exhaustion_score: float = 0.0
    usd_flow_state: str = "NEUTRO"
    usd_flow_delta_pct: float = 0.0
    usd_above_reference: bool = False
    heavyweights_confirmation: str = _UNAVAILABLE_CONFIRMATION
    ibov_confirmation: str = _UNAVAILABLE_CONFIRMATION
    ewz_confirmation: str = _UNAVAILABLE_CONFIRMATION
    guardian_state: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)
    source_metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["confidence"] = _round4(self.confidence)
        payload["reversal_score"] = _round4(self.reversal_score)
        payload["exhaustion_score"] = _round4(self.exhaustion_score)
        payload["usd_flow_delta_pct"] = _round4(self.usd_flow_delta_pct)
        return _serialize_value(payload)


@dataclass(slots=True)
class DiarioSoftFeatureInfluence:
    """Influencia soft do snapshot do Diario sobre a decisao do agente."""

    normalized_action: str = "NEUTRO"
    direction_hint: str = "NEUTRO"
    alignment: str = "NEUTRAL"
    confidence_adjustment: float = 0.0
    adjusted_confidence: float | None = None
    aggressiveness_bias: str = "NEUTRAL"
    reasons: list[str] = field(default_factory=list)
    available: bool = False
    stale: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["confidence_adjustment"] = _round4(self.confidence_adjustment)
        if self.adjusted_confidence is not None:
            payload["adjusted_confidence"] = _round4(self.adjusted_confidence)
        return _serialize_value(payload)


def ensure_diario_market_features_table(db_path: str | Path) -> None:
    """Cria a tabela append-only do Diario para features intraday."""
    conn = _get_connection(db_path)
    try:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direction_hint TEXT NOT NULL DEFAULT 'NEUTRO',
                confidence REAL NOT NULL DEFAULT 0,
                macro_regime TEXT NOT NULL DEFAULT '',
                vies_intraday TEXT NOT NULL DEFAULT '',
                reversal_score REAL NOT NULL DEFAULT 0,
                exhaustion_score REAL NOT NULL DEFAULT 0,
                usd_flow_state TEXT NOT NULL DEFAULT 'NEUTRO',
                usd_flow_delta_pct REAL NOT NULL DEFAULT 0,
                usd_above_reference INTEGER NOT NULL DEFAULT 0,
                heavyweights_confirmation TEXT NOT NULL DEFAULT 'INDISPONIVEL',
                ibov_confirmation TEXT NOT NULL DEFAULT 'INDISPONIVEL',
                ewz_confirmation TEXT NOT NULL DEFAULT 'INDISPONIVEL',
                guardian_state_json TEXT NOT NULL DEFAULT '{{}}',
                tags_json TEXT NOT NULL DEFAULT '[]',
                explanations_json TEXT NOT NULL DEFAULT '[]',
                source_metrics_json TEXT NOT NULL DEFAULT '{{}}',
                snapshot_json TEXT NOT NULL DEFAULT '{{}}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{TABLE_NAME}_timestamp ON {TABLE_NAME}(timestamp DESC)"
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS ix_{TABLE_NAME}_session ON {TABLE_NAME}(session_id, timestamp DESC)"
        )
    finally:
        conn.close()


def calculate_reversal_score(
    candles: list[Any],
    *,
    atr: float | None = None,
) -> tuple[float, str, dict[str, Any]]:
    """Detecta reversao apos movimento esticado usando candles recentes."""
    _, _, _, closes = _extract_candle_prices(candles)
    closes = closes[-6:]
    if len(closes) < 6:
        return 0.0, "NEUTRO", {"reason": "candles_insuficientes"}

    atr_reference = max(_safe_float(atr, 0.0), 1.0)
    stretch_move = closes[-2] - closes[0]
    last_leg = closes[-1] - closes[-2]
    mean_recent = sum(closes[:-1]) / max(len(closes) - 1, 1)
    distance_from_mean = closes[-2] - mean_recent

    direction_hint = "NEUTRO"
    score = 0.0
    if stretch_move > 0 and last_leg < 0:
        direction_hint = "SELL"
        score = (
            min(abs(stretch_move) / (atr_reference * 1.5), 1.0) * 0.45
            + min(abs(last_leg) / (atr_reference * 0.5), 1.0) * 0.35
            + min(max(distance_from_mean, 0.0) / (atr_reference * 0.8), 1.0) * 0.20
        )
    elif stretch_move < 0 and last_leg > 0:
        direction_hint = "BUY"
        score = (
            min(abs(stretch_move) / (atr_reference * 1.5), 1.0) * 0.45
            + min(abs(last_leg) / (atr_reference * 0.5), 1.0) * 0.35
            + min(max(-distance_from_mean, 0.0) / (atr_reference * 0.8), 1.0) * 0.20
        )

    metrics = {
        "atr_reference": atr_reference,
        "stretch_move_points": _round4(stretch_move),
        "last_leg_points": _round4(last_leg),
        "distance_from_mean_points": _round4(distance_from_mean),
        "close_current": _round4(closes[-1]),
        "close_previous": _round4(closes[-2]),
        "close_mean_recent": _round4(mean_recent),
    }
    return _round4(min(score, 1.0)), direction_hint, metrics


def calculate_exhaustion_score(
    candles: list[Any],
) -> tuple[float, str, dict[str, Any]]:
    """Detecta exaustao sem continuidade usando tamanho e direcao dos candles."""
    opens, _, _, closes = _extract_candle_prices(candles)
    opens = opens[-5:]
    closes = closes[-5:]
    if len(opens) < 5 or len(closes) < 5:
        return 0.0, "NEUTRO", {"reason": "candles_insuficientes"}

    bodies = [abs(close - open_) for open_, close in zip(opens, closes)]
    directions = [1 if close >= open_ else -1 for open_, close in zip(opens, closes)]
    setup_directions = directions[:-1]
    dominant = sum(setup_directions)
    if abs(dominant) < 2:
        return 0.0, "NEUTRO", {
            "setup_direction": "MISTO",
            "bodies": [_round4(body) for body in bodies],
        }

    dominant_side = 1 if dominant > 0 else -1
    same_direction_count = sum(1 for item in setup_directions if item == dominant_side)
    setup_bodies = bodies[:-1]
    last_body = bodies[-1]
    average_setup = sum(setup_bodies) / max(len(setup_bodies), 1)
    decreasing_bodies = all(
        setup_bodies[idx] >= setup_bodies[idx + 1]
        for idx in range(len(setup_bodies) - 1)
    )
    continuation_fail = last_body <= max(average_setup * 0.6, 1.0)
    opposite_last = directions[-1] != dominant_side

    if same_direction_count < 3 or not decreasing_bodies:
        return 0.0, "NEUTRO", {
            "setup_direction": "ALTA" if dominant_side > 0 else "BAIXA",
            "bodies": [_round4(body) for body in bodies],
            "continuation_fail": continuation_fail,
            "opposite_last": opposite_last,
        }

    score = 0.45
    if continuation_fail:
        score += 0.25
    if opposite_last:
        score += 0.20
    score += 0.10 * min(
        max(average_setup - last_body, 0.0) / max(average_setup, 1.0),
        1.0,
    )

    direction_hint = "SELL" if dominant_side > 0 else "BUY"
    metrics = {
        "setup_direction": "ALTA" if dominant_side > 0 else "BAIXA",
        "setup_bodies": [_round4(body) for body in setup_bodies],
        "last_body": _round4(last_body),
        "average_setup_body": _round4(average_setup),
        "continuation_fail": continuation_fail,
        "opposite_last": opposite_last,
    }
    return _round4(min(score, 1.0)), direction_hint, metrics


def detect_usd_flow_state(
    live_confirmation: Any,
    opening_context: Any | None = None,
) -> tuple[str, float, bool, dict[str, Any]]:
    """Classifica estresse do dolar em torno da referencia operacional."""
    live = _safe_mapping(live_confirmation)
    symbols = _safe_mapping(live.get("symbols"))
    dol_snapshot = _safe_mapping(symbols.get("DOL"))
    operational_context = _extract_operational_context(opening_context)
    rates_fx = _safe_mapping(operational_context.get("rates_fx"))
    reference_band = _safe_list(rates_fx.get("fx_reference_band"))

    delta_pct = _safe_float(
        dol_snapshot.get("delta_pct", live.get("usd_flow_delta_pct", 0.0))
    )
    price_current = _safe_float(dol_snapshot.get("price_current"))
    lower_ref = upper_ref = None
    if len(reference_band) >= 2:
        band = sorted(_safe_float(item) for item in reference_band[:2])
        lower_ref, upper_ref = band[0], band[1]

    above_reference = bool(upper_ref is not None and price_current > upper_ref)
    below_reference = bool(lower_ref is not None and price_current < lower_ref)

    state = "NEUTRO"
    if above_reference and delta_pct >= 0.20:
        state = "COMPRA_FORTE_ACIMA_REFERENCIA"
    elif above_reference:
        state = "ACIMA_REFERENCIA"
    elif below_reference and delta_pct <= -0.15:
        state = "VENDA_FORTE_ABAIXO_REFERENCIA"
    elif _safe_bool(live.get("dol_forte")) or delta_pct >= 0.20:
        state = "COMPRA_FORTE"
    elif delta_pct <= -0.15:
        state = "VENDA_FORTE"

    metrics = {
        "price_current": _round4(price_current),
        "delta_pct": _round4(delta_pct),
        "reference_low": _round4(lower_ref) if lower_ref is not None else None,
        "reference_high": _round4(upper_ref) if upper_ref is not None else None,
        "below_reference": below_reference,
    }
    return state, _round4(delta_pct), above_reference, metrics


def summarize_correlated_confirmations(live_confirmation: Any) -> dict[str, str]:
    """Resume confirmacoes ou contradicoes de ativos correlatos."""
    live = _safe_mapping(live_confirmation)
    symbols = _safe_mapping(live.get("symbols"))
    heavyweights_confirmation = _group_confirmation(
        [symbols.get("PETR4"), symbols.get("VALE3")]
    )
    return {
        "heavyweights_confirmation": heavyweights_confirmation,
        "ibov_confirmation": _normalize_confirmation_from_snapshot(symbols.get("IBOV")),
        "ewz_confirmation": _normalize_confirmation_from_snapshot(symbols.get("EWZ")),
    }


def _derive_direction_hint(
    *,
    signal_direction: str,
    signal_confidence: float,
    reversal_score: float,
    reversal_hint: str,
    exhaustion_score: float,
    exhaustion_hint: str,
    usd_flow_state: str,
    usd_flow_delta_pct: float,
    confirmations: Mapping[str, Any],
) -> tuple[str, float, list[str], list[str]]:
    direction_hint = (
        signal_direction if signal_direction in {"BUY", "SELL"} else "NEUTRO"
    )
    confidence = signal_confidence if direction_hint in {"BUY", "SELL"} else 0.0
    tags: list[str] = []
    explanations: list[str] = []

    if reversal_score >= 0.58 and reversal_hint in {"BUY", "SELL"}:
        direction_hint = reversal_hint
        confidence = max(
            confidence if reversal_hint == signal_direction else 0.0,
            reversal_score,
        )
        tags.append("reversao_detectada")
        explanations.append(
            f"reversao_intraday={reversal_hint} score={reversal_score:.2f}"
        )

    if exhaustion_score >= 0.70 and exhaustion_hint in {"BUY", "SELL"}:
        direction_hint = exhaustion_hint
        confidence = max(
            confidence if exhaustion_hint == signal_direction else 0.0,
            exhaustion_score,
        )
        tags.append("exaustao_detectada")
        explanations.append(
            f"exaustao_intraday={exhaustion_hint} score={exhaustion_score:.2f}"
        )

    usd_state_upper = usd_flow_state.upper()
    if usd_state_upper.startswith("COMPRA_FORTE"):
        direction_hint = "SELL"
        confidence = max(
            confidence if direction_hint == signal_direction else 0.0,
            min(0.90, 0.55 + abs(usd_flow_delta_pct)),
        )
        tags.append("stress_dolar")
        explanations.append(
            f"dolar_em_estresse={usd_flow_state} delta={usd_flow_delta_pct:+.2f}%"
        )
    elif usd_state_upper.startswith("VENDA_FORTE"):
        tags.append("alivio_dolar")
        explanations.append(
            f"dolar_em_alivio={usd_flow_state} delta={usd_flow_delta_pct:+.2f}%"
        )

    confirmation_votes = {
        "BUY": sum(
            1
            for key in (
                "heavyweights_confirmation",
                "ibov_confirmation",
                "ewz_confirmation",
            )
            if _safe_text(confirmations.get(key)).upper() == _POSITIVE_CONFIRMATION
        ),
        "SELL": sum(
            1
            for key in (
                "heavyweights_confirmation",
                "ibov_confirmation",
                "ewz_confirmation",
            )
            if _safe_text(confirmations.get(key)).upper() == _NEGATIVE_CONFIRMATION
        ),
    }
    if direction_hint in confirmation_votes:
        confidence = min(1.0, confidence + 0.02 * confirmation_votes[direction_hint])
        explanations.append(
            f"confirmacoes_correlatas_{direction_hint.lower()}={confirmation_votes[direction_hint]}"
        )

    if direction_hint == "NEUTRO" and signal_direction in {"BUY", "SELL"}:
        direction_hint = signal_direction
        confidence = signal_confidence

    return direction_hint, _round4(min(max(confidence, 0.0), 1.0)), tags, explanations


def build_diario_market_features_snapshot(
    *,
    session_id: str,
    symbol: str,
    signal: Any,
    candles: list[Any],
    guardian_state: Any,
    live_confirmation: Any | None = None,
    opening_context: Any | None = None,
) -> DiarioMarketFeaturesSnapshot:
    """Monta o snapshot intraday auditavel do Diario."""
    timestamp = _safe_text(getattr(signal, "timestamp", "")) or datetime.now().isoformat(
        timespec="seconds"
    )
    policy = normalize_opening_context(opening_context)
    live_payload = _safe_mapping(live_confirmation)
    signal_direction = _safe_text(getattr(signal, "direcao", "NEUTRO")).upper()
    signal_confidence = _safe_float(getattr(signal, "confianca", 0.0))
    atr = _safe_float(getattr(signal, "atr", 0.0))
    momentum = _safe_float(getattr(signal, "momentum", 0.0))

    reversal_score, reversal_hint, reversal_metrics = calculate_reversal_score(
        candles,
        atr=atr,
    )
    exhaustion_score, exhaustion_hint, exhaustion_metrics = calculate_exhaustion_score(
        candles
    )
    usd_flow_state, usd_flow_delta_pct, usd_above_reference, usd_metrics = (
        detect_usd_flow_state(live_payload, opening_context)
    )
    confirmations = summarize_correlated_confirmations(live_payload)
    direction_hint, confidence, derived_tags, derived_explanations = _derive_direction_hint(
        signal_direction=signal_direction,
        signal_confidence=signal_confidence,
        reversal_score=reversal_score,
        reversal_hint=reversal_hint,
        exhaustion_score=exhaustion_score,
        exhaustion_hint=exhaustion_hint,
        usd_flow_state=usd_flow_state,
        usd_flow_delta_pct=usd_flow_delta_pct,
        confirmations=confirmations,
    )

    guardian_payload = {
        "kill_switch_ativo": _safe_bool(
            getattr(guardian_state, "active_kill_switch", False)
        ),
        "bias_override": _safe_text(getattr(guardian_state, "bias_override", "")),
        "confidence_penalty": _safe_float(
            getattr(guardian_state, "confidence_penalty", 0.0)
        ),
        "kill_switch_reason": _safe_text(
            getattr(guardian_state, "kill_switch_reason", "")
        ),
    }

    _, _, _, closes = _extract_candle_prices(candles)
    latest_close = closes[-1] if closes else 0.0
    previous_close = closes[-2] if len(closes) >= 2 else latest_close
    recent_mean = sum(closes[-5:]) / len(closes[-5:]) if closes else 0.0
    signal_block_reason = _safe_text(getattr(signal, "motivo_bloqueio", ""))
    can_trade = _safe_bool(getattr(signal, "pode_operar", False))

    tags = list(derived_tags)
    if reversal_score >= 0.70:
        tags.append("reversao_alta")
    if exhaustion_score >= 0.70:
        tags.append("exaustao_alta")
    if usd_above_reference:
        tags.append("usd_acima_referencia")
    if guardian_payload["kill_switch_ativo"]:
        tags.append("guardian_kill_switch")
    if not can_trade:
        tags.append("sinal_bloqueado")

    explanations = [
        f"direction_hint={direction_hint} confidence={confidence:.2f} sinal={signal_direction or 'NEUTRO'}",
        f"reversal_score={reversal_score:.2f} exhaustion_score={exhaustion_score:.2f}",
        f"usd_flow={usd_flow_state} delta={usd_flow_delta_pct:+.2f}% heavyweights={confirmations['heavyweights_confirmation']}",
        f"ibov={confirmations['ibov_confirmation']} ewz={confirmations['ewz_confirmation']} guardian={'ON' if guardian_payload['kill_switch_ativo'] else 'OFF'}",
    ]
    explanations.extend(derived_explanations)
    if signal_block_reason:
        explanations.append(f"motivo_operacional={signal_block_reason}")

    source_metrics = {
        "atr": _round4(atr),
        "momentum": _round4(momentum),
        "price_current": _round4(
            _safe_float(getattr(signal, "preco_atual", latest_close))
        ),
        "close_current": _round4(latest_close),
        "close_previous": _round4(previous_close),
        "close_mean_5": _round4(recent_mean),
        "signal_direction": signal_direction,
        "signal_confidence": _round4(signal_confidence),
        "signal_can_trade": can_trade,
        "signal_block_reason": signal_block_reason,
        "reversal_metrics": reversal_metrics,
        "exhaustion_metrics": exhaustion_metrics,
        "usd_metrics": usd_metrics,
        "live_market_confirmation": live_payload,
    }

    return DiarioMarketFeaturesSnapshot(
        timestamp=timestamp,
        session_id=_safe_text(session_id),
        symbol=_safe_text(symbol, "WIN$N"),
        direction_hint=direction_hint,
        confidence=confidence,
        macro_regime=_safe_text(policy.regime_macro),
        vies_intraday=_safe_text(policy.vies_intraday),
        reversal_score=reversal_score,
        exhaustion_score=exhaustion_score,
        usd_flow_state=usd_flow_state,
        usd_flow_delta_pct=usd_flow_delta_pct,
        usd_above_reference=usd_above_reference,
        heavyweights_confirmation=_safe_text(
            confirmations.get("heavyweights_confirmation"),
            _UNAVAILABLE_CONFIRMATION,
        ),
        ibov_confirmation=_safe_text(
            confirmations.get("ibov_confirmation"),
            _UNAVAILABLE_CONFIRMATION,
        ),
        ewz_confirmation=_safe_text(
            confirmations.get("ewz_confirmation"),
            _UNAVAILABLE_CONFIRMATION,
        ),
        guardian_state=guardian_payload,
        tags=sorted(set(tag for tag in tags if tag)),
        explanations=explanations,
        source_metrics=source_metrics,
    )


def persist_diario_market_features_snapshot(
    db_path: str | Path,
    snapshot: DiarioMarketFeaturesSnapshot | Mapping[str, Any],
    *,
    latest_json_path: str | Path = DEFAULT_LATEST_JSON_PATH,
) -> int:
    """Persiste snapshot no SQLite e atualiza espelho latest JSON."""
    ensure_diario_market_features_table(db_path)
    payload = snapshot.to_dict() if hasattr(snapshot, "to_dict") else dict(snapshot)
    timestamp = _safe_text(payload.get("timestamp")) or datetime.now().isoformat(
        timespec="seconds"
    )
    row = (
        timestamp[:10],
        timestamp,
        _safe_text(payload.get("session_id")),
        _safe_text(payload.get("symbol"), "WIN$N"),
        _safe_text(payload.get("direction_hint"), "NEUTRO"),
        _safe_float(payload.get("confidence")),
        _safe_text(payload.get("macro_regime")),
        _safe_text(payload.get("vies_intraday")),
        _safe_float(payload.get("reversal_score")),
        _safe_float(payload.get("exhaustion_score")),
        _safe_text(payload.get("usd_flow_state"), "NEUTRO"),
        _safe_float(payload.get("usd_flow_delta_pct")),
        1 if _safe_bool(payload.get("usd_above_reference")) else 0,
        _safe_text(
            payload.get("heavyweights_confirmation"),
            _UNAVAILABLE_CONFIRMATION,
        ),
        _safe_text(payload.get("ibov_confirmation"), _UNAVAILABLE_CONFIRMATION),
        _safe_text(payload.get("ewz_confirmation"), _UNAVAILABLE_CONFIRMATION),
        _json_dumps(_safe_mapping(payload.get("guardian_state"))),
        _json_dumps(_safe_list(payload.get("tags"))),
        _json_dumps(_safe_list(payload.get("explanations"))),
        _json_dumps(_safe_mapping(payload.get("source_metrics"))),
        _json_dumps(payload),
    )

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            INSERT INTO {TABLE_NAME} (
                date, timestamp, session_id, symbol, direction_hint, confidence,
                macro_regime, vies_intraday, reversal_score, exhaustion_score,
                usd_flow_state, usd_flow_delta_pct, usd_above_reference,
                heavyweights_confirmation, ibov_confirmation, ewz_confirmation,
                guardian_state_json, tags_json, explanations_json,
                source_metrics_json, snapshot_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )
        conn.commit()
        row_id = int(cursor.lastrowid or 0)
    finally:
        conn.close()

    latest_path = Path(latest_json_path)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(_json_dumps(payload), encoding="utf-8")
    return row_id


def fetch_latest_diario_market_features_snapshot(
    db_path: str | Path,
    *,
    session_id: str | None = None,
) -> dict[str, Any] | None:
    """Lê o snapshot mais recente do Diario via SQLite."""
    ensure_diario_market_features_table(db_path)
    conn = _get_connection(db_path)
    try:
        query = f"SELECT snapshot_json FROM {TABLE_NAME}"
        params: list[Any] = []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        query += " ORDER BY timestamp DESC, id DESC LIMIT 1"
        row = conn.execute(query, params).fetchone()
    finally:
        conn.close()

    if row is None:
        return None
    raw = _safe_text(row["snapshot_json"])
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _load_latest_snapshot_from_json(path: str | Path) -> dict[str, Any] | None:
    json_path = Path(path)
    if not json_path.exists():
        return None
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _neutralize_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(snapshot)
    payload["direction_hint"] = "NEUTRO"
    payload["confidence"] = 0.0
    payload["reversal_score"] = 0.0
    payload["exhaustion_score"] = 0.0
    tags = set(_safe_list(payload.get("tags")))
    tags.add("stale")
    payload["tags"] = sorted(tags)
    return payload


def load_diario_market_features_payload(
    db_path: str | Path,
    *,
    latest_json_path: str | Path = DEFAULT_LATEST_JSON_PATH,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> dict[str, Any]:
    """Carrega snapshot do Diario com fallback JSON e status de staleness."""
    snapshot = None
    source = "sqlite"
    try:
        snapshot = fetch_latest_diario_market_features_snapshot(db_path)
    except Exception:
        snapshot = None

    if snapshot is None:
        source = "json"
        snapshot = _load_latest_snapshot_from_json(latest_json_path)

    if snapshot is None:
        return {
            "available": False,
            "source": "none",
            "snapshot": {},
            "effective_snapshot": {},
            "is_stale": False,
            "age_seconds": None,
            "stale_after_seconds": stale_after_seconds,
        }

    timestamp = _parse_timestamp(snapshot.get("timestamp"))
    age_seconds = None
    is_stale = False
    if timestamp is not None:
        age_seconds = max((datetime.now() - timestamp).total_seconds(), 0.0)
        is_stale = age_seconds > max(int(stale_after_seconds), 0)

    effective_snapshot = _neutralize_snapshot(snapshot) if is_stale else dict(snapshot)
    return {
        "available": True,
        "source": source,
        "snapshot": snapshot,
        "effective_snapshot": effective_snapshot,
        "is_stale": is_stale,
        "age_seconds": _round4(age_seconds) if age_seconds is not None else None,
        "stale_after_seconds": stale_after_seconds,
    }


def apply_diario_soft_feature_influence(
    action: Any,
    model_confidence: float | None,
    diario_payload: Mapping[str, Any] | None,
) -> DiarioSoftFeatureInfluence:
    """Traduz o snapshot do Diario em ajuste soft de confianca/agressividade."""
    normalized_action = normalize_action(action)
    if normalized_action not in {"BUY", "SELL"}:
        return DiarioSoftFeatureInfluence(
            normalized_action=normalized_action,
            adjusted_confidence=model_confidence,
        )

    payload = _safe_mapping(diario_payload)
    available = _safe_bool(payload.get("available"))
    stale = _safe_bool(payload.get("is_stale"))
    snapshot = _safe_mapping(payload.get("effective_snapshot"))
    direction_hint = _safe_text(snapshot.get("direction_hint"), "NEUTRO").upper()
    snapshot_confidence = _safe_float(snapshot.get("confidence"))
    reversal_score = _safe_float(snapshot.get("reversal_score"))
    exhaustion_score = _safe_float(snapshot.get("exhaustion_score"))
    usd_flow_state = _safe_text(snapshot.get("usd_flow_state")).upper()

    if not available or not snapshot:
        return DiarioSoftFeatureInfluence(
            normalized_action=normalized_action,
            adjusted_confidence=model_confidence,
            available=available,
            stale=stale,
        )

    adjustment = 0.0
    aggressiveness_bias = "NEUTRAL"
    alignment = "NEUTRAL"
    reasons: list[str] = []

    if direction_hint == normalized_action and snapshot_confidence >= 0.55:
        alignment = "ALIGNED"
        adjustment += 0.05 if snapshot_confidence >= 0.72 else 0.03
        aggressiveness_bias = "INCREASE"
        reasons.append("diario_alinhado_ao_sinal")
    elif (
        direction_hint in {"BUY", "SELL"}
        and direction_hint != normalized_action
        and snapshot_confidence >= 0.55
    ):
        alignment = "CONTRARY"
        adjustment -= 0.08 if snapshot_confidence >= 0.72 else 0.04
        aggressiveness_bias = "DECREASE"
        reasons.append("diario_contrario_ao_sinal")

    if usd_flow_state.startswith("COMPRA_FORTE"):
        if normalized_action == "BUY":
            adjustment -= 0.02
            aggressiveness_bias = "DECREASE"
            reasons.append("compra_contra_estresse_dolar")
        elif normalized_action == "SELL":
            adjustment += 0.02
            if aggressiveness_bias != "DECREASE":
                aggressiveness_bias = "INCREASE"
            reasons.append("venda_com_estresse_dolar")

    if direction_hint == normalized_action and reversal_score >= 0.70:
        adjustment += 0.02
        reasons.append("reversao_favoravel_confirmada")
    if direction_hint == normalized_action and exhaustion_score >= 0.70:
        adjustment += 0.01
        reasons.append("exaustao_favoravel_confirmada")

    adjusted_confidence = model_confidence
    if model_confidence is not None:
        adjusted_confidence = min(
            1.0,
            max(0.0, _safe_float(model_confidence) + adjustment),
        )

    return DiarioSoftFeatureInfluence(
        normalized_action=normalized_action,
        direction_hint=direction_hint,
        alignment=alignment,
        confidence_adjustment=_round4(adjustment),
        adjusted_confidence=adjusted_confidence,
        aggressiveness_bias=aggressiveness_bias,
        reasons=reasons,
        available=available,
        stale=stale,
    )


def build_contexto_operacional_com_diario(
    base_context: Any,
    *,
    base_payload: Mapping[str, Any] | None = None,
    diario_payload: Mapping[str, Any] | None = None,
    diario_influence: DiarioSoftFeatureInfluence | Mapping[str, Any] | None = None,
    db_path: str | Path | None = None,
    latest_json_path: str | Path = DEFAULT_LATEST_JSON_PATH,
    action: Any = None,
    model_confidence: float | None = None,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> dict[str, Any]:
    """Enriquece o contexto operacional com o snapshot do Diario."""
    payload = normalize_opening_context(base_context).to_dict()
    if base_payload:
        payload.update(dict(base_payload))

    if diario_payload is None and db_path is not None:
        diario_payload = load_diario_market_features_payload(
            db_path,
            latest_json_path=latest_json_path,
            stale_after_seconds=stale_after_seconds,
        )
    diario_payload_dict = _safe_mapping(diario_payload)

    if diario_influence is None and diario_payload_dict:
        diario_influence = apply_diario_soft_feature_influence(
            action,
            model_confidence,
            diario_payload_dict,
        )
    if hasattr(diario_influence, "to_dict"):
        influence_payload = diario_influence.to_dict()
    else:
        influence_payload = _safe_mapping(diario_influence)

    payload["diario_market_features_available"] = _safe_bool(
        diario_payload_dict.get("available")
    )
    payload["diario_market_features_source"] = _safe_text(
        diario_payload_dict.get("source"),
        "none",
    )
    payload["diario_market_features_stale"] = _safe_bool(
        diario_payload_dict.get("is_stale")
    )
    payload["diario_market_features_age_seconds"] = diario_payload_dict.get(
        "age_seconds"
    )
    payload["diario_market_features_stale_after_seconds"] = diario_payload_dict.get(
        "stale_after_seconds",
        stale_after_seconds,
    )
    payload["diario_market_features"] = _safe_mapping(
        diario_payload_dict.get("snapshot")
    )
    payload["diario_market_features_effective"] = _safe_mapping(
        diario_payload_dict.get("effective_snapshot")
    )
    payload["diario_market_features_soft_influence"] = influence_payload

    if model_confidence is not None:
        payload["confidence_used_model"] = _round4(model_confidence)
    adjusted_confidence = influence_payload.get("adjusted_confidence")
    if adjusted_confidence is not None:
        payload["confidence_used_diario_adjusted"] = _round4(
            _safe_float(adjusted_confidence)
        )
    return payload


__all__ = [
    "DEFAULT_LATEST_JSON_PATH",
    "DEFAULT_STALE_AFTER_SECONDS",
    "DiarioMarketFeaturesSnapshot",
    "DiarioSoftFeatureInfluence",
    "TABLE_NAME",
    "apply_diario_soft_feature_influence",
    "build_contexto_operacional_com_diario",
    "build_diario_market_features_snapshot",
    "calculate_exhaustion_score",
    "calculate_reversal_score",
    "detect_usd_flow_state",
    "ensure_diario_market_features_table",
    "fetch_latest_diario_market_features_snapshot",
    "load_diario_market_features_payload",
    "persist_diario_market_features_snapshot",
    "summarize_correlated_confirmations",
]
