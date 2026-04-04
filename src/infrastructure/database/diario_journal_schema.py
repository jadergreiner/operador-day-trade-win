"""Schema SQLite para tabelas do diario journal (BLID-022 / ROADMAP-DIARIOS-02).

Fornece funcoes puras para criacao de tabelas e obtencao de conexao,
seguindo o padrao sqlite3 direto (sem SQLAlchemy) dos demais diarios.

Banco alvo: data/db/trading_diarios.db (exclusivo do agente Diarios,
magic_number=234800, conforme ADR-019).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# DDL das tabelas
# ---------------------------------------------------------------------------

_DDL_TRADING_JOURNAL_LOGS = """
CREATE TABLE IF NOT EXISTS trading_journal_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id        TEXT    NOT NULL UNIQUE,
    timestamp       TEXT    NOT NULL,
    symbol          TEXT    NOT NULL,
    headline        TEXT    NOT NULL,
    market_feeling  TEXT    NOT NULL,
    decision        TEXT    NOT NULL,
    confidence      REAL    NOT NULL,
    macro_bias      TEXT    NOT NULL,
    technical_bias  TEXT    NOT NULL,
    alignment_score REAL    NOT NULL,
    outcome_trade   TEXT    DEFAULT 'SEM_TRADE',
    created_at      TEXT    NOT NULL
)
"""

_DDL_JOURNAL_TRADE_CORRELATION = """
CREATE TABLE IF NOT EXISTS journal_trade_correlation (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_entry_id           TEXT    NOT NULL,
    trade_ticket               INTEGER,
    outcome                    TEXT    NOT NULL
        CHECK(outcome IN ('WIN','LOSS','BREAKEVEN','SEM_TRADE')),
    pnl_reais                  REAL,
    narrativa_estava_alinhada  INTEGER,
    created_at                 TEXT    NOT NULL,
    UNIQUE(journal_entry_id)
)
"""


# ---------------------------------------------------------------------------
# Funcoes publicas
# ---------------------------------------------------------------------------


def criar_tabelas_diario(db_path: Path) -> None:
    """Cria as tabelas do diario journal caso nao existam (idempotente).

    Aplica WAL mode e synchronous=NORMAL para desempenho e seguranca.

    Args:
        db_path: Caminho para o arquivo SQLite do banco de dados.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(_DDL_TRADING_JOURNAL_LOGS)
        conn.execute(_DDL_JOURNAL_TRADE_CORRELATION)
        conn.commit()
    finally:
        conn.close()


def obter_conexao_diario(db_path: Path) -> sqlite3.Connection:
    """Retorna uma conexao SQLite configurada para o banco dos diarios.

    O chamador e responsavel por fechar a conexao apos o uso.
    `PRAGMA busy_timeout=30000` cobre bloqueios WAL apos a conexao
    ser estabelecida.

    Args:
        db_path: Caminho para o arquivo SQLite do banco de dados.

    Returns:
        Conexao sqlite3 configurada com WAL, synchronous e busy_timeout.
    """
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn
