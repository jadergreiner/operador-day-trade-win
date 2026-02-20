"""Enums de alertas - tipos de alertas, padrões e níveis."""

from enum import Enum


class NivelAlerta(str, Enum):
    """Nível de severidade do alerta."""

    CRÍTICO = "CRÍTICO"
    ALTO = "ALTO"
    MÉDIO = "MÉDIO"

    def __str__(self) -> str:
        return self.value


class PatraoAlerta(str, Enum):
    """Padrão que disparou o alerta."""

    VOLATILIDADE_EXTREMA = "volatilidade_extrema"
    ENGULFING_BULLISH = "engulfing_bullish"
    ENGULFING_BEARISH = "engulfing_bearish"
    DIVERGENCIA_RSI = "divergencia_rsi"
    BREAK_SUPORTE = "break_suporte"
    BREAK_RESISTENCIA = "break_resistencia"

    def __str__(self) -> str:
        return self.value


class StatusAlerta(str, Enum):
    """Status do alerta no ciclo de vida."""

    GERADO = "GERADO"
    ENFILEIRADO = "ENFILEIRADO"
    DUPLICADO = "DUPLICADO"
    ENTREGANDO = "ENTREGANDO"
    ENTREGUE = "ENTREGUE"
    FALHA_ENTREGA = "FALHA_ENTREGA"
    EXECUTADO = "EXECUTADO"
    REJEITADO = "REJEITADO"

    def __str__(self) -> str:
        return self.value


class CanalEntrega(str, Enum):
    """Canais de entrega de alertas."""

    WEBSOCKET = "websocket"
    EMAIL = "email"
    SMS = "sms"

    def __str__(self) -> str:
        return self.value
