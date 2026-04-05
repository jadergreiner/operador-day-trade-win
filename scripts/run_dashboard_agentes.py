"""BLID-040: Backend FastAPI para o Dashboard Unificado dos Agentes RL.

Endpoints:
    GET /         → redireciona para /dashboard
    GET /dashboard → HTML do dashboard (FileResponse)
    GET /status   → DashboardStatusPayload em JSON
    GET /metricas → DashboardMetricasPayload em JSON
    GET /trades   → DashboardTradesPayload em JSON
    GET /equity   → DashboardEquityPayload em JSON

Porta: 8010 (exclusiva para o dashboard de agentes RL)

Uso:
    python scripts/run_dashboard_agentes.py

ADR: ADR-001 (SQLite direto), ADR-012 (magic numbers), ADR-017 (lookback 7d),
     ADR-023 (banco ausente -> HTTP 200 com payload zerado)
"""
from __future__ import annotations

import dataclasses
import logging
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

# Adicionar raiz do projeto ao sys.path para importacoes relativas
_RAIZ_PROJETO = Path(__file__).resolve().parent.parent
if str(_RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(_RAIZ_PROJETO))

from src.application.services.dashboard_agentes_service import (  # noqa: E402
    DashboardAgentesService,
)

# ---------------------------------------------------------------------------
# Configuracao de logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Instancia do service e da aplicacao FastAPI
# ---------------------------------------------------------------------------

_svc = DashboardAgentesService()

app = FastAPI(
    title="Dashboard Agentes RL",
    description="Dashboard unificado de monitoramento dos agentes RL (BLID-040)",
    version="1.0.0",
)

_TEMPLATE_PATH = _RAIZ_PROJETO / "templates" / "dashboard_agentes.html"

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    """Redirecionar raiz para /dashboard."""
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", include_in_schema=False)
def dashboard() -> FileResponse:
    """Servir o HTML do dashboard de agentes RL.

    Returns:
        FileResponse com o template HTML do dashboard
    """
    return FileResponse(str(_TEMPLATE_PATH), media_type="text/html")


@app.get("/status")
def status() -> JSONResponse:
    """Retornar status atual dos agentes RL.

    Calcula trades_hoje, trades_abertas, pnl_hoje e win_rate por agente.
    Banco ausente retorna payload zerado com HTTP 200 (ADR-023).

    Returns:
        JSON com DashboardStatusPayload
    """
    payload = _svc.obter_status()
    return JSONResponse(content=dataclasses.asdict(payload))


@app.get("/metricas")
def metricas() -> JSONResponse:
    """Retornar metricas dos agentes RL nos ultimos 7 dias.

    Calcula profit_factor, sharpe_ratio, drawdown_maximo e win_rate_7d.
    Banco ausente retorna payload zerado com HTTP 200 (ADR-023).

    Returns:
        JSON com DashboardMetricasPayload
    """
    payload = _svc.obter_metricas()
    return JSONResponse(content=dataclasses.asdict(payload))


@app.get("/trades")
def trades() -> JSONResponse:
    """Retornar lista dos ultimos trades de cada agente (max 10 por agente).

    Banco ausente retorna lista vazia com HTTP 200 (ADR-023).

    Returns:
        JSON com DashboardTradesPayload
    """
    payload = _svc.obter_trades()
    return JSONResponse(content=dataclasses.asdict(payload))


@app.get("/equity")
def equity() -> JSONResponse:
    """Retornar equity curve diaria dos ultimos 7 dias.

    Banco ausente retorna serie vazia com HTTP 200 (ADR-023).

    Returns:
        JSON com DashboardEquityPayload
    """
    payload = _svc.obter_equity()
    return JSONResponse(content=dataclasses.asdict(payload))


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _log.info("Iniciando Dashboard Agentes RL na porta 8010...")
    uvicorn.run(
        "run_dashboard_agentes:app",
        host="0.0.0.0",
        port=8010,
        reload=False,
        log_level="info",
    )
