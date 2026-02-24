# 📋 GitHub Issues Sprint 1 - Criadas 24/02/2026

**Status:** ✅ READY FOR CREATION
**Created:** 2026-02-23T23:50:00Z
**Sprint:** Sprint 1 (27/02-05/03)
**Total Issues:** 5 (#66-#70)

---

## 💼 ISSUE #66: TODO-1 Load Dataset + ML-Based Labeling

**Status:** NEW
**Assignee:** ML Expert
**Priority:** P0 - BLOCKER
**Estimate:** 2-3h
**Due:** 26/02 EOD

### Title
```
TODO-1: Load Dataset + Feature Engineering + Validation
```

### Description
```markdown
## Objetivo
Carregar dataset final, aplicar labeling ML-based, extrair 24 features engineered,
validar splits, e salvar pipeline ready para Day 1 de Sprint 1.

## Acceptance Criteria (7 AC - All Must Pass)

1. **AC1:** Dataset carregado (mínimo 1.000 samples)
   - Load from: backtest_optimized_results.json
   - Validation: Shape checked, types validated
   - Evidence: test_dataset_loading() PASSED

2. **AC2:** Labels validados (consistency checks aprovadas)
   - Labeling strategy: ML-based thresholding
   - Validation: No duplicates, no nulls, distribution check
   - Evidence: test_label_validation() PASSED

3. **AC3:** 24 features extraídas e validadas
   - Features: 6 groups (Volatilidade, Momentum, MA, Padrões, Lags, Correlação)
   - Validation: No NaN in any feature, statistics computed
   - Evidence: test_feature_engineering() PASSED

4. **AC4:** Train/Valid/Test splits criados (70/15/15)
   - Train: 70% (0.7 probability)
   - Valid: 15% (0.15 probability)
   - Test: 15% (0.15 probability)
   - Evidence: test_data_splitting() PASSED with exact percentages

5. **AC5:** Estatísticas computadas (mean, std, skewness, kurtosis)
   - Output: stats.json com todas métricas
   - Validation: No infinite values, all numerical
   - Evidence: test_statistics_computation() PASSED

6. **AC6:** Feature names salvos em production format
   - File: feature_names.json
   - Format: ["feature_1", "feature_2", ..., "feature_24"]
   - Validation: Order preserved, no duplicates
   - Evidence: test_feature_names_persistence() PASSED

7. **AC7:** Quality gates passaram (all 7 assertions green)
   - Gate checks: Dataset integrity + Feature validity + Split correctness
   - Validation: All assertions True
   - Evidence: test_quality_gates() PASSED

## Implementation Guide (5 Steps)

### Step 1: Setup Environment
```python
# Create virtual env if needed
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install pandas numpy scikit-learn xgboost lightgbm
```

### Step 2: Load Dataset
- File: `backtest_optimized_results.json`
- Columns: close, high, low, vol, timestamp, price_change_direction
- Validation: print(df.info(), df.describe())
- Output: DataFrame with shape (N, 7)

### Step 3: Apply ML-Based Labeling
- Strategy: Threshold on price_change_direction
  - If change >= threshold: Label = 1 (BUY)
  - If change < threshold: Label = 0 (HOLD/SELL)
- Threshold: sigma-based (e.g., 1.5 * std)
- Output: Added column 'label' to DataFrame

### Step 4: Feature Engineering (24 Features)
Extract features into 6 groups:
1. **Volatilidade (4):** Bollinger Bands, ATR, Historical Vol, 3-Sigma
2. **Momentum (4):** RSI, MACD, ROC, OBV
3. **Moving Average (5):** SMA 50, EMA 9/21, slopes
4. **Padrões (3):** Mean reversion, Volume spike, Impulse
5. **Lags (9):** Return lags, Close/volume lags
6. **Correlação (2):** 20-period correlation, Trend strength

Output: DataFrame with shape (N, 24+1 including label)

### Step 5: Validate Splits + Save
```python
# Create splits
train_idx = np.random.choice(len(df), size=int(0.7*len(df)), replace=False)
remaining = ~np.isin(np.arange(len(df)), train_idx)
valid_idx = np.random.choice(np.where(remaining)[0], size=int(0.15*len(df)), replace=False)
test_idx = np.where(~np.isin(np.arange(len(df)), np.concatenate([train_idx, valid_idx])))[0]

# Verify splits
assert len(train_idx) / len(df) ≈ 0.70
assert len(valid_idx) / len(df) ≈ 0.15
assert len(test_idx) / len(df) ≈ 0.15

# Save
df_train = df.iloc[train_idx]
df_valid = df.iloc[valid_idx]
df_test = df.iloc[test_idx]

# Save artifacts
df_train.to_json('data/train.json')
df_valid.to_json('data/valid.json')
df_test.to_json('data/test.json')
json.dump(feature_names, open('data/feature_names.json', 'w'))
json.dump(stats_dict, open('data/statistics.json', 'w'))
```

## Unit Tests (7 Test Cases - All Must PASS)

| Test | Description | Expected |
|------|-------------|----------|
| `test_dataset_loading()` | Load + shape check | ✅ PASS |
| `test_label_validation()` | No duplicates, no nulls | ✅ PASS |
| `test_feature_engineering()` | 24 features extracted | ✅ PASS |
| `test_data_splitting()` | 70/15/15 splits exact | ✅ PASS |
| `test_statistics_computation()` | Stats computed, no inf | ✅ PASS |
| `test_feature_names_persistence()` | Names saved, order OK | ✅ PASS |
| `test_quality_gates()` | All 7 assertions pass | ✅ PASS |

## Files Modified/Created
- `data/train.json` - Training set (70%)
- `data/valid.json` - Validation set (15%)
- `data/test.json` - Test set (15%)
- `data/feature_names.json` - Feature names list
- `data/statistics.json` - Dataset statistics
- `tests/test_dataset_preparation.py` - Unit tests (7 cases)

## Blockers/Risks
- ⚠️ Dataset file missing: Check backtest_optimized_results.json exists
- ⚠️ Class imbalance: If >90% one class, adjust threshold
- ⚠️ NaN values: Fill with median/mean before feature extraction

## References
- DESENVOLVIMENTO_DE_TASKS_PRIORIZADAS_SPRINT1.md (TODO-1 specs)
- ML_FEATURE_ENGINEERING_v1.2.md (Feature definitions)
- Dataset: backtest_optimized_results.json
```

---

## 💼 ISSUE #67: TODO-2 Orders Executor Framework

**Status:** NEW
**Assignee:** Eng Sr
**Priority:** P0 - BLOCKER
**Estimate:** 8-10h
**Due:** 02/03 EOD

### Title
```
TODO-2,3,4: Orders Executor Framework (Risk Validators + Executor + Position Monitor)
```

### Description
```markdown
## Objetivo
Implementar framework completo de execução de ordens com 3 validadores de risco,
executor async com retry logic, monitor de posições, e integração E2E.

## Acceptance Criteria (10 AC - All Must Pass)

1. **AC1:** MT5 connection estabelecida e autenticada
   - Connection pooling: 3 connections minimum
   - Heartbeat: Every 30s
   - Timeout fallback: 5s max per request
   - Evidence: test_mt5_connection() PASSED

2. **AC2:** Orders enviadas successfully (async queue)
   - Queue type: asyncio.Queue or Redis
   - Processing: Non-blocking, fire-and-forget
   - Throughput: 50+ orders/minute
   - Evidence: test_order_execution() PASSED

3. **AC3:** Posições rastreadas em real-time
   - Update frequency: Every 5s
   - State tracking: open_positions dict
   - Auditability: All changes logged
   - Evidence: test_position_tracking() PASSED

4. **AC4:** Retry mechanism funcional (3x exponential backoff)
   - Retry 1: 1s delay
   - Retry 2: 2s delay
   - Retry 3: 4s delay
   - Evidence: test_retry_mechanism() PASSED

5. **AC5:** Error recovery + circuit breakers ativados
   - Breaker 1: -3% (alert)
   - Breaker 2: -5% (slow mode - 50% ticket size)
   - Breaker 3: -8% (halt all)
   - Evidence: test_error_recovery() PASSED

6. **AC6:** Audit logging completo (format auditável)
   - Log format: [timestamp] [level] [component] [message] [order_id]
   - Retention: 30 days minimum
   - Evidence: test_audit_logging() PASSED

7. **AC7:** Risk gates validados (3 validators aproved)
   - Gate 1: Capital Adequacy (equity >= 1.5x positions)
   - Gate 2: Correlation (max 70% correlation allowed)
   - Gate 3: Volatility Band (within ±3 sigma)
   - Evidence: test_risk_validator_gates() PASSED

8. **AC8:** Message queue estável (zero loss)
   - Persistence: All messages persisted
   - Ordering: FIFO guaranteed
   - Throughput: 100+ msg/s without loss
   - Evidence: test_message_queue() PASSED

9. **AC9:** Performance metrics <500ms P95
   - Latency P50: <100ms
   - Latency P95: <500ms
   - Latency P99: <1000ms
   - Evidence: test_performance_metrics() PASSED

10. **AC10:** E2E integration tests (10/10 PASS)
    - Full flow: Quote → Risk check → Order → Execution → Tracking
    - Coverage: Happy path + error scenarios
    - Evidence: test_e2e_integration() PASSED (10/10)

## Implementation Guide (4 Steps)

### Step 1: Design Risk Validator (3 Gates)
```python
class RiskValidator:
    def validate_capital_adequacy(self, equity, positions_value):
        # Gate 1: equity >= 1.5 * positions_value
        return equity >= 1.5 * positions_value

    def validate_correlation(self, positions):
        # Gate 2: max correlation 70%
        corr_matrix = calculate_correlation(positions)
        return all(corr_matrix < 0.70)

    def validate_volatility_band(self, price, volatility):
        # Gate 3: within ±3 sigma
        return (price - 3*volatility, price + 3*volatility)
```

### Step 2: Build Orders Executor (Async Queue)
```python
class OrdersExecutor:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.mt5_connection = MT5Connection()

    async def execute_order(self, order):
        await self.queue.put(order)

    async def process_queue(self):
        while True:
            order = await self.queue.get()
            for retry in range(3):
                try:
                    result = self.mt5_connection.send_order(order)
                    self.audit_log(f"Order {order.id} executed")
                    break
                except Exception as e:
                    if retry < 2:
                        await asyncio.sleep(2**retry)  # exponential backoff
```

### Step 3: Create Position Monitor (Real-time Tracking)
```python
class PositionMonitor:
    def __init__(self):
        self.positions = {}

    async def update_positions(self):
        while True:
            positions = self.mt5_connection.get_positions()
            self.positions = {p.ticket: p for p in positions}
            await asyncio.sleep(5)  # Update every 5s

    def get_position(self, ticket):
        return self.positions.get(ticket)
```

### Step 4: E2E Integration Testing
```python
@pytest.mark.asyncio
async def test_e2e_flow():
    # Setup
    executor = OrdersExecutor()
    validator = RiskValidator()
    monitor = PositionMonitor()

    # Create order
    order = Order(symbol="PETR4", qty=100, price=25.50)

    # Validate risk
    assert validator.validate_capital_adequacy(10000, 2500)
    assert validator.validate_correlation({})

    # Execute
    await executor.execute_order(order)
    await asyncio.sleep(1)

    # Verify in monitor
    assert monitor.get_position(order.id) is not None
```

## Unit Tests (10 Test Cases - All Must PASS)

| Test | Description | Expected |
|------|-------------|----------|
| `test_mt5_connection()` | Connection + auth | ✅ PASS |
| `test_order_execution()` | Async queue OK | ✅ PASS |
| `test_position_tracking()` | Real-time updates | ✅ PASS |
| `test_retry_mechanism()` | Exponential backoff | ✅ PASS |
| `test_error_recovery()` | Circuit breaker logic | ✅ PASS |
| `test_audit_logging()` | Format + retention | ✅ PASS |
| `test_risk_validator_gates()` | 3 gates OK | ✅ PASS |
| `test_message_queue()` | Zero loss FIFO | ✅ PASS |
| `test_performance_metrics()` | P95 <500ms | ✅ PASS |
| `test_e2e_integration()` | Full flow OK | ✅ PASS |

## Files to Create
- `src/orders/risk_validator.py` - 3 validation gates
- `src/orders/executor.py` - Async queue processor
- `src/orders/position_monitor.py` - Real-time tracking
- `src/orders/mt5_connection.py` - MT5 interface
- `tests/test_orders_e2e.py` - Integration tests

## References
- DESENVOLVIMENTO_DE_TASKS_PRIORIZADAS_SPRINT1.md (TODO-2,3,4 specs)
- ARQUITETURA_MT5_v1.2.md (MT5 architecture design)
- RISK_FRAMEWORK_v1.2.md (Risk validator specs)
```

---

## 📊 ISSUE #68: TODO-3 Risk Validators (Sub-task of #67)

**Status:** NEW
**Assignee:** Eng Sr
**Priority:** P0 - BLOCKER
**Estimate:** 2-3h
**Due:** 28/02 EOD
**Depends On:** #67 (Orders Executor Framework)

### Title
```
TODO-3: Implement 3 Risk Validation Gates
```

### Description
```markdown
## Objetivo (Sub-task de #67)
Implementar os 3 validadores de risco (Capital Adequacy, Correlation, Volatility Band)
com testes unitários completos.

## AC (3 Core AC)
1. Capital Adequacy: equity >= 1.5 * positions_value
2. Correlation Check: max 70% allowed
3. Volatility Band: ±3 sigma from current price

## Implementation
See #67 Step 1 (RiskValidator class design)

## Files
- `src/orders/risk_validator.py` - Main implementation
- `tests/test_risk_validators.py` - Unit tests (3 gates)

## Part of Epic
[#67 Orders Executor Framework](#issue-67-todo-2-orders-executor-framework)
```

---

## 📊 ISSUE #69: TODO-4 Position Monitor (Sub-task of #67)

**Status:** NEW
**Assignee:** Eng Sr
**Priority:** P0 - BLOCKER
**Estimate:** 2h
**Due:** 01/03 EOD
**Depends On:** #67 (Orders Executor Framework)

### Title
```
TODO-4: Implement Real-Time Position Monitor
```

### Description
```markdown
## Objetivo (Sub-task de #67)
Implementar monitoramento em tempo real de posições abertas com atualização a cada 5s.

## AC (2 Core AC)
1. Update frequency: Every 5s from MT5
2. State tracking: All positions in memory dict

## Implementation
See #67 Step 3 (PositionMonitor class design)

## Files
- `src/orders/position_monitor.py` - Main implementation
- `tests/test_position_monitor.py` - Unit tests

## Part of Epic
[#67 Orders Executor Framework](#issue-67-todo-2-orders-executor-framework)
```

---

## 📧 ISSUE #70: Email Service Implementation Reference

**Status:** CLOSED ✅
**Assignee:** Eng Sr
**Priority:** P0 - BLOCKER (RESOLVED)
**Timeline:** 23/02 14:00-16:00
**Commits:** c52383e, a507166

### Title
```
RESOLVED: Email Service SMTP Configuration + Retry Logic
```

### Description
```markdown
## Status: ✅ COMPLETED

### Completion Evidence
- Commit c52383e: Email service implementation (961 LOC)
- Commit a507166: Tests + configuration
- AC Status: 5/5 PASSED
- Quality: 100% type hints, syntax validated

### Files Implemented
- `templates/alert_email.html` (161 LOC)
- `src/application/services/email_service.py` (340 LOC)
- `tests/test_email_service.py` (340 LOC)
- `.env.example` (20 LOC)
- `requirements_email.txt` (100 LOC)

### Features
✅ SMTP async with exponential backoff
✅ HTML + Text alternatives
✅ Rate limiting (60/minute)
✅ Comprehensive logging
✅ Unit tests 100% coverage

### Labels: closed, completed-23-02, email
```

---

## 📊 SUMEMA DE ISSUES

| # | Title | Assignee | Priority | Status | AC | Est |
|---|-------|----------|----------|--------|----|----|
| **#66** | Load Dataset + Labeling | ML Expert | P0 | NEW | 7 | 2-3h |
| **#67** | Orders Executor Framework | Eng Sr | P0 | NEW | 10 | 8-10h |
| **#68** | Risk Validators (sub) | Eng Sr | P0 | NEW | 3 | 2-3h |
| **#69** | Position Monitor (sub) | Eng Sr | P0 | NEW | 2 | 2h |
| **#70** | Email Service | Eng Sr | P0 | ✅ CLOSED | 5 | DONE |

**Total AC Defined:** 27 acceptance criteria
**Total Estimate:** 14-18h (4-5 days for 2-person team)
**Sprint Timeline:** 27/02-05/03 perfect fit

---

## 🚀 PRÓXIMOS PASSOS

1. ✅ **PO cria issues manualmente** no GitHub usando templates acima (30 min)
2. ✅ **Assign** Eng Sr a #67-69, ML Expert a #66
3. ✅ **Link** #68 e #69 como sub-tasks de #67
4. ✅ **Set milestones** para Gate 1 (05/03)
5. ✅ **Sprint planning** 27/02 com team

---

**Document Generated:** 2026-02-23T23:50:00Z
**Purpose:** Official GitHub Issues Specification for Sprint 1
**Status:** ✅ READY FOR CREATION
