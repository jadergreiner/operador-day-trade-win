"""Backtest A/B para estratégias de SL/TP no WIN contínuo.

Implementa:
- Ingestão de dados do SQLite (`market_data`)
- Montagem de série contínua com rollover diário por maior liquidez
- Simulação de execução intrabar com regra conservadora
- Day trade estrito (zeragem no fim da sessão)
- Custos realistas (slippage + custos fixos por lado)
- Métricas de retorno/risco e decisão de vencedor
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, time
from pathlib import Path
import csv
import json
import math
import sqlite3
from typing import Any, Optional

import pandas as pd


@dataclass(frozen=True)
class CostProfile:
    """Modelo de custo operacional por contrato."""

    name: str
    point_value_brl: float = 0.2
    commission_per_side_brl: float = 0.0
    fees_per_side_brl: float = 0.33
    slippage_points_per_side: float = 2.0


@dataclass(frozen=True)
class GateConfig:
    """Gates para declarar estratégia elegível."""

    max_drawdown_pct: float = 15.0
    min_trades: int = 30
    min_positive_month_ratio: float = 0.5
    max_month_profit_concentration: float = 0.55


@dataclass(frozen=True)
class BacktestConfig:
    """Configuração do backtest A/B."""

    db_path: str
    start_date: str
    end_date: str
    timeframe: str = "M5"
    symbol_series: str = "WIN_CONTINUO"
    session_start: time = time(9, 0)
    session_end: time = time(17, 30)
    tick_size: float = 5.0
    contracts: int = 1
    initial_capital_brl: float = 100_000.0
    baseline_rr_min: float = 1.5
    swing_rr_min: float = 1.5
    baseline_atr_sl_mult: float = 1.5
    baseline_atr_tp_mult: float = 3.0
    baseline_partial_rr: float = 1.0
    baseline_final_rr: float = 3.0
    baseline_contracts: int = 2
    swing_atr_fallback_mult: float = 2.5
    lookback_structure: int = 20
    gate: GateConfig = GateConfig()


@dataclass
class StrategyResult:
    """Resultado de uma estratégia."""

    strategy: str
    metrics: dict[str, Any]
    trades: list[dict[str, Any]]


def get_cost_profile(name: str) -> CostProfile:
    """Retorna profile de custos."""
    key = name.lower().strip()
    if key == "realista":
        return CostProfile(name="realista")
    if key == "sem_custo":
        return CostProfile(
            name="sem_custo",
            fees_per_side_brl=0.0,
            slippage_points_per_side=0.0,
        )
    raise ValueError(f"Cost profile não suportado: {name}")


def load_market_data(config: BacktestConfig) -> pd.DataFrame:
    """Carrega candles WIN do SQLite no período."""
    conn = sqlite3.connect(config.db_path)
    try:
        query = """
            SELECT
                symbol,
                timestamp,
                timeframe,
                open,
                high,
                low,
                close,
                volume
            FROM market_data
            WHERE timestamp >= ?
              AND timestamp <= ?
              AND timeframe = ?
              AND symbol LIKE 'WIN%'
            ORDER BY timestamp ASC
        """
        df = pd.read_sql_query(
            query,
            conn,
            params=(f"{config.start_date} 00:00:00", f"{config.end_date} 23:59:59", config.timeframe),
        )
    finally:
        conn.close()

    if df.empty:
        raise ValueError(
            "Nenhum dado WIN encontrado no período solicitado em market_data."
        )

    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed", errors="coerce")
    df["session_date"] = df["timestamp"].dt.date.astype(str)
    numeric_cols = ["open", "high", "low", "close", "volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"])
    return df


def build_win_continuous_series(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Monta série contínua WIN por liquidez diária.

    Regra de rollover:
    - Para cada sessão, seleciona o símbolo com maior contagem de candles.
    - Empate: maior volume agregado.
    """
    if df.empty:
        return df.copy(), []

    score = (
        df.groupby(["session_date", "symbol"], as_index=False)
        .agg(candles=("timestamp", "count"), volume=("volume", "sum"))
        .sort_values(["session_date", "candles", "volume"], ascending=[True, False, False])
    )
    selected = score.drop_duplicates(subset=["session_date"], keep="first")
    selected = selected.rename(columns={"symbol": "selected_symbol"})
    rollover = selected[["session_date", "selected_symbol", "candles", "volume"]]

    merged = df.merge(
        rollover[["session_date", "selected_symbol"]],
        left_on=["session_date", "symbol"],
        right_on=["session_date", "selected_symbol"],
        how="inner",
    )
    merged = merged.drop(columns=["selected_symbol"]).sort_values("timestamp").reset_index(drop=True)
    return merged, rollover.to_dict(orient="records")


