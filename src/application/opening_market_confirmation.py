"""Confirmacoes objetivas de abertura com market data ao vivo."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from src.application.opening_context_policy import normalize_opening_context

DEFAULT_MONITORED_SYMBOLS = ("PETR4", "VALE3", "DOL", "EWZ", "IBOV")
SYMBOL_ALIASES = {
    "PETR4": ("PETR4",),
    "VALE3": ("VALE3",),
    "DOL": ("WDO$N", "DOL$N", "USDBRL", "WDO", "DOL"),
    "EWZ": ("EWZ", "BEWZ39"),
    "IBOV": ("IBOV", "WIN$N", "BOVA11"),
}
PRICE_SUPPORT_THRESHOLD_PCT = 0.05
DOL_STRONG_THRESHOLD_PCT = 0.20
DOL_CALM_THRESHOLD_PCT = 0.15


def _safe_text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text if text else default


def _safe_float(value: Any, default: float = 0.0) -> float:
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


@dataclass(slots=True)
class LiveMarketSymbolSnapshot:
    """Snapshot de um simbolo monitorado em tempo real."""

    requested_symbol: str
    resolved_symbol: str = ""
    available: bool = False
    price_current: float = 0.0
    price_open: float = 0.0
    delta_points: float = 0.0
    delta_pct: float = 0.0
    direction: str = "UNAVAILABLE"
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_symbol": self.requested_symbol,
            "resolved_symbol": self.resolved_symbol,
            "available": self.available,
            "price_current": self.price_current,
            "price_open": self.price_open,
            "delta_points": self.delta_points,
            "delta_pct": self.delta_pct,
            "direction": self.direction,
            "note": self.note,
        }


@dataclass(slots=True)
class OpeningLiveMarketConfirmation:
    """Contrato consumido pelo gate operacional."""

    timestamp: str
    market_data_source: str = "mt5"
    buy_confirmed: bool = False
    sell_quality_confirmed: bool = False
    dol_comportado: bool = False
    dol_forte: bool = False
    heavyweights_buy_confirmed: bool = False
    heavyweights_negative: bool = False
    monitors_positive: list[str] = field(default_factory=list)
    monitors_negative: list[str] = field(default_factory=list)
    unresolved_symbols: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    symbols: dict[str, LiveMarketSymbolSnapshot] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "market_data_source": self.market_data_source,
            "buy_confirmed": self.buy_confirmed,
            "sell_quality_confirmed": self.sell_quality_confirmed,
            "dol_comportado": self.dol_comportado,
            "dol_forte": self.dol_forte,
            "heavyweights_buy_confirmed": self.heavyweights_buy_confirmed,
            "heavyweights_negative": self.heavyweights_negative,
            "monitors_positive": list(self.monitors_positive),
            "monitors_negative": list(self.monitors_negative),
            "unresolved_symbols": list(self.unresolved_symbols),
            "reasons": list(self.reasons),
            "symbols": {
                key: value.to_dict() for key, value in self.symbols.items()
            },
        }


def build_live_market_confirmation(
    mt5_adapter: Any,
    context: Any,
) -> OpeningLiveMarketConfirmation:
    """Monta a confirmacao objetiva de abertura usando dados ao vivo."""
    policy = normalize_opening_context(context)
    operational_context = {}
    if isinstance(context, Mapping):
        operational_context = _safe_mapping(context.get("contexto_operacional"))
    else:
        features = getattr(context, "features", None)
        if isinstance(features, Mapping):
            operational_context = _safe_mapping(features.get("contexto_operacional"))

    symbols: dict[str, LiveMarketSymbolSnapshot] = {}
    unresolved_symbols: list[str] = []
    monitored = list(DEFAULT_MONITORED_SYMBOLS)
    for extra in [str(item).upper() for item in policy.watchlist]:
        if extra not in monitored:
            monitored.append(extra)

    reference_band = _safe_list(
        operational_context.get("rates_fx", {}).get("fx_reference_band", [])
        if isinstance(operational_context.get("rates_fx"), Mapping)
        else []
    )

    for requested in monitored:
        snapshot = _capture_symbol_snapshot(mt5_adapter, requested)
        symbols[requested] = snapshot
        if not snapshot.available:
            unresolved_symbols.append(requested)

    heavyweights = [symbols.get(item) for item in policy.heavyweights]
    heavyweights = [item for item in heavyweights if item is not None]
    heavyweights_buy_confirmed = (
        bool(heavyweights)
        and all(
            item.available and item.delta_pct >= PRICE_SUPPORT_THRESHOLD_PCT
            for item in heavyweights
        )
    )
    heavyweights_negative = (
        bool(heavyweights)
        and all(
            item.available and item.delta_pct <= -PRICE_SUPPORT_THRESHOLD_PCT
            for item in heavyweights
        )
    )

    dol_snapshot = symbols.get("DOL", LiveMarketSymbolSnapshot(requested_symbol="DOL"))
    dol_comportado = _is_dol_comportado(dol_snapshot, reference_band)
    dol_forte = _is_dol_forte(dol_snapshot, reference_band)

    monitors_positive: list[str] = []
    monitors_negative: list[str] = []
    for symbol_name in ("EWZ", "IBOV"):
        snapshot = symbols.get(symbol_name)
        if snapshot is None or not snapshot.available:
            continue
        if snapshot.delta_pct >= PRICE_SUPPORT_THRESHOLD_PCT:
            monitors_positive.append(symbol_name)
        elif snapshot.delta_pct <= -PRICE_SUPPORT_THRESHOLD_PCT:
            monitors_negative.append(symbol_name)

    reasons: list[str] = []
    if heavyweights_buy_confirmed:
        reasons.append("pesos_pesados_confirmam_compra")
    if heavyweights_negative:
        reasons.append("pesos_pesados_fracos")
    if dol_comportado:
        reasons.append("dol_comportado_live")
    if dol_forte:
        reasons.append("dol_forte_live")
    if monitors_positive:
        reasons.append(f"monitores_favoraveis:{','.join(monitors_positive)}")
    if monitors_negative:
        reasons.append(f"monitores_contrarios:{','.join(monitors_negative)}")

    buy_confirmed = heavyweights_buy_confirmed and (
        dol_comportado or bool(monitors_positive)
    )
    sell_quality_confirmed = dol_forte

    return OpeningLiveMarketConfirmation(
        timestamp=datetime.now().isoformat(timespec="seconds"),
        buy_confirmed=buy_confirmed,
        sell_quality_confirmed=sell_quality_confirmed,
        dol_comportado=dol_comportado,
        dol_forte=dol_forte,
        heavyweights_buy_confirmed=heavyweights_buy_confirmed,
        heavyweights_negative=heavyweights_negative,
        monitors_positive=monitors_positive,
        monitors_negative=monitors_negative,
        unresolved_symbols=unresolved_symbols,
        reasons=reasons,
        symbols=symbols,
    )


def _capture_symbol_snapshot(
    mt5_adapter: Any,
    requested_symbol: str,
) -> LiveMarketSymbolSnapshot:
    aliases = SYMBOL_ALIASES.get(requested_symbol, (requested_symbol,))
    resolved_symbol = _resolve_symbol(mt5_adapter, aliases)
    if not resolved_symbol:
        return LiveMarketSymbolSnapshot(
            requested_symbol=requested_symbol,
            note="symbol_unavailable",
        )

    try:
        tick = mt5_adapter.get_symbol_info_tick(resolved_symbol)
        candle = mt5_adapter.get_daily_candle(resolved_symbol)
    except Exception as exc:
        return LiveMarketSymbolSnapshot(
            requested_symbol=requested_symbol,
            resolved_symbol=resolved_symbol,
            note=f"market_data_error:{exc}",
        )

    if tick is None or candle is None:
        return LiveMarketSymbolSnapshot(
            requested_symbol=requested_symbol,
            resolved_symbol=resolved_symbol,
            note="tick_or_daily_candle_missing",
        )

    price_current = _extract_tick_price(tick)
    price_open = _extract_price_value(getattr(candle, "open", 0.0))
    if price_current <= 0 or price_open <= 0:
        return LiveMarketSymbolSnapshot(
            requested_symbol=requested_symbol,
            resolved_symbol=resolved_symbol,
            note="invalid_prices",
        )

    delta_points = price_current - price_open
    delta_pct = (delta_points / price_open) * 100 if price_open else 0.0
    direction = "UP" if delta_pct > 0 else "DOWN" if delta_pct < 0 else "FLAT"
    return LiveMarketSymbolSnapshot(
        requested_symbol=requested_symbol,
        resolved_symbol=resolved_symbol,
        available=True,
        price_current=price_current,
        price_open=price_open,
        delta_points=delta_points,
        delta_pct=delta_pct,
        direction=direction,
    )


def _resolve_symbol(mt5_adapter: Any, aliases: tuple[str, ...]) -> str:
    for symbol in aliases:
        try:
            if hasattr(mt5_adapter, "select_symbol"):
                mt5_adapter.select_symbol(symbol)
            tick = mt5_adapter.get_symbol_info_tick(symbol)
        except Exception:
            tick = None
        if tick is not None:
            return symbol
    return ""


def _extract_price_value(price_obj: Any) -> float:
    value = getattr(price_obj, "value", price_obj)
    return _safe_float(value, 0.0)


def _extract_tick_price(tick: Any) -> float:
    last = _extract_price_value(getattr(tick, "last", 0.0))
    if last > 0:
        return last
    bid = _extract_price_value(getattr(tick, "bid", 0.0))
    ask = _extract_price_value(getattr(tick, "ask", 0.0))
    if bid > 0 and ask > 0:
        return (bid + ask) / 2.0
    return bid or ask


def _is_dol_comportado(
    dol_snapshot: LiveMarketSymbolSnapshot,
    reference_band: list[Any],
) -> bool:
    if not dol_snapshot.available:
        return False
    if len(reference_band) >= 2:
        lower = min(_safe_float(reference_band[0]), _safe_float(reference_band[1]))
        upper = max(_safe_float(reference_band[0]), _safe_float(reference_band[1]))
        if lower > 0 and upper > 0:
            return lower <= dol_snapshot.price_current <= upper
    return abs(dol_snapshot.delta_pct) <= DOL_CALM_THRESHOLD_PCT


def _is_dol_forte(
    dol_snapshot: LiveMarketSymbolSnapshot,
    reference_band: list[Any],
) -> bool:
    if not dol_snapshot.available:
        return False
    if len(reference_band) >= 2:
        upper = max(_safe_float(reference_band[0]), _safe_float(reference_band[1]))
        if upper > 0 and dol_snapshot.price_current > upper:
            return True
    return dol_snapshot.delta_pct >= DOL_STRONG_THRESHOLD_PCT


__all__ = [
    "LiveMarketSymbolSnapshot",
    "OpeningLiveMarketConfirmation",
    "build_live_market_confirmation",
]
