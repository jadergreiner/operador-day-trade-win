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
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, time as dtime, timedelta
from typing import Any, Mapping, Optional
import pandas as pd

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _resolve_trading_db_path(default_name: str = "trading_rl_5000.db") -> str:
    """Resolve o SQLite do RL v5000 com override explícito opcional."""
    override = (
        os.getenv("RL5000_DB_PATH", "").strip()
        or os.getenv("TRADING_DB_PATH", "").strip()
    )
    if override:
        return str(Path(override).expanduser())
    return str(ROOT_DIR / "data" / "db" / default_name)


TRADING_DB_PATH = _resolve_trading_db_path()
os.environ["RL5000_DB_PATH"] = TRADING_DB_PATH
os.environ["DB_PATH"] = TRADING_DB_PATH
os.environ["TRADING_DB_PATH"] = TRADING_DB_PATH


def _resolve_coordination_db_paths() -> dict[str, str]:
    """Resolve visão multi-DB para coordenação cross-agent."""
    rl_5000_path = os.getenv("RL5000_DB_PATH", "").strip() or TRADING_DB_PATH
    rl_direto_path = os.getenv("RL_DIRETO_DB_PATH", "").strip() or str(
        ROOT_DIR / "data" / "db" / "trading_rl_direto.db"
    )
    return {
        "rl_5000": str(Path(rl_5000_path).expanduser()),
        "rl_direto": str(Path(rl_direto_path).expanduser()),
    }

EXIT_CODE_OK = 0
EXIT_CODE_TARGET_ATINGIDO = 10
EXIT_CODE_STOP_LOSS = 11

from src.infrastructure.adapters.mt5_adapter import MT5Adapter
from src.infrastructure.database.rl_schema import ensure_rl_database
from src.domain.value_objects.financial import Symbol, Price, Quantity
from src.domain.entities.trade import Order
from src.domain.enums.trading_enums import OrderSide, TimeFrame, OrderType
from src.application.services.novo_agente.pipeline_treinamento import PipelineTreinamentoRL
from src.infrastructure.repositories.rl_repository import SqliteRLRepository
from src.infrastructure.database.schema import get_session
from src.application.profit_protection_engine import (
    ProfitProtectionEngine,
    ProfitProtectionResult,
    ProtectionStatus,
)
from src.infrastructure.config.profit_protection_config import (
    carregar_config as _carregar_pp_config,
    resolver_perfil as _resolver_pp_perfil,
)
from src.application.profit_protection_regime_runtime import (
    aplicar_guardrail_cooldown_switch,
    decidir_switch_perfil_profit_protection,
)

# BLID-045: Alertas de reversao de lucro
try:
    from src.application.alert_reversao_handler import (
        AlertReversaoHandler,
        AlertReversaoConfig,
    )
    from src.application.services.alerta_delivery import AlertaDeliveryManager
    import yaml
    _ALERT_REVERSAO_DISPONIVEL = True
except ImportError:
    _ALERT_REVERSAO_DISPONIVEL = False

from src.application.sl_breakeven_validator import (
    ValidadorSLBreakEven,
    StatusValidacaoSL,
)
from src.application.motor_decisao_isolado import (
    DecisaoOperacional,
    MotorDecisaoIsolado,
    TipoPosicao,
    MotivoFechamento,
)
try:
    from src.application.decision_context_policy import (
        DecisionContext,
        compute_context_score,
        apply_context_to_confidence,
    )
    _DECISION_CONTEXT_POLICY_DISPONIVEL = True
except ImportError:
    _DECISION_CONTEXT_POLICY_DISPONIVEL = False
    from src.application.opening_context_policy import normalize_opening_context

    @dataclass(slots=True)
    class DecisionContext:
        """Fallback local para o contrato de contexto decisional."""

        action: str
        raw_confidence: float = 0.0
        opening_context: Any = None
        normalized_context: Any = None
        market_confirmation: dict[str, Any] = field(default_factory=dict)
        diario_payload: dict[str, Any] = field(default_factory=dict)
        volatility: float | None = None
        feature_flags: dict[str, Any] = field(default_factory=dict)
        reason_codes: list[str] = field(default_factory=list)
        reasons: list[str] = field(default_factory=list)
        context_score: float = 1.0
        context_penalty: float = 0.0
        adjusted_confidence: float | None = None

    def _safe_text(value: Any, default: str = "") -> str:
        text = str(value or "").strip()
        return text if text else default

    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _safe_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "sim", "ativo", "on"}:
                return True
            if normalized in {"0", "false", "no", "nao", "off"}:
                return False
        return default

    def _safe_mapping(value: Any) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)
        return {}

    def _dedupe_preserving_order(items: list[str]) -> list[str]:
        return list(dict.fromkeys(item for item in items if item))

    def compute_context_score(decision_context: DecisionContext) -> DecisionContext:
        """Calcula score/penalty soft do contexto sem bloquear a entrada."""
        normalized_context = decision_context.normalized_context
        if normalized_context is None and decision_context.opening_context is not None:
            normalized_context = normalize_opening_context(decision_context.opening_context)

        feature_flags = dict(decision_context.feature_flags or {})
        reason_codes = list(decision_context.reason_codes or [])
        reasons = list(decision_context.reasons or [])
        market_confirmation = _safe_mapping(decision_context.market_confirmation)
        action = _safe_text(decision_context.action).upper()

        regime_macro = _safe_text(getattr(normalized_context, "regime_macro", ""))
        vies_intraday = _safe_text(getattr(normalized_context, "vies_intraday", "")).upper()
        kill_switch_ativo = _safe_bool(
            getattr(normalized_context, "kill_switch_ativo", False)
        )
        watchlist = list(getattr(normalized_context, "watchlist", []) or [])
        heavyweights = list(getattr(normalized_context, "heavyweights", []) or [])
        live_unresolved = list(market_confirmation.get("unresolved_symbols", []) or [])
        live_reasons = list(market_confirmation.get("reasons", []) or [])
        buy_confirmed = _safe_bool(market_confirmation.get("buy_confirmed"))
        sell_quality_confirmed = _safe_bool(
            market_confirmation.get("sell_quality_confirmed")
        )
        volatility = decision_context.volatility
        penalty = 0.0

        feature_flags.update(
            {
                "has_opening_context": decision_context.opening_context is not None,
                "has_normalized_context": normalized_context is not None,
                "regime_macro": regime_macro or None,
                "vies_intraday": vies_intraday or None,
                "kill_switch_ativo": kill_switch_ativo,
                "watchlist_size": len(watchlist),
                "heavyweights_size": len(heavyweights),
                "live_buy_confirmed": buy_confirmed,
                "live_sell_quality_confirmed": sell_quality_confirmed,
                "live_unresolved_symbols": len(live_unresolved),
                "volatility_pct": round(float(volatility), 4) if volatility is not None else None,
                "volatility_below_minimum": (
                    volatility is not None
                    and volatility < AntiOvertradingConfig.MIN_VOLATILITY_PERCENT
                ),
            }
        )

        if kill_switch_ativo:
            penalty += 0.35
            reason_codes.append("kill_switch_abertura_ativo")
            reasons.append("Kill switch da abertura ativo.")

        if action == "BUY":
            if "BAIX" in vies_intraday:
                penalty += 0.18
                reason_codes.append("vies_intraday_baixista")
                reasons.append("Viés intraday baixista contraria compra.")
            if buy_confirmed:
                reason_codes.append("compra_confirmada_live")
                reasons.append("Compra confirmada no live market.")
            else:
                penalty += 0.22
                reason_codes.append("compra_sem_confirmacao_live")
                reasons.append("Compra sem confirmação live.")
        elif action == "SELL":
            if "ALT" in vies_intraday:
                penalty += 0.18
                reason_codes.append("vies_intraday_altista")
                reasons.append("Viés intraday altista contraria venda.")
            if sell_quality_confirmed:
                reason_codes.append("venda_confirmada_live")
                reasons.append("Venda qualificada no live market.")
            else:
                penalty += 0.22
                reason_codes.append("venda_sem_confirmacao_live")
                reasons.append("Venda sem confirmação live.")

        if live_unresolved:
            penalty += 0.05
            reason_codes.append("ativos_sem_confirmacao_live")
            reasons.append(
                "Símbolos sem confirmação live: " + ",".join(live_unresolved)
            )
        if live_reasons:
            reason_codes.extend(
                item for item in live_reasons if isinstance(item, str) and item
            )

        if volatility is not None and volatility < AntiOvertradingConfig.MIN_VOLATILITY_PERCENT:
            penalty += 0.10
            reason_codes.append("volatilidade_abaixo_minima")
            reasons.append("Volatilidade abaixo do mínimo contextual.")

        if action in {"BUY", "SELL"} and getattr(normalized_context, "watchlist", None):
            reason_codes.append("watchlist_operacional_disponivel")

        penalty = max(0.0, min(1.0, penalty))
        context_score = max(0.0, min(1.0, 1.0 - penalty))

        decision_context.normalized_context = normalized_context
        decision_context.feature_flags = feature_flags
        decision_context.reason_codes = _dedupe_preserving_order(reason_codes)
        decision_context.reasons = _dedupe_preserving_order(reasons)
        decision_context.context_penalty = round(penalty, 4)
        decision_context.context_score = round(context_score, 4)
        return decision_context

    def apply_context_to_confidence(confidence: float, decision_context: DecisionContext) -> float:
        """Aplica o score contextual à confiança-base do modelo."""
        base_confidence = max(0.0, min(1.0, _safe_float(confidence)))
        context_score = max(0.0, min(1.0, _safe_float(decision_context.context_score, 1.0)))
        adjusted_confidence = max(0.0, min(1.0, base_confidence * context_score))
        decision_context.adjusted_confidence = round(adjusted_confidence, 6)
        return decision_context.adjusted_confidence
