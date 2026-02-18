"""
Agente de Micro Tendências para Day Trade WINFUT.

Captura micro tendências intraday para gerar oportunidades de operação.
Baseado no modelo docs/model_agente/winfut_micro_tendencia/.

Ciclo: 2 minutos (120s)
Horário: 09:00 - 17:55 (Brasília)

Funcionalidades:
  - Direcional do dia via sistema de pontuação macro
  - Regiões de interesse (VWAP, Pivôs, SMC, Suporte/Resistência)
  - Micro tendências M5/M15 com indicadores de momentum
  - Geração de oportunidades com entrada, SL, TP e R/R
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time as dtime
from decimal import Decimal, ROUND_HALF_UP
import math
import os
import sys
import time
from typing import Optional

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Config local: herda TradingConfig com extra="ignore" para tolerar campos
# extras no .env sem alterar o config/settings.py original.
from pathlib import Path as _Path
from pydantic_settings import SettingsConfigDict
from config.settings import TradingConfig as _BaseTradingConfig


class _MicroTrendConfig(_BaseTradingConfig):
    model_config = SettingsConfigDict(
        env_file=_Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def _get_config() -> _MicroTrendConfig:
    return _MicroTrendConfig()


from src.domain.value_objects import Symbol, Price, Quantity
from src.domain.entities.trade import Order
from src.domain.enums.trading_enums import TimeFrame, OrderSide, OrderType, TradeSignal
from src.infrastructure.adapters.mt5_adapter import MT5Adapter, Candle, TickData
from src.infrastructure.database.schema import create_database, get_session
from src.application.services.macro_score.engine import (
    MacroScoreEngine,
    MacroScoreResult,
    ItemScoreResult,
)
from src.domain.enums.macro_score_enums import MacroSignal
from src.application.services.head_directives import (
    HeadDirective,
    create_directives_table,
    load_active_directive,
)
from src.application.services.diary_feedback import (
    DiaryFeedback,
    create_diary_feedback_table,
    load_latest_feedback,
)

# ────────────────────────────────────────────────────────────────
# Constantes
# ────────────────────────────────────────────────────────────────

REFRESH_SECONDS = 120
PROGRESS_BAR_WIDTH = 38
SYMBOL = "WIN$N"
DB_PATH: str | None = None

# Instância global do MacroScoreEngine (inicializada no main)
_macro_engine: MacroScoreEngine | None = None

# Diretiva ativa do Head Financeiro (carregada na main, atualizada a cada ciclo)
_active_directive: HeadDirective | None = None

# Feedback do diário (análise crítica RL, carregado a cada 10 ciclos)
_diary_feedback: DiaryFeedback | None = None

# ── Dampening do Macro Score (EMA inter-ciclo) ──
_prev_macro_score: int | None = None
_prev_macro_date: str | None = None      # Reseta EMA na virada de pregão
DEFAULT_DAMPENING_ALPHA = 0.3            # Peso do score atual na EMA

# ── Auto-suspensão da diretiva quando mercado diverge ──
_directive_diverge_counter: int = 0       # Ciclos consecutivos com divergência
DIRECTIVE_DIVERGE_THRESHOLD = 10         # Diferença de score para contar divergência
DIRECTIVE_DIVERGE_CYCLES = 3             # Ciclos necessários para suspender

# Horários de pregão (Brasília)
PREGAO_INICIO = dtime(9, 0)
PREGAO_FIM = dtime(17, 55)

# Thresholds do Score Macro (ajustados para 104 itens do MacroScoreEngine)
# Com 104 itens e pesos ponderados, o range efetivo é muito maior que os
# 19 itens legados. O MacroScoreEngine já gera o signal via neutral_threshold,
# mas os thresholds abaixo são usados para lógica de oportunidades/micro_trend.
SCORE_COMPRA_THRESHOLD = 4    # FIX: Reduzido de 5 para 4 — threshold 5 bloqueava oportunidades demais
SCORE_VENDA_THRESHOLD = -4    # FIX: Reduzido de -5 para -4

# ── Trading Automático (desabilitado por padrão) ──
AUTO_TRADING_ENABLED = False   # ⚠️ Ativar via flag --auto-trade
SIMULATE_MODE = False          # 🧪 Modo simulado — logar sem executar (--simulate)
MAX_CONTRACTS = 1              # Contratos por operação
MAX_POSITIONS = 1              # Máximo de posições simultâneas
MIN_CONFIDENCE_TRADE = 45      # Confiança mínima da oportunidade (%) — FIX 12/02/2026: Reduzido de 60 para 45 (agente ficava 100% HOLD com threshold 60)
MIN_RR_TRADE = Decimal("1.5")  # Risk/Reward mínimo
MAX_DAILY_LOSS = Decimal("500")   # Loss máximo diário em pontos
MAX_DAILY_TRADES = 6           # Máximo de trades por dia
TRAILING_STOP_ENABLED = True
TRAILING_DISTANCE_PTS = Decimal("150")  # Distância do trailing em pontos
# FIX 12/02/2026: Cooling-off após stop loss para evitar TILT (reentrada emocional)
COOLING_OFF_MINUTES = 30  # Minutos de espera após stop loss na mesma direção

# Watchdog hedge: fecha posição órfã/contrária sem proteção completa
WATCHDOG_HEDGE_ENABLED = True
WATCHDOG_AUTO_CLOSE_HEDGE_ORPHAN = True

# Plano de lições aprendidas — execução operacional
REVERSAL_BLOCK_ADX = Decimal("24")
REVERSAL_BLOCK_MACRO_SCORE = 7
TREND_MIN_CONFLUENCE = 2
TREND_MAX_DISTANCE_PCT = Decimal("0.35")

# ────────────────────────────────────────────────────────────────
# Dataclasses
# ────────────────────────────────────────────────────────────────


@dataclass
class MacroItem:
    """Item individual do score macro."""

    number: int
    symbol: str
    name: str
    category: str
    correlation: str  # DIRETA ou INVERSA
    score: int = 0
    price_current: Decimal = Decimal("0")
    price_open: Decimal = Decimal("0")
    available: bool = False
    reason: str = ""


@dataclass
class PivotLevels:
    """Níveis de pivô diário."""

    pp: Decimal = Decimal("0")
    r1: Decimal = Decimal("0")
    r2: Decimal = Decimal("0")
    r3: Decimal = Decimal("0")
    s1: Decimal = Decimal("0")
    s2: Decimal = Decimal("0")
    s3: Decimal = Decimal("0")


@dataclass
class VWAPData:
    """Dados de VWAP e desvios."""

    vwap: Decimal = Decimal("0")
    upper_1: Decimal = Decimal("0")  # +1σ
    upper_2: Decimal = Decimal("0")  # +2σ
    lower_1: Decimal = Decimal("0")  # -1σ
    lower_2: Decimal = Decimal("0")  # -2σ


@dataclass
class SMCData:
    """Dados de Smart Money Concepts."""

    direction: str = "NEUTRO"  # ALTA, BAIXA, NEUTRO
    bos_score: int = 0
    equilibrium: str = "NEUTRO"  # DISCOUNT, PREMIUM, NEUTRO
    equilibrium_score: int = 0
    fvg_score: int = 0
    last_bos_price: Decimal = Decimal("0")
    last_bos_type: str = ""  # BOS_ALTA, BOS_BAIXA, CHOCH_ALTA, CHOCH_BAIXA


@dataclass
class SMCTimeframeData:
    """Dados SMC detalhados para um timeframe específico."""

    timeframe: str = ""          # H4, M15, M5
    direction: str = "NEUTRO"    # ALTA, BAIXA, NEUTRO
    bias: str = "NEUTRO"         # BULLISH, BEARISH, NEUTRO
    bos_type: str = ""           # BOS_ALTA, BOS_BAIXA, CHOCH_ALTA, CHOCH_BAIXA
    bos_price: Decimal = Decimal("0")
    equilibrium: str = "NEUTRO"  # DISCOUNT, PREMIUM, NEUTRO
    # Níveis de compra/venda derivados da estrutura SMC
    buy_zone: Decimal = Decimal("0")    # Zona de compra (OB alta / demand zone)
    sell_zone: Decimal = Decimal("0")   # Zona de venda (OB baixa / supply zone)
    # Swing points para referência
    last_swing_high: Decimal = Decimal("0")
    last_swing_low: Decimal = Decimal("0")
    # FVG
    fvg_price: Decimal = Decimal("0")
    fvg_type: str = ""           # FVG_ALTA, FVG_BAIXA
    # Scores
    score: int = 0               # Score consolidado [-3, +3]
    hh_count: int = 0            # Higher Highs
    hl_count: int = 0            # Higher Lows
    lh_count: int = 0            # Lower Highs
    ll_count: int = 0            # Lower Lows


@dataclass
class SMCMultiTF:
    """SMC consolidado multi-timeframe (H4, M15, M5)."""

    h4: SMCTimeframeData = field(default_factory=lambda: SMCTimeframeData(timeframe="H4"))
    m15: SMCTimeframeData = field(default_factory=lambda: SMCTimeframeData(timeframe="M15"))
    m5: SMCTimeframeData = field(default_factory=lambda: SMCTimeframeData(timeframe="M5"))
    # Concordância multi-TF
    alignment: str = "NEUTRO"  # BULLISH, BEARISH, MISTO, NEUTRO
    alignment_score: int = 0   # [-3, +3]


@dataclass
class MomentumData:
    """Indicadores de momentum M5."""

    rsi: Decimal = Decimal("50")
    rsi_score: int = 0
    stoch: Decimal = Decimal("50")
    stoch_score: int = 0
    macd_signal: str = "NEUTRO"
    macd_score: int = 0
    bb_position: str = "DENTRO"  # ACIMA, ABAIXO, DENTRO
    bb_score: int = 0
    adx: Decimal = Decimal("0")
    adx_score: int = 0
    ema9_distance_pct: Decimal = Decimal("0")
    ema9_score: int = 0


@dataclass
class RegionOfInterest:
    """Região de interesse para operação."""

    price: Decimal
    label: str
    tipo: str  # SUPORTE, RESISTENCIA, VWAP, PIVOT, SMC, D1
    confluences: int = 1
    distance_pct: Decimal = Decimal("0")
    source_tf: str = ""       # M1, M5, M15, D1, MULTI — timeframe de origem
    volume_strength: int = 0  # 0=sem info, 1=normal, 2=acima média, 3=explosão


@dataclass
class Opportunity:
    """Oportunidade de operação identificada."""

    direction: str  # COMPRA ou VENDA
    entry: Decimal = Decimal("0")
    stop_loss: Decimal = Decimal("0")
    take_profit: Decimal = Decimal("0")
    risk_reward: Decimal = Decimal("0")
    confidence: Decimal = Decimal("0")
    reason: str = ""
    region: str = ""


@dataclass
class CycleResult:
    """Resultado completo de um ciclo de análise."""

    timestamp: datetime = field(default_factory=datetime.now)
    # Macro
    macro_score: int = 0
    macro_signal: str = "NEUTRO"
    macro_confidence: Decimal = Decimal("0")
    macro_items: list = field(default_factory=list)
    # Micro
    micro_score: int = 0
    micro_trend: str = "CONSOLIDAÇÃO"  # CONTINUAÇÃO, REVERSÃO, CONSOLIDAÇÃO
    # Dados
    price_current: Decimal = Decimal("0")
    price_open: Decimal = Decimal("0")
    vwap: VWAPData = field(default_factory=VWAPData)
    pivots: PivotLevels = field(default_factory=PivotLevels)
    smc: SMCData = field(default_factory=SMCData)
    smc_multi_tf: SMCMultiTF = field(default_factory=SMCMultiTF)
    momentum: MomentumData = field(default_factory=MomentumData)
    regions: list = field(default_factory=list)
    opportunities: list = field(default_factory=list)
    # Volume
    volume_score: int = 0
    obv_score: int = 0
    vwap_score: int = 0
    candle_pattern_score: int = 0
    aggression_score: int = 0
    aggression_ratio: Decimal = Decimal("0.50")


# ────────────────────────────────────────────────────────────────
# Funções de cálculo — Indicadores Técnicos
# ────────────────────────────────────────────────────────────────

def _calc_sma(values: list[Decimal], period: int) -> Decimal:
    """Calcula Simple Moving Average."""
    if len(values) < period:
        return Decimal("0")
    subset = values[-period:]
    return sum(subset) / Decimal(str(period))


def _calc_ema(values: list[Decimal], period: int) -> list[Decimal]:
    """Calcula Exponential Moving Average para toda a série."""
    if len(values) < period:
        return [Decimal("0")] * len(values)
    k = Decimal("2") / Decimal(str(period + 1))
    ema_vals = [Decimal("0")] * len(values)
    # Inicializa com SMA
    ema_vals[period - 1] = sum(values[:period]) / Decimal(str(period))
    for i in range(period, len(values)):
        ema_vals[i] = values[i] * k + ema_vals[i - 1] * (Decimal("1") - k)
    return ema_vals


def _calc_rsi(closes: list[Decimal], period: int = 14) -> Decimal:
    """Calcula RSI."""
    if len(closes) < period + 1:
        return Decimal("50")
    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains.append(diff)
            losses.append(Decimal("0"))
        else:
            gains.append(Decimal("0"))
            losses.append(abs(diff))
    if len(gains) < period:
        return Decimal("50")
    avg_gain = sum(gains[-period:]) / Decimal(str(period))
    avg_loss = sum(losses[-period:]) / Decimal(str(period))
    if avg_loss == 0:
        return Decimal("100")
    rs = avg_gain / avg_loss
    rsi = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))
    return rsi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calc_stochastic(
    highs: list[Decimal], lows: list[Decimal], closes: list[Decimal],
    period: int = 14,
) -> Decimal:
    """Calcula Stochastic %K."""
    if len(closes) < period:
        return Decimal("50")
    highest = max(highs[-period:])
    lowest = min(lows[-period:])
    if highest == lowest:
        return Decimal("50")
    k = ((closes[-1] - lowest) / (highest - lowest)) * Decimal("100")
    return k.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calc_macd(
    closes: list[Decimal],
    fast: int = 12, slow: int = 26, signal: int = 9,
) -> tuple[Decimal, Decimal, str]:
    """Calcula MACD. Retorna (macd_line, signal_line, cruzamento)."""
    if len(closes) < slow + signal:
        return Decimal("0"), Decimal("0"), "NEUTRO"
    ema_fast = _calc_ema(closes, fast)
    ema_slow = _calc_ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    # Signal line (EMA do MACD)
    valid_macd = [v for v in macd_line if v != Decimal("0")]
    if len(valid_macd) < signal:
        return Decimal("0"), Decimal("0"), "NEUTRO"
    signal_ema = _calc_ema(valid_macd, signal)
    macd_val = valid_macd[-1]
    sig_val = signal_ema[-1] if signal_ema else Decimal("0")
    # Cruzamento
    if len(valid_macd) >= 2 and len(signal_ema) >= 2:
        prev_macd = valid_macd[-2]
        prev_sig = signal_ema[-2]
        if prev_macd <= prev_sig and macd_val > sig_val:
            cross = "ALTA"
        elif prev_macd >= prev_sig and macd_val < sig_val:
            cross = "BAIXA"
        else:
            cross = "NEUTRO"
    else:
        cross = "NEUTRO"
    return macd_val, sig_val, cross


def _calc_bollinger(
    closes: list[Decimal], period: int = 20, num_std: int = 2,
) -> tuple[Decimal, Decimal, Decimal]:
    """Calcula Bollinger Bands. Retorna (upper, middle, lower)."""
    if len(closes) < period:
        return Decimal("0"), Decimal("0"), Decimal("0")
    subset = closes[-period:]
    middle = sum(subset) / Decimal(str(period))
    variance = sum((x - middle) ** 2 for x in subset) / Decimal(str(period))
    std = Decimal(str(math.sqrt(float(variance))))
    upper = middle + std * Decimal(str(num_std))
    lower = middle - std * Decimal(str(num_std))
    return upper, middle, lower


def _calc_adx(
    highs: list[Decimal], lows: list[Decimal], closes: list[Decimal],
    period: int = 14,
) -> Decimal:
    """Calcula ADX simplificado."""
    if len(closes) < period + 1:
        return Decimal("0")
    tr_list = []
    plus_dm_list = []
    minus_dm_list = []
    for i in range(1, len(closes)):
        high = highs[i]
        low = lows[i]
        prev_close = closes[i - 1]
        prev_high = highs[i - 1]
        prev_low = lows[i - 1]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        plus_dm = max(high - prev_high, Decimal("0"))
        minus_dm = max(prev_low - low, Decimal("0"))
        if plus_dm > minus_dm:
            minus_dm = Decimal("0")
        elif minus_dm > plus_dm:
            plus_dm = Decimal("0")
        else:
            plus_dm = Decimal("0")
            minus_dm = Decimal("0")
        tr_list.append(tr)
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)
    if len(tr_list) < period:
        return Decimal("0")
    atr = sum(tr_list[-period:]) / Decimal(str(period))
    if atr == 0:
        return Decimal("0")
    plus_di = (sum(plus_dm_list[-period:]) / Decimal(str(period))) / atr * 100
    minus_di = (sum(minus_dm_list[-period:]) / Decimal(str(period))) / atr * 100
    di_sum = plus_di + minus_di
    if di_sum == 0:
        return Decimal("0")
    dx = abs(plus_di - minus_di) / di_sum * 100
    return dx.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calc_atr(
    highs: list[Decimal], lows: list[Decimal], closes: list[Decimal],
    period: int = 14,
) -> Decimal:
    """Calcula ATR."""
    if len(closes) < period + 1:
        return Decimal("0")
    tr_list = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_list.append(tr)
    if len(tr_list) < period:
        return Decimal("0")
    return sum(tr_list[-period:]) / Decimal(str(period))


def _calc_obv(closes: list[Decimal], volumes: list[int]) -> list[Decimal]:
    """Calcula On-Balance Volume."""
    if len(closes) < 2:
        return [Decimal("0")]
    obv = [Decimal("0")]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv.append(obv[-1] + Decimal(str(volumes[i])))
        elif closes[i] < closes[i - 1]:
            obv.append(obv[-1] - Decimal(str(volumes[i])))
        else:
            obv.append(obv[-1])
    return obv


# ────────────────────────────────────────────────────────────────
# Funções de cálculo — VWAP
# ────────────────────────────────────────────────────────────────

def _calc_vwap_from_candles(candles: list[Candle]) -> VWAPData:
    """Calcula VWAP e desvios a partir de candles intraday."""
    if not candles:
        return VWAPData()
    cum_vol = Decimal("0")
    cum_tp_vol = Decimal("0")
    cum_tp2_vol = Decimal("0")
    for c in candles:
        tp = (c.high.value + c.low.value + c.close.value) / Decimal("3")
        vol = Decimal(str(c.volume)) if c.volume > 0 else Decimal("1")
        cum_vol += vol
        cum_tp_vol += tp * vol
        cum_tp2_vol += (tp ** 2) * vol
    if cum_vol == 0:
        return VWAPData()
    vwap = cum_tp_vol / cum_vol
    variance = (cum_tp2_vol / cum_vol) - (vwap ** 2)
    std = Decimal(str(math.sqrt(max(float(variance), 0))))
    # Arredonda ao tick size (WIN = 5 pts)
    tick = Decimal("5")
    def _snap(v: Decimal) -> Decimal:
        return (v / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick
    return VWAPData(
        vwap=_snap(vwap),
        upper_1=_snap(vwap + std),
        upper_2=_snap(vwap + std * 2),
        lower_1=_snap(vwap - std),
        lower_2=_snap(vwap - std * 2),
    )


# ────────────────────────────────────────────────────────────────
# Funções de cálculo — Pivôs Diários
# ────────────────────────────────────────────────────────────────

def _calc_pivot_levels(prev_high: Decimal, prev_low: Decimal, prev_close: Decimal) -> PivotLevels:
    """Calcula pivôs diários clássicos a partir do candle D1 anterior."""
    pp = (prev_high + prev_low + prev_close) / Decimal("3")
    r1 = pp * 2 - prev_low
    s1 = pp * 2 - prev_high
    r2 = pp + (prev_high - prev_low)
    s2 = pp - (prev_high - prev_low)
    r3 = prev_high + Decimal("2") * (pp - prev_low)
    s3 = prev_low - Decimal("2") * (prev_high - pp)
    # Arredonda ao tick size (WIN = 5 pts)
    tick = Decimal("5")
    def _snap(v: Decimal) -> Decimal:
        return (v / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick
    return PivotLevels(
        pp=_snap(pp),
        r1=_snap(r1),
        r2=_snap(r2),
        r3=_snap(r3),
        s1=_snap(s1),
        s2=_snap(s2),
        s3=_snap(s3),
    )


# ────────────────────────────────────────────────────────────────
# Funções de cálculo — Smart Money Concepts
# ────────────────────────────────────────────────────────────────

def _detect_swing_points(
    highs: list[Decimal], lows: list[Decimal], lookback: int = 5,
) -> tuple[list[tuple[int, Decimal]], list[tuple[int, Decimal]]]:
    """Detecta swing highs e swing lows."""
    swing_highs = []
    swing_lows = []
    for i in range(lookback, len(highs) - lookback):
        is_high = all(highs[i] >= highs[i - j] for j in range(1, lookback + 1))
        is_high = is_high and all(highs[i] >= highs[i + j] for j in range(1, min(lookback + 1, len(highs) - i)))
        if is_high:
            swing_highs.append((i, highs[i]))
        is_low = all(lows[i] <= lows[i - j] for j in range(1, lookback + 1))
        is_low = is_low and all(lows[i] <= lows[i + j] for j in range(1, min(lookback + 1, len(lows) - i)))
        if is_low:
            swing_lows.append((i, lows[i]))
    return swing_highs, swing_lows


def _detect_smc(candles: list[Candle]) -> SMCData:
    """Detecta estrutura SMC (BOS, CHoCH, FVG, Equilibrium)."""
    if len(candles) < 20:
        return SMCData()
    highs = [c.high.value for c in candles]
    lows = [c.low.value for c in candles]
    closes = [c.close.value for c in candles]
    swing_highs, swing_lows = _detect_swing_points(highs, lows, lookback=3)
    smc = SMCData()
    # Detecta BOS / CHoCH
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        last_sh = swing_highs[-1]
        prev_sh = swing_highs[-2]
        last_sl = swing_lows[-1]
        prev_sl = swing_lows[-2]
        current_close = closes[-1]
        # BOS de alta: close rompe último swing high
        if current_close > last_sh[1]:
            smc.direction = "ALTA"
            smc.bos_score = 2
            smc.last_bos_price = last_sh[1]
            smc.last_bos_type = "BOS_ALTA"
        # BOS de baixa: close rompe último swing low
        elif current_close < last_sl[1]:
            smc.direction = "BAIXA"
            smc.bos_score = -2
            smc.last_bos_price = last_sl[1]
            smc.last_bos_type = "BOS_BAIXA"
        # CHoCH: mudança de caráter
        elif last_sh[1] < prev_sh[1] and current_close > last_sh[1]:
            smc.direction = "ALTA"
            smc.bos_score = 2
            smc.last_bos_type = "CHOCH_ALTA"
            smc.last_bos_price = last_sh[1]
        elif last_sl[1] > prev_sl[1] and current_close < last_sl[1]:
            smc.direction = "BAIXA"
            smc.bos_score = -2
            smc.last_bos_type = "CHOCH_BAIXA"
            smc.last_bos_price = last_sl[1]
    # Equilibrium: preço vs meio do range
    if swing_highs and swing_lows:
        range_high = max(sh[1] for sh in swing_highs[-3:]) if swing_highs else closes[-1]
        range_low = min(sl[1] for sl in swing_lows[-3:]) if swing_lows else closes[-1]
        mid_range = (range_high + range_low) / Decimal("2")
        current = closes[-1]
        if range_high > range_low:
            position_pct = (current - range_low) / (range_high - range_low)
            if position_pct < Decimal("0.3"):
                smc.equilibrium = "DISCOUNT"
                smc.equilibrium_score = 3
            elif position_pct > Decimal("0.7"):
                smc.equilibrium = "PREMIUM"
                smc.equilibrium_score = -3
            else:
                smc.equilibrium = "NEUTRO"
                smc.equilibrium_score = 0
    # FVG (Fair Value Gap): busca gaps de liquidez
    for i in range(len(candles) - 3, max(len(candles) - 15, 0), -1):
        if i < 0:
            break
        # FVG de alta: low[i+2] > high[i]
        if lows[i + 2] > highs[i]:
            if closes[-1] > lows[i + 2]:
                smc.fvg_score = 1  # FVG de alta abaixo (suporte)
            break
        # FVG de baixa: high[i+2] < low[i]
        if highs[i + 2] < lows[i]:
            if closes[-1] < highs[i + 2]:
                smc.fvg_score = -1  # FVG de baixa acima (resistência)
            break
    return smc


def _detect_smc_for_timeframe(candles: list[Candle], tf_label: str) -> SMCTimeframeData:
    """Detecta estrutura SMC completa para um timeframe específico.

    Retorna SMCTimeframeData com:
      - Direção/bias (BOS/CHoCH)
      - Zona de compra (demand zone / OB de alta)
      - Zona de venda (supply zone / OB de baixa)
      - Swing points, FVG, equilibrium
      - Score consolidado
    """
    data = SMCTimeframeData(timeframe=tf_label)

    if len(candles) < 20:
        return data

    highs = [c.high.value for c in candles]
    lows = [c.low.value for c in candles]
    closes = [c.close.value for c in candles]
    opens = [c.open.value for c in candles]
    volumes = [c.volume for c in candles]

    swing_highs, swing_lows = _detect_swing_points(highs, lows, lookback=3)

    if not swing_highs or not swing_lows:
        return data

    # ── Swing points recentes ──
    data.last_swing_high = swing_highs[-1][1] if swing_highs else Decimal("0")
    data.last_swing_low = swing_lows[-1][1] if swing_lows else Decimal("0")

    # ── Contagem HH/HL/LH/LL ──
    recent_sh = swing_highs[-4:] if len(swing_highs) >= 4 else swing_highs
    recent_sl = swing_lows[-4:] if len(swing_lows) >= 4 else swing_lows

    data.hh_count = sum(1 for i in range(1, len(recent_sh))
                        if recent_sh[i][1] > recent_sh[i - 1][1])
    data.lh_count = sum(1 for i in range(1, len(recent_sh))
                        if recent_sh[i][1] < recent_sh[i - 1][1])
    data.hl_count = sum(1 for i in range(1, len(recent_sl))
                        if recent_sl[i][1] > recent_sl[i - 1][1])
    data.ll_count = sum(1 for i in range(1, len(recent_sl))
                        if recent_sl[i][1] < recent_sl[i - 1][1])

    # ── Bias via estrutura de mercado ──
    bullish = data.hh_count + data.hl_count
    bearish = data.lh_count + data.ll_count
    if bullish > bearish:
        data.bias = "BULLISH"
        data.score = min(bullish - bearish, 3)
    elif bearish > bullish:
        data.bias = "BEARISH"
        data.score = -min(bearish - bullish, 3)
    else:
        data.bias = "NEUTRO"
        data.score = 0

    # ── BOS / CHoCH ──
    current_close = closes[-1]
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        last_sh = swing_highs[-1]
        prev_sh = swing_highs[-2]
        last_sl = swing_lows[-1]
        prev_sl = swing_lows[-2]

        if current_close > last_sh[1]:
            data.direction = "ALTA"
            data.bos_type = "BOS_ALTA"
            data.bos_price = last_sh[1]
            data.score = min(data.score + 1, 3)
        elif current_close < last_sl[1]:
            data.direction = "BAIXA"
            data.bos_type = "BOS_BAIXA"
            data.bos_price = last_sl[1]
            data.score = max(data.score - 1, -3)
        elif last_sh[1] < prev_sh[1] and current_close > last_sh[1]:
            data.direction = "ALTA"
            data.bos_type = "CHOCH_ALTA"
            data.bos_price = last_sh[1]
            data.score = min(data.score + 1, 3)
        elif last_sl[1] > prev_sl[1] and current_close < last_sl[1]:
            data.direction = "BAIXA"
            data.bos_type = "CHOCH_BAIXA"
            data.bos_price = last_sl[1]
            data.score = max(data.score - 1, -3)

    # ── Equilibrium ──
    range_high = max(sh[1] for sh in swing_highs[-3:])
    range_low = min(sl[1] for sl in swing_lows[-3:])
    if range_high > range_low:
        position_pct = (current_close - range_low) / (range_high - range_low)
        if position_pct < Decimal("0.3"):
            data.equilibrium = "DISCOUNT"
        elif position_pct > Decimal("0.7"):
            data.equilibrium = "PREMIUM"
        else:
            data.equilibrium = "NEUTRO"

    # ── Order Blocks → Zonas de Compra / Venda ──
    avg_vol = sum(volumes[-50:]) / max(len(volumes[-50:]), 1) if len(volumes) >= 10 else 1
    scan_range = min(30, len(candles) - 2)

    # OB de alta (demand zone) → buy_zone
    for i in range(len(candles) - 2, max(len(candles) - scan_range - 2, 0), -1):
        if opens[i] > closes[i]:  # candle bearish
            rally_count = sum(
                1 for j in range(i + 1, min(i + 4, len(candles)))
                if closes[j] > closes[j - 1]
            )
            if rally_count >= 2:
                data.buy_zone = lows[i]
                break

    # OB de baixa (supply zone) → sell_zone
    for i in range(len(candles) - 2, max(len(candles) - scan_range - 2, 0), -1):
        if closes[i] > opens[i]:  # candle bullish
            drop_count = sum(
                1 for j in range(i + 1, min(i + 4, len(candles)))
                if closes[j] < closes[j - 1]
            )
            if drop_count >= 2:
                data.sell_zone = highs[i]
                break

    # ── FVG ──
    for i in range(len(candles) - 3, max(len(candles) - 20, 0), -1):
        if i < 0:
            break
        if lows[i + 2] > highs[i]:
            data.fvg_price = (lows[i + 2] + highs[i]) / Decimal("2")
            data.fvg_type = "FVG_ALTA"
            break
        if highs[i + 2] < lows[i]:
            data.fvg_price = (highs[i + 2] + lows[i]) / Decimal("2")
            data.fvg_type = "FVG_BAIXA"
            break

    return data


def _calc_smc_multi_tf(
    candles_h4: list[Candle],
    candles_m15: list[Candle],
    candles_m5: list[Candle],
) -> SMCMultiTF:
    """Calcula SMC para H4, M15 e M5 e consolida alinhamento."""
    multi = SMCMultiTF()

    multi.h4 = _detect_smc_for_timeframe(candles_h4, "H4")
    multi.m15 = _detect_smc_for_timeframe(candles_m15, "M15")
    multi.m5 = _detect_smc_for_timeframe(candles_m5, "M5")

    # ── Alinhamento multi-TF ──
    biases = [multi.h4.bias, multi.m15.bias, multi.m5.bias]
    bullish_count = sum(1 for b in biases if b == "BULLISH")
    bearish_count = sum(1 for b in biases if b == "BEARISH")

    if bullish_count >= 2:
        multi.alignment = "BULLISH"
        multi.alignment_score = bullish_count
    elif bearish_count >= 2:
        multi.alignment = "BEARISH"
        multi.alignment_score = -bearish_count
    elif bullish_count > 0 and bearish_count > 0:
        multi.alignment = "MISTO"
        multi.alignment_score = 0
    else:
        multi.alignment = "NEUTRO"
        multi.alignment_score = 0

    return multi


# ────────────────────────────────────────────────────────────────
# Funções de cálculo — Topos/Fundos com Volume (multi-TF)
# ────────────────────────────────────────────────────────────────

def _detect_swing_with_volume(
    candles: list[Candle], lookback: int = 3, tf_label: str = "M5",
) -> list[RegionOfInterest]:
    """Detecta swing highs/lows com métrica de agressão de volume.

    Cada topo/fundo é classificado por volume_strength:
      0 = sem volume relevante
      1 = volume normal (< 1.2x média)
      2 = volume acima da média (1.2x-2.0x)
      3 = explosão de volume (> 2.0x)
    """
    if len(candles) < lookback * 2 + 5:
        return []

    highs = [c.high.value for c in candles]
    lows = [c.low.value for c in candles]
    volumes = [c.volume for c in candles]

    avg_vol = sum(volumes[-50:]) / max(len(volumes[-50:]), 1) if len(volumes) >= 10 else 1

    regions: list[RegionOfInterest] = []

    for i in range(lookback, len(highs) - lookback):
        # --- Swing High ---
        is_sh = all(highs[i] >= highs[i - j] for j in range(1, lookback + 1))
        is_sh = is_sh and all(
            highs[i] >= highs[i + j] for j in range(1, min(lookback + 1, len(highs) - i))
        )
        if is_sh:
            vol_ratio = volumes[i] / avg_vol if avg_vol > 0 else 0
            vs = 0
            if vol_ratio >= 2.0:
                vs = 3
            elif vol_ratio >= 1.2:
                vs = 2
            elif vol_ratio > 0:
                vs = 1
            regions.append(RegionOfInterest(
                price=highs[i],
                label=f"Topo {tf_label}",
                tipo="RESISTENCIA",
                source_tf=tf_label,
                volume_strength=vs,
            ))

        # --- Swing Low ---
        is_sl = all(lows[i] <= lows[i - j] for j in range(1, lookback + 1))
        is_sl = is_sl and all(
            lows[i] <= lows[i + j] for j in range(1, min(lookback + 1, len(lows) - i))
        )
        if is_sl:
            vol_ratio = volumes[i] / avg_vol if avg_vol > 0 else 0
            vs = 0
            if vol_ratio >= 2.0:
                vs = 3
            elif vol_ratio >= 1.2:
                vs = 2
            elif vol_ratio > 0:
                vs = 1
            regions.append(RegionOfInterest(
                price=lows[i],
                label=f"Fundo {tf_label}",
                tipo="SUPORTE",
                source_tf=tf_label,
                volume_strength=vs,
            ))

    # Manter apenas os últimos N topos/fundos relevantes (evitar poluição)
    # Priorizar os mais recentes e com mais volume
    regions.sort(key=lambda r: (r.volume_strength, -abs(float(r.price))), reverse=True)
    return regions[:8]  # Top 8 por timeframe


def _detect_smc_regions(
    candles: list[Candle], tf_label: str = "M15",
) -> list[RegionOfInterest]:
    """Extrai regiões SMC (Order Blocks e FVGs) como RegionOfInterest.

    - Order Block: último candle antes de um BOS (corpo oposto ao movimento)
    - FVG: gap de valor justo (3 candles, gap entre c[i].high e c[i+2].low)
    """
    if len(candles) < 20:
        return []

    regions: list[RegionOfInterest] = []
    highs = [c.high.value for c in candles]
    lows = [c.low.value for c in candles]
    closes = [c.close.value for c in candles]
    opens = [c.open.value for c in candles]
    volumes = [c.volume for c in candles]
    avg_vol = sum(volumes[-50:]) / max(len(volumes[-50:]), 1) if len(volumes) >= 10 else 1

    # --- Order Blocks ---
    # Busca nos últimos 30 candles o último candle bearish antes de rally (OB de alta)
    # e último candle bullish antes de queda (OB de baixa)
    scan_range = min(30, len(candles) - 2)
    for i in range(len(candles) - 2, max(len(candles) - scan_range - 2, 0), -1):
        # OB de alta: candle bearish seguido por forte alta (3+ candles acima)
        if opens[i] > closes[i]:  # candle vermelho
            rally_count = sum(1 for j in range(i + 1, min(i + 4, len(candles))) if closes[j] > closes[j - 1])
            if rally_count >= 2:
                vol_ratio = volumes[i] / avg_vol if avg_vol > 0 else 0
                vs = 3 if vol_ratio >= 2.0 else (2 if vol_ratio >= 1.2 else 1)
                regions.append(RegionOfInterest(
                    price=lows[i],  # base do OB
                    label=f"OB Alta {tf_label}",
                    tipo="SUPORTE",
                    source_tf=tf_label,
                    volume_strength=vs,
                    confluences=2,  # OB tem confluência inerente
                ))
                break  # só o mais recente

    for i in range(len(candles) - 2, max(len(candles) - scan_range - 2, 0), -1):
        # OB de baixa: candle bullish seguido por forte queda
        if closes[i] > opens[i]:  # candle verde
            drop_count = sum(1 for j in range(i + 1, min(i + 4, len(candles))) if closes[j] < closes[j - 1])
            if drop_count >= 2:
                vol_ratio = volumes[i] / avg_vol if avg_vol > 0 else 0
                vs = 3 if vol_ratio >= 2.0 else (2 if vol_ratio >= 1.2 else 1)
                regions.append(RegionOfInterest(
                    price=highs[i],  # topo do OB
                    label=f"OB Baixa {tf_label}",
                    tipo="RESISTENCIA",
                    source_tf=tf_label,
                    volume_strength=vs,
                    confluences=2,
                ))
                break

    # --- FVGs (Fair Value Gaps) ---
    for i in range(len(candles) - 3, max(len(candles) - 20, 0), -1):
        if i < 0:
            break
        # FVG de alta: low[i+2] > high[i]
        if lows[i + 2] > highs[i]:
            mid_fvg = (lows[i + 2] + highs[i]) / Decimal("2")
            regions.append(RegionOfInterest(
                price=mid_fvg,
                label=f"FVG Alta {tf_label}",
                tipo="SUPORTE",
                source_tf=tf_label,
                volume_strength=1,
            ))
            break  # só o mais recente

    for i in range(len(candles) - 3, max(len(candles) - 20, 0), -1):
        if i < 0:
            break
        # FVG de baixa: high[i+2] < low[i]
        if highs[i + 2] < lows[i]:
            mid_fvg = (highs[i + 2] + lows[i]) / Decimal("2")
            regions.append(RegionOfInterest(
                price=mid_fvg,
                label=f"FVG Baixa {tf_label}",
                tipo="RESISTENCIA",
                source_tf=tf_label,
                volume_strength=1,
            ))
            break

    return regions


def _get_day_reference_prices(
    mt5: MT5Adapter, symbol_code: str,
) -> list[RegionOfInterest]:
    """Busca preços de referência: Ajuste, Abertura, Fechamento, Máx/Mín D0 e D-1.

    Regiões retornadas:
      - Ajuste D-1 (= Close D-1 para futuros B3)
      - Abertura D0
      - Fechamento D-1
      - Abertura D-1
      - Máxima D-1, Mínima D-1
      - Máxima D0, Mínima D0 (intraday até agora)
    """
    regions: list[RegionOfInterest] = []

    # D1 últimos 2 candles
    candles_d1 = _safe_get_candles(mt5, symbol_code, TimeFrame.D1, 2)

    if len(candles_d1) >= 2:
        prev = candles_d1[-2]
        curr = candles_d1[-1]

        # D-1
        if prev.close.value > 0:
            # Ajuste = Close D-1 no mercado futuro B3
            regions.append(RegionOfInterest(
                price=prev.close.value, label="Ajuste D-1", tipo="VWAP",
                source_tf="D1", volume_strength=0,
            ))
            regions.append(RegionOfInterest(
                price=prev.close.value, label="Fech. D-1", tipo="VWAP",
                source_tf="D1", volume_strength=0,
            ))
        if prev.open.value > 0:
            regions.append(RegionOfInterest(
                price=prev.open.value, label="Abert. D-1", tipo="VWAP",
                source_tf="D1", volume_strength=0,
            ))
        if prev.high.value > 0:
            regions.append(RegionOfInterest(
                price=prev.high.value, label="Máx D-1", tipo="RESISTENCIA",
                source_tf="D1", volume_strength=0,
            ))
        if prev.low.value > 0:
            regions.append(RegionOfInterest(
                price=prev.low.value, label="Mín D-1", tipo="SUPORTE",
                source_tf="D1", volume_strength=0,
            ))

        # D0
        if curr.open.value > 0:
            regions.append(RegionOfInterest(
                price=curr.open.value, label="Abert. D0", tipo="VWAP",
                source_tf="D1", volume_strength=0,
            ))
        if curr.high.value > 0:
            regions.append(RegionOfInterest(
                price=curr.high.value, label="Máx D0", tipo="RESISTENCIA",
                source_tf="D1", volume_strength=0,
            ))
        if curr.low.value > 0:
            regions.append(RegionOfInterest(
                price=curr.low.value, label="Mín D0", tipo="SUPORTE",
                source_tf="D1", volume_strength=0,
            ))
    elif len(candles_d1) == 1:
        curr = candles_d1[-1]
        if curr.open.value > 0:
            regions.append(RegionOfInterest(
                price=curr.open.value, label="Abert. D0", tipo="VWAP",
                source_tf="D1", volume_strength=0,
            ))

    return regions


def _map_regions_multi_tf(
    price: Decimal,
    vwap: VWAPData,
    pivots: PivotLevels,
    smc: SMCData,
    candles_m1: list[Candle],
    candles_m5: list[Candle],
    candles_m15: list[Candle],
    day_refs: list[RegionOfInterest],
) -> list[RegionOfInterest]:
    """Mapeia regiões de interesse de M1, M5, M15 com confluência dinâmica.

    Fluxo:
      1. Regiões fixas: VWAP ± σ, Pivôs, referências D1
      2. SMC regiões: Order Blocks + FVGs em M5 e M15
      3. Topos/fundos c/ volume: M1, M5, M15
      4. Deduplicação: regiões dentro de 0.10% são fundidas (somam confluência)
      5. Confluência ajustada: +1 por cada timeframe que confirma mesma zona
      6. Volume strength: herda o maior da zona combinada
    """
    tick = Decimal("5")

    def _snap(v: Decimal) -> Decimal:
        if v <= 0:
            return v
        return (v / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick

    regions: list[RegionOfInterest] = []

    # ── 1. Regiões fixas: VWAP ──
    if vwap.vwap > 0:
        regions.append(RegionOfInterest(vwap.vwap, "VWAP", "VWAP", source_tf="MULTI"))
        regions.append(RegionOfInterest(vwap.upper_1, "VWAP+1σ", "RESISTENCIA", source_tf="MULTI"))
        regions.append(RegionOfInterest(vwap.upper_2, "VWAP+2σ", "RESISTENCIA", source_tf="MULTI"))
        regions.append(RegionOfInterest(vwap.lower_1, "VWAP-1σ", "SUPORTE", source_tf="MULTI"))
        regions.append(RegionOfInterest(vwap.lower_2, "VWAP-2σ", "SUPORTE", source_tf="MULTI"))

    # ── 2. Regiões fixas: Pivôs ──
    if pivots.pp > 0:
        regions.append(RegionOfInterest(pivots.pp, "Pivô PP", "VWAP", source_tf="D1"))
        regions.append(RegionOfInterest(pivots.r1, "Pivô R1", "RESISTENCIA", source_tf="D1"))
        regions.append(RegionOfInterest(pivots.r2, "Pivô R2", "RESISTENCIA", source_tf="D1"))
        regions.append(RegionOfInterest(pivots.r3, "Pivô R3", "RESISTENCIA", source_tf="D1"))
        regions.append(RegionOfInterest(pivots.s1, "Pivô S1", "SUPORTE", source_tf="D1"))
        regions.append(RegionOfInterest(pivots.s2, "Pivô S2", "SUPORTE", source_tf="D1"))
        regions.append(RegionOfInterest(pivots.s3, "Pivô S3", "SUPORTE", source_tf="D1"))

    # ── 3. Referências D0/D-1 ──
    regions.extend(day_refs)

    # ── 4. SMC: BOS price ──
    if smc.last_bos_price > 0:
        tipo = "SUPORTE" if "ALTA" in smc.last_bos_type else "RESISTENCIA"
        regions.append(RegionOfInterest(
            smc.last_bos_price, f"SMC {smc.last_bos_type}", tipo,
            source_tf="M15", confluences=2,
        ))

    # ── 5. SMC regions (OB + FVG) em M5 e M15 ──
    if candles_m15:
        regions.extend(_detect_smc_regions(candles_m15, "M15"))
    if candles_m5:
        regions.extend(_detect_smc_regions(candles_m5, "M5"))

    # ── 6. Topos/fundos com volume — M1, M5, M15 ──
    if candles_m1:
        regions.extend(_detect_swing_with_volume(candles_m1, lookback=3, tf_label="M1"))
    if candles_m5:
        regions.extend(_detect_swing_with_volume(candles_m5, lookback=3, tf_label="M5"))
    if candles_m15:
        regions.extend(_detect_swing_with_volume(candles_m15, lookback=3, tf_label="M15"))

    # ── Arredondar ao tick ──
    for r in regions:
        if r.price > 0:
            r.price = _snap(r.price)

    # ── Deduplicação e fusão de confluências ──
    # Regiões dentro de 0.10% do mesmo preço → fundir
    merged: list[RegionOfInterest] = []
    used = [False] * len(regions)

    for i, r in enumerate(regions):
        if used[i] or r.price <= 0:
            continue
        group = [r]
        used[i] = True
        for j in range(i + 1, len(regions)):
            if used[j] or regions[j].price <= 0:
                continue
            dist = abs(regions[j].price - r.price) / r.price * 100
            if dist < Decimal("0.10"):  # ~130 pontos WIN
                group.append(regions[j])
                used[j] = True

        # Fundir grupo: manter label da região mais "forte"
        best = max(group, key=lambda x: (x.confluences, x.volume_strength))
        total_conf = sum(g.confluences for g in group)
        max_vol = max(g.volume_strength for g in group)
        # Contar timeframes distintos
        tfs = set(g.source_tf for g in group if g.source_tf)
        tf_bonus = max(0, len(tfs) - 1)  # +1 por cada TF adicional
        # Montar labels combinados se mais de 1 elemento
        if len(group) > 1:
            labels_extra = [g.label for g in group if g.label != best.label]
            combined_label = best.label
            if labels_extra:
                combined_label += " +" + "+".join(labels_extra[:2])
                if len(labels_extra) > 2:
                    combined_label += f"+{len(labels_extra) - 2}"
        else:
            combined_label = best.label

        merged.append(RegionOfInterest(
            price=best.price,
            label=combined_label[:30],  # truncar para não quebrar display
            tipo=best.tipo,
            confluences=total_conf + tf_bonus,
            source_tf=",".join(sorted(tfs)) if tfs else best.source_tf,
            volume_strength=max_vol,
        ))

    # ── Calcular distância ao preço atual ──
    for r in merged:
        if price > 0:
            r.distance_pct = ((price - r.price) / price * 100).quantize(Decimal("0.01"))

    # ── Ordenar por distância absoluta ──
    merged.sort(key=lambda r: abs(r.distance_pct))

    return merged

def _calc_momentum(candles: list[Candle]) -> MomentumData:
    """Calcula indicadores de momentum a partir de candles M5."""
    if len(candles) < 30:
        return MomentumData()
    closes = [c.close.value for c in candles]
    highs = [c.high.value for c in candles]
    lows = [c.low.value for c in candles]
    momentum = MomentumData()
    # RSI
    momentum.rsi = _calc_rsi(closes, 14)
    if momentum.rsi < Decimal("30"):
        momentum.rsi_score = 1
    elif momentum.rsi > Decimal("70"):
        momentum.rsi_score = -1
    # Stochastic
    momentum.stoch = _calc_stochastic(highs, lows, closes, 14)
    if momentum.stoch < Decimal("20"):
        momentum.stoch_score = 1
    elif momentum.stoch > Decimal("80"):
        momentum.stoch_score = -1
    # MACD
    _, _, cross = _calc_macd(closes, 12, 26, 9)
    momentum.macd_signal = cross
    if cross == "ALTA":
        momentum.macd_score = 1
    elif cross == "BAIXA":
        momentum.macd_score = -1
    # Bollinger Bands
    bb_upper, bb_mid, bb_lower = _calc_bollinger(closes, 20, 2)
    if bb_upper > 0:
        if closes[-1] > bb_upper:
            momentum.bb_position = "ACIMA"
            momentum.bb_score = -1
        elif closes[-1] < bb_lower:
            momentum.bb_position = "ABAIXO"
            momentum.bb_score = 1
    # ADX
    momentum.adx = _calc_adx(highs, lows, closes, 14)
    if momentum.adx > Decimal("25"):
        momentum.adx_score = 1  # Tendência forte
    elif momentum.adx < Decimal("15"):
        momentum.adx_score = -1  # Lateral — evitar
    # EMA9 distance
    ema9 = _calc_ema(closes, 9)
    if ema9[-1] > 0:
        dist = ((closes[-1] - ema9[-1]) / ema9[-1]) * Decimal("100")
        momentum.ema9_distance_pct = dist.quantize(Decimal("0.01"))
        if dist < Decimal("-0.30"):
            momentum.ema9_score = 1
        elif dist > Decimal("0.30"):
            momentum.ema9_score = -1
    return momentum


# ────────────────────────────────────────────────────────────────
# Funções de cálculo — Volume e Padrões
# ────────────────────────────────────────────────────────────────

def _calc_volume_score(candles: list[Candle]) -> tuple[int, int]:
    """Calcula score de volume e OBV. Retorna (vol_score, obv_score)."""
    if len(candles) < 21:
        return 0, 0
    volumes = [c.volume for c in candles]
    closes = [c.close.value for c in candles]
    # Volume vs média
    avg_vol = sum(volumes[-20:]) / 20
    current_vol = volumes[-1]
    vol_score = 0
    if avg_vol > 0 and current_vol > avg_vol * 1.5:
        if closes[-1] > closes[-2]:
            vol_score = 1
        else:
            vol_score = -1
    # OBV divergência
    obv = _calc_obv(closes, volumes)
    obv_score = 0
    if len(obv) >= 10:
        price_change = closes[-1] - closes[-10]
        obv_change = obv[-1] - obv[-10]
        if price_change < 0 and obv_change > 0:
            obv_score = 1  # Divergência de alta
        elif price_change > 0 and obv_change < 0:
            obv_score = -1  # Divergência de baixa
    return vol_score, obv_score


def _calc_aggression_score(candles: list[Candle]) -> tuple[int, Decimal]:
    """Calcula saldo de agressão do book. Retorna (score, ratio_compra).

    Analisa os últimos 10 candles M5 para estimar se o book
    está sendo agredido na compra ou na venda, usando corpo
    dos candles ponderado por volume como proxy.

    Score:
      ratio > 0.60 → +1 (agressão compradora)
      ratio < 0.40 → -1 (agressão vendedora)
      entre 0.40 e 0.60 → 0 (equilibrado)
    """
    if len(candles) < 10:
        return 0, Decimal("0.50")

    recent = candles[-10:]
    buy_pressure = Decimal("0")
    sell_pressure = Decimal("0")

    for c in recent:
        body = c.close.value - c.open.value
        vol = Decimal(str(c.volume)) if c.volume > 0 else Decimal("1")
        if body > 0:
            buy_pressure += body * vol
        elif body < 0:
            sell_pressure += abs(body) * vol

    total = buy_pressure + sell_pressure
    if total == 0:
        return 0, Decimal("0.50")

    ratio = (buy_pressure / total).quantize(Decimal("0.01"))

    if ratio > Decimal("0.60"):
        return 1, ratio
    elif ratio < Decimal("0.40"):
        return -1, ratio
    return 0, ratio


def _calc_vwap_score(price: Decimal, vwap: VWAPData) -> int:
    """Score baseado na posição do preço relativa ao VWAP."""
    if vwap.vwap == 0:
        return 0
    if price > vwap.upper_2:
        return -2
    elif price > vwap.upper_1:
        return -1
    elif price < vwap.lower_2:
        return 2
    elif price < vwap.lower_1:
        return 1
    return 0


def _detect_candle_patterns(candles: list[Candle], regions: list[RegionOfInterest]) -> int:
    """Detecta padrões de candle em regiões de interesse. Retorna score."""
    if len(candles) < 3:
        return 0
    c = candles[-1]  # Último candle
    p = candles[-2]  # Penúltimo
    current_price = c.close.value
    body = abs(c.close.value - c.open.value)
    total_range = c.high.value - c.low.value
    if total_range == 0:
        return 0
    # Verifica se está próximo a uma região de interesse
    near_support = False
    near_resistance = False
    for r in regions:
        dist_pct = abs(current_price - r.price) / current_price * 100
        if dist_pct < Decimal("0.3"):
            if r.tipo in ("SUPORTE", "VWAP"):
                near_support = True
            elif r.tipo in ("RESISTENCIA",):
                near_resistance = True
    # Engolfo de alta em suporte
    prev_body = abs(p.close.value - p.open.value)
    if near_support and c.close.value > c.open.value and p.close.value < p.open.value:
        if body > prev_body:
            return 2
    # Engolfo de baixa em resistência
    if near_resistance and c.close.value < c.open.value and p.close.value > p.open.value:
        if body > prev_body:
            return -2
    # Pin bar / rejeição
    upper_wick = c.high.value - max(c.open.value, c.close.value)
    lower_wick = min(c.open.value, c.close.value) - c.low.value
    if near_support and lower_wick > body * 2:
        return 1  # Martelo
    if near_resistance and upper_wick > body * 2:
        return -1  # Estrela cadente
    return 0


# ────────────────────────────────────────────────────────────────
# Funções de cálculo — Regiões de Interesse
# ────────────────────────────────────────────────────────────────

def _map_regions(
    price: Decimal, vwap: VWAPData, pivots: PivotLevels,
    smc: SMCData, prev_high: Decimal, prev_low: Decimal,
    open_price: Decimal,
) -> list[RegionOfInterest]:
    """Mapeia todas as regiões de interesse e calcula confluências."""
    regions: list[RegionOfInterest] = []
    # VWAP e desvios
    if vwap.vwap > 0:
        regions.append(RegionOfInterest(vwap.vwap, "VWAP", "VWAP"))
        regions.append(RegionOfInterest(vwap.upper_1, "VWAP+1σ", "RESISTENCIA"))
        regions.append(RegionOfInterest(vwap.upper_2, "VWAP+2σ", "RESISTENCIA"))
        regions.append(RegionOfInterest(vwap.lower_1, "VWAP-1σ", "SUPORTE"))
        regions.append(RegionOfInterest(vwap.lower_2, "VWAP-2σ", "SUPORTE"))
    # Pivôs
    if pivots.pp > 0:
        regions.append(RegionOfInterest(pivots.pp, "Pivô PP", "VWAP"))
        regions.append(RegionOfInterest(pivots.r1, "Pivô R1", "RESISTENCIA"))
        regions.append(RegionOfInterest(pivots.r2, "Pivô R2", "RESISTENCIA"))
        regions.append(RegionOfInterest(pivots.s1, "Pivô S1", "SUPORTE"))
        regions.append(RegionOfInterest(pivots.s2, "Pivô S2", "SUPORTE"))
    # Máx/Mín D1 anterior
    if prev_high > 0:
        regions.append(RegionOfInterest(prev_high, "Máx D-1", "RESISTENCIA"))
    if prev_low > 0:
        regions.append(RegionOfInterest(prev_low, "Mín D-1", "SUPORTE"))
    # Abertura
    if open_price > 0:
        regions.append(RegionOfInterest(open_price, "Abertura", "VWAP"))
    # SMC
    if smc.last_bos_price > 0:
        tipo = "SUPORTE" if "ALTA" in smc.last_bos_type else "RESISTENCIA"
        regions.append(RegionOfInterest(smc.last_bos_price, f"SMC {smc.last_bos_type}", tipo))
    # Arredonda todos os preços de regiões ao tick size (WIN = 5 pts)
    tick = Decimal("5")
    for region in regions:
        if region.price > 0:
            region.price = (region.price / tick).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            ) * tick
    # Calcular confluências e distância
    for region in regions:
        if price > 0:
            region.distance_pct = ((price - region.price) / price * 100).quantize(Decimal("0.01"))
        # Conta confluências (outras regiões próximas)
        for other in regions:
            if other is region:
                continue
            if other.price > 0 and region.price > 0:
                dist = abs(other.price - region.price) / region.price * 100
                if dist < Decimal("0.15"):  # ~200 pontos WIN
                    region.confluences += 1
    # Ordena por distância ao preço atual
    regions.sort(key=lambda r: abs(r.distance_pct))
    return regions


# ────────────────────────────────────────────────────────────────
# Funções de cálculo — Oportunidades
# ────────────────────────────────────────────────────────────────

def _round_tick(price: Decimal, tick: Decimal = Decimal("5")) -> Decimal:
    """Arredonda preço ao múltiplo mais próximo do tick size.

    WIN mini-índice: tick = 5 (move de 5 em 5 pontos).
    Exemplo: 186481.25 → 186480,  185884.02 → 185885
    """
    if tick <= 0:
        return price
    return (price / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick


def _generate_opportunities(
    result: CycleResult, atr: Decimal,
) -> list[Opportunity]:
    """Gera oportunidades de operação baseadas no contexto."""
    global _active_directive
    opportunities = []
    result._rejection_reasons = []  # Diagnóstico de rejeição
    if atr <= 0 or not result.regions:
        result._rejection_reasons.append("ATR=0 ou sem regiões de interesse")
        return opportunities
    price = result.price_current
    if price <= 0:
        result._rejection_reasons.append("Preço atual inválido")
        return opportunities

    # ── Diretivas do Head Financeiro ──
    hd = _active_directive
    if hd:
        # Filtro de evento macro: bloquear novas entradas se reduce_before_event
        if hd.reduce_before_event and hd.event_time:
            try:
                evt_h, evt_m = map(int, hd.event_time.split(":"))
                now = datetime.now().time()
                evt_time = dtime(evt_h, evt_m)
                # Bloquear 30 min antes do evento
                mins_before = (evt_h * 60 + evt_m) - (now.hour * 60 + now.minute)
                if 0 <= mins_before <= 30:
                    result._rejection_reasons.append(
                        f"HEAD: Exposição reduzida — evento em {mins_before}min: {hd.event_description}")
                    return opportunities
            except (ValueError, TypeError):
                pass

    # Região de suporte mais próxima
    supports = [r for r in result.regions if r.tipo == "SUPORTE" and r.distance_pct < Decimal("0")]
    resistances = [r for r in result.regions if r.tipo == "RESISTENCIA" and r.distance_pct > Decimal("0")]
    # Confiança macro em percentual (0-100)
    macro_conf_pct = result.macro_confidence * Decimal("100")
    # Tick size do WIN = 5 pts
    tick = Decimal("5")

    # ── Threshold adaptativo: em tendência forte (ADX>25), reduzir threshold ──
    adx_val = float(result.momentum.adx) if result.momentum.adx else 0
    trend_strong = adx_val > 25
    macro_directional_strong = (
        abs(result.macro_score) >= REVERSAL_BLOCK_MACRO_SCORE
        or macro_conf_pct >= Decimal("70")
    )

    # Confirmação estrutural (SMC multi-TF) para manter exposição normal
    m5_bos = (getattr(result.smc_multi_tf.m5, "bos_type", "") or "").upper()
    structure_confirmed_bull = (
        result.smc_multi_tf.alignment == "BULLISH"
        and result.smc_multi_tf.alignment_score >= 2
        and ("ALTA" in m5_bos)
    )
    structure_confirmed_bear = (
        result.smc_multi_tf.alignment == "BEARISH"
        and result.smc_multi_tf.alignment_score <= -2
        and ("BAIXA" in m5_bos)
    )
    structure_confirmed = structure_confirmed_bull or structure_confirmed_bear
    reduced_exposure_mode = macro_directional_strong and not structure_confirmed

    # Alerta de repique de distribuição (sobe contra macro de baixa forte)
    distribution_rally_alert = (
        trend_strong
        and result.macro_score <= -REVERSAL_BLOCK_MACRO_SCORE
        and result.micro_score > 0
        and result.momentum.rsi_score > 0
        and result.vwap_score >= 1
        and result.smc.equilibrium in ("PREMIUM", "NEUTRO")
    )

    if reduced_exposure_mode:
        result._rejection_reasons.append(
            "EXPOSIÇÃO REDUZIDA: aguardando confirmação estrutural SMC multi-TF"
        )
    if distribution_rally_alert:
        result._rejection_reasons.append(
            "ALERTA DISTRIBUIÇÃO: repique contra tendência de baixa forte — evitar reversão compradora"
        )

    buy_threshold = 3 if trend_strong else SCORE_COMPRA_THRESHOLD
    sell_threshold = -3 if trend_strong else SCORE_VENDA_THRESHOLD
    if reduced_exposure_mode:
        buy_threshold += 1
        sell_threshold -= 1

    def _has_min_confluence(regions_list: list[RegionOfInterest]) -> bool:
        for rg in regions_list:
            if (
                rg.confluences >= TREND_MIN_CONFLUENCE
                and abs(rg.distance_pct) <= TREND_MAX_DISTANCE_PCT
            ):
                return True
        return False

    # ── Ajustes do Diary Feedback (RL aprendizado) ──
    df = _diary_feedback
    if df and df.active:
        # O diário pode sugerir thresholds mais ou menos agressivos
        if df.threshold_sugerido_buy != 5 or df.threshold_sugerido_sell != -5:
            buy_threshold = df.threshold_sugerido_buy
            sell_threshold = df.threshold_sugerido_sell
        # Se o diário detectou que SMC está bloqueando tudo, ativa bypass
        diary_smc_bypass = df.smc_bypass_recomendado
        # Se o diário recomenda trend following
        diary_trend_follow = df.trend_following_recomendado

        # ── Regiões fortes e armadilhas (análise crítica do diário) ──
        diary_strong_prices = []
        diary_trap_prices = []
        try:
            import re
            for r in (df.regioes_fortes or []):
                m = re.search(r'@ (\d+)', r)
                if m:
                    diary_strong_prices.append(float(m.group(1)))
            for r in (df.regioes_armadilhas or []):
                m = re.search(r'@ (\d+)', r)
                if m:
                    diary_trap_prices.append(float(m.group(1)))
        except Exception:
            pass

        # ── Ajuste de confiança pelo direcional macro (análise crítica) ──
        diary_directional_penalty = Decimal("0")
        diary_directional_tag = ""
        try:
            n_vieses = len(df.direcional_vieses or [])
            n_contradicoes = len(df.direcional_contradicoes or [])
            conf_adj = float(df.confianca_direcional_ajustada or 0)

            if n_contradicoes >= 2 or n_vieses >= 2:
                # Direcional comprometido — penalizar forte
                diary_directional_penalty = Decimal("-15")
                diary_directional_tag = f" [DIR_FRACO: {n_contradicoes}contr,{n_vieses}viés]"
            elif n_contradicoes >= 1 or n_vieses >= 1:
                # Direcional questionável — penalizar moderado
                diary_directional_penalty = Decimal("-8")
                diary_directional_tag = f" [DIR_QUEST: {n_contradicoes}contr,{n_vieses}viés]"

            # FIX: Atenuar penalidade quando score macro é consistentemente alto
            # Score >+30 sustentado significa TENDÊNCIA REAL, não score inflado
            # Nesse caso, contradições menores são ruído, não sinal
            macro_abs = abs(result.macro_score) if result else 0
            if macro_abs >= 30 and diary_directional_penalty < 0:
                # Reduzir penalidade pela metade em tendência forte
                diary_directional_penalty = diary_directional_penalty / Decimal("2")
                diary_directional_tag += f" [ATN:sc{macro_abs}]"
            if macro_abs >= 45 and diary_directional_penalty < 0:
                # Score muito alto: penalidade residual mínima
                diary_directional_penalty = max(diary_directional_penalty, Decimal("-3"))
                diary_directional_tag = diary_directional_tag.replace(
                    "DIR_FRACO", "DIR_OK").replace("DIR_QUEST", "DIR_OK")

            # Se o diary ajustou a confiança para baixo e é menor que a macro_conf
            if conf_adj > 0 and conf_adj < float(macro_conf_pct):
                alt_penalty = Decimal(str(conf_adj)) - macro_conf_pct
                if alt_penalty < diary_directional_penalty:
                    diary_directional_penalty = alt_penalty
        except Exception:
            pass
    else:
        diary_smc_bypass = False
        diary_trend_follow = False
        diary_strong_prices = []
        diary_trap_prices = []
        diary_directional_penalty = Decimal("0")
        diary_directional_tag = ""

    # ── Macro Scenario Guardian — Kill Switch e Penalidades ──
    guardian_kill = False
    guardian_penalty = Decimal("0")
    guardian_tag = ""
    if df and df.active:
        # Kill switch — bloquear TODAS as operações
        if df.guardian_kill_switch:
            guardian_kill = True
            reason = (df.guardian_kill_reason or "Cenário macro adverso")[:80]
            result._rejection_reasons.append(
                f"GUARDIAN: 🚨 KILL SWITCH — {reason}")

        # Penalidade de confiança do guardian
        gp = float(df.guardian_confidence_penalty or 0)
        if gp > 0:
            guardian_penalty = Decimal(str(-gp))
            guardian_tag = f" [GUARD:-{gp:.0f}%]"

        # Exposição reduzida — threshold mais conservador
        if df.guardian_reduced_exposure and not guardian_kill:
            # Aumentar thresholds em +2 (mais exigente)
            buy_threshold = max(buy_threshold, buy_threshold + 2)
            sell_threshold = min(sell_threshold, sell_threshold - 2)
            guardian_tag += " [EXP_RED]"

        # Bias override — forçar direção
        if df.guardian_bias_override == "NEUTRO":
            # Neutralizar — exigir scores mais altos
            buy_threshold = max(buy_threshold, 8)
            sell_threshold = min(sell_threshold, -8)
            guardian_tag += " [BIAS_NEUTRO]"

    if guardian_kill:
        # Retornar sem gerar nenhuma oportunidade
        return opportunities

    # Oportunidade de COMPRA
    if result.macro_score >= buy_threshold:
        # ── Filtros do Head Financeiro para COMPRA ──
        buy_blocked_by_head = False
        if hd:
            # Filtro RSI máximo para BUY
            if hd.max_rsi_for_buy > 0 and float(result.momentum.rsi) > hd.max_rsi_for_buy:
                result._rejection_reasons.append(
                    f"HEAD: RSI {result.momentum.rsi} > máx permitido {hd.max_rsi_for_buy} para BUY")
                buy_blocked_by_head = True
            # Zona proibida para BUY
            if hd.forbidden_zone_above > 0 and float(price) > hd.forbidden_zone_above:
                result._rejection_reasons.append(
                    f"HEAD: Preço {price} acima da zona proibida {hd.forbidden_zone_above} para BUY")
                buy_blocked_by_head = True
            # Direção BEARISH do Head proíbe compras
            # FIX 12/02/2026: Respeitar guardian_bias_override="NEUTRO"
            guardian_override_active = (
                _diary_feedback and _diary_feedback.active
                and _diary_feedback.guardian_bias_override == "NEUTRO"
            )
            if hd.direction == "BEARISH" and not guardian_override_active:
                result._rejection_reasons.append(
                    f"HEAD: Direção BEARISH — BUY bloqueado por diretiva")
                buy_blocked_by_head = True
            elif hd.direction == "BEARISH" and guardian_override_active:
                result._rejection_reasons.append(
                    f"HEAD: Direção BEARISH SUSPENSA — guardian override NEUTRO ativo")

        # Micro tendência alinhada ou em desconto
        # Em convicção alta (score ≥ 8), permitir BUY mesmo em PREMIUM (tendência forte)
        high_conviction_buy = result.macro_score >= 8
        # Diary feedback pode recomendar bypass do SMC em tendência
        diary_bypass_buy = diary_smc_bypass and trend_strong
        # FIX: Em tendência forte (ADX>25 + score>5), PREMIUM não deveria bloquear BUY
        # O SMC PREMIUM é para mean-reversion; em rally, preço fica PREMIUM o dia todo
        trend_allows_premium = trend_strong and result.macro_score > 5
        if not buy_blocked_by_head and (
            result.smc.equilibrium in ("DISCOUNT", "NEUTRO")
            or result.momentum.rsi_score > 0
            or high_conviction_buy
            or diary_bypass_buy
            or trend_allows_premium
        ):
            entry = _round_tick(price, tick)
            sl = _round_tick(price - atr * Decimal("1.5"), tick)
            # SL do Head (se definido)
            if hd and hd.stop_loss_pts > 0:
                sl = _round_tick(price - Decimal(str(hd.stop_loss_pts)), tick)
            # TP: próxima resistência ou VWAP+1σ
            tp = result.vwap.upper_1 if result.vwap.upper_1 > price else price + atr * Decimal("3")
            if resistances:
                # Só usar resistência como TP se estiver ACIMA do preço (direção correta para BUY)
                valid_res = [r for r in resistances if r.price > price]
                if valid_res:
                    tp = valid_res[0].price
            tp = _round_tick(tp, tick)
            risk = entry - sl
            reward = tp - entry
            rr = (reward / risk).quantize(Decimal("0.01")) if risk > 0 else Decimal("0")
            conf = min(Decimal("95"), macro_conf_pct + Decimal(str(abs(result.micro_score) * 3)))
            # Ajuste de confiança pelo Head
            # FIX: Head como PISO de confiança (não multiplicador)
            # Se convicção do Head > sinal local, usar Head como base mínima
            if hd:
                head_conf = Decimal(str(hd.confidence_market))
                conf = max(conf, head_conf)
                # Bonus se na zona ideal de compra
                if hd.ideal_buy_zone_low > 0 and hd.ideal_buy_zone_high > 0:
                    if hd.ideal_buy_zone_low <= float(price) <= hd.ideal_buy_zone_high:
                        conf = min(Decimal("95"), conf + Decimal("10"))
            if rr >= Decimal("1.5"):
                reason_extra = ""
                if hd:
                    reason_extra = f" [HEAD: {hd.direction} conf={hd.confidence_market}%]"
                # Anotar quando o diary feedback influenciou esta decisão
                diary_extra = ""
                if diary_bypass_buy:
                    diary_extra = f" [DIARY: th={buy_threshold}, smc_bypass=SIM]"
                elif df and df.threshold_sugerido_buy != 5:
                    diary_extra = f" [DIARY: th={buy_threshold}]"

                # ── Validação de regiões do diário ──
                entry_f = float(entry)
                atr_f = float(atr) if atr > 0 else 150.0
                # Preço perto de SUPORTE forte → boost confiança
                for sp in diary_strong_prices:
                    if abs(entry_f - sp) < atr_f * 0.8:  # dentro de 0.8×ATR
                        conf = min(Decimal("95"), conf + Decimal("10"))
                        diary_extra += f" [REG_FORTE: {sp:.0f}]"
                        break
                # ── Armadilha (resistência) — zonas proporcionais ao ATR ──
                # Zona vermelha: ≤0.3×ATR da armadilha → bloqueio (ou -20% em alta convicção)
                # Zona amarela: 0.3-1.5×ATR → penalidade -15%
                trap_blocked = False
                zona_vermelha = atr_f * 0.3
                zona_amarela = atr_f * 1.5
                for tp_price in diary_trap_prices:
                    dist = tp_price - entry_f  # positivo = armadilha ACIMA
                    if dist < -zona_vermelha:
                        continue  # armadilha muito abaixo — irrelevante para BUY
                    if dist <= zona_vermelha:
                        # ZONA VERMELHA — muito perto da armadilha
                        if high_conviction_buy:
                            # Alta convicção: penalizar em vez de bloquear
                            conf = max(Decimal("20"), conf - Decimal("20"))
                            diary_extra += f" [TRAP_PERTO: {tp_price:.0f} -20%]"
                        else:
                            result._rejection_reasons.append(
                                f"DIARY: BUY bloqueado — preço {entry_f:.0f} a "
                                f"{abs(dist):.0f}pts da armadilha {tp_price:.0f} "
                                f"(zona vermelha ≤{zona_vermelha:.0f}pts)")
                            trap_blocked = True
                        break
                    elif dist <= zona_amarela:
                        # ZONA AMARELA — proximidade moderada → penalizar
                        conf = max(Decimal("20"), conf - Decimal("15"))
                        diary_extra += f" [TRAP_PROX: {tp_price:.0f} -15%]"
                        break
                if not trap_blocked:
                    # ── Ajuste direcional macro do diário ──
                    if diary_directional_penalty != 0:
                        conf = max(Decimal("20"), conf + diary_directional_penalty)
                        diary_extra += diary_directional_tag
                    # ── Penalidade do Guardian Macro ──
                    if guardian_penalty != 0:
                        conf = max(Decimal("20"), conf + guardian_penalty)
                        diary_extra += guardian_tag

                    if reduced_exposure_mode:
                        conf = max(Decimal("20"), conf - Decimal("8"))
                        diary_extra += " [EXP_REDUZIDA]"

                    opportunities.append(Opportunity(
                        direction="COMPRA",
                        entry=entry,
                        stop_loss=sl,
                        take_profit=tp,
                        risk_reward=rr,
                        confidence=conf,
                        reason=f"Macro +{result.macro_score}, {result.micro_trend}{reason_extra}{diary_extra}",
                        region=result.smc.equilibrium,
                    ))
            else:
                result._rejection_reasons.append(
                    f"COMPRA: R/R {rr} < 1.50 (TP={tp} muito próximo)")
        elif not buy_blocked_by_head:
            result._rejection_reasons.append(
                f"COMPRA: SMC={result.smc.equilibrium} + RSI={result.momentum.rsi_score} não alinhado")
    else:
        result._rejection_reasons.append(
            f"COMPRA: macro_score {result.macro_score:+d} < threshold +{buy_threshold}")
    # Oportunidade de VENDA
    if result.macro_score <= sell_threshold:
        # ── Filtros do Head Financeiro para VENDA ──
        sell_blocked_by_head = False
        if hd:
            # Filtro RSI mínimo para SELL
            if hd.min_rsi_for_sell < 100 and float(result.momentum.rsi) < hd.min_rsi_for_sell:
                result._rejection_reasons.append(
                    f"HEAD: RSI {result.momentum.rsi} < mín permitido {hd.min_rsi_for_sell} para SELL")
                sell_blocked_by_head = True
            # Zona proibida para SELL
            if hd.forbidden_zone_below > 0 and float(price) < hd.forbidden_zone_below:
                result._rejection_reasons.append(
                    f"HEAD: Preço {price} abaixo da zona proibida {hd.forbidden_zone_below} para SELL")
                sell_blocked_by_head = True
            # Direção BULLISH do Head proíbe vendas
            # FIX 12/02/2026: Respeitar guardian_bias_override="NEUTRO" que
            # suspende bloqueio direcional quando mercado diverge da diretiva
            guardian_override_active = (
                _diary_feedback and _diary_feedback.active
                and _diary_feedback.guardian_bias_override == "NEUTRO"
            )
            if hd.direction == "BULLISH" and not guardian_override_active:
                result._rejection_reasons.append(
                    f"HEAD: Direção BULLISH — SELL bloqueado por diretiva")
                sell_blocked_by_head = True
            elif hd.direction == "BULLISH" and guardian_override_active:
                result._rejection_reasons.append(
                    f"HEAD: Direção BULLISH SUSPENSA — guardian override NEUTRO ativo")

        # Em convicção alta (score ≤ -8), permitir SELL mesmo em DISCOUNT
        high_conviction_sell = result.macro_score <= -8
        # Diary feedback pode recomendar bypass do SMC em tendência
        diary_bypass_sell = diary_smc_bypass and trend_strong
        # FIX: Em tendência forte de baixa (ADX>25 + score<-5), DISCOUNT não bloqueia SELL
        trend_allows_discount = trend_strong and result.macro_score < -5
        if not sell_blocked_by_head and (
            result.smc.equilibrium in ("PREMIUM", "NEUTRO")
            or result.momentum.rsi_score < 0
            or high_conviction_sell
            or diary_bypass_sell
            or trend_allows_discount
        ):
            entry = _round_tick(price, tick)
            sl = _round_tick(price + atr * Decimal("1.5"), tick)
            # SL do Head (se definido)
            if hd and hd.stop_loss_pts > 0:
                sl = _round_tick(price + Decimal(str(hd.stop_loss_pts)), tick)
            tp = result.vwap.lower_1 if result.vwap.lower_1 < price and result.vwap.lower_1 > 0 else price - atr * Decimal("3")
            if supports:
                # Só usar suporte como TP se estiver ABAIXO do preço (direção correta para SELL)
                valid_sup = [s for s in supports if s.price < price]
                if valid_sup:
                    tp = valid_sup[0].price
            tp = _round_tick(tp, tick)
            risk = sl - entry
            reward = entry - tp
            rr = (reward / risk).quantize(Decimal("0.01")) if risk > 0 else Decimal("0")
            conf = min(Decimal("95"), macro_conf_pct + Decimal(str(abs(result.micro_score) * 3)))
            # Ajuste de confiança pelo Head
            # FIX: Head como PISO de confiança (não multiplicador)
            if hd:
                head_conf = Decimal(str(hd.confidence_market))
                conf = max(conf, head_conf)
                # Bonus se na zona ideal de venda
                if hd.ideal_sell_zone_low > 0 and hd.ideal_sell_zone_high > 0:
                    if hd.ideal_sell_zone_low <= float(price) <= hd.ideal_sell_zone_high:
                        conf = min(Decimal("95"), conf + Decimal("10"))
            if rr >= Decimal("1.5"):
                reason_extra = ""
                if hd:
                    reason_extra = f" [HEAD: {hd.direction} conf={hd.confidence_market}%]"
                # Anotar quando o diary feedback influenciou esta decisão
                diary_extra = ""
                if diary_bypass_sell:
                    diary_extra = f" [DIARY: th={sell_threshold}, smc_bypass=SIM]"
                elif df and df.threshold_sugerido_sell != -5:
                    diary_extra = f" [DIARY: th={sell_threshold}]"

                # ── Validação de regiões do diário ──
                entry_f = float(entry)
                atr_f = float(atr) if atr > 0 else 150.0
                # Preço perto de RESISTÊNCIA forte → boost confiança SELL
                for rp in diary_strong_prices:
                    if abs(entry_f - rp) < atr_f * 0.8:  # dentro de 0.8×ATR
                        conf = min(Decimal("95"), conf + Decimal("10"))
                        diary_extra += f" [REG_FORTE: {rp:.0f}]"
                        break
                # ── Armadilha (suporte) — zonas proporcionais ao ATR ──
                # Zona vermelha: ≤0.3×ATR da armadilha → bloqueio (ou -20% em alta convicção)
                # Zona amarela: 0.3-1.5×ATR → penalidade -15%
                trap_blocked = False
                zona_vermelha = atr_f * 0.3
                zona_amarela = atr_f * 1.5
                for tp_price in diary_trap_prices:
                    dist = entry_f - tp_price  # positivo = armadilha ABAIXO
                    if dist < -zona_vermelha:
                        continue  # armadilha muito acima — irrelevante para SELL
                    if dist <= zona_vermelha:
                        # ZONA VERMELHA — muito perto da armadilha
                        if high_conviction_sell:
                            # Alta convicção: penalizar em vez de bloquear
                            conf = max(Decimal("20"), conf - Decimal("20"))
                            diary_extra += f" [TRAP_PERTO: {tp_price:.0f} -20%]"
                        else:
                            result._rejection_reasons.append(
                                f"DIARY: SELL bloqueado — preço {entry_f:.0f} a "
                                f"{abs(dist):.0f}pts da armadilha {tp_price:.0f} "
                                f"(zona vermelha ≤{zona_vermelha:.0f}pts)")
                            trap_blocked = True
                        break
                    elif dist <= zona_amarela:
                        # ZONA AMARELA — proximidade moderada → penalizar
                        conf = max(Decimal("20"), conf - Decimal("15"))
                        diary_extra += f" [TRAP_PROX: {tp_price:.0f} -15%]"
                        break
                if not trap_blocked:
                    # ── Ajuste direcional macro do diário ──
                    if diary_directional_penalty != 0:
                        conf = max(Decimal("20"), conf + diary_directional_penalty)
                        diary_extra += diary_directional_tag
                    # ── Penalidade do Guardian Macro ──
                    if guardian_penalty != 0:
                        conf = max(Decimal("20"), conf + guardian_penalty)
                        diary_extra += guardian_tag

                    if reduced_exposure_mode:
                        conf = max(Decimal("20"), conf - Decimal("8"))
                        diary_extra += " [EXP_REDUZIDA]"

                    opportunities.append(Opportunity(
                        direction="VENDA",
                        entry=entry,
                        stop_loss=sl,
                        take_profit=tp,
                        risk_reward=rr,
                        confidence=conf,
                        reason=f"Macro {result.macro_score}, {result.micro_trend}{reason_extra}{diary_extra}",
                        region=result.smc.equilibrium,
                    ))
            else:
                result._rejection_reasons.append(
                    f"VENDA: R/R {rr} < 1.50 (TP={tp} muito próximo)")
        elif not sell_blocked_by_head:
            result._rejection_reasons.append(
                f"VENDA: SMC={result.smc.equilibrium} + RSI={result.momentum.rsi_score} não alinhado")
    else:
        result._rejection_reasons.append(
            f"VENDA: macro_score {result.macro_score:+d} > threshold {sell_threshold}")
    # ── Oportunidade TREND FOLLOWING — comprar pullbacks em tendência forte ──
    # Condições: ADX>25 (tendência), score>5 (direção), micro negativo (pullback)
    # Isso captura o cenário "mercado subindo, agente esperando DISCOUNT que nunca vem"
    if (trend_strong and result.macro_score >= 5 and result.micro_score < 0
            and result.smc.equilibrium == "PREMIUM"
            and not guardian_kill):
        if not _has_min_confluence(supports):
            result._rejection_reasons.append(
                "TREND_FOLLOW BUY: sem confluência mínima de suporte próximo"
            )
        else:
            # BUY pullback em tendência de alta
            # Só se o preço está num pullback (micro negativo = recuo temporário)
            buy_blocked_trend = False
            if hd:
                # FIX 12/02/2026: Respeitar guardian override no trend follow
                guardian_override_active = (
                    _diary_feedback and _diary_feedback.active
                    and _diary_feedback.guardian_bias_override == "NEUTRO"
                )
                if hd.direction == "BEARISH" and not guardian_override_active:
                    buy_blocked_trend = True
                if hd.max_rsi_for_buy > 0 and float(result.momentum.rsi) > hd.max_rsi_for_buy:
                    buy_blocked_trend = True

            if not buy_blocked_trend:
                entry = _round_tick(price, tick)
                # SL mais apertado em trend following: 1.2×ATR (pullback curto)
                sl = _round_tick(price - atr * Decimal("1.2"), tick)
                if hd and hd.stop_loss_pts > 0:
                    sl = _round_tick(price - Decimal(str(hd.stop_loss_pts)), tick)
                # TP: VWAP upper 1σ ou ATR×2.5 (tendência continua)
                tp = result.vwap.upper_1 if result.vwap.upper_1 > price else price + atr * Decimal("2.5")
                if resistances:
                    valid_res = [r for r in resistances if r.price > price]
                    if valid_res:
                        tp = valid_res[0].price
                tp = _round_tick(tp, tick)
                risk = entry - sl
                reward = tp - entry
                rr = (reward / risk).quantize(Decimal("0.01")) if risk > 0 else Decimal("0")

                if rr >= Decimal("1.2"):  # R/R mais flexível em trend following
                    # FIX 12/02/2026: Confiança proporcional com fórmula corrigida
                    # Anterior: score + ADX/2 → score 7 + ADX 30/2 = 22% (inviável)
                    # Nova: base 40 + score×2 + min(ADX/3, 15) → 7: 40+14+10 = 64%
                    tf_conf = min(
                        Decimal("85"),
                        Decimal("40") + Decimal(str(result.macro_score)) * Decimal("2")
                        + min(Decimal(str(adx_val)) / Decimal("3"), Decimal("15")),
                    )
                    tf_conf = max(Decimal("40"), tf_conf)
                    # Penalidades do guardian e direcional aplicam
                    if diary_directional_penalty != 0:
                        tf_conf = max(Decimal("25"), tf_conf + diary_directional_penalty)
                    if guardian_penalty != 0:
                        tf_conf = max(Decimal("25"), tf_conf + guardian_penalty)
                    if reduced_exposure_mode:
                        tf_conf = max(Decimal("30"), tf_conf - Decimal("6"))
                    tf_extra = f" [TREND_FOLLOW: ADX={adx_val:.0f}]"
                    if hd:
                        tf_extra += f" [HEAD: {hd.direction} conf={hd.confidence_market}%]"
                    if reduced_exposure_mode:
                        tf_extra += " [EXP_REDUZIDA]"

                    opportunities.append(Opportunity(
                        direction="COMPRA",
                        entry=entry,
                        stop_loss=sl,
                        take_profit=tp,
                        risk_reward=rr,
                        confidence=tf_conf,
                        reason=f"Trend pullback: Macro +{result.macro_score}, ADX={adx_val:.0f}, "
                               f"micro={result.micro_score:+d}{tf_extra}",
                        region="TREND_FOLLOW",
                    ))

    if (trend_strong and result.macro_score <= -5 and result.micro_score > 0
            and result.smc.equilibrium == "DISCOUNT"
            and not guardian_kill):
        if not _has_min_confluence(resistances):
            result._rejection_reasons.append(
                "TREND_FOLLOW SELL: sem confluência mínima de resistência próxima"
            )
        else:
            # SELL pullback em tendência de baixa
            sell_blocked_trend = False
            if hd:
                # FIX 12/02/2026: Respeitar guardian override no trend follow
                guardian_override_active = (
                    _diary_feedback and _diary_feedback.active
                    and _diary_feedback.guardian_bias_override == "NEUTRO"
                )
                if hd.direction == "BULLISH" and not guardian_override_active:
                    sell_blocked_trend = True
                if hd.min_rsi_for_sell < 100 and float(result.momentum.rsi) < hd.min_rsi_for_sell:
                    sell_blocked_trend = True

            if not sell_blocked_trend:
                entry = _round_tick(price, tick)
                sl = _round_tick(price + atr * Decimal("1.2"), tick)
                if hd and hd.stop_loss_pts > 0:
                    sl = _round_tick(price + Decimal(str(hd.stop_loss_pts)), tick)
                tp = result.vwap.lower_1 if result.vwap.lower_1 < price and result.vwap.lower_1 > 0 else price - atr * Decimal("2.5")
                if supports:
                    valid_sup = [s for s in supports if s.price < price]
                    if valid_sup:
                        tp = valid_sup[0].price
                tp = _round_tick(tp, tick)
                risk = sl - entry
                reward = entry - tp
                rr = (reward / risk).quantize(Decimal("0.01")) if risk > 0 else Decimal("0")

                if rr >= Decimal("1.2"):
                    # FIX 12/02/2026: Confiança corrigida para SELL trend following
                    tf_conf = min(
                        Decimal("85"),
                        Decimal("40") + Decimal(str(abs(result.macro_score))) * Decimal("2")
                        + min(Decimal(str(adx_val)) / Decimal("3"), Decimal("15")),
                    )
                    tf_conf = max(Decimal("40"), tf_conf)
                    if diary_directional_penalty != 0:
                        tf_conf = max(Decimal("25"), tf_conf + diary_directional_penalty)
                    if guardian_penalty != 0:
                        tf_conf = max(Decimal("25"), tf_conf + guardian_penalty)
                    if reduced_exposure_mode:
                        tf_conf = max(Decimal("30"), tf_conf - Decimal("6"))
                    tf_extra = f" [TREND_FOLLOW: ADX={adx_val:.0f}]"
                    if hd:
                        tf_extra += f" [HEAD: {hd.direction} conf={hd.confidence_market}%]"
                    if reduced_exposure_mode:
                        tf_extra += " [EXP_REDUZIDA]"

                    opportunities.append(Opportunity(
                        direction="VENDA",
                        entry=entry,
                        stop_loss=sl,
                        take_profit=tp,
                        risk_reward=rr,
                        confidence=tf_conf,
                        reason=f"Trend pullback: Macro {result.macro_score}, ADX={adx_val:.0f}, "
                               f"micro={result.micro_score:+d}{tf_extra}",
                        region="TREND_FOLLOW",
                    ))

    # Oportunidade de REVERSÃO (score neutro mas indicadores esticados)
    reversal_blocked = (
        adx_val >= float(REVERSAL_BLOCK_ADX)
        and macro_directional_strong
    )
    if reversal_blocked:
        result._rejection_reasons.append(
            f"REVERSÃO BLOQUEADA: ADX={adx_val:.0f} e macro direcional forte ({result.macro_score:+d})"
        )
    if abs(result.macro_score) < buy_threshold and not reversal_blocked:
        # Reversão de alta em sobrevenda
        if (
            result.vwap_score >= 2
            and result.momentum.rsi_score > 0
            and not distribution_rally_alert
        ):
            entry = _round_tick(price, tick)
            sl = _round_tick(price - atr * Decimal("2"), tick)
            tp = result.vwap.vwap if result.vwap.vwap > price else price + atr * Decimal("2")
            tp = _round_tick(tp, tick)
            risk = entry - sl
            reward = tp - entry
            rr = (reward / risk).quantize(Decimal("0.01")) if risk > 0 else Decimal("0")
            if rr >= Decimal("2"):
                rev_conf = Decimal("50")
                if reduced_exposure_mode:
                    rev_conf = Decimal("42")
                opportunities.append(Opportunity(
                    direction="COMPRA",
                    entry=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    risk_reward=rr,
                    confidence=rev_conf,
                    reason=(
                        "Reversão alta: VWAP-2σ + RSI sobrevenda"
                        + (" [EXP_REDUZIDA]" if reduced_exposure_mode else "")
                    ),
                    region="REVERSÃO",
                ))
        # Reversão de baixa em sobrecompra
        if result.vwap_score <= -2 and result.momentum.rsi_score < 0:
            entry = _round_tick(price, tick)
            sl = _round_tick(price + atr * Decimal("2"), tick)
            tp = result.vwap.vwap if result.vwap.vwap < price and result.vwap.vwap > 0 else price - atr * Decimal("2")
            tp = _round_tick(tp, tick)
            risk = sl - entry
            reward = entry - tp
            rr = (reward / risk).quantize(Decimal("0.01")) if risk > 0 else Decimal("0")
            if rr >= Decimal("2"):
                rev_conf = Decimal("50")
                if reduced_exposure_mode:
                    rev_conf = Decimal("42")
                opportunities.append(Opportunity(
                    direction="VENDA",
                    entry=entry,
                    stop_loss=sl,
                    take_profit=tp,
                    risk_reward=rr,
                    confidence=rev_conf,
                    reason=(
                        "Reversão baixa: VWAP+2σ + RSI sobrecompra"
                        + (" [EXP_REDUZIDA]" if reduced_exposure_mode else "")
                    ),
                    region="REVERSÃO",
                ))
    return opportunities


# ────────────────────────────────────────────────────────────────
# Trading Automático — Gestão de Ordens
# ────────────────────────────────────────────────────────────────

@dataclass
class OpenTrade:
    """Posição aberta pelo agente."""
    ticket: str
    position_ticket: Optional[int]
    direction: str  # COMPRA ou VENDA
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    quantity: int
    opened_at: datetime
    trailing_stop: Decimal = Decimal("0")
    unrealized_pnl: Decimal = Decimal("0")
    reason: str = ""


class MicroTradingManager:
    """Gerenciador de execução de ordens para o agente micro tendência.

    ⚠️ AVISO: Executa ordens REAIS no MetaTrader 5.
    Sempre teste em conta DEMO primeiro!
    """

    def __init__(self, mt5: MT5Adapter, symbol_code: str = "WIN$N"):
        self.mt5 = mt5
        self.symbol = Symbol(symbol_code)
        self.open_trades: list[OpenTrade] = []
        self.closed_trades: list[dict] = []
        self.daily_pnl = Decimal("0")
        self.daily_trade_count = 0
        self._last_trade_date: Optional[str] = None
        # FIX 12/02/2026: Cooling-off anti-TILT após stop loss
        self._last_stop_loss_time: Optional[datetime] = None
        self._last_stop_loss_direction: Optional[str] = None
        self._watchdog_seen_tickets: set[int] = set()
        self._hydrate_today_summary_from_db()

    def _hydrate_today_summary_from_db(self) -> None:
        """Reidrata resumo do dia a partir da tabela trades após reinício.

        Motivo: o painel em tempo real usa estado em memória (closed_trades/daily_pnl),
        que é perdido ao reiniciar o processo.
        """
        global DB_PATH
        if not DB_PATH:
            return

        import sqlite3

        today = datetime.now().strftime("%Y-%m-%d")
        symbol_prefix = str(self.symbol).replace("$N", "")

        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()

            cur.execute(
                """
                SELECT COUNT(*)
                FROM trades
                WHERE substr(entry_time, 1, 10) = ?
                  AND symbol LIKE ?
                """,
                (today, f"{symbol_prefix}%"),
            )
            total_trades_today = int(cur.fetchone()[0] or 0)

            cur.execute(
                """
                SELECT COALESCE(profit_loss, 0)
                FROM trades
                WHERE substr(entry_time, 1, 10) = ?
                  AND symbol LIKE ?
                  AND status = 'CLOSED'
                ORDER BY exit_time ASC
                """,
                (today, f"{symbol_prefix}%"),
            )
            closed_rows = cur.fetchall()

            conn.close()

            self._last_trade_date = today
            self.daily_trade_count = total_trades_today
            self.closed_trades = [{"pnl": Decimal(str(float(r[0] or 0.0)))} for r in closed_rows]
            self.daily_pnl = sum((t["pnl"] for t in self.closed_trades), Decimal("0"))

            if total_trades_today > 0:
                print(
                    f"  ℹ Reidratação: trades_dia={total_trades_today} | "
                    f"fechados={len(self.closed_trades)} | pnl={self.daily_pnl:+.0f} pts"
                )
        except Exception as e:
            print(f"  [AVISO] Falha ao reidratar resumo diário do banco: {e}")

    def _reset_daily_if_needed(self) -> None:
        """Reseta contadores diários na virada do dia."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._last_trade_date != today:
            self._last_trade_date = today
            self.daily_pnl = Decimal("0")
            self.daily_trade_count = 0
            self.closed_trades.clear()

    def can_trade(self) -> tuple[bool, str]:
        """Verifica se pode abrir nova operação. Retorna (pode, motivo)."""
        self._reset_daily_if_needed()

        if len(self.open_trades) >= MAX_POSITIONS:
            return False, f"Já tem {len(self.open_trades)} posição(ões) aberta(s)"

        if self.daily_trade_count >= MAX_DAILY_TRADES:
            return False, f"Limite diário de {MAX_DAILY_TRADES} trades atingido"

        if self.daily_pnl <= -MAX_DAILY_LOSS:
            return False, f"Loss diário máximo atingido ({self.daily_pnl:+.0f} pts)"

        # Não operar nos últimos 30 min do pregão
        now = datetime.now().time()
        if now >= dtime(17, 25):
            return False, "Últimos 30 min do pregão — sem novas entradas"

        return True, "OK"

    def evaluate_opportunity(self, opp: Opportunity) -> tuple[bool, str]:
        """Avalia se uma oportunidade deve ser executada."""
        global _active_directive

        if opp.confidence < MIN_CONFIDENCE_TRADE:
            return False, f"Confiança {opp.confidence:.0f}% < mínimo {MIN_CONFIDENCE_TRADE}%"

        if opp.risk_reward < MIN_RR_TRADE:
            return False, f"R/R {opp.risk_reward} < mínimo {MIN_RR_TRADE}"

        # FIX 12/02/2026: Cooling-off anti-TILT — bloqueia reentrada na mesma
        # direção por COOLING_OFF_MINUTES minutos após stop loss.
        # Evita o padrão destrutivo de "vingança" contra o mercado.
        if (self._last_stop_loss_time is not None
                and self._last_stop_loss_direction == opp.direction):
            elapsed = (datetime.now() - self._last_stop_loss_time).total_seconds() / 60
            if elapsed < COOLING_OFF_MINUTES:
                remaining = int(COOLING_OFF_MINUTES - elapsed)
                return False, (
                    f"⏳ COOLING-OFF: Stop loss {self._last_stop_loss_direction} "
                    f"há {elapsed:.0f}min — aguardar mais {remaining}min"
                )

        # ── Filtros do Head Financeiro ──
        hd = _active_directive
        if hd:
            # Limite de trades diários do Head
            if hd.max_daily_trades > 0 and self.daily_trade_count >= hd.max_daily_trades:
                return False, f"HEAD: Limite de {hd.max_daily_trades} trades/dia atingido"
            # Agressividade LOW = confiança mínima mais alta
            if hd.aggressiveness == "LOW" and opp.confidence < 70:
                return False, f"HEAD: Agressividade LOW — confiança {opp.confidence:.0f}% < 70% requerido"

        # Plano de lições: exposição reduzida exige critério extra
        if "[EXP_REDUZIDA]" in (opp.reason or ""):
            if opp.confidence < Decimal("55"):
                return False, "EXPOSIÇÃO REDUZIDA: confiança < 55%"
            if opp.risk_reward < Decimal("1.8"):
                return False, "EXPOSIÇÃO REDUZIDA: R/R < 1.8"

        # Verifica se não está entrando contra posição existente
        for trade in self.open_trades:
            if trade.direction != opp.direction:
                return False, f"Já tem posição {trade.direction} aberta — conflito"

        return True, "Oportunidade aprovada"

    def execute_entry(self, opp: Opportunity) -> Optional[str]:
        """Executa entrada no MT5. Retorna ticket ou None."""
        side = OrderSide.BUY if opp.direction == "COMPRA" else OrderSide.SELL
        entry_price = Price(opp.entry)

        order = Order(
            symbol=self.symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=Quantity(MAX_CONTRACTS),
            price=entry_price,
            stop_loss=Price(opp.stop_loss),
            take_profit=Price(opp.take_profit),
        )

        try:
            ticket = self.mt5.send_order(order)
            if ticket:
                position_ticket = self.mt5.resolve_open_position_ticket(self.symbol, side)
                trade = OpenTrade(
                    ticket=ticket,
                    position_ticket=position_ticket,
                    direction=opp.direction,
                    entry_price=opp.entry,
                    stop_loss=opp.stop_loss,
                    take_profit=opp.take_profit,
                    quantity=MAX_CONTRACTS,
                    opened_at=datetime.now(),
                    trailing_stop=opp.stop_loss,
                    reason=opp.reason,
                )
                self.open_trades.append(trade)
                self.daily_trade_count += 1
                return ticket
        except Exception as e:
            print(f"  ✗ ERRO ao executar ordem: {e}")
        return None

    def manage_positions(self, current_price: Decimal) -> None:
        """Gerencia posições abertas: PnL, trailing stop, exits."""
        trades_to_close: list[tuple[OpenTrade, str]] = []

        for trade in self.open_trades:
            # Atualiza PnL não realizado
            if trade.direction == "COMPRA":
                trade.unrealized_pnl = (current_price - trade.entry_price) * trade.quantity
            else:
                trade.unrealized_pnl = (trade.entry_price - current_price) * trade.quantity

            # Verifica stop loss
            if trade.direction == "COMPRA" and current_price <= trade.stop_loss:
                trades_to_close.append((trade, "STOP_LOSS"))
                continue
            elif trade.direction == "VENDA" and current_price >= trade.stop_loss:
                trades_to_close.append((trade, "STOP_LOSS"))
                continue

            # Verifica take profit
            if trade.direction == "COMPRA" and current_price >= trade.take_profit:
                trades_to_close.append((trade, "TAKE_PROFIT"))
                continue
            elif trade.direction == "VENDA" and current_price <= trade.take_profit:
                trades_to_close.append((trade, "TAKE_PROFIT"))
                continue

            # Trailing stop
            if TRAILING_STOP_ENABLED:
                self._update_trailing(trade, current_price)

        # Executa fechamentos
        for trade, reason in trades_to_close:
            self._close_position(trade, current_price, reason)

    def monitor_hedge_orphans(self) -> None:
        """Detecta posição órfã em conta hedge e opcionalmente fecha.

        Cenário visado: posição contrária sem TP (ou sem SL) criada indevidamente.
        """
        if not WATCHDOG_HEDGE_ENABLED:
            return

        try:
            broker_positions = self.mt5.get_positions(self.symbol)
        except Exception as e:
            print(f"  [AVISO] Watchdog hedge: falha ao consultar posições: {e}")
            if DB_PATH:
                try:
                    _persist_hedge_watchdog_event(
                        db_path=DB_PATH,
                        event_type="QUERY_ERROR",
                        action_taken="NO_ACTION",
                        status="ERROR",
                        message="Falha ao consultar posições no watchdog hedge",
                        error_message=str(e),
                    )
                except Exception:
                    pass
            return

        local_tickets = {
            int(t.position_ticket)
            for t in self.open_trades
            if t.position_ticket is not None
        }

        for pos in broker_positions:
            ticket = int(getattr(pos, "ticket", 0) or 0)
            if ticket <= 0:
                continue
            if ticket in local_tickets:
                continue

            sl = float(getattr(pos, "sl", 0.0) or 0.0)
            tp = float(getattr(pos, "tp", 0.0) or 0.0)
            volume = float(getattr(pos, "volume", 0.0) or 0.0)

            suspicious = (tp <= 0.0 or sl <= 0.0) and volume > 0.0
            if not suspicious:
                continue

            if ticket not in self._watchdog_seen_tickets:
                print(
                    f"  ⚠ WATCHDOG HEDGE: posição órfã detectada | "
                    f"ticket={ticket} | symbol={getattr(pos, 'symbol', '?')} | "
                    f"vol={volume} | sl={sl} | tp={tp}"
                )
                if DB_PATH:
                    try:
                        _persist_hedge_watchdog_event(
                            db_path=DB_PATH,
                            event_type="ORPHAN_DETECTED",
                            action_taken="ALERT",
                            position_ticket=ticket,
                            symbol=str(getattr(pos, "symbol", "")),
                            volume=volume,
                            sl=sl,
                            tp=tp,
                            status="WARNING",
                            message="Posição órfã detectada (sem proteção completa)",
                        )
                    except Exception:
                        pass
                self._watchdog_seen_tickets.add(ticket)

            if WATCHDOG_AUTO_CLOSE_HEDGE_ORPHAN:
                try:
                    closed = self.mt5.close_position_by_ticket(ticket)
                    if closed:
                        print(f"  🛡 WATCHDOG HEDGE: posição órfã fechada (ticket={ticket})")
                        if DB_PATH:
                            try:
                                _persist_hedge_watchdog_event(
                                    db_path=DB_PATH,
                                    event_type="ORPHAN_CLOSED",
                                    action_taken="AUTO_CLOSE",
                                    position_ticket=ticket,
                                    symbol=str(getattr(pos, "symbol", "")),
                                    volume=volume,
                                    sl=sl,
                                    tp=tp,
                                    status="SUCCESS",
                                    message="Posição órfã fechada automaticamente pelo watchdog",
                                )
                            except Exception:
                                pass
                except Exception as e:
                    print(f"  [AVISO] Watchdog hedge: erro ao fechar posição {ticket}: {e}")
                    if DB_PATH:
                        try:
                            _persist_hedge_watchdog_event(
                                db_path=DB_PATH,
                                event_type="ORPHAN_CLOSE_ERROR",
                                action_taken="AUTO_CLOSE",
                                position_ticket=ticket,
                                symbol=str(getattr(pos, "symbol", "")),
                                volume=volume,
                                sl=sl,
                                tp=tp,
                                status="ERROR",
                                message="Erro ao fechar posição órfã automaticamente",
                                error_message=str(e),
                            )
                        except Exception:
                            pass

    def _update_trailing(self, trade: OpenTrade, current_price: Decimal) -> None:
        """Atualiza trailing stop."""
        if trade.direction == "COMPRA":
            new_stop = current_price - TRAILING_DISTANCE_PTS
            if new_stop > trade.trailing_stop and new_stop > trade.entry_price:
                trade.trailing_stop = new_stop
                trade.stop_loss = new_stop
        else:
            new_stop = current_price + TRAILING_DISTANCE_PTS
            if new_stop < trade.trailing_stop and new_stop < trade.entry_price:
                trade.trailing_stop = new_stop
                trade.stop_loss = new_stop

    def _close_position(self, trade: OpenTrade, exit_price: Decimal, reason: str) -> bool:
        """Fecha posição no MT5."""
        close_side = OrderSide.SELL if trade.direction == "COMPRA" else OrderSide.BUY
        open_side = OrderSide.BUY if trade.direction == "COMPRA" else OrderSide.SELL

        # Em conta hedge, fechar por `position` evita abrir posição contrária acidental.
        close_position_ticket = trade.position_ticket
        if close_position_ticket is None:
            try:
                close_position_ticket = self.mt5.resolve_open_position_ticket(self.symbol, open_side)
            except Exception:
                close_position_ticket = None

        order = Order(
            symbol=self.symbol,
            side=close_side,
            order_type=OrderType.MARKET,
            quantity=Quantity(trade.quantity),
            price=Price(exit_price),
            close_position_ticket=close_position_ticket,
        )

        try:
            ticket = self.mt5.send_order(order)
            if ticket:
                # Calcula PnL
                if trade.direction == "COMPRA":
                    pnl = (exit_price - trade.entry_price) * trade.quantity
                else:
                    pnl = (trade.entry_price - exit_price) * trade.quantity

                self.daily_pnl += pnl
                duration = int((datetime.now() - trade.opened_at).total_seconds())

                self.closed_trades.append({
                    "ticket": trade.ticket,
                    "direction": trade.direction,
                    "entry": trade.entry_price,
                    "exit": exit_price,
                    "pnl": pnl,
                    "reason": reason,
                    "duration_s": duration,
                })

                self.open_trades.remove(trade)

                # FIX 12/02/2026: Registra stop loss para cooling-off anti-TILT
                if reason == "STOP_LOSS":
                    self._last_stop_loss_time = datetime.now()
                    self._last_stop_loss_direction = trade.direction

                print(f"  {'✓' if pnl >= 0 else '✗'} Trade fechado: {reason} │ "
                      f"PnL: {pnl:+.0f} pts │ Duração: {duration}s")
                return True
        except Exception as e:
            print(f"  ✗ ERRO ao fechar posição: {e}")
        return False

    def close_all(self, current_price: Decimal, reason: str = "FIM_PREGAO") -> None:
        """Fecha todas as posições abertas."""
        for trade in self.open_trades[:]:
            self._close_position(trade, current_price, reason)

    def get_summary(self) -> dict:
        """Resumo do dia."""
        wins = sum(1 for t in self.closed_trades if t["pnl"] > 0)
        losses = sum(1 for t in self.closed_trades if t["pnl"] <= 0)
        return {
            "trades": len(self.closed_trades),
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / len(self.closed_trades) * 100) if self.closed_trades else 0,
            "daily_pnl": self.daily_pnl,
            "open_positions": len(self.open_trades),
        }


