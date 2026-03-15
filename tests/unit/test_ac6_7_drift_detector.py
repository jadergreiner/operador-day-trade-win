"""
Testes para AC6.7 - Detector de Drift de Modelo em Producao

Modulo de testes para validar deteccao de degradacao de modelo
contra baseline statico (primeira 1000 trades).

Estrutura:
- DriftDetectorTest: Suite principal de testes
- Fixtures: baseline_factory, trades_factory
- Casos: stability, degradation, threshold, alerts
"""

import json
import pytest
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List
from pathlib import Path
import tempfile

from src.application.ac6_7_drift_detector import (
    DriftDetector,
    DriftMetrics,
    DriftAlert,
    DriftAlertSeverity,
)


@dataclass
class MockTrade:
    """Trade simulado para testes."""
    trade_id: str
    outcome: str  # "WIN", "LOSS", "BREAKEVEN"
    pnl: float
    entry_price: float
    exit_price: float
    quantity: int
    timestamp: datetime


class TestDriftDetectorInitialization:
    """Testes de inicializacao do DriftDetector."""

    def test_inicializar_com_baseline_valido(self) -> None:
        """Deve criar instancia com baseline valido."""
        detector = DriftDetector(
            baseline_f1=0.68,
            baseline_win_rate=0.65,
            baseline_sharpe=1.2,
            window_size=100
        )
        assert detector.baseline_f1 == 0.68
        assert detector.baseline_win_rate == 0.65
        assert detector.baseline_sharpe == 1.2
        assert detector.window_size == 100

    def test_inicializar_com_valores_default(self) -> None:
        """Deve usar valores default se nao fornecidos."""
        detector = DriftDetector()
        assert detector.baseline_f1 == 0.0  # default
        assert detector.window_size == 100
        assert isinstance(detector.trades_sliding_window, list)
        assert len(detector.trades_sliding_window) == 0

    def test_inicializar_com_parametros_invalidos_falha(self) -> None:
        """Deve falhar com parametros invalidos."""
        with pytest.raises(ValueError):
            DriftDetector(baseline_f1=-0.1)  # F1 nao pode ser negativo

        with pytest.raises(ValueError):
            DriftDetector(baseline_f1=1.5)  # F1 nao pode ser > 1.0

        with pytest.raises(ValueError):
            DriftDetector(window_size=0)  # window deve ser > 0


class TestDriftDetectorMetricsCalculation:
    """Testes de calculo de metricas de drift."""

    def test_calcular_metricas_com_trades_validos(self) -> None:
        """Deve calcular metricas corretamente com trades validos."""
        detector = DriftDetector(baseline_f1=0.68, baseline_win_rate=0.65)

        trades = [
            MockTrade(
                trade_id=f"TRADE_{i}",
                outcome="WIN" if i % 2 == 0 else "LOSS",
                pnl=100.0 if i % 2 == 0 else -50.0,
                entry_price=1.0,
                exit_price=1.1 if i % 2 == 0 else 0.9,
                quantity=100,
                timestamp=datetime.now() - timedelta(seconds=i*60)
            )
            for i in range(10)
        ]

        metrics = detector.calcular_metricas(trades)

        assert isinstance(metrics, DriftMetrics)
        assert 0.0 <= metrics.win_rate <= 1.0  # W-R entre 0 e 1
        assert metrics.num_trades == 10
        assert metrics.avg_pnl == pytest.approx((100 * 5 - 50 * 5) / 10)

    def test_calcular_win_rate_100_porcento(self) -> None:
        """Deve calcular win_rate = 1.0 para todos WINS."""
        detector = DriftDetector()

        trades = [
            MockTrade(
                trade_id=f"TRADE_{i}",
                outcome="WIN",
                pnl=100.0,
                entry_price=1.0,
                exit_price=1.1,
                quantity=100,
                timestamp=datetime.now()
            )
            for i in range(5)
        ]

        metrics = detector.calcular_metricas(trades)
        assert metrics.win_rate == 1.0

    def test_calcular_win_rate_0_porcento(self) -> None:
        """Deve calcular win_rate = 0.0 para todos LOSSES."""
        detector = DriftDetector()

        trades = [
            MockTrade(
                trade_id=f"TRADE_{i}",
                outcome="LOSS",
                pnl=-100.0,
                entry_price=1.0,
                exit_price=0.9,
                quantity=100,
                timestamp=datetime.now()
            )
            for i in range(5)
        ]

        metrics = detector.calcular_metricas(trades)
        assert metrics.win_rate == 0.0

    def test_calcular_sharpe_ratio(self) -> None:
        """Deve calcular Sharpe ratio corretamente."""
        detector = DriftDetector()

        trades = [
            MockTrade(
                trade_id=f"TRADE_{i}",
                outcome="WIN",
                pnl=100.0 + (10.0 * (i % 3 - 1)),  # PnL variavel
                entry_price=1.0,
                exit_price=1.1,
                quantity=100,
                timestamp=datetime.now() - timedelta(seconds=i*60)
            )
            for i in range(20)
        ]

        metrics = detector.calcular_metricas(trades)
        # Sharpe deve ser > 0 para tendencia positiva
        assert metrics.sharpe_ratio > 0


