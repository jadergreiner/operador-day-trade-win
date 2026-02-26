#!/usr/bin/env python3
"""Analisa a origem das ordens - se foram geradas pelo operador ou por sistema automático."""

import sqlite3
from datetime import datetime

DATABASE_PATH = "data/db/trading.db"

def analyze_order_origin():
    """Analisa a origem e características das ordens."""

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        print("\n" + "="*100)
        print("🔍 ANÁLISE DE ORIGEM DAS ORDENS - OPERADOR vs SISTEMA")
        print("="*100 + "\n")

        # As 3 ordens que precisamos analisar
        order_ids = ['2276170194', '2276191196', '2276191635']

        for order_id in order_ids:
            cursor.execute("""
                SELECT id, trade_id, broker_trade_id, symbol, side, quantity,
                       entry_price, entry_time, exit_price, exit_time,
                       stop_loss, take_profit, notes, status, profit_loss,
                       created_at, updated_at
                FROM trades
                WHERE broker_trade_id = ?
            """, (order_id,))

            record = cursor.fetchone()

            if record:
                (db_id, trade_id, broker_id, symbol, side, qty, entry_price,
                 entry_time, exit_price, exit_time, sl, tp, notes, status, pnl,
                 created_at, updated_at) = record

                print(f"{'='*100}")
                print(f"📋 ORDEM: {order_id}")
                print(f"{'='*100}\n")

                print(f"ℹ️ INFORMAÇÕES DA ORDEM:")
                print(f"  Símbolo: {symbol}")
                print(f"  Tipo: {side}")
                print(f"  Volume: {qty}")
                print(f"  Preço Entrada: R$ {float(entry_price):,.2f}")

                if entry_time:
                    print(f"  Hora de Abertura: {entry_time}")

                if exit_time:
                    print(f"  Hora de Fechamento: {exit_time}")

                if sl:
                    print(f"  Stop Loss: R$ {float(sl):,.2f}")

                if tp:
                    print(f"  Take Profit: R$ {float(tp):,.2f}")

                print(f"  P&L: R$ {float(pnl):+,.2f}" if pnl else "  P&L: N/A")

                print(f"\n📅 TIMESTAMPS DO BANCO DE DADOS:")
                print(f"  Criado em: {created_at}")
                print(f"  Atualizado em: {updated_at}")

                print(f"\n📝 NOTAS/COMENTÁRIOS:")
                if notes:
                    print(f"  {notes}")
                else:
                    print(f"  (Nenhuma nota registrada)")

                # Análise de origem
                print(f"\n🔎 ANÁLISE DE ORIGEM:")
                print(f"  {'-'*96}")

                # Indicadores de operador manual
                manual_indicators = []

                # 1. Presença de Stop Loss e Take Profit específicos = manual
                if sl and tp:
                    manual_indicators.append("✓ Tem Stop Loss e Take Profit definidos")
                else:
                    manual_indicators.append("✗ Sem Stop Loss/Take Profit")

                # 2. Hora de entrada compatível com horário de operador (não madrugada)
                if entry_time:
                    try:
                        entry_dt = datetime.fromisoformat(entry_time)
                        hour = entry_dt.hour

                        if 8 <= hour <= 18:
                            manual_indicators.append("✓ Horário de entrada durante expediente (08:00-18:00)")
                        else:
                            manual_indicators.append("✗ Horário fora de expediente normal")
                    except:
                        pass

                # 3. Notas descritivas = manual
                if notes and len(notes) > 10:
                    manual_indicators.append("✓ Contém notas descritivas detalhadas")
                else:
                    manual_indicators.append("✗ Sem notas descritivas")

                # 4. Trade ID UUID vs número sequencial
                if trade_id and "-" in trade_id:
                    manual_indicators.append("✓ Trade ID em formato UUID (padrão do sistema)")

                # 5. Queda automática pelo Take Profit
                if exit_time and tp and exit_price:
                    try:
                        # Verifica se saiu pelo TP
                        exit_price_val = float(exit_price)
                        tp_val = float(tp)

                        if abs(exit_price_val - tp_val) < 1:
                            manual_indicators.append("✓ Fechado pelo Take Profit automático")
                        else:
                            manual_indicators.append("✗ Não fechado pelo TP")
                    except:
                        pass

                for indicator in manual_indicators:
                    print(f"  {indicator}")

                # Conclusão sobre a origem
                print(f"\n🎯 CONCLUSÃO SOBRE A ORIGEM:")
                print(f"  {'-'*96}")

                # Classificação
                has_sl_tp = bool(sl and tp)
                has_notes = bool(notes and len(notes) > 10)
                is_business_hours = False

                if entry_time:
                    try:
                        entry_dt = datetime.fromisoformat(entry_time)
                        hour = entry_dt.hour
                        is_business_hours = 8 <= hour <= 18
                    except:
                        pass

                # Scoring
                score = 0
                score += 3 if has_sl_tp else 0
                score += 2 if is_business_hours else 0
                score += 2 if has_notes else 0

                if score >= 5:
                    print(f"  ✅ OPERADOR MANUAL")
                    print(f"     Evidências:")
                    print(f"     - Stop Loss e Take Profit definidos manualmente")
                    print(f"     - Entrada durante horário de expediente")
                    print(f"     - Características consistentes com decisão humana")

                elif score >= 2:
                    print(f"  ⚠️ PROVÁVEL OPERADOR (COM ASSISTÊNCIA DE SISTEMA)")
                    print(f"     Evidências mistas de operação manual e automática")

                else:
                    print(f"  🤖 PROVÁVEL SISTEMA AUTOMÁTICO")
                    print(f"     Sem indicadores suficientes de operação manual")

                print()

            else:
                print(f"❌ Ordem {order_id} não encontrada no banco de dados\n")

        # Análise geral do padrão
        print(f"\n{'='*100}")
        print("📊 ANÁLISE GERAL DO PADRÃO DE OPERAÇÕES")
        print(f"{'='*100}\n")

        cursor.execute("""
            SELECT COUNT(*),
                   AVG(CASE WHEN stop_loss IS NOT NULL THEN 1.0 ELSE 0 END) as pct_with_sl,
                   AVG(CASE WHEN take_profit IS NOT NULL THEN 1.0 ELSE 0 END) as pct_with_tp,
                   AVG(CASE WHEN notes IS NOT NULL AND length(notes) > 10 THEN 1.0 ELSE 0 END) as pct_with_notes
            FROM trades
            WHERE symbol IN ('WINFUT', 'WINJ26')
            AND date(created_at) = '2026-02-26'
        """)

        result = cursor.fetchone()
        if result:
            total, pct_sl, pct_tp, pct_notes = result

            print(f"Total de Operações (26/02): {total}")
            print(f"Com Stop Loss: {pct_sl*100:.0f}%")
            print(f"Com Take Profit: {pct_tp*100:.0f}%")
            print(f"Com Notas: {pct_notes*100:.0f}%")

            if pct_sl and pct_sl > 0.66:
                print(f"\n✅ Padrão sugere OPERAÇÃO MANUAL")
                print(f"   A maioria das ordens tem Stop Loss e Take Profit definidos")
            else:
                print(f"\n⚠️ Padrão misto")

        print(f"\n{'='*100}\n")

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
    print("\n🔍 Analisando origem das ordens...\n")
    analyze_order_origin()
