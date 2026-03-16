"""
Testes unitarios para Dashboard Stats API - Endpoints REST.

Referencia: docs/BACKLOG.md TODO (Fase 2 - Frontend & Integration)
Pipeline: StatsQueryService -> routes/dashboard.py -> TestClient
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.interfaces.api.routes.dashboard import roteador


# ---------------------------------------------------------------------------
# Fixture: app e client
# ---------------------------------------------------------------------------


@pytest.fixture
def app_teste() -> FastAPI:
    """Cria app FastAPI minimo com apenas o router de dashboard."""
    aplicacao: FastAPI = FastAPI()
    aplicacao.include_router(roteador, prefix="/api/v1")
    return aplicacao


@pytest.fixture
def cliente(app_teste: FastAPI) -> TestClient:
    """Cria TestClient para o app de teste."""
    return TestClient(app_teste)


# ---------------------------------------------------------------------------
# Testes: GET /api/v1/stats/snapshot
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_snapshot_retorna_200(cliente: TestClient) -> None:
    """Endpoint /stats/snapshot deve retornar HTTP 200."""
    resposta = cliente.get("/api/v1/stats/snapshot")
    assert resposta.status_code == 200


@pytest.mark.unit
def test_snapshot_contem_campos_obrigatorios(cliente: TestClient) -> None:
    """Snapshot deve conter campos: timestamp, trade_stats, metricas_operacionais,
    protecao_status, trades_recentes."""
    resposta = cliente.get("/api/v1/stats/snapshot")
    dados = resposta.json()
    assert "timestamp" in dados
    assert "trade_stats" in dados
    assert "metricas_operacionais" in dados
    assert "protecao_status" in dados
    assert "trades_recentes" in dados


@pytest.mark.unit
def test_snapshot_timestamp_formato_iso(cliente: TestClient) -> None:
    """Campo timestamp do snapshot deve estar em formato ISO 8601."""
    resposta = cliente.get("/api/v1/stats/snapshot")
    dados = resposta.json()
    timestamp: str = dados["timestamp"]
    # Formato ISO 8601: YYYY-MM-DDTHH:MM:SS.microseconds
    assert "T" in timestamp
    assert len(timestamp) >= 19


# ---------------------------------------------------------------------------
# Testes: GET /api/v1/stats/recentes
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_recentes_retorna_200(cliente: TestClient) -> None:
    """Endpoint /stats/recentes deve retornar HTTP 200."""
    resposta = cliente.get("/api/v1/stats/recentes")
    assert resposta.status_code == 200


@pytest.mark.unit
def test_recentes_retorna_lista(cliente: TestClient) -> None:
    """Endpoint /stats/recentes deve retornar uma lista JSON."""
    resposta = cliente.get("/api/v1/stats/recentes")
    dados = resposta.json()
    assert isinstance(dados, list)


@pytest.mark.unit
def test_recentes_aceita_parametro_quantidade(cliente: TestClient) -> None:
    """Parametro quantidade deve ser aceito sem erro."""
    resposta = cliente.get("/api/v1/stats/recentes?quantidade=5")
    assert resposta.status_code == 200


@pytest.mark.unit
def test_recentes_quantidade_invalida_retorna_422(cliente: TestClient) -> None:
    """Quantidade fora do range (0 ou >100) deve retornar HTTP 422."""
    resposta_zero = cliente.get("/api/v1/stats/recentes?quantidade=0")
    assert resposta_zero.status_code == 422

    resposta_grande = cliente.get("/api/v1/stats/recentes?quantidade=101")
    assert resposta_grande.status_code == 422


# ---------------------------------------------------------------------------
# Testes: GET /api/v1/stats/periodo/{periodo}
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_periodo_hoje_retorna_200(cliente: TestClient) -> None:
    """Periodo 'hoje' deve retornar HTTP 200."""
    resposta = cliente.get("/api/v1/stats/periodo/hoje")
    assert resposta.status_code == 200


@pytest.mark.unit
def test_periodo_7dias_retorna_200(cliente: TestClient) -> None:
    """Periodo '7dias' deve retornar HTTP 200."""
    resposta = cliente.get("/api/v1/stats/periodo/7dias")
    assert resposta.status_code == 200


@pytest.mark.unit
def test_periodo_30dias_retorna_200(cliente: TestClient) -> None:
    """Periodo '30dias' deve retornar HTTP 200."""
    resposta = cliente.get("/api/v1/stats/periodo/30dias")
    assert resposta.status_code == 200


@pytest.mark.unit
def test_periodo_retorna_campos_trade_stats(cliente: TestClient) -> None:
    """Resposta de periodo deve conter campos de TradeStats."""
    resposta = cliente.get("/api/v1/stats/periodo/hoje")
    dados = resposta.json()
    assert "total_trades" in dados
    assert "win_rate" in dados
    assert "pnl_total_reais" in dados
    assert "drawdown_maximo" in dados
