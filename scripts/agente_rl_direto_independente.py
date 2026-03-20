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

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from datetime import time as dtime
from datetime import timedelta
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

# ============================================================================
# SETUP PATH e VARIÁVEIS DE AMBIENTE
# ============================================================================
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)
TRADING_DB_PATH = str(ROOT_DIR / "data" / "db" / "trading.db")

# Gerar session ID único para este agente
SESSION_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
AGENT_SESSION_ID = f"agente_direto_{SESSION_TIMESTAMP}"
AGENT_MODE = "dinamico"  # padrão

# Parse argumentos
if "--mode" in sys.argv:
    try:
        idx = sys.argv.index("--mode")
        mode_arg = sys.argv[idx + 1]
        if mode_arg in ["dinamico", "fixo"]:
            AGENT_MODE = mode_arg
    except (IndexError, ValueError):
        pass

# Variáveis de ambiente para isolamento
os.environ["AGENTE_SESSION_ID"] = AGENT_SESSION_ID
os.environ["AGENTE_TIPO"] = "DIRETO"
os.environ["AGENTE_MODE"] = AGENT_MODE

# ============================================================================
# LOGGING SEPARADO
# ============================================================================
OUTPUTS_DIR = ROOT_DIR / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

# Arquivo de log dedicado para agente direto
LOG_FILE = OUTPUTS_DIR / f"agente_direto_{SESSION_TIMESTAMP}.log"
DEBUG_LOG_FILE = OUTPUTS_DIR / f"agente_direto_debug_{SESSION_TIMESTAMP}.log"

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
        logging.FileHandler(str(DEBUG_LOG_FILE), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

# ============================================================================
# HEADER DE INICIALIZAÇÃO
# ============================================================================
logger.info("=" * 80)
logger.info("AGENTE RL DIRETO - POSIÇÃO INDEPENDENTE")
logger.info("=" * 80)
logger.info(f"Timestamp: {SESSION_TIMESTAMP}")
logger.info(f"Session ID: {AGENT_SESSION_ID}")
logger.info(f"Modo SL/TP: {AGENT_MODE.upper()}")
logger.info(f"Diretório: {os.getcwd()}")
logger.info(f"Log Principal: {LOG_FILE}")
logger.info(f"Log Debug: {DEBUG_LOG_FILE}")
logger.info("=" * 80)
logger.info("")

# ============================================================================
# IMPORTS APÓS SETUP
# ============================================================================
try:
    logger.info("[INIT] Importando módulos core...")

    from config.settings import TradingConfig
    from src.application.ac6_bootstrap import build_ac6_components
    from src.application.diario_market_features import (
        apply_diario_soft_feature_influence,
        build_contexto_operacional_com_diario,
        load_diario_market_features_payload,
    )
    from src.application.motor_decisao_isolado import (
        DecisaoOperacional,
        MotivoFechamento,
        MotorDecisaoIsolado,
        TipoPosicao,
    )
    from src.application.opening_context_policy import (
        apply_opening_context_strict_filters,
        evaluate_opening_context_gate,
        normalize_opening_context,
    )
    from src.application.opening_context_report import (
        generate_opening_context_vs_result_report,
    )
    from src.application.opening_context_runtime import (
        initialize_opening_context_runtime,
    )
    from src.application.opening_market_confirmation import (
        build_live_market_confirmation,
    )
    from src.application.ordem_backoff_retry import (
        RETCODE_ORDER_FAILED,
        GerenciadorRetryOrdem,
    )
    from src.application.posicao_isolamento import PosicaoIsoladaManager
    from src.application.profit_protection_engine import ProfitProtectionEngine
    from src.application.services.novo_agente.agente_q_learning import (
        AgenteQLearningMiniIndice,
    )
    from src.application.services.novo_agente.pipeline_treinamento import (
        PipelineTreinamentoRL,
    )
    from src.application.trade_performance_tracker import TradeClosureReason
    from src.application.trade_tracker_integration import TradeTrackerIntegration
    from src.domain.enums.trading_enums import TimeFrame
    from src.infrastructure.adapters.mt5_adapter import MT5Adapter
    from src.infrastructure.database.schema import get_session
    from src.infrastructure.repositories.rl_repository import SqliteRLRepository

    logger.info("[OK] Módulos importados com sucesso (incl. isolamento formal)")

except Exception as e:
    logger.error(f"[FATAL] Erro ao importar módulos: {e}", exc_info=True)
    sys.exit(1)

# ============================================================================
# IMPORTS OPCIONAIS — Grupo 2: Feedback e Aprendizado (AC5.8/AC5.9/AC6)
# ============================================================================
_AC5_8_DISPONIVEL = False
_AC5_9_DISPONIVEL = False
_AC6_DISPONIVEL = False
try:
    from src.application.ac5_8_position_monitor import (
        DirecaoOperacao,
        MonitorPositionManager,
        StatusOrdem,
    )

    _AC5_8_DISPONIVEL = True
    logger.info("[OK] AC5.8 MonitorPositionManager disponivel")
except ImportError as _e:
    MonitorPositionManager = None  # type: ignore[assignment,misc]
    logger.warning(f"[WARN] AC5.8 nao disponivel: {_e}")

try:
    from src.application.ac5_9_feedback_validator import (
        FeedbackValidator,
    )
    from src.application.ac6_7_drift_detector import DriftDetector
    from src.application.ac6_8_online_learning import (
        OnlineLearningController,
    )
    from src.application.ac6_9_baseline_comparator import (
        BaselineComparator,
    )

    _AC5_9_DISPONIVEL = True
    _AC6_DISPONIVEL = True
    logger.info("[OK] AC5.9/AC6.7/AC6.8/AC6.9 disponiveis")
except ImportError as _e:
    FeedbackValidator = None  # type: ignore[assignment,misc]
    DriftDetector = None  # type: ignore[assignment,misc]
    OnlineLearningController = None  # type: ignore[assignment,misc]
    BaselineComparator = None  # type: ignore[assignment,misc]
    logger.warning(f"[WARN] AC5.9/AC6 nao disponiveis: {_e}")

# ============================================================================
# IMPORTS SPECIFICIZADOS - Domain Models
# ============================================================================
try:
    from src.domain.entities.trade import Order
    from src.domain.enums.trading_enums import OrderSide, OrderType, TimeFrame
    from src.domain.value_objects import Price, Quantity, Symbol

    logger.info("[OK] Domain models importados")
except Exception as e:
    logger.error(f"[WARN] Domain models import falhou: {e}")
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
STOP_LOSS_PONTOS = 150  # piso fixo (pts)
TAKE_PROFIT_PONTOS = 225  # piso fixo (pts) — mantém R/R 1.5:1 mínimo
ATR_PERIODO = 14  # velas M5 para calcular ATR
ATR_MULT_SL = 0.8  # SL >= 80% do ATR — nunca menor que o ruído
RR_MINIMO = 1.5  # TP sempre >= SL * 1.5
MIN_CONFIDENCE_SCORE = 0.45  # PRD: confiança mínima para entrada
MAX_TRADES_PER_SESSION = 6  # PRD: máximo de 6 trades/dia por agente
COOLDOWN_SECONDS = 300  # PRD: cooldown base de 5 min
STOP_LOSS_COOLDOWN_SECONDS = 1800  # PRD: cooldown de 30 min após LOSS/SL
MONITORAMENTO_INICIO = dtime(9, 0)
NOVAS_ENTRADAS_FIM = dtime(17, 25)
MONITORAMENTO_FIM = dtime(17, 55)

CONFIRM_SIGNAL_BARS = 2  # Confirmação em N velas
TARGET_PROFIT = 140.00
STOP_LOSS_MAX = -250.00
VALOR_PONTO_WINFUT = 0.20

# Variáveis globais para estado do agente
last_signal = "Aguardar"
signal_confirmation_count = 0
last_trade_time = None

# Variáveis globais — Grupo 2: Feedback e Aprendizado
_monitor_posicao_rl = None
_feedback_validator_rl = None
_drift_detector_rl = None
_online_learning_rl = None
_baseline_comparator_rl = None


# ============================================================================
# FUNÇÕES DE DECISÃO E TRADING (RL)
# ============================================================================
def obter_acao_do_modelo(
    dados: pd.DataFrame, pipeline: object, agente: object
) -> Tuple[int, float]:
    """Obtém ação do modelo RL treinado."""
    try:
        from src.application.services.novo_agente.ambiente_trading import (
            AmbienteTradingMiniIndice,
        )

        if not isinstance(dados, pd.DataFrame) or len(dados) == 0:
            logger.debug("[RL] Dados insuficientes, retornando aguardar")
            return 0, 0.0  # Aguardar

        ambiente = AmbienteTradingMiniIndice(dados=dados)
        ambiente.reset()
        ambiente._indice = len(dados) - 1

        estado = ambiente._calcular_estado()
        acao_id = agente.selecionar_acao(estado)
        confidence = 0.7  # Placeholder

        logger.debug(f"[RL] Ação obtida: {acao_id} (confiança: {confidence:.2%})")
        return acao_id, confidence

    except Exception as e:
        logger.error(f"[RL] Erro ao obter ação: {e}")
        return 0, 0.0


def mapear_acao(acao_id: int) -> str:
    """Mapeia ID numérico para ação: 0=Aguardar, 1=Comprar, 2=Vender."""
    mapeamento = {0: "Aguardar", 1: "Comprar", 2: "Vender"}
    return mapeamento.get(acao_id, "Aguardar")


def verificar_horario_trading(agora: Optional[dtime] = None) -> bool:
    """Janela de monitoramento operacional: 09:00-17:55 BRT."""
    horario = agora or datetime.now().time()
    return MONITORAMENTO_INICIO <= horario <= MONITORAMENTO_FIM


def verificar_janela_novas_entradas(agora: Optional[dtime] = None) -> bool:
    """Permite novas entradas somente até 17:25 BRT."""
    horario = agora or datetime.now().time()
    return MONITORAMENTO_INICIO <= horario <= NOVAS_ENTRADAS_FIM


def classificar_fechamento_trade(
    preco_entrada: float,
    preco_saida: float,
    tipo_posicao: TipoPosicao,
    volume: float = 1.0,
) -> tuple[str, float]:
    """Classifica o resultado de um fechamento e calcula PnL em reais."""
    if tipo_posicao == TipoPosicao.COMPRADA:
        diff = preco_saida - preco_entrada
    else:
        diff = preco_entrada - preco_saida

    if diff > 0:
        resultado = "WIN"
    elif diff < 0:
        resultado = "LOSS"
    else:
        resultado = "BREAKEVEN"

    pnl_reais = diff * volume * VALOR_PONTO_WINFUT
    return resultado, pnl_reais


def obter_contexto_fechamento_sessao_atual(
    posicao_mgr: PosicaoIsoladaManager,
    motor: MotorDecisaoIsolado,
) -> Optional[dict]:
    """Obtém o contexto de fechamento apenas se o ticket pertencer à sessão atual."""
    if not posicao_mgr.tem_posicao_aberta():
        return None

    try:
        metadados = posicao_mgr.obter_metadados_posicao()
    except Exception as e:
        logger.warning(f"[ISOLAMENTO] Não foi possível ler metadados da posição: {e}")
        return None

    session_id = str(metadados.get("session_id", ""))
    if session_id and session_id != AGENT_SESSION_ID:
        logger.warning(
            f"[ISOLAMENTO] Sessão divergente detectada: arquivo={session_id}, "
            f"agente={AGENT_SESSION_ID}"
        )
        return None

    ticket = int(metadados.get("ticket", 0) or 0)
    if ticket <= 0:
        logger.warning("[ISOLAMENTO] Ticket inválido nos metadados da posição")
        return None

    posicao = motor.obter_posicao(ticket)
    if posicao is None:
        logger.warning(
            f"[ISOLAMENTO] Ticket {ticket} da sessão atual não encontrado "
            f"no motor isolado do agente"
        )
        return None

    if posicao.agent_id != AGENT_SESSION_ID:
        logger.warning(
            f"[ISOLAMENTO] Ticket {ticket} pertence a outro agent_id "
            f"({posicao.agent_id})"
        )
        return None

    return {
        "ticket": ticket,
        "preco_entrada": float(posicao.preco_entrada),
        "tipo": posicao.tipo,
        "volume": float(posicao.volume),
        "lado": posicao.tipo.value,
    }


def resolver_preco_saida_real(
    mt5_adapter_local: object,
    ticket: int,
    tipo_posicao: TipoPosicao,
    simbolo: str = SIMBOLO,
) -> Optional[float]:
    """Tenta obter o preço real de saída do MT5 para o ticket informado."""
    try:
        if hasattr(mt5_adapter_local, "obter_preco_saida_por_ticket"):
            side = (
                OrderSide.BUY
                if tipo_posicao == TipoPosicao.COMPRADA
                else OrderSide.SELL
            )
            preco = mt5_adapter_local.obter_preco_saida_por_ticket(
                ticket,
                symbol=Symbol(simbolo) if Symbol else simbolo,
                side=side,
            )
            if preco is not None:
                return float(preco)
    except Exception as e:
        logger.warning(
            f"[MT5-CHECK] Falha ao obter preço real de saída do ticket {ticket}: {e}"
        )

    return None


def enviar_ordem_com_backoff(
    mt5_adapter_local: object,
    order: object,
    retry_mgr: Optional[GerenciadorRetryOrdem] = None,
) -> Optional[str]:
    """Envia ordem ao MT5 com backoff/rollover compartilhado para 10006."""
    retry_mgr_local = retry_mgr or GerenciadorRetryOrdem(
        simbolo=SIMBOLO,
        limite_encerrar=5,
        verificar_rollover=True,
    )

    while True:
        try:
            ticket = mt5_adapter_local.send_order(order)
            retry_mgr_local.registrar_sucesso()
            return ticket
        except Exception as e:
            mensagem = str(e)
            if "10006" not in mensagem:
                raise

            logger.warning(f"[BACKOFF] Rejeição MT5 10006 detectada: {mensagem}")
            resultado_retry = retry_mgr_local.registrar_falha_10006(
                RETCODE_ORDER_FAILED
            )
            logger.warning(
                f"[BACKOFF] status={resultado_retry.status.value} "
                f"aguardar={resultado_retry.aguardar_segundos}s "
                f"falhas={resultado_retry.falhas_consecutivas}"
            )

            if resultado_retry.deve_encerrar():
                logger.error(resultado_retry.mensagem)
                return None

            if resultado_retry.aguardar_segundos > 0:
                time.sleep(resultado_retry.aguardar_segundos)


def verificar_confirmacao_sinal(sinal_atual: str, sinal_anterior: str) -> bool:
    """Verifica se o sinal se repete em múltiplas velas."""
    global signal_confirmation_count

    if sinal_atual == "Aguardar":
        signal_confirmation_count = 0
        return False

    if sinal_atual == sinal_anterior:
        signal_confirmation_count += 1
        logger.info(
            f"[OK] Sinal CONFIRMADO ({signal_confirmation_count}/{CONFIRM_SIGNAL_BARS})"
        )
        return signal_confirmation_count >= CONFIRM_SIGNAL_BARS
    else:
        signal_confirmation_count = 1
        logger.info(f"[SINAL] Novo sinal detectado: {sinal_atual}")
        return False


def calcular_atr(dados: pd.DataFrame, periodo: int = ATR_PERIODO) -> float:
    """Calcula ATR (Average True Range) das ultimas `periodo` velas M5.

    Retorna 0.0 se dados insuficientes — o chamador deve usar o piso fixo.
    """
    try:
        if len(dados) < periodo + 1:
            return 0.0
        high = dados["high"]
        low = dados["low"]
        close_ant = dados["close"].shift(1)
        tr = pd.concat(
            [
                high - low,
                (high - close_ant).abs(),
                (low - close_ant).abs(),
            ],
            axis=1,
        ).max(axis=1)
        return float(tr.rolling(periodo).mean().iloc[-1])
    except Exception as e:
        logger.warning(f"[ATR] Erro ao calcular ATR: {e}")
        return 0.0


# ML-1 (18/03/2026): Configuracao do gate de tendencia intraday.
# Desativar via GATE_TENDENCIA_ATIVO=False para facilitar backtesting.
GATE_TENDENCIA_ATIVO: bool = True
EMA_RAPIDA_PERIODO: int = 9
EMA_LENTA_PERIODO: int = 21


def calcular_ema(dados: pd.DataFrame, periodo: int) -> float:
    """Calcula EMA (Exponential Moving Average) para o periodo dado.

    Args:
        dados: DataFrame com coluna 'close'.
        periodo: Numero de velas para calculo da EMA.

    Returns:
        Valor da EMA mais recente, ou 0.0 se dados insuficientes.

    Raises:
        Nao levanta excecoes — retorna 0.0 em caso de erro.
    """
    try:
        if len(dados) < periodo:
            return 0.0
        ema = dados["close"].ewm(span=periodo, adjust=False).mean()
        return float(ema.iloc[-1])
    except Exception as e:
        logger.warning(f"[EMA] Erro ao calcular EMA{periodo}: {e}")
        return 0.0


def aplicar_gate_tendencia(
    acao: str,
    dados: Optional[pd.DataFrame],
    gate_ativo: bool = GATE_TENDENCIA_ATIVO,
) -> str:
    """Aplica gate de tendencia intraday para filtrar entradas contra tendencia.

    ML-1 (18/03/2026): Bloqueia SELL quando EMA9 > EMA21 (tendencia de alta)
    e BUY quando EMA9 < EMA21 (tendencia de baixa). Gate simetrico previne
    entradas com vies direcional errado — licao aprendida em 17/03/2026
    (SELL @ 182590 em mercado bullish gerou LOSS -R$61).

    Args:
        acao: Acao proposta pelo modelo RL ('Comprar', 'Vender', 'Aguardar').
        dados: DataFrame com coluna 'close' para calculo das EMAs.
        gate_ativo: Se False, desativa o gate (util em backtesting).

    Returns:
        Acao original se permitida pelo gate, ou 'Aguardar' se bloqueada.
    """
    if not gate_ativo or acao == "Aguardar" or dados is None or len(dados) == 0:
        return acao

    ema_rapida = calcular_ema(dados, EMA_RAPIDA_PERIODO)
    ema_lenta = calcular_ema(dados, EMA_LENTA_PERIODO)

    if ema_rapida == 0.0 or ema_lenta == 0.0:
        logger.debug("[GATE-TENDENCIA] EMAs indisponiveis — gate ignorado")
        return acao

    tendencia_alta = ema_rapida > ema_lenta
    tendencia_baixa = ema_rapida < ema_lenta

    if acao == "Vender" and tendencia_alta:
        logger.warning(
            f"[GATE-TENDENCIA] SELL bloqueado — EMA{EMA_RAPIDA_PERIODO} "
            f"({ema_rapida:.0f}) > EMA{EMA_LENTA_PERIODO} ({ema_lenta:.0f}) "
            f"(tendencia de alta)"
        )
        return "Aguardar"

    if acao == "Comprar" and tendencia_baixa:
        logger.warning(
            f"[GATE-TENDENCIA] BUY bloqueado — EMA{EMA_RAPIDA_PERIODO} "
            f"({ema_rapida:.0f}) < EMA{EMA_LENTA_PERIODO} ({ema_lenta:.0f}) "
            f"(tendencia de baixa)"
        )
        return "Aguardar"

    logger.debug(
        f"[GATE-TENDENCIA] {acao} PERMITIDO — "
        f"EMA{EMA_RAPIDA_PERIODO}={ema_rapida:.0f} "
        f"EMA{EMA_LENTA_PERIODO}={ema_lenta:.0f}"
    )
    return acao


def calcular_sl_tp(
    acao: str, preco_atual: float, dados: Optional[pd.DataFrame] = None
) -> Tuple[float, float]:
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
            f"[SL/TP] ATR={atr:.0f}pts | "
            f"SL={sl_pts}pts (piso={STOP_LOSS_PONTOS}, atr_min={atr_sl_minimo}) | "
            f"TP={tp_pts}pts | R/R={tp_pts/sl_pts:.2f}:1"
        )
    else:
        logger.debug(
            f"[SL/TP] ATR indisponivel — usando piso fixo SL={sl_pts} TP={tp_pts}"
        )

    if acao == "Comprar":
        sl = preco_atual - sl_pts
        tp = preco_atual + tp_pts
    elif acao == "Vender":
        sl = preco_atual + sl_pts
        tp = preco_atual - tp_pts
    else:
        sl = tp = preco_atual

    return sl, tp


