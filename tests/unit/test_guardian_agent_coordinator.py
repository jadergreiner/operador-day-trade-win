"""Tests for the guardian multi-agent coordinator."""

from __future__ import annotations

import json

from src.application.guardian_agent_coordinator import (
    GuardianAgentCoordinator,
    ResolutionAction,
    ResolutionStrategy,
)
from src.application.multi_agent_conflict_resolver import (
    AgentOrderProposal,
    OrderSide,
)


def test_coordinator_consensus_generates_execute_summary() -> None:
    coordinator = GuardianAgentCoordinator()
    proposals = [
        AgentOrderProposal(
            agent_id="alpha",
            symbol="WIN",
            side=OrderSide.BUY,
            confidence=0.82,
            weight=1.0,
            quantity=2,
        ),
        AgentOrderProposal(
            agent_id="beta",
            symbol="WIN",
            side=OrderSide.BUY,
            confidence=0.76,
            weight=1.2,
            quantity=2,
        ),
    ]

    result = coordinator.coordinate(proposals)

    assert result.decision == ResolutionAction.EXECUTE
    assert result.resolved_side == OrderSide.BUY
    assert result.kill_switch_active is False
    assert result.summary is not None
    assert result.summary.message.startswith("Consensus reached")
    assert result.summary.decision == ResolutionAction.EXECUTE
    assert result.summary.strategy == ResolutionStrategy.CONSENSUS
    assert result.audit_trail[0].event == "coordination_started"
    assert result.audit_trail[-1].event == "consensus"

    payload = result.to_dict()
    assert payload["summary"]["decision"] == "EXECUTE"
    assert json.dumps(payload, ensure_ascii=False)


def test_kill_switch_global_blocks_and_records_audit() -> None:
    coordinator = GuardianAgentCoordinator()
    proposals = [
        AgentOrderProposal(
            agent_id="alpha",
            symbol="WIN",
            side=OrderSide.BUY,
            confidence=0.91,
            weight=1.0,
            quantity=1,
        ),
        AgentOrderProposal(
            agent_id="beta",
            symbol="WIN",
            side=OrderSide.SELL,
            confidence=0.93,
            weight=1.0,
            quantity=1,
        ),
    ]

    result = coordinator.coordinate(
        proposals,
        kill_switch_active=True,
        kill_switch_reason="risk_off",
    )

    assert result.decision == ResolutionAction.BLOCK
    assert result.resolved_side == OrderSide.NEUTRAL
    assert result.kill_switch_active is True
    assert result.kill_switch_reason == "risk_off"
    assert result.strategy == ResolutionStrategy.KILL_SWITCH
    assert result.summary is not None
    assert result.summary.kill_switch_active is True
    assert result.summary.message == "Global kill-switch active; all proposals blocked."
    assert result.audit_trail[-1].event == "kill_switch"

    payload = result.to_dict()
    assert payload["summary"]["kill_switch_active"] is True
    assert payload["resolution"]["strategy"] == "KILL_SWITCH"
    assert json.dumps(payload, ensure_ascii=False)
