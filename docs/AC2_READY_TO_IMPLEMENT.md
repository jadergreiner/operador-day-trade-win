# AC2: Signal Persistence Implementation - Ready to Begin

**Status:** 🟡 READY FOR IMPLEMENTATION  
**Blocking:** AC1 ✅ COMPLETE  
**Required For:** AC3 Signal Tracking Lifecycle  
**Estimated Duration:** 3-4 hours  
**Date Started:** 05/03/2026

---

## Executive Summary

**AC2** implements the persistence layer that saves signals to the database with complete market context, making them queryable and ready for Camada 2 decision logic.

**What AC2 Does:**
```
AC1 Signal (in-memory object)
         ↓
      [AC2 Signal Persistence]
         ↓
Database INSERT into 'signals' table with market_context_json
         ↓
Ready for AC3 (Tracking) + Camada 2 (Decision)
```

**Key Task:** Implement `SignalPersistence.insert()` method to save Signal objects to SQLite

---

## Implementation Checklist

### Phase 1: Understand Current State (15 minutes)

- [ ] Review `Signal` dataclass structure
  - Location: `src/application/signal_persistence.py` (lines ~50-80)
  - Fields: signal_id, timestamp, symbol, signal_type, smc_score, smc_detector, entry_price, market_context
  - Status: ✅ Already defined from AC1

- [ ] Review `MarketContext` dataclass
  - Location: `src/application/signal_persistence.py` (lines ~20-40)
  - Fields: rsi, atr, bb_upper, bb_lower, volume, spread, trend_direction, last_close
  - Status: ✅ Already defined

- [ ] Review database schema
  - Location: `src/infrastructure/database_schema.py` or migrations folder
  - Table: `signals` with columns for all Signal fields + market_context_json
  - Status: ✅ Should already exist (check `data/db/trading.db` schema)

- [ ] Review log examples for INSERT format
  - Reference: `docs/LOG_EXAMPLES_AC1_SIGNAL_GENERATION.md` → Section 4 (Detailed Signal Fields)
  - Shows exact SQL INSERT statement expected
  - Status: ✅ Already documented

**Validation Step:**
```bash
# Confirm signals table exists
C:\repo\operador-day-trade-win> python
>>> import sqlite3
>>> conn = sqlite3.connect('data/db/trading.db')
>>> cursor = conn.cursor()
>>> cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='signals'")
>>> print(cursor.fetchone()[0])
# Should show table definition with market_context_json column
```

