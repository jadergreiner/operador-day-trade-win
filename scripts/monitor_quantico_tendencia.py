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
from types import SimpleNamespace
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Caminho raiz
# ---------------------------------------------------------------------------
ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.application.scheduler_promotion_healthcheck import evaluate_status_payload

try:
    from src.application.dashboard_stats_server import (
        StatsQueryService as _StatsQueryService,
    )

    StatsQueryService: Any = _StatsQueryService
    _STATS_DASHBOARD_DISPONIVEL = True
except Exception as exc:  # pragma: no cover - fallback defensivo
    StatsQueryService = None
    _STATS_DASHBOARD_DISPONIVEL = False
    logging.getLogger("monitor_quantico").debug(
        "dashboard_stats_server indisponivel — fechamentos operacionais desabilitados: %s",
        exc,
    )

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
    yf = SimpleNamespace(Ticker=None)
    _YFINANCE_DISPONIVEL = False
    logger.warning(
        "yfinance nao instalado — dados externos desabilitados. "
        "Execute: pip install yfinance"
    )

try:
    from tradingview_ta import Interval, TA_Handler

    _TV_TA_DISPONIVEL: bool = True
except ImportError:
    TA_Handler = None
    Interval = SimpleNamespace(
        INTERVAL_1_MINUTE="1m",
        INTERVAL_5_MINUTES="5m",
        INTERVAL_15_MINUTES="15m",
        INTERVAL_1_HOUR="1h",
        INTERVAL_1_DAY="1d",
    )
    _TV_TA_DISPONIVEL = False
    logger.debug("tradingview-ta nao instalado — indicadores tecnicos desabilitados")

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
    "sp500": (500.0, 10_000.0),
    "nasdaq": (1_000.0, 30_000.0),
    "dxy": (70.0, 130.0),
    "vix": (8.0, 100.0),
    "ouro": (500.0, 5_500.0),
    "petroleo_wti": (20.0, 250.0),
    "us10y": (0.0, 20.0),
    "usd_brl": (3.0, 12.0),
    "ibov": (50_000.0, 250_000.0),
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
    "sp500": "^GSPC",  # S&P 500 indice real
    "nasdaq": "^IXIC",  # Nasdaq Composite
    "dxy": "DX-Y.NYB",  # Dollar Index
    "vix": "^VIX",  # VIX indice
    "ouro": "GC=F",  # Ouro futuro continuo
    "petroleo_wti": "CL=F",  # WTI futuro continuo
    "us10y": "^TNX",  # Treasury 10 anos (yield %)
    "usd_brl": "BRL=X",  # USD/BRL
    "ibov": "^BVSP",  # Ibovespa
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
    from config import get_config as _get_config

    _cfg = _get_config()
    TWELVEDATA_API_KEY: str = getattr(_cfg, "twelvedata_api_key", "") or os.getenv(
        "TWELVEDATA_API_KEY", ""
    )
    ALPHAVANTAGE_API_KEY: str = getattr(_cfg, "alphavantage_api_key", "") or os.getenv(
        "ALPHAVANTAGE_API_KEY", ""
    )
    FINNHUB_API_KEY: str = getattr(_cfg, "finnhub_api_key", "") or os.getenv(
        "FINNHUB_API_KEY", ""
    )
    MT5_LOGIN: int = getattr(_cfg, "mt5_login", 0) or int(
        os.getenv("MT5_LOGIN", "0") or "0"
    )
    MT5_PASSWORD: str = getattr(_cfg, "mt5_password", "") or os.getenv(
        "MT5_PASSWORD", ""
    )
    MT5_SERVER: str = getattr(_cfg, "mt5_server", "") or os.getenv("MT5_SERVER", "")
    MT5_TERMINAL_PATH: str = getattr(_cfg, "mt5_terminal_path", "") or os.getenv(
        "MT5_TERMINAL_PATH", ""
    )
    logger.info(
        "Configuracao carregada via TradingConfig (conta MT5: %s)",
        MT5_LOGIN or "nao definida",
    )
