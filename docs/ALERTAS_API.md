# 📡 API de Alertas - Documentação Técnica

**Versão:** 1.1.0  
**Data:** 20/02/2026  
**Status:** ✅ PRONTO PARA DESENVOLVIMENTO

---

## 1. Overview

A API de Alertas expõe o sistema de detecção e entrega de oportunidades de trading em tempo real.

**Endpoints:**
- WebSocket: Recebimento em tempo real (<500ms)
- REST API: Consulta de histórico e configuração (futuro)

---

## 2. WebSocket (Real-Time)

### Conexão

```
URL: ws://localhost:8765/alertas
Headers:
  Authorization: Bearer {token}
  Content-Type: application/json
```

### Payload - Alerta Recebido

```json
{
  "tipo": "ALERTA",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp_servidor": "2026-02-20T14:23:45.123456Z",
  "alerta": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "nivel": "CRÍTICO",
    "ativo": "WIN$N",
    "padrão": "volatilidade_extrema",
    "dados_mercado": {
      "preço_atual": 89.250,
      "entrada_minima": 89.100,
      "entrada_maxima": 89.300,
      "stop_loss": 88.800,
      "take_profit": 91.000
    },
    "métricas": {
      "confiança": 0.85,
      "risk_reward": 2.5
    },
    "timestamp_deteccao": "2026-02-20T14:23:40.000000Z"
  }
}
```

### Exemplo - Conexão em Python

```python
import asyncio
import json
import websockets

async def receber_alertas():
    uri = "ws://localhost:8765/alertas"
    headers = {"Authorization": "Bearer seu_token_aqui"}
    
    async with websockets.connect(uri, extra_headers=headers) as websocket:
        print("✅ Conectado ao servidor de alertas")
        
        while True:
            try:
                msg = await websocket.recv()
                alerta = json.loads(msg)
                
                print(f"🚨 ALERTA: {alerta['alerta']['ativo']}")
                print(f"   Padrão: {alerta['alerta']['padrão']}")
                print(f"   Entrada: {alerta['alerta']['dados_mercado']['entrada_minima']}")
                print(f"   Risk:Reward: {alerta['alerta']['métricas']['risk_reward']}")
                
                # TODO: Sua lógica aqui
                
            except websockets.exceptions.ConnectionClosed:
                print("❌ Desconectado. Tentando reconectar em 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"❌ Erro: {e}")
                await asyncio.sleep(1)

# Executar
asyncio.run(receber_alertas())
```

### Exemplo - Conexão em JavaScript

```javascript
// Conecta ao WebSocket
const alertasWs = new WebSocket('ws://localhost:8765/alertas');

alertasWs.onopen = () => {
  console.log('✅ Conectado ao servidor de alertas');
};

alertasWs.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  const alerta = msg.alerta;
  
  console.log(`🚨 ALERTA: ${alerta.ativo}`);
  console.log(`   Nível: ${alerta.nivel}`);
  console.log(`   Entrada: ${alerta.dados_mercado.entrada_minima}`);
  
  // Sua lógica aqui
  processarAlerta(alerta);
};

alertasWs.onerror = (error) => {
  console.error('❌ Erro WebSocket:', error);
};

alertasWs.onclose = () => {
  console.log('❌ Desconectado. Reconectando em 5s...');
  setTimeout(conectarAlertas, 5000);
};

function processarAlerta(alerta) {
  // Validação básica
  if (!alerta.id || !alerta.ativo) {
    console.error('Alerta inválido:', alerta);
    return;
  }
  
  // Executa comércio (exemplo)
  if (alerta.nivel === 'CRÍTICO') {
    console.log(`📈 Executando entrada: ${alerta.dados_mercado.entrada_minima}`);
    // chamar API de execução
  }
}
```

---

## 3. Email (Backup)

Se WebSocket falhar, alerta é entregue por email.

### Formato Email

**Subject:** `[CRÍTICO] WIN$N - Volatilidade Extrema`

**Body (HTML):**
```html
<!DOCTYPE html>
<html>
<head><style>...css...</style></head>
<body>
  <h1>🚨 ALERTA DE OPORTUNIDADE</h1>
  
  <h3>📊 Padrão Detectado</h3>
  <p>Volatilidade Extrema (2.3σ)</p>
  
  <h3>💰 Dados de Mercado</h3>
  <table>
    <tr><td>Preço Atual:</td><td>89.250</td></tr>
    <tr><td>Entrada (banda):</td><td>89.100 - 89.300</td></tr>
    <tr><td>Stop Loss:</td><td>88.800</td></tr>
    <tr><td>Take Profit:</td><td>91.000</td></tr>
  </table>
  
  <h3>📈 Risk:Reward</h3>
  <p>1:2.5</p>
  
  <p><small>ID: 550e8400... | ⏰ 2026-02-20 14:23:45</small></p>
</body>
</html>
```

