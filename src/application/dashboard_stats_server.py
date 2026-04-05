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
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
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

    def __init__(self) -> None:
        """Inicializa StatsQueryService."""
        # TODO: Conectar SQLite database aqui quando BD estiver ready
        # Para agora, retorno dados estruturados vazio/default
        self.db_path: Optional[str] = None

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
            pnl_nao_realizado_reais=pnl_nao_realizado_reais,
            ultima_atualizacao_precos=ultima_atualizacao_precos,
        )

    def obter_trades_recentes(
        self, quantidade: int = 10
    ) -> List[TradeRecente]:
        """
        Obtem ultimos N trades fechados.

        Args:
            quantidade: Numero maximo de trades a retornar

        Returns:
            Lista de TradeRecente (atualmente vazia, integrar com BD)
        """
        # TODO: Query SQLite position_closure_detector + trade_performance_tracker
        # SELECT * FROM trades WHERE status='FECHADA'
        # ORDER BY timestamp_fechamento DESC LIMIT :quantidade
        return []

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
        # TODO: Query dados de:
        # - trades: para sharpe, profit_factor, tempos
        # - position_closure_detector: para tipos fechamento
        return OperationalMetrics(
            sharpe_ratio=0.0,
            profit_factor_bruto=1.0,
            tempo_posicao_media_minutos=30.0,
            percentual_fechamento_tp=33.33,
            percentual_fechamento_sl=33.33,
            percentual_fechamento_manual=33.34,
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
