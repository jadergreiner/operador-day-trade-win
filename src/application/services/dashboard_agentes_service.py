"""BLID-040: Dashboard Unificado dos Agentes RL.

Responsabilidades:
- Consultar tabela `trades` filtrada por magic_number e janela de 7 dias
- Calcular status, metricas, equity curve e lista de trades por agente RL
- Retornar payloads zerados (HTTP 200) quando banco ausente (ADR-023)

Agentes suportados:
    rl_5000 (magic=234500) | rl_direto (magic=234600)

ADR: ADR-001 (SQLite direto), ADR-012 (magic numbers), ADR-017 (lookback 7d),
     ADR-023 (banco ausente -> payload zerado sem exception)
Status: Implementacao v1.0
"""
from __future__ import annotations

import logging
import math
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from config.settings import AGENT_MAGIC_NUMBERS

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes internas
# ---------------------------------------------------------------------------

_LOOKBACK_DIAS: int = 7
_MAX_TRADES_POR_AGENTE: int = 10

# ---------------------------------------------------------------------------
# Dataclasses de dominio
# ---------------------------------------------------------------------------


@dataclass
class AgenteStatus:
    """Status operacional de um agente RL no dia atual.

    Campos:
        magic_number: identificador unico do agente no MT5
        banco_disponivel: True se o banco SQLite esta acessivel
        trades_hoje: total de trades registrados no dia
        trades_abertas: trades sem exit_time (posicoes abertas)
        pnl_hoje: lucro/prejuizo total de trades fechados no dia
        win_rate: taxa de acerto entre 0.0 e 1.0 (trades fechados com P&L)
        status: ATIVO, AGUARDANDO ou OFFLINE
    """

    magic_number: int
    banco_disponivel: bool
    trades_hoje: int
    trades_abertas: int
    pnl_hoje: float
    win_rate: float
    status: str  # "ATIVO", "AGUARDANDO", "OFFLINE"


@dataclass
class AgenteMetricas:
    """Metricas de performance de um agente RL nos ultimos 7 dias.

    Campos:
        magic_number: identificador unico do agente no MT5
        banco_disponivel: True se o banco SQLite esta acessivel
        sharpe_ratio: indice de Sharpe calculado sobre os retornos diarios
        profit_factor: total_ganhos / total_perdas; 0.0 quando sem perdas
        drawdown_maximo_reais: maior drawdown da equity curve em reais
        win_rate_7d: taxa de acerto nos ultimos 7 dias
        total_trades_7d: total de trades fechados com P&L nos ultimos 7 dias
    """

    magic_number: int
    banco_disponivel: bool
    sharpe_ratio: float
    profit_factor: float
    drawdown_maximo_reais: float
    win_rate_7d: float
    total_trades_7d: int


@dataclass
class TradeInfo:
    """Informacoes de um trade individual.

    Campos:
        magic_number: identificador do agente responsavel
        side: direcao (BUY ou SELL)
        entry_price: preco de entrada (None se nao disponivel)
        exit_price: preco de saida (None se nao disponivel)
        profit_loss: resultado financeiro em reais (None se aberto)
        status: estado do trade (ex: CLOSED, OPEN)
        entry_time: timestamp de abertura (YYYY-MM-DD HH:MM:SS)
        exit_time: timestamp de fechamento ou None se aberto
    """

    magic_number: int
    side: str
    entry_price: float | None
    exit_price: float | None
    profit_loss: float | None
    status: str
    entry_time: str
    exit_time: str | None


@dataclass
class EquityPoint:
    """Ponto diario da equity curve dos agentes RL.

    Campos:
        data: data no formato YYYY-MM-DD
        pnl_rl_5000: PnL acumulado do dia para o agente RL 5000
        pnl_rl_direto: PnL acumulado do dia para o agente RL Direto
    """

    data: str  # YYYY-MM-DD
    pnl_rl_5000: float
    pnl_rl_direto: float


@dataclass
class DashboardStatusPayload:
    """Payload de resposta do endpoint /status.

    Campos:
        banco_disponivel: True se pelo menos um banco esta acessivel
        agentes: lista de AgenteStatus por agente
        timestamp: ISO UTC do momento da consulta
    """

    banco_disponivel: bool
    agentes: list[AgenteStatus]
    timestamp: str


@dataclass
class DashboardMetricasPayload:
    """Payload de resposta do endpoint /metricas.

    Campos:
        banco_disponivel: True se pelo menos um banco esta acessivel
        agentes: lista de AgenteMetricas por agente
        timestamp: ISO UTC do momento da consulta
    """

    banco_disponivel: bool
    agentes: list[AgenteMetricas]
    timestamp: str


