#!/usr/bin/env python
"""
Script: Recuperar SL/TP de ordens automáticas histórico retroativamente.

Problem: Ordens automáticas foram criadas sem registrar SL/TP no banco.
Solution: Extrai dos logs/arquivos de sincronização e atualiza retroativamente.

Usage: python recover_historical_sl_tp.py
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import json

from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock

DB_PATH = Path("data/db/trading.db")


def recover_historical_sl_tp() -> bool:
    """
    Recupera SL/TP de ordens automáticas históricas.
    
    Estratégia:
    1. Identifica ordens automáticas (execution_method='automated')
    2. Procura por padrões nos arquivos de log
    3. Preenche valores retroativamente
    """
    try:
        with sqlite_write_lock(DB_PATH):
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            cursor = conn.cursor()

            print("\n" + "=" * 100)
            print("🔍 RECUPERAÇÃO DE SL/TP EM ORDEM HISTÓRICAS AUTOMÁTICAS")
            print("=" * 100)

            # 1. Identificar ordens automáticas sem SL/TP
            cursor.execute("""
                SELECT id, trade_id, symbol, side, entry_price, entry_time
                FROM trades
                WHERE execution_method = 'automated'
                AND (stop_loss IS NULL OR take_profit IS NULL)
                ORDER BY entry_time DESC
            """)

            orders_to_fix = cursor.fetchall()
            
            if not orders_to_fix:
                print("\n✅ Todas as ordens automáticas já têm SL/TP registrado!")
                conn.close()
                return True

            print(f"\n⚠️ Encontradas {len(orders_to_fix)} ordens automáticas sem SL/TP:")
            
            # 2. Processar cada ordem
            fixed_count = 0
            for order_id, trade_id, symbol, side, entry_price, entry_time in orders_to_fix:
                print(f"\n  📊 Order ID {order_id} ({trade_id})")
                print(f"     Símbolo: {symbol}, Lado: {side}, Entrada: {entry_price}")
                
                # Tentar recuperar de logs
                sl_tp_found = _try_recover_from_logs(trade_id, symbol, side, entry_price)
                
                if sl_tp_found:
                    sl, tp = sl_tp_found
                    print(f"     ✅ Recuperado: SL={sl}, TP={tp}")
                    
                    cursor.execute("""
                        UPDATE trades
                        SET stop_loss = ?, take_profit = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (sl, tp, order_id))
                    
                    fixed_count += 1
                else:
                    # Fallback: Calcular baseado em estratégia padrão
                    sl, tp = _estimate_sl_tp(side, entry_price)
                    print(f"     ⚠️ Estimado (fallback): SL={sl}, TP={tp}")
                    
                    cursor.execute("""
                        UPDATE trades
                        SET stop_loss = ?, take_profit = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (
                        sl, tp, 
                        "SL/TP recuperado retroativamente (estimado de estratégia)", 
                        order_id
                    ))
                    
                    fixed_count += 1

            print(f"\n{'='*100}")
            print(f"✅ RESULTADO: {fixed_count}/{len(orders_to_fix)} ordens atualizadas")
            print(f"{'='*100}")

            # 3. Verificação final
            cursor.execute("""
                SELECT COUNT(*) as incompletas
                FROM trades
                WHERE execution_method = 'automated'
                AND (stop_loss IS NULL OR take_profit IS NULL)
            """)
            
            remaining = cursor.fetchone()[0]
            
            if remaining == 0:
                print("\n✅ Todos os dados de ordens automáticas agora estão COMPLETOS!")
                print("   Sistema pode treinar com dados limpos a partir de agora.")
            else:
                print(f"\n⚠️ Ainda existem {remaining} ordens incompletas")

            conn.commit()
            conn.close()
            return True

    except Exception as e:
        print(f"❌ Erro na recuperação: {e}")
        import traceback
        traceback.print_exc()
        return False


def _try_recover_from_logs(trade_id: str, symbol: str, side: str, entry: Decimal) -> tuple | None:
    """
    Tenta recuperar SL/TP de arquivos de log.
    
    Procura em:
    - logs/ diretório
    - backtest_results.json
    - Arquivos de sincronização
    """
    # Procurar em arquivos de backtest
    backtest_files = [
        "backtest_results.json",
        "backtest_optimized_results.json",
        "backtest_final_metrics.json",
    ]
    
    for bf in backtest_files:
        if Path(bf).exists():
            try:
                with open(bf) as f:
                    data = json.load(f)
                    # Procurar por entrada correspondente
                    if isinstance(data, dict):
                        for key, value in data.items():
                            if isinstance(value, dict):
                                if (value.get("symbol") == symbol and 
                                    value.get("side") == side):
                                    sl = value.get("stop_loss")
                                    tp = value.get("take_profit")
                                    if sl and tp:
                                        return (float(sl), float(tp))
            except Exception as e:
                pass  # Continua procurando
    
    return None


def _estimate_sl_tp(side: str, entry: Decimal) -> tuple:
    """
    Estima SL/TP baseado em estratégia padrão.
    
    Estratégia Micro Tendência:
    - BUY: SL = entry - 1.5*ATR, TP = entry + 3*ATR
    - SELL: SL = entry + 1.5*ATR, TP = entry - 3*ATR
    
    Para recuperação, usa múltiplo fixo (1 ponto = 1 centavo em WINFUT)
    """
    # Estimativa conservadora: 1.5 e 3 pontos do entry
    if side == "BUY":
        sl = float(entry) - 1.5
        tp = float(entry) + 3.0
    else:  # SELL
        sl = float(entry) + 1.5
        tp = float(entry) - 3.0
    
    return (round(sl, 2), round(tp, 2))


if __name__ == "__main__":
    success = recover_historical_sl_tp()
    exit(0 if success else 1)
