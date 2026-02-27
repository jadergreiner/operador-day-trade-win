#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDAÇÃO RÁPIDA - FIX S2-5 (Terminal Isolation)
Windows-compatible version (sem usar grep)
"""

import sys
from pathlib import Path

def check_fix_applied():
    """Verifica se o fix foi aplicado ao código."""
    print("\n" + "="*75)
    print("  VALIDAÇÃO RÁPIDA - FIX S2-5 (Terminal Isolation)")
    print("="*75 + "\n")

    file_path = Path("src/infrastructure/adapters/mt5_adapter.py")

    if not file_path.exists():
        print(f"❌ Arquivo não encontrado: {file_path}")
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Verificar se path é passado ao initialize()
    print("[1/3] Verificando se mt5.initialize() usa path parameter...")
    if 'mt5.initialize(path=self.terminal_exe_path)' in content or 'mt5.initialize(path=' in content:
        print("  ✅ ENCONTRADO: mt5.initialize(path=...)")
        initialize_ok = True
    else:
        print("  ❌ NÃO ENCONTRADO: mt5.initialize(path=...)")
        initialize_ok = False

    # 2. Verificar se validação de arquivo foi adicionada
    print("\n[2/3] Verificando se os.path.isfile() foi adicionado...")
    if 'os.path.isfile' in content:
        print("  ✅ ENCONTRADO: os.path.isfile(...)")
        isfile_ok = True
    else:
        print("  ❌ NÃO ENCONTRADO: os.path.isfile()")
        isfile_ok = False

    # 3. Verificar se import os foi adicionado
    print("\n[3/3] Verificando se 'import os' foi adicionado...")
    lines = content.split('\n')
    import_os_found = False

    for i, line in enumerate(lines):
        if 'import MetaTrader5 as mt5' in line:
            # Procurar import os nos próximos 5 linhas
            for j in range(i, min(i+5, len(lines))):
                if 'import os' in lines[j]:
                    print(f"  ✅ ENCONTRADO: import os (linha {j+1})")
                    import_os_found = True
                    break
            break

    if not import_os_found:
        print("  ❌ NÃO ENCONTRADO: import os")

    # Resultado final
    print("\n" + "="*75)
    if initialize_ok and isfile_ok and import_os_found:
        print("  ✅ FIX VALIDADO COM SUCESSO!")
        print("     Código foi alterado corretamente")
        print("     Pronto para testes T2-T5")
        print("="*75 + "\n")
        return True
    else:
        print("  ❌ VALIDAÇÃO FALHOU")
        print(f"     initialize_ok: {initialize_ok}")
        print(f"     isfile_ok: {isfile_ok}")
        print(f"     import_os_found: {import_os_found}")
        print("="*75 + "\n")
        return False

if __name__ == "__main__":
    success = check_fix_applied()
    sys.exit(0 if success else 1)
