#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sqlite3
import shutil

print("=" * 70)
print("DIAGNOSTICO CRITICO - BANCO DE DADOS CHEIO")
print("=" * 70)

# 1. Espaco em disco TOTAL
print("\n1. ESPACO EM DISCO (C:\\)")
try:
    total, used, free = shutil.disk_usage("C:\\")
    free_gb = free / (1024**3)
    used_gb = used / (1024**3)
    total_gb = total / (1024**3)

    print(f"   Total: {total_gb:.1f} GB")
    print(f"   Usado: {used_gb:.1f} GB ({100*used/total:.1f}%)")
    print(f"   LIVRE: {free_gb:.1f} GB ({100*free/total:.1f}%)")

    if free_gb < 1:
        print("   [CRITICO] Menos de 1 GB livre - ESPACO ESGOTADO!")
    elif free_gb < 5:
        print("   [AVISO] Menos de 5 GB livre")
    else:
        print("   [OK] Espaco adequado")
except Exception as e:
    print(f"   ERRO: {e}")

# 2. Analise do banco de dados MAIOR
print("\n2. BANCO DE DADOS PRINCIPAL")
db_path = r"data\db\trading.db"

if os.path.exists(db_path):
    db_size_mb = os.path.getsize(db_path) / (1024*1024)
    print(f"   Arquivo: {db_path}")
    print(f"   Tamanho: {db_size_mb:.2f} MB ({os.path.getsize(db_path):,} bytes)")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Listar todas as tabelas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = cursor.fetchall()
        print(f"\n   TABELAS ({len(tables)}):")

        total_rows = 0
        for table in tables:
            table_name = table[0]
            try:
                cursor.execute(f"SELECT COUNT(*) FROM [{table_name}];")
                count = cursor.fetchone()[0]
                total_rows += count
                if count > 0:
                    # Mostrar tamanho da tabela
                    cursor.execute(f"SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size() WHERE table_name='{table_name}'")
                    print(f"      {table_name:40s}: {count:15,} registros")
            except Exception as e:
                print(f"      {table_name:40s}: ERRO ao contar")

        print(f"\n   Total de registros: {total_rows:,}")

        # Espaco livre do banco
        cursor.execute("PRAGMA freelist_count;")
        free_pages = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size;")
        page_size = cursor.fetchone()[0]
        free_mb = (free_pages * page_size) / (1024*1024)

        print(f"\n   Espaco livre NO BANCO: {free_mb:.2f} MB ({free_pages:,} paginas x {page_size} bytes)")
        print(f"   Journal: PRAGMA journal_mode")
        cursor.execute("PRAGMA journal_mode;")
        journal_mode = cursor.fetchone()[0]
        print(f"           {journal_mode}")

        conn.close()

    except Exception as e:
        print(f"   ERRO ao analisar banco: {e}")
else:
    print(f"   [ERRO] Banco nao encontrado em {db_path}")

# 3. ESPACO LIVRE ESTIMADO
print("\n3. DIAGNOSTICO FINAL")
print(f"   Espaço livre em disco: {free_gb:.1f} GB")
if db_size_mb > 100:
    print(f"   [AVISO] Banco trading.db tem {db_size_mb:.1f} MB (muito grande)")
if free_gb < 1:
    print(f"   [CRITICO] DISCO CHEIO - Nao ha espaco para gravacoes SQLite!")
    print(f"   [ACAO] Limpar arquivos temporarios ou dados antigos urgentemente")

print("\n" + "=" * 70)
