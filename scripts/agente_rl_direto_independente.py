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
    from src.application.trade_tracker_integration import TradeTrackerIntegration
    from src.application.trade_performance_tracker import TradeClosureReason
    from src.domain.enums.trading_enums import TimeFrame
    from src.application.motor_decisao_isolado import (
        MotorDecisaoIsolado,
        TipoPosicao,
        MotivoFechamento,
    )
    from src.application.posicao_isolamento import PosicaoIsoladaManager

    logger.info('[OK] Módulos importados com sucesso (incl. isolamento formal)')

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
MAGIC_NUMBER = 234600  # EA ID exclusivo do agente direto (isolamento)

# SL/TP fixos — mas nunca abaixo do ATR minimo calculado em tempo real.
# Regra: SL = max(SL_FIXO, ATR_14 * ATR_MULT_SL)
#         TP = max(TP_FIXO, SL_efetivo * RR_MINIMO)
STOP_LOSS_PONTOS = 150          # piso fixo (pts)
TAKE_PROFIT_PONTOS = 225        # piso fixo (pts) — mantém R/R 1.5:1 mínimo
ATR_PERIODO = 14                # velas M5 para calcular ATR
ATR_MULT_SL = 0.8               # SL >= 80% do ATR — nunca menor que o ruído
RR_MINIMO = 1.5                 # TP sempre >= SL * 1.5

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


def calcular_atr(dados: pd.DataFrame, periodo: int = ATR_PERIODO) -> float:
    """Calcula ATR (Average True Range) das ultimas `periodo` velas M5.

    Retorna 0.0 se dados insuficientes — o chamador deve usar o piso fixo.
    """
    try:
        if len(dados) < periodo + 1:
            return 0.0
        high = dados['high']
        low = dados['low']
        close_ant = dados['close'].shift(1)
        tr = pd.concat([
            high - low,
            (high - close_ant).abs(),
            (low - close_ant).abs(),
        ], axis=1).max(axis=1)
        return float(tr.rolling(periodo).mean().iloc[-1])
    except Exception as e:
        logger.warning(f'[ATR] Erro ao calcular ATR: {e}')
        return 0.0


def calcular_sl_tp(acao: str, preco_atual: float,
                   dados: Optional[pd.DataFrame] = None) -> Tuple[float, float]:
    """Calcula SL/TP fixos respeitando ATR minimo.

    Regras:
      - SL efetivo = max(STOP_LOSS_PONTOS, ATR_14 * ATR_MULT_SL)
      - TP efetivo = max(TAKE_PROFIT_PONTOS, SL_efetivo * RR_MINIMO)
    Garante que o SL nunca seja menor que o ruido de mercado (ATR).
    """
    atr = calcular_atr(dados) if dados is not None else 0.0
    atr_sl_minimo = round(atr * ATR_MULT_SL)

    sl_pts = max(STOP_LOSS_PONTOS, atr_sl_minimo)
    tp_pts = max(TAKE_PROFIT_PONTOS, round(sl_pts * RR_MINIMO))

    if atr > 0:
        logger.info(
            f'[SL/TP] ATR={atr:.0f}pts | '
            f'SL={sl_pts}pts (piso={STOP_LOSS_PONTOS}, atr_min={atr_sl_minimo}) | '
            f'TP={tp_pts}pts | R/R={tp_pts/sl_pts:.2f}:1'
        )
    else:
        logger.debug(f'[SL/TP] ATR indisponivel — usando piso fixo SL={sl_pts} TP={tp_pts}')

    if acao == "Comprar":
        sl = preco_atual - sl_pts
        tp = preco_atual + tp_pts
    elif acao == "Vender":
        sl = preco_atual + sl_pts
        tp = preco_atual - tp_pts
    else:
        sl = tp = preco_atual

    return sl, tp


