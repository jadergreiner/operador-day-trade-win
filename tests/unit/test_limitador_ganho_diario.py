"""Testes unitarios para LimitadorGanhoDiario."""

import pytest

from src.application.gerenciamento_risco.controles_globais.limitador_ganho_diario import (
    LimitadorGanhoDiario,
    ResultadoGanhoDiario,
)
from src.domain.value_objects.risco_externo import ConfiguracaoGanhoDiario
from src.infrastructure.repositories.repositorio_ganho_diario import (
    RepositorioGanhoDiarioEmMemoria,
)

_DATA_HOJE = "2026-03-24"
_DATA_ONTEM = "2026-03-23"


@pytest.fixture
def repositorio() -> RepositorioGanhoDiarioEmMemoria:
    return RepositorioGanhoDiarioEmMemoria()


@pytest.fixture
def config_1000() -> ConfiguracaoGanhoDiario:
    return ConfiguracaoGanhoDiario(
        limite_ganho_diario_reais=1000.0, congelar_novas_entradas=True
    )


@pytest.fixture
def limitador(
    config_1000: ConfiguracaoGanhoDiario,
    repositorio: RepositorioGanhoDiarioEmMemoria,
) -> LimitadorGanhoDiario:
    return LimitadorGanhoDiario(
        configuracao=config_1000, repositorio=repositorio
    )


class TestVerificarLimite:
    """Testes de verificacao do limite diario."""

    def test_sem_operacoes_libera(
        self, limitador: LimitadorGanhoDiario
    ) -> None:
        resultado = limitador.verificar_limite(data_pregao=_DATA_HOJE)
        assert resultado.aprovado is True
        assert resultado.ganho_total_hoje_reais == 0.0

    def test_ganho_abaixo_limite_libera(
        self,
        limitador: LimitadorGanhoDiario,
        repositorio: RepositorioGanhoDiarioEmMemoria,
    ) -> None:
        repositorio.registrar_pnl(_DATA_HOJE, "agente_1", 500.0)
        resultado = limitador.verificar_limite(data_pregao=_DATA_HOJE)
        assert resultado.aprovado is True
        assert resultado.ganho_total_hoje_reais == 500.0

    def test_ganho_exatamente_no_limite_libera(
        self,
        limitador: LimitadorGanhoDiario,
        repositorio: RepositorioGanhoDiarioEmMemoria,
    ) -> None:
        repositorio.registrar_pnl(_DATA_HOJE, "agente_1", 1000.0)
        resultado = limitador.verificar_limite(data_pregao=_DATA_HOJE)
        assert resultado.aprovado is True

    def test_ganho_acima_limite_bloqueia(
        self,
        limitador: LimitadorGanhoDiario,
        repositorio: RepositorioGanhoDiarioEmMemoria,
    ) -> None:
        repositorio.registrar_pnl(_DATA_HOJE, "agente_1", 1001.0)
        resultado = limitador.verificar_limite(data_pregao=_DATA_HOJE)
        assert resultado.aprovado is False
        assert "limite" in resultado.motivo.lower() or "ganho" in resultado.motivo.lower()

    def test_soma_todos_agentes(
        self,
        limitador: LimitadorGanhoDiario,
        repositorio: RepositorioGanhoDiarioEmMemoria,
    ) -> None:
        """Limite deve considerar ganho total de todos os agentes."""
        repositorio.registrar_pnl(_DATA_HOJE, "agente_rl_5000", 600.0)
        repositorio.registrar_pnl(_DATA_HOJE, "agente_direto", 500.0)
        resultado = limitador.verificar_limite(data_pregao=_DATA_HOJE)
        assert resultado.aprovado is False
        assert resultado.ganho_total_hoje_reais == 1100.0

    def test_ganho_ontem_nao_interfere_hoje(
        self,
        limitador: LimitadorGanhoDiario,
        repositorio: RepositorioGanhoDiarioEmMemoria,
    ) -> None:
        """Ganhos de dias anteriores nao devem influenciar o limite de hoje."""
        repositorio.registrar_pnl(_DATA_ONTEM, "agente_1", 2000.0)
        resultado = limitador.verificar_limite(data_pregao=_DATA_HOJE)
        assert resultado.aprovado is True
        assert resultado.ganho_total_hoje_reais == 0.0

    def test_congelar_false_retorna_aprovado_mesmo_acima(
        self,
        repositorio: RepositorioGanhoDiarioEmMemoria,
    ) -> None:
        """congelar_novas_entradas=False: apenas alerta, nao bloqueia."""
        config = ConfiguracaoGanhoDiario(
            limite_ganho_diario_reais=1000.0, congelar_novas_entradas=False
        )
        limitador = LimitadorGanhoDiario(
            configuracao=config, repositorio=repositorio
        )
        repositorio.registrar_pnl(_DATA_HOJE, "agente_1", 1500.0)
        resultado = limitador.verificar_limite(data_pregao=_DATA_HOJE)
        assert resultado.aprovado is True

    def test_percentual_atingido_calculado(
        self,
        limitador: LimitadorGanhoDiario,
        repositorio: RepositorioGanhoDiarioEmMemoria,
    ) -> None:
        repositorio.registrar_pnl(_DATA_HOJE, "agente_1", 750.0)
        resultado = limitador.verificar_limite(data_pregao=_DATA_HOJE)
        assert abs(resultado.percentual_atingido - 75.0) < 0.1

    def test_resultado_contem_limite(
        self,
        limitador: LimitadorGanhoDiario,
        repositorio: RepositorioGanhoDiarioEmMemoria,
    ) -> None:
        resultado = limitador.verificar_limite(data_pregao=_DATA_HOJE)
        assert resultado.limite_reais == 1000.0


class TestRegistrarResultado:
    """Testes de registro de resultado de operacao."""

    def test_registrar_aumenta_ganho_total(
        self,
        limitador: LimitadorGanhoDiario,
    ) -> None:
        limitador.registrar_resultado("agente_1", 300.0, data_pregao=_DATA_HOJE)
        resultado = limitador.verificar_limite(data_pregao=_DATA_HOJE)
        assert resultado.ganho_total_hoje_reais == 300.0

    def test_registrar_perda_diminui_total(
        self,
        limitador: LimitadorGanhoDiario,
    ) -> None:
        limitador.registrar_resultado("agente_1", -200.0, data_pregao=_DATA_HOJE)
        resultado = limitador.verificar_limite(data_pregao=_DATA_HOJE)
        assert resultado.ganho_total_hoje_reais == -200.0

    def test_registrar_com_ticket(
        self,
        limitador: LimitadorGanhoDiario,
        repositorio: RepositorioGanhoDiarioEmMemoria,
    ) -> None:
        limitador.registrar_resultado(
            "agente_1", 500.0, ticket=12345, data_pregao=_DATA_HOJE
        )
        assert repositorio.consultar_total_dia(_DATA_HOJE) == 500.0


class TestResultadoGanhoDiario:
    """Testes do dataclass ResultadoGanhoDiario."""

    def test_campos_resultado(self) -> None:
        resultado = ResultadoGanhoDiario(
            aprovado=False,
            ganho_total_hoje_reais=1200.0,
            limite_reais=1000.0,
            percentual_atingido=120.0,
            motivo="Limite de ganho diario atingido",
        )
        assert resultado.aprovado is False
        assert resultado.ganho_total_hoje_reais == 1200.0
        assert resultado.percentual_atingido == 120.0
