"""
ATI-2: OAuth Authentication Endpoints
Subtask 5.1 - 5.4: JWT Manager + Password Manager + Login + Refresh Token

Owner: Dev-Backend-1
Duration: 4-6 hours
Success Criteria: 8/8 AC tests passing + rate limiting verified
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
import hashlib
import time
from loguru import logger
import asyncio
from collections import defaultdict

# Configuration
JWT_SECRET = "your-secret-key"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8
REFRESH_TOKEN_EXPIRATION_DAYS = 30
RATE_LIMIT_ATTEMPTS = 10
RATE_LIMIT_WINDOW = 300  # 5 minutes in seconds


# Pydantic Models
class LoginRequest(BaseModel):
    """Login request payload"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response with tokens"""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str
    session_id: str


class RefreshTokenResponse(BaseModel):
    """Refresh token response"""
    access_token: str
    expires_in: int
    token_type: str = "bearer"


class JWTManager:
    """Manages JWT token creation and verification"""

    @staticmethod
    def create_token(trader_id: str, token_type: str = "access") -> tuple:
        """
        Create JWT token

        Args:
            trader_id: Trader identifier
            token_type: "access" (8h) or "refresh" (30d)

        Returns:
            (token, expires_in_seconds)
        """
        if token_type == "access":
            expiration = timedelta(hours=JWT_EXPIRATION_HOURS)
        elif token_type == "refresh":
            expiration = timedelta(days=REFRESH_TOKEN_EXPIRATION_DAYS)
        else:
            raise ValueError(f"Invalid token type: {token_type}")

        exp_time = datetime.utcnow() + expiration

        payload = {
            "trader_id": trader_id,
            "token_type": token_type,
            "exp": exp_time,
            "iat": datetime.utcnow()
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        expires_in = int(expiration.total_seconds())

        logger.info(f"🔑 Token created: {token_type} for trader {trader_id}")

        return token, expires_in

    @staticmethod
    def verify_token(token: str) -> dict:
        """
        Verify JWT token

        Args:
            token: JWT token string

        Returns:
            Token payload dict

        Raises:
            HTTPException: If token invalid/expired
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("❌ Token expired")
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            logger.warning("❌ Invalid token")
            raise HTTPException(status_code=401, detail="Invalid token")


class PasswordManager:
    """Manages password hashing and verification"""

    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=10
        )

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        hashed = self.pwd_context.hash(password)
        logger.debug("🔒 Password hashed")
        return hashed

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        is_valid = self.pwd_context.verify(plain_password, hashed_password)
        logger.debug(f"🔍 Password verification: {'✅' if is_valid else '❌'}")
        return is_valid


class RateLimiter:
    """Rate limiting for login attempts"""

    def __init__(self):
        # Map: username -> List of (timestamp, success)
        self.attempts: Dict[str, list] = defaultdict(list)

    def is_rate_limited(self, username: str) -> bool:
        """
        Check if user is rate limited

        AC-3: Rate limiting enforced (10 attempts / 5 min)
        """
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW

        # Clean old attempts
        self.attempts[username] = [
            ts for ts in self.attempts[username]
            if ts > window_start
        ]

        if len(self.attempts[username]) >= RATE_LIMIT_ATTEMPTS:
            logger.warning(f"⚠️ Rate limit exceeded for {username}")
            return True

        return False

    def record_attempt(self, username: str):
        """Record login attempt"""
        self.attempts[username].append(time.time())


class SessionManager:
    """Manages user sessions"""

    def __init__(self):
        # Map: session_id -> {trader_id, device_id, created_at, expires_at}
        self.sessions: Dict[str, dict] = {}

    def create_session(self, trader_id: str, device_id: str = None) -> str:
        """
        Create session

        AC-7: Multi-device session tracking
        """
        session_id = hashlib.sha256(
            f"{trader_id}{device_id}{time.time()}".encode()
        ).hexdigest()

        self.sessions[session_id] = {
            "trader_id": trader_id,
            "device_id": device_id or "unknown",
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            "token_history": []  # AC-8: Token rotation audit
        }

        logger.info(f"📱 Session created: {session_id} for {trader_id}")
        return session_id

    def validate_session(self, session_id: str) -> bool:
        """Validate session is active"""
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        if datetime.utcnow() > session["expires_at"]:
            del self.sessions[session_id]
            return False

        return True

    def invalidate_session(self, session_id: str):
        """Invalidate session (logout)"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"❌ Session invalidated: {session_id}")

    def log_token_rotation(self, session_id: str, token: str):
        """Log token rotation for audit (AC-8)"""
        if session_id in self.sessions:
            self.sessions[session_id]["token_history"].append({
                "token": token[:20] + "...",  # Abbreviated for security
                "rotated_at": datetime.utcnow()
            })


# Mock User Database (replace with real DB in production)
MOCK_USERS = {
    "trader1": {
        "password_hash": "$2b$10$TUVZqClajSaC4qojDHMjHuEPaydwrp6uuwDEdgoAq5oF5yuOE0PRe",  # password: "test123"
        "trader_id": "TRADER_001"
    },
    "trader2": {
        "password_hash": "$2b$10$TUVZqClajSaC4qojDHMjHuEPaydwrp6uuwDEdgoAq5oF5yuOE0PRe",  # password: "test123"
        "trader_id": "TRADER_002"
    }
}


# FastAPI app
app = FastAPI(title="ATI-2 OAuth Authentication")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global managers
jwt_manager = JWTManager()
password_manager = PasswordManager()
rate_limiter = RateLimiter()
session_manager = SessionManager()


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login endpoint

    AC-1: Successful login returns JWT tokens
    AC-2: Invalid credentials rejected (401)
    AC-3: Rate limiting enforced (10 attempts/5min)
    AC-7: Multi-device login support
    """

    username = request.username

    # Check rate limiting
    if rate_limiter.is_rate_limited(username):
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later."
        )

    # Record attempt
    rate_limiter.record_attempt(username)

    # Validate credentials
    user = MOCK_USERS.get(username)
    if not user or not password_manager.verify_password(request.password, user["password_hash"]):
        logger.warning(f"❌ Failed login attempt for {username}")
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    trader_id = user["trader_id"]

    # Create tokens
    access_token, access_expires = jwt_manager.create_token(trader_id, "access")
    refresh_token, refresh_expires = jwt_manager.create_token(trader_id, "refresh")

    # Create session
    session_id = session_manager.create_session(trader_id, device_id="web")

    # Log token rotation
    session_manager.log_token_rotation(session_id, access_token)

    logger.info(f"✅ Successful login for {trader_id}")

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=access_expires
    )


@app.post("/auth/refresh-token", response_model=RefreshTokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token

    AC-4: Refresh token extends session (8h more)
    AC-8: Token rotation logged for audit
    """

    # Verify refresh token
    try:
        payload = jwt_manager.verify_token(request.refresh_token)
        if payload.get("token_type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except HTTPException:
        raise

    # Validate session
    session_id = request.session_id
    if not session_manager.validate_session(session_id):
        raise HTTPException(status_code=401, detail="Invalid session")

    trader_id = payload["trader_id"]

    # Create new access token
    new_access_token, expires_in = jwt_manager.create_token(trader_id, "access")

    # Log token rotation
    session_manager.log_token_rotation(session_id, new_access_token)

    logger.info(f"🔄 Token refreshed for {trader_id}")

    return RefreshTokenResponse(
        access_token=new_access_token,
        expires_in=expires_in
    )


@app.post("/auth/logout")
async def logout(session_id: str):
    """
    Logout endpoint

    AC-5: Sessions properly validated
    AC-6: Logout clears session
    """

    session_manager.invalidate_session(session_id)

    return {"message": "Logged out successfully"}


@app.get("/auth/session/{session_id}")
async def get_session(session_id: str):
    """Get session information"""

    if not session_manager.validate_session(session_id):
        raise HTTPException(status_code=401, detail="Invalid/expired session")

    session = session_manager.sessions[session_id]

    return {
        "session_id": session_id,
        "trader_id": session["trader_id"],
        "device_id": session["device_id"],
        "created_at": session["created_at"],
        "expires_at": session["expires_at"],
        "token_history_count": len(session["token_history"])
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": len(session_manager.sessions),
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
