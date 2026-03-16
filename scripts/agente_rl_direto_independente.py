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
import json
import uuid
from datetime import datetime
from pathlib import Path
import pandas as pd
from typing import Optional, Tuple

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
    from src.infrastructure.database.schema import get_session
    from src.application.services.novo_agente.agente_q_learning import AgenteQLearningMiniIndice
    from src.application.services.novo_agente.pipeline_treinamento import PipelineTreinamentoRL
    from src.infrastructure.repositories.rl_repository import SqliteRLRepository
    from src.application.profit_protection_engine import ProfitProtectionEngine
    from src.domain.enums.trading_enums import TimeFrame

    logger.info('[OK] Módulos importados com sucesso')

except Exception as e:
    logger.error(f'[FATAL] Erro ao importar módulos: {e}', exc_info=True)
    sys.exit(1)

# ============================================================================
# IMPORTS SPECIFICIZADOS - Domain Models
# ============================================================================
try:
    from src.domain.value_objects import Symbol, Price, Quantity
    from src.domain.entities.trade import Order
    from src.domain.enums.trading_enums import OrderSide, OrderType, TimeFrame
    logger.info('[OK] Domain models importados')
except Exception as e:
    logger.error(f'[WARN] Domain models import falhou: {e}')
    Symbol = None
    TimeFrame = None
    OrderSide = None
    OrderType = None
    Order = None
    Price = None
    Quantity = None

# ============================================================================
# CONSTANTES DE TRADING
# ============================================================================
SIMBOLO = "WINJ26"
STOP_LOSS_PONTOS = 100
TAKE_PROFIT_PONTOS = 150
CONFIRM_SIGNAL_BARS = 2  # Confirmação em N velas
TARGET_PROFIT = 140.00
STOP_LOSS_MAX = -250.00

# Variáveis globais para estado do agente
last_signal = "Aguardar"
signal_confirmation_count = 0
last_trade_time = None

# ============================================================================
# FUNÇÕES DE DECISÃO E TRADING (RL)
# ============================================================================
def obter_acao_do_modelo(dados: pd.DataFrame, pipeline: object, agente: object) -> Tuple[int, float]:
    """Obtém ação do modelo RL treinado."""
    try:
        from src.application.services.novo_agente.ambiente_trading import AmbienteTradingMiniIndice

        if not isinstance(dados, pd.DataFrame) or len(dados) == 0:
            logger.debug('[RL] Dados insuficientes, retornando aguardar')
            return 0, 0.0  # Aguardar

        ambiente = AmbienteTradingMiniIndice(dados=dados)
        ambiente.reset()
        ambiente._indice = len(dados) - 1

        estado = ambiente._calcular_estado()
        acao_id = agente.selecionar_acao(estado)
        confidence = 0.7  # Placeholder

        logger.debug(f'[RL] Ação obtida: {acao_id} (confiança: {confidence:.2%})')
        return acao_id, confidence

    except Exception as e:
        logger.error(f'[RL] Erro ao obter ação: {e}')
        return 0, 0.0


def mapear_acao(acao_id: int) -> str:
    """Mapeia ID numérico para ação: 0=Aguardar, 1=Comprar, 2=Vender."""
    mapeamento = {0: "Aguardar", 1: "Comprar", 2: "Vender"}
    return mapeamento.get(acao_id, "Aguardar")


def verificar_confirmacao_sinal(sinal_atual: str, sinal_anterior: str) -> bool:
    """Verifica se o sinal se repete em múltiplas velas."""
    global signal_confirmation_count

    if sinal_atual == "Aguardar":
        signal_confirmation_count = 0
        return False

    if sinal_atual == sinal_anterior:
        signal_confirmation_count += 1
        logger.info(f'[OK] Sinal CONFIRMADO ({signal_confirmation_count}/{CONFIRM_SIGNAL_BARS})')
        return signal_confirmation_count >= CONFIRM_SIGNAL_BARS
    else:
        signal_confirmation_count = 1
        logger.info(f'[SINAL] Novo sinal detectado: {sinal_atual}')
        return False


