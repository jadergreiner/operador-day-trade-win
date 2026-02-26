# 📋 PHASE 4.1 - FIRST WEEK ACTION PLAN (01-05/03/2026)

**Objetivo:** Deploy completo em staging + 63+ testes PASSING + performance validated
**Timeline:** 5 dias
**Gate Decision:** 05/03 18:00 (Gate 4.1: Staging Readiness)

---

## 🗓️ DAY 1 (Monday 01/03) - INFRASTRUCTURE DEPLOYMENT

### Morning Standup (09:00-09:15)
**Location:** Video call
**Attendees:** All 9 personas

**Topics:**
- Team alignment on kickoff
- Day 1 priorities review
- Risk awareness
- Confirmation of role assignments

### Task 1.1: Azure Infrastructure Deploy (09:15-12:00)

**Owner:** DevOps Lead
**Duration:** 2h 45m
**Participants:** DevOps, Eng Sr (support)

**Checklist:**
```bash
# 1. Create Resource Group
az group create --name operador-dt-staging --location eastus

# 2. Validate Bicep syntax
az bicep build --file infrastructure/staging.bicep

# 3. Deploy infrastructure
az deployment group create \
  --resource-group operador-dt-staging \
  --template-file infrastructure/staging.bicep \
  --parameters environment=staging

# 4. Verify deployment
az resource list --resource-group operador-dt-staging --output table

# 5. Outputs export
az deployment group show \
  --resource-group operador-dt-staging \
  --name staging \
  --query properties.outputs
```

**Expected Outputs:**
- ✅ App Service name: `operador-dt-staging-app`
- ✅ PostgreSQL host: `operador-dt-db-staging-<suffix>.postgres.database.azure.com`
- ✅ Redis host: `operador-dt-cache.redis.cache.windows.net`
- ✅ Key Vault URI: `https://operador-dt-kv-<suffix>.vault.azure.net/`
- ✅ AppInsights key: saved

**Success Criteria:**
- ✅ 8/8 resources created
- ✅ All health checks PASS
- ✅ No errors in logs

### Task 1.2: Configure Application Environment (12:00-13:00)

**Owner:** Eng Sr
**Duration:** 1h
**Participants:** Eng Sr, DevOps

**Checklist:**
```bash
# 1. Create .env.staging
cat > .env.staging << EOF
ENVIRONMENT=staging
LOG_LEVEL=INFO
DATABASE_URL=postgresql://adminuser:password@...
REDIS_URL=redis://:password@...
JWT_SECRET=your-secret-key-staging
MODEL_PATH=s3://operador-models/xgboost_v1.pkl
EOF

# 2. Store secrets in Azure Key Vault
az keyvault secret set --vault-name operador-dt-kv \
  --name "DATABASE-URL" \
  --value "postgresql://..."

az keyvault secret set --vault-name operador-dt-kv \
  --name "REDIS-URL" \
  --value "redis://..."

# 3. Configure App Service settings
az webapp config connection-string set \
  --resource-group operador-dt-staging \
  --name operador-dt-staging-app \
  --connection-string-type PostgreSQL \
  --settings DefaultConnection=...
```

**Expected:**
- ✅ All secrets in Key Vault
- ✅ App Service environment configured
- ✅ Connection strings set

### Lunch Break (13:00-14:00)

### Task 1.3: Deploy Application Code (14:00-16:00)

**Owner:** Eng Sr + DevOps + QA
**Duration:** 2h
**Participants:** All 6 ops people

**Checklist:**
```bash
# 1. Clone repository
git clone https://github.com/jadergreiner/operador-day-trade-win.git
cd operador-day-trade-win
git checkout main

# 2. Build application (local or Docker)
# Option A: Docker
docker build -f Dockerfile -t operador-day-trade:staging .
docker tag operador-day-trade:staging <registry>/operador-day-trade:staging
docker push <registry>/operador-day-trade:staging

# Option B: Direct deployment
pip install -r requirements.txt
python -m pip install --upgrade pip

# 3. Database migrations
python -m alembic upgrade head

# 4. Initialize database
python scripts/init_database.py

# 5. Deploy to App Service
az webapp deployment source config-zip \
  --resource-group operador-dt-staging \
  --name operador-dt-staging-app \
  --src deployment.zip
```

**Parallel Task - QA:**
- Setup Locust environment
- Prepare test scenarios (OAuth, WebSocket, backtest)
- Create load testing database
- Brief team on procedures

