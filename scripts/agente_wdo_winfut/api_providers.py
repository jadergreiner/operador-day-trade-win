"""
Provedores de dados — APIs integradas ao agente WDO/WINFUT.

Modulo independente com integracoes:
  - AwesomeAPI   (cotacao USDBRL direta, gratis, sem chave)
  - TwelveData   (dados de mercado, requer API key)
  - AlphaVantage (indicadores economicos, requer API key)
  - ForexFactory (calendario economico, gratis)
  - Finnhub      (calendario economico, requer API key)
  - Fear & Greed (sentimento, gratis)
  - MetaTrader5  (dados H4/D1 para SMC + Momentum)
  - Telegram Bot (notificacoes de alertas)
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import numpy as np
import requests

logger = logging.getLogger("api_providers")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_DEFAULT_TIMEOUT = 12
_HEADERS = {"User-Agent": "Mozilla/5.0 (Bot WDO/WINFUT Agent)"}


# =========================================================================
# 1. AwesomeAPI — Cotacoes FX brasileiras (gratis, sem chave)
#    https://docs.awesomeapi.com.br/
# =========================================================================

def awesomeapi_usdbrl() -> dict | None:
    """Cotacao USD-BRL direta via AwesomeAPI.

    Returns:
        dict com open, close, high, low, last, volume ou None.
    """
    return awesomeapi_pair("USD-BRL")


def awesomeapi_pair(par_code: str) -> dict | None:
    """Cotacao de qualquer par via AwesomeAPI.

    Args:
        par_code: Par no formato 'XXX-YYY' (ex: 'USD-BRL', 'EUR-USD').

    Returns:
        dict com open, close, high, low, last, volume, source, symbol.
    """
    url = f"https://economia.awesomeapi.com.br/json/last/{par_code}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            logger.warning("AwesomeAPI %s HTTP %d", par_code, resp.status_code)
            return None
        data = resp.json()
        if not data:
            return None
        # A chave eh o par sem hifen: USDBRL
        key = par_code.replace("-", "")
        item = data.get(key, {})
        if not item:
            # Tenta primeira chave disponivel
            item = next(iter(data.values()), {})

        bid = float(item.get("bid", 0))
        ask = float(item.get("ask", 0))
        high = float(item.get("high", 0))
        low = float(item.get("low", 0))
        var_bid = float(item.get("varBid", 0))

        return {
            "open": bid - var_bid,
            "close": bid,
            "high": high,
            "low": low,
            "last": bid,
            "ask": ask,
            "volume": 0,
            "source": "awesomeapi",
            "symbol": par_code,
            "pct_change": float(item.get("pctChange", 0)),
            "timestamp": item.get("create_date", ""),
        }
    except Exception as e:
        logger.warning("AwesomeAPI falhou para %s: %s", par_code, e)
        return None


def awesomeapi_multi(pares: list[str]) -> dict[str, dict]:
    """Busca multiplos pares via AwesomeAPI em chamada unica.

    Args:
        pares: Lista de pares no formato 'XXX-YYY'.

    Returns:
        dict[par_code] -> quote_dict
    """
    url = f"https://economia.awesomeapi.com.br/json/last/{','.join(pares)}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        result = {}
        for par in pares:
            key = par.replace("-", "")
            item = data.get(key, {})
            if not item:
                continue
            bid = float(item.get("bid", 0))
            var_bid = float(item.get("varBid", 0))
            result[par] = {
                "open": bid - var_bid,
                "close": bid,
                "high": float(item.get("high", 0)),
                "low": float(item.get("low", 0)),
                "last": bid,
                "volume": 0,
                "source": "awesomeapi",
                "symbol": par,
                "pct_change": float(item.get("pctChange", 0)),
            }
        return result
    except Exception as e:
        logger.warning("AwesomeAPI multi falhou: %s", e)
        return {}


# =========================================================================
# 2. TwelveData — Dados de mercado (requer API key)
#    https://twelvedata.com/docs
# =========================================================================

def twelvedata_quote(symbol: str, api_key: str | None = None) -> dict | None:
    """Cotacao via TwelveData API.

    Args:
        symbol: Simbolo no formato TwelveData (ex: 'EUR/USD', 'SPY', 'GC').
        api_key: API key TwelveData.

    Returns:
        dict com open, close, high, low, last ou None.
    """
    key = api_key or os.getenv("TWELVEDATA_API_KEY")
    if not key:
        return None

    url = "https://api.twelvedata.com/quote"
    params = {"symbol": symbol, "apikey": key}
    try:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=_DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if "code" in data or "status" in data:
            # Erro da API
            if data.get("code") in (400, 401, 403, 404, 429):
                logger.warning("TwelveData erro %s: %s", symbol, data.get("message", ""))
                return None

        return {
            "open": float(data.get("open", 0)),
            "close": float(data.get("close", 0)),
            "high": float(data.get("high", 0)),
            "low": float(data.get("low", 0)),
            "last": float(data.get("close", 0)),
            "volume": int(data.get("volume", 0)),
            "source": "twelvedata",
            "symbol": symbol,
            "previous_close": float(data.get("previous_close", 0)),
        }
    except Exception as e:
        logger.warning("TwelveData falhou para %s: %s", symbol, e)
        return None


def twelvedata_timeseries(symbol: str, interval: str = "1day",
                          outputsize: int = 5,
                          api_key: str | None = None) -> list[dict] | None:
    """Serie temporal via TwelveData API.

    Args:
        symbol: Simbolo TwelveData.
        interval: Intervalo ('1min', '5min', '1h', '4h', '1day').
        outputsize: Numero de barras.
        api_key: API key.

    Returns:
        Lista de dicts com datetime, open, high, low, close, volume.
    """
    key = api_key or os.getenv("TWELVEDATA_API_KEY")
    if not key:
        return None

    url = "https://api.twelvedata.com/time_series"
    params = {"symbol": symbol, "interval": interval,
              "outputsize": outputsize, "apikey": key}
    try:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=_DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        values = data.get("values", [])
        if not values:
            return None
        return [
            {
                "datetime": v.get("datetime"),
                "open": float(v.get("open", 0)),
                "high": float(v.get("high", 0)),
                "low": float(v.get("low", 0)),
                "close": float(v.get("close", 0)),
                "volume": int(v.get("volume", 0)),
            }
            for v in values
        ]
    except Exception as e:
        logger.warning("TwelveData timeseries falhou: %s", e)
        return None


# =========================================================================
# 3. AlphaVantage — Indicadores economicos (requer API key)
#    https://www.alphavantage.co/documentation/
# =========================================================================

def alphavantage_quote(symbol: str, api_key: str | None = None) -> dict | None:
    """Cotacao via AlphaVantage GLOBAL_QUOTE.

    Args:
        symbol: Simbolo (ex: 'EURAUD', 'SPY', 'VALE').
        api_key: API key AlphaVantage.

    Returns:
        dict com open, close, high, low, last ou None.
    """
    key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")
    if not key:
        return None

    url = "https://www.alphavantage.co/query"
    params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": key}
    try:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        gq = data.get("Global Quote", {})
        if not gq:
            return None
        return {
            "open": float(gq.get("02. open", 0)),
            "high": float(gq.get("03. high", 0)),
            "low": float(gq.get("04. low", 0)),
            "close": float(gq.get("08. previous close", 0)),
            "last": float(gq.get("05. price", 0)),
            "volume": int(gq.get("06. volume", 0)),
            "source": "alphavantage",
            "symbol": symbol,
            "change_pct": gq.get("10. change percent", "0%"),
        }
    except Exception as e:
        logger.warning("AlphaVantage falhou para %s: %s", symbol, e)
        return None


def alphavantage_rsi(symbol: str, interval: str = "daily",
                     time_period: int = 14,
                     api_key: str | None = None) -> dict | None:
    """RSI via AlphaVantage.

    Returns:
        dict com valor RSI atual e anterior.
    """
    key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")
    if not key:
        return None

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "RSI",
        "symbol": symbol,
        "interval": interval,
        "time_period": time_period,
        "series_type": "close",
        "apikey": key,
    }
    try:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        ts = data.get("Technical Analysis: RSI", {})
        if not ts:
            return None
        dates = sorted(ts.keys(), reverse=True)
        if len(dates) < 2:
            return None
        return {
            "atual": float(ts[dates[0]]["RSI"]),
            "anterior": float(ts[dates[1]]["RSI"]),
            "date": dates[0],
        }
    except Exception as e:
        logger.warning("AlphaVantage RSI falhou para %s: %s", symbol, e)
        return None


# =========================================================================
# 4. ForexFactory / FairEconomy — Calendario Economico (gratis)
#    https://nfs.faireconomy.media/ff_calendar_thisweek.json
# =========================================================================

def forexfactory_calendar() -> list[dict]:
    """Calendario economico da semana via ForexFactory/FairEconomy.

    Returns:
        Lista de eventos com title, country, date, impact, forecast, previous, actual.
    """
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        if resp.status_code != 200:
            logger.warning("ForexFactory HTTP %d", resp.status_code)
            return []
        data = resp.json()
        if not isinstance(data, list):
            return []
        eventos = []
        for ev in data:
            eventos.append({
                "title": ev.get("title", ""),
                "country": ev.get("country", ""),
                "date": ev.get("date", ""),
                "impact": ev.get("impact", ""),
                "forecast": ev.get("forecast", ""),
                "previous": ev.get("previous", ""),
                "actual": ev.get("actual", ""),
            })
        return eventos
    except Exception as e:
        logger.warning("ForexFactory calendar falhou: %s", e)
        return []


def filtrar_eventos_br_us(eventos: list[dict]) -> dict:
    """Filtra eventos do calendario relevantes para BRL/USD.

    Returns:
        dict com listas 'brasil' e 'eua' de eventos de alto impacto.
    """
    brasil = []
    eua = []
    for ev in eventos:
        country = ev.get("country", "").upper()
        impact = ev.get("impact", "").lower()
        title = ev.get("title", "").lower()

        if country == "BRL" or "brazil" in title:
            brasil.append(ev)
        elif country == "USD" or country == "US":
            eua.append(ev)

    return {
        "brasil": brasil,
        "eua": eua,
        "brasil_alto_impacto": [e for e in brasil if e.get("impact", "").lower() in ("high", "holiday")],
        "eua_alto_impacto": [e for e in eua if e.get("impact", "").lower() in ("high", "holiday")],
    }


def detectar_copom_fomc(eventos: list[dict]) -> dict:
    """Detecta se ha eventos COPOM ou FOMC na semana atual.

    Returns:
        dict com 'copom_semana', 'fomc_semana', 'copom_fomc_mesma_semana'.
    """
    copom = False
    fomc = False
    copom_date = None
    fomc_date = None

    keywords_copom = ["copom", "selic", "bcb rate", "brazil interest"]
    keywords_fomc = ["fomc", "fed rate", "federal funds", "fed interest"]

    for ev in eventos:
        title = ev.get("title", "").lower()
        country = ev.get("country", "").upper()

        for kw in keywords_copom:
            if kw in title or (country == "BRL" and "rate" in title):
                copom = True
                copom_date = ev.get("date")
                break

        for kw in keywords_fomc:
            if kw in title or (country == "USD" and "rate" in title and "interest" in title):
                fomc = True
                fomc_date = ev.get("date")
                break

    return {
        "copom_semana": copom,
        "fomc_semana": fomc,
        "copom_fomc_mesma_semana": copom and fomc,
        "copom_date": copom_date,
        "fomc_date": fomc_date,
    }


# =========================================================================
# 5. Finnhub — Calendario Economico (requer API key)
#    https://finnhub.io/docs/api
# =========================================================================

def finnhub_calendar(api_key: str | None = None,
                     from_date: str | None = None,
                     to_date: str | None = None) -> list[dict]:
    """Calendario economico via Finnhub.

    Args:
        api_key: Finnhub API key.
        from_date: Data inicio 'YYYY-MM-DD'.
        to_date: Data fim 'YYYY-MM-DD'.

    Returns:
        Lista de eventos economicos.
    """
    key = api_key or os.getenv("FINNHUB_API_KEY")
    if not key:
        return []

    url = "https://finnhub.io/api/v1/calendar/economic"
    params = {"token": key}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date

    try:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=_DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            logger.warning("Finnhub HTTP %d", resp.status_code)
            return []
        data = resp.json()
        events = data.get("economicCalendar", [])
        return [
            {
                "title": ev.get("event", ""),
                "country": ev.get("country", ""),
                "date": ev.get("time", ""),
                "impact": ev.get("impact", ""),
                "actual": ev.get("actual"),
                "estimate": ev.get("estimate"),
                "prev": ev.get("prev"),
                "unit": ev.get("unit", ""),
            }
            for ev in events
        ]
    except Exception as e:
        logger.warning("Finnhub calendar falhou: %s", e)
        return []


# =========================================================================
# 6. Fear & Greed Index — Sentimento de Mercado (gratis)
#    https://alternative.me/crypto/fear-and-greed-index/
# =========================================================================

def fear_greed_index(limit: int = 2) -> dict | None:
    """Indice Fear & Greed via Alternative.me.

    Nota: Originalmente crypto, mas util como proxy de sentimento global.
    Valores: 0 = Extreme Fear, 100 = Extreme Greed.

    Returns:
        dict com value, classification, timestamp.
    """
    url = f"https://api.alternative.me/fng/?limit={limit}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=_DEFAULT_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        fng_data = data.get("data", [])
        if not fng_data:
            return None

        atual = fng_data[0]
        anterior = fng_data[1] if len(fng_data) > 1 else {}

        return {
            "value": int(atual.get("value", 50)),
            "classification": atual.get("value_classification", "Neutral"),
            "timestamp": atual.get("timestamp", ""),
            "anterior_value": int(anterior.get("value", 50)) if anterior else None,
            "anterior_classification": anterior.get("value_classification", "") if anterior else None,
            "tendencia": (int(atual.get("value", 50)) - int(anterior.get("value", 50))) if anterior else 0,
        }
    except Exception as e:
        logger.warning("Fear & Greed Index falhou: %s", e)
        return None


# =========================================================================
# 7. MetaTrader5 — Dados H4/D1 para SMC + Momentum
#    https://www.mql5.com/en/docs/python_metatrader5
# =========================================================================

_MT5_TIMEFRAMES = {
    "M1": 1, "M5": 5, "M15": 15, "M30": 30,
    "H1": 16385, "H4": 16388, "D1": 16408, "W1": 32769,
}


def mt5_conectar(login: int | None = None,
                 password: str | None = None,
                 server: str | None = None) -> bool:
    """Conecta ao terminal MetaTrader5.

    Args:
        login: Numero da conta (ou env MT5_LOGIN).
        password: Senha (ou env MT5_PASSWORD).
        server: Servidor (ou env MT5_SERVER).

    Returns:
        True se conectou, False caso contrario.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        logger.debug("MetaTrader5 package nao instalado")
        return False

    if not mt5.initialize():
        logger.warning("MT5 initialize falhou: %s", mt5.last_error())
        return False

    _login = login or int(os.getenv("MT5_LOGIN", "0"))
    _password = password or os.getenv("MT5_PASSWORD", "")
    _server = server or os.getenv("MT5_SERVER", "")

    if _login and _password and _server:
        if not mt5.login(_login, password=_password, server=_server):
            logger.warning("MT5 login falhou: %s", mt5.last_error())
            return False

    return True


