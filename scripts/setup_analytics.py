"""
Setup de Analytics Database para S2-6

Cria schema para rastreamento de intervenções manuais do trader
(OVERRIDE, PAUSE, CANCEL, EXECUTE).

Execução:
    python scripts/setup_analytics.py --mode interventions
    python scripts/setup_analytics.py --mode optimize
    python scripts/setup_analytics.py --mode validate
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock


def setup_interventions_table(db_path: str) -> bool:
    """
    Cria tabela de intervenções manuais.

    Rastreia:
    - Timestamp
    - Símbolo (WINFUT, etc)
    - Ação (OVERRIDE, PAUSE, CANCEL, EXECUTE)
    - Sinal ML original
    - Decisão do trader
    - Resultado (WIN, LOSS, PARTIAL)
    - P&L
    """
    try:
        with sqlite_write_lock(db_path):
            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            cursor = conn.cursor()

            # Criar tabela principal
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trader_interventions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT,
                    ml_signal FLOAT,
                    trader_decision TEXT,
                    result TEXT,
                    p_and_l FLOAT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    notes TEXT
                )
            """)

            # Criar índices para performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON trader_interventions(timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol
                ON trader_interventions(symbol)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_action
                ON trader_interventions(action)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_result
                ON trader_interventions(result)
            """)

            conn.commit()
            conn.close()

        print("✅ Tabela 'trader_interventions' criada com sucesso")
        return True

    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")
        return False


def optimize_database(db_path: str) -> bool:
    """Otimiza e valida database."""
    try:
        with sqlite_write_lock(db_path):
            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            cursor = conn.cursor()

            # Analyze para otimizar queries
            cursor.execute("ANALYZE")

            # Vacuum para compactar
            cursor.execute("VACUUM")

            conn.commit()
            conn.close()

        print("✅ Database otimizado (ANALYZE + VACUUM)")
        return True

    except Exception as e:
        print(f"❌ Erro ao otimizar: {e}")
        return False


def validate_database(db_path: str) -> bool:
    """Valida integridade do database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Verificar integridade
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()

        if result[0] == "ok":
            print("✅ Integridade do database: OK")
        else:
            print(f"❌ Problemas de integridade: {result[0]}")
            return False

        # Contar tabelas
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='table' AND name LIKE '%intervention%'
        """)
        table_count = cursor.fetchone()[0]
        print(f"✅ Tabelas encontradas: {table_count}")

        # Contar índices
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master
            WHERE type='index' AND tbl_name='trader_interventions'
        """)
        index_count = cursor.fetchone()[0]
        print(f"✅ Índices criados: {index_count}")

        # Verificar rows (se houver dados préexistentes)
        cursor.execute("SELECT COUNT(*) FROM trader_interventions")
        row_count = cursor.fetchone()[0]
        print(f"✅ Registros na tabela: {row_count}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Erro ao validar: {e}")
        return False


def main():
    """Função principal."""
    # Determinar caminho do database
    project_root = Path(__file__).parent.parent
    db_path = str(project_root / "data" / "analytics.db")

    # Criar diretório data se não existir
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("🔧 ANALYTICS DATABASE SETUP (S2-6)")
    print("=" * 70)
    print(f"Database: {db_path}\n")

    # Parse argumentos
    mode = "interventions"  # default
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith("--mode="):
                mode = arg.split("=")[1]
            elif arg == "--mode" and len(sys.argv) > 2:
                mode = sys.argv[sys.argv.index(arg) + 1]

    # Executar modo solicitado
    if mode == "interventions":
        print("📋 Modo: Criar tabela de intervenções")
        print("-" * 70)
        success = setup_interventions_table(db_path)

    elif mode == "optimize":
        print("⚡ Modo: Otimizar database")
        print("-" * 70)
        success = optimize_database(db_path)

    elif mode == "validate":
        print("✔️  Modo: Validar database")
        print("-" * 70)
        success = validate_database(db_path)

    else:
        print(f"❌ Modo desconhecido: {mode}")
        print("Modos suportados: interventions, optimize, validate")
        return 1

    print("=" * 70)

    if success:
        print("✅ Setup concluído com sucesso\n")
        return 0
    else:
        print("❌ Setup falhou\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
