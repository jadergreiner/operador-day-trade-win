"""
Decisor runtime de perfil do ProfitProtectionEngine por regime intraday.

Objetivo:
- Detectar quebra de regime em janela curta de trades fechados.
- Sugerir troca de perfil (conservador/agressivo/baseline) com regra simples.
- Manter lógica leve para uso dentro do loop operacional dos agentes RL.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from src.application.services.profit_protection_calibration_service import (
    DELTA_WIN_RATE_REGIME_PP,
    JANELA_RECENTE_MIN_TRADES,
    _detectar_regime_shift_por_win_rate,
)


@dataclass(frozen=True)
class DecisaoSwitchPerfilPP:
    """Resultado da avaliação de troca de perfil em runtime."""

    deve_trocar: bool
    perfil_atual: str
    perfil_sugerido: str
    regime_shift_detectado: bool
    win_rate_bloco_anterior: float
    win_rate_bloco_recente: float
    motivo: str


def aplicar_guardrail_cooldown_switch(
    *,
    ciclo_atual: int,
    ultimo_ciclo_switch: int | None,
    min_ciclos_entre_switches: int,
) -> tuple[bool, str]:
    """Aplica cooldown anti-thrashing entre trocas de perfil.

    Retorna:
    - permitido: bool
    - motivo: descrição curta para observabilidade em log
    """
    if min_ciclos_entre_switches <= 0:
        return True, "Cooldown desabilitado."

    if ultimo_ciclo_switch is None:
        return True, "Primeira troca permitida."

    ciclos_desde_ultimo = ciclo_atual - ultimo_ciclo_switch
    if ciclos_desde_ultimo >= min_ciclos_entre_switches:
        return True, "Cooldown cumprido."

    restante = min_ciclos_entre_switches - ciclos_desde_ultimo
    return (
        False,
        f"Cooldown anti-thrashing ativo: faltam {restante} ciclo(s).",
    )


def _extrair_resultados(trades_fechados: Iterable[dict], max_items: int) -> list[float]:
    resultados: list[float] = []
    for trade in list(trades_fechados)[-max_items:]:
        if not isinstance(trade, dict):
            continue

        valor = trade.get("pnl")
        if valor is None:
            valor = trade.get("resultado_final_pct")
        if valor is None:
            valor = trade.get("profit_loss")
        if valor is None:
            continue

        try:
            resultados.append(float(valor))
        except (TypeError, ValueError):
            continue
    return resultados


def decidir_switch_perfil_profit_protection(
    *,
    trades_fechados: Iterable[dict],
    perfil_atual: str,
    perfis_disponiveis: Sequence[str],
    janela_recente: int = JANELA_RECENTE_MIN_TRADES,
    delta_regime_pp: float = DELTA_WIN_RATE_REGIME_PP,
    max_items: int = 48,
) -> DecisaoSwitchPerfilPP:
    """Decide troca de perfil com base em recência e mudança de regime.

    Regra:
    - Se não houver evidência suficiente, mantém perfil atual.
    - Se houver regime shift e a janela recente piorar, prioriza conservador.
    - Se houver regime shift e a janela recente melhorar, prioriza agressivo.
    - Fallback para baseline quando perfil alvo não existir.
    """
    resultados = _extrair_resultados(trades_fechados, max_items=max_items)
    min_amostra = janela_recente * 2
    if len(resultados) < min_amostra:
        return DecisaoSwitchPerfilPP(
            deve_trocar=False,
            perfil_atual=perfil_atual,
            perfil_sugerido=perfil_atual,
            regime_shift_detectado=False,
            win_rate_bloco_anterior=0.0,
            win_rate_bloco_recente=0.0,
            motivo=(
                f"Amostra insuficiente para regime shift ({len(resultados)}/{min_amostra})."
            ),
        )

    bloco_anterior = resultados[-(janela_recente * 2):-janela_recente]
    bloco_recente = resultados[-janela_recente:]
    wr_anterior = sum(1 for r in bloco_anterior if r > 0.0) / len(bloco_anterior)
    wr_recente = sum(1 for r in bloco_recente if r > 0.0) / len(bloco_recente)

    regime_shift = _detectar_regime_shift_por_win_rate(
        resultados_pct=resultados,
        janela_recente=janela_recente,
        delta_pp=delta_regime_pp,
    )
    if not regime_shift:
        return DecisaoSwitchPerfilPP(
            deve_trocar=False,
            perfil_atual=perfil_atual,
            perfil_sugerido=perfil_atual,
            regime_shift_detectado=False,
            win_rate_bloco_anterior=wr_anterior,
            win_rate_bloco_recente=wr_recente,
            motivo="Sem regime shift relevante.",
        )

    if wr_recente < wr_anterior:
        alvos = ["conservador", "baseline"]
        racional = "Regime shift com degradação recente de win rate."
    else:
        alvos = ["agressivo", "baseline"]
        racional = "Regime shift com melhora recente de win rate."

    perfis_set = set(perfis_disponiveis)
    perfil_sugerido = perfil_atual
    for alvo in alvos:
        if alvo in perfis_set:
            perfil_sugerido = alvo
            break

    deve_trocar = perfil_sugerido != perfil_atual
    if not deve_trocar:
        racional += " Perfil sugerido já está ativo ou indisponível."

    return DecisaoSwitchPerfilPP(
        deve_trocar=deve_trocar,
        perfil_atual=perfil_atual,
        perfil_sugerido=perfil_sugerido,
        regime_shift_detectado=True,
        win_rate_bloco_anterior=wr_anterior,
        win_rate_bloco_recente=wr_recente,
        motivo=racional,
    )
