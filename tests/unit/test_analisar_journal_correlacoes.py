"""Testes TDD para analisar_journal_correlacoes.py.

BLID-022 / ROADMAP-DIARIOS-02 — Etapa 3: Exportacao JSON.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


from scripts.analisar_journal_correlacoes import exportar_features


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------


def _popular_banco(db: Path) -> None:
    """Popula banco com 3 entradas de journal e 3 correlacoes."""
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trading_journal_logs (
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
            outcome_trade TEXT DEFAULT 'SEM_TRADE',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS journal_trade_correlation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journal_entry_id TEXT NOT NULL,
            trade_ticket INTEGER,
            outcome TEXT NOT NULL,
            pnl_reais REAL,
            narrativa_estava_alinhada INTEGER,
            created_at TEXT NOT NULL,
            UNIQUE(journal_entry_id)
        )
        """
    )
    agora = datetime.now().isoformat()
    entradas = [
        ("e001", "2026-04-02T09:00:00", "BUY"),
        ("e002", "2026-04-02T10:00:00", "SELL"),
        ("e003", "2026-04-02T11:00:00", "BUY"),
    ]
    for eid, ts, dec in entradas:
        conn.execute(
            """
            INSERT INTO trading_journal_logs (
                entry_id, timestamp, symbol, headline, market_feeling,
                decision, confidence, macro_bias, technical_bias,
                alignment_score, outcome_trade, created_at
            ) VALUES (?, ?, 'WIN$N', 'H', 'BULL', ?, 0.8, 'BULL', 'BULL', 0.8, 'SEM_TRADE', ?)
            """,
            (eid, ts, dec, agora),
        )
    correlacoes = [
        ("e001", 1001, "WIN", 200.0, 1),
        ("e002", 1002, "LOSS", -100.0, 0),
        ("e003", None, "SEM_TRADE", None, None),
    ]
    for eid, ticket, outcome, pnl, alinhado in correlacoes:
        conn.execute(
            "INSERT INTO journal_trade_correlation VALUES (NULL,?,?,?,?,?,?)",
            (eid, ticket, outcome, pnl, alinhado, agora),
        )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


class TestAnalisarJournalCorrelacoes:
    """Testes para exportar_features()."""

    def test_exportar_features_schema_version(self, tmp_path: Path) -> None:
        """JSON exportado deve conter schema_version='1.0'."""
        db = tmp_path / "d.db"
        _popular_banco(db)

        caminho = exportar_features("2026-04-02", db, tmp_path)
        dados = json.loads(caminho.read_text(encoding="utf-8"))

        assert dados["schema_version"] == "1.0"

    def test_exportar_features_nome_arquivo_correto(
        self, tmp_path: Path
    ) -> None:
        """Arquivo deve ser nomeado journal_features_YYYYMMDD.json."""
        db = tmp_path / "d.db"
        _popular_banco(db)

        caminho = exportar_features("2026-04-02", db, tmp_path)

        assert caminho.name == "journal_features_20260402.json"

    def test_exportar_features_campos_obrigatorios(
        self, tmp_path: Path
    ) -> None:
        """JSON deve conter todos os campos raiz obrigatorios."""
        db = tmp_path / "d.db"
        _popular_banco(db)

        caminho = exportar_features("2026-04-02", db, tmp_path)
        dados = json.loads(caminho.read_text(encoding="utf-8"))

        campos_obrigatorios = {
            "schema_version",
            "generated_at",
            "data_referencia",
            "magic_number_filtro",
            "totais",
            "metricas",
            "features",
        }
        assert campos_obrigatorios <= set(dados.keys())