def mt5_desconectar():
    """Desconecta do MetaTrader5."""
    try:
        import MetaTrader5 as mt5
        mt5.shutdown()
    except ImportError:
        pass


def mt5_candles(symbol: str, timeframe: str = "H4",
                count: int = 200) -> list[dict] | None:
    """Obtem candles do MetaTrader5.

    Args:
        symbol: Simbolo MT5 (ex: 'USDBRL', 'WIN$N').
        timeframe: 'M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1'.
        count: Numero de barras.

    Returns:
        Lista de dicts com time, open, high, low, close, volume.
        Retorna None se MT5 nao disponivel.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return None

    tf_code = _MT5_TIMEFRAMES.get(timeframe.upper())
    if tf_code is None:
        logger.warning("MT5 timeframe invalido: %s", timeframe)
        return None

    # Selecionar simbolo
    if not mt5.symbol_select(symbol, True):
        # Tenta variantes
        for alt in [symbol.replace("$", ""), symbol + "N", symbol + "$N"]:
            if mt5.symbol_select(alt, True):
                symbol = alt
                break
        else:
            logger.warning("MT5 simbolo nao encontrado: %s", symbol)
            return None

    rates = mt5.copy_rates_from_pos(symbol, tf_code, 0, count)
    if rates is None or len(rates) == 0:
        logger.warning("MT5 sem dados para %s %s: %s", symbol, timeframe, mt5.last_error())
        return None

    candles = []
    for r in rates:
        candles.append({
            "time": int(r["time"]),
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "volume": int(r["tick_volume"]),
        })
    return candles


def mt5_smc_analysis(candles: list[dict], config: dict | None = None) -> dict:
    """Analise Smart Money Concepts a partir de candles H4.

    Detecta:
      - Swing Highs / Swing Lows
      - Break of Structure (BOS) / Change of Character (CHoCH)
      - Order Blocks (OB)
      - Direcao de bias (bullish/bearish/neutral)

    Args:
        candles: Lista de candles H4 (time, open, high, low, close).
        config: Configuracao SMC (swing_window, poi_distancia_pct, etc).

    Returns:
        dict com bias, score, detalhes.
    """
    if not candles or len(candles) < 30:
        return {"bias": "neutral", "score": 0, "detalhes": "dados_insuficientes"}

    cfg = config or {}
    swing_window = cfg.get("swing_window", 3)
    poi_dist_pct = cfg.get("poi_distancia_pct", 2.0)

    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    closes = [c["close"] for c in candles]

    last_price = closes[-1]

    # Detectar Swing Highs e Swing Lows
    swing_highs = []
    swing_lows = []
    for i in range(swing_window, len(candles) - swing_window):
        h = highs[i]
        l = lows[i]
        is_sh = all(h >= highs[j] for j in range(i - swing_window, i + swing_window + 1) if j != i)
        is_sl = all(l <= lows[j] for j in range(i - swing_window, i + swing_window + 1) if j != i)
        if is_sh:
            swing_highs.append({"index": i, "price": h, "time": candles[i]["time"]})
        if is_sl:
            swing_lows.append({"index": i, "price": l, "time": candles[i]["time"]})

    if not swing_highs or not swing_lows:
        return {"bias": "neutral", "score": 0, "detalhes": "sem_swings"}

    # Tendencia: Higher Highs (HH) + Higher Lows (HL) = bullish
    #            Lower Highs (LH) + Lower Lows (LL) = bearish
    recent_highs = swing_highs[-4:] if len(swing_highs) >= 4 else swing_highs
    recent_lows = swing_lows[-4:] if len(swing_lows) >= 4 else swing_lows

    hh_count = sum(1 for i in range(1, len(recent_highs))
                   if recent_highs[i]["price"] > recent_highs[i-1]["price"])
    lh_count = sum(1 for i in range(1, len(recent_highs))
                   if recent_highs[i]["price"] < recent_highs[i-1]["price"])
    hl_count = sum(1 for i in range(1, len(recent_lows))
                   if recent_lows[i]["price"] > recent_lows[i-1]["price"])
    ll_count = sum(1 for i in range(1, len(recent_lows))
                   if recent_lows[i]["price"] < recent_lows[i-1]["price"])

    # Bias
    bullish_signals = hh_count + hl_count
    bearish_signals = lh_count + ll_count

    if bullish_signals > bearish_signals:
        bias = "bullish"
        score = min(bullish_signals - bearish_signals, 3)
    elif bearish_signals > bullish_signals:
        bias = "bearish"
        score = -min(bearish_signals - bullish_signals, 3)
    else:
        bias = "neutral"
        score = 0

    # BOS / CHoCH detection
    last_sh = swing_highs[-1]["price"] if swing_highs else 0
    last_sl = swing_lows[-1]["price"] if swing_lows else 0

    bos = None
    if last_price > last_sh:
        bos = "bullish_bos"
        score += 1
    elif last_price < last_sl:
        bos = "bearish_bos"
        score -= 1

    # POI (Point of Interest) — distancia do preco atual ate ultimo swing
    dist_sh_pct = abs(last_price - last_sh) / last_price * 100 if last_price else 0
    dist_sl_pct = abs(last_price - last_sl) / last_price * 100 if last_price else 0
    near_poi = dist_sh_pct < poi_dist_pct or dist_sl_pct < poi_dist_pct

    return {
        "bias": bias,
        "score": max(min(score, 3), -3),  # Limita a [-3, +3]
        "bos": bos,
        "near_poi": near_poi,
        "last_swing_high": last_sh,
        "last_swing_low": last_sl,
        "hh": hh_count,
        "hl": hl_count,
        "lh": lh_count,
        "ll": ll_count,
        "total_swing_highs": len(swing_highs),
        "total_swing_lows": len(swing_lows),
        "detalhes": f"bias={bias}, bos={bos}, poi={near_poi}",
    }


def mt5_momentum_analysis(candles: list[dict],
                          rsi_period: int = 14,
                          obv_lookback: int = 20) -> dict:
    """Analise de momentum e exaustao a partir de candles D1.

    Calcula:
      - RSI (Relative Strength Index)
      - OBV trend (On Balance Volume)
      - Momentum simples (rate of change)

    Args:
        candles: Lista de candles D1.
        rsi_period: Periodo do RSI.
        obv_lookback: Janela para tendencia do OBV.

    Returns:
        dict com rsi, obv_trend, momentum, score, exaustao.
    """
    if not candles or len(candles) < rsi_period + 5:
        return {"score": 0, "detalhes": "dados_insuficientes"}

    closes = np.array([c["close"] for c in candles], dtype=float)
    volumes = np.array([c["volume"] for c in candles], dtype=float)

    # RSI
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[-rsi_period:])
    avg_loss = np.mean(losses[-rsi_period:])

    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

    # OBV
    obv = np.zeros(len(closes))
    for i in range(1, len(closes)):
        if closes[i] > closes[i-1]:
            obv[i] = obv[i-1] + volumes[i]
        elif closes[i] < closes[i-1]:
            obv[i] = obv[i-1] - volumes[i]
        else:
            obv[i] = obv[i-1]

    obv_recent = obv[-obv_lookback:]
    obv_slope = (obv_recent[-1] - obv_recent[0]) / max(obv_lookback, 1)
    obv_trend = "up" if obv_slope > 0 else ("down" if obv_slope < 0 else "flat")

    # Momentum (Rate of Change 10 periodos)
    roc_period = min(10, len(closes) - 1)
    roc = ((closes[-1] - closes[-roc_period - 1]) / closes[-roc_period - 1]) * 100

    # Scoring
    score = 0

    # RSI extremos
    if rsi > 70:
        score -= 1  # Sobrecomprado — exaustao alta
        exaustao = "sobrecomprado"
    elif rsi < 30:
        score += 1  # Sobrevendido — exaustao baixa
        exaustao = "sobrevendido"
    else:
        exaustao = "neutro"

    # RSI divergencia com preco
    if rsi > 50 and roc < 0:
        score -= 1  # RSI alto mas preco caindo — divergencia bearish
    elif rsi < 50 and roc > 0:
        score += 1  # RSI baixo mas preco subindo — divergencia bullish

    # OBV trend
    if obv_trend == "up":
        score += 1  # Volume confirmando alta
    elif obv_trend == "down":
        score -= 1  # Volume confirmando baixa

    return {
        "rsi": round(rsi, 2),
        "obv_trend": obv_trend,
        "obv_slope": round(obv_slope, 2),
        "roc": round(roc, 4),
        "exaustao": exaustao,
        "score": max(min(score, 3), -3),  # Limita a [-3, +3]
        "detalhes": f"RSI={rsi:.1f}, OBV={obv_trend}, ROC={roc:.2f}%",
    }


# =========================================================================
# 8. Telegram Bot — Notificacoes (requer token + chat_id)
#    https://core.telegram.org/bots/api
# =========================================================================

def telegram_enviar(mensagem: str,
                    token: str | None = None,
                    chat_id: str | None = None,
                    parse_mode: str = "Markdown") -> bool:
    """Envia mensagem via Telegram Bot.

    Args:
        mensagem: Texto da mensagem.
        token: Bot token (ou env TELEGRAM_BOT_TOKEN).
        chat_id: Chat ID destino (ou env TELEGRAM_CHAT_ID).
        parse_mode: 'Markdown' ou 'HTML'.

    Returns:
        True se enviou com sucesso.
    """
    _token = token or os.getenv("TELEGRAM_BOT_TOKEN")
    _chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    if not _token or not _chat_id:
        logger.debug("Telegram nao configurado (sem token ou chat_id)")
        return False

    url = f"https://api.telegram.org/bot{_token}/sendMessage"
    payload = {
        "chat_id": _chat_id,
        "text": mensagem,
        "parse_mode": parse_mode,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Telegram: mensagem enviada com sucesso")
            return True
        else:
            logger.warning("Telegram HTTP %d: %s", resp.status_code, resp.text[:200])
            return False
    except Exception as e:
        logger.warning("Telegram envio falhou: %s", e)
        return False


def formatar_telegram_score(resultado: dict) -> str:
    """Formata resultado do agente para envio via Telegram.

    Args:
        resultado: dict retornado por AgenteWdoWinfut.executar().

    Returns:
        Mensagem formatada em Markdown.
    """
    wdo = resultado.get("wdo", {})
    winfut = resultado.get("winfut", {})
    veto = resultado.get("veto", False)

    emoji_wdo = _emoji_veredito(wdo.get("veredito", "NEUTRAL"))
    emoji_winfut = _emoji_veredito(winfut.get("veredito", "NEUTRAL"))

    msg = f"""📊 *Agente WDO/WINFUT Macro Score*