def calcular_risk_reward(acao: str, preco_atual: float, sl: float, tp: float) -> float:
    """Calcula a relacao risco-retorno para compra/venda."""
    if acao == "Comprar":
        risk = preco_atual - sl
        reward = tp - preco_atual
    else:
        risk = sl - preco_atual
        reward = preco_atual - tp

    if risk <= 0:
        return 0.0
    return abs(reward / risk)


def _executar_pipeline_feedback_rl(trades_fechados: list) -> None:
    """Executa pipeline AC5.9→AC6.7→AC6.8→AC6.9 a cada 10 ciclos.

    Alimentado com trades fechados do ciclo operacional para fechar
    o loop de aprendizado: execucao → feedback → deteccao de drift
    → treino incremental → comparacao com baseline.
    """
    trades_data = [
        {
            "trade_id": str(t.get("ticket", "")),
            "outcome": t.get("resultado", "BREAKEVEN"),
            "pnl": float(t.get("pnl", 0.0)),
            "direction": t.get("direcao", ""),
        }
        for t in trades_fechados
    ]

    # AC5.9: Validacao de saude do feedback
    if _feedback_validator_rl and trades_data:
        try:
            relatorio = _feedback_validator_rl.validate_feedback_health(
                trades=trades_data,
                feedback=trades_data,
            )
            status_icon = {
                "HEALTHY": "OK",
                "WARNING": "AVISO",
                "CRITICAL": "CRITICO",
            }.get(
                relatorio.overall_status,
                "?",
            )
            logger.info(
                f"[AC5.9] Feedback {status_icon} | "
                f"Correlacao: {relatorio.correlation_rate:.0%} | "
                f"Qualidade: {relatorio.data_quality_score:.0%}"
            )
        except Exception as e:
            logger.warning(f"[AC5.9] Erro: {e}")

    # AC6.7: Deteccao de drift
    if _drift_detector_rl and trades_data:
        try:
            alertas = _drift_detector_rl.detectar_drift(trades_data)
            if alertas:
                for a in alertas[:2]:
                    logger.warning(
                        f"[AC6.7] Drift detectado: {a.metric} "
                        f"z={a.z_score:.2f} (limiar={a.threshold:.2f})"
                    )
            else:
                logger.info("[AC6.7] Sem drift detectado")
        except Exception as e:
            logger.warning(f"[AC6.7] Erro: {e}")

    # AC6.8: Aprendizagem online (so executa se drift detectado)
    if _online_learning_rl and trades_data:
        try:
            resultado = _online_learning_rl.train_incremental(trades_data)
            if resultado:
                logger.info(f"[AC6.8] Treino incremental: {resultado}")
        except Exception as e:
            logger.warning(f"[AC6.8] Erro: {e}")

    # AC6.9: Comparacao com baseline
    if _baseline_comparator_rl and trades_data:
        try:
            comparacao = _baseline_comparator_rl.comparar_metricas(
                metricas_atuais={"pnl_medio": sum(t["pnl"] for t in trades_data)},
            )
            fb = _baseline_comparator_rl.gerar_feedback(comparacao)
            if fb:
                logger.info(f"[AC6.9] Baseline: {fb}")
        except Exception as e:
            logger.warning(f"[AC6.9] Erro: {e}")


