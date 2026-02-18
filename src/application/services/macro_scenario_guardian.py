"""
Macro Scenario Guardian — Monitor Contínuo de Cenário Macro.

O Guardião Macro é uma thread de alta frequência (120s) que monitora:
  1. AGRESSÃO no dólar (USD/BRL) — disparo ou queda > 0.5% em janela curta
  2. AGRESSÃO nos índices americanos (S&P500) — move > 0.8%
  3. Eventos de alto impacto (COPOM, FOMC, NFP, CPI) — calendário ForexFactory
  4. Mudança de cenário macro — score deteriorou/melhorou significativamente
  5. Divergências graves — dólar disparando + agente comprando WIN

Persiste alertas no diary_feedback para que o agente ajuste em tempo real.

Autor: Head Financeiro / Sistema IA
Data: 11/02/2026
"""

from __future__ import annotations

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional

logger = logging.getLogger("macro_guardian")

# ── Thresholds de Agressão ──
# Variação % em janela curta que dispara alerta
USDBRL_SPIKE_PCT = 0.50      # Dólar moveu +0.50% em 10 min → agressão
USDBRL_CRASH_PCT = -0.50     # Dólar caiu -0.50% em 10 min → agressão inversa
SP500_SPIKE_PCT = 0.80       # S&P500 moveu ±0.80% → shock global
INDEX_REVERSAL_PTS = 500     # WIN moveu ±500 pts intra-dia → reversal
MACRO_SCORE_SHIFT = 15       # Score mudou ±15 pts entre ciclos → mudança cenário

# ── Frequência do Guardian ──
GUARDIAN_INTERVAL_SEC = 120   # A cada 2 minutos

# ── Cache de preços para detectar deltas ──
_price_history: dict[str, list[tuple[float, float]]] = {}  # symbol → [(timestamp, price)]
_MAX_HISTORY = 30  # Manter últimas 30 leituras (~1h a 2min de intervalo)


@dataclass
class MacroAlert:
    """Alerta individual do Guardian."""
    timestamp: str
    severity: str      # CRITICAL, WARNING, INFO
    category: str      # DOLAR_AGRESSAO, SP500_SHOCK, EVENTO_MACRO, CENARIO_MUDOU, DIVERGENCIA
    message: str
    action: str        # PAUSE_TRADING, REDUCE_EXPOSURE, REVERSE_BIAS, MONITOR, NONE
    data: dict = field(default_factory=dict)


@dataclass
class GuardianState:
    """Estado acumulado do Guardian para o dia."""
    alerts: list[MacroAlert] = field(default_factory=list)
    last_usdbrl: float = 0.0
    last_sp500: float = 0.0
    last_win_price: float = 0.0
    last_macro_score: int = 0
    last_macro_signal: str = ""
    scenario_changes: int = 0       # Quantas vezes o cenário mudou
    active_kill_switch: bool = False  # Kill switch ativo (pausar trading)
    kill_switch_reason: str = ""
    reduced_exposure: bool = False   # Exposição reduzida
    confidence_penalty: float = 0.0  # Penalidade de confiança (0-30)
    bias_override: str = ""          # Override de direção ("", "NEUTRO", "CONTRA")
    last_check: str = ""             # Timestamp do último check
    n_checks: int = 0


def _record_price(symbol: str, price: float) -> None:
    """Registra preço no histórico para cálculo de deltas."""
    now = time.time()
    if symbol not in _price_history:
        _price_history[symbol] = []
    _price_history[symbol].append((now, price))
    # Manter só últimas N leituras
    if len(_price_history[symbol]) > _MAX_HISTORY:
        _price_history[symbol] = _price_history[symbol][-_MAX_HISTORY:]


def _get_price_delta(symbol: str, window_sec: int = 600) -> tuple[float, float]:
    """Calcula variação % do preço na janela de tempo.

    Returns:
        (pct_change, abs_change)
    """
    hist = _price_history.get(symbol, [])
    if len(hist) < 2:
        return 0.0, 0.0

    now = time.time()
    current = hist[-1][1]

    # Achar o preço mais antigo dentro da janela
    oldest_in_window = current
    for ts, px in hist:
        if now - ts <= window_sec:
            oldest_in_window = px
            break

    if oldest_in_window == 0:
        return 0.0, 0.0

    pct = (current - oldest_in_window) / oldest_in_window * 100
    return pct, current - oldest_in_window