def validate_dataset_quality(df: pd.DataFrame, timeframe_minutes: int = 5) -> dict[str, Any]:
    """Calcula métricas de qualidade de dados para o relatório."""
    if df.empty:
        return {
            "rows": 0,
            "sessions": 0,
            "symbols": 0,
            "duplicate_candles": 0,
            "invalid_ohlc_rows": 0,
            "critical_gaps": 0,
            "coverage_days": 0,
        }

    df = df.copy()
    duplicates = int(df.duplicated(subset=["symbol", "timestamp"]).sum())
    invalid = int(
        (
            (df["high"] < df[["open", "close"]].max(axis=1))
            | (df["low"] > df[["open", "close"]].min(axis=1))
            | (df["low"] > df["high"])
        ).sum()
    )

    df = df.sort_values("timestamp")
    df["prev_ts"] = df.groupby("session_date")["timestamp"].shift(1)
    df["gap_min"] = (df["timestamp"] - df["prev_ts"]).dt.total_seconds().div(60)
    critical_gaps = int((df["gap_min"] > (timeframe_minutes * 3)).sum())

    return {
        "rows": int(len(df)),
        "sessions": int(df["session_date"].nunique()),
        "symbols": int(df["symbol"].nunique()),
        "duplicate_candles": duplicates,
        "invalid_ohlc_rows": invalid,
        "critical_gaps": critical_gaps,
        "coverage_days": int(df["timestamp"].dt.normalize().nunique()),
        "start_ts": df["timestamp"].min().isoformat(),
        "end_ts": df["timestamp"].max().isoformat(),
    }


def _round_tick(value: float, tick_size: float) -> float:
    return round(value / tick_size) * tick_size


