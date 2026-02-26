"""
Testes Unitários para XGBoost Training
Validação de 5 Acceptance Criteria (AC-8.1 até AC-8.5)
"""

import pytest
import numpy as np
from src.ml.dataset_loader_ati8 import DatasetLoader
from src.ml.model_trainer_ati8 import XGBoostTrainer


class TestXGBoostTraining:
    """Testes para treinamento e validação de modelo XGBoost"""
    
    @pytest.fixture
    def dataset(self):
        """Preparar dataset para testes"""
        loader = DatasetLoader()
        features, labels = loader.load_dataset()
        X_train, X_test, y_train, y_test = loader.prepare_data(features, labels)
        return X_train, X_test, y_train, y_test, features.columns.tolist()
    
    def test_dataset_loaded(self, dataset):
        """AC-8.1: Dataset carregado com 29 features e labels balanceados"""
        X_train, X_test, y_train, y_test, feature_names = dataset
        
        # Validar número de features
        assert X_train.shape[1] == 29, \
            f"❌ Esperado 29 features, obteve {X_train.shape[1]}"
        
        # Validar número de amostras
        assert X_train.shape[0] >= 800, \
            f"❌ Esperado >= 800 amostras treino, obteve {X_train.shape[0]}"
        assert X_test.shape[0] >= 100, \
            f"❌ Esperado >= 100 amostras teste, obteve {X_test.shape[0]}"
        
        # Validar labels binários
        assert y_train.min() == 0 and y_train.max() == 1, \
            "❌ Labels devem ser binários (0, 1)"
        
        # Validar balanceamento (35% positivos aprox)
        positive_ratio = np.sum(y_train) / len(y_train)
        assert 0.2 < positive_ratio < 0.5, \
            f"❌ Desbalanceamento: {positive_ratio:.2%} positivos"
        
        print(f"   ✅ AC-8.1 PASSED: Dataset valido (29 features, {len(feature_names)} nomes)")
    
    def test_grid_search_execution(self, dataset):
        """AC-8.2: Grid search com 8 configurações executa corretamente"""
        X_train, X_test, y_train, y_test, _ = dataset
        
        trainer = XGBoostTrainer()
        
        # Executar grid search
        results = trainer.grid_search_cv(X_train, y_train, cv_folds=5)
        
        # Validar 8 configs
        assert len(results) == 8, \
            f"❌ Esperado 8 configs, obteve {len(results)}"
        
        # Validar que cada resultado tem as métricas
        for config_num, result in results.items():
            assert 'mean_f1' in result, f"❌ Falta 'mean_f1' na config {config_num}"
            assert 'std_f1' in result, f"❌ Falta 'std_f1' na config {config_num}"
            assert 'cv_scores' in result, f"❌ Falta 'cv_scores' na config {config_num}"
            assert len(result['cv_scores']) == 5, \
                f"❌ Config {config_num} deveria ter 5 folds"
        
        print(f"   ✅ AC-8.2 PASSED: Grid search executado (8/8 configs OK)")
    
    def test_f1_score_threshold(self, dataset):
        """AC-8.3: Cross-validation 5-fold retorna F1 > 0.65"""
        X_train, X_test, y_train, y_test, _ = dataset
        
        trainer = XGBoostTrainer()
        trainer.grid_search_cv(X_train, y_train, cv_folds=5)
        
        # Validar que melhor F1 foi encontrado
        assert trainer.best_f1 > 0.0, "❌ Nenhum F1 válido foi calculado"
        
        # Validar threshold
        assert trainer.best_f1 > 0.65, \
            f"❌ F1 {trainer.best_f1:.4f} <= 0.65 (threshold)"
        
        print(f"   ✅ AC-8.3 PASSED: F1 {trainer.best_f1:.4f} > 0.65")
    
    def test_model_training(self, dataset):
        """AC-8.4: Modelo final treinado e salvo"""
        X_train, X_test, y_train, y_test, _ = dataset
        
        trainer = XGBoostTrainer()
        
        # Grid search para obter best_params
        trainer.grid_search_cv(X_train, y_train, cv_folds=5)
        
        # Treinar modelo final
        assert trainer.best_params is not None, "❌ best_params não definido"
        
        trainer.train_final_model(X_train, y_train)
        
        # Validar que modelo foi treinado
        assert trainer.best_model is not None, "❌ best_model é None"
        
        # Validar que modelo consegue fazer predições
        y_pred = trainer.best_model.predict(X_test)
        assert len(y_pred) == len(y_test), \
            f"❌ Predições {len(y_pred)} != labels {len(y_test)}"
        
        # Validar que predições são binárias
        assert np.all((y_pred == 0) | (y_pred == 1)), \
            "❌ Predições devem ser binárias"
        
        print(f"   ✅ AC-8.4 PASSED: Modelo treinado e funcional")
    
    def test_feature_importance(self, dataset):
        """AC-8.5: Feature importance calculada e documentada (top 10)"""
        X_train, X_test, y_train, y_test, feature_names = dataset
        
        trainer = XGBoostTrainer()
        
        # Grid search + training
        trainer.grid_search_cv(X_train, y_train, cv_folds=5)
        trainer.train_final_model(X_train, y_train)
        
        # Obter feature importance
        importance = trainer.get_feature_importance(feature_names, top_n=10)
        
        # Validar que retornou 10 features
        assert len(importance) == 10, \
            f"❌ Esperado 10 features, obteve {len(importance)}"
        
        # Validar que são float e positivos
        for feat, imp in importance.items():
            assert isinstance(imp, float), \
                f"❌ Importância de '{feat}' não é float"
            assert imp >= 0, \
                f"❌ Importância de '{feat}' é negativa"
        
        # Validar que feature names existem
        for feat in importance.keys():
            assert feat in feature_names, \
                f"❌ Feature '{feat}' não está em feature_names"
        
        # Validar que importâncias estão ordenadas decrescentes
        importance_values = list(importance.values())
        assert importance_values == sorted(importance_values, reverse=True), \
            "❌ Features não estão ordenadas por importância"
        
        print(f"   ✅ AC-8.5 PASSED: Top 10 features calculadas corretamente")


# Fixtures para testes de carga
@pytest.fixture
async def load_test_environment():
    """Setup environment para testes de carga"""
    loader = DatasetLoader()
    features, labels = loader.load_dataset()
    X_train, X_test, y_train, y_test = loader.prepare_data(features, labels)
    yield X_train, X_test, y_train, y_test
    # Cleanup automático


@pytest.fixture
def ml_metrics():
    """Fixture para armazenar métricas de ML"""
    return {
        'cv_f1': None,
        'test_f1': None,
        'top_features': [],
        'training_time': 0.0
    }
