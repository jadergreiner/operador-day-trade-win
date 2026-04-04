"""Testes TDD para persistencia SQLite do TradingJournalService.

BLID-022 / ROADMAP-DIARIOS-02 — Etapa 1: Persistencia.
"""
from __future__ import annotations

import sqlite3
import threading
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.application.services.trading_journal import TradingJournalService
from src.domain.enums.trading_enums import TradeSignal
from src.domain.value_objects import Symbol


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _narrativa_mock(service: TradingJournalService) -> Any:
    """Cria uma narrativa de mercado minima valida."""
    return service.create_narrative(
        symbol=Symbol("WIN$N"),
        current_price=Decimal("125000"),
        opening_price=Decimal("124500"),
        high=Decimal("125500"),
        low=Decimal("124000"),
        decision_data={
            "decision": "BUY",
            "confidence": 0.75,
            "macro_bias": "BULLISH",
            "technical_bias": "BULLISH",
            "alignment_score": Decimal("0.8"),
            "macro_factors": [],
            "technical_factors": [],
            "supporting_factors": [],
            "conflicting_factors": [],
            "market_regime": "TRENDING",
        },
    )


def _dados_decisao() -> dict[str, Any]:
    return {
        "macro_bias": "BULLISH",
        "technical_bias": "BULLISH",
        "alignment_score": Decimal("0.8"),
        "supporting_factors": ["RSI em alta"],
        "market_regime": "TRENDING",
    }


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


class TestSaveEntryPersistenciaSQL:
    """Testes de persistencia SQLite do TradingJournalService."""

    def test_save_entry_persiste_no_sqlite(self, tmp_path: Path) -> None:
        """Dado db_path, save_entry() deve gravar 1 linha em trading_journal_logs."""
        db = tmp_path / "diarios.db"
        svc = TradingJournalService(db_path=db)
        narrativa = _narrativa_mock(svc)

        svc.save_entry(narrativa, _dados_decisao())

        conn = sqlite3.connect(str(db))
        count = conn.execute(
            "SELECT COUNT(*) FROM trading_journal_logs"
        ).fetchone()[0]
        conn.close()

        assert count == 1

    def test_init_cria_banco_se_inexistente(self, tmp_path: Path) -> None:
        """Instanciar com db_path deve criar banco e tabelas automaticamente."""
        db = tmp_path / "novo.db"
        assert not db.exists()

        TradingJournalService(db_path=db)

        assert db.exists()
        conn = sqlite3.connect(str(db))
        tabelas = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()
        assert "trading_journal_logs" in tabelas

    def test_save_entry_usa_write_lock(self, tmp_path: Path) -> None:
        """save_entry() deve acionar sqlite_write_lock durante a escrita."""
        db = tmp_path / "diarios.db"
        svc = TradingJournalService(db_path=db)
        narrativa = _narrativa_mock(svc)

        with patch(
            "src.application.services.trading_journal.sqlite_write_lock"
        ) as mock_lock:
            mock_lock.return_value.__enter__ = lambda s: None
            mock_lock.return_value.__exit__ = lambda s, *a: False
            svc.save_entry(narrativa, _dados_decisao())

        mock_lock.assert_called_once_with(db)

    def test_entry_id_unico_multiplas_entradas(self, tmp_path: Path) -> None:
        """Tres save_entry() devem gerar 3 entry_ids distintos."""
        db = tmp_path / "diarios.db"
        svc = TradingJournalService(db_path=db)

        for _ in range(3):
            narrativa = _narrativa_mock(svc)
            svc.save_entry(narrativa, _dados_decisao())

        conn = sqlite3.connect(str(db))
        ids = [
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT entry_id FROM trading_journal_logs"
            ).fetchall()
        ]
        conn.close()
        assert len(ids) == 3

    def test_retrocompatibilidade_sem_db_path(self) -> None:
        """Sem db_path, save_entry() deve funcionar apenas em memoria sem excecao."""
        svc = TradingJournalService()
        narrativa = _narrativa_mock(svc)

        entry = svc.save_entry(narrativa, _dados_decisao())

        assert entry is not None
        assert len(svc.entries) == 1
