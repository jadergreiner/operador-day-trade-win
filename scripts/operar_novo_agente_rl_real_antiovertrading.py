#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Operador RL v5000 com ANTI-OVERTRADING FILTERS
- Limit operações por sessão
- Cooldown entre trades
- Filtro de volatilidade/volume
- Confirmação multi-vela
Status: PRODUCTION (v5000-SAFE)
Data: 06/03/2026
"""

import logging
import os
import sys
import time
from pathlib import Path
from datetime import datetime, time as dtime, timedelta
from typing import Optional
import pandas as pd

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.domain.value_objects.financial import Symbol, Price, Quantity
from src.domain.entities.trade import Order
from src.domain.enums.trading_enums import OrderSide, TimeFrame, OrderType
from src.application.services.novo_agente.pipeline_treinamento import PipelineTreinamentoRL
from src.infrastructure.repositories.rl_repository import SqliteRLRepository
from src.infrastructure.database.schema import get_session
from src.application.profit_protection_engine import (
    ProfitProtectionEngine,
    ProfitProtectionResult,
)
from src.application.motor_decisao_isolado import (
    MotorDecisaoIsolado,
    TipoPosicao,
    MotivoFechamento,
)
try:
    from src.application.ac5_8_position_monitor import (
        MonitorPositionManager,
        StatusOrdem,
        DirecaoOperacao,
    )
    AC5_8_DISPONIVEL = True
except ImportError:
    AC5_8_DISPONIVEL = False
    MonitorPositionManager = None  # type: ignore[assignment,misc]

# Imports opcionais — Grupo 2: AC5.9/AC6 (feedback e aprendizado)
_AC5_9_DISPONIVEL = False
_AC6_DISPONIVEL = False
try:
    from src.application.ac5_9_feedback_validator import FeedbackValidator
    from src.application.ac6_7_drift_detector import DriftDetector
    from src.application.ac6_8_online_learning import OnlineLearningController
    from src.application.ac6_9_baseline_comparator import BaselineComparator
    _AC5_9_DISPONIVEL = True
    _AC6_DISPONIVEL = True
except ImportError as _e:
    FeedbackValidator = None  # type: ignore[assignment,misc]
    DriftDetector = None  # type: ignore[assignment,misc]
    OnlineLearningController = None  # type: ignore[assignment,misc]
    BaselineComparator = None  # type: ignore[assignment,misc]
from config.settings import TradingConfig
import uuid

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(ROOT_DIR / 'outputs' / 'operar_agente_rl_antiovertrading.log'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# ANTI-OVERTRADING CONFIGURATION
# ============================================================================

class AntiOvertradingConfig:
    """Configurações de proteção contra overtrading - BALANCED MODE.

    BALANCED Mode:
    - Sem limite de trades/dia
    - Aguarda fechamento de candle
    - Volatilidade mínima antes de entrada
    - Continua até atingir TARGET ou STOP LOSS
    """

    # [OK] ATIVO: Filtros BALANCED (sem limite diário)
    COOLDOWN_SECONDS = 300              # 5 minutos entre trades (evita impulsos)
    MIN_VOLATILITY_PERCENT = 0.05       # Mínimo 0.05% volatilidade para operar
    CONFIRM_SIGNAL_BARS = 2             # Esperar 2 velas confirmando sinal

    # [X] DESATIVADO: Limites diários e horários
    # MAX_TRADES_PER_SESSION = Ilimitado (operadora até target/stop loss)
    # MAX_TRADES_PER_HOUR = Ilimitado (apenas cooldown entre trades)

    # Qualidade mínima
    MIN_VOLUME = 1000                   # Volume mínimo
    MIN_CONFIDENCE_SCORE = 0.65         # Confiança mínima do modelo
    MIN_TICKET_PROFIT = 10.0            # Não faz trade se RR < 1:2

# ============================================================================
# GLOBAL STATE
# ============================================================================

SIMBOLO = "WIN$N"
TARGET_LUCRO_DIARIO = 140.00
STOP_PERDA_DIARIA = -250.00
STOP_LOSS_PONTOS = 150
TAKE_PROFIT_PONTOS = 300
MAGIC_NUMBER = 234500

# Modo de calculo SL/TP (dinamico ou fixo)
SL_TP_MODE = os.getenv('AGENTE_SL_TP_MODE', 'dinamico').lower()
if SL_TP_MODE not in ['dinamico', 'fixo']:
    SL_TP_MODE = 'dinamico'

# ID unico para este agente (para controlar posicoes em paralelo)
AGENTE_ID = f"agente_{SL_TP_MODE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Motor de decisao isolado — substitui tickets_proprios (set) inline
# Persistencia file-based: posicoes_ativas_{AGENTE_ID}.json
motor_isolado = MotorDecisaoIsolado(
    agent_id=AGENTE_ID,
    data_dir=Path(__file__).parent.parent / 'outputs',
)

logger.info(f"Modo SL/TP: {SL_TP_MODE.upper()}")
logger.info(f"ID do Agente: {AGENTE_ID}")
logger.info(f"Motor Isolado: MotorDecisaoIsolado({AGENTE_ID})")

config = TradingConfig()
mt5_adapter: Optional[MT5Adapter] = None
pipeline: Optional[PipelineTreinamentoRL] = None
rl_repo: Optional[SqliteRLRepository] = None

# Profit Protection Engine (proteção dinâmica de lucros)
profit_protection_engine = ProfitProtectionEngine(
    profit_target_pct=2.0,
    stop_loss_pct=1.0,
    partial_close_pct=0.75,
    break_even_offset_pct=0.10,
    reversao_threshold_pct=0.75,
    cooldown_seconds=5,
)
logger.info("Motor de proteção de lucros ativado (P1-PROFIT_PROTECTION)")

# Anti-overtrading state
trades_executed_today = 0
last_trade_time: Optional[datetime] = None
trades_by_hour = {}  # {hour: count}
last_signal: Optional[str] = None
signal_confirmation_count = 0
ultimo_registro_progresso: Optional[datetime] = None  # Para registrar a cada 5 min

# Variaveis globais — Grupo 2: Feedback e Aprendizado (AC5.9/AC6)
_feedback_validator_rl: Optional[object] = None
_drift_detector_rl: Optional[object] = None
_online_learning_rl: Optional[object] = None
_baseline_comparator_rl: Optional[object] = None
_trades_fechados_rl: list = []  # Acumulador para pipeline AC5.9/AC6


def inicializar_adaptador_mt5() -> MT5Adapter:
    """Inicializa MT5Adapter."""
    global mt5_adapter

    mt5_adapter = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
        terminal_exe_path=config.mt5_terminal_path,
    )

    if not mt5_adapter.connect():
        raise RuntimeError("Falha ao conectar no MT5")

    logger.info(f"[OK] MT5 conectado: {config.mt5_server}")
    return mt5_adapter


def inicializar_agente_rl() -> PipelineTreinamentoRL:
    """Carrega agente RL v5000."""
    global pipeline

    pipeline = PipelineTreinamentoRL()

    from src.application.services.novo_agente.agente_q_learning import AgenteQLearningMiniIndice

    pipeline._agente = AgenteQLearningMiniIndice(
        tamanho_estado=15,
        n_acoes=3,
        config=pipeline.config_agente
    )

    caminho_modelo = ROOT_DIR / "data/models/novo_agente_rl/modelo_final"
    if (caminho_modelo / "q_network.pkl").exists():
        logger.info(f"Carregando modelo: {caminho_modelo}")
        pipeline._agente.carregar(caminho_modelo)
        logger.info("[OK] Modelo RL pronto")
    else:
        raise RuntimeError(f"Modelo não encontrado")

    return pipeline


def inicializar_rl_repo():
    """Inicializa repositório RL com retry logic."""
    global rl_repo
    db_path = str(ROOT_DIR / "data" / "db" / "trading.db")
    max_retries = 3
    retry_delay = 2

    for tentativa in range(max_retries):
        try:
            logger.info(f"[DB] Conectando RL repo (tentativa {tentativa+1}/{max_retries})...")
            session = get_session(db_path)
            rl_repo = SqliteRLRepository(session)
            rl_repo.seed_dimension_tables()
            logger.info("[OK] RL Repository pronto")
            return rl_repo
        except Exception as e:
            logger.warning(f"[!] Tentativa {tentativa+1} falhou: {str(e)[:100]}")
            if tentativa < max_retries - 1:
                logger.info(f"[Wait] Aguardando {retry_delay}s antes de tentar novamente...")
                time.sleep(retry_delay)
            else:
                logger.error(f"[ERRO] Falha na inicialização RL após {max_retries} tentativas")
                return None


def verificar_horario_trading() -> bool:
    """Horário de trading: 09:00-17:55 BRT."""
    agora = datetime.now().time()
    abertura = dtime(9, 0)
    fechamento = dtime(17, 55)
    return abertura <= agora <= fechamento


def carregar_dados_mt5(simbolo: str, n_candles: int = 100) -> Optional[pd.DataFrame]:
    """Carrega candles via MT5Adapter."""
    try:
        candles = mt5_adapter.get_candles(Symbol(simbolo), TimeFrame.M5, n_candles)
        if not candles or len(candles) < 20:
            return None

        data = pd.DataFrame([
            {
                'time': c.timestamp,
                'open': c.open.value,
                'high': c.high.value,
                'low': c.low.value,
                'close': c.close.value,
                'volume': c.volume,
            }
            for c in candles
        ])

        return data

    except Exception as e:
        logger.error(f"Erro ao carregar dados: {e}")
        return None


def calcular_volatilidade(dados: pd.DataFrame) -> float:
    """Calcula volatilidade percentual das últimas 5 velas."""
    if len(dados) < 5:
        return 0.0

    recent = dados.tail(5)
    high = recent['high'].max()
    low = recent['low'].min()
    volatilidade = ((high - low) / low) * 100
    return volatilidade


def obter_acao_do_modelo(dados: pd.DataFrame) -> tuple[int, float]:
    """
    Extrai ação do modelo RL.
    Retorna (action_id, confidence_score)
    """
    try:
        from src.application.services.novo_agente.ambiente_trading import AmbienteTradingMiniIndice

        ambiente = AmbienteTradingMiniIndice(dados=dados)
        ambiente.reset()
        ambiente._indice = len(dados) - 1

        estado = ambiente._calcular_estado()
        acao_id = pipeline._agente.selecionar_acao(estado)

        # Simular confidence score (0-1) baseado no Q-value
        confidence = 0.7  # TODO: extrair do Q-network

        return acao_id, confidence

    except Exception as e:
        logger.error(f"Erro ao obter ação: {e}")
        return 0, 0.0


def verificar_cooldown() -> bool:
    """
    Verifica se passou o cooldown mínimo entre trades.
    Retorna True se pode fazer trade.
    """
    global last_trade_time

    if last_trade_time is None:
        return True

    elapsed = (datetime.now() - last_trade_time).total_seconds()

    if elapsed < AntiOvertradingConfig.COOLDOWN_SECONDS:
        minutos = (AntiOvertradingConfig.COOLDOWN_SECONDS - elapsed) / 60
        logger.warning(f"⏱️  Cooldown ativo. Aguarde {minutos:.1f} min...")
        return False

    return True


def verificar_limite_trades() -> bool:
    """
    MODO BALANCED: Sem limite de trades!
    Apenas aguarda cooldown e volatilidade mínima.
    Continua operando até atingir TARGET ou STOP LOSS.

    Retorna sempre True (nenhum limite aplicado).
    """
    # [OK] BALANCED: Sem limites diários/horários
    # Operará livremente enquanto:
    # - Houver volatilidade mínima (0.05%)
    # - Respeitar cooldown entre trades (300s)
    # - Sinal estiver confirmado (2 velas)
    return True


def verificar_volatilidade(vol: float) -> bool:
    """
    Verifica se volatilidade está acima do mínimo.
    Retorna True se pode fazer trade.
    """
    if vol < AntiOvertradingConfig.MIN_VOLATILITY_PERCENT:
        logger.info(f"❄️  Mercado MUY estável ({vol:.4f}%). Aguardando volatilidade...")
        return False

    return True


def verificar_confirmacao_sinal(sinal_atual: str, sinal_anterior: str) -> bool:
    """
    Verifica se o sinal se repete (confirmação multi-vela).
    Retorna True se sinal é confirmado.
    """
    global signal_confirmation_count

    if sinal_atual == "Aguardar":
        signal_confirmation_count = 0
        return False

    if sinal_atual == sinal_anterior:
        signal_confirmation_count += 1
        logger.info(f"[OK] Sinal CONFIRMADO ({signal_confirmation_count}/{AntiOvertradingConfig.CONFIRM_SIGNAL_BARS})")
        return signal_confirmation_count >= AntiOvertradingConfig.CONFIRM_SIGNAL_BARS
    else:
        signal_confirmation_count = 1
        logger.info(f"[SINAL] Novo sinal detectado: {sinal_atual}")
        return False


def calcular_sl_tp_dinamico(dados: pd.DataFrame, acao: str, preco_atual: float,
                           lookback_periods: int = 20) -> tuple[float, float]:
    """Calcula SL/TP baseado no modo configurado (dinamico ou fixo).

    Args:
        dados: DataFrame com OHLC
        acao: "Comprar" ou "Vender"
        preco_atual: Preço atual de entrada
        lookback_periods: Número de candles para analisar (padrão 20)

    Returns:
        (stop_loss, take_profit) tupla com valores
    """

    # SE MODO FOR FIXO, RETORNA VALORES FIXOS DIRETO
    if SL_TP_MODE == 'fixo':
        logger.info(f"[FIXO] Usando SL/TP fixo para {acao}")
        if acao == "Comprar":
            return preco_atual - STOP_LOSS_PONTOS, preco_atual + TAKE_PROFIT_PONTOS
        else:
            return preco_atual + STOP_LOSS_PONTOS, preco_atual - TAKE_PROFIT_PONTOS

    # MODO DINAMICO - Calcula baseado em topos/fundos
    try:
        if len(dados) < lookback_periods:
            # Fallback para valores fixos se não houver dados suficientes
            if acao == "Comprar":
                return preco_atual - STOP_LOSS_PONTOS, preco_atual + TAKE_PROFIT_PONTOS
            else:
                return preco_atual + STOP_LOSS_PONTOS, preco_atual - TAKE_PROFIT_PONTOS

        # Analisar últimos N candles
        recent = dados.tail(lookback_periods)
        ultimo_topo = float(recent['high'].max())  # Converter para float (pode ser Decimal)
        ultimo_fundo = float(recent['low'].min())  # Converter para float (pode ser Decimal)

        # Margem de segurança (em pontos)
        margem_seguranca = 20  # 20 pontos de buffer

        if acao == "Comprar":
            # Para COMPRA:
            # TP = último topo (dar um pouco de espaço)
            # SL = último fundo - margem (evitar ser parado por pico acidental)
            tp = ultimo_topo + margem_seguranca  # Um pouco acima do topo
            sl = ultimo_fundo - margem_seguranca  # Um pouco abaixo do fundo

            # Validar relação risk/reward mínima (pelo menos 1:1.5)
            reward = tp - preco_atual
            risk = preco_atual - sl
            if risk > 0 and reward / risk < 1.5:  # RR < 1.5
                # Ajustar TP para manter RR = 1.5
                tp = preco_atual + (risk * 1.5)

        else:  # "Vender"
            # Para VENDA:
            # TP = último fundo (dar um pouco de espaço)
            # SL = último topo + margem (evitar ser parado por pico acidental)
            tp = ultimo_fundo - margem_seguranca  # Um pouco abaixo do fundo
            sl = ultimo_topo + margem_seguranca  # Um pouco acima do topo

            # Validar relação risk/reward mínima (pelo menos 1:1.5)
            reward = preco_atual - tp  # Para venda, reward é negativo
            risk = sl - preco_atual    # Para venda, risk é positivo
            if risk > 0 and reward / risk < 1.5:  # RR < 1.5
                # Ajustar TP para manter RR = 1.5
                tp = preco_atual - (risk * 1.5)

        # Garantir que SL nunca está do mesmo lado que TP
        if acao == "Comprar":
            sl = min(sl, preco_atual - 10)  # SL sempre abaixo do preço
            tp = max(tp, preco_atual + 10)  # TP sempre acima do preço
        else:
            sl = max(sl, preco_atual + 10)  # SL sempre acima do preço
            tp = min(tp, preco_atual - 10)  # TP sempre abaixo do preço

        logger.info(f"[DINAMICO] Topos/Fundos últimas {lookback_periods} velas: "
                   f"Topo={ultimo_topo:.2f}, Fundo={ultimo_fundo:.2f}")
        logger.info(f"[DINAMICO] SL/TP calculados: SL={sl:.2f}, TP={tp:.2f} "
                   f"(Risk/Reward = {abs((tp - preco_atual) / (preco_atual - sl)):.2f}:1"
                   if acao == "Comprar" else
                   f"(Risk/Reward = {abs((preco_atual - tp) / (sl - preco_atual)):.2f}:1")

        return sl, tp

    except Exception as e:
        logger.warning(f"Erro ao calcular SL/TP dinâmico: {e}. Usando valores fixos.")
        # Fallback para fixos em caso de erro
        if acao == "Comprar":
            return preco_atual - STOP_LOSS_PONTOS, preco_atual + TAKE_PROFIT_PONTOS
        else:
            return preco_atual + STOP_LOSS_PONTOS, preco_atual - TAKE_PROFIT_PONTOS


def enviar_ordem_mt5adapter(acao: str, preco_atual: float, vol: float, dados: Optional[pd.DataFrame] = None) -> bool:
    """Envia ordem via MT5Adapter (com validações e SL/TP dinâmicos)."""
    global last_trade_time

    try:
        if acao == "Aguardar":
            return False

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

        if acao == "Comprar":
            side = OrderSide.BUY
        elif acao == "Vender":
            side = OrderSide.SELL
        else:
            return False

        # Calcular SL/TP dinamicamente se temos dados
        if dados is not None and len(dados) >= 20:
            sl, tp = calcular_sl_tp_dinamico(dados, acao, preco_atual)
        else:
            # Fallback para fixos
            if acao == "Comprar":
                sl = preco_atual - STOP_LOSS_PONTOS
                tp = preco_atual + TAKE_PROFIT_PONTOS
            else:
                sl = preco_atual + STOP_LOSS_PONTOS
                tp = preco_atual - TAKE_PROFIT_PONTOS

        logger.info(f"[ENVIO] Enviando: {acao} @ {preco_atual} (SL: {sl}, TP: {tp}, Vol: {vol:.3f}%) [Agente: {AGENTE_ID}, Modo: {SL_TP_MODE.upper()}]")

        order = Order(
            symbol=Symbol(SIMBOLO),
            side=side,
            quantity=Quantity(1),
            order_type=OrderType.MARKET,
            price=Price(preco_atual),
            stop_loss=Price(sl),
            take_profit=Price(tp),
            magic_number=MAGIC_NUMBER,
            execution_method="automated",
        )

        ticket = mt5_adapter.send_order(order)
        logger.info(f"[OK] Ordem enviada! Ticket: {ticket}")

        # Rastrear ticket via MotorDecisaoIsolado (persistido em JSON)
        if ticket:
            tipo = TipoPosicao.COMPRADA if acao == "Comprar" else TipoPosicao.VENDIDA
            motor_isolado.abrir_posicao(
                ticket=int(ticket),
                tipo=tipo,
                preco_entrada=preco_atual,
                volume=1.0,
                stop_loss=sl,
                take_profit=tp,
            )
            logger.info(f"[ISOLAMENTO] Ticket {ticket} registrado via "
                       f"MotorDecisaoIsolado({AGENTE_ID})")

            # AC5.8: Registra ordem no monitor de posições
            if _monitor_posicao_rl:
                try:
                    direcao_ac = (
                        DirecaoOperacao.BUY
                        if acao == "Comprar"
                        else DirecaoOperacao.SELL
                    )
                    _monitor_posicao_rl.registrar_ordem({
                        "trade_id": str(ticket),
                        "signal_id": AGENTE_ID,
                        "symbol": SIMBOLO,
                        "direcao": direcao_ac.value,
                        "volume": 1,
                        "preco_entrada": preco_atual,
                        "sl": sl,
                        "tp": tp,
                        "magic_number": MAGIC_NUMBER,
                    })
                    _monitor_posicao_rl.atualizar_status_ordem(
                        str(ticket), StatusOrdem.FILLED,
                    )
                    logger.info(f"[AC5.8] Ordem {ticket} registrada")
                except Exception as e:
                    logger.warning(f"[AC5.8] {e}")

        # Atualizar apenas o cooldown (sem limitar trades/dia)
        last_trade_time = datetime.now()

        # Persistir episódio
        if rl_repo:
            try:
                episode_id = str(uuid.uuid4())
                episode = {
                    "episode_id": episode_id,
                    "timestamp": datetime.now(),
                    "source": "RL_AGENT_V5000",
                    "win_price": preco_atual,
                    "action": acao.upper(),
                    "symbol": SIMBOLO,
                    "volatility": vol,
                }
                rl_repo.save_episode(episode)
            except Exception as e:
                logger.warning(f"Erro ao persistir: {e}")

        return True

    except Exception as e:
        logger.error(f"Erro ao enviar ordem: {e}")
        return False


def processar_protecao_lucros() -> None:
    """
    Processa proteção de lucros apenas para posições DESTE agente.

    Monitora:
    - Reversões agudas após ganho inicial
    - Ativa break-even stop quando lucro robusto
    - Sugere fechamento parcial para ganho protegido
    """
    try:
        positions = mt5_adapter.get_positions(Symbol(SIMBOLO))
        if not positions or len(positions) == 0:
            return

        for position in positions:
            ticket_pos = int(getattr(position, 'ticket', 0))
            pos_magic = int(getattr(position, 'magic', 0) or 0)
            if pos_magic != MAGIC_NUMBER:
                continue  # Ignorar posições de outros agentes (magic diferente)
            try:
                # Construir trade dict para o motor de proteção
                entry_price = float(getattr(position, 'price_open', 0.0))
                current_price = float(getattr(position, 'price_current', 0.0))
                direcion = "BUY" if getattr(position, 'type', 0) == 0 else "SELL"
                ticket = int(getattr(position, 'ticket', 0))

                trade_dict = {
                    "trade_id": f"T{ticket}",
                    "symbol": SIMBOLO,
                    "entry_price": entry_price,
                    "entry_time": datetime.now(),
                    "direction": direcion,
                    "quantity": float(getattr(position, 'volume', 0.0)),
                    "initial_sl": float(getattr(position, 'sl', 0.0)),
                    "initial_tp": float(getattr(position, 'tp', 0.0)),
                }

                # Processar através do motor de proteção
                resultado = profit_protection_engine.processar_protecao(
                    trade=trade_dict,
                    preco_atual=current_price,
                )

                # Log de proteção
                if resultado.acao_sugerida in ["ATIVAR_BREAK_EVEN_STOP", "FECHAR_PARCIAL"]:
                    logger.info(
                        f"[PROTEÇÃO] Ticket#{ticket} | Lucro:{resultado.profit_atual:.2f}% | "
                        f"Status:{resultado.status.value} | Ação:{resultado.acao_sugerida}"
                    )

                # Implementar ação (break-even stop)
                if resultado.acao_sugerida == "ATIVAR_BREAK_EVEN_STOP":
                    # Break-even stop: SL = entry_price + offset
                    offset = entry_price * (profit_protection_engine.config["break_even_offset_pct"] / 100)
                    novo_sl = entry_price + offset if direcion == "BUY" else entry_price - offset
                    modificar_sl_ordem(ticket, novo_sl)

            except Exception as e:
                logger.debug(f"Erro ao processar proteção para posição: {e}")

    except Exception as e:
        logger.error(f"Erro em processar_protecao_lucros: {e}")


def _executar_pipeline_feedback_rl() -> None:
    """Executa pipeline AC5.9->AC6.7->AC6.8->AC6.9 a cada 10 ciclos.

    Alimentado com trades fechados acumulados em _trades_fechados_rl
    para fechar o loop de aprendizado do RL 5000.
    """
    trades_data = list(_trades_fechados_rl)
    if not trades_data:
        return

    # AC5.9: Validacao de saude do feedback
    if _feedback_validator_rl:
        try:
            relatorio = _feedback_validator_rl.validate_feedback_health(
                trades=trades_data, feedback=trades_data,
            )
            status_icon = {
                'HEALTHY': 'OK', 'WARNING': 'AVISO', 'CRITICAL': 'CRITICO',
            }.get(relatorio.overall_status, '?')
            logger.info(
                f'[AC5.9] Feedback {status_icon} | '
                f'Correlacao: {relatorio.correlation_rate:.0%} | '
                f'Qualidade: {relatorio.data_quality_score:.0%}'
            )
        except Exception as e:
            logger.warning(f'[AC5.9] Erro: {e}')

    # AC6.7: Deteccao de drift
    if _drift_detector_rl:
        try:
            alertas = _drift_detector_rl.detectar_drift(trades_data)
            if alertas:
                for a in alertas[:2]:
                    logger.warning(
                        f'[AC6.7] Drift: {a.metric} z={a.z_score:.2f}'
                    )
            else:
                logger.info('[AC6.7] Sem drift detectado')
        except Exception as e:
            logger.warning(f'[AC6.7] Erro: {e}')

    # AC6.8: Aprendizagem online
    if _online_learning_rl:
        try:
            resultado = _online_learning_rl.train_incremental(trades_data)
            if resultado:
                logger.info(f'[AC6.8] Treino incremental: {resultado}')
        except Exception as e:
            logger.warning(f'[AC6.8] Erro: {e}')

    # AC6.9: Comparacao com baseline
    if _baseline_comparator_rl:
        try:
            comparacao = _baseline_comparator_rl.comparar_metricas(
                metricas_atuais={
                    'pnl_medio': sum(t['pnl'] for t in trades_data),
                },
            )
            fb = _baseline_comparator_rl.gerar_feedback(comparacao)
            if fb:
                logger.info(f'[AC6.9] Baseline: {fb}')
        except Exception as e:
            logger.warning(f'[AC6.9] Erro: {e}')


def monitorar_posicoes() -> bool:
    """Verifica se há posições abertas DESTE agente (por magic number).

    Sincroniza MotorDecisaoIsolado com estado real do MT5:
    - Recupera tickets após restart (magic filter)
    - Remove tickets fechados (SL/TP/manual)
    - Atualiza P&L em tempo real
    """
    try:
        positions = mt5_adapter.get_positions(Symbol(SIMBOLO))
        if not positions:
            # Nenhuma posição no símbolo → fechar posições órfãs no motor
            for pos in motor_isolado.obter_posicoes_abertas():
                logger.info(f"[ISOLAMENTO] Ticket #{pos.ticket} não existe mais "
                           f"no MT5. Fechando no motor.")
                tick = mt5_adapter._mt5.symbol_info_tick(SIMBOLO)
                preco_fechamento = tick.bid if tick else pos.preco_entrada
                motor_isolado.fechar_posicao(
                    pos.ticket, preco_fechamento,
                    MotivoFechamento.SL_ATINGIDO,
                )
            return False

        # Filtrar apenas posições com NOSSO magic number
        minhas_posicoes = [
            p for p in positions
            if int(getattr(p, 'magic', 0) or 0) == MAGIC_NUMBER
        ]
        tickets_mt5_meus = {int(getattr(p, 'ticket', 0)) for p in minhas_posicoes}
        tickets_motor = {p.ticket for p in motor_isolado.obter_posicoes_abertas()}

        # Recuperar tickets do MT5 que não estão no motor (restart)
        novos = tickets_mt5_meus - tickets_motor
        for t in novos:
            pos_mt5 = next(p for p in minhas_posicoes if int(getattr(p, 'ticket', 0)) == t)
            tipo = TipoPosicao.COMPRADA if getattr(pos_mt5, 'type', 0) == 0 else TipoPosicao.VENDIDA
            motor_isolado.abrir_posicao(
                ticket=t, tipo=tipo,
                preco_entrada=float(getattr(pos_mt5, 'price_open', 0)),
                volume=float(getattr(pos_mt5, 'volume', 1)),
                stop_loss=float(getattr(pos_mt5, 'sl', 0)),
                take_profit=float(getattr(pos_mt5, 'tp', 0)),
            )
            logger.info(f"[ISOLAMENTO] Ticket #{t} (magic={MAGIC_NUMBER}) "
                       f"recuperado do MT5 via MotorDecisaoIsolado.")

        # Remover tickets fechados no MT5
        fechados = tickets_motor - tickets_mt5_meus
        for t in fechados:
            tick = mt5_adapter._mt5.symbol_info_tick(SIMBOLO)
            preco = tick.bid if tick else 0.0
            # Calcular PnL estimado para pipeline AC5.9/AC6
            pos_motor = next(
                (p for p in motor_isolado.obter_posicoes_abertas() if p.ticket == t),
                None,
            )
            if pos_motor:
                diff = preco - pos_motor.preco_entrada
                if pos_motor.tipo == TipoPosicao.VENDIDA:
                    diff = -diff
                pnl_est = diff * 0.20
                direcao_str = (
                    'BUY' if pos_motor.tipo == TipoPosicao.COMPRADA else 'SELL'
                )
                _trades_fechados_rl.append({
                    'trade_id': str(t),
                    'outcome': 'WIN' if diff > 0 else 'LOSS',
                    'pnl': pnl_est,
                    'direction': direcao_str,
                })
            motor_isolado.fechar_posicao(t, preco, MotivoFechamento.SL_ATINGIDO)
            logger.info(f"[ISOLAMENTO] Ticket #{t} fechado (SL/TP/manual).")

        # Atualizar P&L de posições ativas
        for pos_mt5 in minhas_posicoes:
            t = int(getattr(pos_mt5, 'ticket', 0))
            preco_atual = float(getattr(pos_mt5, 'price_current', 0))
            motor_isolado.atualizar_posicao(t, preco_atual)
            # AC5.8: Atualiza preço no monitor de posições
            if _monitor_posicao_rl:
                try:
                    _monitor_posicao_rl.atualizar_preco_posicao(
                        str(t), preco_atual,
                    )
                except Exception:
                    pass

        return len(minhas_posicoes) > 0
    except Exception:
        return False


def modificar_sl_ordem(ticket: int, novo_sl: float) -> bool:
    """Modifica o Stop Loss de uma posição aberta.

    Args:
        ticket: ID do ticket da posição
        novo_sl: Novo valor de SL

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        if not hasattr(mt5_adapter, '_mt5') or mt5_adapter._mt5 is None:
            logger.warning(f"[PROTEÇÃO] MT5 não disponível. Não foi possível modificar SL do ticket {ticket}")
            return False

        # Busca a posição
        positions = mt5_adapter._mt5.positions_get()
        if not positions:
            return False

        position = None
        for p in positions:
            if int(getattr(p, 'ticket', 0) or 0) == int(ticket):
                position = p
                break

        if position is None:
            logger.warning(f"[PROTEÇÃO] Posição #{ticket} não encontrada")
            return False

        # Verificação: evitar modificar se o SL já está no valor desejado (tolerância 1.0 ponto)
        current_sl = float(position.sl) if position.sl else 0.0
        if abs(float(novo_sl) - current_sl) < 1.0:
            logger.debug(f"[PROTEÇÃO] SL do ticket {ticket} já está próximo a {current_sl:.2f}. "
                        f"Novo valor {novo_sl:.2f} - diferença < 1.0pt. Ignorando modif.")
            return True

        # Prepa requisicao para modificação
        request = {
            'action': mt5_adapter._mt5.TRADE_ACTION_MODIFY,
            'position': int(position.ticket),
            'sl': float(novo_sl),
            'tp': float(position.tp) if position.tp else 0,
            'magic': MAGIC_NUMBER,
            'comment': 'Profit Protection SL Update'
        }

        logger.debug(f"[PROTEÇÃO] Enviando requisição modify para ticket {ticket}: "
                    f"SL={float(novo_sl):.2f}, TP={float(position.tp) if position.tp else 0:.2f}, "
                    f"Atual: SL={current_sl:.2f}", extra={'action': 'MODIFY_SL'})

        result = mt5_adapter._mt5.order_send(request)

        if result is None:
            logger.error(f"[PROTEÇÃO] order_send retornou None para ticket {ticket}. "
                        f"Verificar conexão MT5 ou conta bloqueada.")
            return False

        retcode = getattr(result, 'retcode', -1)
        comment = getattr(result, 'comment', 'Sem detalhes')

        if retcode != mt5_adapter._mt5.TRADE_RETCODE_DONE:
            logger.warning(f"[PROTEÇÃO] Falha ao modificar SL do ticket {ticket}: "
                          f"retcode={retcode}, mensagem={comment}. "
                          f"Req: SL={float(novo_sl):.2f}, TP={float(position.tp) if position.tp else 0:.2f}")

            # Diagnostico detalhado
            if retcode == 10009:  # TRADE_RETCODE_INVALID_PRICE
                logger.error(f"  -> INVALID PRICE: novo SL {novo_sl:.2f} pode estar fora do spread")
            elif retcode == 10010:  # TRADE_RETCODE_INVALID_STOPS
                logger.error(f"  -> INVALID STOPS: SL ou TP invalido. SL={novo_sl:.2f}, TP={float(position.tp):.2f}")
            elif retcode == 10014:  # TRADE_RETCODE_INVALID_VOLUME
                logger.error(f"  -> INVALID VOLUME: verificar volume=1")
            elif comment == "Invalid request":
                logger.error(f"  -> INVALID REQUEST: PROVAVEL: SL ja esta neste valor ou diferenca < 1 ponto")

            return False

        logger.info(f"[PROTEÇÃO] SL modificado com sucesso para ticket {ticket}: {novo_sl:.2f}")
        return True

    except Exception as e:
        logger.error(f"[PROTEÇÃO] Erro ao modificar SL: {e}")
        return False


