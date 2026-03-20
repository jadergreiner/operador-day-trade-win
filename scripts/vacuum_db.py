#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3
import os
import time

from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock

print("=" * 70)
print("RECUPERACAO DE ESPACO DO BANCO DE DADOS (VACUUM)")
print("=" * 70)

db_path = r"data\db\trading.db"

print(f"\n1. VERIFICANDO BANCO: {db_path}")
db_size_before = os.path.getsize(db_path) / (1024*1024)
print(f"   Tamanho ANTES: {db_size_before:.2f} MB")

try:
    print("\n2. EXECUTANDO VACUUM (pode levar alguns minutos)...")
    with sqlite_write_lock(db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("VACUUM")
        conn.close()
    print("   VACUUM executado com sucesso!")

    time.sleep(1)
    db_size_after = os.path.getsize(db_path) / (1024*1024)
    print(f"\n3. RESULTADOS")
    print(f"   Tamanho DEPOIS: {db_size_after:.2f} MB")
    print(f"   Espaco RECUPERADO: {db_size_before - db_size_after:.2f} MB")
    print(f"   Reducao: {100 * (db_size_before - db_size_after) / db_size_before:.1f}%")

    if db_size_after < db_size_before:
        print("   [OK] Banco compactado com sucesso!")

except Exception as e:
    print(f"   [ERRO] {e}")

print("\n" + "=" * 70)
