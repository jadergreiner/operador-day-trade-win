import sqlite3
from datetime import datetime

def query_stats():
    conn = sqlite3.connect('trading.db')
    cursor = conn.cursor()

    today = "2026-02-23" # Current session date

    print(f"--- RELATÓRIO DO DIA {today} ---")

    # Check if the table exists first by sampling or PRAGMA
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='micro_trend_opportunities'")
    if cursor.fetchone():
        cursor.execute("SELECT count(*) FROM micro_trend_opportunities WHERE date(timestamp) = ?", (today,))
        print(f"Oportunidades (Tendência): {cursor.fetchone()[0]}")
    else:
        print("Tabela micro_trend_opportunities não encontrada.")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
    if cursor.fetchone():
        cursor.execute("SELECT count(*) FROM trades WHERE date(entry_time) = ?", (today,))
        print(f"Trades Executados (Live): {cursor.fetchone()[0]}")
    else:
        print("Tabela trades não encontrada.")

    # Check for labels in backtest if any
    try:
        import json
        with open('backtest_labeled_results.json', 'r') as f:
            data = json.load(f)
            # Assuming labels created today for the 1000 samples
            print(f"Amostras Geradas para Treino (ML): {len(data)}")
    except FileNotFoundError:
        print("Arquivo backtest_labeled_results.json não encontrado.")

    conn.close()

if __name__ == "__main__":
    query_stats()
