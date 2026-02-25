"""
AlertDispatcher - Centro de distribuição de alertas para operadores.

Integra WebSocket (tempo real) com fallback para email (persistência).
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict

from src.application.services.email_service import EmailService

logger = logging.getLogger(__name__)


@dataclass
class TradeAlert:
    """Estrutura de alerta de oportunidade de trade"""
    
    alert_id: str
    symbol: str
    operation: str  # BUY ou SELL
    confidence_score: float  # 0.0 a 1.0
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: str  # ISO format
    features_summary: Dict[str, float]  # Top 5 features
    
    def to_dict(self) -> Dict[str, Any]:
        """Converter para dict para serialização"""
        return asdict(self)
    
    def to_html(self) -> str:
        """Gerar HTML do alerta para email"""
        return f"""
        <div style="border: 2px solid #4CAF50; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <h3 style="color: #4CAF50; margin-top: 0;">⚡ ALERTA DE OPORTUNIDADE</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Símbolo:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{self.symbol}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Operação:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; color: {'#4CAF50' if self.operation == 'BUY' else '#f44336'};"><strong>{self.operation}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Confiança:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{self.confidence_score:.1%}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Preço Entrada:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">R$ {self.entry_price:.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Stop Loss:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">R$ {self.stop_loss:.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>Take Profit:</strong></td>
                    <td style="padding: 8px;">R$ {self.take_profit:.2f}</td>
                </tr>
            </table>
            <p style="margin-top: 10px; color: #666; font-size: 12px;">
                <em>Alerta ID: {self.alert_id} | {self.timestamp}</em>
            </p>
        </div>
        """


class AlertDispatcher:
    """
    Dispatcher para alertas de trade.
    
    AC-1: Dispatcher initializado
    AC-2: WebSocket broadcast implementado
    AC-3: Timeout 30s para fallback email
    AC-4: Fallback email automático
    AC-5: Logging estruturado
    """
    
    def __init__(
        self,
        websocket_manager,  # ConnectionManager do FastAPI
        email_service: Optional[EmailService] = None,
        websocket_timeout: float = 30.0
    ):
        """
        Inicializar dispatcher.
        
        Args:
            websocket_manager: ConnectionManager do FastAPI WebSocket
            email_service: EmailService para fallback
            websocket_timeout: Timeout em segundos para WebSocket (default 30s)
        """
        self.ws_manager = websocket_manager
        self.email_service = email_service
        self.ws_timeout = websocket_timeout
        self.alert_history: List[TradeAlert] = []
        self.failed_alerts: List[Dict[str, Any]] = []
        
        logger.info(f"✅ AlertDispatcher initialized (WS timeout={websocket_timeout}s)")
    
    async def dispatch(self, alert: TradeAlert) -> Dict[str, bool]:
        """
        Disparar alerta via WebSocket com fallback para email.
        
        AC-2: WebSocket broadcast implementado
        AC-3: Timeout 30s para fallback
        AC-4: Fallback email automático
        
        Args:
            alert: TradeAlert object
        
        Returns:
            Dict[str, bool]: {
                'websocket_success': bool,
                'email_fallback_triggered': bool,
                'email_success': bool (se fallback acionado)
            }
        """
        alert_dict = alert.to_dict()
        self.alert_history.append(alert)
        
        result = {
            'websocket_success': False,
            'email_fallback_triggered': False,
            'email_success': False
        }
        
        logger.info(f"📤 Dispatching alert {alert.alert_id} ({alert.symbol} {alert.operation})")
        
        # Tentar WebSocket primeiro (com timeout)
        try:
            await asyncio.wait_for(
                self.ws_manager.broadcast(json.dumps(alert_dict)),
                timeout=self.ws_timeout
            )
            result['websocket_success'] = True
            logger.info(f"✅ WebSocket broadcast succeeded ({alert.alert_id})")
            
        except asyncio.TimeoutError:
            logger.warning(
                f"⏱️  WebSocket broadcast timeout (>{self.ws_timeout}s), "
                f"triggering email fallback ({alert.alert_id})"
            )
            result['email_fallback_triggered'] = True
        
        except Exception as e:
            logger.error(f"❌ WebSocket broadcast failed: {e}")
            result['email_fallback_triggered'] = True
        
        # Se WebSocket falhou, usar email como fallback
        if result['email_fallback_triggered'] and self.email_service:
            try:
                await self._send_alert_email(alert)
                result['email_success'] = True
                logger.info(f"✅ Email fallback succeeded ({alert.alert_id})")
            
            except Exception as e:
                logger.error(f"❌ Email fallback failed: {e}")
                self.failed_alerts.append({
                    'alert_id': alert.alert_id,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        elif result['email_fallback_triggered'] and not self.email_service:
            logger.warning(f"⚠️  Email fallback needed but EmailService not configured")
        
        return result
    
    async def _send_alert_email(self, alert: TradeAlert) -> None:
        """
        Enviar alerta por email (fallback).
        
        Args:
            alert: TradeAlert object
        """
        if not self.email_service:
            raise RuntimeError("EmailService not configured")
        
        subject = f"⚡ ALERTA TRADE {alert.symbol}: {alert.operation} "
        subject += f"({alert.confidence_score:.0%})"
        
        # Corpo HTML
        html_body = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .header {{ background-color: #f5f5f5; padding: 20px; border-radius: 5px; }}
                .content {{ padding: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>Operador Day Trade - Sistema de Alertas</h2>
                    <p style="color: #666; margin: 0;">Alerta em tempo real de oportunidade de trade</p>
                </div>
                
                <div class="content">
                    {alert.to_html()}
                    
                    <p style="margin-top: 20px; color: #666;">
                        <strong>Próximas ações:</strong>
                    </p>
                    <ul style="color: #666;">
                        <li>Aguarde confirmação no dashboard</li>
                        <li>Valide as condições técnicas</li>
                        <li>Execute conforme plano de risco definido</li>
                    </ul>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    
                    <p style="color: #999; font-size: 11px; margin: 10px 0;">
                        Este é um alerta automático do sistema Operador Day Trade.
                        Não responda a este email.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Enviar email
        await self.email_service.send_email_with_retry(
            to_email="operador@example.com",
            subject=subject,
            html_body=html_body
        )
    
    def get_alert_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retornar histórico de alertas.
        
        Args:
            limit: Número máximo de últimos alertas a retornar
        
        Returns:
            Lista de dicts com alertas
        """
        return [alert.to_dict() for alert in self.alert_history[-limit:]]
    
    def get_failed_alerts(self) -> List[Dict[str, Any]]:
        """
        Retornar alertas que falharam em todas as tentativas.
        
        Returns:
            Lista de dicts com falhas
        """
        return self.failed_alerts
    
    async def close(self) -> None:
        """Fechar recursos (email connections, etc)"""
        if self.email_service:
            # Implementar fechamento se necessário
            logger.info("✅ AlertDispatcher closed")


class AlertManager:
    """
    Gerenciador de alertas com histórico e estatísticas.
    """
    
    def __init__(self):
        """Inicializar manager"""
        self.alerts: List[TradeAlert] = []
        self.stats = {
            'total_alerts': 0,
            'buy_alerts': 0,
            'sell_alerts': 0,
            'avg_confidence': 0.0,
            'last_alert_time': None
        }
    
    def add_alert(self, alert: TradeAlert) -> None:
        """Adicionar alerta ao histórico"""
        self.alerts.append(alert)
        self.stats['total_alerts'] += 1
        
        if alert.operation == 'BUY':
            self.stats['buy_alerts'] += 1
        else:
            self.stats['sell_alerts'] += 1
        
        # Atualizar confiança média
        total_conf = sum(a.confidence_score for a in self.alerts)
        self.stats['avg_confidence'] = total_conf / len(self.alerts)
        self.stats['last_alert_time'] = datetime.now().isoformat()
    
    def get_stats(self) -> Dict[str, Any]:
        """Retornar estatísticas"""
        return self.stats.copy()