# ────────────────────────────────────────────────────────────────
# MT5 — Conexão e coleta de dados
# ────────────────────────────────────────────────────────────────

def _connect_mt5(config) -> MT5Adapter:
    """Conecta ao MetaTrader 5."""
    mt5 = MT5Adapter(
        login=config.mt5_login,
        password=config.mt5_password,
        server=config.mt5_server,
    )
    if not mt5.connect():
        raise RuntimeError("Falha ao conectar no MT5. Verifique .env e terminal MT5.")
    return mt5


def _safe_get_tick(mt5: MT5Adapter, symbol_code: str) -> Optional[TickData]:
    """Busca tick de forma segura, retornando None em caso de erro."""
    try:
        return mt5.get_current_tick(Symbol(symbol_code))
    except Exception:
        return None


def _safe_get_candles(
    mt5: MT5Adapter, symbol_code: str, timeframe: TimeFrame, count: int = 100,
) -> list[Candle]:
    """Busca candles de forma segura."""
    try:
        return mt5.get_candles(Symbol(symbol_code), timeframe, count)
    except Exception:
        return []


def _get_daily_open(mt5: MT5Adapter, symbol_code: str) -> Decimal:
    """Retorna o preço de abertura do dia (D1)."""
    candles = _safe_get_candles(mt5, symbol_code, TimeFrame.D1, 1)
    if candles:
        return candles[-1].open.value
    return Decimal("0")


