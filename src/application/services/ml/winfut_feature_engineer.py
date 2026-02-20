"""Feature Engineering para modelo WINFUT XGBoost.

Responsável por:
  1. Seleção e validação de features (Tier-1, Tier-2)
  2. Normalização e encoding
  3. Tratamento de missing values
  4. Feature importance analysis via SHAP

Filosofia:
  - Menos é mais: Tier-1 (15 features) é suficiente para MVP
  - Explicabilidade: Cada feature deve ter "story" clara
  - Validação: Testar colinearidade, variance inflation factor
"""

from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder


class WinFutFeatureEngineer:
    """Engenheira features para WINFUT."""

    # TIER-1: Features críticas (15)
    TIER1_NUMERIC = [
        "macro_score_final",         # Score macro agregado (-100 a +100)
        "micro_score",                # Score micro (-20 a +20)
        "alignment_score",            # Alinhamento das dimensões
        "overall_confidence",         # Confiança geral
        "macro_confidence",           # Confiança do macro score
        "smc_equilibrium_score",      # SMC equilibrium
        "vwap_position",              # Posição relativa ao VWAP (distância)
        "volume_variance_pct",        # Volatilidade de volume
        "probability_up",             # Probabilidade de subida
        "probability_down",           # Probabilidade de queda
    ]

    TIER1_CATEGORICAL = [
        "market_regime",              # TRENDING, RANGING, VOLATILE, UNCERTAIN
        "session_phase",              # OPENING, MIDDAY, AFTERNOON, CLOSING
        "smc_direction",              # BUY, SELL, NEUTRAL
        "vwap_position",              # ABOVE_2S, ABOVE_1S, AT_VWAP, BELOW_1S, BELOW_2S
        "volatility_bracket",         # LOW, NORMAL, HIGH
    ]

    # TIER-2: Features secundárias (35)
    TIER2_NUMERIC = [
        "macro_score_bullish",
        "macro_score_bearish",
        "macro_items_available",
        "volume_today",
        "volume_avg",
        "volume_score",
        "win_price_change_pct",
        "minutes_since_open",
        "hour_decimal",
        "weekday",
        "us_market_open",
        # Correlações agregadas (preenchidas pelo dataset builder)
        # corr_acoes_br, corr_cambio, corr_commodities, etc
    ]

    def __init__(self):
        self.numeric_features = []
        self.categorical_features = []
        self.scaler = None
        self.encoders: Dict[str, LabelEncoder] = {}

    def select_features(self, df: pd.DataFrame, tier: int = 1) -> List[str]:
        """
        Seleciona features baseado no tier.

        Args:
            df: DataFrame com todas as features
            tier: 1 (críticas) ou 2 (críticas + secundárias)

        Returns:
            Lista de feature names disponíveis
        """
        available = df.columns.tolist()

        if tier == 1:
            selected = [f for f in self.TIER1_NUMERIC + self.TIER1_CATEGORICAL if f in available]
        elif tier == 2:
            selected = [
                f for f in
                (self.TIER1_NUMERIC + self.TIER1_CATEGORICAL + self.TIER2_NUMERIC)
                if f in available
            ]
            # Adicionar correlações descobertas automaticamente
            corr_cols = [c for c in available if c.startswith("corr_")]
            selected.extend(corr_cols)
        else:
            raise ValueError("tier deve ser 1 ou 2")

        self.numeric_features = [f for f in selected if f in self.TIER1_NUMERIC + self.TIER2_NUMERIC]
        self.categorical_features = [f for f in selected if f in self.TIER1_CATEGORICAL]

        print(f"✅ Selecionadas {len(selected)} features (Tier {tier})")
        print(f"   Numéricas: {len(self.numeric_features)}")
        print(f"   Categóricas: {len(self.categorical_features)}")

        return selected

    def validate_features(self, df: pd.DataFrame, selected: List[str]) -> Tuple[pd.DataFrame, List[str]]:
        """
        Valida features antes de usar.
        - Remove colunas com > 50% missing
        - Imputa simples missing values
        - Detecta e remove constantes

        Returns:
            (df_cleaned, features_valid)
        """
        df_clean = df[selected].copy()

        # 1. Detectar muitos NaNs
        missing_pct = df_clean.isnull().sum() / len(df_clean)
        to_drop = missing_pct[missing_pct > 0.5].index.tolist()
        if to_drop:
            print(f"⚠️  Removidas {len(to_drop)} features com > 50% missing: {to_drop}")
            df_clean = df_clean.drop(columns=to_drop)
            selected = [f for f in selected if f not in to_drop]

        # 2. Imputa missing numéricos (mediana), categóricos (moda)
        for col in self.numeric_features:
            if col in df_clean.columns and df_clean[col].isnull().any():
                df_clean[col].fillna(df_clean[col].median(), inplace=True)

        for col in self.categorical_features:
            if col in df_clean.columns and df_clean[col].isnull().any():
                df_clean[col].fillna(df_clean[col].mode()[0] if not df_clean[col].mode().empty else "UNKNOWN", inplace=True)

        # 3. Detecta constantes (variance = 0)
        for col in self.numeric_features:
            if col in df_clean.columns:
                if df_clean[col].std() == 0:
                    print(f"⚠️  Feature constante removida: {col}")
                    df_clean = df_clean.drop(columns=[col])
                    selected = [f for f in selected if f != col]

        print(f"✅ Validação concluída: {len(selected)} features mantidas")

        return df_clean, selected

    def encode_features(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """
        Codifica features categóricas usando label encoding.
        Se fit=True, treina. Se False, aplica.
        """
        df_encoded = df.copy()

        for col in self.categorical_features:
            if col not in df_encoded.columns:
                continue

            if fit:
                self.encoders[col] = LabelEncoder()
                df_encoded[col] = self.encoders[col].fit_transform(df_encoded[col].astype(str))
            else:
                if col in self.encoders:
                    # Tratar valores novos
                    df_encoded[col] = df_encoded[col].map(
                        lambda x: self.encoders[col].transform([str(x)])[0]
                        if str(x) in self.encoders[col].classes_
                        else -1
                    )

        return df_encoded

    def scale_features(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """
        Normaliza features numéricas (StandardScaler).
        """
        df_scaled = df.copy()
        numeric_cols_present = [c for c in self.numeric_features if c in df_scaled.columns]

        if fit:
            self.scaler = StandardScaler()
            df_scaled[numeric_cols_present] = self.scaler.fit_transform(df_scaled[numeric_cols_present])
        else:
            if self.scaler is not None:
                df_scaled[numeric_cols_present] = self.scaler.transform(df_scaled[numeric_cols_present])

        return df_scaled

    def analyze_collinearity(self, df: pd.DataFrame, threshold: float = 0.95) -> Dict[str, List[Tuple[str, float]]]:
        """
        Detecta colinearidade entre features.

        Returns:
            Dict {feature: [(other_feature, correlation), ...]}
        """
        numeric_cols = [c for c in self.numeric_features if c in df.columns]
        corr_matrix = df[numeric_cols].corr().abs()

        high_corr = {}
        for col in corr_matrix.columns:
            high_corr[col] = [
                (other, corr)
                for other, corr in corr_matrix[col].items()
                if col != other and corr > threshold
            ]

        if any(high_corr.values()):
            print("⚠️  Colinearidade detectada:")
            for col, pairs in high_corr.items():
                if pairs:
                    print(f"   {col}: {pairs}")

        return high_corr

    def get_feature_importance_hint(self) -> Dict[str, str]:
        """
        Dica de importância esperada de cada feature baseada em lógica de domínio.
        """
        hints = {
            "macro_score_final": "Muito Alto - Score agregado principal",
            "alignment_score": "Alto - Confluência de sinais",
            "smc_equilibrium_score": "Alto - Structure do mercado",
            "probability_up": "Médio-Alto - Sentimento",
            "probability_down": "Médio-Alto - Sentimento (negativo)",
            "micro_score": "Médio - Detalhes técnicos",
            "volume_variance_pct": "Médio - Volume anomalias",
            "market_regime": "Médio - Contexto",
            "overall_confidence": "Médio - Certeza geral",
            "hour_decimal": "Baixo-Médio - Sazonalidade intraday",
        }
        return hints

    def prepare_for_training(
        self,
        df: pd.DataFrame,
        tier: int = 1,
        fit: bool = True,
    ) -> pd.DataFrame:
        """
        Pipeline completo de preparação.

        Args:
            df: DataFrame bruto
            tier: 1 ou 2
            fit: Se True, treina encoders/scaler. Se False, aplica.

        Returns:
            DataFrame pronto para treino
        """
        # 1. Selecionar features
        selected = self.select_features(df, tier=tier)

        # 2. Validar
        df_clean, selected = self.validate_features(df, selected)

        # 3. Codificar categóricas
        df_encoded = self.encode_features(df_clean[selected], fit=fit)

        # 4. Normalizar numéricas
        df_final = self.scale_features(df_encoded, fit=fit)

        # 5. Análise de colinearidade
        self.analyze_collinearity(df_final)

        print(f"\n✅ Features prontas para treino:")
        print(f"   Shape: {df_final.shape}")
        print(f"   Colunas: {df_final.columns.tolist()}")

        return df_final
