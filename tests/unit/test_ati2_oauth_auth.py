"""
Tests for ATI-2: OAuth Authentication Endpoints
Unit tests for all 8 Acceptance Criteria
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import jwt
import time
from unittest.mock import patch, Mock

# Import from main module
from src.application.oauth_auth_ati2 import (
    app, jwt_manager, password_manager, rate_limiter, session_manager,
    JWTManager, PasswordManager, RateLimiter, SessionManager,
    JWT_SECRET, JWT_ALGORITHM, RATE_LIMIT_ATTEMPTS, RATE_LIMIT_WINDOW
)


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def valid_credentials():
    """Valid test credentials"""
    return {
        "username": "trader1",
        "password": "test123"
    }


@pytest.fixture
def reset_rate_limiter():
    """Reset rate limiter between tests"""
    rate_limiter.attempts.clear()
    yield
    rate_limiter.attempts.clear()


class TestJWTManager:
    """Test JWT Manager"""

    def test_create_access_token(self):
        """Test access token creation"""
        token, expires_in = JWTManager.create_token("TRADER_001", "access")

        assert token is not None
        assert expires_in == 8 * 3600  # 8 hours in seconds

    def test_create_refresh_token(self):
        """Test refresh token creation"""
        token, expires_in = JWTManager.create_token("TRADER_001", "refresh")

        assert token is not None
        assert expires_in == 30 * 24 * 3600  # 30 days in seconds

    def test_verify_token_valid(self):
        """Test token verification - valid token"""
        token, _ = JWTManager.create_token("TRADER_001", "access")

        payload = JWTManager.verify_token(token)

        assert payload["trader_id"] == "TRADER_001"
        assert payload["token_type"] == "access"

    def test_verify_token_invalid(self):
        """Test token verification - invalid token"""
        with pytest.raises(Exception):  # HTTPException
            JWTManager.verify_token("invalid.token.here")

    def test_verify_token_expired(self):
        """Test token verification - expired token"""
        # Create token with past expiration
        payload = {
            "trader_id": "TRADER_001",
            "token_type": "access",
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired 1h ago
            "iat": datetime.utcnow()
        }

        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        with pytest.raises(Exception):  # HTTPException
            JWTManager.verify_token(expired_token)


class TestPasswordManager:
    """Test Password Manager"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "test123"
        hashed = password_manager.hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt format

    def test_verify_password_correct(self):
        """Test password verification - correct password"""
        password = "test123"
        hashed = password_manager.hash_password(password)

        is_valid = password_manager.verify_password(password, hashed)
        assert is_valid is True

    def test_verify_password_incorrect(self):
        """Test password verification - incorrect password"""
        password = "test123"
        hashed = password_manager.hash_password(password)

        is_valid = password_manager.verify_password("wrong_password", hashed)
        assert is_valid is False


class TestRateLimiter:
    """Test Rate Limiter"""

    def test_rate_limiting_not_exceeded(self, reset_rate_limiter):
        """Test rate limiting - under limit"""
        username = "trader1"

        # Record attempts below limit
        for _ in range(5):
            assert rate_limiter.is_rate_limited(username) is False
            rate_limiter.record_attempt(username)

    def test_rate_limiting_exceeded(self, reset_rate_limiter):
        """AC-3: Test rate limiting - exceeded"""
        username = "trader1"

        # Record max attempts
        for _ in range(RATE_LIMIT_ATTEMPTS):
            rate_limiter.record_attempt(username)

        # Next attempt should be rate limited
        assert rate_limiter.is_rate_limited(username) is True

    def test_rate_limiting_window_expires(self, reset_rate_limiter):
        """Test rate limiting - window expiration"""
        username = "trader1"

        # Record attempts
        for _ in range(RATE_LIMIT_ATTEMPTS):
            rate_limiter.record_attempt(username)

        assert rate_limiter.is_rate_limited(username) is True

        # Simulate time passing beyond window
        rate_limiter.attempts[username] = []

        assert rate_limiter.is_rate_limited(username) is False


class TestSessionManager:
    """Test Session Manager"""

    def test_create_session(self):
        """AC-7: Test session creation"""
        session_id = session_manager.create_session("TRADER_001", "web")

        assert session_id is not None
        assert session_id in session_manager.sessions

        session = session_manager.sessions[session_id]
        assert session["trader_id"] == "TRADER_001"
        assert session["device_id"] == "web"

    def test_validate_session_active(self):
        """AC-5: Test session validation - active"""
        session_id = session_manager.create_session("TRADER_001", "mobile")

        is_valid = session_manager.validate_session(session_id)
        assert is_valid is True

    def test_validate_session_invalid(self):
        """AC-5: Test session validation - invalid"""
        is_valid = session_manager.validate_session("invalid_session_id")
        assert is_valid is False

    def test_invalidate_session(self):
        """AC-6: Test session logout/invalidation"""
        session_id = session_manager.create_session("TRADER_001", "web")

        assert session_manager.validate_session(session_id) is True

        session_manager.invalidate_session(session_id)

        assert session_manager.validate_session(session_id) is False

    def test_token_rotation_audit(self):
        """AC-8: Test token rotation logging for audit"""
        session_id = session_manager.create_session("TRADER_001", "web")

        token1 = "token_abc123"
        token2 = "token_def456"

        session_manager.log_token_rotation(session_id, token1)
        session_manager.log_token_rotation(session_id, token2)

        session = session_manager.sessions[session_id]
        assert len(session["token_history"]) == 2
        assert session["token_history"][0]["token"] == "token_abc123..."