def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["close"]
    high = out["high"]
    low = out["low"]

    out["ema_fast"] = close.ewm(span=9, adjust=False).mean()
    out["ema_slow"] = close.ewm(span=21, adjust=False).mean()

    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / (loss.replace(0, pd.NA))
    out["rsi"] = 100 - (100 / (1 + rs))
    out["rsi"] = out["rsi"].fillna(50.0)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    out["tr"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    out["atr"] = out["tr"].rolling(14).mean().bfill()

    out["roll_high_20"] = high.rolling(20).max().shift(1)
    out["roll_low_20"] = low.rolling(20).min().shift(1)
    out["roll_high_50"] = high.rolling(50).max().shift(1)
    out["roll_low_50"] = low.rolling(50).min().shift(1)
    return out


def _strategy_signal_baseline(
    row: pd.Series,
    config: BacktestConfig,
) -> Optional[dict[str, float]]:
    close = float(row["close"])
    ema_fast = float(row["ema_fast"])
    ema_slow = float(row["ema_slow"])
    rsi = float(row["rsi"])
    atr = float(row["atr"])

    if any(math.isnan(v) for v in [ema_fast, ema_slow, rsi, atr]) or atr <= 0:
        return None

    if ema_fast > ema_slow and close > ema_fast and 50 <= rsi <= 75:
        entry = _round_tick(close, config.tick_size)
        sl = _round_tick(entry - max(atr * config.baseline_atr_sl_mult, config.tick_size * 8), config.tick_size)
        risk = entry - sl
        tp = _round_tick(entry + (risk * config.baseline_final_rr), config.tick_size)
        reward = tp - entry
        if risk <= 0 or reward / risk < config.baseline_rr_min:
            return None
        return {"direction": 1.0, "entry": entry, "sl": sl, "tp": tp}

    if ema_fast < ema_slow and close < ema_fast and 25 <= rsi <= 50:
        entry = _round_tick(close, config.tick_size)
        sl = _round_tick(entry + max(atr * config.baseline_atr_sl_mult, config.tick_size * 8), config.tick_size)
        risk = sl - entry
        tp = _round_tick(entry - (risk * config.baseline_final_rr), config.tick_size)
        reward = entry - tp
        if risk <= 0 or reward / risk < config.baseline_rr_min:
            return None
        return {"direction": -1.0, "entry": entry, "sl": sl, "tp": tp}

    return None


def _strategy_signal_swing_puro(
    row: pd.Series,
    config: BacktestConfig,
) -> Optional[dict[str, float]]:
    close = float(row["close"])
    ema_fast = float(row["ema_fast"])
    ema_slow = float(row["ema_slow"])
    atr = float(row["atr"])
    h20 = float(row["roll_high_20"]) if pd.notna(row["roll_high_20"]) else float("nan")
    l20 = float(row["roll_low_20"]) if pd.notna(row["roll_low_20"]) else float("nan")
    h50 = float(row["roll_high_50"]) if pd.notna(row["roll_high_50"]) else float("nan")
    l50 = float(row["roll_low_50"]) if pd.notna(row["roll_low_50"]) else float("nan")

    if any(math.isnan(v) for v in [ema_fast, ema_slow, atr, h20, l20]) or atr <= 0:
        return None

    if ema_fast > ema_slow and close > h20:
        entry = _round_tick(close, config.tick_size)
        sl = _round_tick(l20 - config.tick_size, config.tick_size)
        tp_raw = h50 if not math.isnan(h50) and h50 > entry else entry + atr * config.swing_atr_fallback_mult
        tp = _round_tick(tp_raw, config.tick_size)
        risk = entry - sl
        reward = tp - entry
        if risk <= 0 or reward / risk < config.swing_rr_min:
            return None
        return {"direction": 1.0, "entry": entry, "sl": sl, "tp": tp}

    if ema_fast < ema_slow and close < l20:
        entry = _round_tick(close, config.tick_size)
        sl = _round_tick(h20 + config.tick_size, config.tick_size)
        tp_raw = l50 if not math.isnan(l50) and l50 < entry else entry - atr * config.swing_atr_fallback_mult
        tp = _round_tick(tp_raw, config.tick_size)
        risk = sl - entry
        reward = entry - tp
        if risk <= 0 or reward / risk < config.swing_rr_min:
            return None
        return {"direction": -1.0, "entry": entry, "sl": sl, "tp": tp}

    return None


def evaluate_exit_intrabar(
    direction: int,
    sl: float,
    tp: float,
    bar_open: float,
    bar_high: float,
    bar_low: float,
) -> Optional[tuple[float, str]]:
    """Retorna (preço_saida, motivo) usando regra conservadora."""
    if direction == 1:
        if bar_open <= sl:
            return bar_open, "GAP_SL"
        if bar_open >= tp:
            return bar_open, "GAP_TP"
        hit_sl = bar_low <= sl
        hit_tp = bar_high >= tp
        if hit_sl and hit_tp:
            return sl, "SL_AMBIGUOUS_CONSERVATIVE"
        if hit_sl:
            return sl, "SL"
        if hit_tp:
            return tp, "TP"
        return None

    if bar_open >= sl:
        return bar_open, "GAP_SL"
    if bar_open <= tp:
        return bar_open, "GAP_TP"
    hit_sl = bar_high >= sl
    hit_tp = bar_low <= tp
    if hit_sl and hit_tp:
        return sl, "SL_AMBIGUOUS_CONSERVATIVE"
    if hit_sl:
        return sl, "SL"
    if hit_tp:
        return tp, "TP"
    return None


def _apply_slippage(price: float, direction: int, side: str, slippage_points: float) -> float:
    """Aplica slippage adverso por lado."""
    if side not in ("entry", "exit"):
        raise ValueError("side deve ser 'entry' ou 'exit'")
    if direction == 1:
        return price + slippage_points if side == "entry" else price - slippage_points
    return price - slippage_points if side == "entry" else price + slippage_points


def _calculate_trade_pnl(
    direction: int,
    entry_raw: float,
    exit_raw: float,
    cost: CostProfile,
    contracts: int,
) -> tuple[float, float, float]:
    """Retorna (pnl_points, pnl_gross_brl, pnl_net_brl)."""
    entry_eff = _apply_slippage(entry_raw, direction, "entry", cost.slippage_points_per_side)
    exit_eff = _apply_slippage(exit_raw, direction, "exit", cost.slippage_points_per_side)
    pnl_points = (exit_eff - entry_eff) if direction == 1 else (entry_eff - exit_eff)
    pnl_gross = pnl_points * cost.point_value_brl * contracts
    fixed = (cost.commission_per_side_brl + cost.fees_per_side_brl) * contracts * 2
    pnl_net = pnl_gross - fixed
    return pnl_points, pnl_gross, pnl_net


def _build_metrics(
    trades: list[dict[str, Any]],
    initial_capital: float,
    gate: GateConfig,
) -> dict[str, Any]:
    if not trades:
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "expectancy_brl": 0.0,
            "pnl_gross_brl": 0.0,
            "pnl_net_brl": 0.0,
            "max_drawdown_pct": 0.0,
            "positive_month_ratio": 0.0,
            "month_profit_concentration": 0.0,
            "eligible": False,
            "gate_status": {
                "drawdown_ok": True,
                "min_trades_ok": False,
                "consistency_ok": False,
                "concentration_ok": False,
            },
        }

    df = pd.DataFrame(trades)
    pnl_net = df["pnl_net_brl"].astype(float)
    pnl_gross = df["pnl_gross_brl"].astype(float)

    wins = int((pnl_net > 0).sum())
    losses = int((pnl_net <= 0).sum())
    total = int(len(df))
    win_rate = wins / total if total > 0 else 0.0

    gross_profit = float(pnl_net[pnl_net > 0].sum())
    gross_loss = float(-pnl_net[pnl_net < 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    expectancy = float(pnl_net.mean())

    eq = initial_capital + pnl_net.cumsum()
    running_max = eq.cummax()
    drawdown = (eq - running_max) / running_max * 100.0
    max_dd = abs(float(drawdown.min())) if len(drawdown) else 0.0

    df["exit_month"] = pd.to_datetime(df["exit_ts"]).dt.to_period("M").astype(str)
    monthly = df.groupby("exit_month", as_index=False).agg(pnl=("pnl_net_brl", "sum"))
    positive_month_ratio = float((monthly["pnl"] > 0).sum() / len(monthly)) if len(monthly) else 0.0

    total_positive = float(monthly["pnl"][monthly["pnl"] > 0].sum())
    if total_positive > 0:
        month_profit_concentration = float(monthly["pnl"].max() / total_positive)
    else:
        month_profit_concentration = 1.0

    gate_status = {
        "drawdown_ok": max_dd <= gate.max_drawdown_pct,
        "min_trades_ok": total >= gate.min_trades,
        "consistency_ok": positive_month_ratio >= gate.min_positive_month_ratio,
        "concentration_ok": month_profit_concentration <= gate.max_month_profit_concentration,
    }
    eligible = all(gate_status.values())

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4) if math.isfinite(profit_factor) else "inf",
        "expectancy_brl": round(expectancy, 2),
        "pnl_gross_brl": round(float(pnl_gross.sum()), 2),
        "pnl_net_brl": round(float(pnl_net.sum()), 2),
        "max_drawdown_pct": round(max_dd, 2),
        "positive_month_ratio": round(positive_month_ratio, 4),
        "month_profit_concentration": round(month_profit_concentration, 4),
        "eligible": eligible,
        "gate_status": gate_status,
    }


