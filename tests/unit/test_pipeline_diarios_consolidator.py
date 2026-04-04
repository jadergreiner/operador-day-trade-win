"""Testes TDD para PipelineDiariosConsolidator.

BLID-027 / ROADMAP-DIARIOS-07 — Consolidador de Fechamento de Pipeline dos Diarios.

Execucao:
    python3 -m pytest tests/unit/test_pipeline_diarios_consolidator.py -v
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Mocks de dependencias externas para ambiente de testes.
# ---------------------------------------------------------------------------
_MOCKED_EXTERNAL = [
    "sqlalchemy",
    "sqlalchemy.orm",
    "sqlalchemy.ext",
    "sqlalchemy.ext.declarative",
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "sqlalchemy.dialects",
    "numpy",
]
for _mod in _MOCKED_EXTERNAL:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import pytest

from src.application.services.pipeline_diarios_consolidator import (
    PipelineDiariosConsolidator,
    _conectar,
    _tabela_existe,
)


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------


def _criar_banco_basico(db: Path) -> None:
    """Cria banco com tabelas minimas para testes."""
    conn = sqlite3.connect(str(db))
    conn.executescript(
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
        );
        CREATE TABLE IF NOT EXISTS journal_trade_correlation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journal_entry_id TEXT NOT NULL,
            trade_ticket INTEGER,
            outcome TEXT NOT NULL,
            pnl_reais REAL,
            narrativa_estava_alinhada INTEGER,
            created_at TEXT NOT NULL,
            UNIQUE(journal_entry_id)
        );
        CREATE TABLE IF NOT EXISTS ai_reflection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id TEXT NOT NULL UNIQUE,
            timestamp TEXT NOT NULL,
            mood TEXT NOT NULL,
            my_decision TEXT NOT NULL,
            my_confidence REAL NOT NULL,
            my_alignment REAL NOT NULL,
            honest_assessment TEXT NOT NULL,
            data_relevance TEXT NOT NULL,
            am_i_useful TEXT NOT NULL,
            my_data_correlation TEXT NOT NULL,
            one_liner TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reflection_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id TEXT NOT NULL UNIQUE,
            prompt TEXT NOT NULL,
            category TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'basico',
            data_criacao TEXT NOT NULL,
            score_relevancia REAL NOT NULL DEFAULT 0.0,
            total_respostas INTEGER NOT NULL DEFAULT 0,
            respostas_win INTEGER NOT NULL DEFAULT 0,
            respostas_loss INTEGER NOT NULL DEFAULT 0,
            obsoleta INTEGER NOT NULL DEFAULT 0,
            ativa INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS diary_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            date TEXT NOT NULL,
            nota_agente REAL,
            market_range_pts REAL,
            eficiencia_pct REAL,
            n_episodes INTEGER,
            retreinamento_necessario INTEGER DEFAULT 0,
            acao_sugerida TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()
    conn.close()


def _inserir_journal_entry(
    db: Path,
    entry_id: str,
    timestamp: str,
    decision: str = "BUY",
) -> None:
    """Insere uma entrada de journal para testes."""
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        INSERT INTO trading_journal_logs (
            entry_id, timestamp, symbol, headline, market_feeling,
            decision, confidence, macro_bias, technical_bias,
            alignment_score, outcome_trade, created_at
        ) VALUES (?, ?, 'WIN$N', 'Titulo teste', 'BULLISH',
                  ?, 0.8, 'BULLISH', 'BULLISH', 0.9, 'SEM_TRADE', datetime('now'))
        """,
        (entry_id, timestamp, decision),
    )
    conn.commit()
    conn.close()


def _inserir_correlacao(
    db: Path,
    entry_id: str,
    outcome: str,
    pnl: float,
    alinhada: int = 1,
) -> None:
    """Insere correlacao journal-trade."""
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        INSERT INTO journal_trade_correlation (
            journal_entry_id, trade_ticket, outcome,
            pnl_reais, narrativa_estava_alinhada, created_at
        ) VALUES (?, 1001, ?, ?, ?, datetime('now'))
        """,
        (entry_id, outcome, pnl, alinhada),
    )
    conn.commit()
    conn.close()


def _inserir_ai_reflection(
    db: Path,
    entry_id: str,
    timestamp: str,
    mood: str = "Confiante",
    decisao: str = "BUY",
    confianca: float = 0.8,
    alinhamento: float = 0.9,
) -> None:
    """Insere uma reflexao de IA."""
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        INSERT INTO ai_reflection_logs (
            entry_id, timestamp, mood, my_decision, my_confidence,
            my_alignment, honest_assessment, data_relevance,
            am_i_useful, my_data_correlation, one_liner, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'Avaliacao', 'ALTA', 'SIM', 'POSITIVA',
                  'Frase ciclo', datetime('now'))
        """,
        (entry_id, timestamp, mood, decisao, confianca, alinhamento),
    )
    conn.commit()
    conn.close()


