"""
ML Expert Tasks - Relative Imports Fixer

Ajusta importações relativas para buscar config na pasta correta.
Executa antes de rodar backtest.
"""

import sys
from pathlib import Path

# Adicionar src ao path
src_path = Path(__file__).parent / ".." / "src"
sys.path.insert(0, str(src_path.absolute()))

# Agora os imports devem funcionar
from infrastructure.config.alerta_config import get_config, load_config

config = get_config()
print(f"✅ Configuração carregada: {config}")
print(f"   - Window: {config.detection.volatilidade.window}")
print(f"   - Threshold Sigma: {config.detection.volatilidade.threshold_sigma}")
print(f"   - Confirmação Velas: {config.detection.volatilidade.confirmacao_velas}")
