#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICAÇÃO RÁPIDA: Fix S2-5 Terminal Isolation
Data: 27/02/2026
Status: ✅ FIX IMPLEMENTADO - Validação Rápida

Objetivo: Verificar que o fix foi aplicado corretamente
Tempo: <5 minutos
"""

import subprocess
import sys
from pathlib import Path

def check_fix_applied():
    """Verifica se o fix foi aplicado ao código."""
    print("\n" + "="*75)
    print("  VALIDAÇÃO RÁPIDA - FIX S2-5 (Terminal Isolation)")
    print("="*75 + "\n")

    # 1. Verificar se path é passado ao initialize()
    print("[1/3] Verificando se mt5.initialize() usa path parameter...")
    result = subprocess.run(
        ['grep', '-n', 'mt5.initialize(path=', 'src/infrastructure/adapters/mt5_adapter.py'],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"  ✅ ENCONTRADO: {result.stdout.strip()}")
        initialize_ok = True
    else:
        print("  ❌ NÃO ENCONTRADO: mt5.initialize(path=...)")
        initialize_ok = False

    # 2. Verificar se validação de arquivo foi adicionada
    print("\n[2/3] Verificando se os.path.isfile() foi adicionado...")
    result = subprocess.run(
        ['grep', '-n', 'os.path.isfile', 'src/infrastructure/adapters/mt5_adapter.py'],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"  ✅ ENCONTRADO: {result.stdout.strip()}")
        isfile_ok = True
    else:
        print("  ❌ NÃO ENCONTRADO: os.path.isfile()")
        isfile_ok = False

    # 3. Verificar se import os foi adicionado
    print("\n[3/3] Verificando se import os foi adicionado...")
    result = subprocess.run(
        ['grep', '-n', 'import os', 'src/infrastructure/adapters/mt5_adapter.py'],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"  ✅ ENCONTRADO: {result.stdout.strip()}")
        import_ok = True
    else:
        print("  ❌ NÃO ENCONTRADO: import os")
        import_ok = False

    print("\n" + "="*75)

    if initialize_ok and isfile_ok and import_ok:
        print("  ✅ FIX FOI APLICADO CORRETAMENTE!")
        print("\n  Próximas ações:")
        print("  1. Execute: pytest tests/unit/test_mt5_terminal_isolation.py -v")
        print("  2. Execute: python test_terminal_isolation.py")
        print("  3. Rode INICIAR_MICRO_TENDENCIA_AUTO_TRADE.bat com dois terminais MT5")
        print("="*75 + "\n")
        return True
    else:
        print("  ❌ FIX NÃO FOI APLICADO CORRETAMENTE!")
        print("\n  Problemas encontrados:")
        if not initialize_ok:
            print("  - mt5.initialize(path=...) não encontrado")
        if not isfile_ok:
            print("  - os.path.isfile() não encontrado")
        if not import_ok:
            print("  - import os não encontrado")
        print("="*75 + "\n")
        return False

if __name__ == "__main__":
    try:
        success = check_fix_applied()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Erro ao executar verificação: {e}\n")
        sys.exit(1)
