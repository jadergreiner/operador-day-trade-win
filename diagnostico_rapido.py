import os
import sqlite3

print("🔍 DIAGNÓSTICO IMEDIATO\n" + "="*60)

# 1. Espaço em disco
import shutil
total, used, free = shutil.disk_usage("C:\\")
free_gb = free / (1024**3)
used_gb = used / (1024**3)
total_gb = total / (1024**3)

print(f"\n💾 DISCO C:\\")
print(f"  Total: {total_gb:.1f} GB")
print(f"  Usado: {used_gb:.1f} GB ({100*used/total:.1f}%)")
print(f"  Livre: {free_gb:.1f} GB ({100*free/total:.1f}%)")

if free_gb < 1:
    print("  ⚠️  CRÍTICO: Menos de 1GB livre!")
elif free_gb < 5:
    print("  ⚠️  AVISO: Menos de 5GB livre")
else:
    print("  ✅ OK")

# 2. Banco de dados SQLite
try:
    db_path = "data/simulator.db"
    if os.path.exists(db_path):
        db_size_mb = os.path.getsize(db_path) / (1024*1024)
        print(f"\n📦 BANCO DE DADOS: {db_path}")
        print(f"  Tamanho: {db_size_mb:.2f} MB")

        # Conectar e verificar tabelas
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        print(f"  Tabelas: {len(tables)}")

        # Tabela que está dando erro
        cursor.execute("SELECT COUNT(*) FROM rl_correlation_scores;")
        count = cursor.fetchone()[0]
        print(f"    - rl_correlation_scores: {count:,} registros")

        cursor.execute("PRAGMA freelist_count;")
        free_pages = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size;")
        page_size = cursor.fetchone()[0]
        free_mb = (free_pages * page_size) / (1024*1024)
        print(f"  Espaço livre no banco: {free_mb:.2f} MB ({free_pages} páginas)")

        conn.close()
    else:
        print(f"\n❌ Banco não encontrado: {db_path}")
except Exception as e:
    print(f"\n❌ Erro ao diagnosticar banco: {e}")

print("\n" + "="*60)
