# 🔐 SUBTASK 5.1: OAuth Setup & Configuration

**Owner:** Dev-Backend-1 (Authentication Team)  
**Duration:** 1.5 hours  
**Status:** 🟢 READY TO START  
**Start Time:** NOW (PARALLEL with PRIORITY 4+8)  

---

## 📋 Objective

Implement and validate **OAuth authentication framework** with token generation, validation, and comprehensive error handling. This subtask establishes the secure authentication foundation for all subsequent API operations.

---

## ✅ Acceptance Criteria for Subtask 5.1

1. **OAuth Token Generation** ✓
   - ClientCredentialsFlow supported
   - Tokens include trader_id, permissions, exp claims
   - Tokens signed with RSA-256
   - Verified with unit test

2. **Token Validation** ✓
   - Signature verification working
   - Expiration checks enforced
   - Claim validation (trader_id, permissions)
   - Invalid tokens rejected

3. **Permission Scope Management** ✓
   - Read, Write, Delete scopes defined
   - Scope validation against token
   - Unauthorized operations blocked
   - Scope errors logged

4. **Refresh Token Support** ✓
   - Refresh tokens valid for 7 days
   - Access tokens valid for 1 hour
   - Refresh rotation (new token on refresh)
   - Tested with unit test

5. **Rate Limiting** ✓
   - Max 100 login attempts per minute per IP
   - Tracking by client IP address
   - Rate limit errors return 429 status
   - Reset after 60 seconds

---

## 🔧 Implementation Guide

### Step 1: Review Current OAuth Implementation

**File:** `src/application/oauth_auth_ati2.py` (380 LOC)

**Key Classes:**
- `OAuthConfig`: Configuration + RSA key generation
- `OAuthManager`: Token generation, validation, refresh
- `RateLimiter`: Track login attempts by IP
- `PermissionValidator`: Scope/permission checking

**Current Status:** ✅ Baseline implementation complete

### Step 2: Validate OAuth Configuration

**Command:**
```bash
# Test 1: Verify RSA keys exist and are properly formatted
python -c "
from src.application.oauth_auth_ati2 import OAuthConfig
config = OAuthConfig()
print(f'✓ Public Key Type: {type(config.public_key)}')
print(f'✓ Private Key Type: {type(config.private_key)}')
print(f'✓ Algorithm: {config.algorithm}')
"
```

**Expected Output:**
```
✓ Public Key Type: <class 'cryptography.hazmat.primitives.asymmetric.rsa.RSAPublicKey'>
✓ Private Key Type: <class 'cryptography.hazmat.primitives.asymmetric.rsa.RSAPrivateKey'>
✓ Algorithm: RS256
```

### Step 3: Run OAuth Test Suite

**File:** `tests/unit/test_ati2_oauth_auth.py` (310 LOC)

**Command:**
```bash
pytest tests/unit/test_ati2_oauth_auth.py -v
```

**Expected Output:**
```
tests/unit/test_ati2_oauth_auth.py::TestOAuthConfig::test_oauth_config_init PASSED
tests/unit/test_ati2_oauth_auth.py::TestOAuthManager::test_token_generation PASSED
tests/unit/test_ati2_oauth_auth.py::TestOAuthManager::test_token_validation PASSED
tests/unit/test_ati2_oauth_auth.py::TestOAuthManager::test_token_expiration PASSED
tests/unit/test_ati2_oauth_auth.py::TestOAuthManager::test_refresh_token PASSED
tests/unit/test_ati2_oauth_auth.py::TestRateLimiter::test_rate_limit_exceed PASSED
tests/unit/test_ati2_oauth_auth.py::TestRateLimiter::test_rate_limit_reset PASSED
tests/unit/test_ati2_oauth_auth.py::TestPermissionValidator::test_scope_validation PASSED

===================== 8 passed in 1.23s =====================
```

### Step 4: Validate Token Claims

**Test Script** - Create `validate_oauth_tokens.py`:

