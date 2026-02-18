"""Backtesting do modelo ML de trading WINFUT.

Simula trading com o modelo treinado, incluindo custos reais B3,
slippage e métricas financeiras completas.

Uso:
    python scripts/ml/backtest_simulation.py [--model data/models/lgbm/lgbm_classification_latest.pkl]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.ml.extract_rl_dataset import build_unified_dataset
from src.application.services.ml.feature_engineering_v2 import FeatureEngineer
from src.application.services.ml.target_engineering import TargetConfig, TargetEngineer

DB_PATH = ROOT_DIR / "data" / "db" / "trading.db"
MODEL_DIR = ROOT_DIR / "data" / "models" / "lgbm"
REPORT_DIR = ROOT_DIR / "data" / "ml" / "reports"


# ── Custos reais B3 para mini-índice ────────────────────────────────
@dataclass
class TradingCosts:
    """Custos reais de operação no mini-índice WIN na B3."""
    spread_pts: float = 5.0           # Spread médio em pontos
    slippage_entry_pts: float = 10.0  # Slippage na entrada
    slippage_exit_pts: float = 10.0   # Slippage na saída
    emolumentos_brl: float = 0.32     # Emolumentos B3 por contrato (ida)
    taxa_registro_brl: float = 0.06   # Taxa de registro por contrato
    # Valor do ponto WIN = R$0.20 por contrato
    ponto_valor_brl: float = 0.20
    # Total overhead em pontos (spread + slippage ida + slippage volta)
    @property
    def total_overhead_pts(self) -> float:
        return self.spread_pts + self.slippage_entry_pts + self.slippage_exit_pts

    @property
    def total_cost_brl_per_contract(self) -> float:
        return (self.emolumentos_brl + self.taxa_registro_brl) * 2  # ida e volta

    def net_pnl_pts(self, gross_pnl_pts: float) -> float:
        """PnL líquido em pontos, descontados custos."""
        if gross_pnl_pts == 0:
            return 0.0
        # Desconta overhead em pontos + custos fixos convertidos
        cost_pts = self.total_overhead_pts
        cost_brl_as_pts = self.total_cost_brl_per_contract / self.ponto_valor_brl
        return gross_pnl_pts - cost_pts - cost_brl_as_pts


@dataclass
class BacktestConfig:
    """Configuração do backtest."""
    costs: TradingCosts = field(default_factory=TradingCosts)
    min_confidence: float = 0.55        # Confiança mínima para operar
    max_trades_per_day: int = 8         # Limite diário
    max_consecutive_losses: int = 3     # Pausa após N perdas seguidas
    cooldown_periods: int = 5           # Períodos de cooldown após streak de perda
    max_daily_loss_pts: float = 500.0   # Loss máximo diário em pontos
    position_size: int = 1              # Contratos por trade


@dataclass
class Trade:
    """Representa um trade simulado."""
    timestamp: datetime
    action: str          # BUY ou SELL
    confidence: float
    entry_price: float
    gross_pnl_pts: float
    net_pnl_pts: float
    was_correct: bool
    horizon_minutes: int
    features_top5: list[str] = field(default_factory=list)


@dataclass
class DailyResult:
    """Resultado diário do backtest."""
    date: str
    n_trades: int
    n_wins: int
    n_losses: int
    gross_pnl_pts: float
    net_pnl_pts: float
    win_rate: float
    max_drawdown_pts: float
    stopped: bool = False  # True se atingiu daily loss limit


class BacktestSimulation:
    """Motor de simulação de backtesting walk-forward."""

    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()
        self.trades: list[Trade] = []
        self.daily_results: list[DailyResult] = []

    def run(
        self,
        dataset: pd.DataFrame,
        model: Any,
        feature_cols: list[str],
        mode: str = "classification",
        target_horizon: int = 30,
    ) -> dict:
        """Executa backtest completo."""
        print("\n" + "=" * 60)
        print("BACKTEST SIMULATION")
        print("=" * 60)

        cfg = self.config
        self.trades = []
        self.daily_results = []

        # Garantir ordenação temporal
        df = dataset.sort_values("timestamp").reset_index(drop=True)

        # Agrupar por dia
        df["_date"] = df["timestamp"].dt.date.astype(str)
        dates = df["_date"].unique()

        print(f"  Período: {dates[0]} → {dates[-1]} ({len(dates)} dias)")
        print(f"  Episódios: {len(df)}")
        print(f"  Confiança mínima: {cfg.min_confidence:.0%}")
        print(f"  Max trades/dia: {cfg.max_trades_per_day}")

        reward_col = f"reward_cont_{target_horizon}m"
        correct_col = f"was_correct_{target_horizon}m"
        change_col = f"price_chg_pts_{target_horizon}m"

        for date in dates:
            day_data = df[df["_date"] == date].copy()
            day_trades = self._simulate_day(
                day_data, model, feature_cols, mode,
                reward_col, correct_col, change_col,
            )
            self.trades.extend(day_trades)

            # Calcular resultado diário
            daily = self._compute_daily_result(date, day_trades)
            self.daily_results.append(daily)

        # Métricas globais
        metrics = self._compute_global_metrics()
        self._print_report(metrics)

        return metrics

    def _simulate_day(
        self,
        day_data: pd.DataFrame,
        model: Any,
        feature_cols: list[str],
        mode: str,
        reward_col: str,
        correct_col: str,
        change_col: str,
    ) -> list[Trade]:
        """Simula um dia de trading."""
        cfg = self.config
        trades: list[Trade] = []
        consecutive_losses = 0
        cooldown_remaining = 0
        daily_pnl = 0.0

        for idx, row in day_data.iterrows():
            # Checar limites
            if len(trades) >= cfg.max_trades_per_day:
                break
            if daily_pnl <= -cfg.max_daily_loss_pts:
                break
            if cooldown_remaining > 0:
                cooldown_remaining -= 1
                continue

            # Preparar features
            X = pd.DataFrame([row[feature_cols]])
            # Converter object→numeric (exceto categóricas)
            from src.application.services.ml.feature_engineering_v2 import FeatureConfig
            _cat_feats = set(FeatureConfig().categorical_features)
            for col in X.columns:
                if col in _cat_feats:
                    X[col] = X[col].astype("category")
                elif X[col].dtype == object:
                    X[col] = pd.to_numeric(X[col], errors="coerce")
                elif X[col].dtype == bool:
                    X[col] = X[col].astype(int)

            # Predição
            try:
                if mode == "classification":
                    probs = model.predict_proba(X)[0]
                    pred_idx = int(probs.argmax())
                    confidence = float(probs[pred_idx])
                    # Usar classes reais do modelo (podem ser 1,2 ou 0,1,2)
                    model_classes = list(model.classes_)
                    pred_class = model_classes[pred_idx]
                    # Mapear: 0=HOLD, 1=BUY, 2=SELL (conforme target_engineering)
                    action_map = {0: "HOLD", 1: "BUY", 2: "SELL"}
                    action = action_map.get(pred_class, "HOLD")
                else:
                    # Regression: prediz reward
                    pred_reward = float(model.predict(X)[0])
                    if pred_reward > 0.1:
                        action = "BUY"
                        confidence = min(1.0, abs(pred_reward))
                    elif pred_reward < -0.1:
                        action = "SELL"
                        confidence = min(1.0, abs(pred_reward))
                    else:
                        action = "HOLD"
                        confidence = 0.5
            except Exception as e:
                if len(trades) == 0 and not hasattr(self, "_debug_shown"):
                    print(f"  [DEBUG] Erro na predicao: {type(e).__name__}: {e}")
                    self._debug_shown = True
                continue

            # Filtrar por confiança
            if action == "HOLD" or confidence < cfg.min_confidence:
                continue

            # Simular resultado
            gross_pnl = 0.0
            was_correct = False

            if change_col in row and pd.notna(row.get(change_col)):
                price_change = float(row[change_col])
                if action == "BUY":
                    gross_pnl = price_change
                elif action == "SELL":
                    gross_pnl = -price_change
                was_correct = gross_pnl > 0
            elif reward_col in row and pd.notna(row.get(reward_col)):
                gross_pnl = float(row[reward_col])
                was_correct = gross_pnl > 0

            net_pnl = cfg.costs.net_pnl_pts(gross_pnl)

            trade = Trade(
                timestamp=row["timestamp"] if "timestamp" in row else datetime.now(),
                action=action,
                confidence=confidence,
                entry_price=float(row.get("win_price", 0)),
                gross_pnl_pts=gross_pnl,
                net_pnl_pts=net_pnl,
                was_correct=was_correct,
                horizon_minutes=30,
            )
            trades.append(trade)
            daily_pnl += net_pnl

            # Streak management
            if not was_correct:
                consecutive_losses += 1
                if consecutive_losses >= cfg.max_consecutive_losses:
                    cooldown_remaining = cfg.cooldown_periods
                    consecutive_losses = 0
            else:
                consecutive_losses = 0

        return trades

    def _compute_daily_result(self, date: str, trades: list[Trade]) -> DailyResult:
        """Calcula resultado de um dia."""
        if not trades:
            return DailyResult(
                date=date, n_trades=0, n_wins=0, n_losses=0,
                gross_pnl_pts=0, net_pnl_pts=0, win_rate=0,
                max_drawdown_pts=0,
            )

        n_wins = sum(1 for t in trades if t.was_correct)
        n_losses = len(trades) - n_wins
        gross = sum(t.gross_pnl_pts for t in trades)
        net = sum(t.net_pnl_pts for t in trades)

        # Drawdown intraday
        cumulative = np.cumsum([t.net_pnl_pts for t in trades])
        peak = np.maximum.accumulate(cumulative)
        drawdown = peak - cumulative
        max_dd = float(drawdown.max()) if len(drawdown) > 0 else 0

        return DailyResult(
            date=date,
            n_trades=len(trades),
            n_wins=n_wins,
            n_losses=n_losses,
            gross_pnl_pts=gross,
            net_pnl_pts=net,
            win_rate=n_wins / len(trades) if trades else 0,
            max_drawdown_pts=max_dd,
        )

    def _compute_global_metrics(self) -> dict:
        """Calcula métricas globais do backtest."""
        if not self.trades:
            return {"error": "Nenhum trade executado!"}

        net_pnls = [t.net_pnl_pts for t in self.trades]
        gross_pnls = [t.gross_pnl_pts for t in self.trades]
        n_trades = len(self.trades)
        n_wins = sum(1 for t in self.trades if t.was_correct)
        n_losses = n_trades - n_wins

        # PnL
        total_net = sum(net_pnls)
        total_gross = sum(gross_pnls)
        avg_win = np.mean([p for p in net_pnls if p > 0]) if n_wins > 0 else 0
        avg_loss = np.mean([p for p in net_pnls if p <= 0]) if n_losses > 0 else 0

        # Profit Factor
        gross_profit = sum(p for p in net_pnls if p > 0)
        gross_loss = abs(sum(p for p in net_pnls if p < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Sharpe Ratio (diário)
        daily_pnls = [d.net_pnl_pts for d in self.daily_results if d.n_trades > 0]
        if len(daily_pnls) > 1:
            sharpe = np.mean(daily_pnls) / np.std(daily_pnls) * np.sqrt(252)
        else:
            sharpe = 0.0

        # Max Drawdown (cumulativo)
        cumulative = np.cumsum(net_pnls)
        peak = np.maximum.accumulate(cumulative)
        drawdowns = peak - cumulative
        max_drawdown = float(drawdowns.max()) if len(drawdowns) > 0 else 0

        # Calmar Ratio
        if max_drawdown > 0 and len(daily_pnls) > 0:
            annualized_return = np.mean(daily_pnls) * 252
            calmar = annualized_return / max_drawdown
        else:
            calmar = 0.0

        # Métricas por ação
        buy_trades = [t for t in self.trades if t.action == "BUY"]
        sell_trades = [t for t in self.trades if t.action == "SELL"]

        # Opportunity Capture Rate
        total_abs_movement = sum(abs(t.gross_pnl_pts) for t in self.trades)
        oracle_pnl = total_abs_movement  # Oráculo perfeito captura tudo
        ocr = total_net / oracle_pnl if oracle_pnl > 0 else 0

        return {
            "n_trades": n_trades,
            "n_wins": n_wins,
            "n_losses": n_losses,
            "win_rate": n_wins / n_trades,
            "total_gross_pnl_pts": total_gross,
            "total_net_pnl_pts": total_net,
            "avg_win_pts": avg_win,
            "avg_loss_pts": avg_loss,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe,
            "max_drawdown_pts": max_drawdown,
            "calmar_ratio": calmar,
            "opportunity_capture_rate": ocr,
            "trades_per_day": n_trades / max(1, len(self.daily_results)),
            "n_trading_days": len([d for d in self.daily_results if d.n_trades > 0]),
            "n_total_days": len(self.daily_results),
            "total_cost_pts": total_gross - total_net,
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "buy_win_rate": (
                sum(1 for t in buy_trades if t.was_correct) / len(buy_trades)
                if buy_trades else 0
            ),
            "sell_win_rate": (
                sum(1 for t in sell_trades if t.was_correct) / len(sell_trades)
                if sell_trades else 0
            ),
        }

    def _print_report(self, metrics: dict) -> None:
        """Imprime relatório formatado do backtest."""
        if "error" in metrics:
            print(f"\n⚠ {metrics['error']}")
            return

        print("\n" + "=" * 60)
        print("RELATÓRIO DO BACKTEST")
        print("=" * 60)

        print(f"\n📊 Trades:")
        print(f"  Total: {metrics['n_trades']} ({metrics['trades_per_day']:.1f}/dia)")
        print(f"  Wins:  {metrics['n_wins']} | Losses: {metrics['n_losses']}")
        print(f"  Win Rate: {metrics['win_rate']:.1%}")
        print(f"  BUY: {metrics['buy_trades']} ({metrics['buy_win_rate']:.1%}) | "
              f"SELL: {metrics['sell_trades']} ({metrics['sell_win_rate']:.1%})")

        print(f"\n💰 PnL (pontos WIN):")
        print(f"  Bruto:   {metrics['total_gross_pnl_pts']:+.0f} pts")
        print(f"  Custos:  -{metrics['total_cost_pts']:.0f} pts")
        print(f"  Líquido: {metrics['total_net_pnl_pts']:+.0f} pts")
        print(f"  Avg Win:  {metrics['avg_win_pts']:+.0f} pts")
        print(f"  Avg Loss: {metrics['avg_loss_pts']:+.0f} pts")

        print(f"\n📈 Métricas de Risco:")
        print(f"  Profit Factor: {metrics['profit_factor']:.2f}"
              f" {'✅' if metrics['profit_factor'] > 1.5 else '⚠️' if metrics['profit_factor'] > 1.0 else '❌'}")
        print(f"  Sharpe Ratio:  {metrics['sharpe_ratio']:.2f}"
              f" {'✅' if metrics['sharpe_ratio'] > 1.0 else '⚠️' if metrics['sharpe_ratio'] > 0 else '❌'}")
        print(f"  Max Drawdown:  {metrics['max_drawdown_pts']:.0f} pts"
              f" {'✅' if metrics['max_drawdown_pts'] < 500 else '⚠️' if metrics['max_drawdown_pts'] < 1000 else '❌'}")
        print(f"  Calmar Ratio:  {metrics['calmar_ratio']:.2f}")
        print(f"  OCR:           {metrics['opportunity_capture_rate']:.1%}")

        # Resultado diário
        print(f"\n📅 Resultado por Dia:")
        for d in self.daily_results:
            if d.n_trades > 0:
                pnl_char = "✅" if d.net_pnl_pts > 0 else "❌"
                print(f"  {d.date}: {d.n_trades} trades, WR={d.win_rate:.0%}, "
                      f"PnL={d.net_pnl_pts:+.0f} pts {pnl_char}")

        # Veredicto
        print(f"\n{'='*60}")
        pf = metrics["profit_factor"]
        sr = metrics["sharpe_ratio"]
        wr = metrics["win_rate"]
        if pf > 1.5 and sr > 1.0 and wr > 0.5:
            print("✅ VEREDICTO: Modelo APROVADO para shadow mode")
        elif pf > 1.0 and sr > 0 and wr > 0.45:
            print("⚠️ VEREDICTO: Modelo MARGINAL — precisa de mais dados ou tuning")
        else:
            print("❌ VEREDICTO: Modelo REPROVADO — não pronto para produção")
        print("=" * 60)

    def export_trades(self, output_path: Path) -> None:
        """Exporta lista de trades para CSV."""
        if not self.trades:
            return

        rows = []
        for t in self.trades:
            rows.append({
                "timestamp": t.timestamp,
                "action": t.action,
                "confidence": t.confidence,
                "entry_price": t.entry_price,
                "gross_pnl_pts": t.gross_pnl_pts,
                "net_pnl_pts": t.net_pnl_pts,
                "was_correct": t.was_correct,
                "horizon_minutes": t.horizon_minutes,
            })

        df = pd.DataFrame(rows)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"  Trades exportados: {output_path}")

    def export_report(self, metrics: dict, output_path: Path) -> None:
        """Exporta métricas para JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def _convert(obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, default=_convert)
        print(f"  Report exportado: {output_path}")


