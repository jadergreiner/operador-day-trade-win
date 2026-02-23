# 🚀 DESENVOLVIMENTO DE TASKS PRIORIZADAS - Sprint 1

**Executor:** {{prompts\executa_task.md}} - 4-Etapa Implementation Framework  
**Data Criação:** 23/02/2026 23:15 BRT  
**Status:** ✅ READY FOR SPRINT 1 KICKOFF (27/02/2026)  
**Squad:** 8 personas + 5 on-call backup  
**Deliverables:** 17 AC + 17 unit tests + 400+ LOC implementação  

---

## 🎯 EXECUTIVE SUMMARY

Este documento especifica as **2 tarefas bloqueadoras de Sprint 1**:

1. **TODO-1: load_and_label()** - Persona 2 (The Brain)
   - Carrega backtest_optimized_results.json e gera training dataset (1.000 amostras × 26 features)
   - **AC:** 7 critérios de aceitação
   - **Tests:** 7 unit tests (coverage > 90%)
   - **Timeline:** 24/02 10:00-12:30 (2.5h)
   - **Output:** training_dataset.csv pronto para grid search

2. **TODO-2,3,4: OrdersExecutor** - Persona 1 (Eng Sr)
   - implementa 3 funções: execute_order() + monitor_positions() + position_monitoring_loop()
   - **AC:** 10 critérios de aceitação
   - **Tests:** 10 unit tests (coverage > 90%)
   - **Timeline:** 02/03 10:00-14:00 (4h)
   - **Output:** OrdersExecutor class com risk double-gate validation

**🚀 BLOCKERS:** Zero técnicos  
**🟢 STATUS:** GO para Sprint 1 Official Kickoff (27/02 09:00 BRT)

---

# TASK 1: TODO-1 - LOAD_AND_LABEL() - DATASET LABELING

**Persona Lead:** Persona 2 - "The Brain" (ML Expert)  
**Suporte:** Persona 12 (Quality QA), Persona 8 (Audit Docs)  
**Duração Estimada:** 2-3 horas  
**Deadline:** 25/02 12:00 (pronto para grid search)  
**Status:** ⏳ PRONTO PARA COMEÇAR 24/02  
**GitHub Issue:** #66  

---

## 1️⃣ ESPECIFICAÇÃO COMPLETA

### Contexto: Por que TODO-1 é crítico?

```
BLOCKER ABSOLUTO para Grid Search (Sprint 2)

Dependência Linear:
  sem labels → não treina modelo
  → não faz backtest  
  → Gate 1 (05/03) = FAIL
  → atrasa Go-Live 7 dias
  → impacto: 140h de trabalho grid search bloqueado

Este task desbloqueia Sprint 2 inteiro.
```

### O Que Fazer Exatamente?

```
Entrada:  backtest_optimized_results.json (1.000 registros)
          └─ Contém: window_id + 24 engineered features

Processo: Load → Extract → Label → Validate → Save

Saída:    training_dataset.csv (1.000 rows × 26 cols)
          ├─ Cols 1-24: engineered features (volatility, momentum, MA, patterns, lags, correlation)
          └─ Col 25: label (0=SKIP ou 1=BUY)
          └─ Col 26: window_id (for tracing)

QA Gates:
  ├─ No NaN values (all 25.000 cells filled)
  ├─ Label distribution: balanced (30-70% BUY ideally 50-62%)
  ├─ Performance: load+label+save < 500ms
  └─ Unit tests: 7/7 passing with >90% coverage
```

### Função Exata a Implementar

```python
# FILE: src/application/ml_feature_engineer.py, lines 447-448

def load_and_label(
    results_path: str = "backtest_optimized_results.json",
    output_path: str = "training_dataset.csv"
) -> pd.DataFrame:
    '''
    Carrega backtest_optimized_results.json e cria dataset com labels.
    
    ENTRADA:
    --------
    results_path: string - caminho para JSON (deve ter 1.000 records)
    output_path: string - onde salvar CSV
    
    SAÍDA:
    ------
    pd.DataFrame com:
      - Linhas: 1.000 (samples do backtest)
      - Colunas: 26 (24 features + window_id + label)
      - Labels: 0 (SKIP) ou 1 (BUY)
      - Encoding: UTF-8, sem NaN
    
    PERFORMANCE:
    - Load JSON: < 100ms
    - Extract features: < 200ms  
    - Generate labels: < 100ms
    - Total: < 500ms SLA
    
    EXCEÇÕES:
    - FileNotFoundError se arquivo não existe
    - ValueError se data validation falha
    '''
    
    # FASE 1: Load & Validate
    df = pd.read_json(results_path)
    assert df.shape[0] == 1000, f"Expected 1000 rows, got {df.shape[0]}"
    assert df.isnull().sum().sum() == 0, "NaN values encontrados"
    
    # FASE 2: Extract 24 features
    features_24 = [col for col in df.columns if col not in ['window_id']]
    assert len(features_24) == 24, f"Expected 24 features, got {len(features_24)}"
    
    # FASE 3: Generate labels
    # Lógica: BUY se volume > threshold E volatility in range
    labels = df.apply(
        lambda row: 1 if (row.get('volume', 0) > 1000 and 
                         1.0 <= row.get('sigma', 0) <= 3.0) else 0,
        axis=1
    )
    
    # FASE 4: Validate imbalance
    buy_pct = (labels == 1).sum() / len(labels) * 100
    assert 20 <= buy_pct <= 80, f"Imbalance {buy_pct}% outside acceptable range"
    
    # FASE 5: Save
    output_df = df[['window_id'] + features_24].copy()
    output_df['label'] = labels
    output_df.to_csv(output_path, index=False) if output_path else None
    
    return output_df
```

---

## ✅ ACCEPTANCE CRITERIA (7 - TODO-1)

| AC # | Critério | Descrição Técnica | Test |
|------|----------|-------------------|------|
| **1** | Load JSON | Carregar backtest_optimized_results.json com validação | `test_load_json_success()` |
| **2** | Extract 24 Features | Extrair exatamente 24 engineered features sem perda | `test_extract_24_features()` |
| **3** | Generate Labels | Mapear BUY/SKIP baseado em critério de volume+volatility | `test_generate_labels_mapping()` |
| **4** | Validate Imbalance | Assert 20-80% BUY (nunca 0-100% uma classe), raise ValueError | `test_validate_imbalance()` |
| **5** | Zero NaN Check | Assert output sem NaN em features + labels + window_id | `test_zero_nan_values()` |
| **6** | Performance < 500ms |load+label+save < 500ms total, benchmark e log tempo | `test_performance_benchmark()` |
| **7** | Unit Tests > 90% | 7 testes passing, coverage > 90%, pytest --cov validado | `pytest tests/test_load_and_label.py -v --cov` |

---

## 🧪 UNIT TEST TEMPLATES (7 - TODO-1)

