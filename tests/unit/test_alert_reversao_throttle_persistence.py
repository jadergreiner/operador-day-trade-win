"""Testes focados da persistencia de throttling (DT-BLID044-02)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from src.application.alert_reversao_handler import (
    AlertReversaoConfig,
    AlertReversaoHandler,
)


@pytest.fixture
def mock_delivery_manager() -> Mock:
    manager = Mock()
    manager.entregar_alerta = AsyncMock(return_value=True)
    return manager


@pytest.mark.unit
def test_persistencia_throttle_cria_arquivo_estado(
    tmp_path: Path, mock_delivery_manager: Mock
) -> None:
    state_path = tmp_path / "alert_reversao_throttle_state.json"
    cfg = AlertReversaoConfig(
        persistir_throttle_state=True,
        throttle_state_path=str(state_path),
    )
    handler = AlertReversaoHandler(delivery_manager=mock_delivery_manager, config=cfg)
    handler._registrar_alerta("TRADE-001")

    assert state_path.exists()
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert "TRADE-001" in payload["historico_alertas"]


@pytest.mark.unit
def test_persistencia_throttle_carrega_estado_no_startup(
    tmp_path: Path, mock_delivery_manager: Mock
) -> None:
    state_path = tmp_path / "alert_reversao_throttle_state.json"
    cfg = AlertReversaoConfig(
        persistir_throttle_state=True,
        throttle_state_path=str(state_path),
    )
    handler_a = AlertReversaoHandler(delivery_manager=mock_delivery_manager, config=cfg)
    handler_a._registrar_alerta("TRADE-RESTORE")

    handler_b = AlertReversaoHandler(delivery_manager=mock_delivery_manager, config=cfg)
    assert handler_b._deve_throttle("TRADE-RESTORE") is True


@pytest.mark.unit
def test_persistencia_throttle_desabilitada_nao_escreve_arquivo(
    tmp_path: Path, mock_delivery_manager: Mock
) -> None:
    state_path = tmp_path / "alert_reversao_throttle_state.json"
    cfg = AlertReversaoConfig(
        persistir_throttle_state=False,
        throttle_state_path=str(state_path),
    )
    handler = AlertReversaoHandler(delivery_manager=mock_delivery_manager, config=cfg)
    handler._registrar_alerta("TRADE-INMEM")

    assert not state_path.exists()
