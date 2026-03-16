#!/usr/bin/env python3
"""Wrapper para debug: Mostra onde agente tranca."""

import sys
import os
import signal
from pathlib import Path
from threading import Thread
import time

# Setup path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Contador de tempo
last_log_time = time.time()
log_message = ""

def monitor_timeout():
    """Monitor que checa se script está travado."""
    global last_log_time, log_message

    while True:
        time.sleep(2)  # Check a cada 2 segundos
        elapsed = time.time() - last_log_time

        if elapsed > 10:
            logger.error(f"[TIMEOUT] Script travado por {elapsed:.0f}s!")
            logger.error(f"           Ultima acao: {log_message}")
            logger.error(f"           PID: {os.getpid()}")

            # Usar Ctrl+C para sair
            os.kill(os.getpid(), signal.SIGINT)


def patched_main():
    """Versão patchada do main que loga cada passo."""
    from src.application.services.novo_agente.pipeline_treinamento import PipelineTreinamentoRL
    from src.infrastructure.adapters.mt5_adapter import MT5Adapter
    from src.infrastructure.repositories.rl_repository import SqliteRLRepository
    from src.infrastructure.database.schema import get_session
    from config.settings import TradingConfig

    global last_log_time, log_message

    # Log de cada passo
    def log_step(msg):
        global last_log_time, log_message
        logger.info(msg)
        last_log_time = time.time()
        log_message = msg

    try:
        log_step("[1] Inicializando adaptador MT5...")
        config = TradingConfig()
        mt5_adapter = MT5Adapter(
            login=config.mt5_login,
            password=config.mt5_password,
            server=config.mt5_server,
            terminal_exe_path=config.mt5_terminal_path,
        )

        log_step("[2] Conectando no MT5...")
        if not mt5_adapter.connect():
            log_step("[!] Falha ao conectar no MT5 - isso pode causar travamento")
            logger.warning("Continuando mesmo com falha (para debug)...")
        else:
            log_step("[OK] MT5 conectado")

        log_step("[3] Carregando agente RL...")
        pipeline = PipelineTreinamentoRL()
        from src.application.services.novo_agente.agente_q_learning import AgenteQLearningMiniIndice
        pipeline._agente = AgenteQLearningMiniIndice(
            tamanho_estado=15,
            n_acoes=3,
            config=pipeline.config_agente
        )

        log_step("[4] Carregando modelo...")
        caminho_modelo = ROOT_DIR / "data/models/novo_agente_rl/modelo_final"
        pipeline._agente.carregar(caminho_modelo)
        log_step("[OK] Modelo carregado")

        log_step("[5] Inicializando RL Repository...")
        db_path = str(ROOT_DIR / "data" / "db" / "trading.db")
        session = get_session(db_path)
        rl_repo = SqliteRLRepository(session)
        log_step("[OK] RL Repository pronto")

        log_step("[6] Verificando dados de mercado...")
        # Tentar carregar dados do MT5
        try:
            from src.domain.value_objects import Symbol
            from src.domain.enums.trading_enums import TimeFrame
            candles = mt5_adapter.get_candles(Symbol("WIN$N"), TimeFrame.M1, 100)
            if candles is not None and len(candles) > 0:
                log_step(f"    [OK] {len(candles)} candles carregados")
            else:
                log_step(f"    [!] Nenhum candle retornado (MT5 pode estar desconectado)")
        except Exception as e:
            log_step(f"    [!] Erro ao carregar dados: {e}")

        log_step("\n[SUCESSO] Inicializacao completa!")
        logger.info("Agente esta pronto. Travamento nao é na inicializacao.")

        # Teste de saldo
        log_step("[7] Tentando obter saldo da conta...")
        try:
            balance = mt5_adapter.get_account_balance()
            if balance:
                logger.info(f"         Saldo: R${balance:.2f}")
            else:
                logger.warning("         [!] get_account_balance() retornou None")
        except Exception as e:
            logger.error(f"         [!] Erro: {e}")

        log_step("\n[CONCLUSAO] Se travamento ocorre APOS este ponto, e no loop principal!")

    except KeyboardInterrupt:
        logger.info("\n[STOP] Interrompido pelo usuario")
    except Exception as e:
        logger.error(f"[ERRO] {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    # Iniciar thread de monitor
    monitor_thread = Thread(target=monitor_timeout, daemon=True)
    monitor_thread.start()

    # Executar main
    patched_main()
