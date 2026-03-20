"""Testes da confirmacao objetiva de abertura com market data ao vivo."""

from __future__ import annotations

from types import SimpleNamespace

from src.application.opening_market_confirmation import (
    build_live_market_confirmation,
)


def _price(value: float) -> SimpleNamespace:
    return SimpleNamespace(value=value)


class FakeMT5Adapter:
    def __init__(self, snapshots: dict[str, dict[str, float]]) -> None:
        self._snapshots = snapshots

    def select_symbol(self, _symbol: str) -> bool:
        return True

    def get_symbol_info_tick(self, symbol: str):
        data = self._snapshots.get(symbol)
        if data is None:
            return None
        return SimpleNamespace(last=_price(data["current"]))

    def get_daily_candle(self, symbol: str):
        data = self._snapshots.get(symbol)
        if data is None:
            return None
        return SimpleNamespace(open=_price(data["open"]))


def test_build_live_market_confirmation_confirma_compra_e_monitores() -> None:
    adapter = FakeMT5Adapter(
        {
            "PETR4": {"open": 100.0, "current": 100.20},
            "VALE3": {"open": 50.0, "current": 50.10},
            "WDO$N": {"open": 5.215, "current": 5.215},
            "EWZ": {"open": 30.0, "current": 30.05},
            "IBOV": {"open": 100000.0, "current": 100150.0},
        }
    )

    confirmation = build_live_market_confirmation(
        adapter,
        {
            "watchlist": ["PETR4", "VALE3", "DOL", "EWZ", "IBOV"],
            "contexto_operacional": {
                "rates_fx": {"fx_reference_band": [5.21, 5.22]},
            },
        },
    )

    assert confirmation.buy_confirmed is True
    assert confirmation.dol_comportado is True
    assert confirmation.monitors_positive == ["EWZ", "IBOV"]
    assert confirmation.monitors_negative == []
    assert confirmation.unresolved_symbols == []


def test_build_live_market_confirmation_compra_pode_ser_confirmada_por_monitor_positivo() -> None:
    adapter = FakeMT5Adapter(
        {
            "PETR4": {"open": 100.0, "current": 100.07},
            "VALE3": {"open": 50.0, "current": 50.06},
            "WDO$N": {"open": 5.215, "current": 5.10},
            "EWZ": {"open": 30.0, "current": 30.05},
            "IBOV": {"open": 100000.0, "current": 100060.0},
        }
    )

    confirmation = build_live_market_confirmation(
        adapter,
        {
            "watchlist": ["PETR4", "VALE3", "DOL", "EWZ", "IBOV"],
            "contexto_operacional": {
                "rates_fx": {"fx_reference_band": [5.21, 5.22]},
            },
        },
    )

    assert confirmation.buy_confirmed is True
    assert confirmation.dol_comportado is False
    assert confirmation.monitors_positive == ["EWZ", "IBOV"]


def test_build_live_market_confirmation_confirma_venda_e_monitores_negativos() -> None:
    adapter = FakeMT5Adapter(
        {
            "PETR4": {"open": 100.0, "current": 99.80},
            "VALE3": {"open": 50.0, "current": 49.85},
            "WDO$N": {"open": 5.20, "current": 5.22},
            "EWZ": {"open": 30.0, "current": 29.90},
            "IBOV": {"open": 100000.0, "current": 99850.0},
        }
    )

    confirmation = build_live_market_confirmation(
        adapter,
        {
            "watchlist": ["PETR4", "VALE3", "DOL", "EWZ", "IBOV"],
            "contexto_operacional": {
                "rates_fx": {"fx_reference_band": [5.20, 5.21]},
            },
        },
    )

    assert confirmation.sell_quality_confirmed is True
    assert confirmation.dol_forte is True
    assert confirmation.monitors_negative == ["EWZ", "IBOV"]
    assert confirmation.heavyweights_negative is True