except Exception as _cfg_exc:
    logger.debug("TradingConfig indisponivel (%s) — usando .env direto", _cfg_exc)
    TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
    ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
    FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
    MT5_LOGIN = int(
        os.getenv("MT5_LOGIN") or os.getenv("MT5_WINFUT_ACCOUNT", "0") or "0"
    )
    MT5_PASSWORD = os.getenv("MT5_PASSWORD") or os.getenv("MT5_WINFUT_PASSWORD") or ""
    MT5_SERVER = os.getenv("MT5_SERVER") or os.getenv("MT5_WINFUT_SERVER") or ""
    MT5_TERMINAL_PATH = os.getenv("MT5_TERMINAL_PATH", "")

# Simbolos a monitorar no MT5
# WIN$N e DOL$N sao os contratos continuos — funcionam sem precisar
# trocar o vencimento (WINJ26, WINM26 etc.) a cada rollover
SIMBOLO_WIN = "WIN$N"
SIMBOLO_DOLFUT = "DOL$N"
PROMOTION_GATE_ALLOW_SEM_PROMOCAO_UNTIL = (
    os.getenv("PROMOTION_GATE_ALLOW_SEM_PROMOCAO_UNTIL", "").strip() or None
)
MONITOR_FECHAMENTOS_DIAS = max(
    1,
    int(os.getenv("MONITOR_FECHAMENTOS_DIAS", "7") or "7"),
)
MONITOR_FECHAMENTOS_TOP_MOTIVOS = max(
    1,
    int(os.getenv("MONITOR_FECHAMENTOS_TOP_MOTIVOS", "3") or "3"),
)
MONITOR_FECHAMENTOS_ALERTA_TOTAL = max(
    1,
    int(os.getenv("MONITOR_FECHAMENTOS_ALERTA_TOTAL", "2") or "2"),
)
MONITOR_FECHAMENTOS_CRITICO_TOTAL = max(
    MONITOR_FECHAMENTOS_ALERTA_TOTAL + 1,
    int(os.getenv("MONITOR_FECHAMENTOS_CRITICO_TOTAL", "3") or "3"),
)

# ---------------------------------------------------------------------------
# Cache global de dados (atualizado pela thread de coleta)
# ---------------------------------------------------------------------------
_cache_dados: dict[str, Any] = {}
_lock_cache = threading.Lock()