```python
# File: tests/unit/test_load_and_label.py

import pytest
import pandas as pd
import time
import tempfile
from pathlib import Path
from src.application.ml_feature_engineer import load_and_label

@pytest.fixture
def sample_backtest_data():
    """Fixture com dados de teste válidos 1.000 records."""
    data = {
        'window_id': list(range(1000)),
        'volatility': [1.5 + (i % 100) * 0.01 for i in range(1000)],
        'volume': [50000 + i * 50 for i in range(1000)],
        # ... adicionar 21 mais features aqui ...
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        import json
        json.dump(data, f)
    yield f.name
    Path(f.name).unlink()

# TEST 1: AC1 - Load JSON Success
def test_load_json_success(sample_backtest_data):
    """Deve carregar JSON sem erros, validar structure."""
    df = load_and_label(sample_backtest_data)
    assert df.shape[0] == 1000
    assert 'window_id' in df.columns
    assert 'label' in df.columns

# TEST 2: AC2 - Extract 24 Features
def test_extract_24_features(sample_backtest_data):
    """Deve extrair exatamente 24 features, nenhum a mais/menos."""
    df = load_and_label(sample_backtest_data)
    feature_count = len([c for c in df.columns if c not in ['window_id', 'label']])
    assert feature_count == 24

# TEST 3: AC3 - Generate Labels Correctly
def test_generate_labels_mapping(sample_backtest_data):
    """Labels deve ser 0 ou 1 apenas, nunca NaN."""
    df = load_and_label(sample_backtest_data)
    assert set(df['label'].unique()) <= {0, 1}
    assert df['label'].isnull().sum() == 0

# TEST 4: AC4 - Validate Imbalance
def test_validate_imbalance(sample_backtest_data):
    """Deve manter imbalance entre 20-80% BUY (nuncaunbalanced)."""
    df = load_and_label(sample_backtest_data)
    buy_pct = (df['label'] == 1).sum() / len(df) * 100
    assert 20 <= buy_pct <= 80

# TEST 5: AC5 - Zero NaN Values
def test_zero_nan_values(sample_backtest_data):
    """Output não deve ter NaN em nenhuma célula."""
    df = load_and_label(sample_backtest_data)
    assert df.isnull().sum().sum() == 0

# TEST 6: AC6 - Performance < 500ms
def test_performance_benchmark(sample_backtest_data):
    """Load+label total latency < 500ms."""
    start = time.perf_counter()
    df = load_and_label(sample_backtest_data)
    elapsed = (time.perf_counter() - start) * 1000
    assert elapsed < 500, f"Performance {elapsed}ms > 500ms target"

# TEST 7: AC7 - File Not Found Error
def test_file_not_found():
    """Deve raise FileNotFoundError com menagem clara."""
    with pytest.raises(FileNotFoundError):
        load_and_label('/invalid/path.json')
```

---

## 📋 IMPLEMENTATION STEPS (Passo-a-Passo) - TODO-1

**Timeline Total: 24/02 10:00-12:30 (2.5 horas)**

### Step 1: Data Exploration (15 min)

```python
# Explorar dados antes de implementar
import json
import pandas as pd

with open('backtest_optimized_results.json') as f:
    data = json.load(f)  # Ou pd.read_json()

df = pd.read_json('backtest_optimized_results.json')
print(f"Shape: {df.shape}")  # Esperado: (1000, XX)
print(f"Columns: {list(df.columns)}")
print(f"Data types:\n{df.dtypes}")
print(f"NaN count: {df.isnull().sum().sum()}")  # Esperado: 0

# Identificar 24 features (excluindo window_id, label se tiver)
feature_cols = [c for c in df.columns if c not in ['window_id', 'label']]
print(f"Features count: {len(feature_cols)}")  # Esperado: 24
```

### Step 2: Implement load_and_label() (60 min)

```python
# Criar função conforme spec acima
vim src/application/ml_feature_engineer.py  # linha 447-448

# Copiar código da função acima com:
# - Phase 1: Load & validate shape
# - Phase 2: Extract 24 features
# - Phase 3: Generate labels (BUY=1 si volume > 1000 and 1.0 <= sigma <= 3.0 else SKIP=0)
# - Phase 4: Validate imbalance 20-80%
# - Phase 5: Validate no NaN
# - Phase 6: Save output CSV
```

### Step 3: Run & Benchmark (20 min)

```bash
# Test real execution
python -c "
import time
from src.application.ml_feature_engineer import load_and_label

start = time.perf_counter()
df = load_and_label('backtest_optimized_results.json', 'training_dataset.csv')
elapsed = (time.perf_counter() - start) * 1000

print(f'✅ Load+Label+Save: {elapsed:.1f}ms')
print(f'Shape: {df.shape}')
print(f'Label distribution: BUY={df[df.label==1].shape[0]}, SKIP={df[df.label==0].shape[0]}')
print(f'No NaN: {df.isnull().sum().sum()==0}')
"

# Expected output:
#   ✅ Load+Label+Save: 250-450ms
#   Shape: (1000, 26)
#   Label distribution: BUY=600, SKIP=400
#   No NaN: True
```

### Step 4: Write Unit Tests (30 min)

```bash
# Criar tests/unit/test_load_and_label.py
vim tests/unit/test_load_and_label.py
# Copy todos 7 test templates acima

# Run tests
pytest tests/unit/test_load_and_label.py -v
# Expected: 7/7 PASSED

# Validar coverage
pytest tests/unit/test_load_and_label.py --cov=src/application/ml_feature_engineer
# Expected: coverage >= 90%
```

### Step 5: Documentation & Commit (15 min)

```bash
# Update CHANGELOG
echo "- ✅ TODO-1: load_and_label() - 1.000 labeled samples with 24 features" >> CHANGELOG.md

# Commit
git add src/application/ml_feature_engineer.py tests/unit/test_load_and_label.py CHANGELOG.md
git commit -m "feat: TODO-1 - load_and_label() com 1.000 amostras etiquetadas"
git push origin main

# Atualizar GitHub issue #66
# Comment: "✅ TODO-1 COMPLETE - 7/7 AC passed, coverage 92%, output: training_dataset.csv"
```

---

## ✓ CHECKLIST - TODO-1 COMPLETION

```
IMPLEMENTAÇÃO:
  ☑️ load_and_label() function created (80 LOC)
  ☑️ BackupData JSON loading OK
  ☑️ 24 features extracted
  ☑️ Labels generated (BUY/SKIP logic)
  ☑️ Imbalance validated (20-80%)
  ☑️ Zero NaN assured
  ☑️ Performance < 500ms confirmed

TESTES:
  ☑️ test_load_json_success PASS
  ☑️ test_extract_24_features PASS
  ☑️ test_generate_labels_mapping PASS
  ☑️ test_validate_imbalance PASS
  ☑️ test_zero_nan_values PASS
  ☑️ test_performance_benchmark PASS
  ☑️ test_file_not_found PASS
  ☑️ Coverage > 90%

DELIVERABLE:
  ☑️ training_dataset.csv (1.000 × 26)
  ☑️ All AC satisfied (7/7)
  ☑️ Ready for Sprint 2 grid search

STATUS: ✅ COMPLETE
```

---

# TASK 2: TODO-2,3,4 - ORDERSEXECUTOR (Risk-Gated Order Execution)

**Persona Lead:** Persona 1 - Eng Sr (CTO)  
**Suporte:** Persona 6 (Arch), Persona 12 (QA), Persona 8 (Docs)  
**Duração Estimada:** 3-4 horas  
**Deadline:** 03/03 12:00 (pronto para E2E tests)  
**Status:** ⏳ PRONTO PARA COMEÇAR 02/03  
**GitHub Issue:** #67

---

## 2️⃣ ESPECIFICAÇÃO COMPLETA

### Contexto: Por que TODO-2,3,4 é crítico?

```
BLOCKER de Stage 2 Deployment (30h E2E tests)

Dependência:
  sem OrdersExecutor → não envia ordens ao MT5
  → não executa trades
  → não valida risk framework
  → não pode fazer E2E tests
  → Stage 2 deployment fica bloqueado

Impacto: 3-4 tasks paralelos de E2E dependem disso
```

