#!/usr/bin/env python3
"""
Wrapper de supervisão para agente RL.
Captura TUDO - exceptions, erros, warnings, etc.

Args:
    --sl-tp-mode: 'dinamico' ou 'fixo' (padrão: dinamico)
"""

import sys
# TRACE PRECOCE: escreve antes de qualquer otra importacao
import os as _os, time as _time
try:
    _trace_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'outputs')
    _os.makedirs(_trace_dir, exist_ok=True)
    with open(_os.path.join(_trace_dir, 'startup_trace.txt'), 'a', encoding='utf-8') as _tf:
        _tf.write(f"[STARTUP] {_time.strftime('%Y-%m-%d %H:%M:%S')} PID={_os.getpid()} argv={sys.argv}\n")
except Exception:
    pass
import os
import threading
import time
import signal
import traceback
from pathlib import Path
import logging

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


def _resolve_launcher_db_path(default_name: str, env_var: str) -> Path:
    """Resolve banco isolado para este launcher, com override explícito opcional."""
    override = os.getenv(env_var, "").strip()
    if override:
        return Path(override).expanduser()
    return ROOT_DIR / "data" / "db" / default_name


AGENTE_DB_PATH = _resolve_launcher_db_path(
    "trading_rl_5000.db",
    "RL5000_DB_PATH",
)
os.environ["RL5000_DB_PATH"] = str(AGENTE_DB_PATH)
os.environ["DB_PATH"] = str(AGENTE_DB_PATH)
os.environ["TRADING_DB_PATH"] = str(AGENTE_DB_PATH)

# Remover argumentos personalizados antes de importar script agente
sys.argv = [sys.argv[0]]

from src.infrastructure.monitoring.heartbeat_monitor import (
    HeartbeatLoggingHandler,
    HeartbeatMonitor,
)

# Passar modo via variável de ambiente
os.environ['AGENTE_SL_TP_MODE'] = SL_TP_MODE

HEARTBEAT_CHECK_INTERVAL_SECONDS = 5
HEARTBEAT_TIMEOUT_SECONDS = 360
heartbeat_monitor = HeartbeatMonitor(timeout_seconds=HEARTBEAT_TIMEOUT_SECONDS)
monitor_stop_event = threading.Event()

# Redirecionar stderr para capturar tudo
class DualWriter:
    """Escreve em arquivo e console simultaneamente."""
    def __init__(self, console, file_handle, heartbeat):
        self.console = console
        self.file_handle = file_handle
        self.heartbeat = heartbeat

    def write(self, msg):
        if msg.strip():
            self.heartbeat.touch()
        self.console.write(msg)
        self.file_handle.write(msg)
        self.file_handle.flush()

    def flush(self):
        self.console.flush()
        self.file_handle.flush()

# Abrir arquivo de log (modo append para preservar histórico entre sessões)
log_file = open(os.path.join(ROOT_DIR, 'outputs', 'agente_supervision.log'), 'a', encoding='utf-8')
log_file.write(f"\n{'='*80}\n")
log_file.write(f"NOVA SESSAO: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
log_file.write(f"{'='*80}\n")
log_file.flush()
sys.stdout = DualWriter(sys.__stdout__, log_file, heartbeat_monitor)
sys.stderr = DualWriter(sys.__stderr__, log_file, heartbeat_monitor)

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(ROOT_DIR, 'outputs', 'agente_debug.log'), mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logging.getLogger().addHandler(HeartbeatLoggingHandler(heartbeat_monitor))

logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info("INICIANDO AGENTE COM SUPERVISAO COMPLETA")
logger.info("=" * 80)
logger.info(f"Working Directory: {os.getcwd()}")
logger.info(f"ROOT_DIR: {ROOT_DIR}")
logger.info(f"Time: {time.time()}")

def monitor_thread():
    """Thread de monitoramento que checa se processo está vivo."""
    while not monitor_stop_event.wait(HEARTBEAT_CHECK_INTERVAL_SECONDS):
        elapsed = heartbeat_monitor.elapsed()

        if elapsed > HEARTBEAT_TIMEOUT_SECONDS:
            logger.warning(f"[MONITOR] Sem heartbeat por {elapsed:.0f}s - processo pode estar travado!")
        else:
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

OPERATIONAL_EXIT_CODES = {0, 10, 11}

try:
    logger.info("[INIT] Importando agente...")

    # Wrapper ao redor do import para capturar erros
    try:
        from scripts.operar_novo_agente_rl_real_antiovertrading import main
        logger.info("[INIT] Importação bem-sucedida!")
    except Exception as e:
        logger.error(f"[INIT] ERRO ao importar: {e}", exc_info=True)
        raise

    logger.info("[INIT] Bootstrap canonico carregado. Iniciando runtime completo...")
    logger.info("=" * 80)

    # Executar loop principal com supervisão
    try:
        exit_code = main()
        if exit_code in OPERATIONAL_EXIT_CODES:
            if exit_code == 0:
                logger.info("[MAIN] Runtime RL 5000 encerrado normalmente")
            elif exit_code == 10:
                logger.info("[MAIN] Runtime RL 5000 encerrado por meta diaria atingida")
            elif exit_code == 11:
                logger.warning("[MAIN] Runtime RL 5000 encerrado por stop loss diario")
            if exit_code != 0:
                raise SystemExit(exit_code)
        else:
            logger.error(f"[MAIN] Runtime RL 5000 encerrou com código {exit_code}")
            raise SystemExit(exit_code)
    except KeyboardInterrupt:
        logger.info("[MAIN] Interrompido pelo usuário (Ctrl+C)")
    except Exception as e:
        logger.critical(f"[MAIN] ERRO dentro do loop: {e}", exc_info=True)
        raise

except Exception as e:
    logger.critical(f"[FATAL] Erro fatal: {e}", exc_info=True)
    sys.exit(1)

finally:
    monitor_stop_event.set()
    monitor.join(timeout=2)

    logger.info("=" * 80)
    logger.info("ENCERRANDO AGENTE COM SUPERVISAO")
    logger.info("=" * 80)

    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        try:
            handler.flush()
            handler.close()
        except Exception:
            pass

    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    log_file.close()
