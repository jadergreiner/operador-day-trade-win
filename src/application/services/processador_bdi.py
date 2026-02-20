"""
BDI Processor com Integration de Detectors (Phase 6)

Integra os detectors de volatilidade e padroes tecnicos
no fluxo de processamento de velas do BDI.
"""

import asyncio
import logging
from typing import Dict, Optional

from src.application.services.detector_volatilidade import DetectorVolatilidade
from src.application.services.detector_padroes_tecnico import DetectorPadroesTecnico
from src.infrastructure.providers.fila_alertas import FilaAlertas
from src.infrastructure.config.alerta_config import get_config
from src.domain.entities.alerta import AlertaOportunidade

logger = logging.getLogger(__name__)


class ProcessadorBDI:
    """
    BDI Processor com detectors hookados.

    Processa velas do BDI e dispara detectors de alertas em tempo real.
    Integra com fila de alertas para entrega multi-canal.
    """

    def __init__(self):
        """Inicializar processador com detectors e fila."""
        self.config = get_config()
        self.detector_vol = DetectorVolatilidade(
            window=self.config.detection.volatilidade.window,
            threshold_sigma=self.config.detection.volatilidade.threshold_sigma,
            confirmacao_velas=self.config.detection.volatilidade.confirmacao_velas,
        )
        self.detector_padroes = DetectorPadroesTecnico()
        self.fila = FilaAlertas()
        logger.info("ProcessadorBDI inicializado")

    async def processar_vela(
        self, ativo: str, vela: Dict, timestamp: Optional[float] = None
    ) -> None:
        """
        Processa vela e dispara detectors.

        Args:
            ativo: Simbolo do ativo (ex: 'WIN$N')
            vela: Dict com OHLCV {open, high, low, close, volume}
            timestamp: Timestamp da vela (opcional)
        """
        try:
            logger.debug(f"Processando vela {ativo} - close: {vela.get('close')}")

            # Detector de volatilidade
            alerta_vol = self.detector_vol.analisar_vela(ativo, vela)
            if alerta_vol:
                logger.info(f"[ALERTA VOL] {ativo} - Volatilidade detectada")
                await self.fila.adicionar_alerta(alerta_vol)

            # Detector de padroes tecnicos
            alerta_padroes = self.detector_padroes.detectar_padroes(
                close=float(vela.get("close", 0)),
                high=float(vela.get("high", 0)),
                low=float(vela.get("low", 0)),
                volume=float(vela.get("volume", 0)),
            )
            if alerta_padroes:
                logger.info(f"[ALERTA PADRAO] {ativo} - Padrao detectado")
                await self.fila.adicionar_alerta(alerta_padroes)

        except Exception as e:
            logger.error(f"Erro ao processar vela {ativo}: {e}", exc_info=True)

    async def iniciar(self) -> None:
        """Iniciar processador em loop."""
        logger.info("ProcessadorBDI iniciado")
        try:
            # Loop de processamento continuo
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("ProcessadorBDI interrompido pelo usuario")

    async def parar(self) -> None:
        """Parar processador."""
        logger.info("Parando ProcessadorBDI")


# Instancia global para uso facil
_processador_bdi: Optional[ProcessadorBDI] = None


def get_processador_bdi() -> ProcessadorBDI:
    """Obter instancia singleton do processador."""
    global _processador_bdi
    if _processador_bdi is None:
        _processador_bdi = ProcessadorBDI()
    return _processador_bdi


async def processar_vela_bdi(
    ativo: str, vela: Dict, timestamp: Optional[float] = None
) -> None:
    """Funcao auxiliar para processar vela via processador global."""
    processador = get_processador_bdi()
    await processador.processar_vela(ativo, vela, timestamp)


if __name__ == "__main__":
    # Para testes/debug apenas
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("ProcessadorBDI module loaded successfully")
