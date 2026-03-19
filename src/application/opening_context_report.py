"""Relatorio automatico comparando contexto de abertura vs resultado do dia."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class OpeningContextAgentSummary:
    """Resumo por agente/sessao."""

    agent_name: str
    session_id: str
    mode: str
    source: str
    regime_macro: str
    vies_intraday: str
    prompt_abertura_agentes: str
    watchlist: list[str] = field(default_factory=list)
    decisions_total: int = 0
    decision_breakdown: dict[str, int] = field(default_factory=dict)
    trades_closed: int = 0
    wins: int = 0
    losses: int = 0
    breakevens: int = 0
    pnl_total: float = 0.0
    alignment_status: str = "SEM_DADOS"
    decision_examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "mode": self.mode,
            "source": self.source,
            "regime_macro": self.regime_macro,
            "vies_intraday": self.vies_intraday,
            "prompt_abertura_agentes": self.prompt_abertura_agentes,
            "watchlist": list(self.watchlist),
            "decisions_total": self.decisions_total,
            "decision_breakdown": dict(self.decision_breakdown),
            "trades_closed": self.trades_closed,
            "wins": self.wins,
            "losses": self.losses,
            "breakevens": self.breakevens,
            "pnl_total": self.pnl_total,
            "alignment_status": self.alignment_status,
            "decision_examples": list(self.decision_examples),
        }


@dataclass(slots=True)
class OpeningContextReportArtifacts:
    """Artefatos persistidos do relatorio consolidado."""

    target_date: str
    generated_at: str
    summaries: list[OpeningContextAgentSummary]
    json_path: Path
    markdown_path: Path
    latest_json_path: Path
    latest_markdown_path: Path

    def to_dict(self) -> dict[str, Any]:
        total_trades = sum(item.trades_closed for item in self.summaries)
        total_pnl = sum(item.pnl_total for item in self.summaries)
        return {
            "target_date": self.target_date,
            "generated_at": self.generated_at,
            "total_agents": len(self.summaries),
            "total_trades_closed": total_trades,
            "total_pnl": total_pnl,
            "summaries": [item.to_dict() for item in self.summaries],
            "json_path": str(self.json_path),
            "markdown_path": str(self.markdown_path),
            "latest_json_path": str(self.latest_json_path),
            "latest_markdown_path": str(self.latest_markdown_path),
        }


def generate_opening_context_vs_result_report(
    *,
    db_path: str | Path,
    output_dir: str | Path = "outputs/analysis",
    outputs_root: str | Path = "outputs",
    target_date: str | date | datetime | None = None,
) -> OpeningContextReportArtifacts:
    """Cruza auditoria de abertura com decisoes e trades fechados do dia."""
    normalized_date = _normalize_target_date(target_date)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    outputs_dir = Path(outputs_root)

    audit_records = _fetch_audit_records(Path(db_path), normalized_date)
    summaries = [
        _build_summary(record, normalized_date, outputs_dir)
        for record in audit_records
    ]

    generated_at = datetime.now().isoformat(timespec="seconds")
    json_path = output_path / f"opening_context_vs_result_{normalized_date.replace('-', '')}.json"
    markdown_path = output_path / f"opening_context_vs_result_{normalized_date.replace('-', '')}.md"
    latest_json_path = output_path / "opening_context_vs_result_latest.json"
    latest_markdown_path = output_path / "opening_context_vs_result_latest.md"
    artifacts = OpeningContextReportArtifacts(
        target_date=normalized_date,
        generated_at=generated_at,
        summaries=summaries,
        json_path=json_path,
        markdown_path=markdown_path,
        latest_json_path=latest_json_path,
        latest_markdown_path=latest_markdown_path,
    )

    json_payload = json.dumps(artifacts.to_dict(), indent=2, ensure_ascii=False)
    markdown_payload = _render_markdown(artifacts)
    json_path.write_text(
        json_payload,
        encoding="utf-8",
    )
    markdown_path.write_text(
        markdown_payload,
        encoding="utf-8",
    )
    latest_json_path.write_text(json_payload, encoding="utf-8")
    latest_markdown_path.write_text(markdown_payload, encoding="utf-8")
    return artifacts


def load_latest_opening_context_report(
    output_dir: str | Path = "outputs/analysis",
) -> dict[str, Any] | None:
    """Carrega o relatorio consolidado mais recente, se existir."""
    latest_json_path = Path(output_dir) / "opening_context_vs_result_latest.json"
    if not latest_json_path.exists():
        return None
    try:
        payload = json.loads(latest_json_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_target_date(target_date: str | date | datetime | None) -> str:
    if isinstance(target_date, datetime):
        return target_date.date().isoformat()
    if isinstance(target_date, date):
        return target_date.isoformat()
    if isinstance(target_date, str) and target_date.strip():
        text = target_date.strip()
        if len(text) == 8 and text.isdigit():
            return f"{text[:4]}-{text[4:6]}-{text[6:]}"
        return text
    return date.today().isoformat()


def _fetch_audit_records(db_path: Path, normalized_date: str) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT agent_name, session_id, mode, source, prompt_abertura_agentes,
                   regime_macro, vies_intraday, watchlist_json, contexto_json,
                   timestamp
            FROM opening_context_audit
            WHERE date = ?
            ORDER BY timestamp ASC
            """,
            (normalized_date,),
        ).fetchall()
    except sqlite3.OperationalError:
        rows = []
    finally:
        conn.close()

    records: list[dict[str, Any]] = []
    for row in rows:
        watchlist = _load_json_payload(row["watchlist_json"], default=[])
        contexto_json = _load_json_payload(row["contexto_json"], default={})
        records.append(
            {
                "agent_name": row["agent_name"],
                "session_id": row["session_id"],
                "mode": row["mode"],
                "source": row["source"],
                "prompt_abertura_agentes": row["prompt_abertura_agentes"],
                "regime_macro": row["regime_macro"],
                "vies_intraday": row["vies_intraday"],
                "watchlist": watchlist if isinstance(watchlist, list) else [],
                "contexto_json": contexto_json if isinstance(contexto_json, dict) else {},
                "timestamp": row["timestamp"],
            }
        )
    return records


