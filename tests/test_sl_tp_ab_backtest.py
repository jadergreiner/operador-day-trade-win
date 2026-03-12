from datetime import datetime

import pandas as pd

from src.application.services.sl_tp_ab_backtest import (
    BacktestConfig,
    CostProfile,
    build_win_continuous_series,
    evaluate_exit_intrabar,
    run_strategy_backtest,
)


def test_build_win_continuous_series_selects_daily_liquidity_symbol():
    df = pd.DataFrame(
        [
            {"symbol": "WINA", "timestamp": "2026-01-02 09:00:00", "timeframe": "M5", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10, "session_date": "2026-01-02"},
            {"symbol": "WINA", "timestamp": "2026-01-02 09:05:00", "timeframe": "M5", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 10, "session_date": "2026-01-02"},
            {"symbol": "WINB", "timestamp": "2026-01-02 09:00:00", "timeframe": "M5", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 5, "session_date": "2026-01-02"},
            {"symbol": "WINB", "timestamp": "2026-01-03 09:00:00", "timeframe": "M5", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 20, "session_date": "2026-01-03"},
            {"symbol": "WINB", "timestamp": "2026-01-03 09:05:00", "timeframe": "M5", "open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 20, "session_date": "2026-01-03"},
        ]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    cont, rollover = build_win_continuous_series(df)
    assert set(cont[cont["session_date"] == "2026-01-02"]["symbol"]) == {"WINA"}
    assert set(cont[cont["session_date"] == "2026-01-03"]["symbol"]) == {"WINB"}
    assert len(rollover) == 2


def test_evaluate_exit_intrabar_conservative_ambiguity():
    decision = evaluate_exit_intrabar(
        direction=1,
        sl=100.0,
        tp=120.0,
        bar_open=110.0,
        bar_high=125.0,
        bar_low=95.0,
    )
    assert decision == (100.0, "SL_AMBIGUOUS_CONSERVATIVE")


def test_run_strategy_backtest_daytrade_closes_position_at_eod():
    rows = []
    base1 = datetime(2026, 1, 2, 9, 0)
    base2 = datetime(2026, 1, 3, 9, 0)

    # Dia 1: tendência de alta para forçar um sinal baseline.
    price = 100000.0
    for i in range(60):
        ts = base1 + pd.Timedelta(minutes=5 * i)
        close = price + i * 5
        rows.append(
            {
                "symbol": "WINA",
                "timestamp": ts,
                "timeframe": "M5",
                "open": close - 2,
                "high": close + 10,
                "low": close - 10,
                "close": close,
                "volume": 1000 + i,
                "session_date": "2026-01-02",
            }
        )

    # Dia 2: necessário para disparar zeragem de EOD do dia anterior.
    for i in range(5):
        ts = base2 + pd.Timedelta(minutes=5 * i)
        close = 100500 + i * 5
        rows.append(
            {
                "symbol": "WINA",
                "timestamp": ts,
                "timeframe": "M5",
                "open": close - 2,
                "high": close + 10,
                "low": close - 10,
                "close": close,
                "volume": 1000 + i,
                "session_date": "2026-01-03",
            }
        )

    df = pd.DataFrame(rows)
    config = BacktestConfig(
        db_path=":memory:",
        start_date="2026-01-02",
        end_date="2026-01-03",
    )
    cost = CostProfile(name="sem_custo", fees_per_side_brl=0.0, slippage_points_per_side=0.0)
    result = run_strategy_backtest("baseline", df, config, cost)
    assert result.trades, "Era esperado ao menos um trade"
    assert any(t["exit_reason"] in {"EOD", "FORCED_END"} for t in result.trades)

