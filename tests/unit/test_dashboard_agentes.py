"""Testes TDD para BLID-040 — DashboardAgentesService.

RED phase: todos os testes devem FALHAR antes da implementação.
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts import run_dashboard_agentes
from src.application.services.dashboard_agentes_service import (
    AgenteMetricas,
    AgenteStatus,
    DashboardAgentesService,
    DashboardEquityPayload,
    DashboardMetricasPayload,
    DashboardStatusPayload,
    DashboardTradesPayload,
    EquityPoint,
    TradeInfo,
)

_MAGIC_RL_5000 = 234500
_MAGIC_RL_DIRETO = 234600
_DATA_HOJE = str(date.today())
_DATA_3_DIAS = str(date.today() - timedelta(days=3))
_DATA_10_DIAS = str(date.today() - timedelta(days=10))

_DDL_TRADES = """
    CREATE TABLE IF NOT EXISTS trades (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        magic_number INTEGER NOT NULL,
        side         TEXT    NOT NULL,
        entry_time   TEXT    NOT NULL,
        exit_time    TEXT,
        profit_loss  REAL,
        status       TEXT
    );
"""


def _insert_trade(
    conn: sqlite3.Connection,
    magic_number: int,
    profit_loss: float | None,
    entry_date: str = _DATA_HOJE,
    entry_time_str: str = "10:00:00",
    exit_time_str: str | None = "10:05:00",
    side: str = "BUY",
) -> None:
    entry_time = f"{entry_date} {entry_time_str}"
    exit_time = f"{entry_date} {exit_time_str}" if exit_time_str else None
    conn.execute(
        """
        INSERT INTO trades
            (magic_number, side, entry_time, exit_time, profit_loss, status)
        VALUES (?, ?, ?, ?, ?, 'CLOSED')
        """,
        (magic_number, side, entry_time, exit_time, profit_loss),
    )
    conn.commit()


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "trading.db"
    conn = sqlite3.connect(str(path))
    conn.execute(_DDL_TRADES)
    conn.commit()
    conn.close()
    return path


@pytest.fixture()
def svc(db_path: Path) -> DashboardAgentesService:
    return DashboardAgentesService(db_path=db_path)


@pytest.fixture()
def svc_sem_banco(tmp_path: Path) -> DashboardAgentesService:
    return DashboardAgentesService(db_path=tmp_path / "nao_existe.db")


@pytest.fixture()
def api_client(db_path: Path) -> TestClient:
    run_dashboard_agentes._svc = DashboardAgentesService(db_path=db_path)
    return TestClient(run_dashboard_agentes.app)


# H — Happy Path
@pytest.mark.unit
class TestDashboardStatusHappyPath:
    def test_H1_status_banco_populado_retorna_banco_disponivel_true(
        self, svc: DashboardAgentesService, db_path: Path
    ) -> None:
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_5000, 100.0, entry_time_str="09:10:00")
        _insert_trade(conn, _MAGIC_RL_5000, 200.0, entry_time_str="10:00:00")
        _insert_trade(conn, _MAGIC_RL_5000, -50.0, entry_time_str="11:00:00")
        conn.close()
        payload = svc.obter_status()
        assert isinstance(payload, DashboardStatusPayload)
        assert payload.banco_disponivel is True
        agente = next((a for a in payload.agentes if a.magic_number == _MAGIC_RL_5000), None)
        assert agente is not None
        assert agente.pnl_hoje == pytest.approx(250.0)
        assert agente.win_rate == pytest.approx(2 / 3)


@pytest.mark.unit
class TestDashboardMetricasHappyPath:
    def test_H2_metricas_profit_factor_calculado_corretamente(
        self, svc: DashboardAgentesService, db_path: Path
    ) -> None:
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_5000, 150.0, entry_date=_DATA_HOJE)
        _insert_trade(conn, _MAGIC_RL_5000, 150.0, entry_date=_DATA_3_DIAS)
        _insert_trade(conn, _MAGIC_RL_5000, -100.0, entry_date=_DATA_HOJE)
        conn.close()
        payload = svc.obter_metricas()
        assert isinstance(payload, DashboardMetricasPayload)
        agente = next((a for a in payload.agentes if a.magic_number == _MAGIC_RL_5000), None)
        assert agente is not None
        assert agente.profit_factor == pytest.approx(3.0)

    def test_H3_trades_retorna_maximo_10_por_agente(
        self, svc: DashboardAgentesService, db_path: Path
    ) -> None:
        conn = sqlite3.connect(str(db_path))
        for i in range(15):
            hora = 9 + (i // 12)
            minuto = (i * 5) % 60
            _insert_trade(conn, _MAGIC_RL_5000, float(10 + i), entry_date=_DATA_HOJE, entry_time_str=f"{hora:02d}:{minuto:02d}:00")
        conn.close()
        payload = svc.obter_trades()
        assert isinstance(payload, DashboardTradesPayload)
        assert payload.banco_disponivel is True
        trades_rl5000 = [t for t in payload.trades if t.magic_number == _MAGIC_RL_5000]
        assert len(trades_rl5000) == 10

    def test_H4_equity_lookback_7_dias_com_dados_diarios(
        self, svc: DashboardAgentesService, db_path: Path
    ) -> None:
        conn = sqlite3.connect(str(db_path))
        for delta in range(7):
            dia = str(date.today() - timedelta(days=delta))
            _insert_trade(conn, _MAGIC_RL_5000, 50.0, entry_date=dia)
        conn.close()
        payload = svc.obter_equity()
        assert isinstance(payload, DashboardEquityPayload)
        assert payload.banco_disponivel is True
        assert 1 <= len(payload.series) <= 7
        for ponto in payload.series:
            assert isinstance(ponto, EquityPoint)
            assert len(ponto.data) == 10
            assert ponto.data[4] == "-" and ponto.data[7] == "-"


# E — Banco Ausente
@pytest.mark.unit
class TestDashboardBancoAusente:
    def test_E1_banco_ausente_status_retorna_payload_zerado_sem_excecao(
        self, svc_sem_banco: DashboardAgentesService
    ) -> None:
        payload = svc_sem_banco.obter_status()
        assert isinstance(payload, DashboardStatusPayload)
        assert payload.banco_disponivel is False
        assert isinstance(payload.agentes, list)
        for agente in payload.agentes:
            assert agente.win_rate == 0.0
            assert agente.pnl_hoje == 0.0
            assert agente.trades_abertas == 0

    def test_E2_profit_factor_todos_wins_retorna_zero_nao_infinito(
        self, svc: DashboardAgentesService, db_path: Path
    ) -> None:
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_5000, 100.0)
        _insert_trade(conn, _MAGIC_RL_5000, 200.0)
        conn.close()
        payload = svc.obter_metricas()
        agente = next((a for a in payload.agentes if a.magic_number == _MAGIC_RL_5000), None)
        assert agente is not None
        assert agente.profit_factor == 0.0
        assert not math.isinf(agente.profit_factor)
        assert not math.isnan(agente.profit_factor)


# B — Borda e Isolamento
@pytest.mark.unit
class TestDashboardIsolamentoEBorda:
    def test_B1_trades_rl_direto_nao_aparecem_no_payload_de_rl5000(
        self, svc: DashboardAgentesService, db_path: Path
    ) -> None:
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_DIRETO, 500.0)
        conn.close()
        payload = svc.obter_trades()
        trades_rl5000 = [t for t in payload.trades if t.magic_number == _MAGIC_RL_5000]
        assert len(trades_rl5000) == 0

    def test_B2_equity_ignora_trades_alem_de_7_dias(
        self, svc: DashboardAgentesService, db_path: Path
    ) -> None:
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_5000, 999.0, entry_date=_DATA_10_DIAS)
        _insert_trade(conn, _MAGIC_RL_5000, 50.0, entry_date=_DATA_3_DIAS)
        conn.close()
        payload = svc.obter_equity()
        pnls_rl5000 = [pt.pnl_rl_5000 for pt in payload.series]
        assert 999.0 not in pnls_rl5000
        assert any(abs(pnl - 50.0) < 0.01 for pnl in pnls_rl5000)

    def test_B3_trades_abertos_sem_exit_time_nao_contam_em_status(
        self, svc: DashboardAgentesService, db_path: Path
    ) -> None:
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_5000, 100.0, exit_time_str="10:05:00")
        _insert_trade(conn, _MAGIC_RL_5000, 500.0, exit_time_str=None)
        conn.close()
        payload = svc.obter_status()
        agente = next((a for a in payload.agentes if a.magic_number == _MAGIC_RL_5000), None)
        assert agente is not None
        assert agente.pnl_hoje == pytest.approx(100.0)
        assert agente.win_rate == pytest.approx(1.0)


# R — Regressão
@pytest.mark.unit
class TestDashboardRegressao:
    def test_R1_profit_loss_null_excluido_de_status_e_metricas(
        self, svc: DashboardAgentesService, db_path: Path
    ) -> None:
        conn = sqlite3.connect(str(db_path))
        _insert_trade(conn, _MAGIC_RL_5000, 100.0)
        _insert_trade(conn, _MAGIC_RL_5000, None)
        conn.close()
        status_payload = svc.obter_status()
        metricas_payload = svc.obter_metricas()
        agente_status = next((a for a in status_payload.agentes if a.magic_number == _MAGIC_RL_5000), None)
        agente_metricas = next((a for a in metricas_payload.agentes if a.magic_number == _MAGIC_RL_5000), None)
        assert agente_status is not None
        assert agente_status.pnl_hoje == pytest.approx(100.0)
        assert agente_status.win_rate == pytest.approx(1.0)
        assert agente_metricas is not None
        assert agente_metricas.win_rate_7d == pytest.approx(1.0)


@pytest.mark.unit
class TestDashboardApiRotas:
    def test_api_status_canonico_retorna_200(self, api_client: TestClient) -> None:
        response = api_client.get("/api/agentes/status")
        assert response.status_code == 200
        assert "agentes" in response.json()

    def test_api_metricas_canonico_retorna_200(self, api_client: TestClient) -> None:
        response = api_client.get("/api/agentes/metricas")
        assert response.status_code == 200
        assert "agentes" in response.json()

    def test_api_trades_canonico_retorna_200(self, api_client: TestClient) -> None:
        response = api_client.get("/api/agentes/trades")
        assert response.status_code == 200
        assert "trades" in response.json()

    def test_api_equity_canonico_retorna_200(self, api_client: TestClient) -> None:
        response = api_client.get("/api/agentes/equity")
        assert response.status_code == 200
        assert "series" in response.json()