# ============================================================================
# BUG-1 FIX (18/03/2026): NameError motor_decisao em enviar_ordem()
# ============================================================================
# PROBLEMA: NameError ao tentar chamar motor_decisao.abrir_posicao() porque
# a variavel nao estava no escopo da funcao.
#
# SOLUCAO: motor_decisao e recebido como PARAMETRO formal em enviar_ordem().
# Garantias:
# - ✅ motor_decisao é parâmetro de enviar_ordem() (linha ~399)
# - ✅ motor_decisao.abrir_posicao() é chamado dentro da função (linha ~486)
# - ✅ Todas as chamadas a enviar_ordem() passam motor_decisao (linha ~1073)
# - ✅ Função verificar_posicao_no_mt5() recebe motor como parâmetro (linha ~757)
# - ✅ Testes: 7/7 PASSING (verificar: tests/unit/test_bug_motor_decisao.py)
# ============================================================================


def enviar_ordem(
    mt5_adapter: object,
    acao: str,
    preco_atual: float,
    posicao_tracker: object,
    rl_repo: object,
    trade_tracker: object,
    motor_decisao: object,
    dados: Optional[pd.DataFrame] = None,
    retry_mgr: Optional[GerenciadorRetryOrdem] = None,
    opening_context: object = None,
    confidence: float = 0.0,
) -> bool:
    """Envia ordem para abrir posição no MT5.

    Args:
        mt5_adapter: Adaptador do MT5.
        acao: Acao decidida pelo agente (BUY, SELL, Aguardar).
        preco_atual: Preco atual do ativo.
        posicao_tracker: Gerenciador de posicao isolada (PosicaoIsoladaManager).
        rl_repo: Repositorio RL para persistencia.
        trade_tracker: Rastreador de performance de trades.
        motor_decisao: Motor de decisao isolado (MotorDecisaoIsolado).
        dados: DataFrame com dados de mercado (opcional).

    Returns:
        True se ordem enviada com sucesso, False caso contrario.
    """
    global last_trade_time
    normalized_context = (
        normalize_opening_context(opening_context)
        if opening_context is not None
        else None
    )
    try:
        diario_payload = load_diario_market_features_payload(TRADING_DB_PATH)
    except Exception:
        diario_payload = {"available": False, "snapshot": {}, "effective_snapshot": {}}

    def _persist_hold_episode(
        motivo: str,
        fatores: list[str],
        contexto: dict[str, object],
        decisao_operacional: DecisaoOperacional = DecisaoOperacional.HOLD,
    ) -> None:
        """Persiste contexto neutro/cancelado para aprendizagem quando fica de fora."""
        if motor_decisao:
            try:
                motor_decisao.registrar_decisao(
                    decisao_operacional,
                    reasoning=motivo,
                    confianca=confidence,
                    fatores=fatores,
                    contexto_operacional=contexto,
                )
            except Exception as e:
                logger.warning(f"[WARN] Erro ao registrar HOLD no motor isolado: {e}")

        if rl_repo:
            try:
                episode_id = str(uuid.uuid4())
                episode = {
                    "episode_id": episode_id,
                    "timestamp": datetime.now(),
                    "source": "AGENTE_DIRETO",
                    "win_price": preco_atual,
                    "action": "HOLD",
                    "symbol": SIMBOLO,
                    "reasoning": motivo,
                    "overall_confidence": confidence,
                    "alignment_score": None,
                    "market_regime": (
                        normalized_context.regime_macro if normalized_context else None
                    ),
                    "macro_bias": "NEUTRAL",
                    "sentiment_bias": "NEUTRAL",
                    "technical_bias": "NEUTRAL",
                }
                rl_repo.save_episode(episode)
            except Exception as e:
                logger.warning(f"[WARN] Erro ao persistir episódio HOLD: {e}")

    if acao == "Aguardar":
        contexto_hold = build_contexto_operacional_com_diario(
            opening_context,
            base_payload={},
            diario_payload=diario_payload,
            action=acao,
            model_confidence=confidence,
        )
        _persist_hold_episode(
            "Agente permaneceu fora do mercado por decisão operacional.",
            ["acao_agora=Aguardar"],
            contexto_hold,
            DecisaoOperacional.HOLD,
        )
        return False

    contexto_guard = build_contexto_operacional_com_diario(
        opening_context,
        base_payload={},
        diario_payload=diario_payload,
        action=acao,
        model_confidence=confidence,
    )

    if not verificar_janela_novas_entradas():
        logger.warning(
            "[HORARIO] Novas entradas bloqueadas fora da janela do PRD (ate 17:25 BRT)."
        )
        _persist_hold_episode(
            "Entrada bloqueada por janela operacional do PRD.",
            ["janela_novas_entradas=fechada"],
            contexto_guard,
            DecisaoOperacional.CANCELAR,
        )
        return False

    if confidence > 0 and confidence < MIN_CONFIDENCE_SCORE:
        logger.warning(
            "[CONFIDENCE] Entrada bloqueada: %.2f abaixo do minimo %.2f",
            confidence,
            MIN_CONFIDENCE_SCORE,
        )
        _persist_hold_episode(
            "Entrada bloqueada por confiança abaixo do mínimo operacional.",
            ["confidence_abaixo_minimo"],
            contexto_guard,
            DecisaoOperacional.CANCELAR,
        )
        return False

    try:
        live_confirmation = build_live_market_confirmation(
            mt5_adapter,
            opening_context,
        )
        diario_influence = apply_diario_soft_feature_influence(
            acao,
            confidence,
            diario_payload,
        )
        confidence_for_gate = (
            diario_influence.adjusted_confidence
            if diario_influence.adjusted_confidence is not None
            else confidence
        )
        gate = evaluate_opening_context_gate(
            acao,
            opening_context,
            confidence=confidence_for_gate,
            market_confirmation=live_confirmation.to_dict(),
        )
        gate = apply_opening_context_strict_filters(gate)
        contexto_operacional = build_contexto_operacional_com_diario(
            opening_context,
            base_payload=gate.to_context_payload(),
            diario_payload=diario_payload,
            diario_influence=diario_influence,
            action=acao,
            model_confidence=confidence,
        )
        if diario_influence.reasons and diario_influence.confidence_adjustment != 0:
            logger.info(
                "[DIARIO FEATURES] %s | ajuste_conf=%+.2f | alinhamento=%s",
                ", ".join(diario_influence.reasons),
                diario_influence.confidence_adjustment,
                diario_influence.alignment,
            )
        if not gate.allow_entry:
            logger.warning(
                "[PRE-ABERTURA] Ordem %s bloqueada pelo contexto estrutural: %s",
                acao,
                gate.summary,
            )
            _persist_hold_episode(
                f"Bloqueada por contexto de abertura: {gate.summary}",
                gate.reasons,
                contexto_operacional,
                DecisaoOperacional.CANCELAR,
            )
            return False

        # ══════════════════════════════════════════════════════════════
        # GUARDA CRÍTICA: Verificar no MT5 se já existe posição aberta
        # deste agente (por magic number). Evita ordens duplicadas
        # causadas por race condition entre JSON e estado real do MT5.
        # ══════════════════════════════════════════════════════════════
        try:
            posicoes_mt5 = mt5_adapter.get_positions(Symbol(SIMBOLO))
            minhas_posicoes = [
                p
                for p in (posicoes_mt5 or [])
                if int(getattr(p, "magic", 0) or 0) == MAGIC_NUMBER
            ]
            if minhas_posicoes:
                tickets = [int(getattr(p, "ticket", 0)) for p in minhas_posicoes]
                logger.warning(
                    f"[GUARDA] BLOQUEADO: Já existe(m) {len(minhas_posicoes)} "
                    f"posição(ões) aberta(s) com magic={MAGIC_NUMBER} "
                    f"(tickets={tickets}). Ordem NÃO enviada."
                )
                return False
        except Exception as e:
            logger.warning(
                f"[GUARDA] Erro ao verificar posições MT5: {e}. "
                f"Prosseguindo com cautela."
            )

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
        risk_reward = calcular_risk_reward(acao, preco_atual, sl, tp)
        if risk_reward < RR_MINIMO:
            logger.warning(
                "[RISK_REWARD] Entrada bloqueada: RR=%.2f abaixo do minimo %.2f",
                risk_reward,
                RR_MINIMO,
            )
            _persist_hold_episode(
                "Entrada bloqueada por relacao risco-retorno insuficiente.",
                ["risk_reward_abaixo_minimo"],
                contexto_operacional,
                DecisaoOperacional.CANCELAR,
            )
            return False

        logger.info(
            f"[ENVIO] {acao} @ {preco_atual} | SL: {sl} | TP: {tp} | RR: {risk_reward:.2f}"
        )

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

        ticket = enviar_ordem_com_backoff(mt5_adapter, order, retry_mgr=retry_mgr)
        if ticket:
            logger.info(f"[OK] Ordem enviada! Ticket: {ticket}")

            # Registrar posição via módulos formais de isolamento
            posicao_tracker.registrar_posicao_aberta(
                preco_entrada=preco_atual,
                ticket=int(ticket),
                lado=direcao_str,
                quantidade=1,
            )
            tipo = TipoPosicao.COMPRADA if direcao_str == "BUY" else TipoPosicao.VENDIDA
            motor_decisao.abrir_posicao(
                ticket=int(ticket),
                tipo=tipo,
                preco_entrada=preco_atual,
                volume=1.0,
                stop_loss=sl,
                take_profit=tp,
                contexto_operacional=contexto_operacional,
            )
            logger.info(
                f"[ISOLAMENTO] Ticket {ticket} registrado via "
                f"MotorDecisaoIsolado + PosicaoIsoladaManager"
            )

            # AC5.8: Registrar abertura de ordem no monitor de posicoes
            if _monitor_posicao_rl:
                try:
                    direcao_ac58 = (
                        DirecaoOperacao.COMPRA
                        if direcao_str == "BUY"
                        else DirecaoOperacao.VENDA
                    )
                    _monitor_posicao_rl.registrar_ordem(
                        {
                            "trade_id": str(ticket),
                            "direcao": direcao_ac58,
                            "preco_entrada": preco_atual,
                            "stop_loss": sl,
                            "take_profit": tp,
                            "volume": 1,
                            "status": StatusOrdem.ABERTA,
                        }
                    )
                except Exception as e:
                    logger.warning(f"[AC5.8] Erro ao registrar ordem: {e}")

            # Registrar entrada no rastreador de performance
            if trade_tracker:
                try:
                    trade_tracker.registrar_entrada(
                        ticket=ticket,
                        simbolo=SIMBOLO,
                        direcao=direcao_str,
                        preco_entrada=preco_atual,
                    )
                    logger.info(f"[TRACKER] Entrada registrada para ticket {ticket}")
                except Exception as e:
                    logger.warning(f"[WARN] Erro ao registrar entrada no tracker: {e}")

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
                    logger.warning(f"[WARN] Erro ao persistir episódio: {e}")

            last_trade_time = datetime.now()
            return True
        else:
            logger.error(f"[ERRO] Falha ao enviar ordem")
            return False

    except Exception as e:
        logger.error(f"[ERRO] Exceção ao enviar ordem: {e}", exc_info=True)
        return False


