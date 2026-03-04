# -*- coding: utf-8 -*-
"""
Initialize Reflection Persistence - Com Auto-Recovery

Executar ANTES de ai_reflection_continuous.py para:
1. Verificar integridade de dados
2. Recuperar reflexões orfãs do JSONL
3. Validar database SQLite
4. Display health status
"""

import sys
from pathlib import Path
import logging

# Setup path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.persistence.resilient_reflection_persistence import (
    ResilientReflectionPersistence,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            project_root / "data" / "logs" / "reflection_persistence_init.log"
        ),
    ],
)
logger = logging.getLogger("reflection_persistence_init")


def initialize_reflection_persistence():
    """Initialize persistence and auto-recover if needed."""

    print("\n" + "=" * 80)
    print("INICIALIZANDO PERSISTÊNCIA DE REFLEXÕES COM AUTO-RECOVERY")
    print("=" * 80 + "\n")

    try:
        # 1. Initialize persistence layer
        logger.info("Inicializando camada de persistência...")
        persistence = ResilientReflectionPersistence(project_root)
        logger.info("[OK] Camada de persistencia inicializada")

        # 2. Check health status
        logger.info("Verificando saude da persistencia...")
        health = persistence.get_health_status()

        total_reflections = health.get("total_reflections", 0)
        failed_writes = health.get("failed_writes", 0)
        status = health.get("status", "UNKNOWN")

        logger.info(f"  * Total de reflexoes em SQLite: {total_reflections}")
        logger.info(f"  * Escritas falhadas: {failed_writes}")
        logger.info(f"  * Status: {status}")

        # 3. Check for orphaned entries
        logger.info("Procurando por reflexões orfãs em JSONL...")
        orphaned = persistence._find_orphaned_entries()

        if orphaned:
            logger.warning(
                f"Encontradas {len(orphaned)} reflexões orfãs - iniciando recuperação..."
            )

            # 4. Auto-recover
            logger.info("Executando auto-recovery...")
            recovered = persistence.recover_from_failure()

            logger.info(f"[OK] Auto-recovery concluido: {recovered} reflexoes recuperadas")

            # Re-check health after recovery
            health = persistence.get_health_status()
            total_reflections = health.get("total_reflections", 0)
            logger.info(f"  * Total de reflexoes apos recovery: {total_reflections}")

        else:
            logger.info("[OK] Nenhuma reflexao orfa encontrada")

        # 5. Validate database integrity
        logger.info("Validando integridade do database...")
        persistence._repair_corrupted_records()
        logger.info("[OK] Database validation concluido")

        # 6. Display final status
        print("\n" + "-" * 80)
        print("RESULTADO FINAL")
        print("-" * 80 + "\n")

        health = persistence.get_health_status()
        print(f"Status Geral: {health['status']}")
        print(f"Total de reflexoes: {health['total_reflections']}")
        print(f"Escritas falhadas: {health['failed_writes']}")
        print(f"Tamanho database: {health['db_size_mb']} MB")
        print(f"Tamanho JSONL: {health['jsonl_size_mb']} MB")

        if health.get("last_reflection_timestamp"):
            print(f"Ultima reflexao: {health['last_reflection_timestamp']}")

        print("\n" + "=" * 80)
        print("[OK] PERSISTENCIA PRONTA PARA OPERACAO\n")

        logger.info("[OK] Inicializacao de persistencia completa")

        return persistence

    except Exception as e:
        logger.error(f"[ERRO] Erro durante inicializacao: {e}")
        print(f"\n[ERRO] {e}\n")
        raise


if __name__ == "__main__":
    try:
        persistence = initialize_reflection_persistence()
        print("\nVocê pode agora executar:")
        print("  python scripts/ai_reflection_continuous.py")
        print()
    except Exception as e:
        print(f"\nFalha na inicialização: {e}\n")
        sys.exit(1)
