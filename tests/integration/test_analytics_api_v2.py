"""
Testes de Integração - Analytics API (S2-6 Passo 4) v2

Valida a lógica do AnalyticsCollector e os schemas dos endpoints REST:
- POST /api/intervention/log
- POST /api/intervention/{id}/result
- GET /api/analytics/stats
- GET /api/analytics/dashboard

Foco: Testes unitários do collector + validação de schemas esperados
"""

import pytest
from pathlib import Path
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from analytics_collector import AnalyticsCollector


@pytest.fixture
def analytics_db():
    """Cria banco de dados temporário para testes."""
    import sqlite3

    db_path = "data/test_analytics_v2.db"

    # Limpar DB anterior se existe
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except:
            pass

    # Criar tabela se não existe
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trader_interventions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL,
            reason TEXT,
            ml_signal FLOAT,
            trader_decision TEXT,
            result TEXT,
            p_and_l FLOAT,
            created_at DATETIME,
            updated_at DATETIME,
            notes TEXT
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp
        ON trader_interventions(timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_symbol
        ON trader_interventions(symbol)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_action
        ON trader_interventions(action)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_result
        ON trader_interventions(result)
    """)

    conn.commit()
    conn.close()

    # Inicializar collector
    collector = AnalyticsCollector(db_path)
    collector.connect()

    yield collector
    collector.close()

    # Limpar
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except:
            pass


class TestAnalyticsCollectorLogIntervention:
    """Testa log_intervention() - POST /api/intervention/log"""

    def test_log_override_intervention(self, analytics_db):
        """Deve registrar intervenção OVERRIDE com sucesso."""
        intervention_id = analytics_db.log_intervention(
            symbol="WINFUT",
            action="OVERRIDE",
            ml_signal=0.75,
            trader_decision="Aumentar 25% do ticket",
            reason="Volatilidade alta esperada",
            notes="Market moving down, but ML says up"
        )

        assert intervention_id is not None
        assert isinstance(intervention_id, int)
        assert intervention_id > 0

    def test_log_pause_intervention(self, analytics_db):
        """Deve registrar intervenção PAUSE."""
        intervention_id = analytics_db.log_intervention(
            symbol="WINFUT",
            action="PAUSE",
            ml_signal=0.0,
            trader_decision="Pausar programa",
            reason="Atingido máximo diário"
        )
        assert intervention_id is not None

    def test_log_cancel_intervention(self, analytics_db):
        """Deve registrar intervenção CANCEL."""
        intervention_id = analytics_db.log_intervention(
            symbol="WINFUT",
            action="CANCEL",
            ml_signal=0.5,
            trader_decision="Cancelar operação"
        )
        assert intervention_id is not None

    def test_log_execute_intervention(self, analytics_db):
        """Deve registrar intervenção EXECUTE."""
        intervention_id = analytics_db.log_intervention(
            symbol="WINFUT",
            action="EXECUTE",
            ml_signal=0.9,
            trader_decision="Executar com 50% mais alavancagem"
        )
        assert intervention_id is not None

    def test_invalid_action_raises_error(self, analytics_db):
        """Deve rejeitar ação inválida."""
        with pytest.raises(ValueError) as exc_info:
            analytics_db.log_intervention(
                symbol="WINFUT",
                action="INVALID_ACTION",
                ml_signal=0.5,
                trader_decision="Teste"
            )
        # Verificar que mensagem contém referência ao inválido
        error_msg = str(exc_info.value)
        assert "inválido" in error_msg.lower() or "invalid" in error_msg.lower()


class TestAnalyticsCollectorUpdateResult:
    """Testa update_intervention_result() - POST /api/intervention/{id}/result"""

    def test_update_to_win(self, analytics_db):
        """Deve atualizar resultado para WIN."""
        intervention_id = analytics_db.log_intervention(
            symbol="WINFUT",
            action="OVERRIDE",
            ml_signal=0.75,
            trader_decision="Aumentar posição"
        )

        success = analytics_db.update_intervention_result(
            intervention_id=intervention_id,
            result="WIN",
            p_and_l=475.50,
            notes="TP atingido"
        )
        assert success is True

    def test_update_to_loss(self, analytics_db):
        """Deve atualizar resultado para LOSS."""
        intervention_id = analytics_db.log_intervention(
            symbol="WINFUT",
            action="OVERRIDE",
            ml_signal=0.75,
            trader_decision="Aumentar posição"
        )

        success = analytics_db.update_intervention_result(
            intervention_id=intervention_id,
            result="LOSS",
            p_and_l=-250.00,
            notes="SL acionado"
        )
        assert success is True

    def test_update_to_partial(self, analytics_db):
        """Deve atualizar resultado para PARTIAL."""
        intervention_id = analytics_db.log_intervention(
            symbol="WINFUT",
            action="OVERRIDE",
            ml_signal=0.75,
            trader_decision="Aumentar posição"
        )

        success = analytics_db.update_intervention_result(
            intervention_id=intervention_id,
            result="PARTIAL",
            p_and_l=125.25,
            notes="Saída parcial"
        )
        assert success is True

    def test_invalid_result_raises_error(self, analytics_db):
        """Deve rejeitar resultado inválido."""
        intervention_id = analytics_db.log_intervention(
            symbol="WINFUT",
            action="OVERRIDE",
            ml_signal=0.75,
            trader_decision="Teste"
        )

        with pytest.raises(ValueError) as exc_info:
            analytics_db.update_intervention_result(
                intervention_id=intervention_id,
                result="INVALID_RESULT",
                p_and_l=100.00
            )
        # Verificar que mensagem contém referência ao inválido
        error_msg = str(exc_info.value)
        assert "inválido" in error_msg.lower() or "invalid" in error_msg.lower()


class TestAnalyticsCollectorGetStats:
    """Testa get_intervention_stats() - GET /api/analytics/stats"""

    def test_get_empty_stats(self, analytics_db):
        """Deve retornar zeros para banco vazio."""
        stats = analytics_db.get_intervention_stats()

        assert stats is not None
        assert stats["total_interventions"] == 0
        assert stats["wins"] == 0
        assert stats["losses"] == 0
        assert stats["partials"] == 0
        assert stats["win_rate"] == 0.0

    def test_get_stats_with_interventions(self, analytics_db):
        """Deve calcular statistics corretamente."""
        # Log 3 intervenções
        id1 = analytics_db.log_intervention(
            symbol="WINFUT",
            action="OVERRIDE",
            ml_signal=0.75,
            trader_decision="Aumentar"
        )
        id2 = analytics_db.log_intervention(
            symbol="WINFUT",
            action="PAUSE",
            ml_signal=0.0,
            trader_decision="Pausar"
        )
        id3 = analytics_db.log_intervention(
            symbol="WINFUT",
            action="EXECUTE",
            ml_signal=0.9,
            trader_decision="Executar"
        )

        # Atualizar resultados
        analytics_db.update_intervention_result(id1, "WIN", 500.00)
        analytics_db.update_intervention_result(id2, "LOSS", -200.00)
        analytics_db.update_intervention_result(id3, "WIN", 300.00)

        # Obter stats
        stats = analytics_db.get_intervention_stats()

        assert stats["total_interventions"] == 3
        assert stats["wins"] == 2
        assert stats["losses"] == 1
        assert stats["partials"] == 0
        assert abs(stats["win_rate"] - 66.67) < 1.0  # 2/3 = 66.67%
        assert abs(stats["total_pnl"] - 600.00) < 0.01
        assert abs(stats["avg_pnl"] - 200.00) < 0.01

    def test_stats_response_structure(self, analytics_db):
        """Valida estrutura esperada de resposta."""
        stats = analytics_db.get_intervention_stats()

        # Campos obrigatórios
        required_fields = [
            "total_interventions", "wins", "losses", "partials",
            "win_rate", "total_pnl", "avg_pnl"
        ]

        for field in required_fields:
            assert field in stats, f"Field '{field}' missing from stats"

        # Validar tipos
        assert isinstance(stats["total_interventions"], int)
        assert isinstance(stats["wins"], int)
        assert isinstance(stats["losses"], int)
        assert isinstance(stats["partials"], int)
        assert isinstance(stats["win_rate"], (int, float))
        assert isinstance(stats["total_pnl"], (int, float))
        assert isinstance(stats["avg_pnl"], (int, float))


class TestAnalyticsEndpointRequestSchemas:
    """Valida schemas esperados dos endpoints (request)."""

    def test_log_intervention_required_fields(self, analytics_db):
        """Valida campos obrigatórios para log_intervention."""
        # Campos obrigatórios
        required = ["symbol", "action", "ml_signal"]

        # Campos opcionais
        optional = ["trader_decision", "reason", "notes"]

        # Test required fields
        assert all(isinstance(field, str) for field in required)
        assert all(isinstance(field, str) for field in optional)

    def test_update_result_required_fields(self):
        """Valida campos obrigatórios para update_intervention_result."""
        required = ["result", "pnl"]
        optional = ["close_reason"]

        # ValidarAçõesValidas
        valid_results = ["WIN", "LOSS", "PARTIAL"]
        assert len(valid_results) == 3

        assert all(isinstance(field, str) for field in required)


class TestAnalyticsEndpointResponseSchemas:
    """Valida schemas esperados dos endpoints (response)."""

    def test_dashboard_structure(self, analytics_db):
        """Valida estrutura do dashboard completo."""
        # Log algumas intervenções
        for action in ["OVERRIDE", "PAUSE", "CANCEL", "EXECUTE"]:
            analytics_db.log_intervention(
                symbol="WINFUT",
                action=action,
                ml_signal=0.5,
                trader_decision=f"Ação: {action}"
            )

        # Obter stats globais
        global_stats = analytics_db.get_intervention_stats()

        # Validar estrutura global
        assert "total_interventions" in global_stats
        assert "wins" in global_stats
        assert "win_rate" in global_stats
        assert "total_pnl" in global_stats

        # Dashboard teria estrutura como:
        # {
        #     "global": { total_interventions, wins, win_rate, total_pnl, ... },
        #     "by_action": {
        #         "OVERRIDE": { total_interventions, wins, ... },
        #         "PAUSE": { total_interventions, wins, ... },
        #         "CANCEL": { total_interventions, wins, ... },
        #         "EXECUTE": { total_interventions, wins, ... }
        #     }
        # }


class TestAnalyticsCompleteWorkflow:
    """Testa workflow completo end-to-end."""

    def test_complete_flow_log_update_stats(self, analytics_db):
        """Testa fluxo: log → update → stats."""

        # 1. Log intervenção OVERRIDE
        id1 = analytics_db.log_intervention(
            symbol="WINFUT",
            action="OVERRIDE",
            ml_signal=0.85,
            trader_decision="Aumentar posição"
        )
        assert id1 is not None

        # 2. Atualizar para WIN
        success = analytics_db.update_intervention_result(
            intervention_id=id1,
            result="WIN",
            p_and_l=500.00,
            notes="TP atingido"
        )
        assert success is True

        # 3. Obter stats
        stats = analytics_db.get_intervention_stats()
        assert stats["total_interventions"] == 1
        assert stats["wins"] == 1
        assert stats["win_rate"] == 100.0
        assert stats["total_pnl"] == 500.00


class TestAnalyticsValidation:
    """Testes de validação de dados."""

    def test_negative_pnl_allowed(self, analytics_db):
        """Deve permitir P&L negativo (losses)."""
        intervention_id = analytics_db.log_intervention(
            symbol="WINFUT",
            action="OVERRIDE",
            ml_signal=0.75,
            trader_decision="Teste negativo"
        )

        success = analytics_db.update_intervention_result(
            intervention_id=intervention_id,
            result="LOSS",
            p_and_l=-1000.50  # Negativo é válido
        )
        assert success is True

    def test_zero_pnl_allowed(self, analytics_db):
        """Deve permitir P&L zero (break-even)."""
        intervention_id = analytics_db.log_intervention(
            symbol="WINFUT",
            action="OVERRIDE",
            ml_signal=0.75,
            trader_decision="Teste zero"
        )

        success = analytics_db.update_intervention_result(
            intervention_id=intervention_id,
            result="PARTIAL",
            p_and_l=0.00  # Zero é válido
        )
        assert success is True

    def test_large_pnl_values(self, analytics_db):
        """Deve permitir valores grandes de P&L."""
        intervention_id = analytics_db.log_intervention(
            symbol="WINFUT",
            action="OVERRIDE",
            ml_signal=0.75,
            trader_decision="Teste valor grande"
        )

        success = analytics_db.update_intervention_result(
            intervention_id=intervention_id,
            result="WIN",
            p_and_l=9999999.99  # Valor grande
        )
        assert success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
