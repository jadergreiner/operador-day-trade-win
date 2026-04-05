"""
BDI Processor com Integration de Detectors (Phase 6)

Integra os detectors de volatilidade e padroes tecnicos
no fluxo de processamento de velas do BDI.

ENG-202 (BLID-037): Integrar detector de padroes na pipeline BDI
- AC-1: Hook detector_padroes (engulfing, break s/r) no processar_vela()
- AC-2: Filtro de confianca > 0.75 via FiltroConfiancaBDI
- AC-3: Apenas alertas de alta confianca sao enfileirados para WebSocket
- AC-4: Performance medida por vela; alerta emitido se > 100ms
- AC-6: Audit log via FiltroConfiancaBDI.historico_audit
- AC-7: Metricas exportaveis via exportar_metricas()
"""

import asyncio
import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Tuple

from src.application.services.detector_volatilidade import DetectorVolatilidade
from src.application.services.detector_padroes_tecnico import DetectorPadroesTecnico
from src.application.services.detector_smc import DetectorSMC
from src.infrastructure.providers.fila_alertas import FilaAlertas
from src.infrastructure.config.alerta_config import get_config
from src.domain.entities.alerta import AlertaOportunidade
from src.domain.bdi_processor_v2 import FiltroConfiancaBDI, LIMIAR_CONFIANCA_PADRAO
from config.settings import get_config as get_trading_config
from src.domain.entities import Order
from src.infrastructure.adapters.mt5_adapter_proxy import MT5AdapterProxy
from src.infrastructure.adapters.mt5_adapter import MT5Adapter

logger = logging.getLogger(__name__)


