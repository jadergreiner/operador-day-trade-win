"""
Dashboard Stats API - Endpoints REST para visualizacao de metricas.

Responsabilidades:
- Expor StatsQueryService via endpoints GET
- Serializar dataclasses para JSON
- Suportar filtragem por periodo e quantidade

Pipeline:
    StatsQueryService (backend) -> routes/dashboard.py (REST)
    -> Frontend dashboard HTML/JS (consumidor)

Status: Implementacao v1.0 (16/03/2026)
Referencia: docs/BACKLOG.md TODO (Fase 2 - Frontend & Integration)
Agente impactado: INICIAR_AGENTE_RL_5000_FIXED.bat
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.application.dashboard_stats_server import StatsQueryService

roteador: APIRouter = APIRouter()
_servico: StatsQueryService = StatsQueryService()


@roteador.get(
    "/stats/snapshot",
    summary="Snapshot completo do dashboard",
    response_description="DashboardDataSnapshot serializado em JSON",
)
async def obter_snapshot() -> JSONResponse:
    """
    Retorna snapshot completo com trades, metricas e status de protecoes.

    Returns:
        JSONResponse com DashboardDataSnapshot (timestamp, trade_stats,
        metricas_operacionais, protecao_status, trades_recentes)
    """
    snapshot: Dict[str, Any] = _servico.obter_snapshot_dashboard().para_dict()
    return JSONResponse(content=snapshot)


@roteador.get(
    "/stats/recentes",
    summary="Ultimos N trades fechados",
    response_description="Lista de TradeRecente serializados em JSON",
)
async def obter_recentes(
    quantidade: int = Query(
        default=10, ge=1, le=100, description="Quantidade maxima de trades a retornar"
    ),
) -> JSONResponse:
    """
    Retorna lista dos ultimos N trades fechados para exibicao no dashboard.

    Args:
        quantidade: Numero de trades a retornar (1-100, padrao=10)

    Returns:
        JSONResponse com lista de TradeRecente (ticket, simbolo, direcao,
        pnl_reais, motivo_fechamento, etc.)
    """
    trades: List[Dict[str, Any]] = [
        t.para_dict() for t in _servico.obter_trades_recentes(quantidade=quantidade)
    ]
    return JSONResponse(content=trades)


@roteador.get(
    "/stats/periodo/{periodo}",
    summary="Estatisticas agregadas por periodo",
    response_description="TradeStats serializado em JSON",
)
async def obter_por_periodo(periodo: str) -> JSONResponse:
    """
    Retorna estatisticas agregadas de trades para o periodo informado.

    Args:
        periodo: 'hoje', '7dias' ou '30dias' (qualquer outro usa 'hoje')

    Returns:
        JSONResponse com TradeStats (total_trades, win_rate, pnl_total_reais,
        drawdown_maximo, etc.)
    """
    stats: Dict[str, Any] = _servico.obter_stats_por_periodo(periodo).para_dict()
    return JSONResponse(content=stats)
