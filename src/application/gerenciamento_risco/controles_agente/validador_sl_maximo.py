"""
ValidadorSLMaximo: Valida que o stop loss nao excede a perda maxima por operacao.

Responsabilidades:
- Calcular perda estimada: distancia_sl_pontos * volume * valor_ponto
- Rejeitar ordens cuja perda estimada excede perda_maxima_por_operacao_reais
- Suportar tanto compras (SL abaixo) quanto vendas (SL acima)

Formula WINFUT:
    perda_estimada = |preco_entrada - stop_loss| * volume * valor_ponto
    onde valor_ponto = R$ 0.20 por ponto do mini-indice

Pipeline:
    GerenciadorRiscoExterno.avaliar_todos()
    → ValidadorSLMaximo.validar(preco_entrada, stop_loss, volume)
    → ResultadoValidacaoSL.aprovado determina EXECUTE/REJECT no AC4

Status: v1.0 (24/03/2026)
Referencia: docs/BACKLOG.md (Camada Risco Externo - SL Maximo)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.domain.value_objects.risco_externo import ConfiguracaoSLMaximo

logger = logging.getLogger(__name__)


@dataclass
class ResultadoValidacaoSL:
    """
    Resultado da validacao do stop loss maximo.

    Atributos:
        aprovado: True se a perda estimada esta dentro do limite.
        perda_estimada_reais: Perda calculada para a operacao (R$).
        perda_maxima_reais: Limite configurado (R$).
        motivo: Descricao textual da decisao.
    """

    aprovado: bool
    perda_estimada_reais: float
    perda_maxima_reais: float
    motivo: str


class ValidadorSLMaximo:
    """
    Valida que o stop loss configurado nao excede a perda maxima permitida.

    Funciona para posicoes compradas (SL < preco_entrada) e
    vendidas (SL > preco_entrada) usando valor absoluto da distancia.

    Exemplo de uso:
        config = ConfiguracaoSLMaximo(perda_maxima_por_operacao_reais=200.0)
        validador = ValidadorSLMaximo(config)
        resultado = validador.validar(
            preco_entrada=130_000.0,
            stop_loss=129_500.0,
            volume=1.0,
        )
        if not resultado.aprovado:
            # rejeitar ordem
    """

    def __init__(self, configuracao: ConfiguracaoSLMaximo) -> None:
        self._configuracao = configuracao

    def validar(
        self,
        preco_entrada: float,
        stop_loss: float,
        volume: float,
    ) -> ResultadoValidacaoSL:
        """
        Calcula a perda estimada e verifica contra o limite configurado.

        Args:
            preco_entrada: Preco de entrada da ordem.
            stop_loss: Preco de stop loss configurado.
            volume: Volume em contratos/lotes.

        Returns:
            ResultadoValidacaoSL com aprovado=True se dentro do limite.
        """
        distancia_pontos = abs(preco_entrada - stop_loss)
        perda_estimada = distancia_pontos * volume * self._configuracao.valor_ponto
        perda_maxima = self._configuracao.perda_maxima_por_operacao_reais

        if perda_estimada <= perda_maxima:
            motivo = (
                f"SL dentro do limite: perda estimada R${perda_estimada:.2f} "
                f"<= maximo R${perda_maxima:.2f}"
            )
            logger.debug(motivo)
            return ResultadoValidacaoSL(
                aprovado=True,
                perda_estimada_reais=perda_estimada,
                perda_maxima_reais=perda_maxima,
                motivo=motivo,
            )

        motivo = (
            f"SL excede limite: perda estimada R${perda_estimada:.2f} "
            f"excede maximo R${perda_maxima:.2f} "
            f"(distancia={distancia_pontos:.0f}pts, "
            f"volume={volume}, ponto=R${self._configuracao.valor_ponto:.2f})"
        )
        logger.warning(motivo)
        return ResultadoValidacaoSL(
            aprovado=False,
            perda_estimada_reais=perda_estimada,
            perda_maxima_reais=perda_maxima,
            motivo=motivo,
        )
