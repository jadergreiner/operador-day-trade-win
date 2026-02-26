#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SPRINT 2 - ENG-003: MT5 REST API IMPLEMENTATION
===============================================

Especificação técnica completa para implementação da API REST do MT5
Integração com sistema de trading automatizado

Lead: Eng Sr (Senior Engineering)
Squad: Backend (3 developers)
Duration: 6 dias (26/02 - 03/03)
Priority: P0 (Bloqueador)
"""

SPEC = """
# ENG-003: MT5 REST API Implementation

**Objetivo:** Implementar API REST de alta performance para comunicação com MT5
**Owner:** Eng Sr (Backend Lead)
**Team:** 3 Backend Developers + QA Lead
**Sprint:** Sprint 2 (26/02 - 03/03)
**Duration:** 6 dias (48 horas desenvolvimento)
**Deadline:** 03/03 17:00 UTC (ready for GATE 1)

---

## 1. ARCHITECTURE OVERVIEW

### Tech Stack
- **Framework:** FastAPI (async, high-performance)
- **Protocol:** REST API (HTTP/1.1) + WebSocket (real-time)
- **Auth:** OAuth 2.0 (via MT5 token)
- **Database:** SQL (PostgreSQL for audit trail)
- **Queue:** RabbitMQ (async order processing)
- **Cache:** Redis (position cache, rate limiting)
- **Monitoring:** Prometheus + Grafana

### Components
```
┌──────────────────────────────────────────────────────────┐
│                    MT5 REST API                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  [FastAPI Server]                                       │
│  ├─ Authentication Service (OAuth 2.0)                │
│  ├─ Order Management (async queue)                    │
│  ├─ Position Tracking (WebSocket)                     │
│  ├─ Account Monitor (polling)                         │
│  ├─ Error Handler (retry logic)                       │
│  └─ Audit Logger (all transactions)                   │
│                                                          │
│  [External Integrations]                               │
│  ├─ MT5 API Client (via REST/WebSocket)              │
│  ├─ Risk Validator (from Sprint 1)                    │
│  ├─ ML Model (threshold=0.30)                         │
│  └─ Monitoring Stack (Prometheus/Grafana)              │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 2. API ENDPOINTS SPECIFICATION

### 2.1 Authentication

#### POST /api/v1/auth/login
**Purpose:** Authenticate and get JWT token
**Request:**
```json
{
  "mt5_login": "string (required)",
  "mt5_password": "string (required)",
  "mt5_server": "string (default: 'demo.mt5')"
}
```
**Response (200):**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "..."
}
```
**Response (401):** Invalid credentials
**Response (503):** MT5 server unavailable

**AC-1:** Authentication successfully validates credentials with MT5

---

#### POST /api/v1/auth/refresh
**Purpose:** Refresh JWT token
**Headers:** Authorization: Bearer {token}
**Response (200):** New token
**Response (401):** Invalid token
**AC-2:** Token refresh works without re-authentication

---

### 2.2 Orders Management

#### POST /api/v1/orders/send
**Purpose:** Send new trading order
**Headers:** Authorization: Bearer {token}
**Request:**
```json
{
  "symbol": "WINFUT",
  "order_type": "BUY|SELL",
  "volume": 1,
  "price": 123456.0,
  "sl": "123400.0",
  "tp": "123500.0",
  "comment": "ML signal threshold=0.30"
}
```
**Response (200):**
```json
{
  "ticket": "1234567",
  "status": "PENDING|ACCEPTED|REJECTED",
  "timestamp": "2026-02-26T10:30:45Z",
  "message": "Order submitted"
}
```
**AC-3:** Orders sent through async queue (no blocking)
**AC-4:** Retry logic (3x exponential backoff) implemented

---

#### GET /api/v1/orders/{ticket}
**Purpose:** Get order status
**Response (200):**
```json
{
  "ticket": "1234567",
  "status": "PENDING|FILLED|CLOSED",
  "fill_price": 123456.5,
  "volume_filled": 1,
  "timestamp": "2026-02-26T10:30:45Z"
}
```
**AC-5:** Order status tracked in real-time

---

#### GET /api/v1/orders/history
**Purpose:** Get order history (paginated)
**Query:** ?limit=50&offset=0&symbol=WINFUT
**Response (200):**
```json
{
  "total": 1024,
  "page_size": 50,
  "orders": [
    { "ticket": "1234567", "status": "CLOSED", ... }
  ]
}
```

---

### 2.3 Positions Management

#### GET /api/v1/positions
**Purpose:** Get all open positions (real-time via WebSocket)
**Response (200):**
```json
{
  "positions": [
    {
      "ticket": "1234567",
      "symbol": "WINFUT",
      "type": "BUY|SELL",
      "volume": 1,
      "entry_price": 123456.0,
      "current_price": 123470.5,
      "pnl": 145.5,
      "pnl_pct": 0.118,
      "timestamp": "2026-02-26T10:35:00Z"
    }
  ],
  "total_pnl": 145.5,
  "total_pnl_pct": 0.118
}
```
**AC-6:** Positions updated in real-time (< 100ms latency)

