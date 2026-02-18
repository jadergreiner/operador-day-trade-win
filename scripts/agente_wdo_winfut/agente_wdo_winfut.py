"""
Agente Macro Score WDO/WINFUT — Modulo independente.

Produz duas pontuacoes distintas:
  - Score WDO  (Dolar Futuro / USDBRL)
  - Score WINFUT (Ibovespa Futuro)

Capitulos 1-16 adaptados ao mercado brasileiro.
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import os

import numpy as np
import pandas as pd
import requests

# Provedores de dados integrados
from scripts.agente_wdo_winfut import api_providers as apis
from scripts.agente_wdo_winfut import macro_data_provider as macro_api

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config_wdo_winfut.json"
DB_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "db"
DB_PATH = DB_DIR / "wdo_winfut.db"

FRED_API_BASE = "https://api.stlouisfed.org/fred/series/observations"
CFTC_API_BASE = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d"

logger = logging.getLogger("agente_wdo_winfut")

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _carregar_config() -> dict:
    """Carrega config JSON do agente."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _salvar_config(cfg: dict) -> None:
    """Persiste config JSON do agente."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def _inicializar_db() -> sqlite3.Connection:
    """Inicializa banco SQLite e cria tabelas necessarias."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sinais_wdo_winfut (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ativo TEXT NOT NULL,
            timeframe TEXT,
            timestamp_ms INTEGER,
            tipo_sinal TEXT,
            score_total REAL,
            confianca REAL,
            veredito TEXT,
            score_commodities REAL DEFAULT 0,
            score_risco REAL DEFAULT 0,
            score_carry REAL DEFAULT 0,
            score_bcb REAL DEFAULT 0,
            score_fed REAL DEFAULT 0,
            score_fiscal REAL DEFAULT 0,
            score_usd_global REAL DEFAULT 0,
            score_smc REAL DEFAULT 0,
            score_sazonalidade_intraday REAL DEFAULT 0,
            score_macro_brl REAL DEFAULT 0,
            score_macro_usd REAL DEFAULT 0,
            score_momentum REAL DEFAULT 0,
            score_sentimento REAL DEFAULT 0,
            score_sazonalidade_macro REAL DEFAULT 0,
            score_fluxos REAL DEFAULT 0,
            score_geopolitica REAL DEFAULT 0,
            vix_valor REAL,
            sp500_var_pct REAL,
            yield_spread_10y REAL,
            crise_fiscal_alert INTEGER DEFAULT 0,
            intervencao_bcb_alert INTEGER DEFAULT 0,
            modelo TEXT,
            notas TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cotacoes_wdo_winfut (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            simbolo TEXT NOT NULL,
            timeframe TEXT,
            timestamp_ms INTEGER,
            preco_abertura REAL,
            preco_maximo REAL,
            preco_minimo REAL,
            preco_fechamento REAL,
            volume REAL,
            source TEXT DEFAULT 'yahoo',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS detalhes_score (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sinal_id INTEGER,
            capitulo TEXT,
            componente TEXT,
            score_wdo REAL DEFAULT 0,
            score_winfut REAL DEFAULT 0,
            valor_raw TEXT,
            descricao TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Coleta de dados — Yahoo Finance
# ---------------------------------------------------------------------------

def _yahoo_quote(symbol: str) -> dict | None:
    """Obtem cotacao via Yahoo Finance. Retorna {open, close, high, low, volume}."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = YAHOO_QUOTE_URL.format(symbol=symbol)
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return None
        meta = result[0].get("meta", {})
        indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
        timestamps = result[0].get("timestamp", [])
        if not timestamps:
            return None
        # Pegar ultimo dia completo
        idx = -1
        opens = indicators.get("open", [])
        closes = indicators.get("close", [])
        highs = indicators.get("high", [])
        lows = indicators.get("low", [])
        volumes = indicators.get("volume", [])

        if not closes or closes[idx] is None:
            idx = -2 if len(closes) > 1 else -1

        return {
            "open": opens[idx] if opens and opens[idx] is not None else 0,
            "close": closes[idx] if closes and closes[idx] is not None else 0,
            "high": highs[idx] if highs and highs[idx] is not None else 0,
            "low": lows[idx] if lows and lows[idx] is not None else 0,
            "volume": volumes[idx] if volumes and volumes[idx] is not None else 0,
            "last": meta.get("regularMarketPrice", closes[idx] if closes else 0),
            "source": "yahoo",
            "symbol": symbol,
        }
    except Exception as e:
        logger.warning("Yahoo quote falhou para %s: %s", symbol, e)
        return None


def _yahoo_multi_quotes(symbols: list[str]) -> dict[str, dict]:
    """Busca multiplas cotacoes Yahoo em sequencia."""
    result = {}
    for sym in symbols:
        q = _yahoo_quote(sym)
        if q:
            result[sym] = q
    return result


# ---------------------------------------------------------------------------
# Coleta de dados — FRED
# ---------------------------------------------------------------------------

def _fred_latest(series_id: str, api_key: str | None = None) -> dict | None:
    """Obtem as 2 ultimas observacoes de uma serie FRED."""
    try:
        params = {
            "series_id": series_id,
            "sort_order": "desc",
            "limit": 5,
            "file_type": "json",
        }
        if api_key:
            params["api_key"] = api_key
        else:
            params["api_key"] = "DEMO_KEY"
        resp = requests.get(FRED_API_BASE, params=params, timeout=15)
        if resp.status_code != 200:
            return None
        obs = resp.json().get("observations", [])
        # Filtrar valores validos
        valid = [o for o in obs if o.get("value") not in (".", "", None)]
        if len(valid) < 2:
            return None
        return {
            "atual": float(valid[0]["value"]),
            "anterior": float(valid[1]["value"]),
            "date": valid[0]["date"],
            "series_id": series_id,
        }
    except Exception as e:
        logger.warning("FRED falhou para %s: %s", series_id, e)
        return None


# ---------------------------------------------------------------------------
# Coleta de dados — CFTC COT
# ---------------------------------------------------------------------------

def _cftc_cot(contract_name: str, semanas: int = 4) -> list[dict] | None:
    """Busca COT Report da CFTC Socrata API."""
    try:
        params = {
            "$limit": semanas,
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "contract_market_name": contract_name,
        }
        resp = requests.get(CFTC_API_BASE, params=params, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data:
            return None
        return data
    except Exception as e:
        logger.warning("CFTC COT falhou para %s: %s", contract_name, e)
        return None


# ---------------------------------------------------------------------------
# Motor de Score — Capitulos 1-16
# ---------------------------------------------------------------------------

class AgenteWdoWinfut:
    """Agente independente de scoring para WDO (USDBRL) e WINFUT (Ibovespa)."""

    def __init__(self, config_path: str | Path | None = None,
                 fred_api_key: str | None = None,
                 twelvedata_key: str | None = None,
                 alphavantage_key: str | None = None,
                 finnhub_key: str | None = None,
                 telegram_token: str | None = None,
                 telegram_chat_id: str | None = None):
        self.config_path = Path(config_path) if config_path else CONFIG_PATH
        self.cfg = _carregar_config()
        self.fred_key = fred_api_key
        self.twelvedata_key = twelvedata_key or os.getenv("TWELVEDATA_API_KEY")
        self.alphavantage_key = alphavantage_key or os.getenv("ALPHAVANTAGE_API_KEY")
        self.finnhub_key = finnhub_key or os.getenv("FINNHUB_API_KEY")
        self.telegram_token = telegram_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.conn = _inicializar_db()
        self.detalhes: list[dict] = []
        self.scores_wdo: dict[str, float] = {}
        self.scores_winfut: dict[str, float] = {}
        self.vix_valor: float | None = None
        self.sp500_var_pct: float | None = None
        self.yield_spread_10y: float | None = None
        self.cotacoes_cache: dict[str, dict] = {}
        self.mt5_disponivel: bool = False
        self.now = datetime.now(timezone.utc)

        # Tentar conectar MT5 se configurado
        cfg_mt5 = self.cfg.get("apis", {}).get("metatrader5", {})
        if cfg_mt5.get("ativo", False):
            self.mt5_disponivel = apis.mt5_conectar()

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _registrar_detalhe(self, capitulo: str, componente: str,
                           score_wdo: float, score_winfut: float,
                           valor_raw: str = "", descricao: str = ""):
        self.detalhes.append({
            "capitulo": capitulo,
            "componente": componente,
            "score_wdo": score_wdo,
            "score_winfut": score_winfut,
            "valor_raw": str(valor_raw),
            "descricao": descricao,
        })

    def _snapshot_d1(self, quote: dict | None) -> int:
        """Retorna +1 se last > D1 open, -1 se <, 0 se indisponivel."""
        if not quote:
            return 0
        last = quote.get("last", 0)
        d1_open = quote.get("open", 0)
        if not last or not d1_open:
            return 0
        return 1 if last > d1_open else -1

    def _buscar_cotacao(self, cfg_par: dict) -> dict | None:
        """Tenta obter cotacao na cascata de fontes.

        Ordem: Yahoo → AwesomeAPI → TwelveData → AlphaVantage.
        """
        simbolo = cfg_par.get("simbolo", "")

        # 1. Cache
        if simbolo in self.cotacoes_cache:
            return self.cotacoes_cache[simbolo]

        quote = None

        # 2. Yahoo (fonte principal)
        yahoo_syms = cfg_par.get("yahoo", [])
        for sym in yahoo_syms:
            quote = _yahoo_quote(sym)
            if quote:
                break

        # 3. AwesomeAPI (fallback gratis — ideal para FX)
        if not quote:
            awesome_map = {
                "USDBRL": "USD-BRL", "EURUSD": "EUR-USD", "GBPUSD": "GBP-USD",
                "USDMXN": "USD-MXN", "USDZAR": "USD-ZAR", "USDCLP": "USD-CLP",
                "USDCAD": "USD-CAD", "USDJPY": "USD-JPY", "USDCNY": "USD-CNY",
            }
            awesome_sym = awesome_map.get(simbolo)
            # Tambem tenta exchangerate config
            exchangerate_syms = cfg_par.get("exchangerate", [])
            if not awesome_sym and exchangerate_syms:
                raw = exchangerate_syms[0]
                if len(raw) == 6:
                    awesome_sym = f"{raw[:3]}-{raw[3:]}"
            if awesome_sym:
                quote = apis.awesomeapi_pair(awesome_sym)

        # 4. TwelveData (fallback com API key)
        if not quote and self.twelvedata_key:
            td_map = {
                "XAUUSD": "XAU/USD", "XTIUSD": "WTI/USD",
                "US500": "SPX", "STOXX50": "IXIC",
                "VIX": "VIX", "DXY": "DXY",
                "EURUSD": "EUR/USD", "USDBRL": "USD/BRL",
            }
            td_sym = td_map.get(simbolo, simbolo)
            quote = apis.twelvedata_quote(td_sym, self.twelvedata_key)

        # 5. AlphaVantage (ultimo fallback)
        if not quote and self.alphavantage_key:
            av_syms = cfg_par.get("alphavantage", []) or yahoo_syms
            for sym in av_syms:
                # Limpar sufixos Yahoo
                av_sym = sym.replace("=X", "").replace("=F", "").replace("^" , "")
                quote = apis.alphavantage_quote(av_sym, self.alphavantage_key)
                if quote:
                    break

        # Cache resultado
        if quote:
            self.cotacoes_cache[simbolo] = quote

        return quote

    # -----------------------------------------------------------------------
    # Capitulo 1 — Commodities
    # -----------------------------------------------------------------------

    def avaliar_commodities(self) -> tuple[float, float]:
        """Cap. 1: Commodities exportacoes brasileiras."""
        cfg = self.cfg.get("capitulo_1_commodities", {})
        pares = cfg.get("pares", [])
        total_wdo = 0.0
        total_winfut = 0.0

        for par in pares:
            quote = self._buscar_cotacao(par)
            raw = self._snapshot_d1(quote)

            s_wdo = -raw if par.get("invert_wdo", False) else raw
            s_winfut = -raw if par.get("invert_winfut", False) else raw

            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe(
                "cap1_commodities", par["simbolo"],
                s_wdo, s_winfut,
                f"raw={raw}, last={quote.get('last') if quote else 'N/A'}",
                par.get("descricao", ""),
            )

        self.scores_wdo["commodities"] = total_wdo
        self.scores_winfut["commodities"] = total_winfut
        return total_wdo, total_winfut

    # -----------------------------------------------------------------------
    # Capitulo 2 — Risco Global
    # -----------------------------------------------------------------------

    def avaliar_risco_global(self) -> tuple[float, float]:
        """Cap. 2: Risk-on / Risk-off global."""
        cfg = self.cfg.get("capitulo_2_risco_global", {})
        pares = cfg.get("pares", [])
        total_wdo = 0.0
        total_winfut = 0.0

        for par in pares:
            quote = self._buscar_cotacao(par)

            if par["simbolo"] == "VIX":
                # Regra threshold
                vix_val = quote.get("last", 0) if quote else None
                self.vix_valor = vix_val
                if vix_val is not None:
                    if vix_val > par.get("threshold_risk_off", 20):
                        s_wdo, s_winfut = 1, -1  # risk-off
                    elif vix_val < par.get("threshold_risk_on", 15):
                        s_wdo, s_winfut = -1, 1  # risk-on
                    else:
                        s_wdo, s_winfut = 0, 0
                else:
                    s_wdo, s_winfut = 0, 0
                self._registrar_detalhe("cap2_risco", "VIX", s_wdo, s_winfut,
                                        f"vix={vix_val}", "Threshold risk-on/off")
            elif par["simbolo"] == "MOVE":
                raw = self._snapshot_d1(quote)
                s_wdo = raw  # MOVE sobe = stress = dolar sobe
                s_winfut = -raw
                self._registrar_detalhe("cap2_risco", "MOVE", s_wdo, s_winfut,
                                        f"raw={raw}", par.get("descricao", ""))
            elif par["simbolo"] == "US500":
                raw = self._snapshot_d1(quote)
                sp_last = quote.get("last", 0) if quote else 0
                sp_open = quote.get("open", 0) if quote else 0
                if sp_open:
                    self.sp500_var_pct = ((sp_last - sp_open) / sp_open) * 100
                s_wdo = -raw  # risk-on = BRL forte = WDO cai
                s_winfut = raw
                self._registrar_detalhe("cap2_risco", "US500", s_wdo, s_winfut,
                                        f"raw={raw}", par.get("descricao", ""))
            else:
                raw = self._snapshot_d1(quote)
                invert_wdo = par.get("invert_wdo", True)
                invert_winfut = par.get("invert_winfut", False)
                s_wdo = -raw if invert_wdo else raw
                s_winfut = -raw if invert_winfut else raw
                self._registrar_detalhe("cap2_risco", par["simbolo"], s_wdo, s_winfut,
                                        f"raw={raw}", par.get("descricao", ""))

            total_wdo += s_wdo
            total_winfut += s_winfut

        self.scores_wdo["risco"] = total_wdo
        self.scores_winfut["risco"] = total_winfut
        return total_wdo, total_winfut

    # -----------------------------------------------------------------------
    # Capitulo 3 — Carry Trade
    # -----------------------------------------------------------------------

    def avaliar_carry_trade(self) -> tuple[float, float]:
        """Cap. 3: Diferencial de juros BR vs US — com yield curves reais.

        Usa BCB SGS (Selic) + FRED (US10Y, US2Y) para calcular spread
        de carry trade. Fallback para método legado se APIs falharem.
        """
        cfg = self.cfg.get("capitulo_3_carry_trade", {})
        total_wdo = 0.0
        total_winfut = 0.0

        # ── Yield Curves via macro_data_provider ──
        yields_us = macro_api.fetch_yield_curve_us(self.fred_key)
        yields_br = macro_api.fetch_yield_curve_br()

        # US10Y
        us10y = yields_us.get("US10Y")
        if us10y:
            var = us10y["variacao_pct"]
            raw = 1 if var > 0.5 else (-1 if var < -0.5 else 0)
            # US10Y subindo = USD forte = WDO sobe, WINFUT desfavorável
            s_wdo = raw
            s_winfut = -raw
            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe("cap3_carry", "US10Y", s_wdo, s_winfut,
                                    f"yield={us10y['atual']:.3f}%, var={var:.2f}%",
                                    f"Treasury 10Y via {us10y['source']}")
        else:
            self._registrar_detalhe("cap3_carry", "US10Y", 0, 0,
                                    "sem_dados", "FRED DGS10 indisponível")

        # US2Y
        us2y = yields_us.get("US2Y")
        if us2y:
            var = us2y["variacao_pct"]
            raw = 1 if var > 0.5 else (-1 if var < -0.5 else 0)
            s_wdo = raw
            s_winfut = -raw
            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe("cap3_carry", "US2Y", s_wdo, s_winfut,
                                    f"yield={us2y['atual']:.3f}%, var={var:.2f}%",
                                    f"Treasury 2Y via {us2y['source']}")

        # Spread 10Y-2Y (inversão de curva)
        spread_10_2 = yields_us.get("SPREAD_10Y_2Y")
        if spread_10_2:
            delta = spread_10_2["variacao"]
            # Curva achatando/invertendo = risco recessão = risk-off
            raw = 1 if delta > 0.02 else (-1 if delta < -0.02 else 0)
            s_wdo = -raw  # risk-off = dólar sobe globalmente mas BRL costuma correlacionar
            s_winfut = raw  # curva steepening = menos medo recessão = bolsa
            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe("cap3_carry", "SPREAD_10Y_2Y", s_wdo, s_winfut,
                                    f"spread={spread_10_2['atual']:.3f}%, delta={delta:.3f}",
                                    spread_10_2.get("descricao", ""))

        # BR Selic
        br_selic = yields_br.get("BR_SELIC")
        if br_selic:
            # Selic alta e subindo = carry atrativo = BRL forte
            var = br_selic["variacao"]
            raw = 1 if var > 0 else (-1 if var < 0 else 0)
            s_wdo = -raw  # Selic sobe = BRL mais atrativo = dólar cai
            s_winfut = -raw  # Selic sobe = custo capital maior = bolsa pressionada
            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe("cap3_carry", "BR_SELIC", s_wdo, s_winfut,
                                    f"selic={br_selic['atual']:.2f}%, var={var:.2f}",
                                    f"Selic Meta BCB SGS")

        # Carry Trade Spread Calculado (BR - US)
        carry = macro_api.calcular_carry_trade_spread(yields_br, yields_us)
        if carry:
            # Spread subindo = carry mais atrativo = fluxo pra BR
            delta = carry["delta"]
            raw = 1 if delta > 0.1 else (-1 if delta < -0.1 else 0)
            s_wdo = -raw  # carry atrativo = BRL forte = dólar cai
            s_winfut = 0  # carry em si não impacta diretamente bolsa, já capturado na Selic
            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe("cap3_carry", "CARRY_SPREAD_BR_US", s_wdo, s_winfut,
                                    f"spread={carry['spread_atual']:.2f}%, tend={carry['tendencia']}",
                                    f"Carry BR-US ({carry['source']})")
            self.yield_spread_10y = carry["spread_atual"]

        # ── Fallback legado: DI1F via cotação ──
        spreads_cfg = cfg.get("spreads", [])
        for sp in spreads_cfg:
            if sp.get("tipo") == "snapshot_par":
                quote = self._buscar_cotacao(sp)
                raw = self._snapshot_d1(quote)
                s_wdo = -raw
                s_winfut = -raw
                total_wdo += s_wdo
                total_winfut += s_winfut
                self._registrar_detalhe("cap3_carry", sp.get("id", "DI1F"), s_wdo, s_winfut,
                                        f"raw={raw}", sp.get("descricao", ""))

        self.scores_wdo["carry"] = total_wdo
        self.scores_winfut["carry"] = total_winfut
        return total_wdo, total_winfut

    # -----------------------------------------------------------------------
    # Capitulo 4 — BCB Policy (Manual)
    # -----------------------------------------------------------------------

    def avaliar_bcb_policy(self) -> tuple[float, float]:
        """Cap. 4: Politica monetaria BCB (COPOM)."""
        cfg = self.cfg.get("capitulo_4_bcb_policy", {})
        campos = cfg.get("campos", {})
        regras = cfg.get("regras", {})
        total_wdo = 0.0
        total_winfut = 0.0

        for campo, valor in campos.items():
            regra = regras.get(campo, {})
            valor_str = str(valor).lower()
            scores = regra.get(valor_str, {"wdo": 0, "winfut": 0})
            s_wdo = scores.get("wdo", 0)
            s_winfut = scores.get("winfut", 0)
            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe("cap4_bcb", campo, s_wdo, s_winfut,
                                    valor_str, f"BCB {campo}")

        self.scores_wdo["bcb"] = total_wdo
        self.scores_winfut["bcb"] = total_winfut
        return total_wdo, total_winfut

    # -----------------------------------------------------------------------
    # Capitulo 5 — Fed Policy (Manual)
    # -----------------------------------------------------------------------

    def avaliar_fed_policy(self) -> tuple[float, float]:
        """Cap. 5: Politica monetaria Fed (FOMC)."""
        cfg = self.cfg.get("capitulo_5_fed_policy", {})
        campos = cfg.get("campos", {})
        regras = cfg.get("regras", {})
        total_wdo = 0.0
        total_winfut = 0.0

        for campo, valor in campos.items():
            regra = regras.get(campo, {})
            valor_str = str(valor).lower()
            scores = regra.get(valor_str, {"wdo": 0, "winfut": 0})
            s_wdo = scores.get("wdo", 0)
            s_winfut = scores.get("winfut", 0)
            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe("cap5_fed", campo, s_wdo, s_winfut,
                                    valor_str, f"Fed {campo}")

        self.scores_wdo["fed"] = total_wdo
        self.scores_winfut["fed"] = total_winfut
        return total_wdo, total_winfut

    # -----------------------------------------------------------------------
    # Capitulo 6 — Risco Fiscal
    # -----------------------------------------------------------------------

    def avaliar_risco_fiscal(self) -> tuple[float, float]:
        """Cap. 6: Politica fiscal brasileira e risco soberano."""
        cfg = self.cfg.get("capitulo_6_risco_fiscal", {})
        campos = cfg.get("campos_manuais", {})
        regras = cfg.get("regras_manuais", {})
        total_wdo = 0.0
        total_winfut = 0.0

        # CDS 5Y threshold
        cds = campos.get("cds_5y_br_bps", 180)
        th_alto = campos.get("cds_threshold_alto", 200)
        th_baixo = campos.get("cds_threshold_baixo", 150)
        if cds > th_alto:
            s_wdo, s_winfut = 1, -1
        elif cds < th_baixo:
            s_wdo, s_winfut = -1, 1
        else:
            s_wdo, s_winfut = 0, 0
        total_wdo += s_wdo
        total_winfut += s_winfut
        self._registrar_detalhe("cap6_fiscal", "CDS_5Y", s_wdo, s_winfut,
                                f"cds={cds}bps", "CDS 5Y Brasil")

        # Campos manuais (resultado_primario, arcabouco, rating)
        for campo in ["resultado_primario_tone", "arcabouco_fiscal", "rating_soberano"]:
            valor = campos.get(campo, "neutro")
            regra = regras.get(campo, {})
            scores = regra.get(str(valor).lower(), {"wdo": 0, "winfut": 0})
            s_wdo = scores.get("wdo", 0)
            s_winfut = scores.get("winfut", 0)
            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe("cap6_fiscal", campo, s_wdo, s_winfut,
                                    str(valor), f"Fiscal {campo}")

        # EMBI proxy via EMB ETF
        pares_auto = cfg.get("pares_automaticos", [])
        for par in pares_auto:
            quote = self._buscar_cotacao(par)
            raw = self._snapshot_d1(quote)
            # EMB caindo = risco-pais piorando = dolar sobe
            s_wdo = -raw  # EMB sobe = risco cai = bom para BRL
            s_winfut = raw
            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe("cap6_fiscal", "EMBI_PROXY", s_wdo, s_winfut,
                                    f"raw={raw}", par.get("descricao", ""))

        self.scores_wdo["fiscal"] = total_wdo
        self.scores_winfut["fiscal"] = total_winfut
        return total_wdo, total_winfut

    # -----------------------------------------------------------------------
    # Capitulo 7 — Forca USD Global
    # -----------------------------------------------------------------------

    def avaliar_forca_usd_global(self) -> tuple[float, float]:
        """Cap. 7: Forca do dolar global e pares emergentes."""
        cfg = self.cfg.get("capitulo_7_forca_usd_global", {})
        pares = cfg.get("pares", [])
        total_wdo = 0.0
        total_winfut = 0.0

        for par in pares:
            quote = self._buscar_cotacao(par)
            raw = self._snapshot_d1(quote)

            direcao_wdo = par.get("score_wdo_direcao", "direto")
            direcao_winfut = par.get("score_winfut_direcao", "direto")

            s_wdo = raw if direcao_wdo == "direto" else -raw
            s_winfut = raw if direcao_winfut == "direto" else -raw

            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe("cap7_usd_global", par["simbolo"], s_wdo, s_winfut,
                                    f"raw={raw}", par.get("descricao", ""))

        self.scores_wdo["usd_global"] = total_wdo
        self.scores_winfut["usd_global"] = total_winfut
        return total_wdo, total_winfut

    # -----------------------------------------------------------------------
    # Capitulo 8 — SMC (simplificado — baseado em preco)
    # -----------------------------------------------------------------------

    def avaliar_smc(self) -> tuple[float, float]:
        """Cap. 8: Smart Money Concepts — H4 context por ativo.

        Cascata de fontes: MT5 → TwelveData H4 → Yahoo D1 (fallback SMC simplificado).
        Quando nenhuma fonte premium disponível, calcula SMC simplificado
        a partir de dados diários Yahoo (swing highs/lows, BOS detection).
        """
        cfg = self.cfg.get("capitulo_8_smc", {})
        total_wdo = 0.0
        total_winfut = 0.0

        for ativo, label_ativo in [("wdo", "WDO"), ("winfut", "WINFUT")]:
            ativo_cfg = cfg.get(ativo, {})
            symbol = ativo_cfg.get("symbol", "USDBRL" if ativo == "wdo" else "WIN$N")
            barras = ativo_cfg.get("barras", 600)
            smc_cfg = {
                "swing_window": ativo_cfg.get("swing_window", 3),
                "poi_distancia_pct": ativo_cfg.get("poi_distancia_pct", 2.0),
            }

            candles = None
            source = "N/A"

            # 1. Tentar MT5
            if self.mt5_disponivel:
                mt5_syms = self.cfg.get("apis", {}).get("metatrader5", {}).get(
                    f"symbols_{ativo}", [symbol])
                for sym in mt5_syms:
                    candles = apis.mt5_candles(sym, "H4", barras)
                    if candles:
                        source = f"MT5:{sym}"
                        break

            # 2. Fallback TwelveData H4
            if not candles and self.twelvedata_key:
                td_map = {"USDBRL": "USD/BRL", "WIN$N": "IBOV"}
                td_sym = td_map.get(symbol, symbol)
                td_data = apis.twelvedata_timeseries(
                    td_sym, interval="4h", outputsize=min(barras, 100),
                    api_key=self.twelvedata_key
                )
                if td_data:
                    candles = td_data
                    source = f"TwelveData:{td_sym}"

            # 3. Fallback Yahoo Finance D1 → SMC simplificado
            if not candles:
                yahoo_map = {"USDBRL": "BRL=X", "WIN$N": "^BVSP"}
                yahoo_sym = yahoo_map.get(symbol, symbol)
                candles = self._yahoo_d1_candles(yahoo_sym)
                if candles:
                    source = f"Yahoo:{yahoo_sym}"

            if not candles:
                self._registrar_detalhe("cap8_smc", f"SMC_{label_ativo}", 0, 0,
                                        "sem_dados", "SMC sem fonte disponível (MT5/TwelveData/Yahoo)")
                continue

            # Analise SMC
            if source.startswith("Yahoo"):
                # SMC simplificado para dados diários
                smc = self._smc_simplificado(candles, smc_cfg)
            else:
                smc = apis.mt5_smc_analysis(candles, smc_cfg)
            score = smc.get("score", 0)

            if ativo == "wdo":
                total_wdo += score
                self._registrar_detalhe("cap8_smc", f"SMC_{label_ativo}",
                                        score, 0, smc.get("detalhes", ""),
                                        f"SMC {label_ativo} via {source}")
            else:
                total_winfut += score
                self._registrar_detalhe("cap8_smc", f"SMC_{label_ativo}",
                                        0, score, smc.get("detalhes", ""),
                                        f"SMC {label_ativo} via {source}")

        self.scores_wdo["smc"] = total_wdo
        self.scores_winfut["smc"] = total_winfut
        return total_wdo, total_winfut

    def _yahoo_d1_candles(self, symbol: str, days: int = 30) -> list[dict] | None:
        """Busca candles D1 via Yahoo Finance para uso em SMC/Momentum."""
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={days}d&interval=1d"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
            result = data.get("chart", {}).get("result", [])
            if not result:
                return None
            indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
            timestamps = result[0].get("timestamp", [])
            if not timestamps:
                return None

            opens = indicators.get("open", [])
            closes = indicators.get("close", [])
            highs = indicators.get("high", [])
            lows = indicators.get("low", [])
            volumes = indicators.get("volume", [])

            candles = []
            for i in range(len(timestamps)):
                if (opens[i] is not None and closes[i] is not None and
                        highs[i] is not None and lows[i] is not None):
                    candles.append({
                        "time": timestamps[i],
                        "open": opens[i],
                        "high": highs[i],
                        "low": lows[i],
                        "close": closes[i],
                        "volume": volumes[i] if volumes and i < len(volumes) else 0,
                    })
            return candles if len(candles) >= 5 else None
        except Exception as e:
            logger.warning("Yahoo D1 candles falhou para %s: %s", symbol, e)
            return None

    def _smc_simplificado(self, candles: list[dict], cfg: dict) -> dict:
        """SMC simplificado usando swing highs/lows e BOS detection.

        Análise de estrutura de mercado (Market Structure) sem order blocks
        complexos. Detecta:
        - Higher Highs / Lower Lows (tendência)
        - Break of Structure (BOS)
        - Change of Character (CHoCH)
        """
        if len(candles) < 10:
            return {"score": 0, "detalhes": "candles insuficientes"}

        window = cfg.get("swing_window", 3)
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        closes = [c["close"] for c in candles]

        # Detectar swing highs e lows
        swing_highs = []
        swing_lows = []
        for i in range(window, len(candles) - window):
            if highs[i] == max(highs[i - window:i + window + 1]):
                swing_highs.append((i, highs[i]))
            if lows[i] == min(lows[i - window:i + window + 1]):
                swing_lows.append((i, lows[i]))

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return {"score": 0, "detalhes": "swing points insuficientes"}

        # Tendência via últimos 3 swing points
        last_highs = [sh[1] for sh in swing_highs[-3:]]
        last_lows = [sl[1] for sl in swing_lows[-3:]]

        hh = all(last_highs[i] > last_highs[i - 1] for i in range(1, len(last_highs)))
        hl = all(last_lows[i] > last_lows[i - 1] for i in range(1, len(last_lows)))
        lh = all(last_highs[i] < last_highs[i - 1] for i in range(1, len(last_highs)))
        ll = all(last_lows[i] < last_lows[i - 1] for i in range(1, len(last_lows)))

        score = 0
        detalhes_parts = []

        # Estrutura bullish: HH + HL
        if hh and hl:
            score += 2
            detalhes_parts.append("HH+HL=bullish")
        elif hh:
            score += 1
            detalhes_parts.append("HH=mod_bullish")
        # Estrutura bearish: LH + LL
        elif ll and lh:
            score -= 2
            detalhes_parts.append("LL+LH=bearish")
        elif ll:
            score -= 1
            detalhes_parts.append("LL=mod_bearish")
        else:
            detalhes_parts.append("range/indecisão")

        # BOS Detection: preço atual vs último swing
        current = closes[-1]
        last_sh = swing_highs[-1][1]
        last_sl = swing_lows[-1][1]

        if current > last_sh:
            score += 1
            detalhes_parts.append(f"BOS_UP(>{last_sh:.2f})")
        elif current < last_sl:
            score -= 1
            detalhes_parts.append(f"BOS_DOWN(<{last_sl:.2f})")

        # Limitar score a [-3, 3]
        score = max(min(score, 3), -3)

        return {
            "score": score,
            "detalhes": ", ".join(detalhes_parts),
            "swing_highs": len(swing_highs),
            "swing_lows": len(swing_lows),
        }

    # -----------------------------------------------------------------------
    # Capitulo 9 — Ajuste Horario (multiplicador)
    # -----------------------------------------------------------------------

    def _obter_multiplicador_sessao(self) -> tuple[float, str]:
        """Cap. 9: Retorna multiplicador e nome da sessao atual."""
        cfg = self.cfg.get("capitulo_9_ajuste_horario", {})
        sessoes = cfg.get("sessoes", {})
        hora_utc = self.now.strftime("%H:%M")

        for nome, sessao in sessoes.items():
            inicio = sessao.get("inicio", "00:00")
            fim = sessao.get("fim", "23:59")
            valor = sessao.get("valor", 1.0)

            if inicio > fim:
                # Cruza meia-noite
                if hora_utc >= inicio or hora_utc <= fim:
                    return valor, nome
            else:
                if inicio <= hora_utc <= fim:
                    return valor, nome

        return 1.0, "sem_ajuste"

    # -----------------------------------------------------------------------
    # Capitulo 10 — Macro BRL
    # -----------------------------------------------------------------------

    def avaliar_macro_brl(self) -> tuple[float, float]:
        """Cap. 10: Dados macro Brasil via BCB SGS + IBGE SIDRA.

        Resolve lacuna crítica: substitui FRED (dados defasados/incompletos)
        por BCB SGS (dados oficiais) + IBGE SIDRA (complementar).
        """
        cfg = self.cfg.get("capitulo_10_macro_brl", {})
        params = cfg.get("params", {})
        threshold = params.get("variacao_threshold_pct", 0.001)
        total_wdo = 0.0
        total_winfut = 0.0

        # ── Busca dados via macro_data_provider (BCB SGS + IBGE) ──
        dados_brl = macro_api.fetch_macro_brl_completo()

        if not dados_brl:
            # Fallback FRED legado
            logger.warning("Cap10: BCB SGS indisponível, tentando FRED legado")
            fred_series = cfg.get("fred_brl_series", [])
            for serie in fred_series:
                fd = _fred_latest(serie["serie"], self.fred_key)
                if fd:
                    dados_brl[serie["titulo"]] = fd

        # ── Regras de scoring por indicador ──
        regras_macro = {
            # id: (invert_wdo, invert_winfut, descricao)
            # IPCA subindo = inflação alta = BCB aperta = BRL forte (curto prazo) mas economia sofre
            "BRL_IPCA":         (True,  True,  "IPCA mensal — inflação pressiona juros"),
            "BRL_IPCA_12M":     (True,  True,  "IPCA 12M — tendência inflacionária"),
            "BRL_IGPM":         (True,  True,  "IGP-M — inflação ao produtor/aluguéis"),
            # Atividade subindo = economia aquecida = BRL forte, bolsa sobe
            "BRL_IBC_BR":       (True,  False, "IBC-Br — proxy do PIB mensal"),
            "BRL_PIB":          (True,  False, "PIB trimestral IBGE"),
            "BRL_PROD_IND":     (True,  False, "Produção industrial mensal"),
            "BRL_VAREJO":       (True,  False, "Vendas no varejo PMC"),
            # Emprego bom = economia forte = BRL forte, bolsa sobe
            "BRL_CAGED":        (True,  False, "CAGED — emprego formal"),
            "BRL_DESEMPREGO":   (False, True,  "Desemprego PNAD — invertido"),
            # Setor externo: superávit = fluxo USD pro BR = BRL forte
            "BRL_BALANCA":      (True,  False, "Balança comercial — superávit = BRL forte"),
            "BRL_IDP":          (True,  False, "IDP — investimento direto = confiança"),
            "BRL_RESERVAS":     (True,  False, "Reservas internacionais — colchão cambial"),
            # Fiscal: déficit = risco = BRL fraco; resultado_primario positivo = bom
            "BRL_RESULTADO_PRI":(True,  False, "Resultado primário — superávit = fiscal sólido"),
            "BRL_DIVIDA_PIB":   (False, True,  "Dívida/PIB — subindo = risco fiscal"),
            # Focus (expectativas): Selic subindo = hawkish, IPCA subindo = pressão
            "BRL_FOCUS_IPCA":   (True,  True,  "Focus IPCA — expectativa inflação"),
            "BRL_FOCUS_SELIC":  (True,  True,  "Focus Selic — expectativa juros"),
            "BRL_FOCUS_PIB":    (True,  False, "Focus PIB — expectativa crescimento"),
            "BRL_FOCUS_CAMBIO": (False, True,  "Focus Câmbio — câmbio subindo = BRL fraco"),
            # Juros
            "BRL_SELIC":        (True,  True,  "Selic Meta — aperto monetário"),
            "BRL_CDI":          (True,  True,  "CDI — custo do dinheiro"),
        }

        for ind_id, (invert_wdo, invert_winfut, desc) in regras_macro.items():
            dados = dados_brl.get(ind_id)
            if not dados:
                self._registrar_detalhe("cap10_macro_brl", ind_id, 0, 0,
                                        "sem_dados", desc)
                continue

            var_pct = dados.get("variacao", 0)

            if abs(var_pct) < threshold:
                raw = 0
            else:
                raw = 1 if var_pct > 0 else -1

            s_wdo = -raw if invert_wdo else raw
            s_winfut = -raw if invert_winfut else raw

            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe("cap10_macro_brl", ind_id, s_wdo, s_winfut,
                                    f"var={dados.get('variacao_pct', 0):.2f}%, "
                                    f"atual={dados['atual']}, ant={dados['anterior']}",
                                    f"{desc} [{dados['source']}]")

        n_ok = sum(1 for ind_id in regras_macro if ind_id in dados_brl)
        n_total = len(regras_macro)
        logger.info("Cap10 Macro BRL: %d/%d indicadores ativos", n_ok, n_total)

        self.scores_wdo["macro_brl"] = total_wdo
        self.scores_winfut["macro_brl"] = total_winfut
        return total_wdo, total_winfut

    # -----------------------------------------------------------------------
    # Capitulo 11 — Macro USD
    # -----------------------------------------------------------------------

    def avaliar_macro_usd(self) -> tuple[float, float]:
        """Cap. 11: Dados macro USA via FRED com séries otimizadas.

        Usa macro_data_provider para garantir cobertura máxima dos
        indicadores econômicos americanos.
        """
        cfg = self.cfg.get("capitulo_11_macro_usd", {})
        params = cfg.get("params", {})
        threshold = params.get("variacao_threshold_pct", 0.001)
        total_wdo = 0.0
        total_winfut = 0.0

        # ── Busca dados via macro_data_provider (FRED otimizado) ──
        dados_usd = macro_api.fetch_macro_usd_completo(self.fred_key)

        # ── Regras de scoring por indicador ──
        regras_macro = {
            # id: (invert_wdo, invert_winfut, descricao)
            # CPI subindo = inflação = Fed hawkish = USD forte
            "USD_CPI":       (False, True,  "CPI urbano — inflação EUA"),
            "USD_CPI_CORE":  (False, True,  "CPI Core — inflação subjacente"),
            # NFP forte = economia boa = USD forte = risk-on (curto prazo)
            "USD_NFP":       (False, True,  "Non-Farm Payrolls — emprego"),
            # Desemprego subindo = economia fraca = USD cai
            "USD_UNEMP":     (True,  False, "Taxa desemprego EUA"),
            # GDP forte = USD forte
            "USD_GDP":       (False, True,  "PIB trimestral EUA"),
            # Retail forte = consumo = USD forte
            "USD_RETAIL":    (False, True,  "Vendas no varejo EUA"),
            # PCE = medida preferida do Fed
            "USD_PCE":       (False, True,  "PCE Price Index — inflação Fed"),
            "USD_PCE_CORE":  (False, True,  "PCE Core — inflação subjacente Fed"),
            # Jobless claims subindo = fraqueza = USD cai
            "USD_CLAIMS":    (True,  False, "Jobless Claims — pedidos seguro-desemprego"),
            # Michigan caindo = consumidor pessimista
            "USD_MICHIGAN":  (False, True,  "Michigan Sentiment — confiança consumidor"),
            # Fed Funds = nível base de juros
            "USD_FED_FUNDS": (False, True,  "Fed Funds Rate — taxa referência"),
        }

        for ind_id, (invert_wdo, invert_winfut, desc) in regras_macro.items():
            dados = dados_usd.get(ind_id)
            if not dados:
                self._registrar_detalhe("cap11_macro_usd", ind_id, 0, 0,
                                        "sem_dados", desc)
                continue

            var_pct = dados.get("variacao", 0)

            if abs(var_pct) < threshold:
                raw = 0
            else:
                raw = 1 if var_pct > 0 else -1

            s_wdo = -raw if invert_wdo else raw
            s_winfut = -raw if invert_winfut else raw

            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe("cap11_macro_usd", ind_id, s_wdo, s_winfut,
                                    f"var={dados.get('variacao_pct', 0):.2f}%, "
                                    f"atual={dados['atual']}, ant={dados['anterior']}",
                                    f"{desc} [{dados['source']}]")

        n_ok = sum(1 for ind_id in regras_macro if ind_id in dados_usd)
        n_total = len(regras_macro)
        logger.info("Cap11 Macro USD: %d/%d indicadores ativos", n_ok, n_total)

        self.scores_wdo["macro_usd"] = total_wdo
        self.scores_winfut["macro_usd"] = total_winfut
        return total_wdo, total_winfut

    # -----------------------------------------------------------------------
    # Capitulo 12 — Exaustao e Momentum (simplificado)
    # -----------------------------------------------------------------------

    def avaliar_exaustao_momentum(self) -> tuple[float, float]:
        """Cap. 12: Indicadores técnicos de exaustão/momentum.

        Cascata: MT5 → TwelveData → AlphaVantage → Yahoo Finance D1.
        Quando Yahoo disponível, calcula RSI/ROC/OBV internamente.
        """
        cfg = self.cfg.get("capitulo_12_exaustao_momentum", {})
        total_wdo = 0.0
        total_winfut = 0.0

        for ativo, label_ativo in [("wdo", "WDO"), ("winfut", "WINFUT")]:
            ativo_cfg = cfg.get(ativo, {})
            symbol = ativo_cfg.get("symbol", "USDBRL" if ativo == "wdo" else "WIN$N")
            barras = ativo_cfg.get("barras", 240)
            obv_lookback = ativo_cfg.get("obv_lookback", 20)

            candles = None
            source = "N/A"

            # 1. Tentar MT5 D1
            if self.mt5_disponivel:
                mt5_syms = self.cfg.get("apis", {}).get("metatrader5", {}).get(
                    f"symbols_{ativo}", [symbol])
                for sym in mt5_syms:
                    candles = apis.mt5_candles(sym, "D1", barras)
                    if candles:
                        source = f"MT5:{sym}"
                        break

            # 2. Fallback TwelveData D1
            if not candles and self.twelvedata_key:
                td_map = {"USDBRL": "USD/BRL", "WIN$N": "IBOV"}
                td_sym = td_map.get(symbol, symbol)
                td_data = apis.twelvedata_timeseries(
                    td_sym, interval="1day", outputsize=min(barras, 100),
                    api_key=self.twelvedata_key
                )
                if td_data:
                    candles = td_data
                    source = f"TwelveData:{td_sym}"

            # 3. Fallback AlphaVantage RSI (só RSI, sem OBV)
            if not candles and self.alphavantage_key:
                av_map = {"USDBRL": "USDBRL", "WIN$N": "^BVSP"}
                av_sym = av_map.get(symbol, symbol)
                rsi_data = apis.alphavantage_rsi(av_sym, api_key=self.alphavantage_key)
                if rsi_data:
                    rsi = rsi_data["atual"]
                    score = 0
                    if rsi > 70:
                        score = -1
                        exaustao = "sobrecomprado"
                    elif rsi < 30:
                        score = 1
                        exaustao = "sobrevendido"
                    else:
                        exaustao = "neutro"

                    if ativo == "wdo":
                        total_wdo += score
                        self._registrar_detalhe("cap12_momentum", f"RSI_{label_ativo}",
                                                score, 0, f"RSI={rsi:.1f}, {exaustao}",
                                                f"AlphaVantage RSI {label_ativo}")
                    else:
                        total_winfut += score
                        self._registrar_detalhe("cap12_momentum", f"RSI_{label_ativo}",
                                                0, score, f"RSI={rsi:.1f}, {exaustao}",
                                                f"AlphaVantage RSI {label_ativo}")
                    continue

            # 4. Fallback Yahoo Finance D1 → Momentum simplificado
            if not candles:
                yahoo_map = {"USDBRL": "BRL=X", "WIN$N": "^BVSP"}
                yahoo_sym = yahoo_map.get(symbol, symbol)
                candles = self._yahoo_d1_candles(yahoo_sym, days=60)
                if candles:
                    source = f"Yahoo:{yahoo_sym}"

            if not candles:
                self._registrar_detalhe("cap12_momentum", f"MOMENTUM_{label_ativo}", 0, 0,
                                        "sem_dados", "Nenhuma fonte disponível")
                continue

            # Análise momentum
            if source.startswith("Yahoo"):
                momentum = self._momentum_simplificado(candles, obv_lookback)
            else:
                momentum = apis.mt5_momentum_analysis(candles, obv_lookback=obv_lookback)
            score = momentum.get("score", 0)

            if ativo == "wdo":
                total_wdo += score
                self._registrar_detalhe("cap12_momentum", f"MOMENTUM_{label_ativo}",
                                        score, 0, momentum.get("detalhes", ""),
                                        f"Momentum {label_ativo} via {source}")
            else:
                total_winfut += score
                self._registrar_detalhe("cap12_momentum", f"MOMENTUM_{label_ativo}",
                                        0, score, momentum.get("detalhes", ""),
                                        f"Momentum {label_ativo} via {source}")

        self.scores_wdo["momentum"] = total_wdo
        self.scores_winfut["momentum"] = total_winfut
        return total_wdo, total_winfut

    def _momentum_simplificado(self, candles: list[dict], obv_lookback: int = 20) -> dict:
        """Momentum simplificado: RSI + Rate of Change + OBV tendency.

        Calcula internamente sem dependência de ta-lib ou pandas-ta.
        """
        if len(candles) < 15:
            return {"score": 0, "detalhes": "candles insuficientes"}

        closes = [c["close"] for c in candles]
        volumes = [c.get("volume", 0) for c in candles]

        # ── RSI 14 ──
        period = 14
        gains = []
        losses = []
        for i in range(1, len(closes)):
            delta = closes[i] - closes[i - 1]
            gains.append(max(delta, 0))
            losses.append(max(-delta, 0))

        if len(gains) < period:
            return {"score": 0, "detalhes": "dados insuficientes para RSI"}

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # ── Rate of Change 10 ──
        roc = ((closes[-1] - closes[-11]) / closes[-11] * 100) if len(closes) > 11 else 0

        # ── OBV Tendency ──
        obv = [0]
        for i in range(1, len(closes)):
            if closes[i] > closes[i - 1]:
                obv.append(obv[-1] + volumes[i])
            elif closes[i] < closes[i - 1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])

        obv_recent = obv[-obv_lookback:] if len(obv) >= obv_lookback else obv
        obv_trend = 1 if obv_recent[-1] > obv_recent[0] else -1 if obv_recent[-1] < obv_recent[0] else 0

        # ── Scoring composto ──
        score = 0
        detalhes = []

        # RSI
        if rsi > 70:
            score -= 1
            detalhes.append(f"RSI={rsi:.1f}(sobrecomprado)")
        elif rsi > 80:
            score -= 2
            detalhes.append(f"RSI={rsi:.1f}(EXTREMO_OC)")
        elif rsi < 30:
            score += 1
            detalhes.append(f"RSI={rsi:.1f}(sobrevendido)")
        elif rsi < 20:
            score += 2
            detalhes.append(f"RSI={rsi:.1f}(EXTREMO_OV)")
        else:
            detalhes.append(f"RSI={rsi:.1f}(neutro)")

        # ROC
        if roc > 5:
            score += 1
            detalhes.append(f"ROC={roc:.1f}%(momentum+)")
        elif roc < -5:
            score -= 1
            detalhes.append(f"ROC={roc:.1f}%(momentum-)")

        # OBV
        if obv_trend != 0:
            detalhes.append(f"OBV={'subindo' if obv_trend > 0 else 'caindo'}")

        score = max(min(score, 3), -3)

        return {
            "score": score,
            "detalhes": ", ".join(detalhes),
            "rsi": round(rsi, 1),
            "roc": round(roc, 2),
            "obv_trend": obv_trend,
        }

    # -----------------------------------------------------------------------
    # Capitulo 13 — Sentimento / COT
    # -----------------------------------------------------------------------

    def avaliar_sentimento(self) -> tuple[float, float]:
        """Cap. 13: Sentimento e posicionamento institucional (CFTC + manual)."""
        cfg = self.cfg.get("capitulo_13_sentimento", {})
        total_wdo = 0.0
        total_winfut = 0.0

        # COT CFTC — BRL Futures
        contract = cfg.get("cot_contract", "BRAZILIAN REAL")
        semanas = cfg.get("cot_semanas", 4)
        cot_data = _cftc_cot(contract, semanas)

        if cot_data and len(cot_data) >= 2:
            try:
                # Net non-commercial
                now_r = cot_data[0]
                prev_r = cot_data[1]
                net_now = int(now_r.get("noncomm_positions_long_all", 0)) - \
                          int(now_r.get("noncomm_positions_short_all", 0))
                net_prev = int(prev_r.get("noncomm_positions_long_all", 0)) - \
                           int(prev_r.get("noncomm_positions_short_all", 0))
                trend = net_now - net_prev

                # COT BRL: net long crescente = BRL forte = WDO cai
                if net_now > 0 and trend > 0:
                    s_wdo, s_winfut = -1, 1
                elif net_now < 0 and trend < 0:
                    s_wdo, s_winfut = 1, -1
                else:
                    s_wdo, s_winfut = 0, 0

                total_wdo += s_wdo
                total_winfut += s_winfut
                self._registrar_detalhe("cap13_sentimento", "COT_BRL", s_wdo, s_winfut,
                                        f"net={net_now}, trend={trend}",
                                        "COT BRL Futures CFTC")

                # Extreme positioning
                threshold_pct = cfg.get("extreme_threshold_pct", 20.0)
                oi = int(now_r.get("open_interest_all", 1))
                change_long = abs(int(now_r.get("change_in_noncomm_long_all", 0)))
                change_short = abs(int(now_r.get("change_in_noncomm_short_all", 0)))
                change_pct = (change_long + change_short) / max(oi, 1) * 100

                if change_pct > threshold_pct:
                    direction = 1 if trend > 0 else -1
                    s_wdo = -direction * 2
                    s_winfut = direction * 2
                    total_wdo += s_wdo
                    total_winfut += s_winfut
                    self._registrar_detalhe("cap13_sentimento", "EXTREME_POS", s_wdo, s_winfut,
                                            f"change={change_pct:.1f}%",
                                            "Extreme positioning alert")

                # Retail contrarian
                retail_th = cfg.get("retail_threshold_pct", 60.0)
                nonrept_long = int(now_r.get("nonrept_positions_long_all", 0))
                nonrept_short = int(now_r.get("nonrept_positions_short_all", 0))
                total_nonrept = nonrept_long + nonrept_short
                if total_nonrept > 0:
                    long_pct = nonrept_long / total_nonrept * 100
                    if long_pct > retail_th:
                        s_wdo, s_winfut = 1, -1  # retail long BRL = contrarian
                    elif long_pct < (100 - retail_th):
                        s_wdo, s_winfut = -1, 1
                    else:
                        s_wdo, s_winfut = 0, 0
                    total_wdo += s_wdo
                    total_winfut += s_winfut
                    self._registrar_detalhe("cap13_sentimento", "RETAIL_CONTRARIAN",
                                            s_wdo, s_winfut,
                                            f"long_pct={long_pct:.1f}%",
                                            "Non-reportable contrarian")
            except (ValueError, KeyError) as e:
                logger.warning("Erro processando COT BRL: %s", e)
        else:
            self._registrar_detalhe("cap13_sentimento", "COT_BRL", 0, 0,
                                    "sem_dados", "CFTC nao retornou dados")

        # Campos manuais
        campos_manuais = cfg.get("campos_manuais", {})
        regras_manuais = cfg.get("regras_manuais", {})
        for campo, valor in campos_manuais.items():
            regra = regras_manuais.get(campo, {})
            scores = regra.get(str(valor).lower(), {"wdo": 0, "winfut": 0})
            s_wdo = scores.get("wdo", 0)
            s_winfut = scores.get("winfut", 0)
            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe("cap13_sentimento", campo, s_wdo, s_winfut,
                                    str(valor), f"Manual: {campo}")

        # Fear & Greed Index (Alternative.me — gratis)
        cfg_fgi = self.cfg.get("apis", {}).get("fear_greed", {})
        if cfg_fgi.get("ativo", True):
            fgi = apis.fear_greed_index()
            if fgi:
                valor_fgi = fgi["value"]
                tendencia_fgi = fgi.get("tendencia", 0)
                classificacao = fgi["classification"]

                # Extreme Fear (<25) = potencial reversao alta = BRL pode se recuperar
                # Extreme Greed (>75) = potencial reversao baixa = complacencia
                if valor_fgi < 25:
                    s_wdo, s_winfut = -1, 1   # Extreme Fear = risk-off extremo, reversal
                elif valor_fgi > 75:
                    s_wdo, s_winfut = 1, -1   # Extreme Greed = complacencia, risco
                elif valor_fgi < 40 and tendencia_fgi < -10:
                    s_wdo, s_winfut = 0, -1   # Fear crescente = pressao EM
                elif valor_fgi > 60 and tendencia_fgi > 10:
                    s_wdo, s_winfut = 0, 1    # Greed crescente = risk-on
                else:
                    s_wdo, s_winfut = 0, 0

                total_wdo += s_wdo
                total_winfut += s_winfut
                self._registrar_detalhe("cap13_sentimento", "FEAR_GREED_INDEX",
                                        s_wdo, s_winfut,
                                        f"valor={valor_fgi}, {classificacao}, tend={tendencia_fgi}",
                                        "Fear & Greed Index (Alternative.me)")

        self.scores_wdo["sentimento"] = total_wdo
        self.scores_winfut["sentimento"] = total_winfut
        return total_wdo, total_winfut

    # -----------------------------------------------------------------------
    # Capitulo 14 — Sazonalidade Macro
    # -----------------------------------------------------------------------

    def avaliar_sazonalidade_macro(self) -> tuple[float, float]:
        """Cap. 14: Sazonalidade macro — calendario fiscal brasileiro."""
        cfg = self.cfg.get("capitulo_14_sazonalidade_macro", {})
        mes = self.now.month
        dia = self.now.day
        total_wdo = 0.0
        total_winfut = 0.0

        # Score mensal
        regras_wdo = cfg.get("regras_mensais_wdo", {})
        regras_winfut = cfg.get("regras_mensais_winfut", {})
        s_wdo = regras_wdo.get(str(mes), 0)
        s_winfut = regras_winfut.get(str(mes), 0)
        total_wdo += s_wdo
        total_winfut += s_winfut
        self._registrar_detalhe("cap14_sazonalidade", "SCORE_MENSAL", s_wdo, s_winfut,
                                f"mes={mes}", "Sazonalidade mensal")

        # Carnaval
        carnaval = cfg.get("carnaval", {})
        if carnaval:
            c_mes = carnaval.get("mes", 2)
            c_ini = carnaval.get("dia_inicio", 14)
            c_fim = carnaval.get("dia_fim", 18)
            if mes == c_mes and c_ini <= dia <= c_fim:
                s_wdo = carnaval.get("score_wdo", -1)
                s_winfut = carnaval.get("score_winfut", -1)
                total_wdo += s_wdo
                total_winfut += s_winfut
                self._registrar_detalhe("cap14_sazonalidade", "CARNAVAL", s_wdo, s_winfut,
                                        f"dia={dia}", "Carnaval — liquidez reduzida")

        self.scores_wdo["sazonalidade_macro"] = total_wdo
        self.scores_winfut["sazonalidade_macro"] = total_winfut
        return total_wdo, total_winfut

    # -----------------------------------------------------------------------
    # Capitulo 15 — Fluxos de Capital
    # -----------------------------------------------------------------------

    def avaliar_fluxos_capital(self) -> tuple[float, float]:
        """Cap. 15: Fluxos de capital e balanca de pagamentos."""
        cfg = self.cfg.get("capitulo_15_fluxos_capital", {})
        total_wdo = 0.0
        total_winfut = 0.0
        threshold = cfg.get("variacao_threshold_pct", 1.0)

        # Trade Balance BR via FRED
        fred_trade = cfg.get("fred_br_trade")
        if fred_trade:
            fd = _fred_latest(fred_trade, self.fred_key)
            if fd:
                atual = fd["atual"]
                anterior = fd["anterior"]
                var_pct = ((atual - anterior) / abs(anterior)) * 100 if anterior else 0
                if var_pct > threshold:
                    s_wdo, s_winfut = -1, 1  # superavit crescente = BRL forte
                elif var_pct < -threshold:
                    s_wdo, s_winfut = 1, -1
                else:
                    s_wdo, s_winfut = 0, 0
                total_wdo += s_wdo
                total_winfut += s_winfut
                self._registrar_detalhe("cap15_fluxos", "BR_TRADE_BAL", s_wdo, s_winfut,
                                        f"var={var_pct:.2f}%", "Balanca Comercial BR FRED")

        # Campos manuais
        campos = cfg.get("campos_manuais", {})
        regras = cfg.get("regras_manuais", {})
        for campo, valor in campos.items():
            regra = regras.get(campo, {})
            scores = regra.get(str(valor).lower(), {"wdo": 0, "winfut": 0})
            s_wdo = scores.get("wdo", 0)
            s_winfut = scores.get("winfut", 0)
            total_wdo += s_wdo
            total_winfut += s_winfut
            self._registrar_detalhe("cap15_fluxos", campo, s_wdo, s_winfut,
                                    str(valor), f"Fluxos: {campo}")

        self.scores_wdo["fluxos"] = total_wdo
        self.scores_winfut["fluxos"] = total_winfut
        return total_wdo, total_winfut

    # -----------------------------------------------------------------------
    # Capitulo 16 — Geopolitica
    # -----------------------------------------------------------------------

    def avaliar_geopolitica(self) -> tuple[float, float]:
        """Cap. 16: Geopolitica e riscos de cauda."""
        cfg = self.cfg.get("capitulo_16_geopolitica", {})
        eventos = cfg.get("eventos", {})
        total_wdo = 0.0
        total_winfut = 0.0

        for nome, evento in eventos.items():
            if evento.get("ativo", False):
                s_wdo = evento.get("score_wdo", 0)
                s_winfut = evento.get("score_winfut", 0)
                total_wdo += s_wdo
                total_winfut += s_winfut
                self._registrar_detalhe("cap16_geopolitica", nome, s_wdo, s_winfut,
                                        "ATIVO", evento.get("descricao", ""))
            else:
                self._registrar_detalhe("cap16_geopolitica", nome, 0, 0,
                                        "inativo", evento.get("descricao", ""))

        self.scores_wdo["geopolitica"] = total_wdo
        self.scores_winfut["geopolitica"] = total_winfut
        return total_wdo, total_winfut

    # -----------------------------------------------------------------------
    # Calendario Economico — Deteccao automatica COPOM/FOMC
    # -----------------------------------------------------------------------

    def avaliar_calendario_economico(self) -> dict:
        """Detecta eventos COPOM/FOMC na semana via ForexFactory/Finnhub.

        Returns:
            dict com copom_semana, fomc_semana, eventos_alto_impacto.
        """
        calendario = {"copom_semana": False, "fomc_semana": False,
                       "copom_fomc_mesma_semana": False,
                       "eventos_br": [], "eventos_us": []}

        # 1. ForexFactory (gratis, sem chave)
        cfg_ff = self.cfg.get("apis", {}).get("forexfactory", {})
        if cfg_ff.get("ativo", True):
            eventos_ff = apis.forexfactory_calendar()
            if eventos_ff:
                filtrado = apis.filtrar_eventos_br_us(eventos_ff)
                copom_fomc = apis.detectar_copom_fomc(eventos_ff)
                calendario.update(copom_fomc)
                calendario["eventos_br"] = filtrado.get("brasil_alto_impacto", [])
                calendario["eventos_us"] = filtrado.get("eua_alto_impacto", [])

        # 2. Finnhub (complementar, com API key)
        if not calendario["copom_semana"] and not calendario["fomc_semana"]:
            cfg_fh = self.cfg.get("apis", {}).get("finnhub", {})
            if cfg_fh.get("ativo", False) and self.finnhub_key:
                now = datetime.now(timezone.utc)
                from_date = now.strftime("%Y-%m-%d")
                to_date = (now + timedelta(days=7)).strftime("%Y-%m-%d")
                eventos_fh = apis.finnhub_calendar(
                    api_key=self.finnhub_key,
                    from_date=from_date,
                    to_date=to_date
                )
                if eventos_fh:
                    copom_fomc = apis.detectar_copom_fomc(eventos_fh)
                    calendario.update(copom_fomc)

        # Registrar detalhes
        n_br = len(calendario.get("eventos_br", []))
        n_us = len(calendario.get("eventos_us", []))
        self._registrar_detalhe("calendario", "COPOM_FOMC",
                                0, 0,
                                f"copom={calendario['copom_semana']}, "
                                f"fomc={calendario['fomc_semana']}, "
                                f"br_alto={n_br}, us_alto={n_us}",
                                "Calendario economico automatico")

        return calendario

    # -----------------------------------------------------------------------
    # Veredito Final
    # -----------------------------------------------------------------------

    def _classificar_veredito(self, score: float, faixas: dict) -> str:
        """Classifica score em veredito textual."""
        if score > faixas.get("strong_buy", {}).get("min", 10):
            return "STRONG_BUY"
        elif score >= faixas.get("buy", {}).get("min", 6):
            return "BUY"
        elif score <= faixas.get("strong_sell", {}).get("max", -10):
            return "STRONG_SELL"
        elif score <= faixas.get("sell", {}).get("max", -5):
            return "SELL"
        return "NEUTRAL"

    def _calcular_confianca(self, score: float, ativo: str) -> float:
        """Calcula confianca ajustada (0-100%).

        Ajustada pela cobertura de dados dos capítulos (REC1 Head Financeiro).
        """
        ajustes = self.cfg.get("veredito", {}).get("ajustes_confianca", {})
        # Base: proporcional ao score
        base = min(abs(score) / 15.0, 1.0) * 100.0

        # Ajuste VIX
        if self.vix_valor and self.vix_valor > 30:
            if ativo == "winfut" and score > 0:
                base = min(base, ajustes.get("vix_max_30_buy_winfut", 0.5) * 100)
            elif ativo == "wdo" and score < 0:
                base = min(base, 50.0)

        # ── Penalização por capítulos sem dados (REC1) ──
        # Contar capítulos que retornaram score 0 por falta de dados
        detalhes_sem_dados = sum(
            1 for d in self.detalhes
            if d.get("valor_raw", "") == "sem_dados"
        )
        total_detalhes = max(len(self.detalhes), 1)
        cobertura = 1.0 - (detalhes_sem_dados / total_detalhes)
        # Fator de cobertura: se 30% dos itens são "sem_dados", confiança cai 30%
        base *= max(cobertura, 0.3)  # Mínimo 30% (nunca zero total)

        return round(base, 1)

    def _aplicar_threshold_confianca(self, veredito: str, confianca: float,
                                      ativo: str) -> tuple[str, str]:
        """Aplica threshold de confiança mínimo (REC5 Head Financeiro).

        Sinais abaixo do threshold são rebaixados para NEUTRAL com nota explicativa.

        Thresholds:
          - BUY/SELL:         ≥ 50% confiança
          - STRONG_BUY/SELL:  ≥ 70% confiança

        Returns:
            (veredito_final, nota_threshold)
        """
        thresholds = self.cfg.get("veredito", {}).get("thresholds_confianca", {
            "buy_sell_min": 50.0,
            "strong_min": 70.0,
        })
        min_buy_sell = thresholds.get("buy_sell_min", 50.0)
        min_strong = thresholds.get("strong_min", 70.0)
        nota = ""

        if veredito in ("STRONG_BUY", "STRONG_SELL"):
            if confianca < min_strong:
                # Rebaixar STRONG para BUY/SELL se >= min_buy_sell
                if confianca >= min_buy_sell:
                    novo = "BUY" if "BUY" in veredito else "SELL"
                    nota = (f"Rebaixado de {veredito} para {novo} — "
                            f"confiança {confianca:.1f}% < threshold {min_strong:.0f}%")
                    veredito = novo
                else:
                    nota = (f"Rebaixado de {veredito} para NEUTRAL — "
                            f"confiança {confianca:.1f}% < threshold {min_buy_sell:.0f}%")
                    veredito = "NEUTRAL"

        elif veredito in ("BUY", "SELL"):
            if confianca < min_buy_sell:
                nota = (f"Rebaixado de {veredito} para NEUTRAL — "
                        f"confiança {confianca:.1f}% < threshold {min_buy_sell:.0f}%")
                veredito = "NEUTRAL"

        return veredito, nota

    def _verificar_veto(self) -> tuple[bool, str]:
        """Verifica condicoes de veto."""
        veto = self.cfg.get("veredito", {}).get("veto", {})

        # VIX critico + S&P caindo
        if self.vix_valor and self.vix_valor > veto.get("vix_critico", 35):
            if self.sp500_var_pct and self.sp500_var_pct < veto.get("sp500_queda_critica_pct", -3.0):
                return True, f"VETO: VIX={self.vix_valor:.1f} + S&P500={self.sp500_var_pct:.1f}%"

        return False, ""

    # -----------------------------------------------------------------------
    # Execucao Principal
    # -----------------------------------------------------------------------

    def executar(self) -> dict:
        """Executa todos os capitulos e retorna resultado completo."""
        logger.info("=== Agente WDO/WINFUT — Inicio da analise ===")
        self.now = datetime.now(timezone.utc)
        self.detalhes = []
        self.scores_wdo = {}
        self.scores_winfut = {}

        # Executar todos os capitulos
        self.avaliar_commodities()
        self.avaliar_risco_global()
        self.avaliar_carry_trade()
        self.avaliar_bcb_policy()
        self.avaliar_fed_policy()
        self.avaliar_risco_fiscal()
        self.avaliar_forca_usd_global()
        self.avaliar_smc()
        self.avaliar_macro_brl()
        self.avaliar_macro_usd()
        self.avaliar_exaustao_momentum()
        self.avaliar_sentimento()
        self.avaliar_sazonalidade_macro()
        self.avaliar_fluxos_capital()
        self.avaliar_geopolitica()

        # Calendario economico automatico (ForexFactory/Finnhub)
        calendario = self.avaliar_calendario_economico()

        # Score bruto
        raw_wdo = sum(self.scores_wdo.values())
        raw_winfut = sum(self.scores_winfut.values())

        # Ajuste horario (Cap. 9)
        mult, sessao = self._obter_multiplicador_sessao()
        adj_wdo = raw_wdo * mult
        adj_winfut = raw_winfut * mult

        self._registrar_detalhe("cap9_horario", "AJUSTE", 0, 0,
                                f"raw_wdo={raw_wdo}, raw_winfut={raw_winfut}, mult={mult}",
                                f"Sessao: {sessao}")

        # Verificar veto
        veto, veto_msg = self._verificar_veto()

        # Veto adicional: COPOM + FOMC mesma semana
        if not veto and calendario.get("copom_fomc_mesma_semana", False):
            veto_cfg = self.cfg.get("veredito", {}).get("veto", {})
            if veto_cfg.get("copom_fomc_mesma_semana", True):
                veto = True
                veto_msg = "VETO: COPOM + FOMC na mesma semana (deteccao automatica)"

        # Veredito
        faixas = self.cfg.get("veredito", {})
        if veto:
            veredito_wdo = "VETO"
            veredito_winfut = "VETO"
        else:
            veredito_wdo = self._classificar_veredito(adj_wdo, faixas.get("faixas_wdo", {}))
            veredito_winfut = self._classificar_veredito(adj_winfut, faixas.get("faixas_winfut", {}))

        confianca_wdo = self._calcular_confianca(adj_wdo, "wdo")
        confianca_winfut = self._calcular_confianca(adj_winfut, "winfut")

        # ── Threshold de confiança mínimo (REC5) ──
        notas_threshold = []
        if not veto:
            veredito_wdo, nota_wdo = self._aplicar_threshold_confianca(
                veredito_wdo, confianca_wdo, "wdo")
            veredito_winfut, nota_winfut = self._aplicar_threshold_confianca(
                veredito_winfut, confianca_winfut, "winfut")
            if nota_wdo:
                notas_threshold.append(f"WDO: {nota_wdo}")
            if nota_winfut:
                notas_threshold.append(f"WINFUT: {nota_winfut}")

        timestamp_ms = int(self.now.timestamp() * 1000)

        resultado = {
            "timestamp": self.now.isoformat(),
            "timestamp_ms": timestamp_ms,
            "wdo": {
                "ativo": "WDO (USDBRL)",
                "score_raw": raw_wdo,
                "score_ajustado": round(adj_wdo, 2),
                "multiplicador_sessao": mult,
                "sessao": sessao,
                "veredito": veredito_wdo,
                "confianca": confianca_wdo,
                "scores_capitulos": dict(self.scores_wdo),
            },
            "winfut": {
                "ativo": "WINFUT (Ibovespa)",
                "score_raw": raw_winfut,
                "score_ajustado": round(adj_winfut, 2),
                "multiplicador_sessao": mult,
                "sessao": sessao,
                "veredito": veredito_winfut,
                "confianca": confianca_winfut,
                "scores_capitulos": dict(self.scores_winfut),
            },
            "veto": veto,
            "veto_msg": veto_msg,
            "vix": self.vix_valor,
            "sp500_var_pct": self.sp500_var_pct,
            "calendario": calendario,
            "detalhes": self.detalhes,
            "threshold_notas": notas_threshold,
            "cobertura_dados": {
                "total_itens": len(self.detalhes),
                "sem_dados": sum(1 for d in self.detalhes if d.get("valor_raw") == "sem_dados"),
                "com_dados": sum(1 for d in self.detalhes if d.get("valor_raw") != "sem_dados"),
            },
        }

        # Persistir no SQLite
        self._persistir_resultado(resultado)

        # Telegram — enviar alerta se configurado
        cfg_tg = self.cfg.get("apis", {}).get("telegram", {})
        if cfg_tg.get("ativo", False):
            try:
                msg = apis.formatar_telegram_score(resultado)
                apis.telegram_enviar(msg, self.telegram_token, self.telegram_chat_id)
            except Exception as e:
                logger.warning("Telegram envio falhou: %s", e)

        # Desconectar MT5 se conectado
        if self.mt5_disponivel:
            apis.mt5_desconectar()
            self.mt5_disponivel = False

        logger.info("=== Agente WDO/WINFUT — Analise concluida ===")
        return resultado

    # -----------------------------------------------------------------------
    # Persistencia
    # -----------------------------------------------------------------------

    def _persistir_resultado(self, resultado: dict):
        """Persiste resultado no banco SQLite."""
        try:
            ts = resultado["timestamp_ms"]
            # WDO
            self.conn.execute("""
                INSERT INTO sinais_wdo_winfut (
                    ativo, timeframe, timestamp_ms, tipo_sinal,
                    score_total, confianca, veredito,
                    score_commodities, score_risco, score_carry,
                    score_bcb, score_fed, score_fiscal,
                    score_usd_global, score_smc, score_sazonalidade_intraday,
                    score_macro_brl, score_macro_usd,
                    score_momentum, score_sentimento,
                    score_sazonalidade_macro, score_fluxos,
                    score_geopolitica,
                    vix_valor, sp500_var_pct,
                    modelo, notas
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "WDO", "D1", ts, "macro_score",
                resultado["wdo"]["score_ajustado"],
                resultado["wdo"]["confianca"],
                resultado["wdo"]["veredito"],
                self.scores_wdo.get("commodities", 0),
                self.scores_wdo.get("risco", 0),
                self.scores_wdo.get("carry", 0),
                self.scores_wdo.get("bcb", 0),
                self.scores_wdo.get("fed", 0),
                self.scores_wdo.get("fiscal", 0),
                self.scores_wdo.get("usd_global", 0),
                self.scores_wdo.get("smc", 0),
                resultado["wdo"]["multiplicador_sessao"],
                self.scores_wdo.get("macro_brl", 0),
                self.scores_wdo.get("macro_usd", 0),
                self.scores_wdo.get("momentum", 0),
                self.scores_wdo.get("sentimento", 0),
                self.scores_wdo.get("sazonalidade_macro", 0),
                self.scores_wdo.get("fluxos", 0),
                self.scores_wdo.get("geopolitica", 0),
                self.vix_valor,
                self.sp500_var_pct,
                "agente_wdo_winfut_v1",
                resultado.get("veto_msg", ""),
            ))

            # WINFUT
            self.conn.execute("""
                INSERT INTO sinais_wdo_winfut (
                    ativo, timeframe, timestamp_ms, tipo_sinal,
                    score_total, confianca, veredito,
                    score_commodities, score_risco, score_carry,
                    score_bcb, score_fed, score_fiscal,
                    score_usd_global, score_smc, score_sazonalidade_intraday,
                    score_macro_brl, score_macro_usd,
                    score_momentum, score_sentimento,
                    score_sazonalidade_macro, score_fluxos,
                    score_geopolitica,
                    vix_valor, sp500_var_pct,
                    modelo, notas
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "WINFUT", "D1", ts, "macro_score",
                resultado["winfut"]["score_ajustado"],
                resultado["winfut"]["confianca"],
                resultado["winfut"]["veredito"],
                self.scores_winfut.get("commodities", 0),
                self.scores_winfut.get("risco", 0),
                self.scores_winfut.get("carry", 0),
                self.scores_winfut.get("bcb", 0),
                self.scores_winfut.get("fed", 0),
                self.scores_winfut.get("fiscal", 0),
                self.scores_winfut.get("usd_global", 0),
                self.scores_winfut.get("smc", 0),
                resultado["winfut"]["multiplicador_sessao"],
                self.scores_winfut.get("macro_brl", 0),
                self.scores_winfut.get("macro_usd", 0),
                self.scores_winfut.get("momentum", 0),
                self.scores_winfut.get("sentimento", 0),
                self.scores_winfut.get("sazonalidade_macro", 0),
                self.scores_winfut.get("fluxos", 0),
                self.scores_winfut.get("geopolitica", 0),
                self.vix_valor,
                self.sp500_var_pct,
                "agente_wdo_winfut_v1",
                resultado.get("veto_msg", ""),
            ))

            # Detalhes
            sinal_id_wdo = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            for det in self.detalhes:
                self.conn.execute("""
                    INSERT INTO detalhes_score (
                        sinal_id, capitulo, componente,
                        score_wdo, score_winfut, valor_raw, descricao
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    sinal_id_wdo, det["capitulo"], det["componente"],
                    det["score_wdo"], det["score_winfut"],
                    det["valor_raw"], det["descricao"],
                ))

            self.conn.commit()
            logger.info("Resultado persistido no SQLite: %s", DB_PATH)
        except Exception as e:
            logger.error("Erro ao persistir resultado: %s", e)

    # -----------------------------------------------------------------------
    # Fechar
    # -----------------------------------------------------------------------

    def fechar(self):
        """Fecha conexao com banco."""
        if self.conn:
            self.conn.close()
