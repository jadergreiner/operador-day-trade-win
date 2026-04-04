"""
Testes TDD para RLDiaryLearningService.

Cobre gatilho de retreinamento, exportacao de episodios, janela adaptativa,
relatorio de fechamento e o campo retreinamento_necessario do DiaryFeedback.

BLID-024 / ROADMAP-DIARIOS-04
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Optional

import pytest

from src.application.services.diary_feedback import (
    DiaryFeedback,
    create_diary_feedback_table,
    save_diary_feedback,
)
from src.application.services.rl_diary_learning_service import RLDiaryLearningService


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────

_CREATE_EPISODIOS_SQL = """
CREATE TABLE IF NOT EXISTS diario_episodios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    timestamp_entrada TEXT,
    timestamp_saida TEXT,
    direcao TEXT,
    preco_entrada REAL,
    preco_saida REAL,
    sl REAL,
    tp REAL,
    atr_entrada REAL,
    resultado_pts REAL,
    motivo_saida TEXT,
    fase_sessao TEXT,
    qualidade_movimento TEXT,
    exaustao INTEGER DEFAULT 0,
    pullback INTEGER DEFAULT 0,
    correlacao_estado TEXT,
    divergencia_critica INTEGER DEFAULT 0,
    risco_armadilha TEXT,
    preco_extremo INTEGER DEFAULT 0,
    desvio_vwap_pts REAL,
    ajuste_confianca_leitura REAL,
    confianca_entrada REAL,
    alinhamento_entrada REAL,
    momentum_entrada REAL,
    foi_acerto INTEGER DEFAULT 0,
    max_ganho_pts REAL DEFAULT 0,
    eficiencia REAL DEFAULT 0,
    data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def _criar_db_feedback(tmp_dir: str) -> str:
    """Cria banco SQLite temporario com tabela diary_feedback."""
    db_path = os.path.join(tmp_dir, "test_feedback.db")
    create_diary_feedback_table(db_path)
    return db_path


def _criar_db_episodios(tmp_dir: str) -> str:
    """Cria banco SQLite temporario com tabela diario_episodios."""
    db_path = os.path.join(tmp_dir, "test_episodios.db")
    conn = sqlite3.connect(db_path)
    conn.execute(_CREATE_EPISODIOS_SQL)
    conn.commit()
    conn.close()
    return db_path


def _inserir_feedback(
    db_path: str,
    nota: int,
    source: str = "rl_diary",
    data: str = "2026-04-05",
    retreinamento_necessario: bool = False,
) -> None:
    """Insere um feedback no banco para testes."""
    fb = DiaryFeedback(
        date=data,
        timestamp=f"{data}T12:00:00",
        source=source,
        nota_agente=nota,
        retreinamento_necessario=retreinamento_necessario,
    )
    save_diary_feedback(db_path, fb)


def _inserir_episodio(
    db_path: str,
    foi_acerto: int = 1,
    data: str = "2026-04-05",
) -> None:
    """Insere um episodio no banco para testes."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO diario_episodios (foi_acerto, data) VALUES (?, ?)",
        (foi_acerto, data),
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────
# Instancia global do servico
# ─────────────────────────────────────────────────────────────────

_svc = RLDiaryLearningService()


# ─────────────────────────────────────────────────────────────────
# Testes de gatilho de retreinamento
# ─────────────────────────────────────────────────────────────────


def test_gatilho_nao_ativado_sem_feedbacks() -> None:
    """Sem feedbacks no banco, o gatilho nao deve ser ativado."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _criar_db_feedback(tmp)
        resultado = _svc.avaliar_gatilho_retreinamento(db_path, n_ciclos=3)
        assert resultado is False


