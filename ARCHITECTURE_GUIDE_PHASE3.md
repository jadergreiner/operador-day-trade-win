# Guia de Arquitetura - Phase 3 Integration

**Data:** 26/02/2026  
**Status:** 🟢 Production Ready  
**Versão:** 1.0.0

---

## 📋 Conteúdo

1. [Visão Geral da Arquitetura](#visão-geral-da-arquitetura)
2. [Componentes Principais](#componentes-principais)
3. [Integração OAuth + WebSocket](#integração-oauth--websocket)
4. [Backtesting com XGBoost](#backtesting-com-xgboost)
5. [Guia de Uso](#guia-de-uso)
6. [Quality Assurance](#quality-assurance)

---

## Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                   CLIENT (Browser/App)                   │
├─────────────────────────────────────────────────────────┤
│
│  1. LOGIN
│  POST /auth/login → {"username", "password"}
│  RESPONSE → {"access_token": "...", "refresh_token": "..."}
│
├─────────────────────────────────────────────────────────┐
│                      FASTAPI SERVER                       │
├─────────────────────────────────────────────────────────┤
│
│  2. WEBSOCKET CONNECTION
│  WebSocket /ws?token=<JWT>
│  ├─ Token Validation (JWT decode)
│  ├─ Role-based Access (trader/admin/user)
│  └─ Connection Acceptance
│
│  3. MESSAGE EXCHANGE
│  ├─ Client → ping, message, get_users, heartbeat
│  ├─ Server ← pong, broadcast, users_list
│  └─ Real-time bidirectional communication
│
│  4. PREDICTION REQUEST
│  POST /backtest/predict → {"features": {...}}
│  ├─ Load XGBoost model
│  ├─ Feature validation
│  ├─ Model inference
│  └─ RESPONSE → {"prediction": 1, "confidence": 0.85}
│
│  5. BROADCAST RESULT
│  WebSocket broadcast signal to all connected clients
│  with trade prediction and confidence score
│
└─────────────────────────────────────────────────────────┘
```

---

## Componentes Principais

### 1. OAuth/JWT Authentication (P5.2)

**Arquivo:** `src/application/token_manager_ati2.py`

```python
from src.application.token_manager_ati2 import TokenManager

token_manager = TokenManager()

# Login - gerar tokens
access_token, access_expiry = token_manager.create_access_token(
    username="trader01",
    user_id="user_001",
    role="trader"
)

# Refresh token
refresh_token, refresh_expiry = token_manager.create_refresh_token(
    username="trader01",
    user_id="user_001"
)

# Validar token
try:
    payload = token_manager.verify_token(access_token)
    print(f"User: {payload['sub']}, Role: {payload['role']}")
except JWTError:
    print("Token inválido ou expirado")

# Logout - adicionar à blacklist
token_manager.add_to_blacklist(access_token, access_expiry)
```

**Configuração:**
- Algorithm: HS256 (HMAC)
- Access token expiry: 30 minutos
- Refresh token expiry: 7 dias
- Password hashing: bcrypt

### 2. WebSocket Authentication (P4.4 + P5.2)

**Arquivo:** `src/application/websocket_auth_integration.py`

```python
from src.application.websocket_auth_integration import ws_auth_manager

# Conectar como gerenciador autenticado
client_id = str(uuid.uuid4())
user_info = await ws_auth_manager.connect(
    client_id=client_id,
    websocket=websocket,
    token=jwt_token  # Do OAuth
)
# user_info = {"username": "trader01", "user_id": "user_001", "role": "trader", ...}

# Broadcast para todos os clientes
await ws_auth_manager.broadcast({
    "type": "trade_signal",
    "prediction": 1,
    "confidence": 0.85,
    "timestamp": datetime.utcnow().isoformat()
})

# Enviar para usuário específico
await ws_auth_manager.send_to_user(
    user_id="user_001",
    message={"type": "private", "text": "Sua ordem foi executada"}
)

# Heartbeat com listagem de usuários ativos
await ws_auth_manager.send_heartbeat()
# broadcast: {"type": "heartbeat", "active_users": 5, ...}

# Desconectar
await ws_auth_manager.disconnect(client_id)
```

### 3. XGBoost Backtesting (P8.2)

**Arquivo:** `src/ml/backtest_server_xgboost.py`

```python
from src.ml.backtest_server_xgboost import BacktestServer, BacktestStats

# Inicializar servidor
backtest_server = BacktestServer()

# Fazer predição
features = {
    "volatilidade_1": 0.45,
    "rsi_14": 45.2,
    # ... 27 mais features...
}

prediction, confidence = backtest_server.predict(features)
# prediction: 0 (down) or 1 (up)
# confidence: float [0-1]

signal_strength = backtest_server.get_signal_strength(confidence)
# WEAK, MEDIUM, or STRONG

# Calcular estatísticas
stats = BacktestStats.calculate_stats(
    predictions=[1, 0, 1, 1],
    actuals=[1, 0, 1, 0],
    returns=[0.01, -0.002, 0.015, -0.003]
)
# stats = {
#   "total_signals": 4,
#   "winning_signals": 3,
#   "losing_signals": 1,
#   "win_rate": 75.0,
#   "average_return": 0.005,
#   "sharpe_ratio": 1.23,
#   "max_drawdown": -0.5
# }
```

---

## Integração OAuth + WebSocket

### Fluxo Completo

```
1. CLIENT: POST /auth/login
   Body: {"username": "trader01", "password": "secret"}
   ↓
2. SERVER: Verifica credenciais
   ↓
3. SERVER: Gera tokens (access + refresh)
   ↓
4. CLIENT: Recebe tokens
   Response: {
     "access_token": "eyJ...",
     "refresh_token": "eyJ...",
     "token_type": "bearer"
   }
   ↓
5. CLIENT: Abre WebSocket com token
   ws://localhost:8000/ws?token=eyJ...
   ↓
6. SERVER: Valida JWT
   - Decode token
   - Verifica signature (HS256)
   - Valida expiração
   - Verifica blacklist (logout)
   ↓
7. SERVER: Carrega informações do usuário
   - username
   - user_id
   - role (trader/admin/user)
   ↓
8. SERVER: Aceita conexão
   ↓
9. CLIENT: Conectado e autenticado
   - Pode enviar/receber mensagens
   - Acesso baseado em role
```

### Tipos de Mensagem

```python
# Ping/Pong (keep-alive)
{"type": "ping"}
→ {"type": "pong", "timestamp": "2026-02-26T20:30:00"}

# Get active users
{"type": "get_users"}
→ {"type": "users_list", "users": {"trader01": "trader", "admin01": "admin"}}

# Broadcast message
{"type": "message", "text": "Bom dia traders!"}
→ (enviado para todos os clientes)

# Heartbeat (token expiration check)
{"type": "heartbeat"}
→ {"type": "heartbeat", "active_users": 5, "timestamp": "..."}

# Trade signal (trader-only)
{"type": "trade_signal", "symbol": "EURUSD", "action": "BUY"}
→ (processado no /ws/trader)
```

---

## Backtesting com XGBoost

### Predição Única

```python
# FastAPI endpoint
POST /backtest/predict

Body:
{
  "features": {
    "volatilidade_1": 0.45,
    "volatilidade_2": 0.48,
    "volatilidade_3": 0.50,
    "volatilidade_4": 0.52,
    "rsi_14": 45.2,
    # ... 24 mais features...
  },
  "symbols": ["EURUSD", "GBPUSD"],
  "timestamp": "2026-02-26T20:30:00"
}

Response:
{
  "prediction": 1,           # 0=down, 1=up
  "confidence": 0.72,        # 72% confiança
  "signal_strength": "STRONG",
  "timestamp": "2026-02-26T20:30:00.123456",
  "model_version": "1.0.0-ati8"
}
```

### Predição em Batch

```python
POST /backtest/batch-predict

Body:
[
  {"features": {...}},
  {"features": {...}},
  {"features": {...}}
]

Response:
[
  {"prediction": 1, "confidence": 0.72, ...},
  {"prediction": 0, "confidence": 0.58, ...},
  {"prediction": 1, "confidence": 0.81, ...}
]
```

### Validação de Features

```python
POST /backtest/validate

Body:
{
  "volatilidade_1": 0.45,
  # ... features ...
}

Response:
{
  "valid": true,
  "expected_count": 29,
  "actual_count": 29,
  "missing_count": 0,
  "issues": []
}
```

### Simulação de Backtest

```python
POST /backtest/simulate

Body:
{
  "predictions": [1, 0, 1, 1, 0],
  "actuals": [1, 0, 1, 0, 0],
  "returns": [0.01, -0.002, 0.015, -0.003, -0.005]
}

Response:
{
  "simulation_results": {
    "total_signals": 5,
    "winning_signals": 3,
    "losing_signals": 2,
    "win_rate": 60.0,
    "average_return": 0.003,
    "sharpe_ratio": 0.95,
    "max_drawdown": -3.5
  },
  "timestamp": "2026-02-26T20:30:00",
  "recommendations": [
    "✅ Taxa de vitória aceitável",
    "⚠️ Sharpe ratio < 1.0 - risco elevado",
    "✅ Drawdown máximo aceitável"
  ]
}
```

---

## Guia de Uso

### Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/jadergreiner/operador-day-trade-win.git
cd operador-day-trade-win

# 2. Crie environment virtual
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# 3. Instale dependências
pip install -r requirements.txt
pip install python-jose passlib
pip install xgboost scikit-learn

# 4. Configure variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais
```

### Executar Servidor FastAPI

```bash
# Development
uvicorn src.application.main:app --reload --port 8000

# Production
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.application.main:app
```

### Testar OAuth

```bash
# Terminal 1: Inicie servidor
uvicorn src.application.main:app --reload

# Terminal 2: Teste login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"trader01","password":"password123"}'

# Response:
# {
#   "access_token": "eyJ...",
#   "refresh_token": "eyJ...",
#   "token_type": "bearer"
# }
```

### Testar WebSocket

```python
# client.py
import asyncio
import websockets
import json

async def connect():
    token = "eyJ..."  # Do login anterior
    uri = f"ws://localhost:8000/ws?token={token}"
    
    async with websockets.connect(uri) as websocket:
        # Enviar ping
        await websocket.send(json.dumps({"type": "ping"}))
        response = await websocket.recv()
        print(f"Pong: {response}")
        
        # Obter usuários
        await websocket.send(json.dumps({"type": "get_users"}))
        response = await websocket.recv()
        print(f"Users: {response}")

asyncio.run(connect())
```

### Testar Backtesting

```bash
# Health check
curl http://localhost:8000/backtest/health

# Model info
curl http://localhost:8000/backtest/model/info

# Fazer predição
curl -X POST http://localhost:8000/backtest/predict \
  -H "Content-Type: application/json" \
  -d '{
    "features": {
      "volatilidade_1": 0.45,
      # ... 28 mais features...
    }
  }'
```

---

## Quality Assurance

### Executar Testes Localmente

```bash
# Todos os testes
pytest -v

# Testes específicos
pytest tests/unit/test_ati2_auth_endpoints.py -v         # OAuth
pytest tests/performance/test_websocket_load.py -v       # WebSocket
pytest tests/unit/test_ati8_xgboost_training.py -v       # XGBoost
pytest tests/integration/test_websocket_oauth_integration.py -v
pytest tests/unit/test_backtest_server.py -v             # Backtesting

# Com coverage
pytest --cov=src --cov-report=html -v

# Performance
pytest tests/performance/ -v --durations=10
```

### CI/CD Pipeline

Todos os testes rodam automaticamente em:
- Push to main
- Pull requests
- Agendado (daily)

**Status:** Check `.github/workflows/tests.yml`

### Checklist de Deploy

- [ ] 63+ testes PASSING
- [ ] Type hints 100%
- [ ] Code review approved
- [ ] Documentation updated
- [ ] Performance benchmarks OK
- [ ] Security scan passed
- [ ] Staging deployment tested

---

## Troubleshooting

### WebSocket Connection Refused

```
Problema: ws://localhost:8000/ws?token=... recusa conexão
Solução:
  1. Verifique se servidor está rodando: uvicorn ...
  2. Verifique se token é válido: POST /auth/login
  3. Verifique se token não expirou (30 min)
  4. Refresh token se necessário: POST /auth/refresh-token
```

### Model File Not Found

```
Problema: ModuleNotFoundError ao carregar XGBoost model
Solução:
  1. Crie pasta de modelos: mkdir -p models/
  2. Treine modelo: python src/ml/train_xgboost_ati8.py
  3. Modelo salvo em: models/xgboost_model_ati8.pkl
```

### Feature Count Mismatch

```
Problema: Expected 29 features, got 24
Solução:
  1. Verifique dataset_loader_ati8.py
  2. Confirme que dataset tem 29 features
  3. Retraining model: python src/ml/train_xgboost_ati8.py
```

---

## Próximos Passos (Phase 4)

1. **Staging Deployment** (01-05/03)
   - Azure deployment
   - Load testing (100+ users)
   - Performance monitoring

2. **UAT (User Acceptance Testing)** (06-10/03)
   - Trader testing
   - Live data validation
   - Risk management verification

3. **go LIVE** (10/03)
   - FASE 1 Beta
   - R$ 50k capital
   - Live trading

---

**Last Updated:** 26/02/2026  
**Version:** 1.0.0  
**Status:** 🟢 Production Ready
