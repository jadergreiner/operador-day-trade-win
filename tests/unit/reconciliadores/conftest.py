"""
Fixtures compartilhadas para testes de reconciliadores.

Disponibiliza:
- mock_mt5_adapter: MT5Adapter com obter_pnl_fechado controlavel
- mock_fechamento_repo: IFechamentoRepository com atualizar_resultado_fechamento
- sqlite_em_memoria: banco SQLite em tmp_path com tabela historico_fechamentos
- ordens_agente_5000 / ordens_agente_direto: listas de ordens simuladas
"""

import sqlite3
import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from src.infrastructure.repositories.fechamento_repository import IFechamentoRepository


@pytest.fixture
def mock_mt5_adapter() -> MagicMock:
    """Mock do MT5Adapter com obter_pnl_fechado controlavel."""
    adapter = MagicMock()
    adapter.obter_pnl_fechado.return_value = 25.0
    return adapter


@pytest.fixture
def mock_fechamento_repo() -> MagicMock:
    """Mock de IFechamentoRepository com atualizar_resultado_fechamento."""
    repo = MagicMock(spec=IFechamentoRepository)
    repo.atualizar_resultado_fechamento.return_value = True
    repo.obter_resultado_local.return_value = None
    repo.listar_sem_resultado.return_value = []
    return repo


@pytest.fixture
def sqlite_em_memoria(tmp_path: Path):
    """Banco SQLite em tmp_path com tabela historico_fechamentos."""
    db = tmp_path / "test_trading.db"
    conn = sqlite3.connect(str(db))
    conn.execute("""
        CREATE TABLE historico_fechamentos (
            ticket INTEGER PRIMARY KEY,
            agent_id TEXT NOT NULL,
            magic_number INTEGER NOT NULL,
            resultado TEXT,
            pnl_reais REAL,
            pnl_pct REAL,
            status TEXT DEFAULT 'FECHADA'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reconciliation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket INTEGER NOT NULL,
            agent_id TEXT NOT NULL,
            resultado TEXT,
            fonte TEXT,
            status TEXT,
            timestamp TEXT,
            UNIQUE(ticket, agent_id)
        )
    """)
    conn.commit()
    return db, conn


@pytest.fixture
def ordens_agente_5000() -> List[Dict[str, Any]]:
    """Ordens simuladas do agente 5000 (magic_number=234500)."""
    return [
        {"ticket": "1001", "magic_number": 234500,
         "resultado": None, "pnl_pct": 0.42},
        {"ticket": "1002", "magic_number": 234500,
         "resultado": None, "pnl_pct": -0.15},
    ]


@pytest.fixture
def ordens_agente_direto() -> List[Dict[str, Any]]:
    """Ordens do agente direto (magic_number=234600) — nao devem cruzar."""
    return [
        {"ticket": "2001", "magic_number": 234600,
         "resultado": None, "pnl_pct": 0.08},
    ]
