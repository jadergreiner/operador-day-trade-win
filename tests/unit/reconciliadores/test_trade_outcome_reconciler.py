"""
Testes para TradeOutcomeReconciler (ROADMAP-MICRO-03).

Grupos cobertos:
    Grupo 5a: _classificar_resultado (4 testes)
    Grupo 5b: reconciliar_ordem - local (3 testes)
    Grupo 5c: reconciliar_ordem - MT5 fallback (3 testes)
    Grupo 5d: reconciliar_ordem - idempotencia e isolamento (3 testes)
    Grupo 5e: gerar_relatorio_sessao (2 testes)
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from src.application.reconciliadores.trade_outcome_reconciler import (
    TradeOutcomeReconciler,
    ReconcileStatus,
    ReconciliationResult,
)
from src.infrastructure.repositories.fechamento_repository import (
    IFechamentoRepository,
)


def _make_reconciler(
    mock_repo: MagicMock | None = None,
    mock_mt5: MagicMock | None = None,
) -> TradeOutcomeReconciler:
    if mock_repo is None:
        repo = MagicMock(spec=IFechamentoRepository)
        repo.obter_resultado_local.return_value = None
        repo.listar_sem_resultado.return_value = []
        repo.atualizar_resultado_fechamento.return_value = True
    else:
        repo = mock_repo
    mt5 = mock_mt5 if mock_mt5 is not None else MagicMock()
    return TradeOutcomeReconciler(fechamento_repo=repo, mt5_adapter=mt5)


# ==================================================================
# Grupo 5a: _classificar_resultado
# ==================================================================


def test_classificar_resultado_win():
    rec = _make_reconciler()
    assert rec._classificar_resultado(0.10) == "WIN"


def test_classificar_resultado_loss():
    rec = _make_reconciler()
    assert rec._classificar_resultado(-0.10) == "LOSS"


def test_classificar_resultado_breakeven_zero():
    rec = _make_reconciler()
    assert rec._classificar_resultado(0.0) == "BREAKEVEN"


def test_classificar_resultado_none_retorna_breakeven():
    rec = _make_reconciler()
    assert rec._classificar_resultado(None) == "BREAKEVEN"


# ==================================================================
# Grupo 5b: reconciliar_ordem - caminho local
# ==================================================================


def test_reconciliar_ordem_via_dado_local():
    repo = MagicMock(spec=IFechamentoRepository)
    repo.obter_resultado_local.return_value = None
    repo.listar_sem_resultado.return_value = [
        {"ticket": 1001, "pnl_pct": 0.08, "pnl_reais": 120.0}
    ]
    repo.atualizar_resultado_fechamento.return_value = True

    rec = _make_reconciler(mock_repo=repo)
    result = rec.reconciliar_ordem(ticket=1001, agent_id="rl_5000")

    assert result.status == ReconcileStatus.RECONCILIADO_LOCAL
    assert result.resultado == "WIN"
    assert result.reconciled is True
    repo.atualizar_resultado_fechamento.assert_called_once_with(
        ticket=1001, resultado="WIN", pnl=120.0
    )


def test_reconciliar_ordem_local_pnl_pct_negativo():
    repo = MagicMock(spec=IFechamentoRepository)
    repo.obter_resultado_local.return_value = None
    repo.listar_sem_resultado.return_value = [
        {"ticket": 1002, "pnl_pct": -0.07, "pnl_reais": -80.0}
    ]
    repo.atualizar_resultado_fechamento.return_value = True

    rec = _make_reconciler(mock_repo=repo)
    result = rec.reconciliar_ordem(ticket=1002, agent_id="rl_5000")

    assert result.status == ReconcileStatus.RECONCILIADO_LOCAL
    assert result.resultado == "LOSS"


def test_reconciliar_ordem_local_pnl_pct_inexistente_cai_para_mt5():
    repo = MagicMock(spec=IFechamentoRepository)
    repo.obter_resultado_local.return_value = None
    repo.listar_sem_resultado.return_value = [
        {"ticket": 1003}  # sem pnl_pct
    ]
    repo.atualizar_resultado_fechamento.return_value = True
    mt5 = MagicMock()
    mt5.obter_pnl_fechado.return_value = 60.0

    rec = _make_reconciler(mock_repo=repo, mock_mt5=mt5)
    result = rec.reconciliar_ordem(ticket=1003, agent_id="rl_5000")

    assert result.status == ReconcileStatus.RECONCILIADO_MT5


# ==================================================================
# Grupo 5c: reconciliar_ordem - fallback MT5
# ==================================================================


def test_reconciliar_ordem_mt5_retorna_profit_positivo():
    repo = MagicMock(spec=IFechamentoRepository)
    repo.obter_resultado_local.return_value = None
    repo.listar_sem_resultado.return_value = []
    repo.atualizar_resultado_fechamento.return_value = True
    mt5 = MagicMock()
    mt5.obter_pnl_fechado.return_value = 50.0

    rec = _make_reconciler(mock_repo=repo, mock_mt5=mt5)
    result = rec.reconciliar_ordem(ticket=2001, agent_id="rl_5000")

    assert result.status == ReconcileStatus.RECONCILIADO_MT5
    assert result.resultado == "WIN"
    assert result.reconciled is True


def test_reconciliar_ordem_mt5_retorna_none_gera_erro():
    repo = MagicMock(spec=IFechamentoRepository)
    repo.obter_resultado_local.return_value = None
    repo.listar_sem_resultado.return_value = []
    mt5 = MagicMock()
    mt5.obter_pnl_fechado.return_value = None

    rec = _make_reconciler(mock_repo=repo, mock_mt5=mt5)
    result = rec.reconciliar_ordem(ticket=2002, agent_id="rl_5000")

    assert result.status == ReconcileStatus.ERRO
    assert result.reconciled is False
    assert result.resultado is None


def test_reconciliar_ordem_mt5_lanca_excecao_gera_erro():
    repo = MagicMock(spec=IFechamentoRepository)
    repo.obter_resultado_local.return_value = None
    repo.listar_sem_resultado.return_value = []
    mt5 = MagicMock()
    mt5.obter_pnl_fechado.side_effect = RuntimeError("timeout")

    rec = _make_reconciler(mock_repo=repo, mock_mt5=mt5)
    result = rec.reconciliar_ordem(ticket=2003, agent_id="rl_5000")

    assert result.status == ReconcileStatus.ERRO
    assert result.reconciled is False


# ==================================================================
# Grupo 5d: idempotencia e isolamento
# ==================================================================


def test_reconciliar_ordem_idempotente_retorna_pendente():
    repo = MagicMock(spec=IFechamentoRepository)
    repo.obter_resultado_local.return_value = "WIN"

    rec = _make_reconciler(mock_repo=repo)
    result = rec.reconciliar_ordem(ticket=3001, agent_id="rl_5000")

    assert result.status == ReconcileStatus.PENDENTE
    assert result.resultado == "WIN"
    assert result.reconciled is True
    repo.atualizar_resultado_fechamento.assert_not_called()


def test_reconciliar_ordem_agent_id_desconhecido_gera_erro():
    repo = MagicMock(spec=IFechamentoRepository)
    repo.obter_resultado_local.return_value = None
    repo.listar_sem_resultado.return_value = []
    mt5 = MagicMock()
    mt5.obter_pnl_fechado.side_effect = ValueError("agent_id desconhecido")

    rec = _make_reconciler(mock_repo=repo, mock_mt5=mt5)
    result = rec.reconciliar_ordem(ticket=3002, agent_id="agente_invalido")

    assert result.status == ReconcileStatus.ERRO


def test_reconciliar_ordem_nao_chama_mt5_quando_pnl_pct_disponivel():
    repo = MagicMock(spec=IFechamentoRepository)
    repo.obter_resultado_local.return_value = None
    repo.listar_sem_resultado.return_value = [
        {"ticket": 3003, "pnl_pct": 0.06, "pnl_reais": 50.0}
    ]
    repo.atualizar_resultado_fechamento.return_value = True
    mt5 = MagicMock()

    rec = _make_reconciler(mock_repo=repo, mock_mt5=mt5)
    rec.reconciliar_ordem(ticket=3003, agent_id="rl_5000")

    mt5.obter_pnl_fechado.assert_not_called()


# ==================================================================
# Grupo 5e: gerar_relatorio_sessao
# ==================================================================


def test_gerar_relatorio_sessao_cria_arquivo(tmp_path: Path):
    repo = MagicMock(spec=IFechamentoRepository)
    repo.obter_resultado_local.return_value = None
    repo.listar_sem_resultado.return_value = []
    mt5 = MagicMock()
    mt5.obter_pnl_fechado.return_value = 40.0
    repo.atualizar_resultado_fechamento.return_value = True

    rec = _make_reconciler(mock_repo=repo, mock_mt5=mt5)
    rec.reconciliar_ordem(ticket=9001, agent_id="rl_5000")

    caminho = rec.gerar_relatorio_sessao("sessao-abc", tmp_path)

    assert caminho.exists()
    import json
    dados = json.loads(caminho.read_text())
    assert dados["session_id"] == "sessao-abc"
    assert dados["n_total"] == 1
    assert "pct_desconhecido_sessao" in dados


def test_gerar_relatorio_sessao_sem_historico(tmp_path: Path):
    rec = _make_reconciler()
    caminho = rec.gerar_relatorio_sessao("sessao-vazia", tmp_path)

    import json
    dados = json.loads(caminho.read_text())
    assert dados["n_total"] == 0
    assert dados["pct_desconhecido_sessao"] == 0.0