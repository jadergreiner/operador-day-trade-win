"""
ML Expert Tasks - Relative Imports Fixer

Ajusta importações relativas para buscar config na pasta correta.
Executa antes de rodar backtest.
"""

import sys
import os
from pathlib import Path

# CORRECAO: Adicionar diretorio raiz PRIMEIRO
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Depois adicionar src
src_path = root_dir / "src"
sys.path.insert(0, str(src_path))

print(f"[DEBUG] Root dir: {root_dir}")
print(f"[DEBUG] Src path: {src_path}")
print(f"[DEBUG] Python path: {sys.path[:3]}")
print()

# Agora os imports devem funcionar
try:
    from infrastructure.config.alerta_config import get_config, load_config
    print("[OK] Importacoes carregadas com sucesso!")
    print()
    
    config = get_config()
    print(f"[OK] Configuracao carregada: {config}")
    print(f"   - Window: {config.detection.volatilidade.window}")
    print(f"   - Threshold Sigma: {config.detection.volatilidade.threshold_sigma}")
    print(f"   - Confirmacao Velas: {config.detection.volatilidade.confirmacao_velas}")
    print()
    print("[OK] TUDO FUNCIONANDO PERFEITAMENTE!")
except ModuleNotFoundError as e:
    print(f"[ERRO] Problema ao importar: {e}")
    print()
    print("Passos para corrigir:")
    print("1. Verificar se pasta 'src' existe: src/infrastructure/config/alerta_config.py")
    print("2. Executar com PYTHONPATH: PYTHONPATH=. python scripts/test_imports.py")
    print("3. Ou instalar pacote em modo development: pip install -e .")
    sys.exit(1)
