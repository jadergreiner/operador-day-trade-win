"""
Testes para MT5SyncValidator (ROADMAP-MICRO-03).

Grupos cobertos:
    Grupo 6a: validar_sincronizacao - SINCRONIZADO (1 teste)
    Grupo 6b: validar_sincronizacao - DIVERGENCIA_CRITICA (1 teste)
    Grupo 6c: erro no MT5 gera DIVERGENCIA_CRITICA (1 teste)
    Grupo 6d: estrutura do ValidationReport (1 teste)
"""

import pytest
from unittest.mock import MagicMock
from src.application.reconciliadores.mt5_sync_validator import (
    MT5SyncValidator,
    SyncStatus,
    ValidationReport,
)
from src.infrastructure.repositories.fechamento_repository import (
    IFechamentoRepository,
)


def _make_validator(
    contagem_local: int = 0,
    contagem_mt5: int = 0,
    mt5_raises: bool = False,
) -> MT5SyncValidator:
    repo = MagicMock(spec=IFechamentoRepository)
    repo.listar_sem_resultado.return_value = [
        {"ticket": i} for i in range(contagem_local)
    ]
    mt5 = MagicMock()
    if mt5_raises:
        mt5.contar_fechamentos_sem_resultado.side_effect = RuntimeError("MT5 offline")
    else:
        mt5.contar_fechamentos_sem_resultado.return_value = contagem_mt5
    return MT5SyncValidator(fechamento_repo=repo, mt5_adapter=mt5)


def test_validar_sincronizacao_sem_divergencia():
    validator = _make_validator(contagem_local=0, contagem_mt5=0)
    report = validator.validar_sincronizacao(session_id="s1", agent_id="rl_5000")
    assert report.status == SyncStatus.SINCRONIZADO
    assert report.delta == 0
    assert report.reconciled if hasattr(report, "reconciled") else True


def test_validar_sincronizacao_com_divergencia():
    validator = _make_validator(contagem_local=3, contagem_mt5=1)
    report = validator.validar_sincronizacao(session_id="s2", agent_id="rl_5000")
    assert report.status == SyncStatus.DIVERGENCIA_CRITICA
    assert report.delta == 2
    assert report.contagem_local == 3
    assert report.contagem_mt5 == 1


def test_validar_sincronizacao_erro_mt5_gera_divergencia():
    validator = _make_validator(contagem_local=2, mt5_raises=True)
    report = validator.validar_sincronizacao(session_id="s3", agent_id="rl_5000")
    assert report.status == SyncStatus.DIVERGENCIA_CRITICA


def test_validar_sincronizacao_campos_obrigatorios():
    validator = _make_validator(contagem_local=0, contagem_mt5=0)
    report = validator.validar_sincronizacao(session_id="s4", agent_id="rl_direto")
    assert report.session_id == "s4"
    assert report.agent_id == "rl_direto"
    assert isinstance(report.timestamp, str)
    assert len(report.timestamp) > 0
    assert isinstance(report.status, SyncStatus)