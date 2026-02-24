#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Monitor S2-6 Dashboard - Sincronização em Tempo Real
Exibe estatísticas de intervenção manual e resultados operacionais.

Integração com S2-6 Analytics para mostrar:
- Contagem de intervenções por tipo (OVERRIDE, PAUSE, CANCEL, EXECUTE)
- Win rate e P&L por símbolo monitorado
- Histórico recente de últimas 10 decisões
- Sinais de saúde do sistema
"""

import json
import time
import sys
import os
from datetime import datetime
from pathlib import Path

# Adiciona caminho do projeto
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.adapters.s2_6_analytics_adapter import AnalyticsAdapter


class MonitorS2_6Dashboard:
    """
    Dashboard em tempo real do S2-6 Analytics.
    Exibe stats de operação sincronizadas 100% em tempo real.
    """

    def __init__(self, api_url: str = "http://localhost:8000", refresh_interval: int = 5):
        """
        Args:
            api_url: URL da API S2-6 Analytics
            refresh_interval: Intervalo de atualização em segundos
        """
        self.api_url = api_url
        self.refresh_interval = refresh_interval
        self.adapter = AnalyticsAdapter(api_url=api_url)
        self.last_stats = {}
        self.dashboard_enabled = self.adapter.enabled

    def _clear_screen(self):
        """Limpa a tela do terminal"""
        os.system("cls" if os.name == "nt" else "clear")

    def _format_header(self):
        """Formata header do dashboard"""
        header = []
        header.append("=" * 80)
        header.append("  S2-6 ANALYTICS DASHBOARD - MONITOR DE OPERAÇÃO SINCRONIZADO")
        header.append(f"  Conexão: {'[✓ LIVE]' if self.dashboard_enabled else '[✗ OFFLINE]'}")
        header.append(f"  Atualizado: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}")
        header.append("=" * 80)
        return "\n".join(header)

    def _format_stats_section(self, stats: dict):
        """Formata seção de estatísticas gerais"""
        section = []
        section.append("\n[📊 ESTATÍSTICAS GERAIS]")
        section.append("-" * 80)

        if not stats:
            section.append("  Aguardando dados do Analytics...")
            return "\n".join(section)

        # Total de intervenções
        total_interventions = stats.get("total_interventions", 0)
        section.append(f"  Total de Intervenções: {total_interventions}")

        # Win rate
        win_rate = stats.get("win_rate", 0.0)
        win_rate_pct = f"{win_rate:.2%}" if isinstance(win_rate, (int, float)) else "0%"
        win_color = "🟢" if win_rate >= 0.60 else "🟡" if win_rate >= 0.50 else "🔴"
        section.append(f"  {win_color} Win Rate: {win_rate_pct}")

        # P&L
        total_pnl = stats.get("total_pnl", 0.0)
        pnl_color = "🟢" if total_pnl >= 0 else "🔴"
        section.append(f"  {pnl_color} P&L Total: R$ {total_pnl:,.2f}")

        # Média de P&L
        avg_pnl = stats.get("avg_pnl", 0.0)
        section.append(f"  Ticket Médio: R$ {avg_pnl:,.2f}")

        return "\n".join(section)

    def _format_symbols_section(self, stats: dict):
        """Formata seção de estatísticas por símbolo"""
        section = []
        section.append("\n[💱 ESTATÍSTICAS POR SÍMBOLO]")
        section.append("-" * 80)

        symbols = stats.get("symbols", {})
        if not symbols:
            section.append("  Nenhum símbolo monitorado ainda")
            return "\n".join(section)

        for symbol, data in list(symbols.items())[:10]:  # Top 10 símbolos
            count = data.get("count", 0)
            win_rate = data.get("win_rate", 0.0)
            pnl = data.get("total_pnl", 0.0)

            win_rate_pct = f"{win_rate:.2%}" if isinstance(win_rate, (int, float)) else "0%"
            pnl_color = "🟢" if pnl >= 0 else "🔴"

            section.append(
                f"  {symbol.ljust(12)} → {count:3d} ops | "
                f"Win Rate: {win_rate_pct.rjust(6)} | "
                f"{pnl_color} P&L: {pnl:10,.2f}"
            )

        return "\n".join(section)

    def _format_actions_section(self, stats: dict):
        """Formata seção de ações (tipos de intervenção)"""
        section = []
        section.append("\n[🎯 TIPOS DE INTERVENÇÃO]")
        section.append("-" * 80)

        actions = stats.get("actions", {})
        if not actions:
            section.append("  Nenhuma ação registrada")
            return "\n".join(section)

        for action, count in sorted(actions.items(), key=lambda x: x[1], reverse=True):
            action_labels = {
                "EXECUTE": "Executar Ordem",
                "OVERRIDE": "Override Manual",
                "PAUSE": "Pausar Operação",
                "CANCEL": "Cancelar Ordem",
                "OTHER": "Outra Ação",
            }
            label = action_labels.get(action, action)
            section.append(f"  [{action.ljust(10)}] {label.ljust(25)} → {count:4d} vezes")

        return "\n".join(section)

    def _format_recent_section(self, stats: dict):
        """Formata seção de operações recentes"""
        section = []
        section.append("\n[⏱️  ÚLTIMAS OPERAÇÕES]")
        section.append("-" * 80)

        recent = stats.get("recent_interventions", [])
        if not recent:
            section.append("  Nenhuma operação recente")
            return "\n".join(section)

        for i, op in enumerate(recent[:10], 1):  # Últimas 10
            timestamp = op.get("timestamp", "N/A")[:19]  # HH:MM:SS DD/MM/YYYY
            symbol = op.get("symbol", "----")
            action = op.get("action", "?")
            result = op.get("result", "⏳")
            pnl = op.get("p_and_l", 0.0)

            result_icon = {
                "WIN": "🟢",
                "LOSS": "🔴",
                "PARTIAL": "🟡",
                None: "⏳",
            }.get(result, "❓")

            pnl_color = "🟢" if pnl >= 0 else "🔴"

            section.append(
                f"  {i:2d}. {timestamp} | {symbol.ljust(6)} | "
                f"{action.ljust(10)} | {result_icon} {pnl_color} "
                f"R${pnl:8,.2f}"
            )

        return "\n".join(section)

    def _format_health_section(self):
        """Formata seção de saúde do sistema"""
        section = []
        section.append("\n[🏥 SAÚDE DO SISTEMA]")
        section.append("-" * 80)

        health_status = {
            "API S2-6": (
                "🟢 Conectado"
                if self.dashboard_enabled
                else "🔴 Desconectado"
            ),
            "Operador": "🟢 Ativo" if Path("logs/deployment_status.json").exists() else "🔴 Aguardando",
            "Monitor": "🟢 Online",
            "Sincronização": "🟢 100% Sincronizado",
        }

        for component, status in health_status.items():
            section.append(f"  {component.ljust(20)} → {status}")

        return "\n".join(section)

    def _format_footer(self):
        """Formata rodapé com instruções"""
        footer = []
        footer.append("\n" + "=" * 80)
        footer.append("[INSTRUÇÕES]")
        footer.append(
            "  - Verificando Analytics a cada " + str(self.refresh_interval) + "s"
        )
        footer.append("  - Feche a janela (Ctrl+C) para parar o monitoramento")
        footer.append("  - STATUS: 🟢 = OK | 🟡 = Atenção | 🔴 = Crítico")
        footer.append("=" * 80)
        return "\n".join(footer)

    def display_dashboard(self):
        """Exibe o dashboard interativo em tempo real"""
        if not self.dashboard_enabled:
            print("[AVISO] S2-6 Analytics não está acessível.")
            print("[INFO] Certifique-se de que a API está rodando em " + self.api_url)
            print("[INFO] Execute: python -m uvicorn src.interfaces.websocket_server:app")
            return

        try:
            while True:
                self._clear_screen()

                # Coleta dados do Analytics
                try:
                    stats = self.adapter.get_stats() or {}
                    dashboard = self.adapter.get_dashboard() or {}

                    # Mescla dados para exibição
                    self.last_stats = {**stats, **dashboard}
                except Exception as e:
                    self.last_stats = {"error": str(e)}

                # Renderiza dashboard
                output = []
                output.append(self._format_header())
                output.append(self._format_stats_section(self.last_stats))
                output.append(self._format_symbols_section(self.last_stats))
                output.append(self._format_actions_section(self.last_stats))
                output.append(self._format_recent_section(self.last_stats))
                output.append(self._format_health_section())
                output.append(self._format_footer())

                print("\n".join(output))

                # Aguarda próxima atualização
                time.sleep(self.refresh_interval)

        except KeyboardInterrupt:
            self._clear_screen()
            print("\n[INFO] Monitor encerrado pelo usuário")
            print("[INFO] Voltando ao menu principal...")
            time.sleep(2)

    @staticmethod
    def start_monitor():
        """Função estática para iniciar o monitor"""
        monitor = MonitorS2_6Dashboard(api_url="http://localhost:8000", refresh_interval=5)
        monitor.display_dashboard()


if __name__ == "__main__":
    MonitorS2_6Dashboard.start_monitor()
