#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exemplo de Integração S2-6 Analytics no Operador Auto-Trade

Mostra como registrar trades/intervenções e resultados no Analytics.
Sincroniza em tempo real com Monitor de Operação.
"""

from src.adapters.s2_6_analytics_adapter import (
    get_analytics_adapter,
    TradeEvent
)
import logging

logger = logging.getLogger(__name__)


class OperadorComAnalytics:
    """
    Wrapper do operador que integra S2-6 Analytics.

    Cada decisão de trade é registrada:
    1. No início: log_intervention (EXECUTE/OVERRIDE/PAUSE/CANCEL)
    2. No encerramento: update_result (WIN/LOSS/PARTIAL + P&L)
    """

    def __init__(self, api_url: str = "http://localhost:8000"):
        self.analytics = get_analytics_adapter(api_url)
        self.active_trades: dict = {}  # {trade_id: intervention_id}

    def on_trade_executed(
        self,
        symbol: str,
        action: str,  # EXECUTE, OVERRIDE, PAUSE, CANCEL
        decision: str,  # Descrição da decisão (ex: "aumentar_ticket_25pct")
        entry_price: float,
        p_and_l_inicial: float = 0.0
    ) -> int:
        """
        Registra trade executado no Analytics.

        Chamado no momento que a ordem é enviada.

        Args:
            symbol: Símbolo operado (WINFUT, etc)
            action: Ação tomada (EXECUTE/OVERRIDE/PAUSE/CANCEL)
            decision: Descrição da decisão tomada
            entry_price: Preço de entrada
            p_and_l_inicial: P&L no momento da execução

        Returns:
            intervention_id para update posterior
        """
        event = TradeEvent(
            symbol=symbol,
            action=action,
            trader_decision=f"{decision} | entry={entry_price:.2f}",
            p_and_l=p_and_l_inicial,
        )

        intervention_id = self.analytics.log_intervention(event)

        if intervention_id:
            self.active_trades[f"{symbol}_{entry_price}"] = intervention_id

        return intervention_id or 0

    def on_trade_closed(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        p_and_l_final: float,
        reason: str  # "tp_hit", "sl_hit", "manual_close", etc
    ) -> bool:
        """
        Registra fechamento de trade no Analytics.

        Chamado quando a próxima oportunidade é identificada ou posição fechada.

        Args:
            symbol: Símbolo operado
            entry_price: Preço de entrada
            exit_price: Preço de saída
            p_and_l_final: P&L final da operação
            reason: Motivo do fechamento

        Returns:
            True se sucesso, False se erro
        """
        trade_key = f"{symbol}_{entry_price}"
        intervention_id = self.active_trades.get(trade_key)

        if not intervention_id:
            logger.warning(f"[operador] Nenhum intervention_id encontrado para {trade_key}")
            return False

        # Determinar resultado
        if p_and_l_final > 10:  # Threshold mínimo para WIN
            result = "WIN"
        elif p_and_l_final < -10:
            result = "LOSS"
        else:
            result = "PARTIAL"

        success = self.analytics.update_result(
            intervention_id,
            result,
            p_and_l_final
        )

        if success:
            del self.active_trades[trade_key]

        return success

    def on_manual_override(
        self,
        symbol: str,
        override_action: str,  # "aumentar_ticket", "fechar_manual", etc
        new_pnl: float
    ) -> int:
        """
        Registra intervenção manual do trader.

        Args:
            symbol: Símbolo operado
            override_action: Descrição da ação manual
            new_pnl: P&L após ação

        Returns:
            intervention_id
        """
        event = TradeEvent(
            symbol=symbol,
            action="OVERRIDE",
            trader_decision=override_action,
            p_and_l=new_pnl,
        )

        return self.analytics.log_intervention(event) or 0

    def print_stats(self):
        """Imprime estatísticas de intervencoes no terminal"""
        stats = self.analytics.get_stats()

        if stats:
            print("\n" + "=" * 80)
            print("[S2-6 ANALYTICS] Estatísticas de Intervenção Manual")
            print("=" * 80)
            print(f"Total de intervenções: {stats.get('total_interventions', 0)}")
            print(f"  - Wins: {stats.get('wins', 0)}")
            print(f"  - Losses: {stats.get('losses', 0)}")
            print(f"  - Parciais: {stats.get('partials', 0)}")
            print(f"Win Rate: {stats.get('win_rate', 0):.1%}")
            print(f"P&L Total: {stats.get('total_pnl', 0):.2f}")
            print("=" * 80 + "\n")
        else:
            logger.warning("[S2-6] Não conseguiu obter stats")


# Exemplo de uso no loop principal do operador:
"""
def main_operador_loop():
    # Inicializar operador com Analytics
    operador = OperadorComAnalytics(api_url="http://localhost:8000")

    while True:
        # ... lógica de mercado, SMC, BDI, etc ...

        # Ao executar um trade:
        if oportunidade_detectada:
            intervention_id = operador.on_trade_executed(
                symbol="WINFUT",
                action="EXECUTE",
                decision="confluencia_smc_bdi_m1",
                entry_price=127450.50,
                p_and_l_inicial=0.0
            )

        # Ao fechar um trade:
        if trade_fechado:
            operador.on_trade_closed(
                symbol="WINFUT",
                entry_price=127450.50,
                exit_price=127500.00,
                p_and_l_final=250.50,
                reason="tp_hit"
            )

        # Ao fazer override manual:
        if trader_override:
            operador.on_manual_override(
                symbol="WINFUT",
                override_action="aumentar_ticket_25pct",
                new_pnl=350.00
            )

        # Imprimir stats periodicamente
        if hora_de_imprimir_stats:
            operador.print_stats()
"""
