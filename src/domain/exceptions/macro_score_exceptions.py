"""Exceptions para o sistema de Macro Score."""

from src.domain.exceptions.domain_exceptions import DomainError


class MacroScoreError(DomainError):
    """Base para erros do macro score."""

    pass


class SymbolNotAvailableError(MacroScoreError):
    """Simbolo nao disponivel no MT5."""

    pass


class ContractResolutionError(MacroScoreError):
    """Falha ao resolver contrato futuro vigente."""

    pass


class InsufficientDataError(MacroScoreError):
    """Dados insuficientes para calculo."""

    pass
