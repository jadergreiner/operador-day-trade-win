"""
Testes para AlertDispatcher - Task #4.

Valida dispatcher de alertas, WebSocket broadcast, email fallback.
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.application.alert_dispatcher import TradeAlert, AlertDispatcher, AlertManager


class TestTradeAlert:
    """Testes para classe TradeAlert"""
    
    @pytest.fixture
    def sample_alert(self):
        """Criar alerta de exemplo"""
        return TradeAlert(
            alert_id="ALERT_001",
            symbol="PETR4",
            operation="BUY",
            confidence_score=0.85,
            entry_price=24.50,
            stop_loss=24.00,
            take_profit=25.50,
            timestamp=datetime.now().isoformat(),
            features_summary={
                'rsi': 35.2,
                'bollinger': -2.1,
                'macd': 0.45,
                'volume': 1500000,
                'trend': 0.8
            }
        )
    
    def test_alert_to_dict(self, sample_alert):
        """Validar conversão de alerta para dict"""
        alert_dict = sample_alert.to_dict()
        
        assert isinstance(alert_dict, dict)
        assert alert_dict['alert_id'] == 'ALERT_001'
        assert alert_dict['symbol'] == 'PETR4'
        assert alert_dict['operation'] == 'BUY'
        assert alert_dict['confidence_score'] == 0.85
        assert 'features_summary' in alert_dict
    
    def test_alert_to_html(self, sample_alert):
        """Validar geração de HTML do alerta"""
        html = sample_alert.to_html()
        
        assert isinstance(html, str)
        assert 'PETR4' in html
        assert 'BUY' in html
        assert '24.50' in html
        assert 'ALERTA DE OPORTUNIDADE' in html


class TestAlertDispatcher:
    """Testes para AlertDispatcher"""
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock do ConnectionManager do FastAPI"""
        manager = AsyncMock()
        manager.broadcast = AsyncMock(return_value=True)
        return manager
    
    @pytest.fixture
    def mock_email_service(self):
        """Mock do EmailService"""
        service = AsyncMock()
        service.send_email_with_retry = AsyncMock(return_value=True)
        return service
    
    @pytest.fixture
    def sample_alert(self):
        """Criar alerta de exemplo"""
        return TradeAlert(
            alert_id="ALERT_001",
            symbol="PETR4",
            operation="BUY",
            confidence_score=0.85,
            entry_price=24.50,
            stop_loss=24.00,
            take_profit=25.50,
            timestamp=datetime.now().isoformat(),
            features_summary={'rsi': 35.2, 'bollinger': -2.1}
        )
    
    def test_dispatcher_init(self, mock_websocket_manager, mock_email_service):
        """AC-1: AlertDispatcher inicializado com dependências corretas"""
        dispatcher = AlertDispatcher(
            mock_websocket_manager,
            email_service=mock_email_service,
            websocket_timeout=30.0
        )
        
        assert dispatcher.ws_manager is not None
        assert dispatcher.email_service is not None
        assert dispatcher.ws_timeout == 30.0
        assert dispatcher.alert_history == []
        assert dispatcher.failed_alerts == []
    
    @pytest.mark.asyncio
    async def test_dispatch_websocket_success(
        self,
        mock_websocket_manager,
        mock_email_service,
        sample_alert
    ):
        """AC-2: WebSocket broadcast bem-sucedido"""
        dispatcher = AlertDispatcher(
            mock_websocket_manager,
            email_service=mock_email_service
        )
        
        result = await dispatcher.dispatch(sample_alert)
        
        assert result['websocket_success'] is True
        assert result['email_fallback_triggered'] is False
        assert len(dispatcher.alert_history) == 1
    
    @pytest.mark.asyncio
    async def test_dispatch_websocket_timeout_triggers_email(
        self,
        mock_websocket_manager,
        mock_email_service,
        sample_alert
    ):
        """AC-3: Timeout 30s dispara email fallback, AC-4: Email enviado"""
        # Simular timeout no WebSocket
        mock_websocket_manager.broadcast.side_effect = asyncio.TimeoutError()
        
        dispatcher = AlertDispatcher(
            mock_websocket_manager,
            email_service=mock_email_service,
            websocket_timeout=0.1  # Timeout pequeno para teste
        )
        
        result = await dispatcher.dispatch(sample_alert)
        
        assert result['websocket_success'] is False
        assert result['email_fallback_triggered'] is True
        assert result['email_success'] is True
        assert mock_email_service.send_email_with_retry.called
    
    @pytest.mark.asyncio
    async def test_dispatch_websocket_error_triggers_fallback(
        self,
        mock_websocket_manager,
        mock_email_service,
        sample_alert
    ):
        """AC-2/4: WebSocket falha, email fallback acionado"""
        mock_websocket_manager.broadcast.side_effect = Exception("Connection failed")
        
        dispatcher = AlertDispatcher(
            mock_websocket_manager,
            email_service=mock_email_service
        )
        
        result = await dispatcher.dispatch(sample_alert)
        
        assert result['websocket_success'] is False
        assert result['email_fallback_triggered'] is True
        assert result['email_success'] is True
    
    @pytest.mark.asyncio
    async def test_dispatch_without_email_service(
        self,
        mock_websocket_manager,
        sample_alert
    ):
        """AC-1: Dispatcher sem EmailService (graceful degradation)"""
        dispatcher = AlertDispatcher(
            mock_websocket_manager,
            email_service=None
        )
        
        # Simular timeout
        mock_websocket_manager.broadcast.side_effect = asyncio.TimeoutError()
        
        result = await dispatcher.dispatch(sample_alert)
        
        assert result['websocket_success'] is False
        assert result['email_fallback_triggered'] is True
        assert result['email_success'] is False
    
    @pytest.mark.asyncio
    async def test_send_alert_email(
        self,
        mock_websocket_manager,
        mock_email_service,
        sample_alert
    ):
        """AC-4: Email gerado e enviado com template HTML"""
        dispatcher = AlertDispatcher(
            mock_websocket_manager,
            email_service=mock_email_service
        )
        
        await dispatcher._send_alert_email(sample_alert)
        
        # Validar que email foi chamado com argumentos corretos
        assert mock_email_service.send_email_with_retry.called
        call_kwargs = mock_email_service.send_email_with_retry.call_args[1]
        
        assert 'subject' in call_kwargs
        assert 'html_body' in call_kwargs
        assert 'PETR4' in call_kwargs['subject']
        assert 'BUY' in call_kwargs['subject']
    
    def test_get_alert_history(self, mock_websocket_manager, sample_alert):
        """AC-5: Histórico de alertas retornado"""
        dispatcher = AlertDispatcher(mock_websocket_manager)
        
        # Adicionar alertas ao histórico
        dispatcher.alert_history.append(sample_alert)
        dispatcher.alert_history.append(sample_alert)
        
        history = dispatcher.get_alert_history(limit=10)
        
        assert len(history) == 2
        assert history[0]['alert_id'] == 'ALERT_001'
    
    def test_get_failed_alerts(self, mock_websocket_manager):
        """AC-5: Alertas falhados listados"""
        dispatcher = AlertDispatcher(mock_websocket_manager)
        
        # Adicionar falhas
        dispatcher.failed_alerts.append({
            'alert_id': 'ALERT_001',
            'error': 'Email connection timeout',
            'timestamp': datetime.now().isoformat()
        })
        
        failed = dispatcher.get_failed_alerts()
        
        assert len(failed) == 1
        assert failed[0]['alert_id'] == 'ALERT_001'