def _build_summary(
    record: dict[str, Any],
    normalized_date: str,
    outputs_root: Path,
) -> OpeningContextAgentSummary:
    session_id = str(record.get("session_id", "") or "").strip()
    decisions = _load_agent_payload(
        outputs_root / f"decisoes_{session_id}.json",
        timestamp_key="timestamp",
        normalized_date=normalized_date,
    ) if session_id else []
    history = _load_agent_payload(
        outputs_root / f"historico_fechamentos_{session_id}.json",
        timestamp_key="timestamp_fechamento",
        normalized_date=normalized_date,
    ) if session_id else []

    decision_breakdown = Counter(str(item.get("decisao", "")) for item in decisions)
    wins = sum(1 for item in history if float(item.get("pnl_reais", 0.0) or 0.0) > 0)
    losses = sum(1 for item in history if float(item.get("pnl_reais", 0.0) or 0.0) < 0)
    breakevens = sum(1 for item in history if float(item.get("pnl_reais", 0.0) or 0.0) == 0)
    pnl_total = sum(float(item.get("pnl_reais", 0.0) or 0.0) for item in history)

    return OpeningContextAgentSummary(
        agent_name=str(record.get("agent_name", "") or ""),
        session_id=session_id,
        mode=str(record.get("mode", "") or ""),
        source=str(record.get("source", "") or ""),
        regime_macro=str(record.get("regime_macro", "") or ""),
        vies_intraday=str(record.get("vies_intraday", "") or ""),
        prompt_abertura_agentes=str(record.get("prompt_abertura_agentes", "") or ""),
        watchlist=[str(item) for item in record.get("watchlist", []) or []],
        decisions_total=len(decisions),
        decision_breakdown=dict(decision_breakdown),
        trades_closed=len(history),
        wins=wins,
        losses=losses,
        breakevens=breakevens,
        pnl_total=pnl_total,
        alignment_status=_evaluate_alignment(record, decisions),
        decision_examples=_collect_decision_examples(decisions),
    )


def _load_agent_payload(
    file_path: Path,
    *,
    timestamp_key: str,
    normalized_date: str,
) -> list[dict[str, Any]]:
    if not file_path.exists():
        return []
    payload = _load_json_payload(file_path.read_text(encoding="utf-8"), default=[])
    if not isinstance(payload, list):
        return []
    filtered: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        timestamp = str(item.get(timestamp_key, "") or "")
        if timestamp.startswith(normalized_date):
            filtered.append(item)
    return filtered


