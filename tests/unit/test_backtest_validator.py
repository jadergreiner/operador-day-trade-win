"""
Testes para BacktestValidator - Task #3.

Valida grid search com múltiplos thresholds, critérios F1 e win rate.
"""

import logging
import time

import pytest
import json
import numpy as np
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.application.ml_classifier import (
    BacktestValidator,
    GridSearchOrchestrator,
    GridSearchConfig,
    ModelType,
)


class TestBacktestValidator:
    """Testes para classe BacktestValidator"""

    @pytest.fixture
    def sample_data(self):
        """Criar dados de exemplo 70 amostras, 10 features"""
        np.random.seed(42)
        X = np.random.randn(100, 10).astype(np.float32)
        y = np.random.binomial(1, 0.55, 100).astype(np.int32)  # 55% classe 1
        return X, y

    @pytest.fixture
    def csv_with_data(self, tmp_path):
        """Criar CSV temporário com dados de treinamento"""
        # Criar dataset com 24 features
        n_samples = 100
        data = {}

        for i in range(24):
            data[f'feature_{i}'] = np.random.randn(n_samples)

        data['window_id'] = list(range(n_samples))
        data['label'] = np.random.binomial(1, 0.55, n_samples)

        df = pd.DataFrame(data)
        csv_path = tmp_path / "training_dataset.csv"
        df.to_csv(csv_path, index=False)

        return str(csv_path)

    def test_init_validator(self, sample_data):
        """AC-0: Validator inicializado com dimens

ions corretas"""
        X, y = sample_data
        validator = BacktestValidator(X, y, random_state=42)

        assert validator.X.shape == X.shape
        assert validator.y.shape == y.shape
        assert validator.random_state == 42

    def test_load_from_csv(self, csv_with_data):
        """AC-7: Load data from CSV (25 features esperadas - 24 + labels)"""
        X, y = BacktestValidator.load_from_csv(csv_with_data)

        # Validar dimensões
        assert X.shape[1] == 24  # 24 features (sem window_id, label)
        assert y.shape[0] == X.shape[0]  # Mesmo número de samples
        assert X.dtype == np.float32
        assert y.dtype == np.int32

    def test_grid_search_executes(self, sample_data):
        """AC-1: Grid Search Executado com múltiplos thresholds"""
        X, y = sample_data
        validator = BacktestValidator(X, y)

        # Executar grid search com 3 thresholds apenas (para speed)
        thresholds = [1.0, 2.0, 3.0]
        results = validator.grid_search(thresholds=thresholds)

        # Validar que todos os thresholds foram testados
        assert len(results) == len(thresholds)
        assert all(t in results for t in thresholds)

    def test_grid_search_computes_metrics(self, sample_data):
        """AC-2: Métricas Calculadas (F1, precision, recall, accuracy, win_rate)"""
        X, y = sample_data
        validator = BacktestValidator(X, y)

        results = validator.grid_search(thresholds=[1.5, 2.5])

        for threshold, data in results.items():
            # Validar que métricas foram computadas
            assert 'metrics_val' in data
            assert 'metrics_test' in data

            # Validar campos das métricas
            for metric_dict in [data['metrics_val'], data['metrics_test']]:
                assert 'f1' in metric_dict
                assert 'precision' in metric_dict
                assert 'recall' in metric_dict
                assert 'accuracy' in metric_dict

            assert 'win_rate' in data['metrics_test']

            # Validar ranges
            assert 0.0 <= data['metrics_val']['f1'] <= 1.0
            assert 0.0 <= data['metrics_test']['win_rate'] <= 1.0

    def test_select_optimal_threshold(self, sample_data):
        """AC-5: Threshold Ótimo Selecionado (baseado em F1 máximo)"""
        X, y = sample_data
        validator = BacktestValidator(X, y)

        results = validator.grid_search(thresholds=[1.0, 2.0, 3.0])
        optimal = validator.select_optimal_threshold(results)

        # Validar que threshold está na lista de testados
        assert optimal in results

        # Validar que é o com F1 máximo
        best_f1 = results[optimal]['metrics_val']['f1']
        for other_threshold, data in results.items():
            assert data['metrics_val']['f1'] <= best_f1

    def test_validate_criteria_go(self, sample_data):
        """AC-3: F1 > 0.65 Validado, AC-4: Win Rate >= 60% Validado

        Teste para decisão GO (simular dados favoráveis)"""
        X, y = sample_data
        validator = BacktestValidator(X, y)

        # Mock dos resultados para simular GO decision
        mock_results = {
            1.0: {
                'metrics_val': {'f1': 0.70, 'precision': 0.72, 'recall': 0.68, 'accuracy': 0.68},
                'metrics_test': {'f1': 0.68, 'precision': 0.70, 'recall': 0.66, 'accuracy': 0.67, 'win_rate': 0.65}
            }
        }

        go_nogo, reason = validator.validate_criteria(mock_results)

        assert go_nogo is True
        assert "0.70" in reason or "0.70" in str(reason)
        assert "0.65" in reason or "0.65" in str(reason) or "65.0" in reason

    def test_validate_criteria_nogo(self, sample_data):
        """AC-3/4: Teste para decisão NO-GO (métricas insuficientes)"""
        X, y = sample_data
        validator = BacktestValidator(X, y)

        # Mock dos resultados para simular NO-GO decision
        mock_results = {
            1.0: {
                'metrics_val': {'f1': 0.50, 'precision': 0.52, 'recall': 0.48, 'accuracy': 0.50},
                'metrics_test': {'f1': 0.48, 'precision': 0.50, 'recall': 0.46, 'accuracy': 0.49, 'win_rate': 0.50}
            }
        }

        go_nogo, reason = validator.validate_criteria(mock_results)

        assert go_nogo is False
        assert "0.50" in reason or "50.0" in reason

    def test_save_report_creates_json(self, sample_data, tmp_path):
        """AC-6: Relatório Gerado em JSON com estrutura correta"""
        X, y = sample_data
        validator = BacktestValidator(X, y)

        results = validator.grid_search(thresholds=[1.0, 2.0])
        output_path = str(tmp_path / "test_report.json")

        validator.save_report(results, output_path)

        # Validar que arquivo foi criado
        assert Path(output_path).exists()

        # Validar conteúdo do JSON
        with open(output_path, 'r', encoding='utf-8') as f:
            report = json.load(f)

        assert 'grid_search_results' in report
        assert 'optimal_threshold' in report
        assert 'decision' in report
        assert 'reason' in report
        assert 'timestamp' in report
        assert 'validation_criteria' in report
        assert 'grid_search_config' in report

        # Validar campos de validação
        assert report['validation_criteria']['f1_threshold'] == 0.65
        assert report['validation_criteria']['win_rate_threshold'] == 0.60
        assert 'max_f1' in report['validation_criteria']
        assert 'max_win_rate' in report['validation_criteria']


