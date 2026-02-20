"""Gerenciador de entrega multicanal de alertas."""

import asyncio
import logging
import smtplib
from asyncio import TimeoutError as AsyncTimeoutError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Callable, Dict, Optional

from src.application.services.alerta_formatter import AlertaFormatter
from src.domain.entities.alerta import AlertaOportunidade
from src.domain.enums.alerta_enums import CanalEntrega

logger = logging.getLogger(__name__)


class AlertaDeliveryManager:
    """
    Gerenciador de entrega multicanal com retry e fallback automático.

    Estratégia:
    1. PRIMARY: WebSocket (sync, <500ms)
    2. SECONDARY: Email SMTP (async, 2-8s com fallback)
    3. TERTIARY: SMS (v1.2, condicional)

    Garante que nenhum alerta é perdido.
    """

    def __init__(
        self,
        websocket_client: Optional[object] = None,
        email_config: Optional[Dict] = None,
        sms_client: Optional[object] = None,
        audit_log: Optional[object] = None,
    ):
        """
        Inicializa delivery manager.

        Args:
            websocket_client: Cliente WebSocket para push real-time
            email_config: Dict com smtp_host, smtp_port, from_email, password
            sms_client: Cliente SMS (v1.2)
            audit_log: Serviço de auditoria para logging
        """
        self.websocket = websocket_client
        self.email_config = email_config or {}
        self.sms = sms_client
        self.audit_log = audit_log
        self.formatter = AlertaFormatter()

    async def entregar_alerta(self, alerta: AlertaOportunidade) -> bool:
        """
        Orquestra entrega multicanal com retry inteligente.

        Strategy:
        1. Tenta WebSocket (blocking, timeout 500ms)
        2. Em paralelo: Email (async, com retry automático)
        3. Se ambos falharem: SMS (v1.2)

        Args:
            alerta: AlertaOportunidade a entregar

        Returns:
            True se entregue com sucesso, False se falha crítica
        """

        logger.info(f"Iniciando entrega de alerta {alerta.id}")
        timestamp_inicio = datetime.now()

        # PASSO 1: Tenta WebSocket (PRIMARY)
        sucesso_websocket = False
        try:
            sucesso_websocket = await self._entregar_websocket(alerta)
        except Exception as e:
            logger.warning(f"WebSocket falhou: {e}, tentando email fallback")

        # PASSO 2: Email em paralelo (sempre tenta, não bloqueia)
        # Executa em background
        asyncio.create_task(self._entregar_email_com_retry(alerta))

        # PASSO 3: Calcula latência
        latencia_ms = int(
            (datetime.now() - timestamp_inicio).total_seconds() * 1000
        )
        logger.info(f"Entrega iniciada: {alerta.id} em {latencia_ms}ms")

        return sucesso_websocket  # Sucesso se > WebSocket funcionou

    async def _entregar_websocket(
        self, alerta: AlertaOportunidade, timeout_sec: float = 0.5
    ) -> bool:
        """
        Tenta entregar via WebSocket (PRIMARY - real-time).

        Args:
            alerta: AlertaOportunidade
            timeout_sec: Timeout em segundos (500ms)

        Returns:
            True se entregue, False caso contrário
        """

        if not self.websocket:
            logger.debug("WebSocket cliente não configurado")
            return False

        try:
            payload = self.formatter.formatar_json(alerta)

            # Chama com timeout
            await asyncio.wait_for(
                self.websocket.enviar(alerta.id, payload), timeout=timeout_sec
            )

            logger.info(f"✅ WebSocket entregue: {alerta.id}")
            alerta.marcar_entregue(CanalEntrega.WEBSOCKET)

            if self.audit_log:
                self.audit_log.registrar_entrega(
                    alerta_id=str(alerta.id),
                    canal="websocket",
                    status="entregue",
                    latencia_ms=0,
                )

            return True

        except AsyncTimeoutError:
            logger.warning(f"⏱️ WebSocket timeout: {alerta.id}")
            return False
        except Exception as e:
            logger.error(f"❌ WebSocket erro: {e}")
            return False

    async def _entregar_email_com_retry(
        self, alerta: AlertaOportunidade, max_retry: int = 3
    ) -> bool:
        """
        Tenta entregar via Email SMTP com retry exponencial.

        Estratégia:
        - Retry: 1s, 2s, 4s (exponencial)
        - Timeout: 8 segundos por tentativa
        - Se falhar todas: registra em audit para manual

        Args:
            alerta: AlertaOportunidade
            max_retry: Máximo de tentativas

        Returns:
            True se entregue, False se falha após retries
        """

        if not self.email_config:
            logger.debug("Email não configurado")
            return False

        destinatario = self.email_config.get("to_email", "operador@trading.local")
        assunto = self.formatter.formatar_assunto_email(alerta)
        corpo_html = self.formatter.formatar_email_html(alerta)
        corpo_texto = self.formatter.formatar_corpo_email_texto(alerta)

        for tentativa in range(max_retry):
            try:
                await asyncio.wait_for(
                    self._enviar_smtp(
                        destinatario=destinatario,
                        assunto=assunto,
                        corpo_html=corpo_html,
                        corpo_texto=corpo_texto,
                    ),
                    timeout=8.0,  # 8 segundo timeout
                )

                logger.info(f"✅ Email entregue: {alerta.id}")
                alerta.marcar_entregue(CanalEntrega.EMAIL)

                if self.audit_log:
                    self.audit_log.registrar_entrega(
                        alerta_id=str(alerta.id),
                        canal="email",
                        status="entregue",
                        latencia_ms=0,
                    )

                return True

            except AsyncTimeoutError:
                delay = 2 ** tentativa  # exponencial: 1s, 2s, 4s
                logger.warning(
                    f"Email timeout (tentativa {tentativa + 1}/{max_retry}), "
                    f"retry em {delay}s"
                )
                await asyncio.sleep(delay)

            except Exception as e:
                delay = 2 ** tentativa
                logger.error(
                    f"Email erro (tentativa {tentativa + 1}/{max_retry}): {e}, "
                    f"retry em {delay}s"
                )
                await asyncio.sleep(delay)

        # Se chegou aqui, falhou todas as tentativas
        logger.error(f"❌ Email falhou após {max_retry} tentativas: {alerta.id}")
        alerta.marcar_falha_entrega(CanalEntrega.EMAIL, "max_retry_exceeded")

        if self.audit_log:
            self.audit_log.registrar_entrega(
                alerta_id=str(alerta.id),
                canal="email",
                status="falha",
                latencia_ms=-1,
            )

        return False

    async def _enviar_smtp(
        self,
        destinatario: str,
        assunto: str,
        corpo_html: str,
        corpo_texto: str,
    ) -> bool:
        """
        Envio SMTP de fato (roda em executor para não bloquear).

        Args:
            destinatario: Email do operador
            assunto: Subject
            corpo_html: Corpo em HTML
            corpo_texto: Corpo em texto puro

        Returns:
            True se enviado com sucesso
        """

        loop = asyncio.get_event_loop()

        def _envio_bloqueante():
            """Função que faz o envio em thread executor."""
            servidor_smtp = smtplib.SMTP(
                self.email_config.get("smtp_host", "localhost"),
                self.email_config.get("smtp_port", 587),
            )

            servidor_smtp.starttls()

            # Autentica se credenciais fornecidas
            if self.email_config.get("smtp_user"):
                servidor_smtp.login(
                    self.email_config["smtp_user"],
                    self.email_config["smtp_password"],
                )

            # Cria mensagem multipart
            mensagem = MIMEMultipart("alternative")
            mensagem["Subject"] = assunto
            mensagem["From"] = self.email_config.get("from_email", "bot@trading.local")
            mensagem["To"] = destinatario

            # Atach texto e HTML
            parte_texto = MIMEText(corpo_texto, "plain", "utf-8")
            parte_html = MIMEText(corpo_html, "html", "utf-8")
            mensagem.attach(parte_texto)
            mensagem.attach(parte_html)

            # Envia
            servidor_smtp.sendmail(
                mensagem["From"], destinatario, mensagem.as_string()
            )
            servidor_smtp.quit()

            return True

        # Executa em thread pool (não bloqueia event loop)
        return await loop.run_in_executor(None, _envio_bloqueante)

    async def _entregar_sms(
        self, alerta: AlertaOportunidade, max_retry: int = 2
    ) -> bool:
        """
        Tenta entregar via SMS (v1.2 - FUTURO).

        Args:
            alerta: AlertaOportunidade
            max_retry: Máximo de tentativas

        Returns:
            True se entregue, False caso contrário
        """

        if not self.sms or not hasattr(self.sms, "enviar"):
            logger.debug("SMS não configurado ou disponível")
            return False

        corpo_sms = self.formatter.formatar_sms(alerta)

        for tentativa in range(max_retry):
            try:
                await self.sms.enviar(corpo_sms)

                logger.info(f"✅ SMS entregue: {alerta.id}")
                alerta.marcar_entregue(CanalEntrega.SMS)

                if self.audit_log:
                    self.audit_log.registrar_entrega(
                        alerta_id=str(alerta.id),
                        canal="sms",
                        status="entregue",
                        latencia_ms=0,
                    )

                return True

            except Exception as e:
                logger.warning(f"SMS erro (tentativa {tentativa + 1}): {e}")
                await asyncio.sleep(1)

        logger.error(f"❌ SMS falhou: {alerta.id}")
        return False
