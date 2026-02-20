"""
Integração Fila Alertas → WebSocket

Middleware que conecta a fila de alertas com o broadcast WebSocket.
"""

import asyncio
import logging
from typing import Optional

from infrastructure.providers.fila_alertas import FilaAlertas
from interfaces.websocket_server import broadcast_alert
from application.services.alerta_formatter import AlertaFormatter

logger = logging.getLogger(__name__)


class WebSocketFilaIntegrador:
    """
    Integra FilaAlertas com WebSocket broadcasting.

    Processa alertas da fila e envia via WebSocket para todos os clientes.
    """

    def __init__(self, fila: FilaAlertas):
        self.fila = fila
        self.formatter = AlertaFormatter()
        self.rodando = False

    async def processar_fila_com_websocket(self):
        """
        Worker loop que:
        1. Pega alerta da fila
        2. Formata para JSON
        3. Faz broadcast via WebSocket
        4. Registra sucesso/falha
        """
        self.rodando = True
        logger.info("🚀 WebSocket Fila Integrador iniciado")

        try:
            while self.rodando:
                try:
                    # Pega alerta da fila (non-blocking)
                    alerta_oportunidade = await asyncio.wait_for(
                        self.fila._queue.get(),
                        timeout=5.0
                    )

                    # Formata para JSON
                    alerta_json = self.formatter.formatar_json(alerta_oportunidade)

                    # Broadcast via WebSocket
                    await broadcast_alert(alerta_json)

                    logger.info(
                        f"✅ Alerta enviado via WebSocket: "
                        f"{alerta_oportunidade.ativo} "
                        f"- {alerta_oportunidade.padrao.value}"
                    )

                    # Marca como processado na fila
                    self.fila._queue.task_done()

                except asyncio.TimeoutError:
                    # Timeout ok - apenas aguarda
                    continue

                except Exception as e:
                    logger.error(f"❌ Erro ao processar alerta: {e}")
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("🛑 WebSocket Fila Integrador parado")
            self.rodando = False

    async def parar(self):
        """Para o worker loop."""
        self.rodando = False
        logger.info("Parando WebSocket Fila Integrador...")


# Singleton global (inicializar em app startup)
_integrador: Optional[WebSocketFilaIntegrador] = None


async def iniciar_websocket_integrador(fila: FilaAlertas) -> WebSocketFilaIntegrador:
    """
    Inicia integrador WebSocket (chamado em app startup).

    Args:
        fila: Instância de FilaAlertas para monitorar

    Returns:
        Instância do integrador
    """
    global _integrador

    _integrador = WebSocketFilaIntegrador(fila)

    # Inicia worker em background
    asyncio.create_task(_integrador.processar_fila_com_websocket())

    return _integrador


async def parar_websocket_integrador():
    """Para integrador (chamado em app shutdown)."""
    global _integrador

    if _integrador:
        await _integrador.parar()


def get_integrador() -> Optional[WebSocketFilaIntegrador]:
    """Retorna instância global do integrador."""
    return _integrador
