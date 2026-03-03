#!/usr/bin/env python
"""
Script: analyze_historical_patterns.py

FASE 1 do Aprendizado: Análise de Padrões Históricos

Purpose: Estabelecer baseline e padrões antes de novas ordens automáticas chega 
com dados completos.

Usage: python analyze_historical_patterns.py
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from collections import defaultdict
import statistics

DB_PATH = Path("data/db/trading.db")


def analyze_historical_patterns() -> bool:
    """Analisa padrões em dados históricos."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        print("\n" + "=" * 100)
        print("📊 ANÁLISE DE PADRÕES HISTÓRICOS - BASELINE PARA APRENDIZADO")
        print("=" * 100)

        # 1. Estatísticas gerais
        print("\n" + "-" * 100)
        print("📈 ESTATÍSTICAS GERAIS")
        print("-" * 100)

        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as vitorias,
                SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as derrotas,
                ROUND(AVG(profit_loss), 2) as pnl_medio,
                ROUND(MAX(profit_loss), 2) as maior_ganho,
                ROUND(MIN(profit_loss), 2) as maior_perda
            FROM trades
            WHERE status = 'CLOSED'
        """)

        stats = cursor.fetchone()
        total, wins, losses, avg_pnl, max_win, max_loss = stats

        win_rate = (wins / total * 100) if total > 0 else 0

        print(f"\n📊 Trades Fechados")
        print(f"  Total: {total}")
        print(f"  Vitórias: {wins} ({win_rate:.1f}%)")
        print(f"  Derrotas: {losses}")
        print(f"  PnL Médio: {avg_pnl:+.2f}")
        print(f"  Maior Ganho: {max_win:+.2f}")
        print(f"  Maior Perda: {max_loss:+.2f}")
        print(f"  Razão Win/Loss: {max_win / abs(max_loss):.2f}")

        # 2. Análise por tipo de execução
        print("\n" + "-" * 100)
        print("🎯 ANÁLISE POR TIPO DE EXECUÇÃO")
        print("-" * 100)

        cursor.execute("""
            SELECT 
                execution_method,
                COUNT(*) as total,
                SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as vitorias,
                ROUND(AVG(profit_loss), 2) as pnl_medio
            FROM trades
            WHERE status = 'CLOSED'
            GROUP BY execution_method
        """)

        execution_types = cursor.fetchall()
        for exec_type, total, wins, avg in execution_types:
            wr = (wins / total * 100) if total > 0 else 0
            icon = "👤" if exec_type == "manual" else "🤖"
            print(f"\n{icon} {exec_type.upper()}")
            print(f"  Total: {total}")
            print(f"  Win Rate: {wr:.1f}%")
            print(f"  PnL Médio: {avg:+.2f}")

        # 3. Análise por direção (BUY vs SELL)
        print("\n" + "-" * 100)
        print("📍 ANÁLISE POR DIREÇÃO")
        print("-" * 100)

        cursor.execute("""
            SELECT 
                side,
                COUNT(*) as total,
                SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as vitorias,
                ROUND(AVG(profit_loss), 2) as pnl_medio
            FROM trades
            WHERE status = 'CLOSED'
            GROUP BY side
        """)

        directions = cursor.fetchall()
        for direction, total, wins, avg_pnl_dir in directions:
            wr = (wins / total * 100) if total > 0 else 0
            icon = "📈" if direction == "BUY" else "📉"
            print(f"\n{icon} {direction}")
            print(f"  Total: {total}")
            print(f"  Win Rate: {wr:.1f}%")
            print(f"  PnL Médio: {avg_pnl_dir:+.2f}")

        # 4. Análise por horário (early, mid, late)
        print("\n" + "-" * 100)
        print("⏰ ANÁLISE POR HORÁRIO")
        print("-" * 100)

        time_patterns = defaultdict(list)
        cursor.execute("""
            SELECT entry_time, profit_loss
            FROM trades
            WHERE status = 'CLOSED'
            AND entry_time IS NOT NULL
        """)

        for entry_time, pnl in cursor.fetchall():
            hour = datetime.fromisoformat(entry_time).hour
            
            if 9 <= hour < 11:
                period = "Abertura (09:00-11:00)"
            elif 11 <= hour < 14:
                period = "Meio (11:00-14:00)"
            elif 14 <= hour < 17:
                period = "Tarde (14:00-17:00)"
            else:
                period = "Outros"
            
            time_patterns[period].append(pnl)

        for period, pnls in sorted(time_patterns.items()):
            wins_period = sum(1 for p in pnls if p > 0)
            avg_period = sum(pnls) / len(pnls)
            wr_period = (wins_period / len(pnls)) * 100 if pnls else 0

            print(f"\n{period}")
            print(f"  Ordens: {len(pnls)}")
            print(f"  Win Rate: {wr_period:.1f}%")
            print(f"  PnL Médio: {avg_period:+.2f}")

        # 5. Insights e recomendações
        print("\n" + "=" * 100)
        print("💡 INSIGHTS PARA O MODELO ML")
        print("=" * 100)

        print("""
1. BASELINE ESTABELECIDO ✅
   - Você tem {total} trades históricos
   - Win rate atual: {wr:.1f}%
   - Use como referência para comparar com automático

2. DADOS READY PARA APRENDIZADO ✅
   - Entry, Exit, P&L: COMPLETOS
   - Execution Method: MARCADO (manual vs automático)
   - SL/TP: Será COMPLETO em novas ordens

3. PRÓXIMO PASSO: FASE 2
   - Execute INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
   - Novas ordens terão SL/TP validado
   - ML pode começar a aprender risk/reward real

4. TIMELINE
   - 27/02: Primeira ordem automática nova
   - 06/03: 10-20 ordens automáticas acumuladas
   - 13/03: Padrões claros emergem
   - 20/03: Modelo refina e melhora

5. MÉTRICAS A MONITORAR
   - Win rate manual vs automático
   - Sharpe ratio (quando temos SL/TP)
   - Drawdown máximo
   - Correlação horário vs successo
        """.format(
            total=total,
            wr=win_rate
        ))

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = analyze_historical_patterns()
    exit(0 if success else 1)