class ProcessadorBDI:
    """
    BDI Processor com detectors hookados e filtro de confianca (ENG-202).

    Processa velas do BDI, dispara detectors e filtra alertas por
    confianca antes de enfileirar para o WebSocket.

    Fluxo por vela:
        processar_vela()
            -> detector_vol.analisar_vela()          [volatilidade]
            -> detector_smc.detectar_smc()            [BOS/CHoCH/FVG]
            -> detector_padroes.detectar_engulfing()  [AC-1: hookado aqui]
            -> detector_padroes.detectar_break_*()    [AC-1: hookado aqui]
        Cada alerta gerado passa por FiltroConfiancaBDI.avaliar():
            -> APROVADO (confianca > 0.75): fila.enfileirar() -> WebSocket
            -> REJEITADO: apenas audit log, sem enfileiramento
    """

    def __init__(self) -> None:
        """Inicializar processador com detectors, fila e filtro de confianca."""
        self.config = get_config()

        # Limiar de confianca lido da config (AC-2)
        limiar = Decimal(
            str(self.config.detection.padroes.limiar_confianca)
        )
        self.filtro_confianca = FiltroConfiancaBDI(limiar=limiar)

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
        logger.info(
            "ProcessadorBDI inicializado | limiar_confianca=%.2f",
            float(limiar),
        )

    async def processar_vela(
        self, ativo: str, vela: Dict, timestamp: Optional[float] = None
    ) -> None:
        """
        Processa vela e dispara detectors com filtro de confianca.

        AC-1: Todos os detectors (vol, smc, padroes) hookados.
        AC-2/AC-3: Apenas alertas com confianca > limiar sao enfileirados.
        AC-4: Performance medida — log WARNING se > 100ms por vela.
        AC-6: Audit log registrado pelo FiltroConfiancaBDI para cada alerta.

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

            # Inicio de medicao de performance por vela (AC-4)
            inicio_vela = time.perf_counter()

            # ----------------------------------------------------------------
            # Detector de volatilidade
            # ----------------------------------------------------------------
            alerta_vol = self.detector_vol.analisar_vela(
                symbol=ativo,
                close=close,
                timestamp=ts,
            )
            if alerta_vol:
                if self.filtro_confianca.avaliar(alerta_vol):
                    logger.info(
                        "[ALERTA VOL] %s — confianca=%.0f%% APROVADO → fila",
                        ativo,
                        float(alerta_vol.confianca) * 100,
                    )
                    await self.fila.enfileirar(alerta_vol)
                else:
                    logger.debug(
                        "[ALERTA VOL] %s — confianca=%.0f%% REJEITADO pelo filtro",
                        ativo,
                        float(alerta_vol.confianca) * 100,
                    )

            # ----------------------------------------------------------------
            # AC-1: Detectors com vela anterior
            # ----------------------------------------------------------------
            vela_anterior = self._vela_anterior.get(ativo)
            if vela_anterior is not None:
                # Atualiza historico de candles (mantém os 20 ultimos)
                hist = self._candles_hist.setdefault(ativo, [])
                hist.append(vela)
                if len(hist) > 20:
                    hist.pop(0)

                # --- Detector SMC (BOS / CHoCH / FVG) ---
                alerta_smc = self.detector_smc.detectar_smc(
                    symbol=ativo,
                    vela_atual=vela,
                    vela_anterior=vela_anterior,
                    timestamp=ts,
                    candles_hist=hist,
                )
                if alerta_smc:
                    if self.filtro_confianca.avaliar(alerta_smc):
                        logger.info(
                            "[ALERTA SMC] %s — padrao=%s confianca=%.0f%% APROVADO → fila",
                            ativo,
                            alerta_smc.sinal_smc_nome,
                            float(alerta_smc.confianca) * 100,
                        )
                        await self.fila.enfileirar(alerta_smc)
                    else:
                        logger.debug(
                            "[ALERTA SMC] %s — padrao=%s confianca=%.0f%% REJEITADO",
                            ativo,
                            alerta_smc.sinal_smc_nome,
                            float(alerta_smc.confianca) * 100,
                        )

                # --- AC-1: Detector de padroes tecnicos (engulfing) ---
                if self.config.detection.padroes.engulfing_enabled:
                    alerta_eng = self.detector_padroes.detectar_engulfing(
                        symbol=ativo,
                        vela_atual=vela,
                        vela_anterior=vela_anterior,
                        timestamp=ts,
                    )
                    if alerta_eng:
                        if self.filtro_confianca.avaliar(alerta_eng):
                            logger.info(
                                "[ALERTA PADRAO] %s — %s confianca=%.0f%% APROVADO → fila",
                                ativo,
                                alerta_eng.padrao.value,
                                float(alerta_eng.confianca) * 100,
                            )
                            await self.fila.enfileirar(alerta_eng)
                        else:
                            logger.debug(
                                "[ALERTA PADRAO] %s — %s confianca=%.0f%% REJEITADO",
                                ativo,
                                alerta_eng.padrao.value,
                                float(alerta_eng.confianca) * 100,
                            )

                # --- AC-1: Detector de padroes tecnicos (break suporte/resistencia) ---
                precos_hist = [float(c.get("close", 0)) for c in hist]
                if precos_hist:
                    if self.config.detection.padroes.break_suporte_enabled:
                        alerta_bs = self.detector_padroes.detectar_break_suporte(
                            symbol=ativo,
                            precos=precos_hist,
                            timestamp=ts,
                        )
                        if alerta_bs:
                            if self.filtro_confianca.avaliar(alerta_bs):
                                logger.info(
                                    "[ALERTA PADRAO] %s — break_suporte confianca=%.0f%% APROVADO → fila",
                                    ativo,
                                    float(alerta_bs.confianca) * 100,
                                )
                                await self.fila.enfileirar(alerta_bs)
                            else:
                                logger.debug(
                                    "[ALERTA PADRAO] %s — break_suporte confianca=%.0f%% REJEITADO",
                                    ativo,
                                    float(alerta_bs.confianca) * 100,
                                )

                    if self.config.detection.padroes.break_resistencia_enabled:
                        alerta_br = self.detector_padroes.detectar_break_resistencia(
                            symbol=ativo,
                            precos=precos_hist,
                            timestamp=ts,
                        )
                        if alerta_br:
                            if self.filtro_confianca.avaliar(alerta_br):
                                logger.info(
                                    "[ALERTA PADRAO] %s — break_resistencia confianca=%.0f%% APROVADO → fila",
                                    ativo,
                                    float(alerta_br.confianca) * 100,
                                )
                                await self.fila.enfileirar(alerta_br)
                            else:
                                logger.debug(
                                    "[ALERTA PADRAO] %s — break_resistencia confianca=%.0f%% REJEITADO",
                                    ativo,
                                    float(alerta_br.confianca) * 100,
                                )

            # Armazena vela atual como anterior para proxima iteracao
            self._vela_anterior[ativo] = dict(vela)

            # AC-4: Validacao de performance por vela
            elapsed_ms = (time.perf_counter() - inicio_vela) * 1000
            if elapsed_ms > 100:
                logger.warning(
                    "[PERFORMANCE] %s — processamento %.1fms excedeu meta de 100ms",
                    ativo,
                    elapsed_ms,
                )
            else:
                logger.debug(
                    "[PERFORMANCE] %s — %.1fms dentro da meta de 100ms",
                    ativo,
                    elapsed_ms,
                )

        except Exception as e:
            logger.error(f"Erro ao processar vela {ativo}: {e}", exc_info=True)

    def exportar_metricas(self) -> dict:
        """
        AC-7: Exporta metricas da pipeline BDI.

        Returns:
            Dict com precision, recall, f1_score e contadores de filtro.
        """
        return self.filtro_confianca.exportar_metricas()

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
