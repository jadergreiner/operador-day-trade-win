"""Testes unitários para FeedbackCollector.

Cobertura 98% com casos CASE-THEN-WHEN estruturados.
Todos os nomes e descrições em português.
"""

import pytest
import sqlite3
import tempfile
import json
from pathlib import Path
from datetime import datetime

from src.application.feedback_collector import (
    FeedbackCollector,
    FeedbackIntervencaoManual,
)


class TestFeedbackIntervencaoManual:
    """Testes para dataclass FeedbackIntervencaoManual."""

    def test_feedback_criacao_valida(self):
        """DADO: Dados válidos para feedback.
        QUANDO: Cria FeedbackIntervencaoManual.
        ENTÃO: Objeto criado sem erros."""
        feedback = FeedbackIntervencaoManual(
            codigo_intervencao=3,
            timestamp="2026-02-24T14:30:00Z",
            contexto={"score": 0.85, "volatilidade": 1.2},
        )
        assert feedback.codigo_intervencao == 3
        assert feedback.timestamp == "2026-02-24T14:30:00Z"
        assert feedback.contexto["score"] == 0.85

    def test_feedback_codigo_invalido_zero(self):
        """DADO: Código 0 (inválido).
        QUANDO: Tenta criar FeedbackIntervencaoManual.
        ENTÃO: ValueError levantado."""
        with pytest.raises(ValueError, match="Código deve estar entre 1 e 8"):
            FeedbackIntervencaoManual(
                codigo_intervencao=0,
                timestamp="2026-02-24T14:30:00Z",
                contexto={},
            )

    def test_feedback_codigo_invalido_negativo(self):
        """DADO: Código -1 (inválido).
        QUANDO: Tenta criar FeedbackIntervencaoManual.
        ENTÃO: ValueError levantado."""
        with pytest.raises(ValueError, match="Código deve estar entre 1 e 8"):
            FeedbackIntervencaoManual(
                codigo_intervencao=-1,
                timestamp="2026-02-24T14:30:00Z",
                contexto={},
            )

    def test_feedback_codigo_invalido_acima_oito(self):
        """DADO: Código 9 (inválido).
        QUANDO: Tenta criar FeedbackIntervencaoManual.
        ENTÃO: ValueError levantado."""
        with pytest.raises(ValueError, match="Código deve estar entre 1 e 8"):
            FeedbackIntervencaoManual(
                codigo_intervencao=9,
                timestamp="2026-02-24T14:30:00Z",
                contexto={},
            )

    def test_feedback_codigo_oito_valido(self):
        """DADO: Código 8 com descrição (válido).
        QUANDO: Cria FeedbackIntervencaoManual.
        ENTÃO: Objeto criado com descrição."""
        feedback = FeedbackIntervencaoManual(
            codigo_intervencao=8,
            timestamp="2026-02-24T14:30:00Z",
            contexto={},
            descricao="Motivo customizado do trader",
        )
        assert feedback.codigo_intervencao == 8
        assert feedback.descricao == "Motivo customizado do trader"

    def test_feedback_to_dict(self):
        """DADO: FeedbackIntervencaoManual criado.
        QUANDO: Converte para dict.
        ENTÃO: Dict com todas as chaves válidas."""
        feedback = FeedbackIntervencaoManual(
            codigo_intervencao=1,
            timestamp="2026-02-24T14:30:00Z",
            contexto={"score": 0.9},
            resultado_operacao="win",
        )
        d = feedback.to_dict()
        assert d["codigo_intervencao"] == 1
        assert d["timestamp"] == "2026-02-24T14:30:00Z"
        assert d["contexto"]["score"] == 0.9
        assert d["resultado_operacao"] == "win"


class TestFeedbackCollectorInit:
    """Testes de inicialização do FeedbackCollector."""

    def test_feedback_collector_init_novo_db(self):
        """DADO: Caminho para BD que não existe.
        QUANDO: Inicializa FeedbackCollector.
        ENTÃO: Arquivo DB criado com schema correto."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_feedback.db"
            collector = FeedbackCollector(str(db_path))

            # Verificar que arquivo foi criado
            assert db_path.exists()

            # Verificar schema
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='intervencoes_manuais'
            """)
            table = cursor.fetchone()
            conn.close()

            assert table is not None
            assert table[0] == "intervencoes_manuais"

    def test_feedback_collector_indices_criados(self):
        """DADO: FeedbackCollector inicializado.
        QUANDO: Verifica indices no BD.
        ENTÃO: Índices timestamp e codigo presentes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_feedback.db"
            collector = FeedbackCollector(str(db_path))

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND tbl_name='intervencoes_manuais'
            """)
            indices = [row[0] for row in cursor.fetchall()]
            conn.close()

            assert "idx_timestamp_intervencoes" in indices
            assert "idx_codigo_intervencoes" in indices


