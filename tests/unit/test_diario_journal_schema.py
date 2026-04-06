"""Testes TDD para diario_journal_schema.

BLID-022 / ROADMAP-DIARIOS-02 — DDL idempotente.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from src.infrastructure.database.diario_journal_schema import criar_tabelas_diario


class TestCriarTabelasDiario:
    """Testes para criar_tabelas_diario()."""

    def test_criar_tabelas_diario_cria_trading_journal_logs(
        self, tmp_path: Path
    ) -> None:
        """criar_tabelas_diario deve criar tabela trading_journal_logs."""
        db = tmp_path / "t.db"
        criar_tabelas_diario(db)

        conn = sqlite3.connect(str(db))
        tabela = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='trading_journal_logs'"
        ).fetchone()
        conn.close()
        assert tabela is not None

    def test_criar_tabelas_diario_cria_journal_trade_correlation(
        self, tmp_path: Path
    ) -> None:
        """criar_tabelas_diario deve criar tabela journal_trade_correlation."""
        db = tmp_path / "t.db"
        criar_tabelas_diario(db)

        conn = sqlite3.connect(str(db))
        tabela = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='journal_trade_correlation'"
        ).fetchone()
        conn.close()
        assert tabela is not None

    def test_criar_tabelas_diario_idempotente(self, tmp_path: Path) -> None:
        """Chamar criar_tabelas_diario duas vezes nao deve levantar excecao."""
        db = tmp_path / "t.db"
        criar_tabelas_diario(db)
        criar_tabelas_diario(db)  # segunda chamada nao deve falhar

    def test_criar_tabelas_diario_migra_schema_legado(
        self, tmp_path: Path
    ) -> None:
        """Schema legado deve receber colunas canônicas faltantes."""
        db = tmp_path / "legado.db"
        conn = sqlite3.connect(str(db))
        try:
            conn.execute(
                """
                CREATE TABLE trading_journal_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id TEXT NOT NULL UNIQUE,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    headline TEXT NOT NULL,
                    market_feeling TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    macro_bias TEXT NOT NULL,
                    technical_bias TEXT NOT NULL,
                    alignment_score REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

        criar_tabelas_diario(db)

        conn = sqlite3.connect(str(db))
        try:
            colunas = {
                str(row[1])
                for row in conn.execute("PRAGMA table_info(trading_journal_logs)")
            }
        finally:
            conn.close()

        colunas_esperadas = {
            "detailed_narrative",
            "reasoning",
            "fundamental_bias",
            "sentiment_bias",
            "market_regime",
            "key_observations",
            "tags",
            "outcome_trade",
        }
        assert colunas_esperadas <= colunas