def _build_trade_record(
    strategy_name: str,
    position: dict[str, Any],
    exit_ts: str,
    session_date: str,
    exit_price: float,
    exit_reason: str,
    cost: CostProfile,
    contracts: int,
) -> dict[str, Any]:
    """Monta registro de trade com suporte a parcial no baseline."""
    pnl_points = 0.0
    pnl_gross = 0.0
    pnl_net = 0.0

    if position.get("realized_legs"):
        for leg in position["realized_legs"]:
            pnl_points += leg["pnl_points"]
            pnl_gross += leg["pnl_gross_brl"]
            pnl_net += leg["pnl_net_brl"]
    else:
        p_points, p_gross, p_net = _calculate_trade_pnl(
            direction=position["direction"],
            entry_raw=position["entry"],
            exit_raw=exit_price,
            cost=cost,
            contracts=contracts,
        )
        pnl_points += p_points
        pnl_gross += p_gross
        pnl_net += p_net

    # Se ainda resta lote aberto no baseline parcial, fecha esse remanescente agora.
    if position.get("open_contracts", 0) > 0:
        p_points, p_gross, p_net = _calculate_trade_pnl(
            direction=position["direction"],
            entry_raw=position["entry"],
            exit_raw=exit_price,
            cost=cost,
            contracts=position["open_contracts"],
        )
        pnl_points += p_points
        pnl_gross += p_gross
        pnl_net += p_net

    return {
        "strategy": strategy_name,
        "entry_ts": position["entry_ts"],
        "exit_ts": exit_ts,
        "session_date": session_date,
        "direction": "COMPRA" if position["direction"] == 1 else "VENDA",
        "entry_price": position["entry"],
        "exit_price": exit_price,
        "stop_loss": position["sl"],
        "take_profit": position["tp"],
        "exit_reason": exit_reason,
        "pnl_points": round(pnl_points, 2),
        "pnl_gross_brl": round(pnl_gross, 2),
        "pnl_net_brl": round(pnl_net, 2),
        "contracts_total": position.get("contracts_total", contracts),
    }


