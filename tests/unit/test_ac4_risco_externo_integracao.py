"""
Teste de integracao: AC4 DecisionFilter + GerenciadorRiscoExterno.

Verifica que o DecisionFilter rejeita corretamente quando o
GerenciadorRiscoExterno bloqueia, e aprova quando todos os gates passam.
"""

from datetime import datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from src.application.ac4_decision_filter import DecisionFilter, DecisionType
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

_TZ_SP = ZoneInfo("America/Sao_Paulo")


def _criar_gerenciador_risco(tmp_path: Path, hora: int = 11) -> GerenciadorRiscoExterno:
    agora = datetime(2026, 3, 24, hora, 0, tzinfo=_TZ_SP)
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


_SINAL: dict[str, Any] = {
    "signal_id": "INT_001",
    "entry_price": 130_000.0,
    "stop_loss": 129_800.0,
    "volume": 1.0,
    "outcome_trade_id": None,
}


class TestAC4SemGerenciadorRisco:
    """AC4 sem GerenciadorRiscoExterno deve funcionar normalmente."""

    def test_sem_gerenciador_retorna_execute(self, tmp_path: Path) -> None:
        filtro = DecisionFilter(
            db_path=str(tmp_path / "test.db"),
            gerenciador_risco=None,
        )
        decisao = filtro.make_decision(_SINAL)
        assert decisao.decision_type == DecisionType.EXECUTE


class TestAC4ComGerenciadorRisco:
    """AC4 com GerenciadorRiscoExterno integrado."""

    def test_todos_gates_ok_retorna_execute(self, tmp_path: Path) -> None:
        gerenciador = _criar_gerenciador_risco(tmp_path, hora=11)
        filtro = DecisionFilter(
            db_path=str(tmp_path / "test.db"),
            gerenciador_risco=gerenciador,
            agent_id="agente_teste",
        )
        decisao = filtro.make_decision(_SINAL)
        assert decisao.decision_type == DecisionType.EXECUTE

    def test_cooldown_ativo_retorna_reject(self, tmp_path: Path) -> None:
        gerenciador = _criar_gerenciador_risco(tmp_path, hora=11)
        gerenciador._gerenciador_cooldown.registrar_fechamento("agente_teste")

        filtro = DecisionFilter(
            db_path=str(tmp_path / "test.db"),
            gerenciador_risco=gerenciador,
            agent_id="agente_teste",
        )
        decisao = filtro.make_decision(_SINAL)
        assert decisao.decision_type == DecisionType.REJECT
        assert "COOLDOWN" in decisao.justification

    def test_fora_do_horario_retorna_reject(self, tmp_path: Path) -> None:
        gerenciador = _criar_gerenciador_risco(tmp_path, hora=18)
        filtro = DecisionFilter(
            db_path=str(tmp_path / "test.db"),
            gerenciador_risco=gerenciador,
            agent_id="agente_teste",
        )
        decisao = filtro.make_decision(_SINAL)
        assert decisao.decision_type == DecisionType.REJECT
        assert "HORARIO" in decisao.justification

    def test_justificativa_menciona_gate_reprovado(self, tmp_path: Path) -> None:
        gerenciador = _criar_gerenciador_risco(tmp_path, hora=18)
        filtro = DecisionFilter(
            db_path=str(tmp_path / "test.db"),
            gerenciador_risco=gerenciador,
            agent_id="agente_teste",
        )
        decisao = filtro.make_decision(_SINAL)
        assert "Gate externo" in decisao.justification or "HORARIO" in decisao.justification
