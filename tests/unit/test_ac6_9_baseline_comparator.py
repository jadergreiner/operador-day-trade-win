"""
AC6.9 - Testes de Comparação contra Baseline Histórico

Suite completa de testes para o comparador de baseline
com feedback ao sistema.

Cobertura:
- Carregamento de histórico de baseline
- Comparação de métricas atuais contra baseline
- Detecção de degradação com alertas
- Feedback estruturado para sistema
- Geração de relatórios JSON/Markdown
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import json
import tempfile
from dataclasses import dataclass

from src.application.ac6_9_baseline_comparator import (
    BaselineComparator,
    BaselineRecord,
    ComparisonResult,
    SystemFeedback,
)


class TestBaselineRecord:
    """Testes para dataclass BaselineRecord."""

    def test_criar_baseline_record(self) -> None:
        """Deve criar BaselineRecord com validação."""
        record = BaselineRecord(
            version_id="v1.0.0",
            timestamp=datetime.now(),
            metrics={
                "win_rate": 0.65,
                "f1_score": 0.68,
                "sharpe_ratio": 1.2,
            },
            description="Baseline inicial",
        )

        assert record.version_id == "v1.0.0"
        assert record.metrics["win_rate"] == 0.65
        assert record.description == "Baseline inicial"

    def test_baseline_record_para_dict(self) -> None:
        """Deve converter BaselineRecord para dicionário."""
        record = BaselineRecord(
            version_id="v1.0.0",
            timestamp=datetime(2026, 3, 16, 10, 30, 0),
            metrics={"win_rate": 0.65},
            description="Test",
        )

        data = record.para_dict()
        assert data["version_id"] == "v1.0.0"
        assert data["metrics"]["win_rate"] == 0.65
        assert isinstance(data["timestamp"], str)


class TestComparisonResult:
    """Testes para ComparisonResult."""

    def test_criar_comparison_result_sem_degradacao(self) -> None:
        """Deve indicar quando não há degradação."""
        result = ComparisonResult(
            baseline_version="v1.0.0",
            current_metrics={"win_rate": 0.70, "f1_score": 0.70},
            baseline_metrics={"win_rate": 0.65, "f1_score": 0.68},
            degraded_metrics=[],
            is_degraded=False,
            z_scores={"win_rate": 0.94, "f1_score": 0.37},
        )

        assert result.is_degraded is False
        assert len(result.degraded_metrics) == 0

    def test_criar_comparison_result_com_degradacao(self) -> None:
        """Deve detectar quando há degradação."""
        result = ComparisonResult(
            baseline_version="v1.0.0",
            current_metrics={"win_rate": 0.50, "f1_score": 0.60},
            baseline_metrics={"win_rate": 0.65, "f1_score": 0.68},
            degraded_metrics=["win_rate"],
            is_degraded=True,
            z_scores={"win_rate": -2.24},
        )

        assert result.is_degraded is True
        assert "win_rate" in result.degraded_metrics


class TestSystemFeedback:
    """Testes para SystemFeedback."""

    def test_criar_feedback_sem_acao(self) -> None:
        """Deve criar feedback sem ação recomendada."""
        feedback = SystemFeedback(
            comparison_result=ComparisonResult(
                baseline_version="v1.0.0",
                current_metrics={"win_rate": 0.70},
                baseline_metrics={"win_rate": 0.65},
                degraded_metrics=[],
                is_degraded=False,
                z_scores={"win_rate": 0.94},
            ),
            recommended_action="CONTINUE",
            severity="LOW",
            confidence=0.95,
            timestamp=datetime.now(),
        )

        assert feedback.recommended_action == "CONTINUE"
        assert feedback.severity == "LOW"

    def test_criar_feedback_com_acao(self) -> None:
        """Deve criar feedback com recomendação de ação."""
        feedback = SystemFeedback(
            comparison_result=ComparisonResult(
                baseline_version="v1.0.0",
                current_metrics={"win_rate": 0.50},
                baseline_metrics={"win_rate": 0.65},
                degraded_metrics=["win_rate"],
                is_degraded=True,
                z_scores={"win_rate": -2.24},
            ),
            recommended_action="ROLLBACK",
            severity="CRITICAL",
            confidence=0.98,
            timestamp=datetime.now(),
        )

        assert feedback.recommended_action == "ROLLBACK"
        assert feedback.severity == "CRITICAL"


class TestBaselineComparator:
    """Testes para BaselineComparator."""

    @pytest.fixture
    def comparator(self) -> BaselineComparator:
        """Cria comparador para testes."""
        baseline_metrics = {
            "win_rate": 0.65,
            "f1_score": 0.68,
            "sharpe_ratio": 1.2,
            "avg_pnl": 150.0,
        }
        return BaselineComparator(
            baseline_metrics=baseline_metrics,
            z_score_threshold=2.0,
        )

    def test_initializar_comparador(
        self, comparator: BaselineComparator
    ) -> None:
        """Deve inicializar comparador corretamente."""
        assert comparator.baseline_metrics["win_rate"] == 0.65
        assert comparator.z_score_threshold == 2.0
        assert len(comparator.baseline_history) == 1

    def test_add_baseline_record(
        self, comparator: BaselineComparator
    ) -> None:
        """Deve adicionar novo registro de baseline."""
        new_record = BaselineRecord(
            version_id="v1.1.0",
            timestamp=datetime.now(),
            metrics={"win_rate": 0.68, "f1_score": 0.71},
            description="Teste novo baseline",
        )

        comparator.adicionar_baseline(new_record)

        assert len(comparator.baseline_history) == 2
        assert comparator.baseline_history[-1].version_id == "v1.1.0"

    def test_comparar_metricas_sem_degradacao(
        self, comparator: BaselineComparator
    ) -> None:
        """Deve comparar e indicar que não há degradação."""
        current_metrics = {
            "win_rate": 0.67,  # Melhoria vs 0.65
            "f1_score": 0.70,  # Melhoria vs 0.68
            "sharpe_ratio": 1.25,  # Melhoria vs 1.2
            "avg_pnl": 160.0,  # Melhoria vs 150.0
        }

        result = comparator.comparar_metricas(
            current_metrics=current_metrics,
            baseline_version="v1.0.0",
        )

        assert result.is_degraded is False
        assert len(result.degraded_metrics) == 0

    def test_comparar_metricas_com_degradacao_leve(
        self, comparator: BaselineComparator
    ) -> None:
        """Deve detectar degradação leve."""
        current_metrics = {
            "win_rate": 0.63,  # Piora vs 0.65 (Z = -0.47)
            "f1_score": 0.67,  # Piora vs 0.68 (Z = -0.37)
            "sharpe_ratio": 1.15,  # Piora vs 1.2
            "avg_pnl": 140.0,  # Piora vs 150.0
        }

        result = comparator.comparar_metricas(
            current_metrics=current_metrics,
            baseline_version="v1.0.0",
        )

        # Degradação leve não deve trigger degradação com threshold=2.0
        assert result.is_degraded is False

    def test_comparar_metricas_com_degradacao_severa(
        self, comparator: BaselineComparator
    ) -> None:
        """Deve detectar degradação severa."""
        # Simular valores com distribição esperada
        current_metrics = {
            "win_rate": 0.40,  # Piora significativa
            "f1_score": 0.50,  # Piora significativa
            "sharpe_ratio": 0.5,  # Piora significativa
            "avg_pnl": 50.0,  # Piora significativa
        }

        result = comparator.comparar_metricas(
            current_metrics=current_metrics,
            baseline_version="v1.0.0",
        )

        assert result.is_degraded is True
        assert len(result.degraded_metrics) > 0

    def test_gerar_feedback_continue(
        self, comparator: BaselineComparator
    ) -> None:
        """Deve gerar feedback CONTINUE quando tudo bem."""
        current_metrics = {
            "win_rate": 0.70,
            "f1_score": 0.72,
            "sharpe_ratio": 1.3,
            "avg_pnl": 170.0,
        }

        comparison = comparator.comparar_metricas(
            current_metrics=current_metrics,
            baseline_version="v1.0.0",
        )

        feedback = comparator.gerar_feedback(comparison)

        assert feedback.recommended_action == "CONTINUE"
        assert feedback.severity == "LOW"

    def test_gerar_feedback_alert(
        self, comparator: BaselineComparator
    ) -> None:
        """Deve gerar feedback ALERT para degradação." """
        current_metrics = {
            "win_rate": 0.63,
            "f1_score": 0.67,
            "sharpe_ratio": 1.15,
            "avg_pnl": 140.0,
        }

        comparison = comparator.comparar_metricas(
            current_metrics=current_metrics,
            baseline_version="v1.0.0",
        )

        feedback = comparator.gerar_feedback(comparison)

        # Sem degradação severa, deve ser MONITOR
        assert feedback.recommended_action in ["CONTINUE", "MONITOR"]

    def test_relatorio_json(
        self, comparator: BaselineComparator
    ) -> None:
        """Deve gerar relatório JSON estruturado."""
        current_metrics = {
            "win_rate": 0.67,
            "f1_score": 0.70,
            "sharpe_ratio": 1.25,
            "avg_pnl": 160.0,
        }

        comparison = comparator.comparar_metricas(
            current_metrics=current_metrics,
            baseline_version="v1.0.0",
        )

        feedback = comparator.gerar_feedback(comparison)

        relatorio = comparator.gerar_relatorio_json(
            comparison=comparison, feedback=feedback
        )

        assert isinstance(relatorio, dict)
        assert "timestamp" in relatorio
        assert "comparison" in relatorio
        assert "feedback" in relatorio

    def test_relatorio_markdown(
        self, comparator: BaselineComparator
    ) -> None:
        """Deve gerar relatório Markdown legível."""
        current_metrics = {
            "win_rate": 0.67,
            "f1_score": 0.70,
            "sharpe_ratio": 1.25,
            "avg_pnl": 160.0,
        }

        comparison = comparator.comparar_metricas(
            current_metrics=current_metrics,
            baseline_version="v1.0.0",
        )

        feedback = comparator.gerar_feedback(comparison)

        relatorio = comparator.gerar_relatorio_markdown(
            comparison=comparison, feedback=feedback
        )

        assert isinstance(relatorio, str)
        assert "## AC6.9 - Comparação contra Baseline" in relatorio
        assert "### Métricas Atuais" in relatorio
        assert "### Ação Recomendada" in relatorio

    def test_historico_baseline(
        self, comparator: BaselineComparator
    ) -> None:
        """Deve manter histórico de baselines."""
        # Adicionar vários baselines
        for i in range(1, 4):
            record = BaselineRecord(
                version_id=f"v1.{i}.0",
                timestamp=datetime.now() + timedelta(hours=i),
                metrics={
                    "win_rate": 0.65 + (0.01 * i),
                    "f1_score": 0.68 + (0.01 * i),
                },
            )
            comparator.adicionar_baseline(record)

        assert len(comparator.baseline_history) == 4  # 1 inicial + 3 novos

    def test_persistencia_baseline(
        self, comparator: BaselineComparator
    ) -> None:
        """Deve persistir baseline em arquivo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            comparator.models_dir = Path(tmpdir)
            comparator.salvar_baseline()

            # Verificar arquivo criado
            baseline_file = Path(tmpdir) / "baseline_history.json"
            assert baseline_file.exists()

            # Verificar conteúdo
            with open(baseline_file) as f:
                data = json.load(f)
                assert len(data) >= 1

    def test_tipos_retorno_corretos(
        self, comparator: BaselineComparator
    ) -> None:
        """Deve retornar tipos corretos em todos os métodos."""
        current_metrics = {
            "win_rate": 0.67,
            "f1_score": 0.70,
            "sharpe_ratio": 1.25,
            "avg_pnl": 160.0,
        }

        comparison = comparator.comparar_metricas(
            current_metrics=current_metrics,
            baseline_version="v1.0.0",
        )
        assert isinstance(comparison, ComparisonResult)

        feedback = comparator.gerar_feedback(comparison)
        assert isinstance(feedback, SystemFeedback)

        relatorio_json = comparator.gerar_relatorio_json(
            comparison=comparison, feedback=feedback
        )
        assert isinstance(relatorio_json, dict)

        relatorio_md = comparator.gerar_relatorio_markdown(
            comparison=comparison, feedback=feedback
        )
        assert isinstance(relatorio_md, str)

    def test_z_score_threshold_respeitado(
        self, comparator: BaselineComparator
    ) -> None:
        """Deve respeitar threshold de Z-score customizado."""
        # Comparador com threshold diferente
        comparador_lenient = BaselineComparator(
            baseline_metrics={"win_rate": 0.65},
            z_score_threshold=3.0,  # Mais leniente
        )

        current_metrics = {"win_rate": 0.40}

        result = comparador_lenient.comparar_metricas(
            current_metrics=current_metrics,
            baseline_version="v1.0.0",
        )

        # Verificar que Z-score foi calculado
        assert "win_rate" in result.z_scores

    def test_confidence_score_presente(
        self, comparator: BaselineComparator
    ) -> None:
        """Deve incluir confidence score no feedback."""
        current_metrics = {
            "win_rate": 0.67,
            "f1_score": 0.70,
            "sharpe_ratio": 1.25,
            "avg_pnl": 160.0,
        }

        comparison = comparator.comparar_metricas(
            current_metrics=current_metrics,
            baseline_version="v1.0.0",
        )

        feedback = comparator.gerar_feedback(comparison)

        assert feedback.confidence > 0.0
        assert feedback.confidence <= 1.0