def _get_prev_day_hlc(mt5: MT5Adapter, symbol_code: str) -> tuple[Decimal, Decimal, Decimal]:
    """Retorna High, Low, Close do dia anterior."""
    candles = _safe_get_candles(mt5, symbol_code, TimeFrame.D1, 2)
    if len(candles) >= 2:
        prev = candles[-2]
        return prev.high.value, prev.low.value, prev.close.value
    return Decimal("0"), Decimal("0"), Decimal("0")


# ────────────────────────────────────────────────────────────────
# Score Macro — Cálculo do direcional do dia (via MacroScoreEngine)
# ────────────────────────────────────────────────────────────────

def _calc_macro_score(mt5: MT5Adapter) -> tuple[list[MacroItem], int, str, Decimal]:
    """Calcula score macro para direcional do dia usando MacroScoreEngine.

    Delega toda a lógica (104 itens, futuros, forex API, indicadores técnicos,
    spread de curva, fluxo) ao MacroScoreEngine e converte o resultado para
    o formato compatível com CycleResult/display/persistência.
    """
    global _macro_engine

    # Inicializa engine se necessário (reconexão MT5 em novo ciclo)
    if _macro_engine is None or _macro_engine._mt5 is not mt5:
        _macro_engine = MacroScoreEngine(mt5_adapter=mt5)

    # Executa análise completa (104 itens)
    engine_result: MacroScoreResult = _macro_engine.analyze()

    # Converte ItemScoreResult → MacroItem para compatibilidade
    items: list[MacroItem] = []
    for isr in engine_result.items:
        correlation_str = isr.correlation.value if hasattr(isr.correlation, 'value') else str(isr.correlation)
        category_str = isr.category.value if hasattr(isr.category, 'value') else str(isr.category)
        mi = MacroItem(
            number=isr.item_number,
            symbol=isr.resolved_symbol or isr.symbol,
            name=isr.name,
            category=category_str,
            correlation=correlation_str,
            score=isr.final_score,
            price_current=isr.current_price or Decimal("0"),
            price_open=isr.opening_price or Decimal("0"),
            available=isr.available,
            reason=isr.detail,
        )
        items.append(mi)

    # Score final como int (truncado) para compatibilidade com CycleResult
    total_score = int(engine_result.score_final)

    # Sinal vem do engine
    signal = engine_result.signal.value  # "COMPRA", "VENDA", "NEUTRO"

    # Confiança vem do engine
    confidence = engine_result.confidence

    return items, total_score, signal, confidence