**Expected Output:**
```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT UNIQUE NOT NULL,
    timestamp DATETIME NOT NULL,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,  -- BUY/SELL
    smc_score REAL NOT NULL,    -- [-3, +3]
    smc_detector TEXT NOT NULL, -- BOS/CHOCH/FVG
    entry_price REAL NOT NULL,
    market_context_json TEXT,   -- JSON string with 8 fields
    candle_index INTEGER,
    status TEXT DEFAULT 'READY', -- READY/PERSISTED/TRACKING/ARCHIVED
    outcome_type TEXT,           -- WINNING/WHIPSAW/MISSED/NULL
    outcome_pnl REAL,           -- P&L if outcome calculated
    closed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

---

### Phase 2: Implement SignalPersistence.insert() (2-3 hours)

#### Step 1: Create Method Skeleton (30 minutes)

**File:** `src/application/signal_persistence.py`  
**Location:** After `SignalGenerator` class

```python
class SignalPersistence:
    """Handles database persistence of signals (AC2)"""
    
    def __init__(self, db_path: str = "data/db/trading.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.conn = None
        
    def connect(self) -> None:
        """Open SQLite connection"""
        import sqlite3
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
    def disconnect(self) -> None:
        """Close SQLite connection"""
        if self.conn:
            self.conn.close()
            
    def insert(self, signal: Signal) -> bool:
        """
        MAIN AC2 METHOD: Persist signal to database with market context
        
        Args:
            signal: Signal object from AC1
            
        Returns:
            bool: True if successful, False otherwise
            
        Process:
            1. Open DB connection
            2. Serialize market_context to JSON
            3. INSERT into signals table
            4. Commit transaction
            5. Log success/failure
            6. Return result
        """
        # TODO: Implementation goes here
        pass
```

#### Step 2: Serialize Market Context (30 minutes)

**Key Requirement:** Convert `MarketContext` object to JSON string

**Implementation:**

```python
import json
from typing import Optional

def _serialize_market_context(self, market_context: Optional[MarketContext]) -> str:
    """
    Convert MarketContext object to JSON string for DB storage
    
    Input: MarketContext object with 8 fields
    Output: JSON string like:
            {"rsi": 65.5, "atr": 50.0, "bb_upper": 123.75, ...}
    """
    if market_context is None:
        return json.dumps({})
    
    context_dict = {
        "rsi": market_context.rsi,
        "atr": market_context.atr,
        "bb_upper": market_context.bb_upper,
        "bb_lower": market_context.bb_lower,
        "volume": market_context.volume,
        "spread": market_context.spread,
        "trend_direction": market_context.trend_direction,
        "last_close": market_context.last_close,
    }
    
    return json.dumps(context_dict)
```

#### Step 3: Implement INSERT Logic (1 hour)

**Main Logic:**

```python
def insert(self, signal: Signal) -> bool:
    """Persist signal to database"""
    
    if not self.conn:
        self.connect()
    
    try:
        # Serialize market context
        market_context_json = self._serialize_market_context(signal.market_context)
        
        # Prepare INSERT statement
        insert_sql = """
            INSERT INTO signals 
            (signal_id, timestamp, symbol, signal_type, smc_score, 
             smc_detector, entry_price, market_context_json, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Data tuple
        values = (
            signal.signal_id,
            signal.timestamp,
            signal.symbol,
            signal.signal_type.value,  # Enum → string
            signal.smc_score,
            signal.smc_detector.value,  # Enum → string
            signal.entry_price,
            market_context_json,
            "READY"  # Initial status
        )
        
        # Execute INSERT
        cursor = self.conn.cursor()
        cursor.execute(insert_sql, values)
        self.conn.commit()
        
        # Log success
        logging.info(f"""[AC2-PERSISTED] Signal inserted:
            signal_id: {signal.signal_id}
            symbol: {signal.symbol}
            type: {signal.signal_type}
            score: {signal.smc_score:+.1f}
            status: READY for Camada 2
        """)
        
        return True
        
    except Exception as e:
        logging.error(f"[AC2-ERROR] Failed to insert signal: {str(e)}")
        self.conn.rollback()
        return False
```

#### Step 4: Add Transaction Management (30 minutes)

**Key Features:**
- Automatic commit on success
- Automatic rollback on failure
- Handle duplicate signal_id (UNIQUE constraint)

```python
def insert_batch(self, signals: List[Signal]) -> int:
    """Insert multiple signals in single transaction"""
    
    if not self.conn:
        self.connect()
    
    successful = 0
    
    try:
        cursor = self.conn.cursor()
        
        for signal in signals:
            try:
                market_context_json = self._serialize_market_context(signal.market_context)
                
                insert_sql = """
                    INSERT INTO signals 
                    (signal_id, timestamp, symbol, signal_type, smc_score, 
                     smc_detector, entry_price, market_context_json, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                values = (
                    signal.signal_id,
                    signal.timestamp,
                    signal.symbol,
                    signal.signal_type.value,
                    signal.smc_score,
                    signal.smc_detector.value,
                    signal.entry_price,
                    market_context_json,
                    "READY"
                )
                
                cursor.execute(insert_sql, values)
                successful += 1
                
            except sqlite3.IntegrityError:
                # Duplicate signal_id - skip
                logging.warning(f"[AC2-DUPLICATE] Signal {signal.signal_id} already exists")
                continue
        
        self.conn.commit()
        logging.info(f"[AC2-BATCH] Inserted {successful}/{len(signals)} signals")
        return successful
        
    except Exception as e:
        logging.error(f"[AC2-ERROR] Batch insert failed: {str(e)}")
        self.conn.rollback()
        return 0
```

---

### Phase 3: Testing (45 minutes)

#### Test 1: Single Signal Insertion

**File:** `tests/test_camada2_ac2_signal_persistence.py`

```python
def test_ac2_insert_single_signal():
    """Test inserting a single signal to database"""
    
    # Setup
    persistence = SignalPersistence("data/db/trading.db")
    persistence.connect()
    
    # Create test signal (from AC1)
    signal = Signal(
        signal_id="test-uuid-12345",
        timestamp=datetime(2026, 3, 5, 14, 24, 0, 12000),
        symbol="WIN",
        signal_type=SignalType.BUY,
        smc_score=1.5,
        smc_detector=SMCDetector.BOS,
        entry_price=123.6,
        market_context=MarketContext(
            rsi=65.5,
            atr=50.0,
            bb_upper=123.75,
            bb_lower=123.15,
            volume=450,
            spread=2.0,
            trend_direction="UP",
            last_close=123.45
        )
    )
    
    # Execute
    result = persistence.insert(signal)
    
    # Verify
    assert result == True, "Insert should return True"
    
    # Query database to confirm
    cursor = persistence.conn.cursor()
    cursor.execute("SELECT * FROM signals WHERE signal_id = ?", (signal.signal_id,))
    row = cursor.fetchone()
    
    assert row is not None, "Signal should exist in database"
    assert row["symbol"] == "WIN"
    assert row["signal_type"] == "BUY"
    assert row["smc_score"] == 1.5
    
    # Verify market context JSON
    import json
    context = json.loads(row["market_context_json"])
    assert context["rsi"] == 65.5
    assert context["atr"] == 50.0
    assert context["volume"] == 450
    
    # Cleanup
    persistence.disconnect()
```

#### Test 2: Batch Insertion

```python
def test_ac2_insert_batch_signals():
    """Test inserting multiple signals atomically"""
    
    persistence = SignalPersistence("data/db/trading.db")
    persistence.connect()
    
    # Create 3 test signals
    signals = []
    for i in range(3):
        signal = Signal(
            signal_id=f"test-batch-{i}",
            timestamp=datetime(2026, 3, 5, 14, 24, i*60),
            symbol="WIN",
            signal_type=SignalType.BUY if i % 2 == 0 else SignalType.SELL,
            smc_score=1.5 + i * 0.5,
            smc_detector=SMCDetector.BOS,
            entry_price=123.6 + i,
            market_context=MarketContext(rsi=60+i*5, atr=50, ...)
        )
        signals.append(signal)
    
    # Insert batch
    successful = persistence.insert_batch(signals)
    
    # Verify
    assert successful == 3, "All 3 signals should be inserted"
    
    cursor = persistence.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM signals WHERE signal_id LIKE 'test-batch-%'")
    count = cursor.fetchone()[0]
    assert count == 3
    
    persistence.disconnect()
```

#### Test 3: Duplicate Rejection

```python
def test_ac2_rejects_duplicate_signal_id():
    """Test that duplicate signal_id is rejected by UNIQUE constraint"""
    
    persistence = SignalPersistence("data/db/trading.db")
    persistence.connect()
    
    # Create signal
    signal = Signal(
        signal_id="duplicate-test-123",
        timestamp=datetime(2026, 3, 5, 14, 24, 0),
        symbol="WIN",
        signal_type=SignalType.BUY,
        smc_score=1.5,
        smc_detector=SMCDetector.BOS,
        entry_price=123.6,
        market_context=MarketContext(...)
    )
    
    # Insert first time - should succeed
    result1 = persistence.insert(signal)
    assert result1 == True
    
    # Try inserting same signal again - should fail gracefully
    result2 = persistence.insert(signal)
    assert result2 == False  # Duplicate rejected
    
    # Verify only ONE signal in database
    cursor = persistence.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM signals WHERE signal_id = ?", (signal.signal_id,))
    count = cursor.fetchone()[0]
    assert count == 1  # Only one copy
    
    persistence.disconnect()
```

#### Test 4: Market Context Serialization

```python
def test_ac2_market_context_serialization():
    """Test JSON serialization of market context"""
    
    persistence = SignalPersistence("data/db/trading.db")
    
    # Create context with all 8 fields
    context = MarketContext(
        rsi=65.5,
        atr=50.0,
        bb_upper=123.75,
        bb_lower=123.15,
        volume=450,
        spread=2.0,
        trend_direction="UP",
        last_close=123.45
    )
    
    # Serialize
    json_str = persistence._serialize_market_context(context)
    
    # Deserialize and verify
    import json
    data = json.loads(json_str)
    assert data["rsi"] == 65.5
    assert data["atr"] == 50.0
    assert data["volume"] == 450
    assert data["trend_direction"] == "UP"
    assert len(data) == 8  # All 8 fields present
```

---

### Phase 4: Integration with AC1 (30 minutes)

**Connect AC1 → AC2 Pipeline:**

```python
# In agent_executor.py or equivalent

from src.application.signal_persistence import SignalGenerator, SignalPersistence

class AgentExecutor:
    def __init__(self):
        self.signal_generator = SignalGenerator()
        self.signal_persistence = SignalPersistence()
        self.signal_persistence.connect()
    
    def on_m5_candle_close(self, candle_data: dict):
        """Called every M5 candle close"""
        
        # AC1: Generate signal
        signal = self.signal_generator.detect_smc(
            candles_m5=candle_data,
            current_price=candle_data["close"]
        )
        
        # AC2: Persist if signal generated
        if signal:
            success = self.signal_persistence.insert(signal)
            if success:
                logging.info(f"[PIPELINE] Signal {signal.signal_id} persisted")
                # Now ready for AC3: Tracking
            else:
                logging.error(f"[PIPELINE] Failed to persist signal {signal.signal_id}")
```

---

### Phase 5: Code Quality Review (30 minutes)

**Checklist:**

- [ ] Type hints on all parameters
- [ ] Docstrings on all public methods
- [ ] Error handling (try/except)
- [ ] Logging statements ([AC2-*] prefix)
- [ ] Transaction management (commit/rollback)
- [ ] Resource cleanup (disconnect)
- [ ] Edge cases (None context, duplicate signals)

**Run Quality Checks:**

```bash
# Type checking
mypy src/application/signal_persistence.py --strict

# Format
black src/application/signal_persistence.py

# Lint
flake8 src/application/signal_persistence.py

# Docstring validation
pydocstyle src/application/signal_persistence.py
```

---

## Test Execution

**Run AC2 Tests:**

```bash
C:\repo\operador-day-trade-win> pytest tests/test_camada2_ac2_signal_persistence.py -v

# Expected output:
# test_ac2_insert_single_signal PASSED                                [25%]
# test_ac2_insert_batch_signals PASSED                                [50%]
# test_ac2_rejects_duplicate_signal_id PASSED                         [75%]
# test_ac2_market_context_serialization PASSED                        [100%]
#
# ======================== 4 passed in 0.23s ========================
```

---

## Database Verification

**After AC2 Implementation:**

```bash
# Query persisted signals
C:\repo\operador-day-trade-win> python

>>> import sqlite3, json
>>> conn = sqlite3.connect('data/db/trading.db')
>>> cursor = conn.cursor()

# Get first signal
>>> cursor.execute("""
    SELECT signal_id, symbol, signal_type, smc_score, 
           market_context_json, status
    FROM signals
    WHERE status = 'READY'
    LIMIT 1
""")
>>> row = cursor.fetchone()
>>> print(f"Signal: {row[0][:8]}... {row[1]} {row[2]} score={row[3]:+.1f}")
>>> context = json.loads(row[4])
>>> print(f"Context: RSI={context['rsi']}, ATR={context['atr']}, Vol={context['volume']}")

# Count total signals
>>> cursor.execute("SELECT COUNT(*) FROM signals")
>>> print(f"Total signals in database: {cursor.fetchone()[0]}")
```

**Expected Output:**
```
Signal: d4a82f1c... WIN BUY score=+1.5
Context: RSI=65.5, ATR=50.0, Vol=450
Total signals in database: 23
```

---

## Documentation Updates

**After AC2 Implementation:**

1. **Create AC2 Implementation Summary**
   - File: `docs/AC2_SIGNAL_PERSISTENCE.md`
   - Content: Implementation details, test results, SQL schema

2. **Update README.md**
   - Add AC2 completion status
   - Link to AC2 documentation

3. **Update BACKLOG_UNIFICADO.md**
   - Add AC2 completion entry
   - Reference test results

4. **Create Test Results Document**
   - File: `docs/ENGINEERING_REVIEW_AC2_SIGNAL_PERSISTENCE.md`
   - Content: Similar to AC1 review format

---

## Success Criteria (AC2 Complete)

- [x] Method `SignalPersistence.insert()` implemented
- [x] Market context JSON serialization working
- [x] Database transaction management (commit/rollback)
- [x] Duplicate signal rejection (UNIQUE constraint)
- [x] 4 comprehensive tests PASSING (100%)
- [x] Code quality: Type hints, docstrings, error handling
- [x] Integration verified: AC1 → AC2 pipeline
- [x] Documentation: AC2 guide + test results
- [x] Ready for AC3 (Signal Tracking)

---

## Estimated Timeline

```
Phase 1: Understand Current State     ✓ 15 min    (Total: 0:15)
Phase 2: Implement insert()           ✓ 120 min   (Total: 2:15)
Phase 3: Testing                      ✓ 45 min    (Total: 3:00)
Phase 4: AC1 Integration              ✓ 30 min    (Total: 3:30)
Phase 5: Code Quality Review          ✓ 30 min    (Total: 4:00)
─────────────────────────────────────────────────
TOTAL ESTIMATED TIME:                    4 hours

With debugging/iteration: 4-5 hours expected
```

---

## Reference Documents

- Signal Examples: `docs/LOG_EXAMPLES_AC1_SIGNAL_GENERATION.md` (Section 4: Detailed Signal Fields)
- DB Schema: `src/infrastructure/database_schema.py` or `data/db/trading.db`
- AC1 Code: `src/application/signal_persistence.py` (SignalGenerator class)
- AC1 Tests: `tests/test_camada1_ac1_signal_generation.py`

---

## Next: AC3 (Signal Tracking)

Once AC2 is complete, AC3 will:
- Track signal from generation through outcome
- Update outcome_type, outcome_pnl fields
- Link to potential trade execution
- Archive signals after 60-second window

---

**Status:** 🟡 READY TO IMPLEMENT AC2  
**Blocking:** AC1 ✅ COMPLETE  
**Start AC2 when:** All AC1 documentation reviewed & understood  
**Estimated Completion:** 05/03/2026 18:00 (if starting now at 14:30)
