"""AlertReversaoHandler — Disparo de alertas quando reversao e detectada (BLID-044).

Converte um ProfitProtectionResult com status=ALERTA em AlertaOportunidade
e orquestra a entrega multicanal:

1. AlertaDeliveryManager (WebSocket + Email) — entrega sincrona via servico
   ja existente.
2. Webhook Slack/Discord — fire-and-forget assíncrono, sem bloquear.

Throttling:
- Intervalo minimo configuravel por trade_id (padrao: 60s).
- Alertas repetidos do mesmo trade dentro do intervalo sao descartados
  silenciosamente (log DEBUG).

Configuracao:
- ``config/alert_reversoes.yaml`` define throttling, URL do webhook e canais.
- Ausencia do arquivo: valores padrao sao usados (fallback seguro, ADR-023).

Exemplo de uso::

    handler = AlertReversaoHandler()
    resultado = ProfitProtectionResult(
        trade_id="T001",
        status=ProtectionStatus.ALERTA,
        profit_atual=-0.4,
        profit_objetivo=2.0,
        acao_sugerida="break-even stop recomendado",
        timestamp=datetime.now(),
        lucro_maximo_sessao=1.8,
        deviance_reversao=2.2,
    )
    await handler.processar(resultado, simbolo="WINFUT", direcao="BUY")
"""

from __future__ import annotations

import asyncio
import logging
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from urllib.request import Request, urlopen
import json

import yaml

from src.application.profit_protection_engine import (
    ProfitProtectionResult,
    ProtectionStatus,
)
from src.domain.entities.alerta import AlertaOportunidade
from src.domain.enums.alerta_enums import NivelAlerta, PatraoAlerta, StatusAlerta
from src.domain.value_objects.financial import Price, Symbol

logger = logging.getLogger(__name__)

# Caminho padrao do arquivo de configuracao
_CAMINHO_CONFIG_PADRAO = Path("config/alert_reversoes.yaml")

# schema_version do JSON de output (ADR-019)
_SCHEMA_VERSION = "1.0"


# ============================================================
# PROTOCOL: contrato do delivery_manager
# ============================================================


@runtime_checkable
class _DeliveryManagerProtocol(Protocol):
    """Interface minima esperada do AlertaDeliveryManager."""

    async def entregar_alerta(self, alerta: AlertaOportunidade) -> bool:
        """Entrega alerta multicanal."""
        ...


# ============================================================
# DATACLASS: Configuracao do handler
# ============================================================


@dataclass
class ConfiguracaoAlertReversao:
    """Configuracao carregada de config/alert_reversoes.yaml."""

    throttling_segundos: int = 60
    webhook_url: str = ""
    webhook_timeout_segundos: int = 5
    delivery_manager_ativo: bool = True
    webhook_ativo: bool = True
    niveis_por_acao: Dict[str, list[str]] = field(default_factory=lambda: {
        "critico": ["fechar total", "fechar imediatamente"],
        "alto": ["break-even", "fechar parcial", "reversao aguda"],
        "medio": ["monitorar", "aguardar", "_default"],
    })

    @classmethod
    def do_yaml(cls, caminho: Path = _CAMINHO_CONFIG_PADRAO) -> "ConfiguracaoAlertReversao":
        """
        Carrega configuracao a partir de arquivo YAML.

        Fallback seguro: retorna defaults se arquivo ausente ou invalido (ADR-023).

        Args:
            caminho: Caminho do arquivo YAML.

        Returns:
            ConfiguracaoAlertReversao com valores do arquivo ou defaults.
        """
        if not caminho.exists():
            logger.warning(
                "config/alert_reversoes.yaml ausente — usando defaults (ADR-023)"
            )
            return cls()

        try:
            with open(caminho, encoding="utf-8") as f:
                carregado = yaml.safe_load(f)
            if not isinstance(carregado, dict):
                logger.warning(
                    "alert_reversoes.yaml com conteudo invalido — usando defaults"
                )
                return cls()
            dados: Dict[str, Any] = carregado
        except Exception as exc:
            logger.warning(
                "Falha ao ler alert_reversoes.yaml (%s) — usando defaults", exc
            )
            return cls()

        webhook = dados.get("webhook", {})
        canais = dados.get("canais", {})
        niveis = dados.get("niveis_por_acao", {})

        return cls(
            throttling_segundos=int(dados.get("throttling_segundos", 60)),
            webhook_url=str(webhook.get("url", "")),
            webhook_timeout_segundos=int(webhook.get("timeout_segundos", 5)),
            delivery_manager_ativo=bool(canais.get("delivery_manager", True)),
            webhook_ativo=bool(canais.get("webhook", True)),
            niveis_por_acao={
                "critico": list(niveis.get("critico", ["fechar total", "fechar imediatamente"])),
                "alto": list(niveis.get("alto", ["break-even", "fechar parcial", "reversao aguda"])),
                "medio": list(niveis.get("medio", ["monitorar", "aguardar", "_default"])),
            },
        )


