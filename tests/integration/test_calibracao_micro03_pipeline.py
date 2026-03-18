"""
CALIBRACAO-MICRO-03: Testes de integracao do pipeline de episodios reais.

Valida o fluxo completo:
    trade simulado
    -> episodio persistido (micro_episodios, diario_episodios, execution_feedback)
    -> feedback gerado (AC5.9)
    -> retreinamento acionado quando threshold atingido (AC6.8)

Todos os testes usam banco SQLite temporario (sem MT5, sem rede).
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def db_temp():
    """Banco SQLite temporario para cada teste."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_trading.db")
        yield db_path


@pytest.fixture
def pipeline(db_temp):
    """PipelineEpisodiosMicro com banco temporario e sem modulos AC reais."""
    from src.application.pipeline_episodios_micro import PipelineEpisodiosMicro

    return PipelineEpisodiosMicro(
        db_path=db_temp,
        drift_detector=None,
        online_learning=None,
        baseline_comparator=None,
    )


@pytest.fixture
def contexto_entrada_basico():
    """Contexto de entrada simulado com todos os campos."""
    return {
        "macro_score": 6,
        "macro_signal": "BULLISH",
        "macro_confidence": 0.72,
        "micro_score": 4,
        "micro_trend": "CONTINUACAO",
        "adx": 28.5,
        "rsi": 55.3,
        "smc_direction": "BULLISH",
        "confianca": 62.0,
        "reason": "VWAP + RSI momentum",
        "preco": 130500.0,
        "sl": 130200.0,
        "tp": 131100.0,
        "risk_reward": 2.0,
        "timestamp_entrada": "2026-03-18T10:30:00",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Testes unitarios do PipelineEpisodiosMicro
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestPipelineEpisodiosMicro:
    """Testes do pipeline de persistencia de episodios."""

    def test_inicializacao_cria_tabelas(self, db_temp):
        """DADO: db_path valido.
        QUANDO: PipelineEpisodiosMicro e instanciado.
        ENTAO: Tabelas micro_episodios e execution_feedback sao criadas."""
        from src.application.pipeline_episodios_micro import PipelineEpisodiosMicro

        PipelineEpisodiosMicro(db_path=db_temp)

        conn = sqlite3.connect(db_temp)
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tabelas = {r[0] for r in cur.fetchall()}
        conn.close()

        assert "micro_episodios" in tabelas
        assert "execution_feedback" in tabelas

    def test_registrar_fechamento_win_persiste_episodio(
        self, pipeline, db_temp, contexto_entrada_basico
    ):
        """DADO: Trade ganho com contexto de entrada.
        QUANDO: registrar_fechamento() e chamado.
        ENTAO: Episodio e persistido em micro_episodios com outcome=WIN."""
        episode_id = pipeline.registrar_fechamento(
            ticket="TICKET001",
            direction="COMPRA",
            entry_price=130500.0,
            exit_price=131100.0,
            stop_loss=130200.0,
            take_profit=131100.0,
            pnl=600.0,
            motivo_saida="TAKE_PROFIT",
            duracao_s=1800,
            context_entrada=contexto_entrada_basico,
        )

        assert episode_id is not None

        conn = sqlite3.connect(db_temp)
        cur = conn.cursor()
        cur.execute(
            "SELECT outcome, resultado_pts, macro_score, rsi, adx "
            "FROM micro_episodios WHERE episode_id = ?",
            (episode_id,),
        )
        row = cur.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "WIN"
        assert row[1] == 600.0
        assert row[2] == 6  # macro_score
        assert abs(row[3] - 55.3) < 0.01  # rsi
        assert abs(row[4] - 28.5) < 0.01  # adx

    def test_registrar_fechamento_loss_persiste_episodio(
        self, pipeline, db_temp, contexto_entrada_basico
    ):
        """DADO: Trade com perda.
        QUANDO: registrar_fechamento() e chamado com pnl negativo.
        ENTAO: outcome=LOSS."""
        episode_id = pipeline.registrar_fechamento(
            ticket="TICKET002",
            direction="COMPRA",
            entry_price=130500.0,
            exit_price=130200.0,
            stop_loss=130200.0,
            take_profit=131100.0,
            pnl=-300.0,
            motivo_saida="STOP_LOSS",
            duracao_s=600,
            context_entrada=contexto_entrada_basico,
        )

        conn = sqlite3.connect(db_temp)
        cur = conn.cursor()
        cur.execute(
            "SELECT outcome FROM micro_episodios WHERE episode_id = ?",
            (episode_id,),
        )
        row = cur.fetchone()
        conn.close()

        assert row[0] == "LOSS"

    def test_registrar_fechamento_sem_contexto(self, pipeline, db_temp):
        """DADO: Trade sem contexto de entrada (contexto_entrada=None).
        QUANDO: registrar_fechamento() e chamado.
        ENTAO: Episodio e persistido com campos de contexto nulos."""
        episode_id = pipeline.registrar_fechamento(
            ticket="TICKET003",
            direction="VENDA",
            entry_price=130000.0,
            exit_price=129700.0,
            stop_loss=130300.0,
            take_profit=129400.0,
            pnl=300.0,
            motivo_saida="TAKE_PROFIT",
            duracao_s=900,
            context_entrada=None,
        )

        assert episode_id is not None

        conn = sqlite3.connect(db_temp)
        cur = conn.cursor()
        cur.execute(
            "SELECT macro_score, rsi FROM micro_episodios WHERE episode_id = ?",
            (episode_id,),
        )
        row = cur.fetchone()
        conn.close()

        assert row[0] is None  # macro_score ausente
        assert row[1] is None  # rsi ausente

    def test_execution_feedback_preenchido(self, pipeline, db_temp, contexto_entrada_basico):
        """DADO: Trade executado.
        QUANDO: registrar_fechamento() e chamado.
        ENTAO: execution_feedback tem entrada com outcome e pnl corretos."""
        episode_id = pipeline.registrar_fechamento(
            ticket="TICKET004",
            direction="COMPRA",
            entry_price=130500.0,
            exit_price=131100.0,
            stop_loss=130200.0,
            take_profit=131100.0,
            pnl=600.0,
            motivo_saida="TAKE_PROFIT",
            duracao_s=1800,
            context_entrada=contexto_entrada_basico,
        )

        conn = sqlite3.connect(db_temp)
        cur = conn.cursor()
        cur.execute(
            "SELECT outcome_type, pnl, confianca_entrada "
            "FROM execution_feedback WHERE episode_id = ?",
            (episode_id,),
        )
        row = cur.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "WIN"
        assert row[1] == 600.0
        assert abs(row[2] - 62.0) < 0.01  # confianca

    def test_diario_episodio_preenchido(self, pipeline, db_temp, contexto_entrada_basico):
        """DADO: Trade executado.
        QUANDO: registrar_fechamento() e chamado.
        ENTAO: diario_episodios tem entrada com resultado e fase."""
        episode_id = pipeline.registrar_fechamento(
            ticket="TICKET005",
            direction="COMPRA",
            entry_price=130500.0,
            exit_price=131100.0,
            stop_loss=130200.0,
            take_profit=131100.0,
            pnl=600.0,
            motivo_saida="TAKE_PROFIT",
            duracao_s=1800,
            context_entrada=contexto_entrada_basico,
        )

        conn = sqlite3.connect(db_temp)
        cur = conn.cursor()
        cur.execute(
            "SELECT resultado_pts, foi_acerto, fase_sessao "
            "FROM diario_episodios WHERE session_id = ?",
            (episode_id,),
        )
        row = cur.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == 600.0
        assert row[1] == 1  # foi_acerto
        assert row[2] == "MANHA"  # hora 10 -> MANHA

    def test_contador_episodios_incrementa(self, pipeline, contexto_entrada_basico):
        """DADO: Pipeline vazio.
        QUANDO: Tres fechamentos sao registrados.
        ENTAO: Contador interno e 3."""
        for i in range(3):
            pipeline.registrar_fechamento(
                ticket=f"TICKET_CTR_{i}",
                direction="COMPRA",
                entry_price=130000.0 + i * 100,
                exit_price=130500.0 + i * 100,
                stop_loss=129700.0,
                take_profit=131000.0,
                pnl=500.0,
                motivo_saida="TAKE_PROFIT",
                duracao_s=1200,
                context_entrada=contexto_entrada_basico,
            )

        assert pipeline._n_episodios == 3

    def test_contar_episodios_consulta_banco(self, pipeline, db_temp, contexto_entrada_basico):
        """DADO: Dois episodios persistidos.
        QUANDO: contar_episodios() e chamado.
        ENTAO: Retorna 2."""
        for i in range(2):
            pipeline.registrar_fechamento(
                ticket=f"TICKET_CNT_{i}",
                direction="COMPRA",
                entry_price=130000.0,
                exit_price=130500.0,
                stop_loss=129700.0,
                take_profit=131000.0,
                pnl=500.0,
                motivo_saida="TAKE_PROFIT",
                duracao_s=900,
                context_entrada=contexto_entrada_basico,
            )

        total = pipeline.contar_episodios()
        assert total == 2

    def test_calcular_win_rate_real(self, pipeline, db_temp, contexto_entrada_basico):
        """DADO: 3 wins e 1 loss.
        QUANDO: calcular_win_rate_real() e chamado.
        ENTAO: Retorna 0.75."""
        for i in range(3):
            pipeline.registrar_fechamento(
                ticket=f"TICKET_WR_W{i}",
                direction="COMPRA",
                entry_price=130000.0,
                exit_price=130500.0,
                stop_loss=129700.0,
                take_profit=131000.0,
                pnl=500.0,
                motivo_saida="TAKE_PROFIT",
                duracao_s=900,
                context_entrada=contexto_entrada_basico,
            )
        pipeline.registrar_fechamento(
            ticket="TICKET_WR_L0",
            direction="COMPRA",
            entry_price=130000.0,
            exit_price=129700.0,
            stop_loss=129700.0,
            take_profit=131000.0,
            pnl=-300.0,
            motivo_saida="STOP_LOSS",
            duracao_s=600,
            context_entrada=contexto_entrada_basico,
        )

        wr = pipeline.calcular_win_rate_real()
        assert abs(wr - 0.75) < 0.01


# ─────────────────────────────────────────────────────────────────────────────
# Testes de integracao com modulos AC
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestPipelineComModulosAC:
    """Testa acionamento dos modulos AC6.7 e AC6.8."""

    def test_ac67_nao_acionado_abaixo_threshold(self, db_temp, contexto_entrada_basico):
        """DADO: DriftDetector mockado.
        QUANDO: Menos de 10 episodios sao registrados.
        ENTAO: detectar_drift NAO e chamado."""
        from src.application.pipeline_episodios_micro import PipelineEpisodiosMicro

        mock_drift = MagicMock()
        pipeline = PipelineEpisodiosMicro(
            db_path=db_temp,
            drift_detector=mock_drift,
        )

        for i in range(9):
            pipeline.registrar_fechamento(
                ticket=f"T_{i}",
                direction="COMPRA",
                entry_price=130000.0,
                exit_price=130500.0,
                stop_loss=129700.0,
                take_profit=131000.0,
                pnl=500.0,
                motivo_saida="TAKE_PROFIT",
                duracao_s=900,
                context_entrada=contexto_entrada_basico,
            )

        mock_drift.detectar_drift.assert_not_called()

    def test_ac67_acionado_no_decimo_episodio(self, db_temp, contexto_entrada_basico):
        """DADO: DriftDetector mockado.
        QUANDO: Exatamente 10 episodios sao registrados.
        ENTAO: detectar_drift e chamado uma vez."""
        from src.application.pipeline_episodios_micro import PipelineEpisodiosMicro

        mock_drift = MagicMock()
        mock_drift.detectar_drift.return_value = []
        pipeline = PipelineEpisodiosMicro(
            db_path=db_temp,
            drift_detector=mock_drift,
        )

        for i in range(10):
            pipeline.registrar_fechamento(
                ticket=f"T10_{i}",
                direction="COMPRA",
                entry_price=130000.0,
                exit_price=130500.0,
                stop_loss=129700.0,
                take_profit=131000.0,
                pnl=500.0,
                motivo_saida="TAKE_PROFIT",
                duracao_s=900,
                context_entrada=contexto_entrada_basico,
            )

        assert mock_drift.detectar_drift.call_count == 1

    def test_ac68_nao_acionado_abaixo_threshold(self, db_temp, contexto_entrada_basico):
        """DADO: OnlineLearningController mockado.
        QUANDO: Menos de 20 episodios sao registrados.
        ENTAO: train_incremental NAO e chamado."""
        from src.application.pipeline_episodios_micro import PipelineEpisodiosMicro

        mock_learning = MagicMock()
        pipeline = PipelineEpisodiosMicro(
            db_path=db_temp,
            online_learning=mock_learning,
        )

        for i in range(19):
            pipeline.registrar_fechamento(
                ticket=f"T19_{i}",
                direction="COMPRA",
                entry_price=130000.0,
                exit_price=130500.0,
                stop_loss=129700.0,
                take_profit=131000.0,
                pnl=500.0,
                motivo_saida="TAKE_PROFIT",
                duracao_s=900,
                context_entrada=contexto_entrada_basico,
            )

        mock_learning.train_incremental.assert_not_called()

    def test_ac68_acionado_no_vigesimo_episodio(self, db_temp, contexto_entrada_basico):
        """DADO: OnlineLearningController mockado.
        QUANDO: Exatamente 20 episodios sao registrados.
        ENTAO: train_incremental e chamado com batch de ate 30 episodios."""
        from src.application.pipeline_episodios_micro import PipelineEpisodiosMicro

        mock_learning = MagicMock()
        mock_learning.train_incremental.return_value = {"samples_trained": 20}
        pipeline = PipelineEpisodiosMicro(
            db_path=db_temp,
            online_learning=mock_learning,
        )

        for i in range(20):
            pipeline.registrar_fechamento(
                ticket=f"T20_{i}",
                direction="COMPRA",
                entry_price=130000.0,
                exit_price=130500.0,
                stop_loss=129700.0,
                take_profit=131000.0,
                pnl=500.0,
                motivo_saida="TAKE_PROFIT",
                duracao_s=900,
                context_entrada=contexto_entrada_basico,
            )

        assert mock_learning.train_incremental.call_count == 1
        batch_chamado = mock_learning.train_incremental.call_args[0][0]
        assert len(batch_chamado) <= 30

    def test_ac69_acionar_baseline_comparator(self, db_temp, contexto_entrada_basico):
        """DADO: BaselineComparator mockado com episodios acumulados.
        QUANDO: acionar_baseline_comparator() e chamado manualmente.
        ENTAO: comparar_metricas e gerar_feedback sao acionados."""
        from src.application.pipeline_episodios_micro import PipelineEpisodiosMicro

        mock_comp = MagicMock()
        mock_comp.comparar_metricas.return_value = MagicMock()
        mock_comp.gerar_feedback.return_value = MagicMock(
            recommended_action="CONTINUE",
            confidence=0.9,
        )
        pipeline = PipelineEpisodiosMicro(
            db_path=db_temp,
            baseline_comparator=mock_comp,
        )

        for i in range(5):
            pipeline.registrar_fechamento(
                ticket=f"TAC9_{i}",
                direction="COMPRA",
                entry_price=130000.0,
                exit_price=130500.0,
                stop_loss=129700.0,
                take_profit=131000.0,
                pnl=500.0,
                motivo_saida="TAKE_PROFIT",
                duracao_s=900,
                context_entrada=contexto_entrada_basico,
            )

        pipeline.acionar_baseline_comparator()

        mock_comp.comparar_metricas.assert_called_once()
        mock_comp.gerar_feedback.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Teste de fluxo completo
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestFluxoCompleto:
    """Testa o fluxo trade -> episodio -> feedback -> retreinamento."""

    def test_fluxo_20_trades_ativa_retreinamento(self, db_temp):
        """DADO: Pipeline com DriftDetector e OnlineLearning mockados.
        QUANDO: 20 trades sao simulados (mix de wins e losses).
        ENTAO:
            - Todos os 20 episodios estao no banco
            - DriftDetector foi chamado (>= 10 episodios)
            - OnlineLearning foi chamado (>= 20 episodios)
            - Win rate calculado corretamente
        """
        from src.application.pipeline_episodios_micro import PipelineEpisodiosMicro

        mock_drift = MagicMock()
        mock_drift.detectar_drift.return_value = []
        mock_learning = MagicMock()
        mock_learning.train_incremental.return_value = {"samples_trained": 20}

        pipeline = PipelineEpisodiosMicro(
            db_path=db_temp,
            drift_detector=mock_drift,
            online_learning=mock_learning,
        )

        ctx = {
            "macro_score": 5,
            "macro_signal": "BULLISH",
            "macro_confidence": 0.68,
            "micro_score": 3,
            "micro_trend": "CONTINUACAO",
            "adx": 25.0,
            "rsi": 58.0,
            "smc_direction": "BULLISH",
            "confianca": 55.0,
            "reason": "Confluencia VWAP+SMC",
            "preco": 130000.0,
            "sl": 129700.0,
            "tp": 130600.0,
            "risk_reward": 2.0,
            "timestamp_entrada": "2026-03-18T10:00:00",
        }

        # 12 wins e 8 losses
        for i in range(20):
            pnl = 300.0 if i < 12 else -200.0
            exit_price = 130300.0 if i < 12 else 129800.0
            motivo = "TAKE_PROFIT" if i < 12 else "STOP_LOSS"
            pipeline.registrar_fechamento(
                ticket=f"TFLUXO_{i:02d}",
                direction="COMPRA",
                entry_price=130000.0,
                exit_price=exit_price,
                stop_loss=129700.0,
                take_profit=130600.0,
                pnl=pnl,
                motivo_saida=motivo,
                duracao_s=900,
                context_entrada=ctx,
            )

        # Todos os episodios foram persistidos
        total = pipeline.contar_episodios()
        assert total == 20

        # Drift detector acionado a partir de 10 episodios
        assert mock_drift.detectar_drift.call_count >= 1

        # Online learning acionado a partir de 20 episodios
        assert mock_learning.train_incremental.call_count >= 1

        # Win rate calculado corretamente (12/20 = 0.6)
        wr = pipeline.calcular_win_rate_real()
        assert abs(wr - 0.6) < 0.01

        # Execution feedback tem 20 entradas
        conn = sqlite3.connect(db_temp)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM execution_feedback")
        n_feedback = cur.fetchone()[0]
        conn.close()
        assert n_feedback == 20