def _evaluate_baseline_partial_position(
    position: dict[str, Any],
    row: pd.Series,
    config: BacktestConfig,
    cost: CostProfile,
) -> Optional[tuple[float, str]]:
    """Gerencia baseline com 2 lotes: TP1=1R e TP2=3R com stop em BE após parcial."""
    direction = int(position["direction"])
    bar_open = float(row["open"])
    bar_high = float(row["high"])
    bar_low = float(row["low"])

    # Antes da parcial: lote 1 e lote 2 compartilham o mesmo SL.
    if not position.get("partial_taken", False):
        decision = evaluate_exit_intrabar(
            direction=direction,
            sl=position["sl"],
            tp=position["tp1"],
            bar_open=bar_open,
            bar_high=bar_high,
            bar_low=bar_low,
        )
        if decision is None:
            return None

        price, reason = decision
        if "SL" in reason:
            # Stop antes de parcial encerra os 2 lotes.
            position["open_contracts"] = 2
            return price, reason

        # TP1 atingido: realiza 1 lote e move stop do remanescente para BE.
        p_points, p_gross, p_net = _calculate_trade_pnl(
            direction=direction,
            entry_raw=position["entry"],
            exit_raw=price,
            cost=cost,
            contracts=1,
        )
        position.setdefault("realized_legs", []).append(
            {
                "pnl_points": p_points,
                "pnl_gross_brl": p_gross,
                "pnl_net_brl": p_net,
                "reason": "TP1",
                "exit_price": price,
            }
        )
        position["partial_taken"] = True
        position["open_contracts"] = 1
        position["sl"] = position["entry"]  # BE

        # Pós-parcial no mesmo candle (conservador): BE pior prioridade.
        if direction == 1:
            hit_be = bar_low <= position["entry"]
            hit_tp2 = bar_high >= position["tp2"]
            if hit_be and hit_tp2:
                return position["entry"], "BE_AMBIGUOUS_CONSERVATIVE"
            if hit_be:
                return position["entry"], "BE"
            if hit_tp2:
                return position["tp2"], "TP2"
            return None

        hit_be = bar_high >= position["entry"]
        hit_tp2 = bar_low <= position["tp2"]
        if hit_be and hit_tp2:
            return position["entry"], "BE_AMBIGUOUS_CONSERVATIVE"
        if hit_be:
            return position["entry"], "BE"
        if hit_tp2:
            return position["tp2"], "TP2"
        return None

    # Depois da parcial: só lote remanescente.
    return evaluate_exit_intrabar(
        direction=direction,
        sl=position["entry"],  # BE
        tp=position["tp2"],
        bar_open=bar_open,
        bar_high=bar_high,
        bar_low=bar_low,
    )


