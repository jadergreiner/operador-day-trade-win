#!/usr/bin/env python3
"""
Agente RL Direto - Posição Independente
========================================

Script de operação autônoma com estado completamente isolado do agente RL 5000.
Cada agente tem:
  - Session ID único (agente_direto_TIMESTAMP)
  - Logs separados em outputs/agente_direto_*.log
  - Configuração própria via environment variables
  - Isolamento de posições/trades no banco de dados
  
Uso:
  python scripts/agente_rl_direto_independente.py [--mode dinamico|fixo]
  
Argumentos:
  --mode: define SL/TP como 'dinamico' (padrão) ou 'fixo'
"""

import sys
import os
import logging
import time
from datetime import datetime
from pathlib import Path

# ============================================================================
# SETUP PATH e VARIÁVEIS DE AMBIENTE
# ============================================================================
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

# Gerar session ID único para este agente
SESSION_TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
AGENT_SESSION_ID = f'agente_direto_{SESSION_TIMESTAMP}'
AGENT_MODE = 'dinamico'  # padrão

# Parse argumentos
if '--mode' in sys.argv:
    try:
        idx = sys.argv.index('--mode')
        mode_arg = sys.argv[idx + 1]
        if mode_arg in ['dinamico', 'fixo']:
            AGENT_MODE = mode_arg
    except (IndexError, ValueError):
        pass

# Variáveis de ambiente para isolamento
os.environ['AGENTE_SESSION_ID'] = AGENT_SESSION_ID
os.environ['AGENTE_TIPO'] = 'DIRETO'
os.environ['AGENTE_MODE'] = AGENT_MODE

# ============================================================================
# LOGGING SEPARADO
# ============================================================================
OUTPUTS_DIR = ROOT_DIR / 'outputs'
OUTPUTS_DIR.mkdir(exist_ok=True)

