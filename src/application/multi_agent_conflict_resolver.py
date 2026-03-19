"""Multi-agent order conflict resolver with audit trail.

This module consolidates order intents emitted by multiple agents for the same
symbol. It exposes the resolution strategy, the chosen action, and a structured
audit trail so the decision can be inspected later.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Iterable, Sequence


class OrderSide(str, Enum):
    """Directional intent for an order proposal."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NEUTRAL = "NEUTRAL"


class ResolutionAction(str, Enum):
    """Consolidated action emitted by the resolver."""

    EXECUTE = "EXECUTE"
    BLOCK = "BLOCK"
    ADJUST = "ADJUST"


class ResolutionStrategy(str, Enum):
    """Strategy used to reach the consolidated decision."""

    CONSENSUS = "CONSENSUS"
    WEIGHTED_PRIORITY = "WEIGHTED_PRIORITY"
    TIE_BREAK = "TIE_BREAK"
    KILL_SWITCH = "KILL_SWITCH"
    NO_ACTION = "NO_ACTION"


def _serialize_value(value: Any) -> Any:
    """Recursively convert dataclasses, enums and datetimes to JSON-friendly data."""

    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {
            item.name: _serialize_value(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(item) for item in value]
    return value


def _coerce_order_side(value: OrderSide | str) -> OrderSide:
    if isinstance(value, OrderSide):
        return value
    return OrderSide(str(value).upper())


def _coerce_action(value: ResolutionAction | str) -> ResolutionAction:
    if isinstance(value, ResolutionAction):
        return value
    return ResolutionAction(str(value).upper())


def _coerce_strategy(value: ResolutionStrategy | str) -> ResolutionStrategy:
    if isinstance(value, ResolutionStrategy):
        return value
    return ResolutionStrategy(str(value).upper())


@dataclass
class AgentOrderProposal:
    """Order intent proposed by an agent."""

    agent_id: str
    symbol: str
    side: OrderSide
    confidence: float
    weight: float = 1.0
    quantity: int = 1
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.side = _coerce_order_side(self.side)
        if not self.agent_id:
            raise ValueError("agent_id cannot be empty")
        if not self.symbol:
            raise ValueError("symbol cannot be empty")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.weight <= 0:
            raise ValueError("weight must be positive")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return _serialize_value(self)


@dataclass
class ResolutionAuditEntry:
    """Structured audit event emitted during resolution."""

    timestamp: datetime
    event: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _serialize_value(self)


@dataclass
class ResolvedOrderIntent:
    """Final consolidated order intent."""

    symbol: str
    action: ResolutionAction
    side: OrderSide
    quantity: int
    confidence: float
    strategy: ResolutionStrategy
    conflict_detected: bool
    proposal_count: int
    supporting_agents: list[str] = field(default_factory=list)
    winning_agent_ids: list[str] = field(default_factory=list)
    discarded_agent_ids: list[str] = field(default_factory=list)
    scoreboard: dict[str, float] = field(default_factory=dict)
    reason: str = ""
    blocked_reason: str = ""
    adjustment_factor: float = 1.0
    resolved_at: datetime = field(default_factory=datetime.now)
    audit_trail: list[ResolutionAuditEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _serialize_value(self)


class MultiAgentConflictResolver:
    """Consolidates multiple order proposals for the same symbol."""

    def __init__(
        self,
        *,
        min_execute_confidence: float = 0.55,
        tie_margin: float = 0.10,
    ) -> None:
        if not 0.0 <= min_execute_confidence <= 1.0:
            raise ValueError("min_execute_confidence must be between 0 and 1")
        if tie_margin < 0.0:
            raise ValueError("tie_margin must be non-negative")

        self.min_execute_confidence = min_execute_confidence
        self.tie_margin = tie_margin

    def resolve(
        self,
        proposals: Sequence[AgentOrderProposal],
        *,
        kill_switch: bool = False,
        kill_switch_reason: str = "",
    ) -> ResolvedOrderIntent:
        """Resolve a set of proposals into a single order intent."""

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
                event="proposals_received",
                message="Proposals received for consolidation.",
                data={
                    "symbol": symbol,
                    "proposal_count": len(proposal_list),
                    "agents": [proposal.agent_id for proposal in proposal_list],
                },
            )
        ]

        if kill_switch:
            audit.append(
                ResolutionAuditEntry(
                    timestamp=datetime.now(),
                    event="kill_switch",
                    message="Global kill-switch active; blocking all proposals.",
                    data={"reason": kill_switch_reason},
                )
            )
            return ResolvedOrderIntent(
                symbol=symbol,
                action=ResolutionAction.BLOCK,
                side=OrderSide.NEUTRAL,
                quantity=0,
                confidence=0.0,
                strategy=ResolutionStrategy.KILL_SWITCH,
                conflict_detected=False,
                proposal_count=len(proposal_list),
                supporting_agents=[proposal.agent_id for proposal in proposal_list],
                blocked_reason=kill_switch_reason or "global_kill_switch",
                reason="Trading blocked by global kill-switch.",
                resolved_at=datetime.now(),
                audit_trail=audit,
            )

        actionable = [
            proposal
            for proposal in proposal_list
            if proposal.side in (OrderSide.BUY, OrderSide.SELL)
        ]
        if not actionable:
            audit.append(
                ResolutionAuditEntry(
                    timestamp=datetime.now(),
                    event="no_actionable_proposals",
                    message="No BUY/SELL intents were provided.",
                    data={"symbol": symbol},
                )
            )
            return ResolvedOrderIntent(
                symbol=symbol,
                action=ResolutionAction.BLOCK,
                side=OrderSide.NEUTRAL,
                quantity=0,
                confidence=0.0,
                strategy=ResolutionStrategy.NO_ACTION,
                conflict_detected=False,
                proposal_count=len(proposal_list),
                supporting_agents=[proposal.agent_id for proposal in proposal_list],
                blocked_reason="no_actionable_proposals",
                reason="No actionable order intent was provided.",
                resolved_at=datetime.now(),
                audit_trail=audit,
            )

        side_buckets: dict[OrderSide, list[AgentOrderProposal]] = {
            OrderSide.BUY: [],
            OrderSide.SELL: [],
        }
        for proposal in actionable:
            side_buckets[proposal.side].append(proposal)

        active_sides = [side for side, bucket in side_buckets.items() if bucket]
        if len(active_sides) == 1:
            return self._resolve_consensus(symbol, side_buckets[active_sides[0]], audit)

        return self._resolve_conflict(symbol, side_buckets, audit)

    def _resolve_consensus(
        self,
        symbol: str,
        proposals: Sequence[AgentOrderProposal],
        audit: list[ResolutionAuditEntry],
    ) -> ResolvedOrderIntent:
        side = proposals[0].side
        total_weight = sum(proposal.weight for proposal in proposals)
        weighted_confidence = sum(
            proposal.confidence * proposal.weight for proposal in proposals
        ) / total_weight
        total_quantity = sum(proposal.quantity for proposal in proposals)
        winning_agents = [proposal.agent_id for proposal in proposals]
        scoreboard = {
            side.value: round(weighted_confidence, 6),
        }

        audit.append(
            ResolutionAuditEntry(
                timestamp=datetime.now(),
                event="consensus",
                message=f"Consensus detected on {side.value}.",
                data={
                    "symbol": symbol,
                    "side": side.value,
                    "weighted_confidence": round(weighted_confidence, 6),
                    "agent_ids": winning_agents,
                },
            )
        )

        return ResolvedOrderIntent(
            symbol=symbol,
            action=ResolutionAction.EXECUTE,
            side=side,
            quantity=max(1, round(total_quantity / len(proposals))),
            confidence=round(weighted_confidence, 6),
            strategy=ResolutionStrategy.CONSENSUS,
            conflict_detected=False,
            proposal_count=len(proposals),
            supporting_agents=winning_agents,
            winning_agent_ids=winning_agents,
            scoreboard=scoreboard,
            reason=f"Consensus on {side.value} across {len(proposals)} proposal(s).",
            resolved_at=datetime.now(),
            audit_trail=audit,
        )

    def _resolve_conflict(
        self,
        symbol: str,
        side_buckets: dict[OrderSide, list[AgentOrderProposal]],
        audit: list[ResolutionAuditEntry],
    ) -> ResolvedOrderIntent:
        side_scores: dict[OrderSide, float] = {}
        proposal_scores: dict[str, float] = {}
        for side, proposals in side_buckets.items():
            if not proposals:
                continue
            score = sum(proposal.confidence * proposal.weight for proposal in proposals)
            side_scores[side] = round(score, 6)
            for proposal in proposals:
                proposal_scores[proposal.agent_id] = round(
                    proposal.confidence * proposal.weight,
                    6,
                )

        winner_side = max(side_scores, key=side_scores.get)
        loser_side = OrderSide.SELL if winner_side == OrderSide.BUY else OrderSide.BUY
        winner_score = side_scores[winner_side]
        loser_score = side_scores.get(loser_side, 0.0)
        total_score = winner_score + loser_score
        score_gap = winner_score - loser_score
        normalized_gap = score_gap / total_score if total_score else 0.0
        winning_bucket = side_buckets[winner_side]
        winning_agents = [proposal.agent_id for proposal in winning_bucket]
        discarded_agents = [
            proposal.agent_id
            for proposal in side_buckets[loser_side]
        ]
        weighted_confidence = (
            sum(
                proposal.confidence * proposal.weight for proposal in winning_bucket
            )
            / sum(proposal.weight for proposal in winning_bucket)
        )
        winning_quantity = max(
            1,
            round(
                sum(proposal.quantity * proposal.weight for proposal in winning_bucket)
                / sum(proposal.weight for proposal in winning_bucket)
            ),
        )

        audit.append(
            ResolutionAuditEntry(
                timestamp=datetime.now(),
                event="conflict_detected",
                message="Direct BUY/SELL conflict detected.",
                data={
                    "symbol": symbol,
                    "side_scores": {side.value: score for side, score in side_scores.items()},
                    "proposal_scores": proposal_scores,
                },
            )
        )

        clear_win = normalized_gap >= self.tie_margin
        if clear_win and weighted_confidence >= self.min_execute_confidence:
            audit.append(
                ResolutionAuditEntry(
                    timestamp=datetime.now(),
                    event="weighted_priority",
                    message=f"Conflict resolved in favor of {winner_side.value}.",
                    data={
                        "winning_side": winner_side.value,
                        "losing_side": loser_side.value,
                        "score_gap": round(score_gap, 6),
                        "normalized_gap": round(normalized_gap, 6),
                    },
                )
            )
            return ResolvedOrderIntent(
                symbol=symbol,
                action=ResolutionAction.ADJUST,
                side=winner_side,
                quantity=winning_quantity,
                confidence=round(weighted_confidence, 6),
                strategy=ResolutionStrategy.WEIGHTED_PRIORITY,
                conflict_detected=True,
                proposal_count=sum(len(bucket) for bucket in side_buckets.values()),
                supporting_agents=winning_agents + discarded_agents,
                winning_agent_ids=winning_agents,
                discarded_agent_ids=discarded_agents,
                scoreboard={side.value: score for side, score in side_scores.items()},
                reason=(
                    f"Conflict resolved by weighted priority in favor of {winner_side.value}."
                ),
                adjustment_factor=round(max(0.5, normalized_gap + 0.5), 6),
                resolved_at=datetime.now(),
                audit_trail=audit,
            )

        audit.append(
            ResolutionAuditEntry(
                timestamp=datetime.now(),
                event="conflict_blocked",
                message="Conflict could not be resolved safely; blocking order.",
                data={
                    "winning_side": winner_side.value,
                    "score_gap": round(score_gap, 6),
                    "normalized_gap": round(normalized_gap, 6),
                    "tie_margin": self.tie_margin,
                },
            )
        )
        return ResolvedOrderIntent(
            symbol=symbol,
            action=ResolutionAction.BLOCK,
            side=OrderSide.NEUTRAL,
            quantity=0,
            confidence=0.0,
            strategy=ResolutionStrategy.TIE_BREAK,
            conflict_detected=True,
            proposal_count=sum(len(bucket) for bucket in side_buckets.values()),
            supporting_agents=winning_agents + discarded_agents,
            winning_agent_ids=winning_agents,
            discarded_agent_ids=discarded_agents,
            scoreboard={side.value: score for side, score in side_scores.items()},
            reason="Direct conflict without sufficient dominance.",
            blocked_reason="conflict_tie_or_low_dominance",
            resolved_at=datetime.now(),
            audit_trail=audit,
        )


__all__ = [
    "AgentOrderProposal",
    "MultiAgentConflictResolver",
    "OrderSide",
    "ResolutionAction",
    "ResolutionAuditEntry",
    "ResolutionStrategy",
    "ResolvedOrderIntent",
]