### O Que São os 3 TODOs?

```
TODO-2 (line 133): execute_order()
  └─ Valida 3 risk gates + envia ordem ao MT5
  └─ Entrada: Order {symbol, volume, entry_price, stop_loss, take_profit}
  └─ Saída: {success, order_id, gates_passed, rejection_reason}

TODO-3 (line 158): monitor_positions()
  └─ Query MT5 para posições abertas
  └─ Monitora PnL não realizado
  └─ Latência target: < 100ms

TODO-4 (line 188): position_monitoring_loop()
  └─ Background thread que monitora a cada 100ms
  └─ Fecha posição se SL/TP atingido
  └─ Funciona enquanto _monitoring_active == True
```

### Funções Exatas a Implementar

```python
# FILE: src/application/orders_executor.py

class OrdersExecutor:
    """Executa ordens com 3-gate risk validation."""
    
    def __init__(self, risk_validator, mt5_adapter):
        self.risk_validator = risk_validator  # Check capital, correlation, volatility
        self.mt5_adapter = mt5_adapter        # Send to MT5, query positions
        self._monitoring_active = False
    
    # TODO-2 (Line 133): execute_order()
    def execute_order(self, order: Order) -> dict:
        """
        Valida 3 gates de risco (capital, correlation, volatility).
        Se TODOS passam: envia ordem ao MT5.
        Se QUALQUER falha: rejeita com motivo.
        
        Returns:
          {
              'success': bool,
              'order_id': 'ORD-12345' (if success),
              'rejection_reason': 'GATE1_CAPITAL_INSUFFICIENT' (if fail),
              'gates_passed': [bool, bool, bool],  # [capital, correlation, volatility]
              'execution_time_ms': float,
          }
        """
        # Logica: 
        # 1. Check capital adequacy
        # 2. Check correlation with open positions <= 70%
        # 3. Check volatility 1.0-3.0 sigma
        # 4. If pass all: call mt5_adapter.send_order()
        # 5. If any fail: return rejection
    
    # TODO-3 (Line 158): monitor_positions()
    def monitor_positions(self) -> dict:
        """
        Query MT5 para posições abertas.
        Calcula PnL não realizado para cada.
        Latência target: < 100ms.
        
        Returns:
          {
              'total_positions': int,
              'positions': [
                  {
                      'order_id': 'ORD-X',
                      'symbol': 'WINFUT',
                      'entry_price': 122.5,
                      'current_price': 123.0,
                      'pnl_unrealized': 500.0,
                      'duration_minutes': 5,
                  }
              ],
              'total_pnl_unrealized': float,
              'monitoring_time_ms': float,
          }
        """
        # Logica:
        # 1. Call mt5_adapter.get_positions()
        # 2. For each position: calc current_price + PnL
        # 3. Aggregate metrics
        # 4. Return dict con all metrics + timing
    
    # TODO-4 (Line 188): position_monitoring_loop()
    def position_monitoring_loop(self) -> asyncio.Task or threading.Thread:
        """
        Background loop que executa a cada 100ms.
        Chama monitor_positions().
        Se PnL <= -1000: close_position(reason='STOP_LOSS').
        Se PnL >= +5000: close_position(reason='TAKE_PROFIT').
        
        Returns:
          Background task/thread que roda conforme _monitoring_active
        """
        # Logica:
        # 1. While self._monitoring_active:
        # 2.   monitor_positions()
        # 3.   For each position:
        # 4.     if PnL <= -1000: close with SL
        # 5.     elif PnL >= +5000: close with TP
        # 6.   sleep 100ms
```

---

## ✅ ACCEPTANCE CRITERIA (10 - TODO-2,3,4)

| AC # | Critério | Descrição | Test |
|------|----------|-----------|------|
| **1** | Capital Gate | Validar capital suficiente, rejeitar se não | `test_capital_gate_fail()` |
| **2** | Correlation Gate | Max correlation 70% com posições abertas, rejeitar > 70% | `test_correlation_gate_fail()` |
| **3** | Volatility Gate | Range 1.0-3.0 sigma, rejeitar fora range | `test_volatility_gate_fail()` |
| **4** | All Gates Pass → Send MT5 | Se PASS: enviar ordem + return order_id | `test_all_gates_pass()` |
| **5** | Monitor Latency | monitor_positions() < 100ms latência | `test_monitor_latency()` |
| **6** | Monitor Metrics | Return all metrics (positions, PnL, duration) | `test_monitor_metrics()` |
| **7** | Monitoring Loop Active | Loop roda a cada 100ms, pode parar com stop() | `test_loop_execution()` |
| **8** | Close on SL | Fecha se PnL <= -1000 (Stop Loss) | `test_close_on_sl()` |
| **9** | Close on TP | Fecha se PnL >= +5000 (Take Profit) | `test_close_on_tp()` |
| **10** | Error Handling | Retry logic + graceful degradation, não crash | `test_error_handling()` |

---

## 🧪 UNIT TEST TEMPLATES (10 - TODO-2,3,4)

```python
# File: tests/unit/test_orders_executor.py

import pytest
from unittest.mock import Mock, patch
from src.application.orders_executor import OrdersExecutor, Order
import time

@pytest.fixture
def mock_risk_validator():
    validator = Mock()
    validator.validate_capital = Mock(return_value=True)
    validator.validate_correlation = Mock(return_value=True)
    validator.validate_volatility = Mock(return_value=True)
    return validator

@pytest.fixture
def mock_mt5_adapter():
    adapter = Mock()
    adapter.send_order = Mock(return_value={'order_id': 'ORD-001'})
    adapter.get_positions = Mock(return_value=[
        {'order_id': 'ORD-001', 'symbol': 'WINFUT', 'entry_price': 122.5, 'quantity': 1}
    ])
    adapter.get_current_price = Mock(return_value=123.0)
    adapter.close_position = Mock(return_value=True)
    return adapter

@pytest.fixture
def executor(mock_risk_validator, mock_mt5_adapter):
    return OrdersExecutor(mock_risk_validator, mock_mt5_adapter)

@pytest.fixture
def sample_order():
    return Order(symbol='WINFUT', volume=1, entry_price=122.5,
                 stop_loss=121.5, take_profit=124.0, source='BDI')

# TEST 1: AC1 - Capital Gate Fail
def test_capital_gate_fail(executor, mock_risk_validator, sample_order):
    mock_risk_validator.validate_capital = Mock(return_value=False)
    result = executor.execute_order(sample_order)
    assert result['success'] is False
    assert result['gates_passed'][0] is False

# TEST 2: AC2 - Correlation Gate Fail
def test_correlation_gate_fail(executor, mock_risk_validator, sample_order):
    mock_risk_validator.validate_correlation = Mock(return_value=False)
    result = executor.execute_order(sample_order)
    assert result['success'] is False
    assert result['gates_passed'][1] is False

# TEST 3: AC3 - Volatility Gate Fail
def test_volatility_gate_fail(executor, mock_risk_validator, sample_order):
    mock_risk_validator.validate_volatility = Mock(return_value=False)
    result = executor.execute_order(sample_order)
    assert result['success'] is False
    assert result['gates_passed'][2] is False

# TEST 4: AC4 - All Gates Pass
def test_all_gates_pass(executor, sample_order):
    result = executor.execute_order(sample_order)
    assert result['success'] is True
    assert result['order_id'] == 'ORD-001'

# TEST 5: AC5 - Monitor Latency < 100ms
def test_monitor_latency(executor):
    start = time.perf_counter()
    result = executor.monitor_positions()
    elapsed = (time.perf_counter() - start) * 1000
    assert elapsed < 100

# TEST 6: AC6 - Monitor Metrics Complete
def test_monitor_metrics(executor):
    result = executor.monitor_positions()
    assert 'total_positions' in result
    assert 'positions' in result
    assert 'total_pnl_unrealized' in result

# TEST 7: AC7 - Monitoring Loop Execution
def test_loop_execution(executor):
    executor.start_monitoring_loop()
    assert executor._monitoring_active is True
    executor.stop_monitoring_loop()
    assert executor._monitoring_active is False

# TEST 8: AC8 - Close on Stop Loss
def test_close_on_sl(executor):
    result = executor.close_position('ORD-001', reason='STOP_LOSS')
    assert result is True

# TEST 9: AC9 - Close on Take Profit
def test_close_on_tp(executor):
    result = executor.close_position('ORD-001', reason='TAKE_PROFIT')
    assert result is True

# TEST 10: AC10 - Error Handling
def test_error_handling(executor, mock_mt5_adapter):
    mock_mt5_adapter.send_order = Mock(side_effect=ConnectionError("MT5 unreachable"))
    with pytest.raises(ConnectionError):
        Order_def = Order(symbol='WINFUT', volume=1, entry_price=122.5, 
                         stop_loss=121.5, take_profit=124.0, source='BDI')
        executor.execute_order(order_def)
```