def calcular_sl_tp(acao: str, preco_atual: float) -> Tuple[float, float]:
    """Calcula SL/TP baseado na ação."""
    if acao == "Comprar":
        sl = preco_atual - STOP_LOSS_PONTOS
        tp = preco_atual + TAKE_PROFIT_PONTOS
    elif acao == "Vender":
        sl = preco_atual + STOP_LOSS_PONTOS
        tp = preco_atual - TAKE_PROFIT_PONTOS
    else:
        sl = tp = preco_atual

    return sl, tp


def enviar_ordem(mt5_adapter: object, acao: str, preco_atual: float,
                 posicao_tracker: object, rl_repo: object) -> bool:
    """Envia ordem para abrir posição no MT5."""
    global last_trade_time

    if acao == "Aguardar":
        return False

    try:
        # Mapear ação para OrderSide
        if acao == "Comprar":
            side = OrderSide.BUY
        elif acao == "Vender":
            side = OrderSide.SELL
        else:
            return False

        # Calcular SL/TP
        sl, tp = calcular_sl_tp(acao, preco_atual)

        logger.info(f'[ENVIO] {acao} @ {preco_atual} | SL: {sl} | TP: {tp}')

        # Criar e enviar ordem (usar Symbol se disponível)
        try:
            symbol_obj = Symbol(SIMBOLO)
        except:
            symbol_obj = SIMBOLO  # Fallback para string

        order = Order(
            symbol=symbol_obj,
            side=side,  # BUY ou SELL
            quantity=Quantity(1),  # 1 contrato
            order_type=OrderType.MARKET,  # Ordem de mercado
            stop_loss=Price(sl),  # 🔴 CRITICAL: Stop Loss obrigatório
            take_profit=Price(tp),
            execution_method="automated",
        )

        ticket = mt5_adapter.send_order(order)
        if ticket:
            logger.info(f'[OK] Ordem enviada! Ticket: {ticket}')

            # Registrar posição no rastreador
            posicao_tracker.registrar_posicao_aberta()

            # Persistir no RL Repository
            if rl_repo:
                try:
                    episode_id = str(uuid.uuid4())
                    episode = {
                        "episode_id": episode_id,
                        "timestamp": datetime.now(),
                        "source": "AGENTE_DIRETO",
                        "win_price": preco_atual,
                        "action": acao.upper(),
                        "symbol": SIMBOLO,
                    }
                    rl_repo.save_episode(episode)
                except Exception as e:
                    logger.warning(f'[WARN] Erro ao persistir episódio: {e}')

            last_trade_time = datetime.now()
            return True
        else:
            logger.error(f'[ERRO] Falha ao enviar ordem')
            return False

    except Exception as e:
        logger.error(f'[ERRO] Exceção ao enviar ordem: {e}', exc_info=True)
        return False

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

        # 1. MT5 Adapter - usar caminho do .env (Clear Investimentos)
        logger.info('[INIT] Conectando ao MT5...')

        mt5_adapter = MT5Adapter(
            login=config.mt5_login,
            password=config.mt5_password,
            server=config.mt5_server,
            terminal_exe_path=config.mt5_terminal_path,  # Do .env: Clear
        )

        if not mt5_adapter.connect():
            logger.error('[FATAL] Falha ao conectar ao MT5')
            return None

        logger.info('[OK] MT5 conectado')

        # 2. RL Repository (com isolamento por session)
        logger.info('[INIT] Inicializando RL Repository...')
        db_path = str(ROOT_DIR / 'data' / 'db' / 'trading.db')
        session = get_session(db_path)
        rl_repo = SqliteRLRepository(session)
        rl_repo.seed_dimension_tables()

        logger.info('[OK] RL Repository pronto')

        # 3. Pipeline RL
        logger.info('[INIT] Inicializando Pipeline RL...')
        pipeline = PipelineTreinamentoRL()

        logger.info('[OK] Pipeline RL pronto')

        # 4. Agente QL
        logger.info('[INIT] Inicializando Agente Q-Learning...')
        pipeline._agente = AgenteQLearningMiniIndice(
            tamanho_estado=15,
            n_acoes=3,
            config=pipeline.config_agente
        )

        # Carregar modelo pré-treinado
        modelo_path = ROOT_DIR / 'data' / 'models' / 'novo_agente_rl' / 'modelo_final'
        if (modelo_path / 'q_network.pkl').exists():
            logger.info(f'[LOAD] Carregando modelo de {modelo_path}...')
            pipeline._agente.carregar(modelo_path)
            logger.info('[OK] Modelo carregado')
        else:
            logger.warning(f'[WARN] Modelo não encontrado em {modelo_path}')

        agente = pipeline._agente

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
# RASTREAMENTO DE POSIÇÕES POR SESSION
# ============================================================================
class AgentePosicaoStatus:
    """Rastreador de posições isolado por session ID do agente."""

    def __init__(self, session_id: str, data_dir: Path):
        self.session_id = session_id
        self.status_file = data_dir / f'agente_posicao_{session_id}.json'
        self.posicao_aberta = False
        self.posicao_open_time = None
        self.carregar_status()

    def carregar_status(self):
        """Carrega status de posição anterior se existir."""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.posicao_aberta = data.get('aberta', False)
                    self.posicao_open_time = data.get('open_time')
                    if self.posicao_aberta:
                        logger.debug(f'[STATUS] ✅ Posição ABERTA detectada (open_time: {self.posicao_open_time})')
                    else:
                        logger.debug(f'[STATUS] ✅ Nenhuma posição aberta')
            else:
                self.posicao_aberta = False
                self.posicao_open_time = None
                logger.debug(f'[STATUS] Arquivo não existe: {self.status_file}')
        except Exception as e:
            logger.warning(f'[WARN] Erro ao carregar status: {e}')

    def registrar_posicao_aberta(self):
        """Registra que uma posição foi aberta por ESTE agente."""
        self.posicao_aberta = True
        self.posicao_open_time = datetime.now().isoformat()

        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'session_id': self.session_id,
                    'aberta': True,
                    'open_time': self.posicao_open_time,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)
            logger.info(f'[REGISTRO] ✅ Posição aberta REGISTRADA: {self.status_file}')
        except Exception as e:
            logger.error(f'[ERRO] Falha ao registrar posição: {e}')

    def registrar_posicao_fechada(self):
        """Registra que a posição foi fechada por ESTE agente."""
        self.posicao_aberta = False
        self.posicao_open_time = None

        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'session_id': self.session_id,
                    'aberta': False,
                    'open_time': None,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)
            logger.info(f'[REGISTRO] Posição fechada registrada para session {self.session_id}')
        except Exception as e:
            logger.error(f'[ERRO] Falha ao registrar fechamento: {e}')

    def tem_posicao_aberta(self) -> bool:
        """Retorna True se ESTE agente tem uma posição aberta."""
        return self.posicao_aberta

