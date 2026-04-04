"""Servico de correlacao entre entradas do journal e trades executados.

BLID-022 / ROADMAP-DIARIOS-02.

Correlaciona narrativas de mercado com trades fechados via magic_number=234800
dentro de uma janela de tempo configuravel, para alimentar aprendizado por
reforco (ML/RL).

Pipeline:
    correlacionar_sessao(data)
    -> ler trading_journal_logs para data
    -> para cada entrada, buscar trade com maior |profit| em diary_orders
       na janela de 30 minutos (magic_number=234800)
    -> registrar outcome (WIN/LOSS/BREAKEVEN/SEM_TRADE) em
       journal_trade_correlation via UPSERT

Status: Implementacao v1.0 (04/04/2026)
Referencia: docs/BACKLOG.md (BLID-022 / ROADMAP-DIARIOS-02)
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, TypedDict

from src.infrastructure.database.diario_journal_schema import (
    criar_tabelas_diario,
    obter_conexao_diario,
)
from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock

logger = logging.getLogger(__name__)

# Outcomes validos para journal_trade_correlation
_OUTCOME_WIN = "WIN"
_OUTCOME_LOSS = "LOSS"
_OUTCOME_BREAKEVEN = "BREAKEVEN"
_OUTCOME_SEM_TRADE = "SEM_TRADE"

# Lados de ordem validos para calculo de alinhamento
_LADOS_VALIDOS = {"BUY", "SELL"}


class _EntradaJournal(TypedDict):
    """Estrutura de uma entrada de trading_journal_logs."""

    entry_id: str
    timestamp: str
    decision: str


class _TradeCorrelacionado(TypedDict):
    """Estrutura de um trade de diary_orders para correlacao."""

    ticket: int
    profit: float
    side: str


class _DadosCorrelacao(TypedDict):
    """Dados a inserir em journal_trade_correlation."""

    journal_entry_id: str
    trade_ticket: Optional[int]
    outcome: str
    pnl_reais: Optional[float]
    narrativa_estava_alinhada: Optional[int]
    created_at: str


class JournalTradeCorrelatorService:
    """Correlaciona entradas do diario de mercado com trades executados.

    Para cada entrada de trading_journal_logs de uma data de referencia,
    busca o trade com maior |profit| fechado dentro da janela de tempo
    configurada e registra o outcome em journal_trade_correlation.

    Args:
        db_path: Caminho para o banco SQLite contendo ambas as tabelas.
        magic_number: Magic number do EA para filtrar trades (padrao 234800).
        janela_minutos: Janela em minutos apos o timestamp da entrada
                        para buscar trades correlacionados (padrao 30).
    """

    def __init__(
        self,
        db_path: Path,
        magic_number: int = 234800,
        janela_minutos: int = 30,
    ) -> None:
        self._db_path = db_path
        self._magic_number = magic_number
        self._janela_minutos = janela_minutos
        criar_tabelas_diario(db_path)

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------

    def correlacionar_sessao(self, data_referencia: str) -> int:
        """Correlaciona todas as entradas de journal de uma data com trades.

        Para cada entrada:
        - Busca trades filtrados por magic_number dentro da janela
        - Registra outcome via UPSERT (INSERT OR REPLACE)
        - Multiplos trades na janela: usa o de maior |profit|

        Args:
            data_referencia: Data no formato YYYY-MM-DD.

        Returns:
            Numero de correlacoes inseridas ou atualizadas.
        """
        entradas = self._buscar_entradas_journal(data_referencia)
        if not entradas:
            logger.info(
                "Nenhuma entrada de journal para %s", data_referencia
            )
            return 0

        contagem = 0
        for entrada in entradas:
            trade = self._buscar_trade_correlacionado(entrada["timestamp"])
            correlacao = self._construir_correlacao(
                entrada["entry_id"], entrada["decision"], trade
            )
            self._upsert_correlacao(correlacao)
            contagem += 1

        return contagem

    # ------------------------------------------------------------------
    # Metodos privados — leitura
    # ------------------------------------------------------------------

    def _buscar_entradas_journal(
        self, data_referencia: str
    ) -> list[_EntradaJournal]:
        """Retorna entradas do journal para a data informada."""
        conn = obter_conexao_diario(self._db_path)
        try:
            cursor = conn.execute(
                """
                SELECT entry_id, timestamp, decision
                FROM trading_journal_logs
                WHERE timestamp LIKE ?
                ORDER BY timestamp ASC
                """,
                (f"{data_referencia}%",),
            )
            resultado: list[_EntradaJournal] = []
            for row in cursor.fetchall():
                resultado.append(
                    _EntradaJournal(
                        entry_id=str(row[0]),
                        timestamp=str(row[1]),
                        decision=str(row[2]),
                    )
                )
            return resultado
        finally:
            conn.close()

    def _buscar_trade_correlacionado(
        self, timestamp_str: str
    ) -> Optional[_TradeCorrelacionado]:
        """Busca o trade mais relevante (maior |profit|) na janela de tempo.

        Args:
            timestamp_str: Timestamp ISO da entrada de journal.

        Returns:
            Dicionario com dados do trade, ou None se nao encontrado.
        """
        try:
            ts_inicio = datetime.fromisoformat(timestamp_str)
        except ValueError:
            logger.warning("Timestamp invalido: %s", timestamp_str)
            return None

        ts_fim = ts_inicio + timedelta(minutes=self._janela_minutos)

        conn = obter_conexao_diario(self._db_path)
        try:
            tabela_existe = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='diary_orders'"
            ).fetchone()

            if not tabela_existe:
                logger.warning(
                    "Tabela diary_orders nao encontrada em %s — fallback SEM_TRADE",
                    self._db_path,
                )
                return None

            cursor = conn.execute(
                """
                SELECT ticket, profit, side
                FROM diary_orders
                WHERE magic_number = ?
                  AND close_time >= ?
                  AND close_time <= ?
                ORDER BY ABS(profit) DESC
                LIMIT 1
                """,
                (
                    self._magic_number,
                    ts_inicio.isoformat(),
                    ts_fim.isoformat(),
                ),
            )
            row = cursor.fetchone()
            if row is None:
                return None

            return _TradeCorrelacionado(
                ticket=int(row[0]),
                profit=float(row[1]),
                side=str(row[2]),
            )
        except sqlite3.OperationalError as exc:
            logger.warning("Erro ao buscar trades em diary_orders: %s", exc)
            return None
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Metodos privados — construcao e escrita
    # ------------------------------------------------------------------

    def _construir_correlacao(
        self,
        entry_id: str,
        decision: str,
        trade: Optional[_TradeCorrelacionado],
    ) -> _DadosCorrelacao:
        """Constroi o dicionario de correlacao para persistencia.

        Invariante SEM_TRADE: quando trade=None, trade_ticket, pnl_reais e
        narrativa_estava_alinhada sao None.

        Args:
            entry_id: ID da entrada de journal.
            decision: Decisao sugerida pela narrativa (BUY/SELL/HOLD).
            trade: Dados do trade correlacionado, ou None.

        Returns:
            _DadosCorrelacao pronto para UPSERT.
        """
        agora = datetime.now().isoformat()

        if trade is None:
            return _DadosCorrelacao(
                journal_entry_id=entry_id,
                trade_ticket=None,
                outcome=_OUTCOME_SEM_TRADE,
                pnl_reais=None,
                narrativa_estava_alinhada=None,
                created_at=agora,
            )

        profit: float = trade["profit"]
        side: str = trade["side"]
        ticket: int = trade["ticket"]

        if profit > 0:
            outcome = _OUTCOME_WIN
        elif profit < 0:
            outcome = _OUTCOME_LOSS
        else:
            outcome = _OUTCOME_BREAKEVEN

        # Alinhamento: apenas para lados reconhecidos (BUY/SELL)
        decision_upper = decision.upper()
        side_upper = side.upper()
        if decision_upper not in _LADOS_VALIDOS or side_upper not in _LADOS_VALIDOS:
            logger.warning(
                "Alinhamento indefinido: decision=%r side=%r — registrando 0",
                decision,
                side,
            )
            alinhado: int = 0
        else:
            alinhado = 1 if decision_upper == side_upper else 0

        return _DadosCorrelacao(
            journal_entry_id=entry_id,
            trade_ticket=ticket,
            outcome=outcome,
            pnl_reais=profit,
            narrativa_estava_alinhada=alinhado,
            created_at=agora,
        )

    def _upsert_correlacao(self, correlacao: _DadosCorrelacao) -> None:
        """Insere ou substitui correlacao em journal_trade_correlation.

        Usa INSERT OR REPLACE para garantir unicidade por journal_entry_id.
        Usa obter_conexao_diario() para consistencia de PRAGMAs (WAL +
        busy_timeout) na conexao de escrita.

        Args:
            correlacao: Dados tipados da correlacao.
        """
        with sqlite_write_lock(self._db_path):
            conn = obter_conexao_diario(self._db_path)
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO journal_trade_correlation (
                        journal_entry_id, trade_ticket, outcome,
                        pnl_reais, narrativa_estava_alinhada, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        correlacao["journal_entry_id"],
                        correlacao["trade_ticket"],
                        correlacao["outcome"],
                        correlacao["pnl_reais"],
                        correlacao["narrativa_estava_alinhada"],
                        correlacao["created_at"],
                    ),
                )
                conn.commit()
            finally:
                conn.close()
