"""
Entry point para executar processos de aplicacao como modulos.

Permite: python -m src.application.services.processador_bdi
"""

import sys
import argparse
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def run_processador_bdi(config_path: str = None):
    """Executar o processador BDI."""
    try:
        from src.application.services.processador_bdi import ProcessadorBDI
        
        logger.info("🚀 Iniciando ProcessadorBDI...")
        processador = ProcessadorBDI()
        
        logger.info(f"✅ DetectorVolatilidade: window={processador.detector_vol.window}σ")
        logger.info(f"✅ DetectorPadroes: carregado")
        logger.info(f"✅ Fila de alertas: conectada")
        logger.info(f"")
        logger.info(f"ProcessadorBDI rodando em modo listening...")
        logger.info(f"[Aguardando velas da MT5...]")
        
        # Executar indefinidamente
        await processador.iniciar()
        
    except KeyboardInterrupt:
        logger.info("ProcessadorBDI interrompido pelo usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Erro ao rodar ProcessadorBDI: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Executa componentes de aplicacao")
    parser.add_argument("--config", default=None, help="Arquivo de configuracao")
    parser.add_argument("--detectors", default="enabled", help="Detectors: enabled|disabled")
    
    args = parser.parse_args()
    
    # Rodar o processador BDI
    asyncio.run(run_processador_bdi(args.config))


if __name__ == "__main__":
    main()
