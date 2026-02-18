"""Feature Engineering V2 para o modelo ML de trading.

Transforma o dataset bruto extraído das tabelas RL em features
avançadas incluindo lags, deltas, rolling stats, interações e
features temporais.

Uso:
    from src.application.services.ml.feature_engineering_v2 import FeatureEngineer
    fe = FeatureEngineer()
    df_features = fe.transform(df_raw)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class FeatureConfig:
    """Configuração do feature engineering."""

    # Lags (em períodos = ciclos de 120s)
    lag_periods: list[int] = field(default_factory=lambda: [1, 3, 5, 10])

    # Features para calcular lags
    lag_features: list[str] = field(
        default_factory=lambda: [
            "macro_score_final",
            "micro_score",
            "win_price",
            "ind_RSI_14_val",
            "ind_ADX_14_val",
            "volume_score",
            "smc_bos_score",
        ]
    )

    # Features para calcular deltas (velocidade de mudança)
    delta_periods: list[int] = field(default_factory=lambda: [1, 3, 5])
    delta_features: list[str] = field(
        default_factory=lambda: [
            "macro_score_final",
            "micro_score",
            "win_price",
            "ind_RSI_14_val",
            "ind_ADX_14_val",
        ]
    )

    # Rolling stats
    rolling_windows: list[int] = field(default_factory=lambda: [5, 10, 20])
    rolling_features: list[str] = field(
        default_factory=lambda: [
            "macro_score_final",
            "micro_score",
            "ind_RSI_14_val",
        ]
    )

    # Categorias para encoding
    categorical_features: list[str] = field(
        default_factory=lambda: [
            "micro_trend",
            "vwap_position",
            "smc_direction",
            "smc_equilibrium",
            "sentiment_intraday",
            "sentiment_momentum",
            "sentiment_volatility",
            "market_regime",
            "market_condition",
            "session_phase",
            "macro_bias",
            "fundamental_bias",
            "sentiment_bias",
            "technical_bias",
            "action",
            "urgency",
            "risk_level",
            "recommended_approach",
        ]
    )

    # Mínimo de não-nulos para manter uma feature
    min_non_null_ratio: float = 0.3


class FeatureEngineer:
    """Motor de feature engineering para dataset RL de trading."""

    def __init__(self, config: Optional[FeatureConfig] = None):
        self.config = config or FeatureConfig()
        self._original_cols: list[str] = []
        self._generated_cols: list[str] = []

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica todas as transformações de features.

        Args:
            df: DataFrame bruto do extract_rl_dataset.py

        Returns:
            DataFrame com features originais + geradas
        """
        self._original_cols = list(df.columns)
        result = df.copy()

        # Garantir ordenação temporal para lags/rolling
        if "timestamp" in result.columns:
            result = result.sort_values("timestamp").reset_index(drop=True)

        # 1. Lag features
        result = self._add_lag_features(result)

        # 2. Delta features (velocidade de mudança)
        result = self._add_delta_features(result)

        # 3. Rolling statistics
        result = self._add_rolling_features(result)

        # 4. Interações entre features
        result = self._add_interaction_features(result)

        # 5. Features de streak/sequência
        result = self._add_streak_features(result)

        # 6. Features de posição relativa
        result = self._add_position_features(result)

        # 7. Encode categóricas
        result = self._encode_categoricals(result)

        # 8. Limpar features com muitos nulls
        result = self._drop_sparse_features(result)

        self._generated_cols = [
            c for c in result.columns if c not in self._original_cols
        ]

        return result

    def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria features de lag (valor N períodos atrás)."""
        for feat in self.config.lag_features:
            if feat not in df.columns:
                continue
            for lag in self.config.lag_periods:
                col_name = f"{feat}_lag{lag}"
                df[col_name] = df[feat].shift(lag)
        return df

    def _add_delta_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria features de delta (diferença entre atual e N períodos atrás)."""
        for feat in self.config.delta_features:
            if feat not in df.columns:
                continue
            for period in self.config.delta_periods:
                col_name = f"{feat}_delta{period}"
                df[col_name] = df[feat] - df[feat].shift(period)

                # Delta percentual para preço
                if "price" in feat.lower():
                    col_pct = f"{feat}_delta{period}_pct"
                    prev = df[feat].shift(period)
                    df[col_pct] = np.where(prev != 0, (df[feat] - prev) / prev * 100, 0)
        return df

    def _add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria estatísticas deslizantes (média, std, min, max)."""
        for feat in self.config.rolling_features:
            if feat not in df.columns:
                continue
            for window in self.config.rolling_windows:
                prefix = f"{feat}_roll{window}"

                # Média móvel
                df[f"{prefix}_mean"] = df[feat].rolling(window, min_periods=1).mean()

                # Desvio padrão
                df[f"{prefix}_std"] = df[feat].rolling(window, min_periods=2).std()

                # EMA
                df[f"{prefix}_ema"] = df[feat].ewm(span=window, min_periods=1).mean()

                # Posição relativa na janela (0=mínimo, 1=máximo)
                roll_min = df[feat].rolling(window, min_periods=1).min()
                roll_max = df[feat].rolling(window, min_periods=1).max()
                roll_range = roll_max - roll_min
                df[f"{prefix}_pos"] = np.where(
                    roll_range > 0,
                    (df[feat] - roll_min) / roll_range,
                    0.5,
                )
        return df

    def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria features de interação entre variáveis-chave."""
        interactions = [
            # (feat1, feat2, nome, operação)
            ("macro_score_final", "ind_ADX_14_val", "macro_x_adx", "multiply"),
            ("macro_score_final", "micro_score", "macro_x_micro", "multiply"),
            ("macro_score_final", "volume_score", "macro_x_vol", "multiply"),
            ("ind_RSI_14_val", "smc_bos_score", "rsi_x_smc", "multiply"),
            ("probability_up", "probability_down", "prob_spread", "subtract"),
            ("macro_score_bullish", "macro_score_bearish", "bull_bear_ratio", "divide"),
        ]

        for feat1, feat2, name, op in interactions:
            if feat1 not in df.columns or feat2 not in df.columns:
                continue

            v1 = df[feat1].astype(float)
            v2 = df[feat2].astype(float)

            if op == "multiply":
                df[f"inter_{name}"] = v1 * v2 / 100  # normalizar
            elif op == "subtract":
                df[f"inter_{name}"] = v1 - v2
            elif op == "divide":
                df[f"inter_{name}"] = np.where(
                    v2.abs() > 0.01, v1 / v2, 0
                )

        # Score total de correlações positivas vs negativas
        corr_score_cols = [c for c in df.columns if c.startswith("corr_grp_") and c.endswith("_score")]
        if corr_score_cols:
            df["corr_grp_mean_score"] = df[corr_score_cols].mean(axis=1)
            df["corr_grp_std_score"] = df[corr_score_cols].std(axis=1)
            df["corr_grp_n_positive"] = (df[corr_score_cols] > 0).sum(axis=1)
            df["corr_grp_n_negative"] = (df[corr_score_cols] < 0).sum(axis=1)
            df["corr_grp_consensus"] = df["corr_grp_n_positive"] - df["corr_grp_n_negative"]

        # Concordância entre biases (quantos apontam mesma direção)
        bias_cols = ["macro_bias", "fundamental_bias", "sentiment_bias", "technical_bias"]
        existing_bias = [c for c in bias_cols if c in df.columns]
        if len(existing_bias) >= 2:
            # Codificar como numérico temporariamente
            bias_map = {"BULLISH": 1, "BEARISH": -1, "NEUTRAL": 0}
            bias_numeric = df[existing_bias].replace(bias_map).apply(
                pd.to_numeric, errors="coerce"
            )
            df["bias_sum"] = bias_numeric.sum(axis=1)
            df["bias_agreement"] = bias_numeric.apply(
                lambda row: row.dropna().nunique() == 1, axis=1
            ).astype(int)

        return df

    def _add_streak_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cria features de sequência/streak."""
        # Streak de macro positivo
        if "macro_score_final" in df.columns:
            macro_pos = (df["macro_score_final"] > 0).astype(int)
            groups = macro_pos.ne(macro_pos.shift()).cumsum()
            df["macro_positive_streak"] = macro_pos.groupby(groups).cumsum()

            macro_neg = (df["macro_score_final"] < 0).astype(int)
            groups_neg = macro_neg.ne(macro_neg.shift()).cumsum()
            df["macro_negative_streak"] = macro_neg.groupby(groups_neg).cumsum()

        # Streak de micro_score na mesma direção
        if "micro_score" in df.columns:
            micro_pos = (df["micro_score"] > 0).astype(int)
            groups = micro_pos.ne(micro_pos.shift()).cumsum()
            df["micro_positive_streak"] = micro_pos.groupby(groups).cumsum()

        # Streak de decisões certas (últimos rewards)
        if "was_correct_30m" in df.columns:
            correct = df["was_correct_30m"].fillna(0).astype(int)
            groups = correct.ne(correct.shift()).cumsum()
            df["correct_streak"] = correct.groupby(groups).cumsum()

        return df

    def _add_position_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Features de posição relativa do preço."""
        price = "win_price"
        if price not in df.columns:
            return df

        p = df[price].astype(float)

        # Distância para pivots (percentual)
        for pivot_col in ["pivot_r1", "pivot_r2", "pivot_s1", "pivot_s2"]:
            if pivot_col in df.columns:
                pv = df[pivot_col].astype(float)
                df[f"dist_{pivot_col}_pct"] = np.where(
                    pv > 0, (p - pv) / pv * 100, 0
                )

        # Distância para bandas VWAP
        for vwap_col in ["vwap_upper_1sigma", "vwap_lower_1sigma",
                          "vwap_upper_2sigma", "vwap_lower_2sigma"]:
            if vwap_col in df.columns:
                vw = df[vwap_col].astype(float)
                short_name = vwap_col.replace("vwap_", "").replace("sigma", "s")
                df[f"dist_{short_name}_pct"] = np.where(
                    vw > 0, (p - vw) / vw * 100, 0
                )

        # Largura das bandas VWAP (volatilidade)
        if "vwap_upper_1sigma" in df.columns and "vwap_lower_1sigma" in df.columns:
            u1 = df["vwap_upper_1sigma"].astype(float)
            l1 = df["vwap_lower_1sigma"].astype(float)
            vwap = df["vwap_value"].astype(float) if "vwap_value" in df.columns else (u1 + l1) / 2
            df["vwap_band_width_pct"] = np.where(
                vwap > 0, (u1 - l1) / vwap * 100, 0
            )

        return df

    def _encode_categoricals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Codifica features categóricas para LightGBM.

        LightGBM suporta categóricas nativamente — apenas converter para 'category'.
        """
        for col in self.config.categorical_features:
            if col in df.columns:
                df[col] = df[col].astype("category")
        return df

    def _drop_sparse_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove features com muitos valores nulos."""
        min_count = int(len(df) * self.config.min_non_null_ratio)
        sparse_cols = [
            col for col in df.columns
            if df[col].notna().sum() < min_count
            and col not in ["episode_id", "timestamp", "session_date"]
        ]
        if sparse_cols:
            df = df.drop(columns=sparse_cols)
        return df

    def get_feature_names(self, include_target: bool = False) -> list[str]:
        """Retorna nomes das features geradas (sem IDs e targets)."""
        exclude_prefixes = ["episode_id", "timestamp", "session_date", "action"]
        if not include_target:
            exclude_prefixes.extend([
                "reward_", "was_correct_", "price_chg_pts_",
                "mfe_", "mae_", "vol_",
            ])

        return [
            c for c in self._original_cols + self._generated_cols
            if not any(c.startswith(p) for p in exclude_prefixes)
        ]

    def report(self, df: pd.DataFrame) -> str:
        """Gera relatório resumido das features."""
        lines = [
            f"Feature Engineering Report",
            f"{'='*50}",
            f"Total features: {len(df.columns)}",
            f"  - Originais: {len(self._original_cols)}",
            f"  - Geradas:   {len(self._generated_cols)}",
            f"Amostras: {len(df)}",
            f"",
            f"Categóricas:",
        ]
        for col in df.select_dtypes(include=["category"]).columns:
            cats = df[col].cat.categories.tolist()
            lines.append(f"  {col}: {len(cats)} categorias → {cats[:5]}...")

        lines.append(f"\nNulls por feature (top-10):")
        null_counts = df.isnull().sum().sort_values(ascending=False).head(10)
        for col, cnt in null_counts.items():
            if cnt > 0:
                lines.append(f"  {col}: {cnt} ({cnt/len(df)*100:.1f}%)")

        return "\n".join(lines)
