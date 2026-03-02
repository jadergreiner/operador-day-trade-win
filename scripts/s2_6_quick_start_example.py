#!/usr/bin/env python
"""
S2-6 Quick Start Example

Como usar o modulo S2-6: Analytics de Intervencao Manual

Demonstra:
- Criar um sinal
- Registrar no dashboard
- Trader aprova
- Execute sinal
- Fechar posicao
- Ver metricas
"""

import asyncio
from datetime import datetime

from agente_micro_tendencia_winfut.s2_6_analytics import (
    AnalyticsDashboard,
    AnalyticsConfig,
)
from agente_micro_tendencia_winfut.s2_6_analytics.models import (
    Signal,
    InterventionType,
)


async def main():
    """Main example flow"""

    print("\n" + "="*80)
    print("S2-6: ANALYTICS - QUICK START EXAMPLE")
    print("="*80 + "\n")

    # Step 1: Initialize
    print("[STEP 1] Inicializar dashboard...")
    config = AnalyticsConfig()
    dashboard = AnalyticsDashboard(config)
    print(f"  ✅ Dashboard inicializado")
    print(f"  Logs em: {config.log_dir}\n")

    # Step 2: Create signal (from S2-3 + S2-5)
    print("[STEP 2] Criar sinal (S2-3 SMC + S2-5 T+60)...")
    signal = Signal(
        signal_id="s2_6_example_001",
        timestamp=datetime.now(),
        timeframe="M1",
        direction="BULLISH",
        confidence_score=0.82,      # S2-5 T+60 probability
        smc_confluence_score=4.2,   # S2-3 SMC confluence
        entry_price=130000.0,
        stop_loss=129700.0,  # -300 points
        take_profit=130600.0,  # +600 points
        reward_risk_ratio=2.0,
        metadata={
            "source_s2_3": "SMC confluencia alta (M1+M5)",
            "source_s2_5": "T+60 probabilidade 82%",
        }
    )
    print(f"  ✅ Sinal criado: {signal.signal_id}")
    print(f"     Direction: {signal.direction}")
    print(f"     Confidence (S2-5): {signal.confidence_score}")
    print(f"     Confluence (S2-3): {signal.smc_confluence_score}/5\n")

    # Step 3: Register signal on dashboard
    print("[STEP 3] Registrar sinal no dashboard...")
    dashboard.register_signal(signal)
    print(f"  ✅ Sinal registrado")
    print(f"     Status: {signal.status.value}")
    print(f"     Awaiting trader approval...\n")

    # Step 4: Get dashboard data
    print("[STEP 4] Obter dados do dashboard...")
    data = dashboard.get_dashboard_data()
    print(f"  ✅ Dashboard data retrieved")
    print(f"     Pending signals: {data['signals']['pending']}")
    print(f"     Open positions: {data['signals']['open_positions']}")
    print(f"     Connected traders: {data['connectivity']['connected_traders']}\n")

    # Step 5: Trader connects and approves
    print("[STEP 5] Trader conecta e aprova sinal...")
    dashboard.feedback_api.register_trader("trader_001")
    await dashboard.feedback_api.approve_signal(signal.signal_id, "trader_001")
    print(f"  ✅ Sinal aprovado por trader_001\n")

    # Step 6: Execute signal
    print("[STEP 6] Executar sinal (Orders Executor)...")
    dashboard.execute_signal(signal.signal_id, execution_price=130020.0)
    print(f"  ✅ Sinal executado!")
    print(f"     Entry price: {signal.entry_price}")
    print(f"     Execution price: {signal.execution_price}")
    print(f"     Slippage: {signal.execution_price - signal.entry_price} points\n")

    # Step 7: Trader gives feedback
    print("[STEP 7] Trader submete feedback...")
    feedback = await dashboard.feedback_api.submit_feedback(
        signal_id=signal.signal_id,
        trader_id="trader_001",
        feedback_type="signal_quality",
        rating=5,
        comment="Excelente confluencia! Entrada muito precisa.",
        suggestions={"next_signal": "Look for sustained confluence confirmation"},
    )
    print(f"  ✅ Feedback registrado: Rating {feedback.rating}/5\n")

    # Step 8: Close position at take profit
    print("[STEP 8] Fechar posicao (TP atingido)...")
    dashboard.close_position(signal.signal_id, close_price=130600.0)
    position = dashboard.signal_history[signal.signal_id]
    print(f"  ✅ Posicao fechada!")
    print(f"     Close price: {position.pnl_percentage:.1f}%")
    print(f"     P&L points: {position.pnl_points:+.0f}")
    print(f"     P&L percentage: {position.pnl_percentage:+.2f}%\n")

    # Step 9: Manual override (simulated)
    print("[STEP 9] Simular intervencao manual...")
    override = dashboard.override_logger.log_override(
        override_id="override_001",
        trader_id="trader_001",
        intervention_type=InterventionType.SIGNAL_APPROVAL,
        reason="Manual approval - market conditions favorable, high confidence",
        signal_id=signal.signal_id,
    )
    print(f"  ✅ Intervencao registrada com auditoria\n")

    # Step 10: Performance report
    print("[STEP 10] Gerar relatorio de performance...")
    report = dashboard.get_performance_report(days=1)
    print(f"  ✅ Performance Report (dia 27/02):")
    print(f"     Total signals: {report.total_signals}")
    print(f"     Winning trades: {report.winning_trades}")
    print(f"     Losing trades: {report.losing_trades}")
    print(f"     Win rate: {report.win_rate*100:.1f}%")
    print(f"     Total P&L points: {report.total_pnl_points:+.0f}")
    print(f"     Avg profit/trade: {report.avg_profit_per_trade:+.0f}")
    if report.profit_factor > 0:
        print(f"     Profit factor: {report.profit_factor:.2f}x\n")
    else:
        print(f"     Profit factor: N/A (no losing trades)\n")

    # Step 11: Final dashboard view
    print("[STEP 11] Dashboard final view...")
    final_data = dashboard.get_dashboard_data()
    print(f"  ✅ Current Dashboard Status:")
    print(f"     Pending signals: {final_data['signals']['pending']}")
    print(f"     Open positions: {final_data['signals']['open_positions']}")
    print(f"     Performance (today):")
    print(f"       - Total executed: {final_data['performance']['executed_signals']}")
    print(f"       - Win rate: {final_data['performance']['win_rate_pct']:.1f}%")
    print(f"       - Total P&L: {final_data['performance']['total_pnl_points']:+.0f} points")
    print(f"     Risk metrics:")
    print(f"       - Open positions: {final_data['risk']['open_positions_count']}")
    print(f"       - Max drawdown: {final_data['risk']['max_drawdown_pct']:.1f}%\n")

    # Step 12: Override statistics
    print("[STEP 12] Override statistics...")
    override_stats = dashboard.override_logger.get_override_statistics(
        trader_id="trader_001"
    )
    print(f"  ✅ Override Statistics for trader_001:")
    print(f"     Total overrides: {override_stats['total_overrides']}")
    print(f"     By type: {override_stats.get('by_type', {})}\n")

    print("="*80)
    print("✅ S2-6 QUICK START - EXEMPLO COMPLETO")
    print("="*80 + "\n")

    print("📚 Next Steps:")
    print("  1. Integrate S2-3 (SMC) sinal generation")
    print("  2. Integrate S2-5 (T+60) confidence scoring")
    print("  3. Build WebSocket trader feedback UI")
    print("  4. Create real-time dashboard view")
    print("  5. Add performance metrics export\n")


if __name__ == "__main__":
    asyncio.run(main())