_{resultado.get('timestamp', '')[:19]}_

💵 *WDO (Dólar Futuro)*
Score: `{wdo.get('score_ajustado', 0):+.1f}` ({wdo.get('sessao', '')})
Veredito: {emoji_wdo} *{wdo.get('veredito', 'N/A')}*
Confiança: {wdo.get('confianca', 0):.1f}%

📈 *WINFUT (Ibovespa Futuro)*
Score: `{winfut.get('score_ajustado', 0):+.1f}` ({winfut.get('sessao', '')})
Veredito: {emoji_winfut} *{winfut.get('veredito', 'N/A')}*
Confiança: {winfut.get('confianca', 0):.1f}%

📉 VIX: {resultado.get('vix', 'N/A')} | S&P: {resultado.get('sp500_var_pct', 'N/A'):.2f}%"""

    if veto:
        msg += f"\n\n🚫 *VETO ATIVO*: {resultado.get('veto_msg', '')}"

    return msg


def _emoji_veredito(veredito: str) -> str:
    """Retorna emoji correspondente ao veredito."""
    mapa = {
        "STRONG_BUY": "🟢🟢",
        "BUY": "🟢",
        "NEUTRAL": "🟡",
        "SELL": "🔴",
        "STRONG_SELL": "🔴🔴",
        "VETO": "🚫",
    }
    return mapa.get(veredito, "⚪")
