"""Detector de padrões técnicos: engulfing, divergência, breaks."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from src.domain.entities.alerta import AlertaOportunidade
from src.domain.enums.alerta_enums import NivelAlerta, PatraoAlerta
from src.domain.value_objects import Price, Symbol

logger = logging.getLogger(__name__)


class DetectorPadroesTecnico:
    """
    Detector de padrões técnicos clássicos.

    Padrões v1.1 (MVP):
    1. Engulfing (Bullish/Bearish) - 65% confiança
    2. Divergência RSI/Preço - 60% confiança
    3. Break de Suporte/Resistência - 70% confiança

    Padrões v1.2+:
    - Harmonic Patterns (Fibonacci)
    - Ichimoku Cloud
    - Elliott Waves
    """

    def __init__(self):
        """Inicializa detector."""
        self.cache_rsi = {}  # {symbol: últimos valores RSI}
        self.cache_maxima = {}  # {symbol: máximos/mínimos recentes}

    def detectar_engulfing(
        self,
        symbol: str,
        vela_atual: dict,
        vela_anterior: dict,
        timestamp: datetime,
    ) -> Optional[AlertaOportunidade]:
        """
        Detecta padrão Engulfing (candela envolve anterior).

        Args:
            symbol: Código do ativo
            vela_atual: {open, high, low, close}
            vela_anterior: {open, high, low, close}
            timestamp: Quando detectado

        Returns:
            AlertaOportunidade se padrão detectado, None caso contrário
        """

        open_atual = float(vela_atual["open"])
        close_atual = float(vela_atual["close"])
        open_anterior = float(vela_anterior["open"])
        close_anterior = float(vela_anterior["close"])

        # Tamanho dos corpos
        body_atual = abs(close_atual - open_atual)
        body_anterior = abs(close_anterior - open_anterior)

        # BULLISH ENGULFING
        # Vela anterior: Baixista (close < open)
        # Vela atual: Altista (open < close) E envolve anterior
        if (
            close_anterior < open_anterior  # anterior é bearish
            and open_atual < close_atual  # atual é bullish
            and open_atual < close_anterior  # abre abaixo do close anterior
            and close_atual > open_anterior  # fecha acima do open anterior
            and body_atual > body_anterior * 0.8  # corpo maior
        ):
            logger.info(f"{symbol}: Bullish Engulfing detectado")

            return self._criar_alerta_padrao(
                symbol=symbol,
                padrao=PatraoAlerta.ENGULFING_BULLISH,
                nivel=NivelAlerta.ALTO,
                confianca=Decimal("0.65"),
                preco_atual=Decimal(str(close_atual)),
                entrada_min=Decimal(str(min(open_anterior, close_anterior))),
                entrada_max=Decimal(str(max(open_atual, close_atual))),
                timestamp=timestamp,
            )

        # BEARISH ENGULFING
        # Vela anterior: Altista (close > open)
        # Vela atual: Baixista (open > close) E envolve anterior
        if (
            close_anterior > open_anterior  # anterior é bullish
            and open_atual > close_atual  # atual é bearish
            and open_atual > close_anterior  # abre acima do close anterior
            and close_atual < open_anterior  # fecha abaixo do open anterior
            and body_atual > body_anterior * 0.8  # corpo maior
        ):
            logger.info(f"{symbol}: Bearish Engulfing detectado")

            return self._criar_alerta_padrao(
                symbol=symbol,
                padrao=PatraoAlerta.ENGULFING_BEARISH,
                nivel=NivelAlerta.ALTO,
                confianca=Decimal("0.65"),
                preco_atual=Decimal(str(close_atual)),
                entrada_min=Decimal(str(min(close_atual, open_atual))),
                entrada_max=Decimal(str(max(open_anterior, close_anterior))),
                timestamp=timestamp,
            )

        return None

    def detectar_divergencia_rsi(
        self,
        symbol: str,
        precos: List[float],
        rsi_values: List[float],
        timestamp: datetime,
    ) -> Optional[AlertaOportunidade]:
        """
        Detecta divergência entre preço e RSI (esgotamento).

        Bearish divergência:
        - Preço faz novo máximo
        - RSI não faz novo máximo (esgotamento de compradores)

        Bullish divergência:
        - Preço faz novo mínimo
        - RSI não faz novo mínimo (esgotamento de vendedores)

        Args:
            symbol: Código do ativo
            precos: Últimos 5+ preços de fechamento
            rsi_values: Últimos 5+ valores d RSI
            timestamp: Quando detectado

        Returns:
            AlertaOportunidade se divergência detectada
        """

        if len(precos) < 5 or len(rsi_values) < 5:
            return None

        precos_5 = precos[-5:]
        rsi_5 = rsi_values[-5:]
        preco_atual = precos[-1]
        rsi_atual = rsi_values[-1]

        # BEARISH DIVERGÊNCIA (no topo)
        preco_max = max(precos_5)
        rsi_max = max(rsi_5)

        if (
            preco_atual == preco_max
            and rsi_atual < rsi_max
            and rsi_atual > 70  # Confirmação: RSI em nível alto
        ):
            logger.info(f"{symbol}: Bearish Divergência RSI detectada")

            return self._criar_alerta_padrao(
                symbol=symbol,
                padrao=PatraoAlerta.DIVERGENCIA_RSI,
                nivel=NivelAlerta.MÉDIO,
                confianca=Decimal("0.60"),
                preco_atual=Decimal(str(preco_atual)),
                entrada_min=Decimal(str(preco_atual * 0.99)),  # -1%
                entrada_max=Decimal(str(preco_atual * 1.01)),  # +1%
                timestamp=timestamp,
            )

        # BULLISH DIVERGÊNCIA (no fundo)
        preco_min = min(precos_5)
        rsi_min = min(rsi_5)

        if (
            preco_atual == preco_min
            and rsi_atual > rsi_min
            and rsi_atual < 30  # Confirmação: RSI em nível baixo
        ):
            logger.info(f"{symbol}: Bullish Divergência RSI detectada")

            return self._criar_alerta_padrao(
                symbol=symbol,
                padrao=PatraoAlerta.DIVERGENCIA_RSI,
                nivel=NivelAlerta.MÉDIO,
                confianca=Decimal("0.60"),
                preco_atual=Decimal(str(preco_atual)),
                entrada_min=Decimal(str(preco_atual * 0.99)),  # -1%
                entrada_max=Decimal(str(preco_atual * 1.01)),  # +1%
                timestamp=timestamp,
            )

        return None

    def detectar_break_suporte(
        self,
        symbol: str,
        precos: List[float],
        timestamp: datetime,
        window: int = 5,
    ) -> Optional[AlertaOportunidade]:
        """
        Detecta break de suporte (preço quebra mínimo recente).

        Args:
            symbol: Código do ativo
            precos: Preços de fechamento históricos
            timestamp: Quando detectado
            window: Períodos para calcular suporte

        Returns:
            AlertaOportunidade se breakdetectado
        """

        if len(precos) < window + 1:
            return None

        preco_atual = precos[-1]
        preco_anterior = precos[-2]
        suporte = min(precos[-window:])

        # Break: fecha abaixo de suporte e anterior estava acima
        if preco_anterior >= suporte and preco_atual < suporte:
            logger.info(f"{symbol}: Break de Suporte detectado")

            return self._criar_alerta_padrao(
                symbol=symbol,
                padrao=PatraoAlerta.BREAK_SUPORTE,
                nivel=NivelAlerta.ALTO,
                confianca=Decimal("0.70"),
                preco_atual=Decimal(str(preco_atual)),
                entrada_min=Decimal(str(suporte * 0.98)),  # Um pouco abaixo
                entrada_max=Decimal(str(suporte * 1.00)),  # Até suporte
                timestamp=timestamp,
            )

        return None

    def detectar_break_resistencia(
        self,
        symbol: str,
        precos: List[float],
        timestamp: datetime,
        window: int = 5,
    ) -> Optional[AlertaOportunidade]:
        """
        Detecta break de resistência (preço quebra máximo recente).

        Args:
            symbol: Código do ativo
            preços: Preços de fechamento históricos
            timestamp: Quando detectado
            window: Períodos para calcular resistência

        Returns:
            AlertaOportunidade se break detectado
        """

        if len(precos) < window + 1:
            return None

        preco_atual = precos[-1]
        preco_anterior = precos[-2]
        resistencia = max(precos[-window:])

        # Break: fecha acima de resistência e anterior estava abaixo
        if preco_anterior <= resistencia and preco_atual > resistencia:
            logger.info(f"{symbol}: Break de Resistência detectado")

            return self._criar_alerta_padrao(
                symbol=symbol,
                padrao=PatraoAlerta.BREAK_RESISTENCIA,
                nivel=NivelAlerta.ALTO,
                confianca=Decimal("0.70"),
                preco_atual=Decimal(str(preco_atual)),
                entrada_min=Decimal(str(resistencia * 1.00)),  # Até resistência
                entrada_max=Decimal(str(resistencia * 1.02)),  # Um pouco acima
                timestamp=timestamp,
            )

        return None

    def _criar_alerta_padrao(
        self,
        symbol: str,
        padrao: PatraoAlerta,
        nivel: NivelAlerta,
        confianca: Decimal,
        preco_atual: Decimal,
        entrada_min: Decimal,
        entrada_max: Decimal,
        timestamp: datetime,
        atr_multiplier: Decimal = Decimal("1.5"),
    ) -> AlertaOportunidade:
        """
        Cria AlertaOportunidade para padrão técnico (código comum).

        Args:
            symbol: Código do ativo
            padrao: Tipo de padrão
            nivel: Nível de severidade
            confianca: Confiança (0-1)
            preco_atual: Preço de fechamento
            entrada_min: Min da banda de entrada
            entrada_max: Max da banda de entrada
            timestamp: Quando detectado
            atr_multiplier: Multiplicador para SL (padrão 1.5)

        Returns:
            AlertaOportunidade estruturado
        """

        # ATR como proxy (usa diferença das últimas velas)
        atr_value = (entrada_max - entrada_min) * atr_multiplier / Decimal("2")

        # Stop loss: uma ATR abaixo da entrada
        stop_loss = entrada_min - atr_value

        # Take profit: 2.5x o risco
        take_profit = preco_atual + atr_value * Decimal("2.5")

        # Risk:Reward
        risco = preco_atual - stop_loss
        recompensa = take_profit - preco_atual
        risk_reward = recompensa / risco if risco > Decimal("0") else Decimal("0")

        return AlertaOportunidade(
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
        )
