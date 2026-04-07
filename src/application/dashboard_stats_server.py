"""
Dashboard Stats Server - Backend para visualizacao de operacoes.

Componentes:
- Queries eficientes de dados do SQLite
- Agregacoes de metricas (Sharpe ratio, win rate, P&L)
- Endpoints REST (FastAPI) para dashboard frontend
- Dataclasses estruturadas para JSON serialization

Usados por:
- Frontend dashboard HTML/JS (GET /api/stats)
- Monitoramento em tempo real
- Analises historicas (periodo)
"""

import logging
import sqlite3
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from statistics import mean, stdev

logger = logging.getLogger(__name__)


@dataclass
class TradeStats:
    """Estatisticas agregadas de trades."""

    total_trades: int
    total_ganhos: int
    total_perdas: int
    total_breakeven: int
    win_rate: float
    pnl_total_reais: float
    pnl_total_pct: float
    drawdown_maximo: float = 0.0
    drawdown_pct: float = 0.0
    pnl_nao_realizado_reais: float = 0.0

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dict estruturado."""
        return asdict(self)


@dataclass
class OperationalMetrics:
    """Metricas operacionais de execucao."""

    sharpe_ratio: float
    profit_factor_bruto: float
    tempo_posicao_media_minutos: float
    percentual_fechamento_tp: float
    percentual_fechamento_sl: float
    percentual_fechamento_manual: float

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dict estruturado."""
        return asdict(self)


@dataclass
class ProtectionStatus:
    """Status de protecoes ativas (anti-overtrading, etc)."""

    trades_ultima_hora: int
    limite_trades_hora: int
    cooldown_segundos_restantes: int
    total_bloqueios_hora: int
    contador_perda_consecutiva: int
    horario_permite_tradear: bool

    def esta_bloqueado(self) -> bool:
        """Valida se alguma protecao esta ativa (bloqueando)."""
        if self.trades_ultima_hora > self.limite_trades_hora:
            return True
        if self.cooldown_segundos_restantes > 0:
            return True
        if self.contador_perda_consecutiva >= 2:
            return True
        if not self.horario_permite_tradear:
            return True
        return False

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dict estruturado."""
        return asdict(self)


@dataclass
class TradeRecente:
    """Resumo de trade recente para listagem no dashboard."""

    ticket: int
    simbolo: str
    direcao: str  # BUY ou SELL
    preco_entrada: float
    preco_saida: float
    pnl_reais: float
    pnl_pct: float
    duracao_minutos: int
    motivo_fechamento: str  # TP_HIT, SL_HIT, MANUAL_CLOSE, TIMEOUT, CANCELLED
    timestamp_abertura: datetime
    timestamp_fechamento: datetime
    encerrado_por: str = "SISTEMA"

    def para_dict(self) -> Dict[str, Any]:
        """Converte para dict estruturado com timestamps ISO."""
        trade_dict = asdict(self)
        trade_dict["timestamp_abertura"] = self.timestamp_abertura.isoformat()
        trade_dict["timestamp_fechamento"] = (
            self.timestamp_fechamento.isoformat()
        )
        return trade_dict


@dataclass
class DashboardDataSnapshot:
    """Snapshot completo de dados para dashboard."""

    timestamp: datetime
    trade_stats: TradeStats
    metricas_operacionais: OperationalMetrics
    protecao_status: ProtectionStatus
    trades_recentes: List[TradeRecente] = field(default_factory=list)
    fechamentos_por_origem: Dict[str, Any] = field(default_factory=dict)
    pnl_nao_realizado_reais: float = 0.0
    ultima_atualizacao_precos: Optional[datetime] = None

    def para_dict(self) -> Dict[str, Any]:
        """Converte snapshot para dict JSON-serializable."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "trade_stats": self.trade_stats.para_dict(),
            "metricas_operacionais": (
                self.metricas_operacionais.para_dict()
            ),
            "protecao_status": self.protecao_status.para_dict(),
            "trades_recentes": [
                trade.para_dict() for trade in self.trades_recentes
            ],
            "fechamentos_por_origem": self.fechamentos_por_origem,
            "pnl_nao_realizado_reais": self.pnl_nao_realizado_reais,
            "ultima_atualizacao_precos": (
                self.ultima_atualizacao_precos.isoformat()
                if self.ultima_atualizacao_precos
                else None
            ),
        }