# ============================================================================
# LOOP PRINCIPAL
# ============================================================================
def main():
    """Loop principal do agente direto com lógica de RL."""
    global last_signal

    # Inicializar componentes
    componentes = inicializar_componentes()
    if not componentes:
        logger.error('[FATAL] Falha na inicialização. Encerrando.')
        sys.exit(1)

    config = componentes['config']
    mt5_adapter = componentes['mt5_adapter']
    pipeline = componentes['pipeline']
    agente = componentes['agente']
    profit_protection = componentes['profit_protection']
    rl_repo = componentes['rl_repo']

    # Inicializar rastreador de posições deste agente
    posicao_tracker = AgentePosicaoStatus(AGENT_SESSION_ID, OUTPUTS_DIR)

    logger.info('=' * 80)
    logger.info('INICIANDO LOOP OPERACIONAL COM RL')
    logger.info('=' * 80)
    logger.info(f"Target: R${TARGET_PROFIT:.2f} | Stop Loss: R${STOP_LOSS_MAX:.2f}")
    logger.info(f"SL/TP Mode: {AGENT_MODE.upper()}")
    logger.info(f"Session: {AGENT_SESSION_ID}")
    logger.info(f"Isolamento de posições: ATIVADO")
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

                # 🔴 CRITICAL: Recarregar status de posição do arquivo a cada ciclo
                posicao_tracker.carregar_status()
                logger.debug(f'[CICLO {ciclo}] Status posição recarregado: {posicao_tracker.tem_posicao_aberta()}')

                # Verificar conexão MT5 antes de cada ciclo
                if not mt5_adapter.is_connected():
                    logger.warning(f'[CICLO {ciclo}] Detectada perda de conexão MT5, tentando reconectar...')
                    if not mt5_adapter.connect():
                        logger.error(f'[CICLO {ciclo}] Falha ao reconectar ao MT5')
                        time.sleep(5)
                        continue
                    logger.info(f'[CICLO {ciclo}] MT5 reconectado com sucesso')

                # 1. Carregar dados de mercado (últimas 100 velas M5 para contexto RL)
                try:
                    if Symbol is None or TimeFrame is None:
                        logger.debug('[CICLO] Domain models não estão disponíveis')
                        time.sleep(5)
                        continue

                    # Usar padrão correto: Symbol(string), TimeFrame.M5, count=100
                    candles_raw = mt5_adapter.get_candles(Symbol(SIMBOLO), TimeFrame.M5, 100)

                    if candles_raw is None or len(candles_raw) == 0:
                        logger.debug('[CICLO] Aguardando dados de mercado (MT5 pode estar offline)...')
                        time.sleep(5)
                        continue

                    # Converter lista de Candle objects para DataFrame para RL environment
                    dados_df = pd.DataFrame({
                        'open': [c.open.value for c in candles_raw],
                        'high': [c.high.value for c in candles_raw],
                        'low': [c.low.value for c in candles_raw],
                        'close': [c.close.value for c in candles_raw],
                        'volume': [c.volume for c in candles_raw],
                    })

                    # Preço atual vem do último candle
                    preco_atual = float(candles_raw[-1].close.value)
                    logger.debug(f'[CICLO {ciclo}] Preço atual: {preco_atual} | Velas disponíveis: {len(dados_df)}')

                except Exception as e:
                    logger.warning(f'[CICLO {ciclo}] Erro ao obter dados: {e}')
                    time.sleep(5)
                    continue

                # 2. Proteção de lucros (se tem posição)
                if posicao_tracker.tem_posicao_aberta():
                    logger.info(f'[CICLO {ciclo}] ⏸️  Posição DESTE AGENTE em aberto. Aguardando 60s antes de próxima operação...')
                    logger.debug(f'[CICLO {ciclo}] Open time: {posicao_tracker.posicao_open_time}')
                    # TODO: Integrar profit_protection aqui
                    time.sleep(60)  # 🔴 Aumentado de 30s para 60s para garantir uma ordem por vez
                    continue

                # 3. Se sem posição, tentar obter ação do RL
                logger.debug(f'[CICLO {ciclo}] Verificando oportunidade de entrada...')

                try:
                    acao_id, confidence = obter_acao_do_modelo(dados_df, pipeline, agente)
                    acao_str = mapear_acao(acao_id)

                    logger.debug(f'[CICLO {ciclo}] Ação RL: {acao_str} (confiança: {confidence:.2%})')

                except Exception as e:
                    logger.warning(f'[CICLO {ciclo}] Erro ao obter ação RL: {e}')
                    acao_str = "Aguardar"

                # 4. Validar confirmação do sinal
                if acao_str != "Aguardar":
                    confirmado = verificar_confirmacao_sinal(acao_str, last_signal)

                    if confirmado:
                        logger.info(f'[CICLO {ciclo}] SINAL CONFIRMADO: {acao_str}')

                        # 5. Enviar ordem
                        if enviar_ordem(mt5_adapter, acao_str, preco_atual, posicao_tracker, rl_repo):
                            logger.info(f'[CICLO {ciclo}] Ordem aberta com sucesso!')
                            last_signal = acao_str
                            time.sleep(5)
                            continue
                    else:
                        last_signal = acao_str
                        logger.debug(f'[SINAL] Aguardando confirmação: {acao_str}')
                else:
                    signal_confirmation_count = 0
                    last_signal = "Aguardar"

                # Default: aguardar
                logger.debug(f'[CICLO {ciclo}] Aguardando...')
                time.sleep(5)

            except KeyboardInterrupt:
                logger.info('[HALT] Interrupção do usuário (Ctrl+C)')
                break

            except Exception as e:
                logger.error(f'[CICLO {ciclo}] Erro inesperado: {e}', exc_info=True)

                # Tentar reconectar se a conexão caiu
                try:
                    if not mt5_adapter.is_connected():
                        logger.warning('[RECONEXAO] Detectada perda de conexão MT5, tentando reconectar...')
                        if mt5_adapter.connect():
                            logger.info('[RECONEXAO] MT5 reconectado com sucesso')
                        else:
                            logger.error('[RECONEXAO] Falha ao reconectar')
                except:
                    pass

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