def _enriquecer_status_promocao(
    payload: dict[str, Any],
    *,
    allow_sem_promocao_until: Optional[str] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Enriquece o payload com tolerância de pre-open e bloqueio efetivo."""
    allow_until = allow_sem_promocao_until or PROMOTION_GATE_ALLOW_SEM_PROMOCAO_UNTIL
    resultado = evaluate_status_payload(
        {
            "scheduler_symbol_promotion": {
                "status": payload.get("status", "sem_promocao"),
                "motivo": payload.get("motivo", ""),
            }
        },
        fail_on_statuses=("reprovado", "sem_promocao"),
        allow_sem_promocao_until=allow_until,
        now=now,
    )
    status = (
        str(payload.get("status", "sem_promocao")).strip().lower() or "sem_promocao"
    )
    janela_tolerancia_ativa = bool(
        status == "sem_promocao" and resultado.ok and allow_until
    )
    bloqueio_efetivo = bool(
        status in {"reprovado", "sem_promocao", "arquivo_invalido", "payload_invalido"}
        and not janela_tolerancia_ativa
        and status != "aprovado"
    )

    payload["motivo"] = resultado.motivo or str(payload.get("motivo", "")).strip()
    payload["allow_sem_promocao_until"] = allow_until
    payload["janela_tolerancia_ativa"] = janela_tolerancia_ativa
    payload["bloqueio_efetivo"] = bloqueio_efetivo
    payload["status_operacional"] = (
        "PRE_OPEN_TOLERADO"
        if janela_tolerancia_ativa
        else "BLOQUEIO_ESTRITO"
        if bloqueio_efetivo
        else "LIBERADO"
    )
    return payload


def _carregar_status_promocao_scheduler(
    outputs_dir: Optional[Path] = None,
    runtime_config_path: Optional[Path] = None,
    allow_sem_promocao_until: Optional[str] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Le status mais recente de promocao de calibracao do scheduler.

    Retorna payload resiliente para monitoramento; nunca propaga excecao.
    """
    outputs_base = outputs_dir or (Path(ROOT_DIR) / "outputs")
    runtime_path = runtime_config_path or (
        Path(ROOT_DIR) / "data" / "scheduler" / "symbol_calibration_runtime.json"
    )
    promotion_files = sorted(outputs_base.glob("scheduler_symbol_promotion_*.json"))
    if not promotion_files:
        return _enriquecer_status_promocao(
            {
                "disponivel": False,
                "status": "sem_promocao",
                "aprovado": False,
                "motivo": "artefato de promocao ausente",
                "runtime_config_presente": runtime_path.exists(),
            },
            allow_sem_promocao_until=allow_sem_promocao_until,
            now=now,
        )

    latest = promotion_files[-1]
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _enriquecer_status_promocao(
            {
                "disponivel": False,
                "status": "arquivo_invalido",
                "aprovado": False,
                "motivo": f"falha ao ler {latest.name}",
                "arquivo": latest.name,
                "runtime_config_presente": runtime_path.exists(),
            },
            allow_sem_promocao_until=allow_sem_promocao_until,
            now=now,
        )
    if not isinstance(payload, dict):
        return _enriquecer_status_promocao(
            {
                "disponivel": False,
                "status": "payload_invalido",
                "aprovado": False,
                "motivo": f"payload nao-objeto em {latest.name}",
                "arquivo": latest.name,
                "runtime_config_presente": runtime_path.exists(),
            },
            allow_sem_promocao_until=allow_sem_promocao_until,
            now=now,
        )
    aprovado = bool(payload.get("aprovado"))
    return _enriquecer_status_promocao(
        {
            "disponivel": True,
            "status": "aprovado" if aprovado else "reprovado",
            "aprovado": aprovado,
            "motivo": str(payload.get("motivo", "")).strip(),
            "timestamp_promocao": payload.get("timestamp_promocao"),
            "source_report": payload.get("source_report"),
            "arquivo": latest.name,
            "runtime_config_presente": runtime_path.exists(),
        },
        allow_sem_promocao_until=allow_sem_promocao_until,
        now=now,
    )


def _carregar_resumo_fechamentos_operacionais(
    dias: int = MONITOR_FECHAMENTOS_DIAS,
) -> dict[str, Any]:
    """Carrega resumo dos fechamentos operacionais do Micro Tendencia.

    Reutiliza `StatsQueryService` como fonte canônica e nunca propaga
    exceção para a UI do monitor.
    """
    payload: dict[str, Any] = {
        "status": "sem_dados",
        "fonte": "sqlite_stats",
        "periodo_dias": int(dias),
        "db_path": None,
        "total_fechamentos": 0,
        "por_origem": {},
        "por_motivo": {},
        "top_motivos": [],
        "origens_presentes": [],
        "fechamentos_recentes": [],
        "motivo": "Sem fechamentos no período monitorado.",
        "ultima_atualizacao": datetime.now().isoformat(),
        "stale": False,
    }

    if not _STATS_DASHBOARD_DISPONIVEL or StatsQueryService is None:
        payload.update(
            {
                "status": "indisponivel",
                "fonte": "modulo_indisponivel",
                "motivo": "StatsQueryService indisponível no ambiente atual.",
                "stale": True,
            }
        )
        return payload

    try:
        db_path = os.getenv("MONITOR_FECHAMENTOS_DB_PATH", "").strip() or None
        service = StatsQueryService(db_path=db_path)
        resumo = service.obter_resumo_fechamentos_por_origem(dias=int(dias))

        if not isinstance(resumo, dict):
            raise ValueError("resumo de fechamentos retornou payload inválido")

        payload.update(resumo)
        total_fechamentos = int(payload.get("total_fechamentos", 0) or 0)
        por_origem = payload.get("por_origem") or {}
        por_motivo = payload.get("por_motivo") or {}

        payload["status"] = "ok" if total_fechamentos > 0 else "sem_dados"
        payload["origens_presentes"] = sorted(str(chave) for chave in por_origem.keys())

        motivos_ordenados: list[dict[str, Any]] = []
        for motivo, dados in por_motivo.items():
            dados_motivo = dados if isinstance(dados, dict) else {}
            motivos_ordenados.append(
                {
                    "motivo": str(motivo),
                    "quantidade": int(dados_motivo.get("quantidade", 0) or 0),
                    "pnl_total": float(dados_motivo.get("pnl_total", 0.0) or 0.0),
                }
            )

        payload["top_motivos"] = sorted(
            motivos_ordenados,
            key=lambda item: item["quantidade"],
            reverse=True,
        )[:MONITOR_FECHAMENTOS_TOP_MOTIVOS]
        payload["motivo"] = (
            f"{total_fechamentos} fechamento(s) consolidados nos últimos {int(dias)} dia(s)."
            if total_fechamentos > 0
            else "Sem fechamentos recentes para consolidar."
        )
        payload["ultima_atualizacao"] = datetime.now().isoformat()
        payload["stale"] = False
        return payload
    except Exception as exc:
        logger.warning(
            "Falha ao carregar resumo de fechamentos operacionais: %s",
            exc,
        )
        payload.update(
            {
                "status": "indisponivel",
                "fonte": "fallback",
                "motivo": f"falha ao ler fechamentos operacionais: {exc}",
                "stale": True,
            }
        )
        return payload


def _carregar_dashboard_operacional() -> dict[str, Any]:
    """Carrega snapshot executivo do dashboard para o Monitor Quântico.

    Reutiliza `StatsQueryService.obter_snapshot_dashboard()` como fonte
    canônica read-only e nunca propaga exceções para a UI.
    """
    payload: dict[str, Any] = {
        "status": "sem_dados",
        "fonte": "sqlite_stats",
        "resumo": "Sem trades recentes consolidados no dashboard.",
        "trade_stats": {
            "total_trades": 0,
            "win_rate": 0.0,
            "pnl_total_reais": 0.0,
            "drawdown_maximo": 0.0,
            "pnl_nao_realizado_reais": 0.0,
        },
        "metricas_operacionais": {
            "profit_factor_bruto": 0.0,
            "sharpe_ratio": 0.0,
            "tempo_posicao_media_minutos": 0.0,
        },
        "protecao_status": {
            "trades_ultima_hora": 0,
            "limite_trades_hora": 0,
            "cooldown_segundos_restantes": 0,
            "total_bloqueios_hora": 0,
            "contador_perda_consecutiva": 0,
            "horario_permite_tradear": True,
            "bloqueado": False,
        },
        "ultima_atualizacao": datetime.now().isoformat(),
    }

    if not _STATS_DASHBOARD_DISPONIVEL or StatsQueryService is None:
        payload.update(
            {
                "status": "indisponivel",
                "fonte": "modulo_indisponivel",
                "resumo": "StatsQueryService indisponível no ambiente atual.",
            }
        )
        return payload

    try:
        db_path = (
            os.getenv("MONITOR_DASHBOARD_DB_PATH", "").strip()
            or os.getenv("MONITOR_FECHAMENTOS_DB_PATH", "").strip()
            or None
        )
        service = StatsQueryService(db_path=db_path)
        snapshot = service.obter_snapshot_dashboard()
        dados_snapshot = (
            snapshot.para_dict() if hasattr(snapshot, "para_dict") else snapshot
        )

        if not isinstance(dados_snapshot, dict):
            raise ValueError("snapshot do dashboard retornou payload inválido")

        trade_stats = dict(dados_snapshot.get("trade_stats") or {})
        metricas = dict(dados_snapshot.get("metricas_operacionais") or {})
        protecao = dict(dados_snapshot.get("protecao_status") or {})

        trades_ultima_hora = int(protecao.get("trades_ultima_hora", 0) or 0)
        limite_trades_hora = int(protecao.get("limite_trades_hora", 0) or 0)
        cooldown_segundos = int(protecao.get("cooldown_segundos_restantes", 0) or 0)
        contador_perdas = int(protecao.get("contador_perda_consecutiva", 0) or 0)
        horario_permite = bool(protecao.get("horario_permite_tradear", True))
        protecao_ativa = bool(
            (limite_trades_hora > 0 and trades_ultima_hora > limite_trades_hora)
            or cooldown_segundos > 0
            or contador_perdas >= 2
            or not horario_permite
        )
        protecao["bloqueado"] = protecao_ativa

        total_trades = int(trade_stats.get("total_trades", 0) or 0)
        pnl_total = float(trade_stats.get("pnl_total_reais", 0.0) or 0.0)
        win_rate = float(trade_stats.get("win_rate", 0.0) or 0.0)
        drawdown = float(trade_stats.get("drawdown_maximo", 0.0) or 0.0)

        status = "alerta" if protecao_ativa else "ok"
        if total_trades == 0 and not protecao_ativa and pnl_total == 0.0:
            status = "sem_dados"

        resumo = (
            f"P&L hoje {pnl_total:+.2f} | win rate {win_rate:.2f}% | "
            f"proteção {'ativa' if protecao_ativa else 'liberada'}."
        )
        if status == "sem_dados":
            resumo = "Sem trades recentes consolidados no dashboard."

        payload.update(
            {
                "status": status,
                "resumo": resumo,
                "trade_stats": trade_stats,
                "metricas_operacionais": metricas,
                "protecao_status": protecao,
                "ultima_atualizacao": dados_snapshot.get("timestamp")
                or datetime.now().isoformat(),
            }
        )

        if status == "alerta":
            logger.info(
                "[DASHBOARD] ALERTA | pnl=%s | win_rate=%.2f | cooldown=%ss | perdas=%s",
                f"{pnl_total:+.2f}",
                win_rate,
                cooldown_segundos,
                contador_perdas,
            )
        else:
            logger.debug(
                "[DASHBOARD] %s | trades=%s | pnl=%s | drawdown=%s",
                status.upper(),
                total_trades,
                f"{pnl_total:+.2f}",
                f"{drawdown:+.2f}",
            )

        return payload
    except Exception as exc:
        logger.warning("Falha ao carregar dashboard operacional: %s", exc)
        payload.update(
            {
                "status": "indisponivel",
                "fonte": "fallback",
                "resumo": f"falha ao ler dashboard operacional: {exc}",
            }
        )
        return payload


def _classificar_saude_operacional(
    promocao: dict[str, Any],
    anomalia_fechamentos: dict[str, Any],
    dashboard_operacional: dict[str, Any],
) -> dict[str, Any]:
    """Consolida um health-check operacional geral para o monitor.

    Regras do BLID-082:
    - `CRITICO`: gate bloqueado, anomalia crítica ou dashboard indisponível
    - `ALERTA`: pre-open tolerado, anomalia alerta ou proteção ativa
    - `OK`: operação liberada e sem alertas relevantes
    """
    bloqueio_promocao = bool(promocao.get("bloqueio_efetivo", False))
    pre_open_tolerado = bool(promocao.get("janela_tolerancia_ativa", False))
    nivel_anomalia = (
        str(anomalia_fechamentos.get("nivel", "OK")).strip().upper() or "OK"
    )
    status_dashboard = (
        str(dashboard_operacional.get("status", "sem_dados")).strip().lower()
        or "sem_dados"
    )
    protecao_status = dashboard_operacional.get("protecao_status") or {}
    protecao_ativa = bool(protecao_status.get("bloqueado", False))

    nivel = "OK"
    motivos: list[str] = []

    if bloqueio_promocao:
        nivel = "CRITICO"
        motivos.append("gate de promoção bloqueado")
    elif pre_open_tolerado:
        nivel = "ALERTA"
        motivos.append("gate em pre-open tolerado")

    if nivel_anomalia == "CRITICO":
        nivel = "CRITICO"
        motivos.append("anomalia crítica nos fechamentos")
    elif nivel_anomalia == "ALERTA" and nivel != "CRITICO":
        nivel = "ALERTA"
        motivos.append("fechamentos exigem atenção")

    if status_dashboard == "indisponivel":
        nivel = "CRITICO"
        motivos.append("dashboard operacional indisponível")
    elif (status_dashboard == "alerta" or protecao_ativa) and nivel != "CRITICO":
        nivel = "ALERTA"
        motivos.append("proteção operacional ativa")

    if not motivos:
        motivos.append("operação monitorada dentro do esperado")

    resumo = "; ".join(dict.fromkeys(motivos)) + "."
    saude = {
        "nivel": nivel,
        "resumo": resumo,
        "bloqueio_promocao": bloqueio_promocao,
        "pre_open_tolerado": pre_open_tolerado,
        "protecao_ativa": protecao_ativa,
        "status_dashboard": status_dashboard,
        "status_fechamentos": nivel_anomalia,
    }

    if nivel == "CRITICO":
        logger.warning("[SAUDE] CRITICO | %s", resumo)
    elif nivel == "ALERTA":
        logger.info("[SAUDE] ALERTA | %s", resumo)

    return saude


def _classificar_anomalia_fechamentos(
    resumo: dict[str, Any],
) -> dict[str, Any]:
    """Classifica o risco operacional dos fechamentos consolidados.

    Heurística inicial do BLID-079:
    - `CRITICO`: resumo indisponível/stale ou 3+ origens de fechamento
    - `ALERTA`: 2 origens presentes ou presença de `OPERADOR`/`MERCADO`
    - `OK`: sem dados suspeitos e operação dentro do esperado
    """
    status = str(resumo.get("status", "sem_dados")).strip().lower() or "sem_dados"
    total_fechamentos = int(resumo.get("total_fechamentos", 0) or 0)
    stale = bool(resumo.get("stale", False))
    origens_brutas = resumo.get("origens_presentes") or []
    if not origens_brutas and isinstance(resumo.get("por_origem"), dict):
        origens_brutas = list((resumo.get("por_origem") or {}).keys())
    origens_presentes = sorted(str(origem).upper() for origem in origens_brutas)
    top_motivos = resumo.get("top_motivos") or []

    motivo_predominante = ""
    quantidade_motivo_predominante = 0
    if top_motivos and isinstance(top_motivos[0], dict):
        motivo_predominante = str(top_motivos[0].get("motivo", "")).strip()
        quantidade_motivo_predominante = int(top_motivos[0].get("quantidade", 0) or 0)

    origens_risco = [
        origem for origem in origens_presentes if origem in {"OPERADOR", "MERCADO"}
    ]
    nivel = "OK"
    resumo_legivel = "Fluxo de fechamentos operacionais dentro do esperado."

    if status == "indisponivel" or stale:
        nivel = "CRITICO"
        resumo_legivel = str(
            resumo.get("motivo") or "Resumo de fechamentos indisponível no momento."
        )
    elif (
        len(origens_presentes) >= 3
        or quantidade_motivo_predominante >= MONITOR_FECHAMENTOS_CRITICO_TOTAL
    ):
        nivel = "CRITICO"
        resumo_legivel = (
            "Múltiplas origens de fechamento detectadas "
            f"({', '.join(origens_presentes) or 'SEM_ORIGEM'})."
        )
    elif (
        len(origens_presentes) >= 2
        or total_fechamentos >= MONITOR_FECHAMENTOS_ALERTA_TOTAL
        or bool(origens_risco)
    ):
        nivel = "ALERTA"
        resumo_legivel = (
            "Fechamentos exigem atenção operacional: "
            f"origens={', '.join(origens_presentes) or 'SEM_ORIGEM'}"
        )
    elif status == "sem_dados":
        resumo_legivel = "Sem fechamentos recentes no período monitorado."

    anomalia = {
        "nivel": nivel,
        "resumo": resumo_legivel,
        "status_origem": status,
        "total_fechamentos": total_fechamentos,
        "origens_presentes": origens_presentes,
        "origens_risco": origens_risco,
        "motivo_predominante": motivo_predominante,
        "quantidade_motivo_predominante": quantidade_motivo_predominante,
        "stale": stale,
    }

    if nivel == "CRITICO":
        logger.warning(
            "[FECHAMENTOS] CRITICO | total=%s | origens=%s | motivo=%s | stale=%s",
            total_fechamentos,
            origens_presentes,
            motivo_predominante or "N/A",
            stale,
        )
    elif nivel == "ALERTA":
        logger.info(
            "[FECHAMENTOS] ALERTA | total=%s | origens=%s | motivo=%s",
            total_fechamentos,
            origens_presentes,
            motivo_predominante or "N/A",
        )

    return anomalia


def _build_status_payload() -> dict[str, Any]:
    """Monta payload resumido para health-check no endpoint /status."""
    promotion = _cache_dados.get("scheduler_symbol_promotion")
    if not isinstance(promotion, dict):
        promotion = _carregar_status_promocao_scheduler()
    else:
        promotion = _enriquecer_status_promocao(dict(promotion))

    fechamentos = _cache_dados.get("fechamentos_por_origem")
    if not isinstance(fechamentos, dict):
        fechamentos = _carregar_resumo_fechamentos_operacionais()

    top_motivos = fechamentos.get("top_motivos") or []
    top_motivo = ""
    if top_motivos and isinstance(top_motivos[0], dict):
        top_motivo = str(top_motivos[0].get("motivo", "")).strip()

    dashboard_operacional = _cache_dados.get("dashboard_operacional")
    if not isinstance(dashboard_operacional, dict):
        dashboard_operacional = _carregar_dashboard_operacional()

    trade_stats_dashboard = dict(dashboard_operacional.get("trade_stats") or {})
    protecao_dashboard = dict(dashboard_operacional.get("protecao_status") or {})
    anomalia = _classificar_anomalia_fechamentos(fechamentos)
    saude_operacional = _classificar_saude_operacional(
        promotion,
        anomalia,
        dashboard_operacional,
    )

    return {
        "ok": bool(_cache_dados),
        "ultima_atualizacao": _cache_dados.get("timestamp_legivel"),
        "scheduler_symbol_promotion": {
            "status": promotion.get("status", "sem_promocao"),
            "aprovado": bool(promotion.get("aprovado", False)),
            "runtime_config_presente": bool(
                promotion.get("runtime_config_presente", False)
            ),
            "motivo": str(promotion.get("motivo", "")).strip(),
            "allow_sem_promocao_until": promotion.get("allow_sem_promocao_until"),
            "janela_tolerancia_ativa": bool(
                promotion.get("janela_tolerancia_ativa", False)
            ),
            "bloqueio_efetivo": bool(promotion.get("bloqueio_efetivo", False)),
        },
        "fechamentos_por_origem": {
            "status": str(fechamentos.get("status", "sem_dados")),
            "total_fechamentos": int(fechamentos.get("total_fechamentos", 0) or 0),
            "top_motivo": top_motivo,
            "origens_presentes": list(fechamentos.get("origens_presentes") or []),
            "stale": bool(fechamentos.get("stale", False)),
        },
        "anomalia_fechamentos": {
            "nivel": anomalia.get("nivel", "OK"),
            "resumo": anomalia.get("resumo", ""),
            "total_fechamentos": int(anomalia.get("total_fechamentos", 0) or 0),
            "origens_presentes": list(anomalia.get("origens_presentes") or []),
            "stale": bool(anomalia.get("stale", False)),
        },
        "dashboard_operacional": {
            "status": str(dashboard_operacional.get("status", "sem_dados")),
            "resumo": str(dashboard_operacional.get("resumo", "")).strip(),
            "pnl_total_reais": float(
                trade_stats_dashboard.get("pnl_total_reais", 0.0) or 0.0
            ),
            "win_rate": float(trade_stats_dashboard.get("win_rate", 0.0) or 0.0),
            "protecao_ativa": bool(protecao_dashboard.get("bloqueado", False)),
            "trades_ultima_hora": int(
                protecao_dashboard.get("trades_ultima_hora", 0) or 0
            ),
        },
        "saude_operacional": saude_operacional,
    }


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
            logger.debug("yfinance %s (%s): preco zero — descartado", chave, simbolo)
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
        "1m": Interval.INTERVAL_1_MINUTE,
        "5m": Interval.INTERVAL_5_MINUTES,
        "15m": Interval.INTERVAL_15_MINUTES,
        "1h": Interval.INTERVAL_1_HOUR,
        "1d": Interval.INTERVAL_1_DAY,
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
                    chave,
                    simbolo,
                    preco,
                    dado.get("variacao_pct", 0),
                )
            else:
                ativos_sanidade_falha.append(chave)
                logger.warning(
                    "yfinance SANIDADE FALHOU: %-16s %s = %.2f "
                    "(esperado entre %.1f e %.1f)",
                    chave,
                    simbolo,
                    preco,
                    LIMITES_SANIDADE[chave][0],
                    LIMITES_SANIDADE[chave][1],
                )

    ativos_criticos_ausentes = [a for a in _ATIVOS_CRITICOS if a not in ativos]

    if not ativos:
        logger.warning("Nenhum dado externo coletado — verifique: pip install yfinance")
    else:
        logger.info("Ativos coletados: %d/%d", len(ativos), len(_MAPA_YFINANCE))

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