class TestAlertManager:
    """Testes para AlertManager"""
    
    @pytest.fixture
    def sample_alerts(self):
        """Criar múltiplos alertas"""
        return [
            TradeAlert(
                alert_id=f"ALERT_{i:03d}",
                symbol="PETR4" if i % 2 == 0 else "VALE3",
                operation="BUY" if i % 2 == 0 else "SELL",
                confidence_score=0.7 + (i * 0.02),
                entry_price=24.50 + i,
                stop_loss=24.00 + i,
                take_profit=25.50 + i,
                timestamp=datetime.now().isoformat(),
                features_summary={}
            )
            for i in range(5)
        ]
    
    def test_manager_init(self):
        """Inicializar AlertManager"""
        manager = AlertManager()
        
        assert manager.alerts == []
        assert manager.stats['total_alerts'] == 0
        assert manager.stats['buy_alerts'] == 0
        assert manager.stats['sell_alerts'] == 0
    
    def test_add_alert_updates_stats(self, sample_alerts):
        """AC-5: Adicionar alerta atualiza estatísticas"""
        manager = AlertManager()
        
        for alert in sample_alerts:
            manager.add_alert(alert)
        
        assert manager.stats['total_alerts'] == 5
        assert manager.stats['buy_alerts'] == 3  # i=0,2,4
        assert manager.stats['sell_alerts'] == 2  # i=1,3
        
        # Validar confiança média
        expected_avg = (0.70 + 0.72 + 0.74 + 0.76 + 0.78) / 5
        assert abs(manager.stats['avg_confidence'] - expected_avg) < 0.001
    
    def test_get_stats(self, sample_alerts):
        """AC-5: Get stats retorna snapshot correto"""
        manager = AlertManager()
        
        for alert in sample_alerts[:2]:
            manager.add_alert(alert)
        
        stats = manager.get_stats()
        
        assert stats['total_alerts'] == 2
        assert stats['buy_alerts'] == 1
        assert stats['last_alert_time'] is not None