**Expected:**
- ✅ Code ONLINE
- ✅ /health endpoint PASSING
- ✅ Database INITIALIZED
- ✅ Monitoring ACTIVE

### Task 1.4: Load ML Models (14:00-15:00)

**Owner:** ML Expert
**Duration:** 1h
**Participants:** ML Expert, Eng Sr

**Checklist:**
```bash
# 1. Download/prepare XGBoost model
aws s3 cp s3://operador-models/xgboost_v1.pkl ./models/

# 2. Load model in application
python -c "
import pickle
model = pickle.load(open('models/xgboost_v1.pkl', 'rb'))
print(f'Model loaded: {type(model)}')
"

# 3. Verify inference
python scripts/test_model_inference.py

# 4. Validate feature pipeline
python -c "
from src.ml import feature_engineering
print(f'Features: {feature_engineering.FEATURE_NAMES}')
print(f'Count: {len(feature_engineering.FEATURE_NAMES)}')
"
```

**Expected:**
- ✅ Model loaded successfully
- ✅ Inference working (test prediction)
- ✅ 29 features validated

### Task 1.5: Monitoring & Verification (15:00-17:00)

**Owner:** DevOps + QA
**Duration:** 2h
**Participants:** DevOps, QA Lead, Eng Sr

**Checklist:**
```bash
# 1. Verify all endpoints
curl -v https://operador-dt-staging-app.azurewebsites.net/health
curl -v https://operador-dt-staging-app.azurewebsites.net/oauth/login
curl -v https://operador-dt-staging-app.azurewebsites.net/backtest/health

# 2. Check AppInsights
# - Logs flowing?
# - Errors detected?
# - Performance metrics captured?

# 3. Run smoke tests
python -m pytest tests/smoke/ -v

# 4. Verify alerting
# - Create test alert
# - Verify notification
```

**Expected:**
- ✅ All endpoints accessible
- ✅ Monitoring capturing data
- ✅ Alerting working
- ✅ 0 critical errors

### End of Day Report (17:00-17:30)

**Responsible:** Eng Sr
**Attendees:** All 9 personas

**Report Contents:**
```
✅ COMPLETED:
- Azure infrastructure deployed (8/8 resources)
- Application code deployed
- Database migrations complete
- ML models loaded
- Monitoring active

⏳ IN PROGRESS:
- Performance baseline capture
- Test environment setup

🔴 BLOCKERS:
(none expected)

📅 TOMORROW (02/03):
- Integration testing suite execution
- Performance baseline continuation
- WebSocket stress testing prep
```

---

## 🗓️ DAY 2 (Tuesday 02/03) - INTEGRATION TESTING

### Morning Standup (09:00-09:15)

**Topics:**
- Day 1 recap & results
- Day 2 priorities
- Performance baseline review
- Any overnight issues?

### Task 2.1: OAuth Integration Tests (09:15-10:30)

**Owner:** QA Lead
**Duration:** 1h 15m
**Participants:** QA, Integration Eng

**Execution:**
```bash
cd tests/integration

# Run OAuth test suite
python -m pytest test_oauth_integration.py -v

# Expected output:
# test_oauth_login_success.py PASSED
# test_oauth_refresh_token.py PASSED
# test_oauth_token_expiration.py PASSED
# ... (12 tests total)

# Result expected: ✅ 12/12 PASSED (7.04s)
```

**Acceptance Criteria:**
- ✅ All 12 tests PASSED
- ✅ Execution time < 10s
- ✅ 0 flaky tests

### Task 2.2: WebSocket Integration Tests (10:30-11:30)

**Owner:** QA + Integration Eng
**Duration:** 1h
**Participants:** QA, Integration Eng, Eng Sr

**Execution:**
```bash
cd tests/integration

# Run WebSocket test suite
python -m pytest test_websocket_oauth_integration.py -v
python -m pytest test_websocket_authenticated_endpoints.py -v

# Expected output:
# WebSocket auth tests: ✅ 7/7 PASSED (15.31s)
# WebSocket endpoint tests: ✅ 13/13 READY (needs refinement)

# Total: ✅ 20 WebSocket tests
```

**Acceptance Criteria:**
- ✅ 7/7 auth tests PASSED
- ✅ 13 endpoint tests GREEN
- ✅ P95 latency < 500ms

### Task 2.3: XGBoost Inference Tests (11:30-13:00)

