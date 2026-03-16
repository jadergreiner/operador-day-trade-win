#!/usr/bin/env python3
"""Debug avancado: Capta erro exato onde agente tranca/fecha."""

import sys
import os
from pathlib import Path

# Setup path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

# Setup logging COM Unicode
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/debug_agente_exato.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def debug_imports():
    """Testa imports um por um."""
    logger.info("=" * 70)
    logger.info("DEBUG: TESTANDO IMPORTS")
    logger.info("=" * 70)

    imports_to_test = [
        ("MT5Adapter", "from src.infrastructure.adapters.mt5_adapter import MT5Adapter"),
        ("Symbol", "from src.domain.value_objects.financial import Symbol, Price, Quantity"),
        ("Order", "from src.domain.entities.trade import Order"),
        ("OrderSide", "from src.domain.enums.trading_enums import OrderSide, TimeFrame, OrderType"),
        ("PipelineTreinamentoRL", "from src.application.services.novo_agente.pipeline_treinamento import PipelineTreinamentoRL"),
        ("SqliteRLRepository", "from src.infrastructure.repositories.rl_repository import SqliteRLRepository"),
        ("get_session", "from src.infrastructure.database.schema import get_session"),
        ("TradingConfig", "from config.settings import TradingConfig"),
    ]

    for name, import_stmt in imports_to_test:
        try:
            logger.info(f"[IMPORT] Testando: {name}...")
            exec(import_stmt)
            logger.info(f"         [OK] {name} importado")
        except Exception as e:
            logger.error(f"         [ERRO] {name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    logger.info("[SUCESSO] Todos os imports passaram\n")
    return True


def debug_initialize():
    """Tenta inicializar o agente passo a passo."""
    logger.info("=" * 70)
    logger.info("DEBUG: INICIALIZANDO AGENTE")
    logger.info("=" * 70)

    try:
        from src.application.services.novo_agente.pipeline_treinamento import PipelineTreinamentoRL
        from config.settings import TradingConfig

        logger.info("[PASSO 1] Carregando configuracao...")
        config = TradingConfig()
        logger.info(f"         [OK] Config criada")

        logger.info("[PASSO 2] Criando pipeline...")
        pipeline = PipelineTreinamentoRL(
            config_ambiente=None,
            config_agente=None,
            diretorio_modelos=ROOT_DIR / "data" / "models" / "novo_agente_rl",
            semente=42,
        )
        logger.info(f"         [OK] Pipeline criado")

        logger.info("[PASSO 3] Carregando modelo...")
        caminho_modelo = ROOT_DIR / "data" / "models" / "novo_agente_rl" / "modelo_final"
        logger.info(f"         Caminho: {caminho_modelo}")
        logger.info(f"         Existe: {caminho_modelo.exists()}")

        if not caminho_modelo.exists():
            logger.error(f"         [ERRO] Caminho nao existe!")
            return False

        pipeline.carregar_modelo("modelo_final")
        logger.info(f"         [OK] Modelo carregado")

        logger.info("[SUCESSO] Agente inicializado com sucesso\n")
        return True

    except Exception as e:
        logger.error(f"[ERRO] Erro ao inicializar agente: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Main."""
    logger.info("INICIANDO DEBUG DO AGENTE RL v5000")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"ROOT_DIR: {ROOT_DIR}")
    logger.info("")

    # Teste 1: Imports
    if not debug_imports():
        logger.error("[FATAL] Imports falharam")
        return False

    # Teste 2: Inicializacao
    if not debug_initialize():
        logger.error("[FATAL] Inicializacao falhou")
        return False

    logger.info("=" * 70)
    logger.info("DEBUG COMPLETO - PRONTO PARA EXECUTAR")
    logger.info("=" * 70)
    logger.info("\nProximo passo: Executar INICIAR_AGENTE_RL_5000.bat ou:")
    logger.info("  python scripts/operar_novo_agente_rl_real_antiovertrading.py")

    return True


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
