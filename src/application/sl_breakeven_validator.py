"""
BUG-MICRO-01: Validador de SL para Move Break-Even.

Responsabilidades:
- Validar se o novo SL pode ser enviado ao MT5 sem gerar retcode=10013
- Garantir que diferenca entre SL novo e atual >= tick_size do instrumento
- Alinhar SL ao multiplo do tick_size antes de enviar
- Reclassificar "SL ja no break-even" como INFO (nao ERROR)
- Fornecer retry com offset de 2 ticks apos retcode=10013

Pipeline:
    proteger_lucro_trade() decide novo SL
    -> ValidadorSLBreakEven.validar() verifica diferenca e alinha
    -> Se permitido=True: enviar para MT5
    -> Se retcode=10013: ValidadorSLBreakEven.validar_retry_apos_falha()
    -> Retry com sl_ajustado + 2 ticks

Status: Implementacao v1.0 (18/03/2026)
Referencia: docs/BACKLOG.md (BUG-MICRO-01)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict


class StatusValidacaoSL(Enum):
    """Status possiveis de validacao do SL break-even."""

    PERMITIDO = "PERMITIDO"
    """Diferenca valida — pode enviar ao MT5."""

    IGNORADO_SL_JA_APLICADO = "IGNORADO_SL_JA_APLICADO"
    """SL novo == SL atual — break-even ja esta ativo."""

    IGNORADO_DIFERENCA_INSUFICIENTE = "IGNORADO_DIFERENCA_INSUFICIENTE"
    """Diferenca < tick_size — MT5 rejeitaria (retcode=10013)."""

    AJUSTADO_OFFSET_2_TICKS = "AJUSTADO_OFFSET_2_TICKS"
    """SL ajustado com offset de 2 ticks apos retcode=10013."""


@dataclass
class ResultadoValidacaoSL:
    """Resultado da validacao de SL break-even.

    Args:
        permitido: True se o envio ao MT5 deve prosseguir.
        sl_ajustado: Valor final de SL a ser enviado (apos alinhamento de tick).
        sl_original: Valor de SL solicitado pelo chamador.
        sl_atual_mt5: Valor de SL atual registrado no MT5.
        status: Codigo de status da validacao.
        motivo: Descricao legivel do resultado.
        sl_break_even_aplicado: True se o break-even ja estava ou sera aplicado.
        nivel_log: Nivel de log recomendado ("INFO", "DEBUG", "WARNING").
    """

    permitido: bool
    sl_ajustado: float
    sl_original: float
    sl_atual_mt5: float
    status: StatusValidacaoSL
    motivo: str
    sl_break_even_aplicado: bool
    nivel_log: str = "INFO"

    def para_dict(self) -> Dict[str, Any]:
        """Converte resultado para dicionario JSON-serializavel.

        Returns:
            Dict com todos os campos do resultado.
        """
        return {
            "permitido": self.permitido,
            "sl_ajustado": self.sl_ajustado,
            "sl_original": self.sl_original,
            "sl_atual_mt5": self.sl_atual_mt5,
            "status": self.status.value,
            "motivo": self.motivo,
            "sl_break_even_aplicado": self.sl_break_even_aplicado,
            "nivel_log": self.nivel_log,
        }


class ValidadorSLBreakEven:
    """Valida e ajusta SL antes de enviar modificacao de break-even ao MT5.

    Problema resolvido (BUG-MICRO-01):
    - MT5 retorna retcode=10013 quando diferenca entre SL novo e atual
      e menor que o tick minimo do instrumento (WIN$ = 5 pts).
    - O calculo de break-even pode gerar o mesmo valor que o SL existente
      ou com diferenca insuficiente para aceitacao pelo broker.

    Regras de validacao:
    1. Se abs(sl_novo - sl_atual) == 0 -> IGNORADO_SL_JA_APLICADO (INFO)
    2. Se abs(sl_novo - sl_atual) < tick_size -> IGNORADO_DIFERENCA_INSUFICIENTE (DEBUG)
    3. Se diferenca >= tick_size -> PERMITIDO, com sl alinhado ao tick

    Args:
        tick_size: Tick minimo do instrumento em pontos (WIN$ = 5.0 pts).
    """

    def __init__(self, tick_size: float = 5.0) -> None:
        """Inicializa o validador.

        Args:
            tick_size: Tick minimo do instrumento (default 5.0 para WIN$).
        """
        self.tick_size = tick_size

    def validar(
        self,
        sl_novo: float,
        sl_atual_mt5: float,
        direcao: str,
    ) -> ResultadoValidacaoSL:
        """Valida se o novo SL pode ser enviado sem gerar retcode=10013.

        Args:
            sl_novo: Valor de SL desejado (ex: preco de entrada para break-even).
            sl_atual_mt5: Valor de SL atual registrado no MT5.
            direcao: Direcao da posicao ("BUY" ou "SELL").

        Returns:
            ResultadoValidacaoSL com decisao e SL ajustado ao tick.
        """
        diferenca = abs(sl_novo - sl_atual_mt5)

        # Caso 1: SL novo identico ao atual — break-even ja aplicado
        if diferenca == 0.0:
            return ResultadoValidacaoSL(
                permitido=False,
                sl_ajustado=sl_novo,
                sl_original=sl_novo,
                sl_atual_mt5=sl_atual_mt5,
                status=StatusValidacaoSL.IGNORADO_SL_JA_APLICADO,
                motivo=(
                    f"SL ja esta no break-even ({sl_novo:.2f} == {sl_atual_mt5:.2f})"
                ),
                sl_break_even_aplicado=True,
                nivel_log="INFO",
            )

        # Caso 2: Diferenca menor que tick_size — MT5 rejeitaria
        if diferenca < self.tick_size:
            return ResultadoValidacaoSL(
                permitido=False,
                sl_ajustado=sl_novo,
                sl_original=sl_novo,
                sl_atual_mt5=sl_atual_mt5,
                status=StatusValidacaoSL.IGNORADO_DIFERENCA_INSUFICIENTE,
                motivo=(
                    f"Diferenca {diferenca:.1f} pts < tick_size {self.tick_size:.1f} pts. "
                    f"MT5 rejeitaria (retcode=10013)."
                ),
                sl_break_even_aplicado=False,
                nivel_log="DEBUG",
            )

        # Caso 3: Diferenca valida — alinhar SL ao tick
        sl_alinhado = self._alinhar_ao_tick(sl_novo)

        return ResultadoValidacaoSL(
            permitido=True,
            sl_ajustado=sl_alinhado,
            sl_original=sl_novo,
            sl_atual_mt5=sl_atual_mt5,
            status=StatusValidacaoSL.PERMITIDO,
            motivo=(
                f"Diferenca valida: {diferenca:.1f} pts (>= {self.tick_size:.1f} tick). "
                f"SL alinhado: {sl_alinhado:.2f}"
            ),
            sl_break_even_aplicado=False,
            nivel_log="INFO",
        )

    def calcular_sl_com_offset(
        self,
        sl_base: float,
        direcao: str,
        n_ticks: int = 2,
    ) -> float:
        """Calcula SL com offset de N ticks para retry apos retcode=10013.

        Args:
            sl_base: Valor base de SL (ex: preco de entrada).
            direcao: Direcao da posicao ("BUY" ou "SELL").
            n_ticks: Numero de ticks de offset (default 2).

        Returns:
            SL ajustado com offset, alinhado ao tick.
        """
        offset = self.tick_size * n_ticks
        if direcao == "BUY":
            sl_com_offset = sl_base + offset
        else:
            sl_com_offset = sl_base - offset
        return self._alinhar_ao_tick(sl_com_offset)

    def validar_retry_apos_falha(
        self,
        sl_original: float,
        sl_atual_mt5: float,
        direcao: str,
        retcode: int,
    ) -> ResultadoValidacaoSL:
        """Valida retry com offset de 2 ticks apos falha do MT5.

        Aplica apenas quando retcode=10013 (Invalid request).
        Para outros retcodes, retorna nao-permitido.

        Args:
            sl_original: Valor de SL que falhou.
            sl_atual_mt5: Valor de SL atual no MT5.
            direcao: Direcao da posicao ("BUY" ou "SELL").
            retcode: Retcode retornado pelo MT5.

        Returns:
            ResultadoValidacaoSL com SL ajustado para retry.
        """
        # Apenas retcode=10013 (Invalid request) aciona o retry com offset
        if retcode != 10013:
            return ResultadoValidacaoSL(
                permitido=False,
                sl_ajustado=sl_original,
                sl_original=sl_original,
                sl_atual_mt5=sl_atual_mt5,
                status=StatusValidacaoSL.IGNORADO_DIFERENCA_INSUFICIENTE,
                motivo=(
                    f"Retcode {retcode} nao e 10013. "
                    f"Offset automatico nao se aplica."
                ),
                sl_break_even_aplicado=False,
                nivel_log="WARNING",
            )

        sl_com_offset = self.calcular_sl_com_offset(
            sl_base=sl_original,
            direcao=direcao,
            n_ticks=2,
        )
        diferenca_nova = abs(sl_com_offset - sl_atual_mt5)

        if diferenca_nova < self.tick_size:
            return ResultadoValidacaoSL(
                permitido=False,
                sl_ajustado=sl_com_offset,
                sl_original=sl_original,
                sl_atual_mt5=sl_atual_mt5,
                status=StatusValidacaoSL.IGNORADO_DIFERENCA_INSUFICIENTE,
                motivo=(
                    f"Mesmo com offset 2 ticks, diferenca {diferenca_nova:.1f} pts "
                    f"< {self.tick_size:.1f}. Abortar."
                ),
                sl_break_even_aplicado=False,
                nivel_log="WARNING",
            )

        return ResultadoValidacaoSL(
            permitido=True,
            sl_ajustado=sl_com_offset,
            sl_original=sl_original,
            sl_atual_mt5=sl_atual_mt5,
            status=StatusValidacaoSL.AJUSTADO_OFFSET_2_TICKS,
            motivo=(
                f"Retry apos retcode=10013: SL ajustado com offset 2 ticks "
                f"({sl_original:.2f} -> {sl_com_offset:.2f})"
            ),
            sl_break_even_aplicado=False,
            nivel_log="INFO",
        )

    def _alinhar_ao_tick(self, sl: float) -> float:
        """Alinha o valor de SL ao multiplo mais proximo do tick_size.

        Args:
            sl: Valor de SL a alinhar.

        Returns:
            Valor de SL alinhado ao tick.
        """
        return round(round(sl / self.tick_size) * self.tick_size, 2)