def _get_price_from_open(symbol: str) -> tuple[float, float]:
    """Calcula variação desde a abertura do dia (primeiro registro).

    Returns:
        (pct_from_open, pts_from_open)
    """
    hist = _price_history.get(symbol, [])
    if len(hist) < 2:
        return 0.0, 0.0

    open_price = hist[0][1]
    current = hist[-1][1]

    if open_price == 0:
        return 0.0, 0.0

    pct = (current - open_price) / open_price * 100
    return pct, current - open_price


def fetch_usdbrl_live() -> Optional[float]:
    """Busca cotação USD/BRL em tempo real via AwesomeAPI (gratuito)."""
    try:
        import requests
        resp = requests.get(
            "https://economia.awesomeapi.com.br/json/last/USD-BRL",
            timeout=10,
            headers={"User-Agent": "MacroGuardian/1.0"},
        )
        if resp.status_code == 200:
            data = resp.json()
            bid = float(data.get("USDBRL", {}).get("bid", 0))
            return bid if bid > 0 else None
    except Exception as e:
        logger.debug("AwesomeAPI USD/BRL falhou: %s", e)
    return None


def fetch_sp500_proxy(db_path: str) -> Optional[float]:
    """Busca preço do S&P500 proxy via items do agente (WSP no MT5).

    O agente já busca o WSP (mini S&P no MT5) a cada ciclo.
    Consultamos o último registro em micro_trend_items.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute("""
            SELECT price_current FROM micro_trend_items
            WHERE symbol LIKE '%WSP%' AND date(timestamp) = ?
            ORDER BY id DESC LIMIT 1
        """, (today,))
        row = cursor.fetchone()
        conn.close()
        if row and row["price_current"]:
            return float(row["price_current"])
    except Exception:
        pass
    return None


def fetch_win_price(db_path: str) -> Optional[float]:
    """Busca último preço do WIN via micro_trend_decisions."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute("""
            SELECT price FROM micro_trend_decisions
            WHERE date(timestamp) = ?
            ORDER BY id DESC LIMIT 1
        """, (today,))
        row = cursor.fetchone()
        conn.close()
        if row and row["price"]:
            return float(row["price"])
    except Exception:
        pass
    return None


def fetch_latest_macro_score(db_path: str) -> tuple[int, str, float]:
    """Busca score macro mais recente do agente.

    Returns:
        (score, signal, confidence)
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute("""
            SELECT macro_score, macro_signal, macro_confidence
            FROM micro_trend_decisions
            WHERE date(timestamp) = ?
            ORDER BY id DESC LIMIT 1
        """, (today,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return (
                int(row["macro_score"] or 0),
                str(row["macro_signal"] or ""),
                float(row["macro_confidence"] or 0),
            )
    except Exception:
        pass
    return 0, "", 0.0


def fetch_macro_score_history(db_path: str, limit: int = 10) -> list[dict]:
    """Busca evolução recente do score macro."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute("""
            SELECT id, timestamp, macro_score, macro_signal, macro_confidence, price
            FROM micro_trend_decisions
            WHERE date(timestamp) = ?
            ORDER BY id DESC LIMIT ?
        """, (today, limit))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return list(reversed(rows))  # cronológico
    except Exception:
        return []


def fetch_calendar_events() -> list[dict]:
    """Busca calendário econômico — eventos de alto impacto hoje."""
    try:
        from scripts.agente_wdo_winfut.api_providers import (
            forexfactory_calendar,
            filtrar_eventos_br_us,
            detectar_copom_fomc,
        )
        eventos = forexfactory_calendar()
        if not eventos:
            return []

        filtrados = filtrar_eventos_br_us(eventos)
        copom_fomc = detectar_copom_fomc(eventos)

        # Retornar eventos de alto impacto de hoje
        today_str = datetime.now().strftime("%Y-%m-%d")
        alto_impacto = []

        for ev in filtrados.get("brasil_alto_impacto", []) + filtrados.get("eua_alto_impacto", []):
            ev_date = ev.get("date", "")[:10]
            if ev_date == today_str or ev_date == "":
                alto_impacto.append(ev)

        # Adicionar info COPOM/FOMC
        if copom_fomc.get("copom_semana"):
            alto_impacto.append({
                "title": "COPOM esta semana",
                "country": "BRL",
                "impact": "HIGH",
                "date": copom_fomc.get("copom_date", ""),
                "_source": "copom_detection",
            })
        if copom_fomc.get("fomc_semana"):
            alto_impacto.append({
                "title": "FOMC esta semana",
                "country": "USD",
                "impact": "HIGH",
                "date": copom_fomc.get("fomc_date", ""),
                "_source": "fomc_detection",
            })

        return alto_impacto
    except Exception as e:
        logger.debug("Calendar fetch falhou: %s", e)
        return []


def fetch_fear_greed() -> Optional[dict]:
    """Busca índice Fear & Greed."""
    try:
        from scripts.agente_wdo_winfut.api_providers import fear_greed_index
        return fear_greed_index()
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Análises do Guardian
# ──────────────────────────────────────────────────────────────────────────────

def check_dollar_aggression(state: GuardianState) -> list[MacroAlert]:
    """Detecta agressão no dólar (USD/BRL)."""
    alerts = []
    usdbrl = fetch_usdbrl_live()
    if not usdbrl:
        return alerts

    _record_price("USDBRL", usdbrl)
    state.last_usdbrl = usdbrl

    # Delta em 10 min (~5 leituras de 2min)
    pct_10m, abs_10m = _get_price_delta("USDBRL", window_sec=600)
    # Delta desde abertura
    pct_open, abs_open = _get_price_from_open("USDBRL")

    now = datetime.now().isoformat()

    # ── Spike de curto prazo ──
    if pct_10m >= USDBRL_SPIKE_PCT:
        alerts.append(MacroAlert(
            timestamp=now,
            severity="CRITICAL",
            category="DOLAR_AGRESSAO",
            message=(
                f"🚨 DÓLAR DISPAROU +{pct_10m:.2f}% em 10min "
                f"(R$ {usdbrl:.4f}, +{abs_10m:.4f}). "
                f"Fluxo de saída forte — pressão vendedora no índice!"
            ),
            action="REDUCE_EXPOSURE",
            data={"usdbrl": usdbrl, "pct_10m": pct_10m, "direction": "UP"},
        ))
    elif pct_10m <= USDBRL_CRASH_PCT:
        alerts.append(MacroAlert(
            timestamp=now,
            severity="WARNING",
            category="DOLAR_AGRESSAO",
            message=(
                f"💰 DÓLAR DESPENCOU {pct_10m:.2f}% em 10min "
                f"(R$ {usdbrl:.4f}, {abs_10m:.4f}). "
                f"Fluxo de entrada forte — bullish para índice!"
            ),
            action="MONITOR",
            data={"usdbrl": usdbrl, "pct_10m": pct_10m, "direction": "DOWN"},
        ))

    # ── Move extremo intraday ──
    if abs(pct_open) >= 1.5:
        sev = "CRITICAL" if abs(pct_open) >= 2.5 else "WARNING"
        direction = "ALTA" if pct_open > 0 else "QUEDA"
        alerts.append(MacroAlert(
            timestamp=now,
            severity=sev,
            category="DOLAR_EXTREMO",
            message=(
                f"💱 DÓLAR em {direction} EXTREMA no dia: {pct_open:+.2f}% "
                f"(R$ {usdbrl:.4f}). Mercado sob stress cambial."
            ),
            action="REDUCE_EXPOSURE" if sev == "CRITICAL" else "MONITOR",
            data={"usdbrl": usdbrl, "pct_open": pct_open},
        ))

    return alerts


def check_sp500_shock(state: GuardianState, db_path: str) -> list[MacroAlert]:
    """Detecta movimentos bruscos no S&P500."""
    alerts = []
    sp500 = fetch_sp500_proxy(db_path)
    if not sp500 or sp500 <= 0:
        return alerts

    _record_price("SP500", sp500)
    state.last_sp500 = sp500

    pct_10m, _ = _get_price_delta("SP500", window_sec=600)
    pct_open, _ = _get_price_from_open("SP500")

    now = datetime.now().isoformat()

    if abs(pct_10m) >= SP500_SPIKE_PCT:
        direction = "SUBIU" if pct_10m > 0 else "CAIU"
        alerts.append(MacroAlert(
            timestamp=now,
            severity="CRITICAL",
            category="SP500_SHOCK",
            message=(
                f"🌎 S&P500 {direction} {abs(pct_10m):.2f}% em 10min! "
                f"Choque global pode arrastar mercado brasileiro."
            ),
            action="PAUSE_TRADING" if pct_10m < -SP500_SPIKE_PCT else "MONITOR",
            data={"sp500": sp500, "pct_10m": pct_10m},
        ))

    if abs(pct_open) >= 2.0:
        direction = "ALTA" if pct_open > 0 else "QUEDA"
        alerts.append(MacroAlert(
            timestamp=now,
            severity="WARNING",
            category="SP500_EXTREMO",
            message=(
                f"🌎 S&P500 em {direction} extrema no dia: {pct_open:+.2f}%. "
                f"Correlação com B3 pode ser forte."
            ),
            action="MONITOR",
            data={"sp500": sp500, "pct_open": pct_open},
        ))

    return alerts


def check_win_reversal(state: GuardianState, db_path: str) -> list[MacroAlert]:
    """Detecta reversão ou move extremo no WIN."""
    alerts = []
    win = fetch_win_price(db_path)
    if not win or win <= 0:
        return alerts

    _record_price("WIN", win)
    state.last_win_price = win

    _, pts_10m = _get_price_delta("WIN", window_sec=600)
    pct_open, pts_open = _get_price_from_open("WIN")

    now = datetime.now().isoformat()

    # ── Move extremo em 10 min ──
    if abs(pts_10m) >= INDEX_REVERSAL_PTS:
        direction = "SUBIU" if pts_10m > 0 else "CAIU"
        alerts.append(MacroAlert(
            timestamp=now,
            severity="WARNING",
            category="WIN_REVERSAL",
            message=(
                f"📈 WIN {direction} {abs(pts_10m):.0f} pts em 10min! "
                f"Movimento agressivo — verificar se macro mudou."
            ),
            action="MONITOR",
            data={"win": win, "pts_10m": pts_10m},
        ))

    # ── Reversão intraday (subiu muito e agora está voltando) ──
    hist = _price_history.get("WIN", [])
    if len(hist) >= 10:
        max_price = max(px for _, px in hist)
        min_price = min(px for _, px in hist)

        # Se caiu mais de 500pts do máximo do dia
        if max_price - win >= INDEX_REVERSAL_PTS and win > min_price + 200:
            alerts.append(MacroAlert(
                timestamp=now,
                severity="WARNING",
                category="WIN_REVERSAL",
                message=(
                    f"🔄 WIN revertendo: máx {max_price:.0f} → atual {win:.0f} "
                    f"({max_price - win:.0f} pts). Possível virada de tendência."
                ),
                action="REDUCE_EXPOSURE",
                data={"win": win, "max": max_price, "drawdown_pts": max_price - win},
            ))

    return alerts


def check_scenario_change(state: GuardianState, db_path: str) -> list[MacroAlert]:
    """Detecta mudança significativa no cenário macro (score)."""
    alerts = []
    score, signal, confidence = fetch_latest_macro_score(db_path)

    now = datetime.now().isoformat()

    # ── Mudança abrupta de score ──
    if state.last_macro_score != 0:
        delta = score - state.last_macro_score
        if abs(delta) >= MACRO_SCORE_SHIFT:
            direction = "MELHOROU" if delta > 0 else "DETERIOROU"
            alerts.append(MacroAlert(
                timestamp=now,
                severity="CRITICAL" if abs(delta) >= 25 else "WARNING",
                category="CENARIO_MUDOU",
                message=(
                    f"🔄 CENÁRIO {direction}: score {state.last_macro_score:+d} → "
                    f"{score:+d} (Δ{delta:+d}). "
                    f"Sinal: {state.last_macro_signal} → {signal}."
                ),
                action="REVERSE_BIAS" if abs(delta) >= 25 else "MONITOR",
                data={
                    "old_score": state.last_macro_score,
                    "new_score": score,
                    "delta": delta,
                    "old_signal": state.last_macro_signal,
                    "new_signal": signal,
                },
            ))
            state.scenario_changes += 1

    # ── Mudança de sinal (COMPRA→VENDA ou vice-versa) ──
    if (state.last_macro_signal and signal and
        state.last_macro_signal != signal and
        state.last_macro_signal != "NEUTRO" and signal != "NEUTRO"):
        alerts.append(MacroAlert(
            timestamp=now,
            severity="CRITICAL",
            category="SINAL_INVERTEU",
            message=(
                f"⚠️ SINAL INVERTEU: {state.last_macro_signal} → {signal}! "
                f"Score: {score:+d}. O cenário mudou de direção."
            ),
            action="REVERSE_BIAS",
            data={
                "old_signal": state.last_macro_signal,
                "new_signal": signal,
                "score": score,
            },
        ))

    # ── Evolução — score deteriorando progressivamente ──
    history = fetch_macro_score_history(db_path, limit=6)
    if len(history) >= 4:
        scores = [h["macro_score"] for h in history]
        # 4 quedas consecutivas
        diffs = [scores[i+1] - scores[i] for i in range(len(scores)-1)]
        consecutive_drops = sum(1 for d in diffs[-4:] if d < -1)
        if consecutive_drops >= 3:
            alerts.append(MacroAlert(
                timestamp=now,
                severity="WARNING",
                category="DETERIORACAO_PROGRESSIVA",
                message=(
                    f"📉 Score deteriorando progressivamente: "
                    f"{' → '.join(str(s) for s in scores[-4:])}. "
                    f"Momentum macro negativo."
                ),
                action="REDUCE_EXPOSURE",
                data={"scores": scores[-4:], "diffs": diffs[-4:]},
            ))

    state.last_macro_score = score
    state.last_macro_signal = signal

    return alerts


def check_divergences(state: GuardianState, db_path: str) -> list[MacroAlert]:
    """Detecta divergências perigosas entre mercados."""
    alerts = []
    now = datetime.now().isoformat()

    usdbrl_hist = _price_history.get("USDBRL", [])
    win_hist = _price_history.get("WIN", [])

    if len(usdbrl_hist) < 3 or len(win_hist) < 3:
        return alerts

    usdbrl_pct, _ = _get_price_delta("USDBRL", window_sec=600)
    win_pct, win_pts = _get_price_delta("WIN", window_sec=600)

    # ── Dólar subindo + WIN subindo = divergência perigosa ──
    if usdbrl_pct > 0.3 and win_pct > 0.2:
        alerts.append(MacroAlert(
            timestamp=now,
            severity="WARNING",
            category="DIVERGENCIA",
            message=(
                f"⚡ DIVERGÊNCIA: Dólar +{usdbrl_pct:.2f}% E WIN +{win_pct:.2f}% "
                f"subindo juntos! Normalmente inversamente correlacionados. "
                f"Um vai corrigir — CUIDADO com qual."
            ),
            action="REDUCE_EXPOSURE",
            data={"usdbrl_pct": usdbrl_pct, "win_pct": win_pct},
        ))

    # ── Dólar disparando + agente com sinal COMPRA ──
    score, signal, _ = fetch_latest_macro_score(db_path)
    if usdbrl_pct > USDBRL_SPIKE_PCT and signal == "COMPRA":
        alerts.append(MacroAlert(
            timestamp=now,
            severity="CRITICAL",
            category="DIVERGENCIA_SINAL",
            message=(
                f"🚨 CONFLITO: Dólar disparando +{usdbrl_pct:.2f}% mas agente "
                f"em sinal COMPRA (score +{score})! Fluxo de saída contradiz "
                f"posição comprada. Alto risco!"
            ),
            action="PAUSE_TRADING",
            data={"usdbrl_pct": usdbrl_pct, "signal": signal, "score": score},
        ))

    # ── S&P500 caindo forte + agente COMPRA ──
    sp500_pct, _ = _get_price_delta("SP500", window_sec=600)
    if sp500_pct < -SP500_SPIKE_PCT and signal == "COMPRA":
        alerts.append(MacroAlert(
            timestamp=now,
            severity="CRITICAL",
            category="DIVERGENCIA_GLOBAL",
            message=(
                f"🌎 S&P500 caindo {sp500_pct:.2f}% mas agente em COMPRA! "
                f"Crash global em andamento — B3 pode acompanhar."
            ),
            action="PAUSE_TRADING",
            data={"sp500_pct": sp500_pct, "signal": signal},
        ))

    return alerts


def check_calendar_events(state: GuardianState) -> list[MacroAlert]:
    """Verifica eventos de alto impacto no calendário econômico."""
    alerts = []
    events = fetch_calendar_events()
    if not events:
        return alerts

    now_dt = datetime.now()
    now = now_dt.isoformat()

    for ev in events:
        title = ev.get("title", "")
        country = ev.get("country", "")
        impact = ev.get("impact", "").upper()
        actual = ev.get("actual")

        # Evento de alto impacto com resultado publicado
        if impact == "HIGH" and actual is not None and actual != "":
            forecast = ev.get("forecast", "")
            previous = ev.get("previous", "")

            # Tentar detectar surprise
            surprise_msg = ""
            try:
                act_f = float(str(actual).replace("%", "").replace("K", "000").replace("M", "000000"))
                if forecast:
                    fore_f = float(str(forecast).replace("%", "").replace("K", "000").replace("M", "000000"))
                    surprise = act_f - fore_f
                    if abs(surprise) > abs(fore_f) * 0.1:  # >10% de surpresa
                        surprise_msg = (
                            f" SURPRESA: actual={actual} vs forecast={forecast} "
                            f"(diff {surprise:+.2f})"
                        )
            except (ValueError, TypeError):
                pass

            if surprise_msg:
                alerts.append(MacroAlert(
                    timestamp=now,
                    severity="WARNING",
                    category="EVENTO_MACRO",
                    message=(
                        f"📰 [{country}] {title}: {actual} "
                        f"(prev: {previous}).{surprise_msg}"
                    ),
                    action="MONITOR",
                    data={"event": title, "country": country, "actual": actual,
                          "forecast": forecast},
                ))

        # Evento de alto impacto IMINENTE (sem resultado ainda)
        elif impact == "HIGH" and (actual is None or actual == ""):
            ev_date_str = ev.get("date", "")
            if ev_date_str:
                try:
                    # Tentar parsear formato ForexFactory
                    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S",
                                "%m-%d-%Y %H:%M:%S"):
                        try:
                            ev_dt = datetime.strptime(ev_date_str[:19], fmt[:19]
                                                      if len(ev_date_str) < 25 else fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        continue

                    # Se o evento é nas próximas 2h
                    delta = ev_dt - now_dt
                    if timedelta(0) < delta < timedelta(hours=2):
                        mins = int(delta.total_seconds() / 60)
                        alerts.append(MacroAlert(
                            timestamp=now,
                            severity="WARNING",
                            category="EVENTO_IMINENTE",
                            message=(
                                f"⏰ [{country}] {title} em {mins} min! "
                                f"Evento de ALTO IMPACTO — considerar reduzir "
                                f"exposição antes da divulgação."
                            ),
                            action="REDUCE_EXPOSURE",
                            data={"event": title, "country": country,
                                  "minutes_until": mins},
                        ))
                except Exception:
                    pass

    return alerts


def check_fear_greed(state: GuardianState) -> list[MacroAlert]:
    """Verifica índice Fear & Greed para sinais de extremo."""
    alerts = []
    fg = fetch_fear_greed()
    if not fg:
        return alerts

    value = fg.get("value", 50)
    classification = fg.get("classification", "")
    tendencia = fg.get("tendencia", 0)
    now = datetime.now().isoformat()

    if value <= 20:
        alerts.append(MacroAlert(
            timestamp=now,
            severity="WARNING",
            category="SENTIMENTO_EXTREMO",
            message=(
                f"😱 EXTREME FEAR: Fear & Greed = {value} ({classification}). "
                f"Mercado em pânico — oportunidade de compra contrária ou "
                f"sinal de mais quedas."
            ),
            action="MONITOR",
            data={"fear_greed": value, "classification": classification},
        ))
    elif value >= 80:
        alerts.append(MacroAlert(
            timestamp=now,
            severity="WARNING",
            category="SENTIMENTO_EXTREMO",
            message=(
                f"🤑 EXTREME GREED: Fear & Greed = {value} ({classification}). "
                f"Mercado em euforia — risco de correção elevado."
            ),
            action="REDUCE_EXPOSURE",
            data={"fear_greed": value, "classification": classification},
        ))

    # Mudança brusca no sentimento
    if abs(tendencia) >= 15:
        direction = "melhorou" if tendencia > 0 else "piorou"
        alerts.append(MacroAlert(
            timestamp=now,
            severity="INFO",
            category="SENTIMENTO_MUDOU",
            message=(
                f"Sentimento {direction} {abs(tendencia)} pts "
                f"(F&G: {value}, {classification})."
            ),
            action="NONE",
            data={"fear_greed": value, "tendencia": tendencia},
        ))

    return alerts


# ──────────────────────────────────────────────────────────────────────────────
# Lógica principal do Guardian
# ──────────────────────────────────────────────────────────────────────────────

def determine_guardian_actions(state: GuardianState) -> None:
    """Consolida alertas em ações concretas para o agente.

    Atualiza state.active_kill_switch, state.reduced_exposure,
    state.confidence_penalty, state.bias_override.
    """
    if not state.alerts:
        return

    # Resetar ações a cada ciclo (baseado nos alertas ATIVOS)
    recent_alerts = [a for a in state.alerts
                     if a.timestamp >= (datetime.now() - timedelta(minutes=15)).isoformat()]

    has_pause = any(a.action == "PAUSE_TRADING" for a in recent_alerts)
    has_reduce = any(a.action == "REDUCE_EXPOSURE" for a in recent_alerts)
    has_reverse = any(a.action == "REVERSE_BIAS" for a in recent_alerts)
    n_critical = sum(1 for a in recent_alerts if a.severity == "CRITICAL")
    n_warning = sum(1 for a in recent_alerts if a.severity == "WARNING")

    # ── Kill Switch ──
    if has_pause or n_critical >= 3:
        state.active_kill_switch = True
        reasons = [a.message for a in recent_alerts if a.action == "PAUSE_TRADING"]
        state.kill_switch_reason = reasons[0] if reasons else "Múltiplos alertas CRITICAL"
    else:
        state.active_kill_switch = False
        state.kill_switch_reason = ""

    # ── Exposição reduzida ──
    state.reduced_exposure = has_reduce or n_critical >= 2

    # ── Penalidade de confiança ──
    penalty = 0.0
    if n_critical >= 3:
        penalty = 30.0
    elif n_critical >= 2:
        penalty = 20.0
    elif n_critical >= 1:
        penalty = 12.0
    elif n_warning >= 3:
        penalty = 10.0
    elif n_warning >= 2:
        penalty = 5.0
    state.confidence_penalty = penalty

    # ── Override de direção ──
    if has_reverse:
        reverse_alerts = [a for a in recent_alerts if a.action == "REVERSE_BIAS"]
        for ra in reverse_alerts:
            data = ra.data
            if data.get("new_signal"):
                state.bias_override = data["new_signal"]
                break
        else:
            state.bias_override = "NEUTRO"
    elif n_critical >= 3:
        state.bias_override = "NEUTRO"
    else:
        state.bias_override = ""


def run_guardian_check(state: GuardianState, db_path: str) -> list[MacroAlert]:
    """Executa um ciclo completo do Guardian.

    Retorna lista de NOVOS alertas gerados neste ciclo.
    """
    new_alerts = []

    # 1. Agressão no dólar (mais importante para WIN)
    new_alerts.extend(check_dollar_aggression(state))

    # 2. Shock S&P500
    new_alerts.extend(check_sp500_shock(state, db_path))

    # 3. Reversão/Move extremo WIN
    new_alerts.extend(check_win_reversal(state, db_path))

    # 4. Mudança de cenário (score macro)
    new_alerts.extend(check_scenario_change(state, db_path))

    # 5. Divergências perigosas
    new_alerts.extend(check_divergences(state, db_path))

    # 6. Calendário econômico (a cada 10 checks = ~20min)
    if state.n_checks % 10 == 0:
        new_alerts.extend(check_calendar_events(state))

    # 7. Fear & Greed (a cada 15 checks = ~30min)
    if state.n_checks % 15 == 0:
        new_alerts.extend(check_fear_greed(state))

    # Adicionar ao estado
    state.alerts.extend(new_alerts)
    state.n_checks += 1
    state.last_check = datetime.now().isoformat()

    # Limpar alertas muito antigos (>2h)
    cutoff = (datetime.now() - timedelta(hours=2)).isoformat()
    state.alerts = [a for a in state.alerts if a.timestamp >= cutoff]

    # Determinar ações consolidadas
    determine_guardian_actions(state)

    return new_alerts


def format_guardian_display(state: GuardianState,
                            new_alerts: list[MacroAlert]) -> str:
    """Formata display do guardian para o terminal."""
    lines = []
    now = datetime.now()

    lines.append("")
    lines.append("  ╔" + "═" * 64 + "╗")
    lines.append("  ║  🛡️  MACRO SCENARIO GUARDIAN                              ║")
    lines.append("  ║  Monitor contínuo de cenário (a cada 2 min)               ║")
    lines.append("  ╠" + "═" * 64 + "╣")

    # Status dos mercados monitorados
    usdbrl = state.last_usdbrl
    sp500 = state.last_sp500
    win = state.last_win_price

    if usdbrl > 0:
        pct_usd, _ = _get_price_from_open("USDBRL")
        usd_icon = "🔴" if pct_usd > 0.5 else ("🟢" if pct_usd < -0.5 else "⚪")
        lines.append(f"  ║  {usd_icon} USD/BRL: R$ {usdbrl:.4f} ({pct_usd:+.2f}% dia)")

    if sp500 > 0:
        pct_sp, _ = _get_price_from_open("SP500")
        sp_icon = "🟢" if pct_sp > 0.5 else ("🔴" if pct_sp < -0.5 else "⚪")
        lines.append(f"  ║  {sp_icon} S&P500:  {sp500:.0f} ({pct_sp:+.2f}% dia)")

    if win > 0:
        pct_win, pts_win = _get_price_from_open("WIN")
        win_icon = "🟢" if pct_win > 0.2 else ("🔴" if pct_win < -0.2 else "⚪")
        lines.append(f"  ║  {win_icon} WIN:     {win:.0f} ({pts_win:+.0f} pts, {pct_win:+.2f}%)")

    lines.append(f"  ║  Score macro: {state.last_macro_score:+d} ({state.last_macro_signal})")

    lines.append("  ╠" + "═" * 64 + "╣")

    # Estado do guardian
    if state.active_kill_switch:
        lines.append("  ║  🚨 KILL SWITCH ATIVO — TRADING PAUSADO")
        reason = state.kill_switch_reason[:58]
        lines.append(f"  ║     {reason}")
    elif state.reduced_exposure:
        lines.append("  ║  ⚠️  EXPOSIÇÃO REDUZIDA — cenário adverso")
    else:
        lines.append("  ║  ✅ Cenário dentro dos parâmetros")

    if state.confidence_penalty > 0:
        lines.append(f"  ║  Penalidade de confiança: -{state.confidence_penalty:.0f}%")
    if state.bias_override:
        lines.append(f"  ║  Override direcional: {state.bias_override}")
    if state.scenario_changes > 0:
        lines.append(f"  ║  Mudanças de cenário hoje: {state.scenario_changes}")

    lines.append("  ╠" + "═" * 64 + "╣")

    # Novos alertas deste ciclo
    if new_alerts:
        lines.append(f"  ║  🔔 {len(new_alerts)} NOVO(S) ALERTA(S):")
        for alert in new_alerts:
            sev_icon = "🔴" if alert.severity == "CRITICAL" else (
                "🟡" if alert.severity == "WARNING" else "ℹ️")
            # Word-wrap message
            msg = alert.message
            while len(msg) > 58:
                cut = msg[:58].rfind(" ")
                if cut < 20:
                    cut = 58
                lines.append(f"  ║  {sev_icon} {msg[:cut]}")
                msg = "     " + msg[cut:].strip()
            if msg.strip():
                lines.append(f"  ║  {sev_icon} {msg}")
            lines.append(f"  ║     Ação: {alert.action}")
    else:
        lines.append("  ║  Nenhum novo alerta neste ciclo")

    # Resumo de alertas ativos
    recent = [a for a in state.alerts
              if a.timestamp >= (now - timedelta(minutes=30)).isoformat()]
    if recent:
        n_crit = sum(1 for a in recent if a.severity == "CRITICAL")
        n_warn = sum(1 for a in recent if a.severity == "WARNING")
        lines.append(f"  ║  Alertas últimos 30min: {n_crit} CRITICAL, {n_warn} WARNING")

    lines.append("  ╚" + "═" * 64 + "╝")
    lines.append(f"  Check #{state.n_checks} — {now.strftime('%H:%M:%S')}")
    lines.append("")

    return "\n".join(lines)


def guardian_state_to_feedback_fields(state: GuardianState) -> dict:
    """Converte estado do guardian em campos para o DiaryFeedback.

    Retorna dict com os campos que devem ser setados no feedback.
    """
    # Montar lista de alertas ativos para persistir
    recent = [a for a in state.alerts
              if a.timestamp >= (datetime.now() - timedelta(minutes=30)).isoformat()]

    alertas_macro = []
    for a in recent:
        alertas_macro.append(f"[{a.severity}] {a.category}: {a.message[:100]}")

    return {
        "guardian_kill_switch": state.active_kill_switch,
        "guardian_kill_reason": state.kill_switch_reason,
        "guardian_reduced_exposure": state.reduced_exposure,
        "guardian_confidence_penalty": state.confidence_penalty,
        "guardian_bias_override": state.bias_override,
        "guardian_scenario_changes": state.scenario_changes,
        "guardian_alertas": alertas_macro,
    }