class StatsQueryService:
    """
    Service para queries de dados agregados do SQLite.

    Metodos principais:
        obter_snapshot_dashboard(): Snapshot completo atual
        obter_trades_recentes(): Ultimos N trades fechados
        obter_stats_por_periodo(): Stats de um periodo (hoje, 7d, 30d)
        calcular_sharpe_ratio(): Sharpe a partir de serie P&L
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Inicializa StatsQueryService."""
        if db_path:
            self.db_path = db_path
            return

        raiz_projeto = Path(__file__).resolve().parents[2]
        candidatos = [
            raiz_projeto / "data" / "db" / "trading_micro_tendencia.db",
            raiz_projeto / "data" / "db" / "trading.db",
        ]
        self.db_path = None
        for candidato in candidatos:
            if candidato.exists():
                self.db_path = str(candidato)
                break
        if self.db_path is None:
            self.db_path = str(candidatos[0])

    def obter_snapshot_dashboard(
        self,
        pnl_nao_realizado_reais: float = 0.0,
        ultima_atualizacao_precos: Optional[datetime] = None,
    ) -> DashboardDataSnapshot:
        """
        Obtem snapshot completo de dados para dashboard.

        Args:
            pnl_nao_realizado_reais: P&L nao realizado calculado externamente
                via Portfolio.calculate_unrealized_pnl() com precos do MT5.
                Padrao 0.0 quando dados de mercado nao estiverem disponiveis.
            ultima_atualizacao_precos: Momento da ultima consulta de preco no MT5.
                Exposto no payload para auditoria (dashboard refresh < 5s).

        Returns:
            DashboardDataSnapshot com todos dados agregados
        """
        # Stats de hoje
        stats = self._calcular_stats_hoje()
        stats.pnl_nao_realizado_reais = pnl_nao_realizado_reais

        # Metricas operacionais
        metricas = self._calcular_metricas_hoje()

        # Status de protecoes
        protecao = self._obter_protection_status()

        # Trades recentes (ultimos 10)
        trades = self.obter_trades_recentes(quantidade=10)

        if pnl_nao_realizado_reais != 0.0:
            logger.info(
                "dashboard_snapshot | pnl_nao_realizado=%.2f"
                " | ultima_atualizacao_precos=%s",
                pnl_nao_realizado_reais,
                ultima_atualizacao_precos.isoformat()
                if ultima_atualizacao_precos
                else "indisponivel",
            )

        return DashboardDataSnapshot(
            timestamp=datetime.now(),
            trade_stats=stats,
            metricas_operacionais=metricas,
            protecao_status=protecao,
            trades_recentes=trades,
            fechamentos_por_origem=self.obter_resumo_fechamentos_por_origem(dias=7),
            pnl_nao_realizado_reais=pnl_nao_realizado_reais,
            ultima_atualizacao_precos=ultima_atualizacao_precos,
        )

    def _conectar_db(self) -> Optional[sqlite3.Connection]:
        """Abre conexão SQLite, retornando ``None`` se indisponível."""
        if not self.db_path:
            return None

        caminho = Path(self.db_path)
        if not caminho.exists():
            return None

        conn = sqlite3.connect(str(caminho))
        conn.row_factory = sqlite3.Row
        return conn

    def _tabela_existe(self, conn: sqlite3.Connection, nome_tabela: str) -> bool:
        """Verifica se a tabela existe no SQLite."""
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (nome_tabela,),
        ).fetchone()
        return row is not None

    def obter_trades_recentes(
        self, quantidade: int = 10
    ) -> List[TradeRecente]:
        """Obtem ultimos N trades fechados a partir do SQLite do agente."""
        conn = self._conectar_db()
        if conn is None:
            return []

        try:
            if not self._tabela_existe(conn, "posicoes_encerradas"):
                return []

            rows = conn.execute(
                """
                SELECT trade_id, symbol, direcao, preco_entrada,
                       preco_encerramento, pl_final, motivo_encerramento,
                       encerrado_por, criado_em, encerrado_em
                FROM posicoes_encerradas
                ORDER BY datetime(encerrado_em) DESC
                LIMIT ?
                """,
                (int(quantidade),),
            ).fetchall()

            trades: List[TradeRecente] = []
            for row in rows:
                preco_entrada = float(row["preco_entrada"] or 0.0)
                pnl_reais = float(row["pl_final"] or 0.0)
                pnl_pct = (pnl_reais / preco_entrada * 100.0) if preco_entrada else 0.0
                abertura = datetime.fromisoformat(str(row["criado_em"]))
                fechamento = datetime.fromisoformat(str(row["encerrado_em"]))
                duracao_minutos = max(
                    0,
                    int((fechamento - abertura).total_seconds() / 60),
                )
                try:
                    ticket = int(str(row["trade_id"]))
                except (TypeError, ValueError):
                    ticket = 0

                trades.append(
                    TradeRecente(
                        ticket=ticket,
                        simbolo=str(row["symbol"]),
                        direcao=str(row["direcao"]),
                        preco_entrada=preco_entrada,
                        preco_saida=float(row["preco_encerramento"] or 0.0),
                        pnl_reais=pnl_reais,
                        pnl_pct=pnl_pct,
                        duracao_minutos=duracao_minutos,
                        motivo_fechamento=str(row["motivo_encerramento"] or "NAO_INFORMADO"),
                        timestamp_abertura=abertura,
                        timestamp_fechamento=fechamento,
                        encerrado_por=str(row["encerrado_por"] or "SISTEMA"),
                    )
                )

            return trades
        except Exception as exc:
            logger.warning("Falha ao consultar trades recentes do dashboard: %s", exc)
            return []
        finally:
            conn.close()

    def obter_resumo_fechamentos_por_origem(self, dias: int = 7) -> Dict[str, Any]:
        """Resume fechamentos por origem operacional e motivo."""
        conn = self._conectar_db()
        payload: Dict[str, Any] = {
            "periodo_dias": int(dias),
            "db_path": self.db_path,
            "total_fechamentos": 0,
            "por_origem": {},
            "por_motivo": {},
            "fechamentos_recentes": [],
        }
        if conn is None:
            return payload

        try:
            if not self._tabela_existe(conn, "posicoes_encerradas"):
                return payload

            since_dt = (datetime.now() - timedelta(days=max(1, int(dias)))).isoformat()

            total_row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM posicoes_encerradas
                WHERE datetime(encerrado_em) >= datetime(?)
                """,
                (since_dt,),
            ).fetchone()
            payload["total_fechamentos"] = int((total_row["total"] if total_row else 0) or 0)

            rows_origem = conn.execute(
                """
                SELECT COALESCE(encerrado_por, 'SISTEMA') AS origem,
                       COUNT(*) AS quantidade,
                       COALESCE(SUM(pl_final), 0.0) AS pnl_total,
                       COALESCE(AVG(pl_final), 0.0) AS pnl_medio
                FROM posicoes_encerradas
                WHERE datetime(encerrado_em) >= datetime(?)
                GROUP BY COALESCE(encerrado_por, 'SISTEMA')
                ORDER BY quantidade DESC, origem ASC
                """,
                (since_dt,),
            ).fetchall()
            for row in rows_origem:
                origem = str(row["origem"])
                quantidade = int(row["quantidade"] or 0)
                percentual = (
                    round((quantidade / payload["total_fechamentos"]) * 100.0, 2)
                    if payload["total_fechamentos"]
                    else 0.0
                )
                payload["por_origem"][origem] = {
                    "quantidade": quantidade,
                    "pnl_total": float(row["pnl_total"] or 0.0),
                    "pnl_medio": float(row["pnl_medio"] or 0.0),
                    "percentual": percentual,
                }

            rows_motivo = conn.execute(
                """
                SELECT COALESCE(motivo_encerramento, 'NAO_INFORMADO') AS motivo,
                       COUNT(*) AS quantidade,
                       COALESCE(SUM(pl_final), 0.0) AS pnl_total
                FROM posicoes_encerradas
                WHERE datetime(encerrado_em) >= datetime(?)
                GROUP BY COALESCE(motivo_encerramento, 'NAO_INFORMADO')
                ORDER BY quantidade DESC, motivo ASC
                """,
                (since_dt,),
            ).fetchall()
            for row in rows_motivo:
                motivo = str(row["motivo"])
                payload["por_motivo"][motivo] = {
                    "quantidade": int(row["quantidade"] or 0),
                    "pnl_total": float(row["pnl_total"] or 0.0),
                }

            recentes = conn.execute(
                """
                SELECT trade_id, symbol, motivo_encerramento, encerrado_por,
                       pl_final, encerrado_em
                FROM posicoes_encerradas
                WHERE datetime(encerrado_em) >= datetime(?)
                ORDER BY datetime(encerrado_em) DESC
                LIMIT 10
                """,
                (since_dt,),
            ).fetchall()
            payload["fechamentos_recentes"] = [
                {
                    "trade_id": str(row["trade_id"]),
                    "symbol": str(row["symbol"]),
                    "motivo_encerramento": str(row["motivo_encerramento"] or "NAO_INFORMADO"),
                    "encerrado_por": str(row["encerrado_por"] or "SISTEMA"),
                    "pl_final": float(row["pl_final"] or 0.0),
                    "encerrado_em": str(row["encerrado_em"]),
                }
                for row in recentes
            ]
            return payload
        except Exception as exc:
            logger.warning("Falha ao resumir fechamentos por origem: %s", exc)
            return payload
        finally:
            conn.close()

    def obter_stats_por_periodo(self, periodo: str = "hoje") -> TradeStats:
        """
        Obtem stats agregadas de um periodo.

        Args:
            periodo: 'hoje', '7dias', '30dias'

        Returns:
            TradeStats para o periodo
        """
        if periodo == "hoje":
            return self._calcular_stats_hoje()
        elif periodo == "7dias":
            return self._calcular_stats_n_dias(7)
        elif periodo == "30dias":
            return self._calcular_stats_n_dias(30)
        else:
            return self._calcular_stats_hoje()

    def _calcular_stats_hoje(self) -> TradeStats:
        """Calcula stats para hoje (midnight a agora)."""
        # TODO: Query SQLite com filtro de data (DATE(timestamp) = DATE('now'))
        return TradeStats(
            total_trades=0,
            total_ganhos=0,
            total_perdas=0,
            total_breakeven=0,
            win_rate=0.0,
            pnl_total_reais=0.0,
            pnl_total_pct=0.0,
            drawdown_maximo=0.0,
            drawdown_pct=0.0,
        )

    def _calcular_stats_n_dias(self, n_dias: int) -> TradeStats:
        """Calcula stats para ultimos N dias."""
        # TODO: Query SQLite com filtro datetime.now() - timedelta(days=n_dias)
        return TradeStats(
            total_trades=0,
            total_ganhos=0,
            total_perdas=0,
            total_breakeven=0,
            win_rate=0.0,
            pnl_total_reais=0.0,
            pnl_total_pct=0.0,
            drawdown_maximo=0.0,
            drawdown_pct=0.0,
        )

    def _calcular_metricas_hoje(self) -> OperationalMetrics:
        """Calcula metricas operacionais para hoje."""
        resumo = self.obter_resumo_fechamentos_por_origem(dias=1)
        por_motivo = resumo.get("por_motivo", {})
        total = float(resumo.get("total_fechamentos", 0) or 0)

        def _percentual(*motivos: str) -> float:
            if total <= 0:
                return 0.0
            quantidade = sum(
                float((por_motivo.get(motivo, {}) or {}).get("quantidade", 0))
                for motivo in motivos
            )
            return round((quantidade / total) * 100.0, 2)

        return OperationalMetrics(
            sharpe_ratio=0.0,
            profit_factor_bruto=1.0,
            tempo_posicao_media_minutos=30.0,
            percentual_fechamento_tp=_percentual("TAKE_PROFIT", "TP_HIT"),
            percentual_fechamento_sl=_percentual("STOP_LOSS", "SL_HIT"),
            percentual_fechamento_manual=_percentual("MANUAL_CLOSE"),
        )

    def _obter_protection_status(self) -> ProtectionStatus:
        """Obtem status atual de protecoes ativas."""
        # TODO: Query anti_overtrading_protection + blockage_logging
        # SELECT COUNT(*) FROM trades WHERE TIME(timestamp_abertura) >= TIME('now', '-1 hour')
        # SELECT COUNT(*) FROM blockage_log WHERE timestamp >= datetime('now', '-1 hour')
        return ProtectionStatus(
            trades_ultima_hora=0,
            limite_trades_hora=3,
            cooldown_segundos_restantes=0,
            total_bloqueios_hora=0,
            contador_perda_consecutiva=0,
            horario_permite_tradear=True,
        )

    def calcular_sharpe_ratio(
        self, pnl_series: List[float], periodo_dias: int = 252
    ) -> float:
        """
        Calcula Sharpe ratio a partir de serie P&L diaria.

        Args:
            pnl_series: Lista de retornos (P&L em %)
            periodo_dias: 252 para anualizacao (trading days/ano)

        Returns:
            Sharpe ratio (0.0 se serie vazia)
        """
        if not pnl_series or len(pnl_series) < 2:
            return 0.0

        # Retorno medio diario (%)
        media = mean(pnl_series)

        # Desvio padrao diario
        desvio = stdev(pnl_series)

        if desvio == 0.0:
            return 0.0

        # Sharpe = (media - taxa_livre_risco) / desvio
        # Assumindo 0% taxa livre risco (conservador)
        taxa_livre_risco = 0.0

        # Anualizacao
        sharpe = ((media - taxa_livre_risco) / desvio) * (
            periodo_dias ** 0.5
        )

        # Sharpe não pode ser negativo
        if sharpe < 0.0:
            return 0.0
        return float(sharpe)

    def exportar_para_json(self) -> Dict[str, Any]:
        """Exporta snapshot dashboard em JSON estruturado."""
        snapshot = self.obter_snapshot_dashboard()
        return snapshot.para_dict()