def _load_json_payload(raw_value: Any, *, default: Any) -> Any:
    if isinstance(raw_value, (dict, list)):
        return raw_value
    if raw_value in (None, ""):
        return default
    try:
        return json.loads(raw_value)
    except Exception:
        return default


def _evaluate_alignment(
    record: dict[str, Any],
    decisions: list[dict[str, Any]],
) -> str:
    vies_intraday = str(record.get("vies_intraday", "") or "").upper()
    if not decisions:
        return "SEM_DECISOES"

    buy_count = 0
    sell_count = 0
    for item in decisions:
        contexto = item.get("contexto_operacional", {})
        normalized_action = ""
        if isinstance(contexto, dict):
            normalized_action = str(contexto.get("acao_normalizada", "") or "").upper()
        if not normalized_action:
            reasoning = str(item.get("reasoning", "") or "").upper()
            if " BUY" in reasoning or reasoning.endswith("BUY"):
                normalized_action = "BUY"
            elif " SELL" in reasoning or reasoning.endswith("SELL"):
                normalized_action = "SELL"
        if normalized_action == "BUY":
            buy_count += 1
        elif normalized_action == "SELL":
            sell_count += 1

    if "BAIXISTA" in vies_intraday:
        return "ALINHADO_AO_BIAS" if sell_count >= buy_count else "CONTRA_O_BIAS"
    if "ALTISTA" in vies_intraday:
        return "ALINHADO_AO_BIAS" if buy_count >= sell_count else "CONTRA_O_BIAS"
    return "NEUTRO_OU_MISTO"


def _collect_decision_examples(decisions: list[dict[str, Any]]) -> list[str]:
    examples: list[str] = []
    for item in decisions:
        reasoning = str(item.get("reasoning", "") or "").strip()
        if not reasoning:
            continue
        examples.append(reasoning)
        if len(examples) >= 3:
            break
    return examples


def _render_markdown(report: OpeningContextReportArtifacts) -> str:
    payload = report.to_dict()
    lines = [
        "# Relatorio Contexto de Abertura vs Resultado do Dia",
        "",
        f"- Data alvo: `{payload['target_date']}`",
        f"- Gerado em: `{payload['generated_at']}`",
        f"- Agentes auditados: `{payload['total_agents']}`",
        f"- Trades fechados: `{payload['total_trades_closed']}`",
        f"- PnL total: `R$ {payload['total_pnl']:.2f}`",
        "",
    ]

    if not report.summaries:
        lines.extend(
            [
                "## Sem dados",
                "",
                "Nenhum registro encontrado em `opening_context_audit` para a data informada.",
                "",
            ]
        )
        return "\n".join(lines)

    for summary in report.summaries:
        lines.extend(
            [
                f"## {summary.agent_name}",
                "",
                f"- Sessao: `{summary.session_id or 'N/D'}`",
                f"- Fonte: `{summary.source}` | Modo: `{summary.mode or 'N/D'}`",
                f"- Regime macro: `{summary.regime_macro or 'N/D'}`",
                f"- Vies intraday: `{summary.vies_intraday or 'N/D'}`",
                f"- Alignment status: `{summary.alignment_status}`",
                f"- Watchlist: `{', '.join(summary.watchlist) if summary.watchlist else 'N/D'}`",
                f"- Prompt de abertura: `{summary.prompt_abertura_agentes or 'N/D'}`",
                f"- Decisoes: `{summary.decisions_total}` | Breakdown: `{summary.decision_breakdown}`",
                f"- Trades fechados: `{summary.trades_closed}` | Wins: `{summary.wins}` | Losses: `{summary.losses}` | Breakeven: `{summary.breakevens}`",
                f"- PnL total: `R$ {summary.pnl_total:.2f}`",
            ]
        )
        if summary.decision_examples:
            lines.append(
                f"- Exemplos de reasoning: `{' | '.join(summary.decision_examples)}`"
            )
        lines.append("")

    return "\n".join(lines)


__all__ = [
    "OpeningContextAgentSummary",
    "OpeningContextReportArtifacts",
    "generate_opening_context_vs_result_report",
    "load_latest_opening_context_report",
]
