"""
Testes para DashboardStatsServer backend.

Validam queries de dados agregados para dashboard:
- Resumo de execucao (trades, P&L, win rate, drawdown)
- Metricas operacionais (Sharpe, duracoes, fechamentos)
- Protecoes ativas (anti-overtrading, bloqueios)
- Historico de trades recentes
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import sqlite3
import sys
from pathlib import Path

import pytest

# Import direto do módulo para evitar cadeia de importações
import importlib.util
spec = importlib.util.spec_from_file_location(
    "dashboard_stats_server",
    str(Path(__file__).parent.parent.parent / "src" / "application" / "dashboard_stats_server.py")
)
dashboard_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard_module)

TradeStats = dashboard_module.TradeStats
OperationalMetrics = dashboard_module.OperationalMetrics
ProtectionStatus = dashboard_module.ProtectionStatus
TradeRecente = dashboard_module.TradeRecente
DashboardDataSnapshot = dashboard_module.DashboardDataSnapshot
StatsQueryService = dashboard_module.StatsQueryService


class TestTradeStatsDataClass:
    """Testa dataclass TradeStats com dados de execucao."""

    def test_criar_trade_stats_basico(self) -> None:
        """Cria TradeStats com valores basicos."""
        stats = TradeStats(
            total_trades=5,
            total_ganhos=3,
            total_perdas=1,
            total_breakeven=1,
            win_rate=60.0,
            pnl_total_reais=250.50,
            pnl_total_pct=2.50,
            drawdown_maximo=-150.0,
            drawdown_pct=-1.5,
        )
        assert stats.total_trades == 5
        assert stats.win_rate == 60.0
        assert stats.pnl_total_reais == 250.50

    def test_para_dict(self) -> None:
        """Converte TradeStats para dict."""
        stats = TradeStats(
            total_trades=10,
            total_ganhos=6,
            total_perdas=3,
            total_breakeven=1,
            win_rate=60.0,
            pnl_total_reais=500.0,
            pnl_total_pct=5.0,
            drawdown_maximo=-250.0,
            drawdown_pct=-2.5,
        )
        stats_dict = stats.para_dict()
        assert isinstance(stats_dict, Dict)
        assert stats_dict["total_trades"] == 10
        assert stats_dict["pnl_total_reais"] == 500.0


class TestOperationalMetrics:
    """Testa dataclass OperationalMetrics."""

    def test_criar_metricas_operacionais(self) -> None:
        """Cria OperationalMetrics com valores."""
        metricas = OperationalMetrics(
            sharpe_ratio=1.25,
            profit_factor_bruto=2.5,
            tempo_posicao_media_minutos=45,
            percentual_fechamento_tp=45.0,
            percentual_fechamento_sl=35.0,
            percentual_fechamento_manual=20.0,
        )
        assert metricas.sharpe_ratio == 1.25
        assert metricas.tempo_posicao_media_minutos == 45
        assert abs(
            sum(
                [
                    metricas.percentual_fechamento_tp,
                    metricas.percentual_fechamento_sl,
                    metricas.percentual_fechamento_manual,
                ]
            )
            - 100.0
        ) < 0.01  # Total deve ser ~100%


class TestProtectionStatus:
    """Testa dataclass ProtectionStatus."""

    def test_criar_protection_status(self) -> None:
        """Cria ProtectionStatus com status de protecoes."""
        status = ProtectionStatus(
            trades_ultima_hora=2,
            limite_trades_hora=3,
            cooldown_segundos_restantes=45,
            total_bloqueios_hora=1,
            contador_perda_consecutiva=0,
            horario_permite_tradear=True,
        )
        assert status.trades_ultima_hora == 2
        assert status.cooldown_segundos_restantes == 45
        assert status.horario_permite_tradear is True

    def test_indicador_bloqueio_ativo(self) -> None:
        """Valida se bloqueio esta ativo."""
        status_bloqueado = ProtectionStatus(
            trades_ultima_hora=4,  # > limite 3
            limite_trades_hora=3,
            cooldown_segundos_restantes=0,
            total_bloqueios_hora=1,
            contador_perda_consecutiva=2,  # 2x perda
            horario_permite_tradear=False,  # Fora de horario
        )
        # Se qualquer condicao bloqueadora esta ativa
        esta_bloqueado = (
            status_bloqueado.trades_ultima_hora > status_bloqueado.limite_trades_hora
            or status_bloqueado.cooldown_segundos_restantes > 0
            or status_bloqueado.contador_perda_consecutiva >= 2
            or not status_bloqueado.horario_permite_tradear
        )
        assert esta_bloqueado is True


class TestDashboardDataSnapshot:
    """Testa dataclass DashboardDataSnapshot."""

    def test_criar_snapshot_completo(self) -> None:
        """Cria DashboardDataSnapshot com todos dados."""
        trade_stats = TradeStats(
            total_trades=5,
            total_ganhos=3,
            total_perdas=1,
            total_breakeven=1,
            win_rate=60.0,
            pnl_total_reais=250.0,
            pnl_total_pct=2.5,
            drawdown_maximo=-150.0,
            drawdown_pct=-1.5,
        )
        metricas = OperationalMetrics(
            sharpe_ratio=1.2,
            profit_factor_bruto=2.5,
            tempo_posicao_media_minutos=45,
            percentual_fechamento_tp=45.0,
            percentual_fechamento_sl=35.0,
            percentual_fechamento_manual=20.0,
        )
        protecao = ProtectionStatus(
            trades_ultima_hora=1,
            limite_trades_hora=3,
            cooldown_segundos_restantes=0,
            total_bloqueios_hora=0,
            contador_perda_consecutiva=0,
            horario_permite_tradear=True,
        )

        snapshot = DashboardDataSnapshot(
            timestamp=datetime.now(),
            trade_stats=trade_stats,
            metricas_operacionais=metricas,
            protecao_status=protecao,
            trades_recentes=[],
        )

        assert snapshot.trade_stats.total_trades == 5
        assert snapshot.metricas_operacionais.sharpe_ratio == 1.2
        assert snapshot.protecao_status.horario_permite_tradear is True

    def test_para_dict_estrutura(self) -> None:
        """Converte snapshot para dict com estrutura aninhada."""
        snapshot = DashboardDataSnapshot(
            timestamp=datetime.now(),
            trade_stats=TradeStats(
                total_trades=2,
                total_ganhos=1,
                total_perdas=1,
                total_breakeven=0,
                win_rate=50.0,
                pnl_total_reais=0.0,
                pnl_total_pct=0.0,
                drawdown_maximo=0.0,
                drawdown_pct=0.0,
            ),
            metricas_operacionais=OperationalMetrics(
                sharpe_ratio=0.0,
                profit_factor_bruto=1.0,
                tempo_posicao_media_minutos=30,
                percentual_fechamento_tp=50.0,
                percentual_fechamento_sl=50.0,
                percentual_fechamento_manual=0.0,
            ),
            protecao_status=ProtectionStatus(
                trades_ultima_hora=0,
                limite_trades_hora=3,
                cooldown_segundos_restantes=0,
                total_bloqueios_hora=0,
                contador_perda_consecutiva=0,
                horario_permite_tradear=True,
            ),
            trades_recentes=[],
        )

        snapshot_dict = snapshot.para_dict()
        assert isinstance(snapshot_dict, Dict)
        assert "timestamp" in snapshot_dict
        assert "trade_stats" in snapshot_dict
        assert "metricas_operacionais" in snapshot_dict
        assert "protecao_status" in snapshot_dict


class TestStatsQueryService:
    """Testa StatsQueryService com queries de dados."""

    def test_inicializar_service(self) -> None:
        """Cria instancia de StatsQueryService."""
        service = StatsQueryService()
        assert service is not None
        assert hasattr(service, "obter_snapshot_dashboard")
        assert hasattr(service, "obter_trades_recentes")
        assert hasattr(service, "obter_stats_por_periodo")

    def test_obter_snapshot_dashboard_estrutura(self) -> None:
        """Obtem snapshot dashboard com estrutura completa."""
        service = StatsQueryService()

        # Obter snapshot (pode estar vazio em teste sem BD)
        snapshot = service.obter_snapshot_dashboard()

        # Validar estrutura
        assert snapshot is not None
        assert isinstance(snapshot, DashboardDataSnapshot)
        assert snapshot.trade_stats is not None
        assert snapshot.metricas_operacionais is not None
        assert snapshot.protecao_status is not None
        assert isinstance(snapshot.trades_recentes, list)

    def test_obter_stats_por_periodo_validacoes(self) -> None:
        """Valida queries por periodo (hoje, ultimos 7 dias, etc)."""
        service = StatsQueryService()

        # Query de hoje
        stats_hoje = service.obter_stats_por_periodo(periodo="hoje")
        assert stats_hoje is not None
        assert isinstance(stats_hoje, TradeStats)

        # Query de ultimos 7 dias
        stats_7d = service.obter_stats_por_periodo(periodo="7dias")
        assert stats_7d is not None
        assert isinstance(stats_7d, TradeStats)

        # Query de 30 dias
        stats_30d = service.obter_stats_por_periodo(periodo="30dias")
        assert stats_30d is not None
        assert isinstance(stats_30d, TradeStats)

    def test_obter_trades_recentes_quantidade(self) -> None:
        """Obtem ultimos N trades com limite maximo."""
        service = StatsQueryService()

        # Obter ultimos 10 trades
        trades = service.obter_trades_recentes(quantidade=10)
        assert isinstance(trades, list)
        assert len(trades) <= 10  # Pode ser 0 se nao houver dados

    def test_calcular_sharpe_ratio_validacoes(self) -> None:
        """Valida calculo de Sharpe ratio a partir de series de P&L."""
        service = StatsQueryService()

        # Serie vazia
        sharpe_vazio = service.calcular_sharpe_ratio([])
        assert sharpe_vazio == 0.0  # Sem dados = 0

        # Serie com um trade
        sharpe_1trade = service.calcular_sharpe_ratio([100.0])
        assert isinstance(sharpe_1trade, float)

        # Serie com multiplos trades
        pnl_series = [50.0, -25.0, 100.0, -10.0, 75.0]
        sharpe_multi = service.calcular_sharpe_ratio(pnl_series)
        assert isinstance(sharpe_multi, float)
        assert sharpe_multi >= 0.0  # Sharpe >= 0

    def test_para_json_serializable(self) -> None:
        """Valida que snapshot pode ser serializado em JSON."""
        service = StatsQueryService()
        snapshot = service.obter_snapshot_dashboard()

        # Converter para dict (deve ser JSON-serializable)
        snapshot_dict = snapshot.para_dict()
        assert isinstance(snapshot_dict, Dict)

        # Todos valores devem ser tipos basicos (str, int, float, bool, list, dict)
        def validar_json_serializable(obj: Any) -> bool:
            """Recursivamente valida se objeto eh JSON-serializable."""
            if obj is None or isinstance(obj, (bool, int, float, str)):
                return True
            if isinstance(obj, list):
                return all(validar_json_serializable(item) for item in obj)
            if isinstance(obj, dict):
                return all(
                    isinstance(k, str) and validar_json_serializable(v)
                    for k, v in obj.items()
                )
            return False

        assert validar_json_serializable(snapshot_dict)

    def test_obter_resumo_fechamentos_por_origem_agrupar_operador_mercado_agente(
        self, tmp_path: Path
    ) -> None:
        """Deve agrupar fechamentos por origem operacional."""
        db_path = tmp_path / "dashboard_micro.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE posicoes_encerradas (
                posicao_id TEXT PRIMARY KEY,
                trade_id TEXT NOT NULL UNIQUE,
                signal_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                direcao TEXT NOT NULL,
                volume INTEGER NOT NULL,
                preco_entrada REAL NOT NULL,
                preco_encerramento REAL NOT NULL,
                pl_final REAL NOT NULL,
                motivo_encerramento TEXT DEFAULT 'NAO_INFORMADO',
                encerrado_por TEXT DEFAULT 'SISTEMA',
                criado_em TEXT NOT NULL,
                encerrado_em TEXT NOT NULL
            )
            """
        )
        agora = datetime.now().isoformat()
        registros = [
            ("POS_1", "T1", "S1", "WIN$N", "BUY", 1, 100.0, 101.5, 1.5, "TAKE_PROFIT", "MERCADO", agora, agora),
            ("POS_2", "T2", "S2", "WIN$N", "BUY", 1, 100.0, 100.4, 0.4, "MANUAL_CLOSE", "OPERADOR", agora, agora),
            ("POS_3", "T3", "S3", "WIN$N", "SELL", 1, 100.0, 99.0, 1.0, "FIM_PREGAO", "AGENTE", agora, agora),
            ("POS_4", "T4", "S4", "WIN$N", "BUY", 1, 100.0, 99.0, -1.0, "STOP_LOSS", "MERCADO", agora, agora)
        ]
        conn.executemany(
            """
            INSERT INTO posicoes_encerradas (
                posicao_id, trade_id, signal_id, symbol, direcao, volume,
                preco_entrada, preco_encerramento, pl_final,
                motivo_encerramento, encerrado_por, criado_em, encerrado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            registros,
        )
        conn.commit()
        conn.close()

        service = StatsQueryService(db_path=str(db_path))
        resumo = service.obter_resumo_fechamentos_por_origem(dias=7)

        assert resumo["total_fechamentos"] == 4
        assert resumo["por_origem"]["MERCADO"]["quantidade"] == 2
        assert resumo["por_origem"]["OPERADOR"]["quantidade"] == 1
        assert resumo["por_origem"]["AGENTE"]["quantidade"] == 1
        assert resumo["por_motivo"]["MANUAL_CLOSE"]["quantidade"] == 1

    def test_obter_resumo_fechamentos_por_origem_sem_tabela_retorna_zerado(
        self, tmp_path: Path
    ) -> None:
        """Se a tabela ainda não existir, o payload deve vir vazio."""
        db_path = tmp_path / "sem_dados.db"
        sqlite3.connect(db_path).close()

        service = StatsQueryService(db_path=str(db_path))
        resumo = service.obter_resumo_fechamentos_por_origem(dias=7)

        assert resumo["total_fechamentos"] == 0
        assert resumo["por_origem"] == {}
        assert resumo["fechamentos_recentes"] == []
