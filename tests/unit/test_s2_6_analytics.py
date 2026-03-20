"""
Unit Tests para S2-6: Analytics de Intervencao Manual
"""

import threading
from datetime import datetime
from typing import Any, Dict

import pytest

from agente_micro_tendencia_winfut.s2_6_analytics import (
    AnalyticsConfig,
    AnalyticsDashboard,
    ManualOverrideLogger,
    TraderFeedbackAPI,
)
from agente_micro_tendencia_winfut.s2_6_analytics.models import (
    InterventionType,
    Signal,
    SignalStatus,
)


@pytest.fixture
def config() -> AnalyticsConfig:
    """Fixture: Configuracao para testes"""
    return AnalyticsConfig()


@pytest.fixture
def dashboard(config: AnalyticsConfig) -> AnalyticsDashboard:
    """Fixture: Dashboard inicializado"""
    return AnalyticsDashboard(config)


@pytest.fixture
def sample_signal() -> Signal:
    """Fixture: Sinal de exemplo"""
    return Signal(
        signal_id="test_signal_001",
        timestamp=datetime.now(),
        timeframe="M1",
        direction="BULLISH",
        confidence_score=0.85,
        smc_confluence_score=4.5,
        entry_price=130000.0,
        stop_loss=129700.0,
        take_profit=130300.0,
        reward_risk_ratio=2.0,
    )


def test_signal_creation() -> None:
    """WHEN: Criar sinal com parametros validos
    THEN: Sinal deve ser criado com sucesso"""
    signal = Signal(
        signal_id="test_001",
        timestamp=datetime.now(),
        timeframe="M1",
        direction="BULLISH",
        confidence_score=0.8,
        smc_confluence_score=4.0,
        entry_price=130000.0,
        stop_loss=129700.0,
        take_profit=130300.0,
        reward_risk_ratio=2.0,
    )

    assert signal.signal_id == "test_001"
    assert signal.direction == "BULLISH"
    assert signal.confidence_score == 0.8
    assert signal.status == SignalStatus.GENERATED


def test_signal_invalid_confidence() -> None:
    """WHEN: Tentar criar sinal com confidence fora do range
    THEN: Deve rejeitar com ValueError"""
    with pytest.raises(ValueError, match="confidence_score deve estar entre"):
        Signal(
            signal_id="test_001",
            timestamp=datetime.now(),
            timeframe="M1",
            direction="BULLISH",
            confidence_score=1.5,  # Invalido (>1.0)
            smc_confluence_score=4.0,
            entry_price=130000.0,
            stop_loss=129700.0,
            take_profit=130300.0,
            reward_risk_ratio=2.0,
        )


def test_dashboard_register_signal(
    dashboard: AnalyticsDashboard,
    sample_signal: Signal,
) -> None:
    """WHEN: Registrar sinal no dashboard
    THEN: Sinal deve estar em pending_signals"""
    dashboard.register_signal(sample_signal)

    pending = dashboard.feedback_api.get_pending_signals()
    assert sample_signal.signal_id in pending
    assert dashboard.daily_stats["total_signals"] == 1


def test_dashboard_approve_signal(
    dashboard: AnalyticsDashboard,
    sample_signal: Signal,
) -> None:
    """WHEN: Registrar e depois aprovar sinal
    THEN: Sinal deve sair de pending e estar aprovado"""
    dashboard.register_signal(sample_signal)

    # Simular aprovacao
    import asyncio

    asyncio.run(
        dashboard.feedback_api.approve_signal(sample_signal.signal_id, "trader_001")
    )

    pending = dashboard.feedback_api.get_pending_signals()
    assert sample_signal.signal_id not in pending


def test_dashboard_execute_signal(
    dashboard: AnalyticsDashboard,
    sample_signal: Signal,
) -> None:
    """WHEN: Executar um sinal
    THEN: Sinal deve estar em open_positions com execution_price"""
    dashboard.register_signal(sample_signal)

    executed = dashboard.execute_signal(
        sample_signal.signal_id,
        execution_price=130050.0,
    )

    assert executed is not None
    assert executed.execution_price == 130050.0
    assert executed.status == SignalStatus.EXECUTED
    assert sample_signal.signal_id in dashboard.current_open_positions


def test_dashboard_close_position(
    dashboard: AnalyticsDashboard,
    sample_signal: Signal,
) -> None:
    """WHEN: Executar e depois fechar posicao
    THEN: P&L deve ser calculado corretamente"""
    dashboard.register_signal(sample_signal)
    dashboard.execute_signal(sample_signal.signal_id, execution_price=130000.0)

    # Fechar com lucro (BULLISH, close > execution)
    dashboard.close_position(sample_signal.signal_id, close_price=130100.0)

    position = dashboard.signal_history[sample_signal.signal_id]
    assert position.pnl_points == 100.0
    assert position.pnl_percentage > 0
    assert dashboard.daily_stats["winning_trades"] == 1


def test_manual_override_logger(config: AnalyticsConfig) -> None:
    """WHEN: Registrar intervencao manual
    THEN: Logger deve armazenar com auditoria completa"""
    logger = ManualOverrideLogger(config)

    override = logger.log_override(
        override_id="override_001",
        trader_id="trader_001",
        intervention_type=InterventionType.SIGNAL_APPROVAL,
        reason="High confidence signal, market conditions favorable",
        signal_id="signal_001",
    )

    assert override.override_id == "override_001"
    assert override.trader_id == "trader_001"
    assert override.reason == "High confidence signal, market conditions favorable"