def _cotacao_mt5(mt5_mod: Any, simbolo: str) -> Optional[dict[str, Any]]:
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
                variacao_pct = ((info.bid - fechamento_ant) / fechamento_ant) * 100

        # Candles M5 para contexto intraday
        barras_m5 = mt5_mod.copy_rates_from_pos(simbolo, mt5_mod.TIMEFRAME_M5, 0, 30)
        candles_m5 = []
        if barras_m5 is not None:
            for b in barras_m5[-12:]:
                candles_m5.append(
                    {
                        "time": int(b["time"]),
                        "open": float(b["open"]),
                        "high": float(b["high"]),
                        "low": float(b["low"]),
                        "close": float(b["close"]),
                        "volume": int(b["tick_volume"]),
                    }
                )

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


def _calcular_score_tendencia(
    ativos: dict[str, Any], mt5_dados: dict[str, Any]
) -> dict[str, Any]:
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
            fatores.append(
                {
                    "label": label,
                    "variacao": None,
                    "contribuicao": 0,
                    "sinal": "N/A",
                    "peso": peso,
                }
            )
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

        fatores.append(
            {
                "label": label,
                "variacao": round(var, 2),
                "preco": round(dado.get("preco", 0), 2),
                "contribuicao": round(contribuicao, 1),
                "sinal": sinal_local,
                "peso": round(peso * 100),
            }
        )

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
        fatores.append(
            {
                "label": "WIN$ (MT5)",
                "variacao": round(win_variacao, 2),
                "preco": round(win_preco, 0),
                "contribuicao": round(contrib_win, 1),
                "sinal": _sinal_variacao(win_variacao),
                "peso": 10,
            }
        )

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
    ativos_com_dados = sum(1 for f in fatores_externos if f.get("variacao") is not None)
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