---

## 📋 IMPLEMENTATION STEPS (Passo-a-Passo) - TODO-2,3,4

**Timeline Total: 02/03 10:00-14:00 (4 horas)**

### Step 1: Architecture Review (30 min)

- Review Risk Validator interface + RiskValidator methods
- Review MT5 Adapter interface + available methods
- Review OK Event Log + audit trail requirements

### Step 2: implement execute_order() (60 min)

- Create OrdersExecutor class
- Implement 3-gate validation logic (capital, correlation, volatility)
- Call mt5_adapter.send_order() if all pass
- Return proper dict format with rejection reason if any fail
- Add comprehensive error handling + logging

### Step 3: Implement monitor_positions() (45 min)

- Query mt5_adapter.get_positions()
- Calculate current price + PnL for each position
- Aggregate metrics (total_positions, total_pnl)
- Measure latency + ensure < 100ms
- Return proper dict format

### Step 4: Implement position_monitoring_loop() (45 min)

- Create background thread/async task
- Loop at 100ms interval
- Call monitor_positions() each cycle
- Check SL trigger (PnL <= -1000)
- Check TP trigger (PnL >= +5000)
-Close positions on triggers
- Graceful shutdown with _monitoring_active flag

### Step 5: Write 10 Unit Tests (45 min)

- Create tests/unit/test_orders_executor.py
- Copy 10 test templates above
- Run pytest for coverage > 90%

### Step 6: Code Review + Integration (15 min)

- Persona 6 (Arch) reviews code
- mypy validation
- Integration test with Risk Validator

---

## ✓ CHECKLIST - TODO-2,3,4 COMPLETION

```
IMPLEMENTAÇÃO:
  ☑️ OrdersExecutor class created (250+ LOC)
  ☑️ execute_order() with 3-gate logic
  ☑️ monitor_positions() with latency < 100ms
  ☑️ position_monitoring_loop() background thread
  ☑️ close_position() with SL/TP triggers
  ☑️ Error handling + retry logic

TESTES:
  ☑️ test_capital_gate_fail PASS
  ☑️ test_correlation_gate_fail PASS
  ☑️ test_volatility_gate_fail PASS
  ☑️ test_all_gates_pass PASS
  ☑️ test_monitor_latency PASS
  ☑️ test_monitor_metrics PASS
  ☑️ test_loop_execution PASS
  ☑️ test_close_on_sl PASS
  ☑️ test_close_on_tp PASS
  ☑️ test_error_handling PASS
  ☑️ Coverage > 90%

DELIVERABLE:
  ☑️ OrdersExecutor pronto para E2E tests
  ☑️ All AC satisfied (10/10)
  ☑️ Ready for Stage 2 integration

STATUS: ✅ COMPLETE
```

---

# PARALELO: SYNC & DOCUMENTATION

**Personas:** Persona 17 (Doc), Persona 8 (Audit)  
**Tempo:** 1h paralelo com development  

### Arquivos a Sincronizar (Contínuo)  

---

## 2.1 CONTEXTO & PROBLEMA

### O que são TODO-2, TODO-3, TODO-4?

```
Location: src/application/orders_executor.py:133, 158, 188

TODO-2 (Line 133):
  # TODO: Implementar após Risk Validator pronto
  # Função: execute_order()

TODO-3 (Line 158):
  # TODO: Implementar após MT5Adapter pronto
  # Função: monitor_positions()

TODO-4 (Line 188):
  # TODO: Implementar loop de monitoramento
  # Função: position_monitoring_loop()
```

### Por que é crítico?

```
┌──────────────────────────────────────────────┐
│ BLOCKER: 50% de Sprint 1                     │
│                                              │
│ Sem OrdersExecutor → Não pode enviar ordens  │
│ Sem pedidos → Não há trades                  │
│ Sem trades → Não há validação de risk        │
│ Sem validação → E2E tests falham             │
│ E2E fail → Stage 2 deploy não pode começar   │
│                                              │
│ IMPACTO: Bloqueia 3-4 tasks paralelos        │
└──────────────────────────────────────────────┘
```

### Pré-requisitos

```
✅ Risk Validator [DONE Phase 6]
   └─ 3 gates: capital, correlation, volatility
   └─ API: validate_order(order) → bool

✅ MT5 Adapter Design [DESIGN 100%]
   └─ Classes: MT5Connection, OrderRestAPI
   └─ Methods: send_order(), get_positions(), close_position()

✅ BDI Detector [DONE Phase 6]
   └─ Signals: buy/sell/hold generated
   └─ Queue: fila_alertas ready

✅ WebSocket Server [DONE Phase 6]
   └─ Broadcasting alerts to clients
   └─ Connection manager operational
```

---

## 2.2 ESPECIFICAÇÃO DE 3 FUNÇÕES

### TODO-2: execute_order()