def _inserir_diary_feedback(
    db: Path,
    source: str,
    data: str,
    nota: float = 7.0,
    retreinamento: int = 0,
) -> None:
    """Insere feedback de diario."""
    conn = sqlite3.connect(str(db))
    conn.execute(
        """
        INSERT INTO diary_feedback (
            source, date, nota_agente, market_range_pts,
            eficiencia_pct, n_episodes, retreinamento_necessario, created_at
        ) VALUES (?, ?, ?, 50.0, 0.65, 10, ?, datetime('now'))
        """,
        (source, data, nota, retreinamento),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


class TestConsolidarFechamentoPregao:
    """Testes para consolidar_fechamento_pregao()."""

    def test_banco_inexistente_levanta_file_not_found(
        self, tmp_path: Path
    ) -> None:
        """consolidar_fechamento_pregao deve lancar FileNotFoundError se banco ausente."""
        svc = PipelineDiariosConsolidator()
        db_inexistente = tmp_path / "nao_existe.db"

        with pytest.raises(FileNotFoundError):
            svc.consolidar_fechamento_pregao("2026-04-05", db_inexistente)

    def test_banco_vazio_retorna_zeros(self, tmp_path: Path) -> None:
        """Banco vazio (sem tabelas) deve retornar metricas zeradas sem excecao."""
        db = tmp_path / "trading_diarios.db"
        conn = sqlite3.connect(str(db))
        conn.close()

        svc = PipelineDiariosConsolidator()
        resultado = svc.consolidar_fechamento_pregao("2026-04-05", db)

        assert resultado["journal"]["total_entradas"] == 0
        assert resultado["ai_reflection"]["total_reflexoes"] == 0
        assert resultado["rl_diary"]["ciclos_registrados"] == 0
        assert resultado["order_manager"]["n_episodios"] == 0

    def test_retorna_todas_secoes(self, tmp_path: Path) -> None:
        """Resultado deve conter todas as 5 secoes obrigatorias mais resumo."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_basico(db)
        svc = PipelineDiariosConsolidator()

        resultado = svc.consolidar_fechamento_pregao("2026-04-05", db)

        for secao in ("journal", "ai_reflection", "rl_diary",
                      "macro_guardian", "order_manager", "resumo"):
            assert secao in resultado, f"Secao ausente: {secao}"

    def test_retorna_data_e_gerado_em(self, tmp_path: Path) -> None:
        """Resultado deve conter campo 'data' e 'gerado_em'."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_basico(db)
        svc = PipelineDiariosConsolidator()

        resultado = svc.consolidar_fechamento_pregao("2026-04-05", db)

        assert resultado["data"] == "2026-04-05"
        assert "gerado_em" in resultado
        assert len(resultado["gerado_em"]) > 0

    def test_metricas_journal_com_dados(self, tmp_path: Path) -> None:
        """Com entradas e correlacoes inseridas, metricas do journal devem bater."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_basico(db)
        data = "2026-04-05"
        ts = f"{data}T10:00:00"

        _inserir_journal_entry(db, "J001", ts, "BUY")
        _inserir_journal_entry(db, "J002", ts, "SELL")
        _inserir_correlacao(db, "J001", "WIN", 150.0, alinhada=1)
        _inserir_correlacao(db, "J002", "LOSS", -80.0, alinhada=0)

        svc = PipelineDiariosConsolidator()
        resultado = svc.consolidar_fechamento_pregao(data, db)

        journal = resultado["journal"]
        assert journal["total_entradas"] == 2
        assert journal["win"] == 1
        assert journal["loss"] == 1
        assert abs(journal["pnl_total"] - 70.0) < 0.01

    def test_metricas_ai_reflection_com_dados(self, tmp_path: Path) -> None:
        """Com reflexoes inseridas, metricas de AI Reflection devem bater."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_basico(db)
        data = "2026-04-05"
        ts = f"{data}T09:00:00"

        _inserir_ai_reflection(db, "R001", ts, mood="Confiante", confianca=0.9)
        _inserir_ai_reflection(db, "R002", ts, mood="Frustrado", confianca=0.5)

        svc = PipelineDiariosConsolidator()
        resultado = svc.consolidar_fechamento_pregao(data, db)

        ai = resultado["ai_reflection"]
        assert ai["total_reflexoes"] == 2
        assert abs(ai["confianca_media"] - 0.7) < 0.01
        assert "Confiante" in ai["moods"]
        assert "Frustrado" in ai["moods"]

    def test_metricas_rl_diary_com_feedback(self, tmp_path: Path) -> None:
        """Com diary_feedback de source='rl_diary', metricas devem ser carregadas."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_basico(db)
        data = "2026-04-05"

        _inserir_diary_feedback(db, "rl_diary", data, nota=8.0)
        _inserir_diary_feedback(db, "rl_diary", data, nota=6.0)

        svc = PipelineDiariosConsolidator()
        resultado = svc.consolidar_fechamento_pregao(data, db)

        rl = resultado["rl_diary"]
        assert rl["ciclos_registrados"] == 2
        assert abs(rl["nota_media"] - 7.0) < 0.01

    def test_resumo_contem_metricas_numericas(self, tmp_path: Path) -> None:
        """Resumo deve conter todas as metricas numericas esperadas."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_basico(db)
        svc = PipelineDiariosConsolidator()

        resultado = svc.consolidar_fechamento_pregao("2026-04-05", db)

        resumo = resultado["resumo"]
        campos_esperados = [
            "total_entradas_journal",
            "win_rate_journal",
            "pnl_total_reais",
            "total_reflexoes_ia",
            "confianca_media_ia",
            "ciclos_rl_registrados",
            "alertas_macro_warning",
            "kill_switch_ativo",
            "n_episodios_order_manager",
        ]
        for campo in campos_esperados:
            assert campo in resumo, f"Campo ausente no resumo: {campo}"


class TestGerarRelatorioMarkdown:
    """Testes para gerar_relatorio_markdown()."""

    def test_gera_arquivo_md_em_outputs_diarios(
        self, tmp_path: Path
    ) -> None:
        """Deve gerar arquivo .md em diretorio outputs/diarios."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_basico(db)
        dir_saida = tmp_path / "outputs" / "diarios"

        svc = PipelineDiariosConsolidator()
        arquivo = svc.gerar_relatorio_markdown("2026-04-05", db, dir_saida)

        assert arquivo.exists()
        assert arquivo.suffix == ".md"
        assert arquivo.name == "fechamento_diario_20260405.md"

    def test_relatorio_contem_secoes_obrigatorias(
        self, tmp_path: Path
    ) -> None:
        """Relatorio deve conter titulos das 5 secoes obrigatorias."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_basico(db)
        dir_saida = tmp_path / "outputs" / "diarios"

        svc = PipelineDiariosConsolidator()
        arquivo = svc.gerar_relatorio_markdown("2026-04-05", db, dir_saida)
        conteudo = arquivo.read_text(encoding="utf-8")

        for secao in [
            "Journal Correlacoes",
            "AI Reflection",
            "RL Diary",
            "Macro Guardian",
            "Order Manager",
        ]:
            assert secao in conteudo, f"Secao ausente no relatorio: {secao}"

    def test_relatorio_contem_data(self, tmp_path: Path) -> None:
        """Relatorio deve conter a data de pregao no cabecalho."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_basico(db)
        dir_saida = tmp_path / "outputs" / "diarios"

        svc = PipelineDiariosConsolidator()
        arquivo = svc.gerar_relatorio_markdown("2026-04-05", db, dir_saida)
        conteudo = arquivo.read_text(encoding="utf-8")

        assert "2026-04-05" in conteudo

    def test_cria_diretorio_saida_se_inexistente(
        self, tmp_path: Path
    ) -> None:
        """Diretorio de saida deve ser criado automaticamente se nao existir."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_basico(db)
        dir_saida = tmp_path / "novo" / "diretorio" / "saida"
        assert not dir_saida.exists()

        svc = PipelineDiariosConsolidator()
        svc.gerar_relatorio_markdown("2026-04-05", db, dir_saida)

        assert dir_saida.exists()


class TestObterResumoEstatisticas:
    """Testes para obter_resumo_estatisticas()."""

    def test_retorna_subconjunto_do_consolidado(self, tmp_path: Path) -> None:
        """obter_resumo_estatisticas deve retornar dicionario de metricas."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_basico(db)
        svc = PipelineDiariosConsolidator()

        resumo = svc.obter_resumo_estatisticas("2026-04-05", db)

        assert isinstance(resumo, dict)
        assert len(resumo) > 0

    def test_banco_inexistente_levanta_excecao(self, tmp_path: Path) -> None:
        """obter_resumo_estatisticas deve propagar FileNotFoundError."""
        svc = PipelineDiariosConsolidator()
        db_inexistente = tmp_path / "nao_existe.db"

        with pytest.raises(FileNotFoundError):
            svc.obter_resumo_estatisticas("2026-04-05", db_inexistente)
