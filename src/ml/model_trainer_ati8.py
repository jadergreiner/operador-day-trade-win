"""
XGBoost Model Trainer
Grid search, cross-validation e treinamento de modelo de classificação
"""

import xgboost as xgb
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import f1_score, classification_report
import numpy as np
import pickle
from typing import Dict, List, Tuple


class XGBoostTrainer:
    """Treinar e validar modelo XGBoost para classificação"""

    # Grid de hiperparâmetros (8 configurações - AC-8.2)
    PARAM_GRID = [
        {'n_estimators': 50, 'max_depth': 3, 'learning_rate': 0.1, 'subsample': 0.8},
        {'n_estimators': 50, 'max_depth': 5, 'learning_rate': 0.1, 'subsample': 0.8},
        {'n_estimators': 100, 'max_depth': 3, 'learning_rate': 0.05, 'subsample': 0.8},
        {'n_estimators': 100, 'max_depth': 5, 'learning_rate': 0.05, 'subsample': 0.8},
        {'n_estimators': 100, 'max_depth': 7, 'learning_rate': 0.1, 'subsample': 0.9},
        {'n_estimators': 150, 'max_depth': 5, 'learning_rate': 0.05, 'subsample': 0.85},
        {'n_estimators': 150, 'max_depth': 7, 'learning_rate': 0.05, 'subsample': 0.85},
        {'n_estimators': 200, 'max_depth': 5, 'learning_rate': 0.01, 'subsample': 0.8},
    ]

    def __init__(self):
        self.models: Dict = {}
        self.cv_results: Dict = {}
        self.best_model = None
        self.best_params = None
        self.best_f1: float = 0.0

    def grid_search_cv(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        cv_folds: int = 5
    ) -> Dict:
        """
        AC-8.2 + AC-8.3: Executar grid search com cross-validation 5-fold

        Args:
            X_train: Features de treinamento
            y_train: Labels de treinamento
            cv_folds: Número de folds para validação cruzada

        Returns:
            Dict com resultados de cada configuração
        """
        cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        results = {}

        print(f"\n🔍 AC-8.2: Grid Search com 5-Fold CV")
        print(f"   Testando {len(self.PARAM_GRID)} configurações de hiperparâmetros\n")

        for idx, params in enumerate(self.PARAM_GRID, 1):
            print(f"[{idx}/8] max_depth={params['max_depth']}, "
                  f"n_estimators={params['n_estimators']}, "
                  f"lr={params['learning_rate']}")

            # Criar modelo
            clf = xgb.XGBClassifier(
                n_estimators=params['n_estimators'],
                max_depth=params['max_depth'],
                learning_rate=params['learning_rate'],
                subsample=params['subsample'],
                random_state=42,
                eval_metric='logloss',
                verbosity=0
            )

            # Cross-validation com F1 score
            cv_scores = cross_val_score(
                clf, X_train, y_train,
                cv=cv,
                scoring='f1'
            )

            mean_f1 = cv_scores.mean()
            std_f1 = cv_scores.std()

            results[idx] = {
                'params': params,
                'mean_f1': mean_f1,
                'std_f1': std_f1,
                'cv_scores': cv_scores
            }

            print(f"   F1: {mean_f1:.4f} (+/- {std_f1:.4f})\n")

            # Rastrear melhor modelo
            if mean_f1 > self.best_f1:
                self.best_f1 = mean_f1
                self.best_params = params
                self.best_model = clf

        self.cv_results = results

        # Resumo final
        print("\n" + "="*60)
        print(f"✅ AC-8.3: F1 Score Validation")
        print(f"   Best F1: {self.best_f1:.4f}")
        print(f"   Threshold: > 0.65")

        if self.best_f1 > 0.65:
            print(f"   Status: ✅ PASSED (F1 {self.best_f1:.4f} > 0.65)")
        else:
            print(f"   Status: ⚠️ WARNING (F1 {self.best_f1:.4f} <= 0.65)")
        print("="*60)

        return results

    def train_final_model(self, X_train: np.ndarray, y_train: np.ndarray) -> None:
        """
        AC-8.4: Treinar modelo final com melhores parâmetros

        Args:
            X_train: Features de treinamento
            y_train: Labels de treinamento
        """
        print("\n🎯 AC-8.4: Treinando Modelo Final")

        self.best_model = xgb.XGBClassifier(
            n_estimators=self.best_params['n_estimators'],
            max_depth=self.best_params['max_depth'],
            learning_rate=self.best_params['learning_rate'],
            subsample=self.best_params['subsample'],
            random_state=42,
            eval_metric='logloss',
            verbosity=0
        )

        self.best_model.fit(X_train, y_train)
        print("   ✅ Modelo final treinado com sucesso!")

    def evaluate_model(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """
        Avaliar performance no test set

        Args:
            X_test: Features de teste
            y_test: Labels de teste

        Returns:
            Dict com métricas de avaliação
        """
        y_pred = self.best_model.predict(X_test)

        f1 = f1_score(y_test, y_pred)

        print(f"\n📊 Avaliação Test Set:")
        print(f"   F1 Score: {f1:.4f}")
        print(f"\nClassification Report:")
        print(classification_report(y_test, y_pred))

        return {
            'f1': f1,
            'y_pred': y_pred
        }

    def get_feature_importance(
        self,
        feature_names: List[str],
        top_n: int = 10
    ) -> Dict[str, float]:
        """
        AC-8.5: Calcular feature importance (top 10 features)

        Args:
            feature_names: Lista de nomes das features
            top_n: Número de top features para retornar

        Returns:
            Dict com top N features e suas importâncias
        """
        if self.best_model is None:
            raise ValueError("❌ Modelo não foi treinado ainda")

        importances = self.best_model.feature_importances_

        # Top N features
        top_indices = np.argsort(importances)[-top_n:][::-1]
        top_features = {
            feature_names[idx]: float(importances[idx])
            for idx in top_indices
        }

        print(f"\n✅ AC-8.5: Top {top_n} Features")
        for idx, (feat, imp) in enumerate(top_features.items(), 1):
            print(f"   {idx:2d}. {feat:25s}: {imp:.4f}")

        return top_features

    def save_model(self, filepath: str = "models/xgboost_model.pkl") -> None:
        """
        AC-8.4: Salvar modelo treinado em arquivo .pkl

        Args:
            filepath: Caminho onde salvar o modelo
        """
        with open(filepath, 'wb') as f:
            pickle.dump(self.best_model, f)
        print(f"\n   ✅ Modelo salvo em: {filepath}")
