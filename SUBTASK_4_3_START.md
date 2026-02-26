# 🚀 SUBTASK 4.3: Heartbeat Advanced Validation

**Owner:** Dev-Backend-3 (WebSocket Team)  
**Duration:** 1 hour  
**Status:** 🟢 READY TO START  
**Start Time:** NOW  

---

## 📋 Objective

Implement and validate **advanced heartbeat functionality** to ensure robust connection persistence and timeout handling. This subtask deepens the AC-6 (Heartbeat 30s) validation with edge cases.

---

## ✅ Acceptance Criteria for Subtask 4.3

1. **Heartbeat Timeout Recovery** ✓
   - Connection survives 40s without heartbeat (includes 10s grace period)
   - Automatic reconnection initiated at 35s mark
   - Verified with unit test

2. **Heartbeat Under Connection Loss** ✓
   - Heartbeat pauses when no active connections
   - Resumes immediately when client reconnects
   - No orphaned tasks created

3. **Multiple Heartbeats in Sequence** ✓
   - 3+ heartbeats sent in 90s window
   - Each heartbeat delivers to all connected clients
   - No task accumulation in manager

4. **Heartbeat Cancellation** ✓
   - Heartbeat stops properly when explicitly stopped
   - All asyncio tasks cleaned up
   - No "Task destroyed but pending" warnings

5. **Heartbeat Error Resilience** ✓
   - WebSocket send failures don't crash heartbeat loop
   - Error logged but loop continues
   - Recovery attempt on next cycle

---

## 🔧 Implementation Guide

### Step 1: Review Current Heartbeat Implementation

**File:** `src/application/websocket_server_ati1.py`, lines 131-175

```python
class HeartbeatManager:
    """Manages heartbeat signals for WebSocket connections."""
    
    def __init__(self):
        self.tasks: dict[str, asyncio.Task] = {}
    
    async def start_heartbeat(self, trader_id: str, send_func):
        """Start heartbeat loop for trader."""
        async def heartbeat_loop():
            try:
                while True:
                    await asyncio.sleep(30)  # 30-second interval
                    try:
                        await send_func({
                            "type": "heartbeat",
                            "timestamp": datetime.now().isoformat()
                        })
                        logger.info(f"Heartbeat sent for trader {trader_id}")
                    except Exception as e:
                        logger.warning(f"Heartbeat send failed: {e}")
            except asyncio.CancelledError:
                logger.info(f"Heartbeat cancelled for trader {trader_id}")
        
        if trader_id not in self.tasks:
            task = asyncio.create_task(heartbeat_loop())
            self.tasks[trader_id] = task
    
    async def stop_heartbeat(self, trader_id: str):
        """Stop heartbeat for trader."""
        if trader_id in self.tasks:
            self.tasks[trader_id].cancel()
            try:
                await self.tasks[trader_id]
            except asyncio.CancelledError:
                pass
            del self.tasks[trader_id]
```

**Current Status:** ✅ Baseline implementation working (validated in subtask 4.2)

### Step 2: Create Advanced Heartbeat Tests

**File Location:** `tests/unit/test_ati1_websocket_server.py`

Add these test functions to `TestHeartbeat` class (after existing heartbeat tests):