def test_gatilho_nao_ativado_notas_acima_threshold() -> None:
    """Com 3 ciclos de nota >= 6, o gatilho nao deve ser ativado."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _criar_db_feedback(tmp)
        for nota in (7, 8, 9):
            _inserir_feedback(db_path, nota=nota)
        resultado = _svc.avaliar_gatilho_retreinamento(db_path, n_ciclos=3, threshold_nota=6)
        assert resultado is False


def test_gatilho_ativado_tres_ciclos_nota_baixa() -> None:
    """Com 3 ciclos consecutivos de nota < 6, o gatilho deve ser ativado."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _criar_db_feedback(tmp)
        for nota in (3, 4, 5):
            _inserir_feedback(db_path, nota=nota)
        resultado = _svc.avaliar_gatilho_retreinamento(db_path, n_ciclos=3, threshold_nota=6)
        assert resultado is True


def test_gatilho_nao_ativado_dois_ciclos_nota_baixa() -> None:
    """Com apenas 2 ciclos de nota < 6 (n_ciclos=3), nao deve ativar."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _criar_db_feedback(tmp)
        # Dois ciclos baixos
        for nota in (3, 4):
            _inserir_feedback(db_path, nota=nota)
        resultado = _svc.avaliar_gatilho_retreinamento(db_path, n_ciclos=3, threshold_nota=6)
        assert resultado is False


def test_gatilho_ativado_threshold_customizado() -> None:
    """Com threshold=7 e 3 notas de 5, o gatilho deve ser ativado."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _criar_db_feedback(tmp)
        for _ in range(3):
            _inserir_feedback(db_path, nota=5)
        resultado = _svc.avaliar_gatilho_retreinamento(db_path, n_ciclos=3, threshold_nota=7)
        assert resultado is True


# ─────────────────────────────────────────────────────────────────
# Testes de exportacao de episodios
# ─────────────────────────────────────────────────────────────────


def test_exportar_episodios_cria_arquivo() -> None:
    """Exportar episodios deve criar arquivo JSON no diretorio data/training/."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _criar_db_episodios(tmp)
        _inserir_episodio(db_path)
        saida = Path(tmp) / "training"
        caminho = _svc.exportar_episodios_enriquecidos(
            db_path, data_alvo="2026-04-05", diretorio_saida=saida
        )
        assert caminho.exists()
        assert caminho.suffix == ".json"


def test_exportar_episodios_schema_version() -> None:
    """JSON exportado deve conter schema_version='1.0'."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _criar_db_episodios(tmp)
        saida = Path(tmp) / "training"
        caminho = _svc.exportar_episodios_enriquecidos(
            db_path, data_alvo="2026-04-05", diretorio_saida=saida
        )
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        assert dados["schema_version"] == "1.0"


def test_exportar_episodios_sem_dados() -> None:
    """Sem episodios na data, JSON deve ter total_episodios=0 e lista vazia."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _criar_db_episodios(tmp)
        saida = Path(tmp) / "training"
        caminho = _svc.exportar_episodios_enriquecidos(
            db_path, data_alvo="2026-04-05", diretorio_saida=saida
        )
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        assert dados["total_episodios"] == 0
        assert dados["episodios"] == []


def test_exportar_episodios_campos_completos() -> None:
    """Episodio exportado deve conter campos esperados da tabela."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _criar_db_episodios(tmp)
        _inserir_episodio(db_path, foi_acerto=1, data="2026-04-05")
        saida = Path(tmp) / "training"
        caminho = _svc.exportar_episodios_enriquecidos(
            db_path, data_alvo="2026-04-05", diretorio_saida=saida
        )
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        assert dados["total_episodios"] == 1
        ep = dados["episodios"][0]
        assert "foi_acerto" in ep
        assert "data" in ep


# ─────────────────────────────────────────────────────────────────
# Testes de janela adaptativa
# ─────────────────────────────────────────────────────────────────


def test_win_rate_adaptativo_lista_vazia() -> None:
    """Lista vazia deve retornar 0.0."""
    resultado = _svc.calcular_win_rate_adaptativo([])
    assert resultado == 0.0


