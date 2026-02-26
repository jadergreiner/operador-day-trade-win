# 🚀 PRIORITY 5: ATI-2 OAuth Authentication Endpoints

**Owner:** Dev-Backend-1
**Assigned:** Eng Sr to assign
**Status:** ACTIVE - IN EXECUTION
**Start Time:** 2026-02-27 00:00:00Z
**Estimated Duration:** 4-6 hours (parallel with PRIORITY 4)
**Target Completion:** When 8/8 AC tests passing + rate limiting verified

---

## 📋 TASK SHEET

### Subtask 5.1: JWTManager + PasswordManager Setup
**Duration:** 1 hour
**Dependencies:** None

```python
# Location: src/application/oauth_auth_ati2.py
# Todo:
  [ ] Create JWTManager class
  [ ] Methods: create_token(), verify_token()
  [ ] Token payload: trader_id, exp (8h)
  [ ] Create PasswordManager class
  [ ] Methods: hash_password(), verify_password() (bcrypt)
  [ ] Create RateLimiter class (in-memory or Redis ready)
```

**Acceptance Criteria:**
- [ ] JWT tokens created with 8h expiration
- [ ] Token verification works
- [ ] Passwords hashed with bcrypt (cost=10)

**Test File:** tests/unit/test_ati2_oauth_auth.py
- [ ] test_jwt_creation()
- [ ] test_jwt_verification()
- [ ] test_password_hashing()

---

### Subtask 5.2: Login Endpoint Implementation
**Duration:** 1.5 hours
**Dependencies:** 5.1 complete

```python
# Required:
  [ ] @app.post("/auth/login") endpoint
  [ ] Accept: username + password
  [ ] Validate against mock user DB
  [ ] Return: access_token + refresh_token + expires_in
  [ ] Rate limiting: 10 attempts / 5 min
  [ ] Session tracking (Redis or in-memory)
```

**Acceptance Criteria (AC):**
- [ ] AC-1: Successful login returns JWT tokens
- [ ] AC-2: Invalid credentials rejected (401)
- [ ] AC-3: Rate limiting enforced (10 attempts/5min)
- [ ] AC-7: Multi-device login support (track session ID)

**Tests:**
- [ ] test_login_success()
- [ ] test_login_invalid_credentials()
- [ ] test_rate_limiting_exceeded()
- [ ] test_multisession_tracking()

---

### Subtask 5.3: Token Refresh Endpoint
**Duration:** 1 hour
**Dependencies:** 5.2 complete

```python
# Required:
  [ ] @app.post("/auth/refresh-token") endpoint
  [ ] Accept: refresh_token + session_id
  [ ] Validate refresh token (30-day expiration)
  [ ] Return: new access_token
  [ ] Revoke old token
  [ ] Track token history for audit
```

**Acceptance Criteria:**
- [ ] AC-4: Refresh token extends session (8h more)
- [ ] AC-8: Token rotation logged for audit
- [ ] Expired tokens rejected (401)

**Tests:**
- [ ] test_refresh_token_success()
- [ ] test_refresh_token_expired()
- [ ] test_token_history_audit()

---

### Subtask 5.4: Integration + Security Testing
**Duration:** 1.5 hours
**Dependencies:** 5.3 complete

```python
# Required:
  [ ] Session table schema (trader_id, session_id, expires_at, device_id)
  [ ] Logout endpoint (invalidate session)
  [ ] CORS configuration (allow ws://)
  [ ] Security headers (X-Requested-With validation)
  [ ] Integration test with WebSocket endpoint
```

**Acceptance Criteria:**
- [ ] AC-5: Sessions properly validated
- [ ] AC-6: Logout clears session
- [ ] All 8 AC tests PASSING

**Tests:**
- [ ] test_session_validation()
- [ ] test_logout_clears_session()
- [ ] test_cors_headers()
- [ ] test_websocket_auth_integration()

---

## 🎯 SUCCESS CRITERIA (All 8 AC)

```
✅ AC-1: Login returns JWT tokens
✅ AC-2: Invalid credentials rejected (401)
✅ AC-3: Rate limiting enforced (10/5min)
✅ AC-4: Refresh token extends session (8h)
✅ AC-5: Sessions properly validated
✅ AC-6: Logout clears session
✅ AC-7: Multi-device support (session tracking)
✅ AC-8: Token rotation logged for audit

MUST HAVE:
✅ 8/8 AC tests PASSING
✅ Code compiles without errors
✅ All docstrings + type hints present
✅ 120-180 LOC production code
✅ 120+ LOC test code
✅ Rate limiting working
```

---

## 📊 DELIVERABLES

**Code Files:**
- [ ] `src/application/oauth_auth_ati2.py` (120-180 LOC)
- [ ] `tests/unit/test_ati2_oauth_auth.py` (120+ LOC)

**Database Setup:**
- [ ] `src/domain/session_model.py` (session table schema)
- [ ] Migration: create sessions table

**PR When Done:**
- [ ] All 8 AC tests PASSING
- [ ] Rate limiting verified
- [ ] Code review checklist complete
- [ ] Ready to merge to feature/ATI-2-oauth-auth

---

## ⏱️ EXECUTION TIMELINE

```
00:00 - 01:00  → Subtask 5.1 (JWT + Password managers)
01:00 - 02:30  → Subtask 5.2 (Login endpoint)
02:30 - 03:30  → Subtask 5.3 (Refresh endpoint)
03:30 - 05:00  → Subtask 5.4 (Security + integration)

Total: ~5 hours
```

---

## 📞 BLOCKERS / QUESTIONS

If you get stuck:
- Q: "JWT token validation failing?"
  → Check secret key matches between create/verify
- Q: "Rate limiting not working?"
  → Verify redis connection or in-memory dict cleanup
- Q: "Multi-device tracking?"
  → Each login = new session_id, store device_fingerprint
- Q: "CORS errors with WebSocket?"
  → Use fastapi.middleware.cors.CORSMiddleware

**Escalate to Eng Sr if:** Blocker > 30 min

---

## ✅ NEXT STEP

**Type when complete:**
```
"PRIORITY 5 DONE: OAuth endpoints ready + 8/8 AC tests passing + rate limiting verified"
```

Then: Ready for PRIORITY 6 (RabbitMQ) integration

---

**Status:** 🟢 **ACTIVE**
**Owner:** Dev-Backend-1
**Next Review:** After Subtask 5.2 (2h 30m)
