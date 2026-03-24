"""Testes unitarios para GerenciadorRiscoExterno (facade)."""

from datetime import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.application.gerenciamento_risco.controles_agente.gate_unica_ordem import (
    GateUnicaOrdemPorAgente,
)
from src.application.gerenciamento_risco.controles_agente.gerenciador_cooldown import (
    GerenciadorCooldown,
)
from src.application.gerenciamento_risco.controles_agente.validador_sl_maximo import (
    ValidadorSLMaximo,
)
from src.application.gerenciamento_risco.controles_globais.gate_calendario_economico import (
    GateCalendarioEconomico,
)
from src.application.gerenciamento_risco.controles_globais.gate_horario_operacao import (
    GateHorarioOperacao,
)
from src.application.gerenciamento_risco.controles_globais.limitador_ganho_diario import (
    LimitadorGanhoDiario,
)
from src.application.gerenciamento_risco.gerenciador_risco_externo import (
    GerenciadorRiscoExterno,
    ResultadoAvaliacaoRisco,
)
from src.domain.value_objects.risco_externo import (
    ConfiguracaoCooldown,
    ConfiguracaoGanhoDiario,
    ConfiguracaoHorario,
    ConfiguracaoSLMaximo,
)
from src.infrastructure.providers.calendario_economico_provider import (
    CalendarioEconomicoNoop,
)
from src.infrastructure.repositories.repositorio_ganho_diario import (
    RepositorioGanhoDiarioEmMemoria,
)