def test_win_rate_adaptativo_todos_acertos() -> None:
    """Todos os episodios sendo acertos deve retornar ~100.0."""
    episodios = [{"foi_acerto": 1} for _ in range(5)]
    resultado = _svc.calcular_win_rate_adaptativo(episodios)
    assert abs(resultado - 100.0) < 0.001


def test_win_rate_adaptativo_todos_erros() -> None:
    """Todos os episodios sendo erros deve retornar 0.0."""
    episodios = [{"foi_acerto": 0} for _ in range(5)]
    resultado = _svc.calcular_win_rate_adaptativo(episodios)
    assert resultado == 0.0


def test_win_rate_adaptativo_pesos_decrescentes() -> None:
    """Acertos no inicio (mais recentes) devem gerar win_rate maior que acertos no fim."""
    # Acertos nos 3 primeiros, erros nos 3 ultimos
    episodios_acertos_inicio = [
        {"foi_acerto": 1},
        {"foi_acerto": 1},
        {"foi_acerto": 1},
        {"foi_acerto": 0},
        {"foi_acerto": 0},
        {"foi_acerto": 0},
    ]
    # Erros nos 3 primeiros, acertos nos 3 ultimos
    episodios_acertos_fim = [
        {"foi_acerto": 0},
        {"foi_acerto": 0},
        {"foi_acerto": 0},
        {"foi_acerto": 1},
        {"foi_acerto": 1},
        {"foi_acerto": 1},
    ]
    wr_inicio = _svc.calcular_win_rate_adaptativo(episodios_acertos_inicio)
    wr_fim = _svc.calcular_win_rate_adaptativo(episodios_acertos_fim)
    assert wr_inicio > wr_fim


# ─────────────────────────────────────────────────────────────────
# Testes de relatorio de fechamento
# ─────────────────────────────────────────────────────────────────


def test_relatorio_fechamento_cria_arquivo() -> None:
    """gerar_relatorio_fechamento deve criar arquivo .md no diretorio outputs/."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _criar_db_feedback(tmp)
        saida = Path(tmp) / "outputs"
        caminho = _svc.gerar_relatorio_fechamento(
            db_path, data_alvo="2026-04-05", diretorio_saida=saida
        )
        assert caminho.exists()
        assert caminho.suffix == ".md"


def test_relatorio_fechamento_conteudo() -> None:
    """Relatorio deve conter Range, Eficiencia, Episodios e Retreinamentos."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _criar_db_feedback(tmp)
        _inserir_feedback(
            db_path, nota=7, data="2026-04-05", retreinamento_necessario=False
        )
        saida = Path(tmp) / "outputs"
        caminho = _svc.gerar_relatorio_fechamento(
            db_path, data_alvo="2026-04-05", diretorio_saida=saida
        )
        conteudo = caminho.read_text(encoding="utf-8")
        assert "Range" in conteudo
        assert "Eficiencia" in conteudo
        assert "Episodios" in conteudo
        assert "Retreinamentos" in conteudo


# ─────────────────────────────────────────────────────────────────
# Testes do campo retreinamento_necessario
# ─────────────────────────────────────────────────────────────────


def test_retreinamento_necessario_campo_existe() -> None:
    """DiaryFeedback deve ter campo retreinamento_necessario com default False."""
    fb = DiaryFeedback()
    assert hasattr(fb, "retreinamento_necessario")
    assert fb.retreinamento_necessario is False


def test_retreinamento_necessario_salvo_banco() -> None:
    """Campo retreinamento_necessario deve persistir no SQLite e ser lido corretamente."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = _criar_db_feedback(tmp)
        fb = DiaryFeedback(
            date="2026-04-05",
            timestamp="2026-04-05T12:00:00",
            source="rl_diary",
            nota_agente=4,
            retreinamento_necessario=True,
        )
        save_diary_feedback(db_path, fb)

        # Ler de volta
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT retreinamento_necessario FROM diary_feedback ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert int(row["retreinamento_necessario"]) == 1
