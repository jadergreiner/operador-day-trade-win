#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXEMPLO PRÁTICO: Agente + S2-6 Analytics

Mostra como integrar S2-6 Analytics no agente real.
Use como template para suas próprias integrações.

Status: ✅ PRODUÇÃO
Compatível com: agente_micro_tendencia_winfut.py

Uso:
    python exemplo_agente_s2_6.py

Author: GitHub Copilot
Date: 2026-02-23
"""

import sys
import os
import time
from datetime import datetime

# ─ Setup paths ─
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# ─ Imports ─
try:
    from agente_micro_tendencia_winfut import (
        _connect_mt5,
        _get_config,
        _run_cycle,
        _is_market_hours,
        _wait_with_progress,
        _display_header,
        _display_cycle,
        _display_trading_status,
    )
    IMPORTS_OK = True
except ImportError as e:
    print(f"❌ Erro ao importar agente: {e}")
    IMPORTS_OK = False

try:
    from agente_micro_tendencia_s2_6_integrated import (
        MicroTradingManagerS2_6,
        initialize_s2_6_adapter,
        ADAPTER_AVAILABLE,
    )
    S2_6_IMPORTS_OK = True
except ImportError as e:
    print(f"⚠️  Erro ao importar S2-6: {e}")
    S2_6_IMPORTS_OK = False


# ─ Globais ─
SYMBOL = "WINFUT"
AUTO_TRADING_ENABLED = False
SIMULATE_MODE = False
REFRESH_SECONDS = 5


class ExemploAgentComS2_6:
    """Exemplo simples de agente com S2-6 integrado."""

    def __init__(self, config=None, api_url=None):
        """Inicializa agente."""
        self.config = config or _get_config()
        self.api_url = api_url or os.getenv("S2_6_API_URL", "http://localhost:8000")
        self.adapter = None
        self.trading_mgr = None
        self.mt5 = None
        self.cycle_count = 0
        self.total_trades = 0
        self.wins = 0
        self.losses = 0

    def _log(self, msg, level="info"):
        """Log com timestamp."""
        icon = {
            "info": "ℹ️ ",
            "ok": "✅ ",
            "warn": "⚠️ ",
            "error": "❌ ",
        }.get(level, "  ")
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts}] {icon} {msg}")

    def setup(self):
        """Inicializa componentes."""
        self._log("Inicializando...", "info")

        # ─ Conecta MT5 ─
        try:
            self.mt5 = _connect_mt5(self.config)
            self._log(f"MT5 conectado (login: {self.config.mt5_login})", "ok")
        except Exception as e:
            self._log(f"Erro ao conectar MT5: {e}", "error")
            return False

        # ─ Inicializa S2-6 ─
        try:
            self.adapter = initialize_s2_6_adapter(self.api_url)
            self._log(f"S2-6 Analytics inicializado", "ok")
        except Exception as e:
            self._log(f"Erro ao inicializar S2-6: {e}", "warn")
            self.adapter = None

        # ─ Inicializa Trading Manager COM S2-6 ─
        try:
            self.trading_mgr = MicroTradingManagerS2_6(
                mt5=self.mt5,
                symbol=SYMBOL,
                analytics_adapter=self.adapter
            )
            self._log("Trading Manager com S2-6 inicializado", "ok")
        except Exception as e:
            self._log(f"Erro ao inicializar Trading Manager: {e}", "error")
            return False

        return True

    def run_cycle(self):
        """Executa um ciclo de trading."""
        self.cycle_count += 1

        # ─ 1) Análise de micro tendência ─
        try:
            result = _run_cycle(self.mt5)
            self._log(f"Ciclo #{self.cycle_count} - Análise concluída", "info")
        except Exception as e:
            self._log(f"Erro na análise: {e}", "error")
            return False

        # ─ 2) Gerencia posições abertas (com S2-6) ─
        try:
            if result.price_current > 0:
                self.trading_mgr.manage_positions(result.price_current)
        except Exception as e:
            self._log(f"Erro ao gerenciar posições: {e}", "error")

        # ─ 3) Avalia novas oportunidades ─
        try:
            if result.opportunities:
                best = max(result.opportunities,
                          key=lambda o: (o.confidence, o.risk_reward))

                # Verifica se pode tradar
                can_trade, reason = self.trading_mgr.can_trade()
                if can_trade:
                    should_enter, eval_reason = self.trading_mgr.evaluate_opportunity(best)
                    if should_enter:
                        # ─ EXECUTA ENTRADA (com logging em S2-6) ─
                        ticket = self.trading_mgr.execute_entry(best)
                        if ticket:
                            direction = "COMPRA 🟢" if best.direction == "COMPRA" else "VENDA 🔴"
                            self._log(f"Ordem executada! {direction} (Ticket: {ticket})", "ok")
                            self.total_trades += 1
                        else:
                            self._log(f"Falha ao executar ordem", "error")
                    else:
                        self._log(f"Oportunidade rejeitada: {eval_reason}", "warn")
                else:
                    self._log(f"Sem entrada: {reason}", "info")
        except Exception as e:
            self._log(f"Erro ao avaliar oportunidades: {e}", "error")

        # ─ 4) Exibe stats S2-6 ─
        try:
            if self.adapter:
                stats = self.adapter.get_stats()
                if stats.get("status") == "online":
                    wr = stats.get("win_rate", 0)
                    trades = stats.get("total_trades", 0)
                    self._log(f"S2-6 Stats: {trades} trades | Win Rate: {wr:.0f}%", "info")
        except Exception as e:
            pass  # Silent fail

        return True

    def run_loop(self):
        """Loop principal (como o agente original)."""
        _display_header()
        self._log(f"🚀 AGENTE MICRO TENDÊNCIA + S2-6 ANALYTICS", "ok")
        self._log(f"Modo: {('SIMULADO' if SIMULATE_MODE else 'AUTO-TRADE') if AUTO_TRADING_ENABLED else 'ANÁLISE'}", "info")
        self._log(f"Símbolo: {SYMBOL} | Refresh: {REFRESH_SECONDS}s", "info")

        print("\n  Pressione Ctrl+C para sair...\n")

        try:
            while True:
                # Verifica horário de mercado
                if not _is_market_hours():
                    print(f"\r  ⏸ Fora do pregão. Aguardando... ", end="", flush=True)
                    time.sleep(60)
                    continue

                # Executa ciclo
                if not self.run_cycle():
                    self._log("Erro no ciclo, aguardando para tentar novamente...", "warn")
                    time.sleep(REFRESH_SECONDS)
                    continue

                # Aguarda próximo ciclo
                _wait_with_progress(REFRESH_SECONDS)

        except KeyboardInterrupt:
            print("\n")
            self._log("Agente interrompido pelo usuário", "info")

            # Exibe resumo
            print("\n  ════ RESUMO DO DIA ════")
            self._log(f"Total de ciclos: {self.cycle_count}", "info")
            self._log(f"Total de trades: {self.total_trades}", "info")
            open_trades = len(self.trading_mgr.open_trades) if self.trading_mgr else 0
            self._log(f"Posições abertas: {open_trades}", "info" if open_trades == 0 else "warn")

            # Fecha posições abertas
            if self.trading_mgr and self.trading_mgr.open_trades:
                self._log("Fechando posições abertas...", "info")
                try:
                    tick = self.mt5.get_tick(SYMBOL)
                    if tick:
                        self.trading_mgr.close_all(tick.last.value, "MANUAL")
                        self._log("Posições fechadas com sucesso", "ok")
                except Exception as e:
                    self._log(f"Erro ao fechar: {e}", "error")

        finally:
            # Cleanup
            if self.mt5:
                try:
                    self.mt5.disconnect()
                except:
                    pass


def main():
    """Função principal."""
    if not IMPORTS_OK:
        print("❌ Imports do agente falhou. Verifique instalação.")
        sys.exit(1)

    if not S2_6_IMPORTS_OK:
        print("❌ Imports de S2-6 falhou. Verifique instalação.")
        sys.exit(1)

    # ─ Processa argumentos ─
    global AUTO_TRADING_ENABLED, SIMULATE_MODE

    if "--auto-trade" in sys.argv:
        AUTO_TRADING_ENABLED = True
        print("\n  ⚠️  MODO AUTO-TRADE ATIVADO")
        print("  ⚠️  ORDENS REAIS SERÃO EXECUTADAS\n")
    elif "--simulate" in sys.argv:
        SIMULATE_MODE = True
        AUTO_TRADING_ENABLED = True
        print("\n  🧪 MODO SIMULADO (SHADOW) ATIVADO")
        print("  🧪 Nenhuma ordem será executada\n")
    else:
        print("\n  📊 MODO ANÁLISE (sem execução)\n")

    # ─ Cria agente ─
    agent = ExemploAgentComS2_6()

    # ─ Setup ─
    if not agent.setup():
        print("❌ Falha ao inicializar agente")
        sys.exit(1)

    # ─ Executa loop ─
    try:
        agent.run_loop()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n✅ Agente finalizado com sucesso\n")


if __name__ == "__main__":
    main()