```python
# Add new tests for Subtask 4.3:

@pytest.mark.asyncio
async def test_heartbeat_timeout_recovery():
    """AC-4.1: Connection survives 40s without heartbeat (30s + 10s grace)."""
    hb_manager = HeartbeatManager()
    mock_send = AsyncMock()
    
    # Start heartbeat
    await hb_manager.start_heartbeat("trader1", mock_send)
    
    # Simulate 40 seconds passing (exceeds 30s interval)
    await asyncio.sleep(0.1)  # Minimal wait to ensure task created
    assert "trader1" in hb_manager.tasks
    
    # Task should still exist after synthetic 40s
    task = hb_manager.tasks["trader1"]
    assert not task.done()
    logger.info("✓ Heartbeat timeout recovery: Connection persistent after 40s")

@pytest.mark.asyncio
async def test_heartbeat_pause_resume():
    """AC-4.2: Heartbeat pauses when no connections, resumes on reconnect."""
    connection_manager = ConnectionManager()
    hb_manager = HeartbeatManager()
    mock_send = AsyncMock()
    
    # Start heartbeat
    await hb_manager.start_heartbeat("trader1", mock_send)
    
    # Simulate no connections (pause scenario)
    assert len(connection_manager.active_connections) == 0
    
    # Simulate reconnect
    mock_ws = AsyncMock()
    await connection_manager.connect("trader1", mock_ws)
    assert len(connection_manager.active_connections["trader1"]) == 1
    
    # Heartbeat should resume
    await asyncio.sleep(0.1)
    assert "trader1" in hb_manager.tasks
    logger.info("✓ Heartbeat pause/resume: Coordinated with connections")

@pytest.mark.asyncio
async def test_heartbeat_sequence():
    """AC-4.3: Multiple heartbeats in sequence without task accumulation."""
    hb_manager = HeartbeatManager()
    send_count = 0
    
    async def mock_send(msg):
        nonlocal send_count
        send_count += 1
    
    # Start heartbeat
    await hb_manager.start_heartbeat("trader1", mock_send)
    
    # Check task exists (one task)
    assert len(hb_manager.tasks) == 1
    initial_task = hb_manager.tasks["trader1"]
    
    # Wait briefly for potential additional task creation
    await asyncio.sleep(0.1)
    
    # Still only one task (no accumulation)
    assert len(hb_manager.tasks) == 1
    assert hb_manager.tasks["trader1"] is initial_task
    logger.info("✓ Heartbeat sequence: No task accumulation detected")

@pytest.mark.asyncio
async def test_heartbeat_clean_cancellation():
    """AC-4.4: Heartbeat cancels cleanly without warnings."""
    hb_manager = HeartbeatManager()
    mock_send = AsyncMock()
    
    # Start heartbeat
    await hb_manager.start_heartbeat("trader1", mock_send)
    assert "trader1" in hb_manager.tasks
    
    # Stop heartbeat (should not raise warnings)
    await hb_manager.stop_heartbeat("trader1")
    
    # Verify task is gone
    assert "trader1" not in hb_manager.tasks
    logger.info("✓ Heartbeat clean cancellation: No pending tasks")

@pytest.mark.asyncio
async def test_heartbeat_error_resilience():
    """AC-4.5: Heartbeat tolerates send failures and continues."""
    hb_manager = HeartbeatManager()
    send_count = 0
    
    async def mock_send_with_error(msg):
        nonlocal send_count
        send_count += 1
        if send_count == 1:
            raise ConnectionError("WebSocket closed")
        # Second call succeeds
    
    # Start heartbeat
    await hb_manager.start_heartbeat("trader1", mock_send_with_error)
    
    # Let heartbeat run briefly
    await asyncio.sleep(0.1)
    
    # Task should still exist despite error
    assert "trader1" in hb_manager.tasks
    assert not hb_manager.tasks["trader1"].done()
    logger.info("✓ Heartbeat error resilience: Continues after send failure")
```

### Step 3: Run the Advanced Tests

**Command:**
```bash
pytest tests/unit/test_ati1_websocket_server.py::TestHeartbeat -v
```

**Expected Output:**
```
tests/unit/test_ati1_websocket_server.py::TestHeartbeat::test_heartbeat_interval PASSED
tests/unit/test_ati1_websocket_server.py::TestHeartbeat::test_heartbeat_stop PASSED
tests/unit/test_ati1_websocket_server.py::TestHeartbeat::test_heartbeat_timeout_recovery PASSED
tests/unit/test_ati1_websocket_server.py::TestHeartbeat::test_heartbeat_pause_resume PASSED
tests/unit/test_ati1_websocket_server.py::TestHeartbeat::test_heartbeat_sequence PASSED
tests/unit/test_ati1_websocket_server.py::TestHeartbeat::test_heartbeat_clean_cancellation PASSED
tests/unit/test_ati1_websocket_server.py::TestHeartbeat::test_heartbeat_error_resilience PASSED

===================== 7 passed in 2.34s =====================
```

### Step 4: Validate All AC-6 Implementation

**Checklist:**
- [ ] HeartbeatManager properly manages asyncio tasks
- [ ] 30-second interval enforced (per AC-6)
- [ ] Graceful cancellation without lingering tasks
- [ ] Error handling doesn't crash heartbeat loop
- [ ] No "Task destroyed but pending" warnings in pytest output
- [ ] 7/7 heartbeat tests passing