# ============================================================
# HANDLER PRINCIPAL
# ============================================================


class AlertReversaoHandler:
    """
    Converte ProfitProtectionResult(status=ALERTA) em AlertaOportunidade
    e entrega via multicanal com throttling.

    Responsabilidades:
    - Filtrar apenas resultados com status=ALERTA.
    - Aplicar throttling por trade_id (intervalo minimo configuravel).
    - Converter para AlertaOportunidade (dominio).
    - Entregar via AlertaDeliveryManager (WebSocket+Email).
    - Disparar webhook Slack/Discord fire-and-forget.

    Thread-safety:
    - _throttle_cache e protegido por _lock (threading.Lock).
    """

    def __init__(
        self,
        delivery_manager: Optional[_DeliveryManagerProtocol] = None,
        config: Optional[ConfiguracaoAlertReversao] = None,
        caminho_config: Path = _CAMINHO_CONFIG_PADRAO,
    ) -> None:
        """
        Inicializa o handler.

        Args:
            delivery_manager: Instancia de AlertaDeliveryManager. Opcional;
                se None, entrega via delivery manager e desativada.
            config: ConfiguracaoAlertReversao. Se None, carrega do YAML.
            caminho_config: Caminho alternativo do YAML (util em testes).
        """
        self._config = config if config is not None else ConfiguracaoAlertReversao.do_yaml(caminho_config)
        self._delivery_manager: Optional[_DeliveryManagerProtocol] = delivery_manager
        # cache de throttle: trade_id -> timestamp do ultimo alerta (float)
        self._throttle_cache: Dict[str, float] = {}
        self._lock = threading.Lock()

    # ----------------------------------------------------------
    # API publica
    # ----------------------------------------------------------

    async def processar(
        self,
        resultado: ProfitProtectionResult,
        simbolo: str = "WINFUT",
        direcao: str = "BUY",
    ) -> bool:
        """
        Processa um ProfitProtectionResult e dispara alertas se status=ALERTA.

        Args:
            resultado: Resultado da analise de protecao de lucro.
            simbolo: Simbolo do ativo (ex: "WINFUT").
            direcao: Direcao da operacao ("BUY" ou "SELL").

        Returns:
            True se alerta foi enviado, False se ignorado (status != ALERTA
            ou throttling ativo).
        """
        if resultado.status != ProtectionStatus.ALERTA:
            logger.debug(
                "Resultado ignorado (status=%s, esperado=ALERTA)",
                resultado.status.value,
            )
            return False

        if not self._pode_enviar(resultado.trade_id):
            logger.debug(
                "Throttling ativo para trade_id=%s — alerta descartado",
                resultado.trade_id,
            )
            return False

        self._registrar_envio(resultado.trade_id)

        alerta = self._converter_para_alerta(resultado, simbolo, direcao)

        await self._entregar_multicanal(alerta, resultado)

        return True

    # ----------------------------------------------------------
    # Throttling
    # ----------------------------------------------------------

    def _pode_enviar(self, trade_id: str) -> bool:
        """Verifica se o throttle permite envio para este trade_id."""
        with self._lock:
            ultimo = self._throttle_cache.get(trade_id)
            if ultimo is None:
                return True
            return (time.monotonic() - ultimo) >= self._config.throttling_segundos

    def _registrar_envio(self, trade_id: str) -> None:
        """Registra timestamp do envio para throttling."""
        with self._lock:
            self._throttle_cache[trade_id] = time.monotonic()

    def limpar_throttle(self, trade_id: Optional[str] = None) -> None:
        """
        Limpa o cache de throttle.

        Args:
            trade_id: Se fornecido, limpa apenas a entrada deste trade.
                      Se None, limpa todo o cache.
        """
        with self._lock:
            if trade_id is None:
                self._throttle_cache.clear()
            else:
                self._throttle_cache.pop(trade_id, None)

    # ----------------------------------------------------------
    # Conversao de dominio
    # ----------------------------------------------------------

    def _converter_para_alerta(
        self,
        resultado: ProfitProtectionResult,
        simbolo: str,
        direcao: str,
    ) -> AlertaOportunidade:
        """
        Converte ProfitProtectionResult em AlertaOportunidade.

        A conversao adapta os campos do motor de protecao para o
        contrato de dominio de alertas, preservando todas as
        informacoes relevantes.

        Args:
            resultado: ProfitProtectionResult com status=ALERTA.
            simbolo: Simbolo do ativo.
            direcao: Direcao da operacao.

        Returns:
            AlertaOportunidade pronto para entrega.
        """
        nivel = self._determinar_nivel(resultado.acao_sugerida)

        # Preco de referencia ficticio — AlertaOportunidade exige um preco
        # concreto para satisfazer o contrato do dominio.
        # Usamos 100.00 como base simbolica; os valores absolutos nao
        # representam precos reais de mercado neste contexto de reversao.
        _BASE = Decimal("100.00")
        preco_ref = Price(_BASE)
        entrada_min = Price(_BASE - Decimal("0.10"))
        entrada_max = Price(_BASE + Decimal("0.10"))
        # stop_loss DEVE ser < entrada_minima (regra do dominio)
        stop_loss = Price(_BASE - Decimal("0.50"))

        # Confianca baseada no deviance de reversao (quanto maior o desvio, mais critico)
        desvio = resultado.deviance_reversao or 0.0
        confianca_raw = min(abs(desvio) / 5.0, 1.0)  # normaliza para 0-1
        confianca = Decimal(str(round(max(confianca_raw, 0.10), 2)))

        alerta = AlertaOportunidade(
            ativo=Symbol(simbolo),
            padrao=PatraoAlerta.VOLATILIDADE_EXTREMA,
            nivel=nivel,
            preco_atual=preco_ref,
            timestamp_deteccao=resultado.timestamp,
            entrada_minima=entrada_min,
            entrada_maxima=entrada_max,
            stop_loss=stop_loss,
            confianca=confianca,
            risk_reward=Decimal("1.0"),
            sinal_smc_nome="REVERSAO",
            sinal_smc_confianca=confianca,
        )

        logger.info(
            "AlertaOportunidade criado: id=%s trade_id=%s nivel=%s acao='%s'",
            alerta.id,
            resultado.trade_id,
            nivel.value,
            resultado.acao_sugerida,
        )
        return alerta

    def _determinar_nivel(self, acao_sugerida: str) -> NivelAlerta:
        """
        Determina NivelAlerta com base em palavras-chave na acao_sugerida.

        Args:
            acao_sugerida: String descritiva da acao recomendada.

        Returns:
            NivelAlerta correspondente.
        """
        acao_lower = acao_sugerida.lower()

        for palavra in self._config.niveis_por_acao.get("critico", []):
            if palavra != "_default" and palavra in acao_lower:
                return NivelAlerta.CRÍTICO

        for palavra in self._config.niveis_por_acao.get("alto", []):
            if palavra != "_default" and palavra in acao_lower:
                return NivelAlerta.ALTO

        return NivelAlerta.MÉDIO

    # ----------------------------------------------------------
    # Entrega multicanal
    # ----------------------------------------------------------

    async def _entregar_multicanal(
        self,
        alerta: AlertaOportunidade,
        resultado: ProfitProtectionResult,
    ) -> None:
        """
        Orquestra entrega via delivery_manager e webhook.

        Args:
            alerta: AlertaOportunidade a entregar.
            resultado: Resultado original para montar payload do webhook.
        """
        tarefas = []

        if self._config.delivery_manager_ativo and self._delivery_manager is not None:
            tarefas.append(self._entregar_via_delivery_manager(alerta))

        if self._config.webhook_ativo and self._config.webhook_url:
            tarefas.append(self._disparar_webhook(resultado, alerta))

        if tarefas:
            await asyncio.gather(*tarefas, return_exceptions=True)

    async def _entregar_via_delivery_manager(
        self, alerta: AlertaOportunidade
    ) -> None:
        """Entrega via AlertaDeliveryManager (WebSocket + Email)."""
        if self._delivery_manager is None:
            return
        try:
            await self._delivery_manager.entregar_alerta(alerta)
            logger.info("DeliveryManager: alerta %s entregue", alerta.id)
        except Exception as exc:
            logger.error("DeliveryManager falhou para %s: %s", alerta.id, exc)

    async def _disparar_webhook(
        self,
        resultado: ProfitProtectionResult,
        alerta: AlertaOportunidade,
    ) -> None:
        """
        Dispara webhook Slack/Discord — fire-and-forget.

        Nao bloqueia o fluxo principal em caso de falha.

        Args:
            resultado: ProfitProtectionResult original.
            alerta: AlertaOportunidade criado.
        """
        payload = self._montar_payload_webhook(resultado, alerta)
        payload_json = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._enviar_webhook_bloqueante,
                payload_json,
            )
            logger.info("Webhook enviado para trade_id=%s", resultado.trade_id)
        except Exception as exc:
            logger.warning(
                "Webhook falhou (fire-and-forget) para trade_id=%s: %s",
                resultado.trade_id,
                exc,
            )

    def _enviar_webhook_bloqueante(self, payload_json: bytes) -> None:
        """Envia requisicao HTTP ao webhook (executada em thread pool)."""
        req = Request(
            self._config.webhook_url,
            data=payload_json,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=self._config.webhook_timeout_segundos) as resp:
            logger.debug("Webhook resposta: status=%d", resp.status)

    def _montar_payload_webhook(
        self,
        resultado: ProfitProtectionResult,
        alerta: AlertaOportunidade,
    ) -> Dict[str, Any]:
        """
        Monta payload JSON para o webhook Slack/Discord.

        Args:
            resultado: Resultado de protecao original.
            alerta: AlertaOportunidade criado.

        Returns:
            Dicionario pronto para serializacao JSON.
        """
        return {
            "schema_version": _SCHEMA_VERSION,
            "tipo": "ALERTA_REVERSAO",
            "alerta_id": str(alerta.id),
            "trade_id": resultado.trade_id,
            "nivel": alerta.nivel.value,
            "acao_sugerida": resultado.acao_sugerida,
            "profit_atual_pct": resultado.profit_atual,
            "profit_objetivo_pct": resultado.profit_objetivo,
            "lucro_maximo_sessao_pct": resultado.lucro_maximo_sessao,
            "deviance_reversao_pct": resultado.deviance_reversao,
            "timestamp": resultado.timestamp.isoformat(),
            "text": (
                f"🔴 [{alerta.nivel.value}] ALERTA de Reversão | "
                f"Trade: {resultado.trade_id} | "
                f"Ação: {resultado.acao_sugerida} | "
                f"Profit atual: {resultado.profit_atual:.2f}% | "
                f"Reversão desde máx: {resultado.deviance_reversao or 0:.2f}%"
            ),
        }
