"""Testes unitarios para GateHorarioOperacao."""

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

import pytest

from src.application.gerenciamento_risco.controles_globais.gate_horario_operacao import (
    GateHorarioOperacao,
    ResultadoHorario,
)
from src.domain.value_objects.risco_externo import ConfiguracaoHorario

_TZ_SP = ZoneInfo("America/Sao_Paulo")


def _agora_sp(hora: int, minuto: int) -> datetime:
    """Cria datetime em fuso Sao Paulo para injetar no gate."""
    return datetime(2026, 3, 24, hora, minuto, 0, tzinfo=_TZ_SP)


@pytest.fixture
def config_padrao() -> ConfiguracaoHorario:
    """Janela B3: 09:00-17:00, bloquear apos fim, fechar no fim."""
    return ConfiguracaoHorario(
        hora_inicio=time(9, 0),
        hora_fim=time(17, 0),
        bloquear_abertura_apos_fim=True,
        fechar_posicao_no_fim=True,
    )


def _criar_gate(
    config: ConfiguracaoHorario, hora: int, minuto: int
) -> GateHorarioOperacao:
    agora = _agora_sp(hora, minuto)
    return GateHorarioOperacao(
        configuracao=config, _agora=lambda: agora
    )


class TestDentroDoHorario:
    """Dentro da janela, deve liberar abertura e nao fechar posicoes."""

    def test_inicio_da_janela_libera(
        self, config_padrao: ConfiguracaoHorario
    ) -> None:
        gate = _criar_gate(config_padrao, hora=9, minuto=0)
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is True
        assert resultado.deve_fechar_posicoes is False

    def test_meio_da_janela_libera(
        self, config_padrao: ConfiguracaoHorario
    ) -> None:
        gate = _criar_gate(config_padrao, hora=13, minuto=30)
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is True
        assert resultado.deve_fechar_posicoes is False

    def test_ultimo_minuto_antes_fim_libera(
        self, config_padrao: ConfiguracaoHorario
    ) -> None:
        gate = _criar_gate(config_padrao, hora=16, minuto=59)
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is True
        assert resultado.deve_fechar_posicoes is False


class TestForaDoHorario:
    """Fora da janela, deve bloquear abertura."""

    def test_antes_do_inicio_bloqueia(
        self, config_padrao: ConfiguracaoHorario
    ) -> None:
        gate = _criar_gate(config_padrao, hora=8, minuto=59)
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is False
        assert resultado.deve_fechar_posicoes is False

    def test_apos_fim_bloqueia_abertura(
        self, config_padrao: ConfiguracaoHorario
    ) -> None:
        gate = _criar_gate(config_padrao, hora=17, minuto=1)
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is False

    def test_exatamente_no_fim_bloqueia(
        self, config_padrao: ConfiguracaoHorario
    ) -> None:
        gate = _criar_gate(config_padrao, hora=17, minuto=0)
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is False

    def test_madrugada_bloqueia(
        self, config_padrao: ConfiguracaoHorario
    ) -> None:
        gate = _criar_gate(config_padrao, hora=0, minuto=0)
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is False


class TestFecharPosicoes:
    """Sinalizar fechamento de posicoes quando necessario."""

    def test_fechar_posicao_no_fim_true(
        self, config_padrao: ConfiguracaoHorario
    ) -> None:
        """Apos hora_fim com fechar_posicao_no_fim=True deve sinalizar fechamento."""
        gate = _criar_gate(config_padrao, hora=17, minuto=5)
        resultado = gate.verificar()
        assert resultado.deve_fechar_posicoes is True

    def test_fechar_posicao_no_fim_false_nao_sinaliza(self) -> None:
        """fechar_posicao_no_fim=False nao sinaliza fechamento mesmo apos fim."""
        config = ConfiguracaoHorario(
            hora_inicio=time(9, 0),
            hora_fim=time(17, 0),
            bloquear_abertura_apos_fim=True,
            fechar_posicao_no_fim=False,
        )
        gate = _criar_gate(config, hora=17, minuto=5)
        resultado = gate.verificar()
        assert resultado.deve_fechar_posicoes is False

    def test_antes_do_inicio_nao_sinaliza_fechamento(
        self, config_padrao: ConfiguracaoHorario
    ) -> None:
        """Antes do inicio nao deve sinalizar fechamento."""
        gate = _criar_gate(config_padrao, hora=8, minuto=0)
        resultado = gate.verificar()
        assert resultado.deve_fechar_posicoes is False

    def test_bloquear_abertura_false_dentro_do_horario(self) -> None:
        """bloquear_abertura_apos_fim=False: apos hora_fim ainda libera abertura."""
        config = ConfiguracaoHorario(
            hora_inicio=time(9, 0),
            hora_fim=time(17, 0),
            bloquear_abertura_apos_fim=False,
            fechar_posicao_no_fim=False,
        )
        gate = _criar_gate(config, hora=18, minuto=0)
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is True


class TestResultadoHorario:
    """Testes do dataclass ResultadoHorario."""

    def test_campos_resultado(self, config_padrao: ConfiguracaoHorario) -> None:
        gate = _criar_gate(config_padrao, hora=12, minuto=0)
        resultado = gate.verificar()
        assert isinstance(resultado, ResultadoHorario)
        assert isinstance(resultado.horario_atual, time)
        assert isinstance(resultado.motivo, str)

    def test_motivo_menciona_horario(
        self, config_padrao: ConfiguracaoHorario
    ) -> None:
        gate = _criar_gate(config_padrao, hora=8, minuto=30)
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is False
        assert len(resultado.motivo) > 0


class TestConfiguracaoHorario:
    """Testes de validacao do value object ConfiguracaoHorario."""

    def test_fim_antes_inicio_invalido(self) -> None:
        with pytest.raises(ValueError):
            ConfiguracaoHorario(
                hora_inicio=time(17, 0),
                hora_fim=time(9, 0),
            )

    def test_fim_igual_inicio_invalido(self) -> None:
        with pytest.raises(ValueError):
            ConfiguracaoHorario(
                hora_inicio=time(9, 0),
                hora_fim=time(9, 0),
            )
