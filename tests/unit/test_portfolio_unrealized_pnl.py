"""
tests/unit/test_portfolio_unrealized_pnl.py

Testes unitarios para calculo de P&L nao realizado em Portfolio.

BLID-035 — P&L nao realizado (portfolio.py)

Criterios de Aceite:
- AC-1: calculate_unrealized_pnl retorna zero quando nao ha posicoes abertas
- AC-2: calculate_unrealized_pnl calcula corretamente para BUY com lucro
- AC-3: calculate_unrealized_pnl calcula corretamente para BUY com perda
- AC-4: calculate_unrealized_pnl calcula corretamente para SELL
- AC-5: Posicao sem preco disponivel e ignorada (nao levanta excecao)
- AC-6: calculate_total_value sem precos retorna apenas capital (retrocompat.)
- AC-7: calculate_total_value com precos inclui unrealized P&L
- AC-8: calculate_total_value com precos negativos reduz total
- AC-9: Multiplas posicoes sao somadas corretamente
- AC-10: DashboardDataSnapshot serializa pnl_nao_realizado_reais
- AC-11: obter_snapshot_dashboard aceita pnl_nao_realizado_reais
- AC-12: Logs auditaveis sao gerados durante calculo (capturar com caplog)
"""

import logging
from datetime import datetime
from decimal import Decimal

import pytest

from src.domain.entities.portfolio import Portfolio
from src.domain.entities.trade import Trade, Position
from src.domain.enums.trading_enums import OrderSide, TradeStatus
from src.domain.value_objects import Money, Price, Quantity, Symbol, Percentage
from src.application.dashboard_stats_server import (
    DashboardDataSnapshot,
    StatsQueryService,
    TradeStats,
    OperationalMetrics,
    ProtectionStatus,
)


# ---------------------------------------------------------------------------
# Fixtures reutilizaveis
# ---------------------------------------------------------------------------


@pytest.fixture
def capital_inicial() -> Money:
    """Capital inicial padrao para testes (suficiente para WIN$N ~128k)."""
    return Money(Decimal("500000"))


@pytest.fixture
def portfolio_vazio(capital_inicial: Money) -> Portfolio:
    """Portfolio sem posicoes abertas."""
    return Portfolio(initial_capital=capital_inicial)


@pytest.fixture
def trade_buy() -> Trade:
    """Trade BUY aberto em WIN$N a 128000."""
    return Trade(
        symbol=Symbol("WIN$N"),
        side=OrderSide.BUY,
        quantity=Quantity(1),
        entry_price=Price(Decimal("128000")),
        entry_time=datetime.now(),
    )


@pytest.fixture
def trade_sell() -> Trade:
    """Trade SELL aberto em WIN$N a 128500."""
    return Trade(
        symbol=Symbol("WIN$N"),
        side=OrderSide.SELL,
        quantity=Quantity(1),
        entry_price=Price(Decimal("128500")),
        entry_time=datetime.now(),
    )


@pytest.fixture
def portfolio_com_buy(capital_inicial: Money, trade_buy: Trade) -> Portfolio:
    """Portfolio com uma posicao BUY aberta."""
    p = Portfolio(initial_capital=capital_inicial)
    p.open_trade(trade_buy, Percentage(Decimal("0.02")))
    return p


# ---------------------------------------------------------------------------
# AC-1: sem posicoes abertas → unrealized = 0
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unrealized_zero_sem_posicoes(portfolio_vazio: Portfolio) -> None:
    """AC-1: Portfolio sem posicoes abertas deve retornar unrealized = R$0."""
    precos = {"WIN$N": Price(Decimal("128500"))}
    resultado = portfolio_vazio.calculate_unrealized_pnl(precos)
    assert resultado.amount == Decimal("0")