# ────────────────────────────────────────────────────────────────
# Classificação de Micro Tendência
# ────────────────────────────────────────────────────────────────

def _classify_micro_trend(macro_score: int, micro_score: int, adx: Decimal) -> str:
    """Classifica a micro tendência atual."""
    if adx < Decimal("15"):
        return "CONSOLIDAÇÃO"
    # Macro e micro alinhados
    if (macro_score >= SCORE_COMPRA_THRESHOLD and micro_score > 0) or \
       (macro_score <= SCORE_VENDA_THRESHOLD and micro_score < 0):
        return "CONTINUAÇÃO"
    # Macro e micro divergem
    if (macro_score >= SCORE_COMPRA_THRESHOLD and micro_score < 0) or \
       (macro_score <= SCORE_VENDA_THRESHOLD and micro_score > 0):
        return "REVERSÃO"
    return "CONSOLIDAÇÃO"


# ────────────────────────────────────────────────────────────────
# Guardian Inline — Auto-suspensão de diretiva divergente
# ────────────────────────────────────────────────────────────────

def _check_directive_divergence(result: CycleResult) -> None:
    """Verifica se o score macro diverge da diretiva do Head.

    Se a divergência se sustenta por DIRECTIVE_DIVERGE_CYCLES ciclos
    consecutivos, suspende o bloqueio direcional da diretiva emitindo
    guardian_bias_override='NEUTRO' no diary_feedback.

    FIX 12/02/2026: Resolve cenário onde diretiva BULLISH bloqueia
    VENDA enquanto mercado caiu 1.240 pts (score -8 vs diretiva BULLISH).
    """
    global _directive_diverge_counter, _diary_feedback, _active_directive

    hd = _active_directive
    if not hd:
        _directive_diverge_counter = 0
        return

    # Determinar se há divergência: diretiva diz uma coisa, score diz outra
    diverging = False
    if hd.direction == "BULLISH" and result.macro_score <= -DIRECTIVE_DIVERGE_THRESHOLD:
        diverging = True
    elif hd.direction == "BEARISH" and result.macro_score >= DIRECTIVE_DIVERGE_THRESHOLD:
        diverging = True

    if diverging:
        _directive_diverge_counter += 1
        if _directive_diverge_counter >= DIRECTIVE_DIVERGE_CYCLES:
            # Suspender bloqueio direcional via diary_feedback
            if _diary_feedback is None:
                from src.application.services.diary_feedback import DiaryFeedback
                _diary_feedback = DiaryFeedback()
                _diary_feedback.active = True
            _diary_feedback.guardian_bias_override = "NEUTRO"
            _diary_feedback.guardian_alertas.append(
                f"AUTO-SUSPENSÃO: Diretiva {hd.direction} suspensa — "
                f"score {result.macro_score:+d} divergiu por {_directive_diverge_counter} ciclos"
            )
            print(f"  ⚠️  GUARDIAN: Diretiva {hd.direction} SUSPENSA — "
                  f"score {result.macro_score:+d} diverge por {_directive_diverge_counter} ciclos")
    else:
        _directive_diverge_counter = 0


