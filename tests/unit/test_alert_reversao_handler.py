"""
Testes Unitarios para AlertReversaoHandler (BLID-044)

Cobertura:
- Conversao ProfitProtectionResult → AlertaOportunidade
- Throttling de alertas duplicados
- Webhook dispatch (Slack/Discord)
- Integracao com AlertaDeliveryManager
- Validacoes de entrada e edge cases
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from src.application.alert_reversao_handler import (
    AlertReversaoConfig,
    AlertReversaoHandler,
)
from src.application.profit_protection_engine import (
    ProtectionStatus,
    ProfitProtectionResult,
)
from src.domain.enums.alerta_enums import NivelAlerta, PatraoAlerta, StatusAlerta


@pytest.fixture
def mock_delivery_manager():
    """Mock do AlertaDeliveryManager."""
    manager = Mock()
    manager.entregar_alerta = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def config_padrao():
    """Configuracao padrao para testes."""
    return AlertReversaoConfig(
        habilitado=True,
        webhook_url="https://hooks.slack.com/test",
        webhook_timeout_sec=5.0,
        throttle_seconds=60,
        nivel_padrao=NivelAlerta.ALTO,
        incluir_snapshot_trade=True,
    )


@pytest.fixture
def handler(mock_delivery_manager, config_padrao):
    """Handler com mocks configurados."""
    return AlertReversaoHandler(
        delivery_manager=mock_delivery_manager,
        config=config_padrao,
    )


@pytest.fixture
def resultado_alerta():
    """ProfitProtectionResult com status=ALERTA."""
    return ProfitProtectionResult(
        trade_id="TRADE-123",
        status=ProtectionStatus.ALERTA,
        profit_atual=1.5,
        profit_objetivo=2.0,
        acao_sugerida="Mover SL para break-even",
        timestamp=datetime.now(),
        lucro_maximo_sessao=2.2,
        deviance_reversao=-0.7,
    )


@pytest.fixture
def trade_data():
    """Dados de trade completos."""
    return {
        "symbol": "WINFUT",
        "entry_price": 120000.0,
        "direction": "BUY",
        "initial_sl": 118800.0,  # -1%
        "initial_tp": 122400.0,  # +2%
        "quantity": 1,
    }


class TestAlertReversaoHandler:
    """Suite de testes para AlertReversaoHandler."""

    def test_init_config_padrao(self, mock_delivery_manager):
        """Teste: Inicializacao com config padrao."""
        handler = AlertReversaoHandler(delivery_manager=mock_delivery_manager)

        assert handler.config.habilitado is True
        assert handler.config.webhook_url is None
        assert handler.config.throttle_seconds == 60
        assert handler.config.nivel_padrao == NivelAlerta.ALTO
        assert handler._historico_alertas == {}

    def test_init_config_customizada(self, mock_delivery_manager):
        """Teste: Inicializacao com config customizada."""
        config = AlertReversaoConfig(
            habilitado=False,
            webhook_url="https://custom.webhook",
            throttle_seconds=120,
            nivel_padrao=NivelAlerta.CRÍTICO,
        )

        handler = AlertReversaoHandler(
            delivery_manager=mock_delivery_manager, config=config
        )

        assert handler.config.habilitado is False
        assert handler.config.webhook_url == "https://custom.webhook"
        assert handler.config.throttle_seconds == 120
        assert handler.config.nivel_padrao == NivelAlerta.CRÍTICO

    @pytest.mark.asyncio
    async def test_processar_reversao_desabilitado(
        self, handler, resultado_alerta, trade_data
    ):
        """Teste: Alertas desabilitados nao disparam."""
        handler.config.habilitado = False

        resultado = await handler.processar_reversao(resultado_alerta, trade_data)

        assert resultado is False
        handler.delivery_manager.entregar_alerta.assert_not_called()

    @pytest.mark.asyncio
    async def test_processar_reversao_status_nao_alerta(
        self, handler, resultado_alerta, trade_data
    ):
        """Teste: Status diferente de ALERTA nao dispara."""
        resultado_alerta.status = ProtectionStatus.ATIVO

        resultado = await handler.processar_reversao(resultado_alerta, trade_data)

        assert resultado is False
        handler.delivery_manager.entregar_alerta.assert_not_called()

    @pytest.mark.asyncio
    async def test_processar_reversao_sucesso(
        self, handler, resultado_alerta, trade_data
    ):
        """Teste: Reversao detectada dispara alerta com sucesso."""
        resultado = await handler.processar_reversao(resultado_alerta, trade_data)

        assert resultado is True
        handler.delivery_manager.entregar_alerta.assert_called_once()

        # Verificar alerta criado
        alerta = handler.delivery_manager.entregar_alerta.call_args[0][0]
        assert alerta.padrao == PatraoAlerta.REVERSAO_LUCRO
        assert alerta.nivel == NivelAlerta.ALTO
        assert alerta.status == StatusAlerta.GERADO
        assert alerta.ativo.value == "WINFUT"

    @pytest.mark.asyncio
    async def test_processar_reversao_trade_data_invalido(
        self, handler, resultado_alerta
    ):
        """Teste: trade_data sem keys obrigatorias lanca ValueError."""
        trade_data_invalido = {"symbol": "WINFUT"}  # faltando entry_price, direction

        with pytest.raises(ValueError, match="faltando keys obrigatorias"):
            await handler.processar_reversao(resultado_alerta, trade_data_invalido)

    @pytest.mark.asyncio
    async def test_processar_reversao_throttling(
        self, handler, resultado_alerta, trade_data
    ):
        """Teste: Throttling bloqueia alertas duplicados."""
        # Primeira chamada: sucesso
        resultado1 = await handler.processar_reversao(resultado_alerta, trade_data)
        assert resultado1 is True

        # Segunda chamada imediata: throttle
        resultado2 = await handler.processar_reversao(resultado_alerta, trade_data)
        assert resultado2 is False

        # Delivery manager chamado apenas uma vez
        assert handler.delivery_manager.entregar_alerta.call_count == 1

    @pytest.mark.asyncio
    async def test_processar_reversao_throttling_expira(
        self, handler, resultado_alerta, trade_data
    ):
        """Teste: Throttling expira apos tempo configurado."""
        handler.config.throttle_seconds = 1  # 1 segundo para teste

        # Primeira chamada
        resultado1 = await handler.processar_reversao(resultado_alerta, trade_data)
        assert resultado1 is True

        # Aguardar expiracao de throttle
        await asyncio.sleep(1.1)

        # Segunda chamada: permitida
        resultado2 = await handler.processar_reversao(resultado_alerta, trade_data)
        assert resultado2 is True

        # Ambas chamadas executadas
        assert handler.delivery_manager.entregar_alerta.call_count == 2

    @pytest.mark.asyncio
    @patch("src.application.alert_reversao_handler.httpx.AsyncClient")
    async def test_enviar_webhook_sucesso(
        self, mock_httpx, handler, resultado_alerta, trade_data
    ):
        """Teste: Webhook enviado com sucesso."""
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        alerta_id = uuid4()
        resultado = await handler._enviar_webhook(
            resultado_alerta, trade_data, alerta_id
        )

        assert resultado is True
        mock_client.post.assert_called_once()

        # Verificar URL e payload
        call_args = mock_client.post.call_args
        assert call_args[0][0] == handler.config.webhook_url
        assert "json" in call_args[1]
        payload = call_args[1]["json"]
        assert "text" in payload
        assert "blocks" in payload

    @pytest.mark.asyncio
    @patch("src.application.alert_reversao_handler.httpx.AsyncClient")
    async def test_enviar_webhook_erro_http(
        self, mock_httpx, handler, resultado_alerta, trade_data
    ):
        """Teste: Webhook com erro HTTP (4xx/5xx)."""
        # Mock httpx response com erro
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        alerta_id = uuid4()
        resultado = await handler._enviar_webhook(
            resultado_alerta, trade_data, alerta_id
        )

        assert resultado is False

    @pytest.mark.asyncio
    @patch("src.application.alert_reversao_handler.httpx.AsyncClient")
    async def test_enviar_webhook_timeout(
        self, mock_httpx, handler, resultado_alerta, trade_data
    ):
        """Teste: Webhook com timeout."""
        import httpx

        # Mock httpx timeout exception
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")
        mock_httpx.return_value.__aenter__.return_value = mock_client

        alerta_id = uuid4()
        resultado = await handler._enviar_webhook(
            resultado_alerta, trade_data, alerta_id
        )

        assert resultado is False

    def test_criar_alerta_oportunidade_buy(
        self, handler, resultado_alerta, trade_data
    ):
        """Teste: Criacao de alerta para trade BUY."""
        alerta = handler._criar_alerta_oportunidade(
            resultado=resultado_alerta,
            symbol_str=trade_data["symbol"],
            entry_price=trade_data["entry_price"],
            direction=trade_data["direction"],
            trade_data=trade_data,
        )

        assert alerta.padrao == PatraoAlerta.REVERSAO_LUCRO
        assert alerta.nivel == NivelAlerta.ALTO
        assert alerta.ativo.value == "WINFUT"
        assert alerta.status == StatusAlerta.GERADO
        assert alerta.confianca >= Decimal("0")
        assert alerta.confianca <= Decimal("1")
        assert alerta.risk_reward > Decimal("0")

    def test_criar_alerta_oportunidade_sell(
        self, handler, resultado_alerta
    ):
        """Teste: Criacao de alerta para trade SELL."""
        trade_data_sell = {
            "symbol": "WINFUT",
            "entry_price": 120000.0,
            "direction": "SELL",
            "initial_sl": 121200.0,  # +1%
            "initial_tp": 118800.0,  # -1%
            "quantity": 1,
        }

        alerta = handler._criar_alerta_oportunidade(
            resultado=resultado_alerta,
            symbol_str=trade_data_sell["symbol"],
            entry_price=trade_data_sell["entry_price"],
            direction=trade_data_sell["direction"],
            trade_data=trade_data_sell,
        )

        assert alerta.padrao == PatraoAlerta.REVERSAO_LUCRO
        assert alerta.ativo.value == "WINFUT"

    def test_construir_payload_webhook(
        self, handler, resultado_alerta, trade_data
    ):
        """Teste: Payload webhook formatado corretamente."""
        alerta_id = uuid4()
        payload = handler._construir_payload_webhook(
            resultado_alerta, trade_data, alerta_id
        )

        assert "text" in payload
        assert "blocks" in payload
        assert len(payload["blocks"]) > 0
        assert "type" in payload["blocks"][0]
        assert payload["blocks"][0]["type"] == "section"

        # Verificar conteudo do texto
        texto = payload["blocks"][0]["text"]["text"]
        assert "Reversão de Lucro Detectada" in texto
        assert "TRADE-123" in texto
        assert "WINFUT" in texto
        assert str(alerta_id) in texto

    def test_deve_throttle_sem_historico(self, handler):
        """Teste: Sem historico, nao deve throttle."""
        assert handler._deve_throttle("TRADE-999") is False

    def test_deve_throttle_com_alerta_recente(self, handler):
        """Teste: Alerta recente deve throttle."""
        handler._historico_alertas["TRADE-123"] = datetime.now()
        assert handler._deve_throttle("TRADE-123") is True

    def test_deve_throttle_apos_expiracao(self, handler):
        """Teste: Apos expiracao, nao deve throttle."""
        # Alerta de 2 minutos atras (throttle = 60s)
        handler._historico_alertas["TRADE-123"] = datetime.now() - timedelta(
            seconds=120
        )
        assert handler._deve_throttle("TRADE-123") is False

    def test_registrar_alerta(self, handler):
        """Teste: Registro de alerta funciona."""
        assert "TRADE-123" not in handler._historico_alertas

        handler._registrar_alerta("TRADE-123")

        assert "TRADE-123" in handler._historico_alertas
        assert isinstance(handler._historico_alertas["TRADE-123"], datetime)

    def test_registrar_alerta_limpeza_historico(self, handler):
        """Teste: Limpeza de historico antigo."""
        # Adicionar alertas antigos (>24h)
        handler._historico_alertas["OLD-1"] = datetime.now() - timedelta(hours=25)
        handler._historico_alertas["OLD-2"] = datetime.now() - timedelta(hours=30)
        handler._historico_alertas["RECENT"] = datetime.now() - timedelta(hours=1)

        # Registrar novo alerta (triggers limpeza)
        handler._registrar_alerta("NEW")

        # Apenas RECENT e NEW devem permanecer
        assert "OLD-1" not in handler._historico_alertas
        assert "OLD-2" not in handler._historico_alertas
        assert "RECENT" in handler._historico_alertas
        assert "NEW" in handler._historico_alertas


@pytest.mark.integration
class TestAlertReversaoHandlerIntegracao:
    """Testes de integracao com componentes reais."""

    @pytest.mark.asyncio
    async def test_fluxo_completo_sem_webhook(
        self, mock_delivery_manager, resultado_alerta, trade_data
    ):
        """Teste: Fluxo completo sem webhook configurado."""
        config = AlertReversaoConfig(
            habilitado=True,
            webhook_url=None,  # sem webhook
            throttle_seconds=60,
        )

        handler = AlertReversaoHandler(
            delivery_manager=mock_delivery_manager, config=config
        )

        resultado = await handler.processar_reversao(resultado_alerta, trade_data)

        assert resultado is True
        mock_delivery_manager.entregar_alerta.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.application.alert_reversao_handler.httpx.AsyncClient")
    async def test_fluxo_completo_com_webhook(
        self, mock_httpx, mock_delivery_manager, resultado_alerta, trade_data
    ):
        """Teste: Fluxo completo com webhook e entrega multicanal."""
        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_httpx.return_value.__aenter__.return_value = mock_client

        config = AlertReversaoConfig(
            habilitado=True,
            webhook_url="https://hooks.slack.com/test",
            throttle_seconds=60,
        )

        handler = AlertReversaoHandler(
            delivery_manager=mock_delivery_manager, config=config
        )

        resultado = await handler.processar_reversao(resultado_alerta, trade_data)

        assert resultado is True
        mock_delivery_manager.entregar_alerta.assert_called_once()

        # Aguardar webhook asyncrono (fire-and-forget)
        await asyncio.sleep(0.1)
        mock_client.post.assert_called_once()
