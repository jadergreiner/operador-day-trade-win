"""
Handler de Alertas para Reversoes de Lucro (BLID-044)

Responsabilidades:
- Converter ProfitProtectionResult (status=ALERTA) em AlertaOportunidade
- Disparar alertas via AlertaDeliveryManager (WebSocket + Email)
- Enviar webhooks para Slack/Discord com detalhes da reversao
- Aplicar throttling para evitar spam de alertas

Integracao:
    ProfitProtectionEngine (processar_protecao)
    → AlertReversaoHandler (quando status=ALERTA)
    → AlertaDeliveryManager (entrega multicanal)

Referencias:
- BLID-044: P1-PROFIT_PROTECTION item #2
- ADR-037: Arquitetura de alertas de reversao
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

import httpx

from src.application.profit_protection_engine import (
    ProtectionStatus,
    ProfitProtectionResult,
)
from src.application.services.alerta_delivery import AlertaDeliveryManager
from src.domain.entities.alerta import AlertaOportunidade
from src.domain.enums.alerta_enums import NivelAlerta, PatraoAlerta, StatusAlerta
from src.domain.value_objects import Price, Symbol

logger = logging.getLogger(__name__)


@dataclass
class AlertReversaoConfig:
    """
    Configuracao de alertas de reversao de lucro.

    Atributos:
        habilitado: Se alertas estao ativos
        webhook_url: URL do webhook Slack/Discord (optional)
        webhook_timeout_sec: Timeout de envio de webhook
        webhook_retry_attempts: Quantidade de tentativas de envio do webhook
        webhook_retry_backoff_sec: Backoff incremental entre tentativas
        webhook_fire_and_forget: Se True, não bloqueia fluxo aguardando webhook
        throttle_seconds: Minimo entre alertas do mesmo trade
        persistir_throttle_state: Se deve persistir estado de throttling em disco
        throttle_state_path: Caminho do arquivo JSON de estado de throttling
        nivel_padrao: Nivel de severidade padrao (ALTO)
        incluir_snapshot_trade: Se incluir dados completos do trade
    """

    habilitado: bool = True
    webhook_url: Optional[str] = None
    webhook_timeout_sec: float = 5.0
    webhook_retry_attempts: int = 3
    webhook_retry_backoff_sec: float = 0.5
    webhook_fire_and_forget: bool = False
    throttle_seconds: int = 60
    persistir_throttle_state: bool = True
    throttle_state_path: str = "outputs/alert_reversao_throttle_state.json"
    nivel_padrao: NivelAlerta = NivelAlerta.ALTO
    incluir_snapshot_trade: bool = True


class AlertReversaoHandler:
    """
    Handler de alertas de reversao de lucro.

    Converte ProfitProtectionResult (status=ALERTA) em AlertaOportunidade
    e dispara entrega multicanal (WebSocket + Email + Webhook).

    Funcionalidades:
    1. Conversao ProfitProtectionResult → AlertaOportunidade
    2. Webhook para Slack/Discord com payload estruturado
    3. Throttling para evitar spam (60s entre alertas do mesmo trade)
    4. Integracao com AlertaDeliveryManager existente
    """

    def __init__(
        self,
        delivery_manager: AlertaDeliveryManager,
        config: Optional[AlertReversaoConfig] = None,
    ) -> None:
        """
        Inicializa handler de alertas de reversao.

        Args:
            delivery_manager: Gerenciador de entrega multicanal
            config: Configuracao de alertas (usa padrao se None)
        """
        self.delivery_manager = delivery_manager
        self.config = config or AlertReversaoConfig()
        self._historico_alertas: Dict[str, datetime] = {}  # throttling
        self._throttle_state_path = Path(self.config.throttle_state_path)

        self._carregar_estado_throttle()

        logger.info(
            "[AlertReversaoHandler] Inicializado | habilitado=%s | webhook=%s | throttle=%ds",
            self.config.habilitado,
            "SIM" if self.config.webhook_url else "NAO",
            self.config.throttle_seconds,
        )

    async def processar_reversao(
        self,
        resultado: ProfitProtectionResult,
        trade_data: Dict[str, Any],
    ) -> bool:
        """
        Processa resultado de protecao e dispara alerta se reversao detectada.

        Args:
            resultado: ProfitProtectionResult do ProfitProtectionEngine
            trade_data: Dados completos do trade (symbol, entry, direction, etc)

        Returns:
            True se alerta disparado com sucesso, False caso contrario

        Raises:
            ValueError: Se trade_data invalido (missing keys)
        """
        # ============================================================
        # ETAPA 1: Validacao e Gate de Throttling
        # ============================================================
        if not self.config.habilitado:
            logger.debug("Alertas de reversao desabilitados")
            return False

        if resultado.status != ProtectionStatus.ALERTA:
            logger.debug(
                "Status nao e ALERTA (status=%s), ignorando", resultado.status
            )
            return False

        # Throttling: verificar se ja disparamos alerta recente
        if self._deve_throttle(resultado.trade_id):
            logger.info(
                "Throttling ativo para trade_id=%s, ignorando alerta",
                resultado.trade_id,
            )
            return False

        # ============================================================
        # ETAPA 2: Validacao de Trade Data
        # ============================================================
        required_keys = ["symbol", "entry_price", "direction"]
        missing = [k for k in required_keys if k not in trade_data]
        if missing:
            raise ValueError(f"trade_data faltando keys obrigatorias: {missing}")

        symbol_str: str = trade_data["symbol"]
        entry_price: float = trade_data["entry_price"]
        direction: str = trade_data["direction"]

        # ============================================================
        # ETAPA 3: Construir AlertaOportunidade
        # ============================================================
        try:
            alerta = self._criar_alerta_oportunidade(
                resultado=resultado,
                symbol_str=symbol_str,
                entry_price=entry_price,
                direction=direction,
                trade_data=trade_data,
            )
        except Exception as e:
            logger.error("Erro ao criar AlertaOportunidade: %s", e, exc_info=True)
            return False

        # ============================================================
        # ETAPA 4: Disparar Entrega Multicanal
        # ============================================================
        sucesso_entrega = False
        try:
            # Entrega via AlertaDeliveryManager (WebSocket + Email)
            sucesso_entrega = await self.delivery_manager.entregar_alerta(alerta)

            # Webhook Slack/Discord com retries configuráveis
            if self.config.webhook_url:
                if self.config.webhook_fire_and_forget:
                    asyncio.create_task(
                        self._enviar_webhook_com_retry(resultado, trade_data, alerta.id)
                    )
                else:
                    await self._enviar_webhook_com_retry(resultado, trade_data, alerta.id)

            # Registrar throttling
            self._registrar_alerta(resultado.trade_id)

            logger.info(
                "✅ Alerta de reversao disparado: trade_id=%s alerta_id=%s entrega=%s",
                resultado.trade_id,
                alerta.id,
                "OK" if sucesso_entrega else "FALHOU",
            )

            return sucesso_entrega

        except Exception as e:
            logger.error(
                "Erro ao disparar alerta de reversao: %s", e, exc_info=True
            )
            return False

    def _criar_alerta_oportunidade(
        self,
        resultado: ProfitProtectionResult,
        symbol_str: str,
        entry_price: float,
        direction: str,
        trade_data: Dict[str, Any],
    ) -> AlertaOportunidade:
        """
        Converte ProfitProtectionResult em AlertaOportunidade.

        Args:
            resultado: Resultado de protecao
            symbol_str: Simbolo do ativo (ex: "WINFUT")
            entry_price: Preco de entrada do trade
            direction: Direcao ("BUY" ou "SELL")
            trade_data: Dados completos do trade

        Returns:
            AlertaOportunidade construida

        Raises:
            ValueError: Se dados invalidos
        """
        # Calcular preco atual baseado em profit_atual
        # profit_pct = (preco_atual - entry) / entry * 100  (para BUY)
        profit_pct = resultado.profit_atual
        if direction.upper() == "BUY":
            preco_atual_calculado = entry_price * (1 + profit_pct / 100)
        else:  # SELL
            preco_atual_calculado = entry_price * (1 - profit_pct / 100)

        # Stop loss e take profit (estimados se nao fornecidos)
        stop_loss_price = trade_data.get(
            "initial_sl", entry_price * 0.99
        )  # -1% default
        take_profit_price = trade_data.get(
            "initial_tp", entry_price * 1.02
        )  # +2% default

        # Calcular confianca baseado em deviance_reversao
        # Maior reversao = maior confianca no alerta
        deviance = resultado.deviance_reversao or 0.0
        confianca = min(1.0, abs(deviance) / 2.0)  # 2% reversao = 100% confianca

        # Risk/Reward estimado
        risk = abs(entry_price - stop_loss_price)
        reward = abs(take_profit_price - entry_price)
        risk_reward = reward / risk if risk > 0 else 1.0

        alerta = AlertaOportunidade(
            ativo=Symbol(symbol_str),
            padrao=PatraoAlerta.REVERSAO_LUCRO,
            nivel=self.config.nivel_padrao,
            preco_atual=Price(Decimal(str(preco_atual_calculado))),
            timestamp_deteccao=resultado.timestamp,
            entrada_minima=Price(Decimal(str(entry_price * 0.995))),  # -0.5%
            entrada_maxima=Price(Decimal(str(entry_price * 1.005))),  # +0.5%
            stop_loss=Price(Decimal(str(stop_loss_price))),
            take_profit=Price(Decimal(str(take_profit_price))),
            confianca=Decimal(str(confianca)),
            risk_reward=Decimal(str(risk_reward)),
            status=StatusAlerta.GERADO,
        )

        return alerta

    async def _enviar_webhook(
        self,
        resultado: ProfitProtectionResult,
        trade_data: Dict[str, Any],
        alerta_id: UUID,
    ) -> bool:
        """
        Envia webhook para Slack/Discord com detalhes da reversao.

        Formato Slack:
        {
            "text": "🚨 Reversão de Lucro Detectada",
            "blocks": [...]
        }

        Args:
            resultado: ProfitProtectionResult
            trade_data: Dados do trade
            alerta_id: UUID do alerta criado

        Returns:
            True se enviado com sucesso, False caso contrario
        """
        if not self.config.webhook_url:
            return False

        try:
            # Construir payload Slack/Discord
            payload = self._construir_payload_webhook(
                resultado, trade_data, alerta_id
            )

            # Enviar POST com timeout
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.webhook_url,
                    json=payload,
                    timeout=self.config.webhook_timeout_sec,
                )

                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(
                        "✅ Webhook enviado com sucesso: trade_id=%s",
                        resultado.trade_id,
                    )
                    return True
                else:
                    logger.warning(
                        "⚠️ Webhook retornou status %d: %s",
                        response.status_code,
                        response.text,
                    )
                    return False

        except httpx.TimeoutException:
            logger.warning(
                "⏱️ Webhook timeout apos %.1fs", self.config.webhook_timeout_sec
            )
            return False
        except Exception as e:
            logger.error("❌ Erro ao enviar webhook: %s", e, exc_info=True)
            return False

    async def _enviar_webhook_com_retry(
        self,
        resultado: ProfitProtectionResult,
        trade_data: Dict[str, Any],
        alerta_id: UUID,
    ) -> bool:
        """Envia webhook com retries e backoff para aumentar confiabilidade."""
        tentativas = max(1, int(self.config.webhook_retry_attempts))
        backoff_base = max(0.0, float(self.config.webhook_retry_backoff_sec))

        for tentativa in range(1, tentativas + 1):
            sucesso = await self._enviar_webhook(resultado, trade_data, alerta_id)
            if sucesso:
                return True
            if tentativa < tentativas and backoff_base > 0:
                await asyncio.sleep(backoff_base * tentativa)

        logger.warning(
            "Webhook nao entregue apos %d tentativas: trade_id=%s",
            tentativas,
            resultado.trade_id,
        )
        return False

    def _construir_payload_webhook(
        self,
        resultado: ProfitProtectionResult,
        trade_data: Dict[str, Any],
        alerta_id: UUID,
    ) -> Dict[str, Any]:
        """
        Constroi payload formatado para Slack/Discord.

        Args:
            resultado: ProfitProtectionResult
            trade_data: Dados do trade
            alerta_id: UUID do alerta

        Returns:
            Dict com payload formatado para webhook
        """
        symbol = trade_data.get("symbol", "UNKNOWN")
        direction = trade_data.get("direction", "UNKNOWN")
        entry_price = trade_data.get("entry_price", 0.0)

        # Emoji baseado em severidade da reversao
        deviance = resultado.deviance_reversao or 0.0
        emoji = "🔴" if abs(deviance) >= 1.0 else "🟠"

        # Texto principal
        texto = (
            f"{emoji} **Reversão de Lucro Detectada**\n\n"
            f"**Trade:** {resultado.trade_id}\n"
            f"**Símbolo:** {symbol} {direction}\n"
            f"**Preço Entrada:** {entry_price:.2f}\n"
            f"**Lucro Atual:** {resultado.profit_atual:.2f}%\n"
            f"**Lucro Máximo:** {resultado.lucro_maximo_sessao:.2f}%\n"
            f"**Reversão:** {deviance:.2f}%\n\n"
            f"**Ação Sugerida:** {resultado.acao_sugerida}\n"
            f"**Alerta ID:** {alerta_id}"
        )

        # Payload Slack (compativel com Discord)
        payload = {
            "text": f"{emoji} Reversão de Lucro Detectada",
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": texto},
                }
            ],
        }

        return payload

    def _deve_throttle(self, trade_id: str) -> bool:
        """
        Verifica se deve fazer throttling do alerta.

        Args:
            trade_id: ID do trade

        Returns:
            True se deve throttle (alerta recente), False caso contrario
        """
        agora = datetime.now()
        ultimo_alerta = self._historico_alertas.get(trade_id)

        if ultimo_alerta is None:
            return False

        delta = (agora - ultimo_alerta).total_seconds()
        return delta < self.config.throttle_seconds

    def _registrar_alerta(self, trade_id: str) -> None:
        """
        Registra timestamp de alerta para throttling.

        Args:
            trade_id: ID do trade
        """
        self._historico_alertas[trade_id] = datetime.now()

        # Limpeza de historico antigo (keep last 24h only)
        limite = datetime.now() - timedelta(hours=24)
        self._historico_alertas = {
            k: v for k, v in self._historico_alertas.items() if v >= limite
        }

        self._persistir_estado_throttle()

    def _carregar_estado_throttle(self) -> None:
        """Carrega estado de throttling persistido (se habilitado)."""
        if not self.config.persistir_throttle_state:
            return

        try:
            if not self._throttle_state_path.exists():
                return

            conteudo = self._throttle_state_path.read_text(encoding="utf-8")
            payload = json.loads(conteudo)
            if not isinstance(payload, dict):
                return

            historico = payload.get("historico_alertas", {})
            if not isinstance(historico, dict):
                return

            recuperado: Dict[str, datetime] = {}
            for trade_id, timestamp_iso in historico.items():
                if not isinstance(trade_id, str) or not isinstance(timestamp_iso, str):
                    continue
                try:
                    recuperado[trade_id] = datetime.fromisoformat(timestamp_iso)
                except ValueError:
                    continue

            # Aplicar mesma regra de limpeza (>24h)
            limite = datetime.now() - timedelta(hours=24)
            self._historico_alertas = {
                k: v for k, v in recuperado.items() if v >= limite
            }
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao carregar estado de throttling: %s", e)

    def _persistir_estado_throttle(self) -> None:
        """Persiste estado de throttling de forma atômica (se habilitado)."""
        if not self.config.persistir_throttle_state:
            return

        try:
            self._throttle_state_path.parent.mkdir(parents=True, exist_ok=True)
            path_tmp = self._throttle_state_path.with_suffix(".tmp")
            payload = {
                "schema_version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "historico_alertas": {
                    trade_id: ts.isoformat()
                    for trade_id, ts in self._historico_alertas.items()
                },
            }
            path_tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            path_tmp.replace(self._throttle_state_path)
        except Exception as e:  # noqa: BLE001
            logger.warning("Falha ao persistir estado de throttling: %s", e)
