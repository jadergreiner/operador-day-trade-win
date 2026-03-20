"""Composicao de runtime para contexto de abertura dos agentes."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from src.application.guardian_agent_coordinator import GuardianAgentCoordinator
from src.application.log_labels import OPENING_CONTEXT_LABEL
from src.application.macro_guardian_universal import MacroGuardianUniversal
from src.application.opening_context_audit import persist_opening_context_audit
from src.application.opening_context_policy import (
    OpeningContextPolicy,
    normalize_opening_context,
)


@dataclass(slots=True)
class OpeningContextRuntime:
    """Objeto agregado com servicos e payload de abertura."""

    macro_guardian: MacroGuardianUniversal
    coordinator: GuardianAgentCoordinator
    snapshot: Any
    features: dict[str, Any]
    policy: OpeningContextPolicy
    prompt_abertura_agentes: str


def initialize_opening_context_runtime(
    *,
    db_path: str,
    agent_name: str,
    source: str,
    session_id: str = "",
    mode: str = "",
    printer: Callable[[str], None] | None = None,
    logger: Any | None = None,
    operational_context_dir: str | Path | None = None,
) -> OpeningContextRuntime:
    """Inicializa MacroGuardianUniversal + Coordinator e anuncia o prompt."""
    macro_guardian = MacroGuardianUniversal(
        db_path=db_path,
        operational_context_dir=operational_context_dir,
    )
    coordinator = GuardianAgentCoordinator(macro_context_provider=macro_guardian)
    snapshot = macro_guardian.build_snapshot()
    features = macro_guardian.export_features(snapshot)
    policy = normalize_opening_context(features)
    prompt = str(features.get("prompt_abertura_agentes", "") or "")

    _apply_opening_context_to_environment(features, policy)
    _emit_opening_prompt(
        prompt=prompt,
        regime_macro=str(features.get("regime_macro", "")),
        vies_intraday=str(features.get("vies_intraday", "")),
        watchlist=features.get("watchlist", []),
        printer=printer,
        logger=logger,
    )
    try:
        persist_opening_context_audit(
            db_path,
            agent_name=agent_name,
            source=source,
            prompt_abertura_agentes=prompt,
            macro_context=features,
            session_id=session_id,
            mode=mode,
        )
    except Exception as exc:
        # Auditoria é suporte operacional; não deve bloquear a inicialização do agente.
        if logger is not None:
            logger.warning(
                "%s Falha ao persistir auditoria de contexto: %s",
                OPENING_CONTEXT_LABEL,
                exc,
            )
        elif printer is not None:
            printer(
                f"{OPENING_CONTEXT_LABEL} Falha ao persistir auditoria de contexto: {exc}"
            )

    return OpeningContextRuntime(
        macro_guardian=macro_guardian,
        coordinator=coordinator,
        snapshot=snapshot,
        features=features,
        policy=policy,
        prompt_abertura_agentes=prompt,
    )


def _apply_opening_context_to_environment(
    features: dict[str, Any],
    policy: OpeningContextPolicy,
) -> None:
    """Expõe o contexto no ambiente para consumidores legados."""
    os.environ["PROMPT_ABERTURA_AGENTES"] = str(
        features.get("prompt_abertura_agentes", "") or ""
    )
    os.environ["MACRO_REGIME_ABERTURA"] = str(features.get("regime_macro", "") or "")
    os.environ["VIES_INTRADAY_ABERTURA"] = str(
        features.get("vies_intraday", "") or ""
    )
    os.environ["OPENING_CONTEXT_WATCHLIST"] = json.dumps(
        list(policy.watchlist), ensure_ascii=False
    )
    os.environ["OPENING_CONTEXT_KILL_SWITCH_ATIVO"] = (
        "1" if policy.kill_switch_ativo else "0"
    )
    os.environ["OPENING_CONTEXT_JSON"] = json.dumps(
        policy.to_dict(), ensure_ascii=False
    )


def _emit_opening_prompt(
    *,
    prompt: str,
    regime_macro: str,
    vies_intraday: str,
    watchlist: Any,
    printer: Callable[[str], None] | None,
    logger: Any | None,
) -> None:
    """Exibe o resumo operacional de abertura em canais humanos."""
    lines = [
        "",
        f"{OPENING_CONTEXT_LABEL} Contexto operacional carregado",
        f"  Regime macro: {regime_macro or 'N/D'}",
        f"  Vies intraday: {vies_intraday or 'N/D'}",
    ]
    if watchlist:
        lines.append(f"  Watchlist: {', '.join(str(item) for item in watchlist)}")
    if prompt:
        lines.append(f"  Prompt agentes: {prompt}")

    if printer is not None:
        for line in lines:
            printer(line)

    if logger is not None:
        for line in lines[1:]:
            logger.info(line)
