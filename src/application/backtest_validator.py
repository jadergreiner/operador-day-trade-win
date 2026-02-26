"""
BacktestValidator: Validação de Modelo ML via Grid Search Histórico

Responsabilidade:
- Carregar dataset de features + labels
- Executar grid search com múltiplos thresholds
- Calcular métricas (F1, Precision, Recall, ROC-AUC)
- Backtest histórico com simulação de trades
- Validação de win rate >= 60%

Author: GitHub Copilot + ML Expert
Date: 25/02/2026
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    f1_score, precision_score, recall_score, roc_auc_score, 
    confusion_matrix, classification_report
)
import xgboost as xgb


@dataclass
class BacktestConfig:
    """Configuração de um run de backtest"""
    threshold_sigma: float
    f1_score: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    roc_auc: float = 0.0
    win_rate: float = 0.0
    num_trades: int = 0
    profitable_trades: int = 0
    loss_trades: int = 0
    cv_mean: float = 0.0
    cv_std: float = 0.0
    cv_fold_scores: List[float] = None


class BacktestValidator:
    """
    Validador de modelo ML com backtest histórico e grid search paralelo
    
    Exemplo de uso:
        validator = BacktestValidator(dataset_path='datasets/winfut_processed.npz')
        validator.load_dataset()
        results = validator.run_grid_search()
        validator.save_results(results, 'backtest_results.json')
    """

    def __init__(
        self, 
        dataset_path: str, 
        model_type: str = "xgboost",
        n_splits: int = 5,
        random_state: int = 42
    ):
        """
        Inicializa BacktestValidator
        
        Args:
            dataset_path: Path para arquivo .npz com features + labels
            model_type: Tipo de modelo ('xgboost' ou 'lightgbm')
            n_splits: Número de folds para cross-validation
            random_state: Seed para reprodutibilidade
        """
        self.dataset_path = dataset_path
        self.model_type = model_type
        self.n_splits = n_splits
        self.random_state = random_state
        
        # Atributos carregados durante load_dataset()
        self.X: Optional[np.ndarray] = None
        self.y: Optional[np.ndarray] = None
        self.timestamps: Optional[np.ndarray] = None
        self.feature_names: Optional[List[str]] = None
        
        # Modelo base
        self.model = None

    def load_dataset(self) -> None:
        """
        Carrega dataset de features + labels do arquivo .npz
        
        Deve popular:
        - self.X: (435, 24) array de features
        - self.y: (435,) array de labels (0 ou 1)
        - self.timestamps: timestamps das amostras (opcional)
        - self.feature_names: nomes das 24 features
        """
        try:
            # Carregar arquivo .npz
            data = np.load(self.dataset_path, allow_pickle=True)
            
            # Extrair componentes
            if 'X' in data:
                self.X = data['X'].astype(np.float32)
            else:
                # Tentar alternativas de nome
                self.X = data['features'].astype(np.float32) if 'features' in data else None
            
            if 'y' in data:
                self.y = data['y'].astype(np.int32)
            else:
                # Tentar alternativas de nome
                self.y = data['labels'].astype(np.int32) if 'labels' in data else None
            
            # Features opcionais
            if 'timestamps' in data:
                self.timestamps = data['timestamps']
            
            if 'feature_names' in data:
                self.feature_names = list(data['feature_names'])
            else:
                # Nomear features automaticamente se não estiver no arquivo
                self.feature_names = [f"feature_{i}" for i in range(self.X.shape[1])]
            
            # Validações
            assert self.X is not None, "Features (X) não encontradas no arquivo"
            assert self.y is not None, "Labels (y) não encontradas no arquivo"
            assert self.X.shape[0] == 435, f"Esperado 435 amostras, obteve {self.X.shape[0]}"
            assert self.X.shape[1] == 24, f"Esperado 24 features, obteve {self.X.shape[1]}"
            assert self.y.shape[0] == 435, f"Esperado 435 labels, obteve {self.y.shape[0]}"
            
            # Validar labels
            unique_labels = set(np.unique(self.y))
            assert unique_labels.issubset({0, 1}), \
                f"Labels devem ser {{0, 1}}, obteve {unique_labels}"
            
            # Validar NaN
            assert not np.isnan(self.X).any(), "Features contém valores NaN"
            assert not np.isnan(self.y).any(), "Labels contém valores NaN"
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Dataset não encontrado: {self.dataset_path}")
        except (KeyError, AssertionError) as e:
            raise ValueError(f"Erro ao carregar dataset: {str(e)}")

    def _train_model(
        self, 
        X_train: np.ndarray, 
        y_train: np.ndarray
    ) -> Any:
        """
        Treina modelo XGBoost/LightGBM no dataset de training
        
        Args:
            X_train: Features de training (70% dos dados)
            y_train: Labels de training
            
        Returns:
            Modelo treinado pronto para predict
        """
        if self.model_type == "xgboost":
            model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=self.random_state,
                eval_metric='logloss',
                verbosity=0
            )
        elif self.model_type == "lightgbm":
            import lightgbm as lgb
            model = lgb.LGBMClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=self.random_state,
                verbose=-1
            )
        else:
            raise ValueError(f"Modelo desconhecido: {self.model_type}")
        
        # Treinar
        model.fit(X_train, y_train)
        return model

    def _cross_validate(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        model: Any
    ) -> Tuple[List[float], float, float]:
        """
        Executa cross-validation 5-fold
        
        Args:
            X_train: Features
            y_train: Labels
            model: Modelo a validar
            
        Returns:
            Tuple[fold_scores, cv_mean, cv_std]
        """
        # Cross-validation com F1 score
        cv = StratifiedKFold(n_splits=self.n_splits, shuffle=True, 
                            random_state=self.random_state)
        
        fold_scores = cross_val_score(
            model, X_train, y_train, 
            cv=cv, 
            scoring='f1',
            n_jobs=-1
        )
        
        cv_mean = float(np.mean(fold_scores))
        cv_std = float(np.std(fold_scores))
        
        return list(fold_scores), cv_mean, cv_std

    def _run_backtest(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        model: Any,
        threshold_sigma: float
    ) -> Dict[str, Any]:
        """
        Executa backtest histórico
        
        Simula trades baseado em predict_proba > threshold_sigma
        Calcula win_rate baseado em retornos simulados
        
        Args:
            X_test: Features de test (15% dos dados)
            y_test: Labels de test
            model: Modelo treinado
            threshold_sigma: Threshold de confiança (1.0-3.0)
            
        Returns:
            Dict com métricas de backtest (win_rate, num_trades, etc)
        """
        # Predições
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]  # Probabilidade da classe 1
        
        # Filtrar por threshold: só tomar trades com confiança > threshold
        # Threshold em termos de desvios padrão da probabilidade
        prob_mean = np.mean(y_proba)
        prob_std = np.std(y_proba)
        
        # Se std é 0, usar threshold direto na proba normalizando
        if prob_std > 0:
            confidence_threshold = prob_mean + (threshold_sigma * prob_std)
        else:
            confidence_threshold = threshold_sigma / 10.0  # Fallback
        
        # Trades com confiança acima do threshold
        high_confidence_trades = (y_proba > confidence_threshold)
        num_trades = np.sum(high_confidence_trades)
        
        if num_trades == 0:
            # Se nenhum trade com alta confiança, usar todas as predições
            y_pred_filtered = y_pred
            num_trades = len(y_pred)
            profitable_trades = np.sum((y_pred == 1) & (y_test == 1))
        else:
            y_pred_filtered = y_pred[high_confidence_trades]
            y_test_filtered = y_test[high_confidence_trades]
            # Win = predictions corretas (y_pred == y_test)
            profitable_trades = np.sum(y_pred_filtered == y_test_filtered)
        
        loss_trades = num_trades - profitable_trades
        win_rate = (profitable_trades / num_trades * 100) if num_trades > 0 else 0.0
        
        return {
            "num_trades": int(num_trades),
            "profitable_trades": int(profitable_trades),
            "loss_trades": int(loss_trades),
            "win_rate": float(win_rate),
        }

    def _calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_proba: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """
        Calcula métricas ML (F1, Precision, Recall, ROC-AUC)
        
        Args:
            y_true: Labels verdadeiros
            y_pred: Predições do modelo
            y_proba: Probabilidades (para ROC-AUC)
            
        Returns:
            Dict com F1, Precision, Recall, ROC-AUC
        """
        metrics = {
            "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        }
        
        # ROC-AUC requer probabilidades
        if y_proba is not None and len(np.unique(y_true)) > 1:
            try:
                metrics["roc_auc"] = float(roc_auc_score(y_true, y_proba))
            except:
                metrics["roc_auc"] = 0.0
        else:
            metrics["roc_auc"] = 0.0
        
        return metrics

    def run_grid_search(self) -> List[Dict[str, Any]]:
        """
        Executa grid search com 8 thresholds
        
        Para cada threshold em [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 3.0]:
        1. Train modelo em X_train (70%)
        2. Cross-validate em X_val (15%)
        3. Backtest em X_test (15%)
        4. Calcular métricas
        5. Salvar resultado
        
        Returns:
            List[BacktestConfig] com resultados de cada threshold
        """
        # Validar que dataset foi carregado
        if self.X is None or self.y is None:
            raise RuntimeError("Dataset não foi carregado. Chamar load_dataset() primeiro.")
        
        # Split: 70% train, 15% val, 15% test
        X_temp, X_test, y_temp, y_test = train_test_split(
            self.X, self.y, 
            test_size=0.15,
            stratify=self.y,
            random_state=self.random_state
        )
        
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp,
            test_size=0.15 / 0.85,  # Proporcional
            stratify=y_temp,
            random_state=self.random_state
        )
        
        # Grid de thresholds
        threshold_sigmas = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 3.0]
        results = []
        
        for threshold_sigma in threshold_sigmas:
            # 1. Train modelo
            model = self._train_model(X_train, y_train)
            
            # 2. Cross-validate
            cv_scores, cv_mean, cv_std = self._cross_validate(X_train, y_train, model)
            
            # 3. Avaliar em validation set
            y_val_pred = model.predict(X_val)
            y_val_proba = model.predict_proba(X_val)[:, 1]
            
            val_metrics = self._calculate_metrics(y_val, y_val_pred, y_val_proba)
            
            # 4. Backtest em test set
            backtest_metrics = self._run_backtest(X_test, y_test, model, threshold_sigma)
            
            # 5. Consolidar resultado
            config = {
                "threshold_sigma": float(threshold_sigma),
                "f1_score": val_metrics["f1_score"],
                "precision": val_metrics["precision"],
                "recall": val_metrics["recall"],
                "roc_auc": val_metrics["roc_auc"],
                "win_rate": backtest_metrics["win_rate"],
                "num_trades": backtest_metrics["num_trades"],
                "profitable_trades": backtest_metrics["profitable_trades"],
                "loss_trades": backtest_metrics["loss_trades"],
                "cv_mean": cv_mean,
                "cv_std": cv_std,
                "cv_fold_scores": cv_scores,
            }
            
            results.append(config)
        
        return results

    def save_results(
        self, 
        results: List[Dict[str, Any]], 
        output_path: str
    ) -> None:
        """
        Salva resultados em arquivo JSON
        
        Args:
            results: Lista de configs com métricas
            output_path: Path para salvar JSON
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Serializar com indentação para legibilidade
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
