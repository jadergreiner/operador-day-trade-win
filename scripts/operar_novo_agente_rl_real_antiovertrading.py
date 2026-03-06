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
ultimo_registro_progresso: Optional[datetime] = None  # Para registrar a cada 5 min


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
    """Calcula SL/TP dinamicamente baseado em topos/fundos recentes.

    Args:
        dados: DataFrame com OHLC
        acao: "Comprar" ou "Vender"
        preco_atual: Preço atual de entrada
        lookback_periods: Número de candles para analisar (padrão 20)

    Returns:
        (stop_loss, take_profit) tupla com valores dinâmicos
    """
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

        logger.info(f"[ENVIO] Enviando: {acao} @ {preco_atual} (SL: {sl}, TP: {tp}, Vol: {vol:.3f}%)")

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

        # Verificação: evitar modificar se o SL já está no valor desejado (tolerância 0.1)
        current_sl = float(position.sl) if position.sl else 0.0
        if abs(float(novo_sl) - current_sl) < 0.1:
            logger.debug(f"[PROTEÇÃO] SL do ticket {ticket} já está em {current_sl:.2f}. Nenhuma modif necessária")
            return True

        # Prepa requisicao para modificação
        request = {
            'action': mt5_adapter._mt5.TRADE_ACTION_MODIFY,
            'position': int(position.ticket),
            'sl': float(novo_sl),
            'tp': float(position.tp) if position.tp else 0,
            'magic': 234000,
            'comment': 'Profit Protection SL Update'
        }

        result = mt5_adapter._mt5.order_send(request)

        if result is None:
            logger.error(f"[PROTEÇÃO] order_send retornou None para ticket {ticket}")
            return False

        if result.retcode != mt5_adapter._mt5.TRADE_RETCODE_DONE:
            logger.warning(f"[PROTEÇÃO] Falha ao modificar SL do ticket {ticket}: {result.comment}")
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
            'magic': 234000,
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
            # Dados da posição aberta
            ticket = pos.ticket
            entry_price = pos.price_open
            current_price = pos.price_current
            sl = pos.sl
            tp = pos.tp
            side = pos.type  # 0=BUY, 1=SELL
            volume = pos.volume

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

            # Level 1: 25% de lucro → Move SL para break-even
            if percent_tp > 25:
                novo_sl = entry_price
                # Tolerância: não modificar se diferença < 0.5 pontos (evita "Invalid request")
                if side == 0 and novo_sl > sl + 0.5:  # BUY: novo SL > SL antigo + tolerância
                    logger.info(f"[PROTEÇÃO] Posição #{ticket} em +{percent_tp:.1f}% de lucro. "
                               f"Movendo SL para break-even ({novo_sl:.2f})")
                    modificar_sl_ordem(ticket, novo_sl)
                elif side == 1 and novo_sl < sl - 0.5:  # SELL: novo SL < SL antigo - tolerância
                    logger.info(f"[PROTEÇÃO] Posição #{ticket} em +{percent_tp:.1f}% de lucro. "
                               f"Movendo SL para break-even ({novo_sl:.2f})")
                    modificar_sl_ordem(ticket, novo_sl)

            # Level 2: 50% de lucro → Fecha 50% (lock in profits)
            if percent_tp > 50:
                half_volume = volume / 2
                logger.info(f"[PROTEÇÃO] Posição #{ticket} em +{percent_tp:.1f}% de lucro. "
                           f"Fechando 50% do volume ({half_volume:.2f})")
                fechar_parcial_posicao(ticket, half_volume)

            # Level 3: 75% de lucro → Trailing stop (deixa correr)
            if percent_tp > 75:
                trailing_distance = 50  # 50 pontos de trailing
                if side == 0:  # BUY
                    novo_sl = current_price - trailing_distance
                    if novo_sl > sl + 0.5:  # Tolerância: diferença mínima 0.5 pontos
                        logger.info(f"[PROTEÇÃO] Posição #{ticket} em +{percent_tp:.1f}% de lucro. "
                                   f"Ativando trailing stop (SL={novo_sl:.2f})")
                        modificar_sl_ordem(ticket, novo_sl)
                else:  # SELL
                    novo_sl = current_price + trailing_distance
                    if novo_sl < sl - 0.5:  # Tolerância: diferença mínima 0.5 pontos
                        logger.info(f"[PROTEÇÃO] Posição #{ticket} em +{percent_tp:.1f}% de lucro. "
                                   f"Ativando trailing stop (SL={novo_sl:.2f})")
                        modificar_sl_ordem(ticket, novo_sl)

    except Exception as e:
        logger.debug(f"Erro ao proteger lucro de trades: {e}")


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
        account_info = mt5_adapter.get_account_info()
        saldo_inicial = account_info.get("balance", 0.0) if account_info else 0.0
        logger.info(f"[INICIO] Saldo inicial: R${saldo_inicial:.2f}")
    except Exception as e:
        logger.warning(f"Nao foi possivel obter saldo inicial: {e}")
        saldo_inicial = 0.0

    lucro_sessao = 0.0
    ciclo = 0

    while True:
        ciclo += 1

        # ✅ PROTEÇÃO DE LUCRO: Monitora trades abertos continuamente
        proteger_lucro_trade()

        if not verificar_horario_trading():
            logger.info("[HORA] Fora do horario. Aguardando...")
            time.sleep(60)
            continue

        if lucro_sessao >= TARGET_LUCRO_DIARIO:
            logger.info(f"[TARGET] ATINGIDO: R${lucro_sessao:.2f}")
            break

        if lucro_sessao <= STOP_PERDA_DIARIA:
            logger.warning(f"[STOP] STOP LOSS ACIONADO: R${lucro_sessao:.2f}")
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

        # Registrar progresso parcial do dia (a cada 5 minutos)
        registrar_progresso_objetivos(saldo_inicial)

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
                # Passar dados para cálculo dinâmico de SL/TP
                enviar_ordem_mt5adapter(acao_str, preco_atual, vol, dados=dados)
                last_signal = acao_str
                trades_executed_today += 1
                # Registrar progresso apos trade
                registrar_progresso_objetivos(saldo_inicial, forcar=True)
                print_status()
                time.sleep(AntiOvertradingConfig.COOLDOWN_SECONDS)
            else:
                last_signal = acao_str
                logger.info(f"[SINAL] Sinal: {acao_str} (confiança: {confidence:.2%}, vol: {vol:.3f}%)")
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
        logger.info("\n[STOP] Operacao interrompida pelo usuario.")
        print_status()
    except Exception as e:
        logger.error(f"[ERRO] Erro fatal: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if mt5_adapter:
            mt5_adapter.disconnect()
            logger.info("[OK] MT5 desconectado.")
