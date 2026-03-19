"""Tests for multi-agent order conflict resolution."""

from __future__ import annotations

import json

from src.application.multi_agent_conflict_resolver import (
    AgentOrderProposal,
    MultiAgentConflictResolver,
    OrderSide,
    ResolutionAction,
    ResolutionStrategy,
)


def test_consensus_without_conflict_executes() -> None:
    resolver = MultiAgentConflictResolver()
    proposals = [
        AgentOrderProposal(
            agent_id="agent_alpha",
            symbol="WIN",
            side=OrderSide.BUY,
            confidence=0.80,
            weight=1.0,
            quantity=2,
            reason="trend_following",
        ),
        AgentOrderProposal(
            agent_id="agent_beta",
            symbol="WIN",
            side=OrderSide.BUY,
            confidence=0.70,
            weight=1.5,
            quantity=4,
            reason="momentum_confirmation",
        ),
    ]

    resolution = resolver.resolve(proposals)

    assert resolution.action == ResolutionAction.EXECUTE
    assert resolution.side == OrderSide.BUY
    assert resolution.conflict_detected is False
    assert resolution.strategy == ResolutionStrategy.CONSENSUS
    assert resolution.winning_agent_ids == ["agent_alpha", "agent_beta"]
    assert resolution.audit_trail[1].event == "consensus"

    payload = resolution.to_dict()
    assert payload["action"] == "EXECUTE"
    assert payload["strategy"] == "CONSENSUS"
    assert json.dumps(payload, ensure_ascii=False)


def test_direct_conflict_prefers_higher_weighted_score() -> None:
    resolver = MultiAgentConflictResolver()
    proposals = [
        AgentOrderProposal(
            agent_id="buy_agent",
            symbol="WIN",
            side=OrderSide.BUY,
            confidence=0.60,
            weight=1.8,
            quantity=1,
            reason="higher_weight",
        ),
        AgentOrderProposal(
            agent_id="sell_agent",
            symbol="WIN",
            side=OrderSide.SELL,
            confidence=0.92,
            weight=0.8,
            quantity=1,
            reason="higher_raw_confidence",
        ),
    ]

    resolution = resolver.resolve(proposals)

    assert resolution.action == ResolutionAction.ADJUST
    assert resolution.side == OrderSide.BUY
    assert resolution.conflict_detected is True
    assert resolution.strategy == ResolutionStrategy.WEIGHTED_PRIORITY
    assert resolution.winning_agent_ids == ["buy_agent"]
    assert resolution.discarded_agent_ids == ["sell_agent"]
    assert resolution.scoreboard["BUY"] > resolution.scoreboard["SELL"]
    assert resolution.audit_trail[-1].event == "weighted_priority"


def test_priority_by_weight_can_override_raw_confidence() -> None:
    resolver = MultiAgentConflictResolver()
    proposals = [
        AgentOrderProposal(
            agent_id="weight_wins",
            symbol="WIN",
            side=OrderSide.BUY,
            confidence=0.58,
            weight=2.5,
            quantity=2,
            reason="low_confidence_high_weight",
        ),
        AgentOrderProposal(
            agent_id="raw_confidence",
            symbol="WIN",
            side=OrderSide.SELL,
            confidence=0.95,
            weight=1.0,
            quantity=2,
            reason="high_confidence_low_weight",
        ),
    ]

    resolution = resolver.resolve(proposals)

    assert resolution.side == OrderSide.BUY
    assert resolution.action == ResolutionAction.ADJUST
    assert resolution.strategy == ResolutionStrategy.WEIGHTED_PRIORITY
    assert resolution.winning_agent_ids == ["weight_wins"]
    assert resolution.confidence == 0.58


def test_resolution_audit_trail_is_serializable() -> None:
    resolver = MultiAgentConflictResolver()
    proposals = [
        AgentOrderProposal(
            agent_id="agent_one",
            symbol="WIN",
            side=OrderSide.BUY,
            confidence=0.88,
            weight=1.0,
            quantity=1,
            reason="single_side",
        )
    ]

    resolution = resolver.resolve(proposals)
    payload = resolution.to_dict()

    assert payload["audit_trail"][0]["event"] == "proposals_received"
    assert payload["audit_trail"][1]["event"] == "consensus"
    assert payload["resolved_at"]
    assert json.dumps(payload, ensure_ascii=False)