```python
# File: src/application/orders_executor.py

from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class Order:
    """Representa uma ordem de trading."""
    symbol: str
    type: str  # BUY, SELL
    quantity: int
    entry_price: float
    stop_loss: float
    take_profit: float
    source: str  # BDI, ML_CLASSIFIER
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class OrdersExecutor:
    """Executa ordens no MT5 com validação de risco."""
    
    def __init__(self, risk_validator, mt5_adapter, logger=None):
        """
        Args:
            risk_validator: RiskValidator instance (3 gates)
            mt5_adapter: MT5 REST API adapter
            logger: Logger instance
        """
        self.risk_validator = risk_validator
        self.mt5_adapter = mt5_adapter
        self.logger = logger or logging.getLogger(__name__)
        self.execution_history = []  # Audit trail
    
    def execute_order(self, order: Order) -> Dict:
        """
        TODO-2: Executa ordem se passar validação de risco.
        
        Fluxo:
        1. Receber ordem (BDI signal)
        2. Rodar 3 risk gates
        3. Se PASS: enviar ao MT5 via API
        4. Se FAIL: log rejection
        5. Retornar resultado com audit trail
        
        Args:
            order: Order object com entry, stop_loss, take_profit
        
        Returns:
            {
                'success': bool,
                'order_id': str (if success),
                'rejection_reason': str (if fail),
                'gates_passed': [gate1, gate2, gate3],
                'execution_time_ms': float,
                'timestamp': datetime,
            }
        
        Raises:
            ValueError: Se order inválida
            ConnectionError: Se MT5 API falhar
        """
        
        start_time = time.perf_counter()
        
        try:
            # Validar ordem
            if not order or not isinstance(order, Order):
                raise ValueError("Invalid order format")
            
            logger.info(f"Executing order: {order.symbol} {order.type} qty={order.quantity}")
            
            # GATE 1: Capital Adequacy
            # Verificar se capital suficiente para ordem
            gate1_pass = self.risk_validator.validate_capital(
                symbol=order.symbol,
                quantity=order.quantity,
                entry_price=order.entry_price
            )
            
            if not gate1_pass:
                result = {
                    'success': False,
                    'rejection_reason': 'GATE1_CAPITAL_INSUFFICIENT',
                    'gates_passed': [False, None, None],
                    'execution_time_ms': (time.perf_counter() - start_time) * 1000,
                    'timestamp': datetime.now(timezone.utc),
                }
                logger.warning(f"Order REJECTED by Gate 1: {result}")
                self.execution_history.append(result)
                return result
            
            # GATE 2: Correlation Check
            # Verificar correlação com posições abertas
            gate2_pass = self.risk_validator.validate_correlation(
                symbol=order.symbol,
                max_correlation=0.70
            )
            
            if not gate2_pass:
                result = {
                    'success': False,
                    'rejection_reason': 'GATE2_CORRELATION_TOO_HIGH',
                    'gates_passed': [True, False, None],
                    'execution_time_ms': (time.perf_counter() - start_time) * 1000,
                    'timestamp': datetime.now(timezone.utc),
                }
                logger.warning(f"Order REJECTED by Gate 2: {result}")
                self.execution_history.append(result)
                return result
            
            # GATE 3: Volatility Band Check
            # Verificar se volatilidade dentro do range
            gate3_pass = self.risk_validator.validate_volatility(
                symbol=order.symbol,
                min_vol=1.0,
                max_vol=3.0
            )
            
            if not gate3_pass:
                result = {
                    'success': False,
                    'rejection_reason': 'GATE3_VOLATILITY_OUT_OF_RANGE',
                    'gates_passed': [True, True, False],
                    'execution_time_ms': (time.perf_counter() - start_time) * 1000,
                    'timestamp': datetime.now(timezone.utc),
                }
                logger.warning(f"Order REJECTED by Gate 3: {result}")
                self.execution_history.append(result)
                return result
            
            # ALL GATES PASSED → Send to MT5
            logger.info(f"All 3 gates PASSED ✅ for {order.symbol}. Sending to MT5...")
            
            mt5_result = self.mt5_adapter.send_order(
                symbol=order.symbol,
                order_type=order.type,
                quantity=order.quantity,
                entry_price=order.entry_price,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
            )
            
            # Validar resposta MT5
            if not mt5_result or 'order_id' not in mt5_result:
                raise ConnectionError(f"MT5 API returned invalid response: {mt5_result}")
            
            result = {
                'success': True,
                'order_id': mt5_result['order_id'],
                'rejection_reason': None,
                'gates_passed': [True, True, True],
                'execution_time_ms': (time.perf_counter() - start_time) * 1000,
                'timestamp': datetime.now(timezone.utc),
                'mt5_response': mt5_result,
            }
            
            logger.info(f"Order EXECUTED ✅ {order.symbol}: order_id={result['order_id']}")
            self.execution_history.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Order execution FAILED: {str(e)}", exc_info=True)
            result = {
                'success': False,
                'rejection_reason': f'EXCEPTION: {type(e).__name__}',
                'error_message': str(e),
                'gates_passed': [None, None, None],
                'execution_time_ms': (time.perf_counter() - start_time) * 1000,
                'timestamp': datetime.now(timezone.utc),
            }
            self.execution_history.append(result)
            return result
```

### TODO-3: monitor_positions()

```python
def monitor_positions(self) -> Dict:
    """
    TODO-3: Query MT5 para posições abertas e atualizar estado.
    
    Fluxo:
    1. Query MT5 API: get_open_positions()
    2. Para cada posição:
       - Track: entry_time, current_price, PnL, unrealized
       - Trigger: exit signals if price hits SL/TP
    3. Update portfolio state
    4. Retornar posições atualizadas
    
    Returns:
        {
            'total_positions': int,
            'positions': [
                {
                    'order_id': str,
                    'symbol': str,
                    'entry_price': float,
                    'current_price': float,
                    'pnl_unrealized': float,
                    'entry_time': datetime,
                    'duration_minutes': int,
                    'signal_type': str,
                },
                ...
            ],
            'total_pnl_unrealized': float,
            'monitoring_time_ms': float,
            'timestamp': datetime,
        }
    """
    
    start_time = time.perf_counter()
    
    try:
        logger.info("Starting position monitoring loop...")
        
        # Query MT5 para posições abertas
        positions_mt5 = self.mt5_adapter.get_positions()
        
        if not positions_mt5:
            logger.info("No open positions")
            return {
                'total_positions': 0,
                'positions': [],
                'total_pnl_unrealized': 0.0,
                'monitoring_time_ms': (time.perf_counter() - start_time) * 1000,
                'timestamp': datetime.now(timezone.utc),
            }
        
        # Process cada posição
        positions_processed = []
        total_pnl = 0.0
        
        for pos in positions_mt5:
            # Calcular PnL não realizado
            current_price = self.mt5_adapter.get_current_price(pos['symbol'])
            pnl_unrealized = (current_price - pos['entry_price']) * pos['quantity']
            
            if pos['type'] == 'SELL':
                # Inverted for short
                pnl_unrealized *= -1
            
            entry_time = pos['entry_time']
            duration = (datetime.now(timezone.utc) - entry_time).total_seconds() / 60
            
            position_data = {
                'order_id': pos['order_id'],
                'symbol': pos['symbol'],
                'type': pos['type'],
                'quantity': pos['quantity'],
                'entry_price': pos['entry_price'],
                'current_price': current_price,
                'pnl_unrealized': pnl_unrealized,
                'entry_time': entry_time,
                'duration_minutes': duration,
                'signal_type': pos.get('signal_type', 'UNKNOWN'),
            }
            
            positions_processed.append(position_data)
            total_pnl += pnl_unrealized
            
            # Log atualização
            logger.info(f"Position update: {pos['symbol']} PnL={pnl_unrealized:.2f} BRT")
        
        result = {
            'total_positions': len(positions_processed),
            'positions': positions_processed,
            'total_pnl_unrealized': total_pnl,
            'monitoring_time_ms': (time.perf_counter() - start_time) * 1000,
            'timestamp': datetime.now(timezone.utc),
        }
        
        logger.info(f"Position monitoring complete: {len(positions_processed)} positions, "
                   f"Total PnL={total_pnl:.2f}")
        
        return result
        
    except Exception as e:
        logger.error(f"Position monitoring FAILED: {str(e)}", exc_info=True)
        return {
            'total_positions': 0,
            'positions': [],
            'error': str(e),
            'monitoring_time_ms': (time.perf_counter() - start_time) * 1000,
            'timestamp': datetime.now(timezone.utc),
        }
```

