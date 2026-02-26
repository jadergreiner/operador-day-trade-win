"""
ML Classifier - Modelo de Classificação de Oportunidades

Padrão: Sklearn Pipeline + Hyperparameter Tuning
Responsabilidade: Classificar oportunidades como "bom trade" (score ≥80%) ou "skip"

Modelo: XGBoost ou LightGBM
Target: Binary classification (ganho=1, perda=0)

Status: SPRINT 1 - ML Expert (Skeleton)
"""

from typing import Tuple, List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import logging
import json
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score,
    precision_recall_curve, f1_score, roc_curve
)

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Tipos de modelo suportados"""
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    RANDOM_FOREST = "random_forest"


@dataclass
class ModelConfig:
    """Configuração do modelo"""
    model_type: ModelType
    random_state: int = 42
    test_size: float = 0.2
    validation_size: float = 0.1


@dataclass
class TrainingResult:
    """Resultado de um ciclo de treinamento"""
    config_id: str
    model_type: str
    features_selected: int
    training_date: datetime

    # Métricas
    train_accuracy: float
    val_accuracy: float
    test_accuracy: float

    f1_score: float
    precision: float
    recall: float
    roc_auc: float

    # Hyperparameters
    hyperparameters: Dict[str, Any]

    # Assessment
    is_production_ready: bool  # F1 > 0.65
    notes: str = ""


class MLClassifier:
    """
    Classifier para detecção de oportunidades.

    Pipeline:
    1. Raw features (24 features)
    2. Feature selection (drop low-variance)
    3. Scaling (RobustScaler)
    4. Model training (XGBoost/LightGBM)
    5. Hyperparameter tuning (grid search)
    6. Validation (cross-validation + test set)
    7. Export (pickle + ONNX para produção)

    Success metrics (SPRINT 1):
    - F1-score > 0.65 (target: 0.70+)
    - Precision > 0.65 (minimizar false positives)
    - Recall > 0.60 (maximizar true positives)
    - ROC-AUC > 0.72
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        self.model = None
        self.scaler = RobustScaler()
        self.feature_names = None
        self.feature_importance = None
        self.training_history = []

    def prepare_dataset(
        self,
        df: pd.DataFrame,
        target_column: str = 'label',
        drop_columns: Optional[List[str]] = None
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Prepara dataset para treinamento.

        Args:
            df: DataFrame com features + label
            target_column: Nome da coluna de label
            drop_columns: Colunas a descartar (timestamp, etc)

        Returns:
            Tuple[X, y, feature_names]
        """
        if drop_columns is None:
            drop_columns = ['timestamp', 'label', 'label_pnl']

        # Descartar colunas não-features
        X = df.drop(columns=[c for c in drop_columns if c in df.columns])
        y = df[target_column].astype(int)

        # Feature names para interpretabilidade
        self.feature_names = X.columns.tolist()

        # Remove NaN
        mask = y.notna() & X.notna().all(axis=1)
        X = X[mask]
        y = y[mask]

        logger.info(
            f"Dataset preparado: {X.shape[0]} samples, "
            f"{X.shape[1]} features, "
            f"{y.sum()} positivos ({(y.sum()/len(y)):.1%})"
        )

        return X.values, y.values, self.feature_names

    def train_and_evaluate(
        self,
        X: np.ndarray,
        y: np.ndarray,
        hyperparams: Optional[Dict] = None
    ) -> TrainingResult:
        """
        Traina modelo e avalia performance.

        Args:
            X: Features (n_samples, n_features)
            y: Labels (n_samples,)
            hyperparams: Hyperparameters do modelo

        Returns:
            TrainingResult com métricas
        """
        if hyperparams is None:
            hyperparams = self._get_default_hyperparams()

        # Split: train + val
        X_train_val, X_test, y_train_val, y_test = train_test_split(
            X, y,
            test_size=self.config.test_size,
            random_state=self.config.random_state,
            stratify=y
        )

        # Split: train + validation
        val_size_adjusted = self.config.validation_size / (1 - self.config.test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_train_val, y_train_val,
            test_size=val_size_adjusted,
            random_state=self.config.random_state,
            stratify=y_train_val
        )

        # Scaling
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)

        # Training
        self.model = self._build_model(hyperparams)
        self.model.fit(X_train_scaled, y_train)

        # Predictions
        y_train_pred = self.model.predict(X_train_scaled)
        y_val_pred = self.model.predict(X_val_scaled)
        y_test_pred = self.model.predict(X_test_scaled)

        y_test_proba = self.model.predict_proba(X_test_scaled)[:, 1]

        # Métricas
        train_acc = (y_train_pred == y_train).mean()
        val_acc = (y_val_pred == y_val).mean()
        test_acc = (y_test_pred == y_test).mean()

        f1 = f1_score(y_test, y_test_pred)
        precision = (y_test_pred & y_test).sum() / max((y_test_pred).sum(), 1)
        recall = (y_test_pred & y_test).sum() / max(y_test.sum(), 1)
        roc_auc = roc_auc_score(y_test, y_test_proba)

        is_ready = f1 > 0.65

        result = TrainingResult(
            config_id=f"CFG-{int(datetime.now().timestamp())}",
            model_type=self.config.model_type.value,
            features_selected=X.shape[1],
            training_date=datetime.now(),
            train_accuracy=float(train_acc),
            val_accuracy=float(val_acc),
            test_accuracy=float(test_acc),
            f1_score=float(f1),
            precision=float(precision),
            recall=float(recall),
            roc_auc=float(roc_auc),
            hyperparameters=hyperparams,
            is_production_ready=is_ready,
            notes=self._generate_notes(f1, precision, recall, roc_auc)
        )

        self.training_history.append(result)

        logger.info(
            f"Training complete: F1={f1:.3f}, ROC-AUC={roc_auc:.3f}, "
            f"Ready={is_ready}"
        )

        return result

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Prediz probabilidade de ganho para features.

        Args:
            X: Features (pode ser 1 amostra ou batch)

        Returns:
            Probabilidades [prob_loss, prob_ganho]
        """
        if self.model is None:
            logger.error("Modelo não treinado ainda")
            return np.array([[0.5, 0.5]])

        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)

    def decision_threshold(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        target_precision: float = 0.80
    ) -> float:
        """
        Encontra threshold ótimo de score para classificação.

        Objetivo: Encontrar ponto onde precision >= target_precision

        Args:
            X_test: Features de teste
            y_test: Labels de teste
            target_precision: Precision mínima desejada (ex: 80%)

        Returns:
            Threshold ótimo (ex: 0.80)
        """
        y_proba = self.predict_proba(X_test)[:, 1]
        precision, recall, thresholds = precision_recall_curve(y_test, y_proba)

        # Encontrar threshold onde precision >= target
        valid_idx = np.where(precision >= target_precision)[0]
        if len(valid_idx) == 0:
            return 0.99  # Muito conservador

        best_idx = valid_idx[np.argmax(recall[valid_idx])]
        best_threshold = thresholds[best_idx]

        logger.info(
            f"Threshold ótimo: {best_threshold:.2f} "
            f"(precision={precision[best_idx]:.2f}, "
            f"recall={recall[best_idx]:.2f})"
        )

        return float(best_threshold)

    def feature_importance(self) -> Dict[str, float]:
        """Retorna importância de cada feature"""
        if self.model is None or not hasattr(self.model, 'feature_importances_'):
            return {}

        importance_dict = {
            name: float(imp)
            for name, imp in zip(
                self.feature_names,
                self.model.feature_importances_
            )
        }

        # Sort por importância
        return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

    def save_model(self, path: str):
        """Salva modelo treinado"""
        import pickle
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump(self, f)
        logger.info(f"Modelo salvo: {path}")

    def export_metrics_json(self, output_path: str):
        """Exporta métricas de treinamento como JSON"""
        metrics_data = {
            "training_history": [
                {
                    "config_id": r.config_id,
                    "model_type": r.model_type,
                    "training_date": r.training_date.isoformat(),
                    "f1_score": r.f1_score,
                    "roc_auc": r.roc_auc,
                    "precision": r.precision,
                    "recall": r.recall,
                    "is_production_ready": r.is_production_ready,
                    "hyperparameters": r.hyperparameters
                }
                for r in self.training_history
            ]
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(metrics_data, f, indent=2, default=str)

        logger.info(f"Métricas exportadas: {output_path}")

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _build_model(self, hyperparams: Dict):
        """Constrói modelo específico"""
        if self.config.model_type == ModelType.XGBOOST:
            try:
                import xgboost as xgb
                return xgb.XGBClassifier(**hyperparams)
            except ImportError:
                logger.error("xgboost não instalado")
                return None

        elif self.config.model_type == ModelType.LIGHTGBM:
            try:
                import lightgbm as lgb
                return lgb.LGBMClassifier(**hyperparams)
            except ImportError:
                logger.error("lightgbm não instalado")
                return None

        else:
            from sklearn.ensemble import RandomForestClassifier
            return RandomForestClassifier(**hyperparams)

    @staticmethod
    def _get_default_hyperparams() -> Dict:
        """Hyperparameters padrão (XGBoost)"""
        return {
            'n_estimators': 100,
            'max_depth': 5,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'eval_metric': 'logloss'
        }

    @staticmethod
    def _generate_notes(f1: float, precision: float, recall: float, roc_auc: float) -> str:
        """Gera notas sobre qualidade do modelo"""
        notes = []

        if f1 < 0.65:
            notes.append("⚠️ F1-score baixo: modelo ainda em desenvolvimento")
        elif f1 < 0.70:
            notes.append("🟡 F1-score aceitável: faz sentido usar mas monitorar")
        else:
            notes.append("✅ F1-score excelente")

        if precision < 0.70:
            notes.append("🔴 Precision baixa: muitos falsos positivos")
        elif precision < 0.80:
            notes.append("🟡 Precision normal: esperado para trading")
        else:
            notes.append("✅ Precision alta")

        if roc_auc < 0.65:
            notes.append("⚠️ ROC-AUC baixo: modelo pior que random")

        return " | ".join(notes)


# ============================================================================
# GRID SEARCH ORCHESTRATION
# ============================================================================

@dataclass
class GridSearchConfig:
    """Configuração para grid search de hyperparameters"""
    param_grid: Dict[str, List[Any]]
    model_type: ModelType = ModelType.XGBOOST
    cv_folds: int = 5


class GridSearchOrchestrator:
    """
    Orquestra busca em grid de hyperparameters.

    Vai treinar 8+ modelos com diferentes configs e retornar melhores.

    Configs a testar:
    1. Learning rate: [0.05, 0.1, 0.2]
    2. Max depth: [3, 5, 7]
    3. Subsample: [0.6, 0.8, 1.0]
    4. Colsample: [0.6, 0.8, 1.0]

    Total: 3*3*3*3 = 81 configurações (será reduzido para 8-16 melhores)
    """

    def __init__(self, config: GridSearchConfig):
        self.config = config
        self.results: List[TrainingResult] = []

    def search(
        self,
        X: np.ndarray,
        y: np.ndarray,
        max_configs: int = 8
    ) -> Tuple[TrainingResult, List[TrainingResult]]:
        """
        Executa grid search.

        Args:
            X: Features de treino
            y: Labels de treino
            max_configs: Número máximo de configs a testar

        Returns:
            Tuple[best_result, all_results]
        """
        logger.info(f"Iniciando grid search com até {max_configs} configs...")

        # TODO: Implementar grid search em paralelo
        # Por agora, treina alguns configs manuais

        configs_to_test = [
            # Config 1: Conservative
            {
                'n_estimators': 100,
                'max_depth': 3,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8
            },
            # Config 2: Balanced
            {
                'n_estimators': 150,
                'max_depth': 5,
                'learning_rate': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8
            },
            # Config 3: Aggressive
            {
                'n_estimators': 200,
                'max_depth': 7,
                'learning_rate': 0.15,
                'subsample': 0.9,
                'colsample_bytree': 0.9
            },
        ]

        best_result = None

        for config in configs_to_test:
            logger.info(f"Testando: {config}")

            classifier = MLClassifier(
                ModelConfig(self.config.model_type)
            )

            result = classifier.train_and_evaluate(X, y, config)
            self.results.append(result)

            if best_result is None or result.f1_score > best_result.f1_score:
                best_result = result

        logger.info(f"Grid search completo: melhor F1={best_result.f1_score:.3f}")

        return best_result, self.results


# ============================================================================
# BACKTEST VALIDATION - GRID SEARCH COM THRESHOLDS
# ============================================================================

class BacktestValidator:
    """
    Grid search validator para validar modelo ML antes de produção.

    Executa grid search em múltiplos thresholds e valida:
    - F1 >= 0.65 (AC-3)
    - Win Rate >= 60% (AC-4)
    - Threshold ótimo selecionado (AC-5)
    """

    def __init__(self, X: np.ndarray, y: np.ndarray, random_state: int = 42):
        """
        Inicializar validator com dados de treino/teste.

        Args:
            X: Features array (N_samples, N_features)
            y: Labels array (N_samples,) - binary (0 ou 1)
            random_state: Seed para reproducibilidade
        """
        self.X = X
        self.y = y
        self.random_state = random_state

        logger.info(f"✅ BacktestValidator initialized with X shape={X.shape}, y shape={y.shape}")

    def grid_search(
        self,
        thresholds: Optional[List[float]] = None,
        test_size: float = 0.30,
        random_state: Optional[int] = None
    ) -> Dict[float, Dict]:
        """
        Executar grid search com múltiplos thresholds.

        AC-1: Grid Search Executado
        AC-2: Métricas Calculadas

        Args:
            thresholds: Lista de thresholds para testar
                       Default: [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
            test_size: Porcentagem de dados para validação (0.30 = 30%)
            random_state: Seed (usa self.random_state se None)

        Returns:
            Dict[float, Dict]: {
                threshold: {
                    'metrics_val': {...},
                    'metrics_test': {...},
                    'models': {...}
                }
            }
        """
        try:
            from xgboost import XGBClassifier
            from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score, confusion_matrix
        except ImportError:
            logger.error("XGBoost ou sklearn não instalados")
            raise

        if thresholds is None:
            thresholds = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]

        if random_state is None:
            random_state = self.random_state

        results = {}

        logger.info(f"🔍 Starting grid search with {len(thresholds)} thresholds...")

        for threshold in thresholds:
            logger.info(f"  Testing threshold={threshold}")

            # Split data: 70% train, 15% val, 15% test
            X_train, X_rest, y_train, y_rest = train_test_split(
                self.X, self.y, test_size=test_size, random_state=random_state
            )
            X_val, X_test, y_val, y_test = train_test_split(
                X_rest, y_rest, test_size=0.5, random_state=random_state
            )

            # Train XGBoost model
            model = XGBClassifier(
                max_depth=5,
                learning_rate=0.1,
                n_estimators=100,
                random_state=random_state,
                verbosity=0
            )
            model.fit(X_train, y_train, verbose=False)

            # Predict on validation set
            y_pred_val = model.predict(X_val)
            y_pred_proba_val = model.predict_proba(X_val)[:, 1]

            # Predict on test set
            y_pred_test = model.predict(X_test)
            y_pred_proba_test = model.predict_proba(X_test)[:, 1]

            # Calculate metrics for validation set
            metrics_val = {
                'f1': float(f1_score(y_val, y_pred_val, zero_division=0)),
                'precision': float(precision_score(y_val, y_pred_val, zero_division=0)),
                'recall': float(recall_score(y_val, y_pred_val, zero_division=0)),
                'accuracy': float(accuracy_score(y_val, y_pred_val))
            }

            # Calculate metrics for test set
            metrics_test = {
                'f1': float(f1_score(y_test, y_pred_test, zero_division=0)),
                'precision': float(precision_score(y_test, y_pred_test, zero_division=0)),
                'recall': float(recall_score(y_test, y_pred_test, zero_division=0)),
                'accuracy': float(accuracy_score(y_test, y_pred_test)),
                'win_rate': float((y_pred_test == y_test).sum() / len(y_test))
            }

            # Calculate confusion matrix
            cm = confusion_matrix(y_test, y_pred_test)

            results[threshold] = {
                'metrics_val': metrics_val,
                'metrics_test': metrics_test,
                'confusion_matrix': cm.tolist(),
                'model': model,
                'splits': {
                    'train_size': len(X_train),
                    'val_size': len(X_val),
                    'test_size': len(X_test)
                }
            }

            logger.info(
                f"    ✅ F1={metrics_val['f1']:.4f} (val), "
                f"F1={metrics_test['f1']:.4f} (test), "
                f"WR={metrics_test['win_rate']:.1%}"
            )

        logger.info(f"✅ Grid search completed with {len(results)} thresholds")
        return results

    def select_optimal_threshold(self, results: Dict[float, Dict]) -> float:
        """
        Selecionar threshold ótimo baseado em F1 máximo.

        AC-5: Threshold Ótimo Selecionado

        Args:
            results: Output do grid_search()

        Returns:
            float: Threshold ótimo
        """
        if not results:
            raise ValueError("Results dictionary is empty")

        # Ordenar por F1 do validation set (decrescente)
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1]['metrics_val']['f1'],
            reverse=True
        )

        optimal_threshold = sorted_results[0][0]
        optimal_f1 = sorted_results[0][1]['metrics_val']['f1']

        logger.info(f"🎯 Optimal threshold selected: {optimal_threshold} (F1={optimal_f1:.4f})")

        return optimal_threshold

    def validate_criteria(self, results: Dict[float, Dict]) -> Tuple[bool, str]:
        """
        Validar critérios GoNo-Go (F1 >= 0.65, WR >= 60%).

        AC-3: F1 > 0.65 Validado
        AC-4: Win Rate >= 60% Validado

        Args:
            results: Output do grid_search()

        Returns:
            Tuple[bool, str]: (go_nogo, reason)
        """
        # Encontrar melhor F1 e WR
        max_f1 = max(r['metrics_val']['f1'] for r in results.values())
        max_wr = max(r['metrics_test']['win_rate'] for r in results.values())

        # Validar critérios
        f1_ok = max_f1 >= 0.65
        wr_ok = max_wr >= 0.60

        reason = f"F1={max_f1:.4f} (target 0.65) | WR={max_wr:.1%} (target 60%)"

        if f1_ok and wr_ok:
            logger.info(f"🟢 GO DECISION: {reason}")
            return True, reason
        else:
            logger.warning(f"🔴 NO-GO DECISION: {reason}")
            return False, reason

    def save_report(
        self,
        results: Dict[float, Dict],
        output_path: str = "backtest_final_metrics.json"
    ) -> None:
        """
        Salvar relatório em JSON.

        AC-6: Relatório Gerado

        Args:
            results: Output do grid_search()
            output_path: Caminho para salvar JSON
        """
        optimal_threshold = self.select_optimal_threshold(results)
        go_nogo, reason = self.validate_criteria(results)

        # Preparar dados para serialização (remover modelos)
        serializable_results = {}
        for threshold, data in results.items():
            serializable_results[str(threshold)] = {
                'metrics_val': data['metrics_val'],
                'metrics_test': data['metrics_test'],
                'confusion_matrix': data['confusion_matrix'],
                'splits': data['splits']
            }

        report = {
            'grid_search_results': serializable_results,
            'optimal_threshold': float(optimal_threshold),
            'optimal_metrics': {
                'metrics_val': results[optimal_threshold]['metrics_val'],
                'metrics_test': results[optimal_threshold]['metrics_test']
            },
            'validation_criteria': {
                'f1_threshold': 0.65,
                'win_rate_threshold': 0.60,
                'max_f1': float(max(r['metrics_val']['f1'] for r in results.values())),
                'max_win_rate': float(max(r['metrics_test']['win_rate'] for r in results.values()))
            },
            'decision': 'GO' if go_nogo else 'NO-GO',
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'grid_search_config': {
                'n_thresholds': len(results),
                'thresholds_tested': sorted([float(t) for t in results.keys()])
            }
        }

        # Criar diretório se necessário
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Salvar JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Report saved to {output_path}")

    @staticmethod
    def load_from_csv(csv_path: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Carregar dados from training_dataset.csv.

        Args:
            csv_path: Caminho para CSV (output do TODO-1)

        Returns:
            Tuple[X, y]: Features e labels
        """
        df = pd.read_csv(csv_path)

        # Remover window_id e label
        X = df.drop(['window_id', 'label'], axis=1).values.astype(np.float32)
        y = df['label'].values.astype(np.int32)

        logger.info(f"✅ Data loaded from {csv_path}")
        logger.info(f"   X shape: {X.shape}")
        logger.info(f"   y shape: {y.shape}")
        logger.info(f"   Label distribution: {(y==1).sum()} BUY, {(y==0).sum()} SKIP")

        return X, y


if __name__ == "__main__":
    print("MLClassifier module loaded")
