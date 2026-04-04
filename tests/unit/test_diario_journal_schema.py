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
