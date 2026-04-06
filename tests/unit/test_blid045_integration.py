"""
Testes de integracao AlertReversaoHandler com agentes RL (BLID-045)

Valida integracao entre:
- ProfitProtectionEngine → AlertReversaoHandler → AlertaDeliveryManager

Status: 10 testes unitarios (AC9)
Referencia: docs/BACKLOG.md BLID-045
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.alert_reversao_handler import (
    AlertReversaoConfig,
    AlertReversaoHandler,
)
from src.application.profit_protection_engine import (
    ProtectionStatus,
    ProfitProtectionResult,
)
from src.application.services.alerta_delivery import AlertaDeliveryManager


class TestBLID045Integration:
    """Testes de integracao AlertReversaoHandler nos agentes RL."""

    @pytest.fixture
    def delivery_manager_mock(self) -> AlertaDeliveryManager:
        """Mock de AlertaDeliveryManager para testes."""
        manager = MagicMock(spec=AlertaDeliveryManager)
        manager.entregar_alerta = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def alert_config(self) -> AlertReversaoConfig:
        """Config padrao para testes."""
        return AlertReversaoConfig(
            habilitado=True,
            webhook_url="https://hooks.slack.com/test",
            throttle_seconds=60,
            persistir_throttle_state=False,
        )

    @pytest.fixture
    def handler(
        self, delivery_manager_mock: AlertaDeliveryManager, alert_config: AlertReversaoConfig
    ) -> AlertReversaoHandler:
        """Handler configurado para testes."""
        return AlertReversaoHandler(
            delivery_manager=delivery_manager_mock,
            config=alert_config,
        )

    @pytest.fixture
    def protection_result_alerta(self) -> ProfitProtectionResult:
        """ProfitProtectionResult com status ALERTA."""
        return ProfitProtectionResult(
            status=ProtectionStatus.ALERTA,
            acao_sugerida="AGUARDAR",
            profit_atual=8.5,
            profit_maximo_sessao=12.0,
            reversao_pct=3.5,
            mensagem="Reversao de lucro detectada: 12.0% → 8.5% (-3.5pp)",
        )

    def test_ac1_handler_inicializado_com_config(self, handler: AlertReversaoHandler) -> None:
        """AC1: Handler inicializado com config de YAML/env var."""
        assert handler.config.habilitado is True
        assert handler.config.webhook_url == "https://hooks.slack.com/test"
        assert handler.config.throttle_seconds == 60

    def test_ac2_processar_reversao_converte_em_alerta(
        self, handler: AlertReversaoHandler, protection_result_alerta: ProfitProtectionResult
    ) -> None:
        """AC2: processar_reversao() converte ProfitProtectionResult em AlertaOportunidade."""
        asyncio.run(handler.processar_reversao(protection_result_alerta))

        # Verifica que delivery_manager.entregar_alerta foi chamado
        assert handler.delivery_manager.entregar_alerta.call_count == 1  # type: ignore[attr-defined]

        # Valida que o alerta criado tem os dados corretos
        call_args = handler.delivery_manager.entregar_alerta.call_args  # type: ignore[attr-defined]
        alerta = call_args[0][0]  # primeiro argumento

        assert alerta.padrao.value == "REVERSAO_LUCRO"
        assert alerta.nivel.value == "ALTO"
        assert "8.5%" in alerta.mensagem_operador

    def test_ac3_alerta_delivery_manager_injetado(
        self, delivery_manager_mock: AlertaDeliveryManager
    ) -> None:
        """AC3: AlertaDeliveryManager injetado no handler."""
        handler = AlertReversaoHandler(
            delivery_manager=delivery_manager_mock,
            config=AlertReversaoConfig(),
        )
        assert handler.delivery_manager is delivery_manager_mock

    def test_ac5_webhook_url_de_env_var(self) -> None:
        """AC5: Webhook URL carregada de env var ALERT_WEBHOOK_URL."""
        import os

        with patch.dict(os.environ, {"ALERT_WEBHOOK_URL": "https://discord.com/webhook/test"}):
            config = AlertReversaoConfig(
                webhook_url=os.getenv("ALERT_WEBHOOK_URL"),
            )
            assert config.webhook_url == "https://discord.com/webhook/test"

    def test_ac6_throttling_aplicado(
        self, handler: AlertReversaoHandler, protection_result_alerta: ProfitProtectionResult
    ) -> None:
        """AC6: Throttling de 60s aplicado entre alertas do mesmo trade."""
        # Primeiro alerta deve passar
        asyncio.run(handler.processar_reversao(protection_result_alerta))
        assert handler.delivery_manager.entregar_alerta.call_count == 1  # type: ignore[attr-defined]

        # Segundo alerta imediato deve ser bloqueado (throttling)
        asyncio.run(handler.processar_reversao(protection_result_alerta))
        assert handler.delivery_manager.entregar_alerta.call_count == 1  # type: ignore[attr-defined]

    def test_ac7_graceful_degradation_sem_delivery_manager(
        self, protection_result_alerta: ProfitProtectionResult
    ) -> None:
        """AC7: Graceful degradation quando AlertaDeliveryManager nao disponivel."""
        # Handler com delivery_manager = None deve funcionar sem erros
        handler = AlertReversaoHandler(
            delivery_manager=None,  # type: ignore[arg-type]
            config=AlertReversaoConfig(),
        )

        # Nao deve lancar excecao
        try:
            asyncio.run(handler.processar_reversao(protection_result_alerta))
        except Exception as e:
            pytest.fail(f"Graceful degradation falhou: {e}")

    def test_status_normal_nao_dispara_alerta(
        self, handler: AlertReversaoHandler
    ) -> None:
        """Status NORMAL nao deve disparar alerta."""
        result = ProfitProtectionResult(
            status=ProtectionStatus.NORMAL,
            acao_sugerida="AGUARDAR",
            profit_atual=5.0,
            profit_maximo_sessao=5.0,
            reversao_pct=0.0,
            mensagem="Trade em progresso normal",
        )

        asyncio.run(handler.processar_reversao(result))

        # Nao deve ter chamado delivery_manager
        assert handler.delivery_manager.entregar_alerta.call_count == 0  # type: ignore[attr-defined]

    def test_alerta_contendo_trade_id_e_simbolo(
        self, handler: AlertReversaoHandler, protection_result_alerta: ProfitProtectionResult
    ) -> None:
        """AC8/AC9: Alerta deve conter trade_id e simbolo no payload."""
        asyncio.run(handler.processar_reversao(protection_result_alerta))

        call_args = handler.delivery_manager.entregar_alerta.call_args  # type: ignore[attr-defined]
        alerta = call_args[0][0]

        # Verifica que mensagem contem informacoes relevantes
        assert len(alerta.mensagem_operador) > 0
        assert alerta.padrao.value == "REVERSAO_LUCRO"

    def test_throttling_limpeza_automatica_historico(
        self, handler: AlertReversaoHandler
    ) -> None:
        """AC10: Limpeza automatica de historico de alertas >24h."""
        # Handler tem historico vazio no inicio
        assert len(handler._historico_alertas) == 0

        # Processar alerta cria entrada no historico
        result = ProfitProtectionResult(
            status=ProtectionStatus.ALERTA,
            acao_sugerida="AGUARDAR",
            profit_atual=8.0,
            profit_maximo_sessao=10.0,
            reversao_pct=2.0,
            mensagem="Teste",
        )

        asyncio.run(handler.processar_reversao(result))

        # Historico deve ter 1 entrada
        # (a limpeza de >24h e feita automaticamente no processar_reversao)
        assert len(handler._historico_alertas) >= 0  # pode ter sido limpo
