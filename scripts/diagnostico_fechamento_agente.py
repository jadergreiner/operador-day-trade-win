#!/usr/bin/env python3
"""Diagnostico: Identifica por que o agente RL fecha inesperadamente."""

import sys
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Adicionar path do projeto
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Setup logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

log_file = log_dir / f"diagnostico_fechamento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_environment() -> bool:
    """Testa ambiente antes de executar agente."""
    logger.info("=" * 70)
    logger.info("DIAGNOSTICO: AMBIENTE DO AGENTE RL v5000")
    logger.info("=" * 70)

    # 1. Verificar modelo
    model_path = Path("operador-day-trade-win/data/models/novo_agente_rl/modelo_final/q_network.pkl")
    logger.info(f"\n[1] Verificando modelo...")
    if model_path.exists():
        size_kb = model_path.stat().st_size / 1024
        logger.info(f"    [OK] Modelo encontrado: {model_path}")
        logger.info(f"    [SIZE] Tamanho: {size_kb:.1f} KB")
    else:
        logger.error(f"    [ERRO] Modelo NAO encontrado: {model_path}")
        return False

    # 2. Verificar MT5
    logger.info(f"\n[2] Verificando MT5Adapter...")
    try:
        from src.infrastructure.adapters.mt5_adapter import MT5Adapter
        logger.info(f"    [OK] MT5Adapter importado com sucesso")
    except Exception as e:
        logger.error(f"    [ERRO] Erro ao importar MT5Adapter: {e}")
        return False

    # 3. Verificar Pipeline RL
    logger.info(f"\n[3] Verificando Pipeline RL...")
    try:
        from src.application.services.novo_agente.pipeline_treinamento import PipelineTreinamentoRL
        logger.info(f"    [OK] PipelineTreinamentoRL importado com sucesso")
    except Exception as e:
        logger.error(f"    [ERRO] Erro ao importar PipelineTreinamentoRL: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    # 4. Verificar script principal
    logger.info(f"\n[4] Verificando script principal...")
    script_path = Path("operador-day-trade-win/scripts/operar_novo_agente_rl_real_antiovertrading.py")
    if script_path.exists():
        logger.info(f"    [OK] Script encontrado: {script_path}")
    else:
        logger.error(f"    [ERRO] Script NAO encontrado: {script_path}")
        return False

    logger.info(f"\n[SUCESSO] Ambiente OK - Pronto para executar agente")
    return True


def run_agent_with_capture() -> bool:
    """Executa agente capturando qualquer erro."""
    logger.info("\n" + "=" * 70)
    logger.info("EXECUTANDO AGENTE RL v5000")
    logger.info("=" * 70 + "\n")

    try:
        # Executar script do operador
        result = subprocess.run(
            [
                sys.executable,
                "operador-day-trade-win/scripts/operar_novo_agente_rl_real_antiovertrading.py"
            ],
            capture_output=True,
            text=True,
            timeout=60
        )

        # Capturar output
        if result.stdout:
            logger.info("[STDOUT]\n" + result.stdout)

        if result.stderr:
            logger.error("[STDERR]\n" + result.stderr)

        # Verificar código de saída
        if result.returncode != 0:
            logger.error(f"\n[ERRO] Script retornou codigo: {result.returncode}")
            return False

        logger.info(f"\n[SUCESSO] Script executado com sucesso")
        return True

    except subprocess.TimeoutExpired:
        logger.error("[ERRO] Script timeout (excedeu 60 segundos)")
        return False
    except Exception as e:
        logger.error(f"[ERRO] Erro ao executar script: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Main."""
    # Teste ambiente
    if not test_environment():
        logger.error("\n❌ Ambiente com problemas - não é seguro executar agente")
        logger.info(f"\n📋 Log salvo em: {log_file}")
        return False

    # Executar agente
    sucesso = run_agent_with_capture()

    logger.info(f"\n{'='*70}")
    logger.info(f"DIAGNOSTICO COMPLETO - Status: {'SUCESSO' if sucesso else 'ERRO'}")
    logger.info(f"{'='*70}")
    logger.info(f"\n[LOG] Salvo em: {log_file}")

    return sucesso


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
