"""Script temporario para consultar operacoes de hoje no banco de dados."""
import sqlite3
from datetime import datetime

data_hoje = "2026-03-19"

conn = sqlite3.connect("data/db/trading.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 70)
print("ANALISE DO BANCO DE DADOS - OPERACOES DE 19/03/2026")
print("=" * 70)

# 1. Listar tabelas
print("\n=== TABELAS DISPONIVEIS ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tabelas = [t[0] for t in cursor.fetchall()]
for t in tabelas:
    cursor.execute(f"SELECT COUNT(*) FROM {t}")
    count = cursor.fetchone()[0]
    print(f"  - {t}: {count} registros")

# 2. Verificar estrutura de tabelas principais
print("\n=== ESTRUTURA DE TABELAS PRINCIPAIS ===")
for tabela in ["episodes", "rl_episodes", "orders", "trades", "sinais", "signals"]:
    if tabela in tabelas:
        cursor.execute(f"PRAGMA table_info({tabela})")
        cols = cursor.fetchall()
        print(f"\n{tabela}:")
        for col in cols:
            print(f"  {col[1]} ({col[2]})")

# 3. Buscar episodios de hoje
print("\n=== EPISODIOS DE HOJE (19/03/2026) ===")
if "episodes" in tabelas:
    cursor.execute("PRAGMA table_info(episodes)")
    cols = [c[1] for c in cursor.fetchall()]
    print(f"Colunas: {cols}")

    # Tentar varias colunas de data
    for date_col in ["timestamp", "created_at", "date", "data"]:
        if date_col in cols:
            try:
                cursor.execute(f"""
                    SELECT * FROM episodes
                    WHERE {date_col} LIKE ?
                    ORDER BY {date_col} DESC LIMIT 20
                """, (f"%{data_hoje}%",))
                rows = cursor.fetchall()
                if rows:
                    print(f"\nEncontrados {len(rows)} episodios em '{date_col}'")
                    for i, row in enumerate(rows[:10], 1):
                        d = dict(row)
                        print(f"\n--- Episodio {i} ---")
                        for k, v in d.items():
                            print(f"  {k}: {v}")
                break
            except Exception as e:
                print(f"Erro em {date_col}: {e}")

# 4. Verificar rl_episodes
print("\n=== RL EPISODES DE HOJE ===")
if "rl_episodes" in tabelas:
    cursor.execute("PRAGMA table_info(rl_episodes)")
    cols = [c[1] for c in cursor.fetchall()]
    print(f"Colunas: {cols}")

    for date_col in cols:
        if "time" in date_col.lower() or "date" in date_col.lower() or "created" in date_col.lower():
            try:
                cursor.execute(f"""
                    SELECT * FROM rl_episodes
                    WHERE {date_col} LIKE ?
                    ORDER BY {date_col} DESC LIMIT 10
                """, (f"%{data_hoje}%",))
                rows = cursor.fetchall()
                if rows:
                    print(f"\nEncontrados {len(rows)} episodios RL em '{date_col}'")
                    for i, row in enumerate(rows[:5], 1):
                        d = dict(row)
                        print(f"\n--- RL Episode {i} ---")
                        for k, v in list(d.items())[:10]:
                            print(f"  {k}: {v}")
            except Exception as e:
                print(f"Erro: {e}")

# 5. Verificar orders/trades
print("\n=== ORDERS/TRADES DE HOJE ===")
for tabela in ["orders", "trades", "ordens"]:
    if tabela in tabelas:
        cursor.execute(f"PRAGMA table_info({tabela})")
        cols = [c[1] for c in cursor.fetchall()]
        for date_col in cols:
            if "time" in date_col.lower() or "date" in date_col.lower():
                try:
                    cursor.execute(f"""
                        SELECT * FROM {tabela}
                        WHERE {date_col} LIKE ?
                        ORDER BY {date_col} DESC LIMIT 15
                    """, (f"%{data_hoje}%",))
                    rows = cursor.fetchall()
                    if rows:
                        print(f"\nTabela {tabela}: {len(rows)} registros de hoje")
                        for i, row in enumerate(rows[:5], 1):
                            d = dict(row)
                            print(f"  {i}. {d}")
                except Exception as e:
                    print(f"Erro em {tabela}: {e}")

conn.close()
print("\n" + "=" * 70)