---

## 4. SMS (v1.2 - Futuro)

Ativação condicional: Se taxa de falha de email > 2% em 30 dias.

```
Formato:
[C] WIN$N 89.250 E:89.1-300 SL:88.800 R:1 RW:2.5 ...
```

---

## 5. REST API (Futuro - v1.2)

### GET /alertas/historico

Lista alertas históricos com filtros.

**Parâmetros:**
```
GET /alertas/historico?
  data_inicio=2026-02-20&
  data_fim=2026-02-21&
  ativo=WIN$N&
  padrão=volatilidade_extrema&
  nivel=CRÍTICO&
  limit=50
```

**Resposta 200 OK:**
```json
{
  "total": 15,
  "alertas": [
    {
      "id": "550e8400-...",
      "timestamp_deteccao": "2026-02-20T14:23:45Z",
      "ativo": "WIN$N",
      "padrão": "volatilidade_extrema",
      "status": "EXECUTADO",
      "operador": "trader1",
      "pnl": 250.00
    }
  ]
}
```

---

## 6. Códigos de Erro

| Código | Significado | Ação |
|--------|-------------|------|
| 1000 | Fechamento normal | Reconectar |
| 1001 | Saída normal | Reconectar |
| 1006 | Conexão perdida | Reconectar com backoff |
| 4000 | Token inválido | Verificar autenticação |
| 4001 | Não autorizado | Verificar permissões |
| 4002 | Limite de taxa | Diminuir frequência |

---

## 7. Troubleshooting

### WebSocket não conecta

```python
# Verificar firewall
nc -zv localhost 8765

# Verificar token
DEBUG: token_env = os.getenv("WEBSOCKET_TOKEN")
if not token:
    print("❌ WEBSOCKET_TOKEN não definido")
```

### Alertas não chegam

1. Verificar `alertas.habilitado = true` em `config/alertas.yaml`
2. Verificar logs: `tail -f logs/alertas.log`
3. Verificar se detector está habilitado: `detection.volatilidade.habilitado = true`

### Latência alta (>30s)

- Verificar carga do servidor: `top`
- Verificar tamanho da fila: `SELECT COUNT(*) FROM entrega_audit WHERE status='PENDENTE'`
- Aumentar thread pool SMTP

---

## 8. Integração com MT5

Após receber alerta WebSocket:

```python
import MetaTrader5 as mt5

async def executar_alerta(alerta):
    # Conecta MT5
    if not mt5.initialize():
        return False
    
    # Cria ordem
    ordem_req = {
        "action": mt5.TRADE_ACTION_BUY,
        "symbol": "WINFUT",  # Converter WIN$N → WINFUT
        "volume": 1.0,
        "type": mt5.ORDER_TYPE_MARKET,
        "price": alerta['dados_mercado']['entrada_minima'],
        'takeprofit': alerta['dados_mercado']['take_profit'],
        'stoploss': alerta['dados_mercado']['stop_loss'],
        'comment': f"Alerta: {alerta['id']}",
        'type_filling': mt5.ORDER_FILLING_IOC,
        'type_time': mt5.ORDER_TIME_GTC,
    }
    
    # Envia ordem
    result = mt5.order_send(order_req)
    
    if not result or result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Erro: {result.comment if result else 'Desconhecido'}")
        return False
    
    print(f"✅ Ordem enviada: {result.order}")
    return True
```

---

## 9. Monitoramento

### Métricas Chave

```
GET /metricas

{
  "total_alertas_hoje": 12,
  "taxa_entrega": 0.98,  // 98% entregues
  "latencia_p95_ms": 280,
  "fila_tamanho": 3,
  "websockets_conectados": 2,
  "uptime_horas": 48
}
```

### Dashboard

Acesse: `http://localhost:3000/alertas/dashboard`

---

## 10. Segurança

### Autenticação

```
Token JWT válido por 24 horas
Refresh token: renovar a cada 23h 50m
```

### Rate Limiting

```
- 100 alertas/minuto máximo
- 1 alerta/padrão/minuto (strict)
- Deduplicação >95%
```

### Auditoria Completa

Todos os alertas, entregas e ações registrados em SQLite append-only (CVM)

---

**Documentação Técnica Completa pronta para uso em v1.1.0** ✅
