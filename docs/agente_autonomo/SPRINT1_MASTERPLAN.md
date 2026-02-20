# ⚙️ SPRINT 1 MASTERPLAN (27/02 - 05/03) - COORDENAÇÃO AGENTES

**Status:** 🎯 PLANEJAMENTO COMPLETO
**Agentes:** Eng Sr + ML Expert em PARALELO
**Gate Final:** 05/03 EOD

---

## 📊 TIMELINE PARALELO

```
27 FEB (SEGUNDA)
├─ 09:00-12:00
│  ├─ Eng Sr: Kick-off design MT5 architecture
│  └─ ML Expert: Kick-off dataset assembly
├─ 13:00-17:00
│  ├─ Eng Sr: MT5 REST API server (100 LOC)
│  └─ ML Expert: Feature engineering pipeline (200 LOC)
└─ 17:30: Daily standup (15 min)

28 FEB (TERÇA)
├─ 09:00-12:00
│  ├─ Eng Sr: Risk Validator gates (100 LOC)
│  └─ ML Expert: Dataset preprocessing script
├─ 13:00-17:00
│  ├─ Eng Sr: Orders Executor framework (120 LOC)
│  └─ ML Expert: XGBoost baseline model + test
└─ 17:30: Daily standup + tech sync

01 MAR (QUARTA)
├─ 09:00-12:00
│  ├─ Eng Sr: Code review + error handling
│  └─ ML Expert: Grid search setup (8 configs)
├─ 13:00-17:00
│  ├─ Eng Sr: Documentation + deploy mock
│  └─ ML Expert: Cross-validation tuning
└─ 17:30: Daily standup

02 MAR (QUINTA)
├─ 09:00-12:00
│  ├─ Eng Sr: Integration testing MT5 ↔ Risk
│  └─ ML Expert: Backtest validation grid
├─ 13:00-17:00
│  ├─ Eng Sr: Circuit breaker implementation
│  └─ ML Expert: Final model selection
└─ 17:30: Daily standup

03 MAR (SEXTA)
├─ 09:00-12:00
│  ├─ Eng Sr: Final testing + bug fixing
│  └─ ML Expert: Model serialization (pickle)
├─ 13:00-17:00
│  ├─ Eng Sr: Performance benchmarking
│  └─ ML Expert: Feature importance analysis
└─ 18:00: GATE CHECK 1 (Go/No-Go)

04-05 MAR (FIM DE SEMANA)
├─ Buffer time for fixes
└─ Sprint 1 gate checkpoint 05/03 EOD

GATE 1 CHECKPOINT (05/03 17:00)
├─ ✅ MT5 Architecture: Complete
├─ ✅ Risk Framework: Validated
├─ ✅ ML Features: Complete
├─ ✅ XGBoost Baseline: F1 >0.65 (esperado)
├─ ✅ Documentation: Sync'd
└─ 🎯 DECISION: Proceed to Sprint 2 (06/03) OR rework
```

---

## 🎯 DELIVERABLES POR DIA

### **27 FEV (SEGUNDA) - KICKOFF & DESIGN**

**Eng Sr Deliverables:**
- ✅ ARQUITETURA_MT5_v1.2.md (architecture design, 300 LOC)
- ✅ MT5 REST API server skeleton (100 LOC)
- ✅ Risk Validator interface definition

**ML Expert Deliverables:**
- ✅ ML_FEATURE_ENGINEERING_v1.2.md (spec, 24 features)
- ✅ Feature engineering skeleton code (50 LOC)
- ✅ Dataset load pipeline

**Sincronização:**
- 📝 Ambos leem US-001 + RISK_FRAMEWORK_v1.2
- 📝 Align em interfaces: RiskValidationResult, OrderRequest

---

### **28 FEV (TERÇA) - IMPLEMENTATION**

**Eng Sr Deliverables:**
- ✅ MT5 REST API (login, send_order, get_positions) - 150 LOC
- ✅ Risk Validator 3 gates (capital, correlation, volatility) - 150 LOC
- ✅ Orders Executor framework - 100 LOC
- **Total:** 400 LOC novo

**ML Expert Deliverables:**
- ✅ Feature engineering full pipeline (15-25 features) - 200 LOC
- ✅ Dataset preprocessing script - 100 LOC
- ✅ XGBoost baseline model - 80 LOC
- **Total:** 380 LOC novo

**Integration Points:**
- 📡 Risk Validator → Orders Executor (order queue pre-send)
- 📡 ML predictions → Risk Validator (score → confidence)

---

### **01 MAR (QUARTA) - TESTING & TUNING**

**Eng Sr Deliverables:**
- ✅ Unit tests: Risk Validator (3 gates)
- ✅ Mock MT5 API for testing
- ✅ Error handling + retry logic
- ✅ Logging + audit trail

**ML Expert Deliverables:**
- ✅ Grid search (8 hyperparameter configs)
- ✅ Cross-validation 5-fold
- ✅ Feature importance analysis
- ✅ Calibration of prediction scores [0-100%]

