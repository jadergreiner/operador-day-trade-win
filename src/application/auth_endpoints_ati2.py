"""
OAuth/JWT Endpoints para FastAPI
Implementação de /login, /refresh-token, /logout e /me (protegido)
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from datetime import datetime
from typing import Optional
from src.application.oauth_schemas_ati2 import (
    LoginRequest, TokenResponse, RefreshTokenRequest, LogoutResponse, UserInfo
)
from src.application.token_manager_ati2 import TokenManager
from jose import JWTError, jwt

router = APIRouter(prefix="/auth", tags=["authentication"])
token_manager = TokenManager()

# Mock user database (em produção seria em BD real)
USERS_DB = {
    "trader01": {
        "user_id": "user_001",
        "password_hash": token_manager.hash_password("SecurePass123!"),
        "role": "trader"
    },
    "admin01": {
        "user_id": "user_admin",
        "password_hash": token_manager.hash_password("AdminPass123!"),
        "role": "admin"
    }
}


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    Dependency para extraído usuário autenticado do token JWT
    
    Args:
        authorization: Header Authorization (Bearer token)
        
    Returns:
        Dict com payload do token
        
    Raises:
        HTTPException: Se token inválido/ausente
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Token ausente")
    
    try:
        # Extrair token de "Bearer <token>"
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(status_code=401, detail="Formato Authorization inválido")
        
        token = parts[1]
        payload = token_manager.verify_token(token)
        
        if payload.get('type') != 'access':
            raise HTTPException(status_code=401, detail="Token type inválido")
        
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Erro ao validar token: {str(e)}")


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    """
    AC-5.1: Endpoint de login - Retorna access + refresh tokens
    
    Args:
        credentials: LoginRequest com username e password
        
    Returns:
        TokenResponse com access_token e refresh_token
        
    Raises:
        HTTPException: Se credenciais inválidas
    """
    user = USERS_DB.get(credentials.username)
    
    if not user or not token_manager.verify_password(
        credentials.password, 
        user['password_hash']
    ):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    # Criar tokens
    access_token, access_expires = token_manager.create_access_token(
        username=credentials.username,
        user_id=user['user_id'],
        role=user['role']
    )
    
    refresh_token, refresh_expires = token_manager.create_refresh_token(
        username=credentials.username,
        user_id=user['user_id']
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(token_manager.access_token_expire.total_seconds())
    )


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token_endpoint(request: RefreshTokenRequest):
    """
    AC-5.2: Endpoint de refresh token - Renova access token
    
    Args:
        request: RefreshTokenRequest com refresh_token válido
        
    Returns:
        TokenResponse com novo access_token
        
    Raises:
        HTTPException: Se refresh token inválido/expirado
    """
    try:
        payload = token_manager.verify_token(request.refresh_token)
        
        if payload.get('type') != 'refresh':
            raise HTTPException(status_code=401, detail="Token type não é refresh")
        
        # Criar novo access token
        access_token, expires = token_manager.create_access_token(
            username=payload['sub'],
            user_id=payload['user_id'],
            role=payload.get('role', 'user')
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=request.refresh_token,  # Reusar refresh token
            expires_in=int(token_manager.access_token_expire.total_seconds())
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Erro ao renovar token: {str(e)}")


@router.post("/logout", response_model=LogoutResponse)
async def logout(current_user: dict = Depends(get_current_user), authorization: Optional[str] = Header(None)):
    """
    AC-5.3: Endpoint de logout - Invalida token na blacklist
    
    Args:
        current_user: Usuário extraído do token (via Depends)
        authorization: Header Authorization com token
        
    Returns:
        LogoutResponse confirmando logout
    """
    if authorization:
        try:
            token = authorization.split()[1]
            # Parse expiry do token (exp em Unix timestamp)
            payload = jwt.decode(token, token_manager.secret_key, algorithms=[token_manager.algorithm])
            exp_timestamp = payload.get('exp', 0)
            expiry = datetime.fromtimestamp(exp_timestamp) if isinstance(exp_timestamp, int) else datetime.utcnow()
            token_manager.add_to_blacklist(token, expiry)
        except Exception:
            pass  # Se não conseguir extrair expiry, apenas ignora
    
    return LogoutResponse(
        message=f"Logout realizado com sucesso para {current_user['sub']}",
        timestamp=datetime.utcnow()
    )


@router.get("/me", response_model=UserInfo)
async def get_user_info(current_user: dict = Depends(get_current_user)):
    """
    AC-5.4 + AC-5.5: Endpoint protegido - Retorna claims do JWT
    
    Demonstra:
    - AC-5.4: JWT com claims: sub, exp, iat, user_id, role
    - AC-5.5: Rejeita requisições sem token válido (401)
    
    Args:
        current_user: Usuário extraído via Depends(get_current_user)
        
    Returns:
        UserInfo com dados do token
        
    Raises:
        HTTPException 401 se token inválido/ausente (via Depends)
    """
    return UserInfo(
        username=current_user['sub'],
        user_id=current_user['user_id'],
        role=current_user['role'],
        issued_at=datetime.fromisoformat(current_user['iat']) if isinstance(current_user['iat'], str) else current_user['iat'],
        expires_at=datetime.fromisoformat(current_user['exp']) if isinstance(current_user['exp'], str) else current_user['exp']
    )


@router.get("/health")
async def health_check():
    """Health check para endpoint de auth"""
    return {"status": "ok", "service": "auth"}
