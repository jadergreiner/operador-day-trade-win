"""Testes unitarios para GateCalendarioEconomico."""

from datetime import datetime, timedelta, timezone

import pytest

from src.application.gerenciamento_risco.controles_globais.gate_calendario_economico import (
    GateCalendarioEconomico,
    ResultadoCalendario,
)
from src.domain.value_objects.risco_externo import EventoCalendario
from src.infrastructure.providers.calendario_economico_provider import (
    CalendarioEconomicoNoop,
    ICalendarioEconomicoProvider,
)


def _ts_daqui(minutos: float) -> datetime:
    return datetime.now(tz=timezone.utc) + timedelta(minutes=minutos)


def _ts_ha(minutos: float) -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(minutes=minutos)


def _evento(nome: str, minutos_futuro: float) -> EventoCalendario:
    return EventoCalendario(
        nome=nome,
        timestamp_evento=_ts_daqui(minutos_futuro),
        minutos_antes_fechar=5,
        minutos_apos_abrir=2,
    )


class ProviderFixo(ICalendarioEconomicoProvider):
    """Provider de teste com lista de eventos pre-configurada."""

    def __init__(self, eventos: list[EventoCalendario]) -> None:
        self._eventos = eventos

    def obter_proximos_eventos(
        self, janela_minutos: int = 60
    ) -> list[EventoCalendario]:
        agora = datetime.now(tz=timezone.utc)
        return [
            e for e in self._eventos
            if agora <= e.timestamp_evento <= agora + timedelta(minutes=janela_minutos)
        ]

    def obter_eventos_recentes(
        self, janela_passado_minutos: int = 10
    ) -> list[EventoCalendario]:
        agora = datetime.now(tz=timezone.utc)
        limite = agora - timedelta(minutes=janela_passado_minutos)
        return [
            e for e in self._eventos
            if limite <= e.timestamp_evento < agora
        ]


class ProviderComErro(ICalendarioEconomicoProvider):
    """Provider que sempre lanca excecao (para testar fail-open)."""

    def obter_proximos_eventos(
        self, janela_minutos: int = 60
    ) -> list[EventoCalendario]:
        raise ConnectionError("API indisponivel")

    def obter_eventos_recentes(
        self, janela_passado_minutos: int = 10
    ) -> list[EventoCalendario]:
        raise ConnectionError("API indisponivel")


@pytest.fixture
def gate_noop() -> GateCalendarioEconomico:
    return GateCalendarioEconomico(provider=CalendarioEconomicoNoop())


class TestSemEventos:
    """Sem eventos proximos, deve liberar abertura."""

    def test_provider_vazio_libera(
        self, gate_noop: GateCalendarioEconomico
    ) -> None:
        resultado = gate_noop.verificar()
        assert resultado.aprovado_abertura is True
        assert resultado.deve_fechar_posicoes is False
        assert resultado.eventos_proximos == []

    def test_evento_distante_libera(self) -> None:
        """Evento em 60 min nao bloqueia (alem da janela padrao de 5 min)."""
        provider = ProviderFixo([_evento("COPOM", minutos_futuro=60)])
        gate = GateCalendarioEconomico(provider=provider)
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is True


class TestComEventoProximo:
    """Com evento dentro da janela, deve bloquear e sinalizar fechamento."""

    def test_evento_em_4min_bloqueia(self) -> None:
        """Evento em 4 min (< minutos_antes_fechar=5) deve bloquear."""
        provider = ProviderFixo([_evento("COPOM", minutos_futuro=4)])
        gate = GateCalendarioEconomico(provider=provider)
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is False
        assert resultado.deve_fechar_posicoes is True
        assert "COPOM" in resultado.eventos_proximos

    def test_evento_em_5min_bloqueia(self) -> None:
        """Exatamente no limite minutos_antes_fechar deve bloquear."""
        provider = ProviderFixo([_evento("FOMC", minutos_futuro=5)])
        gate = GateCalendarioEconomico(provider=provider)
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is False

    def test_motivo_menciona_evento(self) -> None:
        provider = ProviderFixo([_evento("NFP", minutos_futuro=2)])
        gate = GateCalendarioEconomico(provider=provider)
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is False
        assert "NFP" in resultado.motivo or "evento" in resultado.motivo.lower()


class TestAposEvento:
    """Apos evento + janela minutos_apos_abrir, deve liberar."""

    def test_evento_passado_ha_mais_de_2min_libera(self) -> None:
        """Evento que passou ha 3 min (> minutos_apos_abrir=2) libera."""
        evento_passado = EventoCalendario(
            nome="CPI",
            timestamp_evento=_ts_ha(3),
            minutos_antes_fechar=5,
            minutos_apos_abrir=2,
        )
        provider = ProviderFixo([evento_passado])
        gate = GateCalendarioEconomico(
            provider=provider,
            minutos_antes_fechar=5,
            minutos_apos_abrir=2,
        )
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is True

    def test_evento_passado_ha_menos_de_2min_bloqueia(self) -> None:
        """Evento que passou ha 1 min (< minutos_apos_abrir=2) ainda bloqueia."""
        evento_passado = EventoCalendario(
            nome="GDP",
            timestamp_evento=_ts_ha(1),
            minutos_antes_fechar=5,
            minutos_apos_abrir=2,
        )
        provider = ProviderFixo([evento_passado])
        gate = GateCalendarioEconomico(
            provider=provider,
            minutos_antes_fechar=5,
            minutos_apos_abrir=2,
        )
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is False


class TestFailOpen:
    """Provider com erro deve retornar fail-open (libera)."""

    def test_provider_com_erro_libera_fail_open(self) -> None:
        gate = GateCalendarioEconomico(provider=ProviderComErro())
        resultado = gate.verificar()
        assert resultado.aprovado_abertura is True
        assert resultado.deve_fechar_posicoes is False


class TestResultadoCalendario:
    """Testes do dataclass ResultadoCalendario."""

    def test_campos_resultado(
        self, gate_noop: GateCalendarioEconomico
    ) -> None:
        resultado = gate_noop.verificar()
        assert isinstance(resultado, ResultadoCalendario)
        assert isinstance(resultado.eventos_proximos, list)
        assert isinstance(resultado.motivo, str)
