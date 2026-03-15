"""
AC6.8 - Online Learning Controlado - Testes Isolados

Suite de testes isolada que evita circular imports,
testando OnlineLearningController diretamente.
"""

import json
import pytest
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


# Importar diretamente o módulo para evitar circular imports
def _load_ac6_8_module():
    """Carrega modulo AC6.8 sem executar imports do projeto."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "ac6_8_online_learning",
        Path(__file__).parent.parent.parent / "src" / "application" / "ac6_8_online_learning.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def ac6_8_module():
    """Carrega modulo AC6.8 uma vez por sessao."""
    return _load_ac6_8_module()


@pytest.fixture
def temp_models_dir(tmp_path: Path) -> Path:
    """Cria diretorio temporario para modelos."""
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    return models_dir


@pytest.fixture
def sample_training_batch() -> List[Dict[str, Any]]:
    """Batch de dados para treino."""
    return [
        {
            "features": [1.5, 2.0, 3.5, 0.8, 1.2],
            "outcome": "WIN",
            "pnl": 150.0,
            "timestamp": datetime(2026, 3, 15, 10, 0),
        },
        {
            "features": [1.2, 2.5, 3.0, 0.6, 1.5],
            "outcome": "LOSS",
            "pnl": -100.0,
            "timestamp": datetime(2026, 3, 15, 10, 5),
        },
        {
            "features": [1.8, 2.2, 3.8, 0.9, 1.3],
            "outcome": "WIN",
            "pnl": 200.0,
            "timestamp": datetime(2026, 3, 15, 10, 10),
        },
        {
            "features": [1.3, 2.3, 3.2, 0.7, 1.4],
            "outcome": "WIN",
            "pnl": 175.0,
            "timestamp": datetime(2026, 3, 15, 10, 15),
        },
        {
            "features": [1.6, 2.4, 3.6, 0.8, 1.1],
            "outcome": "LOSS",
            "pnl": -120.0,
            "timestamp": datetime(2026, 3, 15, 10, 20),
        },
    ]


@pytest.fixture
def baseline_metrics() -> Dict[str, float]:
    """Baseline de metricas esperadas."""
    return {
        "win_rate": 0.65,
        "f1_score": 0.68,
        "sharpe_ratio": 1.2,
        "avg_pnl": 100.0,
    }


# ============================================================================
# TESTES DE TREINO INCREMENTAL
# ============================================================================


class TestTrainingIncremental:
    """Testes de treino incremental de modelo."""

    def test_train_incremental_basic(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
    ) -> None:
        """Treino incremental deve processar batch de dados."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="test_model",
            baseline_metrics={"win_rate": 0.65, "f1_score": 0.68},
        )

        result = controller.train_incremental(sample_training_batch)

        assert result is not None
        assert result.get("samples_trained") == len(sample_training_batch)
        assert "model_metrics" in result
        assert result["model_metrics"].get("win_rate") >= 0.0
        assert result["model_metrics"].get("win_rate") <= 1.0

    def test_train_incremental_updates_state(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
    ) -> None:
        """Treino deve atualizar estado interno do controller."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="test_model",
            baseline_metrics={"win_rate": 0.65},
        )

        assert controller.samples_trained == 0

        controller.train_incremental(sample_training_batch)
        assert controller.samples_trained == len(sample_training_batch)

    def test_train_incremental_empty_batch_handled(
        self,
        ac6_8_module,
    ) -> None:
        """Treino com batch vazio deve ser tratado."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="test_model",
            baseline_metrics={"win_rate": 0.65},
        )

        result = controller.train_incremental([])
        assert result["samples_trained"] == 0

    def test_train_incremental_calculates_metrics(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
    ) -> None:
        """Treino deve calcular metricas adequadamente."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="test_model",
            baseline_metrics={"win_rate": 0.65, "f1_score": 0.68},
        )

        result = controller.train_incremental(sample_training_batch)
        metrics = result["model_metrics"]

        # 3 wins, 2 losses = 60% win rate
        assert abs(metrics["win_rate"] - 0.6) < 0.01
        assert metrics["f1_score"] >= 0.0
        assert metrics["avg_pnl"] > 0  # Media positiva neste batch


# ============================================================================
# TESTES DE VALIDACAO
# ============================================================================


class TestModelValidation:
    """Testes de validacao de modelo contra baseline."""

    def test_validate_model_good_performance(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
        baseline_metrics: Dict[str, float],
    ) -> None:
        """Modelo com performance boa deve passar validacao."""
        conservative_baseline = {
            "win_rate": 0.50,
            "f1_score": 0.50,
        }

        controller = ac6_8_module.OnlineLearningController(
            model_name="test_model",
            baseline_metrics=conservative_baseline,
        )

        controller.train_incremental(sample_training_batch)
        validation = controller.validate_model(sample_training_batch)

        assert validation["is_valid"] is True
        assert "metrics" in validation
        assert "comparison" in validation

    def test_validate_model_degradation_detected(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
    ) -> None:
        """Modelo com degradacao deve ser detectado."""
        strict_baseline = {
            "win_rate": 0.95,
            "f1_score": 0.95,
        }

        controller = ac6_8_module.OnlineLearningController(
            model_name="test_model",
            baseline_metrics=strict_baseline,
        )

        controller.train_incremental(sample_training_batch)
        validation = controller.validate_model(
            sample_training_batch,
            threshold_zscore=0.2,  # Threshold mais sensivel para detectar queda
        )

        # Com baseline 95% e metricas reais ~60%, deve falhar
        assert validation["is_valid"] is False

    def test_validate_model_returns_comparison_metrics(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
        baseline_metrics: Dict[str, float],
    ) -> None:
        """Validacao deve retornar comparacao clara."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="test_model",
            baseline_metrics=baseline_metrics,
        )

        controller.train_incremental(sample_training_batch)
        validation = controller.validate_model(sample_training_batch)

        comparison = validation["comparison"]
        assert "win_rate" in comparison
        assert "baseline" in comparison["win_rate"]
        assert "current" in comparison["win_rate"]
        assert "delta" in comparison["win_rate"]


