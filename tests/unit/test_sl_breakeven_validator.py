"""
Testes para BUG-MICRO-01 — Validador de SL Break-Even.

Cobrem os casos:
- Diferença zero entre SL atual e novo (nao enviar)
- Diferença menor que tick_size (nao enviar)
- Diferença valida (enviar com SL alinhado ao tick)
- retcode=10013 com retry usando offset de 2 ticks
- SL ja no break-even = INFO, nao ERROR
- Campo sl_break_even_aplicado (bool) no resultado
"""

import pytest

from src.application.sl_breakeven_validator import (
    ResultadoValidacaoSL,
    StatusValidacaoSL,
    ValidadorSLBreakEven,
)


class TestResultadoValidacaoSL:
    """Testes para o dataclass ResultadoValidacaoSL."""

    def test_criar_resultado_permitido(self) -> None:
        resultado = ResultadoValidacaoSL(
            permitido=True,
            sl_ajustado=181930.0,
            sl_original=181930.0,
            sl_atual_mt5=181900.0,
            status=StatusValidacaoSL.PERMITIDO,
            motivo="Diferenca valida: 30.0 pts (>= 5.0 tick)",
            sl_break_even_aplicado=True,
        )
        assert resultado.permitido is True
        assert resultado.sl_ajustado == 181930.0
        assert resultado.sl_break_even_aplicado is True

    def test_criar_resultado_ignorado(self) -> None:
        resultado = ResultadoValidacaoSL(
            permitido=False,
            sl_ajustado=181930.0,
            sl_original=181930.0,
            sl_atual_mt5=181930.0,
            status=StatusValidacaoSL.IGNORADO_SL_JA_APLICADO,
            motivo="SL ja esta no break-even (181930.0 == 181930.0)",
            sl_break_even_aplicado=True,
        )
        assert resultado.permitido is False
        assert resultado.status == StatusValidacaoSL.IGNORADO_SL_JA_APLICADO

    def test_para_dict(self) -> None:
        resultado = ResultadoValidacaoSL(
            permitido=True,
            sl_ajustado=181930.0,
            sl_original=181930.0,
            sl_atual_mt5=181900.0,
            status=StatusValidacaoSL.PERMITIDO,
            motivo="OK",
            sl_break_even_aplicado=False,
        )
        d = resultado.para_dict()
        assert "permitido" in d
        assert "sl_ajustado" in d
        assert "status" in d
        assert "motivo" in d
        assert "sl_break_even_aplicado" in d


class TestStatusValidacaoSL:
    """Testes para o enum StatusValidacaoSL."""

    def test_valores_esperados(self) -> None:
        valores = [s.value for s in StatusValidacaoSL]
        assert "PERMITIDO" in valores
        assert "IGNORADO_SL_JA_APLICADO" in valores
        assert "IGNORADO_DIFERENCA_INSUFICIENTE" in valores
        assert "AJUSTADO_OFFSET_2_TICKS" in valores

    def test_contagem_minima(self) -> None:
        assert len(StatusValidacaoSL) >= 4


