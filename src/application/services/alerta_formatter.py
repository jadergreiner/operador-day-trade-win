"""Formatadores de alerta para múltiplos canais."""

import json
from datetime import datetime
from typing import Dict

from src.domain.entities.alerta import AlertaOportunidade


class AlertaFormatter:
    """
    Formata AlertaOportunidade para diferentes canais.

    Responsabilidade: 
    - HTML para email SMTP
    - JSON para WebSocket
    - SMS de texto (v1.1)

    Mantém consistência de informações entre canais.
    """

    # Template HTML base
    TEMPLATE_EMAIL_HTML = """
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #8B0000; color: white; padding: 15px; text-align: center; border-radius: 5px; }}
                .nivel-critico {{ background-color: #DC143C; }}
                .nivel-alto {{ background-color: #FF6347; }}
                .nivel-medio {{ background-color: #FFA500; }}
                .content {{ margin: 20px 0; }}
                .info-box {{ 
                    background-color: #f4f4f4; 
                    border-left: 4px solid #333; 
                    padding: 15px; 
                    margin: 10px 0;
                }}
                .metric {{ display: flex; justify-content: space-between; margin: 8px 0; }}
                .metric-label {{ font-weight: bold; }}
                .metric-value {{ color: #0066cc; }}
                .footer {{ margin-top: 20px; font-size: 12px; color: #666; border-top: 1px solid #ddd; padding-top: 15px; }}
                .button {{ 
                    display: inline-block; 
                    background-color: #0066cc; 
                    color: white; 
                    padding: 10px 20px; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header nivel-{nivel_class}">
                    <h1>🚨 [{nivel}] OPORTUNIDADE {ativo}</h1>
                </div>
                
                <div class="content">
                    <div class="info-box">
                        <h3>📊 Padrão Detectado</h3>
                        <div class="metric">
                            <span class="metric-label">Padrão:</span>
                            <span class="metric-value">{padrao}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Ativo:</span>
                            <span class="metric-value">{ativo}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Confiança:</span>
                            <span class="metric-value">{confianca}%</span>
                        </div>
                    </div>
                    
                    <div class="info-box">
                        <h3>💰 Dados de Mercado</h3>
                        <div class="metric">
                            <span class="metric-label">Preço Atual:</span>
                            <span class="metric-value">{preco_atual}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Entrada (banda):</span>
                            <span class="metric-value">{entrada_min} - {entrada_max}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Stop Loss:</span>
                            <span class="metric-value">{stop_loss}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Take Profit:</span>
                            <span class="metric-value">{take_profit}</span>
                        </div>
                    </div>
                    
                    <div class="info-box">
                        <h3>📈 Risk:Reward</h3>
                        <div class="metric">
                            <span class="metric-label">Relação:</span>
                            <span class="metric-value">1:{risk_reward}</span>
                        </div>
                    </div>
                    
                    <div class="metric">
                        <span class="metric-label">⏰ Timestamp:</span>
                        <span class="metric-value">{timestamp}</span>
                    </div>
                    
                    <div class="metric">
                        <span class="metric-label">📋 ID Alerta:</span>
                        <span class="metric-value">{alerta_id}</span>
                    </div>
                </div>
                
                <div class="footer">
                    <p>✅ Gerenciado por: Agente Autônomo v1.1</p>
                    <p>❓ Dúvidas? Consulte a análise completa na dashboard</p>
                    <p>⚠️ Este é um alerta automático. Decisão final é do operador.</p>
                </div>
            </div>
        </body>
    </html>
    """

    @staticmethod
    def formatar_email_html(alerta: AlertaOportunidade) -> str:
        """
        Formata AlertaOportunidade como HTML para email SMTP.

        Args:
            alerta: AlertaOportunidade a formatar

        Returns:
            String HTML pronta para envio via SMTP
        """
        nivel_class = alerta.nivel.value.lower()

        html = AlertaFormatter.TEMPLATE_EMAIL_HTML.format(
            nivel=alerta.nivel.value,
            nivel_class=nivel_class,
            ativo=str(alerta.ativo),
            padrao=alerta.padrao.value.replace("_", " ").title(),
            preco_atual=f"{alerta.preco_atual:.2f}",
            entrada_min=f"{alerta.entrada_minima:.2f}",
            entrada_max=f"{alerta.entrada_maxima:.2f}",
            stop_loss=f"{alerta.stop_loss:.2f}",
            take_profit=f"{alerta.take_profit:.2f}" if alerta.take_profit else "N/A",
            confianca=int(float(alerta.confianca) * 100),
            risk_reward=f"{alerta.risk_reward:.2f}",
            timestamp=alerta.timestamp_deteccao.isoformat(),
            alerta_id=str(alerta.id)[:8],  # Primeiros 8 chars do UUID
        )

        return html

    @staticmethod
    def formatar_json(alerta: AlertaOportunidade) -> Dict:
        """
        Formata AlertaOportunidade como JSON estruturado para WebSocket.

        Args:
            alerta: AlertaOportunidade a formatar

        Returns:
            Dict pronto para serialização JSON
        """
        return {
            "id": str(alerta.id),
            "nivel": alerta.nivel.value,
            "ativo": str(alerta.ativo),
            "padrao": alerta.padrao.value,
            "preco_atual": float(alerta.preco_atual),
            "entrada_min": float(alerta.entrada_minima),
            "entrada_max": float(alerta.entrada_maxima),
            "stop_loss": float(alerta.stop_loss),
            "take_profit": float(alerta.take_profit) if alerta.take_profit else None,
            "confianca": float(alerta.confianca),
            "risk_reward": float(alerta.risk_reward),
            "timestamp_deteccao": alerta.timestamp_deteccao.isoformat(),
        }

    @staticmethod
    def formatar_sms(alerta: AlertaOportunidade) -> str:
        """
        Formata AlertaOportunidade como texto SMS (max 160 caracteres).

        Args:
            alerta: AlertaOportunidade a formatar

        Returns:
            String com no máximo 160 caracteres
        """
        # Formato compacto: [nível] ativo preço E:entrada SL:sl R:rr
        msg = (
            f"[{alerta.nivel.value[0]}] {alerta.ativo} "
            f"{alerta.preco_atual:.0f} "
            f"E:{alerta.entrada_minima:.0f}-{alerta.entrada_maxima:.0f} "
            f"SL:{alerta.stop_loss:.0f} "
            f"R:1:{alerta.risk_reward:.1f}"
        )

        # Trunca se necessário
        if len(msg) > 160:
            msg = msg[:157] + "..."

        return msg

    @staticmethod
    def formatar_assunto_email(alerta: AlertaOportunidade) -> str:
        """
        Formata assunto do email para uma linha.

        Args:
            alerta: AlertaOportunidade

        Returns:
            String para Subject do email
        """
        return (
            f"[{alerta.nivel.value}] {alerta.ativo} - "
            f"{alerta.padrao.value.replace('_', ' ').title()}"
        )

    @staticmethod
    def formatar_corpo_email_texto(alerta: AlertaOportunidade) -> str:
        """
        Formata corpo alternativo em texto puro (fallback).

        Args:
            alerta: AlertaOportunidade

        Returns:
            String em texto puro
        """
        return f"""
===========================================
🚨 ALERTA DE OPORTUNIDADE
===========================================

Nível: {alerta.nivel.value}
Ativo: {alerta.ativo}
Padrão: {alerta.padrao.value}

DADOS DE MERCADO
Preço Atual: {alerta.preco_atual}
Entrada: {alerta.entrada_minima} - {alerta.entrada_maxima}
Stop Loss: {alerta.stop_loss}
Take Profit: {alerta.take_profit or "N/A"}

MÉTRICAS
Confiança: {int(float(alerta.confianca) * 100)}%
Risk:Reward: 1:{alerta.risk_reward}

RASTREAMENTO
ID: {alerta.id}
Timestamp: {alerta.timestamp_deteccao.isoformat()}

---
Agente Autônomo v1.1
"""