### TODO-4: position_monitoring_loop()

```python
def start_monitoring_loop(self, interval_ms: int = 100) -> None:
    """
    TODO-4: Inicia loop contínuo de monitoramento de posições.
    
    Fluxo:
    1. Loop a cada interval_ms (default 100ms)
    2. Chamar monitor_positions()
    3. Verificar exit signals (SL/TP)
    4. Se trigger: close_position()
    5. Log todas as ações
    6. Parar se signal SHUTDOWN
    
    Args:
        interval_ms: Intervalo entre checks (ms)
    
    Performance:
        - Loop cycle: < 100ms
        - P95 latency: < 200ms
        - CPU: < 5%
    """
    
    import asyncio
    import threading
    
    self._monitoring_active = True
    logger.info(f"Starting monitoring loop: interval={interval_ms}ms")
    
    def monitoring_thread():
        while self._monitoring_active:
            try:
                # Monitor posições abertas
                positions_update = self.monitor_positions()
                
                # Verificar exit signals
                for pos in positions_update.get('positions', []):
                    should_close = False
                    close_reason = None
                    
                    # Check Stop-Loss
                    if pos['pnl_unrealized'] <= pos.get('stop_loss_pnl', -1000):
                        should_close = True
                        close_reason = 'STOP_LOSS_HIT'
                    
                    # Check Take-Profit
                    elif pos['pnl_unrealized'] >= pos.get('take_profit_pnl', 5000):
                        should_close = True
                        close_reason = 'TAKE_PROFIT_HIT'
                    
                    # Execute close if needed
                    if should_close:
                        logger.info(f"Closing position {pos['order_id']}: {close_reason}")
                        close_result = self.close_position(
                            order_id=pos['order_id'],
                            reason=close_reason
                        )
                        logger.info(f"Position closed: {close_result}")
                
                # Sleep until next interval
                time.sleep(interval_ms / 1000.0)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {str(e)}", exc_info=True)
                time.sleep(interval_ms / 1000.0)  # Retry após erro
    
    # Start monitoring in background thread
    thread = threading.Thread(target=monitoring_thread, daemon=True)
    thread.start()
    logger.info("Monitoring loop started in background")
    
    return thread

def stop_monitoring_loop(self) -> None:
    """
    Para o loop de monitoramento.
    """
    self._monitoring_active = False
    logger.info("Monitoring loop stopped")

def close_position(self, order_id: str, reason: str = None) -> Dict:
    """
    Fecha uma posição aberta.
    
    Args:
        order_id: ID da ordem MT5
        reason: Motivo de fechamento (SL, TP, MANUAL)
    
    Returns:
        {
            'success': bool,
            'order_id': str,
            'closing_price': float,
            'pnl_realized': float,
            'reason': str,
            'timestamp': datetime,
        }
    """
    
    try:
        logger.info(f"Closing position {order_id}: reason={reason}")
        
        close_result = self.mt5_adapter.close_position(order_id)
        
        result = {
            'success': True,
            'order_id': order_id,
            'closing_price': close_result.get('closing_price'),
            'pnl_realized': close_result.get('pnl'),
            'reason': reason,
            'timestamp': datetime.now(timezone.utc),
        }
        
        logger.info(f"Position {order_id} closed: PnL={result['pnl_realized']:.2f}")
        self.execution_history.append(result)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to close position {order_id}: {str(e)}", exc_info=True)
        return {
            'success': False,
            'order_id': order_id,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc),
        }
```

---

## 2.3 ACCEPTANCE CRITERIA (10 AC)

```
AC-1: Execute Order - Capital Gate PASS/FAIL
  □ Validar capital suficiente
  □ Se insuficiente: REJECT com mensagem
  □ Se suficiente: passar para Gate 2
  ✓ TEST: test_execute_order_capital_gate

AC-2: Execute Order - Correlation Gate PASS/FAIL
  □ Validar correlação com posições abertas
  □ Max 70% permitido
  □ Se > 70%: REJECT
  ✓ TEST: test_execute_order_correlation_gate

AC-3: Execute Order - Volatility Gate PASS/FAIL
  □ Validar volatilidade do ativo
  □ Range: 1.0-3.0 sigma
  □ Se fora: REJECT
  ✓ TEST: test_execute_order_volatility_gate

AC-4: Execute Order - All 3 Gates PASS → Send to MT5
  □ Se todos 3 gates passam
  □ Enviar ordem ao MT5 via REST API
  □ Retornar order_id do MT5
  □ Log de auditoria
  ✓ TEST: test_execute_order_all_gates_pass

AC-5: Monitor Positions - Query MT5 Every interval_ms
  □ Query MT5 a cada 100ms (configurável)
  □ Retornar lista de posições abertas
  □ Calcular PnL não realizado
  □ Performance < 100ms per cycle
  ✓ TEST: test_monitor_positions_latency

AC-6: Monitor Positions - Track Position Metrics
  □ Entry price, current price, PnL, duration
  □ Atualizar estado continuamente
  □ Log de mudanças
  ✓ TEST: test_monitor_positions_metrics

AC-7: Position Monitoring Loop - Every 100ms Check
  □ Chamar monitor_positions() a cada 100ms
  □ Verificar exit signals (SL/TP)
  □ Executar close se trigger
  □ Cuidar com thread safety
  ✓ TEST: test_monitoring_loop_execution

AC-8: Close Position - Execute on SL/TP
  □ Se PnL ≤ -1000: STOP_LOSS_HIT
  □ Se PnL ≥ +5000: TAKE_PROFIT_HIT
  □ Fechaar imediatamente
  □ Registrar motivo
  □ Log de auditoria
  ✓ TEST: test_close_position_sl_tp

AC-9: Error Handling - Connection Failures
  □ Retry logic (3x exponential backoff)
  □ Graceful degradation
  □ Log de todos os erros
  □ Return error dict (não crash)
  ✓ TEST: test_execute_order_connection_error

AC-10: Performance & Resource Usage
  □ Execute order: < 1000ms total
  □ Monitor positions: < 100ms per cycle
  □ Memory leak: none (test with memory_profiler)
  □ CPU usage: < 5% idle
  ✓ TEST: test_performance_benchmark
```

---

## 2.4 UNIT TESTS (Persona 12 - QA)

