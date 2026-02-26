# 🚀 PRIORITY 4: ATI-1 WebSocket Real-time Orders

**Owner:** Dev-Backend-3
**Assigned:** Eng Sr to assign
**Status:** ACTIVE - IN EXECUTION
**Start Time:** 2026-02-27 00:00:00Z
**Estimated Duration:** 4-6 hours
**Target Completion:** When P95 latency <100ms + 6/6 AC tests passing

---

## 📋 TASK SHEET

### Subtask 4.1: Event Loop Setup + Connection Manager
**Duration:** 45 min
**Dependencies:** None

```python
# Location: src/application/websocket_server_ati1.py
# Todo:
  [ ] Create FastAPI app with WebSocket support
  [ ] Implement ConnectionManager class
  [ ] Methods: connect(), disconnect(), broadcast()
  [ ] Store active connections dict
  [ ] Handle authentication token validation
```

**Acceptance Criteria:**
- [ ] Module imports without errors
- [ ] FastAPI app initialized
- [ ] ConnectionManager can store/retrieve connections

**Test File:** tests/unit/test_ati1_websocket_server.py
- [ ] test_connection_manager_connect()
- [ ] test_connection_manager_disconnect()

---

### Subtask 4.2: WebSocket Endpoint Implementation
**Duration:** 1.5 hours
**Dependencies:** 4.1 complete

```python
# Required:
  [ ] @app.websocket("/ws/orders/{trader_id}") endpoint
  [ ] JWT token validation from query params
  [ ] Connection acceptance
  [ ] Message handling loop
  [ ] Error handling (disconnect/reconnect)
```

**Acceptance Criteria (AC):**
- [ ] AC-1: Connection persistence (reconnect within 5s)
- [ ] AC-2: P95 latency < 100ms
- [ ] AC-5: Graceful disconnect (cleanup resources)

**Tests:**
- [ ] test_websocket_connection_success()
- [ ] test_websocket_authentication_failure()
- [ ] test_websocket_message_handling()

---

### Subtask 4.3: Heartbeat Implementation
**Duration:** 1 hour
**Dependencies:** 4.2 complete

```python
# Required:
  [ ] Ping task every 30s
  [ ] Pong response from client
  [ ] Auto-disconnect on missed heartbeat
  [ ] Reconnection logic
```

**Acceptance Criteria:**
- [ ] AC-6: Heartbeat working (30s interval)
- [ ] No message loss during heartbeat

**Tests:**
- [ ] test_heartbeat_interval()
- [ ] test_missed_heartbeat_disconnect()

---

### Subtask 4.4: Performance + Integration
**Duration:** 1.5 hours
**Dependencies:** 4.3 complete

```python
# Required:
  [ ] Latency tracking (P95 < 100ms)
  [ ] Connection scaling test (500 concurrent)
  [ ] Message format validation
  [ ] Integration with order queue (mock)
```

**Acceptance Criteria:**
- [ ] AC-3: Support 500 concurrent connections
- [ ] AC-4: No message loss
- [ ] Performance: P95 <100ms confirmed

**Tests:**
- [ ] test_concurrent_connections_500()
- [ ] test_message_ordering()
- [ ] test_latency_P95()

---

## 🎯 SUCCESS CRITERIA (All 6 AC)

```
✅ AC-1: Connection persistence (reconnect within 5s)
✅ AC-2: P95 latency < 100ms
✅ AC-3: Support 500 concurrent connections
✅ AC-4: No message loss (at-least-once delivery)
✅ AC-5: Graceful disconnect (cleanup)
✅ AC-6: Heartbeat working (30s interval)

MUST HAVE:
✅ 6/6 AC tests PASSING
✅ Code compiles without errors
✅ All docstrings + type hints present
✅ 150-200 LOC production code
✅ 100+ LOC test code
```

---

## 📊 DELIVERABLES

**Code Files:**
- [ ] `src/application/websocket_server_ati1.py` (150-200 LOC)
- [ ] `tests/unit/test_ati1_websocket_server.py` (100+ LOC)

**PR When Done:**
- [ ] All 6 AC tests PASSING
- [ ] Code review checklist complete
- [ ] Ready to merge to feature/ATI-1-websocket-server

---

## ⏱️ EXECUTION TIMELINE

```
00:00 - 00:45  → Subtask 4.1 (Connection manager)
00:45 - 02:15  → Subtask 4.2 (WebSocket endpoint)
02:15 - 03:15  → Subtask 4.3 (Heartbeat)
03:15 - 04:45  → Subtask 4.4 (Performance + tests)

Total: ~4.75 hours
```

---

## 📞 BLOCKERS / QUESTIONS

If you get stuck:
- Q: "ConnectionManager not storing connections?"
  → Check dict vs class attribute scope
- Q: "Heartbeat timing wrong?"
  → Use asyncio.sleep(30) not time.sleep()
- Q: "Tests failing?"
  → Verify pytest fixtures in test file

**Escalate to Eng Sr if:** Blocker > 30 min

---

## ✅ NEXT STEP

**Type when complete:**
```
"PRIORITY 4 DONE: WebSocket endpoint ready + 6/6 AC tests passing"
```

Then: Move to PRIORITY 6 (RabbitMQ) - which depends on this

---

**Status:** 🟢 **ACTIVE**
**Owner:** Dev-Backend-3
**Next Review:** After Subtask 4.2 (2h 15m)
