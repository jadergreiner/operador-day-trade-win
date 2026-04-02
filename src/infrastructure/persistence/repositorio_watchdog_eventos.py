"""
Repositorio SQLite para eventos de observabilidade dos diarios.

ROADMAP-DIARIOS-01: Persistencia de eventos de watchdog.

Responsabilidades:
- Criar tabela diarios_watchdog_eventos no SQLite
- Persistir eventos de gravacao, heartbeat, falha, reinicio e alerta
- Garantir fail-open: excecao de SQLite capturada como WARNING
- Eventos sao append-only (sem DELETE/UPDATE por design)

Tabela:
    diarios_watchdog_eventos (id, session_id, nome_thread, evento,
    estado_resultante, mensagem, stack_trace, gravacoes_sessao,
    created_at)

Status: Implementacao v1.0 (02/04/2026)
Referencia: docs/BACKLOG.md (ROADMAP-DIARIOS-01)
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("repositorio_watchdog_eventos")

# DDL da tabela — CREATE TABLE IF NOT EXISTS garante idempotencia
_DDL_TABELA = """
CREATE TABLE IF NOT EXISTS diarios_watchdog_eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    nome_thread TEXT NOT NULL,
    evento TEXT NOT NULL
        CHECK(evento IN
              ('GRAVACAO','HEARTBEAT','FALHA','REINICIO','ALERTA')),
    estado_resultante TEXT NOT NULL
        CHECK(estado_resultante IN
              ('rodando','pausado','com_erro','reiniciando',
               'aguardando_sinal')),
    mensagem TEXT,
    stack_trace TEXT,
    gravacoes_sessao INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
        DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);
"""

_DDL_IDX_SESSION = """
CREATE INDEX IF NOT EXISTS idx_watchdog_session
    ON diarios_watchdog_eventos(session_id);
"""

_DDL_IDX_THREAD = """
CREATE INDEX IF NOT EXISTS idx_watchdog_thread
    ON diarios_watchdog_eventos(nome_thread, created_at);
"""


@dataclass
class RegistroEvento:
    """Dados necessarios para persistir um evento de watchdog.

    Args:
        session_id: Identificador da sessao atual do painel.
        nome_thread: Nome da thread monitorada.
        evento: Tipo de evento (GRAVACAO/HEARTBEAT/FALHA/REINICIO/ALERTA).
        estado_resultante: Estado da thread apos o evento.
        gravacoes_sessao: Total de gravacoes acumuladas nesta sessao.
        mensagem: Mensagem opcional de contexto.
        stack_trace: Stack trace de excecao (apenas para FALHA).

    """

    session_id: str
    nome_thread: str
    evento: str
    estado_resultante: str
    gravacoes_sessao: int
    mensagem: Optional[str] = None
    stack_trace: Optional[str] = None


class RepositorioWatchdogEventos:
    """Repositorio de eventos de observabilidade dos diarios.

    Persiste eventos no SQLite com fail-open: se o banco estiver
    indisponivel, o evento e descartado com log WARNING — nunca
    levanta excecao para o chamador.

    Exemplo de uso:
        repo = RepositorioWatchdogEventos("data/db/trading.db")
        repo.inicializar()
        repo.inserir(RegistroEvento(
            session_id="abc123",
            nome_thread="TradingJournal",
            evento="GRAVACAO",
            estado_resultante="rodando",
            gravacoes_sessao=5,
        ))

    """

    def __init__(self, caminho_banco: str | Path) -> None:
        """Inicializa o repositorio com o caminho do banco.

        Args:
            caminho_banco: Caminho para o arquivo SQLite.

        """
        self._caminho = Path(caminho_banco)
        self._disponivel = True

    def inicializar(self) -> None:
        """Cria a tabela e indices se nao existirem.

        Em caso de falha de SQLite, registra WARNING e marca o
        repositorio como indisponivel (fail-open).

        """
        try:
            with sqlite3.connect(str(self._caminho)) as conn:
                conn.execute(_DDL_TABELA)
                conn.execute(_DDL_IDX_SESSION)
                conn.execute(_DDL_IDX_THREAD)
                conn.commit()
            self._disponivel = True
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as exc:
            logger.warning(
                "[WatchdogEventos] Falha ao inicializar banco '%s': %s. "
                "Continuando sem persistencia SQLite (fail-open).",
                self._caminho,
                exc,
            )
            self._disponivel = False

    def inserir(self, registro: RegistroEvento) -> None:
        """Insere um evento na tabela diarios_watchdog_eventos.

        Se o banco estiver indisponivel, o evento e descartado com
        WARNING. Nunca levanta excecao.

        Args:
            registro: Dados do evento a persistir.

        """
        if not self._disponivel:
            logger.warning(
                "[WatchdogEventos] Banco indisponivel — evento '%s' de "
                "'%s' descartado (fail-open).",
                registro.evento,
                registro.nome_thread,
            )
            return

        sql = """
            INSERT INTO diarios_watchdog_eventos
                (session_id, nome_thread, evento, estado_resultante,
                 mensagem, stack_trace, gravacoes_sessao)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        try:
            with sqlite3.connect(str(self._caminho)) as conn:
                conn.execute(
                    sql,
                    (
                        registro.session_id,
                        registro.nome_thread,
                        registro.evento,
                        registro.estado_resultante,
                        registro.mensagem,
                        registro.stack_trace,
                        registro.gravacoes_sessao,
                    ),
                )
                conn.commit()
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as exc:
            logger.warning(
                "[WatchdogEventos] Falha ao inserir evento '%s' para "
                "'%s': %s (fail-open).",
                registro.evento,
                registro.nome_thread,
                exc,
            )

    def contar_eventos_sessao(self, session_id: str) -> int:
        """Retorna total de eventos de uma sessao.

        Args:
            session_id: Identificador da sessao.

        Returns:
            Numero de eventos registrados para essa sessao.

        """
        if not self._disponivel:
            return 0
        try:
            with sqlite3.connect(str(self._caminho)) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM diarios_watchdog_eventos "
                    "WHERE session_id = ?",
                    (session_id,),
                )
                row = cursor.fetchone()
                return int(row[0]) if row else 0
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            return 0

    @property
    def disponivel(self) -> bool:
        """Indica se o banco esta acessivel.

        Returns:
            True se banco inicializado com sucesso.

        """
        return self._disponivel
