"""Testes unitarios para ValidadorSLMaximo."""

import pytest

from src.application.gerenciamento_risco.controles_agente.validador_sl_maximo import (
    ResultadoValidacaoSL,
    ValidadorSLMaximo,
)
from src.domain.value_objects.risco_externo import ConfiguracaoSLMaximo


@pytest.fixture
def config_200() -> ConfiguracaoSLMaximo:
    """Perda maxima de R$ 200 por operacao (WINFUT, valor_ponto=0.20)."""
    return ConfiguracaoSLMaximo(
        perda_maxima_por_operacao_reais=200.0, valor_ponto=0.20
    )


@pytest.fixture
def validador(config_200: ConfiguracaoSLMaximo) -> ValidadorSLMaximo:
    return ValidadorSLMaximo(configuracao=config_200)


class TestValidarSLDentroDoLimite:
    """SL que nao excede o limite deve ser aprovado."""

    def test_sl_dentro_do_limite_aprovado(
        self, validador: ValidadorSLMaximo
    ) -> None:
        # distancia=100pts, volume=1, valor_ponto=0.20 => perda=R$20
        resultado = validador.validar(
            preco_entrada=130_000.0, stop_loss=129_900.0, volume=1.0
        )
        assert resultado.aprovado is True
        assert abs(resultado.perda_estimada_reais - 20.0) < 0.01

    def test_sl_exatamente_no_limite_aprovado(
        self, validador: ValidadorSLMaximo
    ) -> None:
        # distancia=1000pts, volume=1, valor_ponto=0.20 => perda=R$200 (igual ao limite)
        resultado = validador.validar(
            preco_entrada=130_000.0, stop_loss=129_000.0, volume=1.0
        )
        assert resultado.aprovado is True
        assert abs(resultado.perda_estimada_reais - 200.0) < 0.01

    def test_sl_com_volume_maior_dentro_do_limite(
        self, validador: ValidadorSLMaximo
    ) -> None:
        # distancia=50pts, volume=2, valor_ponto=0.20 => perda=R$20
        resultado = validador.validar(
            preco_entrada=130_000.0, stop_loss=129_950.0, volume=2.0
        )
        assert resultado.aprovado is True

    def test_sl_venda_short_aprovado(
        self, validador: ValidadorSLMaximo
    ) -> None:
        # Venda: preco_entrada < stop_loss
        # distancia=100pts, volume=1, valor_ponto=0.20 => perda=R$20
        resultado = validador.validar(
            preco_entrada=129_900.0, stop_loss=130_000.0, volume=1.0
        )
        assert resultado.aprovado is True


class TestValidarSLAcimaDoLimite:
    """SL que excede o limite deve ser reprovado."""

    def test_sl_acima_do_limite_reprovado(
        self, validador: ValidadorSLMaximo
    ) -> None:
        # distancia=1001pts, volume=1, valor_ponto=0.20 => perda=R$200.20
        resultado = validador.validar(
            preco_entrada=130_000.0, stop_loss=128_999.0, volume=1.0
        )
        assert resultado.aprovado is False
        assert resultado.perda_estimada_reais > 200.0
        assert "excede" in resultado.motivo.lower()

    def test_sl_muito_acima_do_limite(
        self, validador: ValidadorSLMaximo
    ) -> None:
        # distancia=5000pts, volume=5 => perda=R$5000
        resultado = validador.validar(
            preco_entrada=130_000.0, stop_loss=125_000.0, volume=5.0
        )
        assert resultado.aprovado is False
        assert resultado.perda_estimada_reais > 200.0

    def test_motivo_menciona_valores(
        self, validador: ValidadorSLMaximo
    ) -> None:
        resultado = validador.validar(
            preco_entrada=130_000.0, stop_loss=128_000.0, volume=2.0
        )
        # distancia=2000pts, volume=2, valor_ponto=0.20 => perda=R$800
        assert resultado.aprovado is False
        assert "800" in resultado.motivo or "200" in resultado.motivo


class TestResultadoValidacaoSL:
    """Testes do dataclass ResultadoValidacaoSL."""

    def test_campos_resultado(self) -> None:
        resultado = ResultadoValidacaoSL(
            aprovado=True,
            perda_estimada_reais=50.0,
            perda_maxima_reais=200.0,
            motivo="SL dentro do limite permitido",
        )
        assert resultado.aprovado is True
        assert resultado.perda_estimada_reais == 50.0
        assert resultado.perda_maxima_reais == 200.0


class TestCalculoPerda:
    """Testes da formula de calculo de perda."""

    def test_formula_winfut(self) -> None:
        """Verifica formula: distancia_pontos * volume * valor_ponto."""
        config = ConfiguracaoSLMaximo(
            perda_maxima_por_operacao_reais=1000.0, valor_ponto=0.20
        )
        validador = ValidadorSLMaximo(configuracao=config)
        # 500 pontos * 3 contratos * R$0.20 = R$300
        resultado = validador.validar(
            preco_entrada=130_000.0, stop_loss=129_500.0, volume=3.0
        )
        assert abs(resultado.perda_estimada_reais - 300.0) < 0.01

    def test_formula_valor_ponto_diferente(self) -> None:
        """Testa com valor_ponto diferente (ex: WIN$ full = R$1.00)."""
        config = ConfiguracaoSLMaximo(
            perda_maxima_por_operacao_reais=1000.0, valor_ponto=1.0
        )
        validador = ValidadorSLMaximo(configuracao=config)
        # 200 pontos * 2 contratos * R$1.00 = R$400
        resultado = validador.validar(
            preco_entrada=130_000.0, stop_loss=129_800.0, volume=2.0
        )
        assert abs(resultado.perda_estimada_reais - 400.0) < 0.01


class TestConfiguracaoSLMaximo:
    """Testes de validacao do value object ConfiguracaoSLMaximo."""

    def test_perda_negativa_invalida(self) -> None:
        with pytest.raises(ValueError):
            ConfiguracaoSLMaximo(perda_maxima_por_operacao_reais=-100.0)

    def test_perda_zero_invalida(self) -> None:
        with pytest.raises(ValueError):
            ConfiguracaoSLMaximo(perda_maxima_por_operacao_reais=0.0)

    def test_valor_ponto_zero_invalido(self) -> None:
        with pytest.raises(ValueError):
            ConfiguracaoSLMaximo(
                perda_maxima_por_operacao_reais=200.0, valor_ponto=0.0
            )
