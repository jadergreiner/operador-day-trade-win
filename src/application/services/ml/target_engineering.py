"""Target Engineering para o modelo ML de trading.

Define como a variável alvo (target) é construída a partir dos rewards RL.
O target composto penaliza HOLD em tendência e recompensa risk management.

Uso:
    from src.application.services.ml.target_engineering import TargetEngineer
    te = TargetEngineer()
    df = te.build_targets(df)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class TargetConfig:
    """Configuração do target engineering."""

    # Horizonte principal para target (minutos)
    primary_horizon: int = 30

    # Pesos do reward composto
    weight_result: float = 0.40      # Resultado real em pontos
    weight_mfe: float = 0.20         # Máximo favorável (capturou?)
    weight_mae: float = 0.15         # Máximo adverso (risco controlado?)
    weight_direction: float = 0.15   # Acertou a direção?
    weight_opp_cost: float = 0.10    # Custo de oportunidade (penaliza HOLD)

    # Normalização
    atr_reference: float = 200.0     # ATR médio WIN para normalização
    mfe_max: float = 300.0           # MFE de referência para normalização
    mae_max: float = 200.0           # MAE de referência para normalização
    opp_cost_threshold: float = 50.0  # Pontos mínimos de movimento para penalizar HOLD

    # Classificação
    buy_threshold: float = 0.15      # reward > threshold → BUY
    sell_threshold: float = -0.15    # reward < threshold → SELL
    # Entre thresholds → HOLD

    # Limites
    reward_clip: float = 3.0         # Clip do reward composto


class TargetEngineer:
    """Constrói targets para treinamento do modelo ML."""

    def __init__(self, config: TargetConfig | None = None):
        self.config = config or TargetConfig()

    def build_targets(self, df: pd.DataFrame) -> pd.DataFrame:
        """Constrói todas as variáveis target.

        Adiciona ao DataFrame:
            - target_reward_composite: reward composto (float, para regression)
            - target_class: BUY/SELL/HOLD (para classification)
            - target_class_encoded: 0=HOLD, 1=BUY, 2=SELL (int)
            - target_direction: 1=UP, -1=DOWN, 0=FLAT
            - target_profitable: 1=lucro, 0=prejuízo (binário)
        """
        result = df.copy()
        h = self.config.primary_horizon

        # Colunas de reward esperadas
        col_reward = f"reward_cont_{h}m"
        col_correct = f"was_correct_{h}m"
        col_change = f"price_chg_pts_{h}m"
        col_mfe = f"mfe_{h}m"
        col_mae = f"mae_{h}m"

        # 1. Reward composto
        result["target_reward_composite"] = self._compute_composite_reward(
            result, col_reward, col_correct, col_change, col_mfe, col_mae
        )

        # 2. Reward por ação hipotética (o que aconteceria se fizesse BUY, SELL, HOLD)
        result = self._compute_counterfactual_rewards(result, col_change, col_mfe, col_mae)

        # 3. Classificação baseada no melhor reward contrafactual
        result["target_class"] = self._classify_best_action(result)
        class_map = {"HOLD": 0, "BUY": 1, "SELL": 2}
        result["target_class_encoded"] = result["target_class"].map(class_map).fillna(0).astype(int)

        # 4. Direção simples
        if col_change in result.columns:
            change = result[col_change].fillna(0).astype(float)
            result["target_direction"] = np.select(
                [change > 30, change < -30],
                [1, -1],
                default=0,
            )

        # 5. Lucratividade binária (para o reward do horizonte)
        if col_reward in result.columns:
            result["target_profitable"] = (
                result[col_reward].fillna(0).astype(float) > 0
            ).astype(int)

        # 6. Distribuição dos targets (para logging)
        self._log_target_distribution(result)

        return result

    def _compute_composite_reward(
        self,
        df: pd.DataFrame,
        col_reward: str,
        col_correct: str,
        col_change: str,
        col_mfe: str,
        col_mae: str,
    ) -> pd.Series:
        """Calcula reward composto com 5 componentes."""
        cfg = self.config

        # Componente 1: Resultado real normalizado
        if col_reward in df.columns:
            result_comp = df[col_reward].fillna(0).astype(float) / cfg.atr_reference
        else:
            result_comp = pd.Series(0.0, index=df.index)

        # Componente 2: MFE normalizado (quão favorável o trade chegou a ser)
        if col_mfe in df.columns:
            mfe = df[col_mfe].fillna(0).astype(float)
            mfe_comp = (mfe / cfg.mfe_max).clip(0, 1)
        else:
            mfe_comp = pd.Series(0.0, index=df.index)

        # Componente 3: MAE invertido (quanto menor o drawdown, melhor)
        if col_mae in df.columns:
            mae = df[col_mae].fillna(0).astype(float)
            mae_comp = 1 - (mae / cfg.mae_max).clip(0, 1)
        else:
            mae_comp = pd.Series(0.5, index=df.index)

        # Componente 4: Bônus de direção
        if col_correct in df.columns:
            direction_comp = df[col_correct].fillna(0).astype(float)
            direction_comp = np.where(direction_comp == 1, 1.0, -0.5)
        else:
            direction_comp = pd.Series(0.0, index=df.index)

        # Componente 5: Custo de oportunidade (penaliza HOLD em tendência)
        if col_change in df.columns and "action" in df.columns:
            abs_change = df[col_change].fillna(0).astype(float).abs()
            is_hold = (df["action"] == "HOLD").astype(float)
            # Só penaliza HOLD quando movimento > threshold
            opp_cost = np.where(
                (is_hold > 0) & (abs_change > cfg.opp_cost_threshold),
                -(abs_change - cfg.opp_cost_threshold) / cfg.atr_reference,
                0.0,
            )
            opp_cost = np.clip(opp_cost, -cfg.reward_clip, 0)
        else:
            opp_cost = pd.Series(0.0, index=df.index)

        # Composição ponderada
        composite = (
            cfg.weight_result * result_comp
            + cfg.weight_mfe * mfe_comp
            + cfg.weight_mae * mae_comp
            + cfg.weight_direction * direction_comp
            + cfg.weight_opp_cost * opp_cost
        )

        return composite.clip(-cfg.reward_clip, cfg.reward_clip)

    def _compute_counterfactual_rewards(
        self,
        df: pd.DataFrame,
        col_change: str,
        col_mfe: str,
        col_mae: str,
    ) -> pd.DataFrame:
        """Calcula reward hipotético para cada ação possível.

        Usa price_change_points para estimar o que teria acontecido:
        - Se BUY: reward = +change (lucra na alta)
        - Se SELL: reward = -change (lucra na baixa)
        - Se HOLD: reward = -|change|/atr se |change| > threshold, 0 caso contrário
        """
        cfg = self.config

        if col_change not in df.columns:
            df["cf_reward_buy"] = 0.0
            df["cf_reward_sell"] = 0.0
            df["cf_reward_hold"] = 0.0
            return df

        change = df[col_change].fillna(0).astype(float)
        abs_change = change.abs()

        # BUY: lucra quando preço sobe
        df["cf_reward_buy"] = (change / cfg.atr_reference).clip(
            -cfg.reward_clip, cfg.reward_clip
        )

        # SELL: lucra quando preço cai
        df["cf_reward_sell"] = (-change / cfg.atr_reference).clip(
            -cfg.reward_clip, cfg.reward_clip
        )

        # HOLD: neutro se mercado ficou parado, penaliza se houve tendência
        hold_penalty = np.where(
            abs_change > cfg.opp_cost_threshold,
            -(abs_change - cfg.opp_cost_threshold) / cfg.atr_reference,
            abs_change / cfg.atr_reference * 0.1,  # pequeno bônus por ficar flat
        )
        df["cf_reward_hold"] = np.clip(
            hold_penalty, -cfg.reward_clip, cfg.reward_clip / 2
        )

        return df

    def _classify_best_action(self, df: pd.DataFrame) -> pd.Series:
        """Classifica a melhor ação baseada nos rewards contrafactuais."""
        cf_cols = ["cf_reward_buy", "cf_reward_sell", "cf_reward_hold"]
        existing = [c for c in cf_cols if c in df.columns]

        if not existing:
            return pd.Series("HOLD", index=df.index)

        cf_matrix = df[existing].fillna(0)
        best_idx = cf_matrix.values.argmax(axis=1)

        action_map = {0: "BUY", 1: "SELL", 2: "HOLD"}
        return pd.Series(
            [action_map.get(i, "HOLD") for i in best_idx],
            index=df.index,
        )

    def _log_target_distribution(self, df: pd.DataFrame) -> None:
        """Imprime distribuição dos targets para diagnóstico."""
        print("\n" + "=" * 50)
        print("Target Engineering Report")
        print("=" * 50)

        if "target_reward_composite" in df.columns:
            rc = df["target_reward_composite"]
            print(f"\ntarget_reward_composite:")
            print(f"  mean={rc.mean():.4f}, std={rc.std():.4f}")
            print(f"  min={rc.min():.4f}, max={rc.max():.4f}")
            print(f"  median={rc.median():.4f}")

        if "target_class" in df.columns:
            counts = df["target_class"].value_counts()
            total = len(df)
            print(f"\ntarget_class:")
            for cls, cnt in counts.items():
                print(f"  {cls}: {cnt} ({cnt/total*100:.1f}%)")

        if "target_direction" in df.columns:
            counts = df["target_direction"].value_counts()
            print(f"\ntarget_direction:")
            for d, cnt in counts.items():
                label = {1: "UP", -1: "DOWN", 0: "FLAT"}.get(d, str(d))
                print(f"  {label}: {cnt} ({cnt/len(df)*100:.1f}%)")

        # Rewards contrafactuais
        for col in ["cf_reward_buy", "cf_reward_sell", "cf_reward_hold"]:
            if col in df.columns:
                vals = df[col]
                print(f"\n{col}: mean={vals.mean():.4f}, std={vals.std():.4f}")

        print("=" * 50)

    def get_target_columns(self) -> list[str]:
        """Retorna nomes das colunas target geradas."""
        return [
            "target_reward_composite",
            "target_class",
            "target_class_encoded",
            "target_direction",
            "target_profitable",
            "cf_reward_buy",
            "cf_reward_sell",
            "cf_reward_hold",
        ]