class TestBacktestValidatorIntegration:
    """Testes de integração para BacktestValidator"""

    @pytest.fixture
    def training_dataset(self, tmp_path):
        """Criar dataset de treinamento realista"""
        np.random.seed(42)
        n_samples = 200

        # Criar features correlacionadas com label
        X = np.random.randn(n_samples, 24)
        y = (X[:, 0] + 0.5 * X[:, 1] + np.random.randn(n_samples) > 0).astype(np.int32)

        # Salvar como CSV
        columns = [f'feature_{i}' for i in range(24)]
        df = pd.DataFrame(X, columns=columns)
        df['window_id'] = list(range(n_samples))
        df['label'] = y

        csv_path = tmp_path / "training_dataset.csv"
        df.to_csv(csv_path, index=False)

        return str(csv_path)

    def test_full_pipeline(self, training_dataset, tmp_path):
        """Teste E2E: Load -> Grid Search -> Validate -> Report"""
        # Load
        X, y = BacktestValidator.load_from_csv(training_dataset)
        assert X.shape[0] > 0

        # Initialize
        validator = BacktestValidator(X, y)

        # Grid search
        results = validator.grid_search(thresholds=[1.0, 2.0, 3.0])
        assert len(results) == 3

        # Select optimal
        optimal = validator.select_optimal_threshold(results)
        assert optimal in results

        # Validate
        go_nogo, reason = validator.validate_criteria(results)
        assert isinstance(go_nogo, bool)
        assert isinstance(reason, str)

        # Save report
        output_path = str(tmp_path / "report.json")
        validator.save_report(results, output_path)

        assert Path(output_path).exists()
        with open(output_path, 'r') as f:
            report = json.load(f)

        assert report['decision'] in ['GO', 'NO-GO']


