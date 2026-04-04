"""Testes TDD para AI Reflection — persistencia e relatorio semanal.

Cobre BLID-023 / ROADMAP-DIARIOS-03.

Execucao:
    python3 -m pytest tests/unit/test_ai_reflection_persistencia.py -v
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Patch de dependencias externas ausentes no ambiente de testes.
# Os modulos de AI Reflection usam apenas stdlib (sqlite3, pathlib, datetime),
# mas os __init__.py de src.infrastructure e src.application.services importam
# dependencias pesadas (sqlalchemy, numpy, etc.) nao instaladas neste CI.
# Os mocks abaixo permitem carregar os modulos sem erros de importacao.
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

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.infrastructure.database.ai_reflection_schema import (
    criar_tabelas_ai_reflection,
    obter_conexao_ai_reflection,
)
from src.application.services.ai_reflection_persistence_service import (
    AIReflectionPersistenceService,
)
from src.application.services.ai_reflection_weekly_report import (
    AIReflectionWeeklyReport,
)
from src.application.services.diary_feedback import (
    DiaryFeedback,
    save_diary_feedback,
    load_latest_feedback,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agora() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _reflexao_padrao(
    entry_id: str = "entry-001",
    mood: str = "Confiante",
    decisao: str = "BUY",
    data_relevance: str = "ALTA",
) -> dict:
    return dict(
        entry_id=entry_id,
        timestamp=_agora(),
        mood=mood,
        decisao=decisao,
        confianca=0.75,
        alinhamento=0.8,
        avaliacao_honesta="Mercado favoravel",
        relevancia_dados=data_relevance,
        sou_util="Sim",
        correlacao_dados="Alta correlacao",
        frase_ciclo="Ciclo positivo",
    )


# ---------------------------------------------------------------------------
# 1. Testes de schema — criar_tabelas_ai_reflection
# ---------------------------------------------------------------------------


def test_criar_tabelas_cria_ai_reflection_logs(tmp_path: Path) -> None:
    """Tabela ai_reflection_logs deve existir apos criar_tabelas."""
    db = tmp_path / "db" / "test.db"
    criar_tabelas_ai_reflection(db)

    conn = sqlite3.connect(str(db))
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_reflection_logs'"
    )
    resultado = cursor.fetchone()
    conn.close()

    assert resultado is not None, "Tabela ai_reflection_logs nao foi criada"


def test_criar_tabelas_cria_reflection_questions(tmp_path: Path) -> None:
    """Tabela reflection_questions deve existir apos criar_tabelas."""
    db = tmp_path / "db" / "test.db"
    criar_tabelas_ai_reflection(db)

    conn = sqlite3.connect(str(db))
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='reflection_questions'"
    )
    resultado = cursor.fetchone()
    conn.close()

    assert resultado is not None, "Tabela reflection_questions nao foi criada"


def test_criar_tabelas_e_idempotente(tmp_path: Path) -> None:
    """Chamar criar_tabelas duas vezes nao deve levantar excecao."""
    db = tmp_path / "db" / "test.db"
    criar_tabelas_ai_reflection(db)
    criar_tabelas_ai_reflection(db)  # nao deve levantar excecao


# ---------------------------------------------------------------------------
# 2. Testes de AIReflectionPersistenceService — reflexoes
# ---------------------------------------------------------------------------


def test_salvar_reflexao_persiste_todos_campos(tmp_path: Path) -> None:
    """Todos os campos de uma reflexao devem ser persistidos corretamente."""
    db = tmp_path / "test.db"
    servico = AIReflectionPersistenceService(db)

    servico.salvar_reflexao(**_reflexao_padrao(entry_id="entry-abc"))

    conn = obter_conexao_ai_reflection(db)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM ai_reflection_logs WHERE entry_id = 'entry-abc'")
    linha = cursor.fetchone()
    conn.close()

    assert linha is not None
    assert linha["entry_id"] == "entry-abc"
    assert linha["mood"] == "Confiante"
    assert linha["my_decision"] == "BUY"
    assert abs(float(linha["my_confidence"]) - 0.75) < 0.001
    assert abs(float(linha["my_alignment"]) - 0.8) < 0.001
    assert linha["honest_assessment"] == "Mercado favoravel"
    assert linha["data_relevance"] == "ALTA"
    assert linha["am_i_useful"] == "Sim"
    assert linha["my_data_correlation"] == "Alta correlacao"
    assert linha["one_liner"] == "Ciclo positivo"
    assert linha["created_at"] != ""


def test_salvar_reflexao_ignora_entry_id_duplicado(tmp_path: Path) -> None:
    """Salvar reflexao com entry_id duplicado deve ser operacao idempotente."""
    db = tmp_path / "test.db"
    servico = AIReflectionPersistenceService(db)

    servico.salvar_reflexao(**_reflexao_padrao(entry_id="dup-001", mood="Confiante"))
    servico.salvar_reflexao(**_reflexao_padrao(entry_id="dup-001", mood="Frustrado"))

    conn = sqlite3.connect(str(db))
    cursor = conn.execute(
        "SELECT COUNT(*), mood FROM ai_reflection_logs WHERE entry_id = 'dup-001'"
    )
    contagem, mood_salvo = cursor.fetchone()
    conn.close()

    assert contagem == 1, "Nao deve ter duplicata por entry_id"
    assert mood_salvo == "Confiante", "Primeira insercao deve prevalecer"


# ---------------------------------------------------------------------------
# 3. Testes de AIReflectionPersistenceService — perguntas
# ---------------------------------------------------------------------------


def test_registrar_pergunta_insere_nova(tmp_path: Path) -> None:
    """Pergunta nova deve aparecer na listagem de perguntas ativas."""
    db = tmp_path / "test.db"
    servico = AIReflectionPersistenceService(db)

    servico.registrar_pergunta(
        question_id="q-001",
        prompt="Qual foi minha maior duvida hoje?",
        category="decisao",
        level="basico",
    )

    ativas = servico.listar_perguntas_ativas()
    ids = [p["question_id"] for p in ativas]
    assert "q-001" in ids, "Pergunta registrada deve aparecer nas ativas"


def test_registrar_pergunta_e_idempotente(tmp_path: Path) -> None:
    """Registrar a mesma pergunta duas vezes nao deve duplicar."""
    db = tmp_path / "test.db"
    servico = AIReflectionPersistenceService(db)

    servico.registrar_pergunta("q-dup", "Pergunta duplicada?", "risco")
    servico.registrar_pergunta("q-dup", "Pergunta duplicada?", "risco")

    conn = sqlite3.connect(str(db))
    cursor = conn.execute(
        "SELECT COUNT(*) FROM reflection_questions WHERE question_id = 'q-dup'"
    )
    contagem = cursor.fetchone()[0]
    conn.close()

    assert contagem == 1, "Nao deve haver duplicata de question_id"


def test_registrar_outcome_incrementa_contadores(tmp_path: Path) -> None:
    """Registrar outcome WIN deve incrementar respostas_win e total_respostas."""
    db = tmp_path / "test.db"
    servico = AIReflectionPersistenceService(db)

    servico.registrar_pergunta("q-out", "Pergunta de outcome?", "resultado")
    servico.registrar_outcome_pergunta("q-out", "WIN")

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT total_respostas, respostas_win FROM reflection_questions WHERE question_id = 'q-out'"
    )
    linha = cursor.fetchone()
    conn.close()

    assert linha["total_respostas"] == 1
    assert linha["respostas_win"] == 1


def test_score_relevancia_calculado_corretamente(tmp_path: Path) -> None:
    """Score de relevancia deve ser respostas_win / total_respostas."""
    db = tmp_path / "test.db"
    servico = AIReflectionPersistenceService(db)

    servico.registrar_pergunta("q-score", "Pergunta de score?", "analise")

    # 3 WIN e 2 LOSS = score 3/5 = 0.6
    for _ in range(3):
        servico.registrar_outcome_pergunta("q-score", "WIN")
    for _ in range(2):
        servico.registrar_outcome_pergunta("q-score", "LOSS")

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT score_relevancia, total_respostas FROM reflection_questions WHERE question_id = 'q-score'"
    )
    linha = cursor.fetchone()
    conn.close()

    assert linha["total_respostas"] == 5
    assert abs(float(linha["score_relevancia"]) - 0.6) < 0.01


# ---------------------------------------------------------------------------
# 4. Teste de obsolescencia
# ---------------------------------------------------------------------------


def test_avaliar_obsolescencia_marca_perguntas_com_score_baixo(tmp_path: Path) -> None:
    """Pergunta com score < 0.3 e >= 5 respostas deve ser marcada como obsoleta."""
    db = tmp_path / "test.db"
    servico = AIReflectionPersistenceService(db)

    servico.registrar_pergunta("q-obs", "Pergunta obsoleta?", "historico")

    # 1 WIN e 4 LOSS = score 0.2 (< 0.3) com 5 respostas
    servico.registrar_outcome_pergunta("q-obs", "WIN")
    for _ in range(4):
        servico.registrar_outcome_pergunta("q-obs", "LOSS")

    obsoletas = servico.avaliar_obsolescencia(threshold_score=0.3, min_respostas=5)

    assert "q-obs" in obsoletas, "Pergunta com score baixo deve ser marcada como obsoleta"

    # Confirmar no banco
    conn = sqlite3.connect(str(db))
    cursor = conn.execute(
        "SELECT obsoleta, ativa FROM reflection_questions WHERE question_id = 'q-obs'"
    )
    linha = cursor.fetchone()
    conn.close()

    assert linha[0] == 1, "Campo obsoleta deve ser 1"
    assert linha[1] == 0, "Campo ativa deve ser 0"


# ---------------------------------------------------------------------------
# 5. Teste de deteccao de padroes
# ---------------------------------------------------------------------------


def test_detectar_padrao_mood_frustrado(tmp_path: Path) -> None:
    """Tres ou mais reflexoes com mood=Frustrado devem gerar deteccao de padrao."""
    db = tmp_path / "test.db"
    servico = AIReflectionPersistenceService(db)

    for i in range(3):
        servico.salvar_reflexao(
            **_reflexao_padrao(
                entry_id=f"entry-frust-{i}",
                mood="Frustrado",
            )
        )

    padroes = servico.detectar_padroes_recorrentes(janela_dias=5)

    assert any("PADRAO_MOOD_FRUSTRADO" in p for p in padroes), (
        f"Padrao PADRAO_MOOD_FRUSTRADO nao detectado. Padroes: {padroes}"
    )


# ---------------------------------------------------------------------------
# 6. Teste de relatorio semanal
# ---------------------------------------------------------------------------


def test_gerar_relatorio_semanal_cria_arquivo(tmp_path: Path) -> None:
    """Relatorio semanal deve ser gerado como arquivo Markdown."""
    db = tmp_path / "test.db"
    output_dir = tmp_path / "outputs"

    servico = AIReflectionPersistenceService(db)
    servico.salvar_reflexao(**_reflexao_padrao(entry_id="rep-001"))

    relatorio = AIReflectionWeeklyReport(db_path=db, output_dir=output_dir)
    caminho = relatorio.gerar_relatorio(numero_semana=1)

    assert caminho.exists(), f"Arquivo de relatorio nao foi criado: {caminho}"
    assert caminho.name == "ai_reflection_semana_01.md"

    conteudo = caminho.read_text(encoding="utf-8")
    assert "# AI Reflection" in conteudo
    assert "Resumo da Semana" in conteudo


# ---------------------------------------------------------------------------
# 7. Testes de DiaryFeedback — campo acao_sugerida
# ---------------------------------------------------------------------------


def test_diary_feedback_tem_campo_acao_sugerida() -> None:
    """DiaryFeedback deve ter o campo acao_sugerida com valor padrao vazio."""
    fb = DiaryFeedback()
    assert hasattr(fb, "acao_sugerida"), "Campo acao_sugerida nao encontrado"
    assert fb.acao_sugerida == "", "Valor padrao de acao_sugerida deve ser string vazia"


def test_salvar_diary_feedback_com_acao_sugerida(tmp_path: Path) -> None:
    """Campo acao_sugerida deve ser persistido e recuperado corretamente."""
    db_path = str(tmp_path / "feedback.db")

    fb = DiaryFeedback(
        date="2025-01-01",
        timestamp="2025-01-01T10:00:00",
        acao_sugerida="Revisar filtros de entrada na proxima sessao",
    )
    feedback_id = save_diary_feedback(db_path, fb)

    assert feedback_id > 0, "ID do feedback deve ser positivo"

    recuperado = load_latest_feedback(db_path, today_only=False)
    assert recuperado is not None, "Feedback nao foi recuperado"
    assert recuperado.acao_sugerida == "Revisar filtros de entrada na proxima sessao"
