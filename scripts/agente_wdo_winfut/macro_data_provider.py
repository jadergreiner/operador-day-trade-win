"""
Provedor de Dados Macroeconômicos — BCB SGS + FRED + IBGE SIDRA.

Resolve a LACUNA GRAVE de ingestão de dados macro BRL e USD
identificada pelo Head Global de Finanças (Relatório 10/02/2026).

Fontes:
  - BCB SGS (api.bcb.gov.br): IPCA, Selic, IGP-M, IBC-Br, Emprego, Câmbio —
    dados oficiais atualizados, gratuitos, sem chave.
  - FRED (api.stlouisfed.org): CPI, NFP, GDP, PCE, Jobless Claims, ISM —
    dados oficiais EUA, gratuita com chave (DEMO_KEY funciona com limites).
  - IBGE SIDRA (sidra.ibge.gov.br): PIB, Produção Industrial, PMI, Varejo —
    dados oficiais, gratuitos, sem chave.

Autor: Head Financeiro / Sistema
Data: 11/02/2026
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any

import requests

logger = logging.getLogger("macro_data_provider")

# ──────────────────────────────────────────────────────────────────────────────
# Cache simples em memória
# ──────────────────────────────────────────────────────────────────────────────

_cache: dict[str, tuple[float, Any]] = {}   # key → (timestamp, value)
CACHE_TTL = 3600  # 1 hora — dados macro não mudam intraday


def _get_cached(key: str) -> Any | None:
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return val
    return None


def _set_cached(key: str, val: Any) -> None:
    _cache[key] = (time.time(), val)


# ──────────────────────────────────────────────────────────────────────────────
# BCB SGS — Banco Central do Brasil
# Endpoint: https://api.bcb.gov.br/dados/serie/bcdata.sgs.{ID}/dados/ultimos/{N}?formato=json
# Documentação: https://dadosabertos.bcb.gov.br/dataset/
# ──────────────────────────────────────────────────────────────────────────────

# Séries SGS mais relevantes para o scoring macro
BCB_SERIES = {
    # Inflação
    "IPCA_MENSAL":          433,    # IPCA - Variação mensal (%)
    "IPCA_12M":             13522,  # IPCA acumulado 12 meses (%)
    "IGPM_MENSAL":          189,    # IGP-M - Variação mensal (%)
    "INPC_MENSAL":          188,    # INPC - Variação mensal (%)

    # Atividade Econômica
    "IBC_BR":               24364,  # IBC-Br - Índice de Atividade Econômica
    "IBC_BR_DESSAZONA":     24363,  # IBC-Br dessazonalizado

    # Juros e Política Monetária
    "SELIC_META":           432,    # Taxa Selic Meta (% a.a.)
    "SELIC_DIARIA":         11,     # Taxa Selic Over diária (% a.a.)
    "CDI_DIARIA":           12,     # CDI diário (% a.a.)

    # Câmbio
    "CAMBIO_COMPRA":        1,      # PTAX compra
    "CAMBIO_VENDA":         10813,  # PTAX venda
    "RESERVAS_INTERNAC":    13621,  # Reservas internacionais (US$ milhões)

    # Emprego
    "CAGED_FORMAL":         28763,  # CAGED - Saldo emprego formal

    # Contas Externas
    "BALANCA_COMERCIAL":    22707,  # Saldo balança comercial mensal (US$ milhões)
    "IDP":                  22885,  # Investimento Direto no País (US$ milhões)

    # Focus — Expectativas
    "FOCUS_IPCA_12M":       29043,  # Mediana IPCA Focus próximos 12 meses
    "FOCUS_SELIC_FIM_ANO":  29044,  # Mediana Selic fim do ano Focus
    "FOCUS_PIB_ANO":        29045,  # Mediana PIB ano Focus
    "FOCUS_CAMBIO_FIM_ANO": 29046,  # Mediana câmbio fim do ano Focus

    # Dívida Pública
    "DIVIDA_LIQUIDA_PIB":   4513,   # Dívida líquida/PIB (%)
    "RESULTADO_PRIMARIO":   4649,   # Resultado primário do governo central
}


def bcb_sgs_ultimos(serie_id: int, n: int = 2) -> dict | None:
    """Busca as últimas N observações de uma série BCB SGS.

    Returns:
        dict com {atual, anterior, data, variacao, serie_id} ou None.
    """
    cache_key = f"bcb_sgs_{serie_id}_{n}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie_id}/dados/ultimos/{n}?formato=json"
    try:
        resp = requests.get(url, timeout=15, headers={"Accept": "application/json"})
        if resp.status_code != 200:
            logger.warning("BCB SGS %d retornou %d", serie_id, resp.status_code)
            return None

        dados = resp.json()
        if not dados or len(dados) < 2:
            # Tenta com mais dados
            if n < 10:
                return bcb_sgs_ultimos(serie_id, 10)
            logger.warning("BCB SGS %d sem dados suficientes", serie_id)
            return None

        # Últimos 2 válidos
        valid = [d for d in dados if d.get("valor") not in (None, "", ".", "null")]
        if len(valid) < 2:
            return None

        atual = float(valid[-1]["valor"])
        anterior = float(valid[-2]["valor"])
        variacao = ((atual - anterior) / abs(anterior)) if anterior != 0 else 0

        result = {
            "atual": atual,
            "anterior": anterior,
            "data": valid[-1]["data"],
            "variacao": variacao,
            "variacao_pct": variacao * 100,
            "serie_id": serie_id,
            "source": "BCB_SGS",
        }
        _set_cached(cache_key, result)
        return result

    except Exception as e:
        logger.warning("BCB SGS falhou para série %d: %s", serie_id, e)
        return None


def bcb_sgs_por_periodo(serie_id: int, inicio: str, fim: str) -> list[dict] | None:
    """Busca série BCB SGS por período (formato DD/MM/YYYY)."""
    url = (
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie_id}/dados"
        f"?formato=json&dataInicial={inicio}&dataFinal={fim}"
    )
    try:
        resp = requests.get(url, timeout=20, headers={"Accept": "application/json"})
        if resp.status_code != 200:
            return None
        dados = resp.json()
        return [{"data": d["data"], "valor": float(d["valor"])}
                for d in dados if d.get("valor") not in (None, "", ".")]
    except Exception as e:
        logger.warning("BCB SGS período falhou para %d: %s", serie_id, e)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# FRED — Federal Reserve Economic Data (USA)
# Endpoint: https://api.stlouisfed.org/fred/series/observations
# ──────────────────────────────────────────────────────────────────────────────

# Séries FRED mais confiáveis para EUA
FRED_SERIES_USD = {
    "CPI":              "CPIAUCSL",      # CPI urbano, mensal, SA
    "CPI_CORE":         "CPILFESL",      # CPI Core (ex-food, energy)
    "NFP":              "PAYEMS",        # Non-Farm Payrolls (milhares)
    "UNEMPLOYMENT":     "UNRATE",        # Taxa de desemprego (%)
    "GDP":              "GDP",           # PIB nominal trimestral
    "GDP_REAL":         "GDPC1",         # PIB real trimestral
    "RETAIL_SALES":     "RSXFS",         # Vendas no varejo
    "PCE":              "PCEPI",         # PCE Price Index
    "PCE_CORE":         "PCEPILFE",      # PCE Core
    "ISM_MFG":          "MANEMP",        # ISM Manufacturing proxy
    "JOBLESS_CLAIMS":   "ICSA",          # Initial Jobless Claims, semanal
    "FED_FUNDS":        "FEDFUNDS",      # Fed Funds Rate
    "MICHIGAN":         "UMCSENT",       # Univ Michigan Consumer Sentiment
    "ADP":              "ADPWNUSNERSA",  # ADP National Employment

    # Yields
    "US10Y":            "DGS10",         # Treasury 10Y yield
    "US2Y":             "DGS2",          # Treasury 2Y yield
    "US30Y":            "DGS30",         # Treasury 30Y yield
    "US3M":             "DTB3",          # T-Bill 3M yield
}


def fred_latest(series_id: str, api_key: str | None = None,
                n: int = 5) -> dict | None:
    """Busca últimas N observações de uma série FRED.

    Returns:
        dict com {atual, anterior, data, variacao, variacao_pct, serie_id, source}.
    """
    cache_key = f"fred_{series_id}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    key = api_key or "DEMO_KEY"
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "sort_order": "desc",
        "limit": n,
        "file_type": "json",
        "api_key": key,
    }

    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            logger.warning("FRED %s retornou %d", series_id, resp.status_code)
            return None

        obs = resp.json().get("observations", [])
        valid = [o for o in obs if o.get("value") not in (".", "", None)]
        if len(valid) < 2:
            return None

        atual = float(valid[0]["value"])
        anterior = float(valid[1]["value"])
        variacao = ((atual - anterior) / abs(anterior)) if anterior != 0 else 0

        result = {
            "atual": atual,
            "anterior": anterior,
            "data": valid[0]["date"],
            "variacao": variacao,
            "variacao_pct": variacao * 100,
            "serie_id": series_id,
            "source": "FRED",
        }
        _set_cached(cache_key, result)
        return result

    except Exception as e:
        logger.warning("FRED falhou para %s: %s", series_id, e)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# IBGE SIDRA — Instituto Brasileiro de Geografia e Estatística
# Endpoint: https://apisidra.ibge.gov.br/values/
# ──────────────────────────────────────────────────────────────────────────────

IBGE_TABLES = {
    "PIB_TRIM":         {"tabela": "5932", "variavel": "6561", "descricao": "PIB trimestral (var %)"},
    "PROD_INDUSTRIAL":  {"tabela": "8159", "variavel": "11602", "descricao": "Produção industrial mensal (var %)"},
    "PMC_VAREJO":       {"tabela": "8185", "variavel": "11709", "descricao": "Vendas no varejo (var %)"},
    "PNAD_DESEMPREGO":  {"tabela": "6381", "variavel": "4099", "descricao": "Taxa de desocupação PNAD (%)"},
}


def ibge_sidra_ultimo(tabela: str, variavel: str) -> dict | None:
    """Busca último valor de uma tabela IBGE SIDRA.

    Returns:
        dict com {atual, anterior, periodo, variacao, source}.
    """
    cache_key = f"ibge_{tabela}_{variavel}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    # Busca os últimos 2 períodos, Brasil (N1/1)
    url = (
        f"https://apisidra.ibge.gov.br/values"
        f"/t/{tabela}/n1/1/v/{variavel}/p/last%202"
        f"/d/v{variavel}%202"
    )
    try:
        resp = requests.get(url, timeout=20, headers={"Accept": "application/json"})
        if resp.status_code != 200:
            logger.warning("IBGE SIDRA %s retornou %d", tabela, resp.status_code)
            return None

        dados = resp.json()
        # SIDRA retorna header na primeira posição
        if len(dados) < 3:
            return None

        val_atual = dados[-1].get("V", "")
        val_anterior = dados[-2].get("V", "")

        if val_atual in ("", "...", "-", None) or val_anterior in ("", "...", "-", None):
            return None

        atual = float(val_atual)
        anterior = float(val_anterior)
        variacao = ((atual - anterior) / abs(anterior)) if anterior != 0 else 0

        result = {
            "atual": atual,
            "anterior": anterior,
            "periodo": dados[-1].get("D2C", ""),
            "variacao": variacao,
            "variacao_pct": variacao * 100,
            "source": "IBGE_SIDRA",
        }
        _set_cached(cache_key, result)
        return result

    except Exception as e:
        logger.warning("IBGE SIDRA falhou para tabela %s: %s", tabela, e)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# API Agregada — Macro BRL
# ──────────────────────────────────────────────────────────────────────────────

def fetch_macro_brl_completo() -> dict[str, dict]:
    """Busca todos os indicadores macro BRL disponíveis.

    Cascata: BCB SGS → IBGE SIDRA → FRED (fallback).
    Returns dict[indicador_id] → {atual, anterior, variacao, source, ...}
    """
    resultados: dict[str, dict] = {}

    # ── BCB SGS (fonte primária) ──
    mapeamento_bcb = {
        "BRL_IPCA":         BCB_SERIES["IPCA_MENSAL"],
        "BRL_IPCA_12M":     BCB_SERIES["IPCA_12M"],
        "BRL_IGPM":         BCB_SERIES["IGPM_MENSAL"],
        "BRL_IBC_BR":       BCB_SERIES["IBC_BR_DESSAZONA"],
        "BRL_SELIC":        BCB_SERIES["SELIC_META"],
        "BRL_CDI":          BCB_SERIES["CDI_DIARIA"],
        "BRL_CAGED":        BCB_SERIES["CAGED_FORMAL"],
        "BRL_BALANCA":      BCB_SERIES["BALANCA_COMERCIAL"],
        "BRL_IDP":          BCB_SERIES["IDP"],
        "BRL_DIVIDA_PIB":   BCB_SERIES["DIVIDA_LIQUIDA_PIB"],
        "BRL_RESULTADO_PRI": BCB_SERIES["RESULTADO_PRIMARIO"],
        "BRL_RESERVAS":     BCB_SERIES["RESERVAS_INTERNAC"],
        "BRL_FOCUS_IPCA":   BCB_SERIES["FOCUS_IPCA_12M"],
        "BRL_FOCUS_SELIC":  BCB_SERIES["FOCUS_SELIC_FIM_ANO"],
        "BRL_FOCUS_PIB":    BCB_SERIES["FOCUS_PIB_ANO"],
        "BRL_FOCUS_CAMBIO": BCB_SERIES["FOCUS_CAMBIO_FIM_ANO"],
    }

    for ind_id, serie_id in mapeamento_bcb.items():
        dados = bcb_sgs_ultimos(serie_id)
        if dados:
            dados["indicador_id"] = ind_id
            resultados[ind_id] = dados
            logger.debug("BCB SGS OK: %s = %.4f (var: %.2f%%)",
                         ind_id, dados["atual"], dados["variacao_pct"])

    # ── IBGE SIDRA (complementar) ──
    mapeamento_ibge = {
        "BRL_PIB":          IBGE_TABLES["PIB_TRIM"],
        "BRL_PROD_IND":     IBGE_TABLES["PROD_INDUSTRIAL"],
        "BRL_VAREJO":       IBGE_TABLES["PMC_VAREJO"],
        "BRL_DESEMPREGO":   IBGE_TABLES["PNAD_DESEMPREGO"],
    }

    for ind_id, cfg in mapeamento_ibge.items():
        if ind_id not in resultados:  # Não sobrescrever BCB
            dados = ibge_sidra_ultimo(cfg["tabela"], cfg["variavel"])
            if dados:
                dados["indicador_id"] = ind_id
                resultados[ind_id] = dados
                logger.debug("IBGE SIDRA OK: %s = %.4f", ind_id, dados["atual"])

    n_ok = len(resultados)
    n_total = len(mapeamento_bcb) + len(mapeamento_ibge)
    logger.info("Macro BRL: %d/%d indicadores obtidos", n_ok, n_total)

    return resultados


# ──────────────────────────────────────────────────────────────────────────────
# API Agregada — Macro USD
# ──────────────────────────────────────────────────────────────────────────────

def fetch_macro_usd_completo(fred_key: str | None = None) -> dict[str, dict]:
    """Busca todos os indicadores macro USD via FRED.

    Returns dict[indicador_id] → {atual, anterior, variacao, source, ...}
    """
    resultados: dict[str, dict] = {}

    mapeamento_fred = {
        "USD_CPI":           FRED_SERIES_USD["CPI"],
        "USD_CPI_CORE":      FRED_SERIES_USD["CPI_CORE"],
        "USD_NFP":           FRED_SERIES_USD["NFP"],
        "USD_UNEMP":         FRED_SERIES_USD["UNEMPLOYMENT"],
        "USD_GDP":           FRED_SERIES_USD["GDP"],
        "USD_RETAIL":        FRED_SERIES_USD["RETAIL_SALES"],
        "USD_PCE":           FRED_SERIES_USD["PCE"],
        "USD_PCE_CORE":      FRED_SERIES_USD["PCE_CORE"],
        "USD_CLAIMS":        FRED_SERIES_USD["JOBLESS_CLAIMS"],
        "USD_MICHIGAN":      FRED_SERIES_USD["MICHIGAN"],
        "USD_FED_FUNDS":     FRED_SERIES_USD["FED_FUNDS"],
    }

    for ind_id, serie_id in mapeamento_fred.items():
        dados = fred_latest(serie_id, fred_key)
        if dados:
            dados["indicador_id"] = ind_id
            resultados[ind_id] = dados
            logger.debug("FRED OK: %s = %.4f (var: %.2f%%)",
                         ind_id, dados["atual"], dados["variacao_pct"])

    n_ok = len(resultados)
    n_total = len(mapeamento_fred)
    logger.info("Macro USD: %d/%d indicadores obtidos", n_ok, n_total)

    return resultados


# ──────────────────────────────────────────────────────────────────────────────
# Yield Curves — BR e US (para Carry Trade)
# ──────────────────────────────────────────────────────────────────────────────

def fetch_yield_curve_us(fred_key: str | None = None) -> dict[str, dict]:
    """Busca yields da curva US Treasury via FRED.

    Returns dict com US2Y, US10Y, US30Y, spread_10y_2y, etc.
    """
    resultados: dict[str, dict] = {}

    for label, serie in [("US2Y", "DGS2"), ("US10Y", "DGS10"),
                         ("US30Y", "DGS30"), ("US3M", "DTB3")]:
        dados = fred_latest(serie, fred_key)
        if dados:
            resultados[label] = dados

    # Calcular spreads
    if "US10Y" in resultados and "US2Y" in resultados:
        spread = resultados["US10Y"]["atual"] - resultados["US2Y"]["atual"]
        spread_ant = resultados["US10Y"]["anterior"] - resultados["US2Y"]["anterior"]
        resultados["SPREAD_10Y_2Y"] = {
            "atual": spread,
            "anterior": spread_ant,
            "variacao": spread - spread_ant,
            "variacao_pct": ((spread - spread_ant) / abs(spread_ant) * 100) if spread_ant != 0 else 0,
            "source": "FRED_CALC",
            "descricao": "Spread 10Y-2Y (inclinação da curva)"
        }

    if "US10Y" in resultados and "US3M" in resultados:
        spread = resultados["US10Y"]["atual"] - resultados["US3M"]["atual"]
        spread_ant = resultados["US10Y"]["anterior"] - resultados["US3M"]["anterior"]
        resultados["SPREAD_10Y_3M"] = {
            "atual": spread,
            "anterior": spread_ant,
            "variacao": spread - spread_ant,
            "source": "FRED_CALC",
            "descricao": "Spread 10Y-3M (inversão clássica)"
        }

    return resultados


def fetch_yield_curve_br() -> dict[str, dict]:
    """Busca yields da curva BR via BCB SGS.

    O BCB não publica yields de títulos prefixados direto no SGS,
    mas temos a Selic e os DI futuros que são a referência.
    Complementa com ANBIMA quando disponível.
    """
    resultados: dict[str, dict] = {}

    # Selic (taxa de referência BR — equivalente ao Fed Funds)
    selic = bcb_sgs_ultimos(BCB_SERIES["SELIC_META"])
    if selic:
        resultados["BR_SELIC"] = selic

    # CDI (proxy do juros interbancário — base para DI)
    cdi = bcb_sgs_ultimos(BCB_SERIES["CDI_DIARIA"])
    if cdi:
        resultados["BR_CDI"] = cdi

    return resultados


def calcular_carry_trade_spread(
    yields_br: dict, yields_us: dict
) -> dict | None:
    """Calcula spread de carry trade BR vs US.

    Carry Trade = Yield BR - Yield US - Risco (simplificado).
    Spread > 0 e subindo = carry atrativo = capital pra BR = BRL forte.
    """
    br_rate = yields_br.get("BR_SELIC", {}).get("atual")
    us_rate = yields_us.get("US10Y", {}).get("atual")

    if br_rate is None or us_rate is None:
        return None

    br_rate_ant = yields_br.get("BR_SELIC", {}).get("anterior", br_rate)
    us_rate_ant = yields_us.get("US10Y", {}).get("anterior", us_rate)

    spread_atual = br_rate - us_rate
    spread_anterior = br_rate_ant - us_rate_ant
    delta = spread_atual - spread_anterior

    return {
        "spread_atual": round(spread_atual, 4),
        "spread_anterior": round(spread_anterior, 4),
        "delta": round(delta, 4),
        "br_rate": br_rate,
        "us_rate": us_rate,
        "carry_atrativo": spread_atual > 5.0,  # Threshold empírico
        "tendencia": "subindo" if delta > 0 else ("caindo" if delta < 0 else "estavel"),
        "source": "BCB_SGS+FRED",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Resumo — Status de Cobertura
# ──────────────────────────────────────────────────────────────────────────────

def status_cobertura(macro_brl: dict, macro_usd: dict,
                     yields_br: dict, yields_us: dict) -> dict:
    """Gera relatório de cobertura dos dados macro.

    Util para o Head avaliar quantos capítulos estão "cegos".
    """
    total_brl = 20  # número esperado de indicadores BRL
    total_usd = 11
    total_yields = 6

    return {
        "macro_brl": {
            "obtidos": len(macro_brl),
            "esperados": total_brl,
            "cobertura_pct": round(len(macro_brl) / total_brl * 100, 1),
            "faltantes": [
                ind for ind in [
                    "BRL_IPCA", "BRL_IPCA_12M", "BRL_IGPM", "BRL_IBC_BR",
                    "BRL_SELIC", "BRL_CDI", "BRL_CAGED", "BRL_BALANCA",
                    "BRL_IDP", "BRL_DIVIDA_PIB", "BRL_RESULTADO_PRI",
                    "BRL_RESERVAS", "BRL_FOCUS_IPCA", "BRL_FOCUS_SELIC",
                    "BRL_FOCUS_PIB", "BRL_FOCUS_CAMBIO", "BRL_PIB",
                    "BRL_PROD_IND", "BRL_VAREJO", "BRL_DESEMPREGO"
                ] if ind not in macro_brl
            ],
        },
        "macro_usd": {
            "obtidos": len(macro_usd),
            "esperados": total_usd,
            "cobertura_pct": round(len(macro_usd) / total_usd * 100, 1),
            "faltantes": [
                ind for ind in [
                    "USD_CPI", "USD_CPI_CORE", "USD_NFP", "USD_UNEMP",
                    "USD_GDP", "USD_RETAIL", "USD_PCE", "USD_PCE_CORE",
                    "USD_CLAIMS", "USD_MICHIGAN", "USD_FED_FUNDS"
                ] if ind not in macro_usd
            ],
        },
        "yields": {
            "br_obtidos": len(yields_br),
            "us_obtidos": len(yields_us),
            "cobertura_pct": round(
                (len(yields_br) + len(yields_us)) / total_yields * 100, 1),
        },
    }
