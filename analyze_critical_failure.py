#!/usr/bin/env python3
"""Identifica falha crítica no processo de geração de ordens automáticas."""

import sqlite3
from datetime import datetime

DATABASE_PATH = "data/db/trading.db"

def analyze_critical_failure():
    """Analisa o problema crítico das ordens sem SL/TP."""

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        print("\n" + "="*100)
        print("🔴 ANÁLISE DE FALHA CRÍTICA - ORDENS SEM STOP LOSS E TAKE PROFIT")
        print("="*100 + "\n")

        # As 2 ordens problemáticas do INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat
        order_ids = ['2276191196', '2276191635']

        print("📍 ORDENS DO SISTEMA AUTOMÁTICO (INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat):")
        print("-" * 100)

        for order_id in order_ids:
            cursor.execute("""
                SELECT id, broker_trade_id, symbol, side, quantity, entry_price,
                       entry_time, exit_price, exit_time, stop_loss, take_profit,
                       status, profit_loss, created_at, updated_at, notes
                FROM trades
                WHERE broker_trade_id = ?
            """, (order_id,))

            record = cursor.fetchone()

            if record:
                (db_id, broker_id, symbol, side, qty, entry_price, entry_time,
                 exit_price, exit_time, sl, tp, status, pnl, created_at, updated_at, notes) = record

                print(f"\n🔴 ORDEM {order_id}:")
                print(f"  Símbolo: {symbol} | {side}")
                print(f"  Entrada: R$ {float(entry_price):,.2f} às {entry_time}")
                print(f"  Stop Loss: {float(sl):,.2f}" if sl else "  Stop Loss: ❌ NÃO REGISTRADO")
                print(f"  Take Profit: {float(tp):,.2f}" if tp else "  Take Profit: ❌ NÃO REGISTRADO")
                print(f"  Status: {status}")
                print(f"  Notas: {notes}")

        # Análise do fluxo
        print(f"\n\n{'='*100}")
        print("🔍 ANÁLISE DO FLUXO DE EXECUÇÃO")
        print(f"{'='*100}\n")

        print("1️⃣ ENTRADA NO SISTEMA AUTOMÁTICO:")
        print("   Arquivo: INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat")
        print("   Linha 125: python scripts/launch_agent_with_ml_v1_2_3.py !MODE!")
        print("   Função: _generate_opportunities() cria Opportunity com SL/TP")
        print("   → Na linha 2058-2066, Opportunity é criada COM stop_loss e take_profit")

        print("\n2️⃣ PASSAGEM PARA ORDEM:")
        print("   Arquivo: scripts/agente_micro_tendencia_winfut.py")
        print("   execute_entry() cria Order com:")
        print("   → stop_loss=Price(opp.stop_loss)")
        print("   → take_profit=Price(opp.take_profit)")
        print("   → Price(0) é tecnicamente válido em Python (não dispara erro)")

        print("\n3️⃣ ENVIO PARA MT5:")
        print("   Arquivo: src/infrastructure/adapters/mt5_adapter.py")
        print("   Linha 685-688:")
        print("   if order.stop_loss:")
        print("       request['sl'] = float(order.stop_loss.value)")
        print("   if order.take_profit:")
        print("       request['tp'] = float(order.take_profit.value)")

        print("\n\n🚨 CONCLUSÃO DO PROBLEMA:")
        print("-" * 100)
        print("""
❌ FALHA CRÍTICA IDENTIFICADA:

O código parece estar correto em teoria, MAS há uma desconeção entre:

1. GERAÇÃO DA OPPORTUNITY (_generate_opportunities @ linha 2058):
   - Cria Opportunity com stop_loss=sl e take_profit=tp ✅

2. PASSAGEM PARA ORDER (execute_entry @ linha 2670):
   - Tenta fazer: Order(..., stop_loss=Price(opp.stop_loss), take_profit=Price(opp.take_profit))
   - ❌ POSSÍVEL PROBLEMA: Se opp.stop_loss = 0 ou None → Price(0) ou erro

3. ENVIO PARA MT5 (send_order @ linha 685):
   - if order.stop_loss: → Verifica se Price object é truthy
   - ❌ POSSÍVEL PROBLEMA: Price(0) é um object válido → é truthy!
   - Mas float(Price(0).value) = 0.0 → MT5 recusa SL=0!

🎯 RAIZ PROVÁVEL:
   - As Opportunities ESTÃO sendo criadas com SL/TP corretos
   - MAS algo está zerando esses valores antes de enviar para MT5
   - OU o Price(0) está sendo enviado ao MT5 que o rejeita silenciosamente
""")

        return True

    except Exception as e:
        print(f"❌ Erro na análise: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    analyze_critical_failure()
