"""Testes TDD para DiariosHealthCheckService.

BLID-028 / ROADMAP-DIARIOS-08 — Diagnostico de Saude Pre-Sessao dos Diarios.

Execucao:
    python3 -m pytest tests/unit/test_diarios_health_check_service.py -v
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
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

from src.application.services.diarios_health_check_service import (
    DiariosHealthCheckService,
    _STATUS_CRITICAL,
    _STATUS_OK,
    _STATUS_WARNING,
)


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------


def _criar_banco_com_tabelas(db: Path) -> None:
    """Cria banco com todas as tabelas obrigatorias."""
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS trading_journal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id TEXT NOT NULL UNIQUE,
            timestamp TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS journal_trade_correlation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journal_entry_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ai_reflection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id TEXT NOT NULL UNIQUE,
            timestamp TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reflection_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id TEXT NOT NULL UNIQUE,
            data_criacao TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS diary_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.commit()
    conn.close()


def _inserir_registro_recente(
    db: Path,
    tabela: str,
    coluna_ts: str = "created_at",
) -> None:
    """Insere registro com timestamp recente (agora)."""
    conn = sqlite3.connect(str(db))
    agora = datetime.now().isoformat()
    if tabela == "trading_journal_logs":
        conn.execute(
            f"INSERT INTO {tabela} (entry_id, timestamp, created_at) VALUES (?, ?, ?)",
            ("EID001", agora, agora),
        )
    elif tabela == "ai_reflection_logs":
        conn.execute(
            f"INSERT INTO {tabela} (entry_id, timestamp, created_at) VALUES (?, ?, ?)",
            ("REID001", agora, agora),
        )
    elif tabela == "reflection_questions":
        conn.execute(
            f"INSERT INTO {tabela} (question_id, data_criacao) VALUES (?, ?)",
            ("QID001", agora),
        )
    elif tabela == "diary_feedback":
        conn.execute(
            f"INSERT INTO {tabela} (source, date, created_at) VALUES (?, ?, ?)",
            ("rl_diary", "2026-04-05", agora),
        )
    else:
        conn.execute(
            f"INSERT INTO {tabela} (journal_entry_id, created_at) VALUES (?, ?)",
            ("JID001", agora),
        )
    conn.commit()
    conn.close()


def _inserir_registro_antigo(
    db: Path,
    tabela: str,
) -> None:
    """Insere registro com timestamp antigo (48h atras)."""
    conn = sqlite3.connect(str(db))
    antigo = (datetime.now() - timedelta(hours=48)).isoformat()
    if tabela == "trading_journal_logs":
        conn.execute(
            "INSERT INTO trading_journal_logs (entry_id, timestamp, created_at) VALUES (?, ?, ?)",
            ("OLD001", antigo, antigo),
        )
    else:
        conn.execute(
            f"INSERT INTO {tabela} (journal_entry_id, created_at) VALUES (?, ?)",
            ("OLDJID001", antigo),
        )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


class TestVerificarBancos:
    """Testes para verificar_bancos()."""

    def test_banco_existente_retorna_true(self, tmp_path: Path) -> None:
        """Banco existente e valido deve retornar True."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_com_tabelas(db)

        svc = DiariosHealthCheckService()
        resultado = svc.verificar_bancos(db)

        assert resultado["trading_diarios.db"] is True

    def test_banco_ausente_retorna_false(self, tmp_path: Path) -> None:
        """Banco inexistente deve retornar False."""
        db = tmp_path / "trading_diarios.db"

        svc = DiariosHealthCheckService()
        resultado = svc.verificar_bancos(db)

        assert resultado["trading_diarios.db"] is False