**Sync Checkpoint:**
- 📝 Eng Sr: Testa Risk Validator com dados reais
- 📝 ML Expert: Testa Feature engineering com WinFut histórico

---

### **02 MAR (QUINTA) - INTEGRATION & VALIDATION**

**Eng Sr Deliverables:**
- ✅ E2E integration test (MT5 mock → Risk → Orders)
- ✅ Circuit breaker gates (-4%, -6%, -10%)
- ✅ Position monitor (profit/loss tracking)
- ✅ Performance benchmarking

**ML Expert Deliverables:**
- ✅ Backtest validation (30 dias histórico)
- ✅ Win rate analysis (target 65%+)
- ✅ F1 score report (target >0.68)
- ✅ Model serialization (pickle/joblib)

**Critical Sync:**
- 📡 MT5 mock data precision (Eng Sr) ↔ ML backtest realism (ML Expert)
- 📡 Order timing simulation ↔ latency P95 <500ms requirement

---

### **03 MAR (SEXTA) - FINAL POLISH & GATE CHECK**

**Eng Sr Deliverables:**
- ✅ Final code review + cleanup
- ✅ Documentation (API specs, deployment guide)
- ✅ Bug fixes from testing
- ✅ Performance summary (latency, memory, CPU)

**ML Expert Deliverables:**
- ✅ Model performance summary (accuracy, precision, recall, F1)
- ✅ Feature importance ranking
- ✅ Threshold optimization (selecting 80% cutoff)
- ✅ Production model checkpoint

**GATE 1 DECISION (17:00):**
```
┌────────────────────────────────────────────┐
│ GATE 1 CRITERIA (05/03 17:00)              │
├────────────────────────────────────────────┤
│ Eng Sr:                                    │
│ ✅ MT5 REST API: Functional                │
│ ✅ Risk Validator: 3/3 gates working       │
│ ✅ Orders Executor: Queue + retry OK       │
│ ✅ E2E latency: P95 <500ms validated       │
│ ✅ Code review: 0 critical bugs            │
│                                            │
│ ML Expert:                                 │
│ ✅ Features: 15-25 engineered              │
│ ✅ Model: F1 >0.65 on test set             │
│ ✅ Backtest: Win rate 62-65%               │
│ ✅ Calibration: Score [0-100%] ready       │
│ ✅ Grid search: 8 configs evaluated        │
│                                            │
│ Documentation:                             │
│ ✅ SYNC_MANIFEST.json: Updated             │
│ ✅ Code: 100% type hints                   │
│ ✅ Commits: UTF-8 compliant                │
└────────────────────────────────────────────┘

DECISION:
├─ ✅ GO: Proceed Sprint 2 (06/03)
├─ ⚠️ CONDITIONAL: Fix X then proceed
└─ ❌ NO-GO: Rework Sprint 1 (redeploy 27/02)
```

---

## 💻 MODORIZAÇÃO & INTERFACES

### **Interface: RiskValidationResult (shared)**

```python
# Definido por Eng Sr
# Consumido por ML Expert para logging

@dataclass
class RiskValidationResult:
    passed: bool
    gate_1_capital: bool
    gate_2_correlation: bool
    gate_3_volatility: bool
    messages: List[str]
    timestamp: str
```

### **Interface: Order (shared)**

```python
# Definido por Eng Sr
# Enviado pelo ML Expert após prediction >80%

@dataclass
class Order:
    symbol: str  # "WINFUT_1min"
    volume: float  # 2.0 contracts
    order_type: str  # "OP_BUY" or "OP_SELL"
    price: float  # entry price
    stop_loss: float  # stop loss price
    take_profit: Optional[float]
    comment: str
    magic: int
```

### **Interface: MLPrediction (shared)**

```python
# Definido por ML Expert
# Consumido por Eng Sr para filtrar orders

@dataclass
class MLPrediction:
    pattern_detected: str  # "impulso", "reversal", "vol_spike"
    confidence_score: float  # 0-100%
    should_trade: bool  # confidence >= 80%
    timestamp: str
    feature_values: Dict[str, float]  # para auditoria
```

---

## 📡 DEPEND tátICAS DE SINCRONIZAÇÃO

### **Data Flow v1.2:**

```
MetaTrader5 (WINFUT_1min) ← Eng Sr observa
    ↓
ProcessadorBDI (v1.1 existente)
    ↓
DetectorVolatilidade → Features básicas
    ↓
ML_FeatureEngineer (ML Expert) → 15-25 features
    ↓
ML_Classifier (XGBoost) → score [0-100%]
    ↓ score >= 80%?
    ↓
RiscoValidator (Eng Sr) → 3 gates
    ├─ GATE 1: Capital adequado?
    ├─ GATE 2: Correlação OK?
    └─ GATE 3: Volatilidade normal?
    ↓ all 3 pass?
    ↓
OrdensExecutor (Eng Sr) → enqueue order
    ↓
MT5 REST API → send to MT5
```

