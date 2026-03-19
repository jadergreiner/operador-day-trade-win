"""Guardian coordinator for multi-agent order proposals.

The coordinator receives proposals from multiple agents, applies the conflict
resolver, enforces the global kill-switch, and emits a consolidated decision
plus an operational summary for audit and monitoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from enum import Enum
from collections.abc import Mapping
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
    macro_regime: str = ""
    vies_intraday: str = ""
    prompt_abertura_agentes: str = ""
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
    macro_regime: str = ""
    vies_intraday: str = ""
    prompt_abertura_agentes: str = ""
    macro_context: dict[str, Any] = field(default_factory=dict)
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
        macro_context_provider: Mapping[str, Any] | Any | None = None,
    ) -> None:
        self.resolver = resolver or MultiAgentConflictResolver()
        self.macro_context_provider = macro_context_provider

    def coordinate(
        self,
        proposals: Sequence[AgentOrderProposal],
        *,
        kill_switch_active: bool = False,
        kill_switch_reason: str = "",
        macro_context: Mapping[str, Any] | Any | None = None,
    ) -> GuardianCoordinationResult:
        """Coordinate multiple proposals for a single symbol."""

        proposal_list = list(proposals)
        if not proposal_list:
            raise ValueError("proposals cannot be empty")

        symbol = proposal_list[0].symbol
        for proposal in proposal_list:
            if proposal.symbol != symbol:
                raise ValueError("all proposals must target the same symbol")

        resolved_macro_context = self._resolve_macro_context(macro_context)
        macro_regime = self._read_macro_context_value(
            resolved_macro_context,
            "regime_macro",
        )
        vies_intraday = self._read_macro_context_value(
            resolved_macro_context,
            "vies_intraday",
            "intraday_bias",
        )
        prompt_abertura = self._read_macro_context_value(
            resolved_macro_context,
            "prompt_abertura_agentes",
            "opening_prompt",
        )

        if not kill_switch_active and resolved_macro_context:
            kill_switch_active, kill_switch_reason = self._macro_context_to_kill_switch(
                resolved_macro_context
            )

        audit: list[ResolutionAuditEntry] = [
            ResolutionAuditEntry(
                timestamp=datetime.now(),
                event="coordination_started",
                message="Guardian coordination started.",
                data={
                    "symbol": symbol,
                    "proposal_count": len(proposal_list),
                    "agent_ids": [proposal.agent_id for proposal in proposal_list],
                    "macro_regime": macro_regime,
                    "vies_intraday": vies_intraday,
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
                macro_regime=macro_regime,
                vies_intraday=vies_intraday,
                prompt_abertura_agentes=prompt_abertura,
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
                macro_regime=macro_regime,
                vies_intraday=vies_intraday,
                prompt_abertura_agentes=prompt_abertura,
                macro_context=resolved_macro_context,
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

        if macro_regime:
            action_items.append(f"respect_macro_regime={macro_regime}")
        if vies_intraday:
            action_items.append(f"respect_intraday_bias={vies_intraday}")
        if prompt_abertura:
            action_items.append("publish_opening_prompt")

        summary = OperationalSummary(
            symbol=symbol,
            decision=decision,
            strategy=resolution.strategy,
            proposal_count=len(proposal_list),
            agent_count=len({proposal.agent_id for proposal in proposal_list}),
            conflict_detected=resolution.conflict_detected,
            kill_switch_active=False,
            message=message,
            macro_regime=macro_regime,
            vies_intraday=vies_intraday,
            prompt_abertura_agentes=prompt_abertura,
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
            macro_regime=macro_regime,
            vies_intraday=vies_intraday,
            prompt_abertura_agentes=prompt_abertura,
            macro_context=resolved_macro_context,
            summary=summary,
            resolution=resolution,
            audit_trail=audit,
        )

    def coordinate_with_macro_context(
        self,
        proposals: Sequence[AgentOrderProposal],
        *,
        macro_context: Mapping[str, Any] | Any,
    ) -> GuardianCoordinationResult:
        """Coordinate proposals using a macro snapshot or macro context mapping."""

        kill_switch_active, kill_switch_reason = self._macro_context_to_kill_switch(
            macro_context
        )
        return self.coordinate(
            proposals,
            kill_switch_active=kill_switch_active,
            kill_switch_reason=kill_switch_reason,
            macro_context=macro_context,
        )

    @staticmethod
    def _macro_context_to_kill_switch(
        macro_context: Mapping[str, Any] | Any,
    ) -> tuple[bool, str]:
        """Extract the global kill-switch state from a macro context."""

        def _read(field_name: str, default: Any = None) -> Any:
            if isinstance(macro_context, Mapping):
                return macro_context.get(field_name, default)
            return getattr(macro_context, field_name, default)

        kill_switch_active = bool(
            _read("kill_switch_ativo", _read("active_kill_switch", False))
        )

        reason = _read("kill_switch_reason", "")
        if not reason:
            reason = _read("reason", "")
        if not reason and kill_switch_active:
            regime_macro = _read("regime_macro", "")
            score_guardian = _read("score_guardian", None)
            alertas_ativos = _read("alertas_ativos", None)
            parts: list[str] = ["macro_context kill switch ativo"]
            if regime_macro:
                parts.append(f"regime={regime_macro}")
            if score_guardian is not None:
                parts.append(f"score_guardian={score_guardian}")
            if alertas_ativos is not None:
                parts.append(f"alertas_ativos={alertas_ativos}")
            reason = "; ".join(parts)

        return kill_switch_active, str(reason).strip()

    def _resolve_macro_context(
        self,
        macro_context: Mapping[str, Any] | Any | None,
    ) -> dict[str, Any]:
        """Resolve contexto macro a partir de payload explicito ou provider padrao."""
        source = macro_context if macro_context is not None else self.macro_context_provider
        if source is None:
            return {}

        if isinstance(source, Mapping):
            return {str(key): value for key, value in source.items()}

        if callable(source):
            try:
                source = source()
            except Exception:
                return {}
            if isinstance(source, Mapping):
                return {str(key): value for key, value in source.items()}

        export_features = getattr(source, "export_features", None)
        if callable(export_features):
            try:
                payload = export_features()
            except TypeError:
                payload = export_features(None)
            except Exception:
                payload = {}
            if isinstance(payload, Mapping):
                return {str(key): value for key, value in payload.items()}

        build_snapshot = getattr(source, "build_snapshot", None)
        if callable(build_snapshot):
            try:
                snapshot = build_snapshot()
            except Exception:
                snapshot = None
            if snapshot is not None:
                to_feature_dict = getattr(snapshot, "to_feature_dict", None)
                if callable(to_feature_dict):
                    payload = to_feature_dict()
                    if isinstance(payload, Mapping):
                        return {str(key): value for key, value in payload.items()}
                to_dict = getattr(snapshot, "to_dict", None)
                if callable(to_dict):
                    payload = to_dict()
                    if isinstance(payload, Mapping):
                        return {str(key): value for key, value in payload.items()}

        return {}

    @staticmethod
    def _read_macro_context_value(
        macro_context: Mapping[str, Any],
        *keys: str,
    ) -> str:
        """Extrai um valor textual do contexto macro sem acoplar a um schema unico."""
        for key in keys:
            value = macro_context.get(key)
            if value not in (None, ""):
                return str(value).strip()
        return ""


__all__ = [
    "GuardianAgentCoordinator",
    "GuardianCoordinationResult",
    "OperationalSummary",
]
