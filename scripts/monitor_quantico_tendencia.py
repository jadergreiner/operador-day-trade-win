"""
Monitor Quantico de Tendencia do Dia - WIN$ Mini Indice Brasileiro

Responsabilidades:
- Agregar dados globais (SP500, DXY, ouro, petroleo, juros EUA)
- Coletar dados do Mini Indice via MT5 (se disponivel)
- Calcular tendencia do dia com score ponderado
- Servir JSON via HTTP para o monitor HTML
- Atualizar a cada 60 segundos

Pipeline:
    APIs externas + MT5 -> MacroScoreEngine -> TendenciaCalculator
    -> HTTP JSON -> Monitor HTML

Status: v1.0 (01/04/2026)
Referencia: docs/BACKLOG.md
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Caminho raiz
# ---------------------------------------------------------------------------
ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [QUANTUM] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("monitor_quantico")

# ---------------------------------------------------------------------------
# MT5 e carregado dentro das funcoes (lazy import) — igual ao mt5_adapter.py
# Nao importamos no nivel de modulo para evitar o WARNING no ambiente Linux.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Tentativa de import das bibliotecas de dados externos
# ---------------------------------------------------------------------------
try:
    import yfinance as yf
    _YFINANCE_DISPONIVEL: bool = True
except ImportError:
    _YFINANCE_DISPONIVEL = False
    logger.warning(
        "yfinance nao instalado — dados externos desabilitados. "
        "Execute: pip install yfinance"
    )

try:
    from tradingview_ta import TA_Handler, Interval
    _TV_TA_DISPONIVEL: bool = True
except ImportError:
    _TV_TA_DISPONIVEL = False
    logger.debug(
        "tradingview-ta nao instalado — indicadores tecnicos desabilitados"
    )

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------
PORTA_HTTP = 8765
INTERVALO_ATUALIZACAO = 60  # segundos

# ---------------------------------------------------------------------------
# Limites de sanidade por ativo — precos fora da faixa sao descartados
# Baseado em historico de longo prazo com margem generosa para acomodar
# eventos extremos sem bloquear dados validos.
# ---------------------------------------------------------------------------
LIMITES_SANIDADE: dict[str, tuple[float, float]] = {
    "sp500":        (500.0,     10_000.0),
    "nasdaq":       (1_000.0,   30_000.0),
    "dxy":          (70.0,      130.0),
    "vix":          (8.0,       100.0),
    "ouro":         (500.0,     5_500.0),
    "petroleo_wti": (20.0,      250.0),
    "us10y":        (0.0,       20.0),
    "usd_brl":      (3.0,       12.0),
    "ibov":         (50_000.0,  250_000.0),
}

# Denominador fixo de confianca — apenas os 7 fatores externos
# (WIN$ e sinal bonus local, nao entra no calculo)
_TOTAL_FATORES_EXTERNOS = 7

# Ativos com peso >= 20% — ausencia deles degrada fortemente o score
_ATIVOS_CRITICOS: frozenset[str] = frozenset({"sp500", "dxy"})

# ---------------------------------------------------------------------------
# Mapas de simbolos promovidos a nivel de modulo para testabilidade
# ---------------------------------------------------------------------------
# Mapa yfinance — unica fonte de dados externos (substitui TwelveData e Finnhub)
_MAPA_YFINANCE: dict[str, str] = {
    "sp500":        "^GSPC",    # S&P 500 indice real
    "nasdaq":       "^IXIC",    # Nasdaq Composite
    "dxy":          "DX-Y.NYB", # Dollar Index
    "vix":          "^VIX",     # VIX indice
    "ouro":         "GC=F",     # Ouro futuro continuo
    "petroleo_wti": "CL=F",     # WTI futuro continuo
    "us10y":        "^TNX",     # Treasury 10 anos (yield %)
    "usd_brl":      "BRL=X",    # USD/BRL
    "ibov":         "^BVSP",    # Ibovespa
}

# ---------------------------------------------------------------------------
# Carrega .env — sem dependencia de pydantic ou python-dotenv
# Mesma logica do pydantic_settings: le o arquivo .env da raiz do projeto
# e popula os.environ, entao os.getenv funciona normalmente.
# ---------------------------------------------------------------------------

def _preco_dentro_limites(chave: str, preco: float) -> bool:
    """Retorna True se preco esta dentro dos limites de sanidade configurados."""
    limites = LIMITES_SANIDADE.get(chave)
    if limites is None:
        return True  # sem limites definidos, aceita
    minimo, maximo = limites
    return minimo <= preco <= maximo


def _carregar_dotenv() -> None:
    """Le o arquivo .env da raiz do projeto e injeta em os.environ."""
    env_path = Path(ROOT_DIR) / ".env"
    if not env_path.exists():
        logger.debug(".env nao encontrado em %s", env_path)
        return
    try:
        with open(env_path, encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith("#") or "=" not in linha:
                    continue
                chave, _, valor = linha.partition("=")
                chave = chave.strip()
                valor = valor.strip().strip('"').strip("'")
                # Nao sobrescreve variaveis ja definidas no ambiente do sistema
                if chave and chave not in os.environ:
                    os.environ[chave] = valor
        logger.info(".env carregado de %s", env_path)
    except Exception as exc:
        logger.warning("Erro ao ler .env: %s", exc)


_carregar_dotenv()

# Agora tenta TradingConfig (se pydantic estiver no venv correto)
# Fallback limpo para os.getenv — que agora ja tem o .env carregado
try:
    from config import get_config as _get_config  # type: ignore[import]
    _cfg = _get_config()
    TWELVEDATA_API_KEY: str = getattr(_cfg, "twelvedata_api_key", "") or os.getenv("TWELVEDATA_API_KEY", "")
    ALPHAVANTAGE_API_KEY: str = getattr(_cfg, "alphavantage_api_key", "") or os.getenv("ALPHAVANTAGE_API_KEY", "")
    FINNHUB_API_KEY: str = getattr(_cfg, "finnhub_api_key", "") or os.getenv("FINNHUB_API_KEY", "")
    MT5_LOGIN: int = getattr(_cfg, "mt5_login", 0) or int(os.getenv("MT5_LOGIN", "0") or "0")
    MT5_PASSWORD: str = getattr(_cfg, "mt5_password", "") or os.getenv("MT5_PASSWORD", "")
    MT5_SERVER: str = getattr(_cfg, "mt5_server", "") or os.getenv("MT5_SERVER", "")
    MT5_TERMINAL_PATH: str = getattr(_cfg, "mt5_terminal_path", "") or os.getenv("MT5_TERMINAL_PATH", "")
    logger.info("Configuracao carregada via TradingConfig (conta MT5: %s)", MT5_LOGIN or "nao definida")
except Exception as _cfg_exc:
    logger.debug("TradingConfig indisponivel (%s) — usando .env direto", _cfg_exc)
    TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
    ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
    MT5_LOGIN = int(os.getenv("MT5_LOGIN") or os.getenv("MT5_WINFUT_ACCOUNT", "0") or "0")
    MT5_PASSWORD = os.getenv("MT5_PASSWORD") or os.getenv("MT5_WINFUT_PASSWORD", "")
    MT5_SERVER = os.getenv("MT5_SERVER") or os.getenv("MT5_WINFUT_SERVER", "")
    MT5_TERMINAL_PATH = os.getenv("MT5_TERMINAL_PATH", "")

# Simbolos a monitorar no MT5
# WIN$N e DOL$N sao os contratos continuos — funcionam sem precisar
# trocar o vencimento (WINJ26, WINM26 etc.) a cada rollover
SIMBOLO_WIN = "WIN$N"
SIMBOLO_DOLFUT = "DOL$N"

# ---------------------------------------------------------------------------
# Cache global de dados (atualizado pela thread de coleta)
# ---------------------------------------------------------------------------
_cache_dados: dict[str, Any] = {}
_lock_cache = threading.Lock()


def _buscar_yfinance(chave: str, simbolo: str) -> Optional[dict[str, Any]]:
    """
    Busca cotacao atual via yfinance (Yahoo Finance).

    Usa fast_info para latencia minima (~200ms por ativo). Calcula
    variacao_pct como (preco_atual - abertura) / abertura * 100.

    Args:
        chave: identificador interno do ativo (ex: "sp500") — usado em log.
        simbolo: simbolo Yahoo Finance (ex: "^GSPC").

    Returns:
        Dict com preco/variacao_pct/abertura/max/min/nome, ou None em
        caso de falha, dado ausente ou preco zero.
    """
    if not _YFINANCE_DISPONIVEL:
        return None
    try:
        info = yf.Ticker(simbolo).fast_info
        preco: float = float(info.last_price or 0)
        if preco == 0:
            logger.debug(
                "yfinance %s (%s): preco zero — descartado", chave, simbolo
            )
            return None
        abertura: float = float(info.open or 0)
        variacao_pct: float = 0.0
        if abertura:
            variacao_pct = ((preco - abertura) / abertura) * 100
        return {
            "preco": preco,
            "variacao_pct": round(variacao_pct, 2),
            "abertura": abertura,
            "max": float(info.day_high or 0),
            "min": float(info.day_low or 0),
            "nome": simbolo,
        }
    except Exception as exc:
        logger.debug("yfinance erro %s (%s): %s", chave, simbolo, exc)
    return None


def _buscar_indicadores_tv(
    simbolo_tv: str,
    exchange: str = "BMFBOVESPA",
    screener: str = "brazil",
    intervalo: str = "5m",
) -> Optional[dict[str, Any]]:
    """
    Busca indicadores tecnicos via tradingview-ta (opcional).

    Retorna None silenciosamente se tradingview-ta nao estiver instalado
    ou se a requisicao falhar — nunca propaga excecao para o chamador.

    Args:
        simbolo_tv: simbolo no formato TradingView (ex: "WINCONTFUT").
        exchange: bolsa de valores (ex: "BMFBOVESPA").
        screener: pais/mercado (ex: "brazil").
        intervalo: timeframe como string ("1m", "5m", "15m", "1h", "1d").

    Returns:
        Dict com rsi/macd/recomendacao/sinais ou None em qualquer falha.
    """
    if not _TV_TA_DISPONIVEL:
        return None
    _MAPA_INTERVALO: dict[str, Any] = {
        "1m":  Interval.INTERVAL_1_MINUTE,
        "5m":  Interval.INTERVAL_5_MINUTES,
        "15m": Interval.INTERVAL_15_MINUTES,
        "1h":  Interval.INTERVAL_1_HOUR,
        "1d":  Interval.INTERVAL_1_DAY,
    }
    try:
        handler = TA_Handler(
            symbol=simbolo_tv,
            exchange=exchange,
            screener=screener,
            interval=_MAPA_INTERVALO.get(
                intervalo,
                Interval.INTERVAL_5_MINUTES,
            ),
        )
        analise = handler.get_analysis()
        ind = analise.indicators
        res = analise.summary
        return {
            "rsi": ind.get("RSI"),
            "macd": ind.get("MACD.macd"),
            "macd_signal": ind.get("MACD.signal"),
            "ema_20": ind.get("EMA20"),
            "recomendacao": res.get("RECOMMENDATION"),
            "sinal_buy": res.get("BUY"),
            "sinal_sell": res.get("SELL"),
            "sinal_neutral": res.get("NEUTRAL"),
            "simbolo": simbolo_tv,
            "intervalo": intervalo,
        }
    except Exception as exc:
        logger.debug("tradingview-ta erro %s: %s", simbolo_tv, exc)
    return None


def _buscar_dados_externos() -> tuple[dict[str, Any], list[str], list[str]]:
    """
    Coleta dados globais de mercado via yfinance (Yahoo Finance).

    Usa _MAPA_YFINANCE como unica fonte. Valida cada preco contra
    LIMITES_SANIDADE antes de aceitar.

    Returns:
        Tupla (ativos, ativos_criticos_ausentes, ativos_sanidade_falha).
        - ativos: dict com dados dos ativos coletados e validados
        - ativos_criticos_ausentes: ativos de alto peso (>= 20%) sem dado
        - ativos_sanidade_falha: ativos com preco fora dos limites de sanidade
    """
    ativos: dict[str, Any] = {}
    ativos_sanidade_falha: list[str] = []

    for chave, simbolo in _MAPA_YFINANCE.items():
        dado = _buscar_yfinance(chave, simbolo)
        if dado:
            preco = dado.get("preco", 0)
            if _preco_dentro_limites(chave, preco):
                ativos[chave] = dado
                logger.info(
                    "yfinance OK:   %-16s %s = %.2f (%+.2f%%)",
                    chave, simbolo, preco, dado.get("variacao_pct", 0),
                )
            else:
                ativos_sanidade_falha.append(chave)
                logger.warning(
                    "yfinance SANIDADE FALHOU: %-16s %s = %.2f "
                    "(esperado entre %.1f e %.1f)",
                    chave, simbolo, preco,
                    LIMITES_SANIDADE[chave][0], LIMITES_SANIDADE[chave][1],
                )

    ativos_criticos_ausentes = [a for a in _ATIVOS_CRITICOS if a not in ativos]

    if not ativos:
        logger.warning(
            "Nenhum dado externo coletado — verifique: pip install yfinance"
        )
    else:
        logger.info(
            "Ativos coletados: %d/%d", len(ativos), len(_MAPA_YFINANCE)
        )

    if ativos_criticos_ausentes:
        logger.warning(
            "ATIVOS CRITICOS INDISPONIVEIS (peso alto): %s — "
            "score sera significativamente impreciso",
            ", ".join(ativos_criticos_ausentes),
        )

    return ativos, ativos_criticos_ausentes, ativos_sanidade_falha


# ---------------------------------------------------------------------------
# Coleta de dados via MT5
# Lazy import identico ao padrao do mt5_adapter.py do projeto:
#   - import MetaTrader5 feito DENTRO da funcao
#   - credenciais lidas do .env (MT5_LOGIN, MT5_PASSWORD, MT5_SERVER)
#   - terminal_exe_path usado quando MT5_TERMINAL_PATH esta configurado
# ---------------------------------------------------------------------------

def _conectar_mt5() -> Optional[Any]:
    """
    Conecta ao MT5 com as credenciais do .env e retorna o modulo mt5.
    Retorna None se nao for possivel conectar.
    Lazy import — nao gera WARNING se MT5 nao estiver instalado.
    """
    try:
        import MetaTrader5 as mt5_mod  # noqa: PLC0415 (lazy import intencional)
    except ImportError:
        logger.debug("MetaTrader5 nao instalado — modo sem MT5")
        return None

    try:
        # Inicializa com o path do terminal quando configurado (igual ao
        # mt5_adapter._connect_single), senao deixa o MT5 auto-detectar.
        # Usa Path para normalizar barras no Windows (C:\Program Files\...)
        terminal_ok = False
        if MT5_TERMINAL_PATH:
            terminal_path = Path(MT5_TERMINAL_PATH)
            if terminal_path.is_file():
                terminal_ok = True
                ok = mt5_mod.initialize(path=str(terminal_path))
            else:
                logger.warning(
                    "MT5_TERMINAL_PATH nao encontrado: %s — usando auto-detect",
                    MT5_TERMINAL_PATH,
                )

        if not terminal_ok:
            ok = mt5_mod.initialize()

        if not ok:
            logger.warning("MT5 initialize() falhou: %s", mt5_mod.last_error())
            return None

        # Login explicito com credenciais do .env
        if MT5_LOGIN and MT5_PASSWORD and MT5_SERVER:
            autorizado = mt5_mod.login(
                login=MT5_LOGIN,
                password=MT5_PASSWORD,
                server=MT5_SERVER,
            )
            if not autorizado:
                logger.warning(
                    "MT5 login falhou (conta %s): %s",
                    MT5_LOGIN,
                    mt5_mod.last_error(),
                )
                mt5_mod.shutdown()
                return None

        info = mt5_mod.account_info()
        if info:
            logger.info(
                "MT5 conectado: conta %s | servidor %s | saldo %.2f",
                info.login,
                info.server,
                info.balance,
            )
        return mt5_mod

    except Exception as exc:
        logger.warning("MT5 erro de conexao: %s", exc)
        return None


def _cotacao_mt5(mt5_mod: Any, simbolo: str) -> Optional[dict]:
    """Retorna cotacao atual de um simbolo no MT5."""
    try:
        mt5_mod.symbol_select(simbolo, True)
        info = mt5_mod.symbol_info(simbolo)
        if info is None:
            logger.debug("MT5 simbolo %s nao encontrado", simbolo)
            return None

        # Candles D1 para variacao diaria
        barras = mt5_mod.copy_rates_from_pos(simbolo, mt5_mod.TIMEFRAME_D1, 0, 2)
        variacao_pct = 0.0
        abertura = 0.0
        fechamento_ant = 0.0
        if barras is not None and len(barras) >= 2:
            fechamento_ant = float(barras[-2]["close"])
            abertura = float(barras[-1]["open"])
            if fechamento_ant > 0:
                variacao_pct = (
                    (info.bid - fechamento_ant) / fechamento_ant
                ) * 100

        # Candles M5 para contexto intraday
        barras_m5 = mt5_mod.copy_rates_from_pos(
            simbolo, mt5_mod.TIMEFRAME_M5, 0, 30
        )
        candles_m5 = []
        if barras_m5 is not None:
            for b in barras_m5[-12:]:
                candles_m5.append({
                    "time": int(b["time"]),
                    "open": float(b["open"]),
                    "high": float(b["high"]),
                    "low": float(b["low"]),
                    "close": float(b["close"]),
                    "volume": int(b["tick_volume"]),
                })

        return {
            "simbolo": simbolo,
            "preco": float(info.bid),
            "ask": float(info.ask),
            "variacao_pct": round(variacao_pct, 2),
            "abertura": abertura,
            "fechamento_anterior": fechamento_ant,
            "candles_m5": candles_m5,
            "spread": float(info.ask - info.bid),
        }
    except Exception as exc:
        logger.warning("MT5 cotacao %s erro: %s", simbolo, exc)
    return None


def _dados_mt5() -> dict[str, Any]:
    """Coleta dados do WIN$N e DOL$N via MT5."""
    resultado: dict[str, Any] = {}

    mt5_mod = _conectar_mt5()
    if mt5_mod is None:
        return resultado

    win = _cotacao_mt5(mt5_mod, SIMBOLO_WIN)
    if win:
        resultado["win"] = win

    dol = _cotacao_mt5(mt5_mod, SIMBOLO_DOLFUT)
    if dol:
        resultado["dolfut"] = dol

    # Nao faz shutdown — deixa sessao MT5 aberta para os outros agentes
    # (mesmo comportamento do mt5_adapter_proxy.py)
    return resultado


# ---------------------------------------------------------------------------
# Calculo da Tendencia do Dia
# ---------------------------------------------------------------------------

def _sinal_variacao(variacao_pct: float) -> str:
    """Retorna sinal de alta/baixa baseado na variacao percentual."""
    if variacao_pct > 0.3:
        return "ALTA"
    elif variacao_pct < -0.3:
        return "BAIXA"
    return "NEUTRO"


def _calcular_score_tendencia(ativos: dict, mt5_dados: dict) -> dict[str, Any]:
    """
    Calcula o score de tendencia do dia para o Mini Indice.

    Pesos:
    - SP500 (maior correlacao positiva): 25%
    - Nasdaq (correlacao positiva): 15%
    - DXY - Dolar Index (correlacao negativa com Ibov): 20%
    - USD/BRL (correlacao negativa): 15%
    - VIX (correlacao negativa - medo): 15%
    - Ouro (correlacao positiva moderada): 5%
    - Petroleo WTI (correlacao positiva moderada): 5%

    Score final: -100 a +100
    """
    score = 0.0
    fatores = []

    def _score_ativo(
        chave: str,
        peso: float,
        correlacao_positiva: bool,
        label: str,
    ) -> None:
        nonlocal score
        dado = ativos.get(chave)
        if not dado:
            fatores.append({
                "label": label,
                "variacao": None,
                "contribuicao": 0,
                "sinal": "N/A",
                "peso": peso,
            })
            return

        var = dado.get("variacao_pct", 0)
        # Normaliza: variacao de 1% = 33 pontos de score (max ~3% = 100)
        pontos_brutos = min(abs(var) / 3.0, 1.0) * 100
        direcao = 1 if var > 0 else -1
        if not correlacao_positiva:
            direcao = -direcao

        contribuicao = direcao * pontos_brutos * peso
        score += contribuicao

        sinal_local = _sinal_variacao(var if correlacao_positiva else -var)

        fatores.append({
            "label": label,
            "variacao": round(var, 2),
            "preco": round(dado.get("preco", 0), 2),
            "contribuicao": round(contribuicao, 1),
            "sinal": sinal_local,
            "peso": round(peso * 100),
        })

    _score_ativo("sp500", 0.25, True, "S&P 500")
    _score_ativo("nasdaq", 0.15, True, "Nasdaq")
    _score_ativo("dxy", 0.20, False, "Dolar Index (DXY)")
    _score_ativo("usd_brl", 0.15, False, "USD/BRL")
    _score_ativo("vix", 0.15, False, "VIX (Medo)")
    _score_ativo("ouro", 0.05, True, "Ouro")
    _score_ativo("petroleo_wti", 0.05, True, "Petroleo WTI")

    # Dado local WIN$ do MT5 (bono extra de confianca)
    win_dado = mt5_dados.get("win")
    win_variacao = None
    win_preco = None
    if win_dado:
        win_variacao = win_dado.get("variacao_pct", 0)
        win_preco = win_dado.get("preco", 0)
        # WIN$ influencia diretamente (autocorrelacao intraday)
        peso_win = 0.10
        pontos_win = min(abs(win_variacao) / 2.0, 1.0) * 100
        direcao_win = 1 if win_variacao > 0 else -1
        contrib_win = direcao_win * pontos_win * peso_win
        # Reescala o score para incluir WIN$ (normaliza para -100/+100)
        score = (score * 0.9) + contrib_win
        fatores.append({
            "label": "WIN$ (MT5)",
            "variacao": round(win_variacao, 2),
            "preco": round(win_preco, 0),
            "contribuicao": round(contrib_win, 1),
            "sinal": _sinal_variacao(win_variacao),
            "peso": 10,
        })

    score = max(-100.0, min(100.0, score))

    # Classificacao qualitativa
    if score >= 60:
        tendencia = "FORTEMENTE ALTISTA"
        cor_tendencia = "#00ff88"
        emoji = "🚀"
        mensagem = (
            "Mercado global favoravel. Fluxo de capital tende "
            "ao risco. WIN$ com vies de COMPRA."
        )
    elif score >= 25:
        tendencia = "ALTISTA"
        cor_tendencia = "#44ff66"
        emoji = "📈"
        mensagem = (
            "Contexto externo positivo. Favor para compras, "
            "especialmente em pullbacks."
        )
    elif score >= -25:
        tendencia = "INDEFINIDA / LATERAL"
        cor_tendencia = "#ffcc00"
        emoji = "↔️"
        mensagem = (
            "Forças opostas equilibradas. Operar com cautela, "
            "aguardar confirmacao de direcao."
        )
    elif score >= -60:
        tendencia = "BAIXISTA"
        cor_tendencia = "#ff6644"
        emoji = "📉"
        mensagem = (
            "Contexto externo adverso. Favor para vendas, "
            "evitar compras sem confirmacao."
        )
    else:
        tendencia = "FORTEMENTE BAIXISTA"
        cor_tendencia = "#ff2244"
        emoji = "💥"
        mensagem = (
            "Pressao vendedora global intensa. Evitar compras. "
            "Monitorar kill switch."
        )

    # Confianca baseada nos 7 fatores externos apenas (denominador fixo)
    # WIN$ e sinal bonus local e nao entra no denominador — garante
    # consistencia independente do estado da conexao MT5
    fatores_externos = [f for f in fatores if f.get("label") != "WIN$ (MT5)"]
    ativos_com_dados = sum(
        1 for f in fatores_externos if f.get("variacao") is not None
    )
    confianca_pct = int((ativos_com_dados / _TOTAL_FATORES_EXTERNOS) * 100)

    return {
        "score": round(score, 1),
        "tendencia": tendencia,
        "cor_tendencia": cor_tendencia,
        "emoji": emoji,
        "mensagem": mensagem,
        "confianca_pct": confianca_pct,
        "ativos_com_dados": ativos_com_dados,
        "ativos_externos_total": _TOTAL_FATORES_EXTERNOS,
        "fatores": fatores,
        "win_variacao": win_variacao,
        "win_preco": win_preco,
    }


# ---------------------------------------------------------------------------
# Analise de contexto narrativo
# ---------------------------------------------------------------------------

def _contexto_narrativo(ativos: dict, tendencia_dados: dict) -> str:
    """Gera resumo narrativo do contexto de mercado."""
    partes = []

    sp500 = ativos.get("sp500", {})
    dxy = ativos.get("dxy", {})
    vix = ativos.get("vix", {})
    usd_brl = ativos.get("usd_brl", {})
    ouro = ativos.get("ouro", {})
    petroleo = ativos.get("petroleo_wti", {})

    # EUA
    if sp500.get("variacao_pct") is not None:
        var_sp = sp500["variacao_pct"]
        if var_sp > 0.5:
            partes.append(
                f"Wall Street em alta ({var_sp:+.1f}%) — apetite por risco elevado"
            )
        elif var_sp < -0.5:
            partes.append(
                f"Wall Street em queda ({var_sp:+.1f}%) — aversao a risco"
            )
        else:
            partes.append("Wall Street lateral — sem direcao clara nos EUA")

    # VIX
    if vix.get("preco") is not None:
        v = vix["preco"]
        if v > 25:
            partes.append(f"VIX elevado ({v:.0f}) — mercado em modo de medo")
        elif v > 18:
            partes.append(f"VIX moderado ({v:.0f}) — cautela presente")
        else:
            partes.append(f"VIX baixo ({v:.0f}) — mercado tranquilo")

    # Dolar
    if usd_brl.get("preco") is not None:
        d = usd_brl["preco"]
        var_d = usd_brl.get("variacao_pct", 0)
        if var_d > 0.3:
            partes.append(
                f"Real se desvalorizando (USD/BRL {d:.2f}, {var_d:+.1f}%) — "
                "pressao vendedora no Ibov"
            )
        elif var_d < -0.3:
            partes.append(
                f"Real se valorizando (USD/BRL {d:.2f}, {var_d:+.1f}%) — "
                "suporte ao Ibov"
            )
        else:
            partes.append(f"Dolar/Real estavel ({d:.2f})")

    # Ouro
    if ouro.get("variacao_pct") is not None:
        var_o = ouro["variacao_pct"]
        if abs(var_o) > 0.5:
            sentido = "subindo" if var_o > 0 else "caindo"
            partes.append(
                f"Ouro {sentido} ({var_o:+.1f}%) — sinal de safe-haven"
            )

    # Petroleo
    if petroleo.get("variacao_pct") is not None:
        var_p = petroleo["variacao_pct"]
        if abs(var_p) > 1.0:
            sentido = "em alta" if var_p > 0 else "em queda"
            partes.append(
                f"Petroleo {sentido} ({var_p:+.1f}%) — impacto em Petrobras/Ibov"
            )

    if not partes:
        return (
            "Dados externos indisponiveis. "
            "Verificar conexao e chaves de API no .env"
        )

    return ". ".join(partes) + "."


# ---------------------------------------------------------------------------
# Funcao principal de coleta e calculo
# ---------------------------------------------------------------------------

def _atualizar_dados() -> None:
    """Coleta todos os dados e atualiza o cache global."""
    logger.info("Iniciando coleta de dados...")
    inicio = time.time()

    ativos_externos, ativos_criticos_ausentes, ativos_sanidade_falha = (
        _buscar_dados_externos()
    )
    mt5_dados = _dados_mt5()
    indicadores_tv = _buscar_indicadores_tv(
        simbolo_tv="WINCONTFUT",
        exchange="BMFBOVESPA",
        screener="brazil",
        intervalo="5m",
    )

    tendencia = _calcular_score_tendencia(ativos_externos, mt5_dados)
    narrativa = _contexto_narrativo(ativos_externos, tendencia)

    # Regime macro (baseado no score)
    score = tendencia["score"]
    if score >= 40:
        regime = "FAVORAVEL"
    elif score >= 10:
        regime = "ESTAVEL"
    elif score >= -10:
        regime = "CAUTELOSO"
    elif score >= -40:
        regime = "ALERTA"
    else:
        regime = "CRITICO"

    dados_completos = {
        "timestamp": datetime.now().isoformat(),
        "timestamp_legivel": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "tendencia": tendencia,
        "narrativa": narrativa,
        "regime_macro": regime,
        "ativos": {
            k: {
                "preco": v.get("preco"),
                "variacao_pct": v.get("variacao_pct"),
                "nome": v.get("nome", k),
            }
            for k, v in ativos_externos.items()
        },
        "mt5": {
            "conectado": bool(mt5_dados),
            "win": mt5_dados.get("win"),
            "dolfut": mt5_dados.get("dolfut"),
        },
        "indicadores_tv": indicadores_tv,
        "meta": {
            "tempo_coleta_s": round(time.time() - inicio, 1),
            "yfinance_ativo": _YFINANCE_DISPONIVEL,
            "tradingview_ta_ativo": _TV_TA_DISPONIVEL,
            # Mantidos como noop para nao quebrar .env existente
            "twelvedata_ativo": bool(TWELVEDATA_API_KEY),
            "finnhub_ativo": bool(FINNHUB_API_KEY),
            "mt5_disponivel": bool(MT5_LOGIN),
        },
        "qualidade_dados": {
            "ativos_disponiveis": len(ativos_externos),
            "ativos_total_esperado": len(_MAPA_YFINANCE),
            "ativos_criticos_ausentes": ativos_criticos_ausentes,
            "ativos_sanidade_falha": ativos_sanidade_falha,
            "confianca_score": tendencia["confianca_pct"],
        },
    }

    with _lock_cache:
        _cache_dados.clear()
        _cache_dados.update(dados_completos)

    logger.info(
        "Dados atualizados: score=%.1f tendencia=%s confianca=%d%%",
        tendencia["score"],
        tendencia["tendencia"],
        tendencia["confianca_pct"],
    )


# ---------------------------------------------------------------------------
# Thread de atualizacao periodica
# ---------------------------------------------------------------------------

def _thread_atualizacao() -> None:
    """Roda em background, atualizando dados a cada INTERVALO_ATUALIZACAO s.

    Dorme ANTES da primeira coleta porque main() ja executou _atualizar_dados()
    de forma sincrona — evita segunda chamada imediata a APIs externas e
    esgotamento do rate limit do TwelveData.
    """
    while True:
        time.sleep(INTERVALO_ATUALIZACAO)   # dorme ANTES
        try:
            _atualizar_dados()
        except Exception as exc:
            logger.error("Erro na atualizacao: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# Servidor HTTP
# ---------------------------------------------------------------------------

class MonitorHandler(BaseHTTPRequestHandler):
    """Handler HTTP para servir dados JSON ao monitor HTML."""

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: D401
        """Silencia logs padroes do servidor HTTP."""
        pass

    def _enviar_headers_cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.send_header("Content-Type", "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        """Serve dados JSON ou o arquivo HTML."""
        if self.path in ("/dados", "/dados/"):
            with _lock_cache:
                payload = dict(_cache_dados)
            corpo = json.dumps(payload, ensure_ascii=False, indent=2).encode(
                "utf-8"
            )
            self.send_response(200)
            self._enviar_headers_cors()
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        elif self.path in ("/", "/index.html"):
            # Serve o HTML do monitor
            html_path = Path(__file__).parent.parent / "outputs" / \
                "monitor_quantico.html"
            if html_path.exists():
                corpo = html_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Monitor HTML nao encontrado em outputs/")

        elif self.path == "/status":
            status = {
                "ok": bool(_cache_dados),
                "ultima_atualizacao": _cache_dados.get("timestamp_legivel"),
            }
            corpo = json.dumps(status).encode("utf-8")
            self.send_response(200)
            self._enviar_headers_cors()
            self.end_headers()
            self.wfile.write(corpo)

        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._enviar_headers_cors()
        self.end_headers()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    """Inicializa o monitor quantico."""
    logger.info("=" * 60)
    logger.info("  MONITOR QUANTICO DE TENDENCIA - WIN$ Mini Indice")
    logger.info("=" * 60)
    logger.info("Porta HTTP: %d", PORTA_HTTP)
    logger.info("Intervalo: %ds", INTERVALO_ATUALIZACAO)
    logger.info(
        "APIs: yfinance=%s | tradingview-ta=%s",
        "OK" if _YFINANCE_DISPONIVEL else "NAO INSTALADO",
        "OK" if _TV_TA_DISPONIVEL else "NAO INSTALADO (opcional)",
    )
    logger.info(
        "APIs legado (noop): TwelveData=%s | Finnhub=%s",
        "OK" if TWELVEDATA_API_KEY else "NAO CONFIGURADO",
        "OK" if FINNHUB_API_KEY else "NAO CONFIGURADO",
    )
    logger.info(
        "MT5: conta=%s | servidor=%s | terminal=%s",
        MT5_LOGIN or "NAO CONFIGURADO",
        MT5_SERVER or "NAO CONFIGURADO",
        MT5_TERMINAL_PATH or "auto-detect",
    )
    logger.info("-" * 60)

    # Primeira coleta sincrona antes de abrir o servidor
    logger.info("Coletando dados iniciais...")
    try:
        _atualizar_dados()
    except Exception as exc:
        logger.error("Coleta inicial falhou: %s", exc)

    # Thread de atualizacao periodica
    thread = threading.Thread(target=_thread_atualizacao, daemon=True)
    thread.start()
    logger.info("Thread de atualizacao iniciada (daemon)")

    # Servidor HTTP
    servidor = HTTPServer(("0.0.0.0", PORTA_HTTP), MonitorHandler)
    logger.info(
        "Servidor HTTP ativo em http://localhost:%d/", PORTA_HTTP
    )
    logger.info(
        "Abra outputs/monitor_quantico.html no browser para visualizar"
    )
    logger.info("-" * 60)

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        logger.info("Monitor encerrado pelo usuario")
        servidor.shutdown()


if __name__ == "__main__":
    main()
