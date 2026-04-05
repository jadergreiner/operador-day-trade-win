"""
Dashboard Stats API - Endpoints REST para visualizacao de metricas.

Responsabilidades:
- Expor StatsQueryService via endpoints GET
- Serializar dataclasses para JSON
- Suportar filtragem por periodo e quantidade
- Expor P&L nao realizado via query param (TODO-6 / BLID-035)

Pipeline:
    StatsQueryService (backend) -> routes/dashboard.py (REST)
    -> Frontend dashboard HTML/JS (consumidor)

Status: Implementacao v1.1 (TODO-6 / BLID-035)
Referencia: docs/BACKLOG.md BLID-035
Agente impactado: INICIAR_AGENTE_RL_5000_FIXED.bat
"""

from typing import Any, Dict, List, Optional

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
async def obter_snapshot(
    pnl_nao_realizado_reais: float = Query(
        default=0.0,
        description=(
            "P&L nao realizado em reais calculado pelo chamador via "
            "Portfolio.calculate_unrealized_pnl() com precos do MT5. "
            "Padrao 0.0 quando dados de mercado nao estiverem disponiveis."
        ),
    ),
) -> JSONResponse:
    """
    Retorna snapshot completo com trades, metricas e status de protecoes.

    O campo ``pnl_nao_realizado_reais`` permite que o cliente informe o
    P&L nao realizado atual das posicoes abertas, calculado com precos
    obtidos do MT5 via ``Portfolio.calculate_unrealized_pnl()``.

    Args:
        pnl_nao_realizado_reais: P&L nao realizado em reais (float,
            padrao=0.0).

    Returns:
        JSONResponse com DashboardDataSnapshot (timestamp, trade_stats,
        metricas_operacionais, protecao_status, trades_recentes,
        pnl_nao_realizado_reais, ultima_atualizacao_precos)
    """
    snapshot: Dict[str, Any] = _servico.obter_snapshot_dashboard(
        pnl_nao_realizado_reais=pnl_nao_realizado_reais,
    ).para_dict()
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
