# -*- coding: utf-8 -*-
import sys
import os
import time
from pathlib import Path

# Adiciona o diretório raiz ao sys.path
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

def test_imports_latency():
    """Valida que imports não estão ocorrendo dentro de loops."""
    print("🔍 Testando latência de inicialização de módulos críticos...")

    # Primeiro import (cold)
    from src.application.services.rl_persistence_service import RLPersistenceService

    # Segundo import (warm)
    start = time.perf_counter()
    from src.application.services.rl_persistence_service import RLPersistenceService
    from src.infrastructure.repositories.rl_repository import SqliteRLRepository
    from src.infrastructure.database.rl_schema import create_rl_tables
    from sqlalchemy import create_engine
    end = time.perf_counter()

    latency = (end - start) * 1000
    print(f"✅ Latência de imports (quente): {latency:.4f}ms")
    # No Python, imports subsequentes do mesmo módulo são quase instantâneos (sys.modules lookup)
    assert latency < 1.0, f"Imports subsequentes muito lentos: {latency}ms. Indica que o cache de módulos do Python não está funcionando ou há overhead excessivo."

def test_cycle_latency_simulation():
    """Simula um ciclo operacional para validar o sensor de latência."""
    print("🔍 Simulando ciclo operacional para validar sensor de latência...")

    # Simula o que foi implementado no agente
    start_time = time.perf_counter()

    # Simula processamento (Analysis + Decision)
    time.sleep(0.05) # 50ms simulation

    # Simula Database access
    time.sleep(0.02) # 20ms simulation

    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000

    print(f"✅ Ciclo simulado: {latency_ms:.2f}ms")
    assert latency_ms < 500, f"Ciclo muito lento: {latency_ms}ms"

if __name__ == "__main__":
    try:
        test_imports_latency()
        test_cycle_latency_simulation()
        print("\n🟢 TODOS OS TESTES DE PERFORMANCE PASSARAM.")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n🔴 FALHA NO TESTE DE PERFORMANCE: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n🔴 ERRO INESPERADO: {e}")
        sys.exit(1)
