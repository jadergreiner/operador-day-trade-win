"""Runner CLI do backtest A/B (Baseline vs Swing Puro)."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import sys
from types import SimpleNamespace

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.application.services.sl_tp_ab_backtest import (
    BacktestConfig,
    get_cost_profile,
    run_ab_backtest,
    save_report_markdown,
    save_summary_json,
    save_trades_csv,
)
from src.application.services.win_data_ingestion import ingest_win_history_auto


def _default_dates() -> tuple[str, str]:
    end = datetime.now().date()
    start = end - timedelta(days=365)
    return start.isoformat(), end.isoformat()


def main() -> int:
    start_default, end_default = _default_dates()

    parser = argparse.ArgumentParser(
        description="Backtest A/B de longo prazo para SL/TP (WIN contínuo)."
    )
    parser.add_argument("--db-path", default="data/db/trading.db")
    parser.add_argument("--start-date", default=start_default, help="YYYY-MM-DD")
    parser.add_argument("--end-date", default=end_default, help="YYYY-MM-DD")
    parser.add_argument("--symbol-series", default="WIN_CONTINUO")
    parser.add_argument("--strategy-a", default="baseline")
    parser.add_argument("--strategy-b", default="swing_puro")
    parser.add_argument("--cost-profile", default="realista")
    parser.add_argument("--session-policy", default="daytrade_strict")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--output-dir", default="outputs/backtest")
    parser.add_argument("--auto-ingest-12m", action="store_true")
    parser.add_argument("--ingest-source", default="auto", choices=["auto", "mt5", "csv"])
    parser.add_argument("--export-dir", default="data/export")
    args = parser.parse_args()

    if args.symbol_series != "WIN_CONTINUO":
        raise ValueError("Somente `WIN_CONTINUO` é suportado nesta versão.")
    if args.session_policy != "daytrade_strict":
        raise ValueError("Somente `daytrade_strict` é suportado nesta versão.")

    config = BacktestConfig(
        db_path=args.db_path,
        start_date=args.start_date,
        end_date=args.end_date,
        timeframe=args.timeframe,
        symbol_series=args.symbol_series,
    )
    cost = get_cost_profile(args.cost_profile)

    ingestion = None
    if args.auto_ingest_12m:
        ingest_start = datetime.strptime(args.start_date, "%Y-%m-%d")
        ingest_end = datetime.strptime(args.end_date, "%Y-%m-%d")
        ingestion = ingest_win_history_auto(
            db_path=args.db_path,
            start_dt=ingest_start,
            end_dt=ingest_end,
            timeframe=args.timeframe,
            source=args.ingest_source,
            export_dir=args.export_dir,
        )
        print(
            "Ingestão concluída: "
            f"source={ingestion.source}, symbols={ingestion.symbols_processed}, "
            f"loaded={ingestion.rows_loaded}, inserted={ingestion.rows_inserted}, "
            f"skipped={ingestion.rows_skipped_existing}"
        )
        if ingestion.errors:
            print("Erros de ingestão:")
            for err in ingestion.errors[:10]:
                print(f"- {err}")

    result = run_ab_backtest(
        config=config,
        strategy_a_name=args.strategy_a,
        strategy_b_name=args.strategy_b,
        cost=cost,
    )
    if ingestion is not None:
        result["ingestion"] = ingestion.to_dict()

    output_dir = Path(args.output_dir)
    summary_path = output_dir / "sl_tp_ab_summary.json"
    trades_path = output_dir / "sl_tp_ab_trades.csv"
    report_path = output_dir / "sl_tp_ab_report.md"

    save_summary_json(str(summary_path), result)
    save_trades_csv(str(trades_path), result["trades"])
    save_report_markdown(
        str(report_path),
        config=config,
        cost=cost,
        quality=result["dataset_quality"],
        strategy_a=SimpleNamespace(strategy=args.strategy_a, metrics=result["strategies"][args.strategy_a]),
        strategy_b=SimpleNamespace(strategy=args.strategy_b, metrics=result["strategies"][args.strategy_b]),
        winner=result["winner"],
    )

    print("Backtest A/B concluído.")
    print(f"- Summary: {summary_path}")
    print(f"- Trades:  {trades_path}")
    print(f"- Report:  {report_path}")
    print(f"- Winner:  {result['winner']['winner']} ({result['winner']['reason']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
