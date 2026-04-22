from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest

from src.domain.enums.trading_enums import TimeFrame
from src.domain.exceptions import OrderExecutionError
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter


def criar_adapter(mockar_resolvedor: bool = True) -> MT5Adapter:
    """Cria adapter com dependencias mockadas para testes de candles."""
    adapter = MT5Adapter(
        login=1000346516,
        password="senha_teste",
        server="ClearInvestimentos-DEMO",
    )
    adapter._ensure_connected = Mock()
    if mockar_resolvedor:
        adapter._resolve_tradable_symbol = Mock(return_value="WINJ26")
    adapter._mt5 = MagicMock()
    adapter._mt5.TIMEFRAME_M5 = 5
    return adapter


def test_get_candles_seleciona_simbolo_antes_de_consultar_mt5() -> None:
    """Deve habilitar o simbolo no MT5 antes de buscar candles."""
    adapter = criar_adapter()
    adapter.select_symbol = Mock(return_value=True)
    adapter._mt5.copy_rates_from_pos.return_value = [
        {
            "open": Decimal("1.0"),
            "high": Decimal("2.0"),
            "low": Decimal("0.5"),
            "close": Decimal("1.5"),
            "tick_volume": 10,
            "time": 1710000000,
        }
    ]
    adapter._mt5.symbol_info.return_value = MagicMock(
        trade_mode=4,
        visible=True,
    )
    adapter._mt5.symbol_info_tick.return_value = MagicMock(bid=1.0, ask=1.1, last=1.05)

    candles = adapter.get_candles(Symbol("WIN$N"), TimeFrame.M5, 1)

    assert len(candles) == 1
    adapter.select_symbol.assert_called_once_with("WINJ26")
    adapter._mt5.copy_rates_from_pos.assert_called_once_with("WINJ26", 5, 0, 1)


def test_get_candles_falha_quando_nao_consegue_selecionar_simbolo() -> None:
    """Deve interromper a leitura quando o simbolo nao puder ser habilitado."""
    adapter = criar_adapter()
    adapter.select_symbol = Mock(return_value=False)
    adapter._mt5.last_error.return_value = (-1, "Terminal: Call failed")

    with pytest.raises(OrderExecutionError, match="Failed to select symbol WINJ26"):
        adapter.get_candles(Symbol("WIN$N"), TimeFrame.M5, 1)

    adapter._mt5.copy_rates_from_pos.assert_not_called()


def test_resolve_tradable_symbol_prefere_contrato_vigente_com_dados() -> None:
    """Deve ignorar contrato antigo sem dados e usar o vigente."""
    adapter = criar_adapter(mockar_resolvedor=False)
    adapter.select_symbol = Mock(side_effect=lambda symbol: symbol == "WINM26")

    info_continuo = MagicMock()
    info_continuo.trade_mode = 0
    info_continuo.basis = "WINJ26"

    info_j26 = MagicMock()
    info_j26.trade_mode = adapter._mt5.SYMBOL_TRADE_MODE_FULL = 4

    info_m26 = MagicMock()
    info_m26.trade_mode = 4

    tick_m26 = MagicMock()
    tick_m26.bid = 136000.0
    tick_m26.ask = 136005.0
    tick_m26.last = 136000.0

    def symbol_info_side_effect(symbol: str):
        if symbol == "WIN$N":
            return info_continuo
        if symbol == "WINJ26":
            return info_j26
        if symbol == "WINM26":
            return info_m26
        return None

    adapter._mt5.symbol_info.side_effect = symbol_info_side_effect
    adapter._mt5.symbol_info_tick.side_effect = (
        lambda symbol: tick_m26 if symbol == "WINM26" else None
    )
    adapter._mt5.copy_rates_from_pos.side_effect = (
        lambda symbol, *_: [
            {
                "open": Decimal("136000.0"),
                "high": Decimal("136010.0"),
                "low": Decimal("135990.0"),
                "close": Decimal("136005.0"),
                "tick_volume": 100,
                "time": 1710000000,
            }
        ]
        if symbol == "WINM26"
        else None
    )
    adapter._mt5.symbols_get.return_value = [
        SimpleNamespace(name="WINJ26", trade_mode=4),
        SimpleNamespace(name="WINM26", trade_mode=4),
    ]

    resolvido = adapter._resolve_tradable_symbol("WIN$N")

    assert resolvido == "WINM26"


def test_get_candles_recupera_para_contrato_alternativo_quando_select_falha() -> None:
    """Se o contrato resolvido falhar, deve tentar o proximo contrato valido."""
    adapter = criar_adapter(mockar_resolvedor=False)
    adapter._resolve_tradable_symbol = Mock(return_value="WINJ26")
    adapter.select_symbol = Mock(side_effect=lambda symbol: symbol != "WINJ26")
    adapter._symbol_has_market_data = Mock(side_effect=lambda symbol: symbol == "WINM26")

    adapter._mt5.SYMBOL_TRADE_MODE_FULL = 4
    adapter._mt5.symbols_get.return_value = [
        SimpleNamespace(name="WINJ26", trade_mode=4),
        SimpleNamespace(name="WINM26", trade_mode=4),
    ]
    adapter._mt5.copy_rates_from_pos.return_value = [
        {
            "open": Decimal("136000.0"),
            "high": Decimal("136010.0"),
            "low": Decimal("135990.0"),
            "close": Decimal("136005.0"),
            "tick_volume": 100,
            "time": 1710000000,
        }
    ]

    candles = adapter.get_candles(Symbol("WIN$N"), TimeFrame.M5, 1)

    assert len(candles) == 1
    adapter._mt5.copy_rates_from_pos.assert_called_once_with("WINM26", 5, 0, 1)