**Owner:** ML Expert + QA
**Duration:** 1h 30m
**Participants:** ML Expert, QA, Integration Eng

**Execution:**
```bash
cd tests/unit

# Run XGBoost test suite
python -m pytest test_backtest_server.py -v

# Expected output:
# TestBacktestServerModel: ✅ 6/6 PASSED
# TestBacktestStats: ✅ 7/7 PASSED
# TestPredictionModels: ✅ 2/2 PASSED
# TestRecommendations: ✅ 3/3 PASSED
# TestBacktestEndToEnd: ✅ 2/2 PASSED

# Total: ✅ 20/20 PASSED (14.17s)
```

**Acceptance Criteria:**
- ✅ 20/20 tests PASSED
- ✅ Inference time < 100ms
- ✅ F1 score > 0.65

### Lunch Break (13:00-14:00)

### Task 2.4: Full CI/CD Pipeline Execution (14:00-16:00)

**Owner:** Eng Sr + QA
**Duration:** 2h
**Participants:** All 6 ops

**Execution:**
```bash
# Trigger full CI/CD pipeline
git push origin main

# GitHub Actions automatically runs:
# ├─ ETAPA 1: OAuth (12 tests) → ✅ 7.04s
# ├─ ETAPA 2: WebSocket (6 tests) → ✅ 3.62s
# ├─ ETAPA 3: XGBoost (5 tests) → ✅ 37.91s
# ├─ ETAPA 4: Integration Auth (7 tests) → ✅ 15.31s
# ├─ ETAPA 5: Integration Endpoints (13 tests) → ✅ TBD
# ├─ ETAPA 6: Backtesting (20 tests) → ✅ 14.17s
# └─ Quality Gate → ✅ Code quality check
#
# Total expected: ~100 seconds
# Expected result: ✅ ALL PASSED

# Monitor in:
# https://github.com/jadergreiner/operador-day-trade-win/actions
```

**Parallel Task - Eng Sr:**
- Review test logs for any warnings
- Performance metrics comparison
- Document baseline metrics
- Identify any flaky tests

**Expected:**
- ✅ 63+ tests PASSING
- ✅ Pipeline duration < 120s
- ✅ 0 failures

### Task 2.5: Database Validation (16:00-17:00)

**Owner:** DevOps + Eng Sr
**Duration:** 1h

**Checklist:**
```bash
# 1. Verify schema
psql -h <host> -U adminuser -d operador_db -c "\dt"

# 2. Check data integrity
psql -h <host> -U adminuser -d operador_db -c "SELECT COUNT(*) FROM migrations;"

# 3. Run backups
az backup protection enable-for-vm ...

# 4. Connection pooling
# - Active connections < 50?
# - No deadlocks?
```

**Expected:**
- ✅ Schema intact
- ✅ Data valid
- ✅ Backups working

### End of Day Report (17:00-17:30)

**Report:**
```
✅ COMPLETED:
- All 63+ integration tests PASSED
- CI/CD pipeline validated (100s execution)
- Database integrity confirmed

📊 METRICS:
- OAuth: 12/12 tests PASSED
- WebSocket: 20 tests (7 passed + 13 ready)
- XGBoost: 20/20 tests PASSED
- Coverage: 100%

📅 TOMORROW (03/03):
- Performance baseline testing
- Load preparation
- UAT procedures review
```

---

## 🗓️ DAY 3 (Wednesday 03/03) - PERFORMANCE VALIDATION

### Morning Standup (09:00-09:15)

**Topics:**
- Day 2 results recap
- Day 3 performance focus
- Load testing prep review

### Task 3.1: Performance Baseline (09:15-12:00)

**Owner:** Integration Eng + QA
**Duration:** 3h
**Participants:** Integration Eng, QA, DevOps

**Execution:**
```bash
# 1. Single user performance baseline
ab -n 100 -c 1 https://operador-dt-staging-app.azurewebsites.net/health

# Expected: < 100ms average

# 2. API latency profiling
python scripts/profile_api_latency.py

# Expected output:
# GET /health: 12ms
# POST /oauth/login: 45ms
# POST /backtest/predict: 85ms
# POST /backtest/batch-predict: 250ms (100 records)
# GET /ws/status: 18ms

# 3. Database query performance
# -Enable slow query logging
# - Profile key queries
# - Identify indexing opportunities
```

