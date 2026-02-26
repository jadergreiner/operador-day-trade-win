#!/usr/bin/env python
"""
Migration script: Adicionar coluna execution_method à tabela trades.

Purpose: Diferenciar ordens criadas automaticamente vs ordens manuais.
Execution: python migrate_add_execution_method.py
"""

import sqlite3
from pathlib import Path

DB_PATH = Path("data/db/trading.db")


def migrate_add_execution_method() -> bool:
    """Adiciona coluna execution_method à tabela trades."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(trades)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        if "execution_method" in column_names:
            print("✅ Coluna 'execution_method' já existe na tabela trades")
            conn.close()
            return True

        print("🔄 Adicionando coluna 'execution_method' à tabela trades...")

        # Adicionar a coluna
        cursor.execute(
            """
            ALTER TABLE trades
            ADD COLUMN execution_method VARCHAR(20) DEFAULT 'manual' NOT NULL
            """
        )

        print("✅ Coluna adicionada com sucesso")

        # Verificar resultado
        cursor.execute("PRAGMA table_info(trades)")
        columns = cursor.fetchall()
        print(f"\n📋 Nova estrutura de trades:")
        print(f"{'Coluna':<25} {'Tipo':<20}")
        print("=" * 45)
        for col in columns:
            print(f"{col[1]:<25} {col[2]:<20}")

        conn.commit()
        conn.close()

        print("\n✅ Migração concluída com sucesso!")
        return True

    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        return False


if __name__ == "__main__":
    success = migrate_add_execution_method()
    exit(0 if success else 1)