# =============================================================================
# TESTES DE PARALELIZAÇÃO — BLID-034
# =============================================================================

class TestGridSearchParalelo:
    """
    Testes para paralelização do grid search com joblib.Parallel.

    Critérios de aceite validados:
    - Reprodutibilidade: mesmo random_state → mesmas métricas
    - Sem data leakage: split realizado uma única vez fora do loop
    - Log de progresso: mensagens de timing registradas
    - n_jobs aceito: parâmetro propagado sem erro
    """

    @pytest.fixture
    def dados_treino(self):
        """Dataset determinístico para comparação de resultados."""
        np.random.seed(0)
        X = np.random.randn(120, 10).astype(np.float32)
        y = np.random.binomial(1, 0.55, 120).astype(np.int32)
        return X, y

    # ------------------------------------------------------------------
    # Reprodutibilidade
    # ------------------------------------------------------------------

    def test_reproducibilidade_mesmo_random_state(self, dados_treino):
        """
        DADO random_state fixo,
        QUANDO grid_search é chamado duas vezes,
        ENTÃO todas as métricas (F1, precision, recall, accuracy, win_rate)
        devem ser idênticas.
        """
        X, y = dados_treino
        thresholds = [1.0, 2.0]

        validator_a = BacktestValidator(X, y, random_state=42)
        resultado_a = validator_a.grid_search(thresholds=thresholds, n_jobs=1)

        validator_b = BacktestValidator(X, y, random_state=42)
        resultado_b = validator_b.grid_search(thresholds=thresholds, n_jobs=1)

        campos_val = ['f1', 'precision', 'recall', 'accuracy']
        campos_test = ['f1', 'precision', 'recall', 'accuracy', 'win_rate']

        for t in thresholds:
            for campo in campos_val:
                assert resultado_a[t]['metrics_val'][campo] == pytest.approx(
                    resultado_b[t]['metrics_val'][campo], abs=1e-6
                ), f"metrics_val[{campo}] diferiu para threshold={t}"
            for campo in campos_test:
                assert resultado_a[t]['metrics_test'][campo] == pytest.approx(
                    resultado_b[t]['metrics_test'][campo], abs=1e-6
                ), f"metrics_test[{campo}] diferiu para threshold={t}"

    def test_random_state_diferente_gera_resultado_diferente(self, dados_treino):
        """
        DADO random_states distintos,
        QUANDO grid_search é chamado,
        ENTÃO ao menos um resultado deve ser diferente.
        """
        X, y = dados_treino
        thresholds = [1.0, 2.0]

        validator_a = BacktestValidator(X, y, random_state=42)
        resultado_a = validator_a.grid_search(thresholds=thresholds, n_jobs=1)

        validator_b = BacktestValidator(X, y, random_state=99)
        resultado_b = validator_b.grid_search(thresholds=thresholds, n_jobs=1)

        # Com seeds diferentes, os splits diferem → ao menos 1 métrica deve divergir
        f1_a = [resultado_a[t]['metrics_val']['f1'] for t in thresholds]
        f1_b = [resultado_b[t]['metrics_val']['f1'] for t in thresholds]
        assert f1_a != f1_b, "F1s deveriam diferir com random_state distinto"

    # ------------------------------------------------------------------
    # Parâmetro n_jobs
    # ------------------------------------------------------------------

    def test_njobs_negativo_aceito_sem_erro(self, dados_treino):
        """
        DADO n_jobs=-1 (todos os núcleos),
        QUANDO grid_search é chamado,
        ENTÃO deve retornar resultados sem lançar exceção.
        """
        X, y = dados_treino
        validator = BacktestValidator(X, y, random_state=42)
        resultado = validator.grid_search(thresholds=[1.0, 2.0], n_jobs=-1)
        assert len(resultado) == 2

    def test_njobs_1_aceito_sem_erro(self, dados_treino):
        """
        DADO n_jobs=1 (sem paralelismo),
        QUANDO grid_search é chamado,
        ENTÃO deve retornar resultados sem lançar exceção.
        """
        X, y = dados_treino
        validator = BacktestValidator(X, y, random_state=42)
        resultado = validator.grid_search(thresholds=[1.0, 2.0], n_jobs=1)
        assert len(resultado) == 2

    def test_njobs_2_aceito_sem_erro(self, dados_treino):
        """
        DADO n_jobs=2,
        QUANDO grid_search é chamado,
        ENTÃO deve retornar resultados sem lançar exceção.
        """
        X, y = dados_treino
        validator = BacktestValidator(X, y, random_state=42)
        resultado = validator.grid_search(thresholds=[1.0, 2.0], n_jobs=2)
        assert len(resultado) == 2

    # ------------------------------------------------------------------
    # Sem data leakage — split único fora do loop
    # ------------------------------------------------------------------

    def test_splits_identicos_entre_thresholds(self, dados_treino):
        """
        DADO mesmo random_state,
        QUANDO grid_search avalia vários thresholds,
        ENTÃO os tamanhos de treino/val/teste devem ser idênticos
        para todos os thresholds (split feito uma única vez).
        """
        X, y = dados_treino
        validator = BacktestValidator(X, y, random_state=42)
        resultado = validator.grid_search(
            thresholds=[1.0, 2.0, 3.0], n_jobs=1
        )

        splits_set = {
            (
                r['splits']['train_size'],
                r['splits']['val_size'],
                r['splits']['test_size']
            )
            for r in resultado.values()
        }
        # Todos os thresholds devem usar exatamente o mesmo split
        assert len(splits_set) == 1, (
            f"Splits divergiram entre thresholds: {splits_set}"
        )

    # ------------------------------------------------------------------
    # Log de progresso
    # ------------------------------------------------------------------

    def test_log_timing_registrado(self, dados_treino, caplog):
        """
        DADO qualquer chamada a grid_search,
        QUANDO a execução terminar,
        ENTÃO o log deve conter mensagem de timing no formato 'X.Xs'.
        """
        import re
        X, y = dados_treino
        validator = BacktestValidator(X, y, random_state=42)

        with caplog.at_level(logging.INFO, logger="src.application.ml_classifier"):
            validator.grid_search(thresholds=[1.0, 2.0], n_jobs=1)

        mensagens = " ".join(caplog.messages)
        # Verifica formato numerico de timing: ex. "1.5s" ou "0.3s"
        assert re.search(r"\d+\.\d+s", mensagens), (
            "Log de timing no formato '<numero>s' nao encontrado"
        )

    def test_log_paralelo_registrado(self, dados_treino, caplog):
        """
        DADO chamada a grid_search,
        QUANDO iniciada,
        ENTÃO o log deve mencionar n_jobs e quantidade de thresholds.
        """
        X, y = dados_treino
        validator = BacktestValidator(X, y, random_state=42)

        with caplog.at_level(logging.INFO, logger="src.application.ml_classifier"):
            validator.grid_search(thresholds=[1.0, 2.0], n_jobs=2)

        mensagens = " ".join(caplog.messages)
        assert "n_jobs=2" in mensagens, (
            "n_jobs deveria aparecer no log de progresso"
        )
        assert "2 thresholds" in mensagens, (
            "Quantidade de thresholds deveria aparecer no log"
        )

    # ------------------------------------------------------------------
    # Estrutura do resultado
    # ------------------------------------------------------------------

    def test_resultado_contem_todas_chaves_obrigatorias(self, dados_treino):
        """
        DADO grid_search com thresholds customizados,
        QUANDO executado,
        ENTÃO cada entrada do dicionário deve conter as chaves obrigatórias.
        """
        X, y = dados_treino
        thresholds = [1.5, 3.0, 4.5]
        validator = BacktestValidator(X, y, random_state=42)
        resultado = validator.grid_search(thresholds=thresholds, n_jobs=1)

        assert set(resultado.keys()) == set(thresholds)
        for t in thresholds:
            assert 'metrics_val' in resultado[t]
            assert 'metrics_test' in resultado[t]
            assert 'confusion_matrix' in resultado[t]
            assert 'splits' in resultado[t]
            assert 'win_rate' in resultado[t]['metrics_test']


