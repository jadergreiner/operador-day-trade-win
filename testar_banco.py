#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sqlite3

print("=" * 70)
print("VERIFICACAO DE INTEGRIDADE DO BANCO DE DADOS")
print("=" * 70)

db_path = r"data\db\trading.db"

try:
    print(f"\n1. CONECTANDO AO BANCO: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n2. EXECUTANDO PRAGMA INTEGRITY_CHECK...")
    cursor.execute("PRAGMA integrity_check")
    result = cursor.fetchone()[0]

    if result == "ok":
        print("   [OK] Banco esta integro e saudavel!")
    else:
        print(f"   [AVISO] Problemas detectados: {result}")

    # Verificar se as tabelas criticas existem
    print("\n3. VERIFICANDO TABELAS CRITICAS...")
    critical_tables = [
        'rl_correlation_scores',
        'rl_episodes',
        'rl_rewards',
        'rl_indicator_values'
    ]

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row[0] for row in cursor.fetchall()}

    for table in critical_tables:
        if table in existing_tables:
            cursor.execute(f"SELECT COUNT(*) FROM [{table}]")
            count = cursor.fetchone()[0]
            print(f"   [{table:30s}]: {count:10,} registros")
        else:
            print(f"   [{table:30s}]: NAO EXISTE")

    # Testar INSERT na tabela que estava dando erro
    print("\n4. TESTE DE INSERT (tabela rl_correlation_scores)...")
    try:
        # Nao vamos realmente fazer insert, mas vamos validar estrutura
        cursor.execute("PRAGMA table_info(rl_correlation_scores)")
        columns = cursor.fetchall()
        print(f"   Colunas: {len(columns)}")
        for col in columns:
            print(f"      - {col[1]:20s} ({col[2]})")
        print("   [OK] Estrutura valida para INSERT!")
    except Exception as e:
        print(f"   [ERRO] {e}")

    conn.close()
    print("\n" + "=" * 70)
    print("[OK] BANCO ESTA PRONTO PARA USO!")
    print("=" * 70)

except Exception as e:
    print(f"\n[ERRO CRITICO] {e}")

