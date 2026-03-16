"""
Testes unitarios para sistema de logging de motivos de bloqueio.

Valida:
- BlockageReason enum com 4 tipos
- BlockageLog dataclass com estrutura correta
- BlockageLogger com export CSV
- Funcionalidades gerais de rastreamento
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List

import pytest

from src.application.blockage_logging import (
    BlockageReason,
    BlockageLog,
    BlockageLogger,
)


class TestBlockageReasonEnum:
    """Testes para BlockageReason enum."""

    def test_blockage_reason_tipos(self) -> None:
        """Valida que todos 4 tipos de bloqueio existem."""
        assert hasattr(BlockageReason, "HOURLY_LIMIT_EXCEEDED")
        assert hasattr(BlockageReason, "COOLDOWN_ACTIVE")
        assert hasattr(BlockageReason, "LOSS_STREAK_COOLDOWN")
        assert hasattr(BlockageReason, "OUTSIDE_TRADING_HOURS")

    def test_blockage_reason_valor_string(self) -> None:
        """Valida que enum tem valores em string."""
        assert isinstance(BlockageReason.HOURLY_LIMIT_EXCEEDED.value, str)
        assert BlockageReason.HOURLY_LIMIT_EXCEEDED.value == "HOURLY_LIMIT_EXCEEDED"

    def test_blockage_reason_count(self) -> None:
        """Valida que tem exatamente 4 tipos."""
        tipos = list(BlockageReason)
        assert len(tipos) == 4


class TestBlockageLogDataclass:
    """Testes para BlockageLog dataclass."""

    def test_criar_blockage_log_completo(self) -> None:
        """Cria um BlockageLog com todos os campos."""
        log = BlockageLog(
            timestamp=datetime.now(),
            motivo=BlockageReason.HOURLY_LIMIT_EXCEEDED,
            detalhes="3 trades na ultima hora",
            agent_session_id="agente_20260316_103045",
        )
        assert log.timestamp is not None
        assert log.motivo == BlockageReason.HOURLY_LIMIT_EXCEEDED
        assert log.detalhes == "3 trades na ultima hora"
        assert log.agent_session_id == "agente_20260316_103045"

    def test_blockage_log_para_dict(self) -> None:
        """Converte BlockageLog para dicionario."""
        agora = datetime.now()
        log = BlockageLog(
            timestamp=agora,
            motivo=BlockageReason.COOLDOWN_ACTIVE,
            detalhes="5 min entre trades",
            agent_session_id="agente_test",
        )
        resultado = log.para_dict()
        assert isinstance(resultado, dict)
        assert resultado["motivo"] == "COOLDOWN_ACTIVE"
        assert resultado["detalhes"] == "5 min entre trades"
        assert resultado["agent_session_id"] == "agente_test"

    def test_blockage_log_timestamp_iso(self) -> None:
        """Timestamp é convertido em ISO 8601 no dict."""
        agora = datetime(2026, 3, 16, 10, 30, 45)
        log = BlockageLog(
            timestamp=agora,
            motivo=BlockageReason.LOSS_STREAK_COOLDOWN,
            detalhes="2+ perdas consecutivas",
            agent_session_id="agente_test",
        )
        resultado = log.para_dict()
        assert resultado["timestamp"] == "2026-03-16T10:30:45"


class TestBlockageLogger:
    """Testes para BlockageLogger class."""

    @pytest.fixture
    def temp_session_id(self) -> str:
        """Session ID temporario para testes."""
        return "agente_test_20260316"

    @pytest.fixture
    def logger(self, temp_session_id: str) -> BlockageLogger:
        """Cria BlockageLogger para testes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_dir = Path(tmpdir)
            logger = BlockageLogger(temp_session_id, outputs_dir)
            yield logger

    def test_inicializar_logger(self, temp_session_id: str) -> None:
        """Inicializa BlockageLogger corretamente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_dir = Path(tmpdir)
            logger = BlockageLogger(temp_session_id, outputs_dir)
            assert logger.agent_session_id == temp_session_id
            assert logger.outputs_dir == outputs_dir
            assert logger.bloqueios == []

    def test_registrar_bloqueio_simples(
        self, logger: BlockageLogger
    ) -> None:
        """Registra um bloqueio simples."""
        logger.registrar_bloqueio(
            motivo=BlockageReason.HOURLY_LIMIT_EXCEEDED,
            detalhes="teste",
        )
        assert len(logger.bloqueios) == 1
        assert logger.bloqueios[0].motivo == BlockageReason.HOURLY_LIMIT_EXCEEDED

    def test_registrar_multiplos_bloqueios(
        self, logger: BlockageLogger
    ) -> None:
        """Registra multiplos bloqueios."""
        logger.registrar_bloqueio(BlockageReason.HOURLY_LIMIT_EXCEEDED, "1")
        logger.registrar_bloqueio(BlockageReason.COOLDOWN_ACTIVE, "2")
        logger.registrar_bloqueio(
            BlockageReason.OUTSIDE_TRADING_HOURS, "3"
        )
        assert len(logger.bloqueios) == 3

    def test_exportar_csv(self, logger: BlockageLogger) -> None:
        """Exporta bloqueios para CSV."""
        logger.registrar_bloqueio(
            BlockageReason.HOURLY_LIMIT_EXCEEDED, "teste1"
        )
        logger.registrar_bloqueio(BlockageReason.COOLDOWN_ACTIVE, "teste2")

        arquivo_csv = logger.exportar_csv()
        assert arquivo_csv.exists()
        assert arquivo_csv.suffix == ".csv"

        # Verifica conteudo
        conteudo = arquivo_csv.read_text(encoding="utf-8")
        assert "timestamp" in conteudo
        assert "motivo" in conteudo
        assert "detalhes" in conteudo
        assert "HOURLY_LIMIT_EXCEEDED" in conteudo
        assert "COOLDOWN_ACTIVE" in conteudo

    def test_exportar_json(self, logger: BlockageLogger) -> None:
        """Exporta bloqueios para JSON."""
        logger.registrar_bloqueio(
            BlockageReason.LOSS_STREAK_COOLDOWN, "teste"
        )

        arquivo_json = logger.exportar_json()
        assert arquivo_json.exists()
        assert arquivo_json.suffix == ".json"

        # Verifica conteudo
        with open(arquivo_json, "r", encoding="utf-8") as f:
            dados = json.load(f)
        assert isinstance(dados, dict)
        assert "bloqueios" in dados
        assert len(dados["bloqueios"]) == 1
        assert dados["bloqueios"][0]["motivo"] == "LOSS_STREAK_COOLDOWN"

    def test_obter_estatisticas(self, logger: BlockageLogger) -> None:
        """Calcula estatisticas de bloqueios."""
        logger.registrar_bloqueio(BlockageReason.HOURLY_LIMIT_EXCEEDED, "1")
        logger.registrar_bloqueio(BlockageReason.HOURLY_LIMIT_EXCEEDED, "2")
        logger.registrar_bloqueio(BlockageReason.COOLDOWN_ACTIVE, "3")

        stats = logger.obter_estatisticas()
        assert stats["total_bloqueios"] == 3
        assert stats["HOURLY_LIMIT_EXCEEDED"] == 2
        assert stats["COOLDOWN_ACTIVE"] == 1
        assert stats["LOSS_STREAK_COOLDOWN"] == 0
        assert stats["OUTSIDE_TRADING_HOURS"] == 0

    def test_gerar_relatorio_markdown(self, logger: BlockageLogger) -> None:
        """Gera relatorio em Markdown."""
        logger.registrar_bloqueio(
            BlockageReason.HOURLY_LIMIT_EXCEEDED, "muitos trades"
        )
        logger.registrar_bloqueio(BlockageReason.COOLDOWN_ACTIVE, "esperar")

        relatorio = logger.gerar_relatorio_markdown()
        assert isinstance(relatorio, str)
        assert "HOURLY_LIMIT_EXCEEDED" in relatorio
        assert "COOLDOWN_ACTIVE" in relatorio
        assert "Total de bloqueios" in relatorio


class TestBlockageLoggerIntegracao:
    """Testes de integracao completa."""

    def test_workflow_completo(self) -> None:
        """Testa workflow completo: registrar, exportar, relatorio."""
        with tempfile.TemporaryDirectory() as tmpdir:
            outputs_dir = Path(tmpdir)
            logger = BlockageLogger("agente_int_test", outputs_dir)

            # Registra bloqueios variaos
            logger.registrar_bloqueio(
                BlockageReason.HOURLY_LIMIT_EXCEEDED,
                "3 trades ultimos 60 min",
            )
            logger.registrar_bloqueio(
                BlockageReason.COOLDOWN_ACTIVE,
                "apenas 2 min desde ultimo trade",
            )
            logger.registrar_bloqueio(
                BlockageReason.LOSS_STREAK_COOLDOWN,
                "2 perdas consecutivas, aguardando 30 min",
            )

            # Exporta
            csv_path = logger.exportar_csv()
            json_path = logger.exportar_json()

            assert csv_path.exists()
            assert json_path.exists()

            # Verifica conteudo CSV
            csv_content = csv_path.read_text()
            assert "HOURLY_LIMIT_EXCEEDED" in csv_content
            assert "COOLDOWN_ACTIVE" in csv_content
            assert "LOSS_STREAK_COOLDOWN" in csv_content

            # Verifica conteudo JSON
            with open(json_path) as f:
                json_data = json.load(f)
            assert len(json_data["bloqueios"]) == 3

            # Verifica relatorio
            relatorio = logger.gerar_relatorio_markdown()
            assert "Total de bloqueios:**" in relatorio
            assert "3" in relatorio

    def test_exportar_sem_bloqueios(self) -> None:
        """Exporta quando nao ha bloqueios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = BlockageLogger("agente_vazio", Path(tmpdir))

            csv_path = logger.exportar_csv()
            json_path = logger.exportar_json()

            assert csv_path.exists()
            assert json_path.exists()

            # CSV deve ter header mas sem dados
            csv_content = csv_path.read_text()
            assert "timestamp" in csv_content

            # JSON deve ter lista vazia
            with open(json_path) as f:
                json_data = json.load(f)
            assert json_data["bloqueios"] == []