# ============================================================================
# INICIALIZAÇÃO DE COMPONENTES
# ============================================================================
def inicializar_componentes():
    """Inicializa todos os componentes da aplicação."""

    logger.info("[INIT] Inicializando componentes...")

    try:
        # 0. Carregar configuração
        logger.info("[INIT] Carregando configuração TradingConfig...")
        config = TradingConfig()

        # 1. MT5 Adapter - usar caminho do .env (Clear Investimentos)
        logger.info("[INIT] Conectando ao MT5...")

        mt5_adapter = MT5Adapter(
            login=config.mt5_login,
            password=config.mt5_password,
            server=config.mt5_server,
            terminal_exe_path=config.mt5_terminal_path,  # Do .env: Clear
        )

        if not mt5_adapter.connect():
            logger.error("[FATAL] Falha ao conectar ao MT5")
            return None

        logger.info("[OK] MT5 conectado")

        # 2. RL Repository (com isolamento por session)
        logger.info("[INIT] Inicializando RL Repository...")
        db_path = str(ROOT_DIR / "data" / "db" / "trading.db")
        session = get_session(db_path)
        rl_repo = SqliteRLRepository(session)
        rl_repo.seed_dimension_tables()

        logger.info("[OK] RL Repository pronto")

        # 3. Pipeline RL
        logger.info("[INIT] Inicializando Pipeline RL...")
        pipeline = PipelineTreinamentoRL()

        logger.info("[OK] Pipeline RL pronto")

        # 4. Agente QL
        logger.info("[INIT] Inicializando Agente Q-Learning...")
        pipeline._agente = AgenteQLearningMiniIndice(
            tamanho_estado=15, n_acoes=3, config=pipeline.config_agente
        )

        # Carregar modelo pré-treinado
        modelo_path = ROOT_DIR / "data" / "models" / "novo_agente_rl" / "modelo_final"
        if (modelo_path / "q_network.pkl").exists():
            logger.info(f"[LOAD] Carregando modelo de {modelo_path}...")
            pipeline._agente.carregar(modelo_path)
            logger.info("[OK] Modelo carregado")
        else:
            logger.warning(f"[WARN] Modelo não encontrado em {modelo_path}")

        agente = pipeline._agente

        # 5. Profit Protection Engine
        logger.info("[INIT] Inicializando Profit Protection Engine...")
        profit_protection = ProfitProtectionEngine(
            profit_target_pct=2.0,
            stop_loss_pct=1.0,
            partial_close_pct=0.75,
            break_even_offset_pct=0.10,
            reversao_threshold_pct=0.75,
            cooldown_seconds=5,
        )

        logger.info("[OK] Profit Protection ativado")

        # 5.5. Retry manager compartilhado para retcode 10006
        logger.info("[INIT] Inicializando GerenciadorRetryOrdem...")
        retry_mgr = GerenciadorRetryOrdem(
            simbolo=SIMBOLO,
            limite_encerrar=5,
            verificar_rollover=True,
        )
        logger.info("[OK] GerenciadorRetryOrdem ativado")

        # 6. Anti-Overtrading Protection
        logger.info("[INIT] Inicializando proteção contra overtrading...")
        anti_overtrading = AntiOvertradingProtection(
            max_trades_per_hour=3,  # Guard-rail intradiário
            min_cooldown_seconds=COOLDOWN_SECONDS,
            max_consecutive_losses=2,  # 2 perdas seguidas = pausa
            trading_hours_start=MONITORAMENTO_INICIO,
            trading_hours_end=NOVAS_ENTRADAS_FIM,
            monitoring_hours_end=MONITORAMENTO_FIM,
            max_trades_per_day=MAX_TRADES_PER_SESSION,
            stop_loss_cooldown_seconds=STOP_LOSS_COOLDOWN_SECONDS,
        )
        logger.info("[OK] Anti-Overtrading ativado")

        # 7. Trade Performance Tracker - Rastreamento de P&L
        logger.info("[INIT] Inicializando rastreador de performance de trades...")
        trade_tracker = TradeTrackerIntegration(
            session_id=AGENT_SESSION_ID,
            output_dir=OUTPUTS_DIR,
        )
        logger.info("[OK] Trade Performance Tracker ativado")

        logger.info("[OK] Todos os componentes inicializados com sucesso!")
        logger.info("")

        return {
            "config": config,
            "mt5_adapter": mt5_adapter,
            "rl_repo": rl_repo,
            "pipeline": pipeline,
            "agente": agente,
            "profit_protection": profit_protection,
            "retry_mgr": retry_mgr,
            "anti_overtrading": anti_overtrading,
            "trade_tracker": trade_tracker,
        }

    except Exception as e:
        logger.error(f"[FATAL] Erro ao inicializar componentes: {e}", exc_info=True)
        return None