# ============================================================================
# TESTES DE PERSISTENCIA
# ============================================================================


class TestModelPersistence:
    """Testes de persistencia versionada de modelo."""

    def test_save_model_version_creates_file(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
        temp_models_dir: Path,
    ) -> None:
        """Salvar modelo deve criar arquivo de versao."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="test_model",
            baseline_metrics={"win_rate": 0.65},
            models_dir=str(temp_models_dir),
        )

        controller.train_incremental(sample_training_batch)
        version_id = controller.save_model_version(
            training_data=sample_training_batch,
            description="Test version 1",
        )

        assert version_id is not None
        version_file = temp_models_dir / f"{version_id}.json"
        assert version_file.exists()

    def test_save_model_version_generates_semver(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
        temp_models_dir: Path,
    ) -> None:
        """Versao deve seguir semantic versioning."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="model",
            baseline_metrics={"win_rate": 0.65},
            models_dir=str(temp_models_dir),
        )

        v1 = controller.save_model_version(sample_training_batch)
        assert v1.startswith("v1.0.")

        v2 = controller.save_model_version(sample_training_batch)
        assert v2.startswith("v1.0.")
        assert v2 != v1  # Versoes diferentes

    def test_save_model_version_stores_metadata(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
        temp_models_dir: Path,
    ) -> None:
        """Versao deve armazenar metadados completos."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="test_model",
            baseline_metrics={"win_rate": 0.65},
            models_dir=str(temp_models_dir),
        )

        controller.train_incremental(sample_training_batch)
        version_id = controller.save_model_version(
            training_data=sample_training_batch,
            description="Test version",
        )

        version_file = temp_models_dir / f"{version_id}.json"
        with open(version_file, "r") as f:
            data = json.load(f)

        assert "version_id" in data
        assert "timestamp" in data
        assert "training_samples" in data
        assert data["training_samples"] == len(sample_training_batch)
        assert "baseline_metrics" in data

    def test_load_model_version_restores_state(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
        temp_models_dir: Path,
    ) -> None:
        """Carregar versao deve restaurar estado."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="test_model",
            baseline_metrics={"win_rate": 0.65},
            models_dir=str(temp_models_dir),
        )

        controller.train_incremental(sample_training_batch)
        version_id = controller.save_model_version(sample_training_batch)

        # Novo controller carrega versao
        controller2 = ac6_8_module.OnlineLearningController(
            model_name="test_model",
            baseline_metrics={"win_rate": 0.65},
            models_dir=str(temp_models_dir),
        )
        loaded = controller2.load_model_version(version_id)

        assert loaded is not None
        assert loaded["version_id"] == version_id
        assert loaded["training_samples"] == len(sample_training_batch)


# ============================================================================
# TESTES DE ROLLBACK
# ============================================================================


