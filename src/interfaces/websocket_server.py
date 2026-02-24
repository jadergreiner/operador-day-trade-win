"""
WebSocket Server para Alertas Automáticos

FastAPI + WebSockets para real-time delivery de alertas.
Inclui API REST para Analytics (S2-6).
"""

import asyncio
import logging
from typing import Set, Optional
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
import uvicorn

from src.analytics_collector import AnalyticsCollector

logger = logging.getLogger(__name__)

app = FastAPI(title="Alertas Automáticos - WebSocket Server")

# Connection manager (broadcast para múltiplos operadores)
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Cliente conectado. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"Cliente desconectado. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Envia alerta para todos os clientes conectados."""
        failed_connections = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Erro ao enviar para cliente: {e}")
                failed_connections.append(connection)

        # Remove conexões que falharam
        for conn in failed_connections:
            self.disconnect(conn)

    def get_active_count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()


# Rotas
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "active_connections": manager.get_active_count(),
        "timestamp": asyncio.get_running_loop().time()
    }


@app.get("/metrics")
async def metrics():
    """Métricas do servidor."""
    return {
        "active_connections": manager.get_active_count(),
        "status": "running"
    }


@app.websocket("/alertas")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint para receber e enviar alertas.

    Protocolo:
    - Cliente conecta a ws://localhost:8765/alertas?token=JWT_TOKEN
    - Servidor envia alertas no formato JSON
    - Formato: {
        "id": "uuid",
        "ativo": "WIN$N",
        "padrão": "VOLATILIDADE_EXTREMA",
        "nível": "CRÍTICO",
        "preco_atual": 127450.00,
        "entrada_minima": 127400.00,
        "entrada_maxima": 127500.00,
        "stop_loss": 127000.00,
        "take_profit": 128350.00,
        "confianca": 0.85,
        "timestamp": "2026-02-20T14:30:00Z"
    }
    """
    await manager.connect(websocket)

    try:
        while True:
            # Aguarda por mensagens do cliente (keep-alive)
            data = await asyncio.wait_for(websocket.receive_text(), timeout=300)  # 5 min timeout
            logger.debug(f"Mensagem do cliente: {data}")

    except asyncio.TimeoutError:
        logger.info("Cliente timeout (idle > 5 min)")
        manager.disconnect(websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Cliente desconectou")

    except Exception as e:
        logger.error(f"Erro WebSocket: {e}")
        manager.disconnect(websocket)


# API REST (para operações síncronas - v1.2)
@app.get("/alertas/historico")
async def get_alertas_historico(limit: int = 100, offset: int = 0):
    """
    GET histórico de alertas (v1.2 future).

    Query params:
    - limit: número de alertas (default 100)
    - offset: pagination offset
    - ativo: filtrar por ativo (ex: WIN$N)
    - padrão: filtrar por padrão (ex: VOLATILIDADE_EXTREMA)
    - data_inicio: ISO8601 (ex: 2026-02-20)
    - data_fim: ISO8601

    Returns:
    [{
        "id": "uuid",
        "ativo": "WIN$N",
        ...
    }]
    """
    return {
        "status": "not_implemented",
        "message": "Endpoint v1.2 - Implementação futura",
        "version": "1.1.0"
    }


@app.get("/config")
async def get_config():
    """Configuração ativa (public info apenas)."""
    return {
        "version": "1.1.0",
        "websocket_port": 8765,
        "active_connections": manager.get_active_count(),
        "features": {
            "volatility_detection": True,
            "pattern_detection": True,
            "websocket_delivery": True,
            "email_delivery": True,
            "sms_delivery": False  # v1.2
        }
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Dashboard HTML com monitoramento em tempo real."""
    html_content = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Alertas - Dashboard</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: #fff;
                padding: 20px;
                min-height: 100vh;
            }
            .container { max-width: 1200px; margin: 0 auto; }
            .header {
                text-align: center;
                margin-bottom: 30px;
                padding: 20px;
                background: rgba(0,0,0,0.2);
                border-radius: 10px;
                border-left: 4px solid #4CAF50;
            }
            h1 { font-size: 2.5em; margin-bottom: 10px; }
            .status-bar {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }
            .status-card {
                background: rgba(0,0,0,0.3);
                padding: 20px;
                border-radius: 10px;
                border: 1px solid rgba(76,175,80,0.3);
                backdrop-filter: blur(10px);
            }
            .status-card h3 { font-size: 0.9em; color: #aaa; margin-bottom: 5px; }
            .status-card .value {
                font-size: 2.5em;
                font-weight: bold;
                color: #4CAF50;
            }
            .status-ok { color: #4CAF50; }
            .status-warn { color: #FF9800; }
            .status-error { color: #f44336; }

            .alerts-section {
                background: rgba(0,0,0,0.3);
                padding: 20px;
                border-radius: 10px;
                border: 1px solid rgba(76,175,80,0.3);
                margin-bottom: 20px;
            }
            .alerts-section h2 { margin-bottom: 15px; font-size: 1.5em; }

            #alertsList {
                max-height: 500px;
                overflow-y: auto;
            }
            .alert-item {
                background: rgba(255,255,255,0.05);
                padding: 12px;
                margin-bottom: 10px;
                border-left: 3px solid #4CAF50;
                border-radius: 5px;
                font-size: 0.9em;
            }
            .alert-item.critical { border-left-color: #f44336; }
            .alert-item.warning { border-left-color: #FF9800; }

            .endpoints {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 10px;
                margin-top: 20px;
            }
            .endpoint-btn {
                background: rgba(76,175,80,0.2);
                border: 1px solid #4CAF50;
                color: #fff;
                padding: 10px 15px;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
                text-align: center;
                transition: all 0.3s;
            }
            .endpoint-btn:hover {
                background: rgba(76,175,80,0.4);
                transform: translateY(-2px);
            }
            .timestamp { font-size: 0.8em; color: #999; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Alertas - Dashboard</h1>
                <p>Monitoramento em Tempo Real</p>
                <div class="timestamp" id="timestamp"></div>
            </div>

            <div class="status-bar">
                <div class="status-card">
                    <h3>Status</h3>
                    <div class="value status-ok" id="status">🟢 Online</div>
                </div>
                <div class="status-card">
                    <h3>Conexoes Ativas</h3>
                    <div class="value" id="connections">0</div>
                </div>
                <div class="status-card">
                    <h3>Total de Alertas</h3>
                    <div class="value" id="totalAlerts">0</div>
                </div>
            </div>

            <div class="alerts-section">
                <h2>🚨 Alertas em Tempo Real</h2>
                <div id="alertsList">
                    <div class="alert-item">
                        <span class="status-warn">Aguardando alertas...</span>
                    </div>
                </div>
            </div>

            <div class="alerts-section">
                <h2>🔗 API Endpoints</h2>
                <div class="endpoints">
                    <a href="/health" class="endpoint-btn">/health</a>
                    <a href="/metrics" class="endpoint-btn">/metrics</a>
                    <a href="/config" class="endpoint-btn">/config</a>
                    <a href="/docs" class="endpoint-btn">/docs (Swagger)</a>
                </div>
            </div>
        </div>

        <script>
            let alertCount = 0;
            const alertsListEl = document.getElementById('alertsList');
            const connectionsEl = document.getElementById('connections');
            const totalAlertsEl = document.getElementById('totalAlerts');
            const timestampEl = document.getElementById('timestamp');

            function updateTimestamp() {
                const now = new Date().toLocaleString('pt-BR');
                timestampEl.textContent = now;
            }
            updateTimestamp();
            setInterval(updateTimestamp, 1000);

            function connectWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const ws = new WebSocket(protocol + '//' + window.location.host + '/alertas');

                ws.onopen = function(event) {
                    console.log('✅ Conectado ao WebSocket');
                    connectionsEl.textContent = '1';
                };

                ws.onmessage = function(event) {
                    const alert = JSON.parse(event.data);
                    alertCount++;
                    totalAlertsEl.textContent = alertCount;

                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert-item';

                    const nivel = alert.nivel || 'INFO';
                    if (nivel === 'CRITICO') alertDiv.classList.add('critical');
                    if (nivel === 'AVISO') alertDiv.classList.add('warning');

                    const timestamp = new Date(alert.timestamp).toLocaleTimeString('pt-BR');
                    alertDiv.innerHTML = `
                        <strong>${alert.ativo}</strong> - ${alert.padrao}<br>
                        <small>Preco: ${alert.preco_atual} | Entrada: ${alert.entrada_minima} | Confianca: ${(alert.confianca*100).toFixed(0)}%</small><br>
                        <small style="color: #999;">${timestamp}</small>
                    `;

                    alertsListEl.insertBefore(alertDiv, alertsListEl.firstChild);

                    // Manter apenas os ultimos 20 alertas
                    while (alertsListEl.children.length > 20) {
                        alertsListEl.removeChild(alertsListEl.lastChild);
                    }
                };

                ws.onerror = function(event) {
                    console.error('❌ Erro WebSocket:', event);
                };

                ws.onclose = function(event) {
                    console.log('Desconectado. Reconectando em 3s...');
                    connectionsEl.textContent = '0';
                    setTimeout(connectWebSocket, 3000);
                };
            }

            // Iniciar conexão WebSocket
            connectWebSocket();

            // Atualizar metricas a cada 5s
            setInterval(async function() {
                try {
                    const response = await fetch('/metrics');
                    const data = await response.json();
                    connectionsEl.textContent = data.active_connections;
                } catch (e) {
                    console.log('Erro ao atualizar metricas:', e);
                }
            }, 5000);
        </script>
    </body>
    </html>
    """
    return html_content


# ════════════════════════════════════════════════════════════════════════════════
# S2-6: ANALYTICS DE INTERVENÇÃO MANUAL (Endpoints REST)
# ════════════════════════════════════════════════════════════════════════════════

# Analytics Collector global (inicializado na startup)
analytics_collector: Optional[AnalyticsCollector] = None


@app.post("/api/intervention/log")
async def log_intervention(data: dict):
    """
    Registra uma intervenção manual (OVERRIDE, PAUSE, CANCEL, EXECUTE).
    
    Request body:
    {
        "symbol": "WINFUT",
        "action": "OVERRIDE",  # ou PAUSE, CANCEL, EXECUTE
        "reason": "Divergência SMC com confluência",
        "ml_signal": 0.75,
        "trader_decision": "Aumentar 25% do ticket"
    }
    
    Response:
    {
        "intervention_id": 1,
        "status": "logged"
    }
    """
    if not analytics_collector:
        raise HTTPException(status_code=503, detail="Analytics não inicializado")
    
    try:
        intervention_id = analytics_collector.log_intervention(
            symbol=data.get("symbol", "WINFUT"),
            action=data.get("action"),
            ml_signal=float(data.get("ml_signal", 0.0)),
            trader_decision=data.get("trader_decision", ""),
            reason=data.get("reason"),
            notes=data.get("notes")
        )
        
        if intervention_id is None:
            raise HTTPException(status_code=400, detail="Erro ao registrar intervenção")
        
        return {
            "intervention_id": intervention_id,
            "status": "logged",
            "timestamp": asyncio.get_running_loop().time()
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao registrar intervenção: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")


@app.post("/api/intervention/{intervention_id}/result")
async def update_intervention_result(intervention_id: int, data: dict):
    """
    Atualiza resultado de uma intervenção.
    
    Request body:
    {
        "result": "WIN",  # ou LOSS, PARTIAL
        "p_and_l": 475.50
    }
    
    Response:
    {
        "status": "updated"
    }
    """
    if not analytics_collector:
        raise HTTPException(status_code=503, detail="Analytics não inicializado")
    
    try:
        success = analytics_collector.update_intervention_result(
            intervention_id=intervention_id,
            result=data.get("result", "PARTIAL"),
            p_and_l=float(data.get("p_and_l", 0.0))
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Intervenção não encontrada")
        
        return {"status": "updated"}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao atualizar resultado: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")


@app.get("/api/analytics/stats")
async def get_analytics_stats(symbol: Optional[str] = None):
    """
    Retorna estatísticas de intervenções.
    
    Query params:
    - symbol: Filtrar por símbolo (ex: WINFUT). Se não fornecido, retorna global.
    
    Response:
    {
        "total_interventions": 10,
        "wins": 6,
        "losses": 2,
        "partials": 2,
        "win_rate": 60.0,
        "avg_pnl": 150.5,
        "total_pnl": 1505.0
    }
    """
    if not analytics_collector:
        raise HTTPException(status_code=503, detail="Analytics não inicializado")
    
    try:
        stats = analytics_collector.get_intervention_stats(symbol=symbol)
        return stats
    except Exception as e:
        logger.error(f"Erro ao buscar stats: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")


@app.get("/api/analytics/dashboard")
async def get_analytics_dashboard():
    """
    Retorna dashboard completo de analytics.
    
    Response:
    {
        "global": {
            "total_interventions": 10,
            "wins": 6,
            "win_rate": 60.0,
            "total_pnl": 1505.0
        },
        "by_action": {
            "OVERRIDE": {...},
            "PAUSE": {...},
            "CANCEL": {...},
            "EXECUTE": {...}
        }
    }
    """
    if not analytics_collector:
        raise HTTPException(status_code=503, detail="Analytics não inicializado")
    
    try:
        global_stats = analytics_collector.get_intervention_stats()
        
        dashboard = {
            "global": global_stats,
            "by_action": {
                "OVERRIDE": analytics_collector.get_interventions_by_action("OVERRIDE", limit=5),
                "PAUSE": analytics_collector.get_interventions_by_action("PAUSE", limit=5),
                "CANCEL": analytics_collector.get_interventions_by_action("CANCEL", limit=5),
                "EXECUTE": analytics_collector.get_interventions_by_action("EXECUTE", limit=5),
            },
            "timestamp": asyncio.get_running_loop().time()
        }
        
        return dashboard
    except Exception as e:
        logger.error(f"Erro ao gerar dashboard: {e}")
        raise HTTPException(status_code=500, detail="Erro interno")


# ════════════════════════════════════════════════════════════════════════════════
# LIFECYCLE HANDLERS
# ════════════════════════════════════════════════════════════════════════════════


async def startup():
    """Startup event."""
    global analytics_collector
    logger.info("🚀 WebSocket Server iniciando...")
    logger.info("📍 Ouvindo em ws://0.0.0.0:8765/alertas")
    
    # Inicializar Analytics Collector para S2-6
    try:
        analytics_collector = AnalyticsCollector("data/analytics.db")
        if analytics_collector.connect():
            logger.info("✅ Analytics Collector inicializado")
        else:
            logger.warning("⚠️  Analytics Collector falhou ao conectar")
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar Analytics: {e}")


async def shutdown():
    """Shutdown event."""
    global analytics_collector
    logger.info("🛑 WebSocket Server desligando...")
    for conn in list(manager.active_connections):
        manager.disconnect(conn)
    
    # Fechar Analytics Collector
    if analytics_collector:
        try:
            analytics_collector.close()
            logger.info("✅ Analytics Collector fechado")
        except Exception as e:
            logger.error(f"❌ Erro ao fechar Analytics: {e}")


app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)


async def broadcast_alert(alerta_json: dict):
    """
    Função pública para broadcast de alerta (chamada pela fila).

    Args:
        alerta_json: Alertas convertido para JSON (AlertaFormatter.formatar_json())
    """
    await manager.broadcast(alerta_json)


if __name__ == "__main__":
    # Development
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8765,
        log_level="info"
    )