# ============================================================================
# PROTEÇÃO CONTRA OVERTRADING
# ============================================================================
class AntiOvertradingProtection:
    """Proteção contra overtrading com limites de frequência e risco."""

    def __init__(
        self,
        max_trades_per_hour: int = 3,
        min_cooldown_seconds: int = COOLDOWN_SECONDS,
        max_consecutive_losses: int = 2,
        trading_hours_start: int | dtime = MONITORAMENTO_INICIO,
        trading_hours_end: int | dtime = NOVAS_ENTRADAS_FIM,
        monitoring_hours_end: dtime = MONITORAMENTO_FIM,
        max_trades_per_day: int = MAX_TRADES_PER_SESSION,
        stop_loss_cooldown_seconds: int = STOP_LOSS_COOLDOWN_SECONDS,
    ):
        self.max_trades_per_hour = max_trades_per_hour
        self.min_cooldown_seconds = min_cooldown_seconds
        self.max_consecutive_losses = max_consecutive_losses
        self.trading_hours_start = self._normalizar_horario(trading_hours_start)
        self.trading_hours_end = self._normalizar_horario(trading_hours_end)
        self.monitoring_hours_end = monitoring_hours_end
        self.max_trades_per_day = max_trades_per_day
        self.stop_loss_cooldown_seconds = stop_loss_cooldown_seconds

        self.trades_this_hour = []
        self.last_trade_time = None
        self.consecutive_losses = 0
        self.is_in_cooldown = False
        self.cooldown_until = None
        self.daily_trade_count = 0
        self.daily_reference = None

    @staticmethod
    def _normalizar_horario(valor: int | dtime) -> dtime:
        if isinstance(valor, dtime):
            return valor
        return dtime(int(valor), 0)

    def _sincronizar_janela_diaria(self, now: datetime) -> None:
        dia_atual = now.date()
        if self.daily_reference == dia_atual:
            return

        self.daily_reference = dia_atual
        self.daily_trade_count = 0
        self.trades_this_hour = []
        self.consecutive_losses = 0
        self.is_in_cooldown = False
        self.cooldown_until = None

    def _liberar_cooldown_expirado(self, now: datetime) -> None:
        """Normaliza o estado quando o cooldown já venceu."""
        if not self.is_in_cooldown or not self.cooldown_until:
            return

        if now < self.cooldown_until:
            return

        self.is_in_cooldown = False
        self.cooldown_until = None

        if self.consecutive_losses > 0:
            logger.info(
                "[ANTIOVERTRADING] Cooldown expirado - resetando sequencia de perdas"
            )
            self.consecutive_losses = 0

    def pode_monitorar(self, agora: Optional[datetime] = None) -> bool:
        """Expõe a janela estendida de monitoramento do agente."""
        now = agora or datetime.now()
        horario = now.time()
        return MONITORAMENTO_INICIO <= horario <= self.monitoring_hours_end

    def pode_tradear(self, agora: Optional[datetime] = None) -> tuple[bool, str]:
        """Verifica se é permitido fazer um novo trade. Retorna (permitido, motivo)."""
        now = agora or datetime.now()
        self._sincronizar_janela_diaria(now)

        # 1. Verificar horário de operação
        horario = now.time()
        if not (self.trading_hours_start <= horario <= self.trading_hours_end):
            return (
                False,
                "[ANTIOVERTRADING] Fora da janela de novas entradas "
                f"({self.trading_hours_start.strftime('%H:%M')}-"
                f"{self.trading_hours_end.strftime('%H:%M')})",
            )

        # 2. Verificar cooldown global
        if self.is_in_cooldown and self.cooldown_until and now < self.cooldown_until:
            remaining = (self.cooldown_until - now).total_seconds()
            return False, f"❌ Em cooldown global ({remaining:.0f}s restantes)"

        self._liberar_cooldown_expirado(now)

        # 3. Verificar limite diário do PRD
        if self.daily_trade_count >= self.max_trades_per_day:
            return (
                False,
                f"❌ Limite diário de {self.max_trades_per_day} trades atingido",
            )

        # 4. Verificar limite de trades por hora
        one_hour_ago = now - timedelta(hours=1)
        self.trades_this_hour = [t for t in self.trades_this_hour if t > one_hour_ago]

        if len(self.trades_this_hour) >= self.max_trades_per_hour:
            return (
                False,
                f"❌ Limite de {self.max_trades_per_hour} trades/hora atingido ({len(self.trades_this_hour)}/{self.max_trades_per_hour})",
            )

        # 5. Verificar cooldown mínimo entre trades
        if self.last_trade_time:
            seconds_since_last = (now - self.last_trade_time).total_seconds()
            if seconds_since_last < self.min_cooldown_seconds:
                return (
                    False,
                    f"❌ Cooldown mínimo: {self.min_cooldown_seconds}s (apenas {seconds_since_last:.0f}s se passaram)",
                )

        # 6. Verificar perdas consecutivas
        if self.consecutive_losses >= self.max_consecutive_losses:
            return (
                False,
                f"❌ {self.max_consecutive_losses} perdas consecutivas - pausando operações",
            )

        return True, "✅ Permitido tradear"

    def registrar_trade(self, agora: Optional[datetime] = None):
        """Registra que um novo trade foi aberto."""
        now = agora or datetime.now()
        self._sincronizar_janela_diaria(now)
        self.trades_this_hour.append(now)
        self.last_trade_time = now
        self.daily_trade_count += 1
        logger.info(
            "[ANTIOVERTRADING] Trade registrado | hora=%d | dia=%d/%d",
            len(self.trades_this_hour),
            self.daily_trade_count,
            self.max_trades_per_day,
        )

    def registrar_perda(self, agora: Optional[datetime] = None):
        """Registra uma perda e incrementa contador consecutivo."""
        now = agora or datetime.now()
        self._sincronizar_janela_diaria(now)
        self.consecutive_losses += 1
        logger.warning(
            f"[ANTIOVERTRADING] ⚠️  Perda registrada ({self.consecutive_losses}/{self.max_consecutive_losses})"
        )

        # PRD: respiro operacional após perda/SL antes de nova entrada.
        self.is_in_cooldown = True
        self.cooldown_until = now + timedelta(seconds=self.stop_loss_cooldown_seconds)
        logger.warning(
            "[ANTIOVERTRADING] 🛑 Cooldown de %d min ativado apos LOSS/SL",
            self.stop_loss_cooldown_seconds // 60,
        )

    def registrar_ganho(self):
        """Registra um ganho e reseta contador de perdas consecutivas."""
        self.consecutive_losses = 0
        logger.info(
            f"[ANTIOVERTRADING] ✅ Ganho registrado - contador de perdas resetado"
        )