# ---------------------------------------------------------------------------
# AC-2: BUY com lucro
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unrealized_buy_com_lucro(portfolio_com_buy: Portfolio) -> None:
    """AC-2: BUY com preco atual acima de entrada deve gerar lucro nao realizado."""
    # Entrada = 128000; preco atual = 128500 → diferenca = +500
    precos = {"WIN$N": Price(Decimal("128500"))}
    resultado = portfolio_com_buy.calculate_unrealized_pnl(precos)
    assert resultado.amount == Decimal("500")


# ---------------------------------------------------------------------------
# AC-3: BUY com perda
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unrealized_buy_com_perda(portfolio_com_buy: Portfolio) -> None:
    """AC-3: BUY com preco atual abaixo de entrada deve gerar perda nao realizada."""
    # Entrada = 128000; preco atual = 127000 → diferenca = -1000
    precos = {"WIN$N": Price(Decimal("127000"))}
    resultado = portfolio_com_buy.calculate_unrealized_pnl(precos)
    assert resultado.amount == Decimal("-1000")


# ---------------------------------------------------------------------------
# AC-4: SELL com lucro
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unrealized_sell_com_lucro(
    capital_inicial: Money,
    trade_sell: Trade,
) -> None:
    """AC-4: SELL com preco atual abaixo de entrada deve gerar lucro nao realizado."""
    # Entrada = 128500; preco atual = 127500 → diferenca = +1000 (SELL)
    p = Portfolio(initial_capital=capital_inicial)
    p.open_trade(trade_sell, Percentage(Decimal("0.02")))
    precos = {"WIN$N": Price(Decimal("127500"))}
    resultado = p.calculate_unrealized_pnl(precos)
    assert resultado.amount == Decimal("1000")


