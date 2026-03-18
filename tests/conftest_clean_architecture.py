"""
Fixtures compartilhadas para testes Fase 1 - Clean Architecture Agent

Disponível para todos os módulos do agente Clean Architecture.
Adicione novas fixtures aqui conforme necessário.
"""

import pytest
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List
from uuid import uuid4


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES TRADE & EXECUTION
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def trade_id() -> str:
    """Gera ID de trade único para testes."""
    return str(uuid4())


@pytest.fixture
def sample_trade_outcome() -> Dict:
    """
    Sample trade outcome para validação de reconciliação.

    Representa um trade executado com sucesso que precisa ser reconciliado.
    """
    return {
        "trade_id": str(uuid4()),
        "symbol": "WIN$N",
        "side": "BUY",
        "quantity": 1,
        "entry_price": 100.50,
        "exit_price": 102.75,
        "timestamp_entry": datetime.now().isoformat(),
        "timestamp_exit": datetime.now().isoformat(),
        "status": "CLOSED",
        "pnl": 225.00,  # (102.75 - 100.50) * 1 * 100
        "commission": 5.00,
    }


@pytest.fixture
def sample_unknown_outcome() -> Dict:
    """
    Sample unknown outcome (resultado indeterminado).

    Representa trade com status desconhecido (network error, timeout, etc).
    """
    return {
        "trade_id": str(uuid4()),
        "symbol": "WIN$N",
        "side": "BUY",
        "quantity": 1,
        "entry_price": 100.50,
        "timestamp_entry": datetime.now().isoformat(),
        "status": "UNKNOWN",  # Falta exit info
        "reason": "MT5 connection lost during execution",
    }


@pytest.fixture
def sample_multiple_outcomes() -> List[Dict]:
    """
    Múltiplos outcomes para teste batch de reconciliação.
    """
    return [
        {
            "trade_id": str(uuid4()),
            "symbol": "WIN$N",
            "side": "BUY",
            "quantity": 1,
            "entry_price": 100.00,
            "exit_price": 101.00,
            "timestamp_entry": datetime.now().isoformat(),
            "timestamp_exit": datetime.now().isoformat(),
            "status": "CLOSED",
            "pnl": 100.00,
        },
        {
            "trade_id": str(uuid4()),
            "symbol": "WIN$N",
            "side": "SELL",
            "quantity": 2,
            "entry_price": 102.00,
            "exit_price": 101.50,
            "timestamp_entry": datetime.now().isoformat(),
            "timestamp_exit": datetime.now().isoformat(),
            "status": "CLOSED",
            "pnl": 100.00,
        },
    ]


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES MT5 SYNC
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mt5_position_state() -> Dict:
    """
    Estado de posição no MT5 (simulado).

    Usado para validar sincronização contra banco local.
    """
    return {
        "ticket": 123456,
        "symbol": "WIN$N",
        "type": 0,  # BUY
        "volume": 1.0,
        "price_open": 100.50,
        "sl": 99.50,
        "tp": 102.50,
        "time": int(datetime.now().timestamp()),
        "price_current": 101.00,
        "profit": 50.00,
    }


