"""Testes para Etapa 3: Monitoring do P1-LEARNING Framework.

Objetivo: Validar rastreamento de posição durante sua evolução.

Type hints: 100%
Docstrings: 100%
Português: 100%
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import pytest
from typing import List, Dict, Any


@pytest.fixture
def temp_db() -> Path:
    """Cria banco de dados temporário para testes."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = Path(f.name)
    yield db_path
    # Cleanup
    db_path.unlink(missing_ok=True)


class TestPositionMonitoringDataClass:
    """Testes da dataclass PositionUpdate."""

    def test_criar_position_update_completo(self) -> None:
        """Criar PositionUpdate com todos os campos."""
        from src.application.p1_learning_monitoring import PositionUpdate

        update = PositionUpdate(
            timestamp=datetime.now(),
            episode_id="EP_20260316_140030",
            trade_id="TRD_20260316_140030",
            current_price=105.50,
            entry_price=105.00,
            unrealized_pnl=50.00,
            unrealized_pnl_pct=0.48,
            position_size=1,
            duration_seconds=300,
            market_conditions={"volatility": 1.2, "trend": "UP"},
        )

        assert update.episode_id == "EP_20260316_140030"
        assert update.current_price == 105.50
        assert update.unrealized_pnl == 50.00
        assert update.unrealized_pnl_pct == 0.48

    def test_position_update_para_dict(self) -> None:
        """Converter PositionUpdate para dicionário."""
        from src.application.p1_learning_monitoring import PositionUpdate

        update = PositionUpdate(
            timestamp=datetime(2026, 3, 16, 14, 0, 30),
            episode_id="EP_TEST_001",
            trade_id="TRD_TEST_001",
            current_price=100.0,
            entry_price=100.0,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            position_size=1,
            duration_seconds=0,
            market_conditions={},
        )

        result = update.para_dict()
        assert isinstance(result, dict)
        assert result["episode_id"] == "EP_TEST_001"
        assert result["current_price"] == 100.0
        assert "timestamp" in result