---

#### GET /api/v1/positions/{ticket}
**Purpose:** Get specific position details
**Response (200):** Full position data with P&L

---

#### PATCH /api/v1/positions/{ticket}
**Purpose:** Update position (TP/SL)
**Request:**
```json
{
  "sl": "123400.0",
  "tp": "123600.0"
}
```
**Response (200):** Updated position

---

#### DELETE /api/v1/positions/{ticket}
**Purpose:** Close position
**Request:**
```json
{
  "volume": 1,
  "comment": "Risk management - circuit breaker"
}
```
**Response (200):** Closed position data

---

### 2.4 Account Management

#### GET /api/v1/account
**Purpose:** Get account summary
**Response (200):**
```json
{
  "account_id": "123456789",
  "balance": 100000.0,
  "equity": 100145.5,
  "margin_used": 5000.0,
  "margin_free": 95000.0,
  "margin_level": 2001.0,
  "currency": "BRL",
  "leverage": 1.0
}
```
**AC-7:** Account balance updated every 30 seconds

---

### 2.5 Health & Status

#### GET /api/v1/health
**Purpose:** Healthcheck endpoint
**Response (200):**
```json
{
  "status": "healthy|degraded|unhealthy",
  "mt5_connection": "connected|disconnected",
  "api_uptime": "99.95%",
  "latency_p95": "150ms",
  "queue_depth": 12,
  "timestamp": "2026-02-26T10:40:00Z"
}
```
**AC-8:** Healthcheck includes all dependencies

---

## 3. AUTHENTICATION & SECURITY

### OAuth 2.0 Flow
```
1. Client sends (mt5_login, password)
2. API validates against MT5
3. JWT generated (HS256, 1-hour expiry)
4. Client includes token in Authorization header
5. API verifies signature before processing
6. Token can be refreshed without password
```

### Security Measures
- ✅ HTTPS only (TLS 1.3)
- ✅ Rate limiting: 100 req/min per IP
- ✅ Request signing (X-Signature header)
- ✅ Audit logging: All requests logged
- ✅ CORS: Whitelist specific origins
- ✅ Secrets: Stored in environment variables

---

## 4. ASYNC QUEUE & RETRY LOGIC

### Order Processing Flow
```
┌──────────────────────────────────────────────────┐
│ Client sends order                               │
└────────────────┬─────────────────────────────────┘
                 │
              Validate
                 │
          ┌──────▼───────────────┐
          │ Add to Queue (RabbitMQ)
          └──────┬───────────────┘
                 │
    ┌────────────▼────────────┐
    │ Worker processes order   │
    │ (async, 3x concurrency) │
    └────────────┬────────────┘
                 │
         ┌───────▼────────┐
         │ Send to MT5     │
         └───────┬────────┘
                 │
      ┌──────────▼──────────┐
      │ Success? ───→ Return ticket
      │    │
      │    └─→ Fail → Retry (exp. backoff)
      │              Attempt 1: 1s
      │              Attempt 2: 2s
      │              Attempt 3: 4s
      │              Final fail → DLQ
      └──────────────────────┘
```

**AC-9:** Retry logic (3x with exponential backoff) handles network issues

---

## 5. WEBSOCKET REAL-TIME UPDATES

### WebSocket Connection
**Endpoint:** wss://api.operador.ai/ws/positions
**Auth:** Bearer token in header

### Message Types
```json
{
  "type": "position_update|order_update|account_update",
  "data": { ... },
  "timestamp": "2026-02-26T10:40:00Z"
}
```

### Subscribe to Streams
```json
{
  "action": "subscribe",
  "streams": ["positions", "orders", "account"]
}
```

**AC-10:** WebSocket maintains < 100ms latency for position updates

---

## 6. ERROR HANDLING

### Error Response Format
```json
{
  "error": {
    "code": "ERR_001",
    "message": "MT5 connection timeout",
    "details": "Could not reach MT5 server",
    "retry_after": 30
  }
}
```

### Common Error Codes
- `ERR_001`: MT5 connection error
- `ERR_002`: Authentication failed
- `ERR_003`: Order validation failed
- `ERR_004`: Insufficient margin
- `ERR_005`: Order timeout
- `ERR_006`: Rate limit exceeded

---

## 7. PERFORMANCE REQUIREMENTS

### Latency SLA
- **Order sending:** P95 < 200ms (excluding MT5 network)
- **Position tracking:** P95 < 100ms (WebSocket)
- **Account query:** P95 < 100ms
- **Healthcheck:** P95 < 50ms

### Throughput
- **Orders:** > 100 orders/second (queue)
- **Positions:** > 1000 updates/second (WebSocket)
- **Queries:** > 50 concurrent connections

### Reliability
- **Uptime:** 99.9% (production)
- **Error rate:** < 0.1%
- **Data loss:** Zero (audit trail)

