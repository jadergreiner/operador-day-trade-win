import sqlite3
from datetime import datetime

# Acessar trading.db
print("=" * 80)
print("📊 TRADING.DB - Verificando Trades de 24/02/2026")
print("=" * 80)

try:
    conn = sqlite3.connect('data/db/trading.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Listar tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\n📋 Tabelas disponíveis:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Procurar por trades/orders de 24/02
    for table_name in [row[0] for row in tables]:
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        col_names = [col[1] for col in columns]
        
        # Se tem coluna timestamp ou date, procurar por 24/02
        if any(t in col_names for t in ['timestamp', 'created_at', 'date', 'execution_date']):
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            total = cursor.fetchone()[0]
            print(f"\n📌 Tabela '{table_name}' ({total} registros totais):")
            
            # Procurar registros de 24/02
            try:
                cursor.execute(f"SELECT * FROM {table_name} WHERE timestamp LIKE '2026-02-24%' OR created_at LIKE '2026-02-24%' ORDER BY timestamp DESC LIMIT 5;")
                results = cursor.fetchall()
                if results:
                    print(f"  ✅ Encontrados {len(results)} registros de 24/02:")
                    for row in results:
                        print(f"    {dict(row)}")
                else:
                    print(f"  ❌ Nenhum registro de 24/02 encontrado")
            except Exception as e:
                print(f"  ⚠️  Erro ao consultar: {e}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Erro ao acessar trading.db: {e}")

print("\n" + "=" * 80)

# Acessar wdo_winfut.db
print("\n📊 WDO_WINFUT.DB - Verificando WDO/WINFUT Trades de 24/02/2026")
print("=" * 80)

try:
    conn = sqlite3.connect('data/db/wdo_winfut.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\n📋 Tabelas disponíveis:")
    for table in tables:
        print(f"  - {table[0]}")
    
    for table_name in [row[0] for row in tables]:
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        col_names = [col[1] for col in columns]
        
        if any(t in col_names for t in ['timestamp', 'created_at', 'date', 'execution_date']):
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            total = cursor.fetchone()[0]
            print(f"\n📌 Tabela '{table_name}' ({total} registros totais):")
            
            try:
                cursor.execute(f"SELECT * FROM {table_name} WHERE timestamp LIKE '2026-02-24%' OR created_at LIKE '2026-02-24%' ORDER BY timestamp DESC LIMIT 5;")
                results = cursor.fetchall()
                if results:
                    print(f"  ✅ Encontrados {len(results)} registros de 24/02:")
                    for row in results:
                        print(f"    {dict(row)}")
                else:
                    print(f"  ❌ Nenhum registro de 24/02 encontrado")
            except Exception as e:
                print(f"  ⚠️  Erro ao consultar: {e}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Erro ao acessar wdo_winfut.db: {e}")

print("\n" + "=" * 80)