### **Test Data Pipeline (Sprint 1):**

```
Histórico WinFut (17,280 candles, Jan 2025 - Feb 2026)
    ↓ [ML Expert processes]
    ↓
Dataset (X_train, X_val, X_test + scaler)
    ↓ [Eng Sr imports for mock testing]
    ↓
Risk Validator testing (corpus)
    ↓
Orders Executor testing (queue simulation)
    ↓
E2E mock test (latency validation)
```

---

## 🔍 QUALITY GATES

### **Code Quality (Both):**

```python
# Requirements:
├─ 100% type hints (mypy clean)
├─ docstrings para todas funções
├─ logging em todos métodos críticos
├─ Error handling com try/except
├─ Unit tests >80% coverage
└─ Code review checklist passed

# Tools:
├─ mypy --strict (type checking)
├─ pylint --disable=all --enable=E (errors only)
├─ pytest (unit tests)
└─ black (code formatting)
```

### **Performance Gates (Eng Sr):**

```
├─ Latência P95: <500ms (detection → execution)
├─ Memory peak: <100MB
├─ CPU: <40% during operation
├─ Orders/sec throughput: >10
└─ Retry success rate: >99%
```

### **ML Gates (ML Expert):**

```
├─ F1 Score (test): >0.65
├─ Precision (important for trading): >0.60
├─ ROC-AUC: >0.70
├─ Cross-val std: <0.05
├─ Backtest win rate: 62-65%
└─ Feature variation: <0.3σ between train/val
```

---

## 📁 FILE STRUCTURE (Sprint 1 Deliverables)

```
c:\repo\operador-day-trade-win\

├─ docs/agente_autonomo/
│  ├─ ARQUITETURA_MT5_v1.2.md ✅ (Eng Sr)
│  ├─ ML_FEATURE_ENGINEERING_v1.2.md ✅ (ML Expert)
│  ├─ SPRINT1_MASTERPLAN.md ← THIS FILE
│  └─ SYNC_MANIFEST.json (to update 05/03)
│
├─ src/infrastructure/
│  ├─ mt5_rest_server.py (Eng Sr, 200 LOC)
│  └─ mt5_mock_server.py (test version, 100 LOC)
│
├─ src/application/services/
│  ├─ risk_validator.py (Eng Sr, 150 LOC)
│  ├─ orders_executor.py (Eng Sr, 120 LOC)
│  ├─ ml_feature_engineering.py (ML Expert, 200 LOC)
│  ├─ ml_classifier.py (ML Expert, 100 LOC)
│  └─ position_monitor.py (Eng Sr, 80 LOC)
│
├─ src/scripts/
│  ├─ prepare_dataset_sprint1.py (ML Expert, 80 LOC)
│  ├─ backtest_sprint1.py (ML Expert, 100 LOC)
│  └─ test_e2e_sprint1.py (Both, 150 LOC)
│
└─ data/
   ├─ winfut_1min_labeled.csv (source)
   ├─ X_train_scaled.npy (output)
   ├─ y_train.npy (output)
   └─ feature_names.txt (output)
```

---

## ✍️ DAILY CHECKLIST

### **TODOS (Each agent tracks daily):**

**Eng Sr:**
- [ ] MT5 REST API: login + send_order
- [ ] Risk Validator Gate 1: capital adequacy
- [ ] Risk Validator Gate 2: correlation check
- [ ] Risk Validator Gate 3: volatility check
- [ ] Orders Executor: queue + retry logic
- [ ] Unit tests pass (mypy + pytest)
- [ ] E2E latency P95 <500ms
- [ ] Daily standup (15:30)

**ML Expert:**
- [ ] Feature engineering: 15-25 features done
- [ ] Dataset preprocessing: train/val/test split
- [ ] XGBoost baseline: F1 >0.65
- [ ] Grid search: 8 configs on track
- [ ] Backtest: win rate validation
- [ ] Cross-validation: 5-fold
- [ ] Model serialization ready
- [ ] Daily standup (15:30)

---

## 🚀 SUCCESS CRITERIA (GO/NO-GO)

```
SPRINT 1 COMPLETE WHEN:

Technical:
✅ 600+ LOC novo (Eng Sr)
✅ 400+ LOC novo (ML Expert)
✅ 100% type hints (both)
✅ mtpy --strict: 0 errors
✅ E2E test: Green light
✅ Performance targets: Met

ML Quality:
✅ F1 score: >0.65 (test set)
✅ Backtest: Win rate 62-65%
✅ Features: 15-25 engineered
✅ Calibration: Score [0-100%]

Documentation:
✅ Code documented
✅ SYNC_MANIFEST updated
✅ Commit messages UTF-8
✅ Review by PO/CIO (pending)

GATE 1 RESULT: ✅ GO or ❌ NO-GO
```

---

**Sprint 1 Status:** 🎯 READY TO LAUNCH 27/02
**Next Checkpoint:** 05/03 17:00 Gate Check
**Agentes:** Eng Sr + ML Expert coordenados