@dataclass
class DashboardTradesPayload:
    """Payload de resposta do endpoint /trades.

    Campos:
        banco_disponivel: True se pelo menos um banco esta acessivel
        trades: lista de TradeInfo (max 10 por agente)
        timestamp: ISO UTC do momento da consulta
    """

    banco_disponivel: bool
    trades: list[TradeInfo]
    timestamp: str


@dataclass
class DashboardEquityPayload:
    """Payload de resposta do endpoint /equity.

    Campos:
        banco_disponivel: True se pelo menos um banco esta acessivel
        series: lista de EquityPoint ordenada por data ASC
        timestamp: ISO UTC do momento da consulta
    """

    banco_disponivel: bool
    series: list[EquityPoint]
    timestamp: str


# ---------------------------------------------------------------------------
# Funcoes auxiliares de calculo (modulo-level)
# ---------------------------------------------------------------------------


def _calcular_drawdown_max(profits: list[float]) -> float:
    """Calcular o maximo drawdown da equity curve.

    Algoritmo:
    - Acumula os profits sequencialmente (equity curve)
    - Rastreia o pico corrente
    - Drawdown em cada ponto = peak - equity_corrente
    - Retorna o maior drawdown encontrado

    Args:
        profits: lista de lucros/prejuizos ordenada por tempo

    Returns:
        Maximo drawdown >= 0.0; retorna 0.0 para lista vazia
    """
    if not profits:
        return 0.0

    equity = 0.0
    peak = 0.0
    drawdown_max = 0.0

    for lucro in profits:
        equity += lucro
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > drawdown_max:
            drawdown_max = drawdown

    return drawdown_max


def _calcular_sharpe(profits: list[float]) -> float:
    """Calcular o indice de Sharpe sobre os retornos.

    Usa media / desvio_padrao dos profits (sem risk-free rate).
    Retorna 0.0 para menos de 2 observacoes ou desvio zero.

    Args:
        profits: lista de lucros/prejuizos

    Returns:
        Sharpe ratio; 0.0 se nao calculavel
    """
    if len(profits) < 2:
        return 0.0

    media = sum(profits) / len(profits)
    variancia = sum((p - media) ** 2 for p in profits) / len(profits)
    desvio = math.sqrt(variancia)

    if desvio == 0.0:
        return 0.0

    return media / desvio


def _timestamp_utc() -> str:
    """Retornar timestamp atual em ISO UTC.

    Returns:
        String no formato ISO 8601 com timezone UTC
    """
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Service principal
# ---------------------------------------------------------------------------


