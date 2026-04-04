"""Schema SQLite para tabelas de AI Reflection (BLID-023 / ROADMAP-DIARIOS-03).

Banco alvo: data/db/trading_diarios.db (magic_number=234800, ADR-019).

Fornece funcoes puras para criacao de tabelas e obtencao de conexao,
seguindo o padrao sqlite3 direto (sem SQLAlchemy) dos demais diarios.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

# ---------------------------------------------------------------------------
# DDL das tabelas
# ---------------------------------------------------------------------------

_DDL_AI_REFLECTION_LOGS = """
CREATE TABLE IF NOT EXISTS ai_reflection_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id        TEXT    NOT NULL UNIQUE,
    timestamp       TEXT    NOT NULL,
    mood            TEXT    NOT NULL,
    my_decision     TEXT    NOT NULL,
    my_confidence   REAL    NOT NULL,
    my_alignment    REAL    NOT NULL,
    honest_assessment TEXT  NOT NULL,
    data_relevance  TEXT    NOT NULL,
    am_i_useful     TEXT    NOT NULL,
    my_data_correlation TEXT NOT NULL,
    one_liner       TEXT    NOT NULL,
    created_at      TEXT    NOT NULL
)
"""

_DDL_REFLECTION_QUESTIONS = """
CREATE TABLE IF NOT EXISTS reflection_questions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id      TEXT    NOT NULL UNIQUE,
    prompt           TEXT    NOT NULL,
    category         TEXT    NOT NULL,
    level            TEXT    NOT NULL DEFAULT 'basico',
    data_criacao     TEXT    NOT NULL,
    data_ultima_avaliacao TEXT,
    score_relevancia REAL    NOT NULL DEFAULT 0.0,
    total_respostas  INTEGER NOT NULL DEFAULT 0,
    respostas_win    INTEGER NOT NULL DEFAULT 0,
    respostas_loss   INTEGER NOT NULL DEFAULT 0,
    obsoleta         INTEGER NOT NULL DEFAULT 0,
    data_obsoleta    TEXT,
    ativa            INTEGER NOT NULL DEFAULT 1
)
"""


# ---------------------------------------------------------------------------
# Funcoes publicas
# ---------------------------------------------------------------------------


def criar_tabelas_ai_reflection(db_path: Path) -> None:
    """Cria as tabelas de AI Reflection caso nao existam (idempotente).

    Aplica WAL mode e synchronous=NORMAL para desempenho e seguranca.

    Args:
        db_path: Caminho para o arquivo SQLite do banco de dados.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(_DDL_AI_REFLECTION_LOGS)
        conn.execute(_DDL_REFLECTION_QUESTIONS)
        conn.commit()
    finally:
        conn.close()


def obter_conexao_ai_reflection(db_path: Path) -> sqlite3.Connection:
    """Retorna uma conexao SQLite configurada para o banco de AI Reflection.

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