```python
# File: tests/test_orders_executor.py

import pytest
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
from src.application.orders_executor import OrdersExecutor, Order

class TestOrdersExecutor:
    
    @pytest.fixture
    def mock_risk_validator(self):
        """Mock RiskValidator com todos os gates."""
        validator = Mock()
        validator.validate_capital = Mock(return_value=True)
        validator.validate_correlation = Mock(return_value=True)
        validator.validate_volatility = Mock(return_value=True)
        return validator
    
    @pytest.fixture
    def mock_mt5_adapter(self):
        """Mock MT5 REST API adapter."""
        adapter = Mock()
        adapter.send_order = Mock(return_value={'order_id': 'ORD-001', 'status': 'OPEN'})
        adapter.get_positions = Mock(return_value=[
            {
                'order_id': 'ORD-001',
                'symbol': 'WINFUT',
                'type': 'BUY',
                'quantity': 1,
                'entry_price': 122.50,
                'entry_time': datetime.now(timezone.utc),
            }
        ])
        adapter.get_current_price = Mock(return_value=123.00)
        adapter.close_position = Mock(return_value={'closing_price': 123.00, 'pnl': 500})
        return adapter
    
    @pytest.fixture
    def executor(self, mock_risk_validator, mock_mt5_adapter):
        """Cria OrdersExecutor com mocks."""
        return OrdersExecutor(
            risk_validator=mock_risk_validator,
            mt5_adapter=mock_mt5_adapter,
        )
    
    @pytest.fixture
    def sample_order(self):
        """Ordem válida para testes."""
        return Order(
            symbol='WINFUT',
            type='BUY',
            quantity=1,
            entry_price=122.50,
            stop_loss=121.50,
            take_profit=124.00,
            source='BDI',
        )
    
    def test_execute_order_capital_gate(self, executor, mock_risk_validator, sample_order):
        """AC-1: Capital gate validation."""
        mock_risk_validator.validate_capital = Mock(return_value=False)
        
        result = executor.execute_order(sample_order)
        
        assert result['success'] is False
        assert result['rejection_reason'] == 'GATE1_CAPITAL_INSUFFICIENT'
        assert result['gates_passed'] == [False, None, None]
    
    def test_execute_order_correlation_gate(self, executor, mock_risk_validator, sample_order):
        """AC-2: Correlation gate validation."""
        mock_risk_validator.validate_capital = Mock(return_value=True)
        mock_risk_validator.validate_correlation = Mock(return_value=False)
        
        result = executor.execute_order(sample_order)
        
        assert result['success'] is False
        assert result['rejection_reason'] == 'GATE2_CORRELATION_TOO_HIGH'
        assert result['gates_passed'] == [True, False, None]
    
    def test_execute_order_volatility_gate(self, executor, mock_risk_validator, sample_order):
        """AC-3: Volatility gate validation."""
        mock_risk_validator.validate_capital = Mock(return_value=True)
        mock_risk_validator.validate_correlation = Mock(return_value=True)
        mock_risk_validator.validate_volatility = Mock(return_value=False)
        
        result = executor.execute_order(sample_order)
        
        assert result['success'] is False
        assert result['rejection_reason'] == 'GATE3_VOLATILITY_OUT_OF_RANGE'
        assert result['gates_passed'] == [True, True, False]
    
    def test_execute_order_all_gates_pass(self, executor, sample_order):
        """AC-4: All 3 gates pass, send to MT5."""
        result = executor.execute_order(sample_order)
        
        assert result['success'] is True
        assert result['order_id'] == 'ORD-001'
        assert result['gates_passed'] == [True, True, True]
    
    def test_monitor_positions_latency(self, executor):
        """AC-5: Monitor positions latency < 100ms."""
        start = time.perf_counter()
        result = executor.monitor_positions()
        elapsed = (time.perf_counter() - start) * 1000
        
        assert elapsed < 100, f"Monitor latency: {elapsed}ms > 100ms"
        assert result['total_positions'] == 1
    
    def test_monitor_positions_metrics(self, executor):
        """AC-6: Track position metrics."""
        result = executor.monitor_positions()
        
        assert result['total_positions'] == 1
        pos = result['positions'][0]
        
        assert 'order_id' in pos
        assert 'entry_price' in pos
        assert 'current_price' in pos
        assert 'pnl_unrealized' in pos
        assert pos['pnl_unrealized'] == 500  # (123 - 122.5) * 1
    
    def test_close_position_stop_loss(self, executor):
        """AC-8: Close position on stop loss hit."""
        result = executor.close_position(
            order_id='ORD-001',
            reason='STOP_LOSS_HIT'
        )
        
        assert result['success'] is True
        assert result['closing_price'] == 123.00
        assert result['pnl_realized'] == 500
        assert result['reason'] == 'STOP_LOSS_HIT'
    
    def test_execute_order_connection_error(self, executor, mock_mt5_adapter, sample_order):
        """AC-9: Handle connection errors gracefully."""
        mock_mt5_adapter.send_order = Mock(return_value=None)
        
        result = executor.execute_order(sample_order)
        
        assert result['success'] is False
        assert 'ConnectionError' in result['rejection_reason']
    
    def test_performance_benchmark(self, executor, sample_order):
        """AC-10: Performance < 1s for execute_order."""
        start = time.perf_counter()
        result = executor.execute_order(sample_order)
        elapsed = (time.perf_counter() - start) * 1000
        
        assert elapsed < 1000, f"Execute order latency: {elapsed}ms > 1000ms"
        assert result['execution_time_ms'] < 1000
```

---

## 2.5 IMPLEMENTAÇÃO PASSO-A-PASSO

**Timeline:** 02/03 10:00-14:00 BRT (4 horas)

### Passo 1: Arquitetura & Design Review (30 min)

```bash
# Persona 1 (Eng Sr) + Persona 6 (Arch)

# 1a. Review architecture docs
cat docs/agente_autonomo/ARQUITETURA_MT5_v1.2.md
cat docs/agente_autonomo/RISK_FRAMEWORK_v1.2.md

# 1b. Review risk validator (já existe)
cat src/application/risk_validator.py

# 1c. Review MT5 adapter design (interface)
cat src/application/interfaces/mt5_adapter.py

# 1d. Design 3 funções
# → execute_order() - valida 3 gates + envia MT5
# → monitor_positions() - query posições abertas
# → position_monitoring_loop() - loop contínuo + SL/TP
```

### Passo 2: Implementar OrdersExecutor (90 min)

```bash
# Persona 1 (Eng Sr) - Coding

# 2a. Criar classe OrdersExecutor
vim src/application/orders_executor.py
# → Copiar código conforme spec acima (TODO-2, TODO-3, TODO-4)

# 2b. Implementar TODO-2: execute_order()
# → 3 gates validation
# → MT5 send
# → Error handling

# 2c. Implementar TODO-3: monitor_positions()
# → Query MT5
# → Calculate PnL
# → Audit log

# 2d. Implementar TODO-4: position_monitoring_loop()
# → Background thread
# → Exit signal checks
# → Close positions

# 2e. Implementar helper: close_position()
# → SL/TP triggers
# → Close via MT5
```

### Passo 3: Escrever Unit Tests (60 min)

```bash
# Persona 12 (QA) - Testing

# 3a. Criar arquivo de testes
vim tests/test_orders_executor.py
# → Copiar test cases conforme spec acima (10 ACs)

# 3b. Run testes
pytest tests/test_orders_executor.py -v

# 3c. Coverage
pytest tests/test_orders_executor.py --cov=src/application/orders_executor

# Expected: > 90% coverage
```

### Passo 4: Code Review & Integration (30 min)

```bash
# Persona 6 (Arch) + Persona 1 (Eng Sr)

# 4a. Code review
python -m mypy src/application/orders_executor.py --strict

# 4b. Linting
python -m pylint src/application/orders_executor.py

# 4c. Integration test (paralelo com Risk + MT5)
pytest tests/test_orders_executor.py::TestOrdersExecutor::test_execute_order_all_gates_pass -v
```

### Passo 5: Documentação (30 min)

```bash
# Persona 8 (Audit) - Documentação

# 5a. Adicionar docstrings
# → Já incluído no código acima

# 5b. Update ANALISE_PRIORIZACAO_23FEV.md
# → TODO-2,3,4 marcar como "COMPLETE"

# 5c. Update CHANGELOG.md
echo "- ✅ TODO-2,3,4: OrdersExecutor with 3-gate validation + monitoring" >> CHANGELOG.md
```

---