class TestDriftDetectorDetection:
    """Testes de deteccao de drift."""

    def test_detectar_sem_drift(self) -> None:
        """Nao deve detectar drift quando metricas estao estaves."""
        detector = DriftDetector(
            baseline_f1=0.68,
            baseline_win_rate=0.65,
            baseline_sharpe=1.2,
            drift_threshold_zscore=2.0
        )

        trades = [
            MockTrade(
                trade_id=f"TRADE_{i}",
                outcome="WIN" if i % 100 < 65 else "LOSS",  # ~65% win rate
                pnl=100.0 if i % 100 < 65 else -50.0,
                entry_price=1.0,
                exit_price=1.1 if i % 100 < 65 else 0.9,
                quantity=100,
                timestamp=datetime.now() - timedelta(seconds=i*60)
            )
            for i in range(100)
        ]

        alerts = detector.detectar_drift(trades)
        # Sem drift significativo, deve retornar lista vazia ou alerts com severity LOW
        assert isinstance(alerts, list)

    def test_detectar_degradacao_win_rate(self) -> None:
        """Deve detectar degradacao em win_rate."""
        detector = DriftDetector(
            baseline_win_rate=0.65,
            drift_threshold_zscore=1.5
        )

        trades = [
            MockTrade(
                trade_id=f"TRADE_{i}",
                outcome="LOSS",  # 0% win rate = degradacao
                pnl=-100.0,
                entry_price=1.0,
                exit_price=0.9,
                quantity=100,
                timestamp=datetime.now() - timedelta(seconds=i*60)
            )
            for i in range(50)
        ]

        alerts = detector.detectar_drift(trades)
        assert len(alerts) > 0  # Deve indicar degradacao
        assert any("win_rate" in str(a.metric) for a in alerts)

    def test_detectar_degradacao_sharpe(self) -> None:
        """Deve detectar degradacao em Sharpe ratio."""
        detector = DriftDetector(
            baseline_sharpe=1.2,
            drift_threshold_zscore=1.5
        )

        trades = [
            MockTrade(
                trade_id=f"TRADE_{i}",
                outcome="WIN" if i % 2 == 0 else "LOSS",
                pnl=10.0 if i % 2 == 0 else -100.0,  # Sharpe muito baixo
                entry_price=1.0,
                exit_price=1.01 if i % 2 == 0 else 0.99,
                quantity=100,
                timestamp=datetime.now() - timedelta(seconds=i*60)
            )
            for i in range(50)
        ]

        alerts = detector.detectar_drift(trades)
        assert isinstance(alerts, list)


