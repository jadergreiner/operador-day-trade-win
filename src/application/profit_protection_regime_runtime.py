"""
Decisor runtime de perfil do ProfitProtectionEngine por regime intraday.

Objetivo:
- Detectar quebra de regime em janela curta de trades fechados.
- Sugerir troca de perfil (conservador/agressivo/baseline) com regra simples.
- Manter lógica leve para uso dentro do loop operacional dos agentes RL.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

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


@dataclass(frozen=True)
class ResultadoValidacaoSessaoPP:
    """Resumo de estabilidade do runtime adaptativo em sessao simulada."""

    total_ciclos: int
    total_avaliacoes: int
    total_switches_realizados: int
    total_switches_bloqueados_cooldown: int
    ciclos_switch_realizado: tuple[int, ...]
    thrashing_detectado: bool
    switches_por_100_avaliacoes: float
    motivo_thrashing: str


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


def _extrair_resultados(
    trades_fechados: Iterable[Mapping[str, object]],
    max_items: int,
) -> list[float]:
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

        if isinstance(valor, bool):
            continue
        if isinstance(valor, (int, float, str)):
            try:
                resultados.append(float(valor))
            except ValueError:
                continue
    return resultados


def _detectar_quebra_correlacao(
    *,
    trades_fechados: Iterable[Mapping[str, object]],
    janela_recente: int,
    limiar_quebra_correlacao: float,
    min_eventos_quebra_correlacao: int,
) -> bool:
    if min_eventos_quebra_correlacao <= 0:
        return False

    eventos = 0
    for trade in list(trades_fechados)[-janela_recente:]:
        if not isinstance(trade, dict):
            continue

        valor_quebra = trade.get("quebra_correlacao")
        if isinstance(valor_quebra, bool) and valor_quebra:
            eventos += 1
            continue

        correlacao = trade.get("correlacao_rolling")
        if correlacao is None:
            correlacao = trade.get("rolling_correlation")
        if isinstance(correlacao, bool) or correlacao is None:
            continue
        if isinstance(correlacao, (int, float, str)):
            try:
                valor_corr = abs(float(correlacao))
            except ValueError:
                continue
            if valor_corr < limiar_quebra_correlacao:
                eventos += 1

    return eventos >= min_eventos_quebra_correlacao


def _detectar_degradacao_intraday_critica(
    *,
    bloco_recente: Sequence[float],
    limiar_win_rate_degradado: float,
    min_loss_streak_degradado: int,
    limiar_resultado_acumulado_degradado: float,
    min_sinais_degradacao: int,
) -> tuple[bool, str]:
    if not bloco_recente:
        return False, "Sem janela recente para avaliar degradacao intraday."

    total = len(bloco_recente)
    wins = sum(1 for valor in bloco_recente if valor > 0.0)
    win_rate_recente = wins / total

    loss_streak_atual = 0
    pior_loss_streak = 0
    for valor in bloco_recente:
        if valor < 0.0:
            loss_streak_atual += 1
            if loss_streak_atual > pior_loss_streak:
                pior_loss_streak = loss_streak_atual
        else:
            loss_streak_atual = 0

    resultado_acumulado = float(sum(bloco_recente))

    sinais: list[str] = []
    if win_rate_recente <= limiar_win_rate_degradado:
        sinais.append(
            f"win_rate_recente={win_rate_recente:.2f}<=limiar={limiar_win_rate_degradado:.2f}"
        )
    if pior_loss_streak >= min_loss_streak_degradado:
        sinais.append(
            f"loss_streak={pior_loss_streak}>=min={min_loss_streak_degradado}"
        )
    if resultado_acumulado <= limiar_resultado_acumulado_degradado:
        sinais.append(
            "resultado_acumulado="
            f"{resultado_acumulado:.4f}<=limiar={limiar_resultado_acumulado_degradado:.4f}"
        )

    if len(sinais) < min_sinais_degradacao:
        return False, "Degradacao intraday nao confirmada."

    return True, "Degradacao intraday critica: " + "; ".join(sinais)


def decidir_switch_perfil_profit_protection(
    *,
    trades_fechados: Iterable[Mapping[str, object]],
    perfil_atual: str,
    perfis_disponiveis: Sequence[str],
    janela_recente: int = JANELA_RECENTE_MIN_TRADES,
    delta_regime_pp: float = DELTA_WIN_RATE_REGIME_PP,
    limiar_quebra_correlacao: float = 0.30,
    min_eventos_quebra_correlacao: int = 2,
    limiar_win_rate_degradado: float = 0.30,
    min_loss_streak_degradado: int = 3,
    limiar_resultado_acumulado_degradado: float = -0.08,
    min_sinais_degradacao: int = 2,
    min_trades_degradacao_critica: int = 4,
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
    bloco_recente_degradacao = resultados[-min(janela_recente, len(resultados)):] if resultados else []
    degradacao_critica, motivo_degradacao = _detectar_degradacao_intraday_critica(
        bloco_recente=bloco_recente_degradacao,
        limiar_win_rate_degradado=limiar_win_rate_degradado,
        min_loss_streak_degradado=min_loss_streak_degradado,
        limiar_resultado_acumulado_degradado=limiar_resultado_acumulado_degradado,
        min_sinais_degradacao=min_sinais_degradacao,
    )

    if len(resultados) < min_amostra:
        if degradacao_critica and len(bloco_recente_degradacao) >= min_trades_degradacao_critica:
            perfis_set = set(perfis_disponiveis)
            perfil_sugerido = "conservador" if "conservador" in perfis_set else "baseline"
            deve_trocar = perfil_sugerido != perfil_atual
            if not deve_trocar:
                motivo_degradacao += " Perfil sugerido já está ativo ou indisponível."
            return DecisaoSwitchPerfilPP(
                deve_trocar=deve_trocar,
                perfil_atual=perfil_atual,
                perfil_sugerido=perfil_sugerido,
                regime_shift_detectado=True,
                win_rate_bloco_anterior=0.0,
                win_rate_bloco_recente=(
                    sum(1 for r in bloco_recente_degradacao if r > 0.0) / len(bloco_recente_degradacao)
                    if bloco_recente_degradacao
                    else 0.0
                ),
                motivo=(
                    "Amostra parcial com degradacao critica detectada; "
                    f"{motivo_degradacao}"
                ),
            )
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
    quebra_correlacao = _detectar_quebra_correlacao(
        trades_fechados=trades_fechados,
        janela_recente=janela_recente,
        limiar_quebra_correlacao=limiar_quebra_correlacao,
        min_eventos_quebra_correlacao=min_eventos_quebra_correlacao,
    )
    if not regime_shift and not quebra_correlacao and not degradacao_critica:
        return DecisaoSwitchPerfilPP(
            deve_trocar=False,
            perfil_atual=perfil_atual,
            perfil_sugerido=perfil_atual,
            regime_shift_detectado=False,
            win_rate_bloco_anterior=wr_anterior,
            win_rate_bloco_recente=wr_recente,
            motivo="Sem regime shift relevante.",
        )

    if degradacao_critica:
        alvos = ["conservador", "baseline"]
        racional = motivo_degradacao
    elif quebra_correlacao and not regime_shift:
        alvos = ["conservador", "baseline"]
        racional = (
            "Quebra de correlacao rolling detectada na janela recente; "
            "aplicando postura conservadora."
        )
    elif wr_recente < wr_anterior:
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
        regime_shift_detectado=regime_shift or quebra_correlacao or degradacao_critica,
        win_rate_bloco_anterior=wr_anterior,
        win_rate_bloco_recente=wr_recente,
        motivo=racional,
    )


def validar_sessao_runtime_profit_protection(
    *,
    trades_por_ciclo: Sequence[Iterable[Mapping[str, object]]],
    perfil_inicial: str,
    perfis_disponiveis: Sequence[str],
    min_ciclos_entre_switches: int,
    avaliar_a_cada_n_ciclos: int = 10,
    janela_recente: int = JANELA_RECENTE_MIN_TRADES,
    delta_regime_pp: float = DELTA_WIN_RATE_REGIME_PP,
    limiar_quebra_correlacao: float = 0.30,
    min_eventos_quebra_correlacao: int = 2,
    limiar_win_rate_degradado: float = 0.30,
    min_loss_streak_degradado: int = 3,
    limiar_resultado_acumulado_degradado: float = -0.08,
    min_sinais_degradacao: int = 2,
    min_trades_degradacao_critica: int = 4,
    max_items: int = 48,
    limite_switches_por_100_avaliacoes: float = 20.0,
) -> ResultadoValidacaoSessaoPP:
    """Valida estabilidade do runtime em sessao simulada.

    O objetivo e reproduzir o comportamento do loop online:
    - acumular trades fechados por ciclo;
    - avaliar switch em cadencia fixa;
    - aplicar cooldown anti-thrashing.
    """
    if avaliar_a_cada_n_ciclos <= 0:
        raise ValueError("avaliar_a_cada_n_ciclos deve ser > 0.")
    if limite_switches_por_100_avaliacoes < 0:
        raise ValueError("limite_switches_por_100_avaliacoes deve ser >= 0.")
    if limiar_quebra_correlacao < 0:
        raise ValueError("limiar_quebra_correlacao deve ser >= 0.")
    if min_eventos_quebra_correlacao < 0:
        raise ValueError("min_eventos_quebra_correlacao deve ser >= 0.")
    if not 0.0 <= limiar_win_rate_degradado <= 1.0:
        raise ValueError("limiar_win_rate_degradado deve estar entre 0 e 1.")
    if min_loss_streak_degradado < 1:
        raise ValueError("min_loss_streak_degradado deve ser >= 1.")
    if min_sinais_degradacao < 1:
        raise ValueError("min_sinais_degradacao deve ser >= 1.")
    if min_trades_degradacao_critica < 1:
        raise ValueError("min_trades_degradacao_critica deve ser >= 1.")

    historico_trades: list[Mapping[str, object]] = []
    perfil_atual = perfil_inicial
    ultimo_ciclo_switch: int | None = None

    total_avaliacoes = 0
    total_switches_realizados = 0
    total_switches_bloqueados_cooldown = 0
    ciclos_switch_realizado: list[int] = []

    for ciclo_atual, trades_ciclo in enumerate(trades_por_ciclo, start=1):
        historico_trades.extend(trade for trade in trades_ciclo if isinstance(trade, dict))

        if ciclo_atual % avaliar_a_cada_n_ciclos != 0:
            continue

        total_avaliacoes += 1
        decisao = decidir_switch_perfil_profit_protection(
            trades_fechados=historico_trades,
            perfil_atual=perfil_atual,
            perfis_disponiveis=perfis_disponiveis,
            janela_recente=janela_recente,
            delta_regime_pp=delta_regime_pp,
            limiar_quebra_correlacao=limiar_quebra_correlacao,
            min_eventos_quebra_correlacao=min_eventos_quebra_correlacao,
            limiar_win_rate_degradado=limiar_win_rate_degradado,
            min_loss_streak_degradado=min_loss_streak_degradado,
            limiar_resultado_acumulado_degradado=limiar_resultado_acumulado_degradado,
            min_sinais_degradacao=min_sinais_degradacao,
            min_trades_degradacao_critica=min_trades_degradacao_critica,
            max_items=max_items,
        )
        if not decisao.deve_trocar:
            continue

        permitido, _ = aplicar_guardrail_cooldown_switch(
            ciclo_atual=ciclo_atual,
            ultimo_ciclo_switch=ultimo_ciclo_switch,
            min_ciclos_entre_switches=min_ciclos_entre_switches,
        )
        if not permitido:
            total_switches_bloqueados_cooldown += 1
            continue

        perfil_atual = decisao.perfil_sugerido
        ultimo_ciclo_switch = ciclo_atual
        total_switches_realizados += 1
        ciclos_switch_realizado.append(ciclo_atual)

    switches_por_100_avaliacoes = (
        (total_switches_realizados / total_avaliacoes) * 100.0 if total_avaliacoes > 0 else 0.0
    )
    thrashing_detectado = switches_por_100_avaliacoes > limite_switches_por_100_avaliacoes
    if total_avaliacoes == 0:
        motivo_thrashing = "Sem avaliacoes suficientes para classificar thrashing."
    elif thrashing_detectado:
        motivo_thrashing = (
            "Taxa de switch acima do limite: "
            f"{switches_por_100_avaliacoes:.2f} > {limite_switches_por_100_avaliacoes:.2f}."
        )
    else:
        motivo_thrashing = (
            "Taxa de switch dentro do limite: "
            f"{switches_por_100_avaliacoes:.2f} <= {limite_switches_por_100_avaliacoes:.2f}."
        )

    return ResultadoValidacaoSessaoPP(
        total_ciclos=len(trades_por_ciclo),
        total_avaliacoes=total_avaliacoes,
        total_switches_realizados=total_switches_realizados,
        total_switches_bloqueados_cooldown=total_switches_bloqueados_cooldown,
        ciclos_switch_realizado=tuple(ciclos_switch_realizado),
        thrashing_detectado=thrashing_detectado,
        switches_por_100_avaliacoes=switches_por_100_avaliacoes,
        motivo_thrashing=motivo_thrashing,
    )
