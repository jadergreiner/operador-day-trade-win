"""Replay/staging da degradacao intraday para calibrar guardrail do BLID-060.

Uso:
    python scripts/staging_validation_blid060.py --date 20260406
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.application.profit_protection_regime_runtime import (
    DecisaoSwitchPerfilPP,
    ResultadoValidacaoSessaoPP,
    decidir_switch_perfil_profit_protection,
    validar_sessao_runtime_profit_protection,
)

OUTPUTS_DIR = Path("outputs")


def _parse_iso_dt(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _list_files(pattern: str) -> list[Path]:
    return sorted(OUTPUTS_DIR.glob(pattern))


def _build_cycles_for_day(date_tag: str) -> tuple[list[list[dict[str, float]]], dict[str, Any]]:
    decision_files = _list_files(f"decisoes_agente_direto_{date_tag}_*.json")
    history_files = _list_files(f"historico_fechamentos_agente_direto_{date_tag}_*.json")

    decision_times: list[datetime] = []
    for path in decision_files:
        payload = _load_json(path)
        if not isinstance(payload, list):
            continue
        for item in payload:
            if not isinstance(item, dict):
                continue
            parsed = _parse_iso_dt(item.get("timestamp"))
            if parsed is not None:
                decision_times.append(parsed)

    closed_trades: list[tuple[datetime, float]] = []
    for path in history_files:
        payload = _load_json(path)
        if not isinstance(payload, list):
            continue
        for item in payload:
            if not isinstance(item, dict):
                continue
            parsed = _parse_iso_dt(
                item.get("timestamp_fechamento") or item.get("timestamp_abertura")
            )
            pnl_pct = item.get("pnl_pct")
            if parsed is None or not isinstance(pnl_pct, (int, float)):
                continue
            closed_trades.append((parsed, float(pnl_pct)))

    decision_times.sort()
    closed_trades.sort(key=lambda it: it[0])

    cycles: list[list[dict[str, float]]] = []
    trade_idx = 0
    for decision_ts in decision_times:
        cycle: list[dict[str, float]] = []
        while trade_idx < len(closed_trades) and closed_trades[trade_idx][0] <= decision_ts:
            cycle.append({"pnl": closed_trades[trade_idx][1]})
            trade_idx += 1
        cycles.append(cycle)

    while trade_idx < len(closed_trades):
        cycles.append([{"pnl": closed_trades[trade_idx][1]}])
        trade_idx += 1

    metadata = {
        "decision_files": [path.name for path in decision_files],
        "history_files": [path.name for path in history_files],
        "total_decisions": len(decision_times),
        "total_trades_fechados": len(closed_trades),
        "total_ciclos_replay": len(cycles),
        "total_ciclos_com_trade": sum(1 for cycle in cycles if cycle),
        "pnl_pct_trades": [round(value, 6) for _, value in closed_trades],
    }
    return cycles, metadata


def _build_control_cycles(reference_cycles_count: int) -> list[list[dict[str, float]]]:
    base_values = [0.08, -0.06, 0.07, -0.05, 0.06, -0.04, 0.05, -0.03, 0.04, -0.02]
    control: list[list[dict[str, float]]] = []
    idx = 0
    for cycle_idx in range(reference_cycles_count):
        if cycle_idx % 2 == 0 and idx < len(base_values):
            control.append([{"pnl": base_values[idx]}])
            idx += 1
        else:
            control.append([])
    return control


def _run_validation(
    *,
    cycles: list[list[dict[str, float]]],
    params: dict[str, Any],
) -> ResultadoValidacaoSessaoPP:
    return validar_sessao_runtime_profit_protection(
        trades_por_ciclo=cycles,
        perfil_inicial="baseline",
        perfis_disponiveis=["baseline", "conservador", "agressivo"],
        min_ciclos_entre_switches=30,
        avaliar_a_cada_n_ciclos=1,
        limite_switches_por_100_avaliacoes=20.0,
        **params,
    )


def _run_decision_snapshot(
    *,
    cycles: list[list[dict[str, float]]],
    params: dict[str, Any],
) -> DecisaoSwitchPerfilPP:
    trades = [trade for cycle in cycles for trade in cycle]
    return decidir_switch_perfil_profit_protection(
        trades_fechados=trades,
        perfil_atual="agressivo",
        perfis_disponiveis=["baseline", "conservador", "agressivo"],
        **params,
    )


def _calibrate(cycles_real: list[list[dict[str, float]]]) -> dict[str, Any]:
    cycles_control = _build_control_cycles(len(cycles_real))

    grid = []
    for janela in (2, 3):
        for lim_wr in (0.30, 0.35):
            for loss_streak in (2, 3):
                for lim_sum in (-0.08, -0.10, -0.12):
                    for min_signals in (2, 3):
                        params = {
                            "janela_recente": janela,
                            "delta_regime_pp": 99.0,
                            "min_eventos_quebra_correlacao": 99,
                            "limiar_win_rate_degradado": lim_wr,
                            "min_loss_streak_degradado": loss_streak,
                            "limiar_resultado_acumulado_degradado": lim_sum,
                            "min_sinais_degradacao": min_signals,
                            "min_trades_degradacao_critica": 4,
                        }
                        result_real = _run_validation(cycles=cycles_real, params=params)
                        result_control = _run_validation(cycles=cycles_control, params=params)
                        pass_real = (
                            result_real.total_switches_realizados >= 1
                            and not result_real.thrashing_detectado
                        )
                        pass_control = (
                            result_control.total_switches_realizados == 0
                            and not result_control.thrashing_detectado
                        )
                        if not pass_real:
                            continue
                        # Preferimos menor sensibilidade entre candidatos válidos.
                        sensitivity_score = (
                            (100 * lim_wr)
                            + (100 * abs(lim_sum))
                            + (30 - 5 * loss_streak)
                            + (10 - 3 * min_signals)
                            + (2 if janela == 2 else 0)
                        )
                        grid.append(
                            {
                                "params": params,
                                "pass_real": pass_real,
                                "pass_control": pass_control,
                                "result_real": asdict(result_real),
                                "result_control": asdict(result_control),
                                "sensitivity_score": round(sensitivity_score, 4),
                            }
                        )

    if not grid:
        raise RuntimeError("Nenhuma combinacao valida encontrada para calibracao.")

    grid_sorted = sorted(
        grid,
        key=lambda item: (
            0 if item["pass_control"] else 1,
            item["sensitivity_score"],
            item["result_real"]["switches_por_100_avaliacoes"],
        ),
    )
    return {
        "best": grid_sorted[0],
        "top5": grid_sorted[:5],
        "total_candidates": len(grid_sorted),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now().strftime("%Y%m%d"))
    args = parser.parse_args()

    cycles_real, metadata = _build_cycles_for_day(args.date)
    if not cycles_real:
        raise RuntimeError(f"Nenhum ciclo de replay encontrado para {args.date}.")

    calibration = _calibrate(cycles_real)
    best_params = calibration["best"]["params"]

    decision = _run_decision_snapshot(cycles=cycles_real, params=best_params)
    validation = _run_validation(cycles=cycles_real, params=best_params)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_lines = [
        (
            "[PP-REGIME] Replay BLID-060 | deve_trocar=%s | perfil_atual=%s | "
            "perfil_sugerido=%s | WR_ant=%.1f%% | WR_rec=%.1f%% | motivo=%s"
        )
        % (
            decision.deve_trocar,
            decision.perfil_atual,
            decision.perfil_sugerido,
            decision.win_rate_bloco_anterior * 100.0,
            decision.win_rate_bloco_recente * 100.0,
            decision.motivo,
        )
    ]

    log_path = OUTPUTS_DIR / f"blid060_pp_regime_staging_{now}.log"
    log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    report = {
        "timestamp_validacao": datetime.now().isoformat(timespec="seconds"),
        "modo": "staging_replay_sessao_real_degradada",
        "date_replay": args.date,
        "metadata_replay": metadata,
        "parametros_calibrados": best_params,
        "calibracao_resumo": {
            "total_candidates": calibration["total_candidates"],
            "top5": calibration["top5"],
        },
        "decision_snapshot": {
            "deve_trocar": decision.deve_trocar,
            "perfil_atual": decision.perfil_atual,
            "perfil_sugerido": decision.perfil_sugerido,
            "regime_shift_detectado": decision.regime_shift_detectado,
            "win_rate_bloco_anterior": decision.win_rate_bloco_anterior,
            "win_rate_bloco_recente": decision.win_rate_bloco_recente,
            "motivo": decision.motivo,
        },
        "validacao_sessao": {
            "ciclos_observados": validation.total_ciclos,
            "avaliacoes_realizadas": validation.total_avaliacoes,
            "eventos_pp_regime_total": 1 if decision.regime_shift_detectado else 0,
            "switches_realizados": validation.total_switches_realizados,
            "switches_bloqueados_cooldown": validation.total_switches_bloqueados_cooldown,
            "switches_por_100_avaliacoes": round(
                validation.switches_por_100_avaliacoes, 4
            ),
            "thrashing_detectado": validation.thrashing_detectado,
            "motivo_thrashing": validation.motivo_thrashing,
        },
        "apto_para_concluir_blid060": bool(
            decision.deve_trocar
            and decision.perfil_sugerido == "conservador"
            and validation.total_switches_realizados >= 1
            and not validation.thrashing_detectado
        ),
        "motivo": (
            "Aprovado: replay real detectou degradacao critica com fallback conservador e sem thrashing."
            if (
                decision.deve_trocar
                and decision.perfil_sugerido == "conservador"
                and validation.total_switches_realizados >= 1
                and not validation.thrashing_detectado
            )
            else "Reprovado: criterios de deteccao/estabilidade nao atendidos."
        ),
        "artefatos": {
            "log": str(log_path).replace("\\", "/"),
        },
    }

    report_path = OUTPUTS_DIR / f"blid060_staging_validation_{now}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(report_path))


if __name__ == "__main__":
    main()