# ────────────────────────────────────────────────────────────────
# Execução de um ciclo completo
# ────────────────────────────────────────────────────────────────

def _run_cycle(mt5: MT5Adapter) -> CycleResult:
    """Executa um ciclo completo de análise."""
    global _prev_macro_score, _prev_macro_date
    global _directive_diverge_counter

    result = CycleResult(timestamp=datetime.now())
    # 1) Score Macro (direcional do dia)
    items, raw_macro_score, macro_signal, macro_conf = _calc_macro_score(mt5)

    # ── Dampening: EMA do score para evitar whipsaw ──
    today_str = result.timestamp.strftime("%Y-%m-%d")
    if _prev_macro_date != today_str:
        # Novo pregão: resetar EMA para aceitar gap overnight
        _prev_macro_score = None
        _prev_macro_date = today_str

    if _prev_macro_score is not None:
        alpha = DEFAULT_DAMPENING_ALPHA
        smoothed = int(alpha * raw_macro_score + (1 - alpha) * _prev_macro_score)
    else:
        smoothed = raw_macro_score
    _prev_macro_score = smoothed

    # Sinal derivado do score suavizado (não do raw)
    if smoothed > 0:
        macro_signal = "COMPRA"
    elif smoothed < 0:
        macro_signal = "VENDA"
    else:
        macro_signal = "NEUTRO"

    result.macro_items = items
    result.macro_score = smoothed
    result.macro_signal = macro_signal
    result.macro_confidence = macro_conf
    # Guardar score bruto para diagnóstico
    result._raw_macro_score = raw_macro_score

    # ── Guardian inline: auto-suspensão da diretiva ──
    _check_directive_divergence(result)
    # 2) Preço atual e abertura WIN
    tick = _safe_get_tick(mt5, SYMBOL)
    if tick:
        result.price_current = tick.last.value
    result.price_open = _get_daily_open(mt5, SYMBOL)
    # 3) Candles M1, M5, M15, H1, H4 para micro tendência e regiões multi-TF
    candles_m1 = _safe_get_candles(mt5, SYMBOL, TimeFrame.M1, 200)
    candles_m5 = _safe_get_candles(mt5, SYMBOL, TimeFrame.M5, 100)
    candles_m15 = _safe_get_candles(mt5, SYMBOL, TimeFrame.M15, 100)
    candles_h1 = _safe_get_candles(mt5, SYMBOL, TimeFrame.H1, 50)
    candles_h4 = _safe_get_candles(mt5, SYMBOL, TimeFrame.H4, 50)
    # 4) VWAP (candles M5 do dia)
    today = datetime.now().date()
    candles_m5_today = [c for c in candles_m5 if c.timestamp.date() == today]
    result.vwap = _calc_vwap_from_candles(candles_m5_today)
    result.vwap_score = _calc_vwap_score(result.price_current, result.vwap)
    # 5) Pivôs Diários
    prev_h, prev_l, prev_c = _get_prev_day_hlc(mt5, SYMBOL)
    if prev_h > 0:
        result.pivots = _calc_pivot_levels(prev_h, prev_l, prev_c)
    # 6) SMC (usa M15 para mais estabilidade)
    result.smc = _detect_smc(candles_m15 if candles_m15 else candles_h1)
    # 6b) SMC Multi-Timeframe (H4, M15, M5)
    result.smc_multi_tf = _calc_smc_multi_tf(
        candles_h4 if candles_h4 else [],
        candles_m15 if candles_m15 else [],
        candles_m5 if candles_m5 else [],
    )
    # 7) Momentum M5
    result.momentum = _calc_momentum(candles_m5)
    # 8) Volume e OBV
    result.volume_score, result.obv_score = _calc_volume_score(candles_m5)
    # 8b) Saldo de agressão
    result.aggression_score, result.aggression_ratio = _calc_aggression_score(candles_m5)
    # 9) Regiões de interesse — multi-timeframe (M1, M5, M15)
    day_refs = _get_day_reference_prices(mt5, SYMBOL)
    result.regions = _map_regions_multi_tf(
        result.price_current, result.vwap, result.pivots,
        result.smc, candles_m1, candles_m5, candles_m15,
        day_refs,
    )
    # 10) Padrões de candle
    result.candle_pattern_score = _detect_candle_patterns(candles_m5, result.regions)
    # 11) Score Micro (soma dos componentes intraday)
    result.micro_score = (
        result.smc.bos_score + result.smc.equilibrium_score + result.smc.fvg_score
        + result.vwap_score
        + result.momentum.rsi_score + result.momentum.stoch_score
        + result.momentum.macd_score + result.momentum.bb_score
        + result.momentum.adx_score + result.momentum.ema9_score
        + result.volume_score + result.obv_score
        + result.candle_pattern_score
        + result.aggression_score
    )
    # 12) Classificação micro tendência
    result.micro_trend = _classify_micro_trend(
        result.macro_score, result.micro_score, result.momentum.adx,
    )
    # 13) Gerar oportunidades
    closes_m5 = [c.close.value for c in candles_m5]
    highs_m5 = [c.high.value for c in candles_m5]
    lows_m5 = [c.low.value for c in candles_m5]
    atr = _calc_atr(highs_m5, lows_m5, closes_m5, 14) if candles_m5 else Decimal("0")
    result.opportunities = _generate_opportunities(result, atr)
    return result