class TestRollback:
    """Testes de rollback automatico por degradacao."""

    def test_rollback_detects_degradation(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
        temp_models_dir: Path,
    ) -> None:
        """Rollback deve detectar degradacao."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="test_model",
            baseline_metrics={"win_rate": 0.65},
            models_dir=str(temp_models_dir),
        )

        controller.train_incremental(sample_training_batch)
        version_id = controller.save_model_version(sample_training_batch)

        # Criar batch ruim (100% loss)
        bad_batch = [
            {
                "features": [1.0, 1.0, 1.0, 1.0, 1.0],
                "outcome": "LOSS",
                "pnl": -500.0,
                "timestamp": datetime.now(),
            },
        ]

        result = controller.rollback_on_degradation(
            new_batch=bad_batch,
            previous_version=version_id,
            win_rate_threshold=0.50,
        )

        assert result["degradation_detected"] is True
        assert result["rollback_performed"] is True

    def test_rollback_restores_previous_version(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
        temp_models_dir: Path,
    ) -> None:
        """Rollback deve restaurar versao anterior."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="test_model",
            baseline_metrics={"win_rate": 0.65},
            models_dir=str(temp_models_dir),
        )

        controller.train_incremental(sample_training_batch)
        v1 = controller.save_model_version(sample_training_batch)

        bad_batch = [
            {
                "features": [1.0, 1.0, 1.0, 1.0, 1.0],
                "outcome": "LOSS",
                "pnl": -500.0,
                "timestamp": datetime.now(),
            },
        ]

        result = controller.rollback_on_degradation(
            new_batch=bad_batch,
            previous_version=v1,
            win_rate_threshold=0.50,
        )

        # Versao restaurada deve ser a anterior
        assert result["restored_version"] == v1

    def test_no_rollback_if_good_performance(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
        temp_models_dir: Path,
    ) -> None:
        """Rollback nao deve ocorrer se performance boa."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="test_model",
            baseline_metrics={"win_rate": 0.65},
            models_dir=str(temp_models_dir),
        )

        controller.train_incremental(sample_training_batch)
        v1 = controller.save_model_version(sample_training_batch)

        # Novo batch bom (mais wins)
        good_batch = sample_training_batch  # Mesma performance

        result = controller.rollback_on_degradation(
            new_batch=good_batch,
            previous_version=v1,
            win_rate_threshold=0.40,  # Threshold baixo
        )

        assert result["degradation_detected"] is False
        assert result["rollback_performed"] is False


# ============================================================================
# TESTES DE METRICAS
# ============================================================================


class TestMetrics:
    """Testes de calculo de metricas."""

    def test_calculate_metrics_win_rate(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
    ) -> None:
        """Calculo de win rate deve ser exato."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="test",
            baseline_metrics={"win_rate": 0.65},
        )

        result = controller.train_incremental(sample_training_batch)
        metrics = result["model_metrics"]

        # 3 wins, 2 losses = 60%
        assert abs(metrics["win_rate"] - 0.60) < 0.01

    def test_calculate_metrics_avg_pnl(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
    ) -> None:
        """Calculo de PnL medio deve ser exato."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="test",
            baseline_metrics={"win_rate": 0.65},
        )

        result = controller.train_incremental(sample_training_batch)
        metrics = result["model_metrics"]

        # (150 - 100 + 200 + 175 - 120) / 5 = 305 / 5 = 61
        expected_avg = (150 - 100 + 200 + 175 - 120) / 5
        assert abs(metrics["avg_pnl"] - expected_avg) < 1

    def test_calculate_metrics_f1_score(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
    ) -> None:
        """Calculo de F1 score deve estar entre 0 e 1."""
        controller = ac6_8_module.OnlineLearningController(
            model_name="test",
            baseline_metrics={"win_rate": 0.65},
        )

        result = controller.train_incremental(sample_training_batch)
        metrics = result["model_metrics"]

        assert 0.0 <= metrics["f1_score"] <= 1.0


# ============================================================================
# TESTES INTEGRACAO
# ============================================================================


class TestIntegration:
    """Testes de integracao completa."""

    def test_full_training_workflow(
        self,
        ac6_8_module,
        sample_training_batch: List[Dict[str, Any]],
        temp_models_dir: Path,
    ) -> None:
        """Fluxo completo: treino -> save -> load -> rollback."""
        # 1. Criar controller e treinar
        controller = ac6_8_module.OnlineLearningController(
            model_name="full_test",
            baseline_metrics={"win_rate": 0.65},
            models_dir=str(temp_models_dir),
        )

        result = controller.train_incremental(sample_training_batch)
        assert result["samples_trained"] > 0

        # 2. Validar modelo
        validation = controller.validate_model(sample_training_batch)
        assert "metrics" in validation

        # 3. Salvar versao
        version_id = controller.save_model_version(sample_training_batch)
        assert version_id is not None

        # 4. Carregar versao nova
        controller2 = ac6_8_module.OnlineLearningController(
            model_name="full_test",
            baseline_metrics={"win_rate": 0.65},
            models_dir=str(temp_models_dir),
        )
        loaded = controller2.load_model_version(version_id)
        assert loaded["version_id"] == version_id

        # 5. Testar rollback
        bad_batch = [
            {
                "features": [1.0, 1.0, 1.0, 1.0, 1.0],
                "outcome": "LOSS",
                "pnl": -500.0,
                "timestamp": datetime.now(),
            },
        ]

        rollback = controller2.rollback_on_degradation(
            new_batch=bad_batch,
            previous_version=version_id,
            win_rate_threshold=0.50,
        )

        assert rollback["restored_version"] == version_id
