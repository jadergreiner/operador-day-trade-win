"""
Integração Fila Alertas → WebSocket

Middleware que conecta a fila de alertas com o broadcast WebSocket.

ENG-202 (BLID-037): Defesa extra de confianca antes do broadcast.
- AC-3: Apenas alertas de confianca alta chegam aqui (filtro primario em
  ProcessadorBDI), mas o integrador aplica uma segunda verificacao como
  defesa em profundidade para garantir que nenhum alerta de baixa confianca
  seja transmitido via WebSocket.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Optional

from infrastructure.providers.fila_alertas import FilaAlertas
from interfaces.websocket_server import broadcast_alert
from application.services.alerta_formatter import AlertaFormatter

logger = logging.getLogger(__name__)

# Limiar de confianca minimo para broadcast via WebSocket (AC-3 / ENG-202)
# Sincronizado com LIMIAR_CONFIANCA_PADRAO do bdi_processor_v2.py
_LIMIAR_WEBSOCKET: Decimal = Decimal("0.75")


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
        2. Verifica confianca >= limiar (AC-3: defesa em profundidade)
        3. Formata para JSON
        4. Faz broadcast via WebSocket
        5. Registra sucesso/falha
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

                    # AC-3: Defesa em profundidade — rejeita alertas de baixa
                    # confianca que eventualmente cheguem na fila.
                    # Distingue: atributo ausente (dado invalido) vs. confianca
                    # genuinamente baixa (decisao de filtro).
                    confianca_raw = getattr(alerta_oportunidade, "confianca", None)
                    if confianca_raw is None:
                        logger.error(
                            "❌ Alerta sem atributo 'confianca' interceptado no "
                            "WebSocket | %s — descartado (dado invalido)",
                            getattr(alerta_oportunidade, "ativo", "?"),
                        )
                        self.fila._queue.task_done()
                        continue
                    confianca = Decimal(str(confianca_raw))
                    if confianca <= _LIMIAR_WEBSOCKET:
                        logger.warning(
                            "⚠️ Alerta de baixa confianca interceptado no WebSocket "
                            "| %s | confianca=%.3f <= limiar=%.2f — descartado",
                            getattr(alerta_oportunidade, "ativo", "?"),
                            float(confianca),
                            float(_LIMIAR_WEBSOCKET),
                        )
                        self.fila._queue.task_done()
                        continue

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
