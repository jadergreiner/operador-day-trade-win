# Configuração de Ambiente - Sprint 2 (P0 CRITICAL TASKS)

## 📋 Visão Geral

Este documento descreve o setup completo do ambiente para Sprint 2.

**Status:** ✅ PRONTO PARA EXECUÇÃO (P0 TASK #2)

---

## 🎯 Checklist de Setup

### FASE 1: Docker & Infraestrutura (30 min)

- [ ] **1.1 - Build Docker Compose**
  ```bash
  docker-compose -f docker-compose.yml up -d
  ```
  - PostgreSQL: `localhost:5432`
  - RabbitMQ: `localhost:5672` (management: `localhost:15672`)
  - Redis: `localhost:6379`

- [ ] **1.2 - Validar Serviços**
  ```bash
  docker ps
  docker-compose logs -f
  ```

### FASE 2: Python Virtual Environment (15 min)

- [ ] **2.1 - Criar venv**
  ```bash
  python -m venv venv
  source venv/bin/activate  # Linux/Mac
  venv\Scripts\activate.bat  # Windows
  ```

- [ ] **2.2 - Instalar Dependências**
  ```bash
  pip install --upgrade pip
  pip install -r requirements.txt
  ```

- [ ] **2.3 - Validar Instalação**
  ```bash
  pip list | grep fastapi
  python -c "import fastapi; print(fastapi.__version__)"
  ```

### FASE 3: CI/CD Pipeline (20 min)

- [ ] **3.1 - Setup GitHub Actions**
  ```
  .github/workflows/ci-cd-pipeline.yml
  ```
  - Validação de qualidade de código
  - Testes unitários
  - Testes de integração
  - Varredura de segurança

- [ ] **3.2 - Configurar Secrets** (GitHub Settings)
  ```
  STAGING_SERVER
  STAGING_USER
  STAGING_KEY
  DATABASE_URL
  RABBITMQ_URL
  REDIS_URL
  ```

### FASE 4: Feature Branches (10 min)

- [ ] **4.1 - Criar Branches**
  ```bash
  git branch feature/ATI-1-websocket-server
  git branch feature/ATI-2-risk-validator
  git branch feature/ATI-3-orders-executor
  # ... etc para ATI-4 até ATI-10
  ```

- [ ] **4.2 - Protect Main Branch**
  - Require pull request reviews
  - Require status checks
  - Require branches to be up to date

### FASE 5: TDD Test Fixtures (15 min)

- [ ] **5.1 - Instalar Testes**
  ```bash
  pytest --version
  pytest --collect-only
  ```

- [ ] **5.2 - Rodar Testes**
  ```bash
  pytest tests/ -v
  pytest tests/unit/ -v
  pytest tests/ --cov=src --cov-report=html
  ```

---

## 🔧 Configuração Detalhada

### Docker Compose

Arquivo: `docker-compose.yml`

**Serviços:**
```yaml
postgresql:15-alpine
  - Database principal
  - User: operador
  - Password: password123
  - Port: 5432

rabbitmq:3.12-management
  - Fila de mensagens
  - User: operador
  - Password: password123
  - AMQP Port: 5672
  - Management UI: 15672

redis:7-alpine
  - Cache distribuído
  - Port: 6379
```

### Requirements.txt

**Grupos de Dependências:**

1. **Web Framework**
   - `fastapi>=0.109.0`
   - `uvicorn[standard]>=0.27.0`
   - `websockets>=12.0`

2. **Message Queue & Async**
   - `pika>=1.3.0`
   - `aio-pika>=9.0.0`

3. **Database**
   - `sqlalchemy>=2.0.0`
   - `psycopg2-binary>=2.9.0`
   - `alembic>=1.12.0`

4. **Cache**
   - `redis>=5.0.0`

5. **ML & Data Science**
   - `numpy>=1.24.0`
   - `pandas>=2.0.0`
   - `scikit-learn>=1.3.0`
   - `xgboost>=2.0.0`
   - `shap>=0.43.0`

6. **Testing**
   - `pytest>=7.4.0`
   - `pytest-asyncio>=0.21.0`
   - `pytest-cov>=4.1.0`
   - `pytest-mock>=3.11.0`

7. **Code Quality**
   - `mypy>=1.5.0`
   - `black>=23.7.0`
   - `flake8>=6.1.0`
   - `pylint>=2.17.0`

### pytest.ini

**Configuração:**
- Test paths: `tests/`
- Markers: `unit`, `integration`, `critical`, `orders`, `risk`, `ml`
- Coverage: Mínimo requerido (será configurado)

### conftest.py

**Fixtures Compartilhadas:**

1. **Database**
   - `mock_db_connection`
   - `mock_db_session`
   - `database_url`

2. **Message Queue**
   - `mock_rabbitmq_connection`
   - `mock_rabbitmq_channel`
   - `mock_message_queue`

3. **Cache**
   - `mock_redis`
   - `redis_url`

4. **Web API**
   - `mock_fastapi_app`
   - `http_client`
   - `mock_http_response`

5. **WebSocket**
   - `mock_websocket`

6. **MT5**
   - `mock_mt5_account`
   - `mock_mt5_position`
   - `mock_mt5_order`

7. **ML/Data**
   - `sample_market_data`
   - `sample_features`
   - `sample_labels`
   - `mock_xgboost_model`

---

## 📊 Estrutura de Testes

### Unit Tests (sem dependências externas)

```
tests/unit/
├── test_risk_validator.py        # ATI-2
│   ├── TestRiskValidator (3 GATE + Circuit Breaker)
│   ├── TestCircuitBreaker (3 levels)
│   └── TestOverrideStructure (Trader/CIO/CFO)
│
├── test_orders_executor.py       # ATI-3
│   ├── TestOrdersExecutor
│   ├── TestPositionMonitor
│   ├── TestAuditLogging
│   ├── TestErrorHandling
│   └── TestPerformanceMetrics
│
├── test_websocket.py            # ATI-1
│   ├── TestWebSocketServer
│   ├── TestConnectionManager
│   ├── TestMessageHandling
│   ├── TestPingPong
│   └── TestPerformanceWebSocket
│
└── ... (mais vindo)
```

### Integration Tests

```
tests/integration/
├── test_orders_e2e.py           # Fluxo completo de ordem
├── test_market_data_pipeline.py # Pipeline de dados
├── test_ml_pipeline.py          # Pipeline de ML
└── ... (mais vindo)
```

---

## 🚀 Comandos de Execução

### Inicializar Ambiente

```bash
# 1. Docker
docker-compose up -d

# 2. Virtual Environment
python -m venv venv
source venv/bin/activate

# 3. Dependências
pip install -r requirements.txt

# 4. Validar
pytest tests/ --collect-only
```

### Rodar Testes

```bash
# Todos os testes
pytest tests/ -v

# Apenas testes unitários
pytest tests/unit/ -v

# Apenas testes críticos
pytest tests/ -m critical -v

# Com cobertura
pytest tests/ --cov=src --cov-report=html

# Teste específico
pytest tests/unit/test_risk_validator.py::TestRiskValidator::test_gate_1_capital_adequacy_sufficient -v

# Com output detalhado
pytest tests/unit/test_risk_validator.py -vv --tb=long
```

### Validar Código

```bash
# Black (formatting)
black src/ tests/

# isort (imports)
isort src/ tests/

# flake8 (linting)
flake8 src/ tests/

# mypy (type checking)
mypy src/ --strict

# pylint (analysis)
pylint src/
```

### Git Workflow

```bash
# Feature branch
git checkout -b feature/ATI-2-risk-validator

# Trabalhar
git add .
git commit -m "feat: implementar validador de risco (ATI-2)"

# Push
git push origin feature/ATI-2-risk-validator

# Pull request no GitHub
# → Review → Merge
```

---

## ✅ Checklist de Validação

### Après Setup

- [ ] Docker services estão rodando (verificar `docker ps`)
- [ ] Venv ativado (`which python` aponta para venv)
- [ ] Dependências instaladas (`pip list` mostra `fastapi`, etc)
- [ ] Pytest encontra testes (`pytest --collect-only` mostra testes)
- [ ] Testes rodam (`pytest tests/ -v` tem output)

### Após Implementação

- [ ] Testes passam (`pytest tests/ -v` - 0 failures)
- [ ] Código formatado (`black --check src/`)
- [ ] Imports organizados (`isort --check-only src/`)
- [ ] Linting OK (`flake8 src/` - sem erros)
- [ ] Types validados (`mypy src/ --strict`)
- [ ] Cobertura >= 90% (`pytest --cov=src`)
- [ ] Git branch atualizado (`git pull origin main`)
- [ ] Commit mensagem em português

---

## 🐛 Troubleshooting

### Docker não inicia

```bash
# Ver logs
docker-compose logs -f

# Limpar e reiniciar
docker-compose down -v
docker-compose up -d
```

### Testes falham em conexão

```bash
# Validar conexões
psql -U operador -d operador_db -h localhost
# ou
redis-cli ping
# ou
rabbit_admin CLI
```

### Dependências conflitantes

```bash
# Recriar venv limpo
rmvirtualenv operador  # ou rm -rf venv
python -m venv venv
pip install -r requirements.txt
```

---

## 📚 Próximos Passos (P0 TASKS)

1. **✅ P0 #1**: Team Kick-off → TEAM_KICKOFF_SPRINT2.md (DONE)
2. **⏳ P0 #2**: Environment Setup → Este documento (EXECUTING)
3. **⏳ P0 #3**: Design Reviews → ATI-1,2,3,4 designs
4. **⏳ P0 #4**: Environment Validation → CI/CD pipeline
5. **⏳ P0 #5**: TDD Test Implementation → `pytest` passing 100%

---

## 📞 Suporte

Para problemas:
- Verificar logs: `docker-compose logs -f`
- Consultar conftest.py para fixtures
- Rodar testes com `-vv --tb=long` para debug
- Conferir requirements.txt para versões

---

**Status:** 🟢 PRONTO PARA EXECUÇÃO
**Última Atualização:** Sprint 2 Kick-off
**Responsável:** Infra DevOps (Person 7)