# ────────────────────────────────────────────────────────────────
# Persistência SQLite
# ────────────────────────────────────────────────────────────────

def _create_micro_trend_tables(db_path: str) -> None:
    """Cria tabelas específicas do agente de micro tendências."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS micro_trend_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            macro_score INTEGER NOT NULL,
            macro_signal TEXT NOT NULL,
            macro_confidence REAL NOT NULL,
            micro_score INTEGER NOT NULL,
            micro_trend TEXT NOT NULL,
            price_current REAL,
            price_open REAL,
            vwap REAL,
            pivot_pp REAL,
            smc_direction TEXT,
            smc_equilibrium TEXT,
            adx REAL,
            rsi REAL,
            num_opportunities INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS micro_trend_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER NOT NULL,
            timestamp DATETIME NOT NULL,
            item_number INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            category TEXT NOT NULL,
            score INTEGER NOT NULL,
            price_current REAL,
            price_open REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS micro_trend_regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER NOT NULL,
            timestamp DATETIME NOT NULL,
            price REAL NOT NULL,
            label TEXT NOT NULL,
            tipo TEXT NOT NULL,
            confluences INTEGER DEFAULT 1,
            distance_pct REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS micro_trend_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id INTEGER NOT NULL,
            timestamp DATETIME NOT NULL,
            direction TEXT NOT NULL,
            entry REAL NOT NULL,
            stop_loss REAL NOT NULL,
            take_profit REAL NOT NULL,
            risk_reward REAL NOT NULL,
            confidence REAL NOT NULL,
            reason TEXT,
            region TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mtd_timestamp ON micro_trend_decisions(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mti_decision ON micro_trend_items(decision_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mtr_decision ON micro_trend_regions(decision_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mto_decision ON micro_trend_opportunities(decision_id)")
    # Tabela de trades simulados (shadow mode)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulated_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            session_date DATE NOT NULL,
            direction TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_loss REAL NOT NULL,
            take_profit REAL NOT NULL,
            risk_reward REAL NOT NULL,
            confidence REAL NOT NULL,
            reason TEXT,
            macro_score REAL,
            micro_score REAL,
            micro_trend TEXT,
            smc_direction TEXT,
            price_at_decision REAL,
            result_30m TEXT,
            price_after_30m REAL,
            pnl_30m_pts REAL,
            evaluated_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sim_session ON simulated_trades(session_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sim_timestamp ON simulated_trades(timestamp)")
    # Eventos do watchdog hedge (auditoria e aprendizado)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hedge_watchdog_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            session_date DATE NOT NULL,
            event_type TEXT NOT NULL,
            action_taken TEXT NOT NULL,
            position_ticket INTEGER,
            symbol TEXT,
            volume REAL,
            sl REAL,
            tp REAL,
            status TEXT NOT NULL,
            message TEXT,
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hwe_session ON hedge_watchdog_events(session_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hwe_ticket ON hedge_watchdog_events(position_ticket)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hwe_timestamp ON hedge_watchdog_events(timestamp)")
    # KPI diário: falso positivo de reversão (simulado)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reversal_kpi_daily (
            session_date DATE PRIMARY KEY,
            total_reversal_signals INTEGER DEFAULT 0,
            resolved_reversal_signals INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            false_positive_rate REAL DEFAULT 0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # FIX 12/02/2026: Colunas extras para dampening e guardian override
    for col_def in [
        ("macro_score_raw", "INTEGER"),
        ("directive_suspended", "INTEGER DEFAULT 0"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE micro_trend_decisions ADD COLUMN {col_def[0]} {col_def[1]}")
        except Exception:
            pass  # Coluna já existe
    conn.commit()
    conn.close()


def _persist_cycle(db_path: str, result: CycleResult) -> None:
    """Persiste resultado do ciclo no SQLite."""
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Score bruto (antes do dampening) e status da suspensão da diretiva
    raw_score = getattr(result, '_raw_macro_score', result.macro_score)
    directive_suspended = 1 if (
        _diary_feedback and _diary_feedback.active
        and _diary_feedback.guardian_bias_override == "NEUTRO"
    ) else 0
    # Decisão principal
    cursor.execute("""
        INSERT INTO micro_trend_decisions
        (timestamp, macro_score, macro_signal, macro_confidence, micro_score,
         micro_trend, price_current, price_open, vwap, pivot_pp,
         smc_direction, smc_equilibrium, adx, rsi, num_opportunities,
         macro_score_raw, directive_suspended)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result.timestamp.isoformat(),
        result.macro_score, result.macro_signal, float(result.macro_confidence),
        result.micro_score, result.micro_trend,
        float(result.price_current), float(result.price_open),
        float(result.vwap.vwap), float(result.pivots.pp),
        result.smc.direction, result.smc.equilibrium,
        float(result.momentum.adx), float(result.momentum.rsi),
        len(result.opportunities),
        raw_score, directive_suspended,
    ))
    decision_id = cursor.lastrowid
    # Items macro
    for item in result.macro_items:
        if item.available:
            cursor.execute("""
                INSERT INTO micro_trend_items
                (decision_id, timestamp, item_number, symbol, category, score,
                 price_current, price_open)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision_id, result.timestamp.isoformat(),
                item.number, item.symbol, item.category, item.score,
                float(item.price_current), float(item.price_open),
            ))
    # Regiões (top 10 mais próximas)
    for region in result.regions[:10]:
        cursor.execute("""
            INSERT INTO micro_trend_regions
            (decision_id, timestamp, price, label, tipo, confluences, distance_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            decision_id, result.timestamp.isoformat(),
            float(region.price), region.label, region.tipo,
            region.confluences, float(region.distance_pct),
        ))
    # Oportunidades
    for opp in result.opportunities:
        cursor.execute("""
            INSERT INTO micro_trend_opportunities
            (decision_id, timestamp, direction, entry, stop_loss, take_profit,
             risk_reward, confidence, reason, region)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision_id, result.timestamp.isoformat(),
            opp.direction, float(opp.entry), float(opp.stop_loss),
            float(opp.take_profit), float(opp.risk_reward),
            float(opp.confidence), opp.reason, opp.region,
        ))
    conn.commit()
    conn.close()


# ────────────────────────────────────────────────────────────────
# Display — Console
# ────────────────────────────────────────────────────────────────

def _display_header():
    """Exibe cabeçalho do agente."""
    print("\n" + "═" * 70)
    print("  AGENTE MICRO TENDÊNCIA WINFUT — Day Trade B3")
    print("  Ciclo: 2min │ Horário: 09:00-17:55 │ Símbolo: WIN$N")
    print("═" * 70)


def _display_smc_multi_tf(result: CycleResult):
    """Exibe seção detalhada de SMC por timeframe (H4, M15, M5).

    Mostra para cada TF: bias, estrutura (HH/HL/LH/LL), BOS/CHoCH,
    equilibrium, zona de compra e zona de venda.
    """
    multi = result.smc_multi_tf
    cur = float(result.price_current) if result.price_current else 0.0

    # Ícones de alinhamento
    align_icons = {
        "BULLISH": "🟢",
        "BEARISH": "🔴",
        "MISTO": "🟡",
        "NEUTRO": "⚪",
    }
    align_icon = align_icons.get(multi.alignment, "⚪")

    print(f"╠{'─' * 68}╣")
    print(f"║  SMC MULTI-TIMEFRAME  │ Alinhamento: "
          f"{align_icon} {multi.alignment} ({multi.alignment_score:+d})")
    print(f"║  {'─' * 64}")

    # Header da tabela
    print(f"║  {'TF':>3} │ {'Bias':^8} │ {'Estrutura':^12} │ {'BOS/CHoCH':^12} │ {'Equil.':^9} │ {'Score':>5}")
    print(f"║  {'───':>3}─┼──{'────────':^8}──┼──{'────────────':^12}──┼──{'────────────':^12}──┼──{'─────────':^9}──┼──{'─────':>5}")

    for tf_data in [multi.h4, multi.m15, multi.m5]:
        tf = tf_data.timeframe
        # Bias com ícone
        bias_icons = {"BULLISH": "▲", "BEARISH": "▼", "NEUTRO": "─"}
        bias_icon = bias_icons.get(tf_data.bias, "─")
        bias_str = f"{bias_icon} {tf_data.bias:>7s}"

        # Estrutura (HH/HL ou LH/LL)
        struct = f"HH:{tf_data.hh_count} HL:{tf_data.hl_count}" if tf_data.bias == "BULLISH" else (
            f"LH:{tf_data.lh_count} LL:{tf_data.ll_count}" if tf_data.bias == "BEARISH" else
            f"HH:{tf_data.hh_count} LL:{tf_data.ll_count}"
        )

        # BOS/CHoCH
        bos_str = tf_data.bos_type if tf_data.bos_type else "─"

        # Equilibrium
        eq_icons = {"DISCOUNT": "💰", "PREMIUM": "⚠️", "NEUTRO": "◎"}
        eq_icon = eq_icons.get(tf_data.equilibrium, "◎")
        eq_str = f"{eq_icon}{tf_data.equilibrium:>8s}"

        print(f"║  {tf:>3} │ {bias_str:^8} │ {struct:^12} │ {bos_str:^12} │ {eq_str:^9} │ {tf_data.score:>+5d}")

    print(f"║  {'─' * 64}")

    # ── Zonas de Compra e Venda por TF ──
    print(f"║  PONTOS DE COMPRA/VENDA SMC:")

    for tf_data in [multi.h4, multi.m15, multi.m5]:
        tf = tf_data.timeframe
        buy_price = float(tf_data.buy_zone) if tf_data.buy_zone else 0
        sell_price = float(tf_data.sell_zone) if tf_data.sell_zone else 0
        fvg_price = float(tf_data.fvg_price) if tf_data.fvg_price else 0
        sh = float(tf_data.last_swing_high) if tf_data.last_swing_high else 0
        sl_val = float(tf_data.last_swing_low) if tf_data.last_swing_low else 0

        # Distância do preço atual
        buy_dist = f"{(cur - buy_price) / cur * 100:+.2f}%" if buy_price > 0 and cur > 0 else "  N/A "
        sell_dist = f"{(cur - sell_price) / cur * 100:+.2f}%" if sell_price > 0 and cur > 0 else "  N/A "

        buy_str = f"{buy_price:>10.0f} ({buy_dist})" if buy_price > 0 else "      ─      "
        sell_str = f"{sell_price:>10.0f} ({sell_dist})" if sell_price > 0 else "      ─      "

        # Indicação se preço está próximo da zona (< 0.15%)
        buy_near = " ◄◄" if buy_price > 0 and cur > 0 and abs(cur - buy_price) / cur < 0.0015 else ""
        sell_near = " ◄◄" if sell_price > 0 and cur > 0 and abs(cur - sell_price) / cur < 0.0015 else ""

        print(f"║    {tf:>3}  🟢 Compra: {buy_str}{buy_near}  │  🔴 Venda: {sell_str}{sell_near}")

        # Mostrar FVG se existir
        if fvg_price > 0:
            fvg_dist = f"{(cur - fvg_price) / cur * 100:+.2f}%" if cur > 0 else "N/A"
            fvg_icon = "△" if tf_data.fvg_type == "FVG_ALTA" else "▽"
            print(f"║         FVG {fvg_icon}: {fvg_price:>10.0f} ({fvg_dist}) │ "
                  f"SH: {sh:.0f} │ SL: {sl_val:.0f}")


def _display_cycle(result: CycleResult):
    """Exibe resultado do ciclo no console."""
    now = result.timestamp.strftime("%d/%m/%Y %H:%M:%S")
    # Cabeçalho do ciclo
    print(f"\n╔{'═' * 68}╗")
    print(f"║  {now}  │  WIN$N: {result.price_current}  "
          f"({'▲' if result.price_current >= result.price_open else '▼'} "
          f"vs {result.price_open})")
    print(f"╠{'═' * 68}╣")
    # Score Macro
    avail_count = sum(1 for i in result.macro_items if i.available)
    total_count = len(result.macro_items)
    macro_icon = "🟢" if result.macro_signal == "COMPRA" else ("🔴" if result.macro_signal == "VENDA" else "⚪")
    raw_score = getattr(result, '_raw_macro_score', result.macro_score)
    dampening_tag = f" (raw: {raw_score:+d})" if raw_score != result.macro_score else ""
    print(f"║  DIRECIONAL DO DIA: {macro_icon} {result.macro_signal} "
          f"│ Score: {result.macro_score:+d}{dampening_tag} │ Conf: {result.macro_confidence * 100:.1f}%"
          f" │ {avail_count}/{total_count} itens")
    print(f"╠{'─' * 68}╣")
    # Items macro por categoria (resumo compacto)
    categories = defaultdict(list)
    for item in result.macro_items:
        if item.available:
            categories[item.category].append(item)
    for cat, cat_items in sorted(categories.items()):
        cat_score = sum(i.score for i in cat_items)
        pos = sum(1 for i in cat_items if i.score > 0)
        neg = sum(1 for i in cat_items if i.score < 0)
        icon = "+" if cat_score > 0 else ("-" if cat_score < 0 else "=")
        # Mostra resumo compacto: score total, qtd positivos/negativos
        print(f"║  [{icon}] {cat:25s} │ Score: {cat_score:+3d} │ "
              f"▲{pos} ▼{neg} │ {len(cat_items)} itens")
    print(f"╠{'─' * 68}╣")
    # Micro Tendência
    if result.micro_trend == "CONTINUAÇÃO":
        trend_icon = "↗️" if result.micro_score >= 0 else "↘️"
    elif result.micro_trend == "REVERSÃO":
        trend_icon = "↩️"
    else:
        trend_icon = "↔️"
    print(f"║  MICRO TENDÊNCIA: {trend_icon} {result.micro_trend} │ Score Micro: {result.micro_score:+d}")
    # SMC
    print(f"║  SMC: {result.smc.direction} │ {result.smc.equilibrium} │ "
          f"BOS: {result.smc.bos_score:+d} │ EQ: {result.smc.equilibrium_score:+d} │ "
          f"FVG: {result.smc.fvg_score:+d}")
    # ── SMC Multi-Timeframe (H4, M15, M5) ──
    _display_smc_multi_tf(result)
    # Momentum
    m = result.momentum
    print(f"║  RSI: {m.rsi}({m.rsi_score:+d}) │ Stoch: {m.stoch}({m.stoch_score:+d}) │ "
          f"MACD: {m.macd_signal}({m.macd_score:+d}) │ ADX: {m.adx}({m.adx_score:+d})")
    print(f"║  BB: {m.bb_position}({m.bb_score:+d}) │ EMA9: {m.ema9_distance_pct}%({m.ema9_score:+d}) │ "
          f"Vol: {result.volume_score:+d} │ OBV: {result.obv_score:+d} │ "
          f"VWAP: {result.vwap_score:+d} │ Candle: {result.candle_pattern_score:+d}")
    # Saldo de agressão
    agr_label = "COMPRA" if result.aggression_score > 0 else ("VENDA" if result.aggression_score < 0 else "NEUTRO")
    print(f"║  AGR: {agr_label}({result.aggression_score:+d}) │ "
          f"Ratio: {result.aggression_ratio:.0%} compra / {1 - result.aggression_ratio:.0%} venda")
    print(f"╠{'─' * 68}╣")
    # ── Regiões de Interesse — Mapa Vertical Multi-TF ──
    cur = result.price_current
    regioes_acima = sorted(
        [r for r in result.regions if r.price > cur],
        key=lambda r: r.price,
    )
    regioes_abaixo = sorted(
        [r for r in result.regions if r.price <= cur],
        key=lambda r: r.price, reverse=True,
    )
    sell_zones = regioes_acima[:3]
    buy_zones = regioes_abaixo[:3]

    def _stars(confluences: int) -> str:
        n = max(1, min(5, confluences))
        return "★" * n + "☆" * (5 - n)

    def _vol_icon(vs: int) -> str:
        if vs >= 3: return "🔥"
        if vs >= 2: return "📊"
        if vs >= 1: return "·"
        return " "

    def _dist_str(dist_pct) -> str:
        return f"{float(dist_pct):+.2f}%"

    def _tf_tag(r) -> str:
        tf = getattr(r, 'source_tf', '')
        if not tf or tf == 'MULTI':
            return ""
        return f"[{tf}]"

    def _region_line(r) -> str:
        stars = _stars(r.confluences)
        vol = _vol_icon(getattr(r, 'volume_strength', 0))
        tf = _tf_tag(r)
        label_display = r.label[:18]
        return (
            f"║  {vol} {label_display:18s} │ {r.price:>12} │ "
            f"{_dist_str(r.distance_pct):>8s} │ {stars} {tf}"
        )

    print("║  REGIÕES DE INTERESSE (M1·M5·M15)")
    print(f"║  {'─' * 64}")
    print(f"║  {'🔴 ZONA DE VENDA (Resistências)':^64}")
    for r in reversed(sell_zones):
        print(_region_line(r))
    if not sell_zones:
        print(f"║    {'(sem resistências próximas)':^60}")
    print(f"║  {'─' * 64}")
    print(f"║  {'>>> PREÇO ATUAL':>30} │ {cur:>12} │{'◄':^20}")
    print(f"║  {'─' * 64}")
    for r in buy_zones:
        print(_region_line(r))
    if not buy_zones:
        print(f"║    {'(sem suportes próximos)':^60}")
    print(f"║  {'🟢 ZONA DE COMPRA (Suportes)':^64}")
    print(f"║  {'─' * 64}")
    # ── Referências rápidas ──
    v = result.vwap
    p = result.pivots
    print(f"║  REF │ VWAP: {v.vwap}  PP: {p.pp}  Ajuste: ", end="")
    ajuste = next((r.price for r in result.regions if "Ajuste" in r.label), None)
    print(f"{ajuste}" if ajuste else "N/A")
    # ── Vol legend ──
    print(f"║  🔥=vol explosão  📊=vol acima média  ·=vol normal")
    print(f"╠{'─' * 68}╣")
    # Oportunidades
    if result.opportunities:
        print("║  OPORTUNIDADES IDENTIFICADAS:")
        for opp in result.opportunities:
            direction_icon = "🟢 COMPRA" if opp.direction == "COMPRA" else "🔴 VENDA"
            print(f"║    {direction_icon} │ Entrada: {opp.entry} │ SL: {opp.stop_loss} │ "
                  f"TP: {opp.take_profit}")
            print(f"║    R/R: {opp.risk_reward}:1 │ Conf: {opp.confidence:.0f}% │ {opp.reason}")
    else:
        print("║  SEM OPORTUNIDADES no momento — aguardando setup")
        # Diagnóstico: mostra por que não há oportunidades
        reasons = getattr(result, '_rejection_reasons', [])
        if reasons:
            for reason in reasons:
                print(f"║    └─ {reason}")
    # ── Resumo Macro no rodapé ──
    print(f"╠{'═' * 68}╣")
    print(f"║  {now}  │  WIN$N: {result.price_current}  "
          f"({'▲' if result.price_current >= result.price_open else '▼'} "
          f"vs {result.price_open})")
    print(f"╠{'═' * 68}╣")
    print(f"║  DIRECIONAL DO DIA: {macro_icon} {result.macro_signal} "
          f"│ Score: {result.macro_score:+d}{dampening_tag} │ Conf: {result.macro_confidence * 100:.1f}%"
          f" │ {avail_count}/{total_count} itens")
    print(f"╚{'═' * 68}╝")


def _persist_simulated_trade(db_path: str, opp: 'Opportunity', result: 'CycleResult') -> None:
    """Persiste um trade simulado (shadow mode) no banco de dados."""
    import sqlite3
    from datetime import date
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO simulated_trades
        (timestamp, session_date, direction, entry_price, stop_loss, take_profit,
         risk_reward, confidence, reason, macro_score, micro_score, micro_trend,
         smc_direction, price_at_decision)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(),
        date.today().isoformat(),
        opp.direction,
        float(opp.entry),
        float(opp.stop_loss),
        float(opp.take_profit),
        float(opp.risk_reward),
        float(opp.confidence),
        opp.reason,
        float(result.macro_score) if result.macro_score else None,
        float(result.micro_score) if result.micro_score else None,
        result.micro_trend if hasattr(result, 'micro_trend') else None,
        result.smc_direction if hasattr(result, 'smc_direction') else None,
        float(result.price_current) if result.price_current else None,
    ))
    conn.commit()
    conn.close()


def _persist_hedge_watchdog_event(
    db_path: str,
    event_type: str,
    action_taken: str,
    position_ticket: Optional[int] = None,
    symbol: Optional[str] = None,
    volume: Optional[float] = None,
    sl: Optional[float] = None,
    tp: Optional[float] = None,
    status: str = "INFO",
    message: str = "",
    error_message: Optional[str] = None,
) -> None:
    """Persiste evento do watchdog hedge para auditoria e aprendizado."""
    import sqlite3
    from datetime import date

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO hedge_watchdog_events (
            timestamp, session_date, event_type, action_taken,
            position_ticket, symbol, volume, sl, tp,
            status, message, error_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(),
            date.today().isoformat(),
            event_type,
            action_taken,
            int(position_ticket) if position_ticket is not None else None,
            symbol,
            float(volume) if volume is not None else None,
            float(sl) if sl is not None else None,
            float(tp) if tp is not None else None,
            status,
            message,
            error_message,
        ),
    )
    conn.commit()
    conn.close()


def _get_simulated_summary(db_path: str) -> dict:
    """Retorna resumo dos trades simulados do dia."""
    import sqlite3
    from datetime import date
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    today = date.today().isoformat()
    cursor.execute("""
        SELECT direction, COUNT(*) as total,
               SUM(CASE WHEN result_30m = 'WIN' THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN result_30m = 'LOSS' THEN 1 ELSE 0 END) as losses,
               SUM(CASE WHEN result_30m IS NULL THEN 1 ELSE 0 END) as pending,
               SUM(COALESCE(pnl_30m_pts, 0)) as total_pnl
        FROM simulated_trades WHERE session_date = ?
        GROUP BY direction
    """, (today,))
    rows = cursor.fetchall()
    conn.close()
    summary = {'total': 0, 'wins': 0, 'losses': 0, 'pending': 0, 'pnl': 0.0, 'by_dir': {}}
    for direction, total, wins, losses, pending, pnl in rows:
        summary['total'] += total
        summary['wins'] += (wins or 0)
        summary['losses'] += (losses or 0)
        summary['pending'] += (pending or 0)
        summary['pnl'] += (pnl or 0.0)
        summary['by_dir'][direction] = {'total': total, 'wins': wins or 0, 'losses': losses or 0}
    return summary


def _persist_reversal_false_positive_kpi(db_path: str) -> dict:
    """Calcula e persiste KPI diário de falso positivo para sinais de reversão."""
    import sqlite3
    from datetime import date

    today = date.today().isoformat()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN result_30m IS NOT NULL THEN 1 ELSE 0 END) AS resolved,
            SUM(CASE WHEN result_30m = 'WIN' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN result_30m = 'LOSS' THEN 1 ELSE 0 END) AS losses
        FROM simulated_trades
        WHERE session_date = ?
          AND (reason LIKE 'Reversão%' OR reason LIKE '%REVERSÃO%')
        """,
        (today,),
    )
    row = cursor.fetchone() or (0, 0, 0, 0)
    total = int(row[0] or 0)
    resolved = int(row[1] or 0)
    wins = int(row[2] or 0)
    losses = int(row[3] or 0)
    false_positive_rate = (losses / resolved * 100.0) if resolved > 0 else 0.0

    cursor.execute(
        """
        INSERT INTO reversal_kpi_daily (
            session_date, total_reversal_signals, resolved_reversal_signals,
            wins, losses, false_positive_rate, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_date) DO UPDATE SET
            total_reversal_signals=excluded.total_reversal_signals,
            resolved_reversal_signals=excluded.resolved_reversal_signals,
            wins=excluded.wins,
            losses=excluded.losses,
            false_positive_rate=excluded.false_positive_rate,
            updated_at=excluded.updated_at
        """,
        (
            today,
            total,
            resolved,
            wins,
            losses,
            float(false_positive_rate),
            datetime.now().isoformat(),
        ),
    )

    conn.commit()
    conn.close()
    return {
        "session_date": today,
        "total": total,
        "resolved": resolved,
        "wins": wins,
        "losses": losses,
        "false_positive_rate": false_positive_rate,
    }


