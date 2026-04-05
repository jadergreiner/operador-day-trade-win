"""Testes unitários para AlertReversaoHandler (BLID-044).

Cobertura:
- ConfiguracaoAlertReversao: carregamento YAML, fallback, defaults
- AlertReversaoHandler: throttling, conversao de dominio, entrega multicanal
- Webhook: payload, fire-and-forget, falha silenciosa
- Determinacao de nivel: palavras-chave, fallback MEDIO
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.alert_reversao_handler import (
    AlertReversaoHandler,
    ConfiguracaoAlertReversao,
    _SCHEMA_VERSION,
)
from src.application.profit_protection_engine import (
    ProfitProtectionResult,
    ProtectionStatus,
)
from src.domain.enums.alerta_enums import NivelAlerta


# ============================================================
# FIXTURES
# ============================================================


def _resultado_alerta(
    trade_id: str = "T001",
    profit_atual: float = -0.4,
    acao: str = "break-even stop recomendado",
    lucro_maximo: float = 1.8,
    deviance: float = 2.2,
) -> ProfitProtectionResult:
    """Cria ProfitProtectionResult com status=ALERTA."""
    return ProfitProtectionResult(
        trade_id=trade_id,
        status=ProtectionStatus.ALERTA,
        profit_atual=profit_atual,
        profit_objetivo=2.0,
        acao_sugerida=acao,
        timestamp=datetime(2026, 4, 6, 10, 30, 0),
        lucro_maximo_sessao=lucro_maximo,
        deviance_reversao=deviance,
    )


def _resultado_ativo(trade_id: str = "T002") -> ProfitProtectionResult:
    """Cria ProfitProtectionResult com status=ATIVO (nao deve gerar alerta)."""
    return ProfitProtectionResult(
        trade_id=trade_id,
        status=ProtectionStatus.ATIVO,
        profit_atual=1.2,
        profit_objetivo=2.0,
        acao_sugerida="manter posicao",
        timestamp=datetime(2026, 4, 6, 10, 35, 0),
    )


def _config_sem_throttle() -> ConfiguracaoAlertReversao:
    """Config com throttling zerado para testes sem espera."""
    return ConfiguracaoAlertReversao(throttling_segundos=0)


def _config_sem_canais() -> ConfiguracaoAlertReversao:
    """Config com todos os canais desativados."""
    return ConfiguracaoAlertReversao(
        throttling_segundos=0,
        delivery_manager_ativo=False,
        webhook_ativo=False,
    )


# ============================================================
# TESTES: ConfiguracaoAlertReversao
# ============================================================


class TestConfiguracaoAlertReversao:
    """Testes de carregamento e defaults da configuracao."""

    def test_defaults_sem_arquivo(self, tmp_path: Path) -> None:
        """Arquivo ausente retorna defaults (ADR-023)."""
        config = ConfiguracaoAlertReversao.do_yaml(tmp_path / "nao_existe.yaml")
        assert config.throttling_segundos == 60
        assert config.webhook_url == ""
        assert config.delivery_manager_ativo is True
        assert config.webhook_ativo is True

    def test_carrega_arquivo_valido(self, tmp_path: Path) -> None:
        """Arquivo YAML valido e carregado corretamente."""
        yaml_content = """
version: "1.0.0"
throttling_segundos: 30
webhook:
  url: "https://hooks.slack.com/test"
  timeout_segundos: 3
canais:
  delivery_manager: true
  webhook: false