class DashboardAgentesService:
    """Service de consulta unificada dos agentes RL para o dashboard.

    Implementa ADR-023: banco ausente retorna payload zerado sem exception.
    Implementa ADR-017: lookback maximo de 7 dias em todas as queries.
    Implementa ADR-001: SQLite direto via sqlite3, sem ORM.
    Implementa ADR-012: magic numbers importados de config/settings.py.

    Args:
        db_path: caminho do banco SQLite. Se None, usa caminhos padrao.
                 Se fornecido, usa o mesmo banco para ambos os agentes.
                 Util para modo de teste com banco unico.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._magic_rl_5000: int = AGENT_MAGIC_NUMBERS["rl_5000"]
        self._magic_rl_direto: int = AGENT_MAGIC_NUMBERS["rl_direto"]

        if db_path is not None:
            caminho = Path(db_path)
            self._db_rl_5000: Path = caminho
            self._db_rl_direto: Path = caminho
        else:
            self._db_rl_5000 = Path("data/db/trading.db")
            self._db_rl_direto = Path("data/db/trading.db")

    # ------------------------------------------------------------------
    # Metodos publicos
    # ------------------------------------------------------------------

    def obter_status(self) -> DashboardStatusPayload:
        """Obter status atual dos agentes RL (dia corrente).

        Calcula por agente: trades_hoje, trades_abertas, pnl_hoje, win_rate.
        Trades abertos (sem exit_time) e trades com profit_loss NULL sao
        excluidos do calculo de pnl e win_rate.

        Returns:
            DashboardStatusPayload com status de cada agente.
            Se banco ausente, retorna payload zerado (ADR-023).
        """
        timestamp = _timestamp_utc()

        if not self._banco_disponivel():
            agentes = [
                _status_zerado(magic)
                for magic in [self._magic_rl_5000, self._magic_rl_direto]
            ]
            return DashboardStatusPayload(
                banco_disponivel=False,
                agentes=agentes,
                timestamp=timestamp,
            )

        agentes = []
        for magic, db_path in self._iter_agentes():
            agentes.append(self._calcular_status_agente(magic, db_path))

        return DashboardStatusPayload(
            banco_disponivel=True,
            agentes=agentes,
            timestamp=timestamp,
        )

    def obter_metricas(self) -> DashboardMetricasPayload:
        """Obter metricas de performance dos agentes RL nos ultimos 7 dias.

        Calcula por agente: profit_factor, sharpe_ratio, drawdown_maximo,
        win_rate_7d, total_trades_7d.
        profit_factor retorna 0.0 quando nao ha perdas (evita divisao por zero).

        Returns:
            DashboardMetricasPayload com metricas de cada agente.
            Se banco ausente, retorna payload zerado (ADR-023).
        """
        timestamp = _timestamp_utc()

        if not self._banco_disponivel():
            agentes_m = [
                _metricas_zeradas(magic)
                for magic in [self._magic_rl_5000, self._magic_rl_direto]
            ]
            return DashboardMetricasPayload(
                banco_disponivel=False,
                agentes=agentes_m,
                timestamp=timestamp,
            )

        agentes_m = []
        for magic, db_path in self._iter_agentes():
            agentes_m.append(self._calcular_metricas_agente(magic, db_path))

        return DashboardMetricasPayload(
            banco_disponivel=True,
            agentes=agentes_m,
            timestamp=timestamp,
        )

    def obter_trades(self) -> DashboardTradesPayload:
        """Obter lista dos ultimos trades de cada agente (max 10 por agente).

        Retorna os trades mais recentes ordenados por entry_time DESC.
        Os trades de cada agente sao isolados por magic_number.

        Returns:
            DashboardTradesPayload com lista de trades.
            Se banco ausente, retorna lista vazia (ADR-023).
        """
        timestamp = _timestamp_utc()

        if not self._banco_disponivel():
            return DashboardTradesPayload(
                banco_disponivel=False,
                trades=[],
                timestamp=timestamp,
            )

        todos_trades: list[TradeInfo] = []
        for magic, db_path in self._iter_agentes():
            trades = self._consultar_ultimos_trades(magic, db_path)
            todos_trades.extend(trades)

        return DashboardTradesPayload(
            banco_disponivel=True,
            trades=todos_trades,
            timestamp=timestamp,
        )

    def obter_equity(self) -> DashboardEquityPayload:
        """Obter equity curve diaria dos ultimos 7 dias.

        Agrega PnL por dia para cada agente. Apenas dias com dados sao
        incluidos na serie. Trades alem de 7 dias sao ignorados (ADR-017).

        Returns:
            DashboardEquityPayload com serie temporal de PnL por dia.
            Se banco ausente, retorna serie vazia (ADR-023).
        """
        timestamp = _timestamp_utc()

        if not self._banco_disponivel():
            return DashboardEquityPayload(
                banco_disponivel=False,
                series=[],
                timestamp=timestamp,
            )

        series = self._calcular_equity_curve()

        return DashboardEquityPayload(
            banco_disponivel=True,
            series=series,
            timestamp=timestamp,
        )

    # ------------------------------------------------------------------
    # Metodos privados - calculo por agente
    # ------------------------------------------------------------------

    def _calcular_status_agente(self, magic: int, db_path: Path) -> AgenteStatus:
        """Calcular status de um agente para o dia atual.

        Consulta trades hoje filtrados por magic_number. Trades abertos e
        trades com profit_loss NULL sao excluidos do pnl e win_rate.

        Args:
            magic: numero magico do agente
            db_path: caminho do banco SQLite

        Returns:
            AgenteStatus preenchido; zerado em caso de erro de banco
        """
        hoje = str(date.today())

        try:
            # ADR-001: conexao somente-leitura via URI SQLite
            uri = f"file:{db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=10)
            try:
                # Profits de trades fechados com P&L valido hoje
                cursor = conn.execute(
                    """
                    SELECT profit_loss FROM trades
                    WHERE magic_number = ?
                      AND date(entry_time) = ?
                      AND exit_time IS NOT NULL
                      AND profit_loss IS NOT NULL
                    """,
                    (magic, hoje),
                )
                profits_fechados: list[float] = [
                    float(row[0]) for row in cursor.fetchall()
                ]

                # Contagem de trades abertos (sem exit_time)
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM trades
                    WHERE magic_number = ?
                      AND date(entry_time) = ?
                      AND exit_time IS NULL
                    """,
                    (magic, hoje),
                )
                row_abertos = cursor.fetchone()
                trades_abertas = int(row_abertos[0]) if row_abertos else 0

                # Total de trades hoje (abertos e fechados)
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM trades
                    WHERE magic_number = ?
                      AND date(entry_time) = ?
                    """,
                    (magic, hoje),
                )
                row_total = cursor.fetchone()
                trades_hoje = int(row_total[0]) if row_total else 0

            finally:
                conn.close()

        except Exception as exc:
            _log.warning(
                "Erro ao consultar status do agente %d em %s: %s",
                magic,
                db_path,
                exc,
            )
            return _status_zerado(magic)

        pnl_hoje = sum(profits_fechados)
        total_com_pl = len(profits_fechados)
        wins = sum(1 for p in profits_fechados if p > 0)
        win_rate = wins / total_com_pl if total_com_pl > 0 else 0.0

        status = "ATIVO" if trades_hoje > 0 else "AGUARDANDO"

        return AgenteStatus(
            magic_number=magic,
            banco_disponivel=True,
            trades_hoje=trades_hoje,
            trades_abertas=trades_abertas,
            pnl_hoje=pnl_hoje,
            win_rate=win_rate,
            status=status,
        )

    def _calcular_metricas_agente(self, magic: int, db_path: Path) -> AgenteMetricas:
        """Calcular metricas de performance de um agente nos ultimos 7 dias.

        Exclui trades com profit_loss NULL e trades abertos.
        profit_factor retorna 0.0 quando soma de perdas e zero (ADR-023).

        Args:
            magic: numero magico do agente
            db_path: caminho do banco SQLite

        Returns:
            AgenteMetricas preenchido; zerado em caso de erro de banco
        """
        data_inicio = str(date.today() - timedelta(days=_LOOKBACK_DIAS))

        try:
            # ADR-001: conexao somente-leitura via URI SQLite
            uri = f"file:{db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=10)
            try:
                cursor = conn.execute(
                    """
                    SELECT profit_loss FROM trades
                    WHERE magic_number = ?
                      AND date(entry_time) >= ?
                      AND exit_time IS NOT NULL
                      AND profit_loss IS NOT NULL
                    ORDER BY entry_time ASC
                    """,
                    (magic, data_inicio),
                )
                profits: list[float] = [
                    float(row[0]) for row in cursor.fetchall()
                ]
            finally:
                conn.close()

        except Exception as exc:
            _log.warning(
                "Erro ao consultar metricas do agente %d em %s: %s",
                magic,
                db_path,
                exc,
            )
            return _metricas_zeradas(magic)

        total = len(profits)
        ganhos = [p for p in profits if p > 0]
        perdas = [p for p in profits if p < 0]

        soma_ganhos = sum(ganhos)
        soma_perdas = abs(sum(perdas))

        # profit_factor: 0.0 quando nao ha perdas (evita divisao por zero / infinito)
        profit_factor = soma_ganhos / soma_perdas if soma_perdas > 0.0 else 0.0

        win_rate_7d = len(ganhos) / total if total > 0 else 0.0
        drawdown = _calcular_drawdown_max(profits)
        sharpe = _calcular_sharpe(profits)

        return AgenteMetricas(
            magic_number=magic,
            banco_disponivel=True,
            sharpe_ratio=sharpe,
            profit_factor=profit_factor,
            drawdown_maximo_reais=drawdown,
            win_rate_7d=win_rate_7d,
            total_trades_7d=total,
        )

    def _consultar_ultimos_trades(
        self, magic: int, db_path: Path
    ) -> list[TradeInfo]:
        """Consultar os ultimos trades de um agente (max 10).

        Retorna trades ordenados por entry_time DESC (mais recentes primeiro).
        Colunas entry_price e exit_price sao None (nao disponiveis no schema).

        Args:
            magic: numero magico do agente
            db_path: caminho do banco SQLite

        Returns:
            Lista de TradeInfo com no maximo _MAX_TRADES_POR_AGENTE itens
        """
        try:
            # ADR-001: conexao somente-leitura via URI SQLite
            uri = f"file:{db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=10)
            try:
                cursor = conn.execute(
                    """
                    SELECT magic_number, side, entry_time, exit_time,
                           profit_loss, status
                    FROM trades
                    WHERE magic_number = ?
                    ORDER BY entry_time DESC
                    LIMIT ?
                    """,
                    (magic, _MAX_TRADES_POR_AGENTE),
                )
                rows = cursor.fetchall()
            finally:
                conn.close()

        except Exception as exc:
            _log.warning(
                "Erro ao consultar trades do agente %d em %s: %s",
                magic,
                db_path,
                exc,
            )
            return []

        resultado: list[TradeInfo] = []
        for row in rows:
            resultado.append(
                TradeInfo(
                    magic_number=int(row[0]),
                    side=str(row[1]),
                    entry_price=None,
                    exit_price=None,
                    profit_loss=float(row[4]) if row[4] is not None else None,
                    status=str(row[5]) if row[5] is not None else "DESCONHECIDO",
                    entry_time=str(row[2]),
                    exit_time=str(row[3]) if row[3] is not None else None,
                )
            )

        return resultado

    def _calcular_equity_curve(self) -> list[EquityPoint]:
        """Calcular equity curve diaria dos ultimos 7 dias.

        Agrega PnL por dia para cada agente. Apenas dias com dados de
        qualquer agente sao incluidos. Trades alem de 7 dias sao ignorados.

        Returns:
            Lista de EquityPoint ordenada por data ASC.
            Apenas dias com pelo menos um trade incluem-se na serie.
        """
        data_inicio = str(date.today() - timedelta(days=_LOOKBACK_DIAS))

        pnl_5000: dict[str, float] = {}
        pnl_direto: dict[str, float] = {}

        for magic, db_path, dicionario in [
            (self._magic_rl_5000, self._db_rl_5000, pnl_5000),
            (self._magic_rl_direto, self._db_rl_direto, pnl_direto),
        ]:
            try:
                # ADR-001: conexao somente-leitura via URI SQLite
                uri = f"file:{db_path}?mode=ro"
                conn = sqlite3.connect(uri, uri=True, timeout=10)
                try:
                    cursor = conn.execute(
                        """
                        SELECT date(entry_time) AS dia, SUM(profit_loss)
                        FROM trades
                        WHERE magic_number = ?
                          AND date(entry_time) >= ?
                          AND exit_time IS NOT NULL
                          AND profit_loss IS NOT NULL
                        GROUP BY dia
                        ORDER BY dia ASC
                        """,
                        (magic, data_inicio),
                    )
                    for row in cursor.fetchall():
                        pnl_valor = float(row[1]) if row[1] is not None else 0.0
                        dicionario[str(row[0])] = pnl_valor
                finally:
                    conn.close()

            except Exception as exc:
                _log.warning(
                    "Erro ao calcular equity do agente %d em %s: %s",
                    magic,
                    db_path,
                    exc,
                )

        todos_dias = sorted(set(pnl_5000.keys()) | set(pnl_direto.keys()))

        return [
            EquityPoint(
                data=dia,
                pnl_rl_5000=pnl_5000.get(dia, 0.0),
                pnl_rl_direto=pnl_direto.get(dia, 0.0),
            )
            for dia in todos_dias
        ]

    # ------------------------------------------------------------------
    # Metodos auxiliares internos
    # ------------------------------------------------------------------

    def _iter_agentes(self) -> list[tuple[int, Path]]:
        """Retornar lista de (magic_number, db_path) para cada agente.

        Returns:
            Lista com tupla (magic, db_path) para rl_5000 e rl_direto
        """
        return [
            (self._magic_rl_5000, self._db_rl_5000),
            (self._magic_rl_direto, self._db_rl_direto),
        ]

    def _banco_disponivel(self) -> bool:
        """Verificar se pelo menos um banco esta fisicamente disponivel.

        Returns:
            True se qualquer db_path existe no filesystem
        """
        return self._db_rl_5000.exists() or self._db_rl_direto.exists()


# ---------------------------------------------------------------------------
# Funcoes auxiliares privadas de modulo
# ---------------------------------------------------------------------------


def _status_zerado(magic: int) -> AgenteStatus:
    """Criar AgenteStatus zerado para uso quando banco esta ausente.

    Args:
        magic: numero magico do agente

    Returns:
        AgenteStatus com todos os campos numericos em zero e status OFFLINE
    """
    return AgenteStatus(
        magic_number=magic,
        banco_disponivel=False,
        trades_hoje=0,
        trades_abertas=0,
        pnl_hoje=0.0,
        win_rate=0.0,
        status="OFFLINE",
    )


def _metricas_zeradas(magic: int) -> AgenteMetricas:
    """Criar AgenteMetricas zerado para uso quando banco esta ausente.

    Args:
        magic: numero magico do agente

    Returns:
        AgenteMetricas com todos os campos numericos em zero
    """
    return AgenteMetricas(
        magic_number=magic,
        banco_disponivel=False,
        sharpe_ratio=0.0,
        profit_factor=0.0,
        drawdown_maximo_reais=0.0,
        win_rate_7d=0.0,
        total_trades_7d=0,
    )