def enviar_ordem(mt5_adapter: object, acao: str, preco_atual: float,
                 posicao_tracker: object, rl_repo: object, trade_tracker: object,
                 dados: Optional[pd.DataFrame] = None) -> bool:
    """Envia ordem para abrir posição no MT5."""
    global last_trade_time

    if acao == "Aguardar":
        return False

    try:
        # ══════════════════════════════════════════════════════════════
        # GUARDA CRÍTICA: Verificar no MT5 se já existe posição aberta
        # deste agente (por magic number). Evita ordens duplicadas
        # causadas por race condition entre JSON e estado real do MT5.
        # ══════════════════════════════════════════════════════════════
        try:
            posicoes_mt5 = mt5_adapter.get_positions(Symbol(SIMBOLO))
            minhas_posicoes = [
                p for p in (posicoes_mt5 or [])
                if int(getattr(p, 'magic', 0) or 0) == MAGIC_NUMBER
            ]
            if minhas_posicoes:
                tickets = [int(getattr(p, 'ticket', 0)) for p in minhas_posicoes]
                logger.warning(
                    f'[GUARDA] BLOQUEADO: Já existe(m) {len(minhas_posicoes)} '
                    f'posição(ões) aberta(s) com magic={MAGIC_NUMBER} '
                    f'(tickets={tickets}). Ordem NÃO enviada.'
                )
                return False
        except Exception as e:
            logger.warning(f'[GUARDA] Erro ao verificar posições MT5: {e}. '
                          f'Prosseguindo com cautela.')

        # Mapear ação para OrderSide
        if acao == "Comprar":
            side = OrderSide.BUY
            direcao_str = "BUY"
        elif acao == "Vender":
            side = OrderSide.SELL
            direcao_str = "SELL"
        else:
            return False

        # Calcular SL/TP respeitando ATR minimo
        sl, tp = calcular_sl_tp(acao, preco_atual, dados)

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
            magic_number=MAGIC_NUMBER,
            execution_method="automated",
        )

        ticket = mt5_adapter.send_order(order)
        if ticket:
            logger.info(f'[OK] Ordem enviada! Ticket: {ticket}')

            # Registrar posição via módulos formais de isolamento
            posicao_tracker.registrar_posicao_aberta(
                preco_entrada=preco_atual,
                ticket=int(ticket),
                lado=direcao_str,
                quantidade=1,
            )
            tipo = TipoPosicao.COMPRADA if direcao_str == 'BUY' else TipoPosicao.VENDIDA
            motor_decisao.abrir_posicao(
                ticket=int(ticket),
                tipo=tipo,
                preco_entrada=preco_atual,
                volume=1.0,
                stop_loss=sl,
                take_profit=tp,
            )
            logger.info(
                f'[ISOLAMENTO] Ticket {ticket} registrado via '
                f'MotorDecisaoIsolado + PosicaoIsoladaManager'
            )

            # Registrar entrada no rastreador de performance
            if trade_tracker:
                try:
                    trade_tracker.registrar_entrada(
                        ticket=ticket,
                        simbolo=SIMBOLO,
                        direcao=direcao_str,
                        preco_entrada=preco_atual,
                    )
                    logger.info(f'[TRACKER] Entrada registrada para ticket {ticket}')
                except Exception as e:
                    logger.warning(f'[WARN] Erro ao registrar entrada no tracker: {e}')

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

        # 6. Anti-Overtrading Protection
        logger.info('[INIT] Inicializando proteção contra overtrading...')
        anti_overtrading = AntiOvertradingProtection(
            max_trades_per_hour=3,           # Máximo 3 trades por hora
            min_cooldown_seconds=300,        # Mínimo 5 min entre trades
            max_consecutive_losses=2,        # 2 perdas seguidas = pausa
            trading_hours_start=9,           # Operação: 9h-16h
            trading_hours_end=16,
        )
        logger.info('[OK] Anti-Overtrading ativado')

        # 7. Trade Performance Tracker - Rastreamento de P&L
        logger.info('[INIT] Inicializando rastreador de performance de trades...')
        trade_tracker = TradeTrackerIntegration(
            session_id=AGENT_SESSION_ID,
            output_dir=OUTPUTS_DIR,
        )
        logger.info('[OK] Trade Performance Tracker ativado')

        logger.info('[OK] Todos os componentes inicializados com sucesso!')
        logger.info('')

        return {
            'config': config,
            'mt5_adapter': mt5_adapter,
            'rl_repo': rl_repo,
            'pipeline': pipeline,
            'agente': agente,
            'profit_protection': profit_protection,
            'anti_overtrading': anti_overtrading,
            'trade_tracker': trade_tracker,
        }

    except Exception as e:
        logger.error(f'[FATAL] Erro ao inicializar componentes: {e}', exc_info=True)
        return None

