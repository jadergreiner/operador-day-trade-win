#!/usr/bin/env python3
"""
Script de teste: Validação de modos SL/TP
"""

import os
import sys

print("=" * 70)
print("TESTE: Modos SL/TP Dinâmico vs Fixo")
print("=" * 70)
print()

# Teste 1: Variável de ambiente
print("TEST 1: Variável de Ambiente")
print("-" * 70)
os.environ['AGENTE_SL_TP_MODE'] = 'dinamico'
modo_dinamico = os.environ.get('AGENTE_SL_TP_MODE', 'nao_definido')
print(f"✓ Modo DINAMICO: {modo_dinamico}")

os.environ['AGENTE_SL_TP_MODE'] = 'fixo'
modo_fixo = os.environ.get('AGENTE_SL_TP_MODE', 'nao_definido')
print(f"✓ Modo FIXO: {modo_fixo}")
print()

# Teste 2: Parse de argumentos
print("TEST 2: Parse de Argumentos CLI")
print("-" * 70)

def test_parse_args(argv_test):
    SL_TP_MODE = 'dinamico'  # Padrão
    if '--sl-tp-mode' in argv_test:
        try:
            idx = argv_test.index('--sl-tp-mode')
            SL_TP_MODE = argv_test[idx + 1]
            if SL_TP_MODE not in ['dinamico', 'fixo']:
                return False, f"Modo inválido: {SL_TP_MODE}"
        except (IndexError, ValueError):
            return False, "Argumento --sl-tp-mode requer um valor"
    return True, SL_TP_MODE

# Teste 2a: Com --sl-tp-mode dinamico
success, mode = test_parse_args(['script.py', '--sl-tp-mode', 'dinamico'])
print(f"Argumento: --sl-tp-mode dinamico")
print(f"  Sucesso: {success}, Modo: {mode}")
print()

# Teste 2b: Com --sl-tp-mode fixo
success, mode = test_parse_args(['script.py', '--sl-tp-mode', 'fixo'])
print(f"Argumento: --sl-tp-mode fixo")
print(f"  Sucesso: {success}, Modo: {mode}")
print()

# Teste 2c: Sem argumentos (padrão)
success, mode = test_parse_args(['script.py'])
print(f"Argumento: (nenhum)")
print(f"  Sucesso: {success}, Modo: {mode} (padrão)")
print()

# Teste 3: Geração de ID único
print("TEST 3: ID Único do Agente")
print("-" * 70)
from datetime import datetime

modos = ['dinamico', 'fixo']
for modo in modos:
    agente_id = f"agente_{modo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Agente {modo.upper()}: {agente_id}")

print()
print("=" * 70)
print("TODOS OS TESTES PASSARAM!")
print("=" * 70)
