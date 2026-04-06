"""Testes focados de confiabilidade de webhook (DT-BLID044-01)."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.application.alert_reversao_handler import (
    AlertReversaoConfig,
    AlertReversaoHandler,
)
from src.application.profit_protection_engine import (
    ProtectionStatus,
    ProfitProtectionResult,
)


@pytest.fixture
def mock_delivery_manager() -> Mock:
    manager = Mock()
    manager.entregar_alerta = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def resultado_alerta() -> ProfitProtectionResult:
    return ProfitProtectionResult(
        trade_id="TRADE-REL-001",
        status=ProtectionStatus.ALERTA,
        profit_atual=0.1,  # mantém preco_atual dentro da faixa de entrada para BUY
        profit_objetivo=2.0,
        acao_sugerida="AGUARDAR",
        timestamp=datetime.now(),
        lucro_maximo_sessao=0.2,
        deviance_reversao=-0.1,
    )


@pytest.fixture
def trade_data() -> dict[str, object]:
    return {
        "symbol": "WINFUT",
        "entry_price": 120000.0,
        "direction": "BUY",
        "initial_sl": 118800.0,
        "initial_tp": 122400.0,
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_webhook_retry_ate_sucesso(
    mock_delivery_manager: Mock,
    resultado_alerta: ProfitProtectionResult,
    trade_data: dict[str, object],
) -> None:
    cfg = AlertReversaoConfig(
        webhook_url="https://hooks.slack.com/test",
        webhook_retry_attempts=3,
        webhook_retry_backoff_sec=0.0,
        webhook_fire_and_forget=False,
        persistir_throttle_state=False,
    )
    handler = AlertReversaoHandler(delivery_manager=mock_delivery_manager, config=cfg)
    handler._enviar_webhook = AsyncMock(side_effect=[False, False, True])  # type: ignore[method-assign]

    ok = await handler.processar_reversao(resultado_alerta, trade_data)

    assert ok is True
    assert handler._enviar_webhook.await_count == 3  # type: ignore[attr-defined]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_webhook_retry_respeita_limite_tentativas(
    mock_delivery_manager: Mock,
    resultado_alerta: ProfitProtectionResult,
    trade_data: dict[str, object],
) -> None:
    cfg = AlertReversaoConfig(
        webhook_url="https://hooks.slack.com/test",
        webhook_retry_attempts=2,
        webhook_retry_backoff_sec=0.0,
        webhook_fire_and_forget=False,
        persistir_throttle_state=False,
    )
    handler = AlertReversaoHandler(delivery_manager=mock_delivery_manager, config=cfg)
    handler._enviar_webhook = AsyncMock(return_value=False)  # type: ignore[method-assign]

    ok = await handler.processar_reversao(resultado_alerta, trade_data)

    # entrega principal (delivery_manager) pode ser True, mas webhook falhou após retries
    assert ok is True
    assert handler._enviar_webhook.await_count == 2  # type: ignore[attr-defined]
