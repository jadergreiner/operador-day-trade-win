# 🚀 PRIORITY 4 SUBTASK 4.2: WebSocket Endpoint Implementation

**Owner:** Dev-Backend-3  
**Status:** 🟢 START NOW  
**Duration:** 1.5 hours  
**Prerequisite:** ✅ Subtask 4.1 COMPLETE  
**Target:** `/ws/orders/{trader_id}` endpoint fully functional

---

## 📋 Quick Overview

**What This Subtask Adds to the Code:**

1. **FastAPI App Initialization** (lines 140-145)
   - Already in code ✅

2. **CORS Configuration** (lines 147-154)
   - Already in code ✅

3. **Global Managers** (lines 157-160)
   - Already in code ✅

4. **WebSocket Endpoint** (lines 163-223)
   - Already in code ✅
   - `@app.websocket("/ws/orders/{trader_id}")`

5. **Health Check Endpoint** (lines 226-235)
   - Already in code ✅

---

## 🔧 STEP-BY-STEP EXECUTION

### Step 1: Review FastAPI Endpoint Code (10 min)

**File:** `src/application/websocket_server_ati1.py`

**Read:**
- Lines 163-223: `websocket_endpoint()` function
- JWT verification (line 180-184)
- ConnectionManager.connect() call (line 186-194)
- HeartbeatManager.start_heartbeat() call (line 196-197)
- Message loop (line 199-206)
- Exception handling (line 208-223)

**Key Components:**
1. Query parameter: `token` (JWT token from client)
2. Path parameter: `trader_id` (from URL)
3. Connection flow:
   - Verify JWT token
   - Connect to manager
   - Start heartbeat
   - Message loop
   - Exception handling + cleanup

**AC Requirements:**
- AC-1: Connection persistence ← Already handled by ConnectionManager ✅
- AC-2: P95 latency < 100ms ← Track in line 206
- AC-5: Graceful disconnect ← Cleanup in finally block ✅
- AC-6: Heartbeat 30s ← Already started in line 196 ✅

**Code Status:** ✅ COMPLETE (all logic present)

---

### Step 2: Verify JWT Verification Logic (5 min)

**Code at lines 180-184:**
```python
try:
    verify_jwt_token(token)
except HTTPException as e:
    await websocket.close(code=1008, reason="Unauthorized")
```

**Key Points:**
- JWT_SECRET matches between auth endpoint (ATI-2) and this endpoint
- Shared secret: "your-secret-key" (placeholder, should be env var in production)
- Token format: Bearer token passed as `?token=xxx`

**Test Setup Needed:**
```python
# Client will connect like:
# ws://localhost:8000/ws/orders/TRADER_001?token=<JWT_TOKEN>

# JWT token structure:
# {"trader_id": "TRADER_001", "exp": <future>, "iat": <now>}
```

---

### Step 3: Run Unit Tests for Endpoint (20 min)

```bash
# Terminal: Run WebSocket endpoint tests only
cd c:\repo\operador-day-trade-win

# Test: WebSocket connection valid token
pytest tests/unit/test_ati1_websocket_server.py::TestWebSocketEndpoint -v

# Test: Health endpoint
pytest tests/unit/test_ati1_websocket_server.py::TestWebSocketEndpoint::test_health_check -v

# Expected:
# test_health_check PASSED
# test_websocket_connection_invalid_token PASSED (should raise)
```

---

### Step 4: Run Integration Test (10 min)

```bash
# Integration test: Full connection flow
pytest tests/unit/test_ati1_websocket_server.py::TestAcceptanceCriteria::test_all_ac_integrated -v

# This tests:
# ✅ AC-1: Connection persistence
# ✅ AC-2: P95 latency
# ✅ AC-3: Concurrent (500)
# ✅ AC-4: No message loss
# ✅ AC-5: Graceful disconnect
# ✅ AC-6: Heartbeat
```

---

### Step 5: Manual Integration Test (15 min)

**Create test file:** `test_websocket_manual.py`

```python
# Manual WebSocket client test

import asyncio
import websockets
import json
import jwt
from datetime import datetime, timedelta
from src.application.websocket_server_ati1 import (
    app, JWT_SECRET, JWT_ALGORITHM
)
from fastapi.testclient import TestClient

def create_jwt_token(trader_id):
    """Create valid JWT token"""
    payload = {
        "trader_id": trader_id,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

async def manual_websocket_test():
    """Test WebSocket connection with token"""
    
    # Create token
    token = create_jwt_token("TRADER_001")
    print(f"Token created: {token[:20]}...")
    
    # Note: Manual WebSocket test requires running server
    # For now, we'll use TestClient which is done in pytest
    
    client = TestClient(app)
    
    # Test 1: Health check
    response = client.get("/health")
    assert response.status_code == 200
    print("✅ Test 1: Health check passed")
    
    # Test 2: Health shows stats
    data = response.json()
    assert "connected_traders" in data
    print("✅ Test 2: Health stats present")
    print(f"   Connected traders: {data['connected_traders']}")
    print(f"   Total connections: {data['total_connections']}")

# Run
asyncio.run(manual_websocket_test())
```

