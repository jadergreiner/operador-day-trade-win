"""
==============================================================================
Load Testing Configuration - Locust
Phase 4: Staging Load & Stress Testing (04/03)
Date: 26/02/2026

Objetivo: Simular carga no sistema para validar performance
- Baseline: 100 users
- Medium: 200 users  
- Stress: 500 users
==============================================================================

Instalacao:
  pip install locust

Execucao:
  # Interactive UI (http://localhost:8089)
  locust -f locustfile.py --host=https://operador-dt-staging-app.azurewebsites.net

  # CLI mode (automated)
  locust -f locustfile.py --host=https://... --users=100 --spawn-rate=5 --run-time=5m --headless

Parametros:
  --users: Numero de usuarios simulados (100, 200, 500)
  --spawn-rate: Usuarios criados por segundo
  --run-time: Duracao do teste (5m, 10m, 15m)
  --headless: Modo CLI (sem UI)
==============================================================================
"""

import random
import json
import time
from locust import HttpUser, task, between, events
from locust.clients import HttpSession
from datetime import datetime, timedelta

# ==============================================================================
# CONFIGURACOES GLOBAIS
# ==============================================================================

# URL base (sera passeda via --host)
HOST = "https://operador-dt-staging-app.azurewebsites.net"

# Mock JWT tokens (gerados no setup)
BEARER_TOKEN_TRADER = None
BEARER_TOKEN_USER = None
BEARER_TOKEN_ADMIN = None

# ==============================================================================
# SETUP - Criar tokens antes dos testes
# ==============================================================================

def create_jwt_token(role='user'):
    """
    Gera JWT token mock para teste
    Em staging real, fazer login primeiro para obter token
    """
    import jwt
    from datetime import datetime, timedelta
    
    secret = "your-secret-key"  # Same as app config
    payload = {
        "sub": f"test-user-{role}",
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, secret, algorithm="HS256")

@events.test_start.add_listener
def on_test_start(environment, **_):
    """Executado uma vez antes de iniciar os testes"""
    print("\n" + "="*80)
    print("🚀 INICIANDO LOAD TESTS - PHASE 4")
    print("="*80)
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")
    print(f"🎯 Host: {HOST}")
    print(f"👥 Config: Users={environment.runner.target_user_count}, Rate={environment.runner.spawn_rate}/s")
    
    # Criar tokens para usuarios diferentes
    global BEARER_TOKEN_TRADER, BEARER_TOKEN_USER, BEARER_TOKEN_ADMIN
    print("\n📝 Gerando JWT tokens para teste...")
    
    try:
        BEARER_TOKEN_TRADER = create_jwt_token('trader')
        BEARER_TOKEN_USER = create_jwt_token('user')
        BEARER_TOKEN_ADMIN = create_jwt_token('admin')
        print("✅ Tokens gerados com sucesso")
    except Exception as e:
        print(f"⚠️  Erro ao gerar tokens: {e} (usando fallback)")
        BEARER_TOKEN_TRADER = "test-bearer-token-trader"
        BEARER_TOKEN_USER = "test-bearer-token-user"
        BEARER_TOKEN_ADMIN = "test-bearer-token-admin"

@events.test_stop.add_listener
def on_test_stop(environment, **_):
    """Executado quando os testes terminam"""
    print("\n" + "="*80)
    print("🏁 TESTES FINALIZADOS")
    print("="*80)
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")

# ==============================================================================
# USER CLASS - Comportamentos de usuario
# ==============================================================================

