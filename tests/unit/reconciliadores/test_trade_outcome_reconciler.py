"""
Testes para TradeOutcomeReconciler.

Cobertura de cenários:
1. Ambos existem com valores iguais ✓
2. Ambos existem com valores divergentes ✓
3. Falta no local (importar do MT5) ✓
4. Falta no MT5 (auditoria necessária) ✓
5. Não existe em lugar nenhum ✓
6. Reconciliação em lote ✓
7. Histórico e limpeza ✓
"""

import pytest
from datetime import datetime
from src.application.reconciliadores.trade_outcome_reconciler import (
    TradeOutcomeReconciler,
    ReconciliationResult
)

@pytest.mark.asyncio
async def test_reconciliar_ordem_ambos_valores_iguais():
    reconciler = TradeOutcomeReconciler()
    resultado_local = {"profit": 50.0, "price": 120500}
    resultado_mt5 = {"profit": 50.0, "price": 120500}

    resultado = await reconciler.reconciliar_ordem("101", resultado_local, resultado_mt5)

    assert resultado.reconciled is True
    assert resultado.order_id == "101"
    assert "consistent" in resultado.message.lower()

@pytest.mark.asyncio
async def test_reconciliar_ordem_ambos_valores_divergentes():
    reconciler = TradeOutcomeReconciler()
    resultado_local = {"profit": 50.0}
    resultado_mt5 = {"profit": 49.5}

    resultado = await reconciler.reconciliar_ordem("102", resultado_local, resultado_mt5)

    assert resultado.reconciled is True  # MT5 é autoridade
    assert resultado.mt5_result == 49.5

@pytest.mark.asyncio
async def test_reconciliar_ordem_falta_no_local():
    reconciler = TradeOutcomeReconciler()
    resultado_local = None
    resultado_mt5 = {"profit": 75.0}

    resultado = await reconciler.reconciliar_ordem("103", resultado_local, resultado_mt5)

    assert resultado.reconciled is True
    assert resultado.local_result == 75.0  # Importado do MT5
    assert resultado.mt5_result == 75.0
    assert "importado" in resultado.message.lower()

@pytest.mark.asyncio
async def test_reconciliar_ordem_converte_profit_em_string():
    reconciler = TradeOutcomeReconciler()
    resultado_local = {"profit": "50.25"}
    resultado_mt5 = {"profit": 50.25}

    resultado = await reconciler.reconciliar_ordem("103a", resultado_local, resultado_mt5)

    assert resultado.reconciled is True
    assert resultado.local_result == 50.25
    assert resultado.mt5_result == 50.25
    assert "consistentes" in resultado.message.lower()

@pytest.mark.asyncio
async def test_reconciliar_ordem_ignora_profit_invalido():
    reconciler = TradeOutcomeReconciler()
    resultado_local = {"profit": "abc"}
    resultado_mt5 = {"profit": 10.0}

    resultado = await reconciler.reconciliar_ordem("103b", resultado_local, resultado_mt5)

    assert resultado.reconciled is True
    assert resultado.local_result == 10.0
    assert resultado.mt5_result == 10.0
    assert "importado" in resultado.message.lower()

@pytest.mark.asyncio
async def test_reconciliar_ordem_falta_no_mt5():
    reconciler = TradeOutcomeReconciler()
    resultado_local = {"profit": 100.0}
    resultado_mt5 = None

    resultado = await reconciler.reconciliar_ordem("104", resultado_local, resultado_mt5)

    assert resultado.reconciled is False
    assert resultado.local_result == 100.0
    assert resultado.mt5_result is None
    assert "auditoria" in resultado.message.lower()

@pytest.mark.asyncio
async def test_reconciliar_ordem_nao_existe():
    reconciler = TradeOutcomeReconciler()

    resultado = await reconciler.reconciliar_ordem("105", None, None)

    assert resultado.reconciled is False
    assert resultado.local_result is None
    assert resultado.mt5_result is None

@pytest.mark.asyncio
async def test_reconciliar_lote():
    reconciler = TradeOutcomeReconciler()
    ordens = [
        ("201", {"profit": 50.0}, {"profit": 50.0}),
        ("202", None, {"profit": 75.0}),
        ("203", {"profit": 100.0}, None),
    ]

    resultados = await reconciler.reconciliar_lote(ordens)

    assert len(resultados) == 3
    assert resultados[0].reconciled is True
    assert resultados[1].reconciled is True
    assert resultados[2].reconciled is False

def test_obter_historico():
    reconciler = TradeOutcomeReconciler()

    # Simular reconciliação (usando método auxiliar)
    reconciler.reconciliation_history = [
        ReconciliationResult(
            order_id="301",
            local_result=50.0,
            mt5_result=50.0,
            reconciled=True,
            timestamp=datetime.now(),
            message="Reconciliado"
        )
    ]

    historico = reconciler.obter_historico()

    assert len(historico) == 1
    assert historico[0]["order_id"] == "301"
    assert historico[0]["reconciled"] is True

def test_limpar_historico():
    reconciler = TradeOutcomeReconciler()

    reconciler.reconciliation_history = [
        ReconciliationResult(
            order_id="401",
            local_result=50.0,
            mt5_result=50.0,
            reconciled=True,
            timestamp=datetime.now(),
            message="Teste"
        )
    ]

    assert len(reconciler.reconciliation_history) == 1

    reconciler.limpar_historico()

    assert len(reconciler.reconciliation_history) == 0

@pytest.mark.asyncio
async def test_reconciliar_lote_preserva_ordem_dos_resultados():
    reconciler = TradeOutcomeReconciler()
    ordens = [
        ("301", {"profit": 10.0}, {"profit": 10.0}),
        ("302", {"profit": 11.0}, None),
    ]

    resultados = await reconciler.reconciliar_lote(ordens)

    assert [resultado.order_id for resultado in resultados] == ["301", "302"]