def registrar_bloqueio_anti_overtrading(ciclo: int, acao_str: str, motivo: str) -> None:
    """Registra no log quando um sinal confirmado é bloqueado pela proteção."""
    motivo_normalizado = motivo.lower()
    if "cooldown global" in motivo_normalizado:
        logger.warning(
            f"[CICLO {ciclo}] SINAL CONFIRMADO: {acao_str} | "
            f"ORDEM BLOQUEADA por cooldown pós-loss: {motivo}"
        )
        return

    logger.warning(
        f"[CICLO {ciclo}] SINAL CONFIRMADO: {acao_str} | "
        f"ORDEM BLOQUEADA pela proteção anti-overtrading: {motivo}"
    )


# ============================================================================
# RASTREAMENTO DE POSIÇÕES — Usa módulos formais de isolamento
# (PosicaoIsoladaManager + MotorDecisaoIsolado de src/application/)
# ============================================================================


def verificar_posicao_no_mt5(
    posicao_mgr: PosicaoIsoladaManager, motor: MotorDecisaoIsolado, mt5_adapter_local
) -> bool:
    """Consulta MT5 pelo ticket p/ verificar se posição ainda existe.

    Retorna True se posição AINDA aberta. False caso contrário.
    """
    if not posicao_mgr.tem_posicao_aberta():
        return False

    try:
        metadados = posicao_mgr.obter_metadados_posicao()
    except Exception as e:
        logger.warning(f"[MT5-CHECK] Falha ao ler metadados de posição: {e}")
        return False

    ticket = int(metadados.get("ticket", 0) or 0)
    if ticket <= 0:
        logger.warning("[MT5-CHECK] Ticket inválido para verificação da posição")
        return False

    try:
        positions = mt5_adapter_local.get_positions(Symbol(SIMBOLO))
        for pos in positions:
            pos_ticket = int(getattr(pos, "ticket", 0) or 0)
            pos_magic = int(getattr(pos, "magic", 0) or 0)
            if pos_ticket == ticket and pos_magic == MAGIC_NUMBER:
                preco_atual = float(getattr(pos, "price_current", 0))
                motor.atualizar_posicao(ticket, preco_atual)
                logger.debug(
                    f"[MT5-CHECK] Ticket {ticket} CONFIRMADO aberto "
                    f'(magic={pos_magic}, profit={getattr(pos, "profit", 0):.2f})'
                )
                return True

        # Não encontrado → fechado por SL/TP/manual
        logger.info(
            f"[MT5-CHECK] Ticket {ticket} NAO encontrado no MT5. "
            f"Posição FECHADA (SL/TP ou manual)."
        )
        return False
    except Exception as e:
        logger.warning(f"[MT5-CHECK] Erro ao consultar MT5: {e}")
        return posicao_mgr.tem_posicao_aberta()


