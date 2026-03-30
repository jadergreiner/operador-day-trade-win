#!/usr/bin/env python3
"""
Script para verificar operações abertas e ticket específico.
"""

import sqlite3
from pathlib import Path

# Caminho do banco
DB_PATH = Path(__file__).parent.parent / "data" / "db" / "trading_rl_direto.db"

def verificar_operacao_aberta():
    """Verifica operações abertas e ticket específico"""

    if not DB_PATH.exists():
        print(f"Banco não encontrado: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    print("=== VERIFICANDO OPERAÇÕES ABERTAS ===")

    # Verificar operações abertas
    cursor.execute("""
        SELECT id, trade_id, symbol, side, quantity, entry_price, entry_time,
               status, broker_trade_id, created_at, updated_at
        FROM trades
        WHERE status = 'OPEN'
        ORDER BY entry_time DESC
    """)

    abertas = cursor.fetchall()

    if abertas:
        print(f"\nEncontradas {len(abertas)} operações abertas:")
        for op in abertas:
            print(f"ID={op[0]} | {op[2]} {op[3]} | Entrada: {op[4]} | Preço: {op[5]} | Ticket: {op[8]} | {op[6]}")
    else:
        print("\nNenhuma operação aberta encontrada.")

    # Verificar ticket específico
    ticket_procurado = "2277266572"
    print(f"\n=== VERIFICANDO TICKET {ticket_procurado} ===")

    cursor.execute("""
        SELECT id, trade_id, symbol, side, quantity, entry_price, entry_time,
               exit_price, exit_time, status, broker_trade_id, profit_loss,
               created_at, updated_at
        FROM trades
        WHERE broker_trade_id = ?
    """, (ticket_procurado,))

    ticket_encontrado = cursor.fetchone()

    if ticket_encontrado:
        print("Ticket encontrado:")
        print(f"ID={ticket_encontrado[0]} | {ticket_encontrado[2]} {ticket_encontrado[3]}")
        print(f"Status: {ticket_encontrado[9]} | Preço Entrada: {ticket_encontrado[5]}")
        print(f"Ticket MT5: {ticket_encontrado[10]}")
        print(f"Data/Hora Entrada: {ticket_encontrado[6]}")
        print(f"Data/Hora Saída: {ticket_encontrado[7]}")
        print(f"PnL: {ticket_encontrado[11]}")
        print(f"Criado: {ticket_encontrado[12]} | Atualizado: {ticket_encontrado[13]}")
    else:
        print(f"Ticket {ticket_procurado} NÃO encontrado no banco de dados.")

    # Verificar operações recentes (últimas 10)
    print("\n=== ÚLTIMAS 10 OPERAÇÕES (INDEPENDENTE DO STATUS) ===")
    cursor.execute("""
        SELECT id, trade_id, symbol, side, entry_price, entry_time, status,
               broker_trade_id, profit_loss
        FROM trades
        ORDER BY entry_time DESC
        LIMIT 10
    """)

    recentes = cursor.fetchall()
    for op in recentes:
        status_icon = "🔴" if op[6] == "OPEN" else "✅"
        print(f"{status_icon} ID={op[0]} | {op[2]} {op[3]} | {op[4]} | {op[5]} | Ticket: {op[7]} | PnL: {op[8]}")

    conn.close()

if __name__ == "__main__":
    verificar_operacao_aberta()