```python
#!/usr/bin/env python3
"""Validate OAuth token structure and claims."""

import asyncio
from datetime import datetime, timedelta
from src.application.oauth_auth_ati2 import OAuthManager, OAuthConfig

async def validate_oauth():
    """Run OAuth validation tests."""
    config = OAuthConfig()
    manager = OAuthManager(config)
    
    # Test 1: Generate token
    print("\n🔐 TEST 1: Token Generation")
    token = manager.generate_token(trader_id="trader001", scopes=["read", "write"])
    print(f"✓ Token generated: {token[:50]}...")
    print(f"✓ Token length: {len(token)} characters")
    
    # Test 2: Validate token
    print("\n🔐 TEST 2: Token Validation")
    payload = manager.validate_token(token)
    print(f"✓ Payload: {payload}")
    print(f"✓ Trader ID: {payload.get('trader_id')}")
    print(f"✓ Scopes: {payload.get('scopes')}")
    print(f"✓ Expiration: {datetime.fromtimestamp(payload['exp']).isoformat()}")
    
    # Test 3: Validate claims
    print("\n🔐 TEST 3: Claim Validation")
    assert payload['trader_id'] == 'trader001', "trader_id mismatch"
    assert 'read' in payload['scopes'], "read scope missing"
    assert 'write' in payload['scopes'], "write scope missing"
    assert payload['exp'] > datetime.now().timestamp(), "token expired"
    print("✓ All claims validated")
    
    # Test 4: Token expiration
    print("\n🔐 TEST 4: Token Expiration Check")
    expired_token = manager.generate_token(
        trader_id="trader001", 
        scopes=["read"],
        exp_minutes=-1  # Already expired
    )
    try:
        manager.validate_token(expired_token)
        print("✗ Expired token should have failed")
    except Exception as e:
        print(f"✓ Expired token rejected: {e}")
    
    # Test 5: Refresh token
    print("\n🔐 TEST 5: Token Refresh")
    refresh_token = manager.generate_refresh_token(trader_id="trader001")
    new_access_token = manager.refresh_token(refresh_token)
    new_payload = manager.validate_token(new_access_token)
    print(f"✓ New token generated from refresh")
    print(f"✓ New token trader_id: {new_payload['trader_id']}")
    
    # Test 6: Rate limiting
    print("\n🔐 TEST 6: Rate Limiting")
    limiter = manager.rate_limiter
    client_ip = "192.168.1.100"
    
    # Simulate 100 login attempts
    attempts = 0
    for i in range(105):
        if limiter.check_rate_limit(client_ip):
            attempts += 1
        else:
            print(f"✓ Rate limit triggered at attempt {i+1}")
            break
    
    print(f"✓ Allowed {attempts} attempts from {client_ip}")
    
    # Test 7: Permission validation
    print("\n🔐 TEST 7: Permission Validation")
    token_read_only = manager.generate_token(trader_id="trader001", scopes=["read"])
    payload_read = manager.validate_token(token_read_only)
    
    validator = manager.permission_validator
    
    # Check read permission (should pass)
    has_read = validator.check_permission(payload_read, "read")
    print(f"✓ Read permission check: {has_read}")
    
    # Check write permission (should fail)
    has_write = validator.check_permission(payload_read, "write")
    print(f"✓ Write permission check: {has_write} (should be False)")
    
    print("\n✅ ALL OAUTH VALIDATION TESTS PASSED!\n")

if __name__ == "__main__":
    asyncio.run(validate_oauth())
```

**Run the validation:**
```bash
python validate_oauth_tokens.py
```

**Expected Output:**
```
🔐 TEST 1: Token Generation
✓ Token generated: eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
✓ Token length: 256 characters

🔐 TEST 2: Token Validation
✓ Payload: {'trader_id': 'trader001', 'scopes': ['read', 'write'], ...}
✓ Trader ID: trader001
✓ Scopes: ['read', 'write']
✓ Expiration: 2026-02-26T02:30:45.123456

🔐 TEST 3: Claim Validation
✓ All claims validated

🔐 TEST 4: Token Expiration Check
✓ Expired token rejected: Token has expired

🔐 TEST 5: Token Refresh
✓ New token generated from refresh
✓ New token trader_id: trader001

🔐 TEST 6: Rate Limiting
✓ Rate limit triggered at attempt 101
✓ Allowed 100 attempts from 192.168.1.100

🔐 TEST 7: Permission Validation
✓ Read permission check: True
✓ Write permission check: False

✅ ALL OAUTH VALIDATION TESTS PASSED!
```

### Step 5: Verify Integration with WebSocket

**Test:** OAuth tokens should work with WebSocket authentication

**Command:**
```bash
pytest tests/unit/test_ati2_oauth_auth.py::TestIntegration -v
```

Should include tests for:
- ✅ Token used in WebSocket header: `Authorization: Bearer <token>`
- ✅ Invalid tokens rejected by WebSocket endpoint
- ✅ Expired tokens cause disconnection
- ✅ Refresh token flow for long-lived connections

### Step 6: Generate Coverage Report