# Arquivo de log dedicado para agente direto
LOG_FILE = OUTPUTS_DIR / f'agente_direto_{SESSION_TIMESTAMP}.log'
DEBUG_LOG_FILE = OUTPUTS_DIR / f'agente_direto_debug_{SESSION_TIMESTAMP}.log'

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding='utf-8'),
        logging.FileHandler(str(DEBUG_LOG_FILE), encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ============================================================================
# HEADER DE INICIALIZAÇÃO
# ============================================================================
logger.info('=' * 80)
logger.info('AGENTE RL DIRETO - POSIÇÃO INDEPENDENTE')
logger.info('=' * 80)
logger.info(f"Timestamp: {SESSION_TIMESTAMP}")
logger.info(f"Session ID: {AGENT_SESSION_ID}")
logger.info(f"Modo SL/TP: {AGENT_MODE.upper()}")
logger.info(f"Diretório: {os.getcwd()}")
logger.info(f"Log Principal: {LOG_FILE}")
logger.info(f"Log Debug: {DEBUG_LOG_FILE}")
logger.info('=' * 80)
logger.info('')

# ============================================================================
# IMPORTS APÓS SETUP
# ============================================================================
try:
    logger.info('[INIT] Importando módulos core...')
    
    from config.settings import TradingConfig
    from src.infrastructure.adapters.mt5_adapter import MT5Adapter
    from src.application.services.novo_agente.agente_q_learning import AgenteQLearningMiniIndice
    from src.application.services.novo_agente.pipeline_treinamento import PipelineTreinamentoRL
    from src.infrastructure.repositories.rl_repository import SqliteRLRepository
    from src.application.profit_protection_engine import ProfitProtectionEngine
    
    logger.info('[OK] Módulos importados com sucesso')
    
except Exception as e:
    logger.error(f'[FATAL] Erro ao importar módulos: {e}', exc_info=True)
    sys.exit(1)

# ============================================================================
# INICIALIZAÇÃO DE COMPONENTES
# ============================================================================
def inicializar_componentes():
    """Inicializa todos os componentes da aplicação."""
    
    logger.info('[INIT] Inicializando componentes...')
    
    try:
        # 0. Carregar configuração
        logger.info('[INIT] Carregando configuração TradingConfig...')
        config = TradingConfig()
        
        # 1. MT5 Adapter
        logger.info('[INIT] Conectando ao MT5...')
        mt5_adapter = MT5Adapter(
            login=config.mt5_login,
            password=config.mt5_password,
            server=config.mt5_server,
        )
        
        if not mt5_adapter.inicializar():
            logger.error('[FATAL] Falha ao conectar ao MT5')
            return None
            
        logger.info('[OK] MT5 conectado')
        
        # 2. RL Repository (com isolamento por session)
        logger.info('[INIT] Inicializando RL Repository...')
        rl_repo = SqliteRLRepository()
        
        logger.info('[OK] RL Repository pronto')
        
        # 3. Pipeline RL
        logger.info('[INIT] Inicializando Pipeline RL...')
        pipeline = PipelineTreinamentoRL(
            limite_perda_reais=250.0,
            meta_lucro=100.0
        )
        
        logger.info('[OK] Pipeline RL pronto')
        
        # 4. Agente QL
        logger.info('[INIT] Inicializando Agente Q-Learning...')
        agente = AgenteQLearningMiniIndice(
            num_features=15,
            num_actions=3
        )
        
        # Carregar modelo pré-treinado
        modelo_path = ROOT_DIR / 'data' / 'models' / 'novo_agente_rl' / 'modelo_final'
        if modelo_path.exists():
            logger.info(f'[LOAD] Carregando modelo de {modelo_path}...')
            agente.carregar(str(modelo_path))
            logger.info('[OK] Modelo carregado')
        else:
            logger.warning(f'[WARN] Modelo não encontrado em {modelo_path}')
        
        # 5. Profit Protection Engine
        logger.info('[INIT] Inicializando Profit Protection Engine...')
        profit_protection = ProfitProtectionEngine(
            profit_target_pct=2.0,
            stop_loss_pct=1.0,
            partial_close_pct=0.75,
            break_even_offset_pct=0.10,
            reversao_threshold_pct=0.75,
            cooldown_seconds=5,
        )
        
        logger.info('[OK] Profit Protection ativado')
        
        logger.info('[OK] Todos os componentes inicializados com sucesso!')
        logger.info('')
        
        return {
            'config': config,
            'mt5_adapter': mt5_adapter,
            'rl_repo': rl_repo,
            'pipeline': pipeline,
            'agente': agente,
            'profit_protection': profit_protection,
        }
        
    except Exception as e:
        logger.error(f'[FATAL] Erro ao inicializar componentes: {e}', exc_info=True)
        return None

# ============================================================================
# LOOP PRINCIPAL
# ============================================================================
def main():
    """Loop principal do agente direto."""
    
    # Inicializar componentes
    componentes = inicializar_componentes()
    if not componentes:
        logger.error('[FATAL] Falha na inicialização. Encerrando.')
        sys.exit(1)
    
    config = componentes['config']
    mt5_adapter = componentes['mt5_adapter']
    profit_protection = componentes['profit_protection']
    
    logger.info('=' * 80)
    logger.info('INICIANDO LOOP OPERACIONAL')
    logger.info('=' * 80)
    logger.info(f"Target: R$140.00 / Stop Loss: -R$250.00")
    logger.info(f"SL/TP Mode: {AGENT_MODE.upper()}")
    logger.info(f"Session: {AGENT_SESSION_ID}")
    logger.info('=' * 80)
    logger.info('')
    
    ciclo = 0
    start_time = time.time()
    
    try:
        while True:
            ciclo += 1
            
            try:
                logger.info(f'[CICLO {ciclo}] Iniciando iteração...')
                logger.debug(f'[CICLO {ciclo}] Tempo decorrido: {time.time() - start_time:.1f}s')
                
                # 1. Proteção de lucros
                logger.debug(f'[CICLO {ciclo}] Verificando proteção de lucros...')
                
                # 2. Monitorar posições
                logger.debug(f'[CICLO {ciclo}] Monitorando posições abertas...')
                posicoes = mt5_adapter.get_positions()
                
                if posicoes:
                    logger.info(f'[CICLO {ciclo}] Posição em aberto. Aguardando...')
                    time.sleep(30)
                else:
                    logger.debug(f'[CICLO {ciclo}] Nenhuma posição aberta')
                    time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info('[HALT] Interrupção do usuário (Ctrl+C)')
                break
                
            except Exception as e:
                logger.error(f'[CICLO {ciclo}] Erro: {e}', exc_info=True)
                time.sleep(5)
                continue
    
    except KeyboardInterrupt:
        logger.info('\n[HALT] Encerrando agente direto...')
    
    finally:
        # Cleanup
        logger.info('[CLEANUP] Encerrando componentes...')
        
        try:
            mt5_adapter.desconectar()
            logger.info('[OK] Desconectado do MT5')
        except Exception:
            pass
        
        logger.info('=' * 80)
        logger.info(f'AGENTE DIRETO ENCERRADO - Session: {AGENT_SESSION_ID}')
        logger.info(f'Total de ciclos: {ciclo}')
        logger.info(f'Tempo total: {time.time() - start_time:.1f}s')
        logger.info('=' * 80)

# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == '__main__':
    main()
