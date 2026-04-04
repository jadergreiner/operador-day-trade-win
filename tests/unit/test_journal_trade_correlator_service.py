"""Testes TDD para JournalTradeCorrelatorService.

BLID-022 / ROADMAP-DIARIOS-02 — Etapa 2: Correlacao.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from src.application.services.journal_trade_correlator_service import (
    JournalTradeCorrelatorService,
)
from src.infrastructure.database.diario_journal_schema import criar_tabelas_diario


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------


def _inserir_journal_entry(
    db: Path,
    entry_id: str,
    timestamp: str,
    decision: str = "BUY",
) -> None:
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        INSERT INTO trading_journal_logs (
            entry_id, timestamp, symbol, headline, market_feeling,
            decision, confidence, macro_bias, technical_bias,
            alignment_score, outcome_trade, created_at
        ) VALUES (?, ?, 'WIN$N', 'Titulo', 'BULLISH',
                  ?, 0.75, 'BULLISH', 'BULLISH', 0.8, 'SEM_TRADE', ?)
        """,
        (entry_id, timestamp, decision, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def _criar_tabela_diary_orders(db: Path) -> None:
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS diary_orders (
            ticket       INTEGER PRIMARY KEY,
            magic_number INTEGER,
            close_time   TEXT,
            profit       REAL,
            side         TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def _inserir_diary_order(
    db: Path,
    ticket: int,
    magic: int,
    close_time: str,
    profit: float,
    side: str,
) -> None:
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO diary_orders VALUES (?, ?, ?, ?, ?)",
        (ticket, magic, close_time, profit, side),
    )
    conn.commit()
    conn.close()


def _buscar_correlacao(db: Path, entry_id: str) -> dict[str, Any]:
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM journal_trade_correlation WHERE journal_entry_id=?",
        (entry_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


class TestJournalTradeCorrelatorService:
    """Testes para JournalTradeCorrelatorService."""

    def test_correlacao_sem_trades_retorna_sem_trade(
        self, tmp_path: Path
    ) -> None:
        """Sem tabela diary_orders, correlacao deve registrar SEM_TRADE."""
        db = tmp_path / "d.db"
        criar_tabelas_diario(db)
        _inserir_journal_entry(db, "entry-001", "2026-04-02T10:00:00")

        svc = JournalTradeCorrelatorService(db_path=db)
        n = svc.correlacionar_sessao("2026-04-02")

        assert n == 1
        corr = _buscar_correlacao(db, "entry-001")
        assert corr["outcome"] == "SEM_TRADE"

    def test_invariante_sem_trade_campos_nulos(self, tmp_path: Path) -> None:
        """Quando outcome=SEM_TRADE, ticket, pnl_reais e alinhado devem ser None."""
        db = tmp_path / "d.db"
        criar_tabelas_diario(db)
        _inserir_journal_entry(db, "entry-002", "2026-04-02T10:00:00")

        svc = JournalTradeCorrelatorService(db_path=db)
        svc.correlacionar_sessao("2026-04-02")

        corr = _buscar_correlacao(db, "entry-002")
        assert corr["trade_ticket"] is None
        assert corr["pnl_reais"] is None
        assert corr["narrativa_estava_alinhada"] is None

    def test_alinhamento_correto_buy_buy(self, tmp_path: Path) -> None:
        """decision=BUY e side=BUY deve resultar em narrativa_estava_alinhada=1."""
        db = tmp_path / "d.db"
        criar_tabelas_diario(db)
        ts = "2026-04-02T10:00:00"
        _inserir_journal_entry(db, "entry-003", ts, decision="BUY")
        _criar_tabela_diary_orders(db)
        _inserir_diary_order(
            db, 1001, 234800,
            "2026-04-02T10:15:00", 150.0, "BUY"
        )

        svc = JournalTradeCorrelatorService(db_path=db)
        svc.correlacionar_sessao("2026-04-02")

        corr = _buscar_correlacao(db, "entry-003")
        assert corr["narrativa_estava_alinhada"] == 1

    def test_alinhamento_incorreto_buy_sell(self, tmp_path: Path) -> None:
        """decision=BUY e side=SELL deve resultar em narrativa_estava_alinhada=0."""
        db = tmp_path / "d.db"
        criar_tabelas_diario(db)
        ts = "2026-04-02T10:00:00"
        _inserir_journal_entry(db, "entry-004", ts, decision="BUY")
        _criar_tabela_diary_orders(db)
        _inserir_diary_order(
            db, 1002, 234800,
            "2026-04-02T10:15:00", -100.0, "SELL"
        )

        svc = JournalTradeCorrelatorService(db_path=db)
        svc.correlacionar_sessao("2026-04-02")

        corr = _buscar_correlacao(db, "entry-004")
        assert corr["narrativa_estava_alinhada"] == 0

    def test_outcome_win_loss_breakeven(self, tmp_path: Path) -> None:
        """Testa mapeamento correto profit>0->WIN, <0->LOSS, ==0->BREAKEVEN."""
        db = tmp_path / "d.db"
        criar_tabelas_diario(db)
        _criar_tabela_diary_orders(db)

        casos = [
            ("entry-w", "2026-04-02T09:00:00", 200.0, "WIN"),
            ("entry-l", "2026-04-02T10:00:00", -100.0, "LOSS"),
            ("entry-b", "2026-04-02T11:00:00", 0.0, "BREAKEVEN"),
        ]
        for eid, ts, profit, _ in casos:
            _inserir_journal_entry(db, eid, ts, decision="BUY")
            # close_time 15min depois do timestamp da entrada (dentro da janela)
            ts_dt = datetime.fromisoformat(ts)
            close_time = (ts_dt + timedelta(minutes=15)).isoformat()
            _inserir_diary_order(
                db, hash(eid) % 9999 + 1000, 234800,
                close_time,
                profit, "BUY"
            )

        svc = JournalTradeCorrelatorService(db_path=db)
        svc.correlacionar_sessao("2026-04-02")

        for eid, _, _, expected_outcome in casos:
            corr = _buscar_correlacao(db, eid)
            assert corr["outcome"] == expected_outcome, (
                f"entry_id={eid}: esperado {expected_outcome}, got {corr['outcome']}"
            )
