"""
Repositorio de ganhos diarios para o LimitadorGanhoDiario.

Responsabilidades:
- Persistir P&L de cada operacao por data de pregao e agent_id
- Consultar total de ganhos no dia (somando todos os agentes)
- Consultar ganhos de um agente especifico no dia
- Garantir escrita concorrente segura via sqlite_write_lock

Schema:
    ganhos_diarios (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        data_pregao         TEXT NOT NULL,   -- "YYYY-MM-DD"
        agent_id            TEXT NOT NULL,
        pnl_reais           REAL NOT NULL,
        ticket              INTEGER,
        timestamp_registro  TEXT NOT NULL    -- ISO 8601
    )

Status: v1.0 (24/03/2026)
Referencia: docs/BACKLOG.md (Camada Risco Externo - Ganho Diario)
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock


class IGanhosDiarioRepository(ABC):
    """Interface para repositorio de ganhos diarios."""

    @abstractmethod
    def registrar_pnl(
        self,
        data_pregao: str,
        agent_id: str,
        pnl_reais: float,
        ticket: Optional[int] = None,
    ) -> None:
        """
        Registra o P&L de uma operacao encerrada.

        Args:
            data_pregao: Data do pregao no formato "YYYY-MM-DD".
            agent_id: Identificador do agente que realizou a operacao.
            pnl_reais: Resultado da operacao em R$ (positivo=ganho, negativo=perda).
            ticket: Numero do ticket da ordem no broker (opcional).
        """
        ...

    @abstractmethod
    def consultar_total_dia(self, data_pregao: str) -> float:
        """
        Consulta o ganho total do pregao somando todos os agentes.

        Args:
            data_pregao: Data no formato "YYYY-MM-DD".

        Returns:
            Soma de todos os pnl_reais do dia (pode ser negativo).
        """
        ...

    @abstractmethod
    def consultar_por_agente(
        self, data_pregao: str, agent_id: str
    ) -> float:
        """
        Consulta o ganho de um agente especifico no pregao.

        Args:
            data_pregao: Data no formato "YYYY-MM-DD".
            agent_id: Identificador do agente.

        Returns:
            Soma dos pnl_reais do agente no dia.
        """
        ...


class RepositorioGanhoDiarioEmMemoria(IGanhosDiarioRepository):
    """
    Implementacao em memoria para uso em testes.

    Nao persiste dados entre execucoes.
    """

    def __init__(self) -> None:
        self._data_pregao: list[str] = []
        self._agent_ids: list[str] = []
        self._pnls: list[float] = []
        self._tickets: list[Optional[int]] = []

    def registrar_pnl(
        self,
        data_pregao: str,
        agent_id: str,
        pnl_reais: float,
        ticket: Optional[int] = None,
    ) -> None:
        self._data_pregao.append(data_pregao)
        self._agent_ids.append(agent_id)
        self._pnls.append(pnl_reais)
        self._tickets.append(ticket)

    def consultar_total_dia(self, data_pregao: str) -> float:
        return sum(
            pnl
            for data, pnl in zip(self._data_pregao, self._pnls)
            if data == data_pregao
        )

    def consultar_por_agente(
        self, data_pregao: str, agent_id: str
    ) -> float:
        return sum(
            pnl
            for data, agente, pnl in zip(
                self._data_pregao, self._agent_ids, self._pnls
            )
            if data == data_pregao and agente == agent_id
        )


class SqliteGanhosDiarioRepository(IGanhosDiarioRepository):
    """
    Implementacao SQLite do repositorio de ganhos diarios.

    Cria a tabela automaticamente se nao existir.
    Usa sqlite_write_lock para escrita segura entre multiplos agentes.
    """

    _CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS ganhos_diarios (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            data_pregao         TEXT NOT NULL,
            agent_id            TEXT NOT NULL,
            pnl_reais           REAL NOT NULL,
            ticket              INTEGER,
            timestamp_registro  TEXT NOT NULL
        )
    """
    _CREATE_INDEX = """
        CREATE INDEX IF NOT EXISTS idx_ganhos_data_pregao
        ON ganhos_diarios (data_pregao)
    """

    def __init__(self, db_path: str = "data/db/trading.db") -> None:
        self._db_path = db_path
        self._inicializar_schema()

    def _inicializar_schema(self) -> None:
        """Cria tabela e indice se nao existirem."""
        with sqlite_write_lock(self._db_path):
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute(self._CREATE_TABLE)
                conn.execute(self._CREATE_INDEX)
                conn.commit()
            finally:
                conn.close()

    def registrar_pnl(
        self,
        data_pregao: str,
        agent_id: str,
        pnl_reais: float,
        ticket: Optional[int] = None,
    ) -> None:
        agora = datetime.now(tz=timezone.utc).isoformat()
        with sqlite_write_lock(self._db_path):
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute(
                    """
                    INSERT INTO ganhos_diarios
                        (data_pregao, agent_id, pnl_reais, ticket, timestamp_registro)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (data_pregao, agent_id, pnl_reais, ticket, agora),
                )
                conn.commit()
            finally:
                conn.close()

    def consultar_total_dia(self, data_pregao: str) -> float:
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute(
                "SELECT COALESCE(SUM(pnl_reais), 0.0) FROM ganhos_diarios "
                "WHERE data_pregao = ?",
                (data_pregao,),
            )
            row = cursor.fetchone()
            return float(row[0]) if row else 0.0
        finally:
            conn.close()

    def consultar_por_agente(
        self, data_pregao: str, agent_id: str
    ) -> float:
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute(
                "SELECT COALESCE(SUM(pnl_reais), 0.0) FROM ganhos_diarios "
                "WHERE data_pregao = ? AND agent_id = ?",
                (data_pregao, agent_id),
            )
            row = cursor.fetchone()
            return float(row[0]) if row else 0.0
        finally:
            conn.close()