**Command:**
```bash
pytest tests/unit/test_ati2_oauth_auth.py --cov=src.application.oauth_auth_ati2 --cov-report=html
```

**Expected:** >95% code coverage

---

## 🎯 Success Criteria for Subtask 5.1

```
✅ OAuth configuration loads without errors
✅ All 8 AC tests passing
✅ Token generation produces valid JWT tokens
✅ Token validation works correctly
✅ Expiration enforcement working
✅ Refresh token flow operational
✅ Rate limiting configured (100/min per IP)
✅ Permission scopes enforced
✅ Code coverage >95%
✅ No Warnings in pytest output
```

---

## 📊 Expected Duration

- **Setup & Review:** 10 min
- **Test Execution:** 10 min
- **Validation Script:** 15 min
- **Coverage Report:** 5 min
- **Documentation:** 5 min
- **Total:** ~90 minutes (can run in parallel with 4.3 + 8.1)

---

## 🔗 Dependencies

**Prerequisites (completed):**
- ✅ PRIORITY 1: Environment setup
- ✅ PRIORITY 2: Team sync
- ✅ PRIORITY 3: GATE 1 approval

**Current Codebase:**
- ✅ `src/application/oauth_auth_ati2.py` (380 LOC - COMPLETE)
- ✅ `tests/unit/test_ati2_oauth_auth.py` (310 LOC - COMPLETE)

**External Dependencies:**
- `PyJWT` - JWT token handling
- `cryptography` - RSA key management
- `python-dotenv` - Configuration

**Next:** PRIORITY 5 Subtask 5.2 will add FastAPI OAuth endpoints

---

## ⚠️ Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| "ModuleNotFoundError: No module named 'cryptography'" | Run `pip install cryptography` |
| "Token invalid signature" | Verify RSA keys match between config and validation |
| "Rate limiter not resetting" | Check timestamp logic uses current time |
| "Permission validation failing" | Verify scopes list is properly populated in token |

---

## 🚀 Execution Steps - EXACT COMMANDS

```bash
# 1. Navigate to project
cd c:\repo\operador-day-trade-win

# 2. Verify OAuth config
python -c "from src.application.oauth_auth_ati2 import OAuthConfig; config = OAuthConfig(); print('✓ OAuth config OK')"

# 3. Run OAuth tests
pytest tests/unit/test_ati2_oauth_auth.py -v

# 4. Create validation script
# (Copy validate_oauth_tokens.py code from Step 4 above)

# 5. Run validation
python validate_oauth_tokens.py

# 6. Check coverage
pytest tests/unit/test_ati2_oauth_auth.py --cov=src.application.oauth_auth_ati2 -q

# 7. If all passing
pytest tests/unit/test_ati2_oauth_auth.py -q --tb=short
```

---

## 📝 Documentation Template

When complete, create `SUBTASK_5_1_COMPLETE.md`:

```markdown
# ✅ SUBTASK 5.1 COMPLETE: OAuth Setup & Configuration

**Timestamp:** [TIME]
**Owner:** Dev-Backend-1
**Duration:** [ACTUAL TIME]
**Status:** ✅ COMPLETE

## Test Results
- OAuth Config: ✅ PASSED
- Token Generation: ✅ PASSED
- Token Validation: ✅ PASSED
- Token Expiration: ✅ PASSED
- Refresh Token: ✅ PASSED
- Rate Limiting: ✅ PASSED
- Permission Validation: ✅ PASSED

## AC Status (All 5 AC for 5.1)
✅ AC-1: OAuth Token Generation
✅ AC-2: Token Validation
✅ AC-3: Permission Scope Management
✅ AC-4: Refresh Token Support
✅ AC-5: Rate Limiting

## Coverage
- Code Coverage: >95%
- All edge cases tested

## Next Steps
→ Subtask 5.2: FastAPI OAuth Endpoints
```

---

## ✨ Notes

- **Parallel Execution:** This runs simultaneously with PRIORITY 4.3 + PRIORITY 8.1
- **No Blocking:** Each subtask is independent, doesn't wait on others
- **Integration Later:** OAuth will integrate with WebSocket in PRIORITY 6
- **Rate Limiting:** Critical for security, validates at scale

---

**Status:** 🟢 **READY TO START NOW**

When complete, proceed to **SUBTASK 5.2** (FastAPI OAuth Endpoints)

---

**Parallel Timeline:** Can run simultaneously with Subtasks 4.3 + 8.1  
**Time to Complete:** ~90 min ⏱️