def fechar_parcial_posicao(ticket: int, volume_para_fechar: float) -> bool:
    """Fecha parcialmente uma posição.

    Args:
        ticket: ID do ticket da posição
        volume_para_fechar: Volume para fechar (em contratos)

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        if not hasattr(mt5_adapter, '_mt5') or mt5_adapter._mt5 is None:
            logger.warning(f"[PROTEÇÃO] MT5 não disponível. Não foi possível fechar posição {ticket}")
            return False

        # Busca a posição
        positions = mt5_adapter._mt5.positions_get()
        if not positions:
            return False

        position = None
        for p in positions:
            if int(getattr(p, 'ticket', 0) or 0) == int(ticket):
                position = p
                break

        if position is None:
            logger.warning(f"[PROTEÇÃO] Posição #{ticket} não encontrada para fechamento")
            return False

        # Define tipo de ordem oposta
        if int(position.type) == mt5_adapter._mt5.ORDER_TYPE_BUY:
            order_type = mt5_adapter._mt5.ORDER_TYPE_SELL
        else:
            order_type = mt5_adapter._mt5.ORDER_TYPE_BUY

        # Obtém tick atual
        tick = mt5_adapter._mt5.symbol_info_tick(position.symbol)
        if tick is None:
            logger.error(f"[PROTEÇÃO] Não conseguiu obter tick para {position.symbol}")
            return False

        close_price = tick.bid if order_type == mt5_adapter._mt5.ORDER_TYPE_SELL else tick.ask

        # Prepara requisição
        request = {
            'action': mt5_adapter._mt5.TRADE_ACTION_DEAL,
            'symbol': position.symbol,
            'volume': float(volume_para_fechar),
            'type': order_type,
            'position': int(position.ticket),
            'price': float(close_price),
            'deviation': 10,
            'magic': MAGIC_NUMBER,
            'comment': 'Profit Protection Partial Close',
            'type_time': mt5_adapter._mt5.ORDER_TIME_GTC,
            'type_filling': mt5_adapter._mt5.ORDER_FILLING_RETURN
        }

        result = mt5_adapter._mt5.order_send(request)

        if result is None:
            logger.error(f"[PROTEÇÃO] order_send retornou None para fechar posição {ticket}")
            return False

        if result.retcode != mt5_adapter._mt5.TRADE_RETCODE_DONE:
            logger.warning(f"[PROTEÇÃO] Falha ao fechar parcialmente o ticket {ticket}: {result.comment}")
            return False

        logger.info(f"[PROTEÇÃO] Fechados {volume_para_fechar:.2f} contratos do ticket {ticket}")
        return True

    except Exception as e:
        logger.error(f"[PROTEÇÃO] Erro ao fechar parcialmente: {e}")
        return False


def proteger_lucro_trade() -> None:
    """Protege trades abertos com Profit Protection.

    Estratégia:
    - Se lucro > 25% do TP: Move SL para break-even
    - Se lucro > 50% do TP: Fecha 50% (lock in profits)
    - Se lucro > 75% do TP: Mantém trailing (deixa correr)
    """
    try:
        positions = mt5_adapter.get_positions(Symbol(SIMBOLO))
        if not positions or len(positions) == 0:
            return

        for pos in positions:
            # Dados da posição aberta - com conversão explícita para float
            ticket = pos.ticket

            # Ignorar posições de outros agentes (filtro por magic number)
            pos_magic = int(getattr(pos, 'magic', 0) or 0)
            if pos_magic != MAGIC_NUMBER:
                continue

            entry_price = float(pos.price_open) if pos.price_open else 0.0
            current_price = float(pos.price_current) if pos.price_current else 0.0
            sl = float(pos.sl) if pos.sl else 0.0
            tp = float(pos.tp) if pos.tp else 0.0
            side = pos.type  # 0=BUY, 1=SELL
            volume = float(pos.volume) if pos.volume else 0.0

            # Validação: SL inválido ou zero
            if sl <= 0.0 or tp <= 0.0:
                logger.debug(f"[PROTEÇÃO] Ticket {ticket}: SL ou TP inválido (SL={sl}, TP={tp}). Ignorando.")
                continue

            # Calcular lucro atual da posição
            if side == 0:  # BUY
                lucro_pontos = current_price - entry_price
                lucro_max = tp - entry_price
            else:  # SELL
                lucro_pontos = entry_price - current_price
                lucro_max = entry_price - tp

            # Evitar divisão por zero
            if lucro_max <= 0:
                continue

            percent_tp = (lucro_pontos / lucro_max) * 100

            # Level 1: 25% de lucro -> Move SL para break-even
            if percent_tp > 25:
                novo_sl = entry_price
                diferenca_sl = abs(novo_sl - sl)

                if side == 0:  # BUY
                    # Tolerância: mínimo 1.0 ponto (padrão broker) para evitar "Invalid request"
                    if novo_sl > sl + 1.0:
                        logger.debug(f"[PROTEÇÃO] Ticket {ticket} (BUY): SL atual={sl:.2f}, novo={novo_sl:.2f}, "
                                   f"diferença={diferenca_sl:.2f}, tentando modificar...")
                        logger.info(f"[PROTEÇÃO] Posição #{ticket} em +{percent_tp:.1f}% de lucro. "
                                   f"Movendo SL para break-even ({novo_sl:.2f})")
                        modificar_sl_ordem(ticket, novo_sl)
                    else:
                        logger.debug(f"[PROTEÇÃO] Ticket {ticket} (BUY): Diferença SL={diferenca_sl:.2f} "
                                   f"< 1.0 (inercial). Ignorando.")
                else:  # SELL
                    # Tolerância: mínimo 1.0 ponto (padrão broker)
                    if novo_sl < sl - 1.0:
                        logger.debug(f"[PROTEÇÃO] Ticket {ticket} (SELL): SL atual={sl:.2f}, novo={novo_sl:.2f}, "
                                   f"diferença={diferenca_sl:.2f}, tentando modificar...")
                        logger.info(f"[PROTEÇÃO] Posição #{ticket} em +{percent_tp:.1f}% de lucro. "
                                   f"Movendo SL para break-even ({novo_sl:.2f})")
                        modificar_sl_ordem(ticket, novo_sl)
                    else:
                        logger.debug(f"[PROTEÇÃO] Ticket {ticket} (SELL): Diferença SL={diferenca_sl:.2f} "
                                   f"< 1.0 (inercial). Ignorando.")

            # Level 2: 50% de lucro -> Fecha 50% (lock in profits)
            if percent_tp > 50:
                half_volume = volume / 2
                logger.info(f"[PROTEÇÃO] Posição #{ticket} em +{percent_tp:.1f}% de lucro. "
                           f"Fechando 50% do volume ({half_volume:.2f})")
                fechar_parcial_posicao(ticket, half_volume)

            # Level 3: 75% de lucro -> Trailing stop (deixa correr)
            if percent_tp > 75:
                trailing_distance = 50  # 50 pontos de trailing
                novo_sl = 0.0

                if side == 0:  # BUY
                    novo_sl = current_price - trailing_distance
                    diferenca_sl = abs(novo_sl - sl)
                    # Tolerância: mínimo 1.0 ponto (padrão broker)
                    if novo_sl > sl + 1.0:
                        logger.debug(f"[PROTEÇÃO] Ticket {ticket} (BUY-TRAIL): SL atual={sl:.2f}, novo={novo_sl:.2f}, "
                                   f"diferença={diferenca_sl:.2f}, tentando trailing...")
                        logger.info(f"[PROTEÇÃO] Posição #{ticket} em +{percent_tp:.1f}% de lucro. "
                                   f"Ativando trailing stop (SL={novo_sl:.2f})")
                        modificar_sl_ordem(ticket, novo_sl)
                else:  # SELL
                    novo_sl = current_price + trailing_distance
                    diferenca_sl = abs(novo_sl - sl)
                    # Tolerância: mínimo 1.0 ponto (padrão broker)
                    if novo_sl < sl - 1.0:
                        logger.debug(f"[PROTEÇÃO] Ticket {ticket} (SELL-TRAIL): SL atual={sl:.2f}, novo={novo_sl:.2f}, "
                                   f"diferença={diferenca_sl:.2f}, tentando trailing...")
                        logger.info(f"[PROTEÇÃO] Posição #{ticket} em +{percent_tp:.1f}% de lucro. "
                                   f"Ativando trailing stop (SL={novo_sl:.2f})")
                        modificar_sl_ordem(ticket, novo_sl)

    except Exception as e:
        logger.error(f"[PROTEÇÃO] Erro ao proteger lucro de trades: {e}")


def registrar_progresso_objetivos(saldo_inicial: float, forcar: bool = False) -> None:
    """Registra progresso parcial em relacao aos objetivos do dia.

    Args:
        saldo_inicial: Saldo no inicio da operacao
        forcar: Se True, registra mesmo que nao tenha passado 5 minutos
    """
    global ultimo_registro_progresso

    try:
        agora = datetime.now()

        # Só registra a cada 5 minutos (ou se forçado)
        if not forcar and ultimo_registro_progresso:
            if (agora - ultimo_registro_progresso).total_seconds() < 300:  # 5 minutos
                return

        # Obter saldo atual
        saldo_atual_decimal = mt5_adapter.get_account_balance()
        saldo_atual = float(saldo_atual_decimal) if saldo_atual_decimal else saldo_inicial

        # Calcular P&L
        pl_atual = saldo_atual - saldo_inicial

        # Calcular progresso
        progresso_target = (pl_atual / TARGET_LUCRO_DIARIO) * 100 if TARGET_LUCRO_DIARIO > 0 else 0
        progresso_stop = abs(pl_atual / STOP_PERDA_DIARIA) * 100 if STOP_PERDA_DIARIA != 0 else 0

        # Construir barra visual
        barra_size = 30
        if pl_atual >= 0:
            filled = int((min(pl_atual, TARGET_LUCRO_DIARIO) / TARGET_LUCRO_DIARIO) * barra_size)
            barra = "[" + "=" * filled + "-" * (barra_size - filled) + "]"
            status = f"{pl_atual:+.2f} / {TARGET_LUCRO_DIARIO:.2f} ({progresso_target:.1f}%)"
        else:
            filled = int((abs(min(pl_atual, STOP_PERDA_DIARIA)) / abs(STOP_PERDA_DIARIA)) * barra_size)
            barra = "[" + "x" * filled + "-" * (barra_size - filled) + "]"
            status = f"{pl_atual:+.2f} / {STOP_PERDA_DIARIA:.2f} ({progresso_stop:.1f}%)"

        # Informacoes adicionais
        info_trades = f"Trades: {trades_executed_today}"
        info_tempo = f"Tempo: {(datetime.now().hour * 60 + datetime.now().minute) // 60}h"

        # Registrar no log com barra de progresso
        logger.info(f"[PROGRESSO] {barra} {status} | {info_trades} | {info_tempo}")

        ultimo_registro_progresso = agora

    except Exception as e:
        logger.debug(f"Erro ao registrar progresso: {e}")


def print_status():
    """Exibe status de operação BALANCED MODE."""
    logger.info("\n" + "=" * 70)
    logger.info("[STATUS] OPERACAO (BALANCED MODE)")
    logger.info("=" * 70)
    logger.info(f"Agente ID: {AGENTE_ID}")
    logger.info(f"Modo SL/TP: {SL_TP_MODE.upper()}")
    logger.info(f"Modo: Operando livremente até TARGET ou STOP LOSS")
    logger.info(f"Limite diário: DESATIVADO (ilimitado)")
    logger.info(f"Última operação: {last_trade_time.strftime('%H:%M:%S') if last_trade_time else 'Nenhuma'}")
    logger.info(f"Cooldown: {AntiOvertradingConfig.COOLDOWN_SECONDS}s entre trades")
    logger.info("=" * 70 + "\n")


def loop_operacao():
    """Loop principal com proteções anti-overtrading."""
    global last_signal, trades_executed_today

    logger.info("\n" + "=" * 70)
    logger.info("[START] INICIANDO OPERACAO RL v5000 (BALANCED MODE - SEM LIMITE DIARIO)")
    logger.info("=" * 70)
    logger.info(f"Alvo: R${TARGET_LUCRO_DIARIO} | Stop: R${STOP_PERDA_DIARIA}")
    logger.info(f"Trades/dia: ILIMITADO (até target/stop loss)")
    logger.info(f"Cooldown entre trades: {AntiOvertradingConfig.COOLDOWN_SECONDS}s")
    logger.info(f"Min volatilidade: {AntiOvertradingConfig.MIN_VOLATILITY_PERCENT}%")
    logger.info(f"Confirmação sinal: {AntiOvertradingConfig.CONFIRM_SIGNAL_BARS} velas")

    # Capturar saldo inicial para rastreamento de P&L
    try:
        saldo_inicial = float(mt5_adapter.get_account_balance())
        logger.info(f"[INICIO] Saldo inicial: R${saldo_inicial:.2f}")
    except Exception as e:
        logger.warning(f"Nao foi possivel obter saldo inicial: {e}")
        saldo_inicial = 0.0

    lucro_sessao = 0.0
    ciclo = 0

    while True:
        ciclo += 1
        logger.info(f"\n[CICLO {ciclo}] Iniciando iteração do loop...")

        # ✅ PROTEÇÃO DE LUCRO: Monitora trades abertos continuamente (sistema existente)
        logger.debug(f"[CICLO {ciclo}] Executando proteger_lucro_trade()...")
        proteger_lucro_trade()
        logger.debug(f"[CICLO {ciclo}] proteger_lucro_trade() concluído.")

        # ✅ PROTEÇÃO DE LUCRO: Motor dinâmico (P1-PROFIT_PROTECTION) - NEW
        logger.debug(f"[CICLO {ciclo}] Executando processar_protecao_lucros()...")
        processar_protecao_lucros()
        logger.debug(f"[CICLO {ciclo}] processar_protecao_lucros() concluído.")

        # Grupo 2: Pipeline Feedback/Aprendizado (a cada 10 ciclos)
        if ciclo % 10 == 0:
            try:
                _executar_pipeline_feedback_rl()
            except Exception as _e:
                logger.warning(f'[PIPELINE-FEEDBACK] Erro: {_e}')

        logger.debug(f"[CICLO {ciclo}] Verificando horário de trading...")
        if not verificar_horario_trading():
            logger.info("[HORA] Fora do horario. Aguardando...")
            logger.debug(f"[CICLO {ciclo}] Dormindo 60s (fora do horário)...")
            time.sleep(60)
            logger.debug(f"[CICLO {ciclo}] Retornando ao início do loop após sleep.")
            continue

        logger.debug(f"[CICLO {ciclo}] Verificando lucro vs TARGET...")
        if lucro_sessao >= TARGET_LUCRO_DIARIO:
            logger.info(f"[TARGET] ATINGIDO: R${lucro_sessao:.2f}")
            break

        logger.debug(f"[CICLO {ciclo}] Verificando stop loss...")
        if lucro_sessao <= STOP_PERDA_DIARIA:
            logger.warning(f"[STOP] STOP LOSS ACIONADO: R${lucro_sessao:.2f}")
            break

        logger.debug(f"[CICLO {ciclo}] Monitorando posições abertas...")
        if monitorar_posicoes():
            logger.info("[WAIT] Posicao em aberto. Aguardando fechar...")
            logger.debug(f"[CICLO {ciclo}] Dormindo 30s (posição aberta)...")
            time.sleep(30)
            logger.debug(f"[CICLO {ciclo}] Retornando ao início do loop após sleep.")
            continue

        logger.info(f"\n[Ciclo {ciclo}] Consultando mercado...")
        logger.debug(f"[CICLO {ciclo}] Carregando dados do MT5...")
        dados = carregar_dados_mt5(SIMBOLO, n_candles=100)
        logger.debug(f"[CICLO {ciclo}] Dados carregados: {len(dados) if dados is not None else 0} candles")

        if dados is None or len(dados) < 20:
            logger.warning("[!] Dados insuficientes. Aguardando 30s...")
            logger.debug(f"[CICLO {ciclo}] Dormindo 30s (dados insuficientes)...")
            time.sleep(30)
            logger.debug(f"[CICLO {ciclo}] Retornando ao início do loop após sleep.")
            continue

        # Registrar progresso parcial do dia (a cada 5 minutos)
        logger.debug(f"[CICLO {ciclo}] Registrando progresso...")
        registrar_progresso_objetivos(saldo_inicial)
        logger.debug(f"[CICLO {ciclo}] Progresso registrado.")

        # ════════════════════════════════════════════════════════════════
        # ANTI-OVERTRADING VALIDATIONS
        # ════════════════════════════════════════════════════════════════

        # 1. Verificar volatilidade
        logger.debug(f"[CICLO {ciclo}] Calculando volatilidade...")
        vol = calcular_volatilidade(dados)
        logger.debug(f"[CICLO {ciclo}] Volatilidade calculada: {vol:.3f}%")

        if not verificar_volatilidade(vol):
            logger.debug(f"[CICLO {ciclo}] Volatilidade insuficiente. Aguardando 60s...")
            time.sleep(60)
            continue

        # 2. Verificar cooldown
        logger.debug(f"[CICLO {ciclo}] Verificando cooldown...")
        if not verificar_cooldown():
            logger.debug(f"[CICLO {ciclo}] Cooldown ativo. Aguardando 60s...")
            time.sleep(60)
            continue

        logger.debug(f"[CICLO {ciclo}] Entrando na seção de decisão do modelo...")
        try:
            # 4. Obter ação do modelo
            logger.debug(f"[CICLO {ciclo}] Obtendo ação do modelo...")
            acao_id, confidence = obter_acao_do_modelo(dados)
            mapeamento = {1: "Comprar", 0: "Aguardar", 2: "Vender"}
            acao_str = mapeamento.get(acao_id, "Aguardar")
            preco_atual = float(dados['close'].iloc[-1])
            logger.debug(f"[CICLO {ciclo}] Ação obtida: {acao_str} (confiança: {confidence:.2%})")

            # 5. Verificar confirmação multi-vela
            logger.debug(f"[CICLO {ciclo}] Verificando confirmação do sinal...")
            if confirmado := verificar_confirmacao_sinal(acao_str, last_signal):
                # Executar apenas se confirmado E passou todas as validações
                # Passar dados para cálculo dinâmico de SL/TP
                logger.info(f"[CICLO {ciclo}] Sinal CONFIRMADO! Enviando ordem...")
                logger.debug(f"[CICLO {ciclo}] Chamando enviar_ordem_mt5adapter()...")
                enviar_ordem_mt5adapter(acao_str, preco_atual, vol, dados=dados)
                logger.debug(f"[CICLO {ciclo}] Ordem enviada com sucesso.")
                last_signal = acao_str
                trades_executed_today += 1
                # Registrar progresso apos trade
                registrar_progresso_objetivos(saldo_inicial, forcar=True)
                print_status()
                logger.debug(f"[CICLO {ciclo}] Cooldown por {AntiOvertradingConfig.COOLDOWN_SECONDS}s...")
                time.sleep(AntiOvertradingConfig.COOLDOWN_SECONDS)
                logger.debug(f"[CICLO {ciclo}] Cooldown finalizado.")
            else:
                last_signal = acao_str
                logger.info(f"[SINAL] Sinal: {acao_str} (confiança: {confidence:.2%}, vol: {vol:.3f}%)")
                logger.debug(f"[CICLO {ciclo}] Sinal não confirmado. Aguardando 60s...")
                time.sleep(60)
                logger.debug(f"[CICLO {ciclo}] Aguardo finalizado.")

        except Exception as e:
            logger.error(f"[ERRO] Erro no ciclo {ciclo}: {e}", exc_info=True)
            logger.debug(f"[CICLO {ciclo}] Dormindo 30s após erro...")
            time.sleep(30)
            logger.debug(f"[CICLO {ciclo}] Retornando ao início do loop após erro.")


if __name__ == "__main__":
    # AC5.8: Monitor de posições (Grupo 2)
    _monitor_posicao_rl = None
    if AC5_8_DISPONIVEL and MonitorPositionManager:
        try:
            _db_path = str(ROOT_DIR / "data" / "db" / "trading.db")
            _monitor_posicao_rl = MonitorPositionManager(
                db_caminho=_db_path,
            )
            logger.info("[OK] AC5.8 MonitorPositionManager: Ativo")
        except Exception as e:
            logger.warning(f"[!] AC5.8: {e}")

    # AC5.9/AC6: Feedback e Aprendizado (Grupo 2)
    if _AC5_9_DISPONIVEL and FeedbackValidator:
        try:
            _feedback_validator_rl = FeedbackValidator()
            logger.info("[OK] AC5.9 FeedbackValidator: Ativo")
        except Exception as e:
            logger.warning(f"[!] AC5.9: {e}")

    if _AC6_DISPONIVEL and DriftDetector:
        try:
            _drift_detector_rl = DriftDetector(
                agent_id=str(AGENTE_ID),
                drift_threshold_zscore=2.0,
            )
            logger.info("[OK] AC6.7 DriftDetector: Ativo")
        except Exception as e:
            logger.warning(f"[!] AC6.7: {e}")

    if _AC6_DISPONIVEL and OnlineLearningController:
        try:
            _online_learning_rl = OnlineLearningController(
                agent_id=str(AGENTE_ID),
            )
            logger.info("[OK] AC6.8 OnlineLearningController: Ativo")
        except Exception as e:
            logger.warning(f"[!] AC6.8: {e}")

    if _AC6_DISPONIVEL and BaselineComparator:
        try:
            _baseline_comparator_rl = BaselineComparator(
                agent_id=str(AGENTE_ID),
            )
            logger.info("[OK] AC6.9 BaselineComparator: Ativo")
        except Exception as e:
            logger.warning(f"[!] AC6.9: {e}")

    try:
        logger.info("Inicializando...")
        inicializar_adaptador_mt5()
        inicializar_agente_rl()
        inicializar_rl_repo()

        loop_operacao()

    except KeyboardInterrupt:
        logger.info("\n[STOP] Operacao interrompida pelo usuario.")
        print_status()
    except Exception as e:
        logger.error(f"[ERRO] Erro fatal: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if _monitor_posicao_rl:
            _monitor_posicao_rl.fechar_conexao()
        if mt5_adapter:
            mt5_adapter.disconnect()
            logger.info("[OK] MT5 desconectado.")