class TestVerificarTabelas:
    """Testes para verificar_tabelas()."""

    def test_banco_ausente_retorna_tudo_false(self, tmp_path: Path) -> None:
        """Banco inexistente deve retornar False para todas as tabelas."""
        db = tmp_path / "trading_diarios.db"

        svc = DiariosHealthCheckService()
        resultado = svc.verificar_tabelas(db)

        assert all(not v for v in resultado.values())

    def test_banco_com_todas_tabelas_retorna_tudo_true(
        self, tmp_path: Path
    ) -> None:
        """Banco com todas as tabelas deve retornar True para cada uma."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_com_tabelas(db)

        svc = DiariosHealthCheckService()
        resultado = svc.verificar_tabelas(db)

        for tabela, existe in resultado.items():
            assert existe, f"Tabela deve existir: {tabela}"

    def test_banco_parcial_retorna_mix_true_false(self, tmp_path: Path) -> None:
        """Banco com apenas algumas tabelas deve refletir quais existem."""
        db = tmp_path / "trading_diarios.db"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE trading_journal_logs (id INTEGER PRIMARY KEY, entry_id TEXT, timestamp TEXT, created_at TEXT)"
        )
        conn.commit()
        conn.close()

        svc = DiariosHealthCheckService()
        resultado = svc.verificar_tabelas(db)

        assert resultado["trading_journal_logs"] is True
        assert resultado["ai_reflection_logs"] is False


class TestVerificarUltimoRegistro:
    """Testes para verificar_ultimo_registro()."""

    def test_registro_recente_retorna_true(self, tmp_path: Path) -> None:
        """Registro inserido agora deve ser detectado como recente."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_com_tabelas(db)
        _inserir_registro_recente(db, "trading_journal_logs")

        svc = DiariosHealthCheckService()
        assert svc.verificar_ultimo_registro(db, "trading_journal_logs") is True

    def test_registro_antigo_retorna_false(self, tmp_path: Path) -> None:
        """Registro de 48h atras deve ser detectado como fora da janela de 24h."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_com_tabelas(db)
        _inserir_registro_antigo(db, "trading_journal_logs")

        svc = DiariosHealthCheckService()
        assert svc.verificar_ultimo_registro(db, "trading_journal_logs") is False

    def test_tabela_ausente_retorna_false(self, tmp_path: Path) -> None:
        """Tabela inexistente deve retornar False sem excecao."""
        db = tmp_path / "trading_diarios.db"
        conn = sqlite3.connect(str(db))
        conn.close()

        svc = DiariosHealthCheckService()
        assert svc.verificar_ultimo_registro(db, "tabela_inexistente") is False

    def test_banco_ausente_retorna_false(self, tmp_path: Path) -> None:
        """Banco inexistente deve retornar False sem excecao."""
        db = tmp_path / "nao_existe.db"

        svc = DiariosHealthCheckService()
        assert svc.verificar_ultimo_registro(db, "trading_journal_logs") is False


class TestExecutarDiagnosticoCompleto:
    """Testes para executar_diagnostico_completo()."""

    def test_banco_ausente_retorna_critical(self, tmp_path: Path) -> None:
        """Banco ausente deve resultar em status CRITICAL."""
        db = tmp_path / "trading_diarios.db"

        svc = DiariosHealthCheckService()
        resultado = svc.executar_diagnostico_completo(db)

        assert resultado["status_geral"] == _STATUS_CRITICAL

    def test_banco_completo_sem_problemas_retorna_ok_ou_warning(
        self, tmp_path: Path
    ) -> None:
        """Banco com todas as tabelas deve retornar OK ou WARNING (sem CRITICAL)."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_com_tabelas(db)

        svc = DiariosHealthCheckService()
        resultado = svc.executar_diagnostico_completo(db)

        assert resultado["status_geral"] in (_STATUS_OK, _STATUS_WARNING)
        assert resultado["status_geral"] != _STATUS_CRITICAL

    def test_resultado_contem_campos_obrigatorios(self, tmp_path: Path) -> None:
        """Resultado do diagnostico deve conter todos os campos obrigatorios."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_com_tabelas(db)

        svc = DiariosHealthCheckService()
        resultado = svc.executar_diagnostico_completo(db)

        for campo in (
            "status_geral", "bancos", "tabelas", "atualidade",
            "problemas", "recomendacoes", "verificado_em"
        ):
            assert campo in resultado, f"Campo ausente: {campo}"

    def test_tabelas_ausentes_geram_warnings(self, tmp_path: Path) -> None:
        """Tabelas ausentes devem gerar entradas em 'problemas' com WARNING."""
        db = tmp_path / "trading_diarios.db"
        conn = sqlite3.connect(str(db))
        conn.close()  # banco existe mas sem tabelas

        svc = DiariosHealthCheckService()
        resultado = svc.executar_diagnostico_completo(db)

        assert len(resultado["problemas"]) > 0
        assert any("WARNING" in p or "CRITICAL" in p for p in resultado["problemas"])


class TestGerarRelatorioDiagnostico:
    """Testes para gerar_relatorio_diagnostico()."""

    def test_relatorio_contem_status_geral(self, tmp_path: Path) -> None:
        """Relatorio textual deve conter o status geral."""
        db = tmp_path / "trading_diarios.db"
        _criar_banco_com_tabelas(db)

        svc = DiariosHealthCheckService()
        relatorio = svc.gerar_relatorio_diagnostico(db)

        assert "Status geral" in relatorio or "status" in relatorio.lower()

    def test_relatorio_e_string_nao_vazia(self, tmp_path: Path) -> None:
        """Relatorio deve ser uma string nao vazia."""
        db = tmp_path / "trading_diarios.db"
        svc = DiariosHealthCheckService()
        relatorio = svc.gerar_relatorio_diagnostico(db)

        assert isinstance(relatorio, str)
        assert len(relatorio) > 0

    def test_relatorio_banco_ausente_indica_problema(
        self, tmp_path: Path
    ) -> None:
        """Relatorio com banco ausente deve mencionar o problema."""
        db = tmp_path / "trading_diarios.db"

        svc = DiariosHealthCheckService()
        relatorio = svc.gerar_relatorio_diagnostico(db)

        assert "ERR" in relatorio or "CRITICAL" in relatorio or "ausente" in relatorio.lower()
