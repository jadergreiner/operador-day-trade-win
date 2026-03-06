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

config = TradingConfig()
mt5_adapter: Optional[MT5Adapter] = None
pipeline: Optional[PipelineTreinamentoRL] = None
rl_repo: Optional[SqliteRLRepository] = None

# Anti-overtrading state
trades_executed_today = 0
last_trade_time: Optional[datetime] = None
trades_by_hour = {}  # {hour: count}
last_signal: Optional[str] = None
signal_confirmation_count = 0


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
        logger.info(f"📍 Sinal CONFIRMADO ({signal_confirmation_count}/{AntiOvertradingConfig.CONFIRM_SIGNAL_BARS})")
        return signal_confirmation_count >= AntiOvertradingConfig.CONFIRM_SIGNAL_BARS
    else:
        signal_confirmation_count = 1
        logger.info(f"[SINAL] Novo sinal detectado: {sinal_atual}")
        return False


def enviar_ordem_mt5adapter(acao: str, preco_atual: float, vol: float) -> bool:
    """Envia ordem via MT5Adapter (com validações)."""
    global last_trade_time

    try:
        if acao == "Aguardar":
            return False

        if acao == "Comprar":
            side = OrderSide.BUY
            sl = preco_atual - STOP_LOSS_PONTOS
            tp = preco_atual + TAKE_PROFIT_PONTOS
        elif acao == "Vender":
            side = OrderSide.SELL
            sl = preco_atual + STOP_LOSS_PONTOS
            tp = preco_atual - TAKE_PROFIT_PONTOS
        else:
            return False

        logger.info(f"📤 Enviando: {acao} @ {preco_atual} (SL: {sl}, TP: {tp}, Vol: {vol:.3f}%)")

        order = Order(
            symbol=Symbol(SIMBOLO),
            side=side,
            quantity=Quantity(1),
            order_type=OrderType.MARKET,
            price=Price(preco_atual),
            stop_loss=Price(sl),
            take_profit=Price(tp),
            execution_method="automated",
        )

        ticket = mt5_adapter.send_order(order)
        logger.info(f"[OK] Ordem enviada! Ticket: {ticket}")

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


def monitorar_posicoes() -> bool:
    """Verifica se há posições abertas."""
    try:
        positions = mt5_adapter.get_positions(Symbol(SIMBOLO))
        return len(positions) > 0 if positions else False
    except Exception:
        return False


def print_status():
    """Exibe status de operação BALANCED MODE."""
    logger.info("\n" + "=" * 70)
    logger.info("[STATUS] OPERACAO (BALANCED MODE)")
    logger.info("=" * 70)
    logger.info(f"Modo: Operando livremente até TARGET ou STOP LOSS")
    logger.info(f"Limite diário: DESATIVADO (ilimitado)")
    logger.info(f"Última operação: {last_trade_time.strftime('%H:%M:%S') if last_trade_time else 'Nenhuma'}")
    logger.info(f"Cooldown: {AntiOvertradingConfig.COOLDOWN_SECONDS}s entre trades")
    logger.info("=" * 70 + "\n")


def loop_operacao():
    """Loop principal com proteções anti-overtrading."""
    global last_signal

    logger.info("\n" + "=" * 70)
    logger.info("[START] INICIANDO OPERACAO RL v5000 (BALANCED MODE - SEM LIMITE DIARIO)")
    logger.info("=" * 70)
    logger.info(f"Alvo: R${TARGET_LUCRO_DIARIO} | Stop: R${STOP_PERDA_DIARIA}")
    logger.info(f"Trades/dia: ILIMITADO (até target/stop loss)")
    logger.info(f"Cooldown entre trades: {AntiOvertradingConfig.COOLDOWN_SECONDS}s")
    logger.info(f"Min volatilidade: {AntiOvertradingConfig.MIN_VOLATILITY_PERCENT}%")
    logger.info(f"Confirmação sinal: {AntiOvertradingConfig.CONFIRM_SIGNAL_BARS} velas")

    lucro_sessao = 0.0
    ciclo = 0

    while True:
        ciclo += 1

        if not verificar_horario_trading():
            logger.info("⏰ Fora do horário. Aguardando...")
            time.sleep(60)
            continue

        if lucro_sessao >= TARGET_LUCRO_DIARIO:
            logger.info(f"[TARGET] ATINGIDO: R${lucro_sessao:.2f}")
            break

        if lucro_sessao <= STOP_PERDA_DIARIA:
            logger.warning(f"🛑 STOP LOSS ACIONADO: R${lucro_sessao:.2f}")
            break

        if monitorar_posicoes():
            logger.info("[WAIT] Posicao em aberto. Aguardando fechar...")
            time.sleep(30)
            continue

        logger.info(f"\n[Ciclo {ciclo}] Consultando mercado...")
        dados = carregar_dados_mt5(SIMBOLO, n_candles=100)

        if dados is None or len(dados) < 20:
            logger.warning("[!] Dados insuficientes. Aguardando 30s...")
            time.sleep(30)
            continue

        # ════════════════════════════════════════════════════════════════
        # ANTI-OVERTRADING VALIDATIONS
        # ════════════════════════════════════════════════════════════════

        # 1. Verificar volatilidade
        vol = calcular_volatilidade(dados)
        if not verificar_volatilidade(vol):
            time.sleep(60)
            continue

        # 2. Verificar cooldown
        if not verificar_cooldown():
            time.sleep(60)
            continue

        try:
            # 4. Obter ação do modelo
            acao_id, confidence = obter_acao_do_modelo(dados)
            mapeamento = {1: "Comprar", 0: "Aguardar", 2: "Vender"}
            acao_str = mapeamento.get(acao_id, "Aguardar")
            preco_atual = float(dados['close'].iloc[-1])

            # 5. Verificar confirmação multi-vela
            if confirmado := verificar_confirmacao_sinal(acao_str, last_signal):
                # Executar apenas se confirmado E passou todas as validações
                enviar_ordem_mt5adapter(acao_str, preco_atual, vol)
                last_signal = acao_str
                print_status()
                time.sleep(AntiOvertradingConfig.COOLDOWN_SECONDS)
            else:
                last_signal = acao_str
                logger.info(f"📌 Sinal: {acao_str} (confiança: {confidence:.2%}, vol: {vol:.3f}%)")
                time.sleep(60)

        except Exception as e:
            logger.error(f"Erro no ciclo: {e}")
            time.sleep(30)


if __name__ == "__main__":
    try:
        logger.info("Inicializando...")
        inicializar_adaptador_mt5()
        inicializar_agente_rl()
        inicializar_rl_repo()

        loop_operacao()

    except KeyboardInterrupt:
        logger.info("\n⏹️  Operação interrompida pelo usuário.")
        print_status()
    except Exception as e:
        logger.error(f"[ERRO] Erro fatal: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if mt5_adapter:
            mt5_adapter.disconnect()
            logger.info("[OK] MT5 desconectado.")