# ============================================================================
# PROTEÇÃO CONTRA OVERTRADING
# ============================================================================
class AntiOvertradingProtection:
    """Proteção contra overtrading com limites de frequência e risco."""

    def __init__(self, max_trades_per_hour: int = 3, min_cooldown_seconds: int = 300,
                 max_consecutive_losses: int = 2, trading_hours_start: int = 9,
                 trading_hours_end: int = 16):
        self.max_trades_per_hour = max_trades_per_hour
        self.min_cooldown_seconds = min_cooldown_seconds
        self.max_consecutive_losses = max_consecutive_losses
        self.trading_hours_start = trading_hours_start
        self.trading_hours_end = trading_hours_end

        self.trades_this_hour = []
        self.last_trade_time = None
        self.consecutive_losses = 0
        self.is_in_cooldown = False
        self.cooldown_until = None

    def pode_tradear(self) -> tuple[bool, str]:
        """Verifica se é permitido fazer um novo trade. Retorna (permitido, motivo)."""
        from datetime import datetime, timedelta

        now = datetime.now()

        # 1. Verificar horário de operação
        if now.hour < self.trading_hours_start or now.hour >= self.trading_hours_end:
            return False, f"❌ Fora do horário de operação ({self.trading_hours_start}h-{self.trading_hours_end}h)"

        # 2. Verificar cooldown global
        if self.is_in_cooldown and self.cooldown_until and now < self.cooldown_until:
            remaining = (self.cooldown_until - now).total_seconds()
            return False, f"❌ Em cooldown global ({remaining:.0f}s restantes)"
        else:
            self.is_in_cooldown = False
            self.cooldown_until = None

        # 3. Verificar limite de trades por hora
        one_hour_ago = now - timedelta(hours=1)
        self.trades_this_hour = [t for t in self.trades_this_hour if t > one_hour_ago]

        if len(self.trades_this_hour) >= self.max_trades_per_hour:
            return False, f"❌ Limite de {self.max_trades_per_hour} trades/hora atingido ({len(self.trades_this_hour)}/{self.max_trades_per_hour})"

        # 4. Verificar cooldown mínimo entre trades
        if self.last_trade_time:
            seconds_since_last = (now - self.last_trade_time).total_seconds()
            if seconds_since_last < self.min_cooldown_seconds:
                return False, f"❌ Cooldown mínimo: {self.min_cooldown_seconds}s (apenas {seconds_since_last:.0f}s se passaram)"

        # 5. Verificar perdas consecutivas
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False, f"❌ {self.max_consecutive_losses} perdas consecutivas - pausando operações"

        return True, "✅ Permitido tradear"

    def registrar_trade(self):
        """Registra que um novo trade foi aberto."""
        self.trades_this_hour.append(datetime.now())
        self.last_trade_time = datetime.now()
        logger.info(f"[ANTIOVERTRADING] Trade #{len(self.trades_this_hour)} registrado nesta hora")

    def registrar_perda(self):
        """Registra uma perda e incrementa contador consecutivo."""
        self.consecutive_losses += 1
        logger.warning(f"[ANTIOVERTRADING] ⚠️  Perda registrada ({self.consecutive_losses}/{self.max_consecutive_losses})")

        if self.consecutive_losses >= self.max_consecutive_losses:
            # Activar cooldown de 30 minutos após max perdas consecutivas
            self.is_in_cooldown = True
            self.cooldown_until = datetime.now() + timedelta(minutes=30)
            logger.warning(f"[ANTIOVERTRADING] 🛑 Cooldown de 30min ativado após {self.max_consecutive_losses} perdas")

    def registrar_ganho(self):
        """Registra um ganho e reseta contador de perdas consecutivas."""
        self.consecutive_losses = 0
        logger.info(f"[ANTIOVERTRADING] ✅ Ganho registrado - contador de perdas resetado")

