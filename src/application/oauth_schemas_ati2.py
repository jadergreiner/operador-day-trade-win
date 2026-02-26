"""
OAuth/JWT Schemas para FastAPI
Definição de modelos Pydantic para requisições e respostas de autenticação
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    """Schema para requisição de login"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)

    class Config:
        json_schema_extra = {
            "example": {
                "username": "trader01",
                "password": "SecurePass123!"
            }
        }


class TokenResponse(BaseModel):
    """Schema para resposta de tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class RefreshTokenRequest(BaseModel):
    """Schema para renovar token"""
    refresh_token: str = Field(..., min_length=10)


class TokenPayload(BaseModel):
    """JWT token payload interno"""
    sub: str  # username
    user_id: str
    role: str
    exp: datetime
    iat: datetime
    type: str  # 'access' ou 'refresh'


class LogoutResponse(BaseModel):
    """Schema para resposta de logout"""
    message: str
    timestamp: datetime


class UserInfo(BaseModel):
    """Schema para informações do usuário autenticado"""
    username: str
    user_id: str
    role: str
    issued_at: datetime
    expires_at: datetime
