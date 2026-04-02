"""
Testes para MT5Adapter.obter_pnl_fechado.

Grupo 2 da estrategia TDD — ROADMAP-MICRO-03.

Testa:
- Retorno float com magic_number correto
- Retorno None com magic_number errado
- Retorno None quando deals vazio
- Retorno None quando excecao e lancada internamente
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.infrastructure.adapters.mt5_adapter import MT5Adapter


def _build_adapter() -> MT5Adapter:
    """Cria instancia de MT5Adapter com _mt5 mockado."""
    adapter = MT5Adapter.__new__(MT5Adapter)
    adapter._mt5 = MagicMock()
    adapter._connected = True
    return adapter


def _make_deal(position_id: int, magic: int, profit: float) -> MagicMock:
    deal = MagicMock()
    deal.position_id = position_id
    deal.position = position_id
    deal.magic = magic
    deal.profit = profit
    return deal


def test_obter_pnl_fechado_retorna_float_com_magic_correto():
    """Deve retornar float quando ticket e magic_number coincidem."""
    adapter = _build_adapter()
    deal = _make_deal(position_id=1001, magic=234500, profit=25.0)
    adapter._mt5.history_deals_get.return_value = [deal]

    resultado = adapter.obter_pnl_fechado(ticket=1001, magic_number=234500)

    assert isinstance(resultado, float)
    assert resultado == 25.0


def test_obter_pnl_fechado_retorna_none_com_magic_errado():
    """Deve retornar None quando magic_number nao coincide."""
    adapter = _build_adapter()
    deal = _make_deal(position_id=1001, magic=234600, profit=25.0)
    adapter._mt5.history_deals_get.return_value = [deal]

    resultado = adapter.obter_pnl_fechado(ticket=1001, magic_number=234500)

    assert resultado is None


def test_obter_pnl_fechado_retorna_none_quando_deals_vazio():
    """Deve retornar None quando history_deals_get retorna lista vazia."""
    adapter = _build_adapter()
    adapter._mt5.history_deals_get.return_value = []

    resultado = adapter.obter_pnl_fechado(ticket=1001, magic_number=234500)

    assert resultado is None


def test_obter_pnl_fechado_trata_excecao_mt5_graciosamente():
    """Deve retornar None quando history_deals_get lanca excecao."""
    adapter = _build_adapter()
    adapter._mt5.history_deals_get.side_effect = RuntimeError("MT5 indisponivel")

    resultado = adapter.obter_pnl_fechado(ticket=1001, magic_number=234500)

    assert resultado is None


def test_obter_pnl_fechado_filtra_ticket_correto_entre_multiplos():
    """Deve retornar profit apenas do deal com position_id == ticket."""
    adapter = _build_adapter()
    deal_errado = _make_deal(position_id=9999, magic=234500, profit=100.0)
    deal_certo = _make_deal(position_id=1001, magic=234500, profit=35.0)
    adapter._mt5.history_deals_get.return_value = [deal_errado, deal_certo]

    resultado = adapter.obter_pnl_fechado(ticket=1001, magic_number=234500)

    assert resultado == 35.0