class TestAlertDispatcherIntegration:
    """Testes de integração do AlertDispatcher"""
    
    @pytest.mark.asyncio
    async def test_full_dispatch_flow(self):
        """E2E: Alerta from creation para dispatch com WebSocket success"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.broadcast = AsyncMock(return_value=True)
        
        mock_email = AsyncMock()
        mock_email.send_email_with_retry = AsyncMock(return_value=True)
        
        # Create dispatcher
        dispatcher = AlertDispatcher(mock_ws, email_service=mock_email)
        
        # Create and dispatch alert
        alert = TradeAlert(
            alert_id="INT_TEST_001",
            symbol="TEST",
            operation="BUY",
            confidence_score=0.80,
            entry_price=100.00,
            stop_loss=95.00,
            take_profit=110.00,
            timestamp=datetime.now().isoformat(),
            features_summary={}
        )
        
        result = await dispatcher.dispatch(alert)
        
        # Validar resultado
        assert result['websocket_success'] is True
        assert dispatcher.alert_history[0].alert_id == 'INT_TEST_001'
        
        # Email não deve ter sido chamado (WebSocket sucesso)
        assert not mock_email.send_email_with_retry.called
    
    @pytest.mark.asyncio
    async def test_full_dispatch_with_fallback(self):
        """E2E: Alerta com fallback email após timeout WebSocket"""
        # Setup mocks
        mock_ws = AsyncMock()
        mock_ws.broadcast = AsyncMock(side_effect=asyncio.TimeoutError())
        
        mock_email = AsyncMock()
        mock_email.send_email_with_retry = AsyncMock(return_value=True)
        
        # Create dispatcher
        dispatcher = AlertDispatcher(mock_ws, email_service=mock_email, websocket_timeout=0.1)
        
        # Create and dispatch alert
        alert = TradeAlert(
            alert_id="INT_TEST_002",
            symbol="TEST",
            operation="SELL",
            confidence_score=0.75,
            entry_price=100.00,
            stop_loss=105.00,
            take_profit=90.00,
            timestamp=datetime.now().isoformat(),
            features_summary={}
        )
        
        result = await dispatcher.dispatch(alert)
        
        # Validar resultado
        assert result['websocket_success'] is False
        assert result['email_fallback_triggered'] is True
        assert result['email_success'] is True
        
        # Email deve ter sido chamado
        assert mock_email.send_email_with_retry.called