**Run manual test:**
```bash
python test_websocket_manual.py
```

---

### Step 6: Performance Validation (15 min)

**Create test file:** `test_websocket_performance.py`

```python
# Performance test: Latency measurement

import asyncio
import time
from unittest.mock import AsyncMock, patch
from src.application.websocket_server_ati1 import connection_manager, ConnectionManager

async def test_latency():
    """Measure connection latency - AC-2: P95 < 100ms"""
    
    manager = ConnectionManager()
    latencies = []
    
    # Simulate 100 connections
    for i in range(100):
        start = time.time()
        ws = AsyncMock()
        trader_id = f"TRADER_{i:03d}"
        
        await manager.connect(ws, trader_id)
        
        latency = (time.time() - start) * 1000  # milliseconds
        latencies.append(latency)
    
    # Sort and find P95
    latencies.sort()
    p95_latency = latencies[int(len(latencies) * 0.95)]
    
    print(f"Latency Statistics:")
    print(f"  Min: {min(latencies):.2f}ms")
    print(f"  P50: {latencies[50]:.2f}ms")
    print(f"  P95: {p95_latency:.2f}ms")
    print(f"  Max: {max(latencies):.2f}ms")
    
    # AC-2: P95 should be < 100ms
    assert p95_latency < 100, f"P95 latency {p95_latency}ms exceeds 100ms target"
    print("✅ AC-2: P95 latency < 100ms PASSED")

asyncio.run(test_latency())
```

**Run performance test:**
```bash
python test_websocket_performance.py
```

---

### Step 7: Verify All Tests Pass (10 min)

```bash
# Run ALL WebSocket tests
pytest tests/unit/test_ati1_websocket_server.py -v

# Expected:
# test_connection_manager_connect PASSED
# test_connection_manager_disconnect PASSED
# test_broadcast_message PASSED
# test_message_handler_validate PASSED
# test_heartbeat_interval PASSED
# test_health_check PASSED
# test_websocket_connection_invalid_token PASSED
# test_latency_tracking PASSED
# test_concurrent_connections PASSED
# test_graceful_disconnect PASSED
# test_all_ac_integrated PASSED
# 
# ============ 11 passed in X.XXs ============
```

---

## ✅ AC Validation for Subtask 4.2

**AC-1: Connection persistence (reconnect within 5s)**
- ✅ Endpoint accepts WebSocket
- ✅ ConnectionManager persists connection
- ✅ Test: WebSocket stays connected unless closed

**AC-2: P95 latency < 100ms**
- ✅ Connection setup fast (<100ms)
- ✅ Test: test_latency_tracking validates P95 < 100ms

**AC-5: Graceful disconnect (cleanup)**
- ✅ Finally block: cleanup heartbeat + disconnect
- ✅ Proper error handling + logging
- ✅ Test: test_graceful_disconnect validates cleanup

**AC-6: Heartbeat working (30s interval)**
- ✅ HeartbeatManager starts with connection
- ✅ Sends ping every 30s
- ✅ Test: test_heartbeat_interval validates timing

---

## 📊 Success Criteria for Subtask 4.2

```
✅ FastAPI app initialized
✅ CORS configured for WebSocket
✅ Endpoint: /ws/orders/{trader_id} working
✅ JWT token verification working
✅ ConnectionManager.connect() called
✅ HeartbeatManager.start_heartbeat() called
✅ Message loop functioning
✅ Exception handling complete
✅ Cleanup in finally block present
✅ 11+ unit tests PASSING
✅ P95 latency < 100ms confirmed
✅ Ready to proceed to Subtask 4.3
```

---

## 🚀 Next: Subtask 4.3 (After This Completes)

**Tasks:**
- Heartbeat implementation (already in code!)
- Message timeout handling
- Auto-disconnect on missed heartbeat

**Duration:** 1 hour

---

## 📞 Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| JWT token invalid | Create new token with `create_jwt_token()` function |
| WebSocket won't connect | Check token format: `?token=<jwt>` |
| Heartbeat not firing | Ensure `asyncio.sleep()` not `time.sleep()` |
| Test timeout | Increase pytest timeout in command |

---

## ⏱️ Timeline for This Subtask

```
00:00 - 00:10  Code review (FastAPI + endpoint)
00:10 - 00:20  JWT verification understanding
00:20 - 00:40  Unit tests run
00:40 - 00:55  Manual tests + performance
00:55 - 01:30  Final verification + validation

Total: 1.5 hours
```

---

## ✅ Ready for Subtask 4.2?

**You should have:**
- ✅ Subtask 4.1 COMPLETE
- ✅ ConnectionManager working
- ✅ No import errors
- ✅ Pytest environment ready

**Type when READY:**
```
"PRIORITY 4: Subtask 4.2 READY - starting FastAPI endpoint tests"
```

---

**Status:** 🟢 **READY TO EXECUTE**  
**Owner:** Dev-Backend-3  
**Blocker:** None - code ready in repo  
**Estimated Time to Completion:** 1.5 hours
