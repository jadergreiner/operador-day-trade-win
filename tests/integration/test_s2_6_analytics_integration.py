#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Testes de Integração S2-6 Analytics com Operador Auto-Trade
"""

import pytest
import requests
from unittest.mock import patch, MagicMock
from src.adapters.s2_6_analytics_adapter import (
    AnalyticsAdapter,
    TradeEvent,
    get_analytics_adapter,
    reset_analytics_adapter
)


class TestAnalyticsAdapter:
    """Testes do adapter S2-6 Analytics"""

    @pytest.fixture
    def adapter(self):
        """Cria adapter com mock da API"""
        adapter = AnalyticsAdapter("http://localhost:8000")
        adapter.enabled = True  # Force enable para testes
        return adapter

    def test_trade_event_creation(self):
        """Testa criação de TradeEvent"""
        event = TradeEvent(
            symbol="WINFUT",
            action="EXECUTE",
            trader_decision="confluencia_smc",
            p_and_l=150.50
        )

        assert event.symbol == "WINFUT"
        assert event.action == "EXECUTE"
        assert event.p_and_l == 150.50

    @patch('requests.Session.post')
    def test_log_intervention_success(self, mock_post, adapter):
        """Testa registro de intervenção com sucesso"""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"intervention_id": 42, "status": "logged"}
        mock_post.return_value = mock_response

        event = TradeEvent(
            symbol="WINFUT",
            action="OVERRIDE",
            trader_decision="override_long",
            p_and_l=100.0
        )

        intervention_id = adapter.log_intervention(event)

        assert intervention_id == 42
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/api/intervention/log" in call_args[0][0]

    @patch('requests.Session.post')
    def test_log_intervention_failure(self, mock_post, adapter):
        """Testa falha ao registrar intervenção"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        event = TradeEvent(
            symbol="WINFUT",
            action="EXECUTE",
            trader_decision="test",
        )

        intervention_id = adapter.log_intervention(event)

        assert intervention_id is None

    @patch('requests.Session.post')
    def test_update_result_success(self, mock_post, adapter):
        """Testa atualização de resultado com sucesso"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "updated"}
        mock_post.return_value = mock_response

        success = adapter.update_result(
            intervention_id=42,
            result="WIN",
            p_and_l=250.50
        )

        assert success is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "/api/intervention/42/result" in call_args[0][0]
        assert call_args[1]["json"]["result"] == "WIN"

    @patch('requests.Session.post')
    def test_update_result_with_zero_id(self, mock_post, adapter):
        """Testa que update_result rejeita ID vazio"""
        success = adapter.update_result(
            intervention_id=0,
            result="WIN",
            p_and_l=100.0
        )

        assert success is False
        mock_post.assert_not_called()

    @patch('requests.Session.get')
    def test_get_stats_success(self, mock_get, adapter):
        """Testa obtenção de estatísticas"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_interventions": 10,
            "wins": 6,
            "losses": 3,
            "partials": 1,
            "win_rate": 0.60,
            "total_pnl": 1500.50
        }
        mock_get.return_value = mock_response

        stats = adapter.get_stats()

        assert stats is not None
        assert stats["total_interventions"] == 10
        assert stats["win_rate"] == 0.60
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_get_stats_with_symbol_filter(self, mock_get, adapter):
        """Testa obtenção de stats com filtro por símbolo"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total_interventions": 5}
        mock_get.return_value = mock_response

        stats = adapter.get_stats(symbol="WINFUT")

        assert stats is not None
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["params"]["symbol"] == "WINFUT"

    @patch('requests.Session.get')
    def test_get_dashboard_success(self, mock_get, adapter):
        """Testa obtenção do dashboard"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "OVERRIDE": 5,
            "EXECUTE": 3,
            "PAUSE": 2,
            "CANCEL": 0
        }
        mock_get.return_value = mock_response

        dashboard = adapter.get_dashboard()

        assert dashboard is not None
        assert dashboard["OVERRIDE"] == 5
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_health_check_success(self, mock_get):
        """Testa health check com sucesso"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        adapter = AnalyticsAdapter("http://localhost:8000")

        assert adapter.enabled is True

    @patch('requests.Session.get')
    def test_health_check_failure(self, mock_get):
        """Testa health check com falha"""
        mock_get.side_effect = Exception("Connection refused")

        adapter = AnalyticsAdapter("http://localhost:8000")

        assert adapter.enabled is False

    def test_singleton_pattern(self):
        """Testa padrão singleton do adapter"""
        reset_analytics_adapter()

        adapter1 = get_analytics_adapter("http://localhost:8000")
        adapter2 = get_analytics_adapter("http://localhost:8000")

        assert adapter1 is adapter2

    @patch('requests.Session.post')
    def test_timeout_handling(self, mock_post, adapter):
        """Testa handling de timeout"""
        mock_post.side_effect = requests.Timeout()

        event = TradeEvent(
            symbol="WINFUT",
            action="EXECUTE",
            trader_decision="test"
        )

        intervention_id = adapter.log_intervention(event)

        assert intervention_id is None


class TestOperadorIntegration:
    """Testes de integração do operador com S2-6 Analytics"""

    @patch('src.adapters.s2_6_analytics_adapter.AnalyticsAdapter.log_intervention')
    @patch('src.adapters.s2_6_analytics_adapter.AnalyticsAdapter.update_result')
    def test_complete_trade_lifecycle(self, mock_update, mock_log):
        """Testa ciclo completo: log → trade execution → update result"""
        from examples.operador_com_s2_6_analytics import OperadorComAnalytics

        mock_log.return_value = 42  # intervention_id
        mock_update.return_value = True

        operador = OperadorComAnalytics("http://localhost:8000")

        # 1. Execute trade
        intervention_id = operador.on_trade_executed(
            symbol="WINFUT",
            action="EXECUTE",
            decision="confluencia_smc",
            entry_price=127450.00,
            p_and_l_inicial=0.0
        )

        assert intervention_id == 42
        mock_log.assert_called_once()
        assert "WINFUT_127450.0" in operador.active_trades

        # 2. Close trade with profit
        success = operador.on_trade_closed(
            symbol="WINFUT",
            entry_price=127450.00,
            exit_price=127500.00,
            p_and_l_final=250.00,
            reason="tp_hit"
        )

        assert success is True
        mock_update.assert_called_once()
        call_args = mock_update.call_args
        assert call_args[0][0] == 42  # intervention_id
        assert call_args[0][1] == "WIN"  # result
        assert call_args[0][2] == 250.00  # p_and_l
        assert "WINFUT_127450.0" not in operador.active_trades  # Cleaned up


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
