"""Enums para o sistema de Macro Score."""

from enum import Enum


class CorrelationType(str, Enum):
    """Tipo de correlacao do ativo com WIN."""

    DIRETA = "DIRETA"  # Ativo subindo = WIN subindo
    INVERSA = "INVERSA"  # Ativo subindo = WIN caindo

    def __str__(self) -> str:
        return self.value


class AssetCategory(str, Enum):
    """Categoria do ativo monitorado."""

    INDICES_BRASIL = "INDICES_BRASIL"
    ACOES_BRASIL = "ACOES_BRASIL"
    DOLAR_CAMBIO = "DOLAR_CAMBIO"
    FOREX = "FOREX"
    COMMODITIES = "COMMODITIES"
    JUROS_RENDA_FIXA = "JUROS_RENDA_FIXA"
    CURVA_JUROS = "CURVA_JUROS"  # Vertices da curva DI + spread
    RISCO_PAIS = "RISCO_PAIS"  # CDS, cupom cambial, EWZ
    PETROLEO_ENERGIA = "PETROLEO_ENERGIA"  # WTI, Brent, gas natural
    EMERGENTES = "EMERGENTES"  # ETFs/indices de mercados emergentes
    CRIPTOMOEDAS = "CRIPTOMOEDAS"
    INDICES_GLOBAIS = "INDICES_GLOBAIS"
    VOLATILIDADE = "VOLATILIDADE"
    INDICADORES_TECNICOS = "INDICADORES_TECNICOS"
    FLUXO_MICROESTRUTURA = "FLUXO_MICROESTRUTURA"  # Delta, imbalance, book

    def __str__(self) -> str:
        return self.value


class ForexConvention(str, Enum):
    """Convencao de cotacao forex no MT5."""

    XXX_USD = "XXX_USD"  # EURUSD: alta = moeda base fortalece
    USD_XXX = "USD_XXX"  # USDJPY: alta = USD fortalece

    def __str__(self) -> str:
        return self.value


class MacroSignal(str, Enum):
    """Sinal gerado pelo score macro."""

    COMPRA = "COMPRA"
    VENDA = "VENDA"
    NEUTRO = "NEUTRO"

    def __str__(self) -> str:
        return self.value


class ScoringType(str, Enum):
    """Tipo de pontuacao do item."""

    PRICE_VS_OPEN = "PRICE_VS_OPEN"  # Preco atual vs abertura do dia
    TECHNICAL_INDICATOR = "TECHNICAL_INDICATOR"  # Indicador tecnico calculado
    SPREAD_CURVE = "SPREAD_CURVE"  # Spread entre vertices da curva de juros
    FLOW_INDICATOR = "FLOW_INDICATOR"  # Indicador de fluxo/microestrutura

    def __str__(self) -> str:
        return self.value