# ── Colunas de features (mesmo critério do train) ───────────────────
EXCLUDE_FEATURES = {
    "episode_id", "timestamp", "session_date", "source", "_date",
    "action", "reasoning", "created_at",
    "target_reward_composite", "target_class", "target_class_encoded",
    "target_direction", "target_profitable",
    "cf_reward_buy", "cf_reward_sell", "cf_reward_hold",
}


def _get_feature_columns(df: pd.DataFrame) -> list[str]:
    return [
        c for c in df.columns
        if c not in EXCLUDE_FEATURES
        and not c.startswith("reward_")
        and not c.startswith("was_correct_")
        and not c.startswith("price_chg_pts_")
        and not c.startswith("mfe_")
        and not c.startswith("mae_")
        and not c.startswith("vol_")
        and not c.startswith("target_")
        and not c.startswith("cf_reward_")
        and not c.startswith("_")
    ]


def main():
    parser = argparse.ArgumentParser(description="Backtest do modelo ML de trading")
    parser.add_argument("--model", type=str,
                        default=str(MODEL_DIR / "lgbm_classification_latest.pkl"))
    parser.add_argument("--mode", choices=["classification", "regression"],
                        default="classification")
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--horizon", type=int, default=30)
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--max-trades-day", type=int, default=8)
    parser.add_argument("--export-trades", action="store_true")
    parser.add_argument("--db", type=str, default=str(DB_PATH))
    args = parser.parse_args()

    # Carregar modelo
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"⚠ Modelo não encontrado: {model_path}")
        print("  Execute primeiro: python scripts/ml/train_lgbm_trading.py")
        return

    print(f"Carregando modelo: {model_path}")
    model = joblib.load(model_path)

    # Extrair dados
    print("\nExtraindo dataset...")
    raw_dataset = build_unified_dataset(
        db_path=Path(args.db), days=args.days, horizon=args.horizon
    )

    if raw_dataset.empty:
        print("⚠ Dataset vazio!")
        return

    # Feature engineering
    fe = FeatureEngineer()
    dataset = fe.transform(raw_dataset)

    # Target engineering (para ter o ground truth)
    te = TargetEngineer(TargetConfig(primary_horizon=args.horizon))
    dataset = te.build_targets(dataset)

    # Features
    feature_cols = _get_feature_columns(dataset)

    # Filtrar por features que o modelo conhece
    model_features = getattr(model, "feature_names_", None) or getattr(
        model, "feature_name_", None
    )
    if model_features:
        model_features_set = set(model_features)
        feature_cols = [c for c in feature_cols if c in model_features_set]
        # Adicionar colunas que faltam com NaN
        for mf in model_features:
            if mf not in dataset.columns:
                dataset[mf] = np.nan
        feature_cols = list(model_features)

    print(f"Features para backtest: {len(feature_cols)}")

    # Configurar backtest
    config = BacktestConfig(
        min_confidence=args.min_confidence,
        max_trades_per_day=args.max_trades_day,
    )

    # Executar
    bt = BacktestSimulation(config)
    metrics = bt.run(
        dataset, model, feature_cols,
        mode=args.mode, target_horizon=args.horizon,
    )

    # Exportar
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bt.export_report(metrics, REPORT_DIR / f"backtest_{timestamp}.json")

    if args.export_trades:
        bt.export_trades(REPORT_DIR / f"backtest_trades_{timestamp}.csv")


if __name__ == "__main__":
    main()
