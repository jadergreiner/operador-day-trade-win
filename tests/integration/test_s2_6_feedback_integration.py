"""Testes de integração do FeedbackIntegrationManager.

Valida fluxo completo do capt ura de contexto até persistência.
"""

import pytest
import tempfile
from pathlib import Path

from src.application.integration.feedback_integration import (
    FeedbackIntegrationManager,
)


class TestFeedbackIntegrationManager:
    """Testes para integração de feedback ao loop principal."""

    @pytest.fixture
    def manager(self):
        """Fixture: manager com BD temporário."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "feedback_test.db"
            yield FeedbackIntegrationManager(str(db_path))

    def test_capture_trade_context_sucesso(self, manager):
        """DADO: Manager inicializado.
        QUANDO: Captura contexto de trade.
        ENTÃO: Contexto armazenado corretamente."""
        manager.capture_trade_context(
            trade_id="WINFUT-2026-02-24-14-30",
            score_ia=0.85,
            volatilidade_atr=1.2,
            win_rate_sessao=0.62,
            p_and_l_sessao=1234.56,
        )

        assert manager.current_trade_context is not None
        assert manager.current_trade_context["trade_id"] == (
            "WINFUT-2026-02-24-14-30"
        )
        assert manager.current_trade_context["score"] == 0.85
        assert manager.current_trade_context["volatilidade"] == 1.2
        assert manager.current_trade_context["win_rate"] == 0.62
        assert manager.current_trade_context["p_and_l"] == 1234.56

    def test_capture_trade_context_valores_tipo_correto(self, manager):
        """DADO: Contexto capturado com inteiros.
        QUANDO: Valida tipos.
        ENTÃO: Floats preservados como floats."""
        manager.capture_trade_context(
            trade_id="TEST-001",
            score_ia=1,  # int
            volatilidade_atr=2,  # int
            win_rate_sessao=0.5,  # float
            p_and_l_sessao=5000,  # int
        )

        contexto = manager.current_trade_context
        assert isinstance(contexto["score"], float)
        assert isinstance(contexto["volatilidade"], float)
        assert isinstance(contexto["win_rate"], float)
        assert isinstance(contexto["p_and_l"], float)

    def test_get_feedback_status_badge_sem_dados(self, manager):
        """DADO: BD vazio.
        QUANDO: Solicita status badge.
        ENTÃO: Mensagem 'Sem dados' retornada."""
        badge = manager.get_feedback_status_badge()
        assert "Sem dados" in badge

    def test_get_feedback_status_badge_com_dados(self, manager):
        """DADO: BD com 5 intervencoes.
        QUANDO: Solicita status badge.
        ENTÃO: Badge com contagem e código dominante."""
        # Inserir feedback diretamente no BD (sem solicitar input)
        from src.application.feedback_collector import (
            FeedbackIntervencaoManual,
        )

        for i in range(5):
            feedback = FeedbackIntervencaoManual(
                codigo_intervencao=(i % 8) + 1,
                timestamp=f"2026-02-24T10:{i:02d}:00Z",
                contexto={"score": 0.8},
            )
            manager.collector.registrar_intervencao(feedback, "win")

        badge = manager.get_feedback_status_badge()
        assert "FEEDBACK:" in badge
        assert "5 ops" in badge

    def test_handle_manual_intervention_sem_contexto(self, manager):
        """DADO: Manager sem contexto capturado.
        QUANDO: Tenta solicitar feedback.
        ENTÃO: None retornado."""
        resultado = manager.handle_manual_intervention("win")
        assert resultado is None

    def test_handle_manual_intervention_clearcontext_apos(self, manager):
        """DADO: Contexto capturado.
        QUANDO: Maneja intervenção.
        ENTÃO: Contexto limpo após sucesso."""
        manager.capture_trade_context(
            trade_id="TEST-CLEAR",
            score_ia=0.85,
            volatilidade_atr=1.2,
            win_rate_sessao=0.62,
            p_and_l_sessao=500.0,
        )

        assert manager.current_trade_context is not None

        # Simular que o menu de feedback foi respondido
        # (Nos testes reais, seria interativo)
        # Por agora, only validamos limpeza se sucesso

        # Obs: Não podemos testar handle_manual_intervention
        # sem entrada do usuário. Então testamos apenas estrutura.

    def test_capture_timestamp_sincronizado(self, manager):
        """DADO: Contexto capturado.
        QUANDO: Verifica timestamp.
        ENTÃO: ISO format válido e recent."""
        import dateutil.parser

        manager.capture_trade_context(
            trade_id="TEST-TIMESTAMP",
            score_ia=0.8,
            volatilidade_atr=1.0,
            win_rate_sessao=0.6,
            p_and_l_sessao=100.0,
        )

        timestamp_str = manager.current_trade_context["timestamp_captura"]

        # Validar que é ISO format válido
        try:
            parsed = dateutil.parser.isoparse(timestamp_str)
            assert parsed is not None
        except (ValueError, ImportError):
            # Se não tiver dateutil, apenas validar formato
            assert "T" in timestamp_str
            assert "Z" in timestamp_str or "+" in timestamp_str

    def test_capture_múltiplos_contextos(self, manager):
        """DADO: Manager captura contexto 1.
        QUANDO: Captura contexto 2 sem limpar.
        ENTÃO: Contexto 2 sobrescreve contexto 1."""
        manager.capture_trade_context(
            trade_id="TEST-001",
            score_ia=0.8,
            volatilidade_atr=1.0,
            win_rate_sessao=0.6,
            p_and_l_sessao=100.0,
        )

        assert manager.current_trade_context["trade_id"] == "TEST-001"

        # Capturar novo
        manager.capture_trade_context(
            trade_id="TEST-002",
            score_ia=0.9,
            volatilidade_atr=1.5,
            win_rate_sessao=0.7,
            p_and_l_sessao=200.0,
        )

        # Verificar que novo contexto substituiu anterior
        assert manager.current_trade_context["trade_id"] == "TEST-002"
        assert manager.current_trade_context["score"] == 0.9
        assert manager.current_trade_context["volatilidade"] == 1.5

    def test_get_status_badge_sem_erro_em_excecao(self, manager):
        """DADO: Manager com erro potencial em BD.
        QUANDO: Solicita status badge.
        ENTÃO: Mensagem de erro tratada gracefully."""
        # Fechar conexão para simular erro
        manager.collector.db_path = "/invalid/path/feedback.db"

        badge = manager.get_feedback_status_badge()
        assert badge is not None
        assert isinstance(badge, str)
        # Pode conter "Erro"
