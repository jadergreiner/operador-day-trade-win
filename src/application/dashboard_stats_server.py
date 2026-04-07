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
from dataclasses import asdict, dataclass, field
from datetime import datetime
from datetime import time as horario_time
from datetime import timedelta
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Dict, List, Optional

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
        trade_dict["timestamp_fechamento"] = self.timestamp_fechamento.isoformat()
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
            "metricas_operacionais": (self.metricas_operacionais.para_dict()),
            "protecao_status": self.protecao_status.para_dict(),
            "trades_recentes": [trade.para_dict() for trade in self.trades_recentes],
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
        self.db_path: Optional[str] = None
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
        """Abre conexão SQLite read-only, retornando ``None`` se indisponível."""
        if not self.db_path:
            return None

        caminho = Path(self.db_path)
        if not caminho.exists():
            return None

        try:
            conn = sqlite3.connect(
                f"file:{caminho.as_posix()}?mode=ro",
                uri=True,
            )
        except sqlite3.OperationalError:
            conn = sqlite3.connect(str(caminho))
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA query_only = ON")
        except sqlite3.DatabaseError:
            logger.debug("PRAGMA query_only indisponível para %s", caminho)
        return conn

    def _tabela_existe(self, conn: sqlite3.Connection, nome_tabela: str) -> bool:
        """Verifica se a tabela existe no SQLite."""
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (nome_tabela,),
        ).fetchone()
        return row is not None

    def _trade_stats_zeradas(self) -> TradeStats:
        """Retorna estrutura padrão para ausência de dados."""
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

    def _parse_timestamp(self, valor: Any) -> Optional[datetime]:
        """Converte texto ISO/SQLite em `datetime`, tolerando formatos legados."""
        if valor in (None, ""):
            return None

        texto = str(valor).strip()
        try:
            return datetime.fromisoformat(texto)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
                try:
                    return datetime.strptime(texto, fmt)
                except ValueError:
                    continue
        return None

    def _calcular_trade_stats_desde(self, since_dt: datetime) -> TradeStats:
        """Agrega estatísticas de trades fechados desde `since_dt`."""
        conn = self._conectar_db()
        if conn is None:
            return self._trade_stats_zeradas()

        try:
            if not self._tabela_existe(conn, "posicoes_encerradas"):
                return self._trade_stats_zeradas()

            rows = conn.execute(
                """
                SELECT pl_final, preco_entrada, encerrado_em
                FROM posicoes_encerradas
                WHERE datetime(encerrado_em) >= datetime(?)
                ORDER BY datetime(encerrado_em) ASC, trade_id ASC
                """,
                (since_dt.isoformat(),),
            ).fetchall()

            if not rows:
                return self._trade_stats_zeradas()

            total_trades = len(rows)
            total_ganhos = 0
            total_perdas = 0
            total_breakeven = 0
            pnl_total_reais = 0.0
            notional_total = 0.0
            equity_acumulada = 0.0
            pico_equity = 0.0
            drawdown_maximo = 0.0

            for row in rows:
                pnl = float(row["pl_final"] or 0.0)
                preco_entrada = float(row["preco_entrada"] or 0.0)

                pnl_total_reais += pnl
                notional_total += abs(preco_entrada)

                if pnl > 0:
                    total_ganhos += 1
                elif pnl < 0:
                    total_perdas += 1
                else:
                    total_breakeven += 1

                equity_acumulada += pnl
                pico_equity = max(pico_equity, equity_acumulada)
                drawdown_atual = equity_acumulada - pico_equity
                drawdown_maximo = min(drawdown_maximo, drawdown_atual)

            win_rate = (
                round((total_ganhos / total_trades) * 100.0, 2)
                if total_trades > 0
                else 0.0
            )
            pnl_total_pct = (
                round((pnl_total_reais / notional_total) * 100.0, 2)
                if notional_total > 0
                else 0.0
            )
            drawdown_pct = (
                round((drawdown_maximo / pico_equity) * 100.0, 2)
                if pico_equity > 0 and drawdown_maximo < 0
                else 0.0
            )

            return TradeStats(
                total_trades=total_trades,
                total_ganhos=total_ganhos,
                total_perdas=total_perdas,
                total_breakeven=total_breakeven,
                win_rate=win_rate,
                pnl_total_reais=round(pnl_total_reais, 2),
                pnl_total_pct=pnl_total_pct,
                drawdown_maximo=round(drawdown_maximo, 2),
                drawdown_pct=drawdown_pct,
            )
        except Exception as exc:
            logger.warning("Falha ao calcular trade stats do dashboard: %s", exc)
            return self._trade_stats_zeradas()
        finally:
            conn.close()

    def obter_trades_recentes(self, quantidade: int = 10) -> List[TradeRecente]:
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
                        motivo_fechamento=str(
                            row["motivo_encerramento"] or "NAO_INFORMADO"
                        ),
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
            payload["total_fechamentos"] = int(
                (total_row["total"] if total_row else 0) or 0
            )

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
                    "motivo_encerramento": str(
                        row["motivo_encerramento"] or "NAO_INFORMADO"
                    ),
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
        inicio_hoje = datetime.combine(datetime.now().date(), horario_time.min)
        return self._calcular_trade_stats_desde(inicio_hoje)

    def _calcular_stats_n_dias(self, n_dias: int) -> TradeStats:
        """Calcula stats para ultimos N dias."""
        janela = max(1, int(n_dias))
        since_dt = datetime.now() - timedelta(days=janela)
        return self._calcular_trade_stats_desde(since_dt)

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

        sharpe_ratio = 0.0
        profit_factor_bruto = 1.0
        tempo_posicao_media_minutos = 0.0

        conn = self._conectar_db()
        try:
            if conn is not None and self._tabela_existe(conn, "posicoes_encerradas"):
                inicio_hoje = datetime.combine(datetime.now().date(), horario_time.min)
                rows = conn.execute(
                    """
                    SELECT pl_final, preco_entrada, criado_em, encerrado_em
                    FROM posicoes_encerradas
                    WHERE datetime(encerrado_em) >= datetime(?)
                    ORDER BY datetime(encerrado_em) ASC
                    """,
                    (inicio_hoje.isoformat(),),
                ).fetchall()

                pnl_series_pct: List[float] = []
                soma_ganhos = 0.0
                soma_perdas = 0.0
                duracoes: List[float] = []

                for row in rows:
                    pnl = float(row["pl_final"] or 0.0)
                    preco_entrada = float(row["preco_entrada"] or 0.0)
                    if preco_entrada:
                        pnl_series_pct.append((pnl / preco_entrada) * 100.0)
                    if pnl > 0:
                        soma_ganhos += pnl
                    elif pnl < 0:
                        soma_perdas += abs(pnl)

                    abertura = self._parse_timestamp(row["criado_em"])
                    fechamento = self._parse_timestamp(row["encerrado_em"])
                    if abertura and fechamento:
                        duracao = max(
                            0.0,
                            (fechamento - abertura).total_seconds() / 60.0,
                        )
                        duracoes.append(duracao)

                sharpe_ratio = round(self.calcular_sharpe_ratio(pnl_series_pct), 4)
                if soma_perdas > 0:
                    profit_factor_bruto = round(soma_ganhos / soma_perdas, 2)
                elif soma_ganhos > 0:
                    profit_factor_bruto = round(soma_ganhos, 2)
                else:
                    profit_factor_bruto = 0.0
                tempo_posicao_media_minutos = (
                    round(mean(duracoes), 2) if duracoes else 0.0
                )
        except Exception as exc:
            logger.warning("Falha ao calcular metricas operacionais: %s", exc)
        finally:
            if conn is not None:
                conn.close()

        return OperationalMetrics(
            sharpe_ratio=sharpe_ratio,
            profit_factor_bruto=profit_factor_bruto,
            tempo_posicao_media_minutos=tempo_posicao_media_minutos,
            percentual_fechamento_tp=_percentual("TAKE_PROFIT", "TP_HIT"),
            percentual_fechamento_sl=_percentual("STOP_LOSS", "SL_HIT"),
            percentual_fechamento_manual=_percentual("MANUAL_CLOSE"),
        )

    def _obter_protection_status(self) -> ProtectionStatus:
        """Obtem status atual de protecoes ativas."""
        limite_trades_hora = 3
        cooldown_base_segundos = 300
        agora = datetime.now()
        horario_permite = horario_time(9, 0) <= agora.time() <= horario_time(17, 30)

        conn = self._conectar_db()
        if conn is None:
            return ProtectionStatus(
                trades_ultima_hora=0,
                limite_trades_hora=limite_trades_hora,
                cooldown_segundos_restantes=0,
                total_bloqueios_hora=0,
                contador_perda_consecutiva=0,
                horario_permite_tradear=horario_permite,
            )

        try:
            since_uma_hora = (agora - timedelta(hours=1)).isoformat()
            trades_ultima_hora = 0
            cooldown_segundos_restantes = 0
            total_bloqueios_hora = 0
            contador_perda_consecutiva = 0

            if self._tabela_existe(conn, "posicoes_encerradas"):
                row = conn.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM posicoes_encerradas
                    WHERE datetime(encerrado_em) >= datetime(?)
                    """,
                    (since_uma_hora,),
                ).fetchone()
                trades_ultima_hora = int((row["total"] if row else 0) or 0)

                recentes = conn.execute(
                    """
                    SELECT pl_final, encerrado_em
                    FROM posicoes_encerradas
                    ORDER BY datetime(encerrado_em) DESC, trade_id DESC
                    LIMIT 20
                    """
                ).fetchall()

                if recentes:
                    ultimo_encerramento = self._parse_timestamp(
                        recentes[0]["encerrado_em"]
                    )
                    if ultimo_encerramento is not None:
                        segundos_decorridos = max(
                            0,
                            int((agora - ultimo_encerramento).total_seconds()),
                        )
                        cooldown_segundos_restantes = max(
                            0,
                            cooldown_base_segundos - segundos_decorridos,
                        )

                    for row_recente in recentes:
                        pnl = float(row_recente["pl_final"] or 0.0)
                        if pnl < 0:
                            contador_perda_consecutiva += 1
                        else:
                            break

            if self._tabela_existe(conn, "micro_trend_bloqueios"):
                row_bloqueios = conn.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM micro_trend_bloqueios
                    WHERE datetime(timestamp) >= datetime(?)
                    """,
                    (since_uma_hora,),
                ).fetchone()
                total_bloqueios_hora = int(
                    (row_bloqueios["total"] if row_bloqueios else 0) or 0
                )
            elif self._tabela_existe(conn, "eventos_monitoramento"):
                row_bloqueios = conn.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM eventos_monitoramento
                    WHERE datetime(timestamp) >= datetime(?)
                      AND (
                        LOWER(tipo_evento) LIKE '%bloqueio%'
                        OR LOWER(tipo_evento) LIKE '%cooldown%'
                        OR LOWER(tipo_evento) LIKE '%limit%'
                      )
                    """,
                    (since_uma_hora,),
                ).fetchone()
                total_bloqueios_hora = int(
                    (row_bloqueios["total"] if row_bloqueios else 0) or 0
                )

            return ProtectionStatus(
                trades_ultima_hora=trades_ultima_hora,
                limite_trades_hora=limite_trades_hora,
                cooldown_segundos_restantes=cooldown_segundos_restantes,
                total_bloqueios_hora=total_bloqueios_hora,
                contador_perda_consecutiva=contador_perda_consecutiva,
                horario_permite_tradear=horario_permite,
            )
        except Exception as exc:
            logger.warning("Falha ao obter protection status do dashboard: %s", exc)
            return ProtectionStatus(
                trades_ultima_hora=0,
                limite_trades_hora=limite_trades_hora,
                cooldown_segundos_restantes=0,
                total_bloqueios_hora=0,
                contador_perda_consecutiva=0,
                horario_permite_tradear=horario_permite,
            )
        finally:
            conn.close()

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
        sharpe = ((media - taxa_livre_risco) / desvio) * (periodo_dias**0.5)

        # Sharpe não pode ser negativo
        if sharpe < 0.0:
            return 0.0
        return float(sharpe)

    def exportar_para_json(self) -> Dict[str, Any]:
        """Exporta snapshot dashboard em JSON estruturado."""
        snapshot = self.obter_snapshot_dashboard()
        return snapshot.para_dict()
