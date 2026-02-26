# 🚀 PRIORITY 4 SUBTASK 4.1: ConnectionManager Setup + Event Loop

**Owner:** Dev-Backend-3  
**Status:** 🟢 START NOW  
**Duration:** 45 minutes  
**Target:** ConnectionManager fully functional + accept/disconnect/broadcast working

---

## 📋 Checklist Imediato

```
□ 1. Verify Python environment (3.11.9)
□ 2. Verify FastAPI installed (0.104.1+)
□ 3. Project structure: src/application/ exists
□ 4. Code file ready: src/application/websocket_server_ati1.py ✅ (already created)
□ 5. Test file ready: tests/unit/test_ati1_websocket_server.py ✅ (already created)
□ 6. Run unit tests for ConnectionManager only
□ 7. Verify all 2 AC tests passing
```

---

## 🔧 STEP-BY-STEP EXECUTION

### Step 1: Prepare Environment (5 min)

```bash
# Terminal 1: Verify Python
python --version
# Expected: Python 3.11.9

# Verify FastAPI
python -c "import fastapi; print(fastapi.__version__)"
# Expected: 0.104.1+

# Create necessary directories if missing
mkdir -p src/application
mkdir -p tests/unit
```

**Expected Status:** ✅ READY

---

### Step 2: Review ConnectionManager Code (10 min)

**File:** `src/application/websocket_server_ati1.py`

**Read:**
- Lines 26-87: `ConnectionManager` class
- Methods to understand:
  - `__init__`: Initialize active_connections dict
  - `connect()`: Accept WebSocket + register trader
  - `disconnect()`: Remove WebSocket connection
  - `broadcast()`: Send message to trader(s)

**Key Points:**
- Uses dict: `{trader_id: [ws1, ws2, ...]}`
- Stores connection times for latency tracking
- Handles max connections per trader (5)

**AC Requirements:**
- AC-1: Connection persistence (reconnect within 5s)
- AC-2: P95 latency < 100ms → need connection_times tracking ✅

**Code Status:** ✅ COMPLETE (370 LOC, all 3 classes present)

---

### Step 3: Run ConnectionManager-Only Tests (15 min)

```bash
# Terminal 2: Run pytest for ConnectionManager tests
cd c:\repo\operador-day-trade-win

# Run ONLY ConnectionManager tests
pytest tests/unit/test_ati1_websocket_server.py::TestConnectionManager -v

# Expected output:
# test_connection_manager_connect PASSED
# test_connection_manager_disconnect PASSED
# test_broadcast_message PASSED
```

**If tests FAIL:**

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: pytest` | `pip install pytest pytest-asyncio` |
| `ModuleNotFoundError: fastapi` | `pip install fastapi` |
| `async def requires asyncio` | `pip install pytest-asyncio` |
| Connection dict not working | Check line 31 in websocket_server_ati1.py |

---

### Step 4: Verify Functionality (10 min)

**Manual Test Code:**

```python
# Create temporary test file: test_manual_connectionmanager.py

import asyncio
from src.application.websocket_server_ati1 import ConnectionManager
from unittest.mock import AsyncMock

async def manual_test():
    manager = ConnectionManager()
    
    # Create mock websockets
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    
    # Test 1: Connect
    print("Test 1: Connecting...")
    await manager.connect(ws1, "TRADER_001")
    assert "TRADER_001" in manager.active_connections
    print("✅ Connect test passed")
    
    # Test 2: Store connection time (for AC-2 latency)
    print("Test 2: Connection time stored...")
    assert ws1 in manager.connection_times
    print("✅ Connection time test passed")
    
    # Test 3: Multiple connections per trader
    print("Test 3: Multiple connections...")
    await manager.connect(ws2, "TRADER_001")
    assert len(manager.active_connections["TRADER_001"]) == 2
    print("✅ Multiple connections test passed")
    
    # Test 4: Broadcast
    print("Test 4: Broadcasting...")
    await manager.broadcast(
        {"type": "test", "data": "hello"},
        trader_id="TRADER_001"
    )
    assert ws1.send_json.called
    print("✅ Broadcast test passed")
    
    # Test 5: Disconnect
    print("Test 5: Disconnecting...")
    await manager.disconnect(ws1, "TRADER_001")
    assert len(manager.active_connections["TRADER_001"]) == 1
    print("✅ Disconnect test passed")
    
    print("\n✅✅✅ All manual tests PASSED!")

# Run
asyncio.run(manual_test())
```

**Run manual test:**
```bash
python test_manual_connectionmanager.py
```

**Expected output:**
```
Test 1: Connecting...
✅ Connect test passed
Test 2: Connection time stored...
✅ Connection time test passed
Test 3: Multiple connections...
✅ Multiple connections test passed
Test 4: Broadcasting...
✅ Broadcast test passed
Test 5: Disconnecting...
✅ Disconnect test passed

✅✅✅ All manual tests PASSED!
```

---

### Step 5: Verify pytest All Tests Pass (10 min)

```bash
# Run ALL ConnectionManager-related tests
pytest tests/unit/test_ati1_websocket_server.py::TestConnectionManager -v --tb=short

# Expected: 3/3 tests PASSED
```

---

## ✅ AC Validation for Subtask 4.1

**AC-1: Connection persistence (reconnect within 5s)**
- ✅ ConnectionManager stores connections in dict
- ✅ Can retrieve after connect
- ✅ Test: `test_connection_manager_connect()`

**AC-2: P95 latency < 100ms (preparation)**
- ✅ connection_times dict stores timestamps
- ✅ Ready for latency tracking in next subtask
- ✅ Foundation for latency validation

---

## 📊 Success Criteria for Subtask 4.1

```
✅ ConnectionManager class functional
✅ 3 public methods working:
   - __init__() → initialize dicts
   - connect() → accept + register
   - disconnect() → cleanup
   - broadcast() → send to trader(s)
✅ 3/3 unit tests PASSING
✅ No errors on PyTest
✅ Code compiles without warnings
✅ Ready to proceed to Subtask 4.2
```

---

## 🔗 Next: Subtask 4.2 (Ready After This)

Once Subtask 4.1 complete:
- Start: `FastAPI app initialization`
- Time: 1.5 hours
- Task: Create WebSocket endpoint at `/ws/orders/{trader_id}`

---

## 📞 Blockers / Questions

**Q: ConnectionManager not found?**
A: Ensure you're importing from correct path:
```python
from src.application.websocket_server_ati1 import ConnectionManager
```

**Q: AsyncMock not working?**
A: Install pytest-asyncio:
```bash
pip install pytest-asyncio
```

**Q: Tests timeout?**
A: Increase timeout in pytest.ini:
```ini
[pytest]
asyncio_mode = auto
timeout = 30
```

---

## ⏱️ Timeline for This Subtask

```
00:00 - 00:05  Environment verification
00:05 - 00:15  Code review
00:15 - 00:30  Unit tests run
00:30 - 00:40  Manual validation
00:40 - 00:45  Final verification

Total: 45 minutes
```

---

## ✅ Ready to Start?

**Type when Subtask 4.1 is COMPLETE:**
```
"PRIORITY 4: Subtask 4.1 DONE - ConnectionManager passing all tests, ready for 4.2"
```

Then automatically proceed to **Subtask 4.2: WebSocket Endpoint** (1.5h)

---

**Status:** 🟢 **READY TO EXECUTE**  
**Owner:** Dev-Backend-3  
**Blocker:** None - code ready in repo  
**Estimated Time to Completion:** 45 min