"""
        arquivo = tmp_path / "alert_reversoes.yaml"
        arquivo.write_text(yaml_content, encoding="utf-8")
        config = ConfiguracaoAlertReversao.do_yaml(arquivo)

        assert config.throttling_segundos == 30
        assert config.webhook_url == "https://hooks.slack.com/test"
        assert config.webhook_timeout_segundos == 3
        assert config.delivery_manager_ativo is True
        assert config.webhook_ativo is False

    def test_yaml_invalido_retorna_defaults(self, tmp_path: Path) -> None:
        """YAML com conteudo invalido retorna defaults (ADR-023)."""
        arquivo = tmp_path / "alert_reversoes.yaml"
        arquivo.write_text(":::invalido", encoding="utf-8")
        config = ConfiguracaoAlertReversao.do_yaml(arquivo)
        assert config.throttling_segundos == 60

    def test_niveis_por_acao_defaults(self) -> None:
        """Niveis por acao possuem entradas esperadas."""
        config = ConfiguracaoAlertReversao()
        assert "fechar total" in config.niveis_por_acao["critico"]
        assert "break-even" in config.niveis_por_acao["alto"]
        assert "_default" in config.niveis_por_acao["medio"]


# ============================================================
# TESTES: Throttling
# ============================================================


class TestThrottling:
    """Testes de throttling por trade_id."""

    def test_primeiro_envio_permitido(self) -> None:
        """Primeiro envio para trade_id e sempre permitido."""
        handler = AlertReversaoHandler(config=_config_sem_throttle())
        assert handler._pode_enviar("T001") is True

    def test_segundo_envio_bloqueado_dentro_do_intervalo(self) -> None:
        """Segundo envio dentro do intervalo de throttle e bloqueado."""
        config = ConfiguracaoAlertReversao(throttling_segundos=60)
        handler = AlertReversaoHandler(config=config)
        handler._registrar_envio("T001")
        assert handler._pode_enviar("T001") is False

    def test_envio_permitido_apos_intervalo(self) -> None:
        """Envio permitido apos expirar o intervalo de throttle."""
        config = ConfiguracaoAlertReversao(throttling_segundos=0)
        handler = AlertReversaoHandler(config=config)
        handler._registrar_envio("T001")
        time.sleep(0.01)
        assert handler._pode_enviar("T001") is True

    def test_trades_diferentes_nao_interferem(self) -> None:
        """Throttle de um trade nao afeta outro trade_id."""
        config = ConfiguracaoAlertReversao(throttling_segundos=60)
        handler = AlertReversaoHandler(config=config)
        handler._registrar_envio("T001")
        assert handler._pode_enviar("T002") is True

    def test_limpar_throttle_trade_especifico(self) -> None:
        """limpar_throttle remove entrada de trade especifico."""
        config = ConfiguracaoAlertReversao(throttling_segundos=60)
        handler = AlertReversaoHandler(config=config)
        handler._registrar_envio("T001")
        handler._registrar_envio("T002")
        handler.limpar_throttle("T001")
        assert handler._pode_enviar("T001") is True
        assert handler._pode_enviar("T002") is False

    def test_limpar_throttle_todos(self) -> None:
        """limpar_throttle sem argumento limpa todo o cache."""
        config = ConfiguracaoAlertReversao(throttling_segundos=60)
        handler = AlertReversaoHandler(config=config)
        handler._registrar_envio("T001")
        handler._registrar_envio("T002")
        handler.limpar_throttle()
        assert handler._pode_enviar("T001") is True
        assert handler._pode_enviar("T002") is True

    def test_throttle_thread_safe(self) -> None:
        """Throttle e seguro para uso em multiplas threads."""
        config = ConfiguracaoAlertReversao(throttling_segundos=60)
        handler = AlertReversaoHandler(config=config)
        erros: List[Exception] = []

        def _registrar() -> None:
            try:
                for i in range(100):
                    handler._registrar_envio(f"T{i}")
                    handler._pode_enviar(f"T{i}")
            except Exception as exc:
                erros.append(exc)

        threads = [threading.Thread(target=_registrar) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert erros == [], f"Erros em threads: {erros}"


# ============================================================
# TESTES: Determinacao de nivel
# ============================================================


class TestDeterminarNivel:
    """Testes de mapeamento acao_sugerida -> NivelAlerta."""

    def _handler(self) -> AlertReversaoHandler:
        return AlertReversaoHandler(config=_config_sem_canais())

    def test_nivel_critico_fechar_total(self) -> None:
        handler = self._handler()
        nivel = handler._determinar_nivel("fechar total imediatamente")
        assert nivel == NivelAlerta.CRÍTICO

    def test_nivel_critico_fechar_imediatamente(self) -> None:
        handler = self._handler()
        nivel = handler._determinar_nivel("fechar imediatamente — risco extremo")
        assert nivel == NivelAlerta.CRÍTICO

    def test_nivel_alto_break_even(self) -> None:
        handler = self._handler()
        nivel = handler._determinar_nivel("break-even stop recomendado")
        assert nivel == NivelAlerta.ALTO

    def test_nivel_alto_fechar_parcial(self) -> None:
        handler = self._handler()
        nivel = handler._determinar_nivel("fechar parcial 50%")
        assert nivel == NivelAlerta.ALTO

    def test_nivel_alto_reversao_aguda(self) -> None:
        handler = self._handler()
        nivel = handler._determinar_nivel("reversao aguda detectada")
        assert nivel == NivelAlerta.ALTO

    def test_nivel_medio_fallback(self) -> None:
        """Acao sem palavra-chave mapeada resulta em MEDIO."""
        handler = self._handler()
        nivel = handler._determinar_nivel("aguardar movimento")
        assert nivel == NivelAlerta.MÉDIO

    def test_nivel_medio_sem_keyword(self) -> None:
        """Acao completamente desconhecida retorna MEDIO."""
        handler = self._handler()
        nivel = handler._determinar_nivel("nenhuma acao especifica")
        assert nivel == NivelAlerta.MÉDIO


# ============================================================
# TESTES: processar — fluxo principal
# ============================================================


class TestProcessar:
    """Testes do metodo processar() — fluxo principal."""

    @pytest.mark.asyncio
    async def test_ignora_status_nao_alerta(self) -> None:
        """Resultado com status != ALERTA retorna False sem disparar."""
        handler = AlertReversaoHandler(config=_config_sem_canais())
        resultado = _resultado_ativo()
        enviado = await handler.processar(resultado)
        assert enviado is False

    @pytest.mark.asyncio
    async def test_ignora_parado(self) -> None:
        """Status PARADO e ignorado."""
        config = _config_sem_canais()
        handler = AlertReversaoHandler(config=config)
        resultado = ProfitProtectionResult(
            trade_id="T099",
            status=ProtectionStatus.PARADO,
            profit_atual=-1.0,
            profit_objetivo=2.0,
            acao_sugerida="aguardar",
            timestamp=datetime.now(),
        )
        enviado = await handler.processar(resultado)
        assert enviado is False

    @pytest.mark.asyncio
    async def test_alerta_enviado_retorna_true(self) -> None:
        """ALERTA sem throttle retorna True."""
        handler = AlertReversaoHandler(config=_config_sem_canais())
        resultado = _resultado_alerta()
        enviado = await handler.processar(resultado)
        assert enviado is True

    @pytest.mark.asyncio
    async def test_throttle_bloqueia_segundo_envio(self) -> None:
        """Segundo envio do mesmo trade dentro do intervalo retorna False."""
        config = ConfiguracaoAlertReversao(
            throttling_segundos=60,
            delivery_manager_ativo=False,
            webhook_ativo=False,
        )
        handler = AlertReversaoHandler(config=config)
        resultado = _resultado_alerta(trade_id="TH01")
        await handler.processar(resultado)
        enviado = await handler.processar(resultado)
        assert enviado is False

    @pytest.mark.asyncio
    async def test_delivery_manager_chamado(self) -> None:
        """delivery_manager.entregar_alerta e chamado quando ativo."""
        mock_dm = AsyncMock()
        mock_dm.entregar_alerta = AsyncMock(return_value=True)
        config = ConfiguracaoAlertReversao(
            throttling_segundos=0,
            delivery_manager_ativo=True,
            webhook_ativo=False,
        )
        handler = AlertReversaoHandler(delivery_manager=mock_dm, config=config)
        resultado = _resultado_alerta(trade_id="TDM01")
        await handler.processar(resultado)
        mock_dm.entregar_alerta.assert_called_once()

    @pytest.mark.asyncio
    async def test_delivery_manager_nao_chamado_quando_desativado(self) -> None:
        """delivery_manager nao e chamado quando canal desativado."""
        mock_dm = AsyncMock()
        mock_dm.entregar_alerta = AsyncMock(return_value=True)
        config = ConfiguracaoAlertReversao(
            throttling_segundos=0,
            delivery_manager_ativo=False,
            webhook_ativo=False,
        )
        handler = AlertReversaoHandler(delivery_manager=mock_dm, config=config)
        resultado = _resultado_alerta(trade_id="TDMOFF")
        await handler.processar(resultado)
        mock_dm.entregar_alerta.assert_not_called()

    @pytest.mark.asyncio
    async def test_delivery_manager_none_nao_dispara(self) -> None:
        """delivery_manager=None nao lanca excecao."""
        config = ConfiguracaoAlertReversao(
            throttling_segundos=0,
            delivery_manager_ativo=True,
            webhook_ativo=False,
        )
        handler = AlertReversaoHandler(delivery_manager=None, config=config)
        resultado = _resultado_alerta(trade_id="TNONE")
        enviado = await handler.processar(resultado)
        assert enviado is True  # alerta foi processado, sem erro

    @pytest.mark.asyncio
    async def test_delivery_manager_excecao_nao_propaga(self) -> None:
        """Excecao no delivery_manager nao propaga para o chamador."""
        mock_dm = AsyncMock()
        mock_dm.entregar_alerta = AsyncMock(side_effect=RuntimeError("falha smtp"))
        config = ConfiguracaoAlertReversao(
            throttling_segundos=0,
            delivery_manager_ativo=True,
            webhook_ativo=False,
        )
        handler = AlertReversaoHandler(delivery_manager=mock_dm, config=config)
        resultado = _resultado_alerta(trade_id="TEXC")
        enviado = await handler.processar(resultado)
        assert enviado is True  # nao propaga excecao


# ============================================================
# TESTES: Webhook
# ============================================================


class TestWebhook:
    """Testes do webhook Slack/Discord."""

    def test_payload_contem_campos_obrigatorios(self) -> None:
        """Payload do webhook tem todos os campos esperados."""
        config = _config_sem_canais()
        handler = AlertReversaoHandler(config=config)
        resultado = _resultado_alerta(trade_id="TW01")
        from src.application.alert_reversao_handler import AlertaOportunidade
        from src.domain.value_objects.financial import Price, Symbol
        alerta = handler._converter_para_alerta(resultado, "WINFUT", "BUY")
        payload = handler._montar_payload_webhook(resultado, alerta)

        assert payload["schema_version"] == _SCHEMA_VERSION
        assert payload["tipo"] == "ALERTA_REVERSAO"
        assert "alerta_id" in payload
        assert payload["trade_id"] == "TW01"
        assert "nivel" in payload
        assert "acao_sugerida" in payload
        assert "profit_atual_pct" in payload
        assert "timestamp" in payload
        assert "text" in payload

    def test_payload_serializavel_em_json(self) -> None:
        """Payload e serializavel para JSON sem erros."""
        config = _config_sem_canais()
        handler = AlertReversaoHandler(config=config)
        resultado = _resultado_alerta(trade_id="TW02")
        alerta = handler._converter_para_alerta(resultado, "WINFUT", "BUY")
        payload = handler._montar_payload_webhook(resultado, alerta)
        # Nao deve lancar excecao
        serializado = json.dumps(payload, ensure_ascii=False)
        assert len(serializado) > 0

    @pytest.mark.asyncio
    async def test_webhook_sem_url_nao_dispara(self) -> None:
        """Webhook sem URL configurada nao e disparado."""
        config = ConfiguracaoAlertReversao(
            throttling_segundos=0,
            delivery_manager_ativo=False,
            webhook_ativo=True,
            webhook_url="",  # sem URL
        )
        handler = AlertReversaoHandler(config=config)
        resultado = _resultado_alerta(trade_id="TWU01")
        # Nao deve lancar excecao
        enviado = await handler.processar(resultado)
        assert enviado is True

    @pytest.mark.asyncio
    async def test_webhook_falha_nao_propaga(self) -> None:
        """Falha no webhook (fire-and-forget) nao propaga excecao."""
        config = ConfiguracaoAlertReversao(
            throttling_segundos=0,
            delivery_manager_ativo=False,
            webhook_ativo=True,
            webhook_url="https://hooks.invalid.local/test",
        )
        handler = AlertReversaoHandler(config=config)
        resultado = _resultado_alerta(trade_id="TWF01")

        with patch.object(
            handler, "_enviar_webhook_bloqueante", side_effect=OSError("conn refused")
        ):
            enviado = await handler.processar(resultado)
        assert enviado is True  # falha e silenciosa


# ============================================================
# TESTES: Conversao de dominio
# ============================================================


class TestConversaoDominio:
    """Testes da conversao ProfitProtectionResult -> AlertaOportunidade."""

    def _handler(self) -> AlertReversaoHandler:
        return AlertReversaoHandler(config=_config_sem_canais())

    def test_simbolo_correto(self) -> None:
        """Simbolo do alerta reflete o simbolo passado."""
        handler = self._handler()
        resultado = _resultado_alerta()
        alerta = handler._converter_para_alerta(resultado, "WINFUT", "BUY")
        assert str(alerta.ativo) == "WINFUT"

    def test_padrao_e_volatilidade_extrema(self) -> None:
        """Padrao fixado em VOLATILIDADE_EXTREMA para alertas de reversao."""
        from src.domain.enums.alerta_enums import PatraoAlerta
        handler = self._handler()
        resultado = _resultado_alerta()
        alerta = handler._converter_para_alerta(resultado, "WINFUT", "BUY")
        assert alerta.padrao == PatraoAlerta.VOLATILIDADE_EXTREMA

    def test_nivel_inferido_da_acao(self) -> None:
        """Nivel do alerta e inferido da acao_sugerida."""
        handler = self._handler()
        resultado = _resultado_alerta(acao="break-even stop")
        alerta = handler._converter_para_alerta(resultado, "WINFUT", "BUY")
        assert alerta.nivel == NivelAlerta.ALTO

    def test_confianca_entre_zero_e_um(self) -> None:
        """Confianca do alerta esta no intervalo [0, 1]."""
        handler = self._handler()
        resultado = _resultado_alerta(deviance=10.0)
        alerta = handler._converter_para_alerta(resultado, "WINFUT", "BUY")
        assert Decimal("0") <= alerta.confianca <= Decimal("1")

    def test_confianca_minima_quando_sem_deviance(self) -> None:
        """Confianca minima (0.10) quando deviance_reversao e None."""
        handler = self._handler()
        resultado = ProfitProtectionResult(
            trade_id="TD_NO_DEV",
            status=ProtectionStatus.ALERTA,
            profit_atual=-0.3,
            profit_objetivo=2.0,
            acao_sugerida="aguardar",
            timestamp=datetime.now(),
            deviance_reversao=None,
        )
        alerta = handler._converter_para_alerta(resultado, "WINFUT", "SELL")
        assert alerta.confianca >= Decimal("0.10")

    def test_sinal_smc_nome_reversao(self) -> None:
        """Campo sinal_smc_nome e definido como REVERSAO."""
        handler = self._handler()
        resultado = _resultado_alerta()
        alerta = handler._converter_para_alerta(resultado, "WINFUT", "BUY")
        assert alerta.sinal_smc_nome == "REVERSAO"
