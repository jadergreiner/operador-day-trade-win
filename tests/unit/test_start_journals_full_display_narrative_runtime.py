"""Testes unitarios para a integracao de narrativas do start_journals_full_display."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.start_journals_full_display import NarrativeRuntimeBridge


@dataclass(frozen=True)
class _FakeQuestion:
    prompt: str
    level: str = "basico"
    category: str = "execution"

    def to_dict(self) -> dict[str, str]:
        return {
            "prompt": self.prompt,
            "level": self.level,
            "category": self.category,
            "created_at": "2026-03-18T10:30:00",
        }


class _FakeQuestionEvolution:
    def __init__(self) -> None:
        self.last_context: dict[str, object] | None = None
        self.last_historical_sessions: list[object] | None = None
        self.last_used_prompts: list[str] | None = None
        self.last_limit: int | None = None

    def evolve_questions(
        self,
        trade_context: dict[str, object],
        historical_sessions: list[object],
        used_prompts: list[str] | None = None,
        limit: int = 3,
    ) -> list[_FakeQuestion]:
        self.last_context = trade_context
        self.last_historical_sessions = historical_sessions
        self.last_used_prompts = list(used_prompts or [])
        self.last_limit = limit
        return [
            _FakeQuestion(
                prompt="Qual risco real foi assumido?",
                level="intermediario",
                category="risk",
            )
        ]


class _FakePersistence:
    def __init__(self) -> None:
        self.saved: list[dict[str, object]] = []

    def save_narrative(self, narrative: dict[str, object]) -> dict[str, object]:
        self.saved.append(narrative)
        return narrative

    def list_all(self) -> list[dict[str, object]]:
        return list(self.saved)


class _FakeCorrelator:
    def correlate(
        self,
        trades: list[dict[str, object]],
        narratives: list[dict[str, object]],
    ) -> dict[str, object]:
        return {
            "total_trades": len(trades),
            "total_narratives": len(narratives),
            "correlated_trades": min(len(trades), len(narratives)),
            "unmatched_trades": max(0, len(trades) - len(narratives)),
            "correlation_rate": 1.0 if trades and narratives else 0.0,
            "direct_matches": 1 if trades and narratives else 0,
            "temporal_matches": 0,
            "correlations": [
                {
                    "trade_id": trades[0].get("episode_id") if trades else None,
                    "matched": bool(trades and narratives),
                    "match_type": "trade_id" if trades and narratives else "unmatched",
                    "time_delta_minutes": 0.0 if trades and narratives else None,
                    "narrative_headline": narratives[0].get("headline") if narratives else None,
                    "narrative_category": narratives[0].get("category") if narratives else None,
                    "narrative_text": narratives[0].get("narrative") if narratives else None,
                    "narrative_trade_id": narratives[0].get("trade_id") if narratives else None,
                }
            ]
            if trades or narratives
            else [],
        }

    def extract_features(self, correlations: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            {
                "trade_id": item.get("trade_id"),
                "matched": item.get("matched", False),
                "match_type": item.get("match_type", "unmatched"),
                "time_delta_minutes": item.get("time_delta_minutes"),
                "headline_length": len(str(item.get("narrative_headline") or "")),
                "narrative_length": len(str(item.get("narrative_text") or "")),
                "has_category": item.get("narrative_category") is not None,
                "narrative_trade_id": item.get("narrative_trade_id"),
            }
            for item in correlations
        ]


def test_narrative_runtime_bridge_process_cycle_exports_dataset(tmp_path, capsys) -> None:
    question_evolution = _FakeQuestionEvolution()
    persistence = _FakePersistence()
    correlator = _FakeCorrelator()
    bridge = NarrativeRuntimeBridge(
        export_dir=tmp_path / "outputs",
        export_every_n_cycles=1,
        question_evolution=question_evolution,
        persistence=persistence,
        correlator=correlator,
    )

    reflection = SimpleNamespace(
        timestamp=datetime(2026, 3, 18, 10, 30, 0),
        entry_id="REF-001",
        current_price=Decimal("142500.5"),
        price_change_since_open=Decimal("0.8"),
        price_change_last_10min=Decimal("0.5"),
        mood="FRUSTRADO",
        one_liner="Mercado confuso, mas ainda com leitura.",
        honest_assessment="A leitura atual exige mais cautela.",
        what_im_seeing="Fluxo misto e pouco direcional.",
        data_relevance="Dados ainda ajudam, mas com menor peso.",
        am_i_useful="Sou util quando filtro ruido.",
        my_data_correlation="Correlação moderada.",
    )
    decision = SimpleNamespace(
        action=SimpleNamespace(value="BUY"),
        confidence=Decimal("0.58"),
        alignment_score=Decimal("0.63"),
        recommended_entry=True,
    )
    episodes = [
        {
            "episode_id": "EP-001",
            "timestamp": "2026-03-18T10:28:00",
            "action": "BUY",
            "macro_score_final": 7,
            "micro_score": 3,
            "market_regime": "TREND",
            "session_phase": "OPEN",
            "alignment_score": 0.72,
        }
    ]
    opportunities = [{"direction": "BUY", "confidence": 0.7}]
    historical_sessions = [{}] * 10

    result = bridge.process_cycle(
        reflection=reflection,
        decision=decision,
        episodes=episodes,
        opportunities=opportunities,
        historical_sessions=historical_sessions,
    )

    captured = capsys.readouterr().out

    assert "Perguntas evolutivas:" in captured
    assert question_evolution.last_context is not None
    assert question_evolution.last_context["high_risk"] is True
    assert question_evolution.last_context["emotional_instability"] is True
    assert question_evolution.last_limit == 3
    assert len(persistence.saved) == 2
    assert persistence.saved[0]["category"] == "reflection"
    assert persistence.saved[1]["category"] == "trade"
    assert result["export_path"] is not None

    export_path = Path(result["export_path"])
    assert export_path.exists()

    payload = json.loads(export_path.read_text(encoding="utf-8"))
    assert payload["total_records"] == 2
    assert payload["correlation_summary"]["total_trades"] == 1
    assert payload["correlation_features"][0]["matched"] is True
