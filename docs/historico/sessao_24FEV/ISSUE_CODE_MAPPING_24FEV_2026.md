# 📍 MAPEAMENTO GITHUB ISSUES ↔️ CÓDIGO SOURCE

**Data:** 23/02/2026
**Status:** Planejamento Sprint 1
**Objetivo:** Rastreabilidade entre GitHub issues e TODOs no código-fonte

---

## 🎯 RESUMO EXECUTIVO

Este documento mapeia as 4 GitHub issues criadas (#6-#9) para os TODOs específicos no código-fonte, fornecendo:
- ✅ Localização exata de cada TODO
- ✅ Acceptance Criteria → Linhas de código
- ✅ Dependências entre issues
- ✅ Structure de pastas esperadas

---

## 📊 MATRIZ DE RASTREABILIDADE

| Issue | Título | Arquivo | TODO Lines | Personas | Status |
|-------|--------|---------|------------|----------|--------|
| #6 | ML-101: Label dataset | ml_feature_engineer.py | 447-448 | P2 | 📌 Crítica |
| #7 | ENG-201: OrdersExecutor | orders_executor.py | 133, 158, 188 | P1 | 📌 Crítica |
| #8 | ML-102: Pattern detect | ml_feature_engineer.py | ~460-500 | P2 | 🟠 Alta |
| #9 | ENG-202: BDI Integration | bdi_processor_v2.py | ~TBD | P1+P2 | 🟠 Alta |

---

## 🔴 ISSUE #6: ML-101 - Label Backtest Dataset

**GitHub:** https://github.com/jadergreiner/operador-day-trade-win/issues/6
**Persona:** Persona 2 (The Brain - ML Expert)
**Priority:** 🔴 CRÍTICA
**Effort:** 2-3 horas
**Blocker:** Nenhum
**Desbloqueia:** #8, #9, Sprint 2, v1.2 Go-Live

### Localização do Código

```
📁 src/
 └─ 📁 application/
     └─ 📄 ml_feature_engineer.py
        ├─ Line 447: TODO-1 START
        ├─ Line 448: TODO-1 END (define function signature)
        └─ Line 450-500: Implementation space
```

### Estrutura Esperada do Arquivo

```python
# src/application/ml_feature_engineer.py

# ... imports and other code ...

class MLFeatureEngineer:
    """Responsável por feature engineering e dataset management."""

    # Line 440-445: Existing methods
    def some_existing_method(self):
        pass

    # ==================== TODO-1 START (Line 447) ====================
    def load_and_label(self, path: str) -> dict:
        """
        Load backtest_optimized_results.json and apply labels.

        Args:
            path (str): Path to backtest_optimized_results.json

        Returns:
            dict: {
                'X': features (17280, N_features),
                'y': labels (17280,),
                'metadata': {
                    'imbalance': float,  # % of positive class
                    'nan_count': int,
                    'execution_time': float  # milliseconds
                }
            }

        Acceptance Criteria (7 items):
        ☐ AC-1: Load JSON file efficiently into memory
        ☐ AC-2: Return dict with features + labels
        ☐ AC-3: Map window_id → labels correctly (no off-by-one)
        ☐ AC-4: Class imbalance < 70% (60/40 max)
        ☐ AC-5: Zero NaN values in all columns
        ☐ AC-6: Execution time < 500ms for 17k+ samples
        ☐ AC-7: Unit tests coverage > 90%
        """
        # TODO-1 IMPLEMENTATION GOES HERE
        raise NotImplementedError("TODO-1: Implement load_and_label()")
    # ==================== TODO-1 END (Line 448) ====================

    def other_methods_below(self):
        pass
```

### Acceptance Criteria Detail (via TODOs in code)

```python
# Line 447-500: Detailed implementation checklist

def load_and_label(self, path: str) -> dict:
    """
    AC-1: Load JSON file efficiently
    TODO: Use json.load() or pandas.read_json()
    TODO: Validate file exists before loading
    TODO: Catch JSON decode errors
    """

    """
    AC-2: Return dict structure
    TODO: Create return dict with keys: 'X', 'y', 'metadata'
    TODO: Ensure X is numpy array (17280, N_features)
    TODO: Ensure y is numpy array (17280,)
    """

    """
    AC-3: Map window_id → labels (no off-by-one)
    TODO: Extract window_id from JSON
    TODO: Map to correct label indices (0-based)
    TODO: Validate no gaps or duplicates in mapping
    """

    """
    AC-4: Class imbalance < 70%
    TODO: Calculate label distribution
    TODO: Assert sum(y==1) / len(y) in [0.3, 0.7]
    TODO: Raise WeihgtedImbalanceError if > 70%
    """

    """
    AC-5: Zero NaN in all columns
    TODO: Check for NaN in X and y
    TODO: Assert np.isnan(X).sum() == 0
    TODO: Assert np.isnan(y).sum() == 0
    """

    """
    AC-6: Performance < 500ms
    TODO: Add @timer decorator
    TODO: Assert execution_time < 500
    """

    """
    AC-7: Unit tests > 90% coverage
    TODO: Create tests/unit/test_load_and_label.py
    TODO: test_load_and_label_success
    TODO: test_load_and_label_nan_handling
    TODO: test_load_and_label_imbalance_check
    TODO: test_load_and_label_performance
    """
```

### Testes Esperados

```python
# File: tests/unit/test_load_and_label.py
# Location: parallel to src/ directory

class TestLoadAndLabel:
    """Unit tests para AC-1 até AC-7."""

    def test_load_and_label_success(self):
        """AC-1, AC-2: Load JSON and return dict structure."""
        # Given: backtest_optimized_results.json exists
        # When: load_and_label(path) called
        # Then: returns dict with X, y, metadata
        pass

    def test_load_and_label_nan_handling(self):
        """AC-5: Verify zero NaN values."""
        # Assert: np.isnan(X).sum() == 0
        # Assert: np.isnan(y).sum() == 0
        pass

    def test_load_and_label_imbalance(self):
        """AC-4: Class imbalance < 70%."""
        # Assert: 0.3 <= positive_ratio <= 0.7
        pass

    def test_load_and_label_performance(self):
        """AC-6: Execution < 500ms."""
        # Assert: execution_time < 500
        pass
```

---

## 🔴 ISSUE #7: ENG-201 - OrdersExecutor Implementation

**GitHub:** https://github.com/jadergreiner/operador-day-trade-win/issues/7
**Persona:** Persona 1 (Eng Sr - Backend/Architecture)
**Priority:** 🔴 CRÍTICA
**Effort:** 3-4 horas
**Blocker:** Nenhum (paralelo com #6)
**Desbloqueia:** #9, E2E pipeline, v1.2 Go-Live

### Localização do Código

```
📁 src/
 └─ 📁 application/
     └─ 📄 orders_executor.py
        ├─ Line 133: TODO-2 (execute_order)
        ├─ Line 158: TODO-3 (monitor_positions)
        ├─ Line 188: TODO-4 (handle_stop_loss)
        └─ Line 200-300: Implementation space
```

### Estrutura Esperada do Arquivo

```python
# src/application/orders_executor.py

from typing import Optional, Dict, List
from dataclasses import dataclass
import asyncio
from datetime import datetime

@dataclass
class Order:
    """Order data structure."""
    order_id: str
    symbol: str
    quantity: float
    price: float
    direction: str  # 'BUY' or 'SELL'

class OrdersExecutor:
    """Responsável pela execução e monitoramento de ordens."""

    def __init__(self, risk_validator, mt5_adapter):
        self.risk_validator = risk_validator
        self.mt5_adapter = mt5_adapter
        self.execution_history = []
        self.open_positions = {}

    # ==================== TODO-2 START (Line 133) ====================
    async def execute_order(self, order: Order) -> Dict:
        """
        Validate order against Risk Framework and send to MT5.

        Args:
            order (Order): Order object with symbol, qty, price, direction

        Returns:
            Dict: {
                'order_id': str,
                'status': 'EXECUTED' | 'REJECTED',
                'reason': str,
                'timestamp': datetime
            }

        AC-1: Validate order against Risk Framework
        AC-2: Integrate with MT5Adapter
        AC-3: Implement retry logic (3x exponential backoff)
        AC-4: Logging + audit trail
        """
        # TODO-2 IMPLEMENTATION
        raise NotImplementedError("TODO-2: Implement execute_order()")

    async def execute_order_with_details(self, order: Order) -> Dict:
        """Detailed implementation steps (inline TODOs)."""
        # AC-1: Validate
        # TODO: Call self.risk_validator.validate(order)
        # TODO: Check: margin available?
        # TODO: Check: position limit not exceeded?
        # TODO: Check: circuit breaker not triggered (-3%/-5%/-8%)?

        # AC-2: Integrate with MT5
        # TODO: Call self.mt5_adapter.send_order(order)
        # TODO: Wait for MT5 response (timeout 5s)

        # AC-3: Retry logic
        # TODO: Implement exponential backoff (100ms, 500ms, 2s)
        # TODO: Retry on: network error, timeout (max 3 attempts)
        # TODO: Stop retry on: validation reject, business rule fail

        # AC-4: Logging
        # TODO: Log order submission timestamp
        # TODO: Log MT5 response (status code, message)
        # TODO: Store in self.execution_history
        pass
    # ==================== TODO-2 END (Line 133) ====================

    # ==================== TODO-3 START (Line 158) ====================
    async def monitor_positions(self) -> Optional[List[Dict]]:
        """
        Poll open positions every 30 seconds and detect stop-loss.

        Returns:
            List[Dict]: List of open positions with current metrics

        AC-5: Poll positions every 30s
        AC-6: Detect stop-loss scenarios
        AC-7: Maintain execution history log
        AC-8: Performance < 500ms per polling cycle
        """
        # TODO-3 IMPLEMENTATION
        raise NotImplementedError("TODO-3: Implement monitor_positions()")

    async def monitor_positions_with_details(self) -> Optional[List[Dict]]:
        """Detailed implementation steps."""
        # AC-5: Poll every 30s
        # TODO: While loop with asyncio.sleep(30)
        # TODO: Call self.mt5_adapter.get_open_positions()

        # AC-6: Detect stop-loss
        # TODO: For each position, check if current_price <= stop_loss_price
        # TODO: If triggered, call handle_stop_loss(position)

        # AC-7: Execution history
        # TODO: Log position status at each polling cycle
        # TODO: Store in self.open_positions dict

        # AC-8: Performance
        # TODO: Add @timer decorator
        # TODO: Assert execution < 500ms per cycle
        pass
    # ==================== TODO-3 END (Line 158) ====================

    # ==================== TODO-4 START (Line 188) ====================
    async def handle_stop_loss(self, position: Dict) -> Dict:
        """
        Close position at market price when stop-loss triggered.

        Args:
            position (Dict): Position object with entry, SL, quantity

        Returns:
            Dict: {
                'position_id': str,
                'closed_price': float,
                'closed_time': datetime,
                'pnl': float  # P&L da posição
            }

        AC-9: Close at market price
        AC-10: Log event for audit
        AC-11: Atomically update account state
        """
        # TODO-4 IMPLEMENTATION
        raise NotImplementedError("TODO-4: Implement handle_stop_loss()")

    async def handle_stop_loss_with_details(self, position: Dict) -> Dict:
        """Detailed implementation steps."""
        # AC-9: Close at market
        # TODO: Get current market price from MT5
        # TODO: Create market close order (opposite direction)
        # TODO: Call self.mt5_adapter.send_order(close_order)

        # AC-10: Audit log
        # TODO: Log: position_id, entry_price, close_price, PnL
        # TODO: Store event in execution_history
        # TODO: Include timestamp (datetime.now())

        # AC-11: Atomic update
        # TODO: Update self.open_positions (remove position)
        # TODO: Update account balance
        # TODO: No partial updates (all-or-nothing)
        pass
    # ==================== TODO-4 END (Line 188) ====================

    # Additional methods below
    def get_execution_history(self) -> List[Dict]:
        """Return execution history for audit."""
        return self.execution_history
```

### Testes Esperados

```python
# File: tests/unit/test_orders_executor.py

class TestOrdersExecutor:
    """Unit + E2E tests para AC-1 até AC-14."""

    @pytest.fixture
    def executor(self):
        """Setup mock adapters."""
        mock_validator = MagicMock()
        mock_mt5 = MagicMock()
        return OrdersExecutor(mock_validator, mock_mt5)

    @pytest.mark.asyncio
    async def test_execute_order_success(self, executor):
        """AC-1, AC-2: Execute order successfully."""
        # Given: valid order
        # When: execute_order(order) called
        # Then: returns EXECUTED status
        pass

    @pytest.mark.asyncio
    async def test_execute_order_retry_logic(self, executor):
        """AC-3: Retry on transient failures."""
        # Given: MT5 fails 2x, succeeds on 3rd
        # When: execute_order called
        # Then: retries with exponential backoff (100ms, 500ms)
        pass

    @pytest.mark.asyncio
    async def test_monitor_positions_performance(self, executor):
        """AC-8: Polling < 500ms."""
        # Assert: execution_time < 500ms
        pass

    @pytest.mark.asyncio
    async def test_handle_stop_loss_atomic(self, executor):
        """AC-11: Atomic close (all-or-nothing)."""
        # Given: position at SL level
        # When: handle_stop_loss called
        # Then: position removed from open_positions
        # Then: account updated atomically (no partial state)
        pass
```

---

## 🟠 ISSUE #8: ML-102 - Pattern Detection

**GitHub:** https://github.com/jadergreiner/operador-day-trade-win/issues/8
**Persona:** Persona 2 (The Brain - ML Expert)
**Priority:** 🟠 ALTA
**Effort:** 2-3 horas
**Blocker:** Issue #6 (load_and_label)
**Desbloqueia:** #9 (BDI Integration), Feature selection

### Localização do Código

```
📁 src/
 └─ 📁 application/
     └─ 📄 ml_feature_engineer.py
        ├─ Line 460-500: TODO-5 (detect_patterns)
        └─ Line 510-550: Implementation space
```

### Estrutura Esperada do Arquivo

```python
# File: src/application/ml_feature_engineer.py

class MLFeatureEngineer:

    # ... TODO-1 (load_and_label) above ...

    # ==================== TODO-5 START (Line 460) ====================
    def detect_patterns(self, X: np.ndarray, y: np.ndarray) -> Dict:
        """
        Analyze label distribution and detect feature patterns.

        Args:
            X (np.ndarray): Features (17280, N_features)
            y (np.ndarray): Labels (17280,)

        Returns:
            Dict: {
                'label_distribution': Dict,
                'feature_importance': List[Tuple],
                'insights': List[str],
                'plot_path': str  # histogram path
            }

        AC-1: Analyze label distribution
        AC-2: Detect feature patterns
        AC-3: Generate insights report
        AC-4: Plot histogram
        """
        # TODO-5 IMPLEMENTATION
        raise NotImplementedError("TODO-5: Implement detect_patterns()")
    # ==================== TODO-5 END (Line 500) ====================
```

---

## 🟠 ISSUE #9: ENG-202 - BDI Integration

**GitHub:** https://github.com/jadergreiner/operador-day-trade-win/issues/9
**Persona:** Persona 1 (Eng Sr) + Persona 2 (ML Expert)
**Priority:** 🟠 ALTA
**Effort:** 3-4 horas
**Blocker:** Issues #6 + #7 (load_and_label + OrdersExecutor)
**Desbloqueia:** Beta Launch v1.1 (13/03), Go-Live v1.2 (10/04)

### Localização do Código

```
📁 src/
 ├─ 📁 domain/
 │  └─ 📄 bdi_processor_v2.py (existing)
 │     ├─ Line ~XXX: Hook detector into pipeline
 │     └─ Line ~YYY: Filter by confidence score
 │
 └─ 📁 interfaces/
    └─ 📄 websocket_fila_integrador.py (existing)
       └─ Line ~ZZZ: Send only high-confidence alerts
```

### Estrutura Esperada (Integração)

```python
# File: src/domain/bdi_processor_v2.py
# (Existing file - add detector hook)

class BDIProcessor:
    """BDI processing pipeline."""

    def __init__(self, detector=None):
        self.detector = detector  # Pattern detector instance

    async def process_spike(self, spike_data: Dict) -> Dict:
        """
        Process BDI spike through detector.

        AC-1: Hook detector pattern matching
        AC-2: Filter by confidence > 0.75
        AC-3: Send to WebSocket if confidence OK
        AC-4: Performance < 100ms per alert
        """
        # AC-1: Call detector
        # TODO: confidence_score = self.detector.predict(spike_data)

        # AC-2: Filter by threshold
        # TODO: if confidence_score < 0.75: return None  # skip

        # AC-3: Send to WebSocket
        # TODO: await self.websocket_sender.send_alert(spike_data, confidence_score)

        # AC-4: Performance
        # TODO: Add @timer, assert < 100ms
        pass
```

---

## 🔗 DEPENDENCY GRAPH

```
    [ #6: Load & Label ]
           /        \
          /          \
     [ #8:          [ #7:
      Pattern ]   OrdersExecutor ]
       Detect          \
        /               \
       /                 \
   [ #9: BDI Integration ]
          |
          ↓
   [ Beta v1.1 (13/03) ]
           |
           ↓
   [ Go-Live v1.2 (10/04) ]
```

**Critical Path:**
- #6 (2-3h) → Basis for #8 and #9
- #7 (3-4h) → Parallel with #6, required for #9
- #8 (2-3h) → Depends on #6, feeds into #9
- #9 (3-4h) → Depends on #6 + #7, finalizes Sprint 1

**Total Effort:** 10-14 hours across 4 personas (parallelizable to 48h execution window)

---

## 📋 FILE CHECKLIST

**Files that MUST be created for Sprint 1:**

```
✅ CREATED (Phase 6):
├─ src/interfaces/websocket_server.py (270 LOC)
├─ src/interfaces/websocket_fila_integrador.py (85 LOC)
├─ tests/test_websocket_server.py (180 LOC)
└─ scripts/backtest_detector.py (320 LOC)

📌 TODO-1 (#6): CREATE
├─ src/application/ml_feature_engineer.py (~450-500 LOC)
│  ├─ load_and_label() method (lines 447-448)
│  ├─ detect_patterns() method (lines 460-500)
│  └─ Supporting methods
└─ tests/unit/test_load_and_label.py (~120 LOC)

📌 TODO-2,3,4 (#7): CREATE
├─ src/application/orders_executor.py (~300-350 LOC)
│  ├─ execute_order() method (line 133)
│  ├─ monitor_positions() method (line 158)
│  └─ handle_stop_loss() method (line 188)
└─ tests/unit/test_orders_executor.py (~200 LOC)

📌 TODO-5 (#8): UPDATE EXISTING
├─ src/application/ml_feature_engineer.py (lines 460-500)
│  └─ detect_patterns() method
└─ tests/unit/test_pattern_detection.py (~80 LOC)

📌 TODO-6 (#9): UPDATE EXISTING
├─ src/domain/bdi_processor_v2.py (~50 LOC integration)
├─ src/interfaces/websocket_fila_integrador.py (~30 LOC)
└─ tests/integration/test_bdi_integration.py (~120 LOC)
```

---

## 🎯 EXECUTION ROADMAP (24-25 FEV)

**24/02 - Morning (10:00-12:00):**
- Persona 2: Start #6 (load_and_label)
- Persona 1: Start #7 (OrdersExecutor design)
- Parallel: Setup files + fixtures

**24/02 - Afternoon (14:00-17:00):**
- Finish #6 + #7 implementations
- Run tests + code review

**25/02 - Morning (09:00-12:00):**
- Final validation #6 + #7
- Start #8 (pattern detection) if #6 ready
- Setup #9 integration hooks

---

## ✅ SIGN-OFF

| Issue | Owner | Estimate | Target Date | Status |
|-------|-------|----------|-------------|--------|
| #6 | Persona 2 | 2-3h | 24/02 EOD | 📌 Ready |
| #7 | Persona 1 | 3-4h | 24/02 EOD | 📌 Ready |
| #8 | Persona 2 | 2-3h | 25/02 EOD | 📌 Ready |
| #9 | P1+P2 | 3-4h | 25/02 EOD | 📌 Ready |

**Total:** 10-14 hours | **Timeline:** 24-25 FEV | **Buffer:** +40% (6-8h contingency)

---

**Próximo Passo:** Iniciar Sprint 1 kickoff (24/02 09:00 BRT)