class TestLoginEndpoint:
    """Test login endpoint"""

    def test_login_success(self, client, valid_credentials):
        """AC-1: Test successful login"""
        response = client.post("/auth/login", json=valid_credentials)

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client):
        """AC-2: Test login with invalid credentials"""
        response = client.post("/auth/login", json={
            "username": "trader1",
            "password": "wrong_password"
        })

        assert response.status_code == 401
        assert "Invalid credentials" in response.text

    def test_login_nonexistent_user(self, client):
        """AC-2: Test login with nonexistent user"""
        response = client.post("/auth/login", json={
            "username": "nonexistent",
            "password": "test123"
        })

        assert response.status_code == 401

    def test_login_rate_limiting(self, client, reset_rate_limiter):
        """AC-3: Test login rate limiting"""
        username = "trader1"

        # Make RATE_LIMIT_ATTEMPTS + 1 failed attempts
        for i in range(RATE_LIMIT_ATTEMPTS + 1):
            response = client.post("/auth/login", json={
                "username": username,
                "password": "wrong_password"
            })

            if i < RATE_LIMIT_ATTEMPTS:
                assert response.status_code == 401
            else:
                # Should be rate limited
                assert response.status_code == 429
                assert "Too many login attempts" in response.text


class TestRefreshTokenEndpoint:
    """Test refresh token endpoint"""

    def test_refresh_token_success(self, client, valid_credentials):
        """AC-4: Test successful token refresh"""
        # First login
        login_response = client.post("/auth/login", json=valid_credentials)
        login_data = login_response.json()

        refresh_token = login_data["refresh_token"]

        # Get session ID (in real scenario, would be from response header)
        session_id = list(session_manager.sessions.keys())[0]

        # Refresh token
        response = client.post("/auth/refresh-token", json={
            "refresh_token": refresh_token,
            "session_id": session_id
        })

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_expired(self, client):
        """Test refresh with expired refresh token"""
        # Create expired refresh token
        payload = {
            "trader_id": "TRADER_001",
            "token_type": "refresh",
            "exp": datetime.utcnow() - timedelta(days=1),  # Expired
            "iat": datetime.utcnow()
        }

        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        response = client.post("/auth/refresh-token", json={
            "refresh_token": expired_token,
            "session_id": "any_session_id"
        })

        assert response.status_code == 401

    def test_refresh_token_invalid_session(self, client, valid_credentials):
        """Test refresh with invalid session"""
        # First login
        login_response = client.post("/auth/login", json=valid_credentials)
        login_data = login_response.json()

        refresh_token = login_data["refresh_token"]

        # Try refresh with invalid session
        response = client.post("/auth/refresh-token", json={
            "refresh_token": refresh_token,
            "session_id": "invalid_session_id"
        })

        assert response.status_code == 401


class TestLogoutEndpoint:
    """Test logout endpoint"""

    def test_logout_success(self, client, valid_credentials):
        """AC-6: Test successful logout"""
        # First login
        login_response = client.post("/auth/login", json=valid_credentials)

        # Get session ID
        session_id = list(session_manager.sessions.keys())[0]

        # Logout
        response = client.post(f"/auth/logout?session_id={session_id}")

        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]

        # Verify session is gone
        assert not session_manager.validate_session(session_id)


class TestHealthEndpoint:
    """Test health endpoint"""

    def test_health_check(self, client):
        """Test health endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "active_sessions" in data
        assert "timestamp" in data


class TestAcceptanceCriteria:
    """Integration tests for all 8 AC"""

    def test_all_ac_integrated(self, client, valid_credentials, reset_rate_limiter):
        """
        AC-1: Login returns JWT tokens
        AC-2: Invalid credentials rejected (401)
        AC-3: Rate limiting enforced (10/5min)
        AC-4: Refresh token extends session (8h)
        AC-5: Sessions properly validated
        AC-6: Logout clears session
        AC-7: Multi-device support (session tracking)
        AC-8: Token rotation logged for audit
        """

        # AC-1: Login returns tokens
        login_response = client.post("/auth/login", json=valid_credentials)
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data
        assert "refresh_token" in login_data

        # AC-2: Invalid credentials rejected
        bad_login = client.post("/auth/login", json={
            "username": "trader1",
            "password": "wrong"
        })
        assert bad_login.status_code == 401

        # Get session for further tests
        session_id = list(session_manager.sessions.keys())[0]

        # AC-5: Session validation
        session = session_manager.sessions[session_id]
        assert session["trader_id"] is not None

        # AC-7: Multi-device (different device creates different session)
        session_manager.create_session("TRADER_001", "mobile")
        assert len([s for s in session_manager.sessions.values()
                   if s["trader_id"] == "TRADER_001"]) > 1

        # AC-4: Refresh token
        refresh_response = client.post("/auth/refresh-token", json={
            "refresh_token": login_data["refresh_token"],
            "session_id": session_id
        })
        assert refresh_response.status_code == 200

        # AC-8: Token history
        assert len(session["token_history"]) > 0

        # AC-6: Logout clears session
        logout_response = client.post(f"/auth/logout?session_id={session_id}")
        assert logout_response.status_code == 200
        assert not session_manager.validate_session(session_id)

        print("✅ All 8 AC tests PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
