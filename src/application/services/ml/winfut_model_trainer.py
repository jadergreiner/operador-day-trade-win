"""XGBoost Model Trainer para WINFUT.

Responsável por:
  1. Treinar modelo com walk-forward validation
  2. Calcular métricas (MAE, Sharpe, Win Rate)
  3. Salvar modelo persistido
  4. Gerar relatório de desempenho

Filosofia:
  - Walk-forward: Treino até D-5, validação D-5:D-1, teste D
  - Sem look-ahead bias
  - Reproducible: seed fixo para comparação
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple, List

import json
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, accuracy_score
from xgboost import XGBRegressor

from src.application.services.ml.winfut_feature_engineer import WinFutFeatureEngineer


class WinFutModelTrainer:
    """Treina modelo XGBoost para WINFUT."""

    # Configuração padrão do XGBoost
    XGBOOST_PARAMS = {
        "n_estimators": 300,
        "max_depth": 4,
        "learning_rate": 0.05,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "objective": "reg:squarederror",
        "tree_method": "hist",
        "random_state": 42,
        "n_jobs": -1,
    }

    def __init__(self, model_dir: Optional[Path] = None):
        """
        Args:
            model_dir: Diretório para persistir modelos (default: data/models/winfut/)
        """
        if model_dir is None:
            model_dir = Path("data/models/winfut")

        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.model: Optional[XGBRegressor] = None
        self.feature_engineer = WinFutFeatureEngineer()
        self.metadata: Dict = {}

    def train_walk_forward(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_folds: int = 5,
        test_size_pct: int = 20,
    ) -> Dict:
        """
        Treina modelo com validação walk-forward.

        Args:
            X: DataFrame com features (deve ter index = episode_id, coluna timestamp)
            y: Series com targets
            n_folds: Número de folds para TimeSeriesSplit
            test_size_pct: % do tamanho do teste em relação ao fold

        Returns:
            Dict com métricas por fold
        """
        # Validar dados
        if X.empty or y.empty:
            raise ValueError("X e y não podem estar vazios")

        if len(X) != len(y):
            raise ValueError(f"X ({len(X)}) e y ({len(y)}) têm tamanhos diferentes")

        print("\n" + "="*70)
        print("WALK-FORWARD VALIDATION (TimeSeriesSplit)")
        print("="*70 + "\n")

        tscv = TimeSeriesSplit(n_splits=n_folds)
        fold_results = []

        for fold_num, (train_idx, val_idx) in enumerate(tscv.split(X), start=1):
            print(f"\n--- FOLD {fold_num}/{n_folds} ---")

            # Split treino/validação
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            print(f"Train: {len(X_train)} samples | Val: {len(X_val)} samples")
            print(f"Date range train: {X_train['timestamp'].min()} a {X_train['timestamp'].max()}")
            print(f"Date range val:   {X_val['timestamp'].min()} a {X_val['timestamp'].max()}")

            # Preparar features (fit em treino, apply em val)
            X_train_prep = self.feature_engineer.prepare_for_training(X_train[self.feature_engineer.numeric_features + self.feature_engineer.categorical_features], tier=1, fit=True)
            X_val_prep = self.feature_engineer.prepare_for_training(X_val[self.feature_engineer.numeric_features + self.feature_engineer.categorical_features], tier=1, fit=False)

            # Treinar modelo
            model = XGBRegressor(**self.XGBOOST_PARAMS)
            model.fit(
                X_train_prep,
                y_train,
                eval_set=[(X_val_prep, y_val)],
                verbose=False,
                early_stopping_rounds=20,
            )

            # Predições
            y_train_pred = model.predict(X_train_prep)
            y_val_pred = model.predict(X_val_prep)

            # Métricas
            mae_train = mean_absolute_error(y_train, y_train_pred)
            mae_val = mean_absolute_error(y_val, y_val_pred)
            rmse_val = np.sqrt(mean_squared_error(y_val, y_val_pred))

            # Win rate (prédição acerta o lado?)
            y_val_sign = np.sign(y_val)
            y_val_pred_sign = np.sign(y_val_pred)
            win_rate = (y_val_sign == y_val_pred_sign).mean()

            print(f"MAE (train): {mae_train:.2f} | MAE (val): {mae_val:.2f} | RMSE: {rmse_val:.2f}")
            print(f"Win Rate: {win_rate:.2%}")

            fold_result = {
                "fold": fold_num,
                "train_size": len(X_train),
                "val_size": len(X_val),
                "mae_train": float(mae_train),
                "mae_val": float(mae_val),
                "rmse_val": float(rmse_val),
                "win_rate": float(win_rate),
            }
            fold_results.append(fold_result)

        # Agregar resultados
        summary = {
            "n_folds": n_folds,
            "fold_results": fold_results,
            "avg_mae_train": float(np.mean([f["mae_train"] for f in fold_results])),
            "avg_mae_val": float(np.mean([f["mae_val"] for f in fold_results])),
            "avg_rmse_val": float(np.mean([f["rmse_val"] for f in fold_results])),
            "avg_win_rate": float(np.mean([f["win_rate"] for f in fold_results])),
        }

        print("\n" + "="*70)
        print("RESUMO DO WALK-FORWARD")
        print("="*70)
        print(f"Média MAE (val):    {summary['avg_mae_val']:.2f}")
        print(f"Média RMSE (val):   {summary['avg_rmse_val']:.2f}")
        print(f"Média Win Rate:     {summary['avg_win_rate']:.2%}")
        print("="*70 + "\n")

        self.metadata["walk_forward"] = summary

        return summary

    def train_final(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> XGBRegressor:
        """
        Treina modelo final com TODOS os dados.
        Usado após validação bem-sucedida.

        Returns:
            Modelo treinado
        """
        print("\n" + "="*70)
        print("TREINANDO MODELO FINAL (com todos os dados)")
        print("="*70 + "\n")

        # Preparar features
        X_prep = self.feature_engineer.prepare_for_training(X, tier=1, fit=True)

        # Treinar
        self.model = XGBRegressor(**self.XGBOOST_PARAMS)
        self.model.fit(X_prep, y, verbose=False)

        # Predição completa
        y_pred = self.model.predict(X_prep)
        mae_final = mean_absolute_error(y, y_pred)
        win_rate_final = (np.sign(y) == np.sign(y_pred)).mean()

        print(f"MAE (final): {mae_final:.2f}")
        print(f"Win Rate (final): {win_rate_final:.2%}")
        print("="*70 + "\n")

        self.metadata["final_train"] = {
            "samples": len(X),
            "mae": float(mae_final),
            "win_rate": float(win_rate_final),
        }

        return self.model

    def save_model(self, suffix: str = "latest") -> Path:
        """
        Salva modelo treinado.

        Args:
            suffix: Sufixo no nome do arquivo (ex: "latest", "20260220_153000")

        Returns:
            Path do arquivo salvo
        """
        if self.model is None:
            raise ValueError("Modelo não foi treinado ainda")

        # Metadados
        self.metadata["saved_at"] = datetime.now().isoformat()
        self.metadata["suffix"] = suffix

        # Salvar modelo
        model_path = self.model_dir / f"model_{suffix}.pkl"
        joblib.dump(self.model, model_path)
        print(f"✅ Modelo salvo: {model_path}")

        # Salvar metadados
        meta_path = self.model_dir / f"metadata_{suffix}.json"
        with open(meta_path, "w") as f:
            json.dump(self.metadata, f, indent=2, default=str)
        print(f"✅ Metadados salvos: {meta_path}")

        # Salvar feature engineer (para aplicar em produção)
        fe_path = self.model_dir / f"feature_engineer_{suffix}.pkl"
        joblib.dump(self.feature_engineer, fe_path)
        print(f"✅ Feature Engineer salvo: {fe_path}")

        return model_path

    def load_model(self, suffix: str = "latest") -> XGBRegressor:
        """
        Carrega modelo persistido.
        """
        model_path = self.model_dir / f"model_{suffix}.pkl"
        if not model_path.exists():
            raise FileNotFoundError(f"Modelo não encontrado: {model_path}")

        self.model = joblib.load(model_path)

        meta_path = self.model_dir / f"metadata_{suffix}.json"
        if meta_path.exists():
            with open(meta_path, "r") as f:
                self.metadata = json.load(f)

        fe_path = self.model_dir / f"feature_engineer_{suffix}.pkl"
        if fe_path.exists():
            self.feature_engineer = joblib.load(fe_path)

        print(f"✅ Modelo carregado: {model_path}")
        return self.model

    def predict(self, X: pd.DataFrame, suffix: str = "latest") -> np.ndarray:
        """
        Faz predições com modelo persistido.

        Args:
            X: DataFrame com features (must match training features)
            suffix: Qual versão do modelo usar

        Returns:
            Array de predições
        """
        if self.model is None:
            self.load_model(suffix)

        # Aplicar transformações do feature engineer
        X_prep = self.feature_engineer.prepare_for_training(X, tier=1, fit=False)

        predictions = self.model.predict(X_prep)
        return predictions

    def feature_importance(self, top_n: int = 15) -> pd.DataFrame:
        """
        Retorna top N features mais importantes.
        """
        if self.model is None:
            raise ValueError("Modelo não foi treinado")

        importance_df = pd.DataFrame({
            "feature": self.model.get_booster().feature_names,
            "importance": self.model.get_booster().get_score(importance_type="gain").values(),
        }).sort_values("importance", ascending=False)

        return importance_df.head(top_n)

    def generate_report(self) -> str:
        """
        Gera relatório de treinamento em texto.
        """
        report = []
        report.append("="*70)
        report.append("RELATÓRIO DE TREINAMENTO — MODELO WINFUT XGBOOST")
        report.append("="*70)
        report.append("")

        report.append(f"Data: {self.metadata.get('saved_at', 'N/A')}")
        report.append("")

        if "walk_forward" in self.metadata:
            wf = self.metadata["walk_forward"]
            report.append("WALK-FORWARD VALIDATION:")
            report.append(f"  Folds: {wf['n_folds']}")
            report.append(f"  Média MAE (val): {wf['avg_mae_val']:.2f} pontos")
            report.append(f"  Média RMSE (val): {wf['avg_rmse_val']:.2f} pontos")
            report.append(f"  Média Win Rate: {wf['avg_win_rate']:.2%}")
            report.append("")

        if "final_train" in self.metadata:
            ft = self.metadata["final_train"]
            report.append("MODELO FINAL (todos dados):")
            report.append(f"  Samples: {ft['samples']}")
            report.append(f"  MAE: {ft['mae']:.2f} pontos")
            report.append(f"  Win Rate: {ft['win_rate']:.2%}")
            report.append("")

        report.append("="*70)

        return "\n".join(report)
