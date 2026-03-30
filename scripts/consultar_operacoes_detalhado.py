#!/usr/bin/env python3
"""
Script detalhado para consultar operações do agente RL Direto hoje.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

# Caminho do banco
DB_PATH = Path(__file__).parent.parent / "data" / "db" / "trading_rl_direto.db"

def consultar_operacoes_detalhado():
    """Consulta detalhada das operações realizadas hoje"""

    if not DB_PATH.exists():
        print(f"Banco não encontrado: {DB_PATH}")
        return

    hoje = datetime.now().strftime("%Y-%m-%d")
    print(f"Consultando operações para data: {hoje}")

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Ver todas as operações de hoje (filtrando por entry_time)
    cursor.execute("""
        SELECT id, trade_id, symbol, side, quantity, entry_price, entry_time,
               exit_price, exit_time, status, profit_loss, created_at
        FROM trades
        WHERE DATE(entry_time) = ?
        ORDER BY entry_time DESC
    """, (hoje,))

    todas_operacoes = cursor.fetchall()

    print(f"\n=== TODAS AS OPERAÇÕES DE {hoje} ===")
    print(f"Total de operações encontradas: {len(todas_operacoes)}")

    fechadas = []
    abertas = []

    for op in todas_operacoes:
        (id_, trade_id, symbol, side, quantity, entry_price, entry_time,
         exit_price, exit_time, status, profit_loss, created_at) = op

        if status == 'CLOSED':
            fechadas.append(op)
            print(f"FECHADA: ID={id_} | {symbol} {side} | Entrada: {entry_price} | Saída: {exit_price} | PnL: {profit_loss} | {entry_time}")
        elif status == 'OPEN':
            abertas.append(op)
            print(f"ABERTA:  ID={id_} | {symbol} {side} | Entrada: {entry_price} | {entry_time}")

    print("\n=== RESUMO ===")
    print(f"Operações fechadas: {len(fechadas)}")
    print(f"Operações abertas: {len(abertas)}")

    if fechadas:
        pnl_total = sum(op[10] for op in fechadas if op[10] is not None)
        winners = sum(1 for op in fechadas if op[10] and op[10] > 0)
        losers = sum(1 for op in fechadas if op[10] and op[10] < 0)
        win_rate = (winners / len(fechadas) * 100) if fechadas else 0

        print(f"Vencedoras: {winners}")
        print(f"Perdedoras: {losers}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"PnL Total: R$ {pnl_total:.2f}")

    # Verificar se há operações de outros dias que podem estar sendo incluídas
    cursor.execute("""
        SELECT DATE(created_at) as data, COUNT(*) as total
        FROM trades
        GROUP BY DATE(created_at)
        ORDER BY data DESC
        LIMIT 10
    """)

    distribuicao_datas = cursor.fetchall()
    print("\n=== DISTRIBUIÇÃO POR DATA ===")
    for data, total in distribuicao_datas:
        print(f"{data}: {total} operações")

    conn.close()

if __name__ == "__main__":
    consultar_operacoes_detalhado()