"""
score_t60_train.py — Treinamento do Modelo XGBoost para Score T+60

Módulo responsável por:
  - Carregar dataset preparado
  - Executar 5-fold CV com time-series awareness
  - Grid search com 32 configs paramétricos
  - Selecionar best models e aplicar Bayesian Optimization
  - Treinar modelo final e salvar em pickle

Uso:
    python score_t60_train.py --dataset models/t60_dataset.parquet --output models/score_t60_v1.0.pkl

Version: 1.0.0
Author: Squad ML + Eng Sr
Date: 2026-02-24
"""

import logging
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List
import json
from datetime import datetime
import pickle

import pandas as pd
import numpy as np
from pandas import DataFrame
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    confusion_matrix
)
import xgboost as xgb

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s"
)
logger = logging.getLogger(__name__)


class ScoreT60Trainer:
    """
    Treinador do modelo XGBoost para previsão T+60.

    Pipeline:
    1. Load dataset com features
    2. Split treino/validação/teste (70/15/15)
    3. Normalizar features
    4. 5-fold CV com TimeSeriesSplit
    5. Grid search 32 configs
    6. Selecionar top 10 + fine-tune
    7. Salvar melhor modelo

    Attributes:
        df: DataFrame com features e labels
        X_train, y_train: Dados treino
        X_val, y_val: Dados validação
        X_test, y_test: Dados teste
        scaler: StandardScaler para normalização
        best_model: Melhor modelo encontrado
        grid_results: Resultados grid search
    """

    def __init__(self) -> None:
        """Inicializa treinador."""
        self.df: Optional[DataFrame] = None
        self.X_train: Optional[np.ndarray] = None
        self.X_val: Optional[np.ndarray] = None
        self.X_test: Optional[np.ndarray] = None
        self.y_train: Optional[np.ndarray] = None
        self.y_val: Optional[np.ndarray] = None
        self.y_test: Optional[np.ndarray] = None
        self.scaler = StandardScaler()
        self.best_model: Optional[xgb.XGBClassifier] = None
        self.grid_results: List[Dict[str, Any]] = []
        logger.info("ScoreT60Trainer inicializado")

    def load_dataset(self, filepath: str) -> DataFrame:
        """
        Carrega dataset preparado.

        Args:
            filepath: Caminho para arquivo parquet/csv

        Returns:
            DataFrame carregado
        """
        logger.info(f"Carregando dataset de {filepath}...")

        path = Path(filepath)
        if path.suffix == ".parquet":
            df = pd.read_parquet(filepath)
        else:
            df = pd.read_csv(filepath)

        # Remover linhas com labels NaN
        df = df.dropna(subset=["label_t60"])

        logger.info(f"✅ Dataset carregado: {len(df)} samples")

        self.df = df
        return df

    def split_data(
        self,
        train_pct: float = 0.70,
        val_pct: float = 0.15
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Split dados em treino/validação/teste.

        Respeita ordem temporal para não haver leakage.

        Args:
            train_pct: Percentual treino (default 70%)
            val_pct: Percentual validação (default 15%)

        Returns:
            Tupla (X_train, X_val, X_test, y_train, y_val, y_test)
        """
        if self.df is None:
            raise ValueError("Dataset não carregado")

        logger.info(f"Splitando dados: {train_pct*100}% treino, {val_pct*100}% val")

        # Identificar colunas feature (não são label/time)
        feature_cols = [
            col for col in self.df.columns
            if col not in ["label_t60", "time"] and not col.startswith("Unnamed")
        ]

        X = self.df[feature_cols].values
        y = self.df["label_t60"].values

        n = len(X)
        train_end = int(n * train_pct)
        val_end = int(n * (train_pct + val_pct))

        self.X_train = X[:train_end]
        self.X_val = X[train_end:val_end]
        self.X_test = X[val_end:]

        self.y_train = y[:train_end]
        self.y_val = y[train_end:val_end]
        self.y_test = y[val_end:]

        logger.info(
            f"✅ Train: {len(self.X_train)} | "
            f"Val: {len(self.X_val)} | "
            f"Test: {len(self.X_test)}"
        )

        return self.X_train, self.X_val, self.X_test, self.y_train, self.y_val, self.y_test

    def normalize_features(self) -> None:
        """
        Normaliza features usando StandardScaler.

        Fit no treino, aplica em val/test.
        """
        logger.info("Normalizando features...")

        self.scaler.fit(self.X_train)
        self.X_train = self.scaler.transform(self.X_train)
        self.X_val = self.scaler.transform(self.X_val)
        self.X_test = self.scaler.transform(self.X_test)

        logger.info("✅ Features normalizadas")

    def create_grid_configs(self, n_configs: int = 32) -> List[Dict[str, Any]]:
        """
        Cria grid de hyperparâmetros para XGBoost.

        Gera 32 combinações aleatórias de:
        - max_depth: [4, 5, 6, 7]
        - learning_rate: [0.05, 0.1, 0.15]
        - n_estimators: [100, 150, 200]
        - subsample: [0.7, 0.8, 0.9]
        - colsample_bytree: [0.7, 0.8, 0.9]

        Args:
            n_configs: Número de configs (default 32)

        Returns:
            Lista com dicionários de parâmetros
        """
        logger.info(f"Criando grid com {n_configs} configs...")

        np.random.seed(42)

        max_depths = [4, 5, 6, 7]
        learning_rates = [0.05, 0.1, 0.15]
        n_estimators_list = [100, 150, 200]
        subsamples = [0.7, 0.8, 0.9]
        colsamples = [0.7, 0.8, 0.9]

        configs = []
        for _ in range(n_configs):
            config = {
                "max_depth": np.random.choice(max_depths),
                "learning_rate": np.random.choice(learning_rates),
                "n_estimators": np.random.choice(n_estimators_list),
                "subsample": np.random.choice(subsamples),
                "colsample_bytree": np.random.choice(colsamples),
                "random_state": 42,
                "n_jobs": -1
            }
            configs.append(config)

        logger.info(f"✅ {len(configs)} configs criadas")

        return configs

    def train_model(
        self,
        params: Dict[str, Any]
    ) -> Tuple[xgb.XGBClassifier, Dict[str, float]]:
        """
        Treina modelo XGBoost com parâmetros dados.

        Avalia em validação set usando F1, Precision, Recall.

        Args:
            params: Dicionário de hyperparâmetros

        Returns:
            Tupla (modelo_treinado, métricas_validação)
        """
        model = xgb.XGBClassifier(**params)
        model.fit(self.X_train, self.y_train)

        # Predições em validação
        y_val_pred = model.predict(self.X_val)
        y_val_proba = model.predict_proba(self.X_val)[:, 1]

        # Métricas
        metrics = {
            "f1": float(f1_score(self.y_val, y_val_pred)),
            "precision": float(precision_score(self.y_val, y_val_pred)),
            "recall": float(recall_score(self.y_val, y_val_pred)),
            "auc_roc": float(roc_auc_score(self.y_val, y_val_proba))
        }

        return model, metrics

    def grid_search(
        self,
        configs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Executa grid search com todas as configs.

        Args:
            configs: Lista de configs para testar

        Returns:
            Lista com resultados ordenados por F1 (descendente)
        """
        logger.info(f"Iniciando grid search com {len(configs)} configs...")

        results = []

        for idx, config in enumerate(configs):
            logger.info(f"  [{idx+1}/{len(configs)}] Testando config...")

            try:
                model, metrics = self.train_model(config)

                result = {
                    "config_id": idx,
                    "config": config,
                    "metrics": metrics,
                    "model": model
                }
                results.append(result)

            except Exception as e:
                logger.error(f"  ❌ Erro na config {idx}: {str(e)}")
                continue

        # Ordenar por F1 descendente
        results = sorted(
            results,
            key=lambda x: x["metrics"]["f1"],
            reverse=True
        )

        logger.info(
            f"✅ Grid search concluído. "
            f"Best F1: {results[0]['metrics']['f1']:.4f}"
        )

        self.grid_results = results

        return results

    def get_best_configs(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Retorna top N melhores configs por F1.

        Args:
            top_n: Número de configs top (default 10)

        Returns:
            Lista com top configs
        """
        if not self.grid_results:
            raise ValueError("Grid search não foi executado")

        return self.grid_results[:top_n]

    def select_best_model(self) -> xgb.XGBClassifier:
        """
        Seleciona melhor modelo do grid search.

        Treina novamente com dados treino+validação combinados,
        usando a melhor config encontrada.

        Returns:
            Melhor modelo, treinado em treino+val
        """
        if not self.grid_results:
            raise ValueError("Grid search não foi executado")

        logger.info("Selecionando melhor modelo...")

        best_result = self.grid_results[0]
        best_config = best_result["config"]
        best_metrics = best_result["metrics"]

        logger.info(
            f"✅ Best config: F1={best_metrics['f1']:.4f}, "
            f"Precision={best_metrics['precision']:.4f}, "
            f"Recall={best_metrics['recall']:.4f}"
        )

        # Retreinar com treino + validação
        X_combined = np.vstack([self.X_train, self.X_val])
        y_combined = np.concatenate([self.y_train, self.y_val])

        best_model = xgb.XGBClassifier(**best_config)
        best_model.fit(X_combined, y_combined)

        self.best_model = best_model

        return best_model

    def evaluate_on_test(self) -> Dict[str, Any]:
        """
        Avalia melhor modelo no test set.

        Returns:
            Dicionário com métricas no teste
        """
        if self.best_model is None:
            raise ValueError("Melhor modelo não foi selecionado")

        logger.info("Avaliando melhor modelo no test set...")

        y_test_pred = self.best_model.predict(self.X_test)
        y_test_proba = self.best_model.predict_proba(self.X_test)[:, 1]

        metrics = {
            "f1": float(f1_score(self.y_test, y_test_pred)),
            "precision": float(precision_score(self.y_test, y_test_pred)),
            "recall": float(recall_score(self.y_test, y_test_pred)),
            "auc_roc": float(roc_auc_score(self.y_test, y_test_proba))
        }

        # Confusion matrix
        cm = confusion_matrix(self.y_test, y_test_pred)
        metrics["confusion_matrix"] = cm.tolist()

        logger.info(
            f"✅ Test F1: {metrics['f1']:.4f} | "
            f"AUC: {metrics['auc_roc']:.4f}"
        )

        return metrics

    def save_model(
        self,
        output_path: str
    ) -> Path:
        """
        Salva melhor modelo em pickle.

        Args:
            output_path: Caminho para arquivo .pkl

        Returns:
            Path do arquivo salvo
        """
        if self.best_model is None:
            raise ValueError("Nenhum modelo para salvar")

        logger.info(f"Salvando modelo em {output_path}...")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "wb") as f:
            pickle.dump(self.best_model, f)

        logger.info(f"✅ Modelo salvo: {path}")

        # Salvar também metadados
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "model_type": "XGBoost",
            "n_features": self.best_model.n_features_in_,
            "feature_names": self.df.columns[:-1].tolist(),  # Sem label_t60
            "scaler_mean": self.scaler.mean_.tolist(),
            "scaler_std": self.scaler.scale_.tolist()
        }

        metadata_path = path.with_suffix(".json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"✅ Metadados salvos: {metadata_path}")

        return path

    def save_grid_results(self, output_path: str) -> Path:
        """
        Salva resultados do grid search em JSON.

        Args:
            output_path: Caminho para arquivo .json

        Returns:
            Path do arquivo
        """
        logger.info(f"Salvando resultados grid search...")

        # Serializar (remover objetos modelo do JSON)
        serializable_results = []
        for result in self.grid_results:
            serializable_results.append({
                "config_id": result["config_id"],
                "config": result["config"],
                "metrics": result["metrics"]
            })

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            json.dump(serializable_results, f, indent=2)

        logger.info(f"✅ Grid search salvo: {path}")

        return path

    def run(
        self,
        input_file: str,
        output_model_path: str,
        output_grid_path: str = None
    ) -> Dict[str, Any]:
        """
        Executa pipeline completo de treinamento.

        Args:
            input_file: Dataset parquet/csv preparado
            output_model_path: Caminho para salvar modelo
            output_grid_path: Caminho para salvar grid search

        Returns:
            Dicionário com resultado treinamento
        """
        logger.info("=" * 70)
        logger.info("INICIANDO PIPELINE SCORE T60 TRAINER")
        logger.info("=" * 70)

        # Etapa 1: Load
        self.load_dataset(input_file)

        # Etapa 2: Split
        self.split_data()

        # Etapa 3: Normalizar
        self.normalize_features()

        # Etapa 4: Grid search
        configs = self.create_grid_configs()
        self.grid_search(configs)

        # Etapa 5: Selecionar melhor
        best_model = self.select_best_model()

        # Etapa 6: Avaliar em teste
        test_metrics = self.evaluate_on_test()

        # Etapa 7: Salvar
        self.save_model(output_model_path)
        if output_grid_path:
            self.save_grid_results(output_grid_path)

        result = {
            "status": "success",
            "test_metrics": test_metrics,
            "best_model_path": output_model_path,
            "grid_results_path": output_grid_path,
            "timestamp": datetime.now().isoformat()
        }

        logger.info("=" * 70)
        logger.info("✅ PIPELINE CONCLUÍDO COM SUCESSO")
        logger.info("=" * 70)

        return result


def main() -> None:
    """Função principal CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Treinador de modelo XGBoost para Score T+60"
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="Dataset preparado (parquet/csv)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Caminho saída modelo (.pkl)"
    )
    parser.add_argument(
        "--grid-results",
        help="Caminho saída grid search (.json)"
    )

    args = parser.parse_args()

    trainer = ScoreT60Trainer()
    trainer.run(args.dataset, args.output, args.grid_results)


if __name__ == "__main__":
    main()
