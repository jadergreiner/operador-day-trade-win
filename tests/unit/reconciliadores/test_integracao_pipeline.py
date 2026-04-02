"""
Testes de integracao do pipeline ROADMAP-MICRO-03.

Cobrem o fluxo completo:
    AC5.9 nao recebe resultado DESCONHECIDO
    Pipeline completo -> zero desconhecidos apos sessao
"""

import sqlite3
import pytest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

from src.application.reconciliadores import (
    UnknownResultDetector,
    TradeOutcomeReconciler,
    ReconcileStatus,
    MT5SyncValidator,
    SyncStatus,
)
from src.infrastructure.repositories.fechamento_repository import (
    IFechamentoRepository,
    JsonFechamentoRepository,
)


def _repo_com_dados(
    tmp_path: Path,
    tickets_sem_resultado: List[int],
    agent_id: str = "rl_5000",
) -> JsonFechamentoRepository:
    """Cria JsonFechamentoRepository populado com fechamentos sem resultado."""
    import json

    dados = []
    for t in tickets_sem_resultado:
        dados.append(
            {
                "ticket": t,
                "agent_id": agent_id,
                "magic_number": 234500,
                "resultado": None,
                "pnl_reais": 50.0,
                "pnl_pct": 0.10,
            }
        )

    arquivo = tmp_path / f"historico_fechamentos_{agent_id}.json"
    arquivo.write_text(json.dumps(dados))
    return JsonFechamentoRepository(agent_id=agent_id, data_dir=tmp_path)


def test_integracao_ac5_9_nao_recebe_desconhecido(tmp_path: Path) -> None:
    """Apos reconciliar_ordem, nenhum ticket permanece com resultado None."""
    agent_id = "rl_5000"
    tickets = [5001, 5002, 5003]

    repo = _repo_com_dados(tmp_path, tickets, agent_id=agent_id)
    mt5 = MagicMock()
    mt5.obter_pnl_fechado.return_value = 40.0

    reconciler = TradeOutcomeReconciler(fechamento_repo=repo, mt5_adapter=mt5)

    for ticket in tickets:
        result = reconciler.reconciliar_ordem(ticket=ticket, agent_id=agent_id)
        assert result.resultado is not None, (
            f"ticket={ticket} ainda DESCONHECIDO apos reconciliacao"
        )
        assert result.resultado in {"WIN", "LOSS", "BREAKEVEN"}

    # Verificar que nao ha mais registros sem resultado
    sem_resultado = repo.listar_sem_resultado(agent_id=agent_id, magic_number=None)
    assert len(sem_resultado) == 0, (
        f"Ainda ha {len(sem_resultado)} tickets sem resultado"
    )


def test_integracao_pipeline_completo_zero_desconhecido(tmp_path: Path) -> None:
    """Fluxo completo: detectar -> reconciliar -> validar -> SINCRONIZADO."""
    agent_id = "rl_5000"
    magic_number = 234500
    tickets = [6001, 6002]

    repo = _repo_com_dados(tmp_path, tickets, agent_id=agent_id)
    mt5 = MagicMock()
    mt5.obter_pnl_fechado.return_value = 30.0
    mt5.contar_fechamentos_sem_resultado.return_value = 0

    detector = UnknownResultDetector()
    reconciler = TradeOutcomeReconciler(fechamento_repo=repo, mt5_adapter=mt5)
    validator = MT5SyncValidator(fechamento_repo=repo, mt5_adapter=mt5)

    # Etapa 1: detectar lacunas (devem existir 2 tickets sem resultado)
    ordens_locais = [
        {"ticket": t, "magic_number": magic_number, "resultado": None}
        for t in tickets
    ]
    lacunas = detector.detectar_lacunas(
        agent_id=agent_id,
        magic_number=magic_number,
        ordens_locais=ordens_locais,
        ordens_mt5=[],
    )
    assert len(lacunas) == len(tickets)

    # Etapa 2: reconciliar todos
    for ticket in tickets:
        result = reconciler.reconciliar_ordem(ticket=ticket, agent_id=agent_id)
        assert result.status in {
            ReconcileStatus.RECONCILIADO_LOCAL,
            ReconcileStatus.RECONCILIADO_MT5,
        }

    # Etapa 3: validar sincronizacao -> SINCRONIZADO (0 pendentes locais, 0 no MT5)
    report = validator.validar_sincronizacao(session_id="integ-test", agent_id=agent_id)
    assert report.status == SyncStatus.SINCRONIZADO, (
        f"Pipeline incompleto: delta={report.delta}"
    )