class TestValidadorSLBreakEven:
    """Testes para o motor principal ValidadorSLBreakEven."""

    def setup_method(self) -> None:
        """Cria validador com tick_size padrao WIN$ = 5 pts."""
        self.validador = ValidadorSLBreakEven(tick_size=5.0)

    # ---------------------------------------------------------------
    # Caso 1: SL novo == SL atual (diferenca zero)
    # ---------------------------------------------------------------

    def test_diferenca_zero_retorna_ignorado(self) -> None:
        """SL novo identico ao atual — nao deve enviar, INFO nao ERROR."""
        resultado = self.validador.validar(
            sl_novo=181930.0,
            sl_atual_mt5=181930.0,
            direcao="BUY",
        )
        assert resultado.permitido is False
        assert resultado.status == StatusValidacaoSL.IGNORADO_SL_JA_APLICADO
        assert resultado.sl_break_even_aplicado is True

    def test_diferenca_zero_sell_retorna_ignorado(self) -> None:
        resultado = self.validador.validar(
            sl_novo=182000.0,
            sl_atual_mt5=182000.0,
            direcao="SELL",
        )
        assert resultado.permitido is False
        assert resultado.status == StatusValidacaoSL.IGNORADO_SL_JA_APLICADO

    # ---------------------------------------------------------------
    # Caso 2: Diferenca menor que tick_size (< 5 pts para WIN$)
    # ---------------------------------------------------------------

    def test_diferenca_menor_tick_buy_retorna_ignorado(self) -> None:
        """Diferenca de 3 pts < tick_size 5 pts — nao deve enviar."""
        resultado = self.validador.validar(
            sl_novo=181933.0,
            sl_atual_mt5=181930.0,
            direcao="BUY",
        )
        assert resultado.permitido is False
        assert resultado.status == StatusValidacaoSL.IGNORADO_DIFERENCA_INSUFICIENTE

    def test_diferenca_menor_tick_sell_retorna_ignorado(self) -> None:
        resultado = self.validador.validar(
            sl_novo=182003.0,
            sl_atual_mt5=182000.0,
            direcao="SELL",
        )
        assert resultado.permitido is False
        assert resultado.status == StatusValidacaoSL.IGNORADO_DIFERENCA_INSUFICIENTE

    def test_diferenca_exatamente_um_ponto_retorna_ignorado(self) -> None:
        """O log original: diferenca de 1 pt (<5) causava retcode=10013."""
        resultado = self.validador.validar(
            sl_novo=181931.0,
            sl_atual_mt5=181930.0,
            direcao="BUY",
        )
        assert resultado.permitido is False
        assert resultado.status == StatusValidacaoSL.IGNORADO_DIFERENCA_INSUFICIENTE

    # ---------------------------------------------------------------
    # Caso 3: Diferenca valida (>= tick_size)
    # ---------------------------------------------------------------

    def test_diferenca_valida_buy_permite_envio(self) -> None:
        """Diferenca de 30 pts >= tick_size 5 pts — deve enviar."""
        resultado = self.validador.validar(
            sl_novo=181930.0,
            sl_atual_mt5=181900.0,
            direcao="BUY",
        )
        assert resultado.permitido is True
        assert resultado.status == StatusValidacaoSL.PERMITIDO
        assert resultado.sl_ajustado == 181930.0

    def test_diferenca_valida_sell_permite_envio(self) -> None:
        resultado = self.validador.validar(
            sl_novo=182000.0,
            sl_atual_mt5=182030.0,
            direcao="SELL",
        )
        assert resultado.permitido is True
        assert resultado.status == StatusValidacaoSL.PERMITIDO

    def test_diferenca_exatamente_tick_permite_envio(self) -> None:
        """Diferenca exatamente igual ao tick_size deve ser permitida."""
        resultado = self.validador.validar(
            sl_novo=181935.0,
            sl_atual_mt5=181930.0,
            direcao="BUY",
        )
        assert resultado.permitido is True
        assert resultado.status == StatusValidacaoSL.PERMITIDO

    # ---------------------------------------------------------------
    # Caso 4: SL nao alinhado ao tick — deve ajustar
    # ---------------------------------------------------------------

    def test_sl_nao_alinhado_e_ajustado_ao_tick(self) -> None:
        """SL=181933 nao e multiplo de 5 — deve ser ajustado para 181935."""
        resultado = self.validador.validar(
            sl_novo=181933.0,
            sl_atual_mt5=181900.0,
            direcao="BUY",
        )
        # Diferenca 33 >= 5, mas sl_novo nao e multiplo de 5
        assert resultado.permitido is True
        assert resultado.sl_ajustado % self.validador.tick_size == 0

    def test_sl_alinhado_nao_e_alterado(self) -> None:
        """SL=181935 ja e multiplo de 5 — deve ser mantido."""
        resultado = self.validador.validar(
            sl_novo=181935.0,
            sl_atual_mt5=181900.0,
            direcao="BUY",
        )
        assert resultado.sl_ajustado == 181935.0

    # ---------------------------------------------------------------
    # Caso 5: Retry com offset de 2 ticks apos retcode=10013
    # ---------------------------------------------------------------

    def test_calcular_sl_com_offset_buy(self) -> None:
        """Offset de 2 ticks (10 pts) adiciona ao SL BUY."""
        sl_com_offset = self.validador.calcular_sl_com_offset(
            sl_base=181930.0,
            direcao="BUY",
            n_ticks=2,
        )
        assert sl_com_offset == 181940.0  # 181930 + 2*5

    def test_calcular_sl_com_offset_sell(self) -> None:
        """Offset de 2 ticks (10 pts) subtrai do SL SELL."""
        sl_com_offset = self.validador.calcular_sl_com_offset(
            sl_base=182000.0,
            direcao="SELL",
            n_ticks=2,
        )
        assert sl_com_offset == 181990.0  # 182000 - 2*5

    def test_validar_apos_retcode_10013_aplica_offset(self) -> None:
        """Apos retcode=10013, retry com 2 ticks offset deve ser PERMITIDO."""
        resultado = self.validador.validar_retry_apos_falha(
            sl_original=181930.0,
            sl_atual_mt5=181900.0,
            direcao="BUY",
            retcode=10013,
        )
        assert resultado.permitido is True
        assert resultado.status == StatusValidacaoSL.AJUSTADO_OFFSET_2_TICKS
        assert resultado.sl_ajustado > 181930.0

    def test_validar_retry_retcode_nao_10013_nao_aplica_offset(self) -> None:
        """Retcode diferente de 10013 nao aciona offset."""
        resultado = self.validador.validar_retry_apos_falha(
            sl_original=181930.0,
            sl_atual_mt5=181900.0,
            direcao="BUY",
            retcode=10009,
        )
        assert resultado.permitido is False

    # ---------------------------------------------------------------
    # Caso 6: Validar nivel de log (nao ERROR para sl ja aplicado)
    # ---------------------------------------------------------------

    def test_sl_ja_aplicado_nivel_log_info_nao_error(self) -> None:
        """SL ja no break-even deve retornar nivel_log=INFO."""
        resultado = self.validador.validar(
            sl_novo=181930.0,
            sl_atual_mt5=181930.0,
            direcao="BUY",
        )
        assert resultado.nivel_log == "INFO"

    def test_diferenca_insuficiente_nivel_log_debug(self) -> None:
        """Diferenca < tick deve retornar nivel_log=DEBUG."""
        resultado = self.validador.validar(
            sl_novo=181933.0,
            sl_atual_mt5=181930.0,
            direcao="BUY",
        )
        assert resultado.nivel_log == "DEBUG"

    def test_envio_permitido_nivel_log_info(self) -> None:
        resultado = self.validador.validar(
            sl_novo=181935.0,
            sl_atual_mt5=181900.0,
            direcao="BUY",
        )
        assert resultado.nivel_log == "INFO"

    # ---------------------------------------------------------------
    # Caso 7: Type hints e dataclass
    # ---------------------------------------------------------------

    def test_type_hints_100_porcento(self) -> None:
        """Verifica que as classes publicas tem type hints nos metodos."""
        import inspect

        from src.application.sl_breakeven_validator import ValidadorSLBreakEven

        for nome, obj in inspect.getmembers(ValidadorSLBreakEven, predicate=inspect.isfunction):
            hints = obj.__annotations__
            if not nome.startswith("_"):
                assert "return" in hints, (
                    f"Metodo {nome} sem annotation de retorno"
                )