def run_strategy_backtest(
    strategy_name: str,
    df: pd.DataFrame,
    config: BacktestConfig,
    cost: CostProfile,
) -> StrategyResult:
    """Executa backtest de uma estratégia."""
    if strategy_name not in {"baseline", "swing_puro"}:
        raise ValueError(f"Estratégia não suportada: {strategy_name}")

    bars = _compute_indicators(df).reset_index(drop=True)
    trades: list[dict[str, Any]] = []

    position: Optional[dict[str, Any]] = None
    pending_signal: Optional[dict[str, float]] = None

    for i, row in bars.iterrows():
        ts = row["timestamp"]
        day = row["session_date"]
        current_time = ts.time()
        prev_day = bars.loc[i - 1, "session_date"] if i > 0 else day

        # Rollover de dia: zera posição no último candle do dia anterior.
        if i > 0 and day != prev_day:
            if position is not None:
                prev_close = float(bars.loc[i - 1, "close"])
                trades.append(
                    _build_trade_record(
                        strategy_name=strategy_name,
                        position=position,
                        exit_ts=str(bars.loc[i - 1, "timestamp"]),
                        session_date=prev_day,
                        exit_price=prev_close,
                        exit_reason="EOD",
                        cost=cost,
                        contracts=config.contracts,
                    )
                )
                position = None
            pending_signal = None

        # Entrada pendente no open do candle atual.
        if pending_signal is not None and position is None:
            entry_open = _round_tick(float(row["open"]), config.tick_size)
            direction = int(pending_signal["direction"])
            if strategy_name == "baseline":
                risk = abs(entry_open - float(pending_signal["sl"]))
                tp1 = _round_tick(
                    entry_open + (risk * config.baseline_partial_rr * direction),
                    config.tick_size,
                )
                tp2 = _round_tick(
                    entry_open + (risk * config.baseline_final_rr * direction),
                    config.tick_size,
                )
                position = {
                    "entry_ts": str(ts),
                    "entry": entry_open,
                    "direction": direction,
                    "sl": float(pending_signal["sl"]),
                    "tp": tp2,
                    "tp1": tp1,
                    "tp2": tp2,
                    "partial_taken": False,
                    "open_contracts": config.baseline_contracts,
                    "contracts_total": config.baseline_contracts,
                    "realized_legs": [],
                }
            else:
                position = {
                    "entry_ts": str(ts),
                    "entry": entry_open,
                    "direction": direction,
                    "sl": float(pending_signal["sl"]),
                    "tp": float(pending_signal["tp"]),
                    "open_contracts": config.contracts,
                    "contracts_total": config.contracts,
                    "realized_legs": [],
                }
            pending_signal = None

        # Gerenciamento da posição aberta.
        if position is not None:
            if strategy_name == "baseline":
                decision = _evaluate_baseline_partial_position(
                    position=position,
                    row=row,
                    config=config,
                    cost=cost,
                )
            else:
                decision = evaluate_exit_intrabar(
                    direction=position["direction"],
                    sl=position["sl"],
                    tp=position["tp"],
                    bar_open=float(row["open"]),
                    bar_high=float(row["high"]),
                    bar_low=float(row["low"]),
                )
            if decision is not None:
                exit_price, reason = decision
                trades.append(
                    _build_trade_record(
                        strategy_name=strategy_name,
                        position=position,
                        exit_ts=str(ts),
                        session_date=day,
                        exit_price=exit_price,
                        exit_reason=reason,
                        cost=cost,
                        contracts=config.contracts,
                    )
                )
                position = None

        # Nova geração de sinal somente sem posição/pending e dentro da sessão.
        if position is None and pending_signal is None and config.session_start <= current_time <= config.session_end:
            if strategy_name == "baseline":
                signal = _strategy_signal_baseline(row, config)
            else:
                signal = _strategy_signal_swing_puro(row, config)
            if signal is not None:
                pending_signal = signal

    # Encerramento final (último candle do período).
    if position is not None:
        last_row = bars.iloc[-1]
        exit_price = float(last_row["close"])
        trades.append(
            _build_trade_record(
                strategy_name=strategy_name,
                position=position,
                exit_ts=str(last_row["timestamp"]),
                session_date=last_row["session_date"],
                exit_price=exit_price,
                exit_reason="FORCED_END",
                cost=cost,
                contracts=config.contracts,
            )
        )

    metrics = _build_metrics(trades, config.initial_capital_brl, config.gate)
    return StrategyResult(strategy=strategy_name, metrics=metrics, trades=trades)


def decide_winner(
    strategy_a: StrategyResult,
    strategy_b: StrategyResult,
    criterion: str = "retorno_liquido",
) -> dict[str, Any]:
    """Aplica critério de vencedor com gates."""
    if criterion != "retorno_liquido":
        raise ValueError(f"Critério não suportado: {criterion}")

    a_eligible = bool(strategy_a.metrics.get("eligible"))
    b_eligible = bool(strategy_b.metrics.get("eligible"))
    a_pnl = float(strategy_a.metrics.get("pnl_net_brl", 0.0))
    b_pnl = float(strategy_b.metrics.get("pnl_net_brl", 0.0))

    if a_eligible and not b_eligible:
        winner = strategy_a.strategy
        reason = "A elegível e B reprovada nos gates"
    elif b_eligible and not a_eligible:
        winner = strategy_b.strategy
        reason = "B elegível e A reprovada nos gates"
    elif a_eligible and b_eligible:
        winner = strategy_a.strategy if a_pnl >= b_pnl else strategy_b.strategy
        reason = "Ambas elegíveis; vencedor por maior PnL líquido"
    else:
        winner = strategy_a.strategy if a_pnl >= b_pnl else strategy_b.strategy
        reason = "Nenhuma elegível; desempate por maior PnL líquido"

    return {
        "criterion": criterion,
        "winner": winner,
        "reason": reason,
        "a_pnl_net_brl": round(a_pnl, 2),
        "b_pnl_net_brl": round(b_pnl, 2),
        "a_eligible": a_eligible,
        "b_eligible": b_eligible,
    }