class TestPositionMonitor:
    """Testes da classe principal PositionMonitor."""

    def test_inicializar_position_monitor(self, temp_db: Path) -> None:
        """Inicializar PositionMonitor com banco de dados."""
        from src.application.p1_learning_monitoring import PositionMonitor

        monitor = PositionMonitor(db_path=str(temp_db))
        assert monitor is not None
        # Verificar que tabela foi criada
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='position_monitoring'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_registrar_position_update_simples(self, temp_db: Path) -> None:
        """Registrar atualização simples de posição."""
        from src.application.p1_learning_monitoring import PositionMonitor

        monitor = PositionMonitor(db_path=str(temp_db))
        update_id = monitor.registrar_atualizacao_posicao(
            episode_id="EP_20260316_140030",
            trade_id="TRD_20260316_140030",
            current_price=105.50,
            entry_price=105.00,
            unrealized_pnl=50.00,
            unrealized_pnl_pct=0.48,
            position_size=1,
            duration_seconds=30,
            market_conditions={"volatility": 1.2},
        )

        assert update_id is not None
        assert isinstance(update_id, str)

    def test_registrar_multiplas_atualizacoes(self, temp_db: Path) -> None:
        """Registrar múltiplas atualizações para mesma posição."""
        from src.application.p1_learning_monitoring import PositionMonitor

        monitor = PositionMonitor(db_path=str(temp_db))
        episode_id = "EP_20260316_140030"

        # Update 1
        monitor.registrar_atualizacao_posicao(
            episode_id=episode_id,
            trade_id="TRD_001",
            current_price=105.00,
            entry_price=105.00,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            position_size=1,
            duration_seconds=0,
            market_conditions={},
        )

        # Update 2 (10 segundos depois)
        monitor.registrar_atualizacao_posicao(
            episode_id=episode_id,
            trade_id="TRD_001",
            current_price=105.50,
            entry_price=105.00,
            unrealized_pnl=50.0,
            unrealized_pnl_pct=0.48,
            position_size=1,
            duration_seconds=10,
            market_conditions={"volatility": 1.2},
        )

        # Update 3 (20 segundos depois)
        monitor.registrar_atualizacao_posicao(
            episode_id=episode_id,
            trade_id="TRD_001",
            current_price=105.30,
            entry_price=105.00,
            unrealized_pnl=30.0,
            unrealized_pnl_pct=0.29,
            position_size=1,
            duration_seconds=20,
            market_conditions={"volatility": 1.15},
        )

        # Listar e verificar
        updates = monitor.listar_atualizacoes_posicao(episode_id)
        assert len(updates) == 3

    def test_listar_atualizacoes_por_episode(self, temp_db: Path) -> None:
        """Listar todas as atualizações de um episode."""
        from src.application.p1_learning_monitoring import PositionMonitor

        monitor = PositionMonitor(db_path=str(temp_db))
        episode_id = "EP_20260316_TESTE"

        for i in range(5):
            monitor.registrar_atualizacao_posicao(
                episode_id=episode_id,
                trade_id="TRD_001",
                current_price=100.0 + i,
                entry_price=100.0,
                unrealized_pnl=float(i),
                unrealized_pnl_pct=i * 0.01,
                position_size=1,
                duration_seconds=i * 10,
                market_conditions={},
            )

        updates = monitor.listar_atualizacoes_posicao(episode_id)
        assert len(updates) == 5

    def test_obter_ultima_atualizacao(self, temp_db: Path) -> None:
        """Obter última atualização registrada."""
        from src.application.p1_learning_monitoring import PositionMonitor

        monitor = PositionMonitor(db_path=str(temp_db))
        episode_id = "EP_ULTIMA_TEST"

        # Registrar 3 updates
        for i in range(3):
            monitor.registrar_atualizacao_posicao(
                episode_id=episode_id,
                trade_id="TRD_001",
                current_price=100.0 + i,
                entry_price=100.0,
                unrealized_pnl=float(i * 10),
                unrealized_pnl_pct=i * 0.1,
                position_size=1,
                duration_seconds=i * 60,
                market_conditions={},
            )

        ultima = monitor.obter_ultima_atualizacao(episode_id)
        assert ultima is not None
        assert ultima.current_price == 102.0  # Terceira iteração
        assert ultima.unrealized_pnl == 20.0

    def test_calcular_estatisticas_posicao(self, temp_db: Path) -> None:
        """Calcular estatísticas agregadas de posição."""
        from src.application.p1_learning_monitoring import PositionMonitor

        monitor = PositionMonitor(db_path=str(temp_db))
        episode_id = "EP_STATS"

        prices = [105.0, 105.50, 105.30, 105.80]
        for i, price in enumerate(prices):
            pnl = (price - 105.0) * 1
            monitor.registrar_atualizacao_posicao(
                episode_id=episode_id,
                trade_id="TRD_001",
                current_price=price,
                entry_price=105.0,
                unrealized_pnl=pnl,
                unrealized_pnl_pct=pnl / 105.0,
                position_size=1,
                duration_seconds=i * 60,
                market_conditions={},
            )

        stats = monitor.calcular_estatisticas_posicao(episode_id)
        assert stats is not None
        assert stats["numero_updates"] == 4
        assert stats["preco_maximo"] == pytest.approx(105.80)
        assert stats["preco_minimo"] == pytest.approx(105.0)
        assert stats["pnl_maximo"] == pytest.approx(0.80)
        assert stats["pnl_minimo"] == pytest.approx(0.0)

    def test_estatisticas_contem_campos_obrigatorios(
        self, temp_db: Path
    ) -> None:
        """Verificar que estatísticas contêm campos obrigatórios."""
        from src.application.p1_learning_monitoring import PositionMonitor

        monitor = PositionMonitor(db_path=str(temp_db))
        episode_id = "EP_CAMPOS"

        monitor.registrar_atualizacao_posicao(
            episode_id=episode_id,
            trade_id="TRD_001",
            current_price=100.0,
            entry_price=100.0,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            position_size=1,
            duration_seconds=0,
            market_conditions={},
        )

        stats = monitor.calcular_estatisticas_posicao(episode_id)
        campos_obrigatorios = [
            "numero_updates",
            "preco_maximo",
            "preco_minimo",
            "preco_medio",
            "pnl_maximo",
            "pnl_minimo",
            "pnl_final",
            "volatilidade_intraposicao",
            "tempo_total_segundos",
        ]
        for campo in campos_obrigatorios:
            assert campo in stats, f"Campo {campo} faltando em estatísticas"

    def test_gerar_log_monitoramento(
        self, temp_db: Path, tmp_path: Path
    ) -> None:
        """Gerar relatório de monitoramento em JSON."""
        from src.application.p1_learning_monitoring import PositionMonitor

        monitor = PositionMonitor(db_path=str(temp_db))
        episode_id = "EP_LOG"

        # Registrar algumas atualizações
        for i in range(3):
            monitor.registrar_atualizacao_posicao(
                episode_id=episode_id,
                trade_id="TRD_001",
                current_price=100.0 + i * 0.5,
                entry_price=100.0,
                unrealized_pnl=i * 0.5,
                unrealized_pnl_pct=i * 0.005,
                position_size=1,
                duration_seconds=i * 30,
                market_conditions={"volatility": 1.0 + i * 0.1},
            )

        output_path = tmp_path / "log_monitoramento.json"
        monitor.gerar_log_monitoramento(episode_id, str(output_path))

        assert output_path.exists()
        with open(output_path) as f:
            log_data = json.load(f)

        assert "episode_id" in log_data
        assert "atualizacoes" in log_data
        assert len(log_data["atualizacoes"]) == 3

    def test_validar_integridade_timestamp(self, temp_db: Path) -> None:
        """Validar que timestamps são registrados em ordem."""
        from src.application.p1_learning_monitoring import PositionMonitor

        monitor = PositionMonitor(db_path=str(temp_db))
        episode_id = "EP_TIMESTAMP"

        for i in range(3):
            monitor.registrar_atualizacao_posicao(
                episode_id=episode_id,
                trade_id="TRD_001",
                current_price=100.0 + i,
                entry_price=100.0,
                unrealized_pnl=float(i),
                unrealized_pnl_pct=0.01 * i,
                position_size=1,
                duration_seconds=i * 10,
                market_conditions={},
            )

        updates = monitor.listar_atualizacoes_posicao(episode_id)
        # Verificar que timestamps estão em ordem crescente
        for i in range(len(updates) - 1):
            assert updates[i].timestamp <= updates[i + 1].timestamp

    def test_type_hints_100_porcento(self) -> None:
        """Garantir que módulo tem type hints completos."""
        from src.application.p1_learning_monitoring import (
            PositionUpdate,
            PositionMonitor,
        )
        import inspect

        # Verificar PositionUpdate
        sig = inspect.signature(PositionUpdate)
        for param in sig.parameters.values():
            assert param.annotation != inspect.Parameter.empty

        # Verificar PositionMonitor methods
        for method_name, method in inspect.getmembers(
            PositionMonitor, predicate=inspect.isfunction
        ):
            if not method_name.startswith("_"):
                sig = inspect.signature(method)
                assert (
                    sig.return_annotation != inspect.Signature.empty
                ), f"{method_name} sem return type annotation"