def _contexto_narrativo(ativos: dict[str, Any], tendencia_dados: dict[str, Any]) -> str:
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
            partes.append(f"Wall Street em queda ({var_sp:+.1f}%) — aversao a risco")
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
            partes.append(f"Ouro {sentido} ({var_o:+.1f}%) — sinal de safe-haven")

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
            "Dados externos indisponiveis. " "Verificar conexao e chaves de API no .env"
        )

    return ". ".join(partes) + "."


# ---------------------------------------------------------------------------
# Funcao principal de coleta e calculo
# ---------------------------------------------------------------------------


def _atualizar_dados() -> None:
    """Coleta todos os dados e atualiza o cache global."""
    logger.info("Iniciando coleta de dados...")
    inicio = time.time()

    (
        ativos_externos,
        ativos_criticos_ausentes,
        ativos_sanidade_falha,
    ) = _buscar_dados_externos()
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

    fechamentos_operacionais = _carregar_resumo_fechamentos_operacionais()
    anomalia_fechamentos = _classificar_anomalia_fechamentos(fechamentos_operacionais)
    dashboard_operacional = _carregar_dashboard_operacional()
    scheduler_symbol_promotion = _carregar_status_promocao_scheduler()
    saude_operacional = _classificar_saude_operacional(
        scheduler_symbol_promotion,
        anomalia_fechamentos,
        dashboard_operacional,
    )

    dados_completos = {
        "timestamp": datetime.now().isoformat(),
        "timestamp_legivel": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "tendencia": tendencia,
        "narrativa": narrativa,
        "regime_macro": regime,
        "scheduler_symbol_promotion": scheduler_symbol_promotion,
        "fechamentos_por_origem": fechamentos_operacionais,
        "anomalia_fechamentos": anomalia_fechamentos,
        "dashboard_operacional": dashboard_operacional,
        "saude_operacional": saude_operacional,
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
        time.sleep(INTERVALO_ATUALIZACAO)  # dorme ANTES
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
            corpo = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self._enviar_headers_cors()
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        elif self.path in ("/", "/index.html"):
            # Serve o HTML do monitor
            html_path = (
                Path(__file__).parent.parent / "outputs" / "monitor_quantico.html"
            )
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
            status = _build_status_payload()
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
    logger.info("Servidor HTTP ativo em http://localhost:%d/", PORTA_HTTP)
    logger.info("Abra outputs/monitor_quantico.html no browser para visualizar")
    logger.info("-" * 60)

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        logger.info("Monitor encerrado pelo usuario")
        servidor.shutdown()


if __name__ == "__main__":
    main()