def _display_trading_status(trading_mgr: Optional['MicroTradingManager']) -> None:
    """Exibe status do trading automático."""
    if trading_mgr is None and not SIMULATE_MODE:
        return

    print(f"╔{'═' * 68}╗")
    if SIMULATE_MODE:
        sim = _get_simulated_summary(DB_PATH)
        rev_kpi = _persist_reversal_false_positive_kpi(DB_PATH)
        wr = (sim['wins'] / (sim['wins'] + sim['losses']) * 100) if (sim['wins'] + sim['losses']) > 0 else 0
        print(f"║  🧪 MODO SIMULADO (Shadow Mode) — Sem ordens reais")
        print(f"║  Sinais hoje: {sim['total']} │ "
              f"W/L: {sim['wins']}/{sim['losses']} │ "
              f"Pendente: {sim['pending']} │ "
              f"WR: {wr:.0f}% │ "
              f"PnL sim: {sim['pnl']:+.0f} pts")
        print(f"║  KPI REVERSÃO: total={rev_kpi['total']} │ "
              f"resolvidos={rev_kpi['resolved']} │ "
              f"FP={rev_kpi['false_positive_rate']:.0f}%")
        for d, info in sim['by_dir'].items():
            icon = "🟢" if d == "COMPRA" else "🔴"
            print(f"║    {icon} {d}: {info['total']} sinais │ W: {info['wins']} L: {info['losses']}")
    elif AUTO_TRADING_ENABLED:
        summary = trading_mgr.get_summary()
        status_icon = "🟢" if not trading_mgr.open_trades else "🔵"
        print(f"║  {status_icon} TRADING AUTOMÁTICO ATIVO")
        print(f"║  Trades hoje: {summary['trades']} │ "
              f"W/L: {summary['wins']}/{summary['losses']} │ "
              f"WR: {summary['win_rate']:.0f}% │ "
              f"PnL: {summary['daily_pnl']:+.0f} pts")

        # Posições abertas
        for t in trading_mgr.open_trades:
            icon = "🟢" if t.direction == "COMPRA" else "🔴"
            print(f"║  {icon} {t.direction} │ Entrada: {t.entry_price} │ "
                  f"SL: {t.stop_loss} │ TP: {t.take_profit} │ "
                  f"PnL: {t.unrealized_pnl:+.0f} pts")

        if not trading_mgr.open_trades:
            can, reason = trading_mgr.can_trade()
            status = "Aguardando setup" if can else reason
            print(f"║  📋 {status}")
    else:
        print(f"║  ⏸ TRADING AUTOMÁTICO DESLIGADO (use --auto-trade para ativar)")
    print(f"╚{'═' * 68}╝")


