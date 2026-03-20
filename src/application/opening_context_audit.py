"""Persistencia auditavel do contexto de abertura dos agentes."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock


@dataclass(slots=True)
class OpeningContextAuditRecord:
    """Representa o snapshot auditavel do contexto de abertura."""

    agent_name: str
    session_id: str
    mode: str
    source: str
    prompt_abertura_agentes: str
    regime_macro: str = ""
    vies_intraday: str = ""
    kill_switch_ativo: bool = False
    kill_switch_reason: str = ""
    watchlist: list[str] | None = None
    contexto_json: dict[str, Any] | None = None
    timestamp: str = ""

    def to_row(self) -> tuple[Any, ...]:
        """Converte o registro para a tupla usada no INSERT."""
        payload = self.contexto_json or {}
        watchlist = self.watchlist or []
        timestamp = self.timestamp or datetime.now().isoformat(timespec="seconds")
        return (
            timestamp[:10],
            timestamp,
            self.agent_name,
            self.session_id,
            self.mode,
            self.source,
            self.prompt_abertura_agentes,
            self.regime_macro,
            self.vies_intraday,
            1 if self.kill_switch_ativo else 0,
            self.kill_switch_reason,
            json.dumps(watchlist, ensure_ascii=False),
            json.dumps(payload, ensure_ascii=False),
        )


_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS opening_context_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    session_id TEXT NOT NULL DEFAULT '',
    mode TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'pre_opening',
    prompt_abertura_agentes TEXT NOT NULL DEFAULT '',
    regime_macro TEXT NOT NULL DEFAULT '',
    vies_intraday TEXT NOT NULL DEFAULT '',
    kill_switch_ativo INTEGER NOT NULL DEFAULT 0,
    kill_switch_reason TEXT NOT NULL DEFAULT '',
    watchlist_json TEXT NOT NULL DEFAULT '[]',
    contexto_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_opening_context_audit_date
ON opening_context_audit(date);

CREATE INDEX IF NOT EXISTS ix_opening_context_audit_agent
ON opening_context_audit(agent_name, timestamp DESC);
"""

_CONNECT_TIMEOUT_SECONDS = 30.0
_BUSY_TIMEOUT_MS = 30000
_MAX_RETRIES_LOCK = 4
_BASE_BACKOFF_SECONDS = 0.2


def _open_connection(db_path: str) -> sqlite3.Connection:
    """Abre conexão SQLite com pragmas para reduzir lock transitório."""
    conn = sqlite3.connect(db_path, timeout=_CONNECT_TIMEOUT_SECONDS)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
    return conn


def _is_sqlite_lock_error(exc: sqlite3.OperationalError) -> bool:
    message = str(exc).lower()
    return "database is locked" in message or "database is busy" in message


def _create_opening_context_audit_table_unlocked(db_path: str) -> None:
    last_error: sqlite3.OperationalError | None = None
    for attempt in range(1, _MAX_RETRIES_LOCK + 1):
        conn = _open_connection(db_path)
        try:
            conn.executescript(_CREATE_SQL)
            conn.commit()
            return
        except sqlite3.OperationalError as exc:
            last_error = exc
            if not _is_sqlite_lock_error(exc) or attempt == _MAX_RETRIES_LOCK:
                raise
            time.sleep(_BASE_BACKOFF_SECONDS * attempt)
        finally:
            conn.close()

    if last_error:
        raise last_error


def create_opening_context_audit_table(db_path: str) -> None:
    """Cria a tabela de auditoria se necessario."""
    with sqlite_write_lock(db_path):
        _create_opening_context_audit_table_unlocked(db_path)


def persist_opening_context_audit(
    db_path: str,
    *,
    agent_name: str,
    source: str,
    prompt_abertura_agentes: str,
    macro_context: Mapping[str, Any] | None = None,
    session_id: str = "",
    mode: str = "",
) -> int:
    """Persiste o contexto de abertura para auditoria comparativa."""
    context = dict(macro_context or {})
    record = OpeningContextAuditRecord(
        agent_name=agent_name,
        session_id=session_id,
        mode=mode,
        source=source,
        prompt_abertura_agentes=str(prompt_abertura_agentes or "").strip(),
        regime_macro=str(context.get("regime_macro", "") or ""),
        vies_intraday=str(
            context.get("vies_intraday", context.get("intraday_bias", "")) or ""
        ),
        kill_switch_ativo=bool(
            context.get("kill_switch_ativo", context.get("active_kill_switch", False))
        ),
        kill_switch_reason=str(
            context.get("kill_switch_reason", context.get("reason", "")) or ""
        ),
        watchlist=[str(item) for item in context.get("watchlist", []) or []],
        contexto_json=context,
    )

    last_error: sqlite3.OperationalError | None = None
    with sqlite_write_lock(db_path):
        _create_opening_context_audit_table_unlocked(db_path)
        for attempt in range(1, _MAX_RETRIES_LOCK + 1):
            conn = _open_connection(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO opening_context_audit (
                        date, timestamp, agent_name, session_id, mode, source,
                        prompt_abertura_agentes, regime_macro, vies_intraday,
                        kill_switch_ativo, kill_switch_reason, watchlist_json, contexto_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    record.to_row(),
                )
                conn.commit()
                return int(cursor.lastrowid or 0)
            except sqlite3.OperationalError as exc:
                last_error = exc
                if not _is_sqlite_lock_error(exc) or attempt == _MAX_RETRIES_LOCK:
                    raise
                time.sleep(_BASE_BACKOFF_SECONDS * attempt)
            finally:
                conn.close()

    if last_error:
        raise last_error
    return 0