from src.application.ac6_bootstrap import build_ac6_components
from src.application.opening_market_confirmation import (
    build_live_market_confirmation,
)
from src.application.opening_context_report import (
    generate_opening_context_vs_result_report,
)
from src.application.diario_market_features import (
    apply_diario_soft_feature_influence,
    build_contexto_operacional_com_diario,
    load_diario_market_features_payload,
)
from src.application.opening_context_runtime import initialize_opening_context_runtime
from src.application.log_labels import OPENING_CONTEXT_LABEL
from src.application.services.rl_persistence_service import RLPersistenceService
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

# Imports opcionais — BLID-043: Coordenacao cross-agent
_COORDINATION_DISPONIVEL = False
try:
    from src.application.coordination_manager import (
        CoordinationManager,
        ConfiguracaoCoordinacao,
    )
    from src.application.coordination_signal_reader import CoordinationSignalReader

    _COORDINATION_DISPONIVEL = True
except ImportError as _e_coord:
    CoordinationManager = None  # type: ignore[assignment,misc]
    ConfiguracaoCoordinacao = None  # type: ignore[assignment,misc]
    CoordinationSignalReader = None  # type: ignore[assignment,misc]
from config.settings import AGENT_MAGIC_NUMBERS, TradingConfig
import uuid

from src.application.coordination_signal_reader import CoordinationSignalReader
from src.application.coordination_integration import (
    verificar_pode_abrir_posicao as _verificar_coordination_global,
)

logger = logging.getLogger(__name__)
_LOGGING_CONFIGURED = False

# ---------------------------------------------------------------------------
# Coordination — instancia modulo-level, substituivel em testes
# ---------------------------------------------------------------------------
_coordination_reader: CoordinationSignalReader = CoordinationSignalReader()

# ============================================================================
# ANTI-OVERTRADING CONFIGURATION
# ============================================================================

class AntiOvertradingConfig:
    """Configurações operacionais aderentes ao PRD."""

    COOLDOWN_SECONDS = 300
    STOP_LOSS_COOLDOWN_SECONDS = 1800
    MAX_TRADES_PER_SESSION = 6
    MIN_VOLATILITY_PERCENT = 0.05
    CONFIRM_SIGNAL_BARS = 2

    MIN_VOLUME = 1000
    MIN_CONFIDENCE_SCORE = 0.45
    MIN_RISK_REWARD = 1.5
    RISK_REWARD_TOLERANCE = 1e-6
    SETUP_LOOKBACK_BARS = CONFIRM_SIGNAL_BARS
    STOP_SETUP_BUFFER_PONTOS = 10.0
    TARGET_BUFFER_PONTOS = 20.0


MONITORAMENTO_INICIO = dtime(9, 0)
NOVAS_ENTRADAS_FIM = dtime(17, 25)
MONITORAMENTO_FIM = dtime(17, 55)
VALOR_PONTO_BRL = 0.20
CLOSURE_TOLERANCE_POINTS = 20.0

# ============================================================================
# GLOBAL STATE
# ============================================================================

SIMBOLO = "WIN$N"
TARGET_LUCRO_DIARIO = 140.00
STOP_PERDA_DIARIA = -600.00
STOP_LOSS_PONTOS = 150
TAKE_PROFIT_PONTOS = 300
MAGIC_NUMBER: int = AGENT_MAGIC_NUMBERS["rl_5000"]

def resolver_sl_tp_mode(mode: Optional[str] = None) -> str:
    """Normaliza o modo de cálculo de SL/TP."""
    valor = (mode or os.getenv("AGENTE_SL_TP_MODE", "dinamico")).strip().lower()
    if valor not in {"dinamico", "fixo"}:
        return "dinamico"
    return valor


