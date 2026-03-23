from uuid import UUID

from src.domain.entities.trade import Order
from src.domain.enums.trading_enums import OrderSide, OrderType
from src.domain.value_objects import Price, Quantity, Symbol
from src.infrastructure.adapters.mt5_adapter import MT5Adapter


def _build_order(magic_number: int) -> Order:
    order = Order(
        symbol=Symbol("WIN$N"),
        side=OrderSide.BUY,
        quantity=Quantity(1),
        order_type=OrderType.MARKET,
        price=Price(100000.0),
        magic_number=magic_number,
        execution_method="automated",
    )
    order.order_id = UUID("12345678-1234-5678-1234-567812345678")
    return order


def test_build_order_comment_usa_nome_do_agente_rl_5000() -> None:
    order = _build_order(234500)

    comment = MT5Adapter._build_order_comment(order)

    assert comment == "RL5000_EA234500_MA12345678"


def test_build_order_comment_limita_tamanho_para_mt5() -> None:
    order = _build_order(999999)

    comment = MT5Adapter._build_order_comment(order)

    assert len(comment) <= 31


def test_build_order_comment_remove_caracteres_invalidos() -> None:
    order = _build_order(234700)

    comment = MT5Adapter._build_order_comment(order)

    assert "|" not in comment
    assert " " not in comment