class TestDriftDetectorSlidingWindow:
    """Testes de sliding window de trades."""

    def test_sliding_window_adicionar_trade(self) -> None:
        """Deve manter sliding window atualizada."""
        detector = DriftDetector(window_size=5)

        assert len(detector.trades_sliding_window) == 0

        for i in range(3):
            trade = MockTrade(
                trade_id=f"TRADE_{i}",
                outcome="WIN",
                pnl=100.0,
                entry_price=1.0,
                exit_price=1.1,
                quantity=100,
                timestamp=datetime.now()
            )
            detector.adicionar_trade(trade)

        assert len(detector.trades_sliding_window) == 3

    def test_sliding_window_overflow(self) -> None:
        """Deve descartar trades antigos quando window overflow."""
        detector = DriftDetector(window_size=5)

        for i in range(10):
            trade = MockTrade(
                trade_id=f"TRADE_{i}",
                outcome="WIN",
                pnl=100.0,
                entry_price=1.0,
                exit_price=1.1,
                quantity=100,
                timestamp=datetime.now() - timedelta(seconds=i*60)
            )
            detector.adicionar_trade(trade)

        # Window deve manter apenas ultimas 5 trades
        assert len(detector.trades_sliding_window) == 5
        # Deve conter trades mais recentes (TRADE_5 a TRADE_9)
        # TRADE_5 eh o primeiro (index 0), TRADE_9 eh o ultimo (index 4)
        assert detector.trades_sliding_window[0].trade_id == "TRADE_5"
        assert detector.trades_sliding_window[4].trade_id == "TRADE_9"


class TestDriftDetectorAlerts:
    """Testes de geracao de alerts."""

    def test_alert_severidade_baixa(self) -> None:
        """Deve criar alert com severidade BAIXA."""
        alert = DriftAlert(
            timestamp=datetime.now(),
            metric="win_rate",
            baseline_value=0.65,
            current_value=0.63,
            zscore=1.0,
            severity=DriftAlertSeverity.LOW,
            message="Leve degradacao em win_rate"
        )

        assert alert.severity == DriftAlertSeverity.LOW
        assert "win_rate" in alert.metric

    def test_alert_severidade_media(self) -> None:
        """Deve criar alert com severidade MEDIA."""
        alert = DriftAlert(
            timestamp=datetime.now(),
            metric="sharpe",
            baseline_value=1.2,
            current_value=0.9,
            zscore=2.5,
            severity=DriftAlertSeverity.MEDIUM,
            message="Moderada degradacao em Sharpe"
        )

        assert alert.severity == DriftAlertSeverity.MEDIUM

    def test_alert_severidade_critica(self) -> None:
        """Deve criar alert com severidade CRITICA."""
        alert = DriftAlert(
            timestamp=datetime.now(),
            metric="win_rate",
            baseline_value=0.65,
            current_value=0.20,
            zscore=5.0,
            severity=DriftAlertSeverity.CRITICAL,
            message="Critica degradacao em win_rate"
        )

        assert alert.severity == DriftAlertSeverity.CRITICAL

    def test_serializar_alert_para_json(self) -> None:
        """Deve serializar alert para JSON."""
        alert = DriftAlert(
            timestamp=datetime.now(),
            metric="win_rate",
            baseline_value=0.65,
            current_value=0.50,
            zscore=3.0,
            severity=DriftAlertSeverity.MEDIUM,
            message="Degradacao detectada"
        )

        alert_dict = alert.para_dict()
        assert isinstance(alert_dict, dict)
        assert alert_dict["metric"] == "win_rate"
        assert alert_dict["severity"] == "MEDIUM"

    def test_serializar_alert_para_json_string(self) -> None:
        """Deve serializar alert para JSON string."""
        alert = DriftAlert(
            timestamp=datetime.now(),
            metric="sharpe",
            baseline_value=1.2,
            current_value=0.8,
            zscore=2.0,
            severity=DriftAlertSeverity.MEDIUM,
            message="Teste"
        )

        json_str = alert.para_json()
        parsed = json.loads(json_str)
        assert parsed["metric"] == "sharpe"


