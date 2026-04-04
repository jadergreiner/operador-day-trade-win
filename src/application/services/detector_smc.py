"""
S2-4: Detector de Padroes SMC (Smart Money Concepts)

Detecta padroes estruturais de mercado:
- BOS  (Break of Structure): rompimento de estrutura com continuidade
- CHoCH (Change of Character): reversao de estrutura (mudanca de tendencia)
- FVG  (Fair Value Gap): gap de fair value (desequilibrio oferta/demanda)

Pipeline:
    ProcessadorBDI chama detectar_smc(vela_atual, vela_anterior, candles_hist)
    -> DetectorSMC avalia padroes e retorna AlertaOportunidade enriquecido
    -> Alert trafega para FilaAlertas -> WebSocket -> Trader

Status: Implementacao v1.0 (04/04/2026)
Referencia: docs/BACKLOG.md BLID-031, ADR-025
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from src.domain.entities.alerta import AlertaOportunidade
from src.domain.enums.alerta_enums import NivelAlerta, PatraoAlerta
from src.domain.value_objects import Price, Symbol

logger = logging.getLogger(__name__)

# Limiar de confianca minima para emitir alerta SMC
CONFIANCA_MINIMA_SMC: Decimal = Decimal("0.55")

# Pesos de confluencia por padrao
_PESO_PADRAO: dict = {
    PatraoAlerta.SMC_BOS: 3,
    PatraoAlerta.SMC_CHOCH: 4,
    PatraoAlerta.SMC_FVG: 2,
}


class DetectorSMC:
    """
    Detector de padroes SMC integrado ao pipeline de alertas.

    Responsabilidades:
    - Detectar BOS, CHoCH e FVG em candles M5
    - Enriquecer AlertaOportunidade com metadados SMC
    - Calcular confluencia_strength (1-5) para o trader

    Retrocompativel: nenhuma alteracao em AlertaOportunidade existente;
    campos SMC sao opcionais com default None/True.
    """

    def __init__(
        self,
        confianca_minima: Decimal = CONFIANCA_MINIMA_SMC,
    ) -> None:
        """
        Inicializa detector SMC.

        Args:
            confianca_minima: Limite abaixo do qual o alerta nao e emitido.
        """
        self.confianca_minima = confianca_minima
        self._historico_estrutura: dict = {}  # {symbol: "ALTA" | "BAIXA" | None}

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------

    def detectar_smc(
        self,
        symbol: str,
        vela_atual: dict,
        vela_anterior: dict,
        timestamp: datetime,
        candles_hist: Optional[List[dict]] = None,
    ) -> Optional[AlertaOportunidade]:
        """
        Ponto de entrada principal — avalia BOS, CHoCH e FVG.

        Prioridade de deteccao:
        1. CHoCH (quando estrutura ja existe) — sinal de reversao de tendencia
        2. BOS  (quando estrutura nao existe ou e continuacao)
        3. FVG  (usando historico de 3+ candles)

        Args:
            symbol: Codigo do ativo (ex: "WIN$N")
            vela_atual: {open, high, low, close, volume}
            vela_anterior: {open, high, low, close, volume}
            timestamp: Timestamp da vela
            candles_hist: Historico de velas para FVG (ao menos 3)

        Returns:
            AlertaOportunidade enriquecido com campos SMC, ou None.
        """
        # CHoCH tem prioridade quando estrutura ja foi estabelecida
        if self._historico_estrutura.get(symbol) is not None:
            choch = self._detectar_choch(symbol, vela_atual, vela_anterior, timestamp)
            if choch:
                return choch

        bos = self._detectar_bos(symbol, vela_atual, vela_anterior, timestamp)
        if bos:
            return bos

        if candles_hist and len(candles_hist) >= 3:
            fvg = self._detectar_fvg(symbol, candles_hist, timestamp)
            if fvg:
                return fvg

        return None

    # ------------------------------------------------------------------
    # Deteccao de BOS
    # ------------------------------------------------------------------

    def _detectar_bos(
        self,
        symbol: str,
        vela_atual: dict,
        vela_anterior: dict,
        timestamp: datetime,
    ) -> Optional[AlertaOportunidade]:
        """
        BOS — Break of Structure.

        Regra:
        - Bullish BOS: close atual > high anterior  (rompimento de topo)
        - Bearish BOS: close atual < low anterior   (rompimento de fundo)

        Confianca base: 0.70 (rompimento validado por fechamento)
        """
        close_atual = float(vela_atual.get("close", 0))
        high_anterior = float(vela_anterior.get("high", 0))
        low_anterior = float(vela_anterior.get("low", 0))

        if close_atual <= 0 or high_anterior <= 0 or low_anterior <= 0:
            return None

        if close_atual > high_anterior:
            logger.info(f"{symbol}: BOS Bullish detectado close={close_atual:.0f} > high_ant={high_anterior:.0f}")
            self._historico_estrutura[symbol] = "ALTA"
            return self._criar_alerta_smc(
                symbol=symbol,
                padrao=PatraoAlerta.SMC_BOS,
                nivel=NivelAlerta.ALTO,
                confianca=Decimal("0.70"),
                preco_atual=Decimal(str(close_atual)),
                entrada_min=Decimal(str(high_anterior)),
                entrada_max=Decimal(str(close_atual)),
                sinal_nome="BOS",
                timestamp=timestamp,
            )

        if close_atual < low_anterior:
            logger.info(f"{symbol}: BOS Bearish detectado close={close_atual:.0f} < low_ant={low_anterior:.0f}")
            self._historico_estrutura[symbol] = "BAIXA"
            return self._criar_alerta_smc(
                symbol=symbol,
                padrao=PatraoAlerta.SMC_BOS,
                nivel=NivelAlerta.ALTO,
                confianca=Decimal("0.70"),
                preco_atual=Decimal(str(close_atual)),
                entrada_min=Decimal(str(close_atual)),
                entrada_max=Decimal(str(low_anterior)),
                sinal_nome="BOS",
                timestamp=timestamp,
            )

        return None

    # ------------------------------------------------------------------
    # Deteccao de CHoCH
    # ------------------------------------------------------------------

    def _detectar_choch(
        self,
        symbol: str,
        vela_atual: dict,
        vela_anterior: dict,
        timestamp: datetime,
    ) -> Optional[AlertaOportunidade]:
        """
        CHoCH — Change of Character.

        Regra (requer historico de estrutura):
        - Estrutura anterior era ALTA e close atual < low anterior  -> reversao BAIXA
        - Estrutura anterior era BAIXA e close atual > high anterior -> reversao ALTA

        Confianca base: 0.80 (sinalizacao de mudanca de tendencia)
        """
        estrutura_anterior = self._historico_estrutura.get(symbol)
        if estrutura_anterior is None:
            return None

        close_atual = float(vela_atual.get("close", 0))
        high_anterior = float(vela_anterior.get("high", 0))
        low_anterior = float(vela_anterior.get("low", 0))

        if close_atual <= 0 or high_anterior <= 0 or low_anterior <= 0:
            return None

        if estrutura_anterior == "ALTA" and close_atual < low_anterior:
            logger.info(f"{symbol}: CHoCH — reversao para BAIXA detectada")
            self._historico_estrutura[symbol] = "BAIXA"
            return self._criar_alerta_smc(
                symbol=symbol,
                padrao=PatraoAlerta.SMC_CHOCH,
                nivel=NivelAlerta.CRÍTICO,
                confianca=Decimal("0.80"),
                preco_atual=Decimal(str(close_atual)),
                entrada_min=Decimal(str(close_atual)),
                entrada_max=Decimal(str(low_anterior)),
                sinal_nome="CHoCH",
                timestamp=timestamp,
            )

        if estrutura_anterior == "BAIXA" and close_atual > high_anterior:
            logger.info(f"{symbol}: CHoCH — reversao para ALTA detectada")
            self._historico_estrutura[symbol] = "ALTA"
            return self._criar_alerta_smc(
                symbol=symbol,
                padrao=PatraoAlerta.SMC_CHOCH,
                nivel=NivelAlerta.CRÍTICO,
                confianca=Decimal("0.80"),
                preco_atual=Decimal(str(close_atual)),
                entrada_min=Decimal(str(high_anterior)),
                entrada_max=Decimal(str(close_atual)),
                sinal_nome="CHoCH",
                timestamp=timestamp,
            )

        return None

    # ------------------------------------------------------------------
    # Deteccao de FVG
    # ------------------------------------------------------------------

    def _detectar_fvg(
        self,
        symbol: str,
        candles: List[dict],
        timestamp: datetime,
    ) -> Optional[AlertaOportunidade]:
        """
        FVG — Fair Value Gap.

        Regra (3 velas consecutivas):
        - Bullish FVG: low[2] > high[0]  (gap entre vela 1 e vela 3)
        - Bearish FVG: high[2] < low[0]  (gap invertido)

        Confianca base: 0.65 (zona de rebalanceamento)
        """
        if len(candles) < 3:
            return None

        c0 = candles[-3]
        c2 = candles[-1]

        high_c0 = float(c0.get("high", 0))
        low_c0 = float(c0.get("low", 0))
        high_c2 = float(c2.get("high", 0))
        low_c2 = float(c2.get("low", 0))
        close_c2 = float(c2.get("close", 0))

        if any(v <= 0 for v in [high_c0, low_c0, high_c2, low_c2, close_c2]):
            return None

        # Bullish FVG: espaco livre entre high[0] e low[2]
        if low_c2 > high_c0:
            gap_mid = Decimal(str((low_c2 + high_c0) / 2))
            logger.info(f"{symbol}: FVG Bullish detectado gap={low_c2 - high_c0:.0f} pts")
            return self._criar_alerta_smc(
                symbol=symbol,
                padrao=PatraoAlerta.SMC_FVG,
                nivel=NivelAlerta.MÉDIO,
                confianca=Decimal("0.65"),
                preco_atual=gap_mid,
                entrada_min=Decimal(str(high_c0)),
                entrada_max=Decimal(str(low_c2)),
                sinal_nome="FVG",
                timestamp=timestamp,
            )

        # Bearish FVG: espaco livre entre low[0] e high[2]
        if high_c2 < low_c0:
            gap_mid = Decimal(str((high_c2 + low_c0) / 2))
            logger.info(f"{symbol}: FVG Bearish detectado gap={low_c0 - high_c2:.0f} pts")
            return self._criar_alerta_smc(
                symbol=symbol,
                padrao=PatraoAlerta.SMC_FVG,
                nivel=NivelAlerta.MÉDIO,
                confianca=Decimal("0.65"),
                preco_atual=gap_mid,
                entrada_min=Decimal(str(high_c2)),
                entrada_max=Decimal(str(low_c0)),
                sinal_nome="FVG",
                timestamp=timestamp,
            )

        return None

    # ------------------------------------------------------------------
    # Fabrica interna
    # ------------------------------------------------------------------

    def _criar_alerta_smc(
        self,
        symbol: str,
        padrao: PatraoAlerta,
        nivel: NivelAlerta,
        confianca: Decimal,
        preco_atual: Decimal,
        entrada_min: Decimal,
        entrada_max: Decimal,
        sinal_nome: str,
        timestamp: datetime,
    ) -> Optional[AlertaOportunidade]:
        """
        Fabrica de AlertaOportunidade para padroes SMC.

        Calcula SL/TP proporcional ao gap do padrao e popula
        os campos SMC da entidade.

        Returns:
            AlertaOportunidade ou None se confianca abaixo do limiar.
        """
        if confianca < self.confianca_minima:
            logger.debug(f"{symbol}: {sinal_nome} descartado — confianca {confianca} < {self.confianca_minima}")
            return None

        # Garante que entrada_min < entrada_max
        if entrada_min >= entrada_max:
            entrada_min, entrada_max = entrada_max - Decimal("5"), entrada_max

        # ATR proxy = amplitude da banda
        amplitude = entrada_max - entrada_min
        atr_proxy = amplitude if amplitude > Decimal("0") else Decimal("10")

        stop_loss = entrada_min - atr_proxy * Decimal("1.5")
        take_profit = preco_atual + atr_proxy * Decimal("2.5")

        risco = preco_atual - stop_loss
        recompensa = take_profit - preco_atual
        risk_reward = recompensa / risco if risco > Decimal("0") else Decimal("2.0")

        # Confluencia: baseado no padrao e confianca
        peso = _PESO_PADRAO.get(padrao, 2)
        fator_conf = float(confianca)
        confluencia = min(5, max(1, round(peso * fator_conf)))

        try:
            alerta = AlertaOportunidade(
                ativo=Symbol(symbol),
                padrao=padrao,
                nivel=nivel,
                preco_atual=Price(preco_atual),
                timestamp_deteccao=timestamp,
                entrada_minima=Price(entrada_min),
                entrada_maxima=Price(entrada_max),
                stop_loss=Price(stop_loss),
                take_profit=Price(take_profit),
                confianca=confianca,
                risk_reward=risk_reward,
                # Campos SMC enriquecidos
                sinal_smc_nome=sinal_nome,
                sinal_smc_confianca=confianca,
                confluencia_strength=confluencia,
                trader_pode_ver_sinal=True,
            )
        except ValueError as exc:
            logger.warning(f"{symbol}: Alerta SMC invalido — {exc}")
            return None

        logger.info(
            f"[SMC] {symbol} {sinal_nome} | "
            f"confianca={float(confianca):.0%} "
            f"confluencia={confluencia}/5 "
            f"nivel={nivel.value}"
        )
        return alerta