def test_trader_feedback_api(config: AnalyticsConfig) -> None:
    """WHEN: Usar Trader Feedback API
    THEN: API deve gerenciar sinais e feedback"""
    api = TraderFeedbackAPI(config)

    # Registrar trader
    api.register_trader("trader_001")
    assert "trader_001" in api.get_connected_traders()

    # Criar e submeter sinal
    signal = Signal(
        signal_id="test_signal_001",
        timestamp=datetime.now(),
        timeframe="M1",
        direction="BULLISH",
        confidence_score=0.8,
        smc_confluence_score=4.0,
        entry_price=130000.0,
        stop_loss=129700.0,
        take_profit=130300.0,
        reward_risk_ratio=2.0,
    )

    api.submit_signal_for_approval(signal)
    assert api.get_pending_count() == 1

    # Desregistrar trader
    api.unregister_trader("trader_001")
    assert "trader_001" not in api.get_connected_traders()


def test_submit_signal_for_approval_without_running_loop_triggers_callback(
    config: AnalyticsConfig,
    sample_signal: Signal,
) -> None:
    """WHEN: Submeter sinal sem loop ativo
    THEN: Callback deve ser processado sem RuntimeError"""
    api = TraderFeedbackAPI(config)
    callback_called = threading.Event()
    callback_payload: Dict[str, Any] = {}

    def on_signal_submitted(data: Dict[str, Any]) -> None:
        callback_payload.update(data)
        callback_called.set()

    api.register_callback("signal_submitted", on_signal_submitted)

    api.submit_signal_for_approval(sample_signal)

    assert callback_called.wait(timeout=1.0)
    assert callback_payload["signal_id"] == sample_signal.signal_id
    assert api.get_pending_count() == 1


def test_submit_signal_timeout_without_running_loop_uses_async_callback(
    config: AnalyticsConfig,
    sample_signal: Signal,
) -> None:
    """WHEN: Timeout ocorrer sem loop ativo
    THEN: Timeout deve auto-rejeitar e disparar callback async"""
    api = TraderFeedbackAPI(config)
    timeout_called = threading.Event()
    timeout_payload: Dict[str, Any] = {}

    async def on_signal_timeout(data: Dict[str, Any]) -> None:
        timeout_payload.update(data)
        timeout_called.set()

    api.register_callback("signal_timeout", on_signal_timeout)

    api.submit_signal_for_approval(sample_signal, timeout_seconds=0.01)

    assert timeout_called.wait(timeout=1.0)
    assert timeout_payload["signal_id"] == sample_signal.signal_id
    assert timeout_payload["action"] == "auto_rejected"
    assert api.get_pending_count() == 0


def test_submit_signal_for_approval_uses_running_loop_when_available(
    config: AnalyticsConfig,
    sample_signal: Signal,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WHEN: Houver loop ativo
    THEN: Coroutines devem ser agendadas no loop atual"""

    class FakeLoop:
        def __init__(self) -> None:
            self.coroutines = []

        def create_task(self, coroutine: Any) -> None:
            self.coroutines.append(coroutine)

    fake_loop = FakeLoop()
    monkeypatch.setattr(
        "agente_micro_tendencia_winfut.s2_6_analytics.trader_feedback_api."
        "asyncio.get_running_loop",
        lambda: fake_loop,
    )

    api = TraderFeedbackAPI(config)
    api.submit_signal_for_approval(sample_signal, timeout_seconds=1.0)

    assert len(fake_loop.coroutines) == 2

    for coroutine in fake_loop.coroutines:
        coroutine.close()


def test_dashboard_data_structure(
    dashboard: AnalyticsDashboard,
    sample_signal: Signal,
) -> None:
    """WHEN: Obter dados do dashboard
    THEN: Estrutura deve conter todas as secoes esperadas"""
    dashboard.register_signal(sample_signal)
    dashboard.daily_stats["approved"] = 1
    dashboard.daily_stats["winning_trades"] = 1
    dashboard.daily_stats["losing_trades"] = 0

    data = dashboard.get_dashboard_data()

    # Verificar estrutura
    assert "signals" in data
    assert "performance" in data
    assert "risk" in data
    assert "interventions" in data
    assert "connectivity" in data

    # Verificar dados
    assert data["signals"]["pending"] == 1
    assert data["performance"]["total_signals_today"] == 1
    assert data["performance"]["approved"] == 1


def test_performance_metrics(
    dashboard: AnalyticsDashboard,
    sample_signal: Signal,
) -> None:
    """WHEN: Calcular metricas de performance
    THEN: Metricas devem ser calculadas corretamente"""
    dashboard.register_signal(sample_signal)
    dashboard.execute_signal(sample_signal.signal_id, execution_price=130000.0)
    dashboard.close_position(sample_signal.signal_id, close_price=130100.0)

    report = dashboard.get_performance_report(days=1)

    assert report.total_signals >= 1
    assert report.winning_trades == 1
    assert report.win_rate > 0
    assert report.total_pnl_points == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
