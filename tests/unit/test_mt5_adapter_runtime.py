"""Testes do adaptador MT5 relacionados ao runtime RL/MT5."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.domain.enums.trading_enums import OrderSide
from src.domain.value_objects import Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter


class TestMT5AdapterRuntime:
    @pytest.fixture
    def adapter(self) -> MT5Adapter:
        adapter = MT5Adapter(
            login=123,
            password="pwd",
            server="srv",
            terminal_exe_path=r"C:\Program Files\Clear Investimentos MT5\terminal64.exe",
        )
        adapter._mt5 = MagicMock()
        adapter._mt5.ORDER_TYPE_BUY = 0
        adapter._mt5.ORDER_TYPE_SELL = 1
        adapter._trading_halted = False
        adapter.is_connected = MagicMock(return_value=True)
        adapter._validate_terminal_isolation = MagicMock(return_value=True)
        return adapter

    def test_obter_preco_saida_por_ticket_usa_historia_de_deal(self, adapter: MT5Adapter) -> None:
        adapter._mt5.positions_get.return_value = []

        deal_aberto = MagicMock()
        deal_aberto.position_id = 1234
        deal_aberto.entry = "IN"
        deal_aberto.price = 100000.0
        deal_aberto.time = int(datetime.utcnow().timestamp())

        deal_fechado = MagicMock()
        deal_fechado.position_id = 1234
        deal_fechado.entry = "OUT"
        deal_fechado.price = 100500.0
        deal_fechado.time = int(datetime.utcnow().timestamp()) + 1

        adapter._mt5.history_deals_get.return_value = [deal_aberto, deal_fechado]

        preco = adapter.obter_preco_saida_por_ticket(
            1234,
            symbol=Symbol("WINJ26"),
            side=OrderSide.BUY,
        )

        assert preco == pytest.approx(100500.0, abs=0.01)

    def test_terminal_mismatch_helper_tolera_variacao_segura(self, adapter: MT5Adapter) -> None:
        expected = r"C:\Program Files\Clear Investimentos MT5\terminal64.exe"
        actual_ok = r"C:\Program Files\Clear Investimentos MT5\Build 4090\terminal64.exe"
        actual_bad = r"C:\Program Files\FBS MT5\terminal64.exe"

        assert adapter._terminal_corresponde_ao_esperado(expected, actual_ok) is True
        assert adapter._terminal_corresponde_ao_esperado(expected, actual_bad) is False

    def test_get_mt5_terminal_pid_ignora_terminal_incompativel(self, adapter: MT5Adapter) -> None:
        proc_ok = MagicMock()
        proc_ok.info = {
            "pid": 111,
            "name": "terminal64.exe",
            "exe": r"C:\Program Files\Clear Investimentos MT5\Build 4090\terminal64.exe",
        }
        proc_bad = MagicMock()
        proc_bad.info = {
            "pid": 222,
            "name": "terminal64.exe",
            "exe": r"C:\Program Files\FBS MT5\terminal64.exe",
        }

        with patch("psutil.process_iter", return_value=[proc_bad, proc_ok]):
            pid = adapter._get_mt5_terminal_pid()

        assert pid == 111