class TestGridSearchOrchestratorParalelo:
    """
    Testes para paralelização do GridSearchOrchestrator.search()
    via joblib.Parallel — BLID-034.
    """

    @pytest.fixture
    def dados_treino(self):
        """Dataset determinístico para comparação de resultados."""
        np.random.seed(7)
        X = np.random.randn(150, 12).astype(np.float32)
        y = np.random.binomial(1, 0.5, 150).astype(np.int32)
        return X, y

    def test_search_paralelo_retorna_best_e_lista(self, dados_treino):
        """
        DADO GridSearchOrchestrator com n_jobs=-1 e XGBOOST,
        QUANDO search() é chamado,
        ENTÃO deve retornar (best_result, all_results) sem exceção.
        """
        X, y = dados_treino
        config = GridSearchConfig(
            param_grid={},
            model_type=ModelType.XGBOOST,
            n_jobs=-1
        )
        orquestrador = GridSearchOrchestrator(config)
        melhor, todos = orquestrador.search(X, y, max_configs=2)

        assert melhor is not None
        assert len(todos) == 2
        assert melhor.f1_score == max(r.f1_score for r in todos)

    def test_njobs_propagado_via_gridconfig(self, dados_treino):
        """
        DADO n_jobs=1 em GridSearchConfig,
        QUANDO search() é executado,
        ENTÃO deve funcionar corretamente (sem paralelismo externo).
        """
        X, y = dados_treino
        config = GridSearchConfig(
            param_grid={},
            model_type=ModelType.XGBOOST,
            n_jobs=1
        )
        orquestrador = GridSearchOrchestrator(config)
        melhor, todos = orquestrador.search(X, y, max_configs=2)

        assert melhor is not None
        assert len(todos) == 2

    def test_log_timing_orchestrator(self, dados_treino, caplog):
        """
        DADO GridSearchOrchestrator,
        QUANDO search() é chamado,
        ENTÃO o log deve registrar tempo de execução e n_jobs.
        """
        X, y = dados_treino
        config = GridSearchConfig(
            param_grid={},
            model_type=ModelType.XGBOOST,
            n_jobs=1
        )
        orquestrador = GridSearchOrchestrator(config)

        with caplog.at_level(logging.INFO, logger="src.application.ml_classifier"):
            orquestrador.search(X, y, max_configs=2)

        mensagens = " ".join(caplog.messages)
        assert "n_jobs=1" in mensagens, (
            "n_jobs deveria aparecer no log do GridSearchOrchestrator"
        )
