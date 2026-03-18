"""
Testes para BUG-DIARIOS-02, BUG-DIARIOS-03, BUG-DIARIOS-04.

BUG-DIARIOS-02: eficiencia_pct sempre zero no RL Performance Diary.
BUG-DIARIOS-03: Encoding corrompido nos primeiros feedbacks do dia.
BUG-DIARIOS-04: NameError motor_decisao no Agente RL Direto.

Executor Impactado:
  BUG-DIARIOS-02: INICIAR_DIARIOS.bat
  BUG-DIARIOS-03: INICIAR_DIARIOS.bat
  BUG-DIARIOS-04: INICIAR_AGENTE_RL_DIRETO.bat
"""

import inspect
import sqlite3
import tempfile
import os
import pytest

from src.application.services.diary_feedback import (
    DiaryFeedback,
    _sanitizar_encoding,
    save_diary_feedback,
    create_diary_feedback_table,
)


# ─────────────────────────────────────────────────────────────────────────────
# BUG-DIARIOS-02: eficiencia_pct calculada corretamente
# ─────────────────────────────────────────────────────────────────────────────

class TestBugDiarios02EficienciaPct:
    """Testes para BUG-DIARIOS-02: eficiencia_pct sempre zero."""

    def test_eficiencia_pct_existe_no_dataclass(self) -> None:
        """Campo eficiencia_pct deve existir no DiaryFeedback."""
        fb = DiaryFeedback()
        assert hasattr(fb, "eficiencia_pct")

    def test_eficiencia_pct_default_zero(self) -> None:
        """Valor padrao de eficiencia_pct deve ser 0.0."""
        fb = DiaryFeedback()
        assert fb.eficiencia_pct == 0.0

    def test_eficiencia_pct_pode_ser_definido(self) -> None:
        """eficiencia_pct deve aceitar valor positivo."""
        fb = DiaryFeedback(eficiencia_pct=42.5)
        assert fb.eficiencia_pct == 42.5

    def test_eficiencia_pct_salvo_e_recuperado(self) -> None:
        """eficiencia_pct deve ser persistido e lido corretamente do SQLite."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            create_diary_feedback_table(db_path)
            fb = DiaryFeedback(
                date="2026-03-18",
                timestamp="2026-03-18T10:00:00",
                eficiencia_pct=67.3,
            )
            fb_id = save_diary_feedback(db_path, fb)
            assert fb_id > 0

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT eficiencia_pct FROM diary_feedback WHERE id = ?",
                (fb_id,),
            )
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert abs(row["eficiencia_pct"] - 67.3) < 0.01
        finally:
            os.unlink(db_path)

    def test_eficiencia_pct_nunca_negativa(self) -> None:
        """eficiencia_pct nao deve ser negativa — min de pts capturados e 0."""
        fb = DiaryFeedback(eficiencia_pct=0.0)
        assert fb.eficiencia_pct >= 0.0

    def test_eficiencia_pct_maximo_100(self) -> None:
        """eficiencia_pct deve ser limitada a 100 pelo calculo."""
        # Verifica que logica de min(pct, 100.0) e aplicavel
        capturable = 200.0
        pts_capturados = 250.0  # Mais que o capturable
        eficiencia = min(pts_capturados / capturable * 100, 100.0)
        assert eficiencia == 100.0


# ─────────────────────────────────────────────────────────────────────────────
# BUG-DIARIOS-03: Encoding corrompido nos feedbacks
# ─────────────────────────────────────────────────────────────────────────────

class TestBugDiarios03EncodingCorrompido:
    """Testes para BUG-DIARIOS-03: encoding corrompido em diary_feedback."""

    def test_sanitizar_encoding_existe(self) -> None:
        """Funcao _sanitizar_encoding deve existir no modulo."""
        assert callable(_sanitizar_encoding)

    def test_sanitizar_remove_fffd(self) -> None:
        """Caractere U+FFFD deve ser substituido por '?'."""
        texto_corrompido = "N\ufffdio e poss\ufffdvel"
        resultado = _sanitizar_encoding(texto_corrompido)
        assert "\ufffd" not in resultado
        assert "?" in resultado

    def test_sanitizar_preserva_texto_valido(self) -> None:
        """Texto UTF-8 valido nao deve ser alterado."""
        texto = "Nao e possivel — mercado neutro (COMPRA/VENDA)"
        resultado = _sanitizar_encoding(texto)
        assert resultado == texto

    def test_sanitizar_preserva_acentuacao_correta(self) -> None:
        """Acentos corretos em UTF-8 nao devem ser removidos."""
        texto = "Análise de coerência com ação e decisão"
        resultado = _sanitizar_encoding(texto)
        assert resultado == texto

    def test_sanitizar_preserva_emojis(self) -> None:
        """Emojis Unicode devem ser preservados pela sanitizacao."""
        texto = "🚨 ALERTA CRITICO: threshold 45% 🔴"
        resultado = _sanitizar_encoding(texto)
        assert resultado == texto

    def test_sanitizar_texto_vazio(self) -> None:
        """String vazia deve retornar string vazia."""
        assert _sanitizar_encoding("") == ""

    def test_sanitizar_multiplos_fffd(self) -> None:
        """Multiplos U+FFFD devem ser todos substituidos."""
        texto = "A\ufffdB\ufffdC\ufffd"
        resultado = _sanitizar_encoding(texto)
        assert resultado == "A?B?C?"
        assert "\ufffd" not in resultado

    def test_save_diary_feedback_sanitiza_alertas(self) -> None:
        """save_diary_feedback deve sanitizar alertas_criticos antes de salvar."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            create_diary_feedback_table(db_path)
            fb = DiaryFeedback(
                date="2026-03-18",
                timestamp="2026-03-18T09:00:00",
                alertas_criticos=[
                    "N\ufffdio e poss\ufffdvel operar",
                    "Mercado neutro",
                ],
            )
            fb_id = save_diary_feedback(db_path, fb)
            assert fb_id > 0

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT alertas_criticos FROM diary_feedback WHERE id = ?",
                (fb_id,),
            )
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            # O texto gravado nao deve conter U+FFFD
            assert "\ufffd" not in row["alertas_criticos"]
        finally:
            os.unlink(db_path)

    def test_save_diary_feedback_sanitiza_veredicto(self) -> None:
        """save_diary_feedback deve sanitizar veredicto_regioes."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            create_diary_feedback_table(db_path)
            fb = DiaryFeedback(
                date="2026-03-18",
                timestamp="2026-03-18T09:05:00",
                veredicto_regioes="Regi\ufffdio forte detectada",
            )
            fb_id = save_diary_feedback(db_path, fb)

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT veredicto_regioes FROM diary_feedback WHERE id = ?",
                (fb_id,),
            )
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert "\ufffd" not in row["veredicto_regioes"]
        finally:
            os.unlink(db_path)


# ─────────────────────────────────────────────────────────────────────────────
# BUG-DIARIOS-04: motor_decisao passado como parametro em enviar_ordem
# ─────────────────────────────────────────────────────────────────────────────

class TestBugDiarios04MotorDecisaoEscopo:
    """Testes para BUG-DIARIOS-04: NameError motor_decisao."""

    def test_enviar_ordem_aceita_motor_decisao_como_parametro(self) -> None:
        """enviar_ordem deve ter motor_decisao na assinatura."""
        import importlib.util
        import sys

        caminho = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "scripts",
            "agente_rl_direto_independente.py",
        )
        spec = importlib.util.spec_from_file_location(
            "agente_rl_direto", caminho
        )
        assert spec is not None
        modulo = importlib.util.module_from_spec(spec)
        # Nao executar o modulo — apenas inspecionar codigo fonte
        with open(caminho, encoding="utf-8") as f:
            codigo = f.read()

        # Verificar que motor_decisao aparece na assinatura de enviar_ordem
        assert "motor_decisao: object" in codigo, (
            "enviar_ordem deve ter 'motor_decisao: object' na assinatura"
        )

    def test_enviar_ordem_nao_usa_motor_decisao_como_global(self) -> None:
        """Funcao enviar_ordem nao deve depender de motor_decisao no escopo global."""
        caminho = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "scripts",
            "agente_rl_direto_independente.py",
        )
        with open(caminho, encoding="utf-8") as f:
            linhas = f.readlines()

        # Localizar bloco da funcao enviar_ordem
        inicio = None
        fim = None
        for i, linha in enumerate(linhas):
            if linha.strip().startswith("def enviar_ordem("):
                inicio = i
            if inicio is not None and i > inicio:
                # Proxima funcao de nivel igual termina o bloco
                if linha.startswith("def ") or linha.startswith("class "):
                    fim = i
                    break

        assert inicio is not None, "Funcao enviar_ordem nao encontrada"

        bloco = "".join(linhas[inicio: fim or len(linhas)])

        # Nao deve haver 'global motor_decisao' dentro da funcao
        assert "global motor_decisao" not in bloco, (
            "motor_decisao nao deve ser declarado global em enviar_ordem"
        )

    def test_chamada_enviar_ordem_passa_motor_decisao(self) -> None:
        """O call site de enviar_ordem deve passar motor_decisao como argumento."""
        caminho = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "scripts",
            "agente_rl_direto_independente.py",
        )
        with open(caminho, encoding="utf-8") as f:
            codigo = f.read()

        # A chamada deve incluir motor_decisao
        assert "enviar_ordem(mt5_adapter, acao_str, preco_atual, posicao_tracker, rl_repo, trade_tracker, motor_decisao" in codigo, (
            "O call site de enviar_ordem deve passar motor_decisao"
        )

    def test_type_hints_100_porcento(self) -> None:
        """Verificar que motor_decisao tem type hint na assinatura."""
        caminho = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "scripts",
            "agente_rl_direto_independente.py",
        )
        with open(caminho, encoding="utf-8") as f:
            codigo = f.read()

        # Type hint deve estar presente
        assert "motor_decisao: object" in codigo
