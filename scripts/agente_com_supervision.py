#!/usr/bin/env python3
"""
Wrapper de supervisão para agente RL.
Captura TUDO - exceptions, erros, warnings, etc.

Args:
    --sl-tp-mode: 'dinamico' ou 'fixo' (padrão: dinamico)
"""

import sys
import os
import threading
import time
import signal
import traceback
from pathlib import Path

# Parse argumentos ANTES de limpar sys.argv
SL_TP_MODE = 'dinamico'  # Padrão
if '--sl-tp-mode' in sys.argv:
    try:
        idx = sys.argv.index('--sl-tp-mode')
        SL_TP_MODE = sys.argv[idx + 1]
        if SL_TP_MODE not in ['dinamico', 'fixo']:
            print(f"[ERRO] Modo invalido: {SL_TP_MODE}. Use 'dinamico' ou 'fixo'.")
            sys.exit(1)
    except (IndexError, ValueError):
        print("[ERRO] Argumento --sl-tp-mode requer um valor")
        sys.exit(1)

# Setup path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

# Remover argumentos personalizados antes de importar script agente
sys.argv = [sys.argv[0]]

import logging
from io import StringIO

# Passar modo via variável de ambiente
os.environ['AGENTE_SL_TP_MODE'] = SL_TP_MODE

# Redirecionar stderr para capturar tudo
class DualWriter:
    """Escreve em arquivo e console simultaneamente."""
    def __init__(self, console, file_handle):
        self.console = console
        self.file_handle = file_handle

    def write(self, msg):
        self.console.write(msg)
        self.file_handle.write(msg)
        self.file_handle.flush()

    def flush(self):
        self.console.flush()
        self.file_handle.flush()

# Abrir arquivo de log
log_file = open(os.path.join(ROOT_DIR, 'outputs', 'agente_supervision.log'), 'w', encoding='utf-8')
sys.stdout = DualWriter(sys.__stdout__, log_file)
sys.stderr = DualWriter(sys.__stderr__, log_file)

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(ROOT_DIR, 'outputs', 'agente_debug.log'), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("INICIANDO AGENTE COM SUPERVISAO COMPLETA")
logger.info("=" * 80)
logger.info(f"Working Directory: {os.getcwd()}")
logger.info(f"ROOT_DIR: {ROOT_DIR}")
logger.info(f"Time: {time.time()}")

def monitor_thread():
    """Thread de monitoramento que checa se processo está vivo."""
    last_heartbeat = time.time()

    while True:
        time.sleep(5)
        now = time.time()
        elapsed = now - last_heartbeat

        if elapsed > 60:
            logger.warning(f"[MONITOR] Sem heartbeat por {elapsed:.0f}s - processo pode estar travado!")

        logger.debug(f"[MONITOR] Heartbeat OK (elapsed: {elapsed:.1f}s)")

# Iniciar thread de monitoramento
monitor = threading.Thread(target=monitor_thread, daemon=True)
monitor.start()
logger.info("[MONITOR] Thread de monitoramento iniciada")

def custom_excepthook(exc_type, exc_value, exc_traceback):
    """Captura todas as exceções não tratadas."""
    logger.critical("=" * 80)
    logger.critical("EXCEÇÃO NÃO TRATADA DETECTADA!")
    logger.critical("=" * 80)
    logger.critical(f"Tipo: {exc_type.__name__}")
    logger.critical(f"Mensagem: {exc_value}")
    logger.critical("Traceback:")
    logger.critical(''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
    logger.critical("=" * 80)

    # Chamar handler padrão
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = custom_excepthook

# Função para signal handler
def signal_handler(sig, frame):
    logger.warning(f"[SIGNAL] Sinal {sig} recebido - encerrando...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

logger.info("[INIT] Handlers de sinal configurados")

try:
    logger.info("[INIT] Importando agente...")

    # Wrapper ao redor do import para capturar erros
    try:
        from scripts.operar_novo_agente_rl_real_antiovertrading import (
            inicializar_adaptador_mt5,
            inicializar_agente_rl,
            inicializar_rl_repo,
            loop_operacao
        )
        logger.info("[INIT] Importação bem-sucedida!")
    except Exception as e:
        logger.error(f"[INIT] ERRO ao importar: {e}", exc_info=True)
        raise

    logger.info("[INIT] Inicializando adaptador MT5...")
    try:
        inicializar_adaptador_mt5()
        logger.info("[INIT] MT5 inicializado com sucesso!")
    except Exception as e:
        logger.error(f"[INIT] ERRO ao inicializar MT5: {e}", exc_info=True)
        raise

    logger.info("[INIT] Inicializando agente RL...")
    try:
        inicializar_agente_rl()
        logger.info("[INIT] Agente RL inicializado com sucesso!")
    except Exception as e:
        logger.error(f"[INIT] ERRO ao inicializar agente RL: {e}", exc_info=True)
        raise

    logger.info("[INIT] Inicializando RL Repository...")
    try:
        inicializar_rl_repo()
        logger.info("[INIT] RL Repository inicializado com sucesso!")
    except Exception as e:
        logger.error(f"[INIT] ERRO ao inicializar RL Repository: {e}", exc_info=True)
        raise

    logger.info("[INIT] Todas as inicializações concluídas! Iniciando loop...")
    logger.info("=" * 80)

    # Executar loop principal com supervisão
    try:
        loop_operacao()
        logger.info("[MAIN] Loop operacao encerrado normalmente")
    except KeyboardInterrupt:
        logger.info("[MAIN] Interrompido pelo usuário (Ctrl+C)")
    except Exception as e:
        logger.critical(f"[MAIN] ERRO dentro do loop: {e}", exc_info=True)
        raise

except Exception as e:
    logger.critical(f"[FATAL] Erro fatal: {e}", exc_info=True)
    sys.exit(1)

finally:
    logger.info("=" * 80)
    logger.info("ENCERRANDO AGENTE COM SUPERVISAO")
    logger.info("=" * 80)
    log_file.close()
