#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste de Integração: Monitor Operador Integrado + S2-6 Analytics
Valida sincronização 100% em tempo real conforme ROADMAP governance.

Testes:
1. Monitor carrega com sucesso status do operador
2. Monitor conecta com S2-6 Analytics API
3. Monitor renderiza dashboard sem erros
4. Estatísticas são atualizadas em tempo real
5. E2E: Trade flow completo (EXECUTE → WIN) refletido no Monitor
"""

import json
import pytest
import sys
import time
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Adiciona caminho
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.adapters.s2_6_analytics_adapter import AnalyticsAdapter, TradeEvent
from scripts.monitor_operador_integrado import MonitorOperadorIntegrado


class TestMonitorOperadorIntegrado:
    """Tests para o Monitor Operador Integrado"""

    def test_monitor_initialization(self):
        """Verifica se Monitor inicializa com sucesso"""
        monitor = MonitorOperadorIntegrado(
            api_url="http://localhost:8000",
            status_file="logs/deployment_status.json",
            refresh_interval=5,
        )

        assert monitor.api_url == "http://localhost:8000"
        assert monitor.status_file == "logs/deployment_status.json"
        assert monitor.refresh_interval == 5
        assert monitor.adapter is not None

    def test_monitor_loads_operador_status(self, tmp_path):
        """Verifica se Monitor carrega status do operador"""
        # Cria arquivo de status temporário
        status_data = {
            "status": "LIVE",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "WebSocket Server": {"status": "ACTIVE", "port": "8001"},
                "MT5 Connection": {"status": "READY", "account": "12345"},
            },
        }

        status_file = tmp_path / "deployment_status.json"
        status_file.write_text(json.dumps(status_data), encoding="utf-8")

        monitor = MonitorOperadorIntegrado(status_file=str(status_file))
        loaded_status = monitor._load_operador_status()

        assert loaded_status["status"] == "LIVE"
        assert "WebSocket Server" in loaded_status["components"]
        assert loaded_status["components"]["MT5 Connection"]["status"] == "READY"

    def test_monitor_handles_missing_status_file(self):
        """Verifica se Monitor trata arquivo de status faltando"""
        monitor = MonitorOperadorIntegrado(status_file="/nonexistent/path.json")
        status = monitor._load_operador_status()

        assert status["status"] == "DESCONHECIDO"
        assert status["components"] == {}

    def test_monitor_handles_corrupted_status_file(self, tmp_path):
        """Verifica se Monitor trata arquivo corrompido"""
        corrupted_file = tmp_path / "corrupted.json"
        corrupted_file.write_text("{ invalid json }", encoding="utf-8")

        monitor = MonitorOperadorIntegrado(status_file=str(corrupted_file))
        status = monitor._load_operador_status()

        assert status["status"] == "ERRO"

    def test_monitor_formats_title(self):
        """Verifica se title é formatado corretamente"""
        monitor = MonitorOperadorIntegrado()
        title = monitor._format_title()

        assert "MONITOR OPERADOR INTEGRADO v2.0" in title
        assert "SINCRONIZAÇÃO 100% TEMPO REAL" in title
        assert "═" in title  # Caracteres de borda

    def test_monitor_formats_operador_status(self):
        """Verifica formatação de seção de status"""
        monitor = MonitorOperadorIntegrado()
        status = {
            "status": "LIVE",
            "components": {
                "API": {"status": "ACTIVE", "port": "8000"},
            },
        }

        formatted = monitor._format_operador_status(status)

        assert "[OPERADOR DE EXECUÇÃO]" in formatted
        assert "LIVE" in formatted
        assert "API" in formatted
        assert "[✓]" in formatted

    def test_monitor_formats_analytics_stats_online(self):
        """Verifica formatação de stats quando Analytics está online"""
        monitor = MonitorOperadorIntegrado()
        monitor.analytics_enabled = True

        # Mock do adapter
        mock_stats = {
            "total_interventions": 150,
            "win_rate": 0.6233,
            "total_pnl": 15300.00,
            "avg_pnl": 102.00,
            "symbols": {
                "WDOIT": {"count": 45, "win_rate": 0.65, "total_pnl": 8500.00},
                "WINFUT": {"count": 38, "win_rate": 0.61, "total_pnl": 5200.00},
            },
        }

        monitor.adapter.get_stats = Mock(return_value=mock_stats)

        formatted = monitor._format_analytics_stats()

        assert "[✓] S2-6 Analytics ONLINE" in formatted
        assert "Win Rate: 62.33%" in formatted
        assert "P&L Total: R$ 15,300.00" in formatted
        assert "WDOIT" in formatted

    def test_monitor_formats_analytics_stats_offline(self):
        """Verifica formatação de stats quando Analytics está offline"""
        monitor = MonitorOperadorIntegrado()
        monitor.analytics_enabled = False

        formatted = monitor._format_analytics_stats()

        assert "[✗] S2-6 Analytics OFFLINE" in formatted
        assert "Certifique-se de que a API está rodando" in formatted

    def test_monitor_formats_action_breakdown(self):
        """Verifica formatação de breakdown de ações"""
        monitor = MonitorOperadorIntegrado()

        mock_stats = {
            "actions": {
                "EXECUTE": 89,
                "OVERRIDE": 45,
                "PAUSE": 12,
                "CANCEL": 4,
            }
        }

        monitor.adapter.get_stats = Mock(return_value=mock_stats)

        formatted = monitor._format_action_breakdown()

        assert "[BREAKDOWN DE AÇÕES]" in formatted
        assert "EXECUTE" in formatted
        assert "89" in formatted
        assert "OVERRIDE" in formatted

    def test_monitor_formats_recent_trades(self):
        """Verifica formatação de operações recentes"""
        monitor = MonitorOperadorIntegrado()

        mock_stats = {
            "recent_interventions": [
                {
                    "timestamp": "2026-02-24T10:30:45",
                    "symbol": "WDOIT",
                    "action": "EXECUTE",
                    "result": "WIN",
                    "p_and_l": 120.50,
                },
                {
                    "timestamp": "2026-02-24T10:25:30",
                    "symbol": "WINFUT",
                    "action": "OVERRIDE",
                    "result": "LOSS",
                    "p_and_l": -45.20,
                },
            ]
        }

        monitor.adapter.get_stats = Mock(return_value=mock_stats)

        formatted = monitor._format_recent_trades()

        assert "[ÚLTIMAS OPERAÇÕES]" in formatted
        assert "WDOIT" in formatted
        assert "WINFUT" in formatted
        assert "120.50" in formatted
        assert "45.20" in formatted

    def test_monitor_formats_risk_validators(self):
        """Verifica formatação de risk validators"""
        monitor = MonitorOperadorIntegrado()

        formatted = monitor._format_risk_validators()

        assert "[RISK VALIDATORS]" in formatted
        assert "Gate 1: Capital Adequacy" in formatted
        assert "Gate 2: Correlation Check" in formatted
        assert "Gate 3: Volatility Band" in formatted
        assert "Circuit Breaker" in formatted

    def test_monitor_formats_footer(self):
        """Verifica formatação de footer"""
        monitor = MonitorOperadorIntegrado(refresh_interval=5)

        formatted = monitor._format_footer()

        assert "Sincronização: 100%" in formatted
        assert "Atualização a cada 5s" in formatted
        assert "[STATUS]" in formatted


class TestMonitorE2EIntegration:
    """Testes End-to-End de integração completa"""

    def test_e2e_trade_flow_reflected_in_monitor(self, tmp_path):
        """
        E2E Test: Verifica se um trade completo (EXECUTE → WIN)
        é refletido no Monitor após passar pelo S2-6 Analytics
        """

        # 1. Cria arquivo de status simulado
        status_file = tmp_path / "status.json"
        status_data = {
            "status": "LIVE",
            "timestamp": datetime.now().isoformat(),
            "components": {"API": {"status": "ACTIVE"}},
        }
        status_file.write_text(json.dumps(status_data), encoding="utf-8")

        # 2. Cria monitor
        monitor = MonitorOperadorIntegrado(status_file=str(status_file))

        # 3. Simula dados do Analytics após trade
        mock_stats = {
            "total_interventions": 1,
            "win_rate": 1.0,  # 100% win rate (1 de 1)
            "total_pnl": 250.00,
            "avg_pnl": 250.00,
            "symbols": {"WDOIT": {"count": 1, "win_rate": 1.0, "total_pnl": 250.00}},
            "actions": {"EXECUTE": 1},
            "recent_interventions": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "symbol": "WDOIT",
                    "action": "EXECUTE",
                    "result": "WIN",
                    "p_and_l": 250.00,
                }
            ],
        }

        monitor.adapter.get_stats = Mock(return_value=mock_stats)

        # 4. Renderiza monitor
        title = monitor._format_title()
        operador = monitor._format_operador_status(
            monitor._load_operador_status()
        )
        analytics = monitor._format_analytics_stats()
        actions = monitor._format_action_breakdown()
        trades = monitor._format_recent_trades()

        # 5. Valida que trade é refletido em tudo
        full_output = "\n".join(
            [title, operador, analytics, actions, trades]
        )

        assert "MONITOR OPERADOR INTEGRADO" in full_output
        assert "100.00%" in full_output  # Win rate
        assert "250.00" in full_output  # P&L
        assert "WDOIT" in full_output
        assert "EXECUTE" in full_output
        assert "WIN" in full_output

    def test_monitor_resilience_when_analytics_fails(self, tmp_path):
        """
        Verifica se Monitor continua operando se S2-6 Analytics falhar
        """

        status_file = tmp_path / "status.json"
        status_data = {
            "status": "LIVE",
            "components": {"API": {"status": "ACTIVE"}},
        }
        status_file.write_text(json.dumps(status_data), encoding="utf-8")

        monitor = MonitorOperadorIntegrado(status_file=str(status_file))
        monitor.analytics_enabled = False

        # Adapter throws error
        monitor.adapter.get_stats = Mock(
            side_effect=Exception("Connection refused")
        )

        # Monitor deve tratar erro graciosamente
        analytics = monitor._format_analytics_stats()

        assert "[✗] S2-6 Analytics OFFLINE" in analytics
        # Monitor não travou, continuamos operacionais

    def test_monitor_sync_timing(self):
        """
        Verifica se Monitor respeita sincronização a cada N segundos
        """

        monitor = MonitorOperadorIntegrado(refresh_interval=5)

        assert monitor.refresh_interval == 5

        monitor_2s = MonitorOperadorIntegrado(refresh_interval=2)
        assert monitor_2s.refresh_interval == 2

        # Refresh interval pode ser ajustado dinamicamente
        monitor.refresh_interval = 10
        assert monitor.refresh_interval == 10


class TestMonitorDataConsistency:
    """Testes de consistência de dados"""

    def test_monitor_handles_empty_stats(self):
        """Verifica se Monitor trata stats vazios"""
        monitor = MonitorOperadorIntegrado()
        monitor.adapter.get_stats = Mock(return_value={})

        analytics = monitor._format_analytics_stats()
        assert "[✗] S2-6 Analytics OFFLINE" not in analytics  # Não marca como offline
        assert "0" in analytics or "Nenhuma" in analytics  # Mas mostra 0 ou vazio

    def test_monitor_formats_large_numbers(self):
        """Verifica se Monitor formata números grandes corretamente"""
        monitor = MonitorOperadorIntegrado()

        large_stats = {
            "total_interventions": 9999,
            "total_pnl": 999999.99,
            "avg_pnl": 50000.00,
        }

        monitor.adapter.get_stats = Mock(return_value=large_stats)

        analytics = monitor._format_analytics_stats()

        assert "9999" in analytics
        assert "999,999.99" in analytics or "999999.99" in analytics

    def test_monitor_thread_safety(self, tmp_path):
        """Verifica se múltiplas leituras de arquivo é segura"""
        import threading

        status_file = tmp_path / "status.json"
        status_data = {
            "status": "LIVE",
            "components": {},
        }
        status_file.write_text(json.dumps(status_data), encoding="utf-8")

        monitor = MonitorOperadorIntegrado(status_file=str(status_file))

        # Simula múltiplas threads lendo simultaneamente
        results = []

        def read_status():
            for _ in range(10):
                status = monitor._load_operador_status()
                results.append(status["status"])

        threads = [threading.Thread(target=read_status) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Todos devem ter lido "LIVE" sem erro
        assert all(s == "LIVE" for s in results)
        assert len(results) == 30  # 10 reads x 3 threads


class TestMonitorWithRealAdapter:
    """Testes com adapter real (se API estiver disponível)"""

    @pytest.fixture
    def adapter(self):
        """Cria adapter real"""
        return AnalyticsAdapter(api_url="http://localhost:8000")

    def test_monitor_with_real_api_available(self, adapter):
        """Verifica se Monitor funciona com API real"""
        if not adapter.enabled:
            pytest.skip("S2-6 Analytics API not available")

        monitor = MonitorOperadorIntegrado()
        assert monitor.analytics_enabled

        # Deve conseguir carregar stats
        stats = adapter.get_stats()
        assert isinstance(stats, dict)

    def test_monitor_displays_real_stats(self, adapter):
        """Verifica se Monitor exibe stats reais"""
        if not adapter.enabled:
            pytest.skip("S2-6 Analytics API not available")

        monitor = MonitorOperadorIntegrado()
        monitor.adapter = adapter

        stats = adapter.get_stats() or {}
        if stats:
            analytics = monitor._format_analytics_stats()
            assert "[✓] S2-6 Analytics ONLINE" in analytics


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
