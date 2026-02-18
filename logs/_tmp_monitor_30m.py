import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, time as dtime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import scripts.agente_micro_tendencia_winfut as a

ITERATIONS = 60
INTERVAL_SECONDS = 30


def main():
    a.SIMULATE_MODE = True
    a.AUTO_TRADING_ENABLED = True
    cfg = a._get_config()
    a.DB_PATH = cfg.db_path

    a.create_database(a.DB_PATH)
    a._create_micro_trend_tables(a.DB_PATH)

    a.PREGAO_INICIO = dtime(0, 0)
    a.PREGAO_FIM = dtime(23, 59, 59)

    freq = Counter()
    cycles = []
    trading_mgr = None

    started_at = datetime.now().isoformat()
    print(f"[MONITOR] inicio={started_at} iteracoes={ITERATIONS} intervalo={INTERVAL_SECONDS}s")

    for i in range(1, ITERATIONS + 1):
        mt5 = a._connect_mt5(cfg)

        if trading_mgr is None:
            trading_mgr = a.MicroTradingManager(mt5, a.SYMBOL)
        else:
            trading_mgr.mt5 = mt5

        result = a._run_cycle(mt5)
        reasons = list(getattr(result, "_rejection_reasons", []) or [])
        for rr in reasons:
            freq[rr] += 1

        action = "no_opp"
        eval_reason = None

        if result.opportunities:
            can_trade, cant_reason = trading_mgr.can_trade()
            if can_trade:
                best = max(result.opportunities, key=lambda o: (o.confidence, o.risk_reward))
                should_enter, eval_reason = trading_mgr.evaluate_opportunity(best)
                if should_enter:
                    a._persist_simulated_trade(a.DB_PATH, best, result)
                    action = "sim_signal_logged"
                else:
                    action = "eval_rejected"
                    if eval_reason:
                        freq[eval_reason] += 1
            else:
                action = "cant_trade"
                eval_reason = cant_reason
                if cant_reason:
                    freq[cant_reason] += 1

        a._persist_cycle(a.DB_PATH, result)
        kpi = a._persist_reversal_false_positive_kpi(a.DB_PATH)

        snapshot = {
            "cycle": i,
            "timestamp": datetime.now().isoformat(),
            "macro_score": float(result.macro_score) if result.macro_score is not None else None,
            "micro_score": float(result.micro_score) if result.micro_score is not None else None,
            "opportunities": len(result.opportunities or []),
            "reasons": reasons,
            "action": action,
            "eval_reason": eval_reason,
            "kpi": kpi,
        }
        cycles.append(snapshot)

        print(
            "[CICLO {i:02d}] opp={opp} motivos={mot} acao={ac} | KPI(total={t}, resolved={r}, wins={w}, losses={l}, fp={fp:.2f})".format(
                i=i,
                opp=snapshot["opportunities"],
                mot=len(reasons),
                ac=action,
                t=kpi["total"],
                r=kpi["resolved"],
                w=kpi["wins"],
                l=kpi["losses"],
                fp=kpi["false_positive_rate"],
            )
        )

        try:
            mt5.disconnect()
        except Exception:
            pass

        if i < ITERATIONS:
            time.sleep(INTERVAL_SECONDS)

    out = {
        "generated_at": datetime.now().isoformat(),
        "window_minutes": (ITERATIONS * INTERVAL_SECONDS) / 60,
        "batch_size": ITERATIONS,
        "interval_seconds": INTERVAL_SECONDS,
        "db_path": a.DB_PATH,
        "reason_frequency": dict(sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))),
        "kpi_series": [
            {
                "cycle": c["cycle"],
                "timestamp": c["timestamp"],
                "kpi_total": c["kpi"]["total"],
                "kpi_resolved": c["kpi"]["resolved"],
                "kpi_wins": c["kpi"]["wins"],
                "kpi_losses": c["kpi"]["losses"],
                "kpi_fp": c["kpi"]["false_positive_rate"],
            }
            for c in cycles
        ],
        "cycles": cycles,
    }

    json_path = "logs/consolidado_monitor_30m_rejeicao_kpi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"[OK] consolidado salvo em {json_path}")
    print(f"[FREQ] {out['reason_frequency']}")


if __name__ == "__main__":
    main()
