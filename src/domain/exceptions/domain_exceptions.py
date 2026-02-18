"""Excecoes de dominio - excecoes customizadas para o sistema de trading."""


class DomainError(Exception):
    """Excecao base para todos os erros de dominio."""

    pass


class TradingError(DomainError):
    """Excecao base para erros relacionados a trading."""

    pass


class InvalidOrderError(TradingError):
    """Lancada quando uma ordem e invalida."""

    pass


class InsufficientCapitalError(TradingError):
    """Lancada quando nao ha capital suficiente para a operacao."""

    pass


class InvalidOperationError(TradingError):
    """Lancada quando uma operacao invalida e tentada."""

    pass


class PositionNotFoundError(TradingError):
    """Lancada quando uma posicao nao e encontrada."""

    pass


class RiskLimitExceededError(TradingError):
    """Lancada quando limites de risco sao excedidos."""

    pass


class InvalidPriceError(DomainError):
    """Lancada quando um valor de preco e invalido."""

    pass


class InvalidQuantityError(DomainError):
    """Lancada quando um valor de quantidade e invalido."""

    pass


class ModelError(DomainError):
    """Excecao base para erros relacionados a modelos."""

    pass


class ModelNotTrainedError(ModelError):
    """Lancada ao tentar usar um modelo nao treinado."""

    pass


class InvalidFeatureError(ModelError):
    """Lancada quando features sao invalidas ou ausentes."""

    pass


class BrokerError(DomainError):
    """Excecao base para erros relacionados ao broker."""

    pass


class BrokerConnectionError(BrokerError):
    """Lancada quando a conexao com o broker falha."""

    pass


class OrderExecutionError(BrokerError):
    """Lancada quando a execucao de uma ordem falha."""

    pass


class DataError(DomainError):
    """Excecao base para erros relacionados a dados."""

    pass


class DataNotFoundError(DataError):
    """Lancada quando dados requeridos nao sao encontrados."""

    pass


class InvalidDataError(DataError):
    """Lancada quando dados sao invalidos ou corrompidos."""

    pass