def _criar_gerenciador(
    tmp_path: Path,
    hora_atual: int = 11,
) -> GerenciadorRiscoExterno:
    """Cria GerenciadorRiscoExterno totalmente configurado para testes."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    tz_sp = ZoneInfo("America/Sao_Paulo")
    agora = datetime(2026, 3, 24, hora_atual, 0, 0, tzinfo=tz_sp)

    return GerenciadorRiscoExterno(
        gate_unica_ordem=GateUnicaOrdemPorAgente(outputs_dir=tmp_path),
        gerenciador_cooldown=GerenciadorCooldown(
            configuracao=ConfiguracaoCooldown(periodo_espera_segundos=60),
            outputs_dir=tmp_path,
        ),
        validador_sl=ValidadorSLMaximo(
            configuracao=ConfiguracaoSLMaximo(
                perda_maxima_por_operacao_reais=500.0
            )
        ),
        gate_horario=GateHorarioOperacao(
            configuracao=ConfiguracaoHorario(
                hora_inicio=time(9, 0), hora_fim=time(17, 0)
            ),
            _agora=lambda: agora,
        ),
        gate_calendario=GateCalendarioEconomico(
            provider=CalendarioEconomicoNoop()
        ),
        limitador_ganho=LimitadorGanhoDiario(
            configuracao=ConfiguracaoGanhoDiario(
                limite_ganho_diario_reais=2000.0
            ),
            repositorio=RepositorioGanhoDiarioEmMemoria(),
        ),
    )


_SINAL_VALIDO: dict[str, Any] = {
    "signal_id": "sig_001",
    "entry_price": 130_000.0,
    "stop_loss": 129_800.0,  # 200 pts * 1 * 0.20 = R$40
    "volume": 1.0,
}

_SINAL_SEM_SL: dict[str, Any] = {
    "signal_id": "sig_002",
    "entry_price": 0.0,
    "stop_loss": 0.0,
    "volume": 1.0,
}


class TestTodosGatesAprovados:
    """Cenario feliz: todos os gates devem aprovar."""

    def test_todos_aprovados_retorna_aprovado(self, tmp_path: Path) -> None:
        gerenciador = _criar_gerenciador(tmp_path)
        resultado = gerenciador.avaliar_todos("agente_1", _SINAL_VALIDO)
        assert resultado.aprovado is True
        assert resultado.primeiro_gate_reprovado is None
        assert len(resultado.gates_avaliados) == 6

    def test_motivo_todos_aprovados(self, tmp_path: Path) -> None:
        gerenciador = _criar_gerenciador(tmp_path)
        resultado = gerenciador.avaliar_todos("agente_1", _SINAL_VALIDO)
        assert "aprovaram" in resultado.motivo.lower() or "gates" in resultado.motivo.lower()


class TestGateUnicaOrdem:
    """Gate 1: posicao aberta deve bloquear."""

    def test_posicao_aberta_bloqueia(self, tmp_path: Path) -> None:
        import json
        posicao = {
            "session_id": "agente_1_sess",
            "owner": "agente_1",
            "aberta": True,
            "ticket": 123,
            "lado": "BUY",
            "quantidade": 1,
        }
        (tmp_path / "agente_posicao_agente_1_sess.json").write_text(
            json.dumps(posicao)
        )
        gerenciador = _criar_gerenciador(tmp_path)
        resultado = gerenciador.avaliar_todos("agente_1", _SINAL_VALIDO)
        assert resultado.aprovado is False
        assert resultado.primeiro_gate_reprovado == "UNICA_ORDEM"
        assert len(resultado.gates_avaliados) == 1  # fail-fast: parou no gate 1


class TestGateCooldown:
    """Gate 2: cooldown ativo deve bloquear."""

    def test_cooldown_ativo_bloqueia(self, tmp_path: Path) -> None:
        gerenciador = _criar_gerenciador(tmp_path)
        gerenciador._gerenciador_cooldown.registrar_fechamento("agente_2")
        resultado = gerenciador.avaliar_todos("agente_2", _SINAL_VALIDO)
        assert resultado.aprovado is False
        assert resultado.primeiro_gate_reprovado == "COOLDOWN"
        assert len(resultado.gates_avaliados) == 2  # parou no gate 2


class TestGateSLMaximo:
    """Gate 3: SL acima do limite deve bloquear."""

    def test_sl_acima_do_limite_bloqueia(self, tmp_path: Path) -> None:
        sinal_sl_alto: dict[str, Any] = {
            "signal_id": "sig_sl",
            "entry_price": 130_000.0,
            "stop_loss": 127_000.0,  # 3000 pts * 1 * 0.20 = R$600 > R$500
            "volume": 1.0,
        }
        gerenciador = _criar_gerenciador(tmp_path)
        resultado = gerenciador.avaliar_todos("agente_3", sinal_sl_alto)
        assert resultado.aprovado is False
        assert resultado.primeiro_gate_reprovado == "SL_MAXIMO"

    def test_sem_dados_sl_libera(self, tmp_path: Path) -> None:
        gerenciador = _criar_gerenciador(tmp_path)
        resultado = gerenciador.avaliar_todos("agente_3", _SINAL_SEM_SL)
        assert resultado.aprovado is True


class TestGateHorario:
    """Gate 4: fora do horario deve bloquear."""

    def test_fora_do_horario_bloqueia(self, tmp_path: Path) -> None:
        gerenciador = _criar_gerenciador(tmp_path, hora_atual=18)
        resultado = gerenciador.avaliar_todos("agente_4", _SINAL_VALIDO)
        assert resultado.aprovado is False
        assert resultado.primeiro_gate_reprovado == "HORARIO"


class TestGateGanhoDiario:
    """Gate 6: ganho diario atingido deve bloquear."""

    def test_ganho_diario_atingido_bloqueia(self, tmp_path: Path) -> None:
        repositorio = RepositorioGanhoDiarioEmMemoria()
        repositorio.registrar_pnl("2026-03-24", "agente_6", 2500.0)

        from datetime import datetime
        from zoneinfo import ZoneInfo

        tz_sp = ZoneInfo("America/Sao_Paulo")
        agora = datetime(2026, 3, 24, 11, 0, 0, tzinfo=tz_sp)

        gerenciador = GerenciadorRiscoExterno(
            gate_unica_ordem=GateUnicaOrdemPorAgente(outputs_dir=tmp_path),
            gerenciador_cooldown=GerenciadorCooldown(
                configuracao=ConfiguracaoCooldown(periodo_espera_segundos=60),
                outputs_dir=tmp_path,
            ),
            validador_sl=ValidadorSLMaximo(
                configuracao=ConfiguracaoSLMaximo(
                    perda_maxima_por_operacao_reais=500.0
                )
            ),
            gate_horario=GateHorarioOperacao(
                configuracao=ConfiguracaoHorario(
                    hora_inicio=time(9, 0), hora_fim=time(17, 0)
                ),
                _agora=lambda: agora,
            ),
            gate_calendario=GateCalendarioEconomico(
                provider=CalendarioEconomicoNoop()
            ),
            limitador_ganho=LimitadorGanhoDiario(
                configuracao=ConfiguracaoGanhoDiario(
                    limite_ganho_diario_reais=2000.0
                ),
                repositorio=repositorio,
            ),
        )

        resultado = gerenciador.avaliar_todos("agente_6", _SINAL_VALIDO)
        assert resultado.aprovado is False
        assert resultado.primeiro_gate_reprovado == "GANHO_DIARIO"


class TestNotificarFechamento:
    """Testes do metodo notificar_fechamento."""

    def test_notificacao_inicia_cooldown(self, tmp_path: Path) -> None:
        gerenciador = _criar_gerenciador(tmp_path)
        # Antes: sem cooldown
        assert gerenciador.avaliar_todos("agente_1", _SINAL_VALIDO).aprovado
        # Notificar fechamento
        gerenciador.notificar_fechamento("agente_1", pnl_reais=150.0)
        # Apos: cooldown ativo
        resultado = gerenciador.avaliar_todos("agente_1", _SINAL_VALIDO)
        assert resultado.aprovado is False
        assert resultado.primeiro_gate_reprovado == "COOLDOWN"

    def test_notificacao_registra_pnl(self, tmp_path: Path) -> None:
        repositorio = RepositorioGanhoDiarioEmMemoria()
        from datetime import datetime
        from zoneinfo import ZoneInfo

        tz_sp = ZoneInfo("America/Sao_Paulo")
        agora = datetime(2026, 3, 24, 11, 0, 0, tzinfo=tz_sp)

        gerenciador = GerenciadorRiscoExterno(
            gate_unica_ordem=GateUnicaOrdemPorAgente(outputs_dir=tmp_path),
            gerenciador_cooldown=GerenciadorCooldown(
                configuracao=ConfiguracaoCooldown(periodo_espera_segundos=60),
                outputs_dir=tmp_path,
            ),
            validador_sl=ValidadorSLMaximo(
                configuracao=ConfiguracaoSLMaximo(
                    perda_maxima_por_operacao_reais=500.0
                )
            ),
            gate_horario=GateHorarioOperacao(
                configuracao=ConfiguracaoHorario(
                    hora_inicio=time(9, 0), hora_fim=time(17, 0)
                ),
                _agora=lambda: agora,
            ),
            gate_calendario=GateCalendarioEconomico(
                provider=CalendarioEconomicoNoop()
            ),
            limitador_ganho=LimitadorGanhoDiario(
                configuracao=ConfiguracaoGanhoDiario(
                    limite_ganho_diario_reais=2000.0
                ),
                repositorio=repositorio,
            ),
        )
        from datetime import date
        gerenciador.notificar_fechamento("agente_1", pnl_reais=300.0)
        assert repositorio.consultar_total_dia(date.today().isoformat()) == 300.0


class TestDeveFecharPosicoesAgora:
    """Testes para deve_fechar_posicoes_agora."""

    def test_dentro_do_horario_nao_fechar(self, tmp_path: Path) -> None:
        gerenciador = _criar_gerenciador(tmp_path, hora_atual=11)
        assert gerenciador.deve_fechar_posicoes_agora() is False

    def test_fora_do_horario_deve_fechar(self, tmp_path: Path) -> None:
        gerenciador = _criar_gerenciador(tmp_path, hora_atual=18)
        assert gerenciador.deve_fechar_posicoes_agora() is True


class TestResultadoAvaliacaoRisco:
    """Testes do dataclass ResultadoAvaliacaoRisco."""

    def test_campos_resultado(self) -> None:
        resultado = ResultadoAvaliacaoRisco(
            aprovado=False,
            primeiro_gate_reprovado="COOLDOWN",
            motivo="Cooldown ativo",
        )
        assert resultado.aprovado is False
        assert resultado.primeiro_gate_reprovado == "COOLDOWN"
        assert resultado.gates_avaliados == []
