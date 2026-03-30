#!/usr/bin/env python3
"""
Script para consultar estatísticas de operações do agente RL Direto hoje.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

# Caminho do banco
DB_PATH = Path(__file__).parent.parent / "data" / "db" / "trading_rl_direto.db"

def consultar_operacoes_hoje():
    """Consulta operações realizadas hoje no banco trading_rl_direto.db"""

    if not DB_PATH.exists():
        print(f"Banco não encontrado: {DB_PATH}")
        return

    hoje = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Consultar operações fechadas hoje
    cursor.execute("""
        SELECT COUNT(*), SUM(profit_loss), AVG(profit_loss)
        FROM trades
        WHERE DATE(created_at) = ?
        AND status = 'CLOSED'
    """, (hoje,))

    fechadas = cursor.fetchone()
    total_fechadas = fechadas[0] if fechadas[0] else 0
    pnl_total = fechadas[1] if fechadas[1] else 0.0
    pnl_medio = fechadas[2] if fechadas[2] else 0.0

    # Consultar operações abertas
    cursor.execute("""
        SELECT COUNT(*)
        FROM trades
        WHERE DATE(created_at) = ?
        AND status = 'OPEN'
    """, (hoje,))

    abertas = cursor.fetchone()
    total_abertas = abertas[0] if abertas[0] else 0

    # Consultar vencedores e perdedores
    cursor.execute("""
        SELECT
            SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winners,
            SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losers
        FROM trades
        WHERE DATE(created_at) = ?
        AND status = 'CLOSED'
    """, (hoje,))

    wl = cursor.fetchone()
    winners = wl[0] if wl[0] else 0
    losers = wl[1] if wl[1] else 0

    conn.close()

    # Calcular win rate
    win_rate = (winners / total_fechadas * 100) if total_fechadas > 0 else 0

    print("=== ESTATÍSTICAS DO AGENTE RL DIRETO - HOJE ===")
    print(f"Data: {hoje}")
    print(f"Operações fechadas: {total_fechadas}")
    print(f"Operações abertas: {total_abertas}")
    print(f"Vencedoras: {winners}")
    print(f"Perdedoras: {losers}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"PnL Total: R$ {pnl_total:.2f}")
    print(f"PnL Médio: R$ {pnl_medio:.2f}")

if __name__ == "__main__":
    consultar_operacoes_hoje()