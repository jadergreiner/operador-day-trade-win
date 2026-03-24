"""Excecoes para a camada de gerenciamento de risco externo."""

from src.domain.exceptions.domain_exceptions import DomainError


class ErroRiscoExterno(DomainError):
    """Excecao base para erros do gerenciamento de risco externo."""

    pass


class ViolacaoCooldownError(ErroRiscoExterno):
    """Lancada quando o periodo de cooldown ainda esta ativo para o agente."""

    pass


class ViolacaoSLMaximoError(ErroRiscoExterno):
    """Lancada quando o stop loss excede a perda maxima permitida por operacao."""

    pass


class ViolacaoUnicaOrdemError(ErroRiscoExterno):
    """Lancada quando o agente ja possui uma ordem aberta."""

    pass


class LimiteGanhoDiarioError(ErroRiscoExterno):
    """Lancada quando o ganho diario total atingiu o limite configurado."""

    pass


class ViolacaoHorarioOperacaoError(ErroRiscoExterno):
    """Lancada quando a operacao e tentada fora do horario permitido."""

    pass


class EventoCalendarioProximoError(ErroRiscoExterno):
    """Lancada quando ha evento economico iminente bloqueando novas entradas."""

    pass
