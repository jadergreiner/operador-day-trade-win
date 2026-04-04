"""
BDI Processor com Integration de Detectors (Phase 6)

Integra os detectors de volatilidade e padroes tecnicos
no fluxo de processamento de velas do BDI.
"""

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Tuple

from src.application.services.detector_volatilidade import DetectorVolatilidade
from src.application.services.detector_padroes_tecnico import DetectorPadroesTecnico
from src.application.services.detector_smc import DetectorSMC
from src.infrastructure.providers.fila_alertas import FilaAlertas
from src.infrastructure.config.alerta_config import get_config
from src.domain.entities.alerta import AlertaOportunidade
from config.settings import get_config as get_trading_config
from src.domain.entities import Order
from src.infrastructure.adapters.mt5_adapter_proxy import MT5AdapterProxy
from src.infrastructure.adapters.mt5_adapter import MT5Adapter

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
            lookback_bars=100,
        )
        self.detector_padroes = DetectorPadroesTecnico()
        self.detector_smc = DetectorSMC()
        self.fila = FilaAlertas()
        self._mt5_adapter: Optional[MT5Adapter] = None
        self._mt5_proxy: Optional[MT5AdapterProxy] = None
        # Cache de velas anteriores por ativo para SMC e padroes tecnicos
        self._vela_anterior: Dict[str, Dict] = {}
        self._candles_hist: Dict[str, list] = {}
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
            close = vela.get("close")
            if close is None:
                logger.warning(f"Vela sem close para {ativo}")
                return

            # Converter close para Decimal se necessário
            if isinstance(close, float):
                close = Decimal(str(close))
            elif not isinstance(close, Decimal):
                close = Decimal(str(float(close)))

            # Usar timestamp atual se não fornecido
            ts = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()

            logger.debug(f"Processando vela {ativo} - close: {close}")

            # ----------------------------------------------------------------
            # AC-1: Detector de volatilidade
            # ----------------------------------------------------------------
            alerta_vol = self.detector_vol.analisar_vela(
                symbol=ativo,
                close=close,
                timestamp=ts,
            )
            if alerta_vol:
                logger.info(f"[ALERTA VOL] {ativo} - Volatilidade detectada")
                await self.fila.enfileirar(alerta_vol)

            # ----------------------------------------------------------------
            # AC-1: Detector SMC (BOS / CHoCH / FVG) — integrado ao loop
            # ----------------------------------------------------------------
            vela_anterior = self._vela_anterior.get(ativo)
            if vela_anterior is not None:
                # Atualiza historico de candles (mantém os 20 ultimos)
                hist = self._candles_hist.setdefault(ativo, [])
                hist.append(vela)
                if len(hist) > 20:
                    hist.pop(0)

                alerta_smc = self.detector_smc.detectar_smc(
                    symbol=ativo,
                    vela_atual=vela,
                    vela_anterior=vela_anterior,
                    timestamp=ts,
                    candles_hist=hist,
                )
                if alerta_smc:
                    logger.info(
                        f"[ALERTA SMC] {ativo} - "
                        f"padrao={alerta_smc.sinal_smc_nome} "
                        f"confianca={float(alerta_smc.confianca):.0%}"
                    )
                    await self.fila.enfileirar(alerta_smc)

            # Armazena vela atual como anterior para proxima iteracao
            self._vela_anterior[ativo] = dict(vela)

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

    def _init_mt5_stack(self) -> None:
        """Inicializa stack MT5 (adapter direto + proxy REST)."""
        if self._mt5_proxy is not None:
            return

        trading_config = get_trading_config()
        self._mt5_adapter = MT5Adapter(
            login=trading_config.mt5_login,
            password=trading_config.mt5_password,
            server=trading_config.mt5_server,
            terminal_exe_path=trading_config.mt5_terminal_path,
        )
        self._mt5_proxy = MT5AdapterProxy(
            original_adapter=self._mt5_adapter,
            use_api_rest=False,
            fallback_to_mt5=False,
        )

    def enviar_ordem(self, order: Order) -> Tuple[bool, str]:
        """
        Envia ordem real para MT5 via proxy REST com fallback MT5 direto.

        Returns:
            (True, ticket) se sucesso
            (False, erro) se falha
        """
        try:
            self._init_mt5_stack()

            if self._mt5_adapter and not self._mt5_adapter.is_connected():
                self._mt5_adapter.connect()

            if not self._mt5_proxy:
                return False, "MT5 proxy not initialized"

            ticket = self._mt5_proxy.send_order(order)
            if not ticket:
                return False, "MT5 send_order returned empty ticket"

            return True, str(ticket)

        except Exception as e:
            logger.error(f"Erro ao enviar ordem via MT5: {e}", exc_info=True)
            return False, str(e)


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