def _wait_with_progress(seconds: int) -> None:
    """Aguarda com barra de progresso."""
    for elapsed in range(seconds):
        pct = elapsed / seconds
        filled = int(pct * PROGRESS_BAR_WIDTH)
        bar = "█" * filled + "░" * (PROGRESS_BAR_WIDTH - filled)
        remaining = seconds - elapsed
        print(f"\r  Próximo ciclo: [{bar}] {remaining}s  ", end="", flush=True)
        time.sleep(1)
    print(f"\r  {'  ' * 30}\r", end="", flush=True)


def _is_market_hours() -> bool:
    """Verifica se está dentro do horário de pregão."""
    now = datetime.now().time()
    return PREGAO_INICIO <= now <= PREGAO_FIM


# ────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────

def main():
    """Loop principal do agente de micro tendências."""
    config = _get_config()
    global DB_PATH, AUTO_TRADING_ENABLED, SIMULATE_MODE
    DB_PATH = config.db_path

    # Checa flag --account <numero> para override de conta MT5
    if "--account" in sys.argv:
        idx = sys.argv.index("--account")
        if idx + 1 < len(sys.argv):
            config.mt5_login = int(sys.argv[idx + 1])
            print(f"\n  🔑 Conta MT5 override: {config.mt5_login}")

    # Checa flag --simulate (shadow mode — prioridade sobre --auto-trade)
    if "--simulate" in sys.argv:
        SIMULATE_MODE = True
        AUTO_TRADING_ENABLED = True  # Ativa avaliação de oportunidades
        print("\n  🧪  MODO SIMULADO (SHADOW MODE) ATIVADO")
        print("  🧪  Nenhuma ordem será enviada ao MT5")
        print("  🧪  Sinais serão logados em simulated_trades para análise posterior")
        print("  🧪  Pressione Ctrl+C para encerrar com segurança\n")
    # Checa flag --auto-trade
    elif "--auto-trade" in sys.argv:
        AUTO_TRADING_ENABLED = True
        print("\n  ⚠️  MODO TRADING AUTOMÁTICO ATIVADO")
        print("  ⚠️  ORDENS REAIS SERÃO EXECUTADAS NO MT5")
        print("  ⚠️  Pressione Ctrl+C para encerrar com segurança\n")

    # Cria banco de dados e tabelas
    create_database(DB_PATH)
    _create_micro_trend_tables(DB_PATH)
    create_directives_table(DB_PATH)
    create_diary_feedback_table(DB_PATH)

    # ── Carrega diretivas do Head Financeiro ──
    global _active_directive
    _active_directive = load_active_directive(DB_PATH)

    # ── Carrega feedback do diário (RL) ──
    global _diary_feedback
    _diary_feedback = load_latest_feedback(DB_PATH)

    _display_header()
    print(f"\n  DB: {DB_PATH}")
    print(f"  Símbolo: {SYMBOL}")
    print(f"  Refresh: {REFRESH_SECONDS}s")
    print(f"  Horário de pregão: {PREGAO_INICIO} - {PREGAO_FIM}")

    # ── Exibe diretivas ativas ──
    if _active_directive:
        hd = _active_directive
        dir_icon = "🟢" if hd.direction == "BULLISH" else ("🔴" if hd.direction == "BEARISH" else "⚪")
        print(f"\n  ╔{'═' * 60}╗")
        print(f"  ║  📋 DIRETIVA HEAD FINANCEIRO ATIVA ({hd.date})")
        print(f"  ║  {dir_icon} Direção: {hd.direction} │ Confiança: {hd.confidence_market}% │ Agress: {hd.aggressiveness}")
        print(f"  ║  Posição: {hd.position_size_pct}% │ Stop: {hd.stop_loss_pts or 'padrão'} pts")
        if hd.max_rsi_for_buy > 0:
            print(f"  ║  RSI máx BUY: {hd.max_rsi_for_buy} │ RSI mín SELL: {hd.min_rsi_for_sell}")
        if hd.forbidden_zone_above > 0:
            print(f"  ║  🚫 Zona proibida BUY: > {hd.forbidden_zone_above:.0f}")
        if hd.ideal_buy_zone_low > 0:
            print(f"  ║  ✅ Zona ideal BUY: {hd.ideal_buy_zone_low:.0f} - {hd.ideal_buy_zone_high:.0f}")
        if hd.reduce_before_event:
            print(f"  ║  ⚠️  Evento: {hd.event_description} ({hd.event_time})")
        if hd.notes:
            print(f"  ║  📝 {hd.notes[:55]}")
        print(f"  ╚{'═' * 60}╝")
    else:
        print(f"\n  ℹ️  Sem diretivas do Head Financeiro para hoje")

    # ── Exibe feedback do diário (RL) ──
    if _diary_feedback:
        dfb = _diary_feedback
        nota_icon = "🟢" if dfb.nota_agente >= 7 else ("🟡" if dfb.nota_agente >= 4 else "🔴")
        print(f"\n  ┌{'─' * 60}┐")
        print(f"  │  📊 FEEDBACK DO DIÁRIO (RL)  {nota_icon} Nota: {dfb.nota_agente}/10")
        print(f"  │  Threshold: BUY≥{dfb.threshold_sugerido_buy} SELL≤{dfb.threshold_sugerido_sell} │ "
              f"SMC bypass: {'SIM' if dfb.smc_bypass_recomendado else 'NÃO'} │ "
              f"Trend: {'SIM' if dfb.trend_following_recomendado else 'NÃO'}")
        if dfb.alertas_criticos:
            print(f"  │  ⚠ {len(dfb.alertas_criticos)} alerta(s) crítico(s)")
        if dfb.incoerencias:
            print(f"  │  🔴 {len(dfb.incoerencias)} incoerência(s)")
        if dfb.sugestoes:
            for s in dfb.sugestoes[:2]:
                print(f"  │  💡 {s[:57]}")
        # Regiões analisadas pelo diário
        if dfb.veredicto_regioes:
            print(f"  │  🎯 Regiões: {dfb.veredicto_regioes[:57]}")
        if dfb.regioes_fortes:
            print(f"  │  ✅ {len(dfb.regioes_fortes)} região(ões) FORTE(s) para operar:")
            for rf in dfb.regioes_fortes[:3]:
                print(f"  │     → {rf[:55]}")
        if dfb.regioes_armadilhas:
            print(f"  │  ⚠ {len(dfb.regioes_armadilhas)} armadilha(s) — evitar:")
            for ra in dfb.regioes_armadilhas[:3]:
                print(f"  │     → {ra[:55]}")
        # Análise direcional macro
        if dfb.veredicto_direcional:
            dir_icon = "🟢" if "SÓLIDO" in dfb.veredicto_direcional else (
                "🔴" if "FRACO" in dfb.veredicto_direcional else "🟡")
            print(f"  │  {dir_icon} Direcional: {dfb.veredicto_direcional[:55]}")
            if dfb.confianca_direcional_ajustada > 0:
                print(f"  │     Confiança ajustada: {dfb.confianca_direcional_ajustada:.0f}%")
            n_contra = len(dfb.direcional_contradicoes or [])
            n_vieses = len(dfb.direcional_vieses or [])
            if n_contra > 0 or n_vieses > 0:
                print(f"  │     ⚡ {n_contra} contradição(ões), {n_vieses} viés(es)")
        # Guardian Macro
        if dfb.guardian_kill_switch:
            print(f"  │  🛑 GUARDIAN KILL SWITCH ATIVO")
            if dfb.guardian_kill_reason:
                print(f"  │     Motivo: {dfb.guardian_kill_reason[:55]}")
        else:
            g_parts = []
            if dfb.guardian_confidence_penalty > 0:
                g_parts.append(f"penalty -{dfb.guardian_confidence_penalty:.0f}%")
            if dfb.guardian_reduced_exposure:
                g_parts.append("exposição reduzida")
            if dfb.guardian_bias_override:
                g_parts.append(f"bias→{dfb.guardian_bias_override}")
            if dfb.guardian_scenario_changes > 0:
                g_parts.append(f"{dfb.guardian_scenario_changes} mudança(s)")
            n_alertas = len(dfb.guardian_alertas or [])
            if g_parts or n_alertas > 0:
                print(f"  │  🛡️ Guardian: {' │ '.join(g_parts) if g_parts else 'ativo'}"
                      f"{f' │ {n_alertas} alerta(s)' if n_alertas else ''}")
        print(f"  └{'─' * 60}┘")
    else:
        print(f"\n  ℹ️  Sem feedback do diário disponível")

    if SIMULATE_MODE:
        print(f"  🧪 Modo: SIMULADO (Shadow) │ Contratos: {MAX_CONTRACTS} │ "
              f"Max pos: {MAX_POSITIONS} │ Ordens: SOMENTE LOG")
    elif AUTO_TRADING_ENABLED:
        print(f"  🤖 Auto-Trade: ATIVO │ Contratos: {MAX_CONTRACTS} │ "
              f"Max pos: {MAX_POSITIONS} │ Max loss: {MAX_DAILY_LOSS} pts")
    else:
        print(f"  📊 Modo: ANÁLISE APENAS (sem execução de ordens)")
    print()

    cycle_count = 0
    trading_mgr: Optional[MicroTradingManager] = None

    while True:
        try:
            # Verifica horário de pregão
            if not _is_market_hours():
                # Fecha posições abertas ao sair do pregão
                if trading_mgr and trading_mgr.open_trades:
                    try:
                        mt5 = _connect_mt5(config)
                        tick = _safe_get_tick(mt5, SYMBOL)
                        if tick:
                            trading_mgr.close_all(tick.last.value, "FIM_PREGAO")
                            print("  ✓ Posições fechadas — fim do pregão")
                        mt5.disconnect()
                    except Exception as e:
                        print(f"  ✗ Erro ao fechar posições: {e}")

                now = datetime.now().strftime("%H:%M:%S")
                print(f"\r  ⏸ Fora do horário de pregão ({now}). Aguardando... ", end="", flush=True)
                time.sleep(60)
                continue

            # Conecta ao MT5
            mt5 = _connect_mt5(config)

            # Inicializa trading manager (mantém estado entre ciclos)
            if AUTO_TRADING_ENABLED and trading_mgr is None:
                trading_mgr = MicroTradingManager(mt5, SYMBOL)

            # Atualiza referência do MT5 no trading manager
            if trading_mgr:
                trading_mgr.mt5 = mt5

            # Recarrega diretivas a cada 10 ciclos (pode ter sido atualizada)
            if cycle_count % 10 == 0:
                _active_directive = load_active_directive(DB_PATH)
                # Recarrega feedback do diário (análise crítica RL)
                _diary_feedback = load_latest_feedback(DB_PATH)
                if _diary_feedback and cycle_count == 10:
                    dfb = _diary_feedback
                    print(f"  📊 Diary feedback recarregado: nota={dfb.nota_agente}/10 "
                          f"| thresholds={dfb.threshold_sugerido_buy}/{dfb.threshold_sugerido_sell} "
                          f"| SMC_bypass={'SIM' if dfb.smc_bypass_recomendado else 'NÃO'}")

            # Executa ciclo
            cycle_count += 1
            print(f"\n  ──── Ciclo #{cycle_count} ────")
            result = _run_cycle(mt5)

            # Exibe resultados
            _display_cycle(result)

            # ── Trading Automático / Simulado ──
            if SIMULATE_MODE:
                # Modo simulado: avalia oportunidades mas só loga, sem executar
                if result.opportunities:
                    # Usa trading_mgr apenas para validação de regras
                    if trading_mgr is None:
                        trading_mgr = MicroTradingManager(mt5, SYMBOL)
                    can_trade, cant_reason = trading_mgr.can_trade()
                    if can_trade:
                        best = max(result.opportunities,
                                   key=lambda o: (o.confidence, o.risk_reward))
                        should_enter, eval_reason = trading_mgr.evaluate_opportunity(best)
                        if should_enter:
                            direction_icon = "🟢" if best.direction == "COMPRA" else "🔴"
                            print(f"\n  🧪 SINAL SIMULADO {direction_icon} {best.direction}")
                            print(f"     Entrada: {best.entry} │ SL: {best.stop_loss} │ "
                                  f"TP: {best.take_profit} │ R/R: {best.risk_reward}:1")
                            print(f"     Confiança: {best.confidence:.0f}% │ Razão: {best.reason}")
                            try:
                                _persist_simulated_trade(DB_PATH, best, result)
                                print(f"  ✓ Sinal logado em simulated_trades (sem ordem real)")
                            except Exception as e:
                                print(f"  ✗ Erro ao logar sinal simulado: {e}")
                        else:
                            print(f"  🧪 Opp rejeitada (simulado): {eval_reason}")
                    else:
                        print(f"  🧪 Sem entrada (simulado): {cant_reason}")

            elif AUTO_TRADING_ENABLED and trading_mgr:
                # 0) Watchdog hedge: evita posição contrária órfã sem TP/SL
                trading_mgr.monitor_hedge_orphans()

                # 1) Gerencia posições abertas (PnL, trailing, exits)
                if result.price_current > 0:
                    trading_mgr.manage_positions(result.price_current)

                # 2) Avalia novas oportunidades
                if result.opportunities:
                    can_trade, cant_reason = trading_mgr.can_trade()
                    if can_trade:
                        # Seleciona melhor oportunidade (maior R/R com confiança mínima)
                        best = max(result.opportunities,
                                   key=lambda o: (o.confidence, o.risk_reward))
                        should_enter, eval_reason = trading_mgr.evaluate_opportunity(best)
                        if should_enter:
                            direction_icon = "🟢" if best.direction == "COMPRA" else "🔴"
                            print(f"\n  ⚡ EXECUTANDO {direction_icon} {best.direction}")
                            print(f"     Entrada: {best.entry} │ SL: {best.stop_loss} │ "
                                  f"TP: {best.take_profit} │ R/R: {best.risk_reward}:1")
                            ticket = trading_mgr.execute_entry(best)
                            if ticket:
                                print(f"  ✓ Ordem executada! Ticket: {ticket}")
                            else:
                                print(f"  ✗ Falha na execução da ordem")
                        else:
                            print(f"  ⏸ Oportunidade rejeitada: {eval_reason}")
                    else:
                        print(f"  ⏸ Sem entrada: {cant_reason}")

            # Exibe status do trading
            _display_trading_status(trading_mgr if AUTO_TRADING_ENABLED else None)

            # Persiste no banco
            try:
                _persist_cycle(DB_PATH, result)
                print(f"  ✓ Dados persistidos no SQLite")
            except Exception as e:
                print(f"  ✗ Erro ao persistir: {e}")

            # Persiste episódio RL para aprendizagem por reforço
            try:
                from src.application.services.rl_persistence_service import RLPersistenceService
                from src.infrastructure.repositories.rl_repository import SqliteRLRepository
                from src.infrastructure.database.rl_schema import create_rl_tables
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker

                engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
                create_rl_tables(engine)
                SessionLocal = sessionmaker(bind=engine)
                rl_session = SessionLocal()
                rl_repo = SqliteRLRepository(rl_session)
                rl_service = RLPersistenceService(rl_repo)
                rl_service.initialize()

                episode_id = rl_service.persist_micro_cycle(result)
                if episode_id:
                    print(f"  ✓ Episódio RL persistido: {episode_id[:8]}...")

                # Avaliar recompensas pendentes
                def _get_win_price():
                    try:
                        return result.price_current
                    except Exception:
                        return None

                def _get_win_price_range(start_dt, end_dt):
                    """Retorna (max_price, min_price) do WIN no intervalo via candles M1."""
                    try:
                        candles = mt5.get_candles_range(
                            Symbol(SYMBOL), TimeFrame.M1,
                            start_dt, end_dt,
                        )
                        if not candles:
                            return None, None
                        max_price = max(c.high.value for c in candles)
                        min_price = min(c.low.value for c in candles)
                        return float(max_price), float(min_price)
                    except Exception:
                        return None, None

                evaluated = rl_service.evaluate_pending_rewards(
                    _get_win_price, _get_win_price_range
                )
                if evaluated > 0:
                    print(f"  ✓ {evaluated} recompensas RL avaliadas")

                rl_session.close()
            except Exception as e:
                print(f"  ⚠ RL: {e}")

            # Desconecta MT5
            try:
                mt5.disconnect()
            except Exception:
                pass

            # Aguarda próximo ciclo
            _wait_with_progress(REFRESH_SECONDS)

        except KeyboardInterrupt:
            print("\n\n  Agente encerrado pelo usuário.")
            # Fecha posições abertas
            if trading_mgr and trading_mgr.open_trades:
                print("  Fechando posições abertas...")
                try:
                    mt5 = _connect_mt5(config)
                    tick = _safe_get_tick(mt5, SYMBOL)
                    if tick:
                        trading_mgr.close_all(tick.last.value, "MANUAL")
                    mt5.disconnect()
                except Exception as e:
                    print(f"  ✗ Erro ao fechar posições: {e}")

            # Exibe resumo final
            if trading_mgr and trading_mgr.closed_trades:
                summary = trading_mgr.get_summary()
                print(f"\n  ════ RESUMO DO DIA ════")
                print(f"  Trades: {summary['trades']} │ W/L: {summary['wins']}/{summary['losses']}")
                print(f"  Win Rate: {summary['win_rate']:.0f}% │ PnL: {summary['daily_pnl']:+.0f} pts")
            break
        except Exception as e:
            print(f"\n  ✗ Erro no ciclo: {e}")
            import traceback
            traceback.print_exc()
            print(f"  Tentando novamente em 30s...")
            time.sleep(30)


if __name__ == "__main__":
    main()