def construir_agent_id(sl_tp_mode: Optional[str] = None) -> str:
    """Gera um identificador único e estável para a sessão."""
    modo = resolver_sl_tp_mode(sl_tp_mode)
    return f"agente_{modo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def configure_logging() -> None:
    """Configura logging apenas no bootstrap real do runtime."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    outputs_dir = ROOT_DIR / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(
                outputs_dir / "operar_agente_rl_antiovertrading.log",
                encoding="utf-8",
            ),
            logging.StreamHandler(),
        ],
    )
    _LOGGING_CONFIGURED = True


SL_TP_MODE = resolver_sl_tp_mode()
AGENTE_ID = construir_agent_id(SL_TP_MODE)

config: Optional[TradingConfig] = None
mt5_adapter: Optional[MT5Adapter] = None
pipeline: Optional[PipelineTreinamentoRL] = None
rl_repo: Optional[SqliteRLRepository] = None
motor_isolado: Optional[MotorDecisaoIsolado] = None
_monitor_posicao_rl = None

# Profit Protection Engine — carregado via config canônica (ADR-018).
# Fallback automático para perfil baseline se o YAML estiver ausente.
_pp_cfg = _carregar_pp_config()
_pp_profile = _resolver_pp_perfil(
    _pp_cfg,
    profile_env=_pp_cfg.profile_ativo,
)
profit_protection_engine = ProfitProtectionEngine(
    profile=_pp_profile,
    profile_nome=_pp_cfg.profile_ativo,
    shadow_mode=_pp_cfg.shadow_mode,
)

# Anti-overtrading state
trades_executed_today = 0
last_trade_time: Optional[datetime] = None
last_stop_loss_time: Optional[datetime] = None
trades_by_hour = {}  # {hour: count}
last_signal: Optional[str] = None
signal_confirmation_count = 0
ultimo_registro_progresso: Optional[datetime] = None  # Para registrar a cada 5 min

# Variaveis globais — Grupo 2: Feedback e Aprendizado (AC5.9/AC6)
_feedback_validator_rl: Optional[object] = None
_drift_detector_rl: Optional[object] = None
_online_learning_rl: Optional[object] = None
_baseline_comparator_rl: Optional[object] = None
_rl_persistence_service: Optional[object] = None
_trades_fechados_rl: list = []  # Acumulador para pipeline AC5.9/AC6
_opening_context_runtime = None

# Variaveis globais — BLID-043: Coordenacao cross-agent
_coordination_manager: Optional[object] = None
_coordination_reader: Optional[object] = None

# Variaveis globais — BLID-045: Alertas de reversao de lucro
_alert_reversao_handler: Optional[object] = None
_alerta_delivery_manager: Optional[object] = None
_pp_regime_ultimo_switch_ciclo: Optional[int] = None
_PP_REGIME_SWITCH_MIN_CICLOS = int(os.getenv("PP_REGIME_SWITCH_MIN_CICLOS", "30"))


def get_config() -> TradingConfig:
    """Inicializa a configuração apenas quando o runtime realmente precisar."""
    global config
    if config is None:
        config = TradingConfig()
    return config


def get_motor_isolado() -> MotorDecisaoIsolado:
    """Cria o motor isolado de forma lazy para evitar I/O no import."""
    global motor_isolado
    if motor_isolado is None:
        motor_isolado = MotorDecisaoIsolado(
            agent_id=AGENTE_ID,
            data_dir=ROOT_DIR / "outputs",
        )
    return motor_isolado


def inicializar_adaptador_mt5() -> MT5Adapter:
    """Inicializa MT5Adapter."""
    global mt5_adapter

    current_config = get_config()
    mt5_adapter = MT5Adapter(
        login=current_config.mt5_login,
        password=current_config.mt5_password,
        server=current_config.mt5_server,
        terminal_exe_path=current_config.mt5_terminal_path,
    )

    if not mt5_adapter.connect():
        raise RuntimeError("Falha ao conectar no MT5")

    logger.info(f"[OK] MT5 conectado: {current_config.mt5_server}")
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
    global rl_repo, _rl_persistence_service
    max_retries = 3
    retry_delay = 2

    for tentativa in range(max_retries):
        try:
            logger.info(f"[DB] Conectando RL repo (tentativa {tentativa+1}/{max_retries})...")
            ensure_rl_database(TRADING_DB_PATH)
            session = get_session(TRADING_DB_PATH)
            rl_repo = SqliteRLRepository(session)
            rl_repo.seed_dimension_tables()
            _rl_persistence_service = RLPersistenceService(rl_repo)
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


def verificar_horario_trading(agora: Optional[dtime] = None) -> bool:
    """Janela de monitoramento do pregão: 09:00-17:55 BRT."""
    horario = agora or datetime.now().time()
    return MONITORAMENTO_INICIO <= horario <= MONITORAMENTO_FIM


def verificar_janela_novas_entradas(agora: Optional[dtime] = None) -> bool:
    """Permite novas entradas somente até 17:25 BRT."""
    horario = agora or datetime.now().time()
    return MONITORAMENTO_INICIO <= horario <= NOVAS_ENTRADAS_FIM


def obter_pl_sessao(saldo_inicial: float) -> float:
    """Calcula o P&L da sessão com base no saldo da conta."""
    if mt5_adapter is None:
        return 0.0

    try:
        saldo_atual_decimal = mt5_adapter.get_account_balance()
        saldo_atual = float(saldo_atual_decimal) if saldo_atual_decimal else saldo_inicial
        return saldo_atual - saldo_inicial
    except Exception as exc:
        logger.debug(f"Erro ao calcular P&L da sessao: {exc}")
        return 0.0


def carregar_dados_mt5(simbolo: str, n_candles: int = 100) -> Optional[pd.DataFrame]:
    """Carrega candles via MT5Adapter."""
    try:
        if mt5_adapter is None:
            return None
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


def obter_acao_do_modelo(dados: pd.DataFrame) -> tuple[int, float, list[float]]:
    """
    Extrai ação do modelo RL.
    Retorna (action_id, confidence_score)
    """
    try:
        from src.application.services.novo_agente.ambiente_trading import AmbienteTradingMiniIndice

        if pipeline is None or getattr(pipeline, "_agente", None) is None:
            logger.error("Pipeline RL nao inicializado")
            return 0, 0.0, []

        ambiente = AmbienteTradingMiniIndice(dados=dados)
        ambiente.reset()
        ambiente._indice = len(dados) - 1

        estado = ambiente._calcular_estado()
        acao_id, confidence = pipeline._agente.obter_acao_e_confianca(
            estado,
            modo_producao=True,
        )
        state_vector = estado.astype(float).tolist()

        return acao_id, confidence, state_vector

    except Exception as e:
        logger.error(f"Erro ao obter ação: {e}")
        return 0, 0.0, []


def mapear_acao_operacional_para_rl(acao: str) -> str:
    """Converte a ação operacional para o rótulo canônico do RL."""
    mapa = {
        "Aguardar": "HOLD",
        "Comprar": "BUY",
        "Vender": "SELL",
        "HOLD": "HOLD",
        "BUY": "BUY",
        "SELL": "SELL",
    }
    return mapa.get((acao or "").strip(), "HOLD")


def verificar_cooldown() -> bool:
    """
    Verifica se passou o cooldown mínimo entre trades.
    Retorna True se pode fazer trade.
    """
    global last_trade_time, last_stop_loss_time

    agora = datetime.now()
    restante_base = 0.0
    restante_stop = 0.0

    if last_trade_time is not None:
        restante_base = AntiOvertradingConfig.COOLDOWN_SECONDS - (
            agora - last_trade_time
        ).total_seconds()

    if last_stop_loss_time is not None:
        restante_stop = AntiOvertradingConfig.STOP_LOSS_COOLDOWN_SECONDS - (
            agora - last_stop_loss_time
        ).total_seconds()

    restante = max(restante_base, restante_stop)
    if restante <= 0:
        return True

    minutos = restante / 60
    if restante_stop >= restante_base and restante_stop > 0:
        logger.warning(
            "[GUARD] BLOCKED: cooldown_pos_sl | "
            f"Pos-SL ativo. Aguarde {minutos:.1f} min antes de nova entrada."
        )
    else:
        logger.warning(
            "[GUARD] BLOCKED: cooldown_base | "
            f"Cooldown base ativo. Aguarde {minutos:.1f} min antes de nova entrada."
        )
    return False


def verificar_limite_trades() -> bool:
    """Aplica o limite operacional padrão do PRD: máximo de 6 trades/dia."""
    if trades_executed_today >= AntiOvertradingConfig.MAX_TRADES_PER_SESSION:
        logger.warning(
            "[GUARD] BLOCKED: limite_operacional | Maximo de %d trades na sessao atingido. "
            "Sem novas entradas ate o encerramento do pregao.",
            AntiOvertradingConfig.MAX_TRADES_PER_SESSION,
        )
        return False
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
        signal_confirmation_count = min(
            signal_confirmation_count + 1,
            AntiOvertradingConfig.CONFIRM_SIGNAL_BARS,
        )
        if signal_confirmation_count >= AntiOvertradingConfig.CONFIRM_SIGNAL_BARS:
            logger.info(
                f"[OK] Sinal CONFIRMADO ({signal_confirmation_count}/{AntiOvertradingConfig.CONFIRM_SIGNAL_BARS}) - ciclo fechado"
            )
            signal_confirmation_count = 0
            return True
        logger.info(
            f"[OK] Sinal CONFIRMADO ({signal_confirmation_count}/{AntiOvertradingConfig.CONFIRM_SIGNAL_BARS})"
        )
        return False
    else:
        signal_confirmation_count = 1
        logger.info(f"[SINAL] Novo sinal detectado: {sinal_atual}")
        return False


def calcular_risk_reward(acao: str, preco_atual: float, sl: float, tp: float) -> float:
    """Calcula a relacao risco-retorno da oportunidade."""
    if acao == "Comprar":
        risk = preco_atual - sl
        reward = tp - preco_atual
    else:
        risk = sl - preco_atual
        reward = preco_atual - tp

    if risk <= 0:
        return 0.0
    return abs(reward / risk)


def _decision_context_payload(contexto: Any) -> dict[str, Any]:
    """Extrai metadados de contexto em formato seguro para payload/persistência."""
    if contexto is None:
        return {
            "context_score": None,
            "context_penalty": None,
            "feature_flags": {},
            "reason_codes": [],
            "raw_confidence": None,
            "adjusted_confidence": None,
        }

    feature_flags = getattr(contexto, "feature_flags", {}) or {}
    if isinstance(feature_flags, Mapping):
        feature_flags = dict(feature_flags)
    else:
        feature_flags = {}

    reason_codes = list(getattr(contexto, "reason_codes", []) or [])
    if not isinstance(reason_codes, list):
        reason_codes = list(reason_codes) if reason_codes else []

    try:
        context_score = round(float(getattr(contexto, "context_score", 0.0)), 6)
    except (TypeError, ValueError):
        context_score = None
    try:
        context_penalty = round(float(getattr(contexto, "context_penalty", 0.0)), 6)
    except (TypeError, ValueError):
        context_penalty = None
    try:
        raw_confidence = round(float(getattr(contexto, "raw_confidence", 0.0)), 6)
    except (TypeError, ValueError):
        raw_confidence = None
    try:
        adjusted_confidence_raw = getattr(contexto, "adjusted_confidence", None)
        adjusted_confidence = (
            round(float(adjusted_confidence_raw), 6)
            if adjusted_confidence_raw is not None
            else None
        )
    except (TypeError, ValueError):
        adjusted_confidence = None

    return {
        "context_score": context_score,
        "context_penalty": context_penalty,
        "feature_flags": feature_flags,
        "reason_codes": reason_codes,
        "raw_confidence": raw_confidence,
        "adjusted_confidence": adjusted_confidence,
    }


def inferir_motivo_fechamento(
    posicao,
    preco_saida: float,
    *,
    tolerancia_pontos: float = CLOSURE_TOLERANCE_POINTS,
) -> MotivoFechamento:
    """Classifica o fechamento como TP, SL ou manual."""
    if posicao.tipo == TipoPosicao.COMPRADA:
        if preco_saida >= posicao.take_profit - tolerancia_pontos:
            return MotivoFechamento.TP_ATINGIDO
        if preco_saida <= posicao.stop_loss + tolerancia_pontos:
            return MotivoFechamento.SL_ATINGIDO
    else:
        if preco_saida <= posicao.take_profit + tolerancia_pontos:
            return MotivoFechamento.TP_ATINGIDO
        if preco_saida >= posicao.stop_loss - tolerancia_pontos:
            return MotivoFechamento.SL_ATINGIDO
    return MotivoFechamento.MANUAL


def registrar_fechamento_operacional(posicao, preco_saida: float, motivo: MotivoFechamento) -> None:
    """Atualiza métricas e cooldown a partir de um fechamento detectado."""
    global last_stop_loss_time

    diff = preco_saida - posicao.preco_entrada
    if posicao.tipo == TipoPosicao.VENDIDA:
        diff = -diff
    pnl_est = diff * VALOR_PONTO_BRL * posicao.volume
    direcao_str = "BUY" if posicao.tipo == TipoPosicao.COMPRADA else "SELL"
    _trades_fechados_rl.append({
        "trade_id": str(posicao.ticket),
        "outcome": "WIN" if diff > 0 else "LOSS",
        "pnl": pnl_est,
        "direction": direcao_str,
        "closure_reason": motivo.value,
    })

    if motivo == MotivoFechamento.SL_ATINGIDO:
        last_stop_loss_time = datetime.now()
        logger.warning(
            "[COOLDOWN] Stop loss detectado no ticket %s. "
            "Cooldown de %d min iniciado.",
            posicao.ticket,
            AntiOvertradingConfig.STOP_LOSS_COOLDOWN_SECONDS // 60,
        )


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

    # MODO DINAMICO - TP segue janela maior; SL ancora no setup de entrada
    try:
        if len(dados) < lookback_periods:
            # Fallback para valores fixos se não houver dados suficientes
            if acao == "Comprar":
                return preco_atual - STOP_LOSS_PONTOS, preco_atual + TAKE_PROFIT_PONTOS
            else:
                return preco_atual + STOP_LOSS_PONTOS, preco_atual - TAKE_PROFIT_PONTOS

        recent = dados.tail(lookback_periods)
        setup_barras = max(AntiOvertradingConfig.SETUP_LOOKBACK_BARS, 1)
        setup_entrada = dados.tail(setup_barras)

        alvo_topo = float(recent['high'].max())
        alvo_fundo = float(recent['low'].min())
        setup_maxima = float(setup_entrada['high'].max())
        setup_minima = float(setup_entrada['low'].min())

        margem_alvo = AntiOvertradingConfig.TARGET_BUFFER_PONTOS
        margem_stop = AntiOvertradingConfig.STOP_SETUP_BUFFER_PONTOS

        if acao == "Comprar":
            tp = alvo_topo + margem_alvo
            sl = setup_minima - margem_stop

            reward = tp - preco_atual
            risk = preco_atual - sl
            if risk > 0 and reward / risk < AntiOvertradingConfig.MIN_RISK_REWARD:
                tp = preco_atual + (risk * AntiOvertradingConfig.MIN_RISK_REWARD)

        else:  # "Vender"
            tp = alvo_fundo - margem_alvo
            sl = setup_maxima + margem_stop

            reward = preco_atual - tp
            risk = sl - preco_atual
            if risk > 0 and reward / risk < AntiOvertradingConfig.MIN_RISK_REWARD:
                tp = preco_atual - (risk * AntiOvertradingConfig.MIN_RISK_REWARD)

        if acao == "Comprar":
            sl = min(sl, preco_atual - 10)  # SL sempre abaixo do preço
            tp = max(tp, preco_atual + 10)  # TP sempre acima do preço
        else:
            sl = max(sl, preco_atual + 10)  # SL sempre acima do preço
            tp = min(tp, preco_atual - 10)  # TP sempre abaixo do preço

        logger.info(
            "[DINAMICO] Alvo nas ultimas %d velas: topo=%.2f, fundo=%.2f | "
            "setup entrada (%d velas): maxima=%.2f, minima=%.2f",
            lookback_periods,
            alvo_topo,
            alvo_fundo,
            setup_barras,
            setup_maxima,
            setup_minima,
        )
        risk_reward = calcular_risk_reward(acao, preco_atual, sl, tp)
        logger.info(
            "[DINAMICO] SL/TP calculados: SL=%.2f, TP=%.2f (Risk/Reward = %.2f:1)",
            sl,
            tp,
            risk_reward,
        )

        return sl, tp

    except Exception as e:
        logger.warning(f"Erro ao calcular SL/TP dinâmico: {e}. Usando valores fixos.")
        # Fallback para fixos em caso de erro
        if acao == "Comprar":
            return preco_atual - STOP_LOSS_PONTOS, preco_atual + TAKE_PROFIT_PONTOS
        else:
            return preco_atual + STOP_LOSS_PONTOS, preco_atual - TAKE_PROFIT_PONTOS


def enviar_ordem_mt5adapter(
    acao: str,
    preco_atual: float,
    vol: float,
    dados: Optional[pd.DataFrame] = None,
    confidence: float = 0.0,
    opening_context: object = None,
    state_vector: Optional[list[float]] = None,
    original_action: Optional[str] = None,
) -> bool:
    """Envia ordem via MT5Adapter (com validações e SL/TP dinâmicos)."""
    global last_trade_time
    if mt5_adapter is None:
        logger.warning("[GUARD] BLOCKED: mt5_adapter_indisponivel")
        return False

    motor = get_motor_isolado()
    normalize_opening_context_fn = globals().get("normalize_opening_context")
    normalized_context = (
        normalize_opening_context_fn(opening_context)
        if callable(normalize_opening_context_fn) and opening_context is not None
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
        *,
        blocked_reason: Optional[str] = None,
        original_action: Optional[str] = None,
        state_vector: Optional[list[float]] = None,
        context_score: Optional[float] = None,
        feature_flags: Optional[dict[str, object]] = None,
        reason_codes: Optional[list[str]] = None,
    ) -> None:
        """Persiste contexto neutro/cancelado para aprendizagem quando fica de fora."""
        try:
            motor.registrar_decisao(
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
                    "source": "RL_AGENT_V5000",
                    "win_price": preco_atual,
                    "action": "HOLD",
                    "original_action": original_action or "HOLD",
                    "blocked_reason": blocked_reason,
                    "state_vector": state_vector,
                    "symbol": SIMBOLO,
                    "reasoning": motivo,
                    "overall_confidence": confidence,
                    "alignment_score": None,
                    "context_score": context_score,
                    "feature_flags": feature_flags or {},
                    "reason_codes": reason_codes or [],
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

    try:
        if acao == "Aguardar":
            contexto_hold = build_contexto_operacional_com_diario(
                opening_context,
                base_payload={
                    "context_score": 1.0,
                    "context_penalty": 0.0,
                    "feature_flags": {"action_aguardar": True},
                    "reason_codes": ["acao_agora=Aguardar"],
                },
                diario_payload=diario_payload,
                action=acao,
                model_confidence=confidence,
            )
            _persist_hold_episode(
                "Agente permaneceu fora do mercado por decisão operacional.",
                ["acao_agora=Aguardar"],
                contexto_hold,
                DecisaoOperacional.HOLD,
                original_action="HOLD",
                state_vector=state_vector,
                context_score=1.0,
                feature_flags={"action_aguardar": True},
                reason_codes=["acao_agora=Aguardar"],
            )
            return False

        if dados is None or len(dados) < 20:
            logger.warning("[GUARD] BLOCKED: dados_insuficientes")
            return False

        live_confirmation = build_live_market_confirmation(
            mt5_adapter,
            opening_context,
        )
        diario_influence = apply_diario_soft_feature_influence(
            acao,
            confidence,
            diario_payload,
        )
        confidence_for_context = (
            diario_influence.adjusted_confidence
            if diario_influence.adjusted_confidence is not None
            else confidence
        )
        decision_context = DecisionContext(
            action=acao,
            raw_confidence=confidence_for_context,
            opening_context=opening_context,
            market_confirmation=live_confirmation.to_dict(),
            diario_payload=diario_payload,
            volatility=vol,
            feature_flags={
                "daily_influence_available": bool(
                    getattr(diario_influence, "available", False)
                ),
                "daily_influence_alignment": getattr(
                    diario_influence, "alignment", "NEUTRAL"
                ),
                "daily_influence_reasons": list(
                    getattr(diario_influence, "reasons", []) or []
                ),
                "daily_influence_adjustment": getattr(
                    diario_influence, "confidence_adjustment", 0.0
                ),
            },
            reason_codes=list(getattr(diario_influence, "reasons", []) or []),
        )
        decision_context = compute_context_score(decision_context)
        normalized_context = getattr(
            decision_context, "normalized_context", normalized_context
        )
        confidence_efetiva = apply_context_to_confidence(
            confidence_for_context,
            decision_context,
        )
        contexto_operacional = build_contexto_operacional_com_diario(
            opening_context,
            base_payload=_decision_context_payload(decision_context),
            diario_payload=diario_payload,
            diario_influence=diario_influence,
            action=acao,
            model_confidence=confidence_efetiva,
        )
        confidence = confidence_efetiva
        logger.info(
            "[CONTEXT] score=%.4f penalty=%.4f reasons=%s",
            decision_context.context_score,
            decision_context.context_penalty,
            ",".join(decision_context.reason_codes or ["contexto_neutro"]),
        )
        if diario_influence.reasons and diario_influence.confidence_adjustment != 0:
            logger.info(
                "[DIARIO FEATURES] %s | ajuste_conf=%+.2f | alinhamento=%s",
                ", ".join(diario_influence.reasons),
                diario_influence.confidence_adjustment,
                diario_influence.alignment,
            )
        if confidence_efetiva <= 0.0:
            logger.warning(
                "[GUARD] BLOCKED: confidence_indisponivel"
            )
            _persist_hold_episode(
                "Confiança indisponível para operação real.",
                ["model_confidence=0.0"],
                contexto_operacional,
                DecisaoOperacional.CANCELAR,
                blocked_reason="model_confidence_indisponivel",
                original_action=mapear_acao_operacional_para_rl(acao),
                state_vector=state_vector,
                context_score=decision_context.context_score,
                feature_flags=decision_context.feature_flags,
                reason_codes=decision_context.reason_codes,
            )
            return False

        if confidence_efetiva < AntiOvertradingConfig.MIN_CONFIDENCE_SCORE:
            logger.warning(
                "[GUARD] BLOCKED: confidence_abaixo_minimo | %.4f < %.4f",
                confidence_efetiva,
                AntiOvertradingConfig.MIN_CONFIDENCE_SCORE,
            )
            _persist_hold_episode(
                (
                    "Confiança abaixo do mínimo operacional "
                    f"({confidence_efetiva:.2%} < {AntiOvertradingConfig.MIN_CONFIDENCE_SCORE:.0%})."
                ),
                [f"model_confidence={confidence_efetiva:.4f}"],
                contexto_operacional,
                DecisaoOperacional.CANCELAR,
                blocked_reason="confidence_abaixo_minimo",
                original_action=mapear_acao_operacional_para_rl(acao),
                state_vector=state_vector,
                context_score=decision_context.context_score,
                feature_flags=decision_context.feature_flags,
                reason_codes=decision_context.reason_codes,
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
                p for p in (posicoes_mt5 or [])
                if int(getattr(p, 'magic', 0) or 0) == MAGIC_NUMBER
            ]
            if minhas_posicoes:
                tickets = [int(getattr(p, 'ticket', 0)) for p in minhas_posicoes]
                logger.warning(
                    f'[GUARD] BLOCKED: posicao_aberta_mesmo_magic | Já existe(m) {len(minhas_posicoes)} '
                    f'posição(ões) aberta(s) com magic={MAGIC_NUMBER} '
                    f'(tickets={tickets}). Ordem NÃO enviada.'
                )
                return False
        except Exception as e:
            logger.warning(
                f'[GUARD] BLOCKED: falha_verificacao_posicoes_mt5 | {e}'
            )
            return False

        if acao == "Comprar":
            side = OrderSide.BUY
        elif acao == "Vender":
            side = OrderSide.SELL
        else:
            logger.warning("[GUARD] BLOCKED: acao_invalida")
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

        risk_reward = calcular_risk_reward(acao, preco_atual, sl, tp)
        if (
            risk_reward + AntiOvertradingConfig.RISK_REWARD_TOLERANCE
            < AntiOvertradingConfig.MIN_RISK_REWARD
        ):
            logger.warning(
                "[GUARD] BLOCKED: risk_reward_abaixo_minimo | %.6f < %.6f",
                risk_reward,
                AntiOvertradingConfig.MIN_RISK_REWARD,
            )
            _persist_hold_episode(
                (
                    "Risk/Reward abaixo do mínimo operacional "
                    f"({risk_reward:.6f}:1 < {AntiOvertradingConfig.MIN_RISK_REWARD:.2f}:1)."
                ),
                [f"risk_reward={risk_reward:.4f}"],
                contexto_operacional,
                DecisaoOperacional.CANCELAR,
                blocked_reason="risk_reward_abaixo_minimo",
                original_action=mapear_acao_operacional_para_rl(acao),
                state_vector=state_vector,
                context_score=decision_context.context_score,
                feature_flags=decision_context.feature_flags,
                reason_codes=decision_context.reason_codes,
            )
            return False

        logger.info(
            f"[ENVIO] Enviando: {acao} @ {preco_atual} "
            f"(SL: {sl}, TP: {tp}, RR: {risk_reward:.2f}:1, Vol: {vol:.3f}%) "
            f"[Agente: {AGENTE_ID}, Modo: {SL_TP_MODE.upper()}]"
        )

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

        if not ticket:
            logger.warning("[ENVIO] Ordem sem ticket valido. Operacao sera tratada como falha segura.")
            return False

        # Rastrear ticket via MotorDecisaoIsolado (persistido em JSON)
        tipo = TipoPosicao.COMPRADA if acao == "Comprar" else TipoPosicao.VENDIDA
        motor.abrir_posicao(
            ticket=int(ticket),
            tipo=tipo,
            preco_entrada=preco_atual,
            volume=1.0,
            stop_loss=sl,
            take_profit=tp,
            contexto_operacional=contexto_operacional,
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
                    "original_action": (
                        original_action or mapear_acao_operacional_para_rl(acao)
                    ),
                    "blocked_reason": None,
                    "state_vector": state_vector,
                    "symbol": SIMBOLO,
                    "volatility": vol,
                    "raw_confidence": decision_context.raw_confidence,
                    "overall_confidence": confidence_efetiva,
                    "context_score": decision_context.context_score,
                    "context_penalty": decision_context.context_penalty,
                    "feature_flags": decision_context.feature_flags,
                    "reason_codes": decision_context.reason_codes,
                    "risk_reward": risk_reward,
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
        if mt5_adapter is None:
            return
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

                # BLID-045: Disparar alerta se status=ALERTA
                if _ALERT_REVERSAO_DISPONIVEL and _alert_reversao_handler and resultado.status == ProtectionStatus.ALERTA:
                    try:
                        import asyncio
                        asyncio.run(_alert_reversao_handler.processar_reversao(resultado))
                        logger.info(f"[BLID-045] Alerta de reversao disparado para ticket#{ticket}")
                    except Exception as e_alert:
                        logger.warning(f"[BLID-045] Falha ao enviar alerta de reversao: {e_alert}")

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


def ajustar_profit_protection_por_regime_runtime(ciclo_atual: int) -> None:
    """Ajusta profile do ProfitProtectionEngine por regime de sessão."""
    global profit_protection_engine
    global _pp_regime_ultimo_switch_ciclo

    try:
        decisao = decidir_switch_perfil_profit_protection(
            trades_fechados=_trades_fechados_rl,
            perfil_atual=profit_protection_engine.profile_nome,
            perfis_disponiveis=list(_pp_cfg.profiles.keys()),
        )
        if not decisao.deve_trocar:
            if decisao.regime_shift_detectado:
                logger.info(
                    "[PP-REGIME] Shift detectado sem troca | profile=%s | WR_ant=%.1f%% | WR_rec=%.1f%% | motivo=%s",
                    profit_protection_engine.profile_nome,
                    decisao.win_rate_bloco_anterior * 100.0,
                    decisao.win_rate_bloco_recente * 100.0,
                    decisao.motivo,
                )
            return

        permitido, motivo_cooldown = aplicar_guardrail_cooldown_switch(
            ciclo_atual=ciclo_atual,
            ultimo_ciclo_switch=_pp_regime_ultimo_switch_ciclo,
            min_ciclos_entre_switches=_PP_REGIME_SWITCH_MIN_CICLOS,
        )
        if not permitido:
            logger.info(
                "[PP-REGIME] Switch bloqueado por cooldown | atual=%s | sugerido=%s | ciclo=%d | motivo=%s",
                decisao.perfil_atual,
                decisao.perfil_sugerido,
                ciclo_atual,
                motivo_cooldown,
            )
            return

        novo_profile = _resolver_pp_perfil(
            _pp_cfg,
            profile_env=decisao.perfil_sugerido,
        )
        profit_protection_engine = ProfitProtectionEngine(
            profile=novo_profile,
            profile_nome=decisao.perfil_sugerido,
            shadow_mode=_pp_cfg.shadow_mode,
        )
        logger.warning(
            "[PP-REGIME] Troca automatica de perfil | %s -> %s | WR_ant=%.1f%% | WR_rec=%.1f%% | motivo=%s",
            decisao.perfil_atual,
            decisao.perfil_sugerido,
            decisao.win_rate_bloco_anterior * 100.0,
            decisao.win_rate_bloco_recente * 100.0,
            decisao.motivo,
        )
        _pp_regime_ultimo_switch_ciclo = ciclo_atual
    except Exception as exc:
        logger.warning("[PP-REGIME] Falha ao avaliar switch de perfil: %s", exc)


def _executar_pipeline_feedback_rl(
    *,
    preco_referencia: Optional[float] = None,
) -> None:
    """Executa pipeline AC5.9->AC6.7->AC6.8->AC6.9 a cada 10 ciclos.

    Alimentado com trades fechados acumulados em _trades_fechados_rl
    para fechar o loop de aprendizado do RL 5000.
    """
    trades_data = list(_trades_fechados_rl)

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

    if (
        _rl_persistence_service is not None
        and rl_repo is not None
        and pipeline is not None
        and preco_referencia is not None
    ):
        try:
            avaliadas = _rl_persistence_service.evaluate_pending_rewards(
                lambda: float(preco_referencia)
            )
            if avaliadas <= 0:
                return

            episodios = rl_repo.get_episodes_for_training(limit=256)
            resumo = pipeline.treinar_incremental_de_episodios(
                episodios,
                max_amostras=64,
                salvar_modelo=True,
            )
            if resumo.get("executado"):
                logger.info(
                    '[RL-LEARN] Retreino incremental concluido | '
                    f'avaliadas={avaliadas} | amostras={resumo.get("amostras")} | '
                    f'loss={resumo.get("loss") if resumo.get("loss") is not None else "None"}'
                )
        except Exception as e:
            logger.warning(f'[RL-LEARN] Erro: {e}')


def monitorar_posicoes() -> bool:
    """Verifica se há posições abertas DESTE agente (por magic number).

    Sincroniza MotorDecisaoIsolado com estado real do MT5:
    - Recupera tickets após restart (magic filter)
    - Remove tickets fechados (SL/TP/manual)
    - Atualiza P&L em tempo real
    """
    try:
        if mt5_adapter is None:
            return False

        motor = get_motor_isolado()
        positions = mt5_adapter.get_positions(Symbol(SIMBOLO))
        if not positions:
            # Nenhuma posição no símbolo → fechar posições órfãs no motor
            for pos in motor.obter_posicoes_abertas():
                logger.info(f"[ISOLAMENTO] Ticket #{pos.ticket} não existe mais "
                           f"no MT5. Fechando no motor.")
                tick = mt5_adapter._mt5.symbol_info_tick(SIMBOLO)
                preco_fechamento = tick.bid if tick else pos.preco_entrada
                motivo = inferir_motivo_fechamento(pos, preco_fechamento)
                registrar_fechamento_operacional(pos, preco_fechamento, motivo)
                motor.fechar_posicao(
                    pos.ticket, preco_fechamento,
                    motivo,
                    contexto_operacional=build_contexto_operacional_com_diario(
                        getattr(_opening_context_runtime, "features", None),
                        db_path=TRADING_DB_PATH,
                    ),
                )
            return False

        # Filtrar apenas posições com NOSSO magic number
        minhas_posicoes = [
            p for p in positions
            if int(getattr(p, 'magic', 0) or 0) == MAGIC_NUMBER
        ]
        tickets_mt5_meus = {int(getattr(p, 'ticket', 0)) for p in minhas_posicoes}
        tickets_motor = {p.ticket for p in motor.obter_posicoes_abertas()}

        # Recuperar tickets do MT5 que não estão no motor (restart)
        novos = tickets_mt5_meus - tickets_motor
        for t in novos:
            pos_mt5 = next(p for p in minhas_posicoes if int(getattr(p, 'ticket', 0)) == t)
            tipo = TipoPosicao.COMPRADA if getattr(pos_mt5, 'type', 0) == 0 else TipoPosicao.VENDIDA
            motor.abrir_posicao(
                ticket=t, tipo=tipo,
                preco_entrada=float(getattr(pos_mt5, 'price_open', 0)),
                volume=float(getattr(pos_mt5, 'volume', 1)),
                stop_loss=float(getattr(pos_mt5, 'sl', 0)),
                take_profit=float(getattr(pos_mt5, 'tp', 0)),
                contexto_operacional=build_contexto_operacional_com_diario(
                    getattr(_opening_context_runtime, "features", None),
                    db_path=TRADING_DB_PATH,
                ),
            )
            logger.info(f"[ISOLAMENTO] Ticket #{t} (magic={MAGIC_NUMBER}) "
                       f"recuperado do MT5 via MotorDecisaoIsolado.")

        # Remover tickets fechados no MT5
        fechados = tickets_motor - tickets_mt5_meus
        for t in fechados:
            tick = mt5_adapter._mt5.symbol_info_tick(SIMBOLO)
            preco = tick.bid if tick else 0.0
            pos_motor = next(
                (p for p in motor.obter_posicoes_abertas() if p.ticket == t),
                None,
            )
            if pos_motor:
                motivo = inferir_motivo_fechamento(pos_motor, preco)
                registrar_fechamento_operacional(pos_motor, preco, motivo)
            else:
                motivo = MotivoFechamento.MANUAL
            motor.fechar_posicao(
                t,
                preco,
                motivo,
                contexto_operacional=build_contexto_operacional_com_diario(
                    getattr(_opening_context_runtime, "features", None),
                    db_path=TRADING_DB_PATH,
                ),
            )
            logger.info(f"[ISOLAMENTO] Ticket #{t} fechado (SL/TP/manual).")

        # Atualizar P&L de posições ativas
        for pos_mt5 in minhas_posicoes:
            t = int(getattr(pos_mt5, 'ticket', 0))
            preco_atual = float(getattr(pos_mt5, 'price_current', 0))
            motor.atualizar_posicao(t, preco_atual)
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


_validador_sl = ValidadorSLBreakEven(tick_size=5.0)


def modificar_sl_ordem(ticket: int, novo_sl: float) -> bool:
    """Modifica o Stop Loss de uma posicao aberta.

    Usa ValidadorSLBreakEven (BUG-MICRO-01) para:
    - Evitar retcode=10013 quando diferenca < tick_size do WIN$ (5 pts)
    - Reclassificar "SL ja no break-even" como INFO (nao ERROR)
    - Alinhar SL ao multiplo do tick antes de enviar
    - Retry com offset de 2 ticks se retcode=10013

    Args:
        ticket: ID do ticket da posicao
        novo_sl: Novo valor de SL

    Returns:
        True se sucesso ou SL ja aplicado, False caso contrario
    """
    try:
        if not hasattr(mt5_adapter, '_mt5') or mt5_adapter._mt5 is None:
            logger.warning(
                f"[PROTECAO] MT5 nao disponivel. Nao foi possivel modificar SL do ticket {ticket}"
            )
            return False

        # Busca a posicao
        positions = mt5_adapter._mt5.positions_get()
        if not positions:
            return False

        position = None
        for p in positions:
            if int(getattr(p, 'ticket', 0) or 0) == int(ticket):
                position = p
                break

        if position is None:
            logger.warning(f"[PROTECAO] Posicao #{ticket} nao encontrada")
            return False

        current_sl = float(position.sl) if position.sl else 0.0
        direcao = "BUY" if int(getattr(position, 'type', 0)) == 0 else "SELL"

        # BUG-MICRO-01: Validar diferenca vs tick_size antes de enviar
        validacao = _validador_sl.validar(
            sl_novo=float(novo_sl),
            sl_atual_mt5=current_sl,
            direcao=direcao,
        )

        if not validacao.permitido:
            # Nivel de log adequado: INFO para "ja aplicado", DEBUG para diferenca insuficiente
            nivel = validacao.nivel_log
            msg = (
                f"[PROTECAO] Ticket {ticket}: {validacao.motivo} "
                f"(sl_break_even_aplicado={validacao.sl_break_even_aplicado})"
            )
            if nivel == "INFO":
                logger.info(msg)
            else:
                logger.debug(msg)
            # Retorna True quando SL ja esta aplicado (situacao normal, nao falha)
            return validacao.sl_break_even_aplicado

        sl_para_enviar = validacao.sl_ajustado

        # Prepara requisicao para modificacao com SL alinhado ao tick
        request = {
            'action': mt5_adapter._mt5.TRADE_ACTION_MODIFY,
            'position': int(position.ticket),
            'sl': sl_para_enviar,
            'tp': float(position.tp) if position.tp else 0,
            'magic': MAGIC_NUMBER,
            'comment': 'Profit Protection SL Update'
        }

        logger.debug(
            f"[PROTECAO] Enviando modify para ticket {ticket}: "
            f"SL={sl_para_enviar:.2f} (original={novo_sl:.2f}), "
            f"TP={float(position.tp) if position.tp else 0:.2f}, "
            f"SL atual={current_sl:.2f}"
        )

        result = mt5_adapter._mt5.order_send(request)

        if result is None:
            logger.error(
                f"[PROTECAO] order_send retornou None para ticket {ticket}. "
                f"Verificar conexao MT5 ou conta bloqueada."
            )
            return False

        retcode = getattr(result, 'retcode', -1)
        comment = getattr(result, 'comment', 'Sem detalhes')

        if retcode != mt5_adapter._mt5.TRADE_RETCODE_DONE:
            logger.warning(
                f"[PROTECAO] Falha ao modificar SL do ticket {ticket}: "
                f"retcode={retcode}, mensagem={comment}. "
                f"Req: SL={sl_para_enviar:.2f}, TP={float(position.tp) if position.tp else 0:.2f}"
            )

            # BUG-MICRO-01: Retry com offset de 2 ticks se retcode=10013
            if retcode == 10013:
                validacao_retry = _validador_sl.validar_retry_apos_falha(
                    sl_original=sl_para_enviar,
                    sl_atual_mt5=current_sl,
                    direcao=direcao,
                    retcode=retcode,
                )
                if validacao_retry.permitido:
                    logger.info(
                        f"[PROTECAO] Retry com offset 2 ticks: "
                        f"SL={validacao_retry.sl_ajustado:.2f} (era {sl_para_enviar:.2f})"
                    )
                    request['sl'] = validacao_retry.sl_ajustado
                    result_retry = mt5_adapter._mt5.order_send(request)
                    retcode_retry = getattr(result_retry, 'retcode', -1) if result_retry else -1
                    if result_retry and retcode_retry == mt5_adapter._mt5.TRADE_RETCODE_DONE:
                        logger.info(
                            f"[PROTECAO] SL modificado (retry) para ticket {ticket}: "
                            f"{validacao_retry.sl_ajustado:.2f}"
                        )
                        return True
                    logger.warning(
                        f"[PROTECAO] Retry falhou. retcode={retcode_retry}"
                    )
            elif retcode == 10009:
                logger.error(
                    f"  -> INVALID PRICE: SL {sl_para_enviar:.2f} fora do spread"
                )
            elif retcode == 10010:
                logger.error(
                    f"  -> INVALID STOPS: SL={sl_para_enviar:.2f}, "
                    f"TP={float(position.tp):.2f}"
                )
            elif retcode == 10014:
                logger.error("  -> INVALID VOLUME: verificar volume=1")

            return False

        logger.info(f"[PROTECAO] SL modificado com sucesso para ticket {ticket}: {sl_para_enviar:.2f}")
        return True

    except Exception as e:
        logger.error(f"[PROTECAO] Erro ao modificar SL: {e}")
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
        if mt5_adapter is None:
            return
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

        pl_atual = obter_pl_sessao(saldo_inicial)

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
    """Exibe status operacional aderente ao PRD."""
    logger.info("\n" + "=" * 70)
    logger.info("[STATUS] OPERACAO RL 5000")
    logger.info("=" * 70)
    logger.info(f"Agente ID: {AGENTE_ID}")
    logger.info(f"Modo SL/TP: {SL_TP_MODE.upper()}")
    logger.info("Janela de monitoramento: 09:00-17:55 BRT")
    logger.info("Novas entradas permitidas até: 17:25 BRT")
    logger.info(
        f"Limite diário: {AntiOvertradingConfig.MAX_TRADES_PER_SESSION} trades"
    )
    logger.info(f"Última operação: {last_trade_time.strftime('%H:%M:%S') if last_trade_time else 'Nenhuma'}")
    logger.info(
        f"Cooldown base: {AntiOvertradingConfig.COOLDOWN_SECONDS}s | "
        f"Pos-SL: {AntiOvertradingConfig.STOP_LOSS_COOLDOWN_SECONDS // 60} min"
    )
    logger.info("=" * 70 + "\n")


def _verificar_pode_abrir_posicao_rl5000(
    reader: Optional[CoordinationSignalReader] = None,
) -> bool:
    """Verifica sinal de coordenacao antes de abrir posicao no RL 5000.

    Delega para ``src.application.coordination_integration`` para permitir
    teste unitario sem dependencias pesadas deste script.

    Args:
        reader: Leitor externo para injecao em testes. Se None, usa o
                reader modulo-level ``_coordination_reader``.

    Returns:
        True se abertura permitida, False se bloqueada por STOP_OPERACOES.
    """
    r = reader if reader is not None else _coordination_reader
    return _verificar_coordination_global(reader=r)


def loop_operacao() -> str:
    """Loop principal com proteções anti-overtrading."""
    global last_signal, trades_executed_today

    logger.info("\n" + "=" * 70)
    logger.info("[START] INICIANDO OPERACAO RL v5000 (MODO PRODUCAO ESTRITO)")
    logger.info("=" * 70)
    logger.info(f"Alvo: R${TARGET_LUCRO_DIARIO} | Stop: R${STOP_PERDA_DIARIA}")
    logger.info(
        f"Trades/dia: max {AntiOvertradingConfig.MAX_TRADES_PER_SESSION}"
    )
    logger.info(
        "Janela operacional: monitora ate 17:55, novas entradas so ate 17:25"
    )
    logger.info(
        f"Cooldown entre trades: {AntiOvertradingConfig.COOLDOWN_SECONDS}s "
        f"| cooldown pos-SL: {AntiOvertradingConfig.STOP_LOSS_COOLDOWN_SECONDS // 60} min"
    )
    logger.info(f"Min volatilidade: {AntiOvertradingConfig.MIN_VOLATILITY_PERCENT}%")
    logger.info(f"Confirmação sinal: {AntiOvertradingConfig.CONFIRM_SIGNAL_BARS} velas")
    logger.info(
        f"Confianca minima: {AntiOvertradingConfig.MIN_CONFIDENCE_SCORE:.0%} "
        f"| Risk/Reward minimo: {AntiOvertradingConfig.MIN_RISK_REWARD:.1f}:1"
    )

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

        # BUG-4 (18/03/2026): guard de horario ANTES das protecoes de lucro
        # para evitar ~380 ERRORs/dia por desconexao MT5 esperada fora do pregao.
        logger.debug(f"[CICLO {ciclo}] Verificando horário de trading...")
        if not verificar_horario_trading():
            logger.info("[HORA] Fora do horario. Aguardando...")
            logger.debug(f"[CICLO {ciclo}] Dormindo 60s (fora do horário)...")
            time.sleep(60)
            logger.debug(f"[CICLO {ciclo}] Retornando ao início do loop após sleep.")
            continue

        # ✅ PROTEÇÃO DE LUCRO: Monitora trades abertos continuamente (sistema existente)
        # Executado DENTRO do horario operacional para evitar erros de conexao MT5
        logger.debug(f"[CICLO {ciclo}] Executando proteger_lucro_trade()...")
        proteger_lucro_trade()
        logger.debug(f"[CICLO {ciclo}] proteger_lucro_trade() concluído.")

        # ✅ PROTEÇÃO DE LUCRO: Motor dinâmico (P1-PROFIT_PROTECTION) - NEW
        logger.debug(f"[CICLO {ciclo}] Executando processar_protecao_lucros()...")
        processar_protecao_lucros()
        logger.debug(f"[CICLO {ciclo}] processar_protecao_lucros() concluído.")

        if ciclo % 10 == 0:
            ajustar_profit_protection_por_regime_runtime(ciclo_atual=ciclo)

        lucro_sessao = obter_pl_sessao(saldo_inicial)
        logger.debug(f"[CICLO {ciclo}] Verificando lucro vs TARGET...")
        if lucro_sessao >= TARGET_LUCRO_DIARIO:
            logger.info(f"[TARGET] ATINGIDO: R${lucro_sessao:.2f}")
            return "TARGET_ATINGIDO"

        logger.debug(f"[CICLO {ciclo}] Verificando stop loss...")
        if lucro_sessao <= STOP_PERDA_DIARIA:
            logger.warning(f"[STOP] STOP LOSS ACIONADO: R${lucro_sessao:.2f}")
            return "STOP_LOSS"

        logger.debug(f"[CICLO {ciclo}] Monitorando posições abertas...")
        if monitorar_posicoes():
            logger.warning("[GUARD] BLOCKED: posicao_aberta")
            logger.info("[WAIT] Posicao em aberto. Aguardando fechar...")
            logger.debug(f"[CICLO {ciclo}] Dormindo 30s (posição aberta)...")
            time.sleep(30)
            logger.debug(f"[CICLO {ciclo}] Retornando ao início do loop após sleep.")
            continue

        if not verificar_janela_novas_entradas():
            logger.warning("[GUARD] BLOCKED: janela_novas_entradas_encerrada")
            logger.info(
                "[JANELA] Novas entradas bloqueadas a partir de 17:25. "
                "Mantendo apenas monitoramento ate o fim do pregao."
            )
            time.sleep(60)
            continue

        if not verificar_limite_trades():
            time.sleep(60)
            continue

        logger.info(f"\n[Ciclo {ciclo}] Consultando mercado...")
        logger.debug(f"[CICLO {ciclo}] Carregando dados do MT5...")
        dados = carregar_dados_mt5(SIMBOLO, n_candles=100)
        logger.debug(f"[CICLO {ciclo}] Dados carregados: {len(dados) if dados is not None else 0} candles")

        if dados is None or len(dados) < 20:
            logger.warning("[GUARD] BLOCKED: dados_insuficientes")
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

        # 1. Volatilidade agora entra como feature contextual, não como bloqueio binário
        logger.debug(f"[CICLO {ciclo}] Calculando volatilidade...")
        vol = calcular_volatilidade(dados)
        logger.debug(f"[CICLO {ciclo}] Volatilidade calculada: {vol:.3f}%")

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
            acao_id, confidence, state_vector = obter_acao_do_modelo(dados)
            mapeamento = {1: "Comprar", 0: "Aguardar", 2: "Vender"}
            acao_str = mapeamento.get(acao_id, "Aguardar")
            preco_atual = float(dados['close'].iloc[-1])
            logger.debug(f"[CICLO {ciclo}] Ação obtida: {acao_str} (confiança: {confidence:.2%})")

            # Grupo 2: Pipeline Feedback/Aprendizado (a cada 10 ciclos)
            if ciclo % 10 == 0:
                try:
                    _executar_pipeline_feedback_rl(preco_referencia=preco_atual)
                except Exception as _e:
                    logger.warning(f'[PIPELINE-FEEDBACK] Erro: {_e}')

            # 5. Verificar confirmação multi-vela
            logger.debug(f"[CICLO {ciclo}] Verificando confirmação do sinal...")
            if confirmado := verificar_confirmacao_sinal(acao_str, last_signal):
                # Executar apenas se confirmado E passou todas as validações
                # Passar dados para cálculo dinâmico de SL/TP
                logger.info(f"[CICLO {ciclo}] Sinal CONFIRMADO! Enviando ordem...")

                # 5.5. Gate de coordenacao cross-agent (BLID-043)
                if _coordination_reader is not None and not _coordination_reader.pode_abrir_posicao():
                    _sinal_coord = _coordination_reader.obter_sinal_atual()
                    logger.warning(
                        "[CICLO %d] [COORDENACAO] STOP_OPERACOES ativo — "
                        "abertura de posicao bloqueada (sinal=%s). Aguardando...",
                        ciclo,
                        _sinal_coord.value,
                    )
                    time.sleep(5)
                    continue

                logger.debug(f"[CICLO {ciclo}] Chamando enviar_ordem_mt5adapter()...")
                ordem_enviada = enviar_ordem_mt5adapter(
                    acao_str,
                    preco_atual,
                    vol,
                    dados=dados,
                    confidence=confidence,
                    opening_context=getattr(_opening_context_runtime, "features", None),
                    state_vector=state_vector,
                    original_action=mapear_acao_operacional_para_rl(acao_str),
                )
                last_signal = acao_str
                if ordem_enviada:
                    logger.debug(f"[CICLO {ciclo}] Ordem enviada com sucesso.")
                    trades_executed_today += 1
                    registrar_progresso_objetivos(saldo_inicial, forcar=True)
                    print_status()
                    logger.debug(
                        f"[CICLO {ciclo}] Cooldown por {AntiOvertradingConfig.COOLDOWN_SECONDS}s..."
                    )
                    time.sleep(AntiOvertradingConfig.COOLDOWN_SECONDS)
                    logger.debug(f"[CICLO {ciclo}] Cooldown finalizado.")
                else:
                    logger.info(
                        f"[CICLO {ciclo}] Ordem nao enviada apos validacoes. Retomando monitoramento."
                    )
                    time.sleep(30)
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

    # Ponto de saída defensivo: while True nunca deveria chegar aqui
    logger.warning("[LOOP] while True encerrado de forma inesperada.")
    return "ENCERRADO_NORMAL"


def inicializar_componentes_auxiliares() -> None:
    """Inicializa módulos auxiliares somente no bootstrap real."""
    global _monitor_posicao_rl
    global _feedback_validator_rl
    global _drift_detector_rl
    global _online_learning_rl
    global _baseline_comparator_rl
    global _opening_context_runtime
    global _coordination_manager
    global _coordination_reader

    _monitor_posicao_rl = None
    if AC5_8_DISPONIVEL and MonitorPositionManager:
        try:
            _monitor_posicao_rl = MonitorPositionManager(
                db_caminho=TRADING_DB_PATH,
            )
            logger.info("[OK] AC5.8 MonitorPositionManager: Ativo")
        except Exception as e:
            logger.warning(f"[!] AC5.8: {e}")

    if _AC5_9_DISPONIVEL and FeedbackValidator:
        try:
            _feedback_validator_rl = FeedbackValidator()
            logger.info("[OK] AC5.9 FeedbackValidator: Ativo")
        except Exception as e:
            logger.warning(f"[!] AC5.9: {e}")

    if _AC6_DISPONIVEL and (
        DriftDetector or OnlineLearningController or BaselineComparator
    ):
        try:
            ac6 = build_ac6_components(
                drift_detector_cls=DriftDetector if _AC6_DISPONIVEL else None,
                online_learning_cls=OnlineLearningController if _AC6_DISPONIVEL else None,
                baseline_comparator_cls=BaselineComparator if _AC6_DISPONIVEL else None,
                model_name=f"rl_5000_{AGENTE_ID}",
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
            logger.warning(f"[!] AC6 bootstrap: {e}")

    _opening_context_runtime = initialize_opening_context_runtime(
        db_path=TRADING_DB_PATH,
        agent_name="rl_5000",
        source="operar_novo_agente_rl_real_antiovertrading",
        session_id=AGENTE_ID,
        mode=SL_TP_MODE.upper(),
        logger=logger,
        operational_context_dir=os.getenv("OPENING_CONTEXT_DIR") or None,
    )
    if _opening_context_runtime.prompt_abertura_agentes:
        logger.info(
            "%s Prompt operacional lido pelo agente: %s",
            OPENING_CONTEXT_LABEL,
            _opening_context_runtime.prompt_abertura_agentes,
        )

    # BLID-043: Coordenacao cross-agent — CoordinationManager como thread daemon
    _coordination_manager = None
    _coordination_reader = None
    if _COORDINATION_DISPONIVEL and CoordinationManager and ConfiguracaoCoordinacao and CoordinationSignalReader:
        logger.info("[INIT] Inicializando CoordinationManager (BLID-043)...")
        try:
            _coord_cfg = ConfiguracaoCoordinacao(
                db_path=TRADING_DB_PATH,
                db_path_por_agente=_resolve_coordination_db_paths(),
                agentes_monitorados=["rl_5000", "rl_direto"],
                sinal_atual_path="outputs/coordination_signal_rl_5000.json",
            )
            _coordination_manager = CoordinationManager(config=_coord_cfg)
            _coordination_reader = CoordinationSignalReader(
                sinal_path="outputs/coordination_signal_rl_5000.json"
            )
            _coordination_manager.iniciar()
            logger.info("[OK] CoordinationManager thread daemon iniciada (BLID-043)")
        except Exception as _e_coord:
            logger.warning(
                "[WARN] CoordinationManager init falhou: %s — fallback NORMAL (BLID-043)",
                _e_coord,
            )
            _coordination_manager = None
            _coordination_reader = None

    # BLID-045: Alertas de reversao de lucro
    global _alert_reversao_handler, _alerta_delivery_manager
    if _ALERT_REVERSAO_DISPONIVEL and AlertReversaoHandler and AlertaDeliveryManager:
        logger.info("[INIT] Inicializando AlertReversaoHandler (BLID-045)...")
        try:
            # Carregar config de config/alert_reversoes.yaml se existir
            alert_config = AlertReversaoConfig()
            config_path = ROOT_DIR / "config" / "alert_reversoes.yaml"
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    yaml_config = yaml.safe_load(f)
                    alert_config = AlertReversaoConfig(
                        habilitado=yaml_config.get("habilitado", True),
                        webhook_url=yaml_config.get("webhook_url") or os.getenv("ALERT_WEBHOOK_URL"),
                        webhook_timeout_sec=yaml_config.get("webhook_timeout_sec", 5.0),
                        webhook_retry_attempts=yaml_config.get("webhook_retry_attempts", 3),
                        webhook_retry_backoff_sec=yaml_config.get("webhook_retry_backoff_sec", 0.5),
                        webhook_fire_and_forget=yaml_config.get("webhook_fire_and_forget", False),
                        throttle_seconds=yaml_config.get("throttle_seconds", 60),
                        persistir_throttle_state=yaml_config.get("persistir_throttle_state", True),
                        throttle_state_path=yaml_config.get(
                            "throttle_state_path",
                            "outputs/alert_reversao_throttle_state.json",
                        ),
                    )
            else:
                # Fallback: env var ou padrao
                alert_config.webhook_url = os.getenv("ALERT_WEBHOOK_URL")

            # Inicializar delivery manager (sem WebSocket para evitar dependencias)
            _alerta_delivery_manager = AlertaDeliveryManager(
                websocket_client=None,  # Pode ser None (AC7 graceful degradation)
                email_config=None,  # Pode ser None
            )

            _alert_reversao_handler = AlertReversaoHandler(
                delivery_manager=_alerta_delivery_manager,
                config=alert_config,
            )
            logger.info(
                "[OK] AlertReversaoHandler inicializado | webhook=%s | throttle=%ds (BLID-045)",
                "SIM" if alert_config.webhook_url else "NAO",
                alert_config.throttle_seconds,
            )
        except Exception as _e_alert:
            logger.warning(
                "[WARN] AlertReversaoHandler init falhou: %s — alertas desabilitados (BLID-045)",
                _e_alert,
            )
            _alert_reversao_handler = None
            _alerta_delivery_manager = None
    else:
        logger.info("[SKIP] AlertReversaoHandler nao disponivel - alertas de reversao desabilitados (BLID-045)")


def main() -> int:
    """Bootstrap explícito do runtime RL 5000."""
    configure_logging()
    logger.info(f"Modo SL/TP: {SL_TP_MODE.upper()}")
    logger.info(f"ID do Agente: {AGENTE_ID}")
    logger.info("Motor de proteção de lucros ativado (P1-PROFIT_PROTECTION)")
    logger.info(f"Motor Isolado: MotorDecisaoIsolado({AGENTE_ID})")
    get_motor_isolado()

    try:
        logger.info("Inicializando...")
        get_config()
        inicializar_adaptador_mt5()
        inicializar_agente_rl()
        inicializar_rl_repo()
        inicializar_componentes_auxiliares()
        motivo_encerramento = loop_operacao()

        if motivo_encerramento == "TARGET_ATINGIDO":
            logger.info("[EXIT] Encerrado por meta diaria atingida.")
            return EXIT_CODE_TARGET_ATINGIDO

        if motivo_encerramento == "STOP_LOSS":
            logger.warning("[EXIT] Encerrado por stop loss diario acionado.")
            return EXIT_CODE_STOP_LOSS

        logger.info("[EXIT] Encerrado sem motivo operacional especifico.")
        return EXIT_CODE_OK

    except KeyboardInterrupt:
        logger.info("\n[STOP] Operacao interrompida pelo usuario.")
        print_status()
        return EXIT_CODE_OK
    except Exception as e:
        logger.error(f"[ERRO] Erro fatal: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    finally:
        try:
            relatorio_contexto = generate_opening_context_vs_result_report(
                db_path=TRADING_DB_PATH,
                output_dir=ROOT_DIR / "outputs" / "analysis",
                outputs_root=ROOT_DIR / "outputs",
            )
            logger.info(
                "%s Relatório contexto x resultado gerado: %s",
                OPENING_CONTEXT_LABEL,
                relatorio_contexto.markdown_path,
            )
        except Exception as e:
            logger.warning(
                "%s Falha ao gerar relatório final: %s",
                OPENING_CONTEXT_LABEL,
                e,
            )

        if _monitor_posicao_rl:
            _monitor_posicao_rl.fechar()
        # BLID-043: Encerrar CoordinationManager
        try:
            if _coordination_manager is not None:
                _coordination_manager.parar()
                logger.info("[OK] CoordinationManager encerrado (BLID-043)")
        except Exception as _e_coord_stop:
            logger.warning("[WARN] Erro ao encerrar CoordinationManager: %s", _e_coord_stop)
        if mt5_adapter:
            mt5_adapter.disconnect()
            logger.info("[OK] MT5 desconectado.")


if __name__ == "__main__":
    raise SystemExit(main())