**Expected:**
- ✅ Baseline metrics captured
- ✅ P50 < 100ms
- ✅ P95 < 300ms

### Task 3.2: Load Testing Preparation (13:00-14:00)

**Owner:** QA Lead
**Duration:** 1h

**Checklist:**
```bash
# 1. Setup Locust environment
pip install locust

# 2. Prepare test scenarios
cd tests/load_testing

# 3. Validate config
locust -f locustfile.py --host=https://... -u 0 -r 0 --run-time=0 -H

# Expected: No errors
```

### Task 3.3: WebSocket Concurrent Connection Test (14:00-15:30)

**Owner:** Integration Eng
**Duration:** 1h 30m

**Execution:**
```bash
# 1. Test 100 concurrent connections
python tests/websocket_concurrent_test.py --users=100

# Expected:
# - All 100 connections established
# - Latency P95 < 100ms
# - 0 timeouts

# 2. Test 250 concurrent connections
python tests/websocket_concurrent_test.py --users=250

# Expected:
# - 250+ connections stable
# - P95 < 200ms

# 3. Test 500 concurrent connections
python tests/websocket_concurrent_test.py --users=500

# Expected:
# - 500+ connections stable
# - P95 < 500ms
```

**Expected:**
- ✅ 500+ concurrent WebSocket connections stable
- ✅ P95 latency < 500ms

### End of Day Report (16:00-17:00)

---

## 🗓️ DAY 4 (Thursday 04/03) - LOAD TESTING EXECUTION

### Task 4.1: Baseline Load Test (100 users)

```bash
locust -f tests/load_testing/locustfile.py \
  --host=https://operador-dt-staging-app.azurewebsites.net \
  --users=100 --spawn-rate=5 --run-time=5m --headless
```

**Expected:**
- ✅ P95 latency < 100ms
- ✅ Error rate < 0.1%
- ✅ Throughput > 100 req/s

### Task 4.2: Medium Load Test (200 users)

```bash
locust -f tests/load_testing/locustfile.py \
  --host=https://... \
  --users=200 --spawn-rate=10 --run-time=10m --headless
```

**Expected:**
- ✅ P95 latency < 200ms
- ✅ Error rate < 0.1%

### Task 4.3: Stress Test (500 users)

```bash
locust -f tests/load_testing/locustfile.py \
  --host=https://... \
  --users=500 --spawn-rate=20 --run-time=15m --headless
```

**Expected:**
- ✅ P95 latency < 500ms
- ✅ Error rate < 1%
- ✅ System recovers cleanly

---

## 🎯 DAY 5 (Friday 05/03) - GATE 4.1 CHECKPOINT

### Morning (09:00-12:00): Final Validation

- [ ] All 63+ tests PASSING
- [ ] Performance metrics validated
- [ ] 0 critical issues
- [ ] Documentation complete

### Afternoon (13:00-17:00): Gate 4.1 Decision Meeting

**Committee:** CTO, Eng Sr, ML Expert, QA Lead + CFO/CIO observers

**Decision:**
```
✅ GO FOR UAT (default)
❌ NO-GO (only if critical blockers)
```

**Expected:** 🟢 GO

---

## ✅ SUCCESS CRITERIA (Gate 4.1)

**Technical:**
- ✅ 63+ tests PASSING (100%)
- ✅ Performance P95 < 500ms (500 users)
- ✅ WebSocket 500+ concurrent stable
- ✅ 0 critical issues
- ✅ Monitoring active & validated

**Process:**
- ✅ All tasks completed on time
- ✅ No blockers unresolved
- ✅ Team ready for UAT phase
- ✅ Documentation complete

**Financial:**
- ✅ Infrastructure cost tracked
- ✅ Timeline on schedule
- ✅ No scope creep

---

## 📊 Daily Metrics Tracking

| Day | OAuth | WebSocket | XGBoost | Integration | Total | Status |
|-----|-------|-----------|---------|-------------|-------|---------|
| 01/03 | Setup | Setup | Setup | Setup | Setup | ✅ |
| 02/03 | 12✅ | 20✅ | 20✅ | Inline | 63+ | ✅ |
| 03/03 | - | - | - | Perf | Ready | ✅ |
| 04/03 | - | - | - | Load | Ready | ✅ |
| 05/03 | Gate 4.1 Decision | **GO** | | | | ✅ |

---

*Document Version: 1.0*
*Ready for Execution: 01/03/2026*