@pytest.fixture
def local_position_state() -> Dict:
    """
    Estado de posição no banco local SQLite.
    """
    return {
        "id": str(uuid4()),
        "ticket": 123456,
        "symbol": "WIN$N",
        "side": "BUY",
        "volume": 1,
        "entry_price": 100.50,
        "sl": 99.50,
        "tp": 102.50,
        "entry_time": datetime.now().isoformat(),
        "current_price": 101.00,
        "pnl": 50.00,
        "synced": True,
    }


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES AUDIT & LOGGING
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def audit_entry() -> Dict:
    """
    Entry de auditoria para logging de reconciliação.
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "event_type": "RECONCILIATION",
        "trade_id": str(uuid4()),
        "status": "SUCCESS",
        "details": {
            "source": "MT5",
            "destination": "SQLite",
            "validation_passed": True,
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES ERROR SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def divergent_outcomes() -> tuple[Dict, Dict]:
    """
    Par de outcomes divergentes (MT5 vs Local diferente).

    Para teste de detecção de discrepâncias.
    """
    base_mt5 = {
        "trade_id": str(uuid4()),
        "symbol": "WIN$N",
        "volume": 1,
        "entry_price": 100.50,
        "exit_price": 102.75,
        "profit": 225.00,
    }

    # Local tem volume diferente (error)
    base_local = base_mt5.copy()
    base_local["volume"] = 2  # DIVERGÊNCIA!
    base_local["profit"] = 450.00

    return base_mt5, base_local


@pytest.fixture
def timestamp_misalign() -> Dict:
    """
    Trade com timestamp ligeiramente desalinhado.

    Valida tolerância de sincronização.
    """
    from datetime import timedelta
    now = datetime.now()
    return {
        "trade_id": str(uuid4()),
        "timestamp_mt5": now.isoformat(),
        "timestamp_local": (now + timedelta(seconds=1)).isoformat(),  # 1 sec diff
        "tolerance_ms": 2000,  # 2s tolerance
    }


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES AC5.9 - FEEDBACK VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_trade_feedback_pair() -> tuple[Dict, Dict]:
    """
    Par válido de (trade, feedback) para AC5.9.

    Trade e feedback com correlação perfeita.
    """
    from datetime import timedelta
    
    trade_id = str(uuid4())
    now = datetime.now()
    exit_time = now + timedelta(minutes=1)
    
    trade = {
        "trade_id": trade_id,
        "symbol": "WIN$N",
        "side": "BUY",
        "quantity": 1,
        "entry_price": 100.50,
        "exit_price": 102.75,
        "timestamp_entry": now.isoformat(),
        "timestamp_exit": exit_time.isoformat(),
        "pnl": 225.00,
        "status": "CLOSED"
    }
    
    feedback = {
        "trade_id": trade_id,
        "outcome_type": "CLOSED",
        "pnl_actual": 225.00,
        "pnl_expected": 225.00,
        "correlation_score": 1.0,
        "timestamp": now.isoformat()
    }
    
    return trade, feedback


@pytest.fixture
def invalid_feedback_types() -> list[Dict]:
    """
    Feedbacks com tipos de outcome inválidos.

    Para teste de validação AC5.9.2.
    """
    return [
        {
            "trade_id": str(uuid4()),
            "outcome_type": "INVALID_TYPE",  # ❌ Inválido
            "pnl_actual": 100.0,
            "pnl_expected": 100.0,
            "timestamp": datetime.now().isoformat()
        },
        {
            "trade_id": str(uuid4()),
            "outcome_type": None,  # ❌ None
            "pnl_actual": 50.0,
            "pnl_expected": 50.0,
            "timestamp": datetime.now().isoformat()
        },
        {
            "trade_id": str(uuid4()),
            "outcome_type": "",  # ❌ Empty string
            "pnl_actual": -10.0,
            "pnl_expected": -10.0,
            "timestamp": datetime.now().isoformat()
        }
    ]


@pytest.fixture
def missing_feedback_outcomes() -> tuple[list[Dict], list[Dict]]:
    """
    Trades sem feedback correspondente.

    Para teste de correlação AC5.9.1.
    """
    trades = [
        {
            "trade_id": str(uuid4()),
            "symbol": "WIN$N",
            "side": "BUY",
            "quantity": 1,
            "entry_price": 100.0,
            "exit_price": 101.0,
            "pnl": 100.0,
            "status": "CLOSED"
        }
        for _ in range(3)
    ]
    
    # Apenas feedback para 1 dos 3 trades
    feedbacks = [
        {
            "trade_id": trades[0]["trade_id"],
            "outcome_type": "CLOSED",
            "pnl_actual": 100.0,
            "pnl_expected": 100.0,
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    return trades, feedbacks


@pytest.fixture
def pnl_mismatch_feedbacks() -> list[tuple[float, float]]:
    """
    Pares de (pnl_actual, pnl_expected) com divergências.

    Para teste AC5.9.3 (validação consistência PnL).
    """
    return [
        (100.0, 100.0),   # ✓ Matched
        (100.0, 110.0),   # ✗ Diverge 10
        (50.0, 50.0),     # ✓ Matched
        (200.0, 190.0),   # ✗ Diverge 10
        (-50.0, -50.0),   # ✓ Matched
    ]


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES MARKERS
# ═══════════════════════════════════════════════════════════════════════════

def pytest_configure(config):
    """Registra markers customizados."""
    config.addinivalue_line(
        "markers",
        "reconciliation: marca testes de reconciliação de trades"
    )
    config.addinivalue_line(
        "markers",
        "mt5_sync: marca testes de sincronização MT5"
    )
    config.addinivalue_line(
        "markers",
        "audit: marca testes de auditoria"
    )
    config.addinivalue_line(
        "markers",
        "feedback: marca testes de validação de feedback"
    )
