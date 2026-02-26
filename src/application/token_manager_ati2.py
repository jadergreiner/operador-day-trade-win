"""
Token Manager para JWT e Refresh Tokens
Gerenciamento de criação, validação e invalidação de tokens JWT
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
import time


class TokenManager:
    """Gerenciar JWT tokens, refresh tokens e autenticação"""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7
    ):
        self.secret_key = secret_key or os.getenv("JWT_SECRET", "dev-secret-key-2026-change-in-prod")
        self.algorithm = algorithm
        self.access_token_expire = timedelta(minutes=access_token_expire_minutes)
        self.refresh_token_expire = timedelta(days=refresh_token_expire_days)
        self.blacklist: Dict[str, datetime] = {}  # {token: expiry_time}
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def create_access_token(
        self,
        username: str,
        user_id: str,
        role: str = "user"
    ) -> Tuple[str, datetime]:
        """
        Criar JWT access token

        Args:
            username: Nome do usuário
            user_id: ID do usuário
            role: Papel do usuário (user, trader, admin)

        Returns:
            (token_str, expiry_datetime)
        """
        now = datetime.now(timezone.utc)
        expires = now + self.access_token_expire

        payload = {
            'sub': username,
            'user_id': user_id,
            'role': role,
            'exp': int(expires.timestamp()),  # Unix timestamp
            'iat': int(now.timestamp()),      # Unix timestamp
            'type': 'access'
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expires

    def create_refresh_token(
        self,
        username: str,
        user_id: str
    ) -> Tuple[str, datetime]:
        """
        Criar JWT refresh token (duração maior)

        Args:
            username: Nome do usuário
            user_id: ID do usuário

        Returns:
            (token_str, expiry_datetime)
        """
        now = datetime.now(timezone.utc)
        expires = now + self.refresh_token_expire

        payload = {
            'sub': username,
            'user_id': user_id,
            'exp': int(expires.timestamp()),  # Unix timestamp
            'iat': int(now.timestamp()),      # Unix timestamp
            'type': 'refresh'
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, expires

    def verify_token(self, token: str) -> dict:
        """
        Verificar e decodificar JWT token

        Args:
            token: Token JWT para validar

        Returns:
            Dict com payload do token

        Raises:
            JWTError: Se token inválido/expirado/na blacklist
        """
        if self.is_blacklisted(token):
            raise JWTError("Token está na blacklist (logout realizado)")

        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        return payload

    def add_to_blacklist(self, token: str, expiry: datetime):
        """
        Adicionar token à blacklist (para logout)

        Args:
            token: Token a invalidar
            expiry: Data de expiração do token
        """
        self.blacklist[token] = expiry

    def is_blacklisted(self, token: str) -> bool:
        """
        Verificar se token está na blacklist

        Args:
            token: Token a verificar

        Returns:
            True se na blacklist, False caso contrário
        """
        if token not in self.blacklist:
            return False

        # Limpar tokens expirados da blacklist
        if self.blacklist[token] < datetime.utcnow():
            del self.blacklist[token]
            return False

        return True

    def hash_password(self, password: str) -> str:
        """
        Hash de senha com bcrypt

        Args:
            password: Senha em plaintext

        Returns:
            Senha criptografada (bcrypt)
        """
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verificar se senha corresponde ao hash

        Args:
            plain_password: Senha em plaintext
            hashed_password: Hash bcrypt

        Returns:
            True se senha correta, False caso contrário
        """
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception:
            return False
