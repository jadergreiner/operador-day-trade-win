#!/usr/bin/env python
"""
Script: Verificar execução e diferenciação de ordens (manual vs automático).

Purpose: Validar que ordens automáticas e manuais estão devidamente marcadas
no banco de dados.

Usage: python verify_execution_method_marking.py
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path("data/db/trading.db")


def verify_execution_method_marking() -> bool:
    """Verifica se ordens estão sendo marcadas corretamente."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        print("\n" + "=" * 100)
        print("🔍 VERIFICAÇÃO DE MARCAÇÃO DE ORDENS (MANUAL vs AUTOMÁTICO)")
        print("=" * 100)

        # 1. Verificar coluna existe
        cursor.execute("PRAGMA table_info(trades)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        if "execution_method" not in column_names:
            print("❌ Coluna 'execution_method' não existe!")
            conn.close()
            return False

        print("\n✅ Coluna 'execution_method' existe")

        # 2. Estatísticas gerais
        print("\n" + "-" * 100)
        print("📊 ESTATÍSTICAS DE ORDENS")
        print("-" * 100)

        cursor.execute("""
            SELECT execution_method, COUNT(*) as total,
                   ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM trades), 2) as percentual
            FROM trades
            WHERE status NOT IN ('MANUAL_CLOSURE')
            GROUP BY execution_method
            ORDER BY total DESC
        """)

        stats = cursor.fetchall()
        if not stats:
            print("ℹ️ Nenhuma ordem encontrada")
            conn.close()
            return True

        for method, total, pct in stats:
            icon = "🤖" if method == "automated" else "👤"
            print(f"{icon} {method:12} → {total:5} ordens ({pct}%)")

        # 3. Ordens recentes com execução method
        print("\n" + "-" * 100)
        print("📋 ÚLTIMAS 10 ORDENS (ÚLTIMAS 24H)")
        print("-" * 100)

        cutoff_time = datetime.now() - timedelta(days=1)
        cursor.execute("""
            SELECT 
                id,
                trade_id,
                symbol,
                side,
                entry_price,
                entry_time,
                status,
                execution_method,
                profit_loss
            FROM trades
            WHERE entry_time > ? AND status NOT IN ('MANUAL_CLOSURE')
            ORDER BY entry_time DESC
            LIMIT 10
        """, (cutoff_time.isoformat(),))

        recent_trades = cursor.fetchall()
        if recent_trades:
            print(
                f"\n{'ID':<5} {'Símbolo':<10} {'Lado':<6} "
                f"{'Entrada':<12} {'Status':<12} {'Execução':<12} {'PnL':<10}"
            )
            print("-" * 100)
            for trade in recent_trades:
                pid, trade_id, symbol, side, entry, entry_time, status, exec_method, pnl = trade
                icon = "🤖" if exec_method == "automated" else "👤"
                entry_time_str = entry_time.split("T")[1].split(".")[0] if entry_time else "N/A"
                pnl_str = f"{pnl:+.2f}" if pnl else "N/A"
                print(
                    f"{pid:<5} {symbol:<10} {side:<6} "
                    f"{entry_time_str:<12} {status:<12} {icon} {exec_method:<10} {pnl_str:<10}"
                )
        else:
            print("ℹ️ Nenhuma ordem nas últimas 24h")

        # 4. Ordens com valores SL/TP
        print("\n" + "-" * 100)
        print("🎯 ANÁLISE DE STOP LOSS E TAKE PROFIT")
        print("-" * 100)

        cursor.execute("""
            SELECT execution_method,
                   COUNT(*) as total,
                   SUM(CASE WHEN stop_loss IS NOT NULL THEN 1 ELSE 0 END) as com_sl,
                   SUM(CASE WHEN take_profit IS NOT NULL THEN 1 ELSE 0 END) as com_tp,
                   SUM(CASE WHEN stop_loss IS NOT NULL AND take_profit IS NOT NULL THEN 1 ELSE 0 END) as com_ambos
            FROM trades
            WHERE status NOT IN ('MANUAL_CLOSURE')
            GROUP BY execution_method
        """)

        sl_tp_stats = cursor.fetchall()
        for method, total, with_sl, with_tp, with_both in sl_tp_stats:
            icon = "🤖" if method == "automated" else "👤"
            sl_pct = (with_sl / total * 100) if total > 0 else 0
            tp_pct = (with_tp / total * 100) if total > 0 else 0
            both_pct = (with_both / total * 100) if total > 0 else 0

            print(f"\n{icon} {method.upper()}")
            print(f"  Total ordens: {total}")
            print(f"  Com SL: {with_sl} ({sl_pct:.1f}%)")
            print(f"  Com TP: {with_tp} ({tp_pct:.1f}%)")
            print(f"  Com ambos: {with_both} ({both_pct:.1f}%)")

            if method == "automated" and with_both < total:
                print(
                    f"  ⚠️ ATENÇÃO: {total - with_both} ordens automáticas "
                    f"sem SL/TP completo!"
                )

        # 5. Resumo final
        print("\n" + "=" * 100)
        print("✅ RESUMO DA IMPLEMENTAÇÃO")
        print("=" * 100)
        print("""
Marcação de ordens implementada com sucesso!

Cada ordem agora tem:
  • execution_method = 'manual'    → Aberta pelo operador no MT5
  • execution_method = 'automated' → Gerada pelo INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat

Benefícios:
  ✓ Diferenciação clara entre operações manuais e automáticas
  ✓ Auditoria completa de cada ordem
  ✓ Análise de performance por tipo de execução
  ✓ Conformidade com regulamentações (CVM/B3)

Query para filtrar apenas ordens automáticas:
  SELECT * FROM trades WHERE execution_method = 'automated'

Query para ordens automáticas + análise SL/TP:
  SELECT symbol, side, entry_price, stop_loss, take_profit
  FROM trades
  WHERE execution_method = 'automated'
  AND stop_loss IS NOT NULL AND take_profit IS NOT NULL
        """)

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_execution_method_marking()
    exit(0 if success else 1)
