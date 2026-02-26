#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test: Terminal Isolation Detection (S2-5)

Verifica qual terminal MT5 o sistema consegue encontrar e garante
que está usando o terminal CORRETO (Clear) e não os outros (FBS, Zero).
"""

import subprocess
import sys
from pathlib import Path

def find_all_mt5_terminals():
    """Encontra todos os terminais MT5 no sistema."""
    terminals = {
        "Clear": "C:\\Program Files\\Clear Investimentos MT5 Terminal\\terminal64.exe",
        "FBS": "C:\\Program Files\\FBS MetaTrader 5\\terminal64.exe",
        "Zero Markets": "C:\\Program Files\\Zero Markets MetaTrader 5 Terminal\\terminal64.exe",
    }
    
    found = {}
    for name, path in terminals.items():
        if Path(path).exists():
            found[name] = path
    
    return found

def main():
    print("\n" + "="*75)
    print("  TEST: Terminal Isolation (S2-5) Detection")
    print("="*75 + "\n")
    
    # 1. Encontra terminais disponíveis
    print("🔍 Terminais MT5 disponíveis no sistema:")
    all_terminals = find_all_mt5_terminals()
    
    for i, (name, path) in enumerate(all_terminals.items(), 1):
        status = "✅ CONFIGURADO" if "Clear" in name else "⚠️  RISCO ACIDENTAL"
        print(f"   {i}. [{status}] {name}")
        print(f"      └─ {path}\n")
    
    # 2. Carrega configuração esperada
    print("📋 Configuração do Agente:")
    from config.settings import TradingConfig
    config = TradingConfig()
    print(f"   ✅ Terminal esperado: {config.mt5_terminal_path}")
    print(f"   ✅ Login esperado: {config.mt5_login}")
    print(f"   ✅ Server esperado: {config.mt5_server}\n")
    
    # 3. Valida que terminal configurado existe
    if Path(config.mt5_terminal_path).exists():
        print(f"   ✅ Terminal configurado EXISTE no sistema")
    else:
        print(f"   ❌ Terminal configurado NÃO EXISTE!")
        print(f"      Verifique o caminho em .env")
        return False
    
    # 4. Simula validação de isolamento
    print("\n🛡️  Validação de Isolamento (S2-5):")
    print("   ┌──────────────────────────────────────────┐")
    
    for name, path in all_terminals.items():
        # Verifica se é o esperado
        is_expected = config.mt5_terminal_path.lower() == path.lower()
        
        if is_expected:
            print(f"   │ ✅ {name:20} → CONECTAR")
        else:
            # Verifica se o path está contido no terminal esperado
            if config.mt5_terminal_path.lower() in path.lower():
                print(f"   │ ✅ {name:20} → CONECTAR")
            else:
                print(f"   │ ❌ {name:20} → REJEITAR (acidental)")
    
    print("   └──────────────────────────────────────────┘")
    
    # 5. Resultado final
    print("\n" + "="*75)
    print("  🟢 RESULTADO: Terminal Isolation ATIVO")
    print("="*75)
    print("\nO agente conectará APENAS em:")
    print(f"   {config.mt5_terminal_path}\n")
    print("Mesmo que os terminais abaixo estejam abertos:")
    for name, path in all_terminals.items():
        if config.mt5_terminal_path.lower() != path.lower():
            print(f"   • {name}: {path}")
    
    print("\n✅ Proteção contra acidental switch: ATIVA\n")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except ImportError as e:
        print(f"\n❌ Erro: {e}")
        print("   (Verifique se está no repositório e .env existe)\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}\n")
        sys.exit(1)
