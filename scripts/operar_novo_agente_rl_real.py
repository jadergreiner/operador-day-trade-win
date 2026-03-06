#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Op operador de Novo Agente RL - Versao com MT5Adapter
Status: OPERACAO REAL (v5000)
Data: 06/03/2026 - Refatorado para usar MT5Adapter (arquitetura estavel)
"""

import logging
import os
import sys
import time
from pathlib import Path
from datetime import datetime, time as dtime
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
        logging.FileHandler(ROOT_DIR / 'outputs' / 'operar_agente_rl_real.log'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

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


def inicializar_adaptador_mt5() -> MT5Adapter:
    """Inicializa MT5Adapter com isolamento (arquitetura estavel)."""
    global mt5_adapter

    mt5_adapter = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
        terminal_exe_path=config.mt5_terminal_path,
    )

    if not mt5_adapter.connect():
        raise RuntimeError("Falha ao conectar no MT5")

    logger.info(f"OK MT5 conectado: {config.mt5_server}")
    return mt5_adapter


def inicializar_agente_rl() -> PipelineTreinamentoRL:
    """Carrega agente RL v5000 (5000 episodios)."""
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
        logger.info("OK Modelo RL pronto")
    else:
        raise RuntimeError(f"Modelo nao encontrado")

    return pipeline


def inicializar_rl_repo():
    """Inicializa repositório RL para persistência de episódios."""
    global rl_repo
    try:
        db_path = str(ROOT_DIR / "data" / "db" / "trading.db")
        session = get_session(db_path)
        rl_repo = SqliteRLRepository(session)
        rl_repo.seed_dimension_tables()
        logger.info("OK RL Repository pronto")
        return rl_repo
    except Exception as e:
        logger.error(f"Erro ao inicializar RL Repository: {e}")
        return None


def verificar_horario_trading() -> bool:
    """Horario de trading: 09:00-17:55 BRT."""
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

        logger.info(f"Dados: {len(data)} candles")
        return data

    except Exception as e:
        logger.error(f"Erro ao carregar dados: {e}")
        return None


def obter_acao_do_modelo(dados: pd.DataFrame) -> int:
    """Extrai acao do modelo RL usando AmbienteTrading para calcular o estado."""
    try:
        from src.application.services.novo_agente.ambiente_trading import AmbienteTradingMiniIndice

        # Criar ambiente temporário para calcular o estado atual
        # O agente precisa das últimas N velas para compor o vetor de 15 dimensões
        ambiente = AmbienteTradingMiniIndice(dados=dados)
        ambiente.reset()

        # Ajustar o índice para a última vela disponível
        ambiente._indice = len(dados) - 1

        estado = ambiente._calcular_estado()
        acao_id = pipeline._agente.selecionar_acao(estado)
        return acao_id

    except Exception as e:
        logger.error(f"Erro ao obter acao: {e}")
        return 0


def enviar_ordem_mt5adapter(acao: str, preco_atual: float) -> bool:
    """Envia ordem via MT5Adapter (com retry automático)."""
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

        logger.info(f"Enviando: {acao} @ {preco_atual} (SL: {sl}, TP: {tp})")

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
        logger.info(f"OK Ordem enviada! Ticket: {ticket}")
        return True

    except Exception as e:
        logger.error(f"Erro ao enviar ordem: {e}")
        return False


def monitorar_posicoes() -> bool:
    """Verifica se ha posicoes abertas."""
    try:
        positions = mt5_adapter.get_positions(Symbol(SIMBOLO))
        return len(positions) > 0 if positions else False
    except Exception:
        return False


def loop_operacao():
    """Loop principal de operacao em tempo real."""
    logger.info("--- INICIANDO OPERACAO REAL (V5000) ---")
    logger.info(f"Alvo: R${TARGET_LUCRO_DIARIO} | Stop: R${STOP_PERDA_DIARIA}")

    lucro_sessao = 0.0
    ciclo = 0

    while True:
        ciclo += 1

        if not verificar_horario_trading():
            logger.info("Fora do horario. Aguardando...")
            time.sleep(60)
            continue

        if lucro_sessao >= TARGET_LUCRO_DIARIO:
            logger.info(f"TARGET ATINGIDO: R${lucro_sessao:.2f}")
            break

        if lucro_sessao <= STOP_PERDA_DIARIA:
            logger.warning(f"STOP LOSS ACIONADO: R${lucro_sessao:.2f}")
            break

        if monitorar_posicoes():
            logger.info("Posicao em aberto. Aguardando...")
            time.sleep(30)
            continue

        logger.info(f"[{ciclo}] Consultando mercado...")
        dados = carregar_dados_mt5(SIMBOLO, n_candles=100)

        if dados is None or len(dados) < 20:
            logger.warning("Dados insuficientes. Aguardando 30s...")
            time.sleep(30)
            continue

        try:
            acao_id = obter_acao_do_modelo(dados)
            mapeamento = {1: "Comprar", 0: "Aguardar", 2: "Vender"}
            acao_str = mapeamento.get(acao_id, "Aguardar")
            preco_atual = float(dados['close'].iloc[-1])
            preco_aberto = float(dados['open'].iloc[-1])

            if acao_str != "Aguardar":
                sucesso = enviar_ordem_mt5adapter(acao_str, preco_atual)
                if sucesso:
                    # [NEW] Persistir episódio RL após ordem enviada
                    if rl_repo:
                        try:
                            episode_id = str(uuid.uuid4())
                            episode = {
                                "episode_id": episode_id,
                                "timestamp": datetime.now(),
                                "source": "RL_AGENT_V5000",
                                "win_price": preco_atual,
                                "win_open_price": preco_aberto,
                                "action": acao_str.upper(),
                                "symbol": SIMBOLO,
                                "ciclo": ciclo,
                            }
                            rl_repo.save_episode(episode)
                            logger.info(f"[RL] Episódio persistido: {episode_id[:8]}...")
                        except Exception as e:
                            logger.warning(f"[RL] Erro ao persistir: {e}")
                logger.info("Sinal AGUARDAR. Proxima em 2 minutos.")
                time.sleep(120)

        except Exception as e:
            logger.error(f"Erro no ciclo: {e}")
            time.sleep(30)


if __name__ == "__main__":
    try:
        logger.info("Inicializando...")
        inicializar_adaptador_mt5()
        inicializar_agente_rl()
        inicializar_rl_repo()  # [NEW] Inicializar repositório RL

        loop_operacao()

    except KeyboardInterrupt:
        logger.info("Operacao interrompida.")
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if mt5_adapter:
            mt5_adapter.disconnect()
            logger.info("MT5 desconectado.")