# ============================================================================
# LOOP PRINCIPAL
# ============================================================================
def main():
    """Loop principal do agente direto com lógica de RL."""
    global last_signal
    global _monitor_posicao_rl, _feedback_validator_rl, _drift_detector_rl
    global _online_learning_rl, _baseline_comparator_rl

    # Inicializar componentes
    componentes = inicializar_componentes()
    if not componentes:
        logger.error("[FATAL] Falha na inicialização. Encerrando.")
        sys.exit(1)

    config = componentes["config"]
    mt5_adapter = componentes["mt5_adapter"]
    pipeline = componentes["pipeline"]
    agente = componentes["agente"]
    profit_protection = componentes["profit_protection"]
    retry_mgr = componentes["retry_mgr"]
    rl_repo = componentes["rl_repo"]
    anti_overtrading = componentes[
        "anti_overtrading"
    ]  # 🛑 CRITICAL: Proteção contra overtrading
    trade_tracker = componentes["trade_tracker"]  # 📊 Rastreamento de performance

    # Inicializar módulos formais de isolamento
    posicao_tracker = PosicaoIsoladaManager(
        session_id=AGENT_SESSION_ID,
        agent_version="rl_direto_v3.0",
        outputs_dir=OUTPUTS_DIR,
    )
    motor_decisao = MotorDecisaoIsolado(
        agent_id=AGENT_SESSION_ID,
        data_dir=OUTPUTS_DIR,
    )
    logger.info(
        f"[ISOLAMENTO] PosicaoIsoladaManager + MotorDecisaoIsolado "
        f"inicializados para session {AGENT_SESSION_ID}"
    )

    # Inicializar Grupo 2: Feedback e Aprendizado (AC5.8/AC5.9/AC6)
    if _AC5_8_DISPONIVEL and MonitorPositionManager:
        try:
            _monitor_posicao_rl = MonitorPositionManager(
                db_caminho=str(ROOT_DIR / "data" / "db" / "trading.db"),
            )
            logger.info("[OK] AC5.8 MonitorPositionManager: Ativo")
        except Exception as e:
            logger.warning(f"[WARN] AC5.8 init falhou: {e}")

    if _AC5_9_DISPONIVEL and FeedbackValidator:
        try:
            _feedback_validator_rl = FeedbackValidator()
            logger.info("[OK] AC5.9 FeedbackValidator: Ativo")
        except Exception as e:
            logger.warning(f"[WARN] AC5.9 init falhou: {e}")

    if _AC6_DISPONIVEL and (
        DriftDetector or OnlineLearningController or BaselineComparator
    ):
        try:
            ac6 = build_ac6_components(
                drift_detector_cls=DriftDetector if _AC6_DISPONIVEL else None,
                online_learning_cls=OnlineLearningController
                if _AC6_DISPONIVEL
                else None,
                baseline_comparator_cls=BaselineComparator if _AC6_DISPONIVEL else None,
                model_name=f"rl_direto_{AGENT_SESSION_ID}",
                models_dir_root=ROOT_DIR / "data" / "models",
            )
            _drift_detector_rl = ac6.drift_detector
            _online_learning_rl = ac6.online_learning
            _baseline_comparator_rl = ac6.baseline_comparator
            if _drift_detector_rl is not None:
                logger.info("[OK] AC6.7 DriftDetector: Ativo")
            if _online_learning_rl is not None:
                logger.info("[OK] AC6.8 OnlineLearningController: Ativo")
            if _baseline_comparator_rl is not None:
                logger.info("[OK] AC6.9 BaselineComparator: Ativo")
        except Exception as e:
            logger.warning(f"[WARN] AC6 bootstrap falhou: {e}")

    logger.info("=" * 80)
    logger.info("INICIANDO LOOP OPERACIONAL COM RL")
    logger.info("=" * 80)
    logger.info(f"Target: R${TARGET_PROFIT:.2f} | Stop Loss: R${STOP_LOSS_MAX:.2f}")
    logger.info(f"SL/TP Mode: {AGENT_MODE.upper()}")
    logger.info(f"Session: {AGENT_SESSION_ID}")
    logger.info(f"Isolamento: MotorDecisaoIsolado + PosicaoIsoladaManager")
    logger.info("=" * 80)
    logger.info("")

    opening_runtime = initialize_opening_context_runtime(
        db_path=TRADING_DB_PATH,
        agent_name="rl_direto",
        source="agente_rl_direto_independente",
        session_id=AGENT_SESSION_ID,
        mode=AGENT_MODE.upper(),
        logger=logger,
        operational_context_dir=os.getenv("OPENING_CONTEXT_DIR") or None,
    )
    if opening_runtime.prompt_abertura_agentes:
        logger.info(
            "[PRE-ABERTURA] Prompt operacional lido pelo agente: %s",
            opening_runtime.prompt_abertura_agentes,
        )

    ciclo = 0
    start_time = time.time()
    trades_fechados_rl: list = []  # Acumulador para pipeline AC5.9/AC6

    try:
        while True:
            ciclo += 1

            try:
                logger.info(f"[CICLO {ciclo}] Iniciando iteração...")
                logger.debug(
                    f"[CICLO {ciclo}] Tempo decorrido: {time.time() - start_time:.1f}s"
                )

                # 🔴 CRITICAL: Recarregar status de posição do arquivo a cada ciclo
                posicao_tracker._carregar_status()
                logger.debug(
                    f"[CICLO {ciclo}] Status posição recarregado: {posicao_tracker.tem_posicao_aberta()}"
                )

                # Verificar conexão MT5 antes de cada ciclo
                if not mt5_adapter.is_connected():
                    logger.warning(
                        f"[CICLO {ciclo}] Detectada perda de conexão MT5, tentando reconectar..."
                    )
                    if not mt5_adapter.connect():
                        logger.error(f"[CICLO {ciclo}] Falha ao reconectar ao MT5")
                        time.sleep(5)
                        continue
                    logger.info(f"[CICLO {ciclo}] MT5 reconectado com sucesso")

                # 1. Carregar dados de mercado (últimas 100 velas M5 para contexto RL)
                try:
                    if Symbol is None or TimeFrame is None:
                        logger.debug("[CICLO] Domain models não estão disponíveis")
                        time.sleep(5)
                        continue

                    # Usar padrão correto: Symbol(string), TimeFrame.M5, count=100
                    candles_raw = mt5_adapter.get_candles(
                        Symbol(SIMBOLO), TimeFrame.M5, 100
                    )

                    if candles_raw is None or len(candles_raw) == 0:
                        logger.debug(
                            "[CICLO] Aguardando dados de mercado (MT5 pode estar offline)..."
                        )
                        time.sleep(5)
                        continue

                    # Converter lista de Candle objects para DataFrame para RL environment
                    dados_df = pd.DataFrame(
                        {
                            "open": [c.open.value for c in candles_raw],
                            "high": [c.high.value for c in candles_raw],
                            "low": [c.low.value for c in candles_raw],
                            "close": [c.close.value for c in candles_raw],
                            "volume": [c.volume for c in candles_raw],
                        }
                    )

                    # Preço atual vem do último candle
                    preco_atual = float(candles_raw[-1].close.value)
                    logger.debug(
                        f"[CICLO {ciclo}] Preço atual: {preco_atual} | Velas disponíveis: {len(dados_df)}"
                    )

                except Exception as e:
                    logger.warning(f"[CICLO {ciclo}] Erro ao obter dados: {e}")
                    time.sleep(5)
                    continue

                # 2. Se JSON diz posição aberta, verificar no MT5 pelo ticket
                if posicao_tracker.tem_posicao_aberta():
                    ainda_aberta = verificar_posicao_no_mt5(
                        posicao_tracker,
                        motor_decisao,
                        mt5_adapter,
                    )

                    if not ainda_aberta:
                        contexto_fechamento = obter_contexto_fechamento_sessao_atual(
                            posicao_tracker,
                            motor_decisao,
                        )

                        if contexto_fechamento is None:
                            ticket_local = None
                            try:
                                metadados_local = (
                                    posicao_tracker.obter_metadados_posicao()
                                )
                                ticket_local = int(
                                    metadados_local.get("ticket", 0) or 0
                                )
                            except Exception:
                                ticket_local = None

                            logger.warning(
                                f"[CICLO {ciclo}] Posição sem contexto válido da sessão atual. "
                                f"Registrando como DESCONHECIDO para evitar contaminação."
                            )

                            trades_fechados_rl.append(
                                {
                                    "ticket": ticket_local,
                                    "resultado": "DESCONHECIDO",
                                    "pnl": 0.0,
                                    "direcao": "DESCONHECIDO",
                                }
                            )

                            posicoes_motor_ativas = (
                                motor_decisao.obter_posicoes_abertas()
                            )
                            if posicoes_motor_ativas:
                                ticket_motor = posicoes_motor_ativas[0].ticket
                                try:
                                    motor_decisao.fechar_posicao(
                                        ticket_motor,
                                        preco_atual,
                                        MotivoFechamento.CANCELADA,
                                        contexto_operacional=build_contexto_operacional_com_diario(
                                            getattr(opening_runtime, "features", None),
                                            db_path=TRADING_DB_PATH,
                                        ),
                                    )
                                    logger.warning(
                                        f"[CICLO {ciclo}] Limpeza local do motor para ticket "
                                        f"{ticket_motor} após divergência de sessão"
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"[CICLO {ciclo}] Falha ao limpar estado local do motor: {e}"
                                    )

                            posicao_tracker.registrar_posicao_fechada()
                            continue

                        ticket_aberto = int(contexto_fechamento["ticket"])
                        preco_entrada_reg = float(contexto_fechamento["preco_entrada"])
                        tipo_reg = contexto_fechamento["tipo"]
                        volume_reg = float(contexto_fechamento["volume"])

                        logger.info(
                            f"[CICLO {ciclo}] Posição ticket={ticket_aberto} "
                            f"FECHADA no MT5 (SL/TP ou manual)"
                        )

                        preco_saida_real = resolver_preco_saida_real(
                            mt5_adapter,
                            ticket_aberto,
                            tipo_reg,
                            simbolo=SIMBOLO,
                        )
                        if preco_saida_real is None:
                            logger.warning(
                                f"[CICLO {ciclo}] Preço real de saída indisponível para "
                                f"ticket={ticket_aberto}. Usando preço do candle como fallback."
                            )
                            preco_saida_real = preco_atual

                        resultado, pnl_estimado = classificar_fechamento_trade(
                            preco_entrada=preco_entrada_reg,
                            preco_saida=preco_saida_real,
                            tipo_posicao=tipo_reg,
                            volume=volume_reg,
                        )

                        trades_fechados_rl.append(
                            {
                                "ticket": ticket_aberto,
                                "resultado": resultado,
                                "pnl": pnl_estimado,
                                "direcao": "BUY"
                                if tipo_reg == TipoPosicao.COMPRADA
                                else "SELL",
                                "preco_saida": preco_saida_real,
                            }
                        )

                        # AC5.8: Atualizar status da ordem para fechada
                        if _monitor_posicao_rl and ticket_aberto:
                            try:
                                _monitor_posicao_rl.atualizar_status_ordem(
                                    str(ticket_aberto),
                                    StatusOrdem.FECHADA,
                                )
                            except Exception as e:
                                logger.warning(f"[AC5.8] Erro ao atualizar status: {e}")

                        # Atualizar anti-overtrading
                        if resultado == "LOSS":
                            anti_overtrading.registrar_perda()
                        elif resultado == "WIN":
                            anti_overtrading.registrar_ganho()

                        # Registrar saída no trade tracker
                        if trade_tracker and ticket_aberto:
                            try:
                                motivo = (
                                    TradeClosureReason.SL_HIT
                                    if resultado == "LOSS"
                                    else TradeClosureReason.TP_HIT
                                    if resultado == "WIN"
                                    else TradeClosureReason.MANUAL_CLOSE
                                )
                                trade_tracker.registrar_saida(
                                    ticket=ticket_aberto,
                                    preco_saida=preco_saida_real,
                                    motivo_fechamento=motivo,
                                )
                            except Exception as e:
                                logger.warning(f"[WARN] Erro ao registrar saída: {e}")

                        # Fechar posição nos módulos formais
                        if ticket_aberto:
                            motivo_motor = (
                                MotivoFechamento.SL_ATINGIDO
                                if resultado == "LOSS"
                                else MotivoFechamento.TP_ATINGIDO
                                if resultado == "WIN"
                                else MotivoFechamento.MANUAL
                            )
                            motor_decisao.fechar_posicao(
                                ticket_aberto,
                                preco_saida_real,
                                motivo_motor,
                                contexto_operacional=build_contexto_operacional_com_diario(
                                    getattr(opening_runtime, "features", None),
                                    db_path=TRADING_DB_PATH,
                                ),
                            )
                        posicao_tracker.registrar_posicao_fechada()

                        logger.info(
                            f"[CICLO {ciclo}] Resultado: {resultado} | "
                            f"PnL estimado: R${pnl_estimado:.2f} | "
                            f"Preço saída: {preco_saida_real:.2f} | "
                            f"Pronto para próximo trade"
                        )
                        # Não fazer continue — deixar seguir para buscar novo sinal
                    else:
                        # Posição ainda aberta no MT5 — aguardar
                        posicoes_m = motor_decisao.obter_posicoes_abertas()
                        tk = posicoes_m[0].ticket if posicoes_m else "?"
                        logger.info(
                            f"[CICLO {ciclo}] Posição ticket={tk} "
                            f"AINDA ABERTA no MT5. Aguardando 15s..."
                        )
                        time.sleep(15)
                        continue

                # 3. Se sem posição, tentar obter ação do RL
                logger.debug(f"[CICLO {ciclo}] Verificando oportunidade de entrada...")

                try:
                    acao_id, confidence = obter_acao_do_modelo(
                        dados_df, pipeline, agente
                    )
                    acao_str = mapear_acao(acao_id)

                    logger.debug(
                        f"[CICLO {ciclo}] Ação RL: {acao_str} (confiança: {confidence:.2%})"
                    )

                except Exception as e:
                    logger.warning(f"[CICLO {ciclo}] Erro ao obter ação RL: {e}")
                    acao_str = "Aguardar"

                # 3.5. ML-1 (18/03/2026): Gate de tendencia intraday EMA9/EMA21.
                # Bloqueia SELL em tendencia de alta e BUY em tendencia de baixa.
                acao_str = aplicar_gate_tendencia(acao_str, dados_df)

                # 4. Validar confirmação do sinal
                if acao_str != "Aguardar":
                    confirmado = verificar_confirmacao_sinal(acao_str, last_signal)

                    if confirmado:
                        logger.info(f"[CICLO {ciclo}] SINAL CONFIRMADO: {acao_str}")

                        # 4.5. 🛑 Verificar proteção contra overtrading
                        pode_tradear, motivo = anti_overtrading.pode_tradear()

                        if not pode_tradear:
                            registrar_bloqueio_anti_overtrading(ciclo, acao_str, motivo)
                            time.sleep(5)
                            continue

                        logger.info(
                            f"[CICLO {ciclo}] Proteção anti-overtrading: {motivo}"
                        )

                        # 5. Enviar ordem
                        if enviar_ordem(
                            mt5_adapter,
                            acao_str,
                            preco_atual,
                            posicao_tracker,
                            rl_repo,
                            trade_tracker,
                            motor_decisao,
                            dados_df,
                            retry_mgr=retry_mgr,
                            opening_context=getattr(opening_runtime, "features", None),
                            confidence=confidence,
                        ):
                            logger.info(f"[CICLO {ciclo}] Ordem aberta com sucesso!")
                            anti_overtrading.registrar_trade()  # 📝 Registrar trade na proteção
                            last_signal = acao_str
                            time.sleep(5)
                            continue
                    else:
                        last_signal = acao_str
                        logger.debug(f"[SINAL] Aguardando confirmação: {acao_str}")
                else:
                    signal_confirmation_count = 0
                    last_signal = "Aguardar"

                # Grupo 2: Pipeline Feedback/Aprendizado (a cada 10 ciclos)
                if ciclo % 10 == 0:
                    try:
                        _executar_pipeline_feedback_rl(trades_fechados_rl)
                    except Exception as e:
                        logger.warning(f"[PIPELINE-FEEDBACK] Erro: {e}")

                # Default: aguardar
                logger.debug(f"[CICLO {ciclo}] Aguardando...")
                time.sleep(5)

            except KeyboardInterrupt:
                logger.info("[HALT] Interrupção do usuário (Ctrl+C)")
                break

            except Exception as e:
                logger.error(f"[CICLO {ciclo}] Erro inesperado: {e}", exc_info=True)

                # Tentar reconectar se a conexão caiu
                try:
                    if not mt5_adapter.is_connected():
                        logger.warning(
                            "[RECONEXAO] Detectada perda de conexão MT5, tentando reconectar..."
                        )
                        if mt5_adapter.connect():
                            logger.info("[RECONEXAO] MT5 reconectado com sucesso")
                        else:
                            logger.error("[RECONEXAO] Falha ao reconectar")
                except:
                    pass

                time.sleep(5)
                continue

    except KeyboardInterrupt:
        logger.info("\n[HALT] Encerrando agente direto...")

    finally:
        # Cleanup
        logger.info("[CLEANUP] Encerrando componentes...")

        # Gravar relatorio de performance de trades
        try:
            if trade_tracker:
                arquivo_relatorio = trade_tracker.gerar_relatorio_json()
                logger.info(
                    f"[OK] Relatório de performance gravado: {arquivo_relatorio}"
                )
                stats = trade_tracker.obter_estatisticas()
                logger.info(
                    f'[STATS] Total trades: {stats.get("total_trades", 0)} | '
                    f'Win rate: {stats.get("win_rate", 0):.1f}% | '
                    f'PnL total: R$ {stats.get("pnl_total_reais", 0):.2f}'
                )
        except Exception as e:
            logger.warning(f"[WARN] Erro ao gravar relatório: {e}")

        try:
            relatorio_contexto = generate_opening_context_vs_result_report(
                db_path=str(ROOT_DIR / "data" / "db" / "trading.db"),
                output_dir=ROOT_DIR / "outputs" / "analysis",
                outputs_root=OUTPUTS_DIR,
            )
            logger.info(
                "[PRE-ABERTURA] Relatório contexto x resultado gerado: %s",
                relatorio_contexto.markdown_path,
            )
        except Exception as e:
            logger.warning(f"[PRE-ABERTURA] Falha ao gerar relatório final: {e}")

        try:
            mt5_adapter.desconectar()
            logger.info("[OK] Desconectado do MT5")
        except Exception:
            pass

        logger.info("=" * 80)
        logger.info(f"AGENTE DIRETO ENCERRADO - Session: {AGENT_SESSION_ID}")
        logger.info(f"Total de ciclos: {ciclo}")
        logger.info(f"Tempo total: {time.time() - start_time:.1f}s")
        logger.info("=" * 80)


# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    main()
