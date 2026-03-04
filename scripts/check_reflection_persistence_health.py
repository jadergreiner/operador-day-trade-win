# -*- coding: utf-8 -*-
"""
Monitor e Verificar Persistência de Reflexões

Funções:
- Verificar saúde da persistência
- Recuperar de falhas
- Validar integridade de dados
- Exibir estatísticas
"""

import sys
from pathlib import Path
import json
from datetime import datetime

# Setup path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.persistence.resilient_reflection_persistence import (
    ResilientReflectionPersistence,
)


def check_persistencia_health():
    """Check persistence health status."""
    print("\n" + "=" * 80)
    print("VERIFICAÇÃO DE SAÚDE - PERSISTÊNCIA DE REFLEXÕES")
    print("=" * 80 + "\n")

    persistence = ResilientReflectionPersistence(project_root)
    health = persistence.get_health_status()

    # Display health metrics
    print(f"Status Geral: {health['status']}\n")

    print("Métricas Principais:")
    print(f"  • Total de reflexões: {health['total_reflections']}")
    print(f"  • Escritas falhadas: {health['failed_writes']}")
    print(f"  • Tamanho database (SQLite): {health['db_size_mb']} MB")
    print(f"  • Tamanho JSONL: {health['jsonl_size_mb']} MB")

    if health['last_reflection_timestamp']:
        print(f"  • Última reflexão: {health['last_reflection_timestamp']}")
        if health['time_since_last_reflection_seconds'] is not None:
            minutes = health['time_since_last_reflection_seconds'] / 60
            print(f"  • Tempo desde última reflexão: {minutes:.1f} minutos")

    print("\nMétricas de Persistência:")
    metrics = health.get('metrics', {})
    print(f"  • Total de reflexões (métrica): {metrics.get('total_reflections', 0)}")
    print(f"  • Última escrita bem-sucedida: {metrics.get('last_successful_write', 'N/A')}")
    print(f"  • Último erro: {metrics.get('last_error', 'N/A')}")

    print("\n" + "=" * 80 + "\n")

    return health


def recover_from_failure():
    """Recover from failure and restore missing data."""
    print("\n" + "=" * 80)
    print("RECUPERAÇÃO DE FALHAS - IMPORTAR REFLEXÕES ORFÃS")
    print("=" * 80 + "\n")

    persistence = ResilientReflectionPersistence(project_root)

    print("Buscando por reflexões orfãs em JSONL não presentes em SQLite...")
    recovered_count = persistence.recover_from_failure()

    print(f"\n✓ Recuperação concluída: {recovered_count} reflexões restauradas\n")
    print("=" * 80 + "\n")

    return recovered_count


def validate_data_integrity():
    """Validate data integrity between SQLite and JSONL."""
    print("\n" + "=" * 80)
    print("VALIDAÇÃO DE INTEGRIDADE")
    print("=" * 80 + "\n")

    persistence = ResilientReflectionPersistence(project_root)

    import sqlite3

    conn = sqlite3.connect(str(persistence.db_path))
    cursor = conn.execute("SELECT COUNT(*) FROM reflections")
    db_count = cursor.fetchone()[0]
    conn.close()

    jsonl_count = 0
    if persistence.jsonl_path.exists():
        with open(str(persistence.jsonl_path), "r", encoding="utf-8") as f:
            jsonl_count = sum(1 for line in f if line.strip())

    print(f"Reflexões em SQLite:  {db_count}")
    print(f"Reflexões em JSONL:   {jsonl_count}")

    if db_count >= jsonl_count:
        print(f"\n✓ Integridade OK: SQLite tem todos os dados ({db_count} vs {jsonl_count})")
    else:
        print(f"\n⚠ Aviso: {jsonl_count - db_count} reflexões em JSONL não estão em SQLite")
        print("  Execute: recover_persistencia() para importar dados orfãos\n")

    print("=" * 80 + "\n")


def export_todas_reflexoes():
    """Export all reflections to JSONL format."""
    print("\n" + "=" * 80)
    print("EXPORTAR TODAS AS REFLEXÕES")
    print("=" * 80 + "\n")

    persistence = ResilientReflectionPersistence(project_root)

    export_file = persistence.export_to_jsonl()

    print(f"✓ Reflexões exportadas para: {export_file}\n")
    print("=" * 80 + "\n")

    return export_file


def show_recent_reflections(limit: int = 10):
    """Show recent reflections from database."""
    print("\n" + "=" * 80)
    print(f"ÚLTIMAS {limit} REFLEXÕES")
    print("=" * 80 + "\n")

    persistence = ResilientReflectionPersistence(project_root)

    import sqlite3

    conn = sqlite3.connect(str(persistence.db_path))
    cursor = conn.execute("""
        SELECT entry_id, timestamp, mood, decision, confidence, one_liner
        FROM reflections
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    for entry_id, timestamp, mood, decision, confidence, one_liner in rows:
        print(f"[{timestamp}] {entry_id}")
        print(f"  Humor: {mood}")
        print(f"  Decisão: {decision} (conf: {confidence:.2f})")
        print(f"  \"{one_liner}\"")
        print()

    print("=" * 80 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Monitor e recuperar persistência de reflexões"
    )
    parser.add_argument(
        "action",
        choices=["health", "recover", "validate", "export", "recent"],
        help="Ação a executar",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Número de reflexões a mostrar (para 'recent')",
    )

    args = parser.parse_args()

    try:
        if args.action == "health":
            check_persistencia_health()

        elif args.action == "recover":
            recover_from_failure()
            # Auto-check health after recovery
            print("Verificando saúde após recuperação...")
            check_persistencia_health()

        elif args.action == "validate":
            validate_data_integrity()

        elif args.action == "export":
            export_todas_reflexoes()

        elif args.action == "recent":
            show_recent_reflections(args.limit)

    except Exception as e:
        print(f"\n[ERRO] {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
