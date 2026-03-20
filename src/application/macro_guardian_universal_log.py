"""Persistência universal do macro guardian em SQLite.

Este módulo oferece uma API simples para criar a tabela, persistir eventos
de qualquer severidade e consultar o histórico recente com um snapshot
heurístico do cenário macro.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from src.infrastructure.database.sqlite_write_lock import sqlite_write_lock

DEFAULT_SOURCE = "macro_scenario_guardian"
TABLE_NAME = "macro_guardian_log"

ALLOWED_SEVERITIES = {"INFO", "WARNING", "CRITICAL"}


def _now_iso() -> str:
    """Retorna timestamp UTC em ISO 8601 sem timezone."""
    return datetime.utcnow().isoformat(timespec="seconds")


def _coerce_bool(value: Any) -> int:
    """Normaliza valores booleanos para 0/1."""
    return 1 if bool(value) else 0


def _ensure_parent_dir(db_path: str | Path) -> None:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)


def _get_connection(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_severity(severity: Any) -> str:
    text = str(severity or "INFO").upper()
    return text if text in ALLOWED_SEVERITIES else "INFO"


def _serialize_payload(event: Mapping[str, Any]) -> str:
    return json.dumps(dict(event), ensure_ascii=False, default=str)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    payload_raw = row["payload_json"]
    payload: Any
    try:
        payload = json.loads(payload_raw) if payload_raw else {}
    except json.JSONDecodeError:
        payload = {"_raw": payload_raw}

    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "severity": row["severity"],
        "tipo_evento": row["tipo_evento"],
        "descricao": row["descricao"],
        "valor_atual": row["valor_atual"],
        "valor_anterior": row["valor_anterior"],
        "score_impacto": row["score_impacto"],
        "action": row["action"],
        "source": row["source"],
        "kill_switch_ativo": bool(row["kill_switch_ativo"]),
        "payload_json": payload_raw,
        "payload": payload,
    }


def _ensure_macro_guardian_log_table_unlocked(db_path: str | Path) -> None:
    _ensure_parent_dir(db_path)
    conn = _get_connection(db_path)
    try:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                severity TEXT NOT NULL,
                tipo_evento TEXT NOT NULL,
                descricao TEXT NOT NULL,
                valor_atual REAL,
                valor_anterior REAL,
                score_impacto REAL,
                action TEXT,
                source TEXT NOT NULL,
                kill_switch_ativo INTEGER NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_timestamp "
            f"ON {TABLE_NAME}(timestamp)"
        )
        conn.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_severity "
            f"ON {TABLE_NAME}(severity)"
        )
    finally:
        conn.close()


def ensure_macro_guardian_log_table(db_path: str | Path) -> None:
    """Cria a tabela macro_guardian_log se ainda não existir."""
    with sqlite_write_lock(db_path):
        _ensure_macro_guardian_log_table_unlocked(db_path)


def persist_macro_guardian_events(
    db_path: str | Path,
    events: Iterable[Mapping[str, Any]],
    source: str = DEFAULT_SOURCE,
) -> int:
    """Persiste eventos do macro guardian e retorna quantos foram inseridos."""
    def _persist() -> int:
        _ensure_macro_guardian_log_table_unlocked(db_path)
        conn = _get_connection(db_path)
        inserted = 0
        try:
            with conn:
                for event in events:
                    severity = _normalize_severity(event.get("severity"))
                    timestamp = str(event.get("timestamp") or _now_iso())
                    tipo_evento = str(event.get("tipo_evento") or event.get("category") or "macro_event")
                    descricao = str(event.get("descricao") or event.get("message") or "")
                    action = event.get("action")
                    valor_atual = event.get("valor_atual")
                    valor_anterior = event.get("valor_anterior")
                    score_impacto = event.get("score_impacto")
                    kill_switch_ativo = _coerce_bool(event.get("kill_switch_ativo", False))

                    conn.execute(
                        f"""
                        INSERT INTO {TABLE_NAME} (
                            timestamp, severity, tipo_evento, descricao,
                            valor_atual, valor_anterior, score_impacto, action,
                            source, kill_switch_ativo, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            timestamp,
                            severity,
                            tipo_evento,
                            descricao,
                            valor_atual,
                            valor_anterior,
                            score_impacto,
                            None if action is None else str(action),
                            source,
                            kill_switch_ativo,
                            _serialize_payload(event),
                        ),
                    )
                    inserted += 1
        finally:
            conn.close()
        return inserted

    with sqlite_write_lock(db_path):
        return _persist()


def fetch_recent_macro_guardian_events(
    db_path: str | Path,
    limit: int = 100,
    severities: Optional[Sequence[str]] = None,
) -> list[dict[str, Any]]:
    """Consulta eventos recentes, opcionalmente filtrando por severidade."""
    ensure_macro_guardian_log_table(db_path)
    if limit <= 0:
        return []

    conn = _get_connection(db_path)
    try:
        query = f"SELECT * FROM {TABLE_NAME}"
        params: list[Any] = []
        where_clauses: list[str] = []

        if severities:
            normalized = [_normalize_severity(sev) for sev in severities]
            placeholders = ", ".join("?" for _ in normalized)
            where_clauses.append(f"severity IN ({placeholders})")
            params.extend(normalized)

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY timestamp DESC, id DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def fetch_latest_guardian_snapshot(
    db_path: str | Path,
    lookback_minutes: int = 30,
) -> dict[str, Any]:
    """Retorna um snapshot heurístico dos eventos recentes do guardian."""
    events = fetch_recent_macro_guardian_events(db_path, limit=1000)
    if not events:
        return {
            "kill_switch_ativo": False,
            "score_impacto_medio": 0.0,
            "alertas_ativos": 0,
            "regime_macro": "ESTAVEL",
            "total_eventos": 0,
        }

    cutoff = datetime.utcnow() - timedelta(minutes=max(0, lookback_minutes))
    recentes: list[dict[str, Any]] = []
    for event in events:
        try:
            event_ts = datetime.fromisoformat(str(event["timestamp"]))
        except ValueError:
            continue
        if event_ts >= cutoff:
            recentes.append(event)

    if not recentes:
        return {
            "kill_switch_ativo": False,
            "score_impacto_medio": 0.0,
            "alertas_ativos": 0,
            "regime_macro": "ESTAVEL",
            "total_eventos": 0,
        }

    scores = [
        float(event["score_impacto"])
        for event in recentes
        if event["score_impacto"] is not None
    ]
    score_medio = sum(scores) / len(scores) if scores else 0.0
    alertas_ativos = sum(
        1
        for event in recentes
        if event["severity"] in {"WARNING", "CRITICAL"}
    )
    kill_switch_ativo = any(
        event["kill_switch_ativo"] or event["severity"] == "CRITICAL"
        for event in recentes
    )

    if kill_switch_ativo:
        regime_macro = "CRITICO"
    elif alertas_ativos >= 3 or score_medio <= -3.0:
        regime_macro = "ALERTA"
    elif alertas_ativos == 0 and score_medio >= 2.0:
        regime_macro = "FAVORAVEL"
    else:
        regime_macro = "ESTAVEL"

    return {
        "kill_switch_ativo": kill_switch_ativo,
        "score_impacto_medio": score_medio,
        "alertas_ativos": alertas_ativos,
        "regime_macro": regime_macro,
        "total_eventos": len(recentes),
    }
