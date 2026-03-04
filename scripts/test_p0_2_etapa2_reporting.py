"""
Integration Tests for Etapa 2 - Reporting & Validation (P0-2 Backtest).

Testa:
1. BacktestReporter: Geração de HTML com 20+ seções
2. BacktestVisualizer: Criação de gráficos SVG
3. BacktestValidator: Validação GATE 2 criteria (4 bloqueadores)
4. E2E Integration: Reporter → Visualizer → Validator flow
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_backtest_results() -> Dict[str, Any]:
    """Cria resultados simulados de backtest para testes."""
    return {
        "summary": {
            "mean_sharpe": 1.15,  # PASS (target >= 1.0)
            "mean_win_rate": 0.62,  # PASS (target >= 0.59)
            "mean_max_drawdown": 0.12,  # PASS (target < 0.15)
            "mean_monthly_consistency": 0.25,  # PASS (target < 0.30)
            "mean_sortino_ratio": 1.45,
            "mean_profit_factor": 1.85,
            "mean_recovery_factor": 8.5,
            "mean_expectancy": 125.50,
            "total_pnl": 6250.0,  # Ganho de R$ 6.250 em R$ 50k
        },
        "folds": [
            {
                "fold_id": 0,
                "sharpe_ratio": 1.10,
                "win_rate": 0.61,
                "max_drawdown": 0.11,
                "total_trades": 750,
                "winning_trades": 458,
                "avg_return": 0.015,
                "pnl_total": 1200.0,
                "pnl_monthly_std": 0.24,
                "sortino_ratio": 1.40,
                "recovery_factor": 8.2,
                "hurst_exponent": 0.55,
                "monthly_consistency": 0.24,
            },
            {
                "fold_id": 1,
                "sharpe_ratio": 1.18,
                "win_rate": 0.63,
                "max_drawdown": 0.13,
                "total_trades": 760,
                "winning_trades": 479,
                "avg_return": 0.016,
                "pnl_total": 1300.0,
                "pnl_monthly_std": 0.26,
                "sortino_ratio": 1.50,
                "recovery_factor": 8.8,
                "hurst_exponent": 0.54,
                "monthly_consistency": 0.25,
            },
            {
                "fold_id": 2,
                "sharpe_ratio": 1.12,
                "win_rate": 0.61,
                "max_drawdown": 0.12,
                "total_trades": 755,
                "winning_trades": 461,
                "avg_return": 0.015,
                "pnl_total": 1250.0,
                "pnl_monthly_std": 0.25,
                "sortino_ratio": 1.42,
                "recovery_factor": 8.4,
                "hurst_exponent": 0.55,
                "monthly_consistency": 0.24,
            },
            {
                "fold_id": 3,
                "sharpe_ratio": 1.20,
                "win_rate": 0.64,
                "max_drawdown": 0.11,
                "total_trades": 770,
                "winning_trades": 493,
                "avg_return": 0.017,
                "pnl_total": 1350.0,
                "pnl_monthly_std": 0.23,
                "sortino_ratio": 1.52,
                "recovery_factor": 9.0,
                "hurst_exponent": 0.54,
                "monthly_consistency": 0.23,
            },
            {
                "fold_id": 4,
                "sharpe_ratio": 1.16,
                "win_rate": 0.62,
                "max_drawdown": 0.12,
                "total_trades": 745,
                "winning_trades": 462,
                "avg_return": 0.015,
                "pnl_total": 1150.0,
                "pnl_monthly_std": 0.26,
                "sortino_ratio": 1.44,
                "recovery_factor": 8.3,
                "hurst_exponent": 0.55,
                "monthly_consistency": 0.26,
            },
        ],
    }


@pytest.fixture
def sample_failed_backtest_results() -> Dict[str, Any]:
    """Cria resultados falhados (para testar NO GATE 2 PASS)."""
    return {
        "summary": {
            "mean_sharpe": 0.85,  # FAIL (need >= 1.0)
            "mean_win_rate": 0.52,  # FAIL (need >= 0.59)
            "mean_max_drawdown": 0.20,  # FAIL (need < 0.15)
            "mean_monthly_consistency": 0.45,  # FAIL (need < 0.30)
            "mean_sortino_ratio": 0.95,
            "mean_profit_factor": 1.10,
            "mean_recovery_factor": 4.5,
            "mean_expectancy": 50.0,
            "total_pnl": 2000.0,
        },
        "folds": [
            {
                "fold_id": 0,
                "sharpe_ratio": 0.80,
                "win_rate": 0.50,
                "max_drawdown": 0.22,
                "total_trades": 800,
                "winning_trades": 400,
                "avg_return": 0.010,
                "pnl_total": 400.0,
                "pnl_monthly_std": 0.40,
                "sortino_ratio": 0.90,
                "recovery_factor": 4.0,
                "hurst_exponent": 0.50,
                "monthly_consistency": 0.42,
            },
            {
                "fold_id": 1,
                "sharpe_ratio": 0.90,
                "win_rate": 0.55,
                "max_drawdown": 0.18,
                "total_trades": 810,
                "winning_trades": 445,
                "avg_return": 0.011,
                "pnl_total": 500.0,
                "pnl_monthly_std": 0.45,
                "sortino_ratio": 1.00,
                "recovery_factor": 4.8,
                "hurst_exponent": 0.52,
                "monthly_consistency": 0.48,
            },
            {
                "fold_id": 2,
                "sharpe_ratio": 0.82,
                "win_rate": 0.51,
                "max_drawdown": 0.21,
                "total_trades": 805,
                "winning_trades": 410,
                "avg_return": 0.010,
                "pnl_total": 420.0,
                "pnl_monthly_std": 0.42,
                "sortino_ratio": 0.92,
                "recovery_factor": 4.2,
                "hurst_exponent": 0.50,
                "monthly_consistency": 0.44,
            },
            {
                "fold_id": 3,
                "sharpe_ratio": 0.88,
                "win_rate": 0.53,
                "max_drawdown": 0.20,
                "total_trades": 815,
                "winning_trades": 432,
                "avg_return": 0.010,
                "pnl_total": 480.0,
                "pnl_monthly_std": 0.44,
                "sortino_ratio": 0.98,
                "recovery_factor": 4.6,
                "hurst_exponent": 0.51,
                "monthly_consistency": 0.46,
            },
            {
                "fold_id": 4,
                "sharpe_ratio": 0.83,
                "win_rate": 0.52,
                "max_drawdown": 0.19,
                "total_trades": 795,
                "winning_trades": 413,
                "avg_return": 0.010,
                "pnl_total": 200.0,
                "pnl_monthly_std": 0.43,
                "sortino_ratio": 0.93,
                "recovery_factor": 4.1,
                "hurst_exponent": 0.50,
                "monthly_consistency": 0.43,
            },
        ],
    }


# ============================================================================
# TESTS - BacktestReporter (AC7: Relatório gerado com gráficos)
# ============================================================================


class TestBacktestReporter:
    """Testa geração de relatórios HTML."""

    def test_reporter_initialization(self) -> None:
        """Testa inicialização do reporter."""
        from src.infrastructure.reports.backtest_reporter import (
            BacktestReporter,
            ReportConfig,
        )

        config = ReportConfig(title="Test Report")
        reporter = BacktestReporter(config)

        assert reporter.config.title == "Test Report"
        assert reporter.config.author == "ML Expert Team"

    def test_reporter_html_generation(
        self, sample_backtest_results: Dict[str, Any]
    ) -> None:
        """Testa geração de HTML com resultados reais."""
        from src.infrastructure.reports.backtest_reporter import BacktestReporter

        with tempfile.TemporaryDirectory() as tmpdir:
            # Salvar resultados de teste
            results_file = Path(tmpdir) / "backtest_results.json"
            with open(results_file, "w") as f:
                json.dump(sample_backtest_results, f)

            # Gerar relatório
            reporter = BacktestReporter()
            html = reporter.generate_html(
                str(results_file), str(Path(tmpdir) / "report.html")
            )

            # Validações
            assert html is not None
            assert "<!DOCTYPE html>" in html
            assert "Sumário Executivo" in html
            assert "Sharpe Ratio" in html
            assert "Win Rate" in html
            assert "Max Drawdown" in html
            assert "Consistência" in html

    def test_reporter_gate2_pass_status(
        self, sample_backtest_results: Dict[str, Any]
    ) -> None:
        """Testa status PASS no relatório (todos critérios OK)."""
        from src.infrastructure.reports.backtest_reporter import BacktestReporter

        with tempfile.TemporaryDirectory() as tmpdir:
            results_file = Path(tmpdir) / "backtest_results.json"
            with open(results_file, "w") as f:
                json.dump(sample_backtest_results, f)

            reporter = BacktestReporter()
            html = reporter.generate_html(str(results_file), str(Path(tmpdir) / "report.html"))

            # Verificar status PASS
            assert "PASS ✓" in html or "pass" in html.lower()
            assert "Escalar para R$ 100k" in html

    def test_reporter_gate2_fail_status(
        self, sample_failed_backtest_results: Dict[str, Any]
    ) -> None:
        """Testa status FAIL no relatório (critérios não atendidos)."""
        from src.infrastructure.reports.backtest_reporter import BacktestReporter

        with tempfile.TemporaryDirectory() as tmpdir:
            results_file = Path(tmpdir) / "backtest_results.json"
            with open(results_file, "w") as f:
                json.dump(sample_failed_backtest_results, f)

            reporter = BacktestReporter()
            html = reporter.generate_html(str(results_file), str(Path(tmpdir) / "report.html"))

            # Verificar status FAIL
            assert "FAIL ✗" in html or "fail" in html.lower()
            assert "Manter em R$ 50k" in html


# ============================================================================
# TESTS - BacktestVisualizer (Charts)
# ============================================================================


class TestBacktestVisualizer:
    """Testa geração de visualizações SVG."""

    def test_visualizer_initialization(self) -> None:
        """Testa inicialização do visualizer."""
        from src.infrastructure.reports.backtest_visualizer import (
            BacktestVisualizer,
            ChartConfig,
        )

        config = ChartConfig(figsize=(14, 8))
        viz = BacktestVisualizer(config)

        assert viz.config.figsize == (14, 8)
        assert viz.config.dpi == 100

    def test_visualizer_charts_generation(
        self, sample_backtest_results: Dict[str, Any]
    ) -> None:
        """Testa geração de gráficos SVG."""
        from src.infrastructure.reports.backtest_visualizer import BacktestVisualizer

        with tempfile.TemporaryDirectory() as tmpdir:
            results_file = Path(tmpdir) / "backtest_results.json"
            with open(results_file, "w") as f:
                json.dump(sample_backtest_results, f)

            viz = BacktestVisualizer()
            charts = viz.generate_all_charts(str(results_file), str(Path(tmpdir) / "charts"))

            # Validacoes
            assert "equity_curve" in charts
            assert "drawdown_heatmap" in charts
            assert "win_rate_bars" in charts
            assert all(Path(path).exists() for path in charts.values())

    def test_visualizer_equity_curve_svg(
        self, sample_backtest_results: Dict[str, Any]
    ) -> None:
        """Testa geração específica de SVG equity curve."""
        from src.infrastructure.reports.backtest_visualizer import BacktestVisualizer

        with tempfile.TemporaryDirectory() as tmpdir:
            results_file = Path(tmpdir) / "backtest_results.json"
            with open(results_file, "w") as f:
                json.dump(sample_backtest_results, f)

            viz = BacktestVisualizer()
            viz.generate_all_charts(str(results_file), str(Path(tmpdir) / "charts"))

            # Verificar conteúdo SVG
            equity_svg = viz.get_chart("equity_curve")
            assert "<svg" in equity_svg
            assert "Patrimônio" in equity_svg


# ============================================================================
# TESTS - BacktestValidator (AC8: Validação GATE 2)
# ============================================================================


class TestBacktestValidator:
    """Testa validação de critérios GATE 2."""

    def test_validator_initialization(self) -> None:
        """Testa inicialização do validator."""
        from src.infrastructure.validators.backtest_validator import (
            BacktestValidator,
            GateCriteria,
        )

        criteria = GateCriteria(sharpe_target=1.2)
        validator = BacktestValidator(criteria)

        assert validator.criteria.sharpe_target == 1.2
        assert validator.criteria.win_rate_target == 0.59

    def test_validator_pass_all_criteria(
        self, sample_backtest_results: Dict[str, Any]
    ) -> None:
        """Testa validação com TODOS os critérios atendidos (PASS)."""
        from src.infrastructure.validators.backtest_validator import (
            BacktestValidator,
            GateDecision,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            results_file = Path(tmpdir) / "backtest_results.json"
            with open(results_file, "w") as f:
                json.dump(sample_backtest_results, f)

            validator = BacktestValidator()
            decision = validator.validate(str(results_file))

            assert decision == GateDecision.PASS
            assert all(vr.passed for vr in validator.validation_results)

    def test_validator_fail_criteria(
        self, sample_failed_backtest_results: Dict[str, Any]
    ) -> None:
        """Testa validação com critérios não atendidos (FAIL)."""
        from src.infrastructure.validators.backtest_validator import (
            BacktestValidator,
            GateDecision,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            results_file = Path(tmpdir) / "backtest_results.json"
            with open(results_file, "w") as f:
                json.dump(sample_failed_backtest_results, f)

            validator = BacktestValidator()
            decision = validator.validate(str(results_file))

            assert decision == GateDecision.FAIL
            assert not all(vr.passed for vr in validator.validation_results)

    def test_validator_report_generation(
        self, sample_backtest_results: Dict[str, Any]
    ) -> None:
        """Testa geração de relatório de validação."""
        from src.infrastructure.validators.backtest_validator import BacktestValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            results_file = Path(tmpdir) / "backtest_results.json"
            with open(results_file, "w") as f:
                json.dump(sample_backtest_results, f)

            validator = BacktestValidator()
            validator.validate(str(results_file))

            report = validator.get_validation_report()
            assert "GATE 2" in report
            assert "DECISION" in report
            assert "Sharpe Ratio" in report

    def test_validator_decision_json(
        self, sample_backtest_results: Dict[str, Any]
    ) -> None:
        """Testa formato JSON da decisão (para automação)."""
        from src.infrastructure.validators.backtest_validator import BacktestValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            results_file = Path(tmpdir) / "backtest_results.json"
            with open(results_file, "w") as f:
                json.dump(sample_backtest_results, f)

            validator = BacktestValidator()
            validator.validate(str(results_file))

            decision_json = validator.get_decision_json()
            assert "decision" in decision_json
            assert "criteria" in decision_json
            assert "all_passed" in decision_json
            assert decision_json["decision"] == "PASS"


# ============================================================================
# TESTS - E2E Integration (Full Flow)
# ============================================================================


class TestEtoEIntegration:
    """Testa fluxo completo: Reporter → Visualizer → Validator."""

    def test_complete_pipeline_pass(
        self, sample_backtest_results: Dict[str, Any]
    ) -> None:
        """Testa pipeline completo com resultados PASS."""
        from src.infrastructure.reports.backtest_reporter import BacktestReporter
        from src.infrastructure.reports.backtest_visualizer import BacktestVisualizer
        from src.infrastructure.validators.backtest_validator import (
            BacktestValidator,
            GateDecision,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            results_file = Path(tmpdir) / "backtest_results.json"
            with open(results_file, "w") as f:
                json.dump(sample_backtest_results, f)

            # 1. Reporter: Gerar HTML
            reporter = BacktestReporter()
            reporter.generate_html(
                str(results_file), str(Path(tmpdir) / "report.html")
            )
            assert (Path(tmpdir) / "report.html").exists()

            # 2. Visualizer: Gerar gráficos
            viz = BacktestVisualizer()
            charts = viz.generate_all_charts(str(results_file), str(Path(tmpdir) / "charts"))
            assert len(charts) == 3

            # 3. Validator: Validar GATE 2
            validator = BacktestValidator()
            decision = validator.validate(str(results_file))
            assert decision == GateDecision.PASS

    def test_complete_pipeline_fail(
        self, sample_failed_backtest_results: Dict[str, Any]
    ) -> None:
        """Testa pipeline completo com resultados FAIL."""
        from src.infrastructure.reports.backtest_reporter import BacktestReporter
        from src.infrastructure.reports.backtest_visualizer import BacktestVisualizer
        from src.infrastructure.validators.backtest_validator import (
            BacktestValidator,
            GateDecision,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            results_file = Path(tmpdir) / "backtest_results.json"
            with open(results_file, "w") as f:
                json.dump(sample_failed_backtest_results, f)

            # 1. Reporter: Gerar HTML
            reporter = BacktestReporter()
            reporter.generate_html(str(results_file), str(Path(tmpdir) / "report.html"))
            assert (Path(tmpdir) / "report.html").exists()

            # 2. Visualizer: Gerar gráficos
            viz = BacktestVisualizer()
            charts = viz.generate_all_charts(str(results_file), str(Path(tmpdir) / "charts"))
            assert len(charts) == 3

            # 3. Validator: Validar GATE 2
            validator = BacktestValidator()
            decision = validator.validate(str(results_file))
            assert decision == GateDecision.FAIL