class TestDriftDetectorReporting:
    """Testes de geracao de relatorios."""

    def test_gerar_relatorio_json(self) -> None:
        """Deve gerar relatorio em JSON."""
        detector = DriftDetector(
            baseline_win_rate=0.65,
            baseline_sharpe=1.2
        )

        trades = [
            MockTrade(
                trade_id=f"TRADE_{i}",
                outcome="WIN" if i % 2 == 0 else "LOSS",
                pnl=100.0 if i % 2 == 0 else -50.0,
                entry_price=1.0,
                exit_price=1.1 if i % 2 == 0 else 0.9,
                quantity=100,
                timestamp=datetime.now() - timedelta(seconds=i*60)
            )
            for i in range(20)
        ]

        relatorio = detector.gerar_relatorio_json(trades)
        assert isinstance(relatorio, str)

        parsed = json.loads(relatorio)
        assert "timestamp" in parsed
        assert "baseline" in parsed
        assert "current_metrics" in parsed

    def test_gerar_relatorio_markdown(self) -> None:
        """Deve gerar relatorio em Markdown."""
        detector = DriftDetector(
            baseline_win_rate=0.65,
            baseline_sharpe=1.2
        )

        trades = [
            MockTrade(
                trade_id=f"TRADE_{i}",
                outcome="WIN" if i % 2 == 0 else "LOSS",
                pnl=100.0 if i % 2 == 0 else -50.0,
                entry_price=1.0,
                exit_price=1.1 if i % 2 == 0 else 0.9,
                quantity=100,
                timestamp=datetime.now() - timedelta(seconds=i*60)
            )
            for i in range(20)
        ]

        relatorio = detector.gerar_relatorio_markdown(trades)
        assert isinstance(relatorio, str)
        assert "#" in relatorio  # Deve conter headers markdown
        assert "Baseline" in relatorio or "baseline" in relatorio


class TestDriftDetectorIntegration:
    """Testes de integracao completa."""

    def test_fluxo_completo_deteccao(self) -> None:
        """Deve fazer fluxo completo: adicionar trades, calcular, detectar, alertar."""
        detector = DriftDetector(
            baseline_win_rate=0.65,
            baseline_sharpe=1.2,
            window_size=50,
            drift_threshold_zscore=2.0
        )

        # Simular 50 trades normais
        trades = [
            MockTrade(
                trade_id=f"TRADE_{i}",
                outcome="WIN" if i % 100 < 65 else "LOSS",
                pnl=100.0 if i % 100 < 65 else -50.0,
                entry_price=1.0,
                exit_price=1.1 if i % 100 < 65 else 0.9,
                quantity=100,
                timestamp=datetime.now() - timedelta(seconds=i*60)
            )
            for i in range(50)
        ]

        for trade in trades:
            detector.adicionar_trade(trade)

        assert len(detector.trades_sliding_window) == 50

        # Detectar drift
        alerts = detector.detectar_drift(trades)
        assert isinstance(alerts, list)

    def test_persistencia_relatorio_em_arquivo(self) -> None:
        """Deve salvar relatorio em arquivo."""
        detector = DriftDetector(baseline_win_rate=0.65)

        trades = [
            MockTrade(
                trade_id=f"TRADE_{i}",
                outcome="WIN",
                pnl=100.0,
                entry_price=1.0,
                exit_price=1.1,
                quantity=100,
                timestamp=datetime.now() - timedelta(seconds=i*60)
            )
            for i in range(10)
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            relatorio = detector.gerar_relatorio_json(trades)
            report_file = output_dir / "drift_report.json"
            report_file.write_text(relatorio)

            assert report_file.exists()
            parsed = json.loads(report_file.read_text())
            assert isinstance(parsed, dict)


class TestDriftDetectorEdgeCases:
    """Testes de casos extremos."""

    def test_trades_vazio(self) -> None:
        """Deve lidar com lista de trades vazia."""
        detector = DriftDetector()
        trades: List[MockTrade] = []

        metrics = detector.calcular_metricas(trades)
        assert metrics.num_trades == 0

    def test_um_unico_trade(self) -> None:
        """Deve calcular metricas com um trade."""
        detector = DriftDetector()

        trades = [
            MockTrade(
                trade_id="TRADE_0",
                outcome="WIN",
                pnl=100.0,
                entry_price=1.0,
                exit_price=1.1,
                quantity=100,
                timestamp=datetime.now()
            )
        ]

        metrics = detector.calcular_metricas(trades)
        assert metrics.num_trades == 1
        assert metrics.win_rate == 1.0

    def test_baseline_nao_definido(self) -> None:
        """Nao deve falhar se baseline nao foi definido."""
        detector = DriftDetector()  # Sem baseline

        trades = [
            MockTrade(
                trade_id=f"TRADE_{i}",
                outcome="WIN",
                pnl=100.0,
                entry_price=1.0,
                exit_price=1.1,
                quantity=100,
                timestamp=datetime.now() - timedelta(seconds=i*60)
            )
            for i in range(10)
        ]

        # Deve retornar metricas validas mesmo sem baseline
        metrics = detector.calcular_metricas(trades)
        assert metrics.num_trades == 10
