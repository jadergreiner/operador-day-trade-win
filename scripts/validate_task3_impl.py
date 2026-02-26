#!/usr/bin/env python3
"""
Script de validação rápida de TASK #3
Executa testes do BacktestValidator e reporta resultado
"""

import sys
import subprocess
import json
from pathlib import Path

# Add workspace to path
workspace_path = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_path))

def run_tests():
    """Executa testes e retorna resultado"""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", 
         "tests/unit/test_integration_ml_002_backtest.py", 
         "-v", "--tb=short", "-q"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    print("==== TESTE OUTPUT ====")
    print(result.stdout)
    if result.stderr:
        print("==== STDERR ====")
        print(result.stderr)
    
    return result.returncode == 0

def check_implementation():
    """Valida que a implementação foi completada"""
    from src.application.backtest_validator import BacktestValidator
    
    # Validar que não há mais NotImplementedError
    import inspect
    
    methods_to_check = [
        'load_dataset',
        '_train_model',
        '_cross_validate',
        '_calculate_metrics',
        '_run_backtest',
        'run_grid_search',
        'save_results'
    ]
    
    for method_name in methods_to_check:
        method = getattr(BacktestValidator, method_name)
        source = inspect.getsource(method)
        
        if 'NotImplementedError' in source:
            print(f"❌ {method_name} ainda contém NotImplementedError")
            return False
        else:
            print(f"✅ {method_name} implementado")
    
    return True

if __name__ == "__main__":
    print("🚀 Validando TASK #3 - INTEGRATION-ML-002\n")
    
    # Step 1: Check implementation
    print("Passo 1: Verificar implementação...")
    impl_ok = check_implementation()
    
    if not impl_ok:
        print("\n❌ Implementação incompleta!")
        sys.exit(1)
    
    print("\n✅ Implementação completa!\n")
    
    # Step 2: Run tests
    print("Passo 2: Executar testes...")
    try:
        tests_ok = run_tests()
        
        if tests_ok:
            print("\n✅ TODOS OS TESTES PASSARAM!")
            sys.exit(0)
        else:
            print("\n⚠️  Some testes falharam")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro ao executar testes: {e}")
        sys.exit(1)