def save_summary_json(path: str, payload: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def save_trades_csv(path: str, rows: list[dict[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("strategy,entry_ts,exit_ts,session_date,direction,entry_price,exit_price,stop_loss,take_profit,exit_reason,pnl_points,pnl_gross_brl,pnl_net_brl\n")
        return
    fields: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in fields:
                fields.append(key)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_report_markdown(
    path: str,
    config: BacktestConfig,
    cost: CostProfile,
    quality: dict[str, Any],
    strategy_a: StrategyResult,
    strategy_b: StrategyResult,
    winner: dict[str, Any],
) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Backtest A/B - SL/TP Baseline vs Swing Puro",
        "",
        "## Configuração",
        f"- Período: `{config.start_date}` a `{config.end_date}`",
        f"- Série: `{config.symbol_series}` (`{config.timeframe}`)",
        "- Política: `daytrade_strict`",
        "- Execução intrabar: `pior caso conservador`",
        f"- Custos: `{cost.name}` (slippage={cost.slippage_points_per_side} pts/lado, fees={cost.fees_per_side_brl} BRL/lado)",
        "",
        "## Qualidade do Dataset",
        f"- Rows: `{quality.get('rows', 0)}`",
        f"- Sessões: `{quality.get('sessions', 0)}`",
        f"- Símbolos: `{quality.get('symbols', 0)}`",
        f"- Duplicatas: `{quality.get('duplicate_candles', 0)}`",
        f"- OHLC inválido: `{quality.get('invalid_ohlc_rows', 0)}`",
        f"- Gaps críticos: `{quality.get('critical_gaps', 0)}`",
        "",
        "## Resultado A/B",
        f"- Estratégia A (`{strategy_a.strategy}`): `PnL líquido {strategy_a.metrics.get('pnl_net_brl', 0)} BRL`, `DD {strategy_a.metrics.get('max_drawdown_pct', 0)}%`, `elegível={strategy_a.metrics.get('eligible')}`",
        f"- Estratégia B (`{strategy_b.strategy}`): `PnL líquido {strategy_b.metrics.get('pnl_net_brl', 0)} BRL`, `DD {strategy_b.metrics.get('max_drawdown_pct', 0)}%`, `elegível={strategy_b.metrics.get('eligible')}`",
        "",
        "## Vencedor",
        f"- Winner: `{winner['winner']}`",
        f"- Critério: `{winner['criterion']}`",
        f"- Motivo: {winner['reason']}",
        "",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def run_ab_backtest(
    config: BacktestConfig,
    strategy_a_name: str,
    strategy_b_name: str,
    cost: CostProfile,
) -> dict[str, Any]:
    """Executa pipeline completo de backtest A/B."""
    raw = load_market_data(config)
    continuous, rollover_map = build_win_continuous_series(raw)
    quality = validate_dataset_quality(continuous, timeframe_minutes=5)

    strategy_a = run_strategy_backtest(strategy_a_name, continuous, config, cost)
    strategy_b = run_strategy_backtest(strategy_b_name, continuous, config, cost)
    winner = decide_winner(strategy_a, strategy_b, criterion="retorno_liquido")

    return {
        "config": {
            **asdict(config),
            "session_start": config.session_start.isoformat(),
            "session_end": config.session_end.isoformat(),
        },
        "cost_profile": asdict(cost),
        "dataset_quality": quality,
        "rollover_map": rollover_map,
        "strategies": {
            strategy_a_name: strategy_a.metrics,
            strategy_b_name: strategy_b.metrics,
        },
        "winner": winner,
        "trades": strategy_a.trades + strategy_b.trades,
    }