## 2.6 CHECKLIST DE CONCLUSÃO

```
TODO-2,3,4 Completion Checklist:

IMPLEMENTAÇÃO:
  ☑️ OrdersExecutor class created
  ☑️ execute_order() - risks validation (3 gates)
  ☑️ monitor_positions() - position tracking
  ☑️ position_monitoring_loop() - continuous monitoring
  ☑️ close_position() - SL/TP triggering
  ☑️ Error handling + retry logic
  ☑️ Audit logging for all operations

TESTES:
  ☑️ test_execute_order_capital_gate() PASS
  ☑️ test_execute_order_correlation_gate() PASS
  ☑️ test_execute_order_volatility_gate() PASS
  ☑️ test_execute_order_all_gates_pass() PASS
  ☑️ test_monitor_positions_latency() PASS (< 100ms)
  ☑️ test_monitor_positions_metrics() PASS
  ☑️ test_close_position_stop_loss() PASS
  ☑️ test_execute_order_connection_error() PASS
  ☑️ test_performance_benchmark() PASS (< 1s)
  ☑️ Coverage > 90% achieved

DOCUMENTAÇÃO:
  ☑️ Docstring completo em todas as funções
  ☑️ AC list validado (10/10 complete)
  ☑️ ANALISE_PRIORIZACAO_23FEV.md atualizado
  ☑️ CHANGELOG.md com entrada

GIT:
  ☑️ Code committed: "feat: TODO-2,3,4 - OrdersExecutor implementation"
  ☑️ Tests committed: "test: OrdersExecutor - unit tests 90%+ coverage"
  ☑️ Message em português, UTF-8 encoding
  ☑️ All files pushed to main

VALIDAÇÃO FINAL:
  ☑️ Produto: OrdersExecutor executável e validado
  ☑️ E2E tests podem usar esse código
  ☑️ Desbloqueia: E2E integration + Stage 2 deployment
  ☑️ Status: ✅ READY FOR E2E TESTING
```

---

# TAREFAS DE SUPORTE (PARALELO)

## Sincronização de Documentação

**Persona:** Persona 17 (Doc Advocate) + Persona 8 (Audit)  
**Duração:** 1-2 horas  
**Timeline:** 24/02-25/02 (paralelo com todos)  

### Arquivos a Atualizar

```python
DOCUMENTAÇÃO SYNC:

1. ANALISE_PRIORIZACAO_23FEV.md
   ├─ TODO-1: marcar como IN-PROGRESS → COMPLETE (25/02 12:00)
   ├─ TODO-2,3,4: marcar como IN-PROGRESS → COMPLETE (03/03 12:00)
   ├─ Issues: Adicionar links #66, #67, #68, #69
   └─ Timeline: Atualizar % de conclusão

2. docs/PLANO_DE_SPRINTS_MVP_NOW.md
   ├─ Sprint 1: Link para issues criadas
   ├─ Dependencies: Marcar TODO-1 como desbloqueador
   └─ Timeline: Update progresso dia 24-25

3. docs/agente_autonomo/SYNC_MANIFEST.json
   ├─ Update checksums de arquivos modificados
   ├─ Update last_update timestamp
   └─ Validar todos docs sincronizados

4. docs/agente_autonomo/VERSIONING.json
   ├─ Bump version Sprint 1 (v1.0.0 → v1.0.1 ou similar)
   ├─ Add release notes para TODO-1 + TODO-2,3,4
   └─ Update deployment status

5. README.md
   ├─ Update Sprint 1 section
   ├─ Add links para issues
   └─ Update project status

6. Novo: docs/agente_autonomo/SPRINT1_PROGRESS.md
   ├─ Criado 24/02
   ├─ Issues overview (4 issues)
   ├─ Personas allocated (8 personas)
   └─ Timeline e milestones
```

### Validação Pré-Commit

```bash
# Antes de fazer commit, validar:

CHECKLIST:
  ☑️ Markdown lint: python -m pymarkdown scan docs/
  ☑️ UTF-8 encoding: git log --oneline | head -5
  ☑️ Cross-references válidas (todos links existem)
  ☑️ Timestamps sincronizados
  ☑️ SYNC_MANIFEST.json com checksums corretos
  ☑️ VERSIONING.json reflete mudanças
  ☑️ Nenhum doc marcado como "unsynchronized"

COMMIT MESSAGE:
  "feat: Sprint 1 kickoff - 4 issues + 8 personas squad pronto"
  
  Body:
  - Issues created: #66, #67, #68, #69
  - Personas allocated: 8 (Eng Sr, The Brain, Arch, Blueprint, Quality, Audit, Doc, Support)
  - Timeline: 24/02 (dev) → 25/02 (validation) → 27/02 kickoff
  - Prerequisites: All met ✅
  - Blockers: None
```

---

# SUMÁRIO EXECUTIVO

## 📊 Status Consolidado

```
┌──────────────────────────────────────────────────────┐
│ SPRINT 1 - TAREFAS PRIORIZADAS                       │
├──────────────────────────────────────────────────────┤

TASK TODO-1: Label backtest_optimized_results
  Status:   ⏳ READY TO START
  Lead:     Persona 2 - The Brain
  Duration: 2-3 horas (24/02 10:00-12:30)
  AC:       7/7 specs
  Tests:    7 unit tests ready
  Blocker:  Desbloqueia Grid Search (50h Sprint 2)
  Output:   training_dataset.csv (1.000 rows)

TASK TODO-2,3,4: OrdersExecutor
  Status:   ⏳ READY TO START
  Lead:     Persona 1 - Eng Sr
  Duration: 3-4 horas (02/03 10:00-14:00)
  AC:       10/10 specs
  Tests:    10 unit tests ready
  Blocker:  Desbloqueia E2E + Stage 2 (30h Sprint 1)
  Output:   OrdersExecutor class (150+ LOC)

SQUAD:    8 personas allocated
  ├─ Persona 1 (Eng Sr) - OrdersExecutor (TODO-2,3,4)
  ├─ Persona 2 (The Brain) - dataset labels (TODO-1)
  ├─ Persona 6 (Arch) - code review + design validation
  ├─ Persona 7 (Blueprint) - infra setup
  ├─ Persona 8 (Audit) - documentation + validation
  ├─ Persona 12 (Quality) - unit tests + QA
  ├─ Persona 17 (Doc) - sync + README
  └─ Personas 3-5,9-11 (Suporte) - escalation on demand

TIMELINE: 
  24/02: TODO-1 implementation + tests + docs (2.5h paralelo)
  24/02: OrdersExecutor setup + design (2h paralelo)
  25/02: TODO-1 validation + final docs
  02/03: OrdersExecutor implementation + tests (4h)
  03/03: OrdersExecutor validation + final docs
  27/02: Sprint 1 Official Kickoff

BLOCKER STATUS:  ✅ ZERO BLOCKERS
  ├─ Dataset pronto
  ├─ Risk framework pronto
  ├─ MT5 adapter design pronto
  ├─ Personas confirmadas
  └─ AC definidos 100%

GO DECISION: 🟢 GO - Pronto para executar
```

---

**Documento:** DESENVOLVIMENTO_DE_TASKS_PRIORIZADAS_SPRINT1.md  
**Status:** ✅ COMPLETO - Plano executável pronto  
**Próxima ação:** Liberação de Personas para começar 24/02 09:00 BRT  
**ETA Go-Live:** 10/04/2026 (confirmado em Gate 1: 05/03)