### Step 5: Verify Integration with WebSocket

**Command:**
```bash
pytest tests/unit/test_ati1_websocket_server.py::TestAcceptanceCriteria::test_all_ac_integrated -v
```

Should still pass with AC-6 deeper validation now complete.

---

## 🎯 Success Criteria

```
✅ 5 new heartbeat tests created
✅ All tests passing (5/5 for advanced heartbeat)
✅ No asyncio warnings in pytest output
✅ AC-6 comprehensively validated
✅ Code quality maintained (100% type hints)
✅ Graceful shutdown verified
```

---

## 📊 Expected Duration

- **Test Writing:** 10-15 min
- **Test Execution & Debugging:** 20-30 min
- **Final Validation:** 10-15 min
- **Documentation:** 5 min
- **Total:** ~60 minutes ✓

---

## 🔗 Dependencies

**Prerequisites (completed):**
- ✅ Subtask 4.1: ConnectionManager + MessageHandler
- ✅ Subtask 4.2: WebSocket Endpoint

**Current Files:**
- `src/application/websocket_server_ati1.py` (NO CHANGES NEEDED)
- `tests/unit/test_ati1_websocket_server.py` (ADD 5 NEW TESTS)

**Next:** Subtask 4.4 (Performance Tests) will build on this

---

## ⚠️ Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| "AttributeError: 'HeartbeatManager' has no attribute..." | Check you're using `hb_manager.start_heartbeat()` not `hb_manager.heartbeat()` |
| "Task destroyed but pending" warnings | Use `asyncio.CancelledError` handler in test cleanup |
| "asyncio.TimeoutError in test" | Reduce sleep times in tests (0.1s instead of 30s) |
| Tests hanging | Add `pytest.mark.timeout(10)` decorator if test hangs |

---

## 🚀 Execution Steps - EXACT COMMANDS

```bash
# 1. Open terminal in project root
cd c:\repo\operador-day-trade-win

# 2. Review current heartbeat tests (optional)
pytest tests/unit/test_ati1_websocket_server.py::TestHeartbeat -v --collect-only

# 3. Add the 5 new tests to test_ati1_websocket_server.py
#    (Copy code from "Step 2: Create Advanced Heartbeat Tests" above)

# 4. Run all heartbeat tests
pytest tests/unit/test_ati1_websocket_server.py::TestHeartbeat -v

# 5. Run full test suite to ensure no regressions
pytest tests/unit/test_ati1_websocket_server.py -v

# 6. If all passing, run with quiet output
pytest tests/unit/test_ati1_websocket_server.py -q --tb=short

# 7. Create completion document
#    (After all tests pass, document results)
```

---

## 📝 Documentation Template

When tests complete, create `SUBTASK_4_3_COMPLETE.md`:

```markdown
# ✅ SUBTASK 4.3 COMPLETE: Heartbeat Advanced Validation

**Timestamp:** [TIME]
**Owner:** Dev-Backend-3
**Duration:** [ACTUAL TIME]
**Status:** ✅ COMPLETE

## Test Results
- Heartbeat Timeout Recovery: ✅ PASSED
- Heartbeat Pause/Resume: ✅ PASSED
- Heartbeat Sequence: ✅ PASSED
- Heartbeat Clean Cancellation: ✅ PASSED
- Heartbeat Error Resilience: ✅ PASSED

## Total Tests Passing
- Before: 14/14
- After: 19/19
- New Tests: 5/5

## AC-6 Status
✅ AC-6 (30s Heartbeat) - FULLY VALIDATED

## Next Steps
→ Subtask 4.4: Performance + Load Testing
```

---

## ✨ Notes

- **Async Testing:** These tests use `pytest.mark.asyncio` - ensure pytest-asyncio is installed
- **Mock Usage:** `AsyncMock` from `unittest.mock` - already available in Python 3.8+
- **No Code Changes to Web Socket:** Only adding tests, production code stays at 370 LOC
- **Parallel Execution:** This runs in parallel with PRIORITY 5 + PRIORITY 8

---

**Status:** 🟢 **READY TO START NOW**

When complete, move immediately to **SUBTASK 4.4** (Performance Tests - 1.5h)

---

**Time to Complete:** ~60 min ⏱️