class OperadorDayTradeUser(HttpUser):
    """
    Usuario simulado para load testing
    Simula comportamentos realistas de traders
    """
    
    # Aguardar entre 1-5 segundos entre tasks
    wait_time = between(1, 5)
    
    def on_start(self):
        """Executado quando usuario inicia"""
        self.token = random.choice([BEARER_TOKEN_TRADER, BEARER_TOKEN_USER])
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def on_stop(self):
        """Executado quando usuario para"""
        pass
    
    # ========================================================================
    # OAUTH ENDPOINTS - Login, refresh, logout
    # ========================================================================
    
    @task(2)  # 2% das tarefas
    def task_oauth_login(self):
        """Task: Fazer login"""
        credentials = {
            "email": f"trader{random.randint(1,100)}@operador.com",
            "password": "senha123"
        }
        with self.client.post(
            "/oauth/login",
            json=credentials,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                self.token = response.json().get("access_token")
                self.headers["Authorization"] = f"Bearer {self.token}"
                response.success()
            else:
                response.failure(f"Login failed: {response.status_code}")
    
    @task(1)  # 1% das tarefas
    def task_oauth_refresh(self):
        """Task: Refresh token"""
        with self.client.post(
            "/oauth/refresh",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                self.token = response.json().get("access_token")
                self.headers["Authorization"] = f"Bearer {self.token}"
                response.success()
            else:
                response.failure(f"Token refresh failed: {response.status_code}")
    
    # ========================================================================
    # WEBSOCKET - Conectar, enviar mensagens, desconectar
    # ========================================================================
    
    @task(5)  # 5% das tarefas
    def task_websocket_connect(self):
        """Task: Conectar ao WebSocket"""
        with self.client.get(
            "/ws/status",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "status" in data and data["status"] == "healthy":
                    response.success()
                else:
                    response.failure("WebSocket status unhealthy")
            else:
                response.failure(f"WebSocket status check failed: {response.status_code}")
    
    @task(3)  # 3% das tarefas
    def task_websocket_broadcast(self):
        """Task: Enviar mensagem broadcast"""
        message = {
            "type": "message",
            "content": f"Message from load test {datetime.now().isoformat()}",
            "timestamp": datetime.now().isoformat()
        }
        with self.client.post(
            "/ws/broadcast",
            json=message,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Broadcast failed: {response.status_code}")
    
    # ========================================================================
    # BACKTESTING - Predicoes, batch predictions
    # ========================================================================
    
    @task(10)  # 10% das tarefas (mais frequente)
    def task_backtest_predict(self):
        """Task: Fazer predicao individual"""
        # Gerar dados mock para predicao
        features = [round(random.random(), 4) for _ in range(29)]
        
        payload = {
            "close": features[0],
            "volume": features[1],
            "features": features
        }
        
        with self.client.post(
            "/backtest/predict",
            json=payload,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "prediction" in data and "confidence" in data:
                    response.success()
                else:
                    response.failure("Invalid prediction response")
            else:
                response.failure(f"Prediction failed: {response.status_code}")
    
    @task(5)  # 5% das tarefas
    def task_backtest_batch_predict(self):
        """Task: Batch prediction (100 records)"""
        # Gerar 100 registros mock
        batch_data = [
            {"close": round(random.random(), 4), "volume": random.randint(1000, 10000)}
            for _ in range(100)
        ]
        
        payload = {"data": batch_data}
        
        with self.client.post(
            "/backtest/batch-predict",
            json=payload,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "predictions" in data and len(data["predictions"]) >= 100:
                    response.success()
                else:
                    response.failure("Incomplete batch response")
            else:
                response.failure(f"Batch prediction failed: {response.status_code}")
    
    @task(2)  # 2% das tarefas
    def task_backtest_model_info(self):
        """Task: Obter info do modelo"""
        with self.client.get(
            "/backtest/model/info",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "model_type" in data and "version" in data:
                    response.success()
                else:
                    response.failure("Invalid model info response")
            else:
                response.failure(f"Model info failed: {response.status_code}")
    
    @task(3)  # 3% das tarefas
    def task_backtest_validate(self):
        """Task: Validar dados"""
        features = [round(random.random(), 4) for _ in range(29)]
        payload = {"features": features}
        
        with self.client.post(
            "/backtest/validate",
            json=payload,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Validation failed: {response.status_code}")
    
    @task(2)  # 2% das tarefas
    def task_backtest_health(self):
        """Task: Health check"""
        with self.client.get(
            "/backtest/health",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "status" in data and data["status"] == "healthy":
                    response.success()
                else:
                    response.failure("Unhealthy status")
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    # ========================================================================
    # GENERAL - Health checks, status
    # ========================================================================
    
    @task(5)  # 5% das tarefas
    def task_health_check(self):
        """Task: Health check geral"""
        with self.client.get(
            "/health",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

# ==============================================================================
# USUARIO ESPECIALIZADO - Trader behavior
# ==============================================================================

class TraderUser(OperadorDayTradeUser):
    """
    Trader com comportamento especializado
    - Mais predicoes
    - Menos login/logout
    """
    
    @task(3)
    def task_backtest_predict(self):
        """Trader faz mais predicoes"""
        super().task_backtest_predict()
    
    @task(2)
    def task_websocket_connect(self):
        """Trader monitora WebSocket mais"""
        super().task_websocket_connect()
    
    @task(1)
    def task_oauth_login(self):
        """Trader faz menos login"""
        super().task_oauth_login()

# ==============================================================================
# CONFIGURACOES DE TESTE - Diferentes cenarios
# ==============================================================================

"""
Para executar diferentes cenarios:

1. BASELINE (100 usuarios, 5 ramp-up/s, 5 minutos):
   locust -f locustfile.py --host=https://... \\
     --users=100 --spawn-rate=5 --run-time=5m --headless

2. MEDIUM (200 usuarios, 10 ramp-up/s, 10 minutos):
   locust -f locustfile.py --host=https://... \\
     --users=200 --spawn-rate=10 --run-time=10m --headless

3. STRESS (500 usuarios, 20 ramp-up/s, 15 minutos):
   locust -f locustfile.py --host=https://... \\
     --users=500 --spawn-rate=20 --run-time=15m --headless

4. INTERACTIVE UI (development):
   locust -f locustfile.py --host=https://... 
   (acessa http://localhost:8089 para controlar)

Metricas importantes a monitorar:
- Response Time (P95 < 500ms target)
- RPS (Requests Per Second)
- Failure Rate (< 1% target)
- 95th percentile latency
- Max concurrent connections
"""

# ==============================================================================
# NOTAS DE IMPLEMENTACAO
# ==============================================================================

"""
1. TOKENS: Em staging real, fazer login primeiro para obter JWT token real
   - Atualmente usando mock tokens
   - Implementar login dinamico se necessario

2. FEATURES: Dados utilizados sao mock/aleatorios
   - Em producao, usar dados realistas do backtest

3. ENDPOINTS: Assumindo que todos endpoints estao implementados
   - Se algum falhar, atualizar com versao correta

4. PERFORMANCE TARGETS:
   - Latencia P95: < 500ms
   - Error Rate: < 1%
   - Throughput: > 100 req/s
   - WebSocket concurrent: 500+

5. RESULTADOS: Locust gera relatorio HTML automatico
   - Salvo em: locust_<timestamp>.html
"""
