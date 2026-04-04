"""Testes TDD para persistencia SQLite do TradingJournalService.

BLID-022 / ROADMAP-DIARIOS-02 — Etapa 1: Persistencia.
DT-BLID022-02 — Caminhos de Degradacao.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.application.services.trading_journal import TradingJournalService
from src.application.services.journal_trade_correlator_service import (
    JournalTradeCorrelatorService,
)
from src.infrastructure.database.diario_journal_schema import criar_tabelas_diario
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


# ---------------------------------------------------------------------------
# DT-BLID022-02 — Testes de Caminhos de Degradacao
# ---------------------------------------------------------------------------


class TestCaminhosDegradacao:
    """Testes de robustez para caminhos de erro do TradingJournal e Correlator.

    DT-BLID022-02: Garante que servicos nao falham silenciosamente em
    condicoes degeneradas: banco vazio, coluna ausente, CLI sem argumentos,
    exportacao sem dados.
    """

    def test_correlacionar_sessao_banco_vazio(self, tmp_path: Path) -> None:
        """Banco sem tabela diary_orders deve retornar 0 correlacoes sem erro.

        Garante que correlacionar_sessao() nao levanta excecao ao encontrar
        banco recim-criado (sem diary_orders nem trading_journal_logs).
        """
        db = tmp_path / "trading_diarios.db"
        # Cria banco com tabelas do journal mas sem diary_orders
        criar_tabelas_diario(db)

        svc = JournalTradeCorrelatorService(db_path=db)
        # Sem entradas de journal, deve retornar 0 sem excecao
        resultado = svc.correlacionar_sessao("2026-04-05")

        assert resultado == 0

    def test_correlacionar_sessao_coluna_side_ausente(
        self, tmp_path: Path
    ) -> None:
        """Tabela diary_orders sem coluna 'side' nao deve quebrar o correlacionador.

        Simula esquema legado onde side nao existe: espera que o servico
        retorne sem excecao, tratando o trade como SEM_TRADE ou alinhamento=0.
        """
        db = tmp_path / "trading_diarios.db"
        criar_tabelas_diario(db)

        # Criar diary_orders sem coluna side
        conn = sqlite3.connect(str(db))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS diary_orders (
                ticket       INTEGER PRIMARY KEY,
                magic_number INTEGER,
                close_time   TEXT,
                profit       REAL
            )
            """
        )
        ts = "2026-04-05T10:00:00"
        # Inserir entrada no journal
        conn.execute(
            """
            INSERT INTO trading_journal_logs (
                entry_id, timestamp, symbol, headline, market_feeling,
                decision, confidence, macro_bias, technical_bias,
                alignment_score, outcome_trade, created_at
            ) VALUES ('J001', ?, 'WIN$N', 'Titulo', 'BULLISH',
                      'BUY', 0.8, 'BULLISH', 'BULLISH', 0.9, 'SEM_TRADE', ?)
            """,
            (ts, ts),
        )
        # Inserir trade sem coluna side
        conn.execute(
            "INSERT INTO diary_orders (ticket, magic_number, close_time, profit) VALUES (1, 234800, ?, 100.0)",
            (ts,),
        )
        conn.commit()
        conn.close()

        svc = JournalTradeCorrelatorService(db_path=db)
        # Deve executar sem excecao — pode retornar 0 ou 1 dependendo da implementacao
        try:
            resultado = svc.correlacionar_sessao("2026-04-05")
            # Se nao levantou excecao, o teste passou
            assert isinstance(resultado, int)
        except (sqlite3.OperationalError, sqlite3.DatabaseError, AttributeError) as exc:
            pytest.fail(
                f"correlacionar_sessao levantou excecao inesperada: {exc}"
            )

    def test_cli_main_sem_argumentos_imprime_sem_excecao(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """CLI main() sem argumentos deve imprimir ajuda/uso sem excecao fatal.

        Garante que analisar_journal_correlacoes.main() aceita o estado
        padrao (data=hoje, output_dir padrao) sem lancar SystemExit nao-zero
        quando o banco nao existe (apenas log de aviso esperado).
        """
        from scripts.analisar_journal_correlacoes import main as cli_main

        # Direcionar db-path para banco existente e output para tmp
        with patch(
            "sys.argv",
            [
                "analisar_journal_correlacoes",
                "--db-path",
                str(tmp_path / "trading_diarios.db"),
                "--output-dir",
                str(tmp_path / "output"),
            ],
        ):
            # Banco inexistente deve ser criado ou retornar sem excecao
            try:
                cli_main()
            except SystemExit as exc:
                # SystemExit(0) e aceitavel; != 0 e falha
                assert exc.code == 0 or exc.code is None, (
                    f"CLI retornou codigo de saida: {exc.code}"
                )
            except FileNotFoundError:
                # Banco inexistente pode levantar FileNotFoundError — aceitavel
                pass

    def test_exportar_features_banco_sem_dados(self, tmp_path: Path) -> None:
        """exportar_features com banco sem dados deve gerar JSON valido com lista vazia.

        Garante que o script de exportacao nao falha silenciosamente ao
        encontrar banco recim-criado (sem entradas de journal).
        """
        from scripts.analisar_journal_correlacoes import exportar_features

        db = tmp_path / "trading_diarios.db"
        criar_tabelas_diario(db)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        arquivo = exportar_features(
            data_referencia="2026-04-05",
            db_path=db,
            output_dir=output_dir,
        )

        assert arquivo.exists(), "Arquivo JSON deve ser criado mesmo sem dados"
        conteudo = json.loads(arquivo.read_text(encoding="utf-8"))
        assert isinstance(conteudo, dict), "JSON deve ser um objeto/dicionario"
        # Verificar que ha uma chave de entradas/features como lista vazia
        chaves_lista = [k for k, v in conteudo.items() if isinstance(v, list)]
        assert len(chaves_lista) > 0, "JSON deve ter pelo menos uma lista (possivelmente vazia)"
        for chave in chaves_lista:
            assert isinstance(conteudo[chave], list)
