"""Guardian coordinator for multi-agent order proposals.

The coordinator receives proposals from multiple agents, applies the conflict
resolver, enforces the global kill-switch, and emits a consolidated decision
plus an operational summary for audit and monitoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Sequence

from src.application.multi_agent_conflict_resolver import (
    AgentOrderProposal,
    MultiAgentConflictResolver,
    OrderSide,
    ResolutionAction,
    ResolutionAuditEntry,
    ResolutionStrategy,
    ResolvedOrderIntent,
    _serialize_value,
)


def _serialize_local(value: Any) -> Any:
    """Serialize nested dataclasses using the shared resolver helper."""

    return _serialize_value(value)


@dataclass
class OperationalSummary:
    """Human-readable operational summary for the guardian."""

    symbol: str
    decision: ResolutionAction
    strategy: ResolutionStrategy
    proposal_count: int
    agent_count: int
    conflict_detected: bool
    kill_switch_active: bool
    message: str
    action_items: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return _serialize_local(self)


@dataclass
class GuardianCoordinationResult:
    """Consolidated output produced by the guardian coordinator."""

    symbol: str
    decision: ResolutionAction
    resolved_side: OrderSide
    quantity: int
    confidence: float
    strategy: ResolutionStrategy
    conflict_detected: bool
    kill_switch_active: bool
    kill_switch_reason: str
    proposal_count: int
    agent_ids: list[str] = field(default_factory=list)
    summary: OperationalSummary | None = None
    resolution: ResolvedOrderIntent | None = None
    audit_trail: list[ResolutionAuditEntry] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return _serialize_local(self)


class GuardianAgentCoordinator:
    """Coordinates proposals from multiple agents into a single decision."""

    def __init__(
        self,
        resolver: MultiAgentConflictResolver | None = None,
    ) -> None:
        self.resolver = resolver or MultiAgentConflictResolver()

    def coordinate(
        self,
        proposals: Sequence[AgentOrderProposal],
        *,
        kill_switch_active: bool = False,
        kill_switch_reason: str = "",
    ) -> GuardianCoordinationResult:
        """Coordinate multiple proposals for a single symbol."""

        proposal_list = list(proposals)
        if not proposal_list:
            raise ValueError("proposals cannot be empty")

        symbol = proposal_list[0].symbol
        for proposal in proposal_list:
            if proposal.symbol != symbol:
                raise ValueError("all proposals must target the same symbol")

        audit: list[ResolutionAuditEntry] = [
            ResolutionAuditEntry(
                timestamp=datetime.now(),
                event="coordination_started",
                message="Guardian coordination started.",
                data={
                    "symbol": symbol,
                    "proposal_count": len(proposal_list),
                    "agent_ids": [proposal.agent_id for proposal in proposal_list],
                },
            )
        ]

        if kill_switch_active:
            resolution = self.resolver.resolve(
                proposal_list,
                kill_switch=True,
                kill_switch_reason=kill_switch_reason,
            )
            audit.extend(resolution.audit_trail)
            summary = OperationalSummary(
                symbol=symbol,
                decision=ResolutionAction.BLOCK,
                strategy=ResolutionStrategy.KILL_SWITCH,
                proposal_count=len(proposal_list),
                agent_count=len({proposal.agent_id for proposal in proposal_list}),
                conflict_detected=resolution.conflict_detected,
                kill_switch_active=True,
                message=(
                    "Global kill-switch active; all proposals blocked."
                ),
                action_items=[
                    "keep_trading_paused",
                    "notify_operators",
                    f"reason={kill_switch_reason or 'global_kill_switch'}",
                ],
            )
            return GuardianCoordinationResult(
                symbol=symbol,
                decision=ResolutionAction.BLOCK,
                resolved_side=OrderSide.NEUTRAL,
                quantity=0,
                confidence=0.0,
                strategy=ResolutionStrategy.KILL_SWITCH,
                conflict_detected=resolution.conflict_detected,
                kill_switch_active=True,
                kill_switch_reason=kill_switch_reason or "global_kill_switch",
                proposal_count=len(proposal_list),
                agent_ids=[proposal.agent_id for proposal in proposal_list],
                summary=summary,
                resolution=resolution,
                audit_trail=audit,
            )

        resolution = self.resolver.resolve(proposal_list)
        audit.extend(resolution.audit_trail)

        if resolution.action == ResolutionAction.EXECUTE:
            decision = ResolutionAction.EXECUTE
            message = (
                f"Consensus reached for {symbol}; execution approved."
            )
            action_items = ["route_order_to_executor"]
        elif resolution.action == ResolutionAction.ADJUST:
            decision = ResolutionAction.ADJUST
            message = (
                f"Conflict resolved for {symbol}; execute the winning side with adjustment."
            )
            action_items = [
                "apply_resolution_adjustment",
                "route_adjusted_order",
            ]
        else:
            decision = ResolutionAction.BLOCK
            message = f"Order blocked for {symbol} due to unresolved conflict."
            action_items = ["hold_order", "notify_risk_layer"]

        summary = OperationalSummary(
            symbol=symbol,
            decision=decision,
            strategy=resolution.strategy,
            proposal_count=len(proposal_list),
            agent_count=len({proposal.agent_id for proposal in proposal_list}),
            conflict_detected=resolution.conflict_detected,
            kill_switch_active=False,
            message=message,
            action_items=action_items,
        )

        return GuardianCoordinationResult(
            symbol=symbol,
            decision=decision,
            resolved_side=resolution.side,
            quantity=resolution.quantity,
            confidence=resolution.confidence,
            strategy=resolution.strategy,
            conflict_detected=resolution.conflict_detected,
            kill_switch_active=False,
            kill_switch_reason="",
            proposal_count=len(proposal_list),
            agent_ids=[proposal.agent_id for proposal in proposal_list],
            summary=summary,
            resolution=resolution,
            audit_trail=audit,
        )


__all__ = [
    "GuardianAgentCoordinator",
    "GuardianCoordinationResult",
    "OperationalSummary",
]