# ============================================================================
# RASTREAMENTO DE POSIÇÕES — Usa módulos formais de isolamento
# (PosicaoIsoladaManager + MotorDecisaoIsolado de src/application/)
# ============================================================================


def verificar_posicao_no_mt5(posicao_mgr: PosicaoIsoladaManager,
                              motor: MotorDecisaoIsolado,
                              mt5_adapter_local) -> bool:
    """Consulta MT5 pelo ticket p/ verificar se posição ainda existe.

    Retorna True se posição AINDA aberta. False caso contrário.
    """
    if not posicao_mgr.tem_posicao_aberta():
        return False

    posicoes = motor.obter_posicoes_abertas()
    if not posicoes:
        return False

    ticket = posicoes[0].ticket  # 1 posição por agente
    try:
        positions = mt5_adapter_local.get_positions(Symbol(SIMBOLO))
        for pos in positions:
            pos_ticket = int(getattr(pos, 'ticket', 0) or 0)
            pos_magic = int(getattr(pos, 'magic', 0) or 0)
            if pos_ticket == ticket and pos_magic == MAGIC_NUMBER:
                preco_atual = float(getattr(pos, 'price_current', 0))
                motor.atualizar_posicao(ticket, preco_atual)
                logger.debug(
                    f'[MT5-CHECK] Ticket {ticket} CONFIRMADO aberto '
                    f'(magic={pos_magic}, profit={getattr(pos, "profit", 0):.2f})'
                )
                return True

        # Não encontrado → fechado por SL/TP/manual
        logger.info(
            f'[MT5-CHECK] Ticket {ticket} NAO encontrado no MT5. '
            f'Posição FECHADA (SL/TP ou manual).'
        )
        return False
    except Exception as e:
        logger.warning(f'[MT5-CHECK] Erro ao consultar MT5: {e}')
        return posicao_mgr.tem_posicao_aberta()

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
    anti_overtrading = componentes['anti_overtrading']  # 🛑 CRITICAL: Proteção contra overtrading
    trade_tracker = componentes['trade_tracker']  # 📊 Rastreamento de performance

    # Inicializar módulos formais de isolamento
    posicao_tracker = PosicaoIsoladaManager(
        session_id=AGENT_SESSION_ID,
        agent_version='rl_direto_v3.0',
        outputs_dir=OUTPUTS_DIR,
    )
    motor_decisao = MotorDecisaoIsolado(
        agent_id=AGENT_SESSION_ID,
        data_dir=OUTPUTS_DIR,
    )
    logger.info(
        f'[ISOLAMENTO] PosicaoIsoladaManager + MotorDecisaoIsolado '
        f'inicializados para session {AGENT_SESSION_ID}'
    )

    logger.info('=' * 80)
    logger.info('INICIANDO LOOP OPERACIONAL COM RL')
    logger.info('=' * 80)
    logger.info(f"Target: R${TARGET_PROFIT:.2f} | Stop Loss: R${STOP_LOSS_MAX:.2f}")
    logger.info(f"SL/TP Mode: {AGENT_MODE.upper()}")
    logger.info(f"Session: {AGENT_SESSION_ID}")
    logger.info(f"Isolamento: MotorDecisaoIsolado + PosicaoIsoladaManager")
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
                posicao_tracker._carregar_status()
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

                # 2. Se JSON diz posição aberta, verificar no MT5 pelo ticket
                if posicao_tracker.tem_posicao_aberta():
                    ainda_aberta = verificar_posicao_no_mt5(
                        posicao_tracker, motor_decisao, mt5_adapter,
                    )

                    if not ainda_aberta:
                        # Obter dados da posição do motor antes de fechar
                        posicoes_motor = motor_decisao.obter_posicoes_abertas()
                        ticket_aberto = posicoes_motor[0].ticket if posicoes_motor else None
                        preco_entrada_reg = posicoes_motor[0].preco_entrada if posicoes_motor else None
                        tipo_reg = posicoes_motor[0].tipo if posicoes_motor else None

                        logger.info(
                            f'[CICLO {ciclo}] Posição ticket={ticket_aberto} '
                            f'FECHADA no MT5 (SL/TP ou manual)'
                        )

                        # Determinar resultado (win/loss) pelo preço atual vs entrada
                        resultado = 'DESCONHECIDO'
                        pnl_estimado = 0.0
                        if preco_entrada_reg and tipo_reg:
                            diff = preco_atual - preco_entrada_reg
                            if tipo_reg == TipoPosicao.VENDIDA:
                                diff = -diff
                            resultado = 'WIN' if diff > 0 else 'LOSS'
                            pnl_estimado = diff * 0.20  # mini-índice: R$ 0.20/ponto

                        # Atualizar anti-overtrading
                        if resultado == 'LOSS':
                            anti_overtrading.registrar_perda()
                        elif resultado == 'WIN':
                            anti_overtrading.registrar_ganho()

                        # Registrar saída no trade tracker
                        if trade_tracker and ticket_aberto:
                            try:
                                motivo = (
                                    TradeClosureReason.SL_HIT
                                    if resultado == 'LOSS'
                                    else TradeClosureReason.TP_HIT
                                )
                                trade_tracker.registrar_saida(
                                    ticket=ticket_aberto,
                                    preco_saida=preco_atual,
                                    motivo_fechamento=motivo,
                                )
                            except Exception as e:
                                logger.warning(f'[WARN] Erro ao registrar saída: {e}')

                        # Fechar posição nos módulos formais
                        if ticket_aberto:
                            motivo_motor = (
                                MotivoFechamento.SL_ATINGIDO
                                if resultado == 'LOSS'
                                else MotivoFechamento.TP_ATINGIDO
                            )
                            motor_decisao.fechar_posicao(
                                ticket_aberto, preco_atual, motivo_motor,
                            )
                        posicao_tracker.registrar_posicao_fechada()

                        logger.info(
                            f'[CICLO {ciclo}] Resultado: {resultado} | '
                            f'PnL estimado: R${pnl_estimado:.2f} | '
                            f'Pronto para próximo trade'
                        )
                        # Não fazer continue — deixar seguir para buscar novo sinal
                    else:
                        # Posição ainda aberta no MT5 — aguardar
                        posicoes_m = motor_decisao.obter_posicoes_abertas()
                        tk = posicoes_m[0].ticket if posicoes_m else '?'
                        logger.info(
                            f'[CICLO {ciclo}] Posição ticket={tk} '
                            f'AINDA ABERTA no MT5. Aguardando 15s...'
                        )
                        time.sleep(15)
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

                        # 4.5. 🛑 Verificar proteção contra overtrading
                        pode_tradear, motivo = anti_overtrading.pode_tradear()
                        logger.info(f'[CICLO {ciclo}] {motivo}')

                        if not pode_tradear:
                            logger.warning(f'[CICLO {ciclo}] Ordem BLOQUEADA pela proteção anti-overtrading')
                            time.sleep(5)
                            continue

                        # 5. Enviar ordem
                        if enviar_ordem(mt5_adapter, acao_str, preco_atual, posicao_tracker, rl_repo, trade_tracker, dados_df):
                            logger.info(f'[CICLO {ciclo}] Ordem aberta com sucesso!')
                            anti_overtrading.registrar_trade()  # 📝 Registrar trade na proteção
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

        # Gravar relatorio de performance de trades
        try:
            if trade_tracker:
                arquivo_relatorio = trade_tracker.gerar_relatorio_json()
                logger.info(f'[OK] Relatório de performance gravado: {arquivo_relatorio}')
                stats = trade_tracker.obter_estatisticas()
                logger.info(f'[STATS] Total trades: {stats.get("total_trades", 0)} | '
                           f'Win rate: {stats.get("win_rate", 0):.1f}% | '
                           f'PnL total: R$ {stats.get("pnl_total_reais", 0):.2f}')
        except Exception as e:
            logger.warning(f'[WARN] Erro ao gravar relatório: {e}')

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
