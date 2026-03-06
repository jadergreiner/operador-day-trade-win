#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exemplo de Integração - Inactivity Penalty Manager com Agente RL

Este script demonstra como integrar o InactivityPenaltyManager
no agente RL v5000 para implementar P0-URGENT-1.

Uso:
    python scripts/exemplo_integracao_inactivity_penalty.py

Saída esperada:
    - Confidence original vs ajustada com penalidade
    - Logs de penalidade quando minutes_inactive > 120
    - Estatísticas de inatividade da sessão
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# Setup paths
ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.application.services.inactivity_penalty_manager import (
    InactivityPenaltyManager,
    InactivityConfig,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)


def exemplo_integracao_basica():
    """Exemplo 1: Integração básica com sessão trading."""
    logger.info("=== EXEMPLO 1: Integração Básica ===\n")

    # Inicializar manager com config padrão (R$ 280/dia)
    manager = InactivityPenaltyManager()
    manager.start_session()

    logger.info("Sessão iniciada com operacional_cost_daily = R$ 280\n")

    # Simular decisões em diferentes períodos
    confidence_original = Decimal("0.75")

    # T+0 min: Sinal de BUY
    manager.record_signal_attempt("BUY")
    confidence_1, metrics_1 = manager.calculate_inactivity_metrics(
        confidence_original
    )
    logger.info(
        f"T+0min: Sinal BUY | Confidence: {confidence_1:.2%} | Penalty: {metrics_1.penalty_applied}"
    )

    # T+90 min: Inatividade 90 min (< threshold, sem penalidade)
    current_time = manager.last_signal_time + timedelta(minutes=90)
    confidence_2, metrics_2 = manager.calculate_inactivity_metrics(
        confidence_original, current_time
    )
    logger.info(
        f"T+90min: Inatividade {metrics_2.minutes_inactive}min (< 120) | Confidence: {confidence_2:.2%} | Penalty: {metrics_2.penalty_applied}"
    )

    # T+150 min: Inatividade 150 min (> threshold, COM penalidade!)
    current_time = manager.last_signal_time + timedelta(minutes=150)
    confidence_3, metrics_3 = manager.calculate_inactivity_metrics(
        confidence_original, current_time
    )
    logger.info(
        f"T+150min: Inatividade {metrics_3.minutes_inactive}min (> 120) | Confidence: {confidence_3:.2%} | Penalty: {metrics_3.penalty_applied:.4f}"
    )
    logger.info(f"  └─ Custo operacional acumulado: R${metrics_3.accumulated_cost:.2f}\n")

    # Novo sinal reseta timer
    manager.record_signal_attempt("SELL", current_time)
    current_time = current_time + timedelta(minutes=30)
    confidence_4, metrics_4 = manager.calculate_inactivity_metrics(
        confidence_original, current_time
    )
    logger.info(
        f"T+180min (após novo sinal): Inatividade resetou para {metrics_4.minutes_inactive}min | Confidence: {confidence_4:.2%}"
    )


def exemplo_integracao_agente_rl():
    """Exemplo 2: Integração com agente RL real."""
    logger.info("\n=== EXEMPLO 2: Integração com Agente RL ===\n")

    # Config customizada para operador específico
    config = InactivityConfig(
        operational_cost_daily=Decimal("280.00"),  # R$ 280/dia
        trading_minutes_per_day=390,  # 9:00 - 17:30
        inactivity_threshold_minutes=120,  # 2 horas
        max_penalty=Decimal("0.05"),  # -5% máximo
    )
    manager = InactivityPenaltyManager(config)

    # Simular pregão do dia 06/03/2026
    session_start = datetime(2026, 3, 6, 9, 0, 0)  # 09:00 BRT
    manager.start_session(session_start)
    logger.info(f"Sessão iniciada: {session_start.strftime('%d/%m/%Y %H:%M')}\n")

    # Fluxo realista de trading
    trades_log = []

    # 09:30 - Primeira entrada
    time_1 = session_start + timedelta(hours=0, minutes=30)
    manager.record_signal_attempt("BUY", time_1)
    conf_1, _ = manager.calculate_inactivity_metrics(
        Decimal("0.80"), time_1
    )
    trades_log.append((time_1, "BUY", conf_1))
    logger.info(f"09:30 | BUY  | Confidence: {conf_1:.2%}")

    # 10:30 - Inatividade 60 min (sem penalidade ainda)
    time_2 = session_start + timedelta(hours=1, minutes=30)
    conf_2, metrics_2 = manager.calculate_inactivity_metrics(
        Decimal("0.80"), time_2
    )
    trades_log.append((time_2, "HOLD", conf_2))
    logger.info(
        f"10:30 | HOLD | Inatividade: {metrics_2.minutes_inactive}min (< 120) | Confidence: {conf_2:.2%}"
    )

    # 12:00 - Inatividade 150 min (COM PENALIDADE!)
    time_3 = session_start + timedelta(hours=3)
    conf_3, metrics_3 = manager.calculate_inactivity_metrics(
        Decimal("0.80"), time_3
    )
    trades_log.append((time_3, "HOLD", conf_3))
    logger.info(
        f"12:00 | HOLD | Inatividade: {metrics_3.minutes_inactive}min (> 120) | Confidence: {conf_3:.2%} | Penalty: {metrics_3.penalty_applied:.4f}"
    )

    # 12:15 - Novo sinal SELL
    time_4 = session_start + timedelta(hours=3, minutes=15)
    manager.record_signal_attempt("SELL", time_4)
    conf_4, _ = manager.calculate_inactivity_metrics(
        Decimal("0.75"), time_4
    )
    trades_log.append((time_4, "SELL", conf_4))
    logger.info(f"12:15 | SELL | Confidence: {conf_4:.2%} | Timer resetou")

    # Stats finais
    logger.info("\n--- Resumo da Sessão ---")
    stats = manager.get_inactivity_stats()
    logger.info(f"Duração total: {stats['session_duration_minutes']}min")
    logger.info(f"Minutos inativos acumulados: {stats['minutes_inactive']}min")
    logger.info(f"Custo operacional: R${stats['total_cost_accumulated']:.2f}")