---

## 8. TESTING PLAN

### Unit Tests (100% coverage)
- [ ] Authentication logic
- [ ] Order validation
- [ ] Error handling
- [ ] Queue processing
- [ ] WebSocket messages

### Integration Tests (8 test cases)
- [ ] Login → Send order → Track position
- [ ] Order retry logic (network failure)
- [ ] WebSocket position updates
- [ ] Rate limiting
- [ ] MT5 connection failure
- [ ] Token refresh
- [ ] Concurrent orders
- [ ] Account balance updates

### E2E Tests (5 test cases)
- [ ] Full trading flow (login → order → close)
- [ ] Risk validation (circuit breaker -5%)
- [ ] Multiple concurrent positions
- [ ] Order history pagination
- [ ] Authentication token expiry

### Performance Tests
- [ ] Load test: 100 concurrent orders/sec
- [ ] Latency profiling (P50, P95, P99)
- [ ] Memory usage under load
- [ ] Database connection pooling

---

## 9. DELIVERABLES

### Code (est. 800 LOC)
- [ ] `api/main.py` - FastAPI server (200 LOC)
- [ ] `api/auth.py` - OAuth 2.0 implementation (150 LOC)
- [ ] `api/orders.py` - Order endpoints (200 LOC)
- [ ] `api/positions.py` - Position endpoints (150 LOC)
- [ ] `api/websocket.py` - WebSocket handler (100 LOC)
- [ ] `queue/worker.py` - Queue processor (100 LOC)

### Tests (est. 600 LOC)
- [ ] `tests/test_auth.py` (100 LOC)
- [ ] `tests/test_orders.py` (150 LOC)
- [ ] `tests/test_positions.py` (150 LOC)
- [ ] `tests/test_integration.py` (200 LOC)

### Documentation
- [ ] API specification (OpenAPI/Swagger)
- [ ] Deployment guide
- [ ] Troubleshooting guide
- [ ] Performance baseline

---

## 10. ACCEPTANCE CRITERIA (8 ACs)

| AC | Criterion | Verification |
|----|-----------|--------------|
| AC-1 | Authentication validates credentials | Test: POST /auth/login success/fail |
| AC-2 | Token refresh works | Test: POST /auth/refresh with expired token |
| AC-3 | Orders sent async (no blocking) | Performance: P95 < 200ms |
| AC-4 | Retry logic (3x exponential backoff) | Test: Simulate MT5 failures |
| AC-5 | Order status tracked real-time | Test: GET /orders/{ticket} after send |
| AC-6 | Positions updated < 100ms (WebSocket) | Performance: WebSocket latency |
| AC-7 | Account balance updated every 30s | Test: Monitor balance polling |
| AC-8 | Healthcheck includes all dependencies | Test: GET /health response complete |

---

## 11. SUCCESS METRICS

### Code Quality
- [x] mypy --strict: 0 errors
- [x] pylint: > 9.0/10
- [x] coverage: > 90%
- [x] type hints: 100%

### Performance
- [x] API latency P95: < 200ms
- [x] Throughput: > 100 orders/sec
- [x] Uptime: 99.9%
- [x] Error rate: < 0.1%

### Testing
- [x] Unit tests: 100% pass
- [x] Integration: 8/8 pass
- [x] E2E: 5/5 pass
- [x] Load test: sustained 100 req/sec

---

## 12. RISK MITIGATION

| Risk | Impact | Mitigation |
|------|--------|-----------|
| MT5 connection unstable | P0 | Retry logic + healthcheck + circuit breaker |
| Order execution delay | P1 | Async queue + monitoring |
| Token expiry during trading | P1 | Auto refresh + long-lived cache |
| Database bottleneck | P1 | Connection pooling + read replicas |
| DDoS attack | P1 | Rate limiting + WAF |

---

## 13. TIMELINE (6 dias)

| Day | Task | Lead | Status |
|-----|------|------|--------|
| 26/02 | Design + skeleton | Eng Sr | ⏳ Kickoff |
| 27/02 | Auth + Orders | Dev 1 | - |
| 28/02 | Positions + WebSocket | Dev 2 | - |
| 01/03 | Queue + Retry logic | Dev 3 | - |
| 02/03 | Integration testing | QA Lead | - |
| 03/03 | Final testing + deploy | All | 🎯 GATE 1 |

---

## 14. DEFINITION OF DONE

- [x] Code reviewed (2+ reviewers)
- [x] All tests passing (unit + integration + E2E)
- [x] Performance validated (latency + throughput)
- [x] Documentation complete (API spec + guides)
- [x] Deployed to staging
- [x] Monitoring active (Prometheus + Grafana)
- [x] Trader sign-off obtained
- [x] Ready for GATE 1 checkpoint

---

**Owner:** Eng Sr (Backend Lead)
**Due:** 03/03 17:00 UTC (GATE 1)
**Status:** Not started (ready for kickoff 26/02)
"""

if __name__ == '__main__':
    print(SPEC)
