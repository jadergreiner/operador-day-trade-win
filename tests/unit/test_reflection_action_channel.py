"""Testes unitarios para ReflectionActionChannel."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from src.application.reflection_action_channel import ReflectionActionChannel


def _action(
    action_id: str,
    timestamp: datetime,
    *,
    action_type: str = "trade",
    impact: float = 0.0,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    """Monta payload de acao para os testes."""

    payload: dict[str, object] = {
        "action_id": action_id,
        "action_type": action_type,
        "timestamp": timestamp,
        "impact": impact,
    }
    if metadata is not None:
        payload["metadata"] = metadata
    return payload


def _reflection(
    reflection_id: str,
    timestamp: datetime,
    *,
    text: str = "Reflexao do trade",
    action_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    """Monta payload de reflexao para os testes."""

    payload: dict[str, object] = {
        "reflection_id": reflection_id,
        "timestamp": timestamp,
        "text": text,
    }
    if action_id is not None:
        payload["action_id"] = action_id
    if metadata is not None:
        payload["metadata"] = metadata
    return payload


def test_main_flow_links_by_id_and_summarizes_impact() -> None:
    """Fluxo principal com link direto e resumo agregado."""

    channel = ReflectionActionChannel(temporal_window_minutes=30)
    action_ts = datetime(2026, 3, 18, 10, 0, 0)
    reflection_ts = datetime(2026, 3, 18, 10, 12, 0)

    channel.add_action(_action("A-001", action_ts, action_type="trade", impact=120.5))
    channel.add_reflection(_reflection("R-001", reflection_ts, action_id="A-001"))

    links = channel.link_reflections()
    summary = channel.summarize_impact_by_action_type()

    assert len(links) == 1
    assert links[0].matched_by == "action_id"
    assert links[0].action_id == "A-001"
    assert links[0].action_type == "trade"
    assert summary["total_actions"] == 1
    assert summary["linked_reflections"] == 1
    assert summary["summaries"][0]["action_type"] == "trade"
    assert summary["summaries"][0]["total_impact"] == 120.5
    assert summary["summaries"][0]["average_impact"] == 120.5


def test_add_action_and_reflection_are_idempotent_by_id() -> None:
    """Registros repetidos com o mesmo id nao devem duplicar dados."""

    channel = ReflectionActionChannel()

    first_action = channel.add_action(_action("A-001", datetime(2026, 3, 18, 10, 0, 0)))
    second_action = channel.add_action(
        _action("A-001", datetime(2026, 3, 18, 10, 5, 0), impact=999.0)
    )

    first_reflection = channel.add_reflection(
        _reflection("R-001", datetime(2026, 3, 18, 10, 1, 0), action_id="A-001")
    )
    second_reflection = channel.add_reflection(
        _reflection("R-001", datetime(2026, 3, 18, 10, 2, 0), action_id="A-001")
    )

    links = channel.link_reflections()
    payload = channel.to_dict()

    assert first_action == second_action
    assert first_reflection == second_reflection
    assert len(payload["actions"]) == 1
    assert len(payload["reflections"]) == 1
    assert len(links) == 1
    assert payload["links"][0]["reflection_id"] == "R-001"


def test_temporal_fallback_works_within_window() -> None:
    """Sem action_id, o canal deve usar match temporal dentro da janela."""

    channel = ReflectionActionChannel(temporal_window_minutes=15)

    channel.add_action(_action("A-001", datetime(2026, 3, 18, 10, 0, 0), action_type="trade", impact=-15.0))
    channel.add_reflection(_reflection("R-001", datetime(2026, 3, 18, 10, 9, 0)))

    links = channel.link_reflections()

    assert len(links) == 1
    assert links[0].matched_by == "temporal"
    assert links[0].time_delta_minutes == 9.0


def test_temporal_window_blocks_far_reflection() -> None:
    """Reflexao fora da janela nao deve gerar link."""

    channel = ReflectionActionChannel(temporal_window_minutes=5)

    channel.add_action(_action("A-001", datetime(2026, 3, 18, 10, 0, 0), impact=10.0))
    channel.add_reflection(_reflection("R-001", datetime(2026, 3, 18, 10, 7, 0)))

    links = channel.link_reflections()
    summary = channel.summarize_impact_by_action_type()

    assert links == []
    assert summary["linked_reflections"] == 0
    assert summary["summaries"][0]["link_rate"] == 0.0


def test_summary_metrics_by_action_type() -> None:
    """Resumo deve calcular metricas agregadas por tipo de acao."""

    channel = ReflectionActionChannel()

    channel.add_action(_action("A-001", datetime(2026, 3, 18, 9, 0, 0), action_type="trade", impact=50.0))
    channel.add_action(_action("A-002", datetime(2026, 3, 18, 9, 5, 0), action_type="trade", impact=-20.0))
    channel.add_action(_action("A-003", datetime(2026, 3, 18, 9, 7, 0), action_type="analysis", impact=0.0))

    channel.add_reflection(_reflection("R-001", datetime(2026, 3, 18, 9, 1, 0), action_id="A-001"))
    channel.add_reflection(_reflection("R-002", datetime(2026, 3, 18, 9, 6, 0), action_id="A-002"))

    summary = channel.summarize_impact_by_action_type()
    trade_summary = next(item for item in summary["summaries"] if item["action_type"] == "trade")
    analysis_summary = next(item for item in summary["summaries"] if item["action_type"] == "analysis")

    assert trade_summary["action_count"] == 2
    assert trade_summary["linked_reflections"] == 2
    assert trade_summary["total_impact"] == 30.0
    assert trade_summary["average_impact"] == 15.0
    assert trade_summary["positive_actions"] == 1
    assert trade_summary["negative_actions"] == 1
    assert trade_summary["neutral_actions"] == 0
    assert trade_summary["link_rate"] == 1.0

    assert analysis_summary["action_count"] == 1
    assert analysis_summary["linked_reflections"] == 0
    assert analysis_summary["total_impact"] == 0.0


def test_summary_respects_temporal_window_filter() -> None:
    """Filtro temporal deve limitar o conjunto usado no resumo."""

    channel = ReflectionActionChannel()

    channel.add_action(_action("A-001", datetime(2026, 3, 18, 9, 0, 0), action_type="trade", impact=10.0))
    channel.add_action(_action("A-002", datetime(2026, 3, 18, 11, 0, 0), action_type="trade", impact=40.0))
    channel.add_reflection(_reflection("R-001", datetime(2026, 3, 18, 9, 2, 0), action_id="A-001"))
    channel.add_reflection(_reflection("R-002", datetime(2026, 3, 18, 11, 2, 0), action_id="A-002"))

    summary = channel.summarize_impact_by_action_type(
        window_start=datetime(2026, 3, 18, 10, 0, 0),
        window_end=datetime(2026, 3, 18, 12, 0, 0),
    )

    assert summary["total_actions"] == 1
    assert summary["linked_reflections"] == 1
    assert summary["summaries"][0]["total_impact"] == 40.0
    assert summary["summaries"][0]["action_count"] == 1


def test_to_dict_is_json_serializable() -> None:
    """Serializacao final deve ser amigavel para JSON."""

    channel = ReflectionActionChannel()
    channel.add_action(_action("A-001", datetime(2026, 3, 18, 10, 0, 0), impact=1.5, metadata={"source": "sim"}))
    channel.add_reflection(_reflection("R-001", datetime(2026, 3, 18, 10, 1, 0), text="OK"))

    payload = channel.to_dict()
    encoded = json.dumps(payload, ensure_ascii=False)

    assert "\"temporal_window_minutes\"" in encoded
    assert "\"actions\"" in encoded
    assert "\"reflections\"" in encoded
    assert "\"impact_summary\"" in encoded


def test_rejects_negative_temporal_window() -> None:
    """Janela temporal negativa deve falhar na inicializacao."""

    with pytest.raises(ValueError, match="nao pode ser negativo"):
        ReflectionActionChannel(temporal_window_minutes=-1)


def test_rejects_invalid_action_payload() -> None:
    """Payload de acao incompleto deve ser rejeitado."""

    channel = ReflectionActionChannel()

    with pytest.raises(ValueError, match="acao deve conter"):
        channel.add_action({"action_id": "A-001", "timestamp": datetime(2026, 3, 18, 10, 0, 0)})


def test_rejects_invalid_reflection_payload() -> None:
    """Payload de reflexao incompleto deve ser rejeitado."""

    channel = ReflectionActionChannel()

    with pytest.raises(ValueError, match="reflexao deve conter"):
        channel.add_reflection({"reflection_id": "R-001"})


def test_rejects_non_numeric_impact() -> None:
    """Impacto nao numerico deve falhar."""

    channel = ReflectionActionChannel()

    with pytest.raises(TypeError, match="impacto deve ser numerico"):
        channel.add_action(
            {
                "action_id": "A-001",
                "action_type": "trade",
                "timestamp": datetime(2026, 3, 18, 10, 0, 0),
                "impact": "abc",
            }
        )


def test_accepts_iso_string_timestamps() -> None:
    """Timestamps em ISO string devem ser aceitos."""

    channel = ReflectionActionChannel()

    channel.add_action(
        {
            "action_id": "A-001",
            "action_type": "trade",
            "timestamp": "2026-03-18T10:00:00Z",
            "impact": 10,
        }
    )
    channel.add_reflection(
        {
            "reflection_id": "R-001",
            "timestamp": "2026-03-18T10:03:00Z",
            "action_id": "A-001",
            "text": "ISO",
        }
    )

    links = channel.link_reflections()

    assert links[0].reflection_timestamp.startswith("2026-03-18T10:03:00")
    assert links[0].action_timestamp.startswith("2026-03-18T10:00:00")