def exemplo_decisao_com_penalidade():
    """Exemplo 3: Lógica de decisão integrando penalidade."""
    logger.info("\n=== EXEMPLO 3: Lógica de Decisão com Penalidade ===\n")

    manager = InactivityPenaltyManager()
    manager.start_session()

    def fazer_decisao_trading(confidence_original: Decimal, current_time: datetime) -> str:
        """Função de decisão que integra penalidade de inatividade.

        Pipeline:
        1. Obter confidence do modelo
        2. Aplicar penalidade por inatividade
        3. Comparar com threshold
        4. Tomar decisão (EXECUTE / HOLD / REJECT)
        """
        # AC 3: Aplicar penalidade por inatividade
        confidence_adjusted, metrics = manager.calculate_inactivity_metrics(
            confidence_original, current_time
        )

        # AC 4: Log informativo
        if metrics.penalty_applied < Decimal("0.0"):
            logger.warning(
                f"Penalidade aplicada: {metrics.penalty_applied:.4f} | "
                f"Inatividade: {metrics.minutes_inactive}min"
            )

        # Threshold para entrada (padrão 0.65, relaxado se forced activation)
        threshold = Decimal("0.65")

        if confidence_adjusted >= threshold:
            decision = "EXECUTE"
        elif confidence_adjusted >= Decimal("0.50"):
            decision = "HOLD"
        else:
            decision = "REJECT"

        return decision, confidence_adjusted, metrics

    # Simular diferentes cenários
    current_time = manager.last_signal_time

    logger.info("Cenário 1: Confidence alta, sem inatividade")
    decision, conf_adj, metrics = fazer_decisao_trading(
        Decimal("0.85"), current_time
    )
    logger.info(f"  → Decisão: {decision} (confidence ajustada: {conf_adj:.2%})\n")

    logger.info("Cenário 2: Inatividade 200min (penalidade -0.02)")
    current_time = manager.last_signal_time + timedelta(minutes=200)
    decision, conf_adj, metrics = fazer_decisao_trading(
        Decimal("0.70"), current_time
    )
    logger.info(f"  → Decisão: {decision} (confidence ajustada: {conf_adj:.2%}, penalty: {metrics.penalty_applied:.4f})\n")

    logger.info("Cenário 3: Confidence baixa + inatividade grande")
    manager.last_signal_time = datetime.now() - timedelta(minutes=300)
    current_time = manager.last_signal_time + timedelta(minutes=300)
    decision, conf_adj, metrics = fazer_decisao_trading(
        Decimal("0.45"), current_time
    )
    logger.info(f"  → Decisão: {decision} (confidence ajustada: {conf_adj:.2%}, penalty: {metrics.penalty_applied:.4f})\n")


def exemplo_backtest_analysis():
    """Exemplo 4: Análise para backtest (AC 5)."""
    logger.info("\n=== EXEMPLO 4: Análise para Backtest (AC 5) ===\n")

    manager = InactivityPenaltyManager()
    session_start = datetime(2026, 3, 6, 9, 0, 0)
    manager.start_session(session_start)

    # Simular dia de trading
    barra_count = 0
    signal_attempts = 0

    for hours in range(9, 18):  # 9:00 até 17:00
        for minutes in range(0, 60, 30):  # A cada 30 min
            current_time = session_start + timedelta(hours=hours - 9, minutes=minutes)
            barra_count += 1

            # Simular que 40% das barras tentam entrada
            if barra_count % 5 == 0:  # A cada 5 barras
                manager.record_signal_attempt("BUY")
                signal_attempts += 1

            # Calcular penalty para backest analysis
            _, metrics = manager.calculate_inactivity_metrics(
                Decimal("0.70"), current_time
            )

    stats = manager.get_inactivity_stats()

    logger.info(f"Total barras processadas: {barra_count}")
    logger.info(f"Tentativas de sinal: {signal_attempts}")
    logger.info(f"% tentativas de entrada: {100 * signal_attempts / barra_count:.1f}%")
    logger.info(f"\nCusto operacional diário: R$ {float(manager.config.operational_cost_daily):.2f}")
    logger.info(f"Minutos inativos: {stats['minutes_inactive']}")
    logger.info(f"Custo acumulado inatividade: R${stats['total_cost_accumulated']:.2f}")
    logger.info(f"\nConclussão: A penalidade de inatividade FORÇA modelo a tentar entradas")
    logger.info(f"            evitando acumular custo operacional sem trades.")


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("EXEMPLOS DE INTEGRAÇÃO - INACTIVITY PENALTY MANAGER (P0-URGENT-1)")
    logger.info("=" * 80)

    exemplo_integracao_basica()
    exemplo_integracao_agente_rl()
    exemplo_decisao_com_penalidade()
    exemplo_backtest_analysis()

    logger.info("\n" + "=" * 80)
    logger.info("✅ TODOS OS EXEMPLOS EXECUTADOS COM SUCESSO")
    logger.info("=" * 80)