# ---------------------------------------------------------------------------
# AC-5: simbolo sem preco → ignorado silenciosamente
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unrealized_simbolo_sem_preco_ignorado(
    portfolio_com_buy: Portfolio,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC-5: Posicao sem preco disponivel deve ser ignorada sem excecao."""
    with caplog.at_level(logging.WARNING, logger="src.domain.entities.portfolio"):
        resultado = portfolio_com_buy.calculate_unrealized_pnl({})

    assert resultado.amount == Decimal("0")
    assert any("indisponivel" in msg for msg in caplog.messages)


# ---------------------------------------------------------------------------
# AC-6: calculate_total_value sem precos retorna apenas capital
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_total_value_sem_precos_retrocompativel(
    portfolio_com_buy: Portfolio,
    capital_inicial: Money,
) -> None:
    """AC-6: calculate_total_value() sem argumento deve retornar apenas capital."""
    resultado = portfolio_com_buy.calculate_total_value()
    assert resultado.amount == capital_inicial.amount


# ---------------------------------------------------------------------------
# AC-7: calculate_total_value com precos inclui unrealized P&L positivo
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_total_value_com_precos_inclui_unrealized(
    portfolio_com_buy: Portfolio,
    capital_inicial: Money,
) -> None:
    """AC-7: calculate_total_value com preco acima de entrada soma unrealized."""
    precos = {"WIN$N": Price(Decimal("128500"))}  # +500 unrealized
    resultado = portfolio_com_buy.calculate_total_value(current_prices=precos)
    esperado = capital_inicial.amount + Decimal("500")
    assert resultado.amount == esperado


# ---------------------------------------------------------------------------
# AC-8: calculate_total_value com precos negativos reduz total
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_total_value_com_precos_negativos_reduz_total(
    portfolio_com_buy: Portfolio,
    capital_inicial: Money,
) -> None:
    """AC-8: calculate_total_value com preco abaixo de entrada reduz total."""
    precos = {"WIN$N": Price(Decimal("127000"))}  # -1000 unrealized
    resultado = portfolio_com_buy.calculate_total_value(current_prices=precos)
    esperado = capital_inicial.amount + Decimal("-1000")
    assert resultado.amount == esperado


# ---------------------------------------------------------------------------
# AC-9: multiplas posicoes sao somadas
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unrealized_multiplas_posicoes(capital_inicial: Money) -> None:
    """AC-9: Multiplas posicoes abertas sao somadas corretamente."""
    p = Portfolio(initial_capital=capital_inicial)

    trade1 = Trade(
        symbol=Symbol("WIN$N"),
        side=OrderSide.BUY,
        quantity=Quantity(1),
        entry_price=Price(Decimal("128000")),
        entry_time=datetime.now(),
    )
    trade2 = Trade(
        symbol=Symbol("WDO$N"),
        side=OrderSide.BUY,
        quantity=Quantity(2),
        entry_price=Price(Decimal("5000")),
        entry_time=datetime.now(),
    )

    p.open_trade(trade1, Percentage(Decimal("0.01")))
    p.open_trade(trade2, Percentage(Decimal("0.01")))

    precos = {
        "WIN$N": Price(Decimal("128200")),  # +200 * 1 = +200
        "WDO$N": Price(Decimal("5050")),    # +50 * 2 = +100
    }
    resultado = p.calculate_unrealized_pnl(precos)
    assert resultado.amount == Decimal("300")


# ---------------------------------------------------------------------------
# AC-10: DashboardDataSnapshot serializa pnl_nao_realizado_reais
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dashboard_snapshot_serializa_pnl_nao_realizado() -> None:
    """AC-10: DashboardDataSnapshot.para_dict deve incluir pnl_nao_realizado_reais."""
    stats = TradeStats(
        total_trades=5,
        total_ganhos=3,
        total_perdas=2,
        total_breakeven=0,
        win_rate=60.0,
        pnl_total_reais=1500.0,
        pnl_total_pct=3.0,
        pnl_nao_realizado_reais=750.0,
    )
    metricas = OperationalMetrics(
        sharpe_ratio=1.5,
        profit_factor_bruto=2.0,
        tempo_posicao_media_minutos=25.0,
        percentual_fechamento_tp=60.0,
        percentual_fechamento_sl=25.0,
        percentual_fechamento_manual=15.0,
    )
    protecao = ProtectionStatus(
        trades_ultima_hora=2,
        limite_trades_hora=3,
        cooldown_segundos_restantes=0,
        total_bloqueios_hora=0,
        contador_perda_consecutiva=0,
        horario_permite_tradear=True,
    )
    snapshot = DashboardDataSnapshot(
        timestamp=datetime.now(),
        trade_stats=stats,
        metricas_operacionais=metricas,
        protecao_status=protecao,
        pnl_nao_realizado_reais=750.0,
    )

    payload = snapshot.para_dict()

    assert "pnl_nao_realizado_reais" in payload
    assert payload["pnl_nao_realizado_reais"] == 750.0
    assert payload["trade_stats"]["pnl_nao_realizado_reais"] == 750.0


# ---------------------------------------------------------------------------
# AC-11: obter_snapshot_dashboard aceita pnl_nao_realizado_reais
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_stats_query_service_aceita_pnl_nao_realizado() -> None:
    """AC-11: StatsQueryService.obter_snapshot_dashboard aceita pnl externo."""
    svc = StatsQueryService()
    snapshot = svc.obter_snapshot_dashboard(pnl_nao_realizado_reais=1234.56)

    assert snapshot.pnl_nao_realizado_reais == 1234.56
    assert snapshot.trade_stats.pnl_nao_realizado_reais == 1234.56


# ---------------------------------------------------------------------------
# AC-12: Logs auditaveis sao gerados
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_logs_auditaveis_durante_calculo(
    portfolio_com_buy: Portfolio,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC-12: Calculos de P&L nao realizado devem emitir logs auditaveis (INFO)."""
    precos = {"WIN$N": Price(Decimal("128300"))}

    with caplog.at_level(logging.INFO, logger="src.domain.entities.portfolio"):
        portfolio_com_buy.calculate_total_value(current_prices=precos)

    msgs = " ".join(caplog.messages)
    assert "pnl_nao_realizado" in msgs
    assert "128300" in msgs or "portfolio_total_value" in msgs