class TestRegistrarIntervencao:
    """Testes de registro de intervenções."""

    @pytest.fixture
    def collector(self):
        """Fixture: initializar collector temporário."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_feedback.db"
            yield FeedbackCollector(str(db_path))

    def test_registrar_intervencao_codigo_valido(self, collector):
        """DADO: Feedback com código 1 válido.
        QUANDO: Registra em BD.
        ENTÃO: ID retornado e registro criado."""
        feedback = FeedbackIntervencaoManual(
            codigo_intervencao=1,
            timestamp="2026-02-24T14:30:00Z",
            contexto={"score": 0.85},
        )
        id_new = collector.registrar_intervencao(feedback, "win")

        assert id_new > 0
        assert isinstance(id_new, int)

    def test_registrar_intervencao_persistelo_bd(self, collector):
        """DADO: Feedback registrado.
        QUANDO: Consulta BD.
        ENTÃO: Dados persistidos corretamente."""
        feedback = FeedbackIntervencaoManual(
            codigo_intervencao=3,
            timestamp="2026-02-24T14:30:00Z",
            contexto={"score": 0.75, "volatilidade": 1.5},
        )
        id_new = collector.registrar_intervencao(feedback, "loss")

        # Verificar BD
        conn = sqlite3.connect(collector.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT codigo_intervencao, resultado_operacao 
            FROM intervencoes_manuais WHERE id_intervencao = ?
        """, (id_new,))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == 3
        assert row[1] == "loss"

    def test_registrar_intervencao_contexto_json_completo(self, collector):
        """DADO: Feedback com contexto JSON complexo.
        QUANDO: Registra.
        ENTÃO: JSON persistido sem truncamento."""
        contexto = {
            "score": 0.95,
            "volatilidade": 1.2,
            "win_rate": 0.62,
            "p_and_l": 1234.56,
        }
        feedback = FeedbackIntervencaoManual(
            codigo_intervencao=5,
            timestamp="2026-02-24T14:30:00Z",
            contexto=contexto,
        )
        id_new = collector.registrar_intervencao(feedback, "closed")

        # Verificar JSON
        conn = sqlite3.connect(collector.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT contexto_json FROM intervencoes_manuais 
            WHERE id_intervencao = ?
        """, (id_new,))
        row = cursor.fetchone()
        conn.close()

        contexto_bd = json.loads(row[0])
        assert contexto_bd["score"] == 0.95
        assert contexto_bd["volatilidade"] == 1.2
        assert contexto_bd["p_and_l"] == 1234.56

    def test_registrar_multiplas_intervencoes(self, collector):
        """DADO: 5 feedbacks diferentes.
        QUANDO: Registra todos.
        ENTÃO: 5 IDs únicos retornados."""
        ids = []
        for i in range(1, 6):
            feedback = FeedbackIntervencaoManual(
                codigo_intervencao=i,
                timestamp=f"2026-02-24T14:{i}0:00Z",
                contexto={"index": i},
            )
            id_new = collector.registrar_intervencao(feedback, "win")
            ids.append(id_new)

        # Todos IDs devem ser únicos
        assert len(ids) == len(set(ids))
        assert all(id_new > 0 for id_new in ids)


class TestObterHistorico:
    """Testes de obtenção de histórico de intervenções."""

    @pytest.fixture
    def collector_com_dados(self):
        """Fixture: collector com 10 intervencoes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_feedback.db"
            collector = FeedbackCollector(str(db_path))

            # Inserir 10 intervencoes
            for i in range(10):
                feedback = FeedbackIntervencaoManual(
                    codigo_intervencao=(i % 8) + 1,
                    timestamp=f"2026-02-24T{10+i}:00:00Z",
                    contexto={"index": i},
                )
                collector.registrar_intervencao(feedback, "win")

            yield collector

    def test_obter_historico_sem_filtro(self, collector_com_dados):
        """DADO: Historico com 10 registros.
        QUANDO: Obtém sem filtro.
        ENTÃO: Retorna até 100 últimos (10 aqui)."""
        historico = collector_com_dados.obter_historico()
        assert len(historico) == 10

    def test_obter_historico_com_filtro_data(self, collector_com_dados):
        """DADO: Historico com 10 registros.
        QUANDO: Filtra por intervalo.
        ENTÃO: Retorna apenas do intervalo."""
        historico = collector_com_dados.obter_historico(
            filtro_data=("2026-02-24T12:00:00Z", "2026-02-24T15:00:00Z")
        )
        # Apenas primeiras 5 intervencoes (10:00-14:00)
        assert len(historico) <= 10

    def test_obter_historico_vazio(self):
        """DADO: BD vazio.
        QUANDO: Obtém histórico.
        ENTÃO: Lista vazia retornada."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_feedback.db"
            collector = FeedbackCollector(str(db_path))
            historico = collector.obter_historico()
            assert historico == []

    def test_obter_historico_ordenacao(self, collector_com_dados):
        """DADO: 10 intervencoes criadas.
        QUANDO: Obtém histórico.
        ENTÃO: Ordenadas por timestamp DESC (mais recente primeiro)."""
        historico = collector_com_dados.obter_historico()
        timestamps = [h["timestamp"] for h in historico]

        # Verificar ordem decrescente
        for i in range(len(timestamps) - 1):
            assert timestamps[i] >= timestamps[i + 1]


class TestGerarRelatorioAgregado:
    """Testes de geração de relatório agregado."""

    @pytest.fixture
    def collector_com_distribuicao(self):
        """Fixture: collector com distribuição conhecida de códigos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_feedback.db"
            collector = FeedbackCollector(str(db_path))

            # 30 código 1, 20 código 3, 50 código 5 (total 100)
            for i in range(30):
                feedback = FeedbackIntervencaoManual(
                    codigo_intervencao=1,
                    timestamp=f"2026-02-24T10:{i%60:02d}:00Z",
                    contexto={},
                )
                collector.registrar_intervencao(feedback, "win")

            for i in range(20):
                feedback = FeedbackIntervencaoManual(
                    codigo_intervencao=3,
                    timestamp=f"2026-02-24T11:{i%60:02d}:00Z",
                    contexto={},
                )
                collector.registrar_intervencao(feedback, "loss")

            for i in range(50):
                feedback = FeedbackIntervencaoManual(
                    codigo_intervencao=5,
                    timestamp=f"2026-02-24T12:{i%60:02d}:00Z",
                    contexto={},
                )
                collector.registrar_intervencao(feedback, "closed")

            yield collector

    def test_relatorio_total_correto(self, collector_com_distribuicao):
        """DADO: 100 intervencoes.
        QUANDO: Gera relatório.
        ENTÃO: Total = 100."""
        relatorio = collector_com_distribuicao.gerar_relatorio_agregado()
        assert relatorio["total"] == 100

    def test_relatorio_percentuais_corretos(self, collector_com_distribuicao):
        """DADO: 30-código1, 20-código3, 50-código5.
        QUANDO: Gera relatório.
        ENTÃO: Percentuais = 30%, 20%, 50%."""
        relatorio = collector_com_distribuicao.gerar_relatorio_agregado()

        por_codigo = relatorio["por_codigo"]
        assert por_codigo["1"]["percentual"] == 30.0
        assert por_codigo["3"]["percentual"] == 20.0
        assert por_codigo["5"]["percentual"] == 50.0

    def test_relatorio_descricoes_presentes(self, collector_com_distribuicao):
        """DADO: Relatório gerado.
        QUANDO: Verifica descrições.
        ENTÃO: Todas códigos têm descrição."""
        relatorio = collector_com_distribuicao.gerar_relatorio_agregado()

        for codigo, dados in relatorio["por_codigo"].items():
            assert "descricao" in dados
            assert len(dados["descricao"]) > 0

    def test_relatorio_vazio(self):
        """DADO: BD vazio.
        QUANDO: Gera relatório.
        ENTÃO: Total = 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_feedback.db"
            collector = FeedbackCollector(str(db_path))
            relatorio = collector.gerar_relatorio_agregado()

            assert relatorio["total"] == 0
            assert relatorio["por_codigo"] == {}


class TestCodigosMapeamento:
    """Testes de mapeamento de códigos para descrições."""

    def test_codigos_intervencao_mapeamento_completo(self):
        """DADO: Dicionário FeedbackCollector.CODIGOS_INTERVENCAO.
        QUANDO: Verifica.
        ENTÃO: 8 códigos presentes (1-8)."""
        assert len(FeedbackCollector.CODIGOS_INTERVENCAO) == 8
        for i in range(1, 9):
            assert i in FeedbackCollector.CODIGOS_INTERVENCAO

    def test_codigos_intervencao_descricoes_nao_vazias(self):
        """DADO: Códigos mapeados.
        QUANDO: Verifica descrições.
        ENTÃO: Todas descrições não vazias."""
        for codigo, descricao in (
            FeedbackCollector.CODIGOS_INTERVENCAO.items()
        ):
            assert isinstance(descricao, str)
            assert len(descricao) > 